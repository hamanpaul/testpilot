# D324 BytesSent resolution notes

## Scope

- Case: `wifi-llapi-d324-bytessent`
- Workbook row authority: `D324` / workbook row `324`
- Current YAML metadata: `source.row: 324`
- Historical aligned rerun: `20260411T010328768651`
- Latest failed full-run evidence: `20260411T074146043202`
- Latest failed isolated rerun: `20260411T190338070996`
- Latest failed official WDS-sum rerun: `20260412T005627796136`
- Resolving official rerun: `20260412T060612008433`

## Workbook-style procedure replay

The committed YAML currently replays this source-backed three-way compare on each band:

1. `WiFi.SSID.{i}.Stats.BytesSent?`
2. `WiFi.SSID.{i}.getSSIDStats()` extracted to `GetSSIDStatsBytesSent*`
3. `wl -i wlX if_counters` extracted to `DriverBytesSent*`

Pass currently requires `direct == getSSIDStats == wlX if_counters txbyte`.

## Live evidence

### Latest isolated rerun `20260411T190338070996`

#### Attempt 1

- 5G: `131874002 / 131874002 / 131873776` (`direct / getSSIDStats / wl0 txbyte`, drift `+226`)
- 6G: `81900899 / 81900899 / 81900741` (`+158`)
- 2.4G: `131947990 / 131947990 / 131631950` (`+316040`)

#### Attempt 2

- 5G: `131924828 / 131924828 / 131924828` (exact close)
- 6G: `81927301 / 81927301 / 81927045` (`+256`)
- 2.4G: `132049765 / 132049765 / 131682800` (`+366965`)

### Key observation from the earlier isolated replay

- `direct == getSSIDStats()` still exact-closes on all three bands.
- The failure is only on the independent driver oracle.
- The mismatch is no longer a one-band accident:
  - detached full run `20260411T074146043202` failed on 6G
  - isolated rerun `20260411T190338070996` failed on 5G first, then 6G on retry, while 2.4G was already drifting in both attempts

### Post-teardown idle probe

After the isolated rerun fully tore down, a direct DUT probe exact-closed again at idle:

- 5G: `WiFi.SSID.4.Stats.BytesSent = 258133`, `wl0 txbyte = 258133`
- 6G: `181615`, `wl1 txbyte = 181615`
- 2.4G: `173842`, `wl2 txbyte = 173842`

So the parser is not simply broken; the drift is specific to the live sequential band-validation path.

## Source trace

Active 0403 vendor code shows why the current base-interface oracle is incomplete:

- `whm_brcm_api_ext.c:746-812`
  - `whm_brcm_get_if_stats()` seeds `BytesSent` from `wl if_counters txbyte`
- `whm_brcm_vap.c:186-247`
  - `whm_brcm_vap_update_ap_stats()` first copies base-interface stats into `pAP->pSSID->stats`
  - then scans `/proc/net/dev` for matching `wds*` interfaces
  - for each matching peer, `whm_brcm_vap_ap_stats_accu()` adds that interface's `BytesSent` into the public SSID stats

Unlike `BroadcastPacketsSent`, `BytesSent` is **not** restored from `tmp_stats` at the end of this path. So the public `WiFi.SSID.{i}.Stats.BytesSent` field can legitimately be larger than the base `wlX if_counters txbyte` sample whenever extra matching peer stats are merged in.

The active public pWHM layer also shows why sequential equality can still drift even after the WDS sum is added:

- `wld_ssid.c:746-775`
  - `s_updateSsidStatsValues()` refreshes SSID stats by calling `pAP->pFA->mfn_wvap_update_ap_stats(pAP)` and then copying `pSSID->stats` into the output object
- `wld_ssid.c:777-799`
  - `_SSID_getSSIDStats()` calls `s_updateSsidStatsValues()` before serializing the `Stats` object to the htable return
- `wld_ssid.c:801-825`
  - `_wld_ssid_getStats_orf()` also calls `s_updateSsidStatsValues()` before reading the direct `Stats.*` property object

So `WiFi.SSID.{i}.Stats.BytesSent?` and `WiFi.SSID.{i}.getSSIDStats()` are **not** guaranteed to read the same frozen snapshot during one sequential replay: each access refreshes `pSSID->stats` again.

## Superseding official rerun `20260412T005627796136`

