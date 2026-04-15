"""Orchestrator — central coordinator for plugin loading, test scheduling, and monitoring.

The heavy lifting is delegated to:
- ``case_utils``       — pure helpers for case filtering, band mapping, ID handling
- ``runner_selector``  — agent/runner selection and policy resolution
- ``execution_engine`` — per-case execution with retry and timeout escalation

This module keeps the public API identical to pre-split versions so that
``from testpilot.core.orchestrator import Orchestrator`` continues to work.
"""

from __future__ import annotations

from datetime import date, datetime
import json
import logging
from pathlib import Path
from typing import Any

try:
    from testpilot.core.copilot_session import (
        CopilotSDKUnavailableError,
        CopilotSessionManager,
        CopilotSessionRequest,
        build_case_session_plan,
        build_session_id,
    )
except Exception:  # pragma: no cover - optional during incremental rollout
    build_case_session_plan = None
    CopilotSDKUnavailableError = None  # type: ignore[assignment,misc]
    CopilotSessionManager = None  # type: ignore[assignment,misc]
    CopilotSessionRequest = None  # type: ignore[assignment,misc]
    build_session_id = None  # type: ignore[assignment]

from testpilot.core.case_utils import (
    band_results as _band_results,
    baseline_results_reference as _baseline_results_reference,
    case_aliases as _case_aliases,
    case_band_results as _case_band_results,
    case_matches_requested_ids as _case_matches_requested_ids,
    is_wifi_llapi_official_case as _is_wifi_llapi_official_case,
    overall_case_status as _overall_case_status,
    safe_float as _safe_float,
    safe_int as _safe_int,
    sanitize_case_id as _sanitize_case_id,
)
from testpilot.core.execution_engine import ExecutionEngine, RetryResult
from testpilot.core.advisory import AdvisoryCollector
from testpilot.core.hook_policy import HookDispatcher, build_hook_policy
from testpilot.core.plugin_loader import PluginLoader
from testpilot.core.remediation import RuntimeRemediationCoordinator
from testpilot.core.runner_selector import (
    DEFAULT_WIFI_LLAPI_EXECUTION_POLICY,
    RunnerSelector,
)
from testpilot.core.testbed_config import TestbedConfig
from testpilot.reporting.reporter import generate_reports
from testpilot.reporting import log_capture
from testpilot.reporting.wifi_llapi_excel import (
    ReportMeta,
    WifiLlapiCaseResult,
    collect_alignment_issues,
    create_run_report_from_template,
    ensure_template_report,
    fill_case_results,
    finalize_report_metadata,
    generate_report_filename,
)

log = logging.getLogger(__name__)

# 預設路徑（相對於專案根目錄）
DEFAULT_PLUGINS_DIR = "plugins"
DEFAULT_CONFIG_DIR = "configs"

# Re-export for backward compatibility
__all__ = ["Orchestrator", "DEFAULT_WIFI_LLAPI_EXECUTION_POLICY"]


