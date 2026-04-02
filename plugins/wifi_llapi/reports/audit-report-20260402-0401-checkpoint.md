# Wifi_LLAPI audit report checkpoint (0401 workbook)

## Checkpoint summary (2026-04-02)

> This checkpoint records campaign state after repo-side preflight and baseline hardening.
> No new live single-case alignment was produced in this checkpoint because lab UART access is currently unavailable.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- workbook procedure authority fixed to `Wifi_LLAPI` columns `G/H` (`Test steps` / `Command Output`); `F` is ignored
- latest carried-forward compare snapshot remains `264 / 420` full matches and `156` mismatches
- latest carried-forward aligned live case remains `D023 Inactive` via run `20260402T105808547293`
- latest carried-forward stable fail-shaped mismatches remain `D011` / `D013` / `D020`
- preflight guardrails revalidated:
  - multiline block-scalar ban for official case command fields: pass
  - serialwrap 120-char temp-script staging tests: pass
  - official-case command length inventory over 120 chars: `597` tracked entries
- repo regression status after the offline-survey regression guard: `uv run pytest -q` → `1601 passed`
- `D024 LastDataDownlinkRate` offline survey is ready:
  - workbook authority is row `24`
  - workbook `G/H` and the source model both use DUT `wl -i wl0 sta_info ${STA_MAC}` `rate of last tx pkt` as the AP -> STA truth source
  - the old `20260401T152827516151` fail trace already captured matching LLAPI / driver values, so that fail is treated as consistent with the older shell-pipeline success-classifier bug now covered by regression tests
- adjacent stale metadata is also confirmed:
  - current YAML row ids for `D024` / `D025` / `D026` still read `21` / `22` / `23`
  - `0401.xlsx` rows are actually `24` / `25` / `26`
  - therefore this slice remains pending live rewrite instead of being treated as already aligned
- current live blocker:
  - serialwrap daemon is running, but the environment currently exposes no `/dev/ttyUSB*` and no `/dev/serial/by-id`
  - `serialwrap session list` returns zero sessions
  - `serialwrap session self-test --selector COM0/COM1` fails because `COM0/COM1` do not exist
  - therefore fresh live full run and subsequent live calibration cannot proceed until DUT/STA UART visibility returns
- next ready case after UART recovery: `D024 LastDataDownlinkRate`

</details>

## Active blockers

| Scope | Item | Status | Detail |
|---|---|---|---|
| lab / serialwrap | DUT/STA UART visibility | blocked | No `/dev/ttyUSB*`, no `/dev/serial/by-id`, no `COM0/COM1` sessions |
| plugin cases | official-case long command inventory | tracked risk | `597` commands exceed 120 chars, but current serialwrap temp-script staging keeps them executable |

## Resume steps

1. Restore DUT/STA UART visibility so `/dev/ttyUSB*` or `/dev/serial/by-id` reappear.
2. Rebuild serialwrap `COM0/COM1` sessions and confirm `session self-test` passes.
3. Run the pending fresh full suite.
4. Rebuild `compare-0401.{md,json}` from the new full run.
5. Resume the single-case loop from `D024 LastDataDownlinkRate` (row `24`), then continue `D025` (row `25`) and `D026` (row `26`).
