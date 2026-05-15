"""Offline reproject orchestration for wifi_llapi reports.

Reads an existing JSON result bundle and a checked-in Excel template, fills the
Wifi_LLAPI sheet while preserving the template-owned Summary sheet, and emits
Markdown / JSON / HTML companion reports – all into an isolated output
directory.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from testpilot.reporting.wifi_llapi_excel import (
    ReportMeta,
    WifiLlapiCaseResult,
    create_run_report_from_template,
    fill_case_results,
    finalize_report_metadata,
    read_wifi_llapi_template_objects,
    validate_wifi_llapi_report_template,
)
from testpilot.reporting.wifi_llapi_summary import (
    SUMMARY_POLICY_VERSION,
    build_wifi_llapi_summary,
    extract_fail_reason,
)
from testpilot.reporting.reporter import generate_reports


def reproject_wifi_llapi_report(
    source_json: Path | str,
    template_xlsx: Path | str,
    out_dir: Path | str | None = None,
    output_stem: str = "reproject-report",
) -> dict[str, Any]:
    """Reproject a wifi_llapi JSON bundle against a template workbook.

    Parameters
    ----------
    source_json:
        Path to the existing JSON result bundle (read-only; never modified).
    template_xlsx:
        Path to the checked-in Excel template.
    out_dir:
        Target output directory.  Must not exist or must be empty.  When
        *None*, defaults to ``template_path.resolve().parent.parent /
        '<source_stem>_summary_reproject_<ts>'`` (sibling of the template's
        parent directory, typically ``plugins/wifi_llapi/reports/``).
    output_stem:
        Filename stem used for the XLSX and companion reports.

    Returns
    -------
    dict with keys: status, artifact_dir, report_path, md_report_path,
    html_report_path, json_report_path, summary.
    """
    source_path = Path(source_json)
    template_path = Path(template_xlsx)

    # Load JSON read-only
    source_text = source_path.read_text(encoding="utf-8")
    source_data = json.loads(source_text)
    if not isinstance(source_data, dict):
        raise TypeError(
            f"Expected a JSON object (dict) as source_json root, "
            f"got {type(source_data).__name__!r}. "
            f"Ensure {source_path} contains a JSON object, not an array or scalar."
        )

    # Validate template structure
    validate_wifi_llapi_report_template(template_path)

    # Read object-prefix mapping from template
    row_objects = read_wifi_llapi_template_objects(template_path)

    cases: list[dict[str, Any]] = source_data.get("cases", [])

    # Build shared summary payload
    summary = build_wifi_llapi_summary(cases, row_objects)

    # Resolve output directory anchored to template_path.parent.parent
    if out_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        artifact_dir = (
            template_path.resolve().parent.parent
            / f"{source_path.stem}_summary_reproject_{ts}"
        )
    else:
        artifact_dir = Path(out_dir)

    if artifact_dir.exists() and any(artifact_dir.iterdir()):
        raise FileExistsError(
            f"Output directory is non-empty: {artifact_dir}"
        )
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Copy template to a fresh XLSX in the output directory
    report_path = artifact_dir / f"{output_stem}.xlsx"
    actual_report_path = create_run_report_from_template(template_path, report_path)

    # Build typed case-result objects for Excel fill
    case_results_typed: list[WifiLlapiCaseResult] = []
    for case in cases:
        cr = WifiLlapiCaseResult(
            case_id=str(case.get("case_id", "")),
            source_row=int(case.get("source_row") or 0),
            executed_test_command=str(case.get("executed_test_command", "")),
            command_output=str(case.get("command_output", "")),
            result_5g=str(case.get("result_5g", "")),
            result_6g=str(case.get("result_6g", "")),
            result_24g=str(case.get("result_24g", "")),
            comment=extract_fail_reason(case),
            tester=str(case.get("tester", "testpilot")),
            diagnostic_status=str(case.get("diagnostic_status", "")),
            failure_snapshot=(
                case.get("failure_snapshot")
                if isinstance(case.get("failure_snapshot"), dict)
                else None
            ),
        )
        case_results_typed.append(cr)

    # Fill result columns in XLSX. Summary stays template-owned so existing
    # formulas, styles, merged ranges, and percent formats are preserved.
    fill_case_results(actual_report_path, case_results_typed)

    # Store run metadata in hidden _meta sheet
    source_meta: dict[str, Any] = source_data.get("meta", {})
    report_meta_obj = ReportMeta(
        run_date=date.today(),
        dut_fw_ver=str(source_meta.get("firmware_version", "unknown")),
        source_excel=str(actual_report_path),
    )
    finalize_report_metadata(actual_report_path, report_meta_obj)

    # Build meta dict for text-format report generators
    reprojected_at = datetime.now(timezone.utc).isoformat()
    report_meta: dict[str, Any] = {
        **source_meta,
        "source_json": str(source_path),
        "template_path": str(template_path),
        "reprojected_at": reprojected_at,
        "summary_policy_version": SUMMARY_POLICY_VERSION,
        "wifi_llapi_summary": summary,
        "output_stem": output_stem,
    }

    # Generate MD / JSON / HTML reports (these use the shared summary)
    report_paths = generate_reports(
        case_results=cases,
        meta=report_meta,
        output_dir=artifact_dir,
        formats=("md", "json", "html"),
    )

    paths_by_ext: dict[str, Path] = {
        p.suffix.lstrip("."): p for p in report_paths
    }

    return {
        "status": "ok",
        "artifact_dir": artifact_dir,
        "report_path": actual_report_path,
        "md_report_path": paths_by_ext.get("md"),
        "html_report_path": paths_by_ext.get("html"),
        "json_report_path": paths_by_ext.get("json"),
        "summary": summary,
    }
