# Plugin 開發指南

## 建立新 Plugin

1. 在 `plugins/` 下建立目錄：

```
plugins/
  your_plugin/
    __init__.py
    plugin.py
    cases/
      _template.yaml
      your_test.yaml
```

2. `plugin.py` 須定義 `Plugin` 類別，繼承 `PluginBase`：

```python
from testpilot.core.plugin_base import PluginBase
from testpilot.schema.case_schema import load_cases_dir

class Plugin(PluginBase):
    @property
    def name(self) -> str:
        return "your_plugin"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def cases_dir(self) -> Path:
        return Path(__file__).parent / "cases"

    def discover_cases(self):
        return load_cases_dir(self.cases_dir)

    def setup_env(self, case, topology) -> bool:
        # 佈建測試環境
        ...

    def verify_env(self, case, topology) -> bool:
        # 環境自檢
        ...

    def execute_step(self, case, step, topology) -> dict:
        # 執行單一測試步驟
        ...

    def evaluate(self, case, results) -> bool:
        # 評估通過條件
        ...

    def teardown(self, case, topology) -> None:
        # 清理環境
        ...
```

3. Plugin 會被 `PluginLoader` 自動發現（不需註冊）。

## Test Case YAML 結構

必要欄位：`id`, `name`, `topology`, `steps`, `pass_criteria`

```yaml
id: "unique-case-id"
name: "Human-readable name"
topology:
  devices:
    DUT:
      role: ap
      transport: serial
steps:
  - id: step1
    action: exec
    target: DUT
    command: "..."
pass_criteria:
  - field: result
    operator: "contains"
    value: "expected"
```

變數使用 `{{VAR}}` 語法，由 `configs/testbed.yaml` 的 `variables` 區塊替換。

## Transport 類型

| 類型 | 用途 | config key |
|------|------|-----------|
| serial | UART/serialwrap 控制 DUT | `transport: serial` |
| adb | ADB 控制 Android 手機 | `transport: adb` |
| ssh | SSH 控制 EndpointPC | `transport: ssh` |

參考 `plugins/wifi_llapi/` 與 `cases/_template.yaml`。
