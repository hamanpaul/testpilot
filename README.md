# TestPilot

Plugin-based test automation framework for embedded device verification.

## 概述

TestPilot 是一套可擴充的自動化測試框架，以 Orchestrator → Plugin → YAML Case Descriptor 三層架構，
支援多裝置協調測試（DUT、STA、EndpointPC），適用於 OpenWrt/prplOS 嵌入式網路裝置的韌體驗證。

## 架構

```
Orchestrator ─→ Plugin (wifi_llapi, qos_llapi, sigma_qt, ...)
                  │
                  ├─ cases/*.yaml   ← 測試項目描述
                  │
                  └─ Transport Layer (serial / adb / ssh / network)
                       │         │        │
                     [DUT]     [STA]  [EndpointPC]
```

## 快速開始

```bash
# 安裝
cd ~/testpilot
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# 列出 plugins
testpilot list-plugins

# 列出 test cases
testpilot list-cases wifi_llapi

# 執行測試（skeleton）
testpilot run wifi_llapi
```

## Plugin 開發

參考 `docs/plugin-dev-guide.md` 與 `plugins/wifi_llapi/` 範例。

每個 plugin 需要：
1. `plugins/<name>/plugin.py` — 繼承 `PluginBase`，定義 `Plugin` 類別
2. `plugins/<name>/cases/*.yaml` — 測試項目 YAML 描述檔

## 專案結構

```
testpilot/
├── src/testpilot/       # 核心引擎
│   ├── core/            # orchestrator, plugin_base, test_runner, monitor, reporter
│   ├── transport/       # serial, adb, ssh, network
│   ├── env/             # topology, provisioner, validator
│   └── schema/          # YAML case schema
├── plugins/             # 測試 plugins
├── configs/             # 測試台設定
├── reports/             # 測試報告（auto-generated）
├── tests/               # 單元測試
└── docs/                # 文件與計畫
```

## License

MIT
