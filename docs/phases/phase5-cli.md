# Phase 5：CLI & Integration

## Scope

強化 CLI、整合測試與 plugin agent 選擇/降級留痕。

## Current Status

1. CLI 已有 `run/list` 與 `wifi-llapi build-template-report`。
2. Orchestrator 對 `wifi_llapi` 已有專屬流程。

## Gaps

1. 非 `wifi_llapi` plugin 仍為 skeleton run。
2. integration tests 尚未補齊。
3. plugin agent-config 選擇器與 trace 尚未實作。

## Acceptance Criteria

1. CLI 行為與文件一致。
2. 具備 integration tests（mock transport + 主要流程）。
3. Agent selection/fallback 有 trace 可供稽核。

## Related Todo IDs

- `P5-01` ~ `P5-05`
