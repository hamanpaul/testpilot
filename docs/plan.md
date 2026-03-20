# TestPilot Master Plan

> 更新日期：2026-03-19
> 基線版本：v0.0.3-draft  
> 規劃版本：v0.1.0（第三次重構基線）

---

## 1. 目標

TestPilot 的主目標是：

1. 以 YAML 驅動 DUT / STA / Endpoint 的 deterministic 測試流程。
2. 以 structured evidence 固化每次 run / case / retry 的正式結果。
3. 將 `xlsx` 對外交付報告與 `md/json` 診斷報告分離。
4. 以 Copilot SDK 承接 control-plane 與 operator UX，而不是接管最終 verdict。
5. 在不引入 Codex CLI workaround 的前提下，完成第三次重構。

---

## 2. 現況快照（2026-03-19）

### 2.1 已落地能力

1. CLI 入口：`list-plugins`、`list-cases`、`run`、`wifi-llapi build-template-report`。
2. `wifi_llapi` 已有報表導向 run path 與 row/source 對齊治理。
3. Transport：serialwrap / adb / ssh / network 已實作。
4. Per-case dispatcher、selection trace、retry-aware timeout、attempt trace 已落地。
5. 正式 hot path 仍由 `setup_env -> verify_env -> execute_step -> evaluate` 決定。
6. 415 官方 row-indexed cases 已有實機全量驗證基線；兩個 duplicate-row legacy YAML 已改為 underscore-prefixed compatibility fixtures，不再混入 discoverable case inventory。
7. `wifi_llapi` 目前已固化 146 筆 trusted/calibrated official cases，尚餘 269 筆待校正；目前明確 blockers 為 `D037 OperatingStandard`、`D054 Tx_RetransmissionsFailed`、`D055 TxBytes`，但目前先不插回主 queue，等其餘 sequential 校正收斂後再回頭處理。
8. repo-only 校正 handoff 已同步到 `docs/audit-todo.md` 與 `plugins/wifi_llapi/reports/audit-report-260313-185447.md`；目前 handoff 已補記 `D060 UNIIBandsCapabilities`、`D061 UplinkBandwidth`、`D062 UplinkMCS`、`D063 UplinkShortGuard`、`D064 VendorOUI`、`D065 VhtCapabilities`、`D066 APBridgeDisable`、`D067 BridgeInterface`、`D068 DiscoveryMethodEnabled (FILS)`、`D069 DiscoveryMethodEnabled (UPR)`、`D070 DiscoveryMethodEnabled (RNR)`、`D072 Enable`、`D073 FTOverDSEnable`、`D074 MobilityDomain`、`D077 InterworkingEnable`、`D078 QoSMapSet`、`D079 MacFilterAddressList`、`D080 Entry`、`D081 Mode`、`D082 MaxAssociatedDevices`、`D083 MBOEnable`、`D084 MultiAPType`、`D085 Neighbour`、`D086 EncryptionMode` 的 committed checkpoint，並已將 `D185 TPCMode`、`D368 SRGBSSColorBitmap`、`D371 SRGPartialBSSIDBitmap` 這三筆 official checkpoint 納入完成數，從待校正池移出。
9. reboot 後的 default lab baseline 已重建並落成文件：5G `testpilot5G` / 2.4G `testpilot2G` 使用 `WPA2-Personal + 00000000`，6G `testpilot6G` 固定使用 `WPA3-Personal + key_mgmt=SAE + 00000000`；`D086 EncryptionMode` 已在這組 baseline 下完成 AP-only multiband `Not Supported` checkpoint（workbook row 78；AP1/AP3/AP5 的 getter 都固定回 `EncryptionMode="Default"`，但 `/tmp/wl{0,1,2}_hapd.conf` 仍明確暴露 `WPA-PSK/SAE + CCMP` 的真實 security lines，符合 workbook `hardcode in pwhm`），主 sequence 的下一個 ready single-case 入口為 `D087 KeyPassPhrase`。
10. 第三次重構的 Copilot SDK 深度研究已完成，並已複製到 `docs/copilot-sdk-hooks-skills-session-resume-persistenc.md`。

### 2.2 尚未落地

1. Copilot SDK session / hooks / custom agents / skills runtime 整合。
2. MD/JSON diagnostic projector。
3. structured remediation planner + whitelist executor + rerun gate。
4. `plugins/wifi_llapi/agent-config.yaml` 與新 policy 的 runtime 對齊。
5. 將 plugin fallback heuristic 收斂為更 schema/evidence-driven 的 path。

---

## 3. 不可改變的設計決策

### 3.1 Control plane / verdict plane 分層

- **Copilot SDK control plane**：session、resume、hooks、custom agents、skills、selective MCP、operator UX。
- **Deterministic verdict kernel**：YAML semantics、transport execution、pass criteria comparison、canonical result、report projection。

### 3.2 Final verdict authority

- `plugin.evaluate()` 與 deterministic rerun outcome 才能決定最終 `Pass/Fail`。
- advisory agent 可以補充 root cause / suggestion / diagnostic status，但不可覆寫 canonical evidence。

### 3.3 報告投影分離

