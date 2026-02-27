"""Orchestrator — central coordinator for plugin loading, test scheduling, and monitoring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from testpilot.core.plugin_loader import PluginLoader
from testpilot.core.testbed_config import TestbedConfig

log = logging.getLogger(__name__)

# 預設路徑（相對於專案根目錄）
DEFAULT_PLUGINS_DIR = "plugins"
DEFAULT_CONFIG_DIR = "configs"


class Orchestrator:
    """主編排器：載入 plugin、排程測試、協調監控與報告。"""

    def __init__(
        self,
        project_root: Path | str | None = None,
        plugins_dir: Path | str | None = None,
        config_path: Path | str | None = None,
    ) -> None:
        self.root = Path(project_root) if project_root else Path(__file__).resolve().parents[3]
        self.plugins_dir = Path(plugins_dir) if plugins_dir else self.root / DEFAULT_PLUGINS_DIR
        config = config_path or self.root / DEFAULT_CONFIG_DIR / "testbed.yaml"
        self.config = TestbedConfig(config)
        self.loader = PluginLoader(self.plugins_dir)

    def discover_plugins(self) -> list[str]:
        """列出所有可用 plugin。"""
        return self.loader.discover()

    def list_cases(self, plugin_name: str) -> list[dict[str, Any]]:
        """載入指定 plugin 並列出其 test cases。"""
        plugin = self.loader.load(plugin_name)
        return plugin.discover_cases()

    def run(self, plugin_name: str, case_ids: list[str] | None = None) -> dict[str, Any]:
        """執行測試。（Phase 3 完整實作）

        目前為 skeleton，僅列出將執行的 cases。
        """
        plugin = self.loader.load(plugin_name)
        cases = plugin.discover_cases()
        if case_ids:
            cases = [c for c in cases if c.get("id") in case_ids]

        log.info("would run %d cases from plugin '%s'", len(cases), plugin_name)
        return {
            "plugin": plugin_name,
            "plugin_version": plugin.version,
            "cases_count": len(cases),
            "case_ids": [c.get("id", "?") for c in cases],
            "status": "skeleton — not yet implemented",
        }
