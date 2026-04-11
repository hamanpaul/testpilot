# D282 getScanResults() OperatingStandards blocker

## Status

- case id: `d282-getscanresults-operatingstandards`
- current YAML: `plugins/wifi_llapi/cases/D282_getscanresults_operatingstandards.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `282`
- current YAML row metadata: `284`
- disposition: **blocked / keep YAML unchanged**
- blocker type: **active 0403 public `getScanResults().OperatingStandards` does have a same-source sibling in `WiFi.NeighboringWiFiDiagnostic()`, but that sibling launches fresh internal scans and still cannot produce an all-band durable replay (`ReportingRadios="wl0"`, `FailedRadios="wl1,wl2"` in the newest same-window probe)**

## Why this case is blocked

The old blocker explanation mixed the legacy Broadcom `_wldm_get_standards()` helper with the active public `ubus-cli "WiFi.Radio.{i}.getScanResults()"` path. New source tracing shows the current public path is different.

For the active 0403 public getter, `OperatingStandards` is carried in `wld_scanResultSSID_t.operatingStandards`, copied out of parsed beacon/probe IEs, cached in `pRad->scanState.lastScanResults`, and finally serialized with `swl_radStd_toChar(..., SWL_RADSTD_FORMAT_STANDARD, 0)`.

That matters because the shared radio-standards model is a **bitmask**, not a single-value enum, and the shared header explicitly marks the older "legacy representation" as something to avoid. So cumulative LLAPI shapes such as `a,n,ac,ax`, `ax,be`, or `b,g,n,ax` are expected on the active public path and do not need to match the older Broadcom helper's `if / else-if` output shape.

The newer source reading also tightens the model further:

1. the nl80211 parser fills **both** `pResult->operatingStandards` and `pResult->supportedStandards`
2. but `_getScanResults()` / `s_getScanResults()` only serializes public `OperatingStandards`
3. the sibling `SupportedStandards` bitmask is serialized only in other diagnostic/helper paths, not in the public row used by workbook `282`

The blocker is now narrower:

1. the old `iw` / capability-family replay is not guaranteed to be the same-source oracle for public `OperatingStandards`
2. a same-source sibling serializer does exist in the active pWHM ubus path: `WiFi.NeighboringWiFiDiagnostic()`
3. but that sibling is **not** a cache dump; it launches a fresh internal scan on each radio and only serializes radios that actually finish that diagnostic scan
4. so `getScanResults()` can legally still show 6G/2.4G targets while `NeighboringWiFiDiagnostic()` omits them in the same runtime window
5. the sibling path already exact-closes one 2.4G same-target replay in principle, but the newest live probe still reports only `ReportingRadios = "wl0"` / `FailedRadios = "wl1,wl2"`
6. therefore 6G and 2.4G still lack a durable all-band same-target sibling replay even though the right source family is now identified

## Active public 0403 path

The active `ubus-cli "WiFi.Radio.{i}.getScanResults()"` chain is:

1. `wld_nl80211_getScanResultsPerFreqBand(...)` returns band-filtered scan results through the nl80211 scan callback path
2. `wld_nl80211_parser.c` parses `NL80211_BSS_INFORMATION_ELEMENTS` / `NL80211_BSS_BEACON_IES` with `swl_80211_parseInfoElementsBuffer(...)`
3. `s_copyScanInfoFromIEs(...)` copies `pWirelessDevIE->operatingStandards` into `wld_scanResultSSID_t.operatingStandards`
4. the same parser also copies `pWirelessDevIE->supportedStandards` into `wld_scanResultSSID_t.supportedStandards`
5. `wifiGen_rad_getScanResults(...)` returns copies of `pRad->scanState.lastScanResults`
6. `_getScanResults()` / `s_getScanResults()` serializes only `ssid->operatingStandards` to the public `OperatingStandards` string with `SWL_RADSTD_FORMAT_STANDARD`
7. the sibling diagnostic path `WiFi.NeighboringWiFiDiagnostic()` serializes **both** `OperatingStandards` and `SupportedStandards` from the same `wld_scanResultSSID_t`

Key citations:

- `src/nl80211/wld_nl80211_scan.c:325-352`
- `src/nl80211/wld_nl80211_parser.c:1409-1426`
- `src/nl80211/wld_nl80211_parser.c:1524-1539`
- `src/Plugin/wifiGen_rad.c:1110-1119`
- `src/RadMgt/wld_rad_scan.c:544-605`
- `src/RadMgt/wld_rad_scan.c:1492-1520`
- `odl/wld_definitions.odl:160-168`
- `src/RadMgt/wld_rad_scan.c:1377-1404`
- `src/RadMgt/wld_rad_scan.c:1551-1584`
- `src/RadMgt/wld_rad_scan.c:1629-1668`
- `src/wld_radio.c:3884-3890`
- `targets/BGW720-300/fs.build/public/include/prplos/swl/swl_common_radioStandards.h:128-172`

The critical shared-model points are:

- `swl_wirelessDevice_infoElements_t` stores both `operatingStandards` and `supportedStandards` as `swl_radioStandard_m` bitmasks
- `_getScanResults()` only exports `OperatingStandards`, even though the parser also populated `supportedStandards`
- `SWL_RADSTD_FORMAT_STANDARD` is the active public serialization format
- the shared header explicitly says the old legacy representation should be avoided

## Legacy Broadcom path that must not be treated as the active public authority

The older Broadcom helper still exists:

- `bcmdrivers/.../wldm_lib_wifi.c:4350-4418`

It parses `HT / VHT / HE / EHT` markers using an `if / else-if` chain and then does:

```c
/* Set OperatingStandards same as SupportedStandards */
strncpy(neighbor[i].ap_OperatingStandards, neighbor[i].ap_SupportedStandards,
        sizeof(neighbor[i].ap_OperatingStandards));
