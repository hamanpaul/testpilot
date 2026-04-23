# TestPilot Development Guidelines

## Scope

本檔定義本專案在開發/維護時的固定規範，重點是：

1. 文件與進度一致性
2. `docs/todos.md` 治理規則
3. plugin 級 agent/model 配置慣例

## Project Structure

```text
src/testpilot/
  core/       # orchestrator, plugin_base, plugin_loader, testbed_config
  reporting/  # wifi_llapi_excel and related report helpers
  transport/  # transport abstractions
  env/        # env modules (roadmap)
  schema/     # YAML case schema validation
plugins/      # each plugin in its own directory
configs/      # testbed config (see testbed.yaml.example)
docs/         # plan, todos, phase docs
scripts/      # utility scripts (gen_cases, build_template_report)
```

## Case Discovery Convention

1. `plugins/wifi_llapi/cases/` 中，官方 discoverable cases 以 workbook row-indexed `D###` YAML 為主。
2. 檔名 stem 以 `_` 開頭的 YAML 視為 explicit fixtures / legacy compatibility artifacts；`load_cases_dir()` 會排除這類檔案，不得計入 discoverable case inventory。
3. 若需保留 legacy YAML 供 schema / backward-compat 測試，優先使用 underscore-prefixed fixture 命名，不要沿用會被誤認成正式 case 的 `D###` 命名。

## Commands

```bash
uv pip install -e ".[dev]"
cp configs/testbed.yaml.example configs/testbed.yaml   # 首次設定
python -m testpilot.cli --version
python -m testpilot.cli list-plugins
python -m testpilot.cli list-cases wifi_llapi
python -m testpilot.cli wifi-llapi baseline-qualify --repeat-count 5 --soak-minutes 15
python -m testpilot.cli run wifi_llapi
python -m testpilot.cli wifi-llapi build-template-report --source-xlsx <path>
uv run pytest -q
```

Wifi_llapi reporting guidance:

3. `testpilot wifi-llapi build-template-report --source-xlsx <path>` is a build/audit path. `testpilot run wifi_llapi` must not depend on raw source workbooks.
4. `wifi_llapi` runtime alignment treats `(source.object, source.api)` as the canonical lookup key into the checked-in template workbook; `D###`, `source.row`, and matching `id` fragments are derived metadata and may be auto-corrected during `testpilot run wifi_llapi`.
5. `testpilot run wifi_llapi` may rename case files and rewrite `source.row` / `id` in-place. Review and commit those case diffs together with the corresponding runtime artifacts.
6. Alignment and audit are separate responsibilities: runtime alignment fixes metadata drift only; audit mode remains the place to change `name`, `steps`, `pass_criteria`, `source.object`, `source.api`, or `aliases`.

## Local Artifact Version Control Policy

1. repo root workbook inputs (`/*.xlsx`, `/*.xls`, `/*.xlsm`) and compare outputs (`compare-*.md`, `compare-*.json`) are local-only artifacts; do not commit them.
2. one-off campaign notes such as `*-full-run-static.md` and root-level STA experiment scratch notes are local-only unless explicitly promoted into `docs/`.
3. reusable report assets that stay versioned belong under `plugins/wifi_llapi/reports/templates/`; runtime output bundles under `plugins/wifi_llapi/reports/<artifact_name>/` remain untracked.

## Versioning and Release Policy

1. Repository release tags use Semantic Versioning in the form `vX.Y.Z`; the managed baseline for this workflow starts at `v0.1.5`.
2. Canonical project version lives in `pyproject.toml`; `src/testpilot/__init__.py` is the runtime mirror for `testpilot --version` and must stay identical.
3. User-facing pull requests should update `CHANGELOG.md` under `Unreleased`, or explicitly record why no changelog entry is needed.
4. Release preparation happens in a dedicated `release/vX.Y.Z` PR that updates version metadata, finalizes `CHANGELOG.md`, and syncs `README.md`, `docs/release-flow.md`, and this `AGENTS.md` when process guidance changes.
5. Only tag merged `main` commits; release tags must be `vX.Y.Z` and match the in-repo version. Tag push is responsible for publishing the GitHub Release.
6. Prefer GitHub-native controls first: PR template checklist, Actions CI, and tag-triggered Releases. Add extra local rules only where GitHub cannot enforce behavior directly.
7. Current publication scope is GitHub tag + GitHub Release notes only; do not assume wheel / sdist / binary assets are produced. Installation guidance should point to tagged-source installs until package publication is added.

## Todo Governance（嚴格）

1. `docs/todos.md` 是唯一待辦看板。
2. 非 Plan Mode：不得增減項次、不得調整 ID。
3. 非 Plan Mode：只允許更新狀態與必要註記。
4. Plan Mode：才可新增/刪除/重排項次。

## Documentation Sync Rule

當更新規劃或進度時，必須同步檢查以下文件一致性：

1. `docs/plan.md`
2. `docs/todos.md`
3. `README.md`
4. 本檔 `AGENTS.md`

## Audit Report Format Policy

1. `wifi_llapi` 的人工校正 audit report 必須使用 collapsible markdown sections。
2. 一旦某批 case 被判定為「已 live 對齊」，report 中必須新增或更新 `Per-case 摘要表（zh-tw）` 區塊。
3. `Per-case 摘要表（zh-tw）` 至少要包含：
   - case id
   - workbook row
   - API 名稱
   - verdict
   - DUT log interval
   - STA log interval
4. 每個已對齊 case 都必須附上 markdown fenced code blocks，分別記錄：
   - STA 指令
   - DUT 指令
   - 判定 pass 的 log 摘錄 / log 區間
