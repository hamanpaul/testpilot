# TestPilot Todo Board（Single Source of Truth）

## 治理規則

1. 本檔是專案唯一待辦清單。
2. 狀態僅允許：`pending`、`in_progress`、`done`、`blocked`。
3. 非 Plan Mode：不得增減項次，不得調整 ID。
4. 非 Plan Mode：僅可更新「狀態」與必要註記。
5. 已核准的重構計畫實作，需對齊 `docs/plan.md` 的 phase 與邊界。
6. 本檔狀態需同步反映 `docs/plan.md` 的現況快照。

---

## Phase 0：Scaffold

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P0-01 | scaffold（目錄與 pyproject） | done | 已建立 |
| P0-02 | plugin-base（PluginBase + Loader） | done | 已建立 |
| P0-03 | case-schema 驗證 | done | 已建立 |
| P0-04 | testbed-config 解析 | done | 已建立 |
| P0-05 | transport-base（StubTransport） | done | 已建立 |
| P0-06 | skeleton-cli | done | 已具備 `list-plugins/list-cases/run` |
| P0-07 | skeleton-orchestrator | done | 已可載入 plugin/cases |
| P0-08 | wifi-plugin-stub | done | plugin hook 目前仍為 stub |
| P0-09 | docs-init | done | 已完成 master plan/todos/phases 對齊 |
| P0-10 | github-push | done | v0.0.3-draft tag 已推送 |

## Phase 1：Transport Layer

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P1-01 | serial-wrap transport | done | 已完成 serialwrap transport，實機全量 run 驗證 |
| P1-02 | adb transport | done | `src/testpilot/transport/adb.py` |
| P1-03 | ssh transport | done | `src/testpilot/transport/ssh.py` |
| P1-04 | network utils（ping/arping/iperf） | done | `src/testpilot/transport/network.py` |

## Phase 2：Environment Management

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P2-01 | topology module | pending | `src/testpilot/env/` 目前僅 `__init__.py` |
| P2-02 | provisioner module | pending | 尚未實作 |
| P2-03 | validator module | pending | 尚未實作 |

## Phase 3：Core Engine

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P3-01 | test-runner loop | in_progress | `wifi_llapi` per-case dispatcher 已有；其餘 plugin 仍待 |
| P3-02 | monitor subsystem | pending | 尚未實作 |
| P3-03 | reporter（MD/JSON） | in_progress | Excel reporter 已有；MD/JSON 尚未完成 |
| P3-04 | verdict merge policy | pending | 規格已定，runtime 尚未落地 |
| P3-05 | post-run remediation loop | pending | 策略已定，runtime 尚未落地 |

## Phase 4：Wifi_LLAPI Plugin

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P4-01 | wifi-plugin full implementation | done | setup/verify/execute/evaluate 已完成 |
| P4-02 | case-getRadioStats | done | legacy compatibility fixture 已保留，改為 underscore-prefixed explicit fixture，不進 discover_cases |
| P4-03 | case-kickStation | done | legacy compatibility fixture 已保留，改為 underscore-prefixed explicit fixture，不進 discover_cases |
| P4-04 | 417 case source 對齊治理 | done | 415 官方 discoverable D### 已對齊；2 legacy duplicate-row YAML 已轉為 explicit fixtures；目前 handoff 已補記 D060/D061/D062/D063/D064/D065/D066/D067/D068/D069/D070/D072/D073/D074/D077/D078/D079/D080/D081/D082/D083/D084/D085/D086/D087/D088 committed checkpoint，且 D185/D368/D371 已折入 completed official cases（progress=`148 / 415`，remaining=`267`）；default lab baseline 已重建為 5G/2.4G=`WPA2-Personal + 00000000`、6G=`WPA3-Personal + SAE + 00000000`，主 sequence 下一個 ready single-case 入口改為 D089 |
| P4-05 | Wifi_LLAPI Excel report pipeline | done | template + run report + merged-cell 相容 |

## Phase 5：CLI & Integration

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P5-01 | cli-full | done | `run/list` + `wifi-llapi build-template-report` |
| P5-02 | orchestrator-full | in_progress | `wifi_llapi` 流程已整合；其他 plugin 仍 skeleton |
| P5-03 | integration tests（mock transport） | done | 已補齊 realistic runtime 測試；最新逐案校正後 `tests/test_wifi_llapi_plugin_runtime.py=227 passed`、full suite `280 passed` |
| P5-04 | plugin agent-config schema/runtime | done | `agent_runtime.py` |
| P5-05 | agent selection trace | done | per-case selection / fallback trace |
| P5-06 | case-agent dispatcher（sequential） | done | `max_concurrency=1` |
| P5-07 | retry-aware timeout policy | done | 遞增 timeout + 上限 |
| P5-08 | per-case trace artifact writer | done | `reports/agent_trace/<run_id>/` |
| P5-09 | integration tests for per-case agent | done | selector / fallback / retry / timeout / trace 全覆蓋 |

