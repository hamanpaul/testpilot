"""Inline tests for the one-shot alignment script.

Run with:
    uv run pytest tools/oneoff/2026-04-24-align-missing-rows/test_align_missing_rows.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the script importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
import align_missing_rows as ali  # noqa: E402


def clone_cases(cases: dict[str, ali.CaseInfo]) -> dict[str, ali.CaseInfo]:
    return {name: dict(info) for name, info in cases.items()}


def test_load_support_rows_returns_415_entries():
    rows = ali.load_support_rows()
    assert len(rows) == 415
    # Spot-check a known row
    assert rows[428]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert rows[428]["param"] == "Channel"


def test_scan_cases_returns_420_files():
    cases = ali.scan_cases()
    # Pre-action count; verify _template.yaml is excluded
    assert "_template.yaml" not in cases
    assert len(cases) == 420
    # Spot-check a known yaml
    assert cases["D115_getstationstats_accesspoint.yaml"]["source_row"] == 115


def test_filename_row_parsing():
    assert ali.filename_row("D068_foo.yaml") == 68
    assert ali.filename_row("D0428_bar.yaml") == 428
    assert ali.filename_row("_template.yaml") is None


def test_plan_validates_against_current_repo_state():
    rows = ali.load_support_rows()
    cases = ali.scan_cases()
    errors = ali.validate_plan(rows, cases)
    assert errors == [], "\n".join(errors)


def test_plan_rejects_rename_source_row_drift():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    cases["D068_discoverymethodenabled_accesspoint_fils.yaml"]["source_row"] = 999

    errors = ali.validate_plan(rows, cases)

    assert "rename source row drift: D068_discoverymethodenabled_accesspoint_fils.yaml" in errors


def test_plan_rejects_rename_source_id_drift():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    cases["D068_discoverymethodenabled_accesspoint_upr.yaml"]["id"] = "wifi-llapi-D999-wrong"

    errors = ali.validate_plan(rows, cases)

    assert "rename source id drift: D068_discoverymethodenabled_accesspoint_upr.yaml" in errors


def test_plan_rejects_move_source_row_and_id_drift():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    cases["D495_retrycount_ssid_stats_basic.yaml"]["source_row"] = 407
    cases["D495_retrycount_ssid_stats_basic.yaml"]["id"] = "wifi-llapi-D407-retrycount"

    errors = ali.validate_plan(rows, cases)

    assert "move source row drift: D495_retrycount_ssid_stats_basic.yaml" in errors
    assert "move source id drift: D495_retrycount_ssid_stats_basic.yaml" in errors


def test_plan_rejects_metadata_only_row_drift():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    cases["D495_retrycount_ssid_stats_verified.yaml"]["source_row"] = 495

    errors = ali.validate_plan(rows, cases)

    assert "metadata-only source row drift: D495_retrycount_ssid_stats_verified.yaml" in errors
