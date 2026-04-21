"""Shared fixtures and path configuration for brcm_fw_upgrade plugin tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add repo root to sys.path so that "from plugins.brcm_fw_upgrade..." imports work
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[3]