The next source-backed trial replaced base `wlX if_counters txbyte` with the active 0403 formula `wlX txbyte + Σ matching wds* txbyte` and re-ran the official runner path:

### Attempt 1

- 5G: `148970905 / 148971033 / 148971377`
- 6G: `97196210 / 97196210 / 97196330`
- 2.4G: `157367729 / 157391543 / 157415359`

### Attempt 2

- 5G: `149022147 / 149022215 / 149022559`
- 6G: `97222418 / 97222418 / 97222418`
- 2.4G: `157517138 / 157517138 / 157517454`

This new rerun materially improved the older blocker shape:

- the earlier large 2.4G gap (`+316040`, `+366965`) collapsed to a small residual `+316` driver lead on attempt 2
- 6G exact-closed completely on attempt 2

But the official runner still did **not** produce a commit-worthy deterministic replay:

- 5G failed on both attempts with a staircase shape `direct < getSSIDStats < driver`
- 2.4G attempt 1 also showed the same staircase shape, and attempt 2 still ended with `driver = direct + 316`

That means the WDS-sum direction is valid, but the sequential runner path still refreshes these counters fast enough that equality is not durable.

## Superseding clean-start rerun `20260412T033924192464`

This rerun was executed after two shared runtime fixes:

1. unresolved placeholder `sta_env_setup` templates are now skipped instead of replayed at runtime
2. the 6G OCV stabilization loop now accepts a restarted `wl1` `hostapd` process even when `/var/run/hostapd/wl1` is still absent during clean start

### What changed

- both attempts reached `evaluate`
- `AssocMac5g` was present on both attempts
- the earlier clean-reset blocker (`assoc_5g.AssocMac5g` missing) did not recur

### Attempt 1

- 5G: `329835 / 329835 / 305843`
- 6G: `271290 / 271290 / 270724`
- 2.4G: `381499 / 381499 / 381341`

### Attempt 2

- 5G: `562142 / 562414 / 537347`
- 6G: `402490 / 402490 / 402332`
- 2.4G: `611651 / 611651 / 611493`

This clean-start rerun supersedes the earlier environment-layer failure:

- the case now fails in `evaluate`, not `verify_env`
- the dominant residual mismatch is still 5G `BytesSent`
- attempt 2 also re-proves that direct `Stats.*` and `getSSIDStats()` can diverge by themselves (`562142` vs `562414`) before the later driver readback

## Why YAML is not updated yet

The currently committed D324 oracle assumes base `wlX if_counters txbyte` is always the final authoritative driver view. The latest live reruns no longer support that assumption.

However, the next source-backed hypothesis has now also been exercised and rejected for commit:

- `wlX txbyte + Σ matching wds* txbyte` is directionally correct
- but the official runner still sees separate refreshes for direct `Stats.*`, `getSSIDStats()`, and the later driver readback
- so the full three-way equality still drifts during the same sequential replay

## Resolution

Official rerun `20260412T060612008433` resolved the remaining runner-path drift by keeping the same source-backed WDS-sum authority, but changing the per-band command ordering into one raw-first snapshot:

1. sample raw `wl if_counters txbyte + matching wds txbyte` first
2. capture one `getSSIDStats()` snapshot
3. read the direct `Stats.BytesSent?` getter in the same shell step
4. evaluate all three values from that same replay window

That rerun exact-closed the full runner path on attempt 1:

- 5G: `direct / getSSIDStats / formula = 1141986 / 1141986 / 1141986`
- 6G: `1113827 / 1113827 / 1113827`
- 2.4G: `1186105 / 1186105 / 1186105`

So the earlier staircase (`direct < getSSIDStats < driver`) was not an authority mismatch in `wlX txbyte + Σ matching wds* txbyte` itself; it was sequential refresh noise caused by reading direct `Stats.*`, `getSSIDStats()`, and the driver formula in separate shell steps.

## Current decision

`D324` is now **aligned**.

- keep the committed YAML on the raw-first single-snapshot source-backed formula
- keep workbook row metadata at `324`
- keep `results_reference.v4.0.3` at `Pass / Pass / Pass`
- retain this file only as historical trial and resolution evidence

## Next direction

1. Move the next open-set revisit to `D295`.
2. Keep `D281` / `D282` / `D295` as the remaining open blockers until each one has a deterministic source-backed official rerun.
