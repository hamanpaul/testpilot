from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from pathlib import Path
import re
import shutil
import subprocess
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


@dataclass(slots=True)
class WifiLlapiInventoryReconcileAction:
    kind: Literal["restore", "rewrite", "demote", "blocker"]
    row: int | None
    case_file: Path | None
    target_file: Path | None
    reason: str
    source_ref: str | None = None

    def to_line(self) -> str:
        parts = [self.kind]
        if self.row is not None:
            parts.append(f"row={self.row:03d}")
        if self.case_file is not None:
            parts.append(f"case={self.case_file.name}")
        if self.target_file is not None and self.target_file != self.case_file:
            parts.append(f"target={self.target_file.name}")
        if self.source_ref:
            parts.append(f"source={self.source_ref}")
        if self.reason:
            parts.append(f"reason={self.reason}")
        return " ".join(parts)


@dataclass(slots=True)
class WifiLlapiInventoryReconcilePlan:
    template_xlsx: Path
    cases_dir: Path
    repo_root: Path
    audit: WifiLlapiInventoryAudit
    actions: tuple[WifiLlapiInventoryReconcileAction, ...] = ()
    blockers: tuple[WifiLlapiInventoryReconcileAction, ...] = ()

    def to_lines(self) -> list[str]:
        lines = [action.to_line() for action in self.actions]
        lines.extend(action.to_line() for action in self.blockers)
        return lines

    def to_dict(self) -> dict[str, object]:
        return {
            "template_xlsx": str(self.template_xlsx),
            "cases_dir": str(self.cases_dir),
            "repo_root": str(self.repo_root),
            "audit": self.audit.to_dict(),
            "actions": [action.to_line() for action in self.actions],
            "blockers": [action.to_line() for action in self.blockers],
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


def _replace_case_id_row(case_id: str, row: int) -> str:
    return _ID_D_PATTERN.sub(lambda match: f"{match.group(1)}{row:03d}{match.group(3)}", case_id, count=1)


def _sanitize_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_text(text)).strip("_")
    return slug or "case"


def _case_slug(case: dict[str, Any], case_file: Path) -> str:
    stem = case_file.stem
    match = _FILE_D_PATTERN.match(stem)
    if match and match.group("suffix"):
        slug = match.group("suffix").lstrip("_")
        if slug:
            return slug
    name = str(case.get("name", "")).strip()
    if name:
        return _sanitize_slug(name)
    case_id = str(case.get("id", "")).strip()
    if case_id:
        return _sanitize_slug(case_id)
    return "case"


def _canonical_case_filename(case: dict[str, Any], row: int, case_file: Path) -> str:
    return f"D{row:03d}_{_case_slug(case, case_file)}.yaml"


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


def _find_repo_root(path: Path) -> Path:
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
    return path


def _git_capture(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _collect_history_candidates(repo_root: Path, cases_dir: Path) -> dict[int, tuple[str, str]]:
    output = _git_capture(
        repo_root,
        "log",
        "--all",
        "--diff-filter=AMR",
        "--name-only",
        "--pretty=format:%H",
        "--",
        str(cases_dir.relative_to(repo_root)),
    )
    candidates: dict[int, tuple[str, str]] = {}
    current_sha = ""
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"[0-9a-f]{40}", line):
            current_sha = line
            continue
        path = Path(line)
        match = _FILE_D_PATTERN.match(path.name)
        if not match:
            continue
        row = int(match.group("row"))
        if row not in candidates:
            candidates[row] = (current_sha, line)
    return candidates


def _load_case_yaml(path: Path) -> dict[str, Any]:
    return load_case(path, validator=validate_wifi_llapi_case)


def _normalize_case_metadata(case: dict[str, Any], *, row: int, case_file: Path) -> dict[str, Any]:
    normalized = deepcopy(case)
    normalized["id"] = _replace_case_id_row(str(normalized.get("id", "")), row)
    normalized["source"] = dict(normalized.get("source") or {})
    normalized["source"]["row"] = row
    normalized["source"]["object"] = normalized["source"].get("object", "")
    normalized["source"]["api"] = normalized["source"].get("api", "")
    return normalized


