"""Tests for the MD / JSON report projectors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from testpilot.reporting.reporter import (
    IReporter,
    JsonReporter,
    MarkdownReporter,
    generate_reports,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_META: dict[str, Any] = {
    "title": "WiFi LLAPI Run",
    "date": "2025-07-15",
    "tester": "bot",
    "testbed": "lab-01",
    "dut_model": "AX-9000",
    "firmware_version": "1.2.3",
    "plugin": "wifi_llapi",
}

_CASES: list[dict[str, Any]] = [
    {
        "case_id": "D001",
        "source_row": 5,
        "executed_test_command": "wl -i wl0 status",
        "command_output": "Status: connected",
        "result_5g": "pass",
        "result_6g": "fail",
        "result_24g": "pass",
        "comment": "6G radio off",
        "tester": "bot",
    },
    {
        "case_id": "D002",
        "source_row": 6,
        "executed_test_command": "wl -i wl1 assoclist",
        "command_output": "AA:BB:CC:DD:EE:FF",
        "result_5g": "pass",
        "result_6g": "not_supported",
        "result_24g": "pass",
        "comment": "",
        "tester": "bot",
    },
]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_markdown_reporter_satisfies_protocol() -> None:
    reporter: IReporter = MarkdownReporter()
    assert callable(getattr(reporter, "generate", None))


def test_json_reporter_satisfies_protocol() -> None:
    reporter: IReporter = JsonReporter()
    assert callable(getattr(reporter, "generate", None))


# ---------------------------------------------------------------------------
# MarkdownReporter
# ---------------------------------------------------------------------------


class TestMarkdownReporter:
    def test_generates_valid_markdown_with_summary_table(self, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        result = MarkdownReporter().generate(_CASES, _META, out)
        assert result == out
        text = out.read_text(encoding="utf-8")
        # Header
        assert "# WiFi LLAPI Run" in text
        assert "**Date**: 2025-07-15" in text
        assert "**Tester**: bot" in text
        # Summary table
        assert "| case_id |" in text
        assert "| D001 |" in text
        assert "| D002 |" in text

    def test_case_details_collapsible(self, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        MarkdownReporter().generate(_CASES, _META, out)
        text = out.read_text(encoding="utf-8")
        assert "<details><summary>D001</summary>" in text
        assert "wl -i wl0 status" in text

    def test_empty_cases(self, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        MarkdownReporter().generate([], _META, out)
        text = out.read_text(encoding="utf-8")
        assert "# WiFi LLAPI Run" in text
        # Table header present, but no data rows beyond header/sep
        assert "| case_id |" in text

    def test_missing_optional_fields(self, tmp_path: Path) -> None:
        minimal: list[dict[str, Any]] = [{"case_id": "D097", "source_row": 99}]
        out = tmp_path / "report.md"
        MarkdownReporter().generate(minimal, _META, out)
        text = out.read_text(encoding="utf-8")
        assert "D097" in text

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        out = tmp_path / "sub" / "dir" / "report.md"
        MarkdownReporter().generate(_CASES, _META, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# JsonReporter
# ---------------------------------------------------------------------------


class TestJsonReporter:
    def test_generates_valid_json_structure(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        result = JsonReporter().generate(_CASES, _META, out)
        assert result == out
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert "meta" in payload
        assert "cases" in payload
        assert "summary" in payload

    def test_summary_counts(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        JsonReporter().generate(_CASES, _META, out)
        summary = json.loads(out.read_text(encoding="utf-8"))["summary"]
        assert summary["total_cases"] == 2
        assert summary["pass"] == 4
        assert summary["fail"] == 1
        assert summary["not_supported"] == 1
        assert summary["error"] == 0

    def test_meta_preserved(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        JsonReporter().generate(_CASES, _META, out)
        meta = json.loads(out.read_text(encoding="utf-8"))["meta"]
        assert meta["tester"] == "bot"
        assert meta["dut_model"] == "AX-9000"

    def test_empty_cases(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        JsonReporter().generate([], _META, out)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["cases"] == []
        assert payload["summary"]["total_cases"] == 0

    def test_missing_optional_fields(self, tmp_path: Path) -> None:
        minimal: list[dict[str, Any]] = [{"case_id": "D097"}]
        out = tmp_path / "report.json"
        JsonReporter().generate(minimal, _META, out)
        cases = json.loads(out.read_text(encoding="utf-8"))["cases"]
        assert cases[0]["case_id"] == "D097"


# ---------------------------------------------------------------------------
# generate_reports()
# ---------------------------------------------------------------------------


class TestGenerateReports:
    def test_creates_both_formats(self, tmp_path: Path) -> None:
        paths = generate_reports(_CASES, _META, tmp_path)
        assert len(paths) == 2
        suffixes = {p.suffix for p in paths}
        assert suffixes == {".md", ".json"}
        assert all(p.exists() for p in paths)

    def test_single_format(self, tmp_path: Path) -> None:
        paths = generate_reports(_CASES, _META, tmp_path, formats=("json",))
        assert len(paths) == 1
        assert paths[0].suffix == ".json"

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported report format"):
            generate_reports(_CASES, _META, tmp_path, formats=("pdf",))

    def test_empty_cases_both_formats(self, tmp_path: Path) -> None:
        paths = generate_reports([], _META, tmp_path)
        assert len(paths) == 2
        assert all(p.exists() for p in paths)
