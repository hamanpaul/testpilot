"""wifi_llapi Excel report helpers.

This module keeps report layout compatible with the reference
`Wifi_LLAPI` worksheet and supports:
1) building a template report from source workbook,
2) creating dated run reports from template,
3) filling test command and result columns by case source row.
"""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from datetime import date
import json
import os
from pathlib import Path
import re
import shutil
from typing import Iterable

from testpilot.reporting.excel_adapter import (
    col_to_index as column_index_from_string,
    is_merged_cell,
    open_workbook as load_workbook,
)

DEFAULT_SHEET_NAME = "Wifi_LLAPI"
DEFAULT_TEMPLATE_NAME = "wifi_llapi_template.xlsx"
DEFAULT_TEMPLATE_MAX_COLUMN = "M"
RESULT_GROUP_HEADER = "Result"
RESULT_HEADERS_BY_COLUMN = {
    "I": "WiFi 5G",
    "J": "WiFi 6G",
    "K": "WiFi 2.4G",
}
TESTER_HEADER = "Tester"
COMMENT_HEADER = "Comment"
SUMMARY_BUCKET_HEADERS = {
    "N": "Summary Bucket WiFi 5G",
    "O": "Summary Bucket WiFi 6G",
    "P": "Summary Bucket WiFi 2.4G",
}
SUMMARY_BUCKET_COLUMNS = (
    ("result_5g", "N"),
    ("result_6g", "O"),
    ("result_24g", "P"),
)
SUMMARY_SHEET_NAME = "Summary"
SUMMARY_HEADERS: tuple[str, ...] = (
    "Module",
    "Object Category",
    "Total Items",
    "Tested Items",
    "Pass",
    "Fail",
    "To be tested",
    "Not Supported",
    "Skip",
    "Pass Rate",
    "result empty",
    "Progress",
)
DEFAULT_CLEAR_COLUMNS = (
    "G",   # Test steps
    "H",   # Driver-level verified command output
    "I",   # ARC 5g result
    "J",   # ARC 6g result
    "K",   # ARC 2.4g result
    "L",   # ARC tester
    "M",   # Reporter comment
)
DATA_START_ROW = 4
EMPTY_STREAK_STOP = 200
MAX_SCAN_ROWS = 5000
_PROMPT_PREFIX_RE = re.compile(r"^(?:root@[^:]+:[^#\n]*#\s*|[>$#]\s*)")


class TemplateValidationError(ValueError):
    """Raised when an Excel template does not match the expected layout."""


@dataclass(slots=True)
class ClearRules:
    """Template clear behavior for wifi_llapi sheet."""

    clear_columns: tuple[str, ...] = DEFAULT_CLEAR_COLUMNS
    data_start_row: int = DATA_START_ROW
    empty_streak_stop: int = EMPTY_STREAK_STOP
    max_scan_rows: int = MAX_SCAN_ROWS


@dataclass(slots=True)
class TemplateBuildResult:
    template_path: Path
    sheet_name: str
    total_case_rows: int
    cleared_columns: tuple[str, ...]
    source_workbook: Path
    source_sheet: str


@dataclass(slots=True)
class ReportMeta:
    run_date: date
    dut_fw_ver: str
    source_excel: str
    sheet_name: str = DEFAULT_SHEET_NAME


@dataclass(slots=True)
class WifiLlapiCaseResult:
    case_id: str
    source_row: int
    executed_test_command: str
    command_output: str
    result_5g: str
    result_6g: str
    result_24g: str
    comment: str = ""
    tester: str = "testpilot"
    dut_log_lines: str = ""
    sta_log_lines: str = ""
    diagnostic_status: str = ""
    remediation_history: list[dict[str, object]] = field(default_factory=list)
    failure_snapshot: dict[str, object] | None = None
    case_started_at: str = ""
    case_finished_at: str = ""
    case_duration_seconds: float = 0.0
    overall_status: str = ""


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", str(text))
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def sanitize_fw_version(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip())
    cleaned = cleaned.strip("-._")
    return cleaned or "DUT-FW-VER"


