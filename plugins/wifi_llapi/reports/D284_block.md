# D284 getScanResults() SecurityModeEnabled resolution notes

## Scope

- case id: `d284-getscanresults-securitymodeenabled`
- current YAML: `plugins/wifi_llapi/cases/D284_getscanresults_securitymodeenabled.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `284`
- current YAML row metadata: refreshed to `284`
- earlier decisive blocker reruns: `20260410T170750425931`, `20260410T171358112868`
- resolving official reruns: `20260412T015141491861`, `20260412T015235280960`

## Historical blocker

The earlier blocked rewrites both relied on target selectors that were not durable on 6G:

1. the first-WPA-target replay closed on 5G / 2.4G, but selected 6G target `3a:06:e6:2b:a3:1a` still came back as `IwSecurityMode6g=None`
2. follow-up manual probes then showed LLAPI and `iw` were drifting between at least two WPA3-capable 6G BSSIDs
3. the associated-BSSID rewrite still did not land, because the LLAPI step emitted no `LlapiBssid6g` and left the `iw` step with an unresolved runtime placeholder

So the blocker was real for the earlier selectors, but it did not prove the row itself was unalignable.

## Source authority

The active 0403 public security mode still comes from scan-result RSN / WPA / AKM evidence:

- `wldm_lib_wifi.c:4298-4337`
  - maps neighboring `SecurityModeEnabled` from `found_RSN / found_WPA3 / found_WPA2 / found_WPA / found_PSK`

So the durable replay must keep LLAPI and `iw` on the same serialized target, then re-derive the security mode from the same `iw` BSS block.

## Resolving official reruns

The resolving rewrite switched D284 away from first-WPA-target / associated-BSSID selection and onto the same transport-safe first-object pattern already proven by D283:

1. capture the first serialized LLAPI scan object with `head -60 | sed -n "/BSSID = /,/^        },/p"`
2. extract `BSSID` and LLAPI `SecurityModeEnabled`
3. replay the same `BSSID` in `iw dev wlX scan`
4. derive `IwSecurityMode*` from the same target's `RSN` / `WPA` / `Authentication suites`

### Official rerun `20260412T015141491861`

- 5G: `38:88:71:2f:f6:a7` -> `WPA2-Personal` / `WPA2-Personal`
- 6G: `6e:15:db:9e:33:72` -> `WPA3-Personal` / `WPA3-Personal`
- 2.4G: `2c:59:17:00:03:f7` -> `WPA2-Personal` / `WPA2-Personal`
- `diagnostic_status=Pass`

### Follow-up rerun `20260412T015235280960`

- 5G: `38:88:71:2f:f6:a7` -> `WPA2-Personal` / `WPA2-Personal`
- 6G: `6e:15:db:9e:33:72` -> `WPA3-Personal` / `WPA3-Personal`
- 2.4G: `2c:59:17:00:03:f7` -> `WPA2-Personal` / `WPA2-Personal`
- `diagnostic_status=Pass`

The second official rerun reproduced the same all-band shape exactly, so the new committed replay is durable enough for the official acceptance path.

## Current decision

`D284` is now **aligned**.

- YAML metadata is refreshed from stale row `286` to workbook row `284`
- the committed case now uses transport-safe first-object capture plus same-target `iw` security replay
- the committed oracle is: parseable first-object BSSID + non-empty LLAPI `SecurityModeEnabled` + same-target `IwSecurityMode == LlapiSecurityMode` on all three bands
- this file is retained as historical resolution notes for the rejected first-WPA-target / associated-BSSID selectors

## Next direction

1. Keep `D285` as the next remaining scan-results blocker to revisit.
2. Retain this history so future regressions do not switch D284 back to the unstable 6G selectors.
