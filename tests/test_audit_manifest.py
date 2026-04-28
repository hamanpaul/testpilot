from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from testpilot.audit import manifest


def git_short_sha(cwd: Path) -> str:
    out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(cwd))
    return out.decode().strip()


def git_full_sha(cwd: Path) -> str:
    out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(cwd))
    return out.decode().strip()


def test_generate_rid_format(tmp_path, monkeypatch):
    # run inside worktree cwd
    cwd = Path(".")
    rid = manifest.generate_rid()
    assert re.match(manifest.RID_PATTERN, rid)
    expected_prefix = git_short_sha(cwd) + "-"
    assert rid.startswith(expected_prefix)


def test_create_and_load_run(tmp_path):
    cwd = Path(".")
    plugin = "wifi_llapi"
    cli_args = ["--repeat-count", "5"]
    cases = ["D001"]
    workbook = "nonexistent.xlsx"

    # Create a run
    run_info = manifest.create_run(plugin=plugin, workbook_path=workbook, cli_args=cli_args, cases=cases)

    # Basic checks
    assert "rid" in run_info
    rid = run_info["rid"]
    assert re.match(manifest.RID_PATTERN, rid)
    run_dir = Path("audit") / "runs" / rid / plugin
    assert (run_dir / "case").exists()
    assert (run_dir / "buckets").exists()
    mpath = run_dir / "manifest.json"
    assert mpath.exists()

    loaded = manifest.load_run(rid, plugin)
    assert loaded["plugin"] == plugin
    assert loaded["rid"] == rid
    assert loaded["workbook_path"] == workbook
    # workbook missing -> empty sha
    assert loaded["workbook_sha256"] == ""
    assert loaded["cli_args"] == cli_args
    assert loaded["cases"] == cases
    # git commit sha should be full 40-char
    assert loaded["git_commit_sha"] == git_full_sha(cwd)
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{6}Z", loaded["init_timestamp"]) or re.match(r"\d{4}-\d{2}-\d{2}T\d{6}Z", run_info["init_timestamp"]) 
