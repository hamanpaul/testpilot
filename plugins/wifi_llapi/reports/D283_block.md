# D283 getScanResults() RSSI resolution notes

## Scope

- case id: `d283-getscanresults-rssi`
- current YAML: `plugins/wifi_llapi/cases/D283_getscanresults_rssi.yaml`
- workbook authority: `0401.xlsx` `Wifi_LLAPI` row `283`
- current YAML row metadata: refreshed to `283`
- earlier decisive blocker rerun: `20260411T214050136894`
- resolving official reruns: `20260412T013944779069`, `20260412T014018880783`

## Historical blocker

The earlier committed generic case still used a full-payload `read` against `WiFi.Radio.{i}.getScanResults()`. On the active 0403 lab state, that shape reproduced the old transport failure:

1. historical full run `20260409T213837737224` already failed at `step_6g_scan`
2. isolated rerun `20260410T164405221878` hung after `setup_env`
3. isolated rerun `20260411T214050136894` again emitted no step output, no top-level report files, and left `plugins/wifi_llapi/reports/agent_trace/20260411T214050136894/` empty

So the blocker was real for the committed full-payload shape, but it was not the end-state of the row itself.

## Corrected source trace

Active 0403 source tracing shows `D283 RSSI` is the same public field family as `D286 SignalStrength`:

1. `wld_nl80211_parser.c` fills `pResult->rssi` from `NL80211_BSS_SIGNAL_UNSPEC` or `NL80211_BSS_SIGNAL_MBM`
2. `wld_rad_scan.c` serializes public `RSSI = ssid->rssi`
3. the same file also serializes public `SignalStrength = ssid->rssi`

So the durable public replay for this row is not another raw full-payload probe; it is a transport-safe first-object capture that proves the public scan object exposes a parseable BSSID and that public `RSSI` / public `SignalStrength` stay equal on the same serialized target.

## Resolving official reruns

The resolving rewrite switched D283 to the same transport-safe first-object pattern that had already unblocked D277:

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

### Official rerun `20260412T013944779069`

- 5G: `38:88:71:2f:f6:a7 / -66 / -66`
- 6G: `6e:15:db:9e:33:72 / -95 / -95`
- 2.4G: `2c:59:17:00:03:f7 / -47 / -47`
- `diagnostic_status=Pass`

### Follow-up rerun `20260412T014018880783`

- 5G: `38:88:71:2f:f6:a7 / -66 / -66`
- 6G: `6e:15:db:9e:33:72 / -95 / -95`
- 2.4G: `2c:59:17:00:03:f7 / -47 / -47`
- `diagnostic_status=Pass`

The follow-up rerun reproduced the same all-band shape exactly, so the new committed replay is durable enough for the official acceptance path.

## Current decision

`D283` is now **aligned**.

- YAML metadata is refreshed from stale row `285` to workbook row `283`
- the committed case uses transport-safe first-object replay rather than the older full-payload scan
- the committed oracle is: parseable public BSSID + numeric public RSSI + `SignalStrength == RSSI` on the same first scan object for all three bands
- this file is retained as historical resolution notes for the rejected full-payload transport shape

## Next direction

1. Keep `D286` blocked until its own committed oracle is explicitly revalidated; D283's shared-field-family result should inform that revisit, but it does not by itself close D286.
2. Resume from the next remaining scan-results blocker in the current queue: `D284`.
