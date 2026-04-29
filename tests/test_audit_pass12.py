"""Tests for Pass 1/2 main flow (pass12.py) and 'audit pass12' CLI command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import testpilot.audit.cli as audit_cli
from testpilot.audit import bucket, manifest
from testpilot.audit.extractor import ExtractedCommand
from testpilot.audit.pass12 import PassResult, run_pass12_for_case
from testpilot.audit.runner_facade import AuditCaseResult
from testpilot.audit.workbook_index import WorkbookRow
from testpilot.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workbook_row(
    result_5g: str = "Pass",
    result_6g: str = "Pass",
    result_24g: str = "Pass",
    test_steps: str = "",
    command_output: str = "",
) -> WorkbookRow:
    return WorkbookRow(
        raw_row_index=2,
        object_path="WiFi.Radio.{i}.",
        api="GetRadioStats",
        test_steps=test_steps,
        command_output=command_output,
        result_5g=result_5g,
        result_6g=result_6g,
        result_24g=result_24g,
    )


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["git", "init", "-q"], cwd=str(path))
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=str(path))
    subprocess.check_call(["git", "config", "user.name", "Test User"], cwd=str(path))
    (path / "README.md").write_text("repo\n", encoding="utf-8")
    subprocess.check_call(["git", "add", "README.md"], cwd=str(path))
    subprocess.check_call(["git", "commit", "-qm", "init"], cwd=str(path))
    return path


# ---------------------------------------------------------------------------
# Unit tests for run_pass12_for_case
# ---------------------------------------------------------------------------


def test_pass1_match_returns_confirmed(tmp_path: Path) -> None:
    """Pass 1 verdict matches workbook → bucket=confirmed, pass2_verdict_match=None."""
    facade_result = AuditCaseResult(
        case_id="D001",
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={"json_report_path": "/tmp/report.json"},
        error=None,
    )
    wb_row = _make_workbook_row(result_5g="Pass", result_6g="Pass", result_24g="Pass")

    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        result = run_pass12_for_case(
            plugin="wifi_llapi",
            case_id="D001",
            workbook_row=wb_row,
            run_dir=tmp_path,
            repo_root=tmp_path,
        )

    assert result.bucket == "confirmed"
    assert result.pass1_verdict_match is True
    assert result.pass2_verdict_match is None
    assert result.reason == "pass1_verdict_match"
    assert result.extracted_commands == []
    assert result.pass1_artifacts["artifacts"] == {"json_report_path": "/tmp/report.json"}


def test_pass1_mismatch_with_extract_returns_needs_pass3(tmp_path: Path) -> None:
    """Pass 1 mismatch + commands extracted → needs_pass3, pass2_verdict_match=None."""
    facade_result = AuditCaseResult(
        case_id="D366",
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={},
        error=None,
    )
    wb_row = _make_workbook_row(
        result_5g="Fail",
        result_6g="Fail",
        result_24g="Fail",
        test_steps="`wl -i wl0 sr_config srg_obsscolorbmp`",
        command_output="",
    )

    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        result = run_pass12_for_case(
            plugin="wifi_llapi",
            case_id="D366",
            workbook_row=wb_row,
            run_dir=tmp_path,
            repo_root=tmp_path,
        )

    assert result.bucket == "needs_pass3"
    assert result.pass1_verdict_match is False
    # Phase B: Pass 2 never reruns
    assert result.pass2_verdict_match is None
    assert result.reason == "pass2_extract_only_no_rerun"
    assert result.extracted_commands
    assert any("wl" in c.command for c in result.extracted_commands)


def test_pass1_mismatch_no_extract_returns_needs_pass3(tmp_path: Path) -> None:
    """Pass 1 mismatch + no extractable commands → needs_pass3, reason=pass2_no_extract."""
    facade_result = AuditCaseResult(
        case_id="D369",
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={},
        error=None,
    )
    wb_row = _make_workbook_row(
        result_5g="Fail",
        result_6g="Fail",
        result_24g="Fail",
        test_steps="設定 SRG bitmap 並驗證 driver 是否拉起",  # Chinese prose, no commands
        command_output="",
    )

    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        result = run_pass12_for_case(
            plugin="wifi_llapi",
            case_id="D369",
            workbook_row=wb_row,
            run_dir=tmp_path,
            repo_root=tmp_path,
        )

    assert result.bucket == "needs_pass3"
    assert result.pass1_verdict_match is False
    assert result.pass2_verdict_match is None
    assert result.reason == "pass2_no_extract"
    assert result.extracted_commands == []


def test_pass1_error_returns_block(tmp_path: Path) -> None:
    """Facade error → bucket=block with reason containing the error."""
    facade_result = AuditCaseResult(
        case_id="D001",
        verdict_per_band={},
        capture={},
        artifacts={},
        error="orchestrator error: connection refused",
    )
    wb_row = _make_workbook_row()

    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        result = run_pass12_for_case(
            plugin="wifi_llapi",
            case_id="D001",
            workbook_row=wb_row,
            run_dir=tmp_path,
            repo_root=tmp_path,
        )

    assert result.bucket == "block"
    assert result.pass1_verdict_match is False
    assert result.pass2_verdict_match is None
    assert "pass1_error" in result.reason
    assert "connection refused" in result.reason


def test_pass2_verdict_match_is_none_even_with_extract(tmp_path: Path) -> None:
    """Ensure pass2_verdict_match stays None (Phase B never reruns Pass 2)."""
    facade_result = AuditCaseResult(
        case_id="D010",
        verdict_per_band={"5g": "Pass"},
        capture={},
        artifacts={},
        error=None,
    )
    wb_row = _make_workbook_row(
        result_5g="Fail",
        result_6g="",
        result_24g="",
        test_steps="wl -i wl0 channel",
    )

    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        result = run_pass12_for_case(
            plugin="wifi_llapi",
            case_id="D010",
            workbook_row=wb_row,
            run_dir=tmp_path,
            repo_root=tmp_path,
        )

    assert result.pass2_verdict_match is None


def test_run_pass12_for_case_forwards_repo_root(tmp_path: Path) -> None:
    """run_pass12_for_case must forward the explicit repo_root into the facade layer."""
    facade_result = AuditCaseResult(
        case_id="D013",
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={},
        error=None,
    )
    wb_row = _make_workbook_row()

    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result) as run_facade:
        result = run_pass12_for_case(
            plugin="wifi_llapi",
            case_id="D013",
            workbook_row=wb_row,
            run_dir=tmp_path,
            repo_root=tmp_path,
        )

    run_facade.assert_called_once_with("wifi_llapi", "D013", tmp_path)
    assert result.bucket == "confirmed"


# ---------------------------------------------------------------------------
# CLI tests for `audit pass12`
# ---------------------------------------------------------------------------


def _make_minimal_xlsx(path: Path) -> None:
    """Write a minimal but valid .xlsx with the expected header row."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Wifi_LLAPI"
    ws.append(["Object", "API", "Test Steps", "Command Output", "5G", "6G", "2.4G"])
    wb.save(str(path))


