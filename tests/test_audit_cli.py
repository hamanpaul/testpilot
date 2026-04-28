from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

import testpilot.audit.cli as audit_cli
from testpilot.audit import bucket, manifest
from testpilot.cli import main


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["git", "init", "-q"], cwd=str(path))
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=str(path))
    subprocess.check_call(["git", "config", "user.name", "Test User"], cwd=str(path))
    (path / "README.md").write_text("repo\n", encoding="utf-8")
    subprocess.check_call(["git", "add", "README.md"], cwd=str(path))
    subprocess.check_call(["git", "commit", "-qm", "init"], cwd=str(path))
    return path


def test_audit_init_discovers_default_workbook_and_d_cases(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "audit" / "workbooks" / "demo.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"workbook-bytes")

    cases_dir = root / "plugins" / "demo" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "D002_two.yaml").write_text("id: demo-D002\n", encoding="utf-8")
    (cases_dir / "D001_one.yaml").write_text("id: demo-D001\n", encoding="utf-8")
    (cases_dir / "_fixture.yaml").write_text("id: ignored\n", encoding="utf-8")

    calls: list[tuple[Path, str, dict[str, str] | None]] = []

    def fake_build_index(
        workbook_path: Path | str,
        *,
        sheet_name: str = "Wifi_LLAPI",
        column_overrides: dict[str, str] | None = None,
    ) -> dict[tuple[str, str], list[object]]:
        calls.append((Path(workbook_path), sheet_name, column_overrides))
        return {}

    monkeypatch.setattr(audit_cli, "build_index", fake_build_index)

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "init", "demo"])

    assert result.exit_code == 0, result.output
    rid = result.output.strip()
    assert manifest.RID_PATTERN.match(rid)
    assert calls == [(workbook, "Wifi_LLAPI", None)]

    data = manifest.load_run(rid, plugin="demo", audit_root=root / "audit")
    assert data["cases"] == ["D001", "D002"]
    snapshot = root / "audit" / "runs" / rid / "demo" / "workbook_snapshot.xlsx"
    assert snapshot.read_bytes() == workbook.read_bytes()


def test_audit_init_accepts_explicit_cli_options(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "manual.xlsx"
    workbook.write_bytes(b"manual-workbook")

    calls: list[tuple[Path, str, dict[str, str] | None]] = []

    def fake_build_index(
        workbook_path: Path | str,
        *,
        sheet_name: str = "Wifi_LLAPI",
        column_overrides: dict[str, str] | None = None,
    ) -> dict[tuple[str, str], list[object]]:
        calls.append((Path(workbook_path), sheet_name, column_overrides))
        return {}

    monkeypatch.setattr(audit_cli, "build_index", fake_build_index)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--root",
            str(root),
            "audit",
            "init",
            "demo",
            "--workbook",
            str(workbook),
            "--cases",
            "D009,D011",
            "--sheet",
            "CustomSheet",
            "--col-object",
            "F",
            "--col-api",
            "E",
            "--col-steps",
            "G",
            "--col-output",
            "H",
            "--col-result-5g",
            "R",
            "--col-result-6g",
            "S",
            "--col-result-24g",
            "T",
        ],
    )

    assert result.exit_code == 0, result.output
    rid = result.output.strip()
    assert manifest.RID_PATTERN.match(rid)
    assert calls == [
        (
            workbook,
            "CustomSheet",
            {
                "object": "F",
                "api": "E",
                "test_steps": "G",
                "command_output": "H",
                "result_5g": "R",
                "result_6g": "S",
                "result_24g": "T",
            },
        )
    ]

    data = manifest.load_run(rid, plugin="demo", audit_root=root / "audit")
    assert data["cases"] == ["D009", "D011"]
    assert data["cli_args"] == {
        "sheet": "CustomSheet",
        "cases": ["D009", "D011"],
        "column_overrides": {
            "object": "F",
            "api": "E",
            "test_steps": "G",
            "command_output": "H",
            "result_5g": "R",
            "result_6g": "S",
            "result_24g": "T",
        },
    }


