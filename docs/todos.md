# TestPilot Todo Board（Single Source of Truth）

## 治理規則

1. 本檔是專案唯一待辦清單。
2. 狀態僅允許：`pending`、`in_progress`、`done`、`blocked`。
3. 非 Plan Mode：不得增減項次，不得調整 ID。
4. 非 Plan Mode：僅可更新「狀態」與必要註記。
5. Plan Mode：才允許增減項次、重編排序、調整 phase 結構。
6. 本檔狀態需對齊 `docs/plan.md` 的「現況快照」與 phase 邊界。

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
| P0-10 | github-push | pending | 尚未標記完成 |

## Phase 1：Transport Layer

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P1-01 | serial-wrap transport | pending | 尚未實作 |
| P1-02 | adb transport | pending | 尚未實作 |
| P1-03 | ssh transport | pending | 尚未實作 |
| P1-04 | network utils（ping/arping/iperf） | pending | 尚未實作 |

## Phase 2：Environment Management

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P2-01 | topology module | pending | `src/testpilot/env/` 目前僅 `__init__.py` |
| P2-02 | provisioner module | pending | 尚未實作 |
| P2-03 | validator module | pending | 尚未實作 |

## Phase 3：Core Engine

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P3-01 | test-runner loop | in_progress | orchestrator 已有 `wifi_llapi` 路徑；待補 case-level agent dispatcher（sequential） |
| P3-02 | monitor subsystem | pending | 尚未實作 |
| P3-03 | reporter（MD/JSON） | in_progress | 已有 Wifi_LLAPI Excel reporter；MD/JSON 尚未完成 |
| P3-04 | verdict merge policy（plugin + agent） | pending | 規格已定，runtime 尚未落地 |
| P3-05 | post-run remediation loop | pending | 策略已定，runtime 尚未落地 |

## Phase 4：Wifi_LLAPI Plugin

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P4-01 | wifi-plugin full implementation | pending | `setup/verify/execute/evaluate` 仍 stub |
| P4-02 | case-getRadioStats | done | case 已存在 |
| P4-03 | case-kickStation | done | case 已存在 |
| P4-04 | 417 case source 對齊治理 | in_progress | 已有 alignment gate，需持續維護；另有 2 條 legacy non-row-indexed case（getRadioStats/kickStation） |
| P4-05 | Wifi_LLAPI Excel report pipeline | done | template + run report 已落地 |

## Phase 5：CLI & Integration

| ID | 項目 | 狀態 | 註記 |
|---|---|---|---|
| P5-01 | cli-full | in_progress | 已有 `run/list` + `wifi-llapi build-template-report` |
| P5-02 | orchestrator-full | in_progress | `wifi_llapi` 專屬流程已整合；其他 plugin 仍 skeleton |
| P5-03 | integration tests（mock transport） | pending | 尚未補齊 |
| P5-04 | plugin agent-config schema/runtime | in_progress | `wifi_llapi` 已有 `agent-config.yaml`；待補 per-case runtime selector |
| P5-05 | agent selection trace | in_progress | 目標改為每個 case 獨立 fallback/selection trace |
| P5-06 | case-agent dispatcher（sequential） | pending | 每個 test case 各自呼叫 agent，`max_concurrency=1` |
| P5-07 | retry-aware timeout policy | pending | timeout 需依 retry attempt 遞增並有上限 |
| P5-08 | per-case trace artifact writer | pending | `reports/agent_trace/<run_id>/<case_id>.json` |
| P5-09 | integration tests for per-case agent run | pending | 覆蓋 selector/fallback/retry/timeout/trace |
