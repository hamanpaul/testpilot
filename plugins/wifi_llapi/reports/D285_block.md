# D285 getScanResults() SignalNoiseRatio resolution notes

## Scope

- case id: `d285-getscanresults-signalnoiseratio`
- current YAML: `plugins/wifi_llapi/cases/D285_getscanresults_signalnoiseratio.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `285`
- current YAML row metadata: refreshed to `285`
- earlier decisive blocker evidence: raw same-target `wl` replay could not close
- resolving official reruns: `20260412T020817105728`, `20260412T020839239161`

## Historical blocker

The earlier blocker treated `SignalNoiseRatio` as if it had to replay against raw driver `SNR` on the same BSSID:

1. the old 6G LLAPI first target `3A:06:E6:2B:A3:1A` could not even be replayed through direct `wl -i wl1 escanresults`
2. the old 2.4G same-target raw probe on `8C:19:B5:6E:85:E1` drifted badly (`LLAPI 34` vs raw `SNR 21`)
3. that proved the old raw-driver oracle was not durable, but it did not prove the public row itself was unalignable

## Corrected source authority

Active 0403 source tracing shows the public row is not backed by a standalone raw `SNR:` field:

1. `targets/BGW720-300/fs.install/etc/amx/wld/wld_radio.odl:72-86` declares public `scanresult_t` with `SignalNoiseRatio`, `Noise`, `RSSI`, and `SignalStrength`
2. `bcmdrivers/broadcom/net/wl/impl107/main/components/apps/wldm/wldm_lib_wifi.h:803-821` still keeps neighboring internals on `ap_SignalStrength` plus `ap_Noise`; there is no neighboring `ap_SignalNoiseRatio`
3. `bcmdrivers/broadcom/net/wl/impl107/main/components/apps/wldm/wldm_lib_wifi.c:4928-4938` fills those neighboring fields from raw `RSSI: ` and `noise: `

So the durable public replay for D285 is the same serialized scan object itself: capture its public `RSSI`, `Noise`, and `SignalNoiseRatio`, then verify the public invariant `SignalNoiseRatio == RSSI - Noise`.

## Resolving official reruns

The resolving rewrite switched D285 onto the same transport-safe first-object pattern already proven by D283/D284:

```bash
BLOCK=$(ubus-cli "WiFi.Radio.N.getScanResults()" | head -60 | sed -n "/BSSID = /,/^        },/p")
```

Each band then extracts:

- the first serialized `BSSID`
- public `RSSI`
- public `Noise`
- public `SignalNoiseRatio`
- derived `RSSI - Noise`

and validates:

- `BSSID` is parseable
- `RSSI` is numeric
- `Noise` is numeric
- `SignalNoiseRatio == RSSI - Noise`

### Official rerun `20260412T020817105728`

- 5G: `38:88:71:2f:f6:a7 / -66 / -100 / 34`
- 6G: `6e:15:db:9e:33:72 / -95 / -97 / 2`
- 2.4G: `2c:59:17:00:03:f7 / -47 / -80 / 33`
- `diagnostic_status=Pass`

### Follow-up rerun `20260412T020839239161`

- 5G: `38:88:71:2f:f6:a7 / -66 / -100 / 34`
- 6G: `6e:15:db:9e:33:72 / -95 / -97 / 2`
- 2.4G: `2c:59:17:00:03:f7 / -47 / -80 / 33`
- `diagnostic_status=Pass`

The second official rerun reproduced the same all-band shape exactly, so the committed replay is durable enough for the official acceptance path.

## Current decision

`D285` is now **aligned**.

- YAML metadata is refreshed from stale row `287` to workbook row `285`
- the committed case now uses transport-safe first-object capture rather than the older raw-driver same-target replay
- the committed oracle is: parseable public BSSID + numeric public RSSI/Noise + `SignalNoiseRatio == RSSI - Noise` on the same first scan object for all three bands
- this file is retained as historical resolution notes for the rejected raw `wl SNR` replay

## Next direction

1. Resume from the next remaining scan-results case in the current queue: `D286`.
2. Keep this history so future regressions do not switch D285 back to the unstable raw-driver `SNR` oracle.
