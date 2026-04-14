# D179 Ampdu blocker

## Status

- case: `D179 Radio.Ampdu`
- workbook row: `179`
- current state: **blocked as DUT+STA 6G baseline bring-up failure**
- next ready actionable compare-open case: `D180 Radio.Amsdu`

## Why this is blocked

Workbook row `179` is not a bare DUT-only setter/readback row. `compare-0401` row `179` keeps the original workbook story: first connect a station to the gateway, then toggle `Ampdu`, then verify the live driver-side effect with `wl -i wlx ampdu`.

The first focused rerun `20260413T175446838229` proved the older DUT-only replay was not a valid closure path for that workbook intent: the northbound getter moved to `0`, but the 5G driver readback still stayed `1`, and the rerun emitted no per-case STA evidence at all. After that, the trial case was upgraded to explicit `DUT + STA` tri-band topology so the plugin would engage the current tri-band STA baseline machinery before replaying row `179`.

That second clean-start rerun, started as `20260413T182427454124`, never reached the D179 step execution phase because `verify_env` kept failing to stabilize the 6G baseline. At that point the blocker stopped being a simple 5G compare issue and became a broader `DUT + STA` 6G bring-up failure.

## Workbook evidence

- `0401.xlsx` row `179`
  - object/api: `WiFi.Radio.{i}.DriverConfig.` / `Ampdu`
  - answer columns `R/S/T`: `Pass / Pass / Pass`
  - workbook `G` excerpt (`compare-0401.md:264-281`): connect WiFi station to GW, set `Ampdu=1`, run throughput, then disable and restore
  - workbook `H` excerpt (`compare-0401.md:264-281`): driver oracle is `wl -i wlx ampdu`

## Focused rerun evidence

### 1. DUT-only focused rerun invalidated the old replay shape

- official rerun summary: `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260413t175446838229.md:7-12`
  - `d179-radio-ampdu`
  - `source_row=179`
  - `result_5g/result_6g/result_24g = Fail / Fail / Fail`
  - `diagnostic_status=FailTest`
- same report command/output block: `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260413t175446838229.md:17-31,75-98,170-172`
  - 5G replay was still DUT-only (`ubus-cli ... Ampdu=1/0/-1` plus `wl -i wl0 ampdu`)
  - failure snapshot closed on `after_set0_5g.AfterSet0DriverAmpdu5g expected=0 actual=1`
- DUT log: `plugins/wifi_llapi/reports/20260413T175446838229_DUT.log:35-64` and `:302-333`
  - `AfterSet0GetterAmpdu5g=0`
  - `AfterSet0DriverAmpdu5g=1`
- STA artifact: `plugins/wifi_llapi/reports/20260413T175446838229_STA.log`
  - file is empty; the rerun did not produce per-case STA evidence

This means the earlier DUT-only shape was not a workbook-faithful closure path. It skipped the row-179 prerequisite that a station must already be connected before the driver-side `ampdu` readback is judged.

### 2. Current trial YAML now requires explicit DUT+STA topology

- current trial case: `plugins/wifi_llapi/cases/D179_ampdu.yaml:1-38`
  - row `179` retained
  - topology now declares `DUT` on `COM0` and `STA` on `COM1`
  - tri-band STA links are explicit for `5g`, `6g`, and `2.4g`
  - workbook comment now says the pass intent is an active-STA replay
- runtime contract tests: `plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py:18889-18993`
  - assert the new `DUT + STA` topology and tri-band links
  - keep the 6G BSS-effect oracle in evaluation
- command-budget guardrail: `plugins/wifi_llapi/tests/test_wifi_llapi_command_budget.py:8-43`
  - current long-command inventory is intentionally updated to `729`

### 3. Clean-start DUT+STA rerun exposed the real blocker: 6G baseline bring-up

Before the second focused rerun, both boards were hard-reset with `firstboot -y; sync; sync; sync; reboot -f` to eliminate stale environment carry-over. The new rerun started as `20260413T182427454124`, but it never reached D179 step execution because `verify_env` repeatedly failed on 6G recovery. The repeated shell evidence was:

```text
6G ocv=0 fix applied, wl1 hostapd restarted
6G ocv fix did not stabilize wl1 after retries
sta_baseline_bss[1] not ready after 60s cmd=wl -i wl1 bss
STA 6g link check failed (iface=wl1, rc=0): Not connected.
```

Artifacts from this stopped rerun confirm it did not become an authoritative closure:

- partial xlsx only: `plugins/wifi_llapi/reports/20260413_BGW720-0403_wifi_LLAPI_20260413T182427454124.xlsx`
  - row `179` only retains workbook metadata; result cells were never written
- no report markdown/json was emitted for run `20260413T182427454124`
- `plugins/wifi_llapi/reports/agent_trace/20260413T182427454124/` is empty

## Why the case is not being closed

The current trial direction is likely correct — row `179` does need active STA context — but there is still no authoritative tri-band step-level proof for the rewritten case. The clean-start `DUT + STA` attempt died in 6G baseline recovery before any final `Ampdu` step outputs were collected.

Closing D179 now, or updating `compare-0401` as if it were aligned, would invent a successful tri-band replay that the lab has not actually produced.

## Required follow-up

1. Re-stabilize the shared 6G `DUT + STA` baseline outside D179 until `wl1 bss` stays up and STA 6G reconnects cleanly after the current OCV repair path.
2. Re-run D179 with the active STA baseline intact and capture the actual 5G / 6G / 2.4G step outputs under that topology.
3. Only after that rerun reaches step-level evidence should row `179` be considered for compare closure.
