"""Release/version metadata guardrails."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from testpilot.cli import main


ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]["version"]


def _runtime_version() -> str:
    init_text = (ROOT / "src/testpilot/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    assert match is not None, "__version__ must be defined in src/testpilot/__init__.py"
    return match.group(1)


def _version_file_version() -> str:
    version_file = ROOT / "VERSION"
    assert version_file.exists(), "VERSION file must exist at repository root"
    return version_file.read_text(encoding="utf-8").strip()


def test_runtime_version_matches_pyproject() -> None:
    """Runtime version mirror should stay aligned with package metadata."""
    assert _runtime_version() == _pyproject_version()


def test_project_version_uses_semver_core() -> None:
    """Project version should use plain SemVer core format."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", _pyproject_version())


def test_changelog_keeps_unreleased_section() -> None:
    """CHANGELOG keeps an Unreleased queue for release-prep PRs."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in changelog


# --- Task 1.1: VERSION canonical mirror alignment ---


def test_version_file_exists() -> None:
    """VERSION file must exist at repository root."""
    assert (ROOT / "VERSION").exists(), "VERSION file missing"


def test_version_file_matches_pyproject() -> None:
    """VERSION file must mirror pyproject.toml version."""
    assert _version_file_version() == _pyproject_version()


def test_version_file_matches_runtime() -> None:
    """VERSION file must mirror src/testpilot/__init__.py __version__."""
    assert _version_file_version() == _runtime_version()


def test_all_versions_are_0_2_0() -> None:
    """Migration target: VERSION, pyproject.toml, and __init__.py must all be 0.2.0."""
    assert _version_file_version() == "0.2.0"
    assert _pyproject_version() == "0.2.0"
    assert _runtime_version() == "0.2.0"


# --- Task 1.1: source-ref-aware testpilot --version ---


def test_version_output_branch_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """--version should print 'TestPilot X.Y.Z (branch@short-sha)' on a branch."""
    monkeypatch.chdir(ROOT)
    runner = CliRunner()

    def _fake_run(cmd, **kwargs):
        class _R:
            returncode = 0
            stdout = ""

        if "symbolic-ref" in cmd and "--short" in cmd:
            _R.stdout = "main\n"
        elif "rev-parse" in cmd and "--short" in cmd:
            _R.stdout = "abcdef1\n"
        else:
            _R.stdout = ""
            _R.returncode = 1
        return _R()

    with patch("testpilot.cli._git_run", side_effect=_fake_run):
        result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert re.search(r"TestPilot 0\.2\.0 \(main@abcdef1\)", result.output)


def test_version_output_tag_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """--version should print 'TestPilot X.Y.Z (tag@short-sha)' when on a tag."""
    monkeypatch.chdir(ROOT)
    runner = CliRunner()

    def _fake_run(cmd, **kwargs):
        class _R:
            returncode = 0
            stdout = ""

        if "symbolic-ref" in cmd:
            _R.returncode = 128
            _R.stdout = ""
        elif "describe" in cmd and "--tags" in cmd:
            _R.returncode = 0
            _R.stdout = "v0.2.0\n"
        elif "rev-parse" in cmd and "--short" in cmd:
            _R.stdout = "2f7caf8\n"
        else:
            _R.stdout = ""
            _R.returncode = 1
        return _R()

    with patch("testpilot.cli._git_run", side_effect=_fake_run):
        result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert re.search(r"TestPilot 0\.2\.0 \(v0\.2\.0@2f7caf8\)", result.output)


def test_version_output_detached_head_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """--version should fall back to 'commit@short-sha' on detached HEAD."""
    monkeypatch.chdir(ROOT)
    runner = CliRunner()

    def _fake_run(cmd, **kwargs):
        class _R:
            returncode = 128
            stdout = ""

        if "rev-parse" in cmd and "--short" in cmd:
            _R.returncode = 0
            _R.stdout = "deadbee\n"
        return _R()

    with patch("testpilot.cli._git_run", side_effect=_fake_run):
        result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert re.search(r"TestPilot 0\.2\.0 \(commit@deadbee\)", result.output)
