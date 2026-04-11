# D282 getScanResults() OperatingStandards blocker

## Status

- case id: `d282-getscanresults-operatingstandards`
- current YAML: `plugins/wifi_llapi/cases/D282_getscanresults_operatingstandards.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `282`
- current YAML row metadata: `284`
- disposition: **blocked / keep YAML unchanged**
- blocker type: **active 0403 public `getScanResults().OperatingStandards` does have a same-source sibling in `WiFi.NeighboringWiFiDiagnostic()`, but live runtime currently reports only `wl2`; `wl0`/`wl1` still fail, so the oracle is not yet durable enough to commit**

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
3. that sibling path already exact-closes 2.4G same-target `OperatingStandards`, but live runtime still returns `FailedRadios = "wl0,wl1"` / `ReportingRadios = "wl2"`
4. so 5G/6G still lack a durable same-target sibling replay even though the right source family is now identified

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
- `src/RadMgt/wld_rad_scan.c:1629-1665`
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

## Why no YAML rewrite landed

1. the active public source is now traced to nl80211 IE parsing plus shared bitmask serialization, not to the old Broadcom helper
2. the public workbook row only exports `OperatingStandards`, but the sibling diagnostic path does expose both `OperatingStandards` and `SupportedStandards` from the same `wld_scanResultSSID_t`
3. the new sibling path exact-closes same-target 2.4G, so it is a valid reopen candidate in principle
4. however, live `WiFi.NeighboringWiFiDiagnostic()` currently reports only `wl2` and fails `wl0`/`wl1`
5. therefore there is still no live-authoritative basis to:
   - refresh `source.row` from `284` to `282`
   - commit any new workbook-style equality semantics
   - declare `WiFi.NeighboringWiFiDiagnostic()` durable enough as the all-band sibling oracle for this row

So D282 must remain blocked and the committed YAML stays unchanged for now.

## Best next direction if this row is reopened

1. first stabilize `WiFi.NeighboringWiFiDiagnostic()` so it reports `wl0` / `wl1` / `wl2` together under the current baseline
2. if that succeeds, reopen D282 with a same-target replay shape:
   - `getScanResults()` captures `BSSID + OperatingStandards`
   - `NeighboringWiFiDiagnostic().Result[]` replays the same `Radio + BSSID`
   - `SupportedStandards` is kept as evidence only, not as the row-282 verdict source
3. only after the sibling oracle becomes all-band durable, decide whether D282 should become:
   - a workbook-style plain `Pass`, or
   - a source-backed mixed verdict / fail-shaped mismatch