def sanitize_filename_suffix(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip())
    return cleaned.strip("-._")


def generate_report_filename(
    run_date: date,
    dut_fw_ver: str,
    *,
    unique_suffix: str | None = None,
) -> str:
    """Generate user-required report filename format.

    Format: YYYYMMDD_<DUT-FW-VER>_wifi_LLAPI.xlsx
    """
    base = f"{run_date:%Y%m%d}_{sanitize_fw_version(dut_fw_ver)}_wifi_LLAPI"
    suffix = sanitize_filename_suffix(unique_suffix or "")
    if suffix:
        return f"{base}_{suffix}.xlsx"
    return f"{base}.xlsx"


def sanitize_report_output(text: str | None) -> str:
    if text is None:
        return ""

    lines: list[str] = []
    for raw in str(text).splitlines():
        line = _PROMPT_PREFIX_RE.sub("", raw).strip()
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_command_block(text: str | None) -> str:
    if text is None:
        return ""
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    return "\n".join(lines).strip()


def _resolve_report_copy_path(dst: Path) -> Path:
    if not dst.exists():
        return dst

    counter = 1
    while True:
        candidate = dst.with_name(f"{dst.stem}_{counter:02d}{dst.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _get_sheet(wb, preferred_name: str):
    if preferred_name in wb.sheetnames:
        return wb[preferred_name]
    lower_map = {n.lower(): n for n in wb.sheetnames}
    if preferred_name.lower() in lower_map:
        return wb[lower_map[preferred_name.lower()]]
    raise KeyError(f"sheet not found: {preferred_name}, available={wb.sheetnames}")


def _iter_case_rows(
    ws,
    data_start_row: int,
    empty_streak_stop: int,
    max_scan_rows: int,
) -> list[int]:
    """Detect continuous test-case rows by Parameter Name column (C)."""
    rows: list[int] = []
    empty_streak = 0
    row = data_start_row
    max_row = min(ws.max_row, data_start_row + max_scan_rows)
    while row <= max_row:
        value = ws.cell(row=row, column=3).value
        if value is None or str(value).strip() == "":
            empty_streak += 1
            if empty_streak >= empty_streak_stop:
                break
        else:
            rows.append(row)
            empty_streak = 0
        row += 1
    return rows


def _iter_source_object_api_rows(
    ws,
    data_start_row: int,
    empty_streak_stop: int,
    max_scan_rows: int,
) -> Iterable[tuple[int, str | None, str | None]]:
    """Yield (row, object, api) sequentially for read-only worksheets.

    Random ``ws.cell(row=...)`` access on read-only worksheets becomes very slow
    when the workbook carries stale dimensions with a huge ``max_row``. Walking
    the sheet once via ``iter_rows()`` keeps alignment checks bounded.
    """
    empty_streak = 0
    max_row = min(ws.max_row, data_start_row + max_scan_rows)
    for row_idx, values in enumerate(
        ws.iter_rows(
            min_row=data_start_row,
            max_row=max_row,
            min_col=1,
            max_col=3,
            values_only=True,
        ),
        start=data_start_row,
    ):
        obj, _, api = values
        if api is None or str(api).strip() == "":
            empty_streak += 1
            if empty_streak >= empty_streak_stop:
                break
            continue
        empty_streak = 0
        yield row_idx, obj, api


def _to_col_idx(col: str | int) -> int:
    if isinstance(col, int):
        return col
    return column_index_from_string(col)


def _trim_sheet_to_max_column(ws, max_col_idx: int) -> None:
    """Trim worksheet columns to max_col_idx and clean residual metadata."""
    if ws.max_column > max_col_idx:
        ws.delete_cols(max_col_idx + 1, ws.max_column - max_col_idx)

    # delete_cols may leave stale merges/dimensions from the source sheet.
    for merged in list(ws.merged_cells.ranges):
        if merged.max_col <= max_col_idx:
            continue
        ws.merged_cells.ranges.remove(merged)
        if merged.min_col > max_col_idx:
            continue
        clipped_max_col = max_col_idx
        if (
            merged.min_col == clipped_max_col
            and merged.min_row == merged.max_row
        ):
            continue
        ws.merge_cells(
            start_row=merged.min_row,
            end_row=merged.max_row,
            start_column=merged.min_col,
            end_column=clipped_max_col,
        )

    stale_cells = [coord for coord in ws._cells if coord[1] > max_col_idx]
    for coord in stale_cells:
        del ws._cells[coord]

    for col_letter in list(ws.column_dimensions.keys()):
        try:
            col_idx = column_index_from_string(col_letter)
        except ValueError:
            continue
        if col_idx > max_col_idx:
            del ws.column_dimensions[col_letter]


def _set_cell_value_safe(ws, row: int, col: str, value: str | None) -> None:
    """Set worksheet cell value with merged-cell fallback.

    Some source rows in Wifi_LLAPI map to vertically merged result cells.
    openpyxl raises on assigning to non-anchor merged cells, so we resolve
    to the merge anchor in the same column.
    """
    col_idx = _to_col_idx(col)
    cell = ws.cell(row=row, column=col_idx)
    if not is_merged_cell(cell):
        cell.value = value
        return

    coordinate = cell.coordinate
    for merged in ws.merged_cells.ranges:
        if coordinate not in merged:
            continue
        if merged.min_col != col_idx:
            # Horizontal merge (cross-column) cannot keep per-column semantics.
            return
        ws.cell(row=merged.min_row, column=col_idx).value = value
        return


def _normalize_template_headers(ws) -> None:
    """Normalize Wifi_LLAPI result/tester header semantics for columns I~M."""
    for merged in list(ws.merged_cells.ranges):
        if merged.max_row < 2 or merged.min_row > 2:
            continue
        if merged.max_col < 9 or merged.min_col > 12:
            continue
        ws.unmerge_cells(str(merged))

    ws.merge_cells(start_row=2, end_row=2, start_column=9, end_column=11)
    ws.cell(row=2, column=9).value = RESULT_GROUP_HEADER
    ws.cell(row=2, column=12).value = TESTER_HEADER
    ws.cell(row=3, column=9).value = RESULT_HEADERS_BY_COLUMN["I"]
    ws.cell(row=3, column=10).value = RESULT_HEADERS_BY_COLUMN["J"]
    ws.cell(row=3, column=11).value = RESULT_HEADERS_BY_COLUMN["K"]
    ws.cell(row=3, column=12).value = TESTER_HEADER
    ws.cell(row=3, column=13).value = COMMENT_HEADER
    _ensure_summary_bucket_columns(ws)


def _ensure_summary_bucket_columns(ws) -> None:
    for column, header in SUMMARY_BUCKET_HEADERS.items():
        ws[f"{column}3"] = header
        ws.column_dimensions[column].hidden = True


def _copy_summary_sheet_from_existing_template(wb, template_path: Path) -> None:
    if not template_path.exists():
        return

    existing_wb = load_workbook(template_path, data_only=False)
    try:
        if SUMMARY_SHEET_NAME not in existing_wb.sheetnames:
            return

        if SUMMARY_SHEET_NAME in wb.sheetnames:
            del wb[SUMMARY_SHEET_NAME]
        src_ws = existing_wb[SUMMARY_SHEET_NAME]
        dst_ws = wb.create_sheet(SUMMARY_SHEET_NAME, 0)
        dst_ws.sheet_format = copy(src_ws.sheet_format)
        dst_ws.sheet_properties = copy(src_ws.sheet_properties)
        dst_ws.freeze_panes = src_ws.freeze_panes

        for row in src_ws.iter_rows():
            for src_cell in row:
                dst_cell = dst_ws[src_cell.coordinate]
                dst_cell.value = src_cell.value
                if src_cell.has_style:
                    dst_cell._style = copy(src_cell._style)
                if src_cell.number_format:
                    dst_cell.number_format = src_cell.number_format
                if src_cell.hyperlink:
                    dst_cell._hyperlink = copy(src_cell.hyperlink)
                if src_cell.comment:
                    dst_cell.comment = copy(src_cell.comment)

        for merged in src_ws.merged_cells.ranges:
            dst_ws.merge_cells(str(merged))
        for key, dim in src_ws.column_dimensions.items():
            dst_ws.column_dimensions[key] = copy(dim)
        for key, dim in src_ws.row_dimensions.items():
            dst_ws.row_dimensions[key] = copy(dim)
    finally:
        existing_wb.close()


def _truncate_comment(text: str | None, limit: int = 200) -> str:
    if not text:
        return ""
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)] + "..."