class Orchestrator:
    """主編排器：載入 plugin、排程測試、協調監控與報告。

    Delegates runner selection to :class:`RunnerSelector` and per-case
    execution to :class:`ExecutionEngine`.
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        plugins_dir: Path | str | None = None,
        config_path: Path | str | None = None,
    ) -> None:
        self.root = Path(project_root) if project_root else Path(__file__).resolve().parents[3]
        self.plugins_dir = Path(plugins_dir) if plugins_dir else self.root / DEFAULT_PLUGINS_DIR
        config = config_path or self.root / DEFAULT_CONFIG_DIR / "testbed.yaml"
        self.config = TestbedConfig(config)
        log_capture.configure(
            binary=self.config.raw.get("testbed", {}).get("serialwrap_binary"),
        )
        self.loader = PluginLoader(self.plugins_dir)
        self.runner_selector = RunnerSelector(self.plugins_dir)
        self.execution_engine = ExecutionEngine(self.config)
        self.session_manager: CopilotSessionManager | None = self._try_init_session_manager()

    def _build_execution_engine(
        self,
        *,
        plugin_name: str,
        plugin: Any,
        agent_config: dict[str, Any],
    ) -> ExecutionEngine:
        policy = build_hook_policy(agent_config)
        dispatcher = HookDispatcher(policy)
        advisory_collector = AdvisoryCollector()
        advisory_handler = advisory_collector.to_hook_handler()
        dispatcher.register("on_failure", advisory_handler)
        dispatcher.register("post_case", advisory_handler)

        remediation_policy = agent_config.get("remediation", {})
        if not isinstance(remediation_policy, dict):
            remediation_policy = {}
        remediation = RuntimeRemediationCoordinator(
            plugin=plugin,
            topology=self.config,
            policy=remediation_policy,
        )
        for hook_name, handler in (
            ("pre_case", remediation.handle_pre_case),
            ("on_failure", remediation.handle_on_failure),
            ("on_retry", remediation.handle_on_retry),
            ("post_case", remediation.handle_post_case),
        ):
            dispatcher.register(hook_name, handler)
        self.execution_engine = ExecutionEngine(self.config, dispatcher)
        log.debug(
            "execution engine rebuilt for %s hooks=%s",
            plugin_name,
            dispatcher.registered_hooks,
        )
        return self.execution_engine

    # -- SDK session management ------------------------------------------------

    @staticmethod
    def _try_init_session_manager() -> CopilotSessionManager | None:
        """Try to create a CopilotSessionManager; return None if SDK unavailable."""
        if CopilotSessionManager is None:
            return None
        try:
            mgr = CopilotSessionManager()
            mgr._load_sdk()  # probe availability
            return mgr
        except Exception:
            log.debug("Copilot SDK unavailable — session foundation disabled")
            return None

    def _create_case_session(
        self,
        session_plan: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Attempt to create an SDK session from a session plan; return handle info or None."""
        if self.session_manager is None or CopilotSessionRequest is None:
            return None
        try:
            provider = session_plan.get("provider_config")
            request = CopilotSessionRequest(
                session_id=str(session_plan.get("session_id", "")),
                model=str(session_plan.get("model", "")),
                reasoning_effort=str(session_plan.get("reasoning_effort", "high")),
                provider=provider,
            )
            handle = self.session_manager.create_session(request)
            return {
                "session_id": handle.session_id,
                "workspace_path": handle.workspace_path,
                "status": "created",
            }
        except Exception as exc:
            log.warning("SDK session creation failed: %s", exc)
            return {"status": "failed", "error": str(exc)}

    def _cleanup_case_session(self, session_id: str | None) -> None:
        """Best-effort cleanup of a case-level SDK session."""
        if not session_id or self.session_manager is None:
            return
        try:
            self.session_manager.delete_session(session_id)
        except Exception:
            log.debug("SDK session cleanup failed for %s", session_id)

    # -- discovery -------------------------------------------------------------

    @staticmethod
    def _load_wifi_llapi_template_source(manifest_path: Path) -> str | None:
        if not manifest_path.exists():
            return None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            log.warning("failed to read wifi_llapi template manifest: %s", manifest_path)
            return None
        source_workbook = payload.get("source_workbook")
        if not isinstance(source_workbook, str):
            return None
        source_text = source_workbook.strip()
        return source_text or None

    def discover_plugins(self) -> list[str]:
        """列出所有可用 plugin。"""
        return self.loader.discover()

    def list_cases(self, plugin_name: str) -> list[dict[str, Any]]:
        """載入指定 plugin 並列出其 test cases。"""
        plugin = self.loader.load(plugin_name)
        return plugin.discover_cases()

    # -- backward-compatible static/class delegates ----------------------------
    # Existing tests call e.g. ``Orchestrator._safe_int(...)``; keep them
    # working by delegating to the new ``case_utils`` module.

    @staticmethod
    def _band_results(status: str, bands: list[str] | None) -> tuple[str, str, str]:
        return _band_results(status, bands)

    @staticmethod
    def _baseline_results_reference(case: dict[str, Any]) -> dict[str, Any] | None:
        return _baseline_results_reference(case)

    @classmethod
    def _case_band_results(cls, case: dict[str, Any], verdict: bool) -> tuple[str, str, str]:
        return _case_band_results(case, verdict)

    @staticmethod
    def _overall_case_status(result_5g: str, result_6g: str, result_24g: str) -> str:
        return _overall_case_status(result_5g, result_6g, result_24g)

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        return _safe_int(value, default)

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        return _safe_float(value, default)

    @staticmethod
    def _sanitize_case_id(case_id: str) -> str:
        return _sanitize_case_id(case_id)

    @staticmethod
    def _case_aliases(case: dict[str, Any]) -> list[str]:
        return _case_aliases(case)

    @classmethod
    def _case_matches_requested_ids(
        cls,
        case: dict[str, Any],
        requested_ids: set[str],
    ) -> bool:
        return _case_matches_requested_ids(case, requested_ids)

    @staticmethod
    def _is_wifi_llapi_official_case(case: dict[str, Any]) -> bool:
        return _is_wifi_llapi_official_case(case)

    # -- runner selection delegates (backward compat) --------------------------

    def _load_wifi_llapi_agent_config(self, plugin_name: str) -> dict[str, Any]:
        return self.runner_selector.load_agent_config(plugin_name)

    def _wifi_llapi_execution_policy(self, agent_config: dict[str, Any]) -> dict[str, Any]:
        return self.runner_selector.build_execution_policy(agent_config)

    def _enabled_runners(self, agent_config: dict[str, Any]) -> list[dict[str, Any]]:
        return self.runner_selector.enabled_runners(agent_config)

    def _runner_availability_overrides(self, plugin_name: str) -> dict[str, str | bool]:
        return self.runner_selector.runner_availability_overrides(plugin_name)

    @staticmethod
    def _runner_summary(runner: dict[str, Any]) -> dict[str, Any]:
        return RunnerSelector.runner_summary(runner)

    def _match_runner_by_selector(
        self, selector: Any, runners: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        return self.runner_selector.match_runner_by_selector(selector, runners)

    def _normalize_runtime_selection(
        self, selection: Any, runners: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        return self.runner_selector.normalize_runtime_selection(selection, runners)

    def _select_runner_via_agent_runtime(
        self,
        plugin_name: str,
        case: dict[str, Any],
        agent_config: dict[str, Any],
        runners: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        return self.runner_selector.select_runner_via_agent_runtime(
            plugin_name, case, agent_config, runners
        )

    def _select_case_runner(
        self,
        plugin_name: str,
        case: dict[str, Any],
        agent_config: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.runner_selector.select_case_runner(plugin_name, case, agent_config)

    # -- execution delegates (backward compat) ---------------------------------

    def _attempt_timeout_seconds(
        self,
        *,
        steps_count: int,
        attempt_index: int,
        execution_policy: dict[str, Any],
    ) -> float:
        return ExecutionEngine.attempt_timeout_seconds(
            steps_count=steps_count,
            attempt_index=attempt_index,
            execution_policy=execution_policy,
        )

    def _execute_wifi_llapi_case_once(
        self,
        plugin: Any,
        case: dict[str, Any],
        *,
        attempt_index: int,
        attempt_timeout_seconds: float,
        runner: dict[str, Any],
    ) -> dict[str, Any]:
        return self.execution_engine.execute_case_once(
            plugin=plugin,
            case=case,
            attempt_index=attempt_index,
            attempt_timeout_seconds=attempt_timeout_seconds,
            runner=runner,
        )

    @staticmethod
    def _write_case_trace(path: Path, payload: dict[str, Any]) -> None:
        ExecutionEngine.write_case_trace(path, payload)

    # -- serialwrap log lifecycle helpers --------------------------------------

    def _start_serialwrap_for_run(self) -> Path | None:
        """確保 serialwrap daemon 已啟動並重設 WAL。

        若 daemon 已在執行，只做 wal.reset（不重啟，不斷線）。
        若 daemon 未執行，啟動新 daemon 並設定 sessions。
        Returns the WAL path on success, None if serialwrap is unavailable.
        """
        try:
            status = log_capture.daemon_status()
            if status and status.get("ok"):
                # daemon 已執行：用 wal.reset 取代 restart
                log_capture.wal_reset()
                wal_path = log_capture.get_wal_path()
                log.info("serialwrap daemon already running (pid=%s), WAL reset done",
                         status.get("pid"))
                return wal_path

            # daemon 未執行：啟動新 daemon
            log_capture.clean_wal()
            log_capture.start_daemon()
            wal_path = log_capture.get_wal_path()
            # Setup sessions from testbed config (keys may be DUT/dut)
            devs = self.config.devices
            dut_cfg = devs.get("dut") or devs.get("DUT") or {}
            sta_cfg = devs.get("sta") or devs.get("STA") or {}
            devices = []
            for alias, cfg in [("dut", dut_cfg), ("sta", sta_cfg)]:
                selector = cfg.get("selector", "")
                if selector:
                    devices.append({
                        "com": selector,
                        "alias": alias,
                        "profile": "prpl-template",
                        "serial_port": cfg.get("serial_port", ""),
                    })
            if devices:
                log_capture.setup_sessions(devices)
            log.info("serialwrap daemon started, wal_path=%s", wal_path)
            return wal_path
        except Exception:
            log.warning("serialwrap daemon start failed; logs will be unavailable", exc_info=True)
            return None

    def _stop_serialwrap(self) -> None:
        """Run 結束後的 serialwrap 清理。

        不再 stop daemon，讓 human console 持續連線。
        """
        log.debug("serialwrap daemon kept alive for console coexistence")

    def _export_serialwrap_logs(
        self,
        *,
        run_id: str,
        reports_root: Path,
        case_seq_ranges: dict[str, dict[str, int | None]],
        case_results: list[WifiLlapiCaseResult],
    ) -> dict[str, str]:
        """Export WAL records, decode DUT/STA logs, and annotate case results."""
        records = log_capture.export_records(from_seq=1)
        if not records:
            return {}

        devs = self.config.devices
        dut_dev = devs.get("dut") or devs.get("DUT") or {}
        sta_dev = devs.get("sta") or devs.get("STA") or {}
        dut_com = dut_dev.get("com_port") or dut_dev.get("selector", "COM0")
        sta_com = sta_dev.get("com_port") or sta_dev.get("selector", "COM1")

        # Decode & save per-device log files
        dut_text = log_capture.decode_log(records, com_filter=dut_com)
        sta_text = log_capture.decode_log(records, com_filter=sta_com)
        dut_log_path = log_capture.save_decoded_log(
            dut_text, reports_root / f"{run_id}_DUT.log"
        )
        sta_log_path = log_capture.save_decoded_log(
            sta_text, reports_root / f"{run_id}_STA.log"
        )

        # Build seq→line maps
        dut_line_map = log_capture.build_seq_to_line_map(records, com_filter=dut_com)
        sta_line_map = log_capture.build_seq_to_line_map(records, com_filter=sta_com)

        # Annotate each case result with log line ranges
        for cr in case_results:
            seq_range = case_seq_ranges.get(cr.case_id)
            if not seq_range:
                continue
            s, e = seq_range.get("seq_start"), seq_range.get("seq_end")
            cr.dut_log_lines = log_capture.seq_range_to_line_range(
                s, e, dut_line_map
            )
            cr.sta_log_lines = log_capture.seq_range_to_line_range(
                s, e, sta_line_map
            )

        log.info("serialwrap logs saved: %s, %s", dut_log_path, sta_log_path)
        return {
            "dut_log_path": str(dut_log_path),
            "sta_log_path": str(sta_log_path),
        }

    # -- wifi_llapi run loop ---------------------------------------------------

    def _run_wifi_llapi(
        self,
        plugin_name: str,
        case_ids: list[str] | None,
        dut_fw_ver: str | None,
        report_source_xlsx: str | None,
        provider_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plugin = self.loader.load(plugin_name)
        discovered_cases = plugin.discover_cases()
        if case_ids:
            requested_ids = {str(case_id).strip() for case_id in case_ids if str(case_id).strip()}
            cases = [
                c for c in discovered_cases if _case_matches_requested_ids(c, requested_ids)
            ]
        else:
            cases = [
                c
                for c in discovered_cases
                if _is_wifi_llapi_official_case(c)
            ]

        reports_root = self.plugins_dir / plugin_name / "reports"
        template_path = reports_root / "templates" / "wifi_llapi_template.xlsx"
        manifest_path = reports_root / "templates" / "wifi_llapi_template.manifest.json"
        source_xlsx = Path(report_source_xlsx) if report_source_xlsx else None
        alignment_xlsx: Path
        source_report = ""

        if source_xlsx is not None:
            if not source_xlsx.exists():
                raise FileNotFoundError(f"wifi_llapi source report not found: {source_xlsx}")
            ensure_template_report(
                source_xlsx=source_xlsx,
                template_path=template_path,
                manifest_path=manifest_path,
            )
            alignment_xlsx = source_xlsx
            source_report = str(source_xlsx)
        elif template_path.exists():
            alignment_xlsx = template_path
            source_report = self._load_wifi_llapi_template_source(manifest_path) or str(template_path)
        else:
            raise FileNotFoundError(
                "wifi_llapi template not found. Run "
                "`testpilot wifi-llapi build-template-report --source-xlsx <path>` "
                "or pass `--report-source-xlsx <path>` to rebuild it."
            )

        alignment_issues = collect_alignment_issues(cases, alignment_xlsx)
        if alignment_issues:
            alignment_dir = reports_root / "alignment"
            alignment_dir.mkdir(parents=True, exist_ok=True)
            alignment_path = alignment_dir / f"{date.today():%Y%m%d}_wifi_llapi_alignment_issues.json"
            alignment_path.write_text(
                json.dumps(
                    {
                        "source_report": source_report,
                        "alignment_sheet": str(alignment_xlsx),
                        "issues_count": len(alignment_issues),
                        "issues": alignment_issues,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            log.warning(
                "alignment issues: %d case(s) have source.row mismatch with template Excel "
                "(report row placement may be inaccurate); report: %s",
                len(alignment_issues),
                alignment_path,
            )

        agent_config = self.runner_selector.load_agent_config(plugin_name)
        execution_policy = self.runner_selector.build_execution_policy(agent_config)
        self._build_execution_engine(
            plugin_name=plugin_name,
            plugin=plugin,
            agent_config=agent_config,
        )
        run_id = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        agent_trace_dir = reports_root / "agent_trace" / run_id
        agent_trace_dir.mkdir(parents=True, exist_ok=True)

        run_date = date.today()
        fw_ver = dut_fw_ver or "DUT-FW-VER"
        report_name = generate_report_filename(run_date, fw_ver, unique_suffix=run_id)
        report_path = reports_root / report_name
        report_path = create_run_report_from_template(
            template_xlsx=template_path,
            out_report_xlsx=report_path,
        )

        case_results: list[WifiLlapiCaseResult] = []
        pass_count = 0
        fail_count = 0
        case_trace_files: list[str] = []

        # -- serialwrap daemon lifecycle: start fresh for this run -------------
        wal_path = self._start_serialwrap_for_run()
        case_seq_ranges: dict[str, dict[str, int | None]] = {}

        for case in cases:
            case_id = str(case.get("id", "?"))
            source = case.get("source", {}) if isinstance(case.get("source"), dict) else {}
            try:
                source_row = int(source.get("row", 0))
            except (TypeError, ValueError):
                source_row = 0

            raw_steps = case.get("steps", [])
            steps_count = len(raw_steps) if isinstance(raw_steps, list) else 0

            selected_runner, selection_trace = self.runner_selector.select_case_runner(
                plugin_name=plugin_name,
                case=case,
                agent_config=agent_config,
            )
            if callable(build_case_session_plan):
                session_plan = build_case_session_plan(
                    run_id, case_id, selected_runner,
                    provider_config=provider_config,
                )
                if session_plan is not None:
                    selection_trace["session_plan"] = session_plan

            # Wire SDK session if a plan was created
            active_session_id: str | None = None
            session_plan_dict = selection_trace.get("session_plan")
            if session_plan_dict and isinstance(session_plan_dict, dict):
                session_handle = self._create_case_session(session_plan_dict)
                if session_handle:
                    selection_trace["session_handle"] = session_handle
                    if session_handle.get("status") == "created":
                        active_session_id = session_handle.get("session_id")

            seq_before = log_capture.get_current_seq(wal_path)
            try:
                retry_result = self.execution_engine.execute_with_retry(
                    plugin=plugin,
                    case=case,
                    runner=selected_runner,
                    execution_policy=execution_policy,
                )
            finally:
                self._cleanup_case_session(active_session_id)
            seq_after = log_capture.get_current_seq(wal_path)
            case_seq_ranges[case_id] = {
                "seq_start": seq_before,
                "seq_end": seq_after,
            }
            verdict = retry_result.verdict
            comment = retry_result.comment
            commands = retry_result.commands
            outputs = retry_result.outputs
            attempts_trace = retry_result.attempts

            result_5g, result_6g, result_24g = _case_band_results(case, verdict)
            status = _overall_case_status(result_5g, result_6g, result_24g)

            # Enrich attempt entries with band-level status for trace
            for att in attempts_trace:
                att_verdict = att.get("verdict", False)
                a5, a6, a24 = _case_band_results(case, att_verdict)
                att["status"] = _overall_case_status(a5, a6, a24)

            case_trace_path = (
                agent_trace_dir / f"{_sanitize_case_id(case_id)}.json"
            )
            ExecutionEngine.write_case_trace(
                case_trace_path,
                {
                    "run_id": run_id,
                    "plugin": plugin_name,
                    "case_id": case_id,
                    "source_row": source_row,
                    "execution": execution_policy,
                    "selection_trace": selection_trace,
                    "attempts": attempts_trace,
                    "final": {
                        "status": status,
                        "evaluation_verdict": "Pass" if verdict else "Fail",
                        "attempts_used": retry_result.attempts_used,
                        "comment": comment,
                        "diagnostic_status": retry_result.diagnostic_status,
                    },
                    "diagnostic_status": retry_result.diagnostic_status,
                    "remediation_history": retry_result.remediation_history or [],
                    "failure_snapshot": retry_result.failure_snapshot,
                },
            )
            case_trace_files.append(str(case_trace_path))

            if status == "Pass":
                pass_count += 1
            else:
                fail_count += 1
            case_results.append(
                WifiLlapiCaseResult(
                    case_id=case_id,
                    source_row=source_row,
                    executed_test_command="\n".join(commands).strip(),
                    command_output="\n".join(outputs).strip(),
                    result_5g=result_5g,
                    result_6g=result_6g,
                    result_24g=result_24g,
                    comment=comment,
                    diagnostic_status=retry_result.diagnostic_status,
                    remediation_history=retry_result.remediation_history or [],
                    failure_snapshot=retry_result.failure_snapshot,
                )
            )

        # -- serialwrap log export & decode ------------------------------------
        dut_log_path = ""
        sta_log_path = ""
        try:
            log_result = self._export_serialwrap_logs(
                run_id=run_id,
                reports_root=reports_root,
                case_seq_ranges=case_seq_ranges,
                case_results=case_results,
            )
            dut_log_path = log_result.get("dut_log_path", "")
            sta_log_path = log_result.get("sta_log_path", "")
        except Exception:
            log.warning("serialwrap log export failed", exc_info=True)
        finally:
            self._stop_serialwrap()

        fill_case_results(report_xlsx=report_path, case_results=case_results)
        finalize_report_metadata(
            report_xlsx=report_path,
            meta=ReportMeta(
                run_date=run_date,
                dut_fw_ver=fw_ver,
                source_excel=source_report,
            ),
        )

        # -- md / json reports ------------------------------------------------
        import dataclasses

        report_meta: dict[str, Any] = {
            "title": f"{fw_ver}_wifi_LLAPI_{run_id}",
            "date": run_date.isoformat(),
            "plugin": plugin_name,
            "firmware_version": fw_ver,
            "run_id": run_id,
        }
        case_dicts = [dataclasses.asdict(cr) for cr in case_results]
        md_json_paths = generate_reports(
            case_results=case_dicts,
            meta=report_meta,
            output_dir=reports_root,
            formats=["md", "json"],
        )
        for p in md_json_paths:
            log.info("wifi_llapi %s report generated: %s", p.suffix, p)

        log.info("wifi_llapi report generated: %s", report_path)
        return {
            "plugin": plugin_name,
            "plugin_version": plugin.version,
            "cases_count": len(cases),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "status": "completed",
            "template_path": str(template_path),
            "report_path": str(report_path),
            "md_report_path": str(md_json_paths[0]) if len(md_json_paths) > 0 else "",
            "json_report_path": str(md_json_paths[1]) if len(md_json_paths) > 1 else "",
            "dut_log_path": dut_log_path,
            "sta_log_path": sta_log_path,
            "source_report": source_report,
            "run_id": run_id,
            "agent_trace_dir": str(agent_trace_dir),
            "agent_trace_count": len(case_trace_files),
        }

    # -- public entry point ----------------------------------------------------

    def run(
        self,
        plugin_name: str,
        case_ids: list[str] | None = None,
        *,
        dut_fw_ver: str | None = None,
        report_source_xlsx: str | None = None,
        provider_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """執行測試。

        wifi_llapi plugin:
        - builds/extracts template report from source Excel sheet,
        - executes cases through plugin hooks,
        - fills report test command/result columns by source row.

        other plugins:
        - keeps skeleton behavior.
        """
        if plugin_name == "wifi_llapi":
            return self._run_wifi_llapi(
                plugin_name=plugin_name,
                case_ids=case_ids,
                dut_fw_ver=dut_fw_ver,
                report_source_xlsx=report_source_xlsx,
                provider_config=provider_config,
            )

        plugin = self.loader.load(plugin_name)
        cases = plugin.discover_cases()
        if case_ids:
            requested_ids = {str(case_id).strip() for case_id in case_ids if str(case_id).strip()}
            cases = [c for c in cases if _case_matches_requested_ids(c, requested_ids)]

        log.info("would run %d cases from plugin '%s'", len(cases), plugin_name)
        return {
            "plugin": plugin_name,
            "plugin_version": plugin.version,
            "cases_count": len(cases),
            "case_ids": [c.get("id", "?") for c in cases],
            "status": "skeleton — not yet implemented",
        }