```

This helper is useful as a legacy comparison point, but it is not the same model as the active public ubus path:

1. it collapses `OperatingStandards` into the same string as `SupportedStandards`
2. it is based on Broadcom raw scan text heuristics
3. it does not express the shared-model bitmask semantics used by the active public path

So the older `_wldm_get_standards()` logic cannot be treated as the definitive authority for the current ubus row.

## Live replay that was tested and rejected

### Attempted command

```bash
uv run python -m testpilot.cli run wifi_llapi --case d282-getscanresults-operatingstandards --dut-fw-ver BGW720-0403
```

### Isolated rerun `20260410T163026194231`

Observed output shape:

```text
5G:
  LlapiOperatingStandards5g=a,n,ac,ax
  WlOperatingStandards5g=a,n,ac,ax

6G:
  LlapiOperatingStandards6g=ax,be
  WlOperatingStandards6g=(missing)

2.4G:
  LlapiOperatingStandards24g=b,g,n,ax
  WlOperatingStandards24g=b,g,n,ax,be
```

So the workbook-style replay still failed in two different ways:

1. 6G never produced a same-target external compare block
2. 2.4G external replay kept one extra family (`be`) beyond the public LLAPI value
3. the public LLAPI capture itself exposed only `LlapiOperatingStandards*`; there was no same-target public `SupportedStandards` field to tell whether the external `...,+be` was actually matching the sibling supported-family bitmask instead

### Controlled baseline probes

The follow-up baseline probes also did not close the gap:

- `testpilot5G`: LLAPI `a,n,ac,ax,be`, external replay `a,n,ac,ax`
- `testpilot6G`: not found in the same LLAPI/external replay snapshot
- `testpilot2G`: not found in LLAPI scan output, but the external replay still showed an EHT-capable baseline BSSID

This reinforces that the current external replay is not a durable same-source oracle for the active public field.

### Manual sibling-diagnostic probe on the active ubus path

After the source survey identified `WiFi.NeighboringWiFiDiagnostic()` as the same-source sibling serializer, a direct live probe was run on DUT (`COM1`) without changing YAML.

Observed runtime facts:

1. `ubus-cli "WiFi.Radio.3.getScanResults()" | head -22` currently returns first 2.4G target `BSSID = "04:70:56:D2:22:4F"` with `OperatingStandards = "b,g,n,ax"`
2. `ubus-cli "WiFi.NeighboringWiFiDiagnostic()" | grep -i -A16 -B1 "04:70:56:D2:22:4F"` returns the same target on `Radio = "WiFi.Radio.3"` with:
   - `OperatingStandards = "b,g,n,ax"`
   - `SupportedStandards = "b,g,n,ax"`
3. `ubus-cli "WiFi.Radio.1.getScanResults()" | head -30` currently returns first 5G target `BSSID = "62:15:DB:9E:31:F1"` with `OperatingStandards = "a,n,ac,ax,be"`
4. `ubus-cli "WiFi.Radio.2.getScanResults()" | head -30` currently returns first 6G target `BSSID = "2C:59:17:00:19:96"` with `OperatingStandards = "ax,be"`
5. but `ubus-cli "WiFi.NeighboringWiFiDiagnostic()" | grep -E "FailedRadios|ReportingRadios"` currently reports:

```text
FailedRadios = "wl0,wl1"
ReportingRadios = "wl2"
```

So the new sibling path is real and source-correct, but it is only usable on 2.4G in the current live environment. That is not enough to promote D282 to a committed all-band replay.

### New readiness-gated sibling probe after focused baseline recovery

The latest source + runtime pass clarifies **why** the sibling remains non-durable.

Source now shows:

1. `_NeighboringWiFiDiagnostic()` does **not** read cached `lastScanResults`
2. it registers a scan-status callback and calls `s_startScan(..., SCAN_TYPE_INTERNAL)` on every radio
3. `s_startScan()` first requires `wld_rad_isUpAndReady(pRad)`, i.e. detailed state in `CM_RAD_UP` / `CM_RAD_BG_CAC_EXT` / `CM_RAD_BG_CAC_EXT_NS` / `CM_RAD_DELAY_AP_UP`, and no scan already running
4. radios only enter `ReportingRadios` when the diagnostic scan-complete callback sees `event->success=true`; start failures or unsuccessful completions land in `FailedRadios`
5. only `completedRads` are later serialized into `NeighboringWiFiDiagnostic().Result[]`

So the sibling oracle is a fresh-scan readiness-gated view, not a guaranteed replay of already visible `getScanResults()` cache entries.

To test whether environment repair could make that sibling durable, a focused recovery run was executed:

```bash
uv run python -m testpilot.cli wifi-llapi baseline-qualify --band 6g --band 2.4g --repeat-count 1 --soak-minutes 0
```

Observed outcome:

1. 2.4G qualification became stable and ended with DUT `wl2 bss=up`, STA linked to `testpilot2G`
2. 6G still failed both qualification rounds at post-verify with `dut_ocv_not_zero`
3. immediately after that recovery, live readback still showed:
   - `Device.WiFi.Radio.1.ChannelMgt.RadioStatus="Up"`
   - `Device.WiFi.Radio.2.ChannelMgt.RadioStatus="Down"`
   - `Device.WiFi.Radio.3.ChannelMgt.RadioStatus="Down"`
4. in the same time window, `getScanResults()` still returned first targets on all three radios:
   - 5G `2C:59:17:00:03:E5` with `OperatingStandards="a,n,ac,ax,be"`
   - 6G `2C:59:17:00:19:96` with `OperatingStandards="ax,be"`
   - 2.4G `2C:59:17:00:03:F7` with `OperatingStandards="b,g,n,ax,be"`
5. but the immediate sibling diagnostic still returned:

```text
FailedRadios = "wl1,wl2"
ReportingRadios = "wl0"
```

and only included the 5G same-target entry `BSSID="2C:59:17:00:03:E5"`.

This is the strongest live-authoritative evidence so far that the sibling method is still not an all-band durable replay oracle for row 282.

## Why no YAML rewrite landed

1. the active public source is now traced to nl80211 IE parsing plus shared bitmask serialization, not to the old Broadcom helper
2. the public workbook row only exports `OperatingStandards`, but the sibling diagnostic path does expose both `OperatingStandards` and `SupportedStandards` from the same `wld_scanResultSSID_t`
3. source now proves that sibling diagnostic is a fresh internal-scan path gated by radio readiness and scan success, not a stable cache replay
4. even after focused 6G/2.4G baseline recovery, same-window live probes still show `getScanResults()` data on all three radios while `NeighboringWiFiDiagnostic()` reports only `wl0`
5. the best-case sibling replay is still limited to one band at a time (older 2.4G-only proof, newer 5G-only proof), never all three together
6. therefore there is still no live-authoritative basis to:
   - refresh `source.row` from `284` to `282`
   - commit any new workbook-style equality semantics
   - declare `WiFi.NeighboringWiFiDiagnostic()` durable enough as the all-band sibling oracle for this row

So D282 must remain blocked and the committed YAML stays unchanged for now.

## Source-level investigation: full call path and FailedRadios mechanics

### BGW720-0403-VERIFY build, wld_rad_scan.c

**Key source file:**
`pwhm-v7.6.38/src/RadMgt/wld_rad_scan.c`

#### Complete `WiFi.NeighboringWiFiDiagnostic()` call path

```
ubus-cli "WiFi.NeighboringWiFiDiagnostic()"
  → tr181-wifi plugin: _NeighboringWiFiDiagnostic() [dm_method.c:36]
    → mod_wifi_neighboring_diagnostic(retval) [mod_wifi_intf.c:361]
      → amxm_execute_function(SO_NAME, MODNAME_WIFICTRL, "execute_method", ...)
        → wifi_radio_neighboring_diagnostic() [wifi_radio.c:2025]  (dispatch table: wifi_system.c:83)
          → diag_start(ret)   -- DiagnosticsState = "Requested"
          → diag_wait_for_complete()  -- 10s timeout in mod-wifi layer
          → diag_collect_results(ret)
             [parallel in WLD: _NeighboringWiFiDiagnostic() wld_rad_scan.c:1629]
              → s_startScan(radio, SCAN_TYPE_INTERNAL) per Radio -- wld_rad_scan.c:1660
              → swl_function_defer() -- async; scan events drive completion
              → s_radScanStatusUpdateCb() -- wld_rad_scan.c:1377
              → s_sendNeighboringWifiDiagnosticResult() -- wld_rad_scan.c:1587
                → mfn_wrad_scan_results() per completedRad -- line 1609
                → s_addDiagRadioResultsToMap() → s_addDiagSingleResultToMap() -- line 1492
