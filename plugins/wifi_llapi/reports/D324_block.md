# D324 BytesSent blocker

## Scope

- Case: `wifi-llapi-d324-bytessent`
- Workbook row authority: `D324` / workbook row `324`
- Current YAML metadata: `source.row: 324`
- Historical aligned rerun: `20260411T010328768651`
- Latest failed full-run evidence: `20260411T074146043202`
- Latest failed isolated rerun: `20260411T190338070996`
- Latest failed official WDS-sum rerun: `20260412T005627796136`

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

## Why YAML is not updated yet

The currently committed D324 oracle assumes base `wlX if_counters txbyte` is always the final authoritative driver view. The latest live reruns no longer support that assumption.

However, the next source-backed hypothesis has now also been exercised and rejected for commit:

- `wlX txbyte + Σ matching wds* txbyte` is directionally correct
- but the official runner still sees separate refreshes for direct `Stats.*`, `getSSIDStats()`, and the later driver readback
- so the full three-way equality still drifts during the same sequential replay

## Current decision

`D324` remains **blocked**.

- Do **not** keep claiming `wlX if_counters txbyte` is a durable all-band oracle
- Do **not** treat the earlier exact-close rerun as sufficient green-lock anymore
- Do **not** refresh the YAML to the WDS-sum rewrite yet; the official runner still shows non-durable sequential refresh drift

## Next direction

1. If D324 is revisited again, capture lower-level per-read evidence around the sequential refresh path to determine whether `Stats.*` and `getSSIDStats()` can ever be made to share one durable snapshot in the official runner.
2. Do **not** commit any further timing-only workaround unless it exact-closes all three bands in the official runner path.
3. Keep `D324` blocked for now and continue with the remaining non-direct open set, starting from `D281`.
