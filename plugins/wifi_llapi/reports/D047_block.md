# D047 SupportedHe160MCS blocker

## Status

- case: `D047 SupportedHe160MCS`
- workbook row: `47`
- current state: **blocked as workbook/source authority conflict**
- next ready actionable compare-open case: `D050 SupportedVhtMCS`

## Why this is blocked

`compare-0401` is correctly treating workbook row `47` as open because the loader reads answer columns `R/S/T` (`src/testpilot/reporting/wifi_llapi_compare_0401.py:135-149`), and row `47` currently resolves to `Pass / Pass / Not Supported`.

However, the same workbook row also contains conflicting evidence that matches the live 0403 runtime:

- legacy workbook columns `I/J/K` read `Not Support / Not Support / Not Support`
- workbook note `V47` explicitly says pWHM does **not** support standalone `SupportedHe160MCS` and only defines:
  - `RxSupportedHe160MCS`
  - `TxSupportedHe160MCS`
  - `RxSupportedHeMCS`
  - `TxSupportedHeMCS`

That row-level note matches the current 0403 source/runtime split for `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.`.

## Workbook evidence

- `0401.xlsx` row `47`
  - object/api: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `SupportedHe160MCS`
  - workbook command seed (`D47`): `ubus-cli WiFi.AccessPoint.{i}.AssociatedDevice.{i}.SupportedHe160MCS=`
  - answer columns `R/S/T`: `Pass / Pass / Not Supported`
  - legacy columns `I/J/K`: `Not Support / Not Support / Not Support`
  - note `V47`: standalone `SupportedHe160MCS` is not supported by pWHM; only Rx/Tx sibling fields exist

## 0403 source/runtime evidence

### Installed ODL split

- `targets/BGW720-300/fs.install/etc/amx/wld/wld_accesspoint.odl:L1605-L1616`
  - `AssociatedDevice` exposes only:
    - `RxSupportedHe160MCS`
    - `TxSupportedHe160MCS`
- `targets/BGW720-300/fs.install/etc/amx/wld/wld_endpoint.odl:L371-L377`
  - standalone `SupportedHe160MCS` exists under the endpoint model, not the access-point associated-device model

### Official rerun evidence

- official rerun: `20260412T235952361188`
- DUT log: `plugins/wifi_llapi/reports/20260412T235952361188_DUT.log:L84-L109`
  - `SupportedHe160MCS?` returns `error=4` / `message=parameter not found`
  - same `AssociatedDevice.1` entry still exposes:
    - `DriverRxSupportedHe160MCS=11,11,11,11`
    - `DriverTxSupportedHe160MCS=11,11,11,11`
- DUT log: `plugins/wifi_llapi/reports/20260412T235952361188_DUT.log:L62-L70`
  - same station MAC resolves as `2C:59:17:00:04:85`
- STA log: `plugins/wifi_llapi/reports/20260412T235952361188_STA.log:L82-L99`
  - STA is stably connected to `testpilot5G`
- trace JSON: `plugins/wifi_llapi/reports/agent_trace/20260412T235952361188/wifi-llapi-D047-supportedhe160mcs.json`
  - `evaluation_verdict=Pass`
  - live case logic exact-closes the not-supported getter plus sibling-field evidence

## Why the YAML is not being rewritten

The current YAML is source/runtime-correct for `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.SupportedHe160MCS`: the standalone field is not exposed on the AssociatedDevice object in current 0403, while the sibling Rx/Tx fields are.

Rewriting `results_reference` back to workbook `Pass / Pass / Not Supported` would invent support for an AssociatedDevice field that current 0403 does not expose and that the rerun explicitly reports as `parameter not found`.

## Required follow-up

Before D047 can be closed, one of these authority questions must be resolved:

1. confirm workbook row `47` answer columns `R/S/T` are wrong and should be corrected to the row note / source/runtime shape, or
2. confirm the row should have targeted a different object family (for example endpoint rather than access-point associated-device), then remap the case accordingly.

Until that authority conflict is resolved, keep D047 in the blocker bucket and do not rewrite the current YAML to workbook-pass semantics.
