"""YAML edit boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from testpilot.audit.verify_edit import (
    ALLOWED_PATH_PREFIXES,
    BoundaryViolation,
    append_verify_edit_log,
    check_boundary,
    diff_paths,
    file_sha256,
    is_path_allowed,
)

_BASE_YAML = """
id: wifi-llapi-D366-srgbsscolorbitmap
name: SRGBSSColorBitmap
version: '1.1'
source:
  row: 366
  object: WiFi.Radio.{i}.IEEE80211ax.
  api: SRGBSSColorBitmap
bands: [5g, 6g, 2.4g]
steps:
  - id: s1
    action: exec
    target: DUT
    command: ubus-cli "WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap?"
    capture: r1
pass_criteria:
  - field: r1.SRGBSSColorBitmap
    operator: equals
    value: ''
verification_command:
  - ubus-cli "WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap?"
"""


# ---------------------------------------------------------------------------
# is_path_allowed
# ---------------------------------------------------------------------------


def test_path_allowed_for_pass_criteria_change():
    assert is_path_allowed("pass_criteria[0].value")
    assert is_path_allowed("pass_criteria[0].field")
    assert is_path_allowed("pass_criteria[2].operator")


def test_path_allowed_for_steps_command_change():
    assert is_path_allowed("steps[0].command")
    assert is_path_allowed("steps[3].capture")


def test_path_allowed_for_verification_command():
    assert is_path_allowed("verification_command")
    assert is_path_allowed("verification_command[0]")
    assert is_path_allowed("verification_command[1]")


def test_path_disallowed_for_source_row():
    assert not is_path_allowed("source.row")


def test_path_disallowed_for_source_object():
    assert not is_path_allowed("source.object")


def test_path_disallowed_for_id():
    assert not is_path_allowed("id")


def test_path_disallowed_for_name():
    assert not is_path_allowed("name")


def test_path_disallowed_for_topology():
    assert not is_path_allowed("topology.devices.DUT.role")


def test_path_disallowed_for_steps_id():
    # steps[*].id is NOT in the allowlist (only .command and .capture are)
    assert not is_path_allowed("steps[0].id")


def test_path_disallowed_for_steps_action():
    assert not is_path_allowed("steps[0].action")


def test_path_disallowed_for_steps_command_suffix():
    assert not is_path_allowed("steps[0].command_extra")
    assert not is_path_allowed("steps[0].command.nested")


# ---------------------------------------------------------------------------
# diff_paths
# ---------------------------------------------------------------------------


def test_diff_paths_detects_value_change():
    before = "x: 1\n"
    after = "x: 2\n"
    assert diff_paths(before, after) == {"x"}


def test_diff_paths_detects_nested_change():
    before = "source:\n  row: 1\n"
    after = "source:\n  row: 2\n"
    assert diff_paths(before, after) == {"source.row"}


def test_diff_paths_detects_list_item_change():
    before = "items:\n  - a\n  - b\n"
    after = "items:\n  - a\n  - c\n"
    assert diff_paths(before, after) == {"items[1]"}


def test_diff_paths_detects_added_key():
    before = "x: 1\n"
    after = "x: 1\ny: 2\n"
    assert diff_paths(before, after) == {"y"}


def test_diff_paths_detects_removed_key():
    before = "x: 1\ny: 2\n"
    after = "x: 1\n"
    assert diff_paths(before, after) == {"y"}


def test_diff_paths_detects_removed_null_key():
    before = "x: null\n"
    after = ""
    assert diff_paths(before, after) == {"x"}


def test_diff_paths_detects_added_null_key():
    before = ""
    after = "x: null\n"
    assert diff_paths(before, after) == {"x"}


def test_diff_paths_no_change():
    assert diff_paths(_BASE_YAML, _BASE_YAML) == set()


# ---------------------------------------------------------------------------
# check_boundary
# ---------------------------------------------------------------------------


def test_check_boundary_passes_pass_criteria_only_change(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    after.write_text(_BASE_YAML.replace("value: ''", "value: '1'"))
    diffs = check_boundary(before, after)
    assert "pass_criteria[0].value" in diffs


def test_check_boundary_passes_verification_command_change(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    after.write_text(
        _BASE_YAML.replace(
            'ubus-cli "WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap?"',
            'ubus-cli "WiFi.Radio.2.IEEE80211ax.SRGBSSColorBitmap?"',
        )
    )
    # should not raise — both steps[0].command and verification_command[0] changed
    check_boundary(before, after)


def test_check_boundary_passes_steps_command_change(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    after.write_text(_BASE_YAML.replace("capture: r1", "capture: r2"))
    check_boundary(before, after)


def test_check_boundary_rejects_source_row_change(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    after.write_text(_BASE_YAML.replace("row: 366", "row: 412"))
    with pytest.raises(
        BoundaryViolation,
        match=r"source\.row.*steps\[N\]\.\(command\|capture\)",
    ):
        check_boundary(before, after)


def test_check_boundary_rejects_step_addition(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    extra_step = """
  - id: s2
    action: exec
    target: DUT
    command: ubus-cli foo
    capture: r2
