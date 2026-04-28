from __future__ import annotations

import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ensure local src is importable when running tests in the worktree
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from testpilot.audit import manifest


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["git", "init"], cwd=str(path))
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=str(path))
    subprocess.check_call(["git", "config", "user.name", "Test User"], cwd=str(path))
    # make initial commit
    (path / "README").write_text("hi")
    subprocess.check_call(["git", "add", "README"], cwd=str(path))
    subprocess.check_call(["git", "commit", "-m", "initial"], cwd=str(path))
    return path


def test_generate_rid_and_create_run(tmp_path):
    repo = init_repo(tmp_path / "repo")
    audit_root = tmp_path / "audit"

    plugin = "wifi_llapi"
    workbook = repo / "wb.xlsx"
    workbook.write_text("content")

    rid = manifest.generate_rid(repo_root=repo, now=datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    assert manifest.RID_PATTERN.match(rid)

    rid_created = manifest.create_run(
        plugin=plugin,
        workbook_path=workbook,
        cli_args={"repeat": 5},
        case_ids=["D001"],
        audit_root=audit_root,
        repo_root=repo,
    )

    assert rid_created == rid or manifest.RID_PATTERN.match(rid_created)

    # files exist
    run_dir = audit_root / "runs" / rid_created / plugin
    assert (run_dir / "case").exists()
    assert (run_dir / "buckets").exists()
    mpath = run_dir / "manifest.json"
    assert mpath.exists()

    loaded = manifest.load_run(rid_created, plugin=plugin, audit_root=audit_root)
    assert loaded["plugin"] == plugin
    assert loaded["rid"] == rid_created
    assert loaded["workbook_path"] == str(workbook)
    assert loaded["workbook_sha256"] != ""
    assert loaded["cli_args"]["repeat"] == 5
    assert loaded["cases"] == ["D001"]
    assert len(loaded["git_commit_sha"]) == 40
    assert loaded["init_timestamp"].endswith("Z")


def test_prevent_overwrite_on_collision(tmp_path, monkeypatch):
    repo = init_repo(tmp_path / "repo2")
    audit_root = tmp_path / "audit2"
    plugin = "wifi_llapi"

    fixed_rid = "deadbeef-2020-01-02T030405Z"
    monkeypatch.setattr(manifest, "generate_rid", lambda *a, **k: fixed_rid)

    rid1 = manifest.create_run(
        plugin=plugin,
        workbook_path=Path("/no/such"),
        cli_args={},
        case_ids=[],
        audit_root=audit_root,
        repo_root=repo,
    )
    assert rid1 == fixed_rid

    with pytest.raises(FileExistsError):
        manifest.create_run(
            plugin=plugin,
            workbook_path=Path("/no/such"),
            cli_args={},
            case_ids=[],
            audit_root=audit_root,
            repo_root=repo,
        )


def test_generate_rid_requires_repo_or_commit():
    # calling without repo_root or commit_sha should raise ValueError
    with pytest.raises(ValueError):
        manifest.generate_rid()


def test_generate_rid_propagates_git_errors(tmp_path):
    # Non-git directory should cause subprocess.CalledProcessError to be raised
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()
    import subprocess as _sub

    with pytest.raises(_sub.CalledProcessError):
        manifest.generate_rid(repo_root=non_repo)


def test_create_run_cleans_up_reserved_dir_on_failure(tmp_path, monkeypatch):
    repo = init_repo(tmp_path / "repo3")
    audit_root = tmp_path / "audit3"
    plugin = "wifi_llapi"
    fixed_rid = "feedbee-2020-01-02T030405Z"

    monkeypatch.setattr(manifest, "generate_rid", lambda *a, **k: fixed_rid)

    def _boom(_: Path) -> str:
        raise RuntimeError("git metadata failure")

    monkeypatch.setattr(manifest, "_git_full_sha", _boom)

    with pytest.raises(RuntimeError, match="git metadata failure"):
        manifest.create_run(
            plugin=plugin,
            workbook_path=Path("/no/such"),
            cli_args={},
            case_ids=[],
            audit_root=audit_root,
            repo_root=repo,
        )

    assert not (audit_root / "runs" / fixed_rid / plugin).exists()
    assert not (audit_root / "runs" / fixed_rid).exists()
