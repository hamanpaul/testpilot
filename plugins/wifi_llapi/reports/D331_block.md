# D331 MulticastPacketsSent blocker

## Scope

- Case: `wifi-llapi-d331-multicastpacketssent`
- Workbook row authority: `D331` / workbook row `331`
- Current YAML metadata remains reverted to stale workbook-style row `255`
- Latest formula trial reruns:
  - `20260411T192138186700`
  - `20260411T192524301950`
  - `20260411T234124237416` (superseding official rerun)
  - `20260412T003609854183` (post-`verify_env` settle retrial)

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

### Superseding official rerun — same formula still fails in the real runner path

Official rerun `20260411T234124237416` retried the same source-backed formula after the temporary YAML rewrite, but the failure shape became even less durable:

- attempt 1
  - 5G: `direct / getSSIDStats / formula = 286001 / 286001 / 286006`
  - 6G: `177024 / 177024 / 177063`
  - 2.4G: `302809 / 302809 / 302810`
- attempt 2
  - 5G: `286140 / 286140 / 286192`
  - 6G: `177132 / 177132 / 177132`
  - 2.4G: `302912 / 302912 / 302912`

This supersedes the earlier fixed-`+4` reading: in the real runner path the 5G delta is now non-deterministic (`+5`, then `+52`), 6G only exact-closes on the second attempt, and 2.4G still showed a `+1` first-attempt drift before exact-closing.

### Trial 3 — post-`verify_env` settle still leaves a 6G delta

Official rerun `20260412T003609854183` retried the same source-backed formula again, but inserted the same short settle (`sleep 2`) that resolved `D322`:

- attempt 1
  - 5G: `direct / getSSIDStats / formula = 291686 / 291686 / 291686`
  - 6G: `181336 / 181336 / 181337`
  - 2.4G: `307396 / 307396 / 307396`
- attempt 2
  - 5G: `291887 / 291887 / 291887`
  - 6G: `181375 / 181375 / 181377`
  - 2.4G: `307560 / 307560 / 307560`

This trial materially narrowed the runner drift shape:

- 5G exact-closed on both attempts
- 2.4G exact-closed on both attempts
- but 6G still stayed above the public field by `+1`, then `+2`

So the short settle helps, but it does **not** close the real runner path deterministically the way it did for `D322`.

Focused DUT-only probes still exact-close the same formula outside the full runner path, including repeated delayed replays (`Direct / Get / Driver = 123422 / 123422 / 123422` across five loops), so the acceptance authority must remain the official runner rather than the isolated probe.

## Why YAML is not updated yet

The source-backed formula is directionally correct and much closer than the stale workbook `/proc $18` compare, but it still is not exact or deterministic on the real runner path:

- the first two trial reruns kept the same fixed `+4` 5G delta
- the superseding official rerun widened the 5G drift to `+5`, then `+52`
- the post-`verify_env` settle retrial removed the 5G/2.4G drift, but 6G still failed at `181336 / 181336 / 181337` and `181375 / 181375 / 181377`

So there is still no live-validated reason to commit the formula rewrite into the official YAML.

## Current decision

`D331` remains **blocked**.

- keep the committed YAML on its pre-trial state
- do not promote the source-backed formula to a committed pass oracle yet
- carry the case forward as part of the patch-scope open set

## Next direction

1. Trace why the full runner path can still inflate the 6G source-backed formula after the 6G OCV/hostapd stabilization sequence, even when the same settle fixed 5G/2.4G.
2. Check whether the public field is sampling a post-merge/public snapshot that lags the raw TX-side subtraction formula specifically on the 6G retry path.
3. Keep `D331` blocked for now and move on to `D333`; only reopen if a deterministic runner-stable 6G correction can be proven.
