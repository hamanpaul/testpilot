"""Thin wrapper over Orchestrator.run() for single-case audit execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from testpilot.core.orchestrator import Orchestrator

_VERDICT_FIELDS: tuple[tuple[str, str], ...] = (
    ("result_5g", "5g"),
    ("result_6g", "6g"),
    ("result_24g", "2.4g"),
)
_CAPTURE_EXCLUDED_FIELDS = frozenset({"case_id", *(field for field, _ in _VERDICT_FIELDS)})
_ARTIFACT_KEYS: tuple[str, ...] = (
    "artifact_dir",
    "template_path",
    "report_path",
    "json_report_path",
    "md_report_path",
    "html_report_path",
    "dut_log_path",
    "sta_log_path",
    "agent_trace_dir",
)


@dataclass(slots=True)
class AuditCaseResult:
    case_id: str
    verdict_per_band: dict[str, str]
    capture: dict[str, Any]
    artifacts: dict[str, str]
    error: str | None


def _matches_case_id(requested_case_id: str, reported_case_id: str) -> bool:
    requested = requested_case_id.strip().lower()
    reported = reported_case_id.strip().lower()
    if not requested or not reported:
        return False
    return (
        requested == reported
        or requested.startswith(f"{reported}-")
        or reported.startswith(f"{requested}-")
    )


def _project_artifacts(result: Mapping[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for key in _ARTIFACT_KEYS:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            artifacts[key] = value
    return artifacts


def _load_matching_case(json_report_path: Path, case_id: str) -> dict[str, Any] | None:
    payload = json.loads(json_report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json report must be an object: {json_report_path}")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"json report missing cases list: {json_report_path}")

    requested = case_id.strip().lower()
    exact_matches: list[dict[str, Any]] = []
    prefix_matches: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        reported = str(case.get("case_id", "")).strip().lower()
        if not reported:
            continue
        if requested == reported:
            exact_matches.append(dict(case))
            continue
        if _matches_case_id(case_id, reported):
            prefix_matches.append(dict(case))

    # Prefer an exact case-id hit; only fall back to dash-delimited family matching.
    matches = exact_matches or prefix_matches
    if len(matches) > 1:
        raise ValueError(f"multiple cases matched json report: {case_id}")
    if matches:
        return matches[0]
    return None


def _project_verdicts(case_payload: Mapping[str, Any]) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    for source_key, audit_key in _VERDICT_FIELDS:
        value = case_payload.get(source_key)
        if value is None:
            continue
        verdict = str(value).strip()
        if verdict:
            verdicts[audit_key] = verdict
    return verdicts


def _project_capture(case_payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in case_payload.items()
        if key not in _CAPTURE_EXCLUDED_FIELDS
    }


def run_one_case_for_audit(
    plugin: str,
    case_id: str,
    *,
    repo_root: Path | None = None,
) -> AuditCaseResult:
    """Run a single case through the public Orchestrator API for audit mode."""
    resolved_root = repo_root or Path.cwd()
    orchestrator = Orchestrator(project_root=resolved_root)

    try:
        run_result = orchestrator.run(plugin, case_ids=[case_id])
    except Exception as exc:
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts={},
            error=f"orchestrator error: {exc}",
        )

    artifacts = _project_artifacts(run_result)
    json_report = artifacts.get("json_report_path")
    if not json_report:
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts=artifacts,
            error="missing json_report_path from orchestrator result",
        )

    json_report_path = Path(json_report)
    if not json_report_path.is_file():
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts=artifacts,
            error=f"json report not found: {json_report_path}",
        )

    try:
        case_payload = _load_matching_case(json_report_path, case_id)
    except json.JSONDecodeError as exc:
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts=artifacts,
            error=f"json report parse error: {exc}",
        )
    except OSError as exc:
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts=artifacts,
            error=f"json report read error: {exc}",
        )
    except ValueError as exc:
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts=artifacts,
            error=str(exc),
        )

    if case_payload is None:
        return AuditCaseResult(
            case_id=case_id,
            verdict_per_band={},
            capture={},
            artifacts=artifacts,
            error=f"case not found in json report: {case_id}",
        )

    return AuditCaseResult(
        case_id=case_id,
        verdict_per_band=_project_verdicts(case_payload),
        capture=_project_capture(case_payload),
        artifacts=artifacts,
        error=None,
    )
