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

## Commands

```bash
uv pip install -e ".[dev]"
cp configs/testbed.yaml.example configs/testbed.yaml   # 首次設定
python -m testpilot.cli --version
python -m testpilot.cli list-plugins
python -m testpilot.cli list-cases wifi_llapi
python -m testpilot.cli run wifi_llapi
python -m testpilot.cli wifi-llapi build-template-report --source-xlsx <path>
pytest
```

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

## Plugin Agent Config Policy

1. plugin 若需宣告 CLI agent/model，使用 `plugins/<plugin>/agent-config.yaml`。
2. `wifi_llapi` 優先序固定為：
   - Priority 1: `codex + gpt-5.3-codex + high`
   - Priority 2: `copilot + sonnet-4.6 + high`
3. 第一優先不可用時允許自動降級，且需留 `selection trace`。
4. `wifi_llapi` 執行策略以 case-level 為主（每個 test case 各自呼叫 agent）。
5. `wifi_llapi` 排程策略預設為 `sequential`（`max_concurrency=1`）。
6. case 失敗策略為 `retry_then_fail_and_continue`，且 timeout 需隨 retry attempt 調整。

## Code Style

1. Python 3.11+，型別標註優先。
2. 維持最小必要變更，避免無關重構。
3. plugin 需繼承 `PluginBase` 並匯出 `Plugin` 類別。
