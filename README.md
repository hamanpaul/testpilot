# TestPilot

Plugin-based test automation framework for embedded device verification.

## 概述

TestPilot 採用 `Orchestrator -> Plugin -> YAML Cases` 架構，目標是支援 prplOS/OpenWrt 裝置的可擴充測試流程。

## 目前能力（Current）

1. 可列出 plugin/cases，並執行 `wifi_llapi` 的報告導向流程。
2. 可從來源 Excel 抽取 `Wifi_LLAPI` 樣板並產出測試報告。
3. `wifi_llapi` 已有大量 case YAML 與 row/source 對齊治理。
4. `wifi_llapi` 已支援 per-case agent dispatcher（sequential）與 per-case trace 輸出。
5. 已支援 retry-aware timeout（依 attempt 調整）與 case fail-and-continue。
6. `wifi_llapi` plugin `setup_env/verify_env/execute_step/evaluate` 已完成 runtime 實作，可接 transport 執行。
7. transport 已具備 `serialwrap/adb/ssh/network`，並完成 row-indexed 官方 415 cases 實機全量 run 驗證。
8. 報告檔名已帶 `run_id`，避免覆蓋既有 run；xlsx H 欄會自動清理 serialwrap marker/prompt。
9. 已提供 `wifi-llapi audit-yaml-commands` dry-run 工具，稽核 YAML 中 `&&`/`;` 串接指令。

## Roadmap（Target）

1. 真實 transport（serial/adb/ssh/network）。
2. env provision/validate 與 monitor。
3. plugin evaluate + agent audit 合併判讀。
4. post-run remediation（測後修正/重測）。

詳見：`docs/plan.md` 與 `docs/todos.md`。

## Usage

### 1) 環境準備

```bash
cd testpilot
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m testpilot.cli --version
```

### 2) 設定 testbed（首次）

```bash
cp configs/testbed.yaml.example configs/testbed.yaml
# 依實際環境修改 configs/testbed.yaml（DUT/STA/Endpoint）
```

`wifi_llapi` 常見使用 `DUT: transport: serial`，可用 `serial_port`/`selector`/`alias`/`session_id` 對應 serialwrap session。

### 3) 驗證環境與案例列表

```bash
# 建議先確認 serialwrap session 狀態
serialwrap session list | jq '.sessions[] | {session_id, com, alias, state, device_by_id, real_path}'

# 探索 plugin / cases
python -m testpilot.cli list-plugins
python -m testpilot.cli list-cases wifi_llapi
```

### 4) 建立 Wifi_LLAPI 報告模板（可選）

```bash
python -m testpilot.cli wifi-llapi build-template-report \
  --source-xlsx "0302-AT&T_LLAPI_Test_Report_20260107.xlsx"
```

### 5) 執行 wifi_llapi 測試

先跑單一 case（smoke）：

```bash
python -m testpilot.cli run wifi_llapi \
  --case wifi-llapi-D006-kickstation \
  --dut-fw-ver BGW720-B0-403 \
  --report-source-xlsx "0302-AT&T_LLAPI_Test_Report_20260107.xlsx"
```

全量執行（預設會跑官方 row-indexed `wifi-llapi-D###`，目前 415 cases）：

```bash
python -m testpilot.cli run wifi_llapi \
  --dut-fw-ver BGW720-B0-403 \
  --report-source-xlsx "0302-AT&T_LLAPI_Test_Report_20260107.xlsx"
```

### 6) 產出檔案

1. Excel 報告：`plugins/wifi_llapi/reports/YYYYMMDD_<FW>_wifi_LLAPI_<run_id>.xlsx`
2. 每 case trace：`plugins/wifi_llapi/reports/agent_trace/<run_id>/`
3. 對齊失敗報告：`plugins/wifi_llapi/reports/alignment/*_alignment_issues.json`

### 7) YAML 指令稽核（dry-run）

```bash
python -m testpilot.cli wifi-llapi audit-yaml-commands \
  --out /tmp/wifi_llapi_command_audit.json
```

會掃描 `command`、`verification_command`、`hlapi_command`、`setup_steps`、`sta_env_setup`，
找出未被引號包住的 `&&` / `;` 串接，輸出建議拆分結果，不會直接覆寫 case YAML。

### 7) 常見錯誤

若出現 `ModuleNotFoundError: testpilot`，先確認已執行 `uv pip install -e ".[dev]"`。  
臨時排查可改用：`PYTHONPATH=src python -m testpilot.cli ...`

## 報告策略（雙軌）

1. Agent 分析用：Markdown/JSON（規劃中）。
2. 對外交付用：Excel（`Wifi_LLAPI` 樣式，已落地）。

## Plugin Agent/Model 配置

每個 plugin 可於自身目錄放置 `agent-config.yaml`，用於宣告 CLI agent/model 優先序。

`wifi_llapi` 目前規格：

1. 第一優先：`codex + gpt-5.3-codex + high`
2. 第二優先：`copilot + sonnet-4.6 + high`
3. 第一優先不可用時，自動降級第二優先（需留 trace）
4. 執行模式：`per_case + sequential(max_concurrency=1)`（已實作）
5. 失敗策略：`retry_then_fail_and_continue`，timeout 會隨 retry attempt 調整（已實作）

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
├── scripts/
│   ├── gen_cases.py
│   └── wifi_llapi_build_template_report.py
└── tests/
```

## 開發說明

1. Plugin 開發指南：`docs/plugin-dev-guide.md`
2. 主計畫：`docs/plan.md`
3. 待辦看板：`docs/todos.md`

## License

MIT
