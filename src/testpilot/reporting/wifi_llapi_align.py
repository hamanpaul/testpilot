from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from openpyxl import load_workbook

from testpilot.reporting.wifi_llapi_excel import (
    DATA_START_ROW,
    DEFAULT_SHEET_NAME,
    EMPTY_STREAK_STOP,
    MAX_SCAN_ROWS,
    normalize_text,
)

AlignStatus = Literal["already_aligned", "auto_aligned", "blocked", "skipped"]
BlockedReason = Literal[
    "object_api_not_in_template",
    "name_points_to_different_row",
    "name_not_in_template",
]

_ID_D_PATTERN = re.compile(r"(wifi-llapi-D)(\d{3})(-)")
_FILE_D_PATTERN = re.compile(r"^D(?P<row>\d{3})(?P<suffix>.*)$")


@dataclass(slots=True)
class TemplateIndex:
    forward: dict[int, tuple[str, str]]
    by_object_api: dict[tuple[str, str], int]
    by_api: dict[str, list[int]]


@dataclass(slots=True)
class AlignResult:
    case_file: Path
    status: AlignStatus
    source_row_before: int
    source_row_after: int | None
    source_object: str
    source_api: str
    filename_before: str
    filename_after: str | None
    id_before: str
    id_after: str | None
    blocked_reason: BlockedReason | None = None
    skip_winner_filename: str | None = None
    template_row: int | None = None
    template_row_object: str | None = None
    template_row_api: str | None = None


class AlignmentConflictError(RuntimeError):
    pass


def _extract_name_api(name: object) -> str:
    text = str(name).strip() if isinstance(name, str) else ""
    return text.split(".")[-1].strip() if text else ""


def _replace_id_row(case_id: str, canonical_row: int) -> str | None:
    if not _ID_D_PATTERN.search(case_id):
        return None
    return _ID_D_PATTERN.sub(rf"\g<1>{canonical_row:03d}\g<3>", case_id, count=1)


def build_template_index(template_xlsx: Path) -> TemplateIndex:
    wb = load_workbook(template_xlsx, read_only=True, data_only=True)
    try:
        ws = wb[DEFAULT_SHEET_NAME]
        forward: dict[int, tuple[str, str]] = {}
        by_object_api: dict[tuple[str, str], int] = {}
        by_api: dict[str, list[int]] = {}
        empty_streak = 0
        for row in range(DATA_START_ROW, min(ws.max_row, DATA_START_ROW + MAX_SCAN_ROWS) + 1):
            obj = normalize_text(ws[f"A{row}"].value)
            api = normalize_text(ws[f"C{row}"].value)
            if not api:
                empty_streak += 1
                if empty_streak >= EMPTY_STREAK_STOP:
                    break
                continue
            empty_streak = 0
            forward[row] = (obj, api)
            by_object_api[(obj, api)] = row
            by_api.setdefault(api, []).append(row)
        return TemplateIndex(forward=forward, by_object_api=by_object_api, by_api=by_api)
    finally:
        wb.close()


def align_case(case: dict, index: TemplateIndex, case_file: Path) -> AlignResult:
    source = case.get("source") if isinstance(case.get("source"), dict) else {}
    obj = normalize_text(source.get("object"))
    api = normalize_text(source.get("api"))
    source_row_before = int(source.get("row", 0) or 0)
    case_id = str(case.get("id", ""))
    name_api = _extract_name_api(case.get("name"))
    filename_before = case_file.name
    template_row = index.by_object_api.get((obj, api))
    template_object, template_api = index.forward.get(template_row, ("", ""))
    if template_row is None:
        return AlignResult(
            case_file=case_file,
            status="blocked",
            source_row_before=source_row_before,
            source_row_after=None,
            source_object=obj,
            source_api=api,
            filename_before=filename_before,
            filename_after=None,
            id_before=case_id,
            id_after=None,
            blocked_reason="object_api_not_in_template",
        )
    if name_api and name_api != template_api:
        candidate_rows = index.by_api.get(name_api, [])
        reason = "name_points_to_different_row" if candidate_rows else "name_not_in_template"
        return AlignResult(
            case_file=case_file,
            status="blocked",
            source_row_before=source_row_before,
            source_row_after=None,
            source_object=obj,
            source_api=api,
            filename_before=filename_before,
            filename_after=None,
            id_before=case_id,
            id_after=None,
            blocked_reason=reason,
            template_row=template_row,
            template_row_object=template_object,
            template_row_api=template_api,
        )
    filename_after = None
    source_row_after = template_row
    id_after = _replace_id_row(case_id, template_row)
    if not filename_before.startswith(f"D{template_row:03d}_"):
        match = _FILE_D_PATTERN.match(case_file.stem)
        suffix = match.group("suffix") if match else f"_{case_file.stem}"
        filename_after = f"D{template_row:03d}{suffix}{case_file.suffix}"
    if source_row_before == template_row and filename_after is None and id_after in (None, case_id):
        return AlignResult(
            case_file=case_file,
            status="already_aligned",
            source_row_before=source_row_before,
            source_row_after=template_row,
            source_object=obj,
            source_api=api,
            filename_before=filename_before,
            filename_after=None,
            id_before=case_id,
            id_after=None,
            template_row=template_row,
            template_row_object=template_object,
            template_row_api=template_api,
        )
    return AlignResult(
        case_file=case_file,
        status="auto_aligned",
        source_row_before=source_row_before,
        source_row_after=template_row,
        source_object=obj,
        source_api=api,
        filename_before=filename_before,
        filename_after=filename_after,
        id_before=case_id,
        id_after=id_after if id_after != case_id else None,
        template_row=template_row,
        template_row_object=template_object,
        template_row_api=template_api,
    )
