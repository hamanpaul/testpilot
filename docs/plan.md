# TestPilot Master Plan

> 更新日期：2026-03-27
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

## 2. 現況快照（2026-03-27）

### 2.1 已落地能力

1. CLI 入口：`list-plugins`、`list-cases`、`run`、`wifi-llapi build-template-report`。
2. `wifi_llapi` 已有報表導向 run path 與 row/source 對齊治理。
3. Transport：serialwrap / adb / ssh / network 已實作。serialwrap 已支援 auto-detect template（COM init 時自動偵測 prpl / openwrt / generic）與 prpl-template 復原。
4. Per-case dispatcher、selection trace、retry-aware timeout、attempt trace 已落地。
5. 正式 hot path 仍由 `setup_env -> verify_env -> execute_step -> evaluate` 決定。
6. 420 官方 row-indexed cases 已全部校正完畢；兩個 duplicate-row legacy YAML 已改為 underscore-prefixed compatibility fixtures，不再混入 discoverable case inventory。
7. `wifi_llapi` 全部 420 筆 official cases 已校正完畢（343 Support + 54 Not Supported + 20 Skip + 3 Blocked）；僅餘 3 筆 Blocked（`D035`、`D052`、`D053`）因環境/BCM 限制暫無法驗證。
8. repo-only 校正 handoff 已同步到 `docs/audit-todo.md` 與 `plugins/wifi_llapi/reports/audit-report-260313-185447.md`；校正工作已全部完成，歷史 checkpoint 紀錄保留於 audit-todo.md。
9. reboot 後的 default lab baseline 已重建並落成文件：5G `testpilot5G` / 2.4G `testpilot2G` 使用 `WPA2-Personal + 00000000`，6G `testpilot6G` 固定使用 `WPA3-Personal + key_mgmt=SAE + 00000000`。
10. 第三次重構的 Copilot SDK 深度研究已完成，並已複製到 `docs/copilot-sdk-hooks-skills-session-resume-persistenc.md`。
11. 校正工作守則已補強為「不中斷持續作業」：commit、簡短狀態回覆與 targeted tests pass 都不是停點；只要沒有 blocker 或使用者要求暫停，就必須在同一輪把下一個 ready case 直接推進到 `in_progress`。
12. **3x full run determinism 驗證完成**（2026-03-25）：420 cases × 3 runs 全部 exit=0，Run 2/3 verdict 100% 一致，Run 1 僅 2/355 rows 差異（baseline warm-up 效應）。修復 4 個 live runtime bugs：DUT kernel flood、5G ModeEnabled reversion、6G connect fatal、multi-line printf split。詳見 `plugins/wifi_llapi/reports/3x_determinism_report_20260325.md`。
13. **serialwrap human-agent 共存**（2026-03-26）：新增 `wal.reset` / `wal.current_seq` RPC + `session.bind` 冪等化（ser-dep PR #18）。testpilot 改用 `wal.reset` 取代 daemon restart，保留 human console (minicom) 連線（PR #7）。WAL fan-out 驗證通過。
14. **Copilot SDK 原生支援 Azure BYOK**（2026-03-27 確認）：`SessionConfig.provider` 支援 `type: "azure"`，`COPILOT_PROVIDER_*` env vars 可切換認證。詳見下方 §8。

### 2.2 尚未落地

1. P2 Environment modules（topology / provisioner / validator）— 低優先。
2. P3-02 Monitor subsystem — 規格未定。
3. R5-04 Session / device binding 嚴格化 — 低優先。
4. R4/R5 各模組已 scaffolded 但尚未接入 hot path（agent_roles → orchestrator、advisory → hook handler、remediation → post-run、skill/mcp → session request、reporter → orchestrator output）。

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
| R4-01 | Copilot SDK session foundation | SDK session wire-in with create/cleanup lifecycle | done |
| R4-02 | hook policy layer | 6 lifecycle hooks: pre/post_case, pre/post_step, on_failure, on_retry | done |
| R4-03 | custom agents roles | executor / advisor / remediation / observer + role merging | done |
| R4-04 | skills packages | SkillRegistry + SKILL.md discovery + role-based resolution | done |
| R4-05 | advisory agent outputs | AdvisoryOutput + AdvisoryCollector + IHook handler factory | done |
| R4-06 | remediation planner loop | RemediationPlanner + severity-prioritized action mapping | done |
| R4-07 | runtime policy alignment | plugin agent-config / runner policy 改為 copilot-only order | done |
| R4-08 | selective MCP | MCPRegistry + role-selective server management | done |

