# D524 SSID WMM AC_BE Stats WmmPacketsSent block

- workbook row: `524`
- current committed YAML row: `391` (no rewrite landed; committed case remains unchanged)
- compare overlay: `compare-0401.md` still maps `d524-ssid-wmm-ac_be_stats_wmmpacketssent` to workbook `Pass / Pass / Pass`
- disposition: **blocked by tri-band tx-frame oracle drift under the current lab shape**

## Focused live survey

The current live replay exact-closes the API path on every band:

```text
5G   getSSIDStats/direct = 452 / 452
6G   getSSIDStats/direct = 510 / 510
2.4G getSSIDStats/direct = 547 / 547
```

But the same-window driver `wl wme_counters` `AC_BE` **tx frames** do not close:

```text
5G   driver tx frames = 896
6G   driver tx frames = 1015
2.4G driver tx frames = 1090
```

That means promoting `D524` to workbook `Pass / Pass / Pass` would currently require either:

1. accepting an API-only close, or
2. inventing a derived oracle that is not justified by the workbook evidence.

Both are disallowed, so the case stays blocked.

## Why this is blocked

- workbook `G524` explicitly assumes a **two-station** throughput path before judging `WmmPacketsSent.AC_BE`
- under the current single-STA continuation path, `getSSIDStats()` and the direct getter agree with each other but drift on all three bands against the obvious driver candidate `tx frames`
- the drift is not a one-band anomaly:
  - 5G: `452 / 452 / 896`
  - 6G: `510 / 510 / 1015`
  - 2.4G: `547 / 547 / 1090`
- therefore there is no stable independent oracle yet for a workbook-faithful rewrite

## Evidence

### Focused serialwrap survey (2026-04-15)

Commands used:

```sh
ubus-cli "WiFi.SSID.4.getSSIDStats()" | sed -n '/WmmPacketsSent = {/,/}/p'
ubus-cli "WiFi.SSID.4.Stats.WmmPacketsSent.AC_BE?"
wl -i wl0 wme_counters | grep -A2 '^AC_BE:'

ubus-cli "WiFi.SSID.6.getSSIDStats()" | sed -n '/WmmPacketsSent = {/,/}/p'
ubus-cli "WiFi.SSID.6.Stats.WmmPacketsSent.AC_BE?"
wl -i wl1 wme_counters | grep -A2 '^AC_BE:'

ubus-cli "WiFi.SSID.8.getSSIDStats()" | sed -n '/WmmPacketsSent = {/,/}/p'
ubus-cli "WiFi.SSID.8.Stats.WmmPacketsSent.AC_BE?"
wl -i wl2 wme_counters | grep -A2 '^AC_BE:'
```

Observed output:

```text
5G
GetSSIDStatsWmmPacketsSent5g=452
WiFi.SSID.4.Stats.WmmPacketsSent.AC_BE=452
AC_BE: tx frames: 896 bytes: 398214 failed frames: 0 failed bytes: 0

6G
GetSSIDStatsWmmPacketsSent6g=510
WiFi.SSID.6.Stats.WmmPacketsSent.AC_BE=510
AC_BE: tx frames: 1015 bytes: 484878 failed frames: 0 failed bytes: 0

2.4G
GetSSIDStatsWmmPacketsSent24g=547
WiFi.SSID.8.Stats.WmmPacketsSent.AC_BE=547
AC_BE: tx frames: 1090 bytes: 526480 failed frames: 0 failed bytes: 0
```

## Current disposition

- `D524` remains **blocked**
- committed YAML and runtime metadata stay unchanged (`row 391`, `Fail / Fail / Fail`)
- next ready compare-open case: `D525 SSID WMM AC_BK Stats WmmPacketsSent`