```

#### FailedRadios / ReportingRadios state machine (wld_rad_scan.c)

**Global state** (`g_neighWiFiDiag`, line 81): four `amxc_llist_t` lists:
`runningRads`, `completedRads`, `failedRads`, `canceledRads`

**Scan start (line 1654–1663):**
```c
// for each Radio instance:
status = s_startScan(pRadio->pBus, func, &localArgs, retval, SCAN_TYPE_INTERNAL);
if(status != amxd_status_deferred) {
    amxc_llist_add_string(&g_neighWiFiDiag.failedRads, pRadio->Name);  // immediate fail
}
```

`s_startScan()` fails and returns non-deferred when (line 300–393):
1. `wld_scan_isRunning(pR)` — a scan is already running on this radio (`scanType != SCAN_TYPE_NONE`)
2. `!wld_rad_isUpAndReady(pR)` — radio is not in up/ready state
3. `s_isExternalScanFilter(pR)` — vendor scan filter active
4. `wld_scan_start()` returns error from kernel/nl80211

**Scan completion callback `s_radScanStatusUpdateCb()` (line 1377):**
```c
if(event->start) {
    amxc_llist_add_string(&g_neighWiFiDiag.runningRads, pRadio->Name);  // added to running
    return;
}
// on scan done:
if(event->success) {
    amxc_llist_append(&g_neighWiFiDiag.completedRads, it);  // → ReportingRadios
} else {
    amxc_llist_append(&g_neighWiFiDiag.failedRads, it);     // → FailedRadios
}
// if runningRads empty: s_sendNeighboringWifiDiagnosticResult()
```

**Result assembly `s_addDiagRadiosStatusToMap()` (line 1560):**
```c
if(!amxc_llist_is_empty(&g_neighWiFiDiag.runningRads)) {
    // timeout path: any still-running radio goes to FailedRadios
    s_addDiagRadiosListToMap(retval, "FailedRadios", &g_neighWiFiDiag.runningRads);
    return;
}
s_addDiagRadiosListToMap(retval, "ReportingRadios", &g_neighWiFiDiag.completedRads);  // line 1582
s_addDiagRadiosListToMap(retval, "FailedRadios",    &g_neighWiFiDiag.failedRads);     // line 1584
```

#### Why `wl0`/`wl1` end up in FailedRadios

When `_NeighboringWiFiDiagnostic()` is called, `s_startScan()` is called for each radio
in sequence. 5G (`wl0`) and 2.4G (`wl1`) fail at `s_startScan()` call time when they are
already running a background scan (ACS, chanim, auto-scan) at that exact moment —
`wld_scan_isRunning(pR)` returns `true` because `pR->scanState.scanType != SCAN_TYPE_NONE`.

The "failing set" drifts between calls (`wl0,wl1` vs `wl1,wl2`) because background scans
run periodically and asynchronously; whichever radios happen to be mid-scan when
`_NeighboringWiFiDiagnostic()` iterates them determines the failing set.

#### Why this does NOT affect `getScanResults()`

`_getScanResults()` (line 655) → `s_getScanResults()` (line 544):
```c
if(pR->pFA->mfn_wrad_scan_results(pR, &res) < 0) { ... }
```
This reads cached scan results **without calling `s_startScan()` or `wld_scan_start()`**.
No scan is initiated; no `s_isScanRequestReady()` check; no race with background scans.
A radio being busy with an in-progress ACS scan does not affect `getScanResults()` at all.

#### OperatingStandards source: confirmed identical for both paths

`getScanResults()` path (line 602–605):
```c
swl_radStd_toChar(operatingStandardsChar, sizeof(operatingStandardsChar),
                  ssid->operatingStandards, SWL_RADSTD_FORMAT_STANDARD, 0);
