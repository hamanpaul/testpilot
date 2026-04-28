from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

import testpilot.audit.cli as audit_cli
from testpilot.audit import manifest
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
