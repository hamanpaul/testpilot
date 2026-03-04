# TestPilot

Plugin-based test automation framework for embedded device verification.

## 概述

TestPilot 採用 `Orchestrator -> Plugin -> YAML Cases` 架構，目標是支援 prplOS/OpenWrt 裝置的可擴充測試流程。

## 目前能力（Current）

1. 可列出 plugin/cases，並執行 `wifi_llapi` 的報告導向流程。
2. 可從來源 Excel 抽取 `Wifi_LLAPI` 樣板並產出測試報告。
3. `wifi_llapi` 已有大量 case YAML 與 row/source 對齊治理。

注意：`wifi_llapi` plugin 的 `setup_env/verify_env/execute_step/evaluate` 目前仍屬 stub，尚未完成真實環境執行。

## Roadmap（Target）

1. 真實 transport（serial/adb/ssh/network）。
2. env provision/validate 與 monitor。
3. plugin evaluate + agent audit 合併判讀。
4. post-run remediation（測後修正/重測）。

詳見：`docs/plan.md` 與 `docs/todos.md`。

## CLI 快速開始

```bash
cd ~/prj_pri/testpilot
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# 探索
python -m testpilot.cli list-plugins
python -m testpilot.cli list-cases wifi_llapi

# 建立 Wifi_LLAPI template
python -m testpilot.cli wifi-llapi build-template-report \
  --source-xlsx "/mnt/c/Users/paul_chen/Downloads/0302-AT&T_LLAPI_Test_Report_20260107.xlsx"

# 執行 wifi_llapi
python -m testpilot.cli run wifi_llapi \
  --dut-fw-ver BGW720-B0-403 \
  --report-source-xlsx "/mnt/c/Users/paul_chen/Downloads/0302-AT&T_LLAPI_Test_Report_20260107.xlsx"
```

## 報告策略（雙軌）

1. Agent 分析用：Markdown/JSON（規劃中）。
2. 對外交付用：Excel（`Wifi_LLAPI` 樣式，已落地）。

## Plugin Agent/Model 配置

每個 plugin 可於自身目錄放置 `agent-config.yaml`，用於宣告 CLI agent/model 優先序。

`wifi_llapi` 目前規格：

1. 第一優先：`codex + gpt-5.3-codex + high`
2. 第二優先：`copilot + sonnet-4.6 + high`
3. 第一優先不可用時，自動降級第二優先（需留 trace）

## 專案結構

```text
testpilot/
├── src/testpilot/
│   ├── cli.py
│   ├── core/
│   ├── reporting/
│   ├── schema/
│   ├── transport/
│   └── env/
├── plugins/
│   └── wifi_llapi/
│       ├── plugin.py
│       ├── agent-config.yaml
│       ├── cases/
│       └── reports/
├── configs/
├── docs/
└── tests/
```

## 開發說明

1. Plugin 開發指南：`docs/plugin-dev-guide.md`
2. 主計畫：`docs/plan.md`
3. 待辦看板：`docs/todos.md`

## License

MIT
