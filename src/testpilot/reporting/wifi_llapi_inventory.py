from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Literal

from testpilot.reporting.wifi_llapi_align import build_template_index
from testpilot.reporting.wifi_llapi_excel import normalize_text
from testpilot.schema.case_schema import load_case, validate_wifi_llapi_case

_FILE_D_PATTERN = re.compile(r"^D(?P<row>\d{3})(?P<suffix>.*)$")
_ID_D_PATTERN = re.compile(r"(wifi-llapi-D)(\d{3})(-)")

CaseStatus = Literal["canonical", "drifted", "duplicate", "extra"]
RowStatus = Literal["canonical", "missing", "drifted", "duplicate"]


@dataclass(slots=True)
class WifiLlapiInventoryCaseAudit:
    case_file: Path
    case_id: str
    source_row: int | None
    source_object: str
    source_api: str
    resolved_row: int | None
    status: CaseStatus
    reason: str
    filename_row: int | None
    id_row: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "case_file": str(self.case_file),
            "case_id": self.case_id,
            "source_row": self.source_row,
            "source_object": self.source_object,
            "source_api": self.source_api,
            "resolved_row": self.resolved_row,
            "status": self.status,
            "reason": self.reason,
            "filename_row": self.filename_row,
            "id_row": self.id_row,
        }


@dataclass(slots=True)
class WifiLlapiInventoryRowAudit:
    row: int
    source_object: str
    source_api: str
    status: RowStatus
    discoverable_case_files: tuple[str, ...] = ()
    canonical_case_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "row": self.row,
            "source_object": self.source_object,
            "source_api": self.source_api,
            "status": self.status,
            "discoverable_case_files": list(self.discoverable_case_files),
            "canonical_case_file": self.canonical_case_file,
        }


@dataclass(slots=True)
class WifiLlapiInventoryAudit:
    template_xlsx: Path
    cases_dir: Path
    rows: dict[int, WifiLlapiInventoryRowAudit] = field(default_factory=dict)
    cases: dict[str, WifiLlapiInventoryCaseAudit] = field(default_factory=dict)
    case_status_counts: dict[str, int] = field(default_factory=dict)
    missing_rows: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "template_xlsx": str(self.template_xlsx),
            "cases_dir": str(self.cases_dir),
            "rows": {str(row): audit.to_dict() for row, audit in sorted(self.rows.items())},
            "cases": {name: audit.to_dict() for name, audit in sorted(self.cases.items())},
            "case_status_counts": dict(sorted(self.case_status_counts.items())),
            "missing_rows": list(self.missing_rows),
        }


def _extract_row_from_filename(case_file: Path) -> int | None:
    match = _FILE_D_PATTERN.match(case_file.stem)
    if not match:
        return None
    return int(match.group("row"))


def _extract_row_from_case_id(case_id: str) -> int | None:
    match = _ID_D_PATTERN.search(case_id)
    if not match:
        return None
    return int(match.group(2))


def _is_canonical_metadata(case: dict[str, Any], row: int, case_file: Path) -> bool:
    source = case.get("source") if isinstance(case.get("source"), dict) else {}
    source_row = source.get("row")
    return (
        int(source_row or 0) == row
        and _extract_row_from_filename(case_file) == row
        and _extract_row_from_case_id(str(case.get("id", ""))) == row
    )


