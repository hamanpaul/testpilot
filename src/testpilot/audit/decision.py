"""Citation verification + bucket decision logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Citation:
    file: str
    line: int
    snippet: str


@dataclass
class DecisionInput:
    verdict_match: bool
    citation_present: bool
    citation_verified: bool
    field_scope_safe: bool
    schema_valid: bool


def verify_citation(c: Citation, *, repo_root: Path) -> bool:
    """Check that file exists, line is valid, and snippet matches the line (whitespace-tolerant)."""
    path = Path(c.file)
    if not path.is_absolute():
        path = repo_root / path
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return False
    if c.line < 1 or c.line > len(lines):
        return False
    actual = lines[c.line - 1].strip()
    snippet = c.snippet.strip()
    return snippet in actual


def verify_all(citations: Iterable[Citation], *, repo_root: Path) -> bool:
    """Return True only when every citation verifies."""
    return all(verify_citation(c, repo_root=repo_root) for c in citations)


def decide_bucket(inp: DecisionInput) -> tuple[str, str]:
    """Return (bucket, reason).

    Rules:
    - ``block``   when verdict_match is False
    - ``applied`` when verdict_match is True and all other checks pass
    - ``pending`` otherwise, with comma-joined reasons
    """
    if not inp.verdict_match:
        return "block", "verdict_mismatch_after_all_passes"

    if (
        inp.citation_present
        and inp.citation_verified
        and inp.field_scope_safe
        and inp.schema_valid
    ):
        return "applied", "all_checks_passed"

    reasons: list[str] = []
    if not inp.citation_present:
        reasons.append("citation_missing")
    if not inp.citation_verified:
        reasons.append("citation_not_verified")
    if not inp.field_scope_safe:
        reasons.append("field_scope_violation")
    if not inp.schema_valid:
        reasons.append("schema_invalid")
    return "pending", ",".join(reasons)
