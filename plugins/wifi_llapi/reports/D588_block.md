# D588 SSID MLDUnit block

- workbook row: `588`
- current committed YAML row: `591` (no rewrite landed; committed case remains unchanged)
- compare overlay: `compare-0401.md` still maps `d588-ssid-mldunit` to workbook `Pass / Pass / Pass`
- disposition: **blocked by current getter / driver authority mismatch under the current DUT firmware**

## Focused live survey

The current live replay does **not** reproduce workbook `G588/H588`:

```text
5G   WiFi.SSID.4.MLDUnit=-1
6G   WiFi.SSID.6.MLDUnit=-1
2.4G WiFi.SSID.8.MLDUnit=-1
```

The obvious driver candidates from workbook `H588` are also unavailable on the current DUT:

```text
wl -i wl0 mld_unit 0  -> wl: Unsupported
wl -i wl1 mld_unit 0  -> wl: Unsupported
wl -i wl2 mld_unit 0  -> wl: Unsupported

wl -i wl0 mld_unit    -> wl: Unsupported
wl -i wl1 mld_unit    -> wl: Unsupported
wl -i wl2 mld_unit    -> wl: Unsupported
```

And the live hostapd configs do not expose a fallback `mld_unit=` readback:

```text
grep -nE '^mld_unit=' /tmp/wl0_hapd.conf /tmp/wl1_hapd.conf /tmp/wl2_hapd.conf
# no output
```

## Why this is blocked

- workbook `G588/H588` expects `MLDUnit=0` with `wl -i wlX mld_unit 0` evidence
- under the current DUT firmware, the public getter still returns `-1` on all three bands
- the `wl mld_unit` driver command is unsupported, and the current hostapd configs do not expose `mld_unit=` as a fallback oracle
- promoting `D588` to workbook `Pass / Pass / Pass` would therefore require inventing an unsupported oracle or ignoring the live getter mismatch

Both are disallowed, so the case stays blocked.

## Evidence

### Focused serialwrap survey (2026-04-15)

Commands used:

```sh
ubus-cli "WiFi.SSID.4.MLDUnit?"
ubus-cli "WiFi.SSID.6.MLDUnit?"
ubus-cli "WiFi.SSID.8.MLDUnit?"

wl -i wl0 mld_unit 0
wl -i wl1 mld_unit 0
wl -i wl2 mld_unit 0

wl -i wl0 mld_unit
wl -i wl1 mld_unit
wl -i wl2 mld_unit

grep -nE "^mld_unit=" /tmp/wl0_hapd.conf /tmp/wl1_hapd.conf /tmp/wl2_hapd.conf 2>/dev/null || true
```

Observed output:

```text
WiFi.SSID.4.MLDUnit=-1
WiFi.SSID.6.MLDUnit=-1
WiFi.SSID.8.MLDUnit=-1

wl: Unsupported
wl: Unsupported
wl: Unsupported

wl: Unsupported
wl: Unsupported
wl: Unsupported

# no mld_unit lines in /tmp/wl*_hapd.conf
```

## Current disposition

- `D588` remains **blocked**
- committed YAML and runtime metadata stay unchanged (`row 591`, `Fail / Fail / Fail`)
- next ready compare-open case: `D600 WiFi7STARole.NSTRSupport`