def _load_discoverable_cases(cases_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not cases_dir.is_dir():
        return []
    discovered: list[tuple[Path, dict[str, Any]]] = []
    for case_file in sorted(cases_dir.glob("*.y*ml")):
        if case_file.stem.startswith("_"):
            continue
        case = load_case(case_file, validator=validate_wifi_llapi_case)
        discovered.append((case_file, case))
    return discovered


def _resolve_case_row(
    case: dict[str, Any],
    candidate_rows: list[int],
) -> int | None:
    source = case.get("source") if isinstance(case.get("source"), dict) else {}
    source_row = int(source.get("row", 0) or 0)
    if source_row in candidate_rows:
        return source_row
    if len(candidate_rows) == 1:
        return candidate_rows[0]
    return None


def audit_wifi_llapi_inventory(template_xlsx: Path | str, cases_dir: Path | str) -> WifiLlapiInventoryAudit:
    template_xlsx = Path(template_xlsx)
    cases_dir = Path(cases_dir)
    index = build_template_index(template_xlsx)
    official_rows = sorted(index.forward)

    discovered_cases = _load_discoverable_cases(cases_dir)
    row_groups: dict[int, list[tuple[Path, dict[str, Any]]]] = {row: [] for row in official_rows}
    case_audits: dict[str, WifiLlapiInventoryCaseAudit] = {}
    extra_rows: dict[str, WifiLlapiInventoryCaseAudit] = {}
    case_status_counts = {"canonical": 0, "drifted": 0, "duplicate": 0, "extra": 0}

    for case_file, case in discovered_cases:
        source = case.get("source") if isinstance(case.get("source"), dict) else {}
        source_object = normalize_text(source.get("object"))
        source_api = normalize_text(source.get("api"))
        source_row = int(source.get("row", 0) or 0) or None
        case_id = str(case.get("id", ""))
        filename_row = _extract_row_from_filename(case_file)
        id_row = _extract_row_from_case_id(case_id)
        candidate_rows = index.by_object_api.get((source_object, source_api), [])
        resolved_row = _resolve_case_row(case, candidate_rows)
        if resolved_row is None:
            status: CaseStatus = "extra" if not candidate_rows else "drifted"
            reason = "object_api_not_in_template" if not candidate_rows else "unresolved_object_api_family"
            audit = WifiLlapiInventoryCaseAudit(
                case_file=case_file,
                case_id=case_id,
                source_row=source_row,
                source_object=source_object,
                source_api=source_api,
                resolved_row=None,
                status=status,
                reason=reason,
                filename_row=filename_row,
                id_row=id_row,
            )
            if status == "extra":
                extra_rows[case_file.name] = audit
            else:
                case_audits[case_file.name] = audit
                case_status_counts["drifted"] += 1
            continue
        row_groups.setdefault(resolved_row, []).append((case_file, case))
        case_audits[case_file.name] = WifiLlapiInventoryCaseAudit(
            case_file=case_file,
            case_id=case_id,
            source_row=source_row,
            source_object=source_object,
            source_api=source_api,
            resolved_row=resolved_row,
            status="canonical",  # provisional; refined below
            reason="",
            filename_row=filename_row,
            id_row=id_row,
        )

    row_audits: dict[int, WifiLlapiInventoryRowAudit] = {}
    missing_rows: list[int] = []

    for row in official_rows:
        source_object, source_api = index.forward[row]
        grouped = sorted(row_groups.get(row, []), key=lambda item: str(item[0]))
        if not grouped:
            row_audits[row] = WifiLlapiInventoryRowAudit(
                row=row,
                source_object=source_object,
                source_api=source_api,
                status="missing",
            )
            missing_rows.append(row)
            continue

        exact = [
            case_file.name
            for case_file, case in grouped
            if _is_canonical_metadata(case, row, case_file)
        ]
        canonical_case_file = min(exact) if exact else None

        row_status: RowStatus
        if canonical_case_file is not None and len(grouped) == 1:
            row_status = "canonical" if _is_canonical_metadata(grouped[0][1], row, grouped[0][0]) else "drifted"
        elif canonical_case_file is not None:
            row_status = "duplicate"
        else:
            row_status = "drifted" if len(grouped) == 1 else "duplicate"

        row_audits[row] = WifiLlapiInventoryRowAudit(
            row=row,
            source_object=source_object,
            source_api=source_api,
            status=row_status,
            discoverable_case_files=tuple(case_file.name for case_file, _case in grouped),
            canonical_case_file=canonical_case_file,
        )

        if canonical_case_file is not None:
            case_statuses = {
                case_file.name: ("canonical" if case_file.name == canonical_case_file and _is_canonical_metadata(case, row, case_file) else "duplicate")
                for case_file, case in grouped
            }
        else:
            case_statuses = {
                case_file.name: ("drifted" if len(grouped) == 1 else "duplicate")
                for case_file, _case in grouped
            }

        if canonical_case_file is None and len(grouped) == 1:
            only_case_file, only_case = grouped[0]
            case_statuses[only_case_file.name] = "drifted"
            case_audits[only_case_file.name] = WifiLlapiInventoryCaseAudit(
                case_file=only_case_file,
                case_id=str(only_case.get("id", "")),
                source_row=int(only_case.get("source", {}).get("row", 0) or 0) or None,
                source_object=normalize_text(only_case.get("source", {}).get("object")),
                source_api=normalize_text(only_case.get("source", {}).get("api")),
                resolved_row=row,
                status="drifted",
                reason="stale_row_bearing_metadata",
                filename_row=_extract_row_from_filename(only_case_file),
                id_row=_extract_row_from_case_id(str(only_case.get("id", ""))),
            )
        else:
            for case_file, case in grouped:
                status = case_statuses[case_file.name]
                reason = "canonical_metadata" if status == "canonical" else "row_already_claimed"
                if status == "duplicate" and not _is_canonical_metadata(case, row, case_file):
                    reason = "stale_row_bearing_metadata" if len(grouped) == 1 else "duplicate_discoverable_row"
                case_audits[case_file.name] = WifiLlapiInventoryCaseAudit(
                    case_file=case_file,
                    case_id=str(case.get("id", "")),
                    source_row=int(case.get("source", {}).get("row", 0) or 0) or None,
                    source_object=normalize_text(case.get("source", {}).get("object")),
                    source_api=normalize_text(case.get("source", {}).get("api")),
                    resolved_row=row,
                    status=status,  # type: ignore[arg-type]
                    reason=reason,
                    filename_row=_extract_row_from_filename(case_file),
                    id_row=_extract_row_from_case_id(str(case.get("id", ""))),
                )

        for status in case_statuses.values():
            case_status_counts[status] += 1

    for case_name, audit in extra_rows.items():
        case_audits[case_name] = audit
        case_status_counts["extra"] += 1

    # Ensure canonical row selection is stable for duplicate rows with multiple exact matches.
    for row, row_audit in row_audits.items():
        if row_audit.status != "duplicate" or row_audit.canonical_case_file is None:
            continue
        exact_candidates = sorted(
            name
            for name, audit in case_audits.items()
            if audit.resolved_row == row and audit.status == "canonical"
        )
        if exact_candidates:
            row_audit.canonical_case_file = exact_candidates[0]

    return WifiLlapiInventoryAudit(
        template_xlsx=template_xlsx,
        cases_dir=cases_dir,
        rows=row_audits,
        cases=case_audits,
        case_status_counts=case_status_counts,
        missing_rows=tuple(missing_rows),
    )
