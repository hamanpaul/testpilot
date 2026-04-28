"""Pass 1 (baseline) + Pass 2 (mechanical extract from workbook G/H).

Phase B behaviour:
- Pass 1 runs via runner_facade.
- If Pass 1 verdict matches workbook → bucket=confirmed.
- If Pass 1 mismatches → mechanically extract commands from test_steps / command_output.
- If no commands extracted → bucket=needs_pass3, reason=pass2_no_extract.
- If commands extracted → DO NOT rerun. Return bucket=needs_pass3,
  reason=pass2_extract_only_no_rerun, carry extracted_commands for Phase D.
- pass2_verdict_match is always None in Phase B (Pass 2 does not rerun).
- If the Pass 1 facade returns an error → bucket=block with explicit reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from testpilot.audit.extractor import ExtractedCommand, extract_commands
from testpilot.audit.runner_facade import (
    AuditCaseResult,
    run_one_case_for_audit,
)


@dataclass
class PassResult:
    case_id: str
    pass1_verdict_match: bool
    pass2_verdict_match: bool | None  # None = Pass 2 not run (Phase B always None)
    extracted_commands: list[ExtractedCommand] = field(default_factory=list)
    bucket: str = "needs_pass3"  # confirmed / needs_pass3 / block
    reason: str = ""
    pass1_artifacts: dict[str, Any] = field(default_factory=dict)
    pass2_artifacts: dict[str, Any] = field(default_factory=dict)  # reserved for later rerun phases


def _run_facade(plugin: str, case_id: str) -> AuditCaseResult:
    """Thin indirection so tests can patch without reaching into runner_facade."""
    return run_one_case_for_audit(plugin, case_id)


def _verdict_matches_workbook(verdict_per_band: dict[str, str], workbook_row: Any) -> bool:
    """Return True when all populated workbook verdict bands match the facade result."""
    if not verdict_per_band:
        return False
    expected = {
        "5g": str(getattr(workbook_row, "result_5g", "") or "").strip().lower(),
        "6g": str(getattr(workbook_row, "result_6g", "") or "").strip().lower(),
        "2.4g": str(getattr(workbook_row, "result_24g", "") or "").strip().lower(),
    }
    actual = {k.strip().lower(): str(v).strip().lower() for k, v in verdict_per_band.items()}
    populated = {band for band, val in expected.items() if val}
    if not populated:
        return False
    return all(actual.get(band) == expected[band] for band in populated)


def run_pass12_for_case(
    *,
    plugin: str,
    case_id: str,
    workbook_row: Any,
    run_dir: Path,
) -> PassResult:
    """Run Pass 1 then (extract-only) Pass 2 for one case.

    Caller is responsible for persisting bucket entries and JSON artifacts.
    ``run_dir`` is accepted for interface symmetry with later phases; Pass 1/2
    itself does not write files — the CLI layer does.
    """
    # ---- Pass 1 ----------------------------------------------------------------
    p1 = _run_facade(plugin, case_id)

    if p1.error:
        return PassResult(
            case_id=case_id,
            pass1_verdict_match=False,
            pass2_verdict_match=None,
            bucket="block",
            reason=f"pass1_error: {p1.error}",
            pass1_artifacts={
                "verdict": p1.verdict_per_band,
                "error": p1.error,
                "artifacts": dict(p1.artifacts),
            },
        )

    p1_match = _verdict_matches_workbook(p1.verdict_per_band, workbook_row)
    if p1_match:
        return PassResult(
            case_id=case_id,
            pass1_verdict_match=True,
            pass2_verdict_match=None,
            bucket="confirmed",
            reason="pass1_verdict_match",
            pass1_artifacts={
                "verdict": p1.verdict_per_band,
                "error": None,
                "artifacts": dict(p1.artifacts),
            },
        )

    # ---- Pass 2 (extract-only) ------------------------------------------------
    text = "\n".join([
        getattr(workbook_row, "test_steps", "") or "",
        getattr(workbook_row, "command_output", "") or "",
    ])
    cmds = extract_commands(text)

    if not cmds:
        return PassResult(
            case_id=case_id,
            pass1_verdict_match=False,
            pass2_verdict_match=None,
            bucket="needs_pass3",
            reason="pass2_no_extract",
            pass1_artifacts={
                "verdict": p1.verdict_per_band,
                "error": None,
                "artifacts": dict(p1.artifacts),
            },
        )

    # Commands extracted but NOT rerun in Phase B.
    return PassResult(
        case_id=case_id,
        pass1_verdict_match=False,
        pass2_verdict_match=None,
        extracted_commands=cmds,
        bucket="needs_pass3",
        reason="pass2_extract_only_no_rerun",
        pass1_artifacts={
            "verdict": p1.verdict_per_band,
            "error": None,
            "artifacts": dict(p1.artifacts),
        },
    )
