# tests/test_audit_provenance_hook.py
"""Pre-commit hook: audit YAML provenance enforcement."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


HOOK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_audit_yaml_provenance.py"


def _run_hook(
    *args: str,
    cwd: Path,
    env_extra: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    import os

    env = os.environ.copy()
    # Remove any pre-existing COMMIT_MSG to avoid test pollution
    env.pop("COMMIT_MSG", None)
    env.pop("GIT_DIR", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )
    return p.returncode, p.stdout, p.stderr


def _stub_repo_with_audit(tmp_path: Path) -> Path:
    """Create a minimal repo layout with an audit/runs dir."""
    repo = tmp_path / "repo"
    (repo / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)
    (repo / "audit" / "runs" / "rid1" / "wifi_llapi").mkdir(parents=True)
    return repo


# ---------------------------------------------------------------------------
# Soft-skip paths
# ---------------------------------------------------------------------------


def test_hook_soft_skips_when_audit_dir_absent(tmp_path):
    """Hook must exit 0 and print a warning when audit/ does not exist."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "plugins" / "wifi_llapi" / "cases").mkdir(parents=True)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D001_x.yaml"
    yaml_file.write_text("id: x\n")
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    assert rc == 0, f"Expected soft-skip (rc=0), got rc={rc}\nout={out}\nerr={err}"
    assert "audit/" in (out + err)


def test_hook_soft_skips_when_log_is_empty(tmp_path):
    """Hook must exit 0 when audit/ exists but all verify_edit_log.jsonl are empty."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D001_x.yaml"
    yaml_file.write_text("id: D001\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text("")
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    assert rc == 0, f"Expected soft-skip (rc=0), got rc={rc}\nout={out}\nerr={err}"
    assert "soft-skip" in (out + err)


# ---------------------------------------------------------------------------
# Pass path
# ---------------------------------------------------------------------------


def test_hook_passes_when_log_matches(tmp_path):
    """Hook must exit 0 when the current file SHA matches a log entry."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D001_x.yaml"
    yaml_content = "id: D001\nname: x\n"
    yaml_file.write_text(yaml_content)
    sha = hashlib.sha256(yaml_content.encode()).hexdigest()
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text(
        json.dumps(
            {
                "case": "D001",
                "yaml_path": str(yaml_file),
                "yaml_sha256_after_proposed": sha,
                "diff_paths": ["pass_criteria[0].value"],
            }
        )
        + "\n"
    )
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    assert rc == 0, f"out={out}\nerr={err}"


def test_hook_passes_with_relative_path_in_log(tmp_path):
    """Hook must pass when yaml_path in the log is a relative path (pre-commit style)."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D002_y.yaml"
    yaml_content = "id: D002\nname: y\n"
    yaml_file.write_text(yaml_content)
    sha = hashlib.sha256(yaml_content.encode()).hexdigest()
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    # Store as relative path (as pre-commit passes filenames)
    log.write_text(
        json.dumps(
            {
                "case": "D002",
                "yaml_path": "plugins/wifi_llapi/cases/D002_y.yaml",
                "yaml_sha256_after_proposed": sha,
                "diff_paths": ["steps[0].command"],
            }
        )
        + "\n"
    )
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    assert rc == 0, f"out={out}\nerr={err}"


# ---------------------------------------------------------------------------
# Fail path
# ---------------------------------------------------------------------------


def test_hook_fails_when_no_log_match(tmp_path):
    """Hook must exit non-zero when the YAML SHA has no matching log entry."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D001_x.yaml"
    yaml_file.write_text("id: D001\nname: untracked\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text(
        json.dumps(
            {
                "case": "D001",
                "yaml_path": str(yaml_file),
                "yaml_sha256_after_proposed": "deadbeef",
                "diff_paths": [],
            }
        )
        + "\n"
    )
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    assert rc != 0, f"Expected failure, got rc={rc}"
    assert "verify-edit" in (out + err)


