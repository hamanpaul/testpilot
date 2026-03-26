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
    def version(self) -> str:
        """Plugin 版本。預設 '0.0.0'；子類別可覆寫。"""
        return "0.0.0"

    @property
    def cases_dir(self) -> Path:
        """cases/ 目錄路徑，預設為 plugin 同層的 cases/。"""
        return Path(__file__).parent / "cases"

    @abstractmethod
    def discover_cases(self) -> list[dict[str, Any]]:
        """掃描 cases/ 目錄，回傳所有 test case 描述（已解析的 YAML dict）。"""

    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        """依 case 描述佈建測試環境（DUT/STA/EndpointPC）。

        預設實作直接回傳 True（不需佈建）。子類別可覆寫。

        Returns:
            True if setup succeeded.
        """
        return True

    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        """環境自檢：驗證連線、服務就緒。

        預設實作直接回傳 True（不需驗證）。子類別可覆寫。

        Returns:
            True if environment is ready.
        """
        return True

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

    def teardown(self, case: dict[str, Any], topology: Any) -> None:
        """清理測試環境。預設為 no-op；子類別可覆寫。"""

    # -- optional overridable reporter -----------------------------------------

    def create_reporter(self) -> Any:
        """Return a reporter instance for this plugin.

        Defaults to None (use orchestrator default). Override to provide
        a plugin-specific reporter implementing the IReporter protocol.
        """
        return None

    def report_formats(self) -> list[str]:
        """Return the output formats this plugin supports.

        Defaults to ['xlsx']. Plugins may override to add 'md', 'json', etc.
        """
        return ["xlsx"]

    # -- optional overridable pipeline -----------------------------------------

    def run_pipeline(
        self,
        case: dict[str, Any],
        topology: Any,
    ) -> dict[str, Any]:
        """Execute the full case pipeline: setup → verify → steps → evaluate → teardown.

        Plugins may override this to customise execution order or add
        additional phases.  The default implementation mirrors the
        ExecutionEngine contract.
        """
        commands: list[str] = []
        outputs: list[str] = []
        verdict = False
        comment = ""

        try:
            if not self.setup_env(case, topology):
                return {"verdict": False, "comment": "setup_env failed", "commands": [], "outputs": []}
            if not self.verify_env(case, topology):
                return {"verdict": False, "comment": "env_verify gate failed", "commands": [], "outputs": []}

            step_results: dict[str, Any] = {}
            raw_steps = case.get("steps", [])
            steps = raw_steps if isinstance(raw_steps, list) else []
            for step in steps:
                step_data = dict(step) if isinstance(step, dict) else {"id": "step", "command": str(step)}
                step_id = str(step_data.get("id", "step"))
                cmd = str(step_data.get("command", "")).strip()
                if cmd:
                    commands.append(cmd)
                result = self.execute_step(case, step_data, topology)
                step_results[step_id] = result
                out = str(result.get("output", "")).strip()
                if out:
                    outputs.append(out)
                if not result.get("success", False):
                    comment = f"step failed: {step_id}"
                    break

            if not comment:
                verdict = self.evaluate(case, {"steps": step_results})
                if not verdict:
                    comment = "pass_criteria not satisfied"

        except Exception as exc:
            comment = f"exception: {exc}"
        finally:
            self.teardown(case, topology)

        return {
            "verdict": verdict,
            "comment": comment,
            "commands": commands,
            "outputs": outputs,
        }