"""
    after.write_text(
        _BASE_YAML.replace(
            "    capture: r1\n",
            f"    capture: r1\n{extra_step}",
        )
    )
    with pytest.raises(BoundaryViolation, match="steps"):
        check_boundary(before, after)


def test_check_boundary_rejects_minimal_step_addition(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    extra_step = """
  - command: ubus-cli foo
    capture: r2
"""
    after.write_text(
        _BASE_YAML.replace(
            "    capture: r1\n",
            f"    capture: r1\n{extra_step}",
        )
    )
    with pytest.raises(BoundaryViolation, match="steps"):
        check_boundary(before, after)


def test_check_boundary_rejects_pass_criteria_addition(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    extra_criteria = """
  - field: r1.extra
    operator: equals
    value: '1'
"""
    after.write_text(
        _BASE_YAML.replace(
            "    value: ''\n",
            f"    value: ''\n{extra_criteria}",
        )
    )
    with pytest.raises(BoundaryViolation, match="pass_criteria"):
        check_boundary(before, after)


def test_check_boundary_rejects_step_removal(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(
        _BASE_YAML.replace(
            "    capture: r1\n",
            "    capture: r1\n"
            "  - id: s2\n"
            "    action: exec\n"
            "    target: DUT\n"
            "    command: ubus-cli foo\n"
            "    capture: r2\n",
        )
    )
    after.write_text(_BASE_YAML)
    with pytest.raises(BoundaryViolation, match="steps"):
        check_boundary(before, after)


def test_check_boundary_rejects_pass_criteria_removal(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(
        _BASE_YAML.replace(
            "    value: ''\n",
            "    value: ''\n"
            "  - field: r1.extra\n"
            "    operator: equals\n"
            "    value: '1'\n",
        )
    )
    after.write_text(_BASE_YAML)
    with pytest.raises(BoundaryViolation, match="pass_criteria"):
        check_boundary(before, after)


def test_check_boundary_rejects_name_change(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    after.write_text(_BASE_YAML.replace("name: SRGBSSColorBitmap", "name: Changed"))
    with pytest.raises(BoundaryViolation, match="name"):
        check_boundary(before, after)


def test_check_boundary_no_diff_returns_empty_set(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(_BASE_YAML)
    after.write_text(_BASE_YAML)
    assert check_boundary(before, after) == set()


# ---------------------------------------------------------------------------
# file_sha256
# ---------------------------------------------------------------------------


def test_file_sha256_deterministic(tmp_path):
    f = tmp_path / "test.yaml"
    f.write_bytes(b"hello world\n")
    h1 = file_sha256(f)
    h2 = file_sha256(f)
    assert h1 == h2
    assert len(h1) == 64  # hex SHA-256


def test_file_sha256_differs_for_different_content(tmp_path):
    f1 = tmp_path / "a.yaml"
    f2 = tmp_path / "b.yaml"
    f1.write_bytes(b"content A")
    f2.write_bytes(b"content B")
    assert file_sha256(f1) != file_sha256(f2)


# ---------------------------------------------------------------------------
# append_verify_edit_log
# ---------------------------------------------------------------------------


def test_append_verify_edit_log_creates_file(tmp_path):
    log = tmp_path / "runs" / "r1" / "wifi_llapi" / "verify_edit_log.jsonl"
    append_verify_edit_log(
        log_path=log,
        case="wifi-llapi-D366",
        yaml_path=Path("plugins/wifi_llapi/cases/D366.yaml"),
        sha_before="abc123",
        sha_after_proposed="def456",
        diff_paths_set={"pass_criteria[0].value"},
    )
    assert log.exists()
    entry = json.loads(log.read_text().strip())
    assert entry["case"] == "wifi-llapi-D366"
    assert entry["yaml_sha256_before"] == "abc123"
    assert entry["yaml_sha256_after_proposed"] == "def456"
    assert entry["diff_paths"] == ["pass_criteria[0].value"]
    assert "ts" in entry


def test_append_verify_edit_log_appends(tmp_path):
    log = tmp_path / "verify_edit_log.jsonl"
    kwargs = dict(
        log_path=log,
        case="c1",
        yaml_path=Path("x.yaml"),
        sha_before="a",
        sha_after_proposed="b",
        diff_paths_set=set(),
    )
    append_verify_edit_log(**kwargs)
    append_verify_edit_log(**kwargs)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2


def test_append_verify_edit_log_diff_paths_sorted(tmp_path):
    log = tmp_path / "verify_edit_log.jsonl"
    append_verify_edit_log(
        log_path=log,
        case="c1",
        yaml_path=Path("x.yaml"),
        sha_before="a",
        sha_after_proposed="b",
        diff_paths_set={"pass_criteria[1].value", "pass_criteria[0].value"},
    )
    entry = json.loads(log.read_text().strip())
    assert entry["diff_paths"] == sorted(entry["diff_paths"])


# ---------------------------------------------------------------------------
# ALLOWED_PATH_PREFIXES exported constant
# ---------------------------------------------------------------------------


def test_allowed_path_prefixes_contains_expected():
    assert "steps[*].command" in ALLOWED_PATH_PREFIXES
    assert "steps[*].capture" in ALLOWED_PATH_PREFIXES
    assert "pass_criteria[" in ALLOWED_PATH_PREFIXES
    assert "verification_command" in ALLOWED_PATH_PREFIXES
    assert "verification_command[*]" in ALLOWED_PATH_PREFIXES
