# TestPilot Master Plan

> 更新日期：2026-03-10  
> 基線版本：v0.0.3-draft  
> 目標版本：v0.1.0

---

## 1. 目標

TestPilot 是一套 plugin-based 嵌入式測試框架，核心目標是：

1. 以 YAML 驅動 DUT/STA/Endpoint 的測試流程。
2. 將可預期規則判讀與預期外異常判讀分離。
3. 以可追蹋的方式產出兩類報告：
   - 給 Agent：Markdown/JSON（除錯與重測依據）
   - 對外交付：Excel（依 Wifi_LLAPI 樣式）
4. 以 Copilot SDK 整合 agent 能力，支援自然語言操作。

---

## 2. 現況快照（v0.0.3-draft, 2026-03-10）

### 2.1 已落地能力

1. CLI 入口：`list-plugins`、`list-cases`、`run`、`wifi-llapi build-template-report`。
2. Orchestrator 可執行 `wifi_llapi` 專屬報表流程。
3. 417 cases（415 官方 D### + 2 legacy），已對齊 Excel Wifi_LLAPI row/source。
4. Transport：serialwrap / adb / ssh / network 實作與工廠。
5. Per-case agent dispatcher + retry-aware timeout + selection trace。
6. 6G STA 穩定流程已驗證，415 YAML 批次更新。
7. Case ID 已對齊 `wifi-llapi-D###-*` 命名規則（舊 `r###` 保留為 alias）。
8. 46 tests 通過。
9. Report 檔名已帶 `run_id`，避免覆蓋既有結果；H 欄輸出已清理 serialwrap marker/prompt。
10. 已新增 `wifi-llapi audit-yaml-commands` dry-run 稽核工具，協助治理 YAML 串接指令。

### 2.2 尚未落地

1. monitor / remediation 全流程。
2. MD/JSON report。
3. Plugin 擴展需改 orchestrator（硬編碼問題）。

---

## 3. 核心設計決策

### 3.1 判讀責任分層

1. `plugin.evaluate()`：主判可預期條件（pass criteria）。
2. `agent audit`：補判預期外問題（post-run remediation）。
3. 合併裁決：`Pass` / `Fail` / `Inconclusive`。

### 3.2 報告雙軌

1. Agent 分析報告：Markdown/JSON（規劃中）。
2. 對外交付報告：Excel（已落地）。

### 3.3 Agent 執行策略（wifi_llapi）

- 粒度：per_case，每個 case 獨立 dispatcher。
- 排程：sequential（max_concurrency=1）。
- 失敗策略：retry_then_fail_and_continue。
- Timeout：`min(max_sec, (base + steps × per_step) × multiplier^(attempt-1))`。

---

## 4. 已識別隱患（深度研究 2026-03-10）

### 🔴 嚴重

| # | 隱患 | 位置 | 說明 |
|---|------|------|------|
| H1 | Orchestrator God Class | `orchestrator.py` (893L) | 混合 9 種職責，違反 SRP |
| H2 | wifi_llapi 硬編碼 | `orchestrator.run()` | 新 plugin 需改 orchestrator，違反 OCP |
| H3 | Report 覆蓋無防呆 | `wifi_llapi_excel.py` | `shutil.copy2` 直接覆蓋 |
| H4 | Serialwrap marker 洩漏 | `plugin.py` H 欄 | report 含 `__TP_*`、`root@prplOS` |
| H5 | YAML 多指令單行 | `cases/*.yaml` | `cmd1 && cmd2 ; cmd3` 不利除錯 |
| H6 | Plugin 巨型單檔 | `plugin.py` (1202L) | 混合指令/解析/環境/評估/transport |
| H7 | RC 擷取用 LAST match | `serialwrap.py` L424 | 多 marker 時可能取錯 return code |

### 🟡 中等

| # | 隱患 | 說明 |
|---|------|------|
| H8 | Retry 只保留最後結果 | report 只呈現最後 attempt |
| H9 | sys.path 污染 | plugin 目錄直接加入 sys.path |
| H10 | openpyxl 私用 API | 直接操作 `ws._cells` |
| H11 | Agent runtime 非實際呼叫 | 有 selector 但不呼叫 LLM |
| H12 | Session 解析 6+ fallback | 可能靜默選錯裝置 |
| H13 | MD/JSON report 缺失 | 規劃雙軌但只有 xlsx |
| H14 | PluginBase 介面過胖 | 7 abstract methods，不是都需要 |

---

## 5. v0.1.0 重構方案

### Phase R1：指令格式與 Report 清理（低風險）

