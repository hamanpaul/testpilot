# D336 UnicastPacketsSent blocker history (resolved)

## Scope

- Case: `wifi-llapi-d336-unicastpacketssent`
- Workbook row authority: `D336` / workbook row `336`
- Current committed YAML is now aligned on workbook row `336`
- Latest stale replay run: `20260411T201639103833`
- Latest source-backed trial runs: `20260411T201939105374`, `20260411T202824539933`
- Resolving official rerun: `20260412T000744842751`

## Workbook-style replay result

The committed workbook-era case compares:

1. `WiFi.SSID.{i}.Stats.UnicastPacketsSent?`
2. `WiFi.SSID.{i}.getSSIDStats()`
3. `/proc/net/dev_extstats` field `$22`

Run `20260411T201639103833` proved that workbook path is no longer durable on 0403.

### Attempt 2 snapshot

- 5G: `direct / getSSIDStats / /proc = 26434 / 26434 / 0`
- 6G: `21540 / 21540 / 0`
- 2.4G: `10563 / 10563 / 0`

So the old `/proc/net/dev_extstats` `$22` path is rejected as a stale oracle.

## Source-backed trial results

### Trial 1: direct txframe/txmulti parser

Trial rewrite used the candidate formula:

- `(wl if_counters txframe + matching wds txframe) - (wl if_counters txmulti + matching wds txmulti)`

Run `20260411T201939105374` did not even reach semantic evaluation cleanly:

- 5G direct/getSSIDStats already exact-closed at `26439 / 26439`
- `driver_5g` step failed with `/tmp/_tp_cmd.sh: line 1: syntax error: unexpected "(" (expecting ")")`

That parser was rejected.

### Trial 2: safer awk+expr parser

Run `20260411T202824539933` removed the shell parse failure, but the formula still did not converge deterministically:

- attempt 1: 6G drifted `direct / getSSIDStats / driver = 21654 / 21654 / 21682` (`+28`)
- attempt 2: 5G exact-closed `26444 / 26444 / 26444`
- attempt 2: 6G exact-closed `21759 / 21759 / 21759`
- attempt 2: 2.4G still drifted `11690 / 11690 / 11691` (`+1`)

So the signed txframe/txmulti formula was directionally close, but that intermediate trial was not yet durable across retries and bands.

### Superseding runner revalidation: unsigned formula closes the row

Further source/live tracing showed the active 0403 path is more specific than the earlier trial captured:

- `whm_brcm_api_ext.c` derives `UnicastPacketsSent = PacketsSent - MulticastPacketsSent`
- both fields are stored as `uint32_t`, so underflow wraps instead of clamping
- `whm_brcm_vap.c` only copies/accumulates `UnicastPacketsSent`; it does not recompute it after later multicast/broadcast adjustments

Focused DUT-only probes then exact-closed the unsigned formula repeatedly on the current baseline:

- 5G: `direct / getSSIDStats / driver = 4294846062 / 4294846062 / 4294846062`
- 6G: `4294876430 / 4294876430 / 4294876430`
- 2.4G: `4294955352 / 4294955352 / 4294955352`

The official rerun `20260412T000744842751` promoted that into the real runner path:

- attempt 1
  - 5G: `27169 / 27169 / 27169`
  - 6G: `24709 / 24710 / 24710`
  - 2.4G: `17013 / 17013 / 17014`
- attempt 2
  - 5G: `27172 / 27172 / 27172`
  - 6G: `24703 / 24703 / 24703`
  - 2.4G: `17117 / 17117 / 17117`

So the row now passes under the official retry policy once the driver oracle uses the unsigned `((txframe + matching wds txframe) - (d11_txmulti + matching wds d11_txmulti)) & 0xffffffff` shape.

## Current decision

`D336` is now **aligned**.

- stale workbook `/proc $22` is rejected
- the committed YAML now uses the unsigned txframe/d11_txmulti source-backed oracle at workbook row `336`
- this file remains only as historical evidence for the failed intermediate trials before the resolving rerun

## Next direction

1. Keep the historical failed-trial evidence here so future regressions do not fall back to workbook `/proc $22` or the earlier signed formula.
2. Resume from the remaining direct-stats blockers: `D322`, `D331`, `D333`.
