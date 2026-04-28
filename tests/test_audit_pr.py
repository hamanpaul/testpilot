"""Tests for testpilot.audit.pr — mock-only, no real git/gh."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from testpilot.audit.pr import build_pr_body, open_pr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_dir(tmp_path: Path, *, plugin: str = "wifi_llapi") -> Path:
    run_dir = tmp_path / "audit" / "runs" / "rid1" / plugin
    (run_dir / "buckets").mkdir(parents=True)
    return run_dir


def _write_manifest(run_dir: Path, *, rid: str, plugin: str, cases: list) -> None:
    import json
    (run_dir / "manifest.json").write_text(
        json.dumps({"rid": rid, "plugin": plugin, "cases": cases}),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# build_pr_body
# ---------------------------------------------------------------------------


def test_build_pr_body_contains_rid_and_buckets(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=["D366", "D369"])
    (run_dir / "buckets" / "applied.jsonl").write_text(
        '{"case": "D366", "reason": "pass3_verified"}\n'
        '{"case": "D369", "reason": "pass3_verified"}\n',
        encoding="utf-8",
    )
    body = build_pr_body(run_dir, rid="rid1")

    assert "rid1" in body
    # bucket table row format: "| applied | 2 |"
    assert "applied | 2" in body
    assert "D366" in body
    assert "D369" in body


def test_build_pr_body_case_id_compat(tmp_path: Path) -> None:
    """build_pr_body handles legacy 'case_id' key as well as 'case'."""
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid2", plugin="wifi_llapi", cases=["D370"])
    (run_dir / "buckets" / "applied.jsonl").write_text(
        '{"case_id": "D370", "reason": "pass1_match"}\n',
        encoding="utf-8",
    )
    body = build_pr_body(run_dir, rid="rid2")
    assert "D370" in body
    assert "applied | 1" in body


def test_build_pr_body_block_list_present(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid3", plugin="wifi_llapi", cases=["D400"])
    (run_dir / "buckets" / "applied.jsonl").write_text("")
    (run_dir / "buckets" / "block.jsonl").write_text(
        '{"case": "D400", "reason": "workbook_row_missing"}\n',
        encoding="utf-8",
    )
    body = build_pr_body(run_dir, rid="rid3")
    assert "D400" in body
    assert "Block list" in body


# ---------------------------------------------------------------------------
# open_pr
# ---------------------------------------------------------------------------


def _mock_run_side_effect(args, **kwargs):
    """Return realistic mock values depending on the command."""
    mock = MagicMock(returncode=0)
    if args[0] == "git" and args[1] == "rev-parse":
        mock.stdout = "/fake/repo\n"
    elif args[0] == "gh" and "pr" in args:
        mock.stdout = "https://example.com/pr/1"
    else:
        mock.stdout = ""
    return mock


def test_open_pr_invokes_subprocess_and_returns_url(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=["D366"])
    fake_repo = tmp_path / "repo-main"
    cases_dir = fake_repo / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D366_test.yaml").write_text("id: D366\n", encoding="utf-8")
    (run_dir / "buckets" / "applied.jsonl").write_text('{"case": "D366", "reason": "ready"}\n')

    def _mock_run(args, **kwargs):
        mock = MagicMock(returncode=0)
        if args[0] == "git" and args[1] == "rev-parse":
            mock.stdout = str(fake_repo) + "\n"
        elif args[0] == "gh" and "pr" in args:
            mock.stdout = "https://example.com/pr/1"
        else:
            mock.stdout = ""
        return mock

    with patch("testpilot.audit.pr.subprocess.run", side_effect=_mock_run) as mock_run:
        url = open_pr(run_dir, rid="rid1", draft=False)

    # Expect: git rev-parse + git add + git commit + git push + gh pr create
    assert mock_run.call_count >= 4
    assert "https://" in url


def test_open_pr_draft_flag_forwarded(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=["D366"])
    fake_repo = tmp_path / "repo-draft"
    cases_dir = fake_repo / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D366_test.yaml").write_text("id: D366\n", encoding="utf-8")
    (run_dir / "buckets" / "applied.jsonl").write_text('{"case": "D366", "reason": "ready"}\n')

    def _mock_run(args, **kwargs):
        mock = MagicMock(returncode=0)
        if args[0] == "git" and args[1] == "rev-parse":
            mock.stdout = str(fake_repo) + "\n"
        elif args[0] == "gh":
            mock.stdout = "https://example.com/pr/1"
        else:
            mock.stdout = ""
        return mock

    with patch("testpilot.audit.pr.subprocess.run", side_effect=_mock_run) as mock_run:
        open_pr(run_dir, rid="rid1", draft=True)

    # Find the gh pr create call and verify --draft is present
    gh_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "gh"]
    assert gh_calls, "gh pr create was not called"
    gh_args = gh_calls[0].args[0]
    assert "--draft" in gh_args


def test_open_pr_returns_empty_when_no_applied_files(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=[])
    (run_dir / "buckets" / "applied.jsonl").write_text("")

    with patch("testpilot.audit.pr.subprocess.run", side_effect=_mock_run_side_effect) as mock_run:
        url = open_pr(run_dir, rid="rid1", draft=False)

    assert url == ""
    rev_parse_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == "git" and c.args[0][1] == "rev-parse"
    ]
    assert rev_parse_calls
    assert len(mock_run.call_args_list) == 1


def test_open_pr_stages_only_applied_case_files(tmp_path: Path) -> None:
    """Only the specific YAML files from applied bucket should be staged."""
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=["D366"])
    # Write a YAML file for D366 in the (fake) repo structure
    fake_repo = tmp_path / "repo"
    cases_dir = fake_repo / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    case_yaml = cases_dir / "D366_some_test.yaml"
    case_yaml.write_text("id: D366\n")
    (run_dir / "buckets" / "applied.jsonl").write_text(
        '{"case": "D366", "reason": "pass3_verified"}\n'
    )

    def mock_run_with_repo(args, **kwargs):
        mock = MagicMock(returncode=0)
        if args[0] == "git" and args[1] == "rev-parse":
            mock.stdout = str(fake_repo) + "\n"
        elif args[0] == "gh":
            mock.stdout = "https://example.com/pr/2"
        else:
            mock.stdout = ""
        return mock

    with patch("testpilot.audit.pr.subprocess.run", side_effect=mock_run_with_repo) as mock_run:
        open_pr(run_dir, rid="rid1", draft=False)

    # The git add call must reference the specific case YAML, not the whole cases dir
    git_add_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == "git" and c.args[0][1] == "add"
    ]
    assert git_add_calls, "git add was not called"
    added_args = git_add_calls[0].args[0]
    assert str(case_yaml) in added_args
    # Must NOT be a blanket add of the cases directory (directory path without filename)
    cases_dir_str = str(cases_dir)
    assert cases_dir_str not in added_args, (
        f"git add should not include the whole cases directory: {cases_dir_str}"
    )


def test_open_pr_case_id_key_in_applied_bucket(tmp_path: Path) -> None:
    """Entries with legacy 'case_id' key are staged correctly."""
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=["D370"])
    fake_repo = tmp_path / "repo2"
    cases_dir = fake_repo / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    case_yaml = cases_dir / "D370_compat.yaml"
    case_yaml.write_text("id: D370\n")
    (run_dir / "buckets" / "applied.jsonl").write_text(
        '{"case_id": "D370", "reason": "pass1_match"}\n'
    )

    def mock_run_compat(args, **kwargs):
        mock = MagicMock(returncode=0)
        if args[0] == "git" and args[1] == "rev-parse":
            mock.stdout = str(fake_repo) + "\n"
        elif args[0] == "gh":
            mock.stdout = "https://example.com/pr/3"
        else:
            mock.stdout = ""
        return mock

    with patch("testpilot.audit.pr.subprocess.run", side_effect=mock_run_compat) as mock_run:
        url = open_pr(run_dir, rid="rid1", draft=False)

    git_add_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == "git" and c.args[0][1] == "add"
    ]
    assert git_add_calls
    added_args = git_add_calls[0].args[0]
    assert str(case_yaml) in added_args
    assert "https://" in url


def test_open_pr_raises_when_applied_case_yaml_is_ambiguous(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    _write_manifest(run_dir, rid="rid1", plugin="wifi_llapi", cases=["D500"])
    fake_repo = tmp_path / "repo-ambiguous"
    cases_dir = fake_repo / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D500_a.yaml").write_text("id: D500\n", encoding="utf-8")
    (cases_dir / "D500_b.yaml").write_text("id: D500\n", encoding="utf-8")
    (run_dir / "buckets" / "applied.jsonl").write_text('{"case": "D500", "reason": "ready"}\n')

    def _mock_run(args, **kwargs):
        mock = MagicMock(returncode=0)
        if args[0] == "git" and args[1] == "rev-parse":
            mock.stdout = str(fake_repo) + "\n"
        else:
            mock.stdout = ""
        return mock

    with patch("testpilot.audit.pr.subprocess.run", side_effect=_mock_run):
        with pytest.raises(ValueError, match="ambiguous"):
            open_pr(run_dir, rid="rid1", draft=False)
