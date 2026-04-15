# D257 getRadioAirStats() Load historical parked note

## Status update

- case: `D257 getRadioAirStats() Load`
- blocker-era isolated rerun: `20260414T183120002375`
- resolving official rerun: `20260414T200750384793`
- current closure shape: `5g=83`, `6g=62`, `2.4g=98`
- compare status: closed on workbook row `257` `Pass / Pass / Pass`
- disposition: **historical note retained for the temporary empty-array / 6G baseline blocker**

## Historical blocker context

The historical authoritative full-run trace already proves that the stale authored mapping is wrong:

- `20260412T113008433351` returned numeric `Load = 84 / 62 / 96`
- the old committed YAML still pointed at stale row `259` with `Fail / Fail / Fail`

So `D257` is **not** blocked by workbook authority. The blocker is that the current isolated lab state does not reproduce the healthy radio-active shape needed for a closure rerun.

The latest isolated rerun returned empty arrays on all three radios:

```text
WiFi.Radio.1.getRadioAirStats() returned
[
    ""
]
WiFi.Radio.2.getRadioAirStats() returned
[
    ""
]
WiFi.Radio.3.getRadioAirStats() returned
[
    ""
]
```

A short same-window trial rewrite (`20260414T182753422531`) also failed to recover parseable `getRadioAirStats()` / `ChannelLoad?` fields; it could only derive survey load (`S5=89`, `S6=65`, `S24=96`) while the air-stats getter path stayed blank.

Earlier source-backed triage for `D262 getRadioAirStats():void` already recorded the relevant runtime behavior: `_getRadioAirStats()` early-returns `amxd_status_ok` without filling the return map whenever the radio is not active (`wld_rad_isActive(pR) == false`).

Safe environment repair also fell back into the known shared 6G baseline blocker:

- `wifi-llapi baseline-qualify --band 6g --repeat-count 1 --soak-minutes 0`
- `6G ocv fix did not stabilize wl1 after retries`
- `sta_baseline_bss[1] not ready after 60s cmd=wl -i wl1 bss`
- `STA band baseline/connect failed`

That was the blocker state before baseline recovery restored structured air-stats objects.

## Evidence

### Historical authoritative full-run trace

File:

- `plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d257-getradioairstats-load.json`

Observed output:

```text
WiFi.Radio.1.getRadioAirStats() returned ... Load = 84
WiFi.Radio.2.getRadioAirStats() returned ... Load = 62
WiFi.Radio.3.getRadioAirStats() returned ... Load = 96
```

### Latest isolated rerun `20260414T183120002375`

Files:

- `plugins/wifi_llapi/reports/20260414T183120002375_DUT.log`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t183120002375.md`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t183120002375.json`

Observed output:

```text
WiFi.Radio.1.getRadioAirStats() returned
[
    ""
]
WiFi.Radio.2.getRadioAirStats() returned
[
    ""
]
WiFi.Radio.3.getRadioAirStats() returned
[
    ""
]
```

### Failed same-window probe `20260414T182753422531`

Files:

- `plugins/wifi_llapi/reports/20260414T182753422531_DUT.log`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t182753422531.md`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t182753422531.json`

Observed output:

```text
S5=89
S6=65
S24=96
failure_snapshot field=capture_5g.Air5 expected=^\d+$ actual=
```

## Resolution

Multi-band `wifi-llapi baseline-qualify --repeat-count 1 --soak-minutes 0` later recovered all three band links well enough for a follow-up official rerun. `D257` then exact-closed on workbook row `257` via `20260414T200750384793`, with tri-band getter output `Load = 83 / 62 / 98`. Keep this file only as provenance of the temporary blocker; current continuation should follow `compare-0401` and move to `D261 getRadioAirStats() TxTime`.
