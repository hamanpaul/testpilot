# TestPilot Master Plan（現況對齊版）

## 1. 目標

TestPilot 是一套 plugin-based 嵌入式測試框架，核心目標是：

1. 以 YAML 驅動 DUT/STA/Endpoint 的測試流程。
2. 將可預期規則判讀與預期外異常判讀分離。
3. 以可追蹤的方式產出兩類報告：
   - 給 Agent：Markdown/JSON（除錯與重測依據）
   - 對外交付：Excel（依 Wifi_LLAPI 樣式）

---

## 2. 現況快照（2026-03-04）

### 2.1 已落地能力

1. CLI 基本入口與子命令：`list-plugins`、`list-cases`、`run`、`wifi-llapi build-template-report`。
2. Orchestrator 可執行 `wifi_llapi` 專屬報表流程（template 生成、alignment gate、run report 輸出）。
3. `wifi_llapi` case 已大量整理並對齊 Excel `Wifi_LLAPI` row/source。
4. Excel 報告模組已獨立於 `src/testpilot/reporting/wifi_llapi_excel.py`。
5. 基礎測試包含 schema/loader 與 wifi llapi excel template 測試。

### 2.2 尚未完整落地（仍為 roadmap）

1. `wifi_llapi` plugin 執行 hook（`setup_env/verify_env/execute_step/evaluate`）目前仍為 stub。
2. `serial/adb/ssh/network` 真實 transport 尚未完成。
3. monitor / remediation / integration 測試仍待補齊。

---

## 3. 核心設計決策

### 3.1 判讀責任分層（不衝突）

1. `plugin.evaluate()`：主判可預期條件（pass criteria）。
2. `agent audit`：補判預期外問題（例如 RSSI 來自錯誤 STA 身份）。
3. 合併裁決：`Pass` / `Fail` / `Inconclusive`。

### 3.2 監控與修復策略（不衝突）

1. 測試過程發現異常可先記錄，不必立即中止所有測項。
2. 測試結束後由 Agent 進行修正、調整與重測（post-run remediation loop）。

### 3.3 報告雙軌（不衝突）

1. Agent 分析報告：Markdown/JSON。
2. 人工/對外交付報告：`Wifi_LLAPI` Excel 樣式。

---

## 4. Plugin 級 CLI Agent / Model 選擇策略

### 4.1 配置位置

每個 plugin 可在自身目錄宣告：

- `plugins/<plugin>/agent-config.yaml`

### 4.2 優先序規範（目前強制於 wifi_llapi）

第一優先：`codex + gpt-5.3-codex + high`  
第二優先：`copilot + sonnet-4.6 + high`

### 4.3 YAML 規格

```yaml
version: 1
default_mode: headless
selection_policy:
  fallback: automatic
  on_unavailable: next_priority
runners:
  - priority: 1
    cli_agent: codex
    model: gpt-5.3-codex
    effort: high
    enabled: true
  - priority: 2
    cli_agent: copilot
    model: sonnet-4.6
    effort: high
    enabled: true
```

### 4.4 選擇規則

1. 依 `priority` 由小到大選擇。
2. 第一優先不可用時，自動降級到第二優先。
3. 每次選擇需留存 `selection trace`（選擇結果、降級原因、時間戳）。

---

## 5. 目前目錄與模組（實際對齊）

```text
src/testpilot/
  cli.py
  core/
    orchestrator.py
    plugin_base.py
    plugin_loader.py
    testbed_config.py
  reporting/
    wifi_llapi_excel.py
  schema/
    case_schema.py
  transport/
    base.py
  env/
    __init__.py

plugins/wifi_llapi/
  plugin.py
  agent-config.yaml
  cases/*.yaml
  reports/

docs/
  plan.md
  todos.md
  plugin-dev-guide.md
  phases/phase0~phase5.md
  enhance-plan-v1.md  # 歷史設計與實作記錄
```

---

## 6. Phase 與交付邊界

以 `docs/todos.md` 為唯一進度看板，以下為 phase 定義：

1. Phase 0：骨架與基礎能力（已完成大部分）。
2. Phase 1：transport 真實化（serial/adb/ssh/network）。
3. Phase 2：env 管理（topology/provisioner/validator）。
4. Phase 3：核心引擎（test-runner/monitor/reporter + verdict merge）。
5. Phase 4：wifi_llapi 完整執行實作（非 stub）。
6. Phase 5：CLI 與整合測試（含 agent selection trace）。

---

## 7. 文件治理規則

1. `docs/todos.md` 是唯一待辦與狀態來源。
2. 非 Plan Mode 不得增減 `docs/todos.md` 項次，只能更新狀態。
3. Plan Mode 才可調整項次與 phase 結構。
4. 任何規劃更新需同步檢查：`plan.md`、`todos.md`、`README.md`、`AGENTS.md`。

---

## 8. 與 enhance-plan-v1 的關係

`docs/enhance-plan-v1.md` 的 Wifi_LLAPI Excel pipeline 已被整併到本計畫。  
後續以 `docs/plan.md` 為主，`enhance-plan-v1.md` 保留歷史追溯用途。