---

## Phase R1：指令格式與 Report 清理

| ID | 項目 | 狀態 | 對應隱患 | 說明 |
|---|---|---|---|---|
| R1-01 | Report 保存不覆蓋 | done | H3 | 報告檔名加 `run_id`，copy 另有 `_01/_02` 防呆 |
| R1-02 | xlsx report output 清理 marker | done | H4 | `sanitize_report_output()` 清除舊 serial prompt / marker 汙染 |
| R1-03 | xlsx report cmd 欄單行化 | done | 需求 | G 欄改為單行一條指令 |
| R1-04 | YAML 指令單行化工具 | done | H5 | 新增 `wifi-llapi audit-yaml-commands` dry-run 稽核 |

## Phase R2：Orchestrator 解耦

| ID | 項目 | 狀態 | 對應隱患 | 說明 |
|---|---|---|---|---|
| R2-01 | 拆分 Orchestrator | pending | H1 | CaseDiscovery / TestRunner / RetryPolicy / ReportCoordinator |
| R2-02 | Plugin 自宣告執行流程 | pending | H2 | PluginBase.run_pipeline() |
| R2-03 | Plugin 自宣告 Reporter | pending | H2 | PluginBase.create_reporter() |
| R2-04 | Retry 歷史保留 | pending | H8 | 所有 attempt 結果存入 list |

## Phase R3：Plugin Template

| ID | 項目 | 狀態 | 對應隱患 | 說明 |
|---|---|---|---|---|
| R3-01 | 乾淨 plugin template | pending | 需求 | `plugins/_template/` 完整骨架 |
| R3-02 | Plugin scaffold CLI | pending | 需求 | `testpilot create-plugin <name>` |
| R3-03 | Plugin 拆檔示範 | pending | H6 | executor / evaluator / environment / output_parser |
| R3-04 | PluginBase 瘦身 | pending | H14 | Executable / EnvironmentManager / Evaluator protocol |

## Phase R4：Copilot SDK 控制平面

| ID | 項目 | 狀態 | 對應隱患 / 需求 | 說明 |
|---|---|---|---|---|
| R4-00 | 第三次重構研究 / 文件基線 | done | 需求 | Copilot SDK 深度研究完成，docs / README / AGENTS 已同步基線 |
| R4-01 | Copilot SDK session foundation | in_progress | 需求 | thin SDK adapter、session ID policy、create/resume/list/delete 已落地；尚未接入正式 run path |
| R4-02 | hook policy layer | pending | 需求 | `on_session_start` / `on_pre_tool_use` / `on_post_tool_use` / `on_error_occurred` |
| R4-03 | custom agents roles | pending | 需求 | operator / case-auditor / remediation-planner / run-summarizer |
| R4-04 | skills packages | pending | 需求 | diagnostics / remediation policy / report style |
| R4-05 | advisory agent outputs | pending | 需求 | per-case audit / run summary / md 草稿生成 |
| R4-06 | remediation planner loop | pending | 需求 | structured JSON plan + whitelist executor + rerun gate |
| R4-07 | runtime policy alignment | done | 需求 | `plugins/wifi_llapi/agent-config.yaml` 已改為 copilot-only policy |
| R4-08 | selective MCP integrations | pending | 需求 | 僅限 GitHub / KB / lab inventory 等非熱路徑工具 |

## Phase R5：可靠性與測試補強

| ID | 項目 | 狀態 | 對應隱患 | 說明 |
|---|---|---|---|---|
| R5-01 | serialwrap RC 擷取修正 | done | H7 | `_extract_marker_output()` 改為 FIRST match |
| R5-02 | Plugin loader 改良 | pending | H9 | 移除 `sys.path` 污染 |
| R5-03 | openpyxl API 隔離 | pending | H10 | 封裝進 adapter |
| R5-04 | Session 解析簡化 | pending | H12 | 減少 fallback 層數並嚴格裝置綁定 |
| R5-05 | 測試覆蓋 >80% | pending | 品質 | 補邊界條件與 CLI integration |
| R5-06 | MD/JSON report 實作 | pending | H13 | canonical result → md/json projector |
| R5-07 | `execute_step` heuristic 收斂 | pending | 新增 | 減少自由文字 fallback，回到 schema / evidence 驅動 |
| R5-08 | control-plane / verdict-plane 邊界測試 | pending | 新增 | 確保 Copilot 不直接決定最終 `Pass/Fail` |
