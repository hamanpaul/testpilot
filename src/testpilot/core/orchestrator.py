"""Orchestrator — central coordinator for plugin loading, test scheduling, and monitoring."""

from __future__ import annotations

from datetime import date
import json
import logging
from pathlib import Path
import re
from typing import Any

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
            cases = [c for c in discovered_cases if c.get("id") in case_ids]
        else:
            # Default to official row-indexed cases.
            cases = [
                c
                for c in discovered_cases
                if re.match(r"^wifi-llapi-r\d+", str(c.get("id", "")))
            ]

        reports_root = self.plugins_dir / plugin_name / "reports"
        template_path = reports_root / "templates" / "wifi_llapi_template.xlsx"
        manifest_path = reports_root / "templates" / "wifi_llapi_template.manifest.json"
        source_xlsx = Path(report_source_xlsx) if report_source_xlsx else Path(DEFAULT_WIFI_LLAPI_SOURCE_XLSX)

        if not source_xlsx.exists():
            raise FileNotFoundError(
                f"wifi_llapi source report not found: {source_xlsx}"
            )

        template_result = ensure_template_report(
            source_xlsx=source_xlsx,
            template_path=template_path,
            manifest_path=manifest_path,
        )

        alignment_issues = collect_alignment_issues(cases, source_xlsx)
        if alignment_issues:
            alignment_dir = reports_root / "alignment"
            alignment_dir.mkdir(parents=True, exist_ok=True)
            alignment_path = alignment_dir / f"{date.today():%Y%m%d}_wifi_llapi_alignment_issues.json"
            alignment_path.write_text(
                json.dumps(
                    {
                        "source_report": str(source_xlsx),
                        "issues_count": len(alignment_issues),
                        "issues": alignment_issues,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return {
                "plugin": plugin_name,
                "plugin_version": plugin.version,
                "cases_count": len(cases),
                "status": "alignment_failed",
                "message": "case source.row/object/api mismatch with source Excel sheet",
                "alignment_report": str(alignment_path),
                "issues_count": len(alignment_issues),
            }

        run_date = date.today()
        fw_ver = dut_fw_ver or "DUT-FW-VER"
        report_name = generate_report_filename(run_date, fw_ver)
        report_path = reports_root / report_name
        create_run_report_from_template(template_xlsx=template_path, out_report_xlsx=report_path)

        case_results: list[WifiLlapiCaseResult] = []
        pass_count = 0
        fail_count = 0

        for case in cases:
            case_id = str(case.get("id", "?"))
            source = case.get("source", {}) if isinstance(case.get("source"), dict) else {}
            try:
                source_row = int(source.get("row", 0))
            except (TypeError, ValueError):
                source_row = 0

            commands: list[str] = []
            outputs: list[str] = []
            verdict = False
            comment = ""

            try:
                setup_ok = bool(plugin.setup_env(case, topology=self.config))
                if not setup_ok:
                    comment = "setup_env failed"
                env_ok = setup_ok and bool(plugin.verify_env(case, topology=self.config))
                if setup_ok and not env_ok:
                    comment = "env_verify gate failed"

                step_results: dict[str, Any] = {}
                if env_ok:
                    for step in case.get("steps", []):
                        step_id = str(step.get("id", "step"))
                        command = str(step.get("command", "")).strip()
                        if command:
                            commands.append(command)
                        result = plugin.execute_step(case, step, topology=self.config)
                        step_results[step_id] = result
                        out = str(result.get("output", "")).strip()
                        if out:
                            outputs.append(out)
                        if not bool(result.get("success", False)):
                            comment = f"step failed: {step_id}"
                            break

                    if not comment:
                        verdict = bool(plugin.evaluate(case, {"steps": step_results}))
                        if not verdict:
                            comment = "pass_criteria not satisfied"

            except Exception as exc:  # pragma: no cover - defensive catch for runtime errors
                comment = f"exception: {exc}"
            finally:
                try:
                    plugin.teardown(case, topology=self.config)
                except Exception:
                    log.exception("teardown failed: %s", case_id)

            status = "Pass" if verdict else "Fail"
            if verdict:
                pass_count += 1
            else:
                fail_count += 1

            result_5g, result_6g, result_24g = self._band_results(status, case.get("bands"))
            case_results.append(
                WifiLlapiCaseResult(
                    case_id=case_id,
                    source_row=source_row,
                    executed_test_command="\n\n".join(commands).strip(),
                    command_output="\n\n".join(outputs).strip(),
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
                source_excel=str(source_xlsx),
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
            "template_path": str(template_result.template_path),
            "report_path": str(report_path),
            "source_report": str(source_xlsx),
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
            cases = [c for c in cases if c.get("id") in case_ids]

        log.info("would run %d cases from plugin '%s'", len(cases), plugin_name)
        return {
            "plugin": plugin_name,
            "plugin_version": plugin.version,
            "cases_count": len(cases),
            "case_ids": [c.get("id", "?") for c in cases],
            "status": "skeleton — not yet implemented",
        }
