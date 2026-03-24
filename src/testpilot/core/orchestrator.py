"""Orchestrator — central coordinator for plugin loading, test scheduling, and monitoring."""

from __future__ import annotations

from datetime import date, datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

import yaml

try:
    from testpilot.core import agent_runtime as agent_runtime_module
except Exception:  # pragma: no cover - optional module during incremental rollout
    agent_runtime_module = None
try:
    from testpilot.core.copilot_session import build_case_session_plan
except Exception:  # pragma: no cover - optional during incremental rollout
    build_case_session_plan = None

from testpilot.core.plugin_loader import PluginLoader
from testpilot.core.testbed_config import TestbedConfig
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
DEFAULT_WIFI_LLAPI_SOURCE_XLSX = (
    "/mnt/c/Users/paul_chen/Downloads/0302-AT&T_LLAPI_Test_Report_20260107.xlsx"
)
DEFAULT_WIFI_LLAPI_EXECUTION_POLICY: dict[str, Any] = {
    "scope": "per_case",
    "mode": "sequential",
    "max_concurrency": 1,
    "failure_policy": "retry_then_fail_and_continue",
    "retry": {
        "max_attempts": 2,
        "backoff_seconds": 5,
    },
    "timeout": {
        "base_seconds": 120,
        "per_step_seconds": 45,
        "retry_multiplier": 1.25,
        "max_seconds": 900,
    },
}


