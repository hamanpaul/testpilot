# D204 Radio.MultiUserMIMOEnabled parked note

## Summary

- case: `D204 Radio.MultiUserMIMOEnabled`
- latest official rerun: `20260414T165000634858`
- current live getter shape: `5g=1`, `6g=1`, `2.4g=0`
- compare status: still open against workbook row `204` `Pass / Pass / Pass`
- disposition: **parked for workbook/source authority clarification**

## Why this is parked

The latest official rerun exact-closes the same tri-band getter shape that already appears in historical authoritative traces:

- `20260414T165000634858` → `1 / 1 / 0`
- `20260412T113008433351` → `1 / 1 / 0`
- `20260409T213837737224` → `1 / 1 / 0`

Workbook row `204` still marks `R/S/T = Pass / Pass / Pass`, but note `V204` says:

> `2.4GHz mu features are disable by default "need clarification why it is disabled by default because 5G and 6G are enabled."`

That note matches the repeated live getter shape more closely than the answer cells. The workbook `H204` driver snippet is also suspicious because it repeats `wl -i wl1 mu_features` twice instead of clearly showing the 2.4G radio command.

Because the workbook answer cells and workbook note point in different directions, the case should not be rewritten to workbook-pass semantics until that authority conflict is resolved.

## Evidence

### Official rerun `20260414T165000634858`

```text
WiFi.Radio.1.MultiUserMIMOEnabled=1
WiFi.Radio.2.MultiUserMIMOEnabled=1
WiFi.Radio.3.MultiUserMIMOEnabled=0
```

Files:

- `plugins/wifi_llapi/reports/20260414T165000634858_DUT.log`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t165000634858.md`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t165000634858.json`

### Historical authoritative full-run trace

`plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d204-radio-multiusermimoenabled.json`

```text
WiFi.Radio.1.MultiUserMIMOEnabled=1
WiFi.Radio.2.MultiUserMIMOEnabled=1
WiFi.Radio.3.MultiUserMIMOEnabled=0
```

## Next action

Skip `D204` for now and continue with the next ready non-blocked compare-open case:

- `D205 Radio.MultiUserMIMOSupported`
