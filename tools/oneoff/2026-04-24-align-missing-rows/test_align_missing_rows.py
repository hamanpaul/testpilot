"""Inline tests for the one-shot alignment script.

Run with:
    uv run pytest tools/oneoff/2026-04-24-align-missing-rows/test_align_missing_rows.py -v
"""

from __future__ import annotations

import sys
from textwrap import dedent
from pathlib import Path
import pytest

# Make the script importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
import align_missing_rows as ali  # noqa: E402


def clone_cases(cases: dict[str, ali.CaseInfo]) -> dict[str, ali.CaseInfo]:
    return {name: dict(info) for name, info in cases.items()}


def test_metadata_edit_only_updates_id_and_source_row_for_realistic_yaml(tmp_path):
    dst = tmp_path / "synthetic.yaml"
    before = dedent(
        """\
        id: wifi-llapi-D115-getstationstats-accesspoint
        name: getStationStats() — WiFi.AccessPoint.{i}.
        version: '1.0'
        source:
          row: 115
          object: WiFi.AccessPoint.{i}.
          api: getStationStats()
        test_environment: 'Topology:

          - DUT: COM1 (B0, AP role)

          - Workbook H excerpt uses `hostapd_cli sta`, but current 0403 official baseline
          exposes `/tmp/wl0_hapd.conf` without a matching `/var/run/hostapd/wl0` control socket;
          `hostapd_cli` returns `wpa_ctrl_open: No such file or directory`.

          - Current single-STA baseline therefore uses driver `wl assoclist` as the stable
          runtime association oracle and verifies that getStationStats() returns the same
          STA MAC.

          '
        steps:
        - id: step1_assoc_precheck
          action: exec
          target: DUT
          command: wl -i wl0 assoclist | awk 'NR==1 {print "AssocMac=" $2}'
          capture: assoc_check
        - id: step2_getstationstats
          action: exec
          target: DUT
          command:
          - A="$(wl -i wl0 assoclist | awk 'NR==1 {print $2}')"
          - S="$(ubus-cli "WiFi.AccessPoint.1.getStationStats()" 2>/dev/null)"
          - M="$(printf '%s\\n' "$S" | grep -m1 'MACAddress = ' | cut -d'"' -f2)"
          - echo "StationStatsMac=$M"
          - printf '%s\\n' "$S" | grep -m1 'Active = ' | cut -d= -f2 | tr -d ' ,' | sed
            's/^/TopLevelActive=/'
          capture: stats_output
        verification_command:
        - wl -i wl0 assoclist
        - ubus-cli "WiFi.AccessPoint.1.getStationStats()" 2>&1 | grep -m1 'MACAddress =
          '
        - ubus-cli "WiFi.AccessPoint.1.getStationStats()" 2>&1 | grep -m1 'Active = '
        """
    )
    dst.write_text(before)

    expected_after = (
        before
        .replace(
            "id: wifi-llapi-D115-getstationstats-accesspoint",
            "id: wifi-llapi-D109-getstationstats",
            1,
        )
        .replace("  row: 115", "  row: 109", 1)
    )

    changes = ali._edit_metadata(dst, new_row=109, new_id="wifi-llapi-D109-getstationstats")

    assert changes == {
        "id": ["wifi-llapi-D115-getstationstats-accesspoint", "wifi-llapi-D109-getstationstats"],
        "source.row": [115, 109],
    }
    after = dst.read_text()
    assert after == expected_after


def test_metadata_edit_inserts_source_row_without_touching_later_nested_row(tmp_path):
    dst = tmp_path / "synthetic.yaml"
    before = dedent(
        """\
        id: wifi-llapi-D115-getstationstats-accesspoint
        name: getStationStats() — WiFi.AccessPoint.{i}.
        source:
          object: WiFi.AccessPoint.{i}.
          api: getStationStats()
        other_section:
          label: example
          row: 999
        """
    )
    dst.write_text(before)

    changes = ali._edit_metadata(dst, new_row=109, new_id=None)

    assert changes == {"source.row": [None, 109]}
    after = dst.read_text()
    assert "source:\n  row: 109\n  object: WiFi.AccessPoint.{i}.\n  api: getStationStats()" in after
    assert "other_section:\n  label: example\n  row: 999" in after
    assert "  row: 109\n" in after.split("other_section:", 1)[0]


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


def test_verify_post_state_returns_expected_summary(monkeypatch):
    rows = {row: {} for row in range(1, 416)}
    cases = {
        f"D{row:03d}_case.yaml": {"source_row": row, "id": f"wifi-llapi-D{row:03d}-case"}
        for row in rows
    }

    class DummyTemplate:
        def exists(self) -> bool:
            return True

    monkeypatch.setattr(ali, "load_support_rows", lambda: rows)
    monkeypatch.setattr(ali, "scan_cases", lambda: cases)
    monkeypatch.setattr(ali, "TEMPLATE_YAML", DummyTemplate())

    state = ali.verify_post_state()

    assert state == {
        "total_cases": 415,
        "incl_template": 416,
        "support_rows": 415,
        "canonical_coverage": 415,
        "liberal_missing": [],
    }


def test_verify_post_state_counts_duplicate_row_coverage_once(monkeypatch):
    rows = {row: {} for row in range(1, 416)}

    class Cases(dict):
        def __len__(self) -> int:  # pragma: no cover - test helper
            return 415

    cases = Cases(
        {
            "D001_alpha.yaml": {"source_row": 1, "id": "wifi-llapi-D001-alpha"},
            "D001_beta.yaml": {"source_row": 1, "id": "wifi-llapi-D001-beta"},
            **{
                f"D{row:03d}_case.yaml": {"source_row": row, "id": f"wifi-llapi-D{row:03d}-case"}
                for row in range(2, 416)
            },
        }
    )

    class DummyTemplate:
        def exists(self) -> bool:
            return True

    monkeypatch.setattr(ali, "load_support_rows", lambda: rows)
    monkeypatch.setattr(ali, "scan_cases", lambda: cases)
    monkeypatch.setattr(ali, "TEMPLATE_YAML", DummyTemplate())

    state = ali.verify_post_state()

    assert state["canonical_coverage"] == 415


def test_verify_post_state_raises_with_missing_rows(monkeypatch):
    cases = {
        "D001_alpha.yaml": {"source_row": 1, "id": "wifi-llapi-D001-alpha"},
        "D500_other.yaml": {"source_row": 999, "id": "wifi-llapi-D500-other"},
    }

    class DummyTemplate:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(ali, "load_support_rows", lambda: {1: {}, 2: {}})
    monkeypatch.setattr(ali, "scan_cases", lambda: cases)
    monkeypatch.setattr(ali, "TEMPLATE_YAML", DummyTemplate())

    with pytest.raises(ali.PostStateError) as excinfo:
        ali.verify_post_state()

    message = str(excinfo.value)
    assert "liberal-missing rows: [2]" in message
    assert "canonical coverage = 1/415" in message
    assert "'liberal_missing': [2]" in message


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