def test_audit_init_resolves_relative_workbook_against_root(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "manual.xlsx"
    workbook.write_bytes(b"manual-workbook")

    cases_dir = root / "plugins" / "demo" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "D009_one.yaml").write_text("id: demo-D009\n", encoding="utf-8")

    calls: list[Path] = []

    def fake_build_index(
        workbook_path: Path | str,
        *,
        sheet_name: str = "Wifi_LLAPI",
        column_overrides: dict[str, str] | None = None,
    ) -> dict[tuple[str, str], list[object]]:
        calls.append(Path(workbook_path))
        return {}

    monkeypatch.setattr(audit_cli, "build_index", fake_build_index)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--root",
            str(root),
            "audit",
            "init",
            "demo",
            "--workbook",
            "manual.xlsx",
            "--cases",
            "D009",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [workbook]


def test_audit_init_cleans_up_run_when_snapshot_copy_fails(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "audit" / "workbooks" / "demo.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"workbook-bytes")

    cases_dir = root / "plugins" / "demo" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "D001_one.yaml").write_text("id: demo-D001\n", encoding="utf-8")

    monkeypatch.setattr(audit_cli, "build_index", lambda *args, **kwargs: {})

    def _boom(*args, **kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr(audit_cli.shutil, "copy2", _boom)

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "init", "demo"])

    assert result.exit_code != 0
    assert "copy failed" in result.output
    runs_root = root / "audit" / "runs"
    assert not runs_root.exists() or not any(runs_root.iterdir())


def test_audit_init_wraps_git_failures_as_click_errors(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "audit" / "workbooks" / "demo.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"workbook-bytes")

    cases_dir = root / "plugins" / "demo" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "D001_one.yaml").write_text("id: demo-D001\n", encoding="utf-8")

    monkeypatch.setattr(audit_cli, "build_index", lambda *args, **kwargs: {})

    def _git_fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["git", "rev-parse", "--short", "HEAD"])

    monkeypatch.setattr(audit_cli.manifest, "create_run", _git_fail)

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "init", "demo"])

    assert result.exit_code != 0
    assert "returned non-zero exit status 1" in result.output


