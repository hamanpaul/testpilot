"""PluginLoader — discover and load plugins from the plugins/ directory."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from testpilot.core.plugin_base import PluginBase

log = logging.getLogger(__name__)


class PluginLoader:
    """動態發現並載入 plugins/ 下的 plugin 模組。

    每個 plugin 目錄須包含 plugin.py，其中定義一個 PluginBase 子類別，
    並以模組層級變數 `Plugin` 匯出。
    """

    def __init__(self, plugins_dir: Path | str) -> None:
        self.plugins_dir = Path(plugins_dir)
        self._plugins: dict[str, PluginBase] = {}

    def discover(self) -> list[str]:
        """掃描 plugins/ 目錄，回傳可用 plugin 名稱列表。"""
        found: list[str] = []
        if not self.plugins_dir.is_dir():
            log.warning("plugins dir not found: %s", self.plugins_dir)
            return found
        for child in sorted(self.plugins_dir.iterdir()):
            plugin_py = child / "plugin.py"
            if child.is_dir() and plugin_py.exists():
                found.append(child.name)
        return found

    def load(self, name: str) -> PluginBase:
        """載入指定 plugin 並回傳其實例。"""
        if name in self._plugins:
            return self._plugins[name]

        plugin_py = self.plugins_dir / name / "plugin.py"
        if not plugin_py.exists():
            raise FileNotFoundError(f"plugin not found: {plugin_py}")

        module_name = f"testpilot_plugin_{name}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_py)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load plugin spec: {plugin_py}")

        # Temporarily add plugin dir to sys.path for plugin internal imports
        plugin_dir = str(self.plugins_dir / name)
        added_to_path = plugin_dir not in sys.path
        if added_to_path:
            sys.path.insert(0, plugin_dir)
        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        finally:
            if added_to_path and plugin_dir in sys.path:
                sys.path.remove(plugin_dir)

        plugin_cls: Any = getattr(module, "Plugin", None)
        if plugin_cls is None:
            raise AttributeError(f"plugin.py must define 'Plugin' class: {plugin_py}")

        instance = plugin_cls()
        if not isinstance(instance, PluginBase):
            raise TypeError(f"Plugin class must inherit PluginBase: {plugin_cls}")

        self._plugins[name] = instance
        log.info("loaded plugin: %s v%s", instance.name, instance.version)
        return instance

    def load_all(self) -> dict[str, PluginBase]:
        """載入所有已發現的 plugins。"""
        for name in self.discover():
            try:
                self.load(name)
            except Exception:
                log.exception("failed to load plugin: %s", name)
        return dict(self._plugins)

    @property
    def loaded(self) -> dict[str, PluginBase]:
        return dict(self._plugins)