def _summary_bucket_for(item: WifiLlapiCaseResult, band_key: str) -> str:
    from testpilot.reporting.wifi_llapi_summary import classify_band_result  # noqa: PLC0415

    case_context = {
        "result_5g": item.result_5g,
        "result_6g": item.result_6g,
        "result_24g": item.result_24g,
        "diagnostic_status": item.diagnostic_status,
        "failure_snapshot": item.failure_snapshot or {},
        "comment": item.comment,
    }
    return classify_band_result(getattr(item, band_key), case_context).bucket


def build_template_from_source(
    source_xlsx: Path | str,
    out_template_xlsx: Path | str,
    *,
    sheet_name: str = DEFAULT_SHEET_NAME,
    clear_rules: ClearRules | None = None,
) -> TemplateBuildResult:
    """Extract wifi_LLAPI sheet as template, keep A~M columns, and clear runtime fields."""
    rules = clear_rules or ClearRules()
    source = Path(source_xlsx)
    out_path = Path(out_template_xlsx)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(source)
    ws = _get_sheet(wb, sheet_name)
    actual_sheet_name = ws.title

    # Keep only target sheet to match "extract this page".
    for name in list(wb.sheetnames):
        if name != actual_sheet_name:
            wb.remove(wb[name])
    wb.active = 0
    ws = wb[actual_sheet_name]

    # Keep template schema stable: only columns A~M are preserved.
    template_max_col_idx = _to_col_idx(DEFAULT_TEMPLATE_MAX_COLUMN)
    _trim_sheet_to_max_column(ws, template_max_col_idx)
    _normalize_template_headers(ws)

    case_rows = _iter_case_rows(
        ws,
        rules.data_start_row,
        rules.empty_streak_stop,
        rules.max_scan_rows,
    )
    clear_col_indices = [_to_col_idx(c) for c in rules.clear_columns]
    for row in case_rows:
        for col_idx in clear_col_indices:
            cell = ws.cell(row=row, column=col_idx)
            if is_merged_cell(cell):
                continue
            cell.value = None

    _copy_summary_sheet_from_existing_template(wb, out_path)
    wb.save(out_path)
    wb.close()

    return TemplateBuildResult(
        template_path=out_path,
        sheet_name=actual_sheet_name,
        total_case_rows=len(case_rows),
        cleared_columns=rules.clear_columns,
        source_workbook=source,
        source_sheet=actual_sheet_name,
    )