def test_audit_init_wraps_invalid_workbook_errors(tmp_path: Path) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "audit" / "workbooks" / "demo.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"not-a-real-xlsx")

    cases_dir = root / "plugins" / "demo" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "D001_one.yaml").write_text("id: demo-D001\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "init", "demo"])

    assert result.exit_code != 0
    assert result.output


def test_audit_init_cleans_up_when_snapshot_sha_mismatches(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "audit" / "workbooks" / "demo.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"workbook-bytes")

    cases_dir = root / "plugins" / "demo" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "D001_one.yaml").write_text("id: demo-D001\n", encoding="utf-8")

    monkeypatch.setattr(audit_cli, "build_index", lambda *args, **kwargs: {})

    def _copy_different(src: Path, dst: Path) -> Path:
        Path(dst).write_bytes(b"different-snapshot-bytes")
        return Path(dst)

    monkeypatch.setattr(audit_cli.shutil, "copy2", _copy_different)

    runner = CliRunner()
    result = runner.invoke(main, ["--root", str(root), "audit", "init", "demo"])

    assert result.exit_code != 0
    assert "snapshot sha mismatch" in result.output.lower()
    runs_root = root / "audit" / "runs"
    assert not runs_root.exists() or not any(runs_root.iterdir())


def test_audit_status_reports_manifest_and_bucket_counts(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "audit" / "workbooks" / "demo.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"workbook-bytes")

    monkeypatch.setattr(audit_cli, "build_index", lambda *args, **kwargs: {})

    runner = CliRunner()
    init_result = runner.invoke(
        main,
        ["--root", str(root), "audit", "init", "demo", "--cases", "D001,D002"],
    )

    assert init_result.exit_code == 0, init_result.output
    rid = init_result.output.strip()
    run_dir = root / "audit" / "runs" / rid / "demo"
    bucket.append_to_bucket(run_dir, "confirmed", {"case_id": "D001"})
    bucket.append_to_bucket(run_dir, "pending", {"case_id": "D002"})
    bucket.append_to_bucket(run_dir, "needs_pass3", {"case_id": "D003"})

    status_result = runner.invoke(main, ["--root", str(root), "audit", "status", rid])

    assert status_result.exit_code == 0, status_result.output
    assert f"RID: {rid}" in status_result.output
    assert "plugin: demo" in status_result.output
    assert "cases: 2" in status_result.output
    for bucket_name, count in {
        "confirmed": 1,
        "applied": 0,
        "pending": 1,
        "block": 0,
        "needs_pass3": 1,
    }.items():
        assert f"  {bucket_name}: {count}" in status_result.output


def test_audit_summary_writes_markdown_report(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    workbook = root / "manual.xlsx"
    workbook.write_bytes(b"manual-workbook")

    monkeypatch.setattr(audit_cli, "build_index", lambda *args, **kwargs: {})

    runner = CliRunner()
    init_result = runner.invoke(
        main,
        [
            "--root",
            str(root),
            "audit",
            "init",
            "demo",
            "--workbook",
            str(workbook),
            "--cases",
            "D009,D011",
        ],
    )

    assert init_result.exit_code == 0, init_result.output
    rid = init_result.output.strip()
    run_dir = root / "audit" / "runs" / rid / "demo"
    bucket.append_to_bucket(run_dir, "confirmed", {"case_id": "D009"})
    bucket.append_to_bucket(run_dir, "block", {"case_id": "D011"})

    summary_result = runner.invoke(main, ["--root", str(root), "audit", "summary", rid])

    assert summary_result.exit_code == 0, summary_result.output
    summary_path = run_dir / "summary.md"
    assert summary_path.is_file()
    body = summary_path.read_text(encoding="utf-8")
    assert "# Audit Run Summary" in body
    assert f"- **RID**: `{rid}`" in body
    assert "- **Plugin**: `demo`" in body
    assert f"- **Workbook**: `{workbook}`" in body
    assert "- **Total cases**: 2" in body
    data = manifest.load_run(rid, plugin="demo", audit_root=root / "audit")
    assert f"- **Init**: {data['init_timestamp']}" in body
    assert "| Bucket | Count |" in body
    for bucket_name, count in {
        "confirmed": 1,
        "applied": 0,
        "pending": 0,
        "block": 1,
        "needs_pass3": 0,
    }.items():
        assert f"| {bucket_name} | {count} |" in body


_VALID_CASE_YAML = """\
id: x
name: x
source: {row: 1, object: 'WiFi.Radio.{i}.', api: 'Noise'}
bands: [5g]
topology: {devices: {DUT: {role: ap}}}
steps:
- {id: s1, action: exec, target: DUT, command: 'ubus-cli foo', capture: r}
pass_criteria:
- {field: r.x, operator: equals, value: '5'}
"""


def _init_audit_run(runner, root: Path, monkeypatch) -> str:
    """Helper: init an audit run under root; return RID."""
    monkeypatch.setattr(audit_cli, "build_index", lambda *a, **kw: {})
    workbook = root / "wb.xlsx"
    workbook.write_bytes(b"fake-xlsx-bytes")
    result = runner.invoke(
        main,
        ["--root", str(root), "audit", "init", "wifi_llapi", "--workbook", str(workbook), "--cases", "D001"],
    )
    assert result.exit_code == 0, result.output
    return result.output.strip().splitlines()[-1]


def test_verify_edit_pass(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    yaml_path = root / "plugins" / "wifi_llapi" / "cases" / "D001_noise.yaml"
    yaml_path.write_text(_VALID_CASE_YAML, encoding="utf-8")

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    proposed_dir = root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D001"
    proposed_dir.mkdir(parents=True, exist_ok=True)
    proposed_path = proposed_dir / "proposed.yaml"
    proposed_path.write_text(_VALID_CASE_YAML.replace("value: '5'", "value: '6'"), encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "verify-edit", rid, "D001",
            "--yaml", str(yaml_path),
            "--proposed", str(proposed_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "[OK]" in result.output

    log_path = root / "audit" / "runs" / rid / "wifi_llapi" / "verify_edit_log.jsonl"
    log = log_path.read_text(encoding="utf-8")
    assert "D001" in log
    assert "pass_criteria" in log


def test_verify_edit_rejects_source_row_change(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    yaml_path = root / "plugins" / "wifi_llapi" / "cases" / "D001_noise.yaml"
    yaml_path.write_text(_VALID_CASE_YAML, encoding="utf-8")

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    proposed_dir = root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D001"
    proposed_dir.mkdir(parents=True, exist_ok=True)
    proposed_path = proposed_dir / "proposed.yaml"
    proposed_path.write_text(_VALID_CASE_YAML.replace("row: 1", "row: 2"), encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "verify-edit", rid, "D001",
            "--yaml", str(yaml_path),
            "--proposed", str(proposed_path),
        ],
    )
    assert result.exit_code != 0
    assert "source.row" in result.output


def test_verify_edit_reports_yaml_parse_errors_clearly(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    yaml_path = root / "plugins" / "wifi_llapi" / "cases" / "D001_noise.yaml"
    yaml_path.write_text(_VALID_CASE_YAML, encoding="utf-8")

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    proposed_dir = root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D001"
    proposed_dir.mkdir(parents=True, exist_ok=True)
    proposed_path = proposed_dir / "proposed.yaml"
    proposed_path.write_text("id: x\nname: [\n", encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "verify-edit", rid, "D001",
            "--yaml", str(yaml_path),
            "--proposed", str(proposed_path),
        ],
    )

    assert result.exit_code != 0
    assert "YAML parse error" in result.output


def test_verify_edit_rejects_schema_invalid_proposed(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    yaml_path = root / "plugins" / "wifi_llapi" / "cases" / "D001_noise.yaml"
    yaml_path.write_text(_VALID_CASE_YAML, encoding="utf-8")

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    proposed_dir = root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D001"
    proposed_dir.mkdir(parents=True, exist_ok=True)
    proposed_path = proposed_dir / "proposed.yaml"
    proposed_path.write_text(_VALID_CASE_YAML.replace("command: 'ubus-cli foo'", "command: 123"), encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "verify-edit", rid, "D001",
            "--yaml", str(yaml_path),
            "--proposed", str(proposed_path),
        ],
    )

    assert result.exit_code != 0
    assert "schema invalid" in result.output


def test_record_writes_pass3_source_and_ok_status(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    source_file = root / "src" / "driver.c"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("line1\nuint16 srg_pbssid_bmp[4];\nline3\n", encoding="utf-8")

    evidence_path = root / "evidence.json"
    evidence_path.write_text(
        """{
  "candidate_commands": [],
  "citations": [
    {
      "file": "src/driver.c",
      "line": 2,
      "snippet": "uint16 srg_pbssid_bmp[4];"
    }
  ]
}
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "record", rid, "D001",
            "--evidence", str(evidence_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "[OK]" in result.output
    recorded = json.loads(
        (root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D001" / "pass3_source.json").read_text(
            encoding="utf-8"
        )
    )
    assert recorded["citations_verified"] is True


def test_record_writes_warn_status_when_citations_do_not_verify(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    source_file = root / "src" / "driver.c"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("line1\nuint16 srg_pbssid_bmp[4];\nline3\n", encoding="utf-8")

    evidence_path = root / "evidence.json"
    evidence_path.write_text(
        """{
  "candidate_commands": [],
  "citations": [
    {
      "file": "src/driver.c",
      "line": 9,
      "snippet": "uint16 srg_pbssid_bmp[4];"
    }
  ]
}
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "record", rid, "D001",
            "--evidence", str(evidence_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "[WARN]" in result.output
    recorded = json.loads(
        (root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D001" / "pass3_source.json").read_text(
            encoding="utf-8"
        )
    )
    assert recorded["citations_verified"] is False


def test_decide_writes_decision_json_and_bucket(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "decide", rid, "D366",
            "--bucket", "applied",
            "--reason", "test ok",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "[applied] D366: test ok" in result.output

    decision_path = root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D366" / "decision.json"
    assert decision_path.is_file()
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["bucket"] == "applied"
    assert decision["reason"] == "test ok"
    assert decision["case"] == "D366"

    bucket_path = root / "audit" / "runs" / rid / "wifi_llapi" / "buckets" / "applied.jsonl"
    bucket_lines = bucket_path.read_text(encoding="utf-8").splitlines()
    assert any('"D366"' in line for line in bucket_lines)


def test_decide_is_idempotent_and_moves_between_buckets(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)
    run_dir = root / "audit" / "runs" / rid / "wifi_llapi"

    # First decide: pending
    r1 = runner.invoke(
        main,
        ["--root", str(root), "audit", "decide", rid, "D366", "--bucket", "pending", "--reason", "first"],
    )
    assert r1.exit_code == 0, r1.output

    # Second decide: applied (rebucket)
    r2 = runner.invoke(
        main,
        ["--root", str(root), "audit", "decide", rid, "D366", "--bucket", "applied", "--reason", "second"],
    )
    assert r2.exit_code == 0, r2.output

    # D366 should NOT appear in pending any more
    pending_entries = bucket.list_bucket(run_dir, "pending")
    assert not any(e.get("case") == "D366" or e.get("case_id") == "D366" for e in pending_entries)

    # D366 should appear exactly once in applied
    applied_entries = bucket.list_bucket(run_dir, "applied")
    d366_in_applied = [e for e in applied_entries if e.get("case") == "D366" or e.get("case_id") == "D366"]
    assert len(d366_in_applied) == 1

    # decision.json reflects the latest decision
    decision = json.loads(
        (run_dir / "case" / "D366" / "decision.json").read_text(encoding="utf-8")
    )
    assert decision["bucket"] == "applied"
    assert decision["reason"] == "second"


def test_decide_stores_resolved_proposed_yaml(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    proposed_yaml = root / "patches" / "D999.yaml"
    proposed_yaml.parent.mkdir(parents=True, exist_ok=True)
    proposed_yaml.write_text("id: D999\n", encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "decide", rid, "D999",
            "--bucket", "confirmed",
            "--reason", "verified",
            "--proposed-yaml", str(proposed_yaml),
        ],
    )

    assert result.exit_code == 0, result.output
    decision = json.loads(
        (root / "audit" / "runs" / rid / "wifi_llapi" / "case" / "D999" / "decision.json").read_text(
            encoding="utf-8"
        )
    )
    assert decision["proposed_yaml"] == str(proposed_yaml.resolve())


def test_apply_updates_case_yaml_from_applied_bucket(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    cases_dir = root / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)
    run_dir = root / "audit" / "runs" / rid / "wifi_llapi"

    bucket.append_to_bucket(run_dir, "applied", {"case": "D366", "reason": "ready"})
    (run_dir / "case" / "D366").mkdir(parents=True, exist_ok=True)
    (run_dir / "case" / "D366" / "proposed.yaml").write_text("id: D366\nname: new\n", encoding="utf-8")
    (cases_dir / "D366_test.yaml").write_text("id: D366\nname: old\n", encoding="utf-8")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "apply", rid,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "[applied] D366" in result.output
    assert "Total applied: 1" in result.output
    assert "name: new" in (cases_dir / "D366_test.yaml").read_text(encoding="utf-8")


def test_apply_exits_nonzero_when_errors_occur(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)
    run_dir = root / "audit" / "runs" / rid / "wifi_llapi"

    bucket.append_to_bucket(run_dir, "applied", {"case": "D400", "reason": "ready"})

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "apply", rid,
        ],
    )

    assert result.exit_code != 0
    assert "[error] D400: proposed.yaml missing" in result.output
    assert "case(s) failed to apply" in result.output


def test_pr_prints_info_when_nothing_to_stage(tmp_path: Path, monkeypatch) -> None:
    root = init_repo(tmp_path / "repo")
    (root / "audit").mkdir()
    (root / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)

    runner = CliRunner()
    rid = _init_audit_run(runner, root, monkeypatch)

    monkeypatch.setattr(audit_cli.pr_mod, "open_pr", lambda run_dir, rid, draft=False: "")

    result = runner.invoke(
        main,
        [
            "--root", str(root),
            "audit", "pr", rid,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "no applied cases to stage" in result.output
