# D035 blocker — AssociatedDevice OperatingStandard

## Summary

- Case: `D035` / workbook row `35`
- API: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.OperatingStandard`
- Workbook intent: `Pass / Pass / Pass`
- Current status: **blocked**
- Compare snapshot impact: unchanged at `247 / 420 full matches`、`173 mismatches`、`58 metadata drifts`

## Why this is blocked

`D035` is not a pure stale-metadata closure like `D461` / `D462` / `D463` / `D465` / `D467`.

The authoritative full-run trace already used workbook row `35`, so the repo needs a real tri-band case rewrite before it can be closed. A local trial rewrite was prepared, but it did **not** converge under live runtime validation:

1. Official rerun `20260413T014428270219` failed twice at `step1_5g_sta_join`.
2. The machine-readable trace records `reason_code=step_command_failed`, command `iw dev wl0 link`, output `Not connected.` on both attempts.
3. But the same STA verify-env log still showed `wl0` had already completed a valid 5G join (`SSID: testpilot5G`, `wpa_state=COMPLETED`), which means the failure was not a simple missing baseline setup.
4. A second trial rerun `20260413T015210910141` added an explicit `select_network + sleep` reconnect before each `*_sta_join` step. That removed the immediate 5G join failure, but the run then fell into a repeated 6G recovery loop and never reached a stable final verdict:
   - `verify_env: ... 6G restart attempt=1 unstable`
   - `verify_env: ... 6G ocv=0 fix applied, wl1 hostapd restarted`
   - `env: retry command after recovery_action=ATTACH`
   - `verify_env: ... 6G ocv=0 verify failed — BSS loop may persist`

Because the tri-band rewrite is still gated by shared 6G runtime instability, it was reverted locally and **not committed**.

## Evidence

### Prior failed official rerun

- Run id: `20260413T014428270219`
- Trace: `plugins/wifi_llapi/reports/agent_trace/20260413T014428270219/d035-assocdev-operatingstandard.json`
- Final status: `Fail`
- Failure point: `step1_5g_sta_join`

Key trace excerpt:

```json
"comment": "step1_5g_sta_join command failed",
"reason_code": "step_command_failed",
"device": "sta",
"band": "5g",
"command": "iw dev wl0 link",
"output": "Not connected."
```

### STA evidence from the same rerun

File: `plugins/wifi_llapi/reports/20260413T014428270219_STA.log`

```text
L505-L534
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: testpilot5G
...
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
bssid=2c:59:17:00:19:95
ssid=testpilot5G
key_mgmt=WPA2-PSK
wpa_state=COMPLETED
```

### DUT evidence from the same rerun

File: `plugins/wifi_llapi/reports/20260413T014428270219_DUT.log`

```text
L694-L700
wl -i wl1 bss
up
ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"
WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:04:86"

L747-L758
ubus-cli WiFi.AccessPoint.5.Enable=1
WiFi.AccessPoint.5.Enable=1
sleep 5
--wl2 FSM DONE--
wl -i wl2 bss
up
```

### Reconnect trial transcript

- Trial rerun id: `20260413T015210910141`
- Result: aborted after repeated runtime recovery loop; no final report artifact was kept because the runner was stopped once it was clearly stuck in env recovery.

Observed runner transcript:

```text
verify_env: d035-assocdev-operatingstandard 6G restart attempt=1 unstable
verify_env: d035-assocdev-operatingstandard 6G ocv=0 fix applied, wl1 hostapd restarted
env: retry command after recovery_action=ATTACH attempt=1 cmd=grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1
env: retry command after recovery_action=ATTACH attempt=2 cmd=grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1
verify_env: d035-assocdev-operatingstandard 6G ocv=0 verify failed — BSS loop may persist
```

## Commands tried

### Workbook-style / trial STA checks

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

### Reconnect trial

```sh
wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0
sleep 5
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

### DUT-side visibility checks

```sh
wl -i wl1 bss
ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"
ubus-cli WiFi.AccessPoint.5.Enable=1
wl -i wl2 bss
```

## Decision

- Do **not** commit the local tri-band rewrite for `D035`
- Do **not** refresh `source.row`, `bands`, or `results_reference` yet
- Keep compare/handoff at the current pushed snapshot through `D467`
- Track `D035` as a runtime/env blocker until the shared 6G OCV / ATTACH recovery loop is stabilized

## Next ready case

- Next low-risk workbook-Pass revisit: `D045`