### Phase R5：Deterministic kernel 補強

| ID | 項目 | 輸出 | 狀態 |
|---|---|---|---|
| R5-01 | serialwrap RC 擷取修正 | FIRST match return code | done |
| R5-02 | Plugin loader 改良 | sys.path try/finally cleanup | done |
| R5-03 | openpyxl API 隔離 | excel_adapter.py 封裝 | done |
| R5-04 | Session / device binding 嚴格化 | 減少 fallback、避免靜默選錯裝置 | pending |
| R5-05 | 測試覆蓋 >80% | coverage baseline 81% (2492 stmts) | done |
| R5-06 | MD/JSON report projector | IReporter + MarkdownReporter + JsonReporter | done |
| R5-07 | `execute_step` heuristic 收斂 | CommandResolver strategy pattern refactor | done |
| R5-08 | control-plane / verdict-plane 邊界測試 | 15 boundary tests for hook/retry/timeout/band | done |

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
| P3 | Core Engine（runner loop / monitor / reporter / verdict merge） | done (except P3-02 Monitor) |
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

---

## 8. Azure OpenAI BYOK 整合計畫（2026-03-27）

### 8.1 背景

test team 沒有 GitHub Copilot 存取權限。需要讓 testpilot 建立的 agent session 可以透過 Azure OpenAI API 認證，而非 GitHub OAuth。

### 8.2 核心發現

**Copilot SDK v0.1.23 原生支援 Azure BYOK**：

- `SessionConfig.provider` TypedDict 支援 `type: Literal["openai", "azure", "anthropic"]`
- `ProviderConfig` 欄位：`type`, `base_url`, `api_key`, `bearer_token`, `wire_api`, `azure`
- `AzureProviderOptions` 欄位：`api_version`
- SDK `client.py:486-489`：`create_session()` 會讀取 `provider` 並傳給 CLI server
- SDK `client.py:1048-1076`：`_convert_provider_to_wire_format()` 做 snake_case → camelCase 轉換
- **`CopilotSessionRequest` 已有 `provider` 欄位**（`copilot_session.py:61`），`_base_config()` 已處理傳遞

Copilot CLI 也有官方 BYOK 支援（`copilot help providers`）：
```bash
COPILOT_PROVIDER_TYPE=azure \
COPILOT_PROVIDER_BASE_URL=https://my-resource.openai.azure.com \
COPILOT_PROVIDER_API_KEY=your-key-here \
COPILOT_MODEL=gpt-4 \
copilot
```

### 8.3 設計決策

| 決策 | 選擇 | 理由 |
|------|------|------|
| API 風格 | Chat Completions | Azure 所有版本支援，相容性最佳 |
| 認證切換方式 | env vars + agent-config.yaml | 跟 Copilot CLI 官方 env var 一致 |
| 架構改動 | 不新建 provider 層 | SDK 原生支援，只需傳遞 config |
| 新增 dependency | 無 | 完全用現有 Copilot SDK 功能 |

### 8.4 使用方式

**外層（Copilot CLI 對話，如現在）+ 內層（testpilot session）可各自選擇認證**：

| 層 | 認證 | 設定方式 |
|---|---|---|
| 外層 Copilot CLI | GitHub OAuth（預設）或 Azure BYOK | `COPILOT_PROVIDER_*` env vars |
| 內層 testpilot session | GitHub OAuth（預設）或 Azure BYOK | agent-config.yaml `provider` 或 env vars |

兩層完全獨立，互不影響。

**使用 Azure 的完整設定**：
```bash
# 必要 env vars（從 Azure Portal 取得）
export COPILOT_PROVIDER_TYPE=azure
export COPILOT_PROVIDER_BASE_URL=https://your-resource.openai.azure.com
export COPILOT_PROVIDER_API_KEY=your-azure-api-key
export COPILOT_MODEL=gpt-4o                            # Azure deployment name

# 選填（有預設值）
export COPILOT_PROVIDER_AZURE_API_VERSION=2024-10-21   # 預設 2024-10-21
export COPILOT_PROVIDER_WIRE_API=completions            # 預設 completions

# 指令完全不變
testpilot run wifi_llapi
testpilot run wifi_llapi --case wifi-llapi-D004-kickstation
```