def _create_audit_run(
    root: Path,
    plugin: str,
    case_ids: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Helper: init an audit run and return RID."""
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})
    workbook = root / "audit" / "workbooks" / f"{plugin}.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    _make_minimal_xlsx(workbook)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--root", str(root), "audit", "init", plugin, "--cases", ",".join(case_ids)],
    )
    assert result.exit_code == 0, result.output
    return result.output.strip()


def test_audit_pass12_happy_path_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Happy path: confirmed case writes pass1_baseline.json and bucket entry."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D001"

    # Create case YAML
    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_getradiostats.yaml").write_text(
        "id: wifi-llapi-D001\nsource:\n  object: WiFi.Radio.{i}.\n  api: GetRadioStats\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)

    # Place workbook snapshot
    snapshot = root / "audit" / "runs" / rid / plugin / "workbook_snapshot.xlsx"
    wb_index = {
        ("WiFi.Radio.{i}", "GetRadioStats"): [
            WorkbookRow(
                raw_row_index=2,
                object_path="WiFi.Radio.{i}.",
                api="GetRadioStats",
                test_steps="",
                command_output="",
                result_5g="Pass",
                result_6g="Pass",
                result_24g="Pass",
            )
        ]
    }

    facade_result = AuditCaseResult(
        case_id=case_id,
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={"json_report_path": "/tmp/pass1.json"},
        error=None,
    )

    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: wb_index)
    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        runner = CliRunner()
        result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[confirmed]" in result.output
    assert case_id in result.output

    # Verify artifact written
    pass1_path = root / "audit" / "runs" / rid / plugin / "case" / case_id / "pass1_baseline.json"
    assert pass1_path.is_file()
    data = json.loads(pass1_path.read_text(encoding="utf-8"))
    assert data["case_id"] == case_id
    assert data["pass1_verdict_match"] is True
    assert data["bucket"] == "confirmed"
    assert data["pass1_artifacts"]["artifacts"] == {"json_report_path": "/tmp/pass1.json"}

    # No pass2 file when no commands extracted
    pass2_path = pass1_path.parent / "pass2_workbook.json"
    assert not pass2_path.exists()

    # Bucket entry
    entries = bucket.list_bucket(
        root / "audit" / "runs" / rid / plugin, "confirmed"
    )
    assert any(e["case_id"] == case_id for e in entries)


def test_audit_pass12_writes_pass2_artifact_when_commands_extracted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mismatch + extracted commands → needs_pass3 + pass2_workbook.json written."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D366"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_srg.yaml").write_text(
        "id: wifi-llapi-D366\nsource:\n  object: WiFi.Radio.{i}.IEEE80211ax.\n  api: SRGBSSColorBitmap\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)

    wb_index = {
        ("WiFi.Radio.{i}.IEEE80211ax", "SRGBSSColorBitmap"): [
            WorkbookRow(
                raw_row_index=5,
                object_path="WiFi.Radio.{i}.IEEE80211ax.",
                api="SRGBSSColorBitmap",
                test_steps="`wl -i wl0 sr_config srg_obsscolorbmp`",
                command_output="",
                result_5g="Fail",
                result_6g="Fail",
                result_24g="Fail",
            )
        ]
    }

    facade_result = AuditCaseResult(
        case_id=case_id,
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={},
        error=None,
    )

    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: wb_index)
    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        runner = CliRunner()
        result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[needs_pass3]" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    case_dir = run_dir / "case" / case_id
    assert (case_dir / "pass1_baseline.json").is_file()
    assert (case_dir / "pass2_workbook.json").is_file()

    p2 = json.loads((case_dir / "pass2_workbook.json").read_text(encoding="utf-8"))
    assert p2["case_id"] == case_id
    assert p2["pass2_verdict_match"] is None
    assert p2["extracted_commands"]
    assert any("wl" in cmd["command"] for cmd in p2["extracted_commands"])

    entries = bucket.list_bucket(run_dir, "needs_pass3")
    assert any(e["case_id"] == case_id for e in entries)


def test_audit_pass12_workbook_row_missing_lands_in_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case whose (object, api) key is absent from workbook → block bucket."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D005"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_unknown.yaml").write_text(
        "id: wifi-llapi-D005\nsource:\n  object: WiFi.Radio.{i}.Unknown.\n  api: NoSuchAPI\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)

    # Empty workbook index: key not present
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "workbook_row_missing" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "block")
    assert any(
        e["case_id"] == case_id and e["reason"] == "workbook_row_missing"
        for e in entries
    )
    assert not (run_dir / "case" / case_id).exists()


def test_audit_pass12_workbook_row_ambiguous_lands_in_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case whose (object, api) maps to multiple workbook rows → block bucket."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D007"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_dup.yaml").write_text(
        "id: wifi-llapi-D007\nsource:\n  object: WiFi.Radio.{i}.\n  api: DupAPI\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)

    row_a = WorkbookRow(
        raw_row_index=10,
        object_path="WiFi.Radio.{i}.",
        api="DupAPI",
        test_steps="",
        command_output="",
        result_5g="Pass",
        result_6g="Pass",
        result_24g="Pass",
    )
    row_b = WorkbookRow(
        raw_row_index=11,
        object_path="WiFi.Radio.{i}.",
        api="DupAPI",
        test_steps="",
        command_output="",
        result_5g="Fail",
        result_6g="Fail",
        result_24g="Fail",
    )
    wb_index = {("WiFi.Radio.{i}", "DupAPI"): [row_a, row_b]}

    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: wb_index)

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "workbook_row_ambiguous" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "block")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert matched
    assert matched[0]["reason"] == "workbook_row_ambiguous"
    assert set(matched[0]["candidate_row_indices"]) == {10, 11}


def test_audit_pass12_case_yaml_ambiguous_lands_in_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple matching case YAML files should block instead of picking one silently."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D009"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_one.yaml").write_text(
        "id: wifi-llapi-D009\nsource:\n  object: WiFi.Radio.{i}.\n  api: GetRadioStats\n",
        encoding="utf-8",
    )
    (cases_dir / f"{case_id}_two.yaml").write_text(
        "id: wifi-llapi-D009\nsource:\n  object: WiFi.Radio.{i}.\n  api: GetRadioStats\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "case_yaml_ambiguous" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "block")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert matched
    assert matched[0]["reason"] == "case_yaml_ambiguous"
    assert set(matched[0]["candidate_files"]) == {f"{case_id}_one.yaml", f"{case_id}_two.yaml"}
    assert not (run_dir / "case" / case_id).exists()


def test_audit_pass12_case_yaml_not_found_lands_in_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing case YAML should block and avoid creating an empty case directory."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D010"

    (root / "plugins" / plugin / "cases").mkdir(parents=True, exist_ok=True)
    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "case_yaml_not_found" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "block")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert matched
    assert matched[0]["reason"] == "case_yaml_not_found"
    assert not (run_dir / "case" / case_id).exists()


def test_audit_pass12_cases_dir_missing_lands_in_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing plugin cases directory should block all manifest cases on Python 3.11+."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D010"

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "cases_dir_not_found" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "block")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert matched
    assert matched[0]["reason"] == "cases_dir_not_found"


def test_audit_pass12_cli_writes_block_artifact_for_pass1_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Facade-level pass1 error should still write pass1_baseline.json and a block bucket entry."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D011"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_error.yaml").write_text(
        "id: wifi-llapi-D011\nsource:\n  object: WiFi.Radio.{i}.\n  api: GetRadioStats\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)
    wb_index = {
        ("WiFi.Radio.{i}", "GetRadioStats"): [
            WorkbookRow(
                raw_row_index=2,
                object_path="WiFi.Radio.{i}.",
                api="GetRadioStats",
                test_steps="",
                command_output="",
                result_5g="Pass",
                result_6g="Pass",
                result_24g="Pass",
            )
        ]
    }

    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: wb_index)
    error_result = AuditCaseResult(
        case_id=case_id,
        verdict_per_band={},
        capture={},
        artifacts={"json_report_path": "/tmp/error.json"},
        error="orchestrator error: boom",
    )

    with patch("testpilot.audit.pass12._run_facade", return_value=error_result):
        runner = CliRunner()
        result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "pass1_error" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    case_dir = run_dir / "case" / case_id
    baseline = json.loads((case_dir / "pass1_baseline.json").read_text(encoding="utf-8"))
    assert baseline["bucket"] == "block"
    assert "pass1_error" in baseline["reason"]
    assert baseline["pass1_artifacts"]["artifacts"] == {"json_report_path": "/tmp/error.json"}

    entries = bucket.list_bucket(run_dir, "block")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert matched
    assert "pass1_error" in matched[0]["reason"]


def test_audit_pass12_case_yaml_missing_source_lands_in_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """YAML without a mapping `source` should produce a dedicated block reason."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D014"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_missing_source.yaml").write_text(
        "id: wifi-llapi-D014\nsource: invalid\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert result.exit_code == 0, result.output
    assert "[block]" in result.output
    assert "case_yaml_missing_source" in result.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "block")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert matched
    assert matched[0]["reason"] == "case_yaml_missing_source"
    assert not (run_dir / "case" / case_id).exists()


