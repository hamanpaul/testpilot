# D287 getScanResults() SSID resolution notes

## Scope

- case id: `d287-getscanresults-ssid`
- current YAML: `plugins/wifi_llapi/cases/D287_getscanresults_ssid.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `287`
- current YAML row metadata: refreshed to `287`
- earlier decisive blocker evidence: old workbook-style same-target replay on stale 6G target `3a:06:e6:2b:a3:1a`
- resolving official reruns: `20260412T022708923585`, `20260412T022738004752`

## Historical blocker

The earlier blocker did not prove the public row was unalignable. It proved the old selector was wrong:

1. the trial rewrite used a workbook-style same-target `iw` replay against 6G target `3a:06:e6:2b:a3:1a`
2. 5G and 2.4G exact-closed on that older replay path, but 6G never produced a same-target external `SSID`
3. direct raw `wl -i wl1 escanresults` also failed to replay that same stale 6G BSSID

So the blocker was the unstable/stale 6G target choice, not the public `SSID` field itself.

## Corrected source authority

Active 0403 source tracing keeps the public row on the parsed scan-result model:

1. `src/nl80211/wld_nl80211_parser.c:1409-1424` copies `pWirelessDevIE->ssid` into `wld_scanResultSSID_t.ssid`
2. `src/RadMgt/wld_rad_scan.c:577-579` serializes public `SSID` from `ssid->ssid / ssidLen` with `wld_ssid_to_string(...)`
3. `targets/BGW720-300/fs.install/etc/amx/wld/wld_radio.odl:72-86` declares public `scanresult_t` with both `SSID` and `BSSID`

So the durable replay must stay on the same serialized public scan object, not on the older stale external 6G target.

## Resolving official reruns

The resolving rewrite follows the same transport-safe first-object strategy already proven by D283-D286:

```bash
OUT=$(ubus-cli "WiFi.Radio.N.getScanResults()" | head -60)
```

Each band then extracts the first serialized:

- `BSSID`
- `SSID`

and replays the same BSSID via:

```bash
iw dev wlN scan | grep -A20 -im1 "^BSS $TARGET"
```

to compare:

- non-empty public `LlapiSSID`
- non-empty same-target external `IwSSID`
- `IwSSID == LlapiSSID`

The first official probe `20260412T022553794480` exposed a repo-side parser bug, not a runtime mismatch: the loose `SSID` extractor also matched `BSSID`, so 5G briefly compared `Verizon_Z4RY7R` against `38:88:71:2f:f6:a7`. Anchoring the LLAPI extractors to `^[[:space:]]*SSID = ` and `^[[:space:]]*BSSID = ` fixed that local bug without changing the case semantics.

### Official rerun `20260412T022708923585`

- 5G: `38:88:71:2f:f6:a7 / Verizon_Z4RY7R / Verizon_Z4RY7R`
- 6G: `6e:15:db:9e:33:72 / **TELUS0227 / **TELUS0227`
- 2.4G: `2c:59:17:00:03:f7 / OpenWrt_1 / OpenWrt_1`
- `diagnostic_status=Pass`

### Follow-up rerun `20260412T022738004752`

- 5G: `38:88:71:2f:f6:a7 / Verizon_Z4RY7R / Verizon_Z4RY7R`
- 6G: `6e:15:db:9e:33:72 / **TELUS0227 / **TELUS0227`
- 2.4G: `2c:59:17:00:03:f7 / OpenWrt_1 / OpenWrt_1`
- `diagnostic_status=Pass`

The second official rerun reproduced the same all-band shape exactly, so the committed replay is durable enough for the official acceptance path.

## Current decision

`D287` is now **aligned**.

- YAML metadata is refreshed from stale row `289` to workbook row `287`
- the committed case now uses transport-safe first-object capture plus same-target `iw` SSID replay
- the committed oracle is: parseable first-object BSSID + non-empty public SSID + non-empty same-target `iw` SSID + `IwSSID == LlapiSSID` on all three bands
- this file is retained as historical resolution notes for the rejected stale-6G-target replay model

## Next direction

1. Return to the remaining scan-results blockers in the current queue: `D281`, then `D282`.
2. Keep this history so future regressions do not reopen D287 with the old `3a:06:e6:2b:a3:1a` selector.
