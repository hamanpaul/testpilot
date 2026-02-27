"""wifi_llapi plugin — Wifi LLAPI test automation for prplOS/Broadcom."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from testpilot.core.plugin_base import PluginBase
from testpilot.schema.case_schema import load_cases_dir

log = logging.getLogger(__name__)


class Plugin(PluginBase):
    """Wifi LLAPI 測試 plugin。

    測試 prplOS WiFi.Radio / WiFi.AccessPoint 的 LLAPI 介面，
    透過 ubus-cli 與 wl 指令驗證參數讀寫與功能正確性。
    """

    @property
    def name(self) -> str:
        return "wifi_llapi"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def cases_dir(self) -> Path:
        return Path(__file__).parent / "cases"

    def discover_cases(self) -> list[dict[str, Any]]:
        return load_cases_dir(self.cases_dir)

    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        """佈建 WiFi 測試環境。（Phase 4 完整實作）"""
        log.info("[%s] setup_env: %s (stub)", self.name, case.get("id"))
        return True

    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        """驗證 WiFi 連線就緒。（Phase 4 完整實作）"""
        log.info("[%s] verify_env: %s (stub)", self.name, case.get("id"))
        return True

    def execute_step(self, case: dict[str, Any], step: dict[str, Any], topology: Any) -> dict[str, Any]:
        """執行單一 ubus-cli / wl 測試步驟。（Phase 4 完整實作）"""
        log.info("[%s] execute_step: %s.%s (stub)", self.name, case.get("id"), step.get("id"))
        return {
            "success": True,
            "output": f"[stub] {step.get('command', '')}",
            "captured": {},
            "timing": 0.0,
        }

    def evaluate(self, case: dict[str, Any], results: dict[str, Any]) -> bool:
        """評估通過條件。（Phase 4 完整實作）"""
        log.info("[%s] evaluate: %s (stub)", self.name, case.get("id"))
        return True

    def teardown(self, case: dict[str, Any], topology: Any) -> None:
        """清理環境。（Phase 4 完整實作）"""
        log.info("[%s] teardown: %s (stub)", self.name, case.get("id"))
