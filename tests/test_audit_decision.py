"""Citation verification + bucket decision tests (Task 13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from testpilot.audit.decision import (
    Citation,
    DecisionInput,
    decide_bucket,
    verify_citation,
)


def test_verify_citation_matches_existing_file(tmp_path: Path) -> None:
    f = tmp_path / "src" / "code.c"
    f.parent.mkdir(parents=True)
    f.write_text("line1\nuint16 srg_pbssid_bmp[4];\nline3\n")

    cit = Citation(file=str(f), line=2, snippet="uint16 srg_pbssid_bmp[4];")
    assert verify_citation(cit, repo_root=tmp_path) is True


def test_verify_citation_rejects_wrong_line(tmp_path: Path) -> None:
    f = tmp_path / "src" / "code.c"
    f.parent.mkdir(parents=True)
    f.write_text("line1\nuint16 srg_pbssid_bmp[4];\nline3\n")

    cit = Citation(file=str(f), line=99, snippet="uint16 srg_pbssid_bmp[4];")
    assert verify_citation(cit, repo_root=tmp_path) is False


def test_verify_citation_rejects_missing_file(tmp_path: Path) -> None:
    cit = Citation(file=str(tmp_path / "no.c"), line=1, snippet="x")
    assert verify_citation(cit, repo_root=tmp_path) is False


def test_decide_bucket_applied() -> None:
    inp = DecisionInput(
        verdict_match=True,
        citation_present=True,
        citation_verified=True,
        field_scope_safe=True,
        schema_valid=True,
    )
    bucket, reason = decide_bucket(inp)
    assert bucket == "applied"


def test_decide_bucket_pending_when_citation_missing() -> None:
    inp = DecisionInput(
        verdict_match=True,
        citation_present=False,
        citation_verified=False,
        field_scope_safe=True,
        schema_valid=True,
    )
    bucket, reason = decide_bucket(inp)
    assert bucket == "pending"
    assert "citation" in reason


def test_decide_bucket_block_on_verdict_mismatch() -> None:
    inp = DecisionInput(
        verdict_match=False,
        citation_present=True,
        citation_verified=True,
        field_scope_safe=True,
        schema_valid=True,
    )
    bucket, reason = decide_bucket(inp)
    assert bucket == "block"


def test_verify_citation_relative_path(tmp_path: Path) -> None:
    """Relative file paths are resolved against repo_root."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "api.c").write_text("// comment\nint foo(void);\n")

    cit = Citation(file="src/api.c", line=2, snippet="int foo(void);")
    assert verify_citation(cit, repo_root=tmp_path) is True


def test_verify_citation_snippet_substring_tolerance(tmp_path: Path) -> None:
    """Snippet only needs to be contained in the stripped line."""
    f = tmp_path / "f.c"
    f.write_text("    int result = 0;  // init\n")

    cit = Citation(file=str(f), line=1, snippet="int result = 0;")
    assert verify_citation(cit, repo_root=tmp_path) is True


def test_decide_bucket_pending_field_scope_violation() -> None:
    inp = DecisionInput(
        verdict_match=True,
        citation_present=True,
        citation_verified=True,
        field_scope_safe=False,
        schema_valid=True,
    )
    bucket, reason = decide_bucket(inp)
    assert bucket == "pending"
    assert "field_scope" in reason


def test_decide_bucket_pending_when_citation_not_verified() -> None:
    inp = DecisionInput(
        verdict_match=True,
        citation_present=True,
        citation_verified=False,
        field_scope_safe=True,
        schema_valid=True,
    )
    bucket, reason = decide_bucket(inp)
    assert bucket == "pending"
    assert "citation_not_verified" in reason


def test_decide_bucket_pending_when_schema_invalid() -> None:
    inp = DecisionInput(
        verdict_match=True,
        citation_present=True,
        citation_verified=True,
        field_scope_safe=True,
        schema_valid=False,
    )
    bucket, reason = decide_bucket(inp)
    assert bucket == "pending"
    assert "schema_invalid" in reason