amxc_var_add_key(cstring_t, pEntry, "OperatingStandards", operatingStandardsChar);
```

`NeighboringWiFiDiagnostic()` path via `s_addDiagSingleResultToMap()` (line 1515–1520):
```c
swl_radStd_toChar(operatingStandardsChar, sizeof(operatingStandardsChar),
                  pSsid->operatingStandards, SWL_RADSTD_FORMAT_STANDARD, 0);
swl_radStd_toChar(supportedStandardsChar, sizeof(supportedStandardsChar),
                  pSsid->supportedStandards, SWL_RADSTD_FORMAT_STANDARD, 0);
amxc_var_add_key(cstring_t, resulMap, "OperatingStandards", operatingStandardsChar);
amxc_var_add_key(cstring_t, resulMap, "SupportedStandards", supportedStandardsChar);
```

Both use `wld_scanResultSSID_t.operatingStandards` + `SWL_RADSTD_FORMAT_STANDARD`.
**The `OperatingStandards` values are guaranteed identical if the same scan cache entry is read.**

Note: the `SupportedStandards` bug (SSW-8679, `supportedStandards = operatingStandards`)
exists only in `fillFullScanResultsList()` (line 853–854, used for full-scan ODL updates),
NOT in the `_NeighboringWiFiDiagnostic()` path. The diagnostic path correctly reads the
separate `pSsid->supportedStandards` field.

#### `SCAN_TYPE_INTERNAL` semantics

From `wld.h:1123`:
```c
SCAN_TYPE_INTERNAL, // Internal middleware to know AP environment => no ODL update
```
The diagnostic scan does not update the ODL data model. Results are returned only via
the deferred function call return value.

## Best next direction if this row is reopened

The source investigation confirms the FailedRadios problem is a **scan-busy race at call
time**, not a configuration or protocol issue. `NeighboringWiFiDiagnostic()` calls
`s_startScan()` which calls `s_isScanRequestReady()` — if a radio already has
`scanState.scanType != SCAN_TYPE_NONE` (a background ACS/chanim scan in progress),
`wl_scan_isRunning()` returns `true` and the radio is immediately added to `failedRads`
before any scan is attempted. The set drifts because periodic background scans
fire at unpredictable times.

`getScanResults()` does NOT call `s_startScan()` — it reads the cached
`wld_scanResultSSID_t` entries directly via `mfn_wrad_scan_results()`, so background
scan activity is irrelevant.

**Recommended path:**

1. Switch the oracle to per-radio `getScanResults()` (three sequential calls).
   This reads the same `wld_scanResultSSID_t.operatingStandards` field with the same
   `swl_radStd_toChar(SWL_RADSTD_FORMAT_STANDARD)` serialization, but without the race.
   - `WiFi.Radio.1.getScanResults()` → 5G BSSID + OperatingStandards
   - `WiFi.Radio.2.getScanResults()` → 6G BSSID + OperatingStandards
   - `WiFi.Radio.3.getScanResults()` → 2.4G BSSID + OperatingStandards

2. The sibling `NeighboringWiFiDiagnostic()` probe can be kept as optional evidence
   (confirming source identity on 2.4G) but must NOT be the primary verdict oracle.

3. A `NeighboringWiFiDiagnostic()`-based D282 rewrite is only viable in a controlled
   window where all background scans on all three radios are quiesced simultaneously —
   which is not achievable in normal lab operation without dedicated firmware support.
