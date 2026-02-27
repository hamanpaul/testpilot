# Phase 0: 專案骨架

## 目標

建立 TestPilot 最小可執行骨架，包含：
- 完整目錄結構與 pyproject.toml
- PluginBase ABC + PluginLoader 動態載入
- YAML case schema 驗證
- Testbed config 解析與變數替換
- Transport ABC + StubTransport
- 最小 CLI（`testpilot --version`、`list-plugins`、`list-cases`）
- 最小 Orchestrator（載入 plugin、列出 cases）
- wifi_llapi plugin stub + 2 條範例 case YAML
- docs/ 文件

## 驗收標準

1. `testpilot --version` 正常輸出
2. `testpilot list-plugins` 列出 wifi_llapi
3. `testpilot list-cases wifi_llapi` 列出 getRadioStats、kickStation
4. `pytest` 基礎測試通過
5. push 至 GitHub

## 交付物

- `~/testpilot/` 完整專案
- GitHub repo: `testpilot`
