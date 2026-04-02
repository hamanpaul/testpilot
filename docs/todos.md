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
| P3-01 | test-runner loop | done | ExecutionEngine + runner_selector 已落地 (R2-01) |
| P3-02 | monitor subsystem | pending | 尚未實作 |
| P3-03 | reporter（MD/JSON） | done | IReporter + MarkdownReporter + JsonReporter 已落地 (R5-06) |
| P3-04 | verdict merge policy | done | 與 R4-05/R4-06 合併；AdvisoryCollector + diagnostic_status / remediation_history 投影已落地 |
| P3-05 | post-run remediation loop | done | 與 R4-06 合併；RemediationPlanner 保留 post-run 彙整，wifi_llapi 已接上 in-run safe remediation loop |

## Phase 4：Wifi_LLAPI Plugin

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P4-01 | wifi-plugin full implementation | done | setup/verify/execute/evaluate 已完成 |
| P4-02 | case-getRadioStats | done | legacy compatibility fixture 已保留，改為 underscore-prefixed explicit fixture，不進 discover_cases |
| P4-03 | case-kickStation | done | legacy compatibility fixture 已保留，改為 underscore-prefixed explicit fixture，不進 discover_cases |
| P4-04 | 420 case source 對齊治理 | in_progress | discoverable inventory 維持 420；目前依 `0401.xlsx` compare-driven single-case loop 持續 live 對齊，manual procedure authority 固定為 workbook `G/H`（忽略 `F`）；最新進度 `264/420` full matches；`D015`/`D016`/`D017`/`D018`/`D023` 已 live 對齊 row 15 / row 16 / row 17 / row 18 / row 23，`D011`/`D013`/`D020` 維持已驗證 fail-shaped mismatch，next=`D024`；目前 fresh full run 因 lab 端缺少 UART devices / COM0/COM1 sessions 而 blocked |
| P4-05 | Wifi_LLAPI Excel report pipeline | done | template + run report + merged-cell 相容 |

## Phase 5：CLI & Integration

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P5-01 | cli-full | done | `run/list` + `wifi-llapi build-template-report` |
| P5-02 | orchestrator-full | done | Orchestrator 拆分 + SDK session + hook policy + advisory/remediation hot-path wiring 已落地 |
| P5-03 | integration tests（mock transport） | done | 已補齊 realistic runtime 測試；最新 full suite `1600 passed`；3x live full run determinism 驗證通過（Run 2/3 = 100% 一致） |
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
| R2-01 | 拆分 Orchestrator | done | H1 | 拆為 case_utils / runner_selector / execution_engine / orchestrator facade |
| R2-02 | Plugin 自宣告執行流程 | done | H2 | PluginBase.run_pipeline() |
| R2-03 | Plugin 自宣告 Reporter | done | H2 | PluginBase.create_reporter() + report_formats() |
| R2-04 | Retry 歷史保留 | done | H8 | ExecutionEngine.execute_with_retry() + RetryResult dataclass |

## Phase R3：Plugin Template

| ID | 項目 | 狀態 | 對應隱患 | 說明 |
|---|---|---|---|---|
| R3-01 | 乾淨 plugin template | done | 需求 | `plugins/_template/` 完整骨架 |
| R3-02 | Plugin scaffold CLI | done | 需求 | template loadable by PluginLoader |
| R3-03 | Plugin 拆檔示範 | done | H6 | CommandResolver 拆為 `command_resolver.py` |
| R3-04 | PluginBase 瘦身 | done | H14 | 最小合約：name + discover_cases + execute_step + evaluate |

## Phase R4：Copilot SDK 控制平面

| ID | 項目 | 狀態 | 對應隱患 / 需求 | 說明 |
|---|---|---|---|---|
| R4-00 | 第三次重構研究 / 文件基線 | done | 需求 | Copilot SDK 深度研究完成，docs / README / AGENTS 已同步基線 |
| R4-01 | Copilot SDK session foundation | done | 需求 | SDK session wire-in with create/cleanup lifecycle per case |
| R4-02 | hook policy layer | done | 需求 | 6 lifecycle hooks: pre/post_case, pre/post_step, on_failure, on_retry |
| R4-03 | custom agents roles | done | 需求 | executor / advisor / remediation / observer + role merging |
| R4-04 | skills packages | done | 需求 | SkillRegistry + SKILL.md discovery + role-based resolution |
| R4-05 | advisory agent outputs | done | 需求 | AdvisoryOutput + AdvisoryCollector + IHook handler factory |
| R4-06 | remediation planner loop | done | 需求 | RemediationPlanner + severity-prioritized action mapping + wifi_llapi in-run safe remediation loop |
| R4-07 | runtime policy alignment | done | 需求 | `plugins/wifi_llapi/agent-config.yaml` 已改為 copilot-only policy |
| R4-08 | selective MCP integrations | done | 需求 | MCPRegistry + role-selective server management |

## Phase R5：可靠性與測試補強

| ID | 項目 | 狀態 | 對應隱患 | 說明 |
|---|---|---|---|---|
| R5-01 | serialwrap RC 擷取修正 | done | H7 | `_extract_marker_output()` 改為 FIRST match |
| R5-02 | Plugin loader 改良 | done | H9 | sys.path try/finally cleanup |
| R5-03 | openpyxl API 隔離 | done | H10 | excel_adapter.py 封裝 |
| R5-04 | Session 解析簡化 | pending | H12 | 減少 fallback 層數並嚴格裝置綁定 |
| R5-05 | 測試覆蓋 >80% | done | 品質 | coverage baseline 81% (2492 stmts) |
| R5-06 | MD/JSON report 實作 | done | H13 | IReporter + MarkdownReporter + JsonReporter |
| R5-07 | `execute_step` heuristic 收斂 | done | 新增 | CommandResolver strategy pattern refactor |
| R5-08 | control-plane / verdict-plane 邊界測試 | done | 新增 | 15 boundary tests for hook/retry/timeout/band interactions |