def write_template_manifest(
    manifest_path: Path | str,
    build_result: TemplateBuildResult,
) -> Path:
    out = Path(manifest_path)
    payload = {
        "template_path": _serialize_manifest_path(build_result.template_path, out),
        "sheet_name": build_result.sheet_name,
        "total_case_rows": build_result.total_case_rows,
        "cleared_columns": list(build_result.cleared_columns),
        "source_workbook": _serialize_manifest_path(build_result.source_workbook, out),
        "source_sheet": build_result.source_sheet,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _serialize_manifest_path(path: Path | str, manifest_path: Path | str) -> str:
    target = Path(path)
    manifest = Path(manifest_path)
    resolved_target = target.resolve(strict=False)
    repo_root = _find_git_root(manifest.parent)
    if repo_root is not None:
        try:
            return resolved_target.relative_to(repo_root.resolve(strict=False)).as_posix()
        except ValueError:
            pass
    try:
        return os.path.relpath(
            resolved_target,
            start=manifest.parent.resolve(strict=False),
        ).replace("\\", "/")
    except ValueError:
        pass
    return str(resolved_target if target.is_absolute() else target)


def _find_git_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def create_run_report_from_template(
    template_xlsx: Path | str,
    out_report_xlsx: Path | str,
) -> Path:
    src = Path(template_xlsx)
    dst = _resolve_report_copy_path(Path(out_report_xlsx))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def fill_case_results(
    report_xlsx: Path | str,
    case_results: Iterable[WifiLlapiCaseResult],
    *,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> Path:
    """Batch fill test command and result columns by source row."""
    path = Path(report_xlsx)
    wb = load_workbook(path)
    ws = _get_sheet(wb, sheet_name)

    for column, header in SUMMARY_BUCKET_HEADERS.items():
        ws[f"{column}3"] = header
        ws.column_dimensions[column].hidden = True

    for item in case_results:
        if item.source_row <= 0:
            continue
        row = item.source_row
        _set_cell_value_safe(ws, row, "G", normalize_command_block(item.executed_test_command))
        _set_cell_value_safe(ws, row, "H", sanitize_report_output(item.command_output))
        _set_cell_value_safe(ws, row, "I", item.result_5g)
        _set_cell_value_safe(ws, row, "J", item.result_6g)
        _set_cell_value_safe(ws, row, "K", item.result_24g)
        _set_cell_value_safe(ws, row, "L", item.tester)
        _set_cell_value_safe(ws, row, "M", _truncate_comment(item.comment))
        for band_key, column in SUMMARY_BUCKET_COLUMNS:
            _set_cell_value_safe(ws, row, column, _summary_bucket_for(item, band_key))

    wb.save(path)
    wb.close()
    return path


def finalize_report_metadata(
    report_xlsx: Path | str,
    meta: ReportMeta,
) -> Path:
    """Store report metadata in a hidden _meta sheet."""
    path = Path(report_xlsx)
    wb = load_workbook(path)
    if "_meta" in wb.sheetnames:
        ws = wb["_meta"]
        ws.delete_rows(1, ws.max_row)
    else:
        ws = wb.create_sheet("_meta")
        ws.sheet_state = "hidden"

    ws["A1"] = "run_date"
    ws["B1"] = meta.run_date.isoformat()
    ws["A2"] = "dut_fw_ver"
    ws["B2"] = meta.dut_fw_ver
    ws["A3"] = "source_excel"
    ws["B3"] = meta.source_excel
    ws["A4"] = "sheet_name"
    ws["B4"] = meta.sheet_name

    wb.save(path)
    wb.close()
    return path


def ensure_template_report(
    source_xlsx: Path | str,
    template_path: Path | str,
    *,
    manifest_path: Path | str | None = None,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> TemplateBuildResult:
    """Build template and optional manifest."""
    result = build_template_from_source(
        source_xlsx=source_xlsx,
        out_template_xlsx=template_path,
        sheet_name=sheet_name,
    )
    if manifest_path is not None:
        write_template_manifest(manifest_path, result)
    return result


def read_source_rows(
    source_xlsx: Path | str,
    *,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> dict[int, dict[str, str]]:
    """Read source object/api by row from Wifi_LLAPI sheet."""
    source = Path(source_xlsx)
    wb = load_workbook(source, read_only=True, data_only=False)
    ws = _get_sheet(wb, sheet_name)
    out: dict[int, dict[str, str]] = {}
    current_object = ""
    for row, obj, api in _iter_source_object_api_rows(
        ws,
        DATA_START_ROW,
        EMPTY_STREAK_STOP,
        MAX_SCAN_ROWS,
    ):
        obj_norm = normalize_text(obj)
        if obj_norm:
            current_object = obj_norm
        out[row] = {
            "object": current_object,
            "api": normalize_text(api),
        }
    wb.close()
    return out


def collect_alignment_issues(
    cases: Iterable[dict],
    source_xlsx: Path | str,
    *,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> list[dict[str, str | int]]:
    """Compare case source.row/object/api against source Excel sheet."""
    source_rows = read_source_rows(source_xlsx, sheet_name=sheet_name)
    issues: list[dict[str, str | int]] = []
    for case in cases:
        source = case.get("source", {}) if isinstance(case.get("source"), dict) else {}
        case_id = str(case.get("id", "?"))
        try:
            row = int(source.get("row", 0))
        except (TypeError, ValueError):
            row = 0

        expected_object = normalize_text(source.get("object"))
        expected_api = normalize_text(source.get("api"))

        if row not in source_rows:
            issues.append(
                {
                    "case_id": case_id,
                    "source_row": row,
                    "issue": "row_not_found",
                    "expected_object": expected_object,
                    "expected_api": expected_api,
                    "sheet_object": "",
                    "sheet_api": "",
                }
            )
            continue

        actual_object = source_rows[row]["object"]
        actual_api = source_rows[row]["api"]
        if expected_object != actual_object or expected_api != actual_api:
            issues.append(
                {
                    "case_id": case_id,
                    "source_row": row,
                    "issue": "object_or_api_mismatch",
                    "expected_object": expected_object,
                    "expected_api": expected_api,
                    "sheet_object": actual_object,
                    "sheet_api": actual_api,
                }
            )
    return issues


def _clear_result_row(ws, row: int) -> None:
    # Column M is reserved for evaluate-failure comments, so BLOCKED/SKIP
    # marker flows intentionally clear only G~L and leave M unchanged.
    for column in ("G", "H", "I", "J", "K", "L"):
        _set_cell_value_safe(ws, row, column, None)


def fill_blocked_markers(report_xlsx: Path, blocked: list[object]) -> None:
    if not blocked:
        return
    path = Path(report_xlsx)
    wb = load_workbook(path)
    ws = _get_sheet(wb, DEFAULT_SHEET_NAME)

    try:
        for item in blocked:
            try:
                row = int(getattr(item, "source_row_before", 0) or 0)
            except (TypeError, ValueError):
                row = 0
            if row <= 0 or row > ws.max_row:
                continue
            _clear_result_row(ws, row)
            reason = getattr(item, "blocked_reason", None)
            reason = reason or "unknown"
            _set_cell_value_safe(ws, row, "H", f"BLOCKED: {reason}")
    finally:
        # Ensure workbook is saved and closed even on errors
        wb.save(path)
        wb.close()


def fill_skip_markers(report_xlsx: Path, skipped: list[object]) -> None:
    if not skipped:
        return
    path = Path(report_xlsx)
    wb = load_workbook(path)
    ws = _get_sheet(wb, DEFAULT_SHEET_NAME)

    try:
        for item in skipped:
            try:
                row = int(getattr(item, "source_row_before", 0) or 0)
            except (TypeError, ValueError):
                row = 0
            try:
                template_row = int(getattr(item, "template_row", 0) or 0)
            except (TypeError, ValueError):
                template_row = 0
            # Validate source row
            if row <= 0 or row > ws.max_row:
                continue
            # Validate template_row - must be a positive integer and within worksheet bounds
            if template_row <= 0 or template_row > ws.max_row:
                continue
            _clear_result_row(ws, row)
            _set_cell_value_safe(ws, row, "H", f"SKIP: duplicate with D{template_row:03d}")
    finally:
        wb.save(path)
        wb.close()


def validate_wifi_llapi_report_template(
    template_xlsx: Path | str,
) -> dict[str, str]:
    """Validate Excel template shape and return sheet name mapping.

    Returns ``{"summary_sheet": "Summary", "wifi_sheet": "Wifi_LLAPI"}`` on success.
    Raises :exc:`TemplateValidationError` for any structural mismatch.
    """
    path = Path(template_xlsx)
    wb = load_workbook(path)
    try:
        for sheet_name in (SUMMARY_SHEET_NAME, DEFAULT_SHEET_NAME):
            if sheet_name not in wb.sheetnames:
                raise TemplateValidationError(f"missing sheet: {sheet_name}")

        ws = wb[DEFAULT_SHEET_NAME]
        for col, expected in RESULT_HEADERS_BY_COLUMN.items():
            col_idx = _to_col_idx(col)
            actual = normalize_text(ws.cell(row=3, column=col_idx).value)
            if actual != normalize_text(expected):
                raise TemplateValidationError(
                    f"result header mismatch at {DEFAULT_SHEET_NAME}!{col}3: "
                    f"expected '{expected}', got '{actual}'"
                )

        # Validate required column-1 headers (substring match).
        _col1_checks: tuple[tuple[str, int, str], ...] = (
            ("A", 1, "Object"),
            ("E", 1, "LLAPI"),
            ("L", 1, "Tester"),
        )
        for col_letter, row_num, expected_text in _col1_checks:
            col_idx = _to_col_idx(col_letter)
            actual = normalize_text(ws.cell(row=row_num, column=col_idx).value)
            if expected_text.lower() not in actual.lower():
                raise TemplateValidationError(
                    f"column header mismatch at {DEFAULT_SHEET_NAME}!{col_letter}{row_num}: "
                    f"expected to contain '{expected_text}', got '{actual}'"
                )

        # M1 or M3 must contain the comment/fail-reason header.
        m_col_idx = _to_col_idx("M")
        m1_val = normalize_text(ws.cell(row=1, column=m_col_idx).value)
        m3_val = normalize_text(ws.cell(row=3, column=m_col_idx).value)
        if COMMENT_HEADER.lower() not in m1_val.lower() and COMMENT_HEADER.lower() not in m3_val.lower():
            raise TemplateValidationError(
                f"comment/fail-reason column header missing: "
                f"expected '{COMMENT_HEADER}' in {DEFAULT_SHEET_NAME}!M1 or M3, "
                f"got M1='{m1_val}', M3='{m3_val}'"
            )

        for col_letter, expected_header in SUMMARY_BUCKET_HEADERS.items():
            actual = normalize_text(ws[f"{col_letter}3"].value)
            if actual != expected_header:
                raise TemplateValidationError(
                    f"summary bucket header mismatch at {DEFAULT_SHEET_NAME}!{col_letter}3: "
                    f"expected '{expected_header}', got '{actual}'"
                )
            if ws.column_dimensions[col_letter].hidden is not True:
                raise TemplateValidationError(
                    f"summary bucket column must be hidden: {DEFAULT_SHEET_NAME}!{col_letter}:{col_letter}"
                )

        summary_ws = wb[SUMMARY_SHEET_NAME]
        required = {"Module", "Total Items", "Pass", "Fail", "Progress"}

        def _header_set(row_num: int) -> set[str]:
            return {
                normalize_text(summary_ws.cell(row=row_num, column=c).value)
                for c in range(1, len(SUMMARY_HEADERS) + 1)
            }

        if not (required <= _header_set(2) or required <= _header_set(3)):
            raise TemplateValidationError(
                f"Summary sheet missing required headers in row 2 or 3; "
                f"expected columns: {SUMMARY_HEADERS}"
            )

        required_fail_formulas = {
            "F3": "N",
            "F9": "O",
            "F15": "P",
        }
        for cell_ref, bucket_col in required_fail_formulas.items():
            formula = normalize_text(summary_ws[cell_ref].value)
            if not formula.startswith("="):
                raise TemplateValidationError(
                    f"Summary fail formula missing at {SUMMARY_SHEET_NAME}!{cell_ref}: "
                    f"expected formula referencing Wifi_LLAPI!${bucket_col}:${bucket_col}"
                )
            expected_ref = f"Wifi_LLAPI!${bucket_col}:${bucket_col}"
            if expected_ref not in formula:
                raise TemplateValidationError(
                    f"Summary fail formula at {SUMMARY_SHEET_NAME}!{cell_ref} must reference "
                    f"{expected_ref}, got '{formula}'"
                )

        return {"summary_sheet": SUMMARY_SHEET_NAME, "wifi_sheet": DEFAULT_SHEET_NAME}
    finally:
        wb.close()


def read_wifi_llapi_template_objects(
    template_xlsx: Path | str,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> dict[int, str]:
    """Return a row-number → object-prefix mapping from the template worksheet.

    Blank object-prefix cells carry the previous non-empty value forward.
    """
    path = Path(template_xlsx)
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = _get_sheet(wb, sheet_name)
    out: dict[int, str] = {}
    current_object = ""
    for row, obj, _api in _iter_source_object_api_rows(
        ws, DATA_START_ROW, EMPTY_STREAK_STOP, MAX_SCAN_ROWS
    ):
        obj_norm = normalize_text(obj)
        if obj_norm:
            current_object = obj_norm
        out[row] = current_object
    wb.close()
    return out


def write_summary_sheet(
    report_xlsx: Path | str,
    summary_payload: dict[str, object],
) -> Path:
    """Write (or overwrite) the Summary sheet in *report_xlsx* from *summary_payload*.

    Layout:
    - Row 1: policy marker ("Summary Policy", policy_version)
    - Row 3: column headers
    - Row 4+: one row per entry in ``summary_payload["band_category"]``
    """
    # Deferred to avoid circular dependency: wifi_llapi_excel ← wifi_llapi_summary.
    from testpilot.reporting.wifi_llapi_summary import SUMMARY_POLICY_VERSION  # noqa: PLC0415

    path = Path(report_xlsx)
    wb = load_workbook(path)

    if SUMMARY_SHEET_NAME in wb.sheetnames:
        insert_idx = wb.sheetnames.index(SUMMARY_SHEET_NAME)
        del wb[SUMMARY_SHEET_NAME]
        ws = wb.create_sheet(SUMMARY_SHEET_NAME, insert_idx)
    else:
        ws = wb.create_sheet(SUMMARY_SHEET_NAME, 0)

    policy_version = summary_payload.get("policy_version") or SUMMARY_POLICY_VERSION
    ws.cell(row=1, column=1).value = "Summary Policy"
    ws.cell(row=1, column=2).value = policy_version

    for col_idx, header in enumerate(SUMMARY_HEADERS, start=1):
        ws.cell(row=3, column=col_idx).value = header

    band_category = summary_payload.get("band_category", [])
    for offset, row_data in enumerate(band_category):
        r = 4 + offset
        label = (
            row_data.get("band_label")
            or row_data.get("band")
            or row_data.get("band_key")
            or ""
        )
        ws.cell(row=r, column=1).value = label
        ws.cell(row=r, column=2).value = row_data.get("category", "")
        ws.cell(row=r, column=3).value = row_data.get("total_items", 0)
        ws.cell(row=r, column=4).value = row_data.get("tested_items", 0)
        ws.cell(row=r, column=5).value = row_data.get("pass", 0)
        ws.cell(row=r, column=6).value = row_data.get("fail", 0)
        ws.cell(row=r, column=7).value = row_data.get("to_be_tested", 0)
        ws.cell(row=r, column=8).value = row_data.get("not_supported", 0)
        ws.cell(row=r, column=9).value = row_data.get("skip", 0)
        ws.cell(row=r, column=10).value = f"=IFERROR(E{r}/SUM(E{r}:G{r}),0)"
        ws.cell(row=r, column=11).value = f"=C{r}-SUM(E{r}:I{r})"
        ws.cell(row=r, column=12).value = f"=IFERROR(D{r}/C{r},0)"

    try:
        wb.save(path)
    finally:
        wb.close()
    return path
