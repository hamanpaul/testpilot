"""Release/version metadata guardrails."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]["version"]


def _runtime_version() -> str:
    init_text = (ROOT / "src/testpilot/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    assert match is not None, "__version__ must be defined in src/testpilot/__init__.py"
    return match.group(1)


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