- `xlsx`：Pass / Fail only
- `md/json`：`PassAfterRemediation`、`FailEnv`、`FailConfig`、`FailTest`、`Inconclusive` + root cause + suggestion

### 3.4 Agent / model policy（第三次重構目標）

1. Priority 1：`copilot + gpt-5.4 + high`
2. Priority 2：`copilot + sonnet-4.6 + high`
3. Priority 3：`copilot + gpt-5-mini + high`
4. 不再維持 Codex CLI workaround 相容層。

### 3.5 執行策略不變

- 粒度：`per_case`
- 排程：`sequential (max_concurrency=1)`
- 失敗策略：`retry_then_fail_and_continue`
- Timeout：retry-aware、cap 保留
- Selection trace：mandatory

---

## 4. 第三次重構 Phase

### Phase R4：Copilot SDK 控制平面

| ID | 項目 | 輸出 | 狀態 |
|---|---|---|---|
| R4-00 | 第三次重構研究 / 文件基線 | 研究報告與 docs sync 完成 | done |
| R4-01 | Copilot SDK session foundation | create / resume / list / delete / workspace policy | in_progress |
| R4-02 | hook policy layer | `on_session_start` / `on_pre_tool_use` / `on_post_tool_use` / `on_error_occurred` | pending |
| R4-03 | custom agents roles | operator / case-auditor / remediation-planner / run-summarizer | pending |
| R4-04 | skills packages | diagnostics / remediation policy / report style | pending |
| R4-05 | advisory agent outputs | per-case audit / run summary / md draft generation | pending |
| R4-06 | remediation planner loop | structured JSON plan + whitelist executor + rerun gate | pending |
| R4-07 | runtime policy alignment | plugin agent-config / runner policy 改為 copilot-only order | done |
| R4-08 | selective MCP | GitHub / KB / lab inventory 等非熱路徑工具 | pending |

### Phase R5：Deterministic kernel 補強

| ID | 項目 | 輸出 | 狀態 |
|---|---|---|---|
| R5-01 | serialwrap RC 擷取修正 | FIRST match return code | done |
| R5-02 | Plugin loader 改良 | 移除 `sys.path` 污染 | pending |
| R5-03 | openpyxl API 隔離 | 封裝進 adapter | pending |
| R5-04 | Session / device binding 嚴格化 | 減少 fallback、避免靜默選錯裝置 | pending |
| R5-05 | 測試覆蓋 >80% | 補邊界條件與 CLI integration | pending |
| R5-06 | MD/JSON report projector | canonical result → md/json 實作 | pending |
| R5-07 | `execute_step` heuristic 收斂 | 減少自由文字 fallback，回到 schema/evidence 驅動 | pending |
| R5-08 | control-plane / verdict-plane 邊界測試 | 確保 Copilot 不直接決定最終 pass/fail | pending |

### 4.3 舊 Phase 的位置

- R1：Report / 指令清理（低風險，已大幅落地）
- R2：Orchestrator 解耦（仍重要）
- R3：Plugin Template / PluginBase 瘦身（仍重要）
- R4：第三次重構，正式導入 Copilot SDK control plane
- R5：第三次重構期間同步進行的 kernel hardening

### 執行順序

```text
R1 / R2 / R3 kernel 邊界整理
    -> R4-01 ~ R4-04 control-plane foundation
    -> R5-04 / R5-07 / R5-08 kernel boundary hardening
    -> R4-05 / R4-06 advisory audit + remediation
    -> R4-08 selective MCP
```

---

## 5. 歷史 Phase（摘要）

| Phase | 內容 | 狀態 |
|---|---|---|
| P0 | Scaffold（目錄 / pyproject / loader / schema / cli） | done |
| P1 | Transport Layer（serialwrap / adb / ssh / network） | done |
| P2 | Environment Management（topology / provisioner / validator） | partial |
| P3 | Core Engine（runner loop / monitor / reporter / verdict merge） | partial |
| P4 | Wifi_LLAPI Plugin（完整 runtime + cases） | done |
| P5 | CLI & Integration（dispatcher / trace / retry / tests） | done |

---

## 6. 風險與 Gate

1. **Copilot SDK 為 technical preview**：先導入 control plane，再逐步放大使用範圍。
2. **不可把 YAML 當主要 prompt**：正式測試仍由 kernel 執行。
3. **不可讓 advisory output 直接變更 verdict**：必須經 whitelist remediation + deterministic rerun。
4. **不得為舊 Codex CLI policy 補 workaround**：新 policy 以 Copilot SDK 為主體。
5. **文件與政策需一致化**：`spec.md`、`plan.md`、`todos.md`、`README.md`、`AGENTS.md` 必須同步。

---

## 7. 文件治理與參考

1. `docs/todos.md` 是唯一待辦與狀態來源。
2. `docs/spec.md` 是系統規格與架構邊界來源。
3. `docs/copilot-sdk-hooks-skills-session-resume-persistenc.md` 是第三次重構深度研究基線。
4. `README.md` 提供對外的 current/target 摘要。
5. `AGENTS.md` 定義專案級 agent/model/policy 規則。
