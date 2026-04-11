# D295 scan() resolution notes

## Scope

- Case: `d295-scan`
- Workbook row authority: `D295` / workbook row `295`
- Current YAML metadata: `source.row: 295`
- Latest baseline-free probe: 2026-04-11 manual serialwrap on `COM1`
- Latest isolated reruns:
  - `20260411T183430680092` (committed YAML, DUT-only topology)
  - `20260411T185559873987` (local experimental topology patch with `STA` + three band links; not committed)
  - `20260412T063939977577` (official rerun proving first-driver-BSSID equality is not durable)
  - `20260412T064317622551` (resolving official rerun, current authority)

## Workbook-style procedure replay

The current workbook-aligned YAML keeps the procedure minimal:

1. `ubus-cli "WiFi.Radio.1.scan()"`
2. `ubus-cli "WiFi.Radio.2.scan()"`
3. `ubus-cli "WiFi.Radio.3.scan()"`
4. Pass criterion: output must not contain `error`

## Live evidence

### 1. Baseline-free probe on current committed topology

Direct serialwrap probes on the DUT (`COM1`) showed the radios are not left in a scan-ready state once the case runs without a `STA` transport:

```text
> ubus-cli "WiFi.Radio.1.Status?"
WiFi.Radio.1.Status="Dormant"

> ubus-cli "WiFi.Radio.2.Status?"
WiFi.Radio.2.Status="Dormant"

> ubus-cli "WiFi.Radio.3.Status?"
WiFi.Radio.3.Status="Dormant"
```

Under that state, the method itself does not cleanly satisfy the workbook no-error criterion:

```text
> ubus-cli "WiFi.Radio.2.scan()"
ERROR: call (null) failed with status 1 - unknown error
WiFi.Radio.2.scan() returned
[
    ""
]
```

The adjacent `startScan()` path currently shows the same environment-shaped failure in this dormant state:

```text
> ubus-cli "WiFi.Radio.2.startScan()"
ERROR: call (null) failed with status 1 - unknown error
WiFi.Radio.2.startScan() returned
[
    ""
]
```

### 2. Latest committed-YAML isolated rerun

`20260411T183430680092` no longer produced a usable per-case trace:

- runner log stopped after `setup_env: d295-scan connected=True devices=['DUT']`
- `plugins/wifi_llapi/reports/agent_trace/20260411T183430680092/` exists but is empty
- only the top-level workbook-style xlsx was emitted; no per-case JSON survived

### 3. Experimental topology patch rerun (not committed)

To test whether the missing `STA` transport was the sole root cause, the case was locally patched to add:

- `STA: COM0`
- links for `5g`, `6g`, `2.4g`

That rerun (`20260411T185559873987`) moved farther than the committed version:

```text
setup_env: d295-scan connected=True devices=['DUT', 'STA']
verify_env: d295-scan BSS already up, re-applying deterministic DUT baseline
verify_env: d295-scan 6G restart attempt=1 unstable (ocv=False socket=False bss=False), retrying
verify_env: d295-scan 6G restart attempt=2 unstable (ocv=True socket=False bss=True), retrying
verify_env: d295-scan 6G restart attempt=3 unstable (ocv=True socket=False bss=True), retrying
verify_env: d295-scan 6G ocv=0 fix applied, wl1 hostapd restarted
verify_env: d295-scan BSS already up, re-applying deterministic DUT baseline
```

But it still failed to reach any `step_5g/step_6g/step_24g` output:

- the run stalled after the second `verify_env` cycle
- `plugins/wifi_llapi/reports/agent_trace/20260411T185559873987/` is also empty
- no xlsx/json case artifact was emitted for this rerun
- the local topology patch was therefore reverted instead of being committed

## Source / runtime trace

The current runtime behavior matches the plugin lifecycle:

- `plugin.py:1563-1568` — `_should_auto_prepare_wifi_bands()` only returns true when a `STA` transport exists
- `plugin.py:2770-2789` — `verify_env()` only runs `_prepare_case_band()` when `STA` is present
- `baseline_qualifier.py:220-222` — `qualify_baseline()` always calls `plugin.teardown(...)` in `finally`, so a successful baseline qualification does **not** leave the radios permanently prepared for a later DUT-only case

So the committed D295 YAML currently has no source-backed guarantee that `scan()` will execute after the radios fall back to `Dormant`.

## Why earlier rewrites were rejected

We now know two things:

1. The committed DUT-only topology is not deterministic: the radios can be `Dormant`, and `scan()` then returns `ERROR ... unknown error`.
2. Simply adding `STA` + band links is also not yet sufficient: it pushes the failure deeper into the 6G verify/OCV stabilization path, but still does not produce a clean step-level replay.

That means there is still no live-validated, source-backed path that lets us promote D295 back into a confidently aligned plain-pass row.

## Resolution

Official rerun `20260412T064317622551` now provides a durable source-backed pass path:

1. Keep `STA + links` topology so `_should_auto_prepare_wifi_bands()` and per-band `verify_env()` actually run before each band.
2. Reject the earlier stricter `first scan BSSID == first driver BSSID` oracle. Official rerun `20260412T063939977577` showed that ordering is not durable: the 5G `scan()` first BSSID stayed fixed at `62:15:db:9e:31:f1`, while the first `wl0 escanresults` BSSID drifted across retries (`ca:45:e8:2a:49:0e` then `a8:a2:37:6b:e7:ec`).
3. Use the stable driver-backed oracle instead: `scan()` first BSSID must exist somewhere in same-band `wl escanresults`.

The resolving official rerun exact-closed all three bands:

- 5G `62:15:db:9e:31:f1`
- 6G `86:82:fe:58:ac:a6`
- 2.4G `6a:d7:aa:02:d7:bf`

## Current decision

`D295` is now aligned as **Pass / Pass / Pass**.

- Keep the authored `STA` topology + three band links
- Keep the committed oracle on `scan() first BSSID exists in same-band wl escanresults`
- Retain this file as historical blocker/resolution evidence

## Next direction

1. Continue with `D281` and `D282`, which are now the remaining open-set blockers.
2. Treat the rejected `first-driver-BSSID` equality trial as ordering-noise evidence, not as the final D295 oracle.
3. Keep adjacent `D298 startScan()` / `D299 stopScan()` notes as historical context only; D295 no longer blocks on their dormant-radio failure shape.
