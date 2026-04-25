"""Inline tests for the one-shot alignment script.

Run with:
    uv run pytest tools/oneoff/2026-04-24-align-missing-rows/test_align_missing_rows.py -v
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Make the script importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
import align_missing_rows as ali  # noqa: E402


def clone_cases(cases: dict[str, ali.CaseInfo]) -> dict[str, ali.CaseInfo]:
    return {name: dict(info) for name, info in cases.items()}


def test_metadata_edit_preserves_multiline_test_environment(tmp_path):
    src = ali.CASES_DIR / "D115_getstationstats_accesspoint.yaml"
    dst = tmp_path / "copy.yaml"
    shutil.copy2(src, dst)

    before = dst.read_text()
    assert "Workbook row 109 is getStationStats()" in before, \
        "fixture sanity: multiline test_environment block must be present"

    changes = ali._edit_metadata(dst, new_row=109, new_id="wifi-llapi-D109-getstationstats")

    assert changes == {
        "id": ["wifi-llapi-D115-getstationstats-accesspoint", "wifi-llapi-D109-getstationstats"],
        "source.row": [115, 109],
    }
    after = dst.read_text()
    assert "Workbook row 109 is getStationStats()" in after, \
        "round-trip must preserve multiline test_environment block"
    assert "row: 109" in after
    assert "wifi-llapi-D109-getstationstats" in after


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


def test_plan_rejects_metadata_only_id_drift():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    cases["D495_retrycount_ssid_stats_verified.yaml"]["id"] = "wifi-llapi-d495-retrycount-wrong"

    errors = ali.validate_plan(rows, cases)

    assert "metadata-only source id drift: D495_retrycount_ssid_stats_verified.yaml" in errors


def test_plan_rejects_delete_row_drift():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    cases["D096_uapsdenable.yaml"]["source_row"] = 999

    errors = ali.validate_plan(rows, cases)

    assert "delete source row drift: D096_uapsdenable.yaml" in errors


def test_plan_rejects_delete_row_still_in_support_set():
    rows = ali.load_support_rows()
    cases = clone_cases(ali.scan_cases())
    rows[96] = {
        "object": "WiFi.AccessPoint.{i}.",
        "type": "boolean",
        "param": "UAPSDEnable",
        "hlapi": "ubus-cli WiFi.AccessPoint.{i}.UAPSDEnable=0",
    }

    errors = ali.validate_plan(rows, cases)

    assert "delete stale row still in Support set: D096_uapsdenable.yaml" in errors


def test_main_fails_when_plan_validation_errors_exist(monkeypatch, capsys):
    support_rows = {
        428: {
            "object": "WiFi.AccessPoint.{i}.Neighbour.{i}.",
            "type": "unsignedInt",
            "param": "Channel",
            "hlapi": 'ubus-cli "WiFi.AccessPoint.{i}.Neighbour.{i}.Channel=36"',
        }
    }
    cases = {
        "D115_getstationstats_accesspoint.yaml": {
            "source_row": 115,
            "id": "wifi-llapi-D115-getstationstats-accesspoint",
        }
    }

    monkeypatch.setattr(ali, "load_support_rows", lambda: support_rows)
    monkeypatch.setattr(ali, "scan_cases", lambda: cases)
    monkeypatch.setattr(
        ali,
        "validate_plan",
        lambda rows, scanned: [
            "rename source missing: D068_discoverymethodenabled_accesspoint_fils.yaml",
            "delete source row drift: D096_uapsdenable.yaml",
        ],
    )

    rc = ali.main([])
    captured = capsys.readouterr()

    assert rc != 0
    assert "plan validation failed" in captured.err
    assert "rename source missing: D068_discoverymethodenabled_accesspoint_fils.yaml" in captured.err
    assert "delete source row drift: D096_uapsdenable.yaml" in captured.err
    assert "mode:" not in captured.out
