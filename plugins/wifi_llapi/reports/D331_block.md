# D331 MulticastPacketsSent resolution notes

## Scope

- Case: `wifi-llapi-d331-multicastpacketssent`
- Workbook row authority: `D331` / workbook row `331`
- Current YAML metadata is now refreshed from stale workbook-style row `255` to workbook row `331`
- Latest formula trial reruns:
  - `20260411T192138186700`
  - `20260411T192524301950`
  - `20260411T234124237416` (superseding official rerun)
  - `20260412T003609854183` (post-`verify_env` settle retrial)
  - `20260412T040941971904` (resolving clean-start official rerun)

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

## Resolution

Clean-start official rerun `20260412T040941971904` resolved the remaining runner-path drift by changing the per-band command ordering inside the real acceptance path:

1. sample raw `wl if_counters txmulti + matching wds txmulti` first
2. capture one `getSSIDStats()` snapshot and parse both `MulticastPacketsSent` and `BroadcastPacketsSent`
3. read the direct getter in the same shell step
4. evaluate `max((txmulti + matching wds txmulti) - BroadcastPacketsSent, 0)` against that same public snapshot

That run exact-closed the full runner path on attempt 1:

- 5G: `direct / getSSIDStats / formula = 904 / 904 / 904`
- 6G: `732 / 732 / 732`
- 2.4G: `973 / 973 / 973`

So the earlier `+4`, `+5`, `+52`, then `+1/+2` drifts were not an authority mismatch in the formula itself; they were still command-order noise inside the runner path. The committed YAML now keeps the source-backed formula, but captures it as a raw-first single snapshot per band.

An immediate back-to-back rerun was started afterward, but it stayed in repeated 6G `verify_env` OCV repair loops without reaching `evaluate`; that reused-environment attempt was discarded as non-authoritative for this case and is kept only as baseline-noise context.

## Current decision

`D331` is now **aligned**.

- keep the committed YAML on the raw-first single-snapshot source-backed formula
- keep workbook row metadata at `331`
- keep `results_reference.v4.0.3` at `Pass / Pass / Pass`
- retain this file only as historical trial and resolution evidence

## Next direction

1. Move the next open-set direct-stats revisit to `D333`.
2. Keep immediate reused-environment rerun noise separate from accepted per-case authority; when reopening adjacent stats cases, prefer clean-start official reruns over back-to-back retries if 6G `verify_env` starts looping before `evaluate`.
