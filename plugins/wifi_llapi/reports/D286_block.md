# D286 getScanResults() SignalStrength resolution notes

## Scope

- case id: `d286-getscanresults-signalstrength`
- current YAML: `plugins/wifi_llapi/cases/D286_getscanresults_signalstrength.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `286`
- current YAML row metadata: refreshed to `286`
- earlier decisive blocker evidence: old workbook-style same-target `iw` / raw replay
- resolving official reruns: `20260412T021725610895`, `20260412T021748934770`

## Historical blocker

The earlier blocker treated D286 as if it still needed an external same-target replay distinct from D283:

1. the old workbook-style rewrite chased `iw` / raw-driver `RSSI` on the same BSSID
2. that path only partially closed on 5G, failed entirely on 6G, and drifted badly on 2.4G
3. so the external replay was not durable, but it did not prove the public row itself was unalignable

## Corrected source authority

Active 0403 source tracing shows D286 is the same public field family already proven by D283:

1. `targets/BGW720-300/fs.install/etc/amx/wld/wld_radio.odl:72-86` declares public `scanresult_t` with both `RSSI` and `SignalStrength`
2. `src/nl80211/wld_nl80211_parser.c:1471-1482` fills `pResult->rssi`
3. `src/RadMgt/wld_rad_scan.c:584` serializes public `RSSI = ssid->rssi`
4. `src/RadMgt/wld_rad_scan.c:588` serializes public `SignalStrength = ssid->rssi`

So on the active public ubus path, `SignalStrength` is not an independent external-oracle field; the durable replay is the same first serialized scan object itself, proving `SignalStrength == RSSI`.

## Resolving official reruns

The resolving rewrite re-used the same transport-safe first-object capture already proven by D283:

```bash
BLOCK=$(ubus-cli "WiFi.Radio.N.getScanResults()" | head -60 | sed -n "/BSSID = /,/^        },/p")
```

Each band then extracts:

- the first serialized `BSSID`
- public `RSSI`
- public `SignalStrength`

and validates:

- `BSSID` is parseable
- `RSSI` is numeric
- `SignalStrength == RSSI`

### Official rerun `20260412T021725610895`

- 5G: `38:88:71:2f:f6:a7 / -66 / -66`
- 6G: `6e:15:db:9e:33:72 / -95 / -95`
- 2.4G: `2c:59:17:00:03:f7 / -47 / -47`
- `diagnostic_status=Pass`

### Follow-up rerun `20260412T021748934770`

- 5G: `38:88:71:2f:f6:a7 / -66 / -66`
- 6G: `6e:15:db:9e:33:72 / -95 / -95`
- 2.4G: `2c:59:17:00:03:f7 / -47 / -47`
- `diagnostic_status=Pass`

The second official rerun reproduced the same all-band shape exactly, so the committed replay is durable enough for the official acceptance path.

## Current decision

`D286` is now **aligned**.

- YAML metadata is refreshed from stale row `288` to workbook row `286`
- the committed case now uses transport-safe first-object capture rather than the older same-target `iw` / raw replay
- the committed oracle is: parseable public BSSID + numeric public RSSI + `SignalStrength == RSSI` on the same first scan object for all three bands
- this file is retained as historical resolution notes for the rejected external replay model

## Next direction

1. Resume from the next remaining scan-results case in the current queue: `D287`.
2. Keep this history so future regressions do not reopen D286 with the old same-target `iw` / raw replay.