def _write_case_yaml(path: Path, case: dict[str, Any]) -> None:
    import yaml

    path.write_text(yaml.safe_dump(case, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _demote_case_file(case_file: Path) -> Path:
    if case_file.stem.startswith("_"):
        return case_file
    return case_file.with_name(f"_{case_file.name}")


def _choose_survivor(row: int, grouped: list[tuple[Path, dict[str, Any]]]) -> tuple[Path, dict[str, Any]]:
    def score(item: tuple[Path, dict[str, Any]]) -> tuple[int, int, int, str]:
        case_file, case = item
        source = case.get("source") if isinstance(case.get("source"), dict) else {}
        return (
            1 if int(source.get("row", 0) or 0) == row else 0,
            1 if _extract_row_from_filename(case_file) == row else 0,
            1 if _extract_row_from_case_id(str(case.get("id", ""))) == row else 0,
            str(case_file),
        )

    return sorted(grouped, key=score, reverse=True)[0]


def build_wifi_llapi_inventory_reconcile_plan(
    template_xlsx: Path | str,
    cases_dir: Path | str,
    *,
    repo_root: Path | str | None = None,
) -> WifiLlapiInventoryReconcilePlan:
    template_xlsx = Path(template_xlsx)
    cases_dir = Path(cases_dir)
    repo_root = _find_repo_root(Path(repo_root) if repo_root is not None else cases_dir)
    audit = audit_wifi_llapi_inventory(template_xlsx, cases_dir)
    history_candidates = _collect_history_candidates(repo_root, cases_dir)

    actions: list[WifiLlapiInventoryReconcileAction] = []
    blockers: list[WifiLlapiInventoryReconcileAction] = []

    grouped_rows: dict[int, list[tuple[Path, dict[str, Any]]]] = {}
    for case_audit in audit.cases.values():
        if case_audit.resolved_row is None or case_audit.status == "extra":
            continue
        grouped_rows.setdefault(case_audit.resolved_row, []).append((case_audit.case_file, _load_case_yaml(case_audit.case_file)))

    for row in audit.missing_rows:
        candidate = history_candidates.get(row)
        if not candidate:
            blockers.append(
                WifiLlapiInventoryReconcileAction(
                    kind="blocker",
                    row=row,
                    case_file=None,
                    target_file=None,
                    reason="missing_history_candidate",
                )
            )
            continue
        sha, relative_path = candidate
        target_file = cases_dir / Path(relative_path).name
        actions.append(
            WifiLlapiInventoryReconcileAction(
                kind="restore",
                row=row,
                case_file=target_file,
                target_file=target_file,
                reason="restore_from_history",
                source_ref=f"{sha}:{relative_path}",
            )
        )

    for row, row_audit in sorted(audit.rows.items()):
        grouped = sorted(grouped_rows.get(row, []), key=lambda item: str(item[0]))
        if not grouped:
            continue
        survivor = None
        if row_audit.canonical_case_file is not None:
            for case_file, case in grouped:
                if case_file.name == row_audit.canonical_case_file:
                    survivor = (case_file, case)
                    break
        else:
            survivor = _choose_survivor(row, grouped)

        if survivor is None:
            continue

        survivor_file, survivor_case = survivor
        canonical_name = _canonical_case_filename(survivor_case, row, survivor_file)
        canonical_path = survivor_file.with_name(canonical_name)
        if canonical_path != survivor_file or not _is_canonical_metadata(survivor_case, row, survivor_file):
            actions.append(
                WifiLlapiInventoryReconcileAction(
                    kind="rewrite",
                    row=row,
                    case_file=survivor_file,
                    target_file=canonical_path,
                    reason="canonical_row_bearing_metadata",
                )
            )

        for case_file, _case in grouped:
            if case_file == survivor_file:
                continue
            actions.append(
                WifiLlapiInventoryReconcileAction(
                    kind="demote",
                    row=row,
                    case_file=case_file,
                    target_file=_demote_case_file(case_file),
                    reason="non_canonical_leftover",
                )
            )

    for case_name, case_audit in sorted(audit.cases.items()):
        if case_audit.status != "extra":
            continue
        actions.append(
            WifiLlapiInventoryReconcileAction(
                kind="demote",
                row=case_audit.resolved_row,
                case_file=case_audit.case_file,
                target_file=_demote_case_file(case_audit.case_file),
                reason="extra_outside_official_inventory",
            )
        )

    actions.sort(key=lambda action: ({"restore": 0, "rewrite": 1, "demote": 2, "blocker": 3}[action.kind], action.row or 0, action.case_file.name if action.case_file else ""))
    blockers.sort(key=lambda action: (action.row or 0, action.reason))
    return WifiLlapiInventoryReconcilePlan(
        template_xlsx=template_xlsx,
        cases_dir=cases_dir,
        repo_root=repo_root,
        audit=audit,
        actions=tuple(actions),
        blockers=tuple(blockers),
    )


def apply_wifi_llapi_inventory_reconcile_plan(plan: WifiLlapiInventoryReconcilePlan) -> None:
    for action in plan.actions:
        if action.kind == "restore":
            assert action.case_file is not None
            assert action.source_ref is not None
            sha, relative_path = action.source_ref.split(":", 1)
            restored_text = _git_capture(plan.repo_root, "show", f"{sha}:{relative_path}")
            case = _load_case_yaml_from_text(restored_text, action.case_file)
            normalized = _normalize_case_metadata(case, row=action.row or 0, case_file=action.case_file)
            action.case_file.parent.mkdir(parents=True, exist_ok=True)
            if action.case_file.exists():
                raise FileExistsError(f"restore target already exists: {action.case_file}")
            _write_case_yaml(action.case_file, normalized)
        elif action.kind == "rewrite":
            assert action.case_file is not None
            assert action.target_file is not None
            case = _load_case_yaml(action.case_file)
            normalized = _normalize_case_metadata(case, row=action.row or 0, case_file=action.target_file)
            if action.target_file != action.case_file:
                action.target_file.parent.mkdir(parents=True, exist_ok=True)
                if action.target_file.exists():
                    raise FileExistsError(f"rewrite target already exists: {action.target_file}")
                _write_case_yaml(action.target_file, normalized)
                action.case_file.unlink()
            else:
                _write_case_yaml(action.case_file, normalized)
        elif action.kind == "demote":
            assert action.case_file is not None
            assert action.target_file is not None
            action.target_file.parent.mkdir(parents=True, exist_ok=True)
            if action.target_file == action.case_file:
                continue
            if action.target_file.exists():
                raise FileExistsError(f"demote target already exists: {action.target_file}")
            shutil.move(str(action.case_file), str(action.target_file))
        elif action.kind == "blocker":
            continue


def _load_case_yaml_from_text(text: str, source: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise TypeError(f"{source}: restored case must be a mapping")
    validate_wifi_llapi_case(data, source)
    return data


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