def test_audit_pass12_is_idempotent_for_bucket_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-running pass12 for the same RID should not duplicate bucket entries."""
    root = init_repo(tmp_path / "repo")
    plugin = "wifi_llapi"
    case_id = "D012"

    cases_dir = root / "plugins" / plugin / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{case_id}_repeat.yaml").write_text(
        "id: wifi-llapi-D012\nsource:\n  object: WiFi.Radio.{i}.\n  api: GetRadioStats\n",
        encoding="utf-8",
    )

    rid = _create_audit_run(root, plugin, [case_id], monkeypatch)
    wb_index = {
        ("WiFi.Radio.{i}", "GetRadioStats"): [
            WorkbookRow(
                raw_row_index=2,
                object_path="WiFi.Radio.{i}.",
                api="GetRadioStats",
                test_steps="",
                command_output="",
                result_5g="Pass",
                result_6g="Pass",
                result_24g="Pass",
            )
        ]
    }
    facade_result = AuditCaseResult(
        case_id=case_id,
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={},
        artifacts={},
        error=None,
    )

    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: wb_index)
    with patch("testpilot.audit.pass12._run_facade", return_value=facade_result):
        runner = CliRunner()
        first = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])
        second = runner.invoke(main, ["--root", str(root), "audit", "pass12", rid])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    run_dir = root / "audit" / "runs" / rid / plugin
    entries = bucket.list_bucket(run_dir, "confirmed")
    matched = [e for e in entries if e["case_id"] == case_id]
    assert len(matched) == 1