def test_hook_fail_message_mentions_remediation(tmp_path):
    """Error output must mention testpilot audit verify-edit for guidance."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D003_z.yaml"
    yaml_file.write_text("id: D003\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text(
        json.dumps({"case": "D003", "yaml_sha256_after_proposed": "aabbcc"})
        + "\n"
    )
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    assert rc != 0
    combined = out + err
    assert "testpilot audit verify-edit" in combined
    assert "audit-bypass" in combined


# ---------------------------------------------------------------------------
# Bypass path
# ---------------------------------------------------------------------------


def test_hook_audit_bypass_via_commit_msg(tmp_path):
    """Hook must exit 0 and write bypass_log.jsonl when commit msg has [audit-bypass]."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D001_x.yaml"
    yaml_file.write_text("id: D001\nname: untracked\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text("")  # no entries — would normally soft-skip, but bypass takes priority
    rc, out, err = _run_hook(
        str(yaml_file),
        cwd=repo,
        env_extra={"COMMIT_MSG": "fix: rename id [audit-bypass: rename only]"},
    )
    assert rc == 0, f"out={out}\nerr={err}"
    bypass_log = repo / "audit" / "bypass_log.jsonl"
    assert bypass_log.is_file(), "bypass_log.jsonl should have been created"


def test_hook_bypass_log_content(tmp_path):
    """bypass_log.jsonl entry must contain reason and files fields."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D005_w.yaml"
    yaml_file.write_text("id: D005\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text(
        json.dumps({"yaml_sha256_after_proposed": "wrongsha"}) + "\n"
    )
    rc, out, err = _run_hook(
        str(yaml_file),
        cwd=repo,
        env_extra={"COMMIT_MSG": "chore: reformat [audit-bypass: formatting only]"},
    )
    assert rc == 0
    bypass_log = repo / "audit" / "bypass_log.jsonl"
    entry = json.loads(bypass_log.read_text().strip())
    assert entry["reason"] == "formatting only"
    assert any("D005_w.yaml" in f for f in entry["files"])


def test_hook_bypass_reads_commit_message_from_git_dir(tmp_path):
    """Hook must read COMMIT_EDITMSG from GIT_DIR for git worktree compatibility."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D007_wt.yaml"
    yaml_file.write_text("id: D007\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    log.write_text("")

    git_dir = tmp_path / "fake-git-dir"
    git_dir.mkdir()
    (git_dir / "COMMIT_EDITMSG").write_text("chore: bypass [audit-bypass: worktree test]", encoding="utf-8")

    rc, out, err = _run_hook(
        str(yaml_file),
        cwd=repo,
        env_extra={"GIT_DIR": str(git_dir)},
    )

    assert rc == 0, f"out={out}\nerr={err}"
    assert "BYPASS" in out
    assert (repo / "audit" / "bypass_log.jsonl").is_file()


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------


def test_hook_ignores_non_case_yaml(tmp_path):
    """Hook must exit 0 without checking provenance for non-D*.yaml files."""
    repo = _stub_repo_with_audit(tmp_path)
    # A non-matching YAML path
    other = repo / "plugins" / "wifi_llapi" / "cases" / "_fixture.yaml"
    other.write_text("id: fixture\n")
    rc, out, err = _run_hook(str(other), cwd=repo)
    assert rc == 0


def test_hook_exits_zero_with_no_files(tmp_path):
    """Hook invoked with no arguments must exit 0."""
    repo = tmp_path / "repo"
    repo.mkdir()
    rc, out, err = _run_hook(cwd=repo)
    assert rc == 0


# ---------------------------------------------------------------------------
# Robustness: malformed JSONL
# ---------------------------------------------------------------------------


def test_hook_tolerates_malformed_jsonl_lines(tmp_path):
    """Hook must not crash on malformed JSONL lines; should fail gracefully."""
    repo = _stub_repo_with_audit(tmp_path)
    yaml_file = repo / "plugins" / "wifi_llapi" / "cases" / "D010_k.yaml"
    yaml_file.write_text("id: D010\n")
    log = repo / "audit" / "runs" / "rid1" / "wifi_llapi" / "verify_edit_log.jsonl"
    # Mix of malformed and a valid-but-wrong-sha entry
    log.write_text("not-json\n{broken\n" + json.dumps({"yaml_sha256_after_proposed": "x"}) + "\n")
    rc, out, err = _run_hook(str(yaml_file), cwd=repo)
    # Should fail (no matching SHA) but not raise an unhandled exception
    assert rc != 0
    assert "Traceback" not in (out + err)
