"""PluginBase — abstract base class for all test plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PluginBase(ABC):
    """每個測試類型（wifi_llapi, qos_llapi, sigma_qt ...）繼承此類別。

    Plugin 負責：
    1. 發現並載入 cases/*.yaml
    2. 依 case 描述佈建測試環境
    3. 執行測試步驟
    4. 評估通過條件
    5. 清理環境
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin 識別名稱，如 'wifi_llapi'。"""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin 版本。"""

    @property
    def cases_dir(self) -> Path:
        """cases/ 目錄路徑，預設為 plugin 同層的 cases/。"""
        return Path(__file__).parent / "cases"

    @abstractmethod
    def discover_cases(self) -> list[dict[str, Any]]:
        """掃描 cases/ 目錄，回傳所有 test case 描述（已解析的 YAML dict）。"""

    @abstractmethod
    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        """依 case 描述佈建測試環境（DUT/STA/EndpointPC）。

        Returns:
            True if setup succeeded.
        """

    @abstractmethod
    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        """環境自檢：驗證連線、服務就緒。

        Returns:
            True if environment is ready.
        """

    @abstractmethod
    def execute_step(self, case: dict[str, Any], step: dict[str, Any], topology: Any) -> dict[str, Any]:
        """執行單一測試步驟。

        Returns:
            dict with keys: success (bool), output (str), captured (dict), timing (float)
        """

    @abstractmethod
    def evaluate(self, case: dict[str, Any], results: dict[str, Any]) -> bool:
        """依 pass_criteria 評估測試結果。

        Returns:
            True if all criteria pass.
        """

    @abstractmethod
    def teardown(self, case: dict[str, Any], topology: Any) -> None:
        """清理測試環境。"""
