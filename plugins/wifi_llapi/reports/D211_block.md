# D211 Radio.OperatingStandards parked note

## Summary

- case: `D211 Radio.OperatingStandards`
- latest getter rerun: `20260414T172208746324`
- current getter-only live shape: `5g=be`, `6g=be`, `2.4g=be`
- compare status: still open against workbook row `211` `Pass / Pass / Pass`
- disposition: **parked until workbook step 3 / step 6 beacon evidence is re-validated**

## Why this is parked

The current committed YAML is only a getter replay:

```sh
ubus-cli "WiFi.Radio.1.OperatingStandards?"
ubus-cli "WiFi.Radio.2.OperatingStandards?"
ubus-cli "WiFi.Radio.3.OperatingStandards?"
```

That is not workbook-faithful. Workbook row `211` requires a full mode-switch procedure:

1. set all radios to `be`
2. verify getter reads back `be`
3. capture air beacon and confirm **EHT IE is present**
4. set all radios to `ax`
5. verify getter reads back `ax`
6. capture air beacon and confirm **EHT IE is absent while HE IE remains present**
7. switch each radio back according to `SupportedStandards`

The latest getter rerun exact-closes only step 2:

```text
WiFi.Radio.1.OperatingStandards="be"
WiFi.Radio.2.OperatingStandards="be"
WiFi.Radio.3.OperatingStandards="be"
```

Earlier repo handoff already recorded the unresolved blocker shape for the missing workbook-faithful steps:

> `0315/0403 行為沒變：getter 可切 be -> ax，但 runtime beacon / EHT 仍維持 enabled，無法達成 workbook step 6`

So this case should not be rewritten to workbook-pass semantics until the full `be -> ax` beacon validation path is re-proven on the current lab state.

## Evidence

### Getter rerun `20260414T172208746324`

Files:

- `plugins/wifi_llapi/reports/20260414T172208746324_DUT.log`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t172208746324.md`
- `plugins/wifi_llapi/reports/bgw720-0403_wifi_llapi_20260414t172208746324.json`

Observed getter output:

```text
WiFi.Radio.1.OperatingStandards="be"
WiFi.Radio.2.OperatingStandards="be"
WiFi.Radio.3.OperatingStandards="be"
```

### Workbook authority

Workbook row `211` (`0401.xlsx`, `Wifi_LLAPI`):

- `G211` explicitly requires `be -> ax` switching plus beacon capture
- `R/S/T = Pass / Pass / Pass`
- `V211` notes prior verification history and BRCM fix tracking

## Next action

Skip `D211` for now and continue with the next ready non-blocked compare-open case:

- `D212 Radio.PossibleChannels`