| ID | 項目 | 對應 | 說明 |
|---|------|------|------|
| R1-01 | Report 保存不覆蓋 | H3 | 檔名加 run_id，舊報告保留 |
| R1-02 | Report output 清理 marker | H4 | sanitize_output() 清除 serialwrap 殘留 |
| R1-03 | Report cmd 欄單行化 | 需求 | G 欄每條指令一行 |
| R1-04 | YAML 指令單行化工具 | H5 | 批次拆 `&&`/`;` 串接 |

### Phase R2：Orchestrator 解耦（中風險）

| ID | 項目 | 對應 | 說明 |
|---|------|------|------|
| R2-01 | 拆分 Orchestrator | H1 | CaseDiscovery / TestRunner / RetryPolicy / ReportCoordinator |
| R2-02 | Plugin 自宣告執行流程 | H2 | PluginBase.run_pipeline() |
| R2-03 | Plugin 自宣告 Reporter | H2 | PluginBase.create_reporter() |
| R2-04 | Retry 歷史保留 | H8 | 所有 attempt 結果存入 list |

### Phase R3：Plugin Template（中風險）

| ID | 項目 | 對應 | 說明 |
|---|------|------|------|
| R3-01 | 乾淨 plugin template | 需求 | plugins/_template/ 完整骨架 |
| R3-02 | Plugin scaffold CLI | 需求 | `testpilot create-plugin <name>` |
| R3-03 | Plugin 拆檔示範 | H6 | executor / evaluator / environment / output_parser |
| R3-04 | PluginBase 瘦身 | H14 | 拆為 Executable / EnvironmentManager / Evaluator protocol |

### Phase R4：自然語言執行介面（中高風險）

| ID | 項目 | 對應 | 說明 |
|---|------|------|------|
| R4-01 | Copilot SDK 整合 | 需求 | 取代 dummy agent runtime |
| R4-02 | 自然語言 case 選擇 | 需求 | `testpilot '測試D273的測試項'` |
| R4-03 | 自然語言 plugin 建立 | 需求 | agent 從 xlsx 產生 plugin |
| R4-04 | Hook 確認測試完成 | 需求 | callback 通知 agent |

### Phase R5：可靠性與測試補強（低風險）

| ID | 項目 | 對應 | 說明 |
|---|------|------|------|
| R5-01 | serialwrap RC 修正 | H7 | FIRST match 取代 LAST |
| R5-02 | Plugin loader 改良 | H9 | 移除 sys.path 污染 |
| R5-03 | openpyxl API 隔離 | H10 | 封裝進 adapter |
| R5-04 | Session 解析簡化 | H12 | 減少 fallback 層數 |
| R5-05 | 測試覆蓋 >80% | 品質 | 補邊界條件與 CLI integration |
| R5-06 | MD/JSON report | H13 | agent 分析用報告 |

### 執行順序

```
R1（Report/指令清理）→ R2（Orchestrator 解耦）→ R3（Plugin Template）→ R4（Copilot SDK）
                                                    ↘ R5（可靠性補強）穿插進行
```

### SOLID 原則對照

| 原則 | 現狀問題 | 重構對應 |
|------|----------|----------|
| **S**RP | Orchestrator / Plugin 各混合多種職責 | R2-01 / R3-03 |
| **O**CP | 新 plugin 需改 orchestrator | R2-02 |
| **L**SP | Transport 介面不統一 | R3-04 + R5-02 |
| **I**SP | PluginBase 7 abstract methods 過胖 | R3-04 |
| **D**IP | Orchestrator 直接 import 具體 reporting | R2-03 |

---

## 6. 已完成的 Phase（歷史）

| Phase | 內容 | 狀態 |
|-------|------|------|
| P0 | Scaffold（目錄/pyproject/plugin-base/schema/cli） | done |
| P1 | Transport Layer（serialwrap/adb/ssh/network） | done |
| P2 | Environment Management（topology/provisioner/validator） | pending |
| P3 | Core Engine（runner loop/monitor/reporter/verdict merge） | partial |
| P4 | Wifi_LLAPI Plugin（完整實作 + 415 case run） | done |
| P5 | CLI & Integration（agent dispatcher/retry/trace/tests） | done |

---

## 7. 文件治理規則

1. `docs/todos.md` 是唯一待辦與狀態來源。
2. `docs/spec.md` 是系統規格書（含架構圖、時序圖、流程圖）。
3. 非 Plan Mode 不得增減 `todos.md` 項次。
4. 任何規劃更新需同步：`plan.md`、`todos.md`、`spec.md`、`README.md`、`AGENTS.md`。

---

## 8. 風險與注意事項

1. **向後相容**：R2 拆 orchestrator 時確保 `testpilot run wifi_llapi` 行為不變。
2. **415 YAML 批次修改**：R1-04 如改 schema 需批次遷移工具。
3. **Copilot SDK 成熟度**：R4 需確認 SDK 穩定性。
4. **不提交敏感資訊**：JSON dump、report output、agent trace、機台/客戶資訊一律不進 git。
