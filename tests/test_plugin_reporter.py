"""Tests for plugin self-declared reporter support (R2-03)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from testpilot.core.plugin_base import PluginBase
from testpilot.core.plugin_loader import PluginLoader


# ---------------------------------------------------------------------------
# Concrete stub for testing PluginBase defaults
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[1]


class _StubPlugin(PluginBase):
    """Minimal concrete implementation used to verify base-class defaults."""

    @property
    def name(self) -> str:
        return "stub"

    @property
    def version(self) -> str:
        return "0.0.1"

    def discover_cases(self) -> list[dict[str, Any]]:
        return []

    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        return True

    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        return True

    def execute_step(
        self, case: dict[str, Any], step: dict[str, Any], topology: Any
    ) -> dict[str, Any]:
        return {"success": True, "output": "", "captured": {}, "timing": 0.0}

    def evaluate(self, case: dict[str, Any], results: dict[str, Any]) -> bool:
        return True

    def teardown(self, case: dict[str, Any], topology: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# PluginBase defaults
# ---------------------------------------------------------------------------


class TestPluginBaseDefaults:
    def test_create_reporter_returns_none(self) -> None:
        plugin = _StubPlugin()
        assert plugin.create_reporter() is None

    def test_report_formats_returns_xlsx(self) -> None:
        plugin = _StubPlugin()
        assert plugin.report_formats() == ["xlsx"]


# ---------------------------------------------------------------------------
# wifi_llapi overrides
# ---------------------------------------------------------------------------


class TestWifiLlapiReporter:
    def test_create_reporter_returns_markdown(self) -> None:
        from testpilot.reporting.reporter import MarkdownReporter

        loader = PluginLoader(_ROOT / "plugins")
        plugin = loader.load("wifi_llapi")
        reporter = plugin.create_reporter()
        assert isinstance(reporter, MarkdownReporter)

    def test_report_formats_includes_md_and_json(self) -> None:
        loader = PluginLoader(_ROOT / "plugins")
        plugin = loader.load("wifi_llapi")
        fmts = plugin.report_formats()
        assert "md" in fmts
        assert "json" in fmts
        assert "xlsx" in fmts


# ---------------------------------------------------------------------------
# _template plugin inherits defaults
# ---------------------------------------------------------------------------


class TestTemplatePluginDefaults:
    def test_create_reporter_returns_none(self) -> None:
        plugins_dir = _ROOT / "plugins"
        if not (plugins_dir / "_template" / "plugin.py").exists():
            pytest.skip("_template plugin not found at expected path")
        loader = PluginLoader(plugins_dir)
        plugin = loader.load("_template")
        assert plugin.create_reporter() is None

    def test_report_formats_returns_xlsx(self) -> None:
        plugins_dir = _ROOT / "plugins"
        if not (plugins_dir / "_template" / "plugin.py").exists():
            pytest.skip("_template plugin not found at expected path")
        loader = PluginLoader(plugins_dir)
        plugin = loader.load("_template")
        assert plugin.report_formats() == ["xlsx"]