**或在 agent-config.yaml 中配置**（避免 key 用 env var 引用）：
```yaml
provider:
  type: azure
  base_url: ${COPILOT_PROVIDER_BASE_URL}
  api_key: ${COPILOT_PROVIDER_API_KEY}
  wire_api: completions
  azure:
    api_version: "2024-10-21"
```

### 8.5 Azure 資訊需求

從 Azure Portal 取得（需公司 Azure 管理員提供）：

| 項目 | 說明 | 取得位置 |
|------|------|---------|
| API Key | Azure OpenAI 資源金鑰 | Azure Portal → Keys and Endpoint |
| Endpoint URL | 資源專屬 URL（公司指定，非通用） | Azure Portal → Keys and Endpoint |
| Deployment name | 管理員部署的模型名稱 | Azure Portal → Model deployments |

Endpoint URL 格式：`https://{資源名稱}.openai.azure.com`。同一組 key/endpoint 可供多個應用共用（n8n、testpilot 等），但共享 TPM 配額。

連線驗證：`curl -I https://your-resource.openai.azure.com/` 回 HTTP 404 即表示網路可達。

### 8.6 實作 Todos

#### T1: copilot_session.py — 讀取 provider config

- 新增 `_resolve_provider_config(agent_config: dict) -> dict | None`
  - 優先讀 `agent_config["provider"]` section
  - Fallback 讀 `COPILOT_PROVIDER_*` env vars
  - 支援 `${VAR_NAME}` 內插（YAML 值引用 env var）
  - 回傳 `ProviderConfig` dict 或 None
- 更新 `build_case_session_plan()` 接受 `agent_config` 參數
  - 呼叫 `_resolve_provider_config()` 取得 provider
  - 如果有 provider，放進 session plan dict（key: `"provider"`）
  - 如果沒有，維持現狀（GitHub OAuth）

檔案：`src/testpilot/core/copilot_session.py`

#### T2: orchestrator.py — 傳遞 provider config

- `_create_case_session()` 從 session plan 取 `provider` config
- 傳入 `CopilotSessionRequest(provider=provider_config)`
- 更新 `_run_wifi_llapi()` 中 `build_case_session_plan()` 的呼叫，加入 `agent_config`
- 不改其他邏輯

檔案：`src/testpilot/core/orchestrator.py`

#### T3: 測試

- 新建 `tests/test_azure_byok.py`
- 測試 `_resolve_provider_config()`：
  - env vars only → 正確建構 provider dict
  - YAML config only → 正確讀取
  - 兩者都有 → YAML 優先
  - 都沒有 → 回傳 None
  - `${VAR}` 內插
- 測試 `build_case_session_plan()` with provider
- Mock SDK `create_session` 驗證 provider 正確傳入 request
- 驗證無 provider config 時行為不變
- 確認既有 tests 不受影響

#### T4: 文件更新

- `README.md`：Azure BYOK setup section（env vars + 使用方式）
- `plugins/wifi_llapi/agent-config.yaml`：加入 provider 範例（註解形式）
- `AGENTS.md`：更新 Plugin Agent Config Policy，加入 provider 說明

### 8.7 預計檔案變更

| 檔案 | 變更 |
|------|------|
| `src/testpilot/core/copilot_session.py` | 新增 `_resolve_provider_config()`，更新 `build_case_session_plan()` |
| `src/testpilot/core/orchestrator.py` | `_create_case_session()` 傳遞 provider，`_run_wifi_llapi()` 傳 agent_config |
| `tests/test_azure_byok.py` | **新建** — provider config 解析 + session plan 測試 |
| `plugins/wifi_llapi/agent-config.yaml` | 加入 provider 範例註解 |
| `README.md` | Azure BYOK setup section |
| `AGENTS.md` | 更新 policy |

### 8.8 關鍵原則

1. **Zero breaking change**：沒有 `COPILOT_PROVIDER_*` env vars 且 config 沒有 `provider` section 時，行為完全不變。
2. **Env var naming 一致**：跟 Copilot CLI 官方 env var 名稱一致（`COPILOT_PROVIDER_*`），不另外發明。
3. **Config override**：agent-config.yaml 的 `provider` section 可覆蓋 env vars（per-plugin 需求）。
4. **No new dependencies**：完全用現有 Copilot SDK 功能，不需要 `openai` package。

### 8.9 分支

- Branch: `feat/azure-openai-support`（已建立，base: `main`）
- 狀態：**Planning — 待開工**
