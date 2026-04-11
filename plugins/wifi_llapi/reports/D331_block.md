# D331 MulticastPacketsSent blocker

## Scope

- Case: `wifi-llapi-d331-multicastpacketssent`
- Workbook row authority: `D331` / workbook row `331`
- Current YAML metadata remains reverted to stale workbook-style row `255`
- Latest formula trial reruns:
  - `20260411T192138186700`
  - `20260411T192524301950`

## Workbook-style procedure replay

The committed workbook-era case still compares:

1. `WiFi.SSID.{i}.Stats.MulticastPacketsSent?`
2. `WiFi.SSID.{i}.getSSIDStats()`
3. `/proc/net/dev_extstats` field `$18`

That legacy `/proc $18` oracle is already known to be stale from the adjacent `D310 getSSIDStats() MulticastPacketsSent` source-backed closure, so a source-backed rewrite was trialed but not committed.

## Source-backed trial and live evidence

Active 0403 source for the SSID stats path still matches the already-closed `D310` family:

- `whm_brcm_get_if_stats()` seeds `MulticastPacketsSent` from `wl if_counters txmulti`
- `whm_brcm_vap_ap_stats_accu()` can add matching `wds*` peer counters
- `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsSent` and clamps at zero

So the trial rewrite used:

- `max((wl if_counters txmulti + matching wds txmulti) - BroadcastPacketsSent, 0)`

### Trial 1 — direct `BroadcastPacketsSent?` as subtraction term

Run `20260411T192138186700`:

- attempt 1
  - 5G: `direct / getSSIDStats / formula = 259962 / 259962 / 259966`
  - 6G: `156472 / 156472 / 156510`
  - 2.4G: `281272 / 281272 / 281272`
- attempt 2
  - 5G: `260097 / 260097 / 260101`
  - 6G: `156538 / 156538 / 156538`
  - 2.4G: `281420 / 281420 / 281420`

This proved the old `/proc $18` heuristic is not the right path, but the 5G formula still stayed `+4` above the public field on both attempts.

### Trial 2 — same `getSSIDStats()` snapshot `BroadcastPacketsSent`

Run `20260411T192524301950` retried the same formula, but changed the subtraction term to come from a fresh `getSSIDStats()` snapshot within the driver-formula step itself.

- attempt 1
  - 5G: `260377 / 260377 / 260381`
  - 6G: `156472 / 156472 / 156510`
  - 2.4G: `281272 / 281272 / 281272`
- attempt 2
  - 5G: `260613 / 260613 / 260617`
  - 6G: `156538 / 156538 / 156538`
  - 2.4G: `281420 / 281420 / 281420`

The 5G `+4` drift remained unchanged, so the mismatch is not explained only by using a separately sampled direct `BroadcastPacketsSent?`.

## Why YAML is not updated yet

The source-backed formula is directionally correct and much closer than the stale workbook `/proc $18` compare, but it still is not exact or deterministic on 5G:

- both trial reruns kept the same `+4` 5G delta
- 6G exact-closed only after the second attempt
- 2.4G exact-closed, but that is not enough to claim a durable three-band oracle

So there is still no live-validated reason to commit the formula rewrite into the official YAML.

## Current decision

`D331` remains **blocked**.

- keep the committed YAML on its pre-trial state
- do not promote the source-backed formula to a committed pass oracle yet
- carry the case forward as part of the patch-scope open set

## Next direction

1. Trace where the persistent 5G `+4` comes from in the TX-side merge path after `tmp_stats.BroadcastPacketsSent` is restored/subtracted.
2. Check whether the public field is shaving off a small fixed header/control contribution that raw `txmulti` still keeps.
3. If a deterministic correction term or tighter authoritative source can be proven, rerun the direct-property case; otherwise keep D331 blocked and move on to `D332` / `D333`.
