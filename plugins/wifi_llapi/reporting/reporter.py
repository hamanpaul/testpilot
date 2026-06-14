"""WifiLlapiReporter — owns the wifi_llapi run/report generation flow.

This module hosts the report-generation pipeline that previously lived inside
``testpilot.core.orchestrator``.  The computation is moved verbatim; the core
orchestrator now delegates the full wifi_llapi run via ``plugin.create_reporter()``
without naming wifi_llapi itself.

``WifiLlapiReporter`` is dual-purpose:

* It implements the :class:`IReporter` protocol (``generate``) by delegating to
  the core :class:`~testpilot.reporting.reporter.MarkdownReporter`, so it can be
  returned from ``Plugin.create_reporter()``.
* It exposes :meth:`run`, which executes the complete wifi_llapi run-and-report
  flow.  The orchestrator calls this when the plugin's reporter advertises it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
import logging
import time
from typing import Any, Mapping, Sequence

from testpilot.core.case_utils import (
    case_band_results as _case_band_results,
    case_matches_requested_ids as _case_matches_requested_ids,
    is_wifi_llapi_official_case as _is_wifi_llapi_official_case,
    overall_case_status as _overall_case_status,
    sanitize_case_id as _sanitize_case_id,
)
from testpilot.core.execution_engine import ExecutionEngine
from testpilot.reporting.reporter import MarkdownReporter, generate_reports
from testpilot.schema.case_schema import load_case, validate_wifi_llapi_case

from plugins.wifi_llapi.reporting.wifi_llapi_align import (
    AlignResult,
    _resolve_collisions,
    align_case,
    apply_alignment_mutations,
    build_template_index,
    write_blocked_cases_report,
    write_skipped_cases_report,
)
from plugins.wifi_llapi.reporting.wifi_llapi_excel import (
    ReportMeta,
    WifiLlapiCaseResult,
    create_run_report_from_template,
    fill_blocked_markers,
    fill_case_results,
    fill_skip_markers,
    finalize_report_metadata,
    generate_report_filename,
    read_wifi_llapi_template_objects,
    write_summary_sheet,
)
from plugins.wifi_llapi.reporting.wifi_llapi_summary import build_wifi_llapi_summary

log = logging.getLogger(__name__)


@dataclass(slots=True)
class WifiLlapiAlignmentPrep:
    runnable_cases: list[dict[str, Any]]
    blocked_results: list[Any]
    skipped_results: list[Any]
    alignment_summary: dict[str, Any]


class WifiLlapiReporter:
    """Plugin-side reporter that owns the wifi_llapi run/report flow.

    Implements the IReporter ``generate`` contract (delegating to the core
    MarkdownReporter) and exposes :meth:`run` for the full pipeline.
    """

    def __init__(self) -> None:
        self._markdown = MarkdownReporter()

    # -- IReporter protocol ----------------------------------------------------

    def generate(
        self,
        case_results: Sequence[Mapping[str, Any]],
        meta: Mapping[str, Any],
        output_path: Path,
    ) -> Path:
        return self._markdown.generate(case_results, meta, output_path)

    # -- firmware / case loading ----------------------------------------------

    def _resolve_firmware_version(
        self,
        orchestrator: Any,
        *,
        plugin: Any,
        cases: list[dict[str, Any]],
        requested: str | None,
    ) -> tuple[str, str]:
        requested_value = (requested or "").strip()
        if requested_value and requested_value != "DUT-FW-VER":
            return requested_value, "cli"
        capture = getattr(plugin, "capture_dut_firmware_version", None)
        if callable(capture):
            captured = str(capture(orchestrator.config, cases) or "").strip()
            if captured:
                return captured, "dut_git_revision"
        return "DUT-FW-VER", "fallback_default"

    def _load_case_pairs(
        self,
        *,
        plugin: Any,
        case_ids: list[str] | None,
    ) -> list[tuple[Path, dict[str, Any]]]:
        case_files = [
            path
            for path in sorted(plugin.cases_dir.glob("*.y*ml"))
            if not path.stem.startswith("_")
        ]
        case_pairs = [(path, load_case(path, validator=validate_wifi_llapi_case)) for path in case_files]
        if case_ids:
            requested_ids = {str(case_id).strip() for case_id in case_ids if str(case_id).strip()}
            return [
                (path, case)
                for path, case in case_pairs
                if _case_matches_requested_ids(case, requested_ids)
            ]
        return [
            (path, case)
            for path, case in case_pairs
            if _is_wifi_llapi_official_case(case)
        ]

    # -- alignment -------------------------------------------------------------

    @staticmethod
    def _build_alignment_summary(align_results: list[Any]) -> dict[str, Any]:
        blocked_details = [
            {
                "case_id": result.id_before,
                "reason": result.blocked_reason,
                "candidate_template_rows": list(result.candidate_template_rows or []),
            }
            for result in align_results
            if result.status == "blocked"
        ]
        return {
            "already_aligned": sum(
                1 for result in align_results if result.status == "already_aligned"
            ),
            "auto_aligned": sum(1 for result in align_results if result.status == "auto_aligned"),
            "blocked": sum(1 for result in align_results if result.status == "blocked"),
            "skipped": sum(1 for result in align_results if result.status == "skipped"),
            "blocked_details": blocked_details,
            "mutations": [
                {
                    "case_id": result.id_before,
                    "filename_before": result.filename_before,
                    "filename_after": result.case_file.name,
                    "source_row_before": result.source_row_before,
                    "source_row_after": result.source_row_after,
                    "id_after": result.id_after or result.id_before,
                    "status": result.status,
                }
                for result in align_results
            ],
        }

    def _prepare_alignment(
        self,
        *,
        plugin: Any,
        case_ids: list[str] | None,
        template_path: Path,
    ) -> WifiLlapiAlignmentPrep:
        case_pairs = self._load_case_pairs(plugin=plugin, case_ids=case_ids)
        index = build_template_index(template_path)
        align_results: list[AlignResult] = []
        validate_delta_schema = getattr(plugin, "_validate_delta_schema", None)
        for path, case in case_pairs:
            if callable(validate_delta_schema):
                error = validate_delta_schema(case)
                if error:
                    source = case.get("source") if isinstance(case.get("source"), dict) else {}
                    align_results.append(
                        AlignResult(
                            case_file=path,
                            status="blocked",
                            source_row_before=int(source.get("row", 0) or 0),
                            source_row_after=None,
                            source_object=str(source.get("object", "") or ""),
                            source_api=str(source.get("api", "") or ""),
                            filename_before=path.name,
                            filename_after=None,
                            id_before=str(case.get("id", "")),
                            id_after=None,
                            blocked_reason=f"invalid_delta_schema: {error}",
                        )
                    )
                    continue
            align_results.append(align_case(case, index, path))
        _resolve_collisions(align_results)
        apply_alignment_mutations(align_results)
        runnable_results = [
            result
            for result in align_results
            if result.status in {"already_aligned", "auto_aligned"}
        ]
        blocked_results = [result for result in align_results if result.status == "blocked"]
        skipped_results = [result for result in align_results if result.status == "skipped"]
        return WifiLlapiAlignmentPrep(
            runnable_cases=[
                load_case(result.case_file, validator=validate_wifi_llapi_case)
                for result in runnable_results
            ],
            blocked_results=blocked_results,
            skipped_results=skipped_results,
            alignment_summary=self._build_alignment_summary(align_results),
        )

    @staticmethod
    def _finalize_alignment_artifacts(
        *,
        report_path: Path,
        artifact_dir: Path,
        prep: WifiLlapiAlignmentPrep,
    ) -> None:
        fill_blocked_markers(report_xlsx=report_path, blocked=prep.blocked_results)
        fill_skip_markers(report_xlsx=report_path, skipped=prep.skipped_results)
        write_blocked_cases_report(prep.blocked_results, artifact_dir / "blocked_cases.md")
        write_skipped_cases_report(prep.skipped_results, artifact_dir / "skipped_cases.md")

    # -- run loop --------------------------------------------------------------

    def run(
        self,
        orchestrator: Any,
        plugin_name: str,
        case_ids: list[str] | None,
        dut_fw_ver: str | None,
        provider_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from testpilot.reporting import log_capture
        from testpilot.core.orchestrator import build_case_session_plan

        plugin = orchestrator.loader.load(plugin_name)
        reports_root = orchestrator.plugins_dir / plugin_name / "reports"
        template_path = reports_root / "templates" / "wifi_llapi_template.xlsx"
        run_date = date.today()

        if not template_path.exists():
            raise FileNotFoundError(
                "wifi_llapi template not found. Run "
                "`testpilot wifi-llapi build-template-report --source-xlsx <path>` "
                "to rebuild it."
            )

        alignment_prep = self._prepare_alignment(
            plugin=plugin,
            case_ids=case_ids,
            template_path=template_path,
        )
        cases = alignment_prep.runnable_cases

        # -- serialwrap daemon lifecycle: start fresh for this run -------------
        wal_path = orchestrator._start_serialwrap_for_run()
        run_seq_start = log_capture.get_current_seq(wal_path)

        fw_ver, fw_ver_source = self._resolve_firmware_version(
            orchestrator,
            plugin=plugin,
            cases=cases,
            requested=dut_fw_ver,
        )
        run_id = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        report_name = generate_report_filename(run_date, fw_ver, unique_suffix=run_id)
        artifact_name = Path(report_name).stem
        artifact_dir = reports_root / artifact_name
        artifact_dir.mkdir(parents=True, exist_ok=True)

        agent_config = orchestrator.runner_selector.load_agent_config(plugin_name)
        execution_policy = orchestrator.runner_selector.build_execution_policy(agent_config)
        orchestrator._build_execution_engine(
            plugin_name=plugin_name,
            plugin=plugin,
            agent_config=agent_config,
        )
        agent_trace_dir = artifact_dir / "agent_trace"
        agent_trace_dir.mkdir(parents=True, exist_ok=True)

        report_path = artifact_dir / report_name
        report_path = create_run_report_from_template(
            template_xlsx=template_path,
            out_report_xlsx=report_path,
        )

        case_results: list[WifiLlapiCaseResult] = []
        pass_count = 0
        fail_count = 0
        case_trace_files: list[str] = []
        run_started_monotonic = time.monotonic()
        run_started_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        first_case_started_monotonic: float | None = None
        first_case_started_at_iso = ""

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

            selected_runner, selection_trace = orchestrator.runner_selector.select_case_runner(
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
                session_handle = orchestrator._create_case_session(session_plan_dict)
                if session_handle:
                    selection_trace["session_handle"] = session_handle
                    if session_handle.get("status") == "created":
                        active_session_id = session_handle.get("session_id")

            seq_before = log_capture.get_current_seq(wal_path)
            case_started_monotonic = time.monotonic()
            case_started_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
            if first_case_started_monotonic is None:
                first_case_started_monotonic = case_started_monotonic
                first_case_started_at_iso = case_started_at_iso
            try:
                retry_result = orchestrator.execution_engine.execute_with_retry(
                    plugin=plugin,
                    case=case,
                    runner=selected_runner,
                    execution_policy=execution_policy,
                )
            finally:
                orchestrator._cleanup_case_session(active_session_id)
            case_finished_monotonic = time.monotonic()
            case_finished_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
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
                    case_started_at=case_started_at_iso,
                    case_finished_at=case_finished_at_iso,
                    case_duration_seconds=round(
                        case_finished_monotonic - case_started_monotonic,
                        3,
                    ),
                    overall_status=status,
                )
            )

        # -- serialwrap log export & decode ------------------------------------
        dut_log_path = ""
        sta_log_path = ""
        try:
            run_seq_end = log_capture.get_current_seq(wal_path)
            log_result = orchestrator._export_serialwrap_logs(
                run_id=run_id,
                artifact_dir=artifact_dir,
                case_seq_ranges=case_seq_ranges,
                case_results=case_results,
                run_seq_start=run_seq_start,
                run_seq_end=run_seq_end,
            )
            dut_log_path = log_result.get("dut_log_path", "")
            sta_log_path = log_result.get("sta_log_path", "")
        except Exception:
            log.warning("serialwrap log export failed", exc_info=True)
        finally:
            orchestrator._stop_serialwrap()

        fill_case_results(report_xlsx=report_path, case_results=case_results)
        self._finalize_alignment_artifacts(
            report_path=report_path,
            artifact_dir=artifact_dir,
            prep=alignment_prep,
        )
        finalize_report_metadata(
            report_xlsx=report_path,
            meta=ReportMeta(
                run_date=run_date,
                dut_fw_ver=fw_ver,
                source_excel="",
            ),
        )

        # -- md / json / html reports -----------------------------------------
        run_finished_monotonic = time.monotonic()
        run_finished_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        timing_rows: list[dict[str, Any]] = [
            {
                "metric": "suite run",
                "started_at": run_started_at_iso,
                "finished_at": run_finished_at_iso,
                "duration_seconds": round(
                    run_finished_monotonic - run_started_monotonic,
                    3,
                ),
            }
        ]
        if first_case_started_monotonic is not None:
            timing_rows.append(
                {
                    "metric": "environment buildup",
                    "started_at": run_started_at_iso,
                    "finished_at": first_case_started_at_iso,
                    "duration_seconds": round(
                        first_case_started_monotonic - run_started_monotonic,
                        3,
                    ),
                }
            )

        case_dicts = [asdict(cr) for cr in case_results]
        template_objects = read_wifi_llapi_template_objects(template_path)
        wifi_llapi_summary = build_wifi_llapi_summary(case_dicts, template_objects)
        write_summary_sheet(report_path, wifi_llapi_summary)

        report_meta: dict[str, Any] = {
            "title": artifact_name,
            "date": run_date.isoformat(),
            "plugin": plugin_name,
            "firmware_version": fw_ver,
            "firmware_version_source": fw_ver_source,
            "run_id": run_id,
            "timing": timing_rows,
            "output_stem": artifact_name,
            "alignment_summary": alignment_prep.alignment_summary,
            "plugin_summary": wifi_llapi_summary,
        }
        report_paths = generate_reports(
            case_results=case_dicts,
            meta=report_meta,
            output_dir=artifact_dir,
            formats=["md", "json", "html"],
        )
        paths_by_suffix = {p.suffix.lstrip("."): p for p in report_paths}
        for p in report_paths:
            log.info("wifi_llapi %s report generated: %s", p.suffix, p)

        log.info("wifi_llapi report generated: %s", report_path)
        return {
            "plugin": plugin_name,
            "plugin_version": plugin.version,
            "cases_count": len(cases),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "status": "completed",
            "artifact_dir": str(artifact_dir),
            "template_path": str(template_path),
            "report_path": str(report_path),
            "md_report_path": str(paths_by_suffix.get("md", "")),
            "json_report_path": str(paths_by_suffix.get("json", "")),
            "html_report_path": str(paths_by_suffix.get("html", "")),
            "dut_log_path": dut_log_path,
            "sta_log_path": sta_log_path,
            "run_id": run_id,
            "agent_trace_dir": str(agent_trace_dir),
            "agent_trace_count": len(case_trace_files),
        }