5. 不可只寫 prose summary 而省略指令與 log block；有標記 aligned 的 case，command/log evidence 是必填。
6. 若同一批 case 共用 STA baseline，可重複列出，或在每個 case 內明確引用同一組 baseline 指令，但不可省略。
7. 若已知 log 行號區間，沿用 `Lxxx-Lyyy` 表示法，避免後續批次漂移成不同風格。
8. `wifi_llapi` aligned YAML 的 workbook row reference 只保留在 `source.row`；舊的 `wifi-llapi-rXXX-*` alias 視為 stale metadata，live 對齊時應移除，不再作為 row 來源。

## Calibration Continuation Policy

1. 目前 `wifi_llapi` workbook 校正工作必須嚴格採 **single-case mode**：一次只處理一個 official case。
2. 不可把未解案例再拆成 batch 並行處理，也不可自行建立加速工具／腳本來跳過逐案 evidence 驗證。
3. sub-agent 只可協助 offline survey、source tracing、code review；最終 live serialwrap 操作與 verdict 仍由主操作者手動收斂。
4. repo-only handoff 必須落在已提交的文件，而不是 session-local SQL / plan scratchpad。最少要同步：
   - `docs/audit-todo.md`
   - `plugins/wifi_llapi/reports/audit-report-*.md` 的最新 checkpoint 區塊
   - `README.md`
   - `docs/plan.md`
5. 每次完成單案校正或確認 blocker 後，repo handoff 文件至少要同步：
   - 目前 calibrated / remaining counts
   - active blockers
   - 最新已提交 case 與 verdict 形狀
   - 下一個 ready case
   - 最新驗證指令與結果
6. **commit / brief status update / targeted tests pass 都不是停點**；只要沒有明確 blocker、lab 失真、或使用者要求暫停，就必須在同一輪直接推進到下一個 ready single case。
7. 每個 single-case loop 的預設完成定義固定為：offline survey → live 三個 band 驗證/切換 → YAML 重寫 → runtime targeted tests → runtime file / full suite → docs sync → precise stage/commit → 立刻把下一個 ready case 標成 `in_progress`。
8. 若因 context 壓縮、tool/runtime crash、或 session 中斷而被迫停下，必須先把「最新已提交 case、目前 counts、next ready case、active blocker、最新驗證結果」落回 repo handoff 文件，再視為可接受中斷。
9. 對使用者的進度回覆應以「不中斷主流程」為原則：除非需要請求決策或回報 blocker，說明完當前 checkpoint 後就要繼續執行下一筆，不得把單次回答本身當成停工理由。

## Default Lab Baseline Policy

1. 預設 baseline 不可使用 open security SSID。
2. 若 testcase 沒有明確要求特殊安全模式，預設使用：
   - 5G：`testpilot5G` / `WPA2-Personal` / password `00000000`
   - 2.4G：`testpilot2G` / `WPA2-Personal` / password `00000000`
   - 6G：`testpilot6G` / `WPA3-Personal` / `key_mgmt=SAE` / password `00000000`
3. baseline 因 reboot / session recover 重建後，必須先把最新 SSID / security readback 與已驗證 band link 狀態同步回 repo handoff 文件，再繼續逐案校正。

## Plugin Agent Config Policy

1. plugin 若需宣告 agent/model policy，使用 `plugins/<plugin>/agent-config.yaml`。
2. `wifi_llapi` 第三次重構目標優先序固定為：
   - Priority 1: `copilot + gpt-5.4 + high`
   - Priority 2: `copilot + sonnet-4.6 + high`
   - Priority 3: `copilot + gpt-5-mini + high`
3. 不再以 `codex CLI` 為相容目標，不為舊 runner policy 增加 workaround code。
4. 第一優先不可用時允許自動降級，且需留 `selection trace`。
5. `wifi_llapi` 執行策略以 case-level 為主（每個 test case 各自呼叫 agent）。
6. `wifi_llapi` 排程策略預設為 `sequential`（`max_concurrency=1`）。
7. case 失敗策略為 `retry_then_fail_and_continue`，且 timeout 需隨 retry attempt 調整。
8. `wifi_llapi` 目前允許的 live remediation 只限 safe environment repair：`serial_session_recover`、`sta_band_reconnect`、`sta_band_rebaseline`、`dut_band_rebaseline`、`case_env_reverify`。
9. live remediation 僅允許發生在 retry attempts 之間；不得 mid-step takeover，也不得修改 YAML semantics、step 指令、pass criteria 或 xlsx final verdict。
10. 若 agent remediation decision 無法取得、格式不合法、或超出 whitelist，必須 fallback 到 deterministic builtin classifier，或直接不套 remediation。

## Azure OpenAI BYOK Policy

1. CLI 提供 `--azure` flag，啟動時互動式詢問 endpoint / api_key / model 三個參數。
2. 認證順序：`--azure` 互動 → `COPILOT_PROVIDER_*` 環境變數 → GitHub OAuth → 全部失敗則結束程式。
3. 環境變數命名遵循 Copilot CLI 官方慣例：
   - `COPILOT_PROVIDER_TYPE=azure`
   - `COPILOT_PROVIDER_BASE_URL=<endpoint>`
   - `COPILOT_PROVIDER_API_KEY=<key>`
   - `COPILOT_MODEL=<deployment-name>`
   - `COPILOT_PROVIDER_AZURE_API_VERSION=<version>` (預設 `2024-10-21`)
4. API key 與 endpoint 不得提交至版本控制；secrets 一律透過環境變數或 shell profile 注入。
5. `agent-config.yaml` 只放執行策略（model priority / timeout / retry），不放 secrets。

## Code Style

1. Python 3.11+，型別標註優先。
2. 維持最小必要變更，避免無關重構。
3. plugin 需繼承 `PluginBase` 並匯出 `Plugin` 類別。