class Orchestrator:
    """主編排器：載入 plugin、排程測試、協調監控與報告。"""

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
        self.loader = PluginLoader(self.plugins_dir)

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

    @staticmethod
    def _band_results(status: str, bands: list[str] | None) -> tuple[str, str, str]:
        if not bands:
            return status, status, status
        normalized = {b.strip().lower() for b in bands}
        r5 = status if "5g" in normalized else "N/A"
        r6 = status if "6g" in normalized else "N/A"
        r24 = status if "2.4g" in normalized else "N/A"
        return r5, r6, r24

    @staticmethod
    def _baseline_results_reference(case: dict[str, Any]) -> dict[str, Any] | None:
        source = case.get("source")
        if not isinstance(source, dict):
            return None
        results_reference = case.get("results_reference")
        if not isinstance(results_reference, dict):
            return None

        baseline = str(source.get("baseline", "")).strip()
        candidates: list[str] = []
        if baseline:
            candidates.append(baseline)
            version_match = re.search(r"\bv\d+(?:\.\d+)+\b", baseline, re.IGNORECASE)
            if version_match:
                candidates.append(version_match.group(0))
            numeric_match = re.search(r"\b\d+(?:\.\d+)+\b", baseline)
            if numeric_match:
                candidates.append(f"v{numeric_match.group(0)}")

        seen: set[str] = set()
        for candidate in candidates:
            normalized = candidate.strip()
            if not normalized or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            value = results_reference.get(normalized)
            if isinstance(value, dict):
                return value
            for key, entry in results_reference.items():
                if isinstance(key, str) and key.strip().lower() == normalized.lower() and isinstance(entry, dict):
                    return entry
        return None

    @classmethod
    def _case_band_results(cls, case: dict[str, Any], verdict: bool) -> tuple[str, str, str]:
        default_status = "Pass" if verdict else "Fail"
        result_5g, result_6g, result_24g = cls._band_results(default_status, case.get("bands"))
        reference = cls._baseline_results_reference(case)
        if not reference:
            return result_5g, result_6g, result_24g

        by_band = {
            "5g": result_5g,
            "6g": result_6g,
            "2.4g": result_24g,
        }
        for band in ("5g", "6g", "2.4g"):
            value = reference.get(band)
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if not normalized:
                continue
            if verdict:
                by_band[band] = normalized
            elif normalized in {"Skip", "N/A"}:
                by_band[band] = normalized

        return by_band["5g"], by_band["6g"], by_band["2.4g"]

    @staticmethod
    def _overall_case_status(result_5g: str, result_6g: str, result_24g: str) -> str:
        return "Fail" if "Fail" in {result_5g, result_6g, result_24g} else "Pass"

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _sanitize_case_id(case_id: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", case_id.strip())
        return normalized or "case"

    @staticmethod
    def _case_aliases(case: dict[str, Any]) -> list[str]:
        raw_aliases = case.get("aliases")
        if not isinstance(raw_aliases, list):
            return []
        aliases: list[str] = []
        for item in raw_aliases:
            alias = str(item).strip()
            if alias:
                aliases.append(alias)
        return aliases

    @classmethod
    def _case_matches_requested_ids(
        cls,
        case: dict[str, Any],
        requested_ids: set[str],
    ) -> bool:
        if not requested_ids:
            return False
        case_ids = {str(case.get("id", "")).strip(), *cls._case_aliases(case)}
        case_ids.discard("")
        return bool(case_ids & requested_ids)

    @staticmethod
    def _is_wifi_llapi_official_case(case: dict[str, Any]) -> bool:
        return re.match(r"^(?:wifi-llapi-)?[Dd]\d+", str(case.get("id", "")).strip()) is not None

    def _load_wifi_llapi_agent_config(self, plugin_name: str) -> dict[str, Any]:
        path = self.plugins_dir / plugin_name / "agent-config.yaml"
        if not path.exists():
            return {}
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive config parse
            log.warning("failed to load agent-config for %s: %s", plugin_name, exc)
            return {}
        return content if isinstance(content, dict) else {}

    def _wifi_llapi_execution_policy(self, agent_config: dict[str, Any]) -> dict[str, Any]:
        execution = agent_config.get("execution")
        if not isinstance(execution, dict):
            execution = {}

        retry = execution.get("retry")
        if not isinstance(retry, dict):
            retry = {}

        timeout = execution.get("timeout")
        if not isinstance(timeout, dict):
            timeout = {}

        defaults = DEFAULT_WIFI_LLAPI_EXECUTION_POLICY
        policy = {
            "scope": str(execution.get("scope", defaults["scope"])),
            "mode": str(execution.get("mode", defaults["mode"])),
            "max_concurrency": max(1, self._safe_int(execution.get("max_concurrency"), 1)),
            "failure_policy": str(execution.get("failure_policy", defaults["failure_policy"])),
            "retry": {
                "max_attempts": max(1, self._safe_int(retry.get("max_attempts"), 2)),
                "backoff_seconds": max(0.0, self._safe_float(retry.get("backoff_seconds"), 5.0)),
            },
            "timeout": {
                "base_seconds": max(1.0, self._safe_float(timeout.get("base_seconds"), 120.0)),
                "per_step_seconds": max(0.0, self._safe_float(timeout.get("per_step_seconds"), 45.0)),
                "retry_multiplier": max(
                    1.0, self._safe_float(timeout.get("retry_multiplier"), 1.25)
                ),
                "max_seconds": max(1.0, self._safe_float(timeout.get("max_seconds"), 900.0)),
            },
        }

        # wifi_llapi current dispatcher only supports sequential single worker.
        if policy["mode"] != "sequential":
            log.warning("wifi_llapi execution.mode=%s is not supported, force to sequential", policy["mode"])
            policy["mode"] = "sequential"
        if policy["max_concurrency"] != 1:
            log.warning(
                "wifi_llapi max_concurrency=%s is not supported, force to 1",
                policy["max_concurrency"],
            )
            policy["max_concurrency"] = 1

        return policy

    def _enabled_runners(self, agent_config: dict[str, Any]) -> list[dict[str, Any]]:
        runners_raw = agent_config.get("runners")
        if not isinstance(runners_raw, list):
            return []

        runners: list[dict[str, Any]] = []
        for idx, item in enumerate(runners_raw, start=1):
            if not isinstance(item, dict):
                continue
            if item.get("enabled", True) is False:
                continue
            runner = dict(item)
            runner.setdefault("priority", idx)
            runners.append(runner)

        runners.sort(key=lambda r: self._safe_int(r.get("priority"), 9999))
        return runners

    def _runner_availability_overrides(self, plugin_name: str) -> dict[str, str | bool]:
        """Optional availability overrides from env for deterministic fallback simulation.

        Env var format:
        - flat map: {"codex": true, "copilot": "binary_not_found"}
        - plugin map: {"wifi_llapi": {"codex": false, "copilot": true}}
        """
        raw = os.environ.get("TESTPILOT_AGENT_AVAILABILITY", "").strip()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except Exception:
            log.warning("invalid TESTPILOT_AGENT_AVAILABILITY, ignore override")
            return {}
        if not isinstance(payload, dict):
            return {}

        scoped = payload.get(plugin_name, payload)
        if not isinstance(scoped, dict):
            return {}

        out: dict[str, str | bool] = {}
        for key, value in scoped.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if isinstance(value, bool):
                out[key.strip()] = value
                continue
            if value is None:
                out[key.strip()] = False
                continue
            out[key.strip()] = str(value)
        return out

    @staticmethod
    def _runner_summary(runner: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(runner, dict):
            runner = {
                "priority": getattr(runner, "priority", 0),
                "cli_agent": getattr(runner, "cli_agent", ""),
                "model": getattr(runner, "model", ""),
                "effort": getattr(runner, "effort", ""),
                "enabled": getattr(runner, "enabled", True),
            }
        return {
            "priority": runner.get("priority"),
            "cli_agent": runner.get("cli_agent"),
            "model": runner.get("model"),
            "effort": runner.get("effort"),
            "enabled": runner.get("enabled", True),
        }

    def _match_runner_by_selector(
        self, selector: Any, runners: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        if hasattr(selector, "runner"):
            return self._match_runner_by_selector(getattr(selector, "runner"), runners)
        if (
            hasattr(selector, "cli_agent")
            and hasattr(selector, "model")
            and not isinstance(selector, dict)
        ):
            selector = {
                "priority": getattr(selector, "priority", None),
                "cli_agent": getattr(selector, "cli_agent", ""),
                "model": getattr(selector, "model", ""),
                "effort": getattr(selector, "effort", "high"),
                "enabled": getattr(selector, "enabled", True),
            }
        if isinstance(selector, dict):
            if "cli_agent" in selector and "model" in selector:
                for runner in runners:
                    if str(runner.get("cli_agent")) == str(selector.get("cli_agent")) and str(
                        runner.get("model")
                    ) == str(selector.get("model")):
                        return runner
                return {
                    "priority": selector.get("priority", 0),
                    "cli_agent": selector.get("cli_agent"),
                    "model": selector.get("model"),
                    "effort": selector.get("effort", "high"),
                    "enabled": True,
                }

            for runner in runners:
                if "priority" in selector and self._safe_int(
                    runner.get("priority"), -1
                ) != self._safe_int(selector.get("priority"), -2):
                    continue
                if "cli_agent" in selector and str(runner.get("cli_agent")) != str(
                    selector.get("cli_agent")
                ):
                    continue
                if "model" in selector and str(runner.get("model")) != str(selector.get("model")):
                    continue
                return runner
            return None

        if isinstance(selector, str):
            lowered = selector.strip().lower()
            for runner in runners:
                if str(runner.get("cli_agent", "")).lower() == lowered:
                    return runner
                if str(runner.get("model", "")).lower() == lowered:
                    return runner
            return None

        if isinstance(selector, (int, float)):
            wanted = int(selector)
            for runner in runners:
                if self._safe_int(runner.get("priority"), -1) == wanted:
                    return runner
            return None

        return None

    def _normalize_runtime_selection(
        self, selection: Any, runners: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        if selection is None:
            return None
        if isinstance(selection, dict):
            for key in ("selected_runner", "runner", "selected", "selection"):
                if key in selection:
                    matched = self._match_runner_by_selector(selection.get(key), runners)
                    if matched is not None:
                        return matched
            matched = self._match_runner_by_selector(selection, runners)
            if matched is not None:
                return matched
        return self._match_runner_by_selector(selection, runners)

    def _select_runner_via_agent_runtime(
        self,
        plugin_name: str,
        case: dict[str, Any],
        agent_config: dict[str, Any],
        runners: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        trace: dict[str, Any] = {
            "module_available": agent_runtime_module is not None,
            "method": None,
            "reason": "",
        }
        if agent_runtime_module is None:
            trace["reason"] = "agent_runtime module unavailable"
            return None, trace

        parse_fn = getattr(agent_runtime_module, "parse_agent_runtime_config", None)
        select_fn = getattr(agent_runtime_module, "select_runner", None)
        if callable(parse_fn) and callable(select_fn):
            try:
                runtime_config = parse_fn(agent_config)
                availability = self._runner_availability_overrides(plugin_name)
                selection = select_fn(runtime_config, availability=availability)
                trace["method"] = "module.select_runner"
                trace["availability"] = availability

                selection_items: list[dict[str, Any]] = []
                for item in getattr(selection, "trace", []):
                    selection_items.append(
                        {
                            "priority": getattr(item, "priority", 0),
                            "cli_agent": getattr(item, "cli_agent", ""),
                            "model": getattr(item, "model", ""),
                            "status": getattr(item, "status", ""),
                            "unavailable_reason": getattr(item, "unavailable_reason", None),
                        }
                    )
                trace["selection"] = selection_items

                matched = self._normalize_runtime_selection(selection, runners)
                if matched is not None:
                    return matched, trace
                trace["reason"] = "module.select_runner returned no valid runner"
            except Exception as exc:
                trace["reason"] = f"module.select_runner failed: {exc}"

        case_id = str(case.get("id", "?"))
        call_targets: list[tuple[str, Any]] = []
        for fn_name in ("select_runner_for_case", "select_runner"):
            fn = getattr(agent_runtime_module, fn_name, None)
            if callable(fn):
                call_targets.append((f"module.{fn_name}", fn))

        runtime_cls = getattr(agent_runtime_module, "AgentRuntime", None)
        if callable(runtime_cls):
            runtime_obj = None
            for init_kwargs in (
                {"plugin_name": plugin_name, "agent_config": agent_config},
                {"plugin": plugin_name, "config": agent_config},
                {},
            ):
                try:
                    runtime_obj = runtime_cls(**init_kwargs)
                    break
                except TypeError:
                    continue
                except Exception as exc:  # pragma: no cover - defensive runtime init
                    trace["reason"] = f"AgentRuntime init failed: {exc}"
                    break
            if runtime_obj is not None:
                for method_name in ("select_runner_for_case", "select_runner"):
                    fn = getattr(runtime_obj, method_name, None)
                    if callable(fn):
                        call_targets.append((f"AgentRuntime.{method_name}", fn))

        if not call_targets:
            trace["reason"] = "no callable selector in agent_runtime"
            return None, trace

        for method_name, selector in call_targets:
            for kwargs in (
                {"plugin_name": plugin_name, "case": case, "agent_config": agent_config},
                {"plugin_name": plugin_name, "case_id": case_id, "agent_config": agent_config},
                {"plugin": plugin_name, "case": case, "config": agent_config},
                {"case": case, "agent_config": agent_config},
                {"case_id": case_id, "agent_config": agent_config},
            ):
                try:
                    selection = selector(**kwargs)
                except TypeError:
                    continue
                except Exception as exc:  # pragma: no cover - defensive runtime call
                    trace["reason"] = f"{method_name} failed: {exc}"
                    break

                matched = self._normalize_runtime_selection(selection, runners)
                if matched is not None:
                    trace["method"] = method_name
                    return matched, trace

            try:
                selection = selector(plugin_name, case, agent_config)
            except Exception:
                continue
            matched = self._normalize_runtime_selection(selection, runners)
            if matched is not None:
                trace["method"] = method_name
                return matched, trace

        trace["reason"] = trace["reason"] or "selector returned no valid runner"
        return None, trace

    def _select_case_runner(
        self,
        plugin_name: str,
        case: dict[str, Any],
        agent_config: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        runners = self._enabled_runners(agent_config)
        selection_trace: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "case_id": str(case.get("id", "?")),
            "candidates": [self._runner_summary(r) for r in runners],
            "fallback": {
                "applied": False,
                "reason": "",
            },
        }

        selected_runner: dict[str, Any] | None = None
        runtime_trace: dict[str, Any] = {
            "module_available": False,
            "method": None,
            "reason": "skip: no enabled runners",
        }
        if runners:
            selected_runner, runtime_trace = self._select_runner_via_agent_runtime(
                plugin_name=plugin_name,
                case=case,
                agent_config=agent_config,
                runners=runners,
            )

        selection_trace["runtime"] = runtime_trace
        runtime_selection = runtime_trace.get("selection", [])
        if isinstance(runtime_selection, list):
            for item in runtime_selection:
                if not isinstance(item, dict):
                    continue
                if str(item.get("status", "")).lower() != "unavailable":
                    continue
                reason = str(item.get("unavailable_reason") or "next_priority")
                selection_trace["fallback"] = {
                    "applied": True,
                    "reason": f"next_priority due unavailable: {reason}",
                }
                break

        if selected_runner is None and runners:
            selected_runner = runners[0]
            selection_trace["fallback"] = {
                "applied": True,
                "reason": runtime_trace.get("reason") or "fallback to first enabled runner",
            }

        if selected_runner is None:
            selected_runner = {
                "priority": 0,
                "cli_agent": "plugin-native",
                "model": "plugin-hooks",
                "effort": "high",
                "enabled": True,
            }
            selection_trace["fallback"] = {
                "applied": True,
                "reason": "no enabled runner configured",
            }

        selection_trace["selected"] = self._runner_summary(selected_runner)
        return selected_runner, selection_trace

    def _attempt_timeout_seconds(
        self,
        *,
        steps_count: int,
        attempt_index: int,
        execution_policy: dict[str, Any],
    ) -> float:
        timeout = execution_policy.get("timeout", {})
        if not isinstance(timeout, dict):
            timeout = {}
        base_seconds = max(1.0, self._safe_float(timeout.get("base_seconds"), 120.0))
        per_step_seconds = max(0.0, self._safe_float(timeout.get("per_step_seconds"), 45.0))
        retry_multiplier = max(1.0, self._safe_float(timeout.get("retry_multiplier"), 1.25))
        max_seconds = max(1.0, self._safe_float(timeout.get("max_seconds"), 900.0))

        raw_timeout = (base_seconds + max(0, steps_count) * per_step_seconds) * (
            retry_multiplier ** max(0, attempt_index - 1)
        )
        return min(max_seconds, raw_timeout)

    def _execute_wifi_llapi_case_once(
        self,
        plugin: Any,
        case: dict[str, Any],
        *,
        attempt_index: int,
        attempt_timeout_seconds: float,
        runner: dict[str, Any],
    ) -> dict[str, Any]:
        commands: list[str] = []
        outputs: list[str] = []
        verdict = False
        comment = ""

        runtime_case = dict(case)
        runtime_case["_agent_runner"] = self._runner_summary(runner)
        runtime_case["_attempt_index"] = attempt_index
        runtime_case["_attempt_timeout_seconds"] = attempt_timeout_seconds

        try:
            setup_ok = bool(plugin.setup_env(runtime_case, topology=self.config))
            if not setup_ok:
                comment = "setup_env failed"
            env_ok = setup_ok and bool(plugin.verify_env(runtime_case, topology=self.config))
            if setup_ok and not env_ok:
                comment = "env_verify gate failed"

            step_results: dict[str, Any] = {}
            raw_steps = runtime_case.get("steps", [])
            steps = raw_steps if isinstance(raw_steps, list) else []
            if env_ok:
                for step in steps:
                    step_data = dict(step) if isinstance(step, dict) else {"id": "step", "command": str(step)}
                    step_id = str(step_data.get("id", "step"))
                    command = str(step_data.get("command", "")).strip()
                    if command:
                        commands.append(command)

                    step_payload = dict(step_data)
                    step_payload.setdefault("timeout", attempt_timeout_seconds)
                    step_payload["_attempt_index"] = attempt_index
                    step_payload["_attempt_timeout_seconds"] = attempt_timeout_seconds

                    result = plugin.execute_step(runtime_case, step_payload, topology=self.config)
                    step_results[step_id] = result
                    out = str(result.get("output", "")).strip()
                    if out:
                        outputs.append(out)
                    if not bool(result.get("success", False)):
                        comment = f"step failed: {step_id}"
                        break

                if not comment:
                    verdict = bool(plugin.evaluate(runtime_case, {"steps": step_results}))
                    if not verdict:
                        comment = "pass_criteria not satisfied"

        except Exception as exc:  # pragma: no cover - defensive catch for runtime errors
            comment = f"exception: {exc}"
        finally:
            try:
                plugin.teardown(runtime_case, topology=self.config)
            except Exception:
                log.exception("teardown failed: %s", runtime_case.get("id", "?"))

        return {
            "verdict": verdict,
            "comment": comment,
            "commands": commands,
            "outputs": outputs,
        }

    @staticmethod
    def _write_case_trace(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _run_wifi_llapi(
        self,
        plugin_name: str,
        case_ids: list[str] | None,
        dut_fw_ver: str | None,
        report_source_xlsx: str | None,
    ) -> dict[str, Any]:
        plugin = self.loader.load(plugin_name)
        discovered_cases = plugin.discover_cases()
        if case_ids:
            requested_ids = {str(case_id).strip() for case_id in case_ids if str(case_id).strip()}
            cases = [
                c for c in discovered_cases if self._case_matches_requested_ids(c, requested_ids)
            ]
        else:
            # Default to official D{row} row-indexed cases.
            cases = [
                c
                for c in discovered_cases
                if self._is_wifi_llapi_official_case(c)
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
            default_source = Path(DEFAULT_WIFI_LLAPI_SOURCE_XLSX)
            if not default_source.exists():
                raise FileNotFoundError(
                    "wifi_llapi template not found. Run "
                    "`python -m testpilot.cli wifi-llapi build-template-report --source-xlsx <path>` "
                    "or pass `--report-source-xlsx <path>` to rebuild it."
                )
            ensure_template_report(
                source_xlsx=default_source,
                template_path=template_path,
                manifest_path=manifest_path,
            )
            alignment_xlsx = default_source
            source_report = str(default_source)

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

        agent_config = self._load_wifi_llapi_agent_config(plugin_name)
        execution_policy = self._wifi_llapi_execution_policy(agent_config)
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

        for case in cases:
            case_id = str(case.get("id", "?"))
            source = case.get("source", {}) if isinstance(case.get("source"), dict) else {}
            try:
                source_row = int(source.get("row", 0))
            except (TypeError, ValueError):
                source_row = 0

            raw_steps = case.get("steps", [])
            steps_count = len(raw_steps) if isinstance(raw_steps, list) else 0

            selected_runner, selection_trace = self._select_case_runner(
                plugin_name=plugin_name,
                case=case,
                agent_config=agent_config,
            )
            if callable(build_case_session_plan):
                session_plan = build_case_session_plan(run_id, case_id, selected_runner)
                if session_plan is not None:
                    selection_trace["session_plan"] = session_plan

            max_attempts = self._safe_int(
                execution_policy.get("retry", {}).get("max_attempts"), 1
            )
            failure_policy = str(execution_policy.get("failure_policy", "retry_then_fail_and_continue"))

            attempts_trace: list[dict[str, Any]] = []
            commands: list[str] = []
            outputs: list[str] = []
            verdict = False
            comment = ""

            for attempt_index in range(1, max_attempts + 1):
                attempt_timeout = self._attempt_timeout_seconds(
                    steps_count=steps_count,
                    attempt_index=attempt_index,
                    execution_policy=execution_policy,
                )
                attempt_result = self._execute_wifi_llapi_case_once(
                    plugin=plugin,
                    case=case,
                    attempt_index=attempt_index,
                    attempt_timeout_seconds=attempt_timeout,
                    runner=selected_runner,
                )
                commands = [str(x) for x in attempt_result.get("commands", [])]
                outputs = [str(x) for x in attempt_result.get("outputs", [])]
                verdict = bool(attempt_result.get("verdict", False))
                comment = str(attempt_result.get("comment", ""))
                attempt_result_5g, attempt_result_6g, attempt_result_24g = self._case_band_results(
                    case, verdict
                )
                attempt_status = self._overall_case_status(
                    attempt_result_5g, attempt_result_6g, attempt_result_24g
                )

                attempts_trace.append(
                    {
                        "attempt": attempt_index,
                        "timeout_seconds": attempt_timeout,
                        "runner": self._runner_summary(selected_runner),
                        "status": attempt_status,
                        "evaluation_verdict": "Pass" if verdict else "Fail",
                        "comment": comment,
                        "commands": commands,
                        "outputs": outputs,
                    }
                )

                if verdict:
                    break
                should_retry = (
                    failure_policy == "retry_then_fail_and_continue" and attempt_index < max_attempts
                )
                if not should_retry:
                    break

            attempts_used = len(attempts_trace)
            if verdict and attempts_used > 1 and not comment:
                comment = f"pass after retry ({attempts_used}/{max_attempts})"
            if not verdict and attempts_used > 1:
                if comment:
                    comment = f"{comment} (failed after {attempts_used}/{max_attempts} attempts)"
                else:
                    comment = f"failed after {attempts_used}/{max_attempts} attempts"

            result_5g, result_6g, result_24g = self._case_band_results(case, verdict)
            status = self._overall_case_status(result_5g, result_6g, result_24g)
            case_trace_path = (
                agent_trace_dir / f"{self._sanitize_case_id(case_id)}.json"
            )
            self._write_case_trace(
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
                        "attempts_used": attempts_used,
                        "comment": comment,
                    },
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
                )
            )

        fill_case_results(report_xlsx=report_path, case_results=case_results)
        finalize_report_metadata(
            report_xlsx=report_path,
            meta=ReportMeta(
                run_date=run_date,
                dut_fw_ver=fw_ver,
                source_excel=source_report,
            ),
        )

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
            "source_report": source_report,
            "run_id": run_id,
            "agent_trace_dir": str(agent_trace_dir),
            "agent_trace_count": len(case_trace_files),
        }

    def run(
        self,
        plugin_name: str,
        case_ids: list[str] | None = None,
        *,
        dut_fw_ver: str | None = None,
        report_source_xlsx: str | None = None,
    ) -> dict[str, Any]:
        """執行測試。（Phase 3 完整實作）

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
            )

        plugin = self.loader.load(plugin_name)
        cases = plugin.discover_cases()
        if case_ids:
            requested_ids = {str(case_id).strip() for case_id in case_ids if str(case_id).strip()}
            cases = [c for c in cases if self._case_matches_requested_ids(c, requested_ids)]

        log.info("would run %d cases from plugin '%s'", len(cases), plugin_name)
        return {
            "plugin": plugin_name,
            "plugin_version": plugin.version,
            "cases_count": len(cases),
            "case_ids": [c.get("id", "?") for c in cases],
            "status": "skeleton — not yet implemented",
        }
