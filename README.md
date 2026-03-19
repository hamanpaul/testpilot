# TestPilot

Plugin-based test automation framework for embedded device verification.

## 概述

TestPilot 目前以 `wifi_llapi` 為主要落地路徑，並朝第三次重構方向演進為：

- **Deterministic verdict kernel**：`Orchestrator -> Plugin -> YAML Cases -> Transport -> Structured Evidence -> Report Projection`
- **Copilot SDK control plane**：`sessions / resume / hooks / custom agents / skills / selective MCP`

這個方向的核心原則是：**Copilot SDK 負責 control plane，不負責最終 verdict**。

## 目前能力（Current）

1. 可列出 plugin / cases，並執行 `wifi_llapi` 的報告導向流程。
2. 可從來源 Excel 抽取 `Wifi_LLAPI` 樣板並產出測試報告。
3. `wifi_llapi` 已有大量 case YAML 與 row/source 對齊治理。
4. `wifi_llapi` 已支援 per-case dispatcher（sequential）與 per-case trace 輸出。
5. 已支援 retry-aware timeout（依 attempt 調整）與 case fail-and-continue。
6. `wifi_llapi` plugin `setup_env / verify_env / execute_step / evaluate` 已完成 runtime 實作，可接 transport 執行。
7. transport 已具備 `serialwrap / adb / ssh / network`，並完成 row-indexed 官方 415 discoverable cases 實機全量 run 驗證。
8. 兩個 duplicate-row legacy YAML 已改為 underscore-prefixed compatibility fixtures，保留 explicit load 能力，但不再混入 `list-cases` / `discover_cases`。
9. `wifi_llapi` 目前已固化 135 筆 trusted/calibrated cases，尚餘 280 筆待校正；目前明確 blockers 為 `D037 OperatingStandard`、`D054 Tx_RetransmissionsFailed`、`D055 TxBytes`。
10. 報告檔名已帶 `run_id`，避免覆蓋既有 run；xlsx H 欄會自動清理 serialwrap marker/prompt。
11. 已提供 `wifi-llapi audit-yaml-commands` dry-run 工具，稽核 YAML 中 `&&` / `;` 串接指令。
12. 第三次重構的 Copilot SDK 深度研究已同步到 `docs/copilot-sdk-hooks-skills-session-resume-persistenc.md`。
13. 逐案校正的 repo handoff 以 `docs/audit-todo.md` 與 `plugins/wifi_llapi/reports/audit-report-260313-185447.md` 為主；目前 handoff 已補記 `D060 UNIIBandsCapabilities`、`D061 UplinkBandwidth`、`D062 UplinkMCS`、`D063 UplinkShortGuard`、`D064 VendorOUI`、`D065 VhtCapabilities`、`D066 APBridgeDisable`、`D067 BridgeInterface`、`D068 DiscoveryMethodEnabled (FILS)`、`D069 DiscoveryMethodEnabled (UPR)`、`D070 DiscoveryMethodEnabled (RNR)`、`D072 Enable`、`D073 FTOverDSEnable`、`D074 MobilityDomain`、`D077 InterworkingEnable`、`D078 QoSMapSet` 的 committed checkpoint 與 `D185 TPCMode` targeted fail-shaped checkpoint。
14. reboot 後的預設 live baseline 已重建為 non-open：5G `testpilot5G` / 2.4G `testpilot2G` 使用 `WPA2-Personal + 00000000`，6G `testpilot6G` 固定使用 `WPA3-Personal + key_mgmt=SAE + 00000000`；`D078 QoSMapSet` 已在這組 baseline 下完成 AP-only multiband `Not Supported` checkpoint（workbook row 70；AP1/AP3/AP5 的 baseline getter / hostapd config 都是 `EMPTY / ABSENT`，寫入請求 DSCP map 後 northbound getter 與 hostapd 都只收斂成 scalar `255` / `qos_map_set=255`，最後 clear path 回到 `EMPTY / ABSENT`），下一個 ready case 為 `D079 MacFilterAddressList`。

## 第三次重構方向（Target）

1. 以 Copilot SDK 作為正式 agent runtime / control plane。
2. 保留 deterministic kernel，避免把 YAML 直接變成主要 prompt。
3. 將 advisory audit、remediation planning、run summary 交給 Copilot agents。
4. 保持 `xlsx = Pass/Fail only`、`md/json = richer diagnostics`。
5. 不再以 Codex CLI 相容性為目標，不引入 workaround code。

詳見：`docs/plan.md`、`docs/todos.md`、`docs/spec.md`、`docs/copilot-sdk-hooks-skills-session-resume-persistenc.md`。

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
# 依實際環境修改 configs/testbed.yaml（DUT / STA / Endpoint）
```

`wifi_llapi` 常見使用 `DUT: transport: serial`，可用 `serial_port` / `selector` / `alias` / `session_id` 對應 serialwrap session。

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
  --dut-fw-ver BGW720-B0-403
```

全量執行（預設會跑官方 row-indexed `wifi-llapi-D###`，目前 415 discoverable cases；underscore-prefixed legacy fixtures 不會被自動掃入）：

```bash
python -m testpilot.cli run wifi_llapi \
  --dut-fw-ver BGW720-B0-403
```

`run wifi_llapi` 會優先使用既有的 `plugins/wifi_llapi/reports/templates/wifi_llapi_template.xlsx`。
只有在你要第一次建立 / 重新整理 template 時，才需要提供 `--report-source-xlsx <原始 Excel>`。

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

### 8) 常見錯誤

若出現 `ModuleNotFoundError: testpilot`，先確認已執行 `uv pip install -e ".[dev]"`。  
臨時排查可改用：`PYTHONPATH=src python -m testpilot.cli ...`

## 報告策略（雙軌）

1. 對外交付：`xlsx`（`Pass` / `Fail` only）
2. 內部診斷：`md/json`（規劃中，承載 detailed status / root cause / suggestion / remediation history）

## 第三次重構目標 Agent / Model Policy

> 此節描述第三次重構的 target policy，而不是舊的 Codex CLI 相容策略。

1. 第一優先：`copilot + gpt-5.4 + high`
2. 第二優先：`copilot + sonnet-4.6 + high`
3. 第三優先：`copilot + gpt-5-mini + high`
4. 執行模式：`per_case + sequential(max_concurrency=1)`
5. 失敗策略：`retry_then_fail_and_continue`，timeout 會隨 retry attempt 調整
6. 第一優先不可用時可自動降級，但必須保留 `selection trace`
7. 不再維持 Codex CLI workaround layer

## 專案結構

```text
testpilot/
├── README.md
├── AGENTS.md
├── docs/
│   ├── plan.md
│   ├── spec.md
│   ├── todos.md
│   └── copilot-sdk-hooks-skills-session-resume-persistenc.md
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
├── scripts/
└── tests/
```

## 開發文件

1. 系統規格：`docs/spec.md`
2. 主計畫：`docs/plan.md`
3. 待辦看板：`docs/todos.md`
4. 校正交接／恢復入口：`docs/audit-todo.md`
5. 校正證據報告：`plugins/wifi_llapi/reports/audit-report-260313-185447.md`
6. Copilot SDK 第三次重構研究：`docs/copilot-sdk-hooks-skills-session-resume-persistenc.md`

## License

MIT
