# Wifi_LLAPI Workbook Calibration Audit Todo

> Audit checklist for workbook-driven LLAPI calibration.
>
> `docs/todos.md` remains the project-wide board. This file expands the calibration work into a checkable execution list for review and evidence tracking.
>
> Any session SQL tracking is internal assistant scratchpad only. User-facing review artifacts for this work are this file and the final audit report.

## Calibration authority

- Acceptance baseline: repo-root `0401.xlsx` `Wifi_LLAPI` sheet, answer columns `R/S/T`.
- Compare rule: normalize both sides so only literal `Pass` stays `Pass`; all other workbook/run values become `Fail`.
- Additional interpretation source: workbook columns `G/H` (`Test Steps` / `Command Output`).
- Manual procedure seed: workbook `G/H`; use source survey only after workbook/live evidence still disagree.
- Live validation path: direct serialwrap operation on `COM0/COM1`.
- Explicitly not used as correctness evidence: run1 result and any existing YAML pass/fail condition that conflicts with the workbook baseline.
- YAML writeback gate: only update YAML after the live serialwrap result matches the workbook baseline.
- Read-only verification rule:
  - if the target LLAPI is read-only, do not treat a direct set command as a valid test
  - first find the writable LLAPI or external command that actually drives the read-only value
  - then verify the read-only readback matches the value or state change caused by that writable control
- Refresh / trigger rule:
  - some read paths are only populated after a precursor action such as a stats refresh call
  - example pattern: read `AssociatedDevice.*.UplinkRateSpec?` only after the required trigger such as `ubus call WiFi.AccessPoint.1 getStationStats {}`
  - identifying these prerequisite trigger steps is part of calibration, and the trigger must be written into YAML when it is required for a valid readback
- Side-effect rule:
  - for setter or method cases, LLAPI/ubus readback alone is not enough
  - pass requires verification of the actual behavior or downstream state change caused by the operation
- Counter validation rule:
  - for counter / statistics / beacon-related cases, if the current lab cannot generate the relevant packet or beacon condition, focus on numeric cross-check and readback consistency
  - record this limitation explicitly in the final audit report instead of inventing unsupported traffic generation steps
- Blocker rule:
  - external-environment failures may be recorded as blockers when the root cause is outside the LLAPI/YAML logic itself
  - examples: STA disconnected, unusable RSSI, missing traffic source, missing Radius, topology mismatch
- Workbook `To be tested` / `Not Supported` rule:
  - if the workbook marks a row as `To be tested` or `Not Support` / `Not Supported`, do not rewrite that case into pass-style criteria
  - when the live evidence is clear and the user wants workbook alignment, the YAML may still be updated, but it must preserve the workbook non-pass semantics explicitly (`To be tested` / `Not Supported`) instead of pretending the case passed
- DUT / STA identity rule:
  - do not rely on the old A0/B0 heuristic to distinguish DUT and STA behavior
  - the STA board has changed and the STA 2.4G / 5G / 6G connectivity to DUT APs must be re-mapped from live evidence first
  - once the rebuilt mapping and working environment settings are verified, sync them back into the YAML environment setup instead of leaving them only in notes
- YAML sync scope rule:
  - sync shared, verified environment settings back into the baseline first
  - only sync case-specific settings into an individual case YAML when that case truly needs unique environment settings such as a different security mode
- Default non-open baseline rule:
  - unless a case explicitly requires another security mode, do not use open-security SSIDs
  - default baseline naming / credential is `testpilot5G` / `testpilot6G` / `testpilot2G` with password `00000000`
  - current verified default security policy is:
    - 5G = `WPA2-Personal`
    - 2.4G = `WPA2-Personal`
    - 6G = `WPA3-Personal` with `key_mgmt=SAE`
- Baseline acceptance rule:
  - baseline is only considered OK if the STA can complete a 6G STA->AP connection, obtain an IP address by DHCP, and ping the DUT(AP)
  - do not keep all three bands connected simultaneously, because that can create loop issues
  - individual test cases must switch from this single-band environment baseline to the target band required by the case
- Available-tools rule:
  - do not use a validation method that depends on a tool that does not exist on the console
  - if a console command such as `iperf` is unavailable, do not keep it in the candidate flow; choose another valid method or fall back to numeric cross-check where appropriate

## How I will do the work

- I will use existing tools to parse and organize the workbook:
  - `bash` + short Python/openpyxl snippets
  - `sql` for internal session-only row/case/batch tracking
  - `rg` / `view` for YAML and repo inspection
- I will drive serialwrap myself for live DUT/STA validation:
  - baseline setup
  - precondition check
  - command execution
  - evidence capture
  - retry / rerun when needed
- I will use subagents only for offline help:
  - source-code tracing
  - bulk mapping checks
  - repo-wide pattern analysis
- I will not use a subagent to drive serialwrap or to make the final live pass/fail decision.
- Current continuation rule: strict **single-case mode** only.
  - do not batch unresolved cases
  - do not create ad-hoc acceleration tools/scripts to skip the manual evidence loop
- I will update YAML and regression tests directly in this repo after a case is proven live.

## How to resume this work next time

If I open only this file in a future session, I should do the following in order:

1. Re-read the calibration authority and working rules in this file.
2. Re-open repo-root `0401.xlsx` and use `Wifi_LLAPI` `R/S/T` as the answer key (`Pass` = pass, everything else = fail).
3. Rebuild the current STA 2.4G / 5G / 6G interface-to-DUT AP mapping from live MAC/BSSID evidence if it has not already been refreshed for this session.
4. Read the current repo handoff snapshot in this file and `compare-0401.{md,json}`; do not rely on session-local SQL as the primary resume source.
5. Confirm serialwrap access to `COM0/COM1` is healthy before attempting live validation.
6. Pick the next ready **single case** from the handoff snapshot.
7. For that case, follow the per-case operator loop below.
8. Only after live evidence matches the workbook baseline, update YAML and tests.
9. If the case still does not match after sanitation + source cross-check + rerun, move it to blocker tracking instead of forcing a YAML change.

## Per-case calibration loop（Single-Case Mode）

每筆 case 嚴格按以下步驟執行，完成後**不停**，直接進下一筆：

1. **Offline Survey**（sub-agent `explore`）
   - 讀舊 YAML、workbook row、鄰近 prior art
   - 產出：預期 object/API、workbook command、可能 verdict
   - sub-agent **只做離線分析**，不操作實機
2. **Live 三 Band 驗證**（主操作者透過 serialwrap）
   - 5G = AP1 / `wl0` / Radio.1 / SSID.4 / `testpilot5G` / WPA2-Personal
   - 6G = AP3 / `wl1` / Radio.2 / SSID.6 / `testpilot6G` / WPA3-Personal (SAE)
   - 2.4G = AP5 / `wl2` / Radio.3 / SSID.8 / `testpilot2G` / WPA2-Personal
   - 每個 band：baseline getter → setter → readback → driver/hostapd cross-check → restore baseline
   - 判定 verdict：Pass / Not Supported / Fail / mixed-band
3. **YAML 重寫** — 對齊 `0401.xlsx` row、填入 `source.row`、保留 live evidence 與目前 deterministic baseline
4. **Tests**
   - `load_case()` schema 驗證
   - targeted `pytest -k 'dXXX'`
   - runtime file `pytest tests/test_wifi_llapi_plugin_runtime.py`
   - full suite `pytest`
5. **Docs Sync** — 同步 `README.md`、`docs/plan.md`、`docs/todos.md`、`docs/audit-todo.md`、`audit-report`
6. **Precise Stage & Commit** — 只 stage 本案相關檔案，不混入其他 dirty YAML
7. **立刻進下一案** — 把下一個 ready case 標 `in_progress`，回到步驟 1

> commit、簡短進度回覆與 targeted tests pass 都不是停點。只要沒有明確 blocker、lab 失真、或使用者要求暫停，就必須在同一輪直接推進到下一個 ready single case。

## Current repo handoff snapshot（2026-04-02）

- Acceptance campaign: compare live/full-run results against repo-root `0401.xlsx`, `Wifi_LLAPI` sheet, columns `R/S/T`.
- Current compare summary (`compare-0401.json`, rebuilt with overlay through run `20260402T105808547293`):
  - compared cases: **420**
  - full matches: **264**
  - mismatches: **156**
  - metadata drift rows: **67**
  - per-band matched / mismatched:
    - 5G: **283 / 137**
    - 6G: **273 / 147**
    - 2.4G: **275 / 145**
- Active blockers:
  - `D035 OperatingStandard`
  - `D052 Tx_RetransmissionsFailed`
  - `D053 TxBytes`
- Current verified live baseline findings:
  - DUT `COM0`:
    - 5G = `wl0` / `AccessPoint.1` / `SSID.4` / SSID `testpilot5G` / BSSID `2c:59:17:00:19:95` / `WPA2-Personal` / passphrase `00000000`
    - 6G = `wl1` / `AccessPoint.3` / `SSID.6` / SSID `testpilot6G` / BSSID `2c:59:17:00:19:96` / `WPA3-Personal` / `key_mgmt=SAE` / SAE passphrase `00000000`
    - 2.4G = `wl2` / `AccessPoint.5` / `SSID.8` / SSID `testpilot2G` / BSSID `2c:59:17:00:19:a7` / `WPA2-Personal` / passphrase `00000000`
  - STA `COM1` managed interfaces:
    - 5G = `wl0` / BSSID `2c:59:17:00:04:85`
    - 6G = `wl1` / BSSID `2c:59:17:00:04:86`
    - 2.4G = `wl2` / BSSID `2c:59:17:00:04:97`
- Latest live-aligned `0401` checkpoints:
  - `D004 kickStation()` → `Pass/Pass/Pass` via run `20260402T013838223177`
  - `D005 kickStationReason()` → `Pass/Pass/Pass` via run `20260402T020432759837`
  - `D006 sendBssTransferRequest()` → `Pass/Pass/Pass` via run `20260402T021317975166` (pass after retry)
  - `D007 sendRemoteMeasumentRequest()` → `Pass/Pass/Pass` via run `20260402T021716841976`
  - `D009 AssociationTime` → `Pass/Pass/Pass` via run `20260402T023927691290`
  - `D010 AuthenticationState` → `Pass/Pass/Pass` via run `20260402T030604339596`
  - `D012 AvgSignalStrengthByChain` → `Pass/Pass/Pass` via run `20260402T040807394935`
  - `D015 ConnectionDuration` → `Pass/Pass/Pass` via run `20260402T054957340010`
  - `D016 DownlinkBandwidth` → `Pass/Pass/Pass` via run `20260402T060543524189`
  - `D017 DownlinkMCS` → `Pass/Pass/Pass` via run `20260402T063003376730`
  - `D018 DownlinkShortGuard` → `Pass/Pass/Pass` via run `20260402T071356233843`
  - `D023 Inactive` → `Pass/Pass/Pass` via run `20260402T105808547293`
- Latest verified unresolved mismatches:
  - `D011 AvgSignalStrength` → live/source-confirmed `Fail/Fail/Fail` via run `20260402T034832813249`
  - workbook row 11 still expects raw `Pass/Pass/Pass`, so compare remains mismatched on all three bands
  - live evidence:
    - AP1/AP3/AP5 each exposed one live STA (`AssocMac5g/6g/24g`)
    - `wl sta_info` still reported negative smoothed RSSI (`-28 / -85 / -2`)
    - `ubus-cli "WiFi.AccessPoint.{1,3,5}.AssociatedDevice.1.AvgSignalStrength?"` stayed `0` on all three bands
  - source evidence:
    - public/source `wld_ap_nl80211_copyStationInfoToAssocDev()` updates `pAD->SignalStrength`, not the average accumulator path
    - pWHM `wld_assocdev.c` publishes `AvgSignalStrength` from `WLD_ACC_TO_VAL(pAD->rssiAccumulator)`
    - live firmware therefore still behaves fail-shaped even though the datamodel field exists
  - `D013 Capabilities` → live/source-confirmed `Fail/Fail/Fail` via run `20260402T051006378317`
  - workbook row 13 still expects raw `Pass/Pass/Pass`, so compare remains mismatched on all three bands
  - live evidence:
    - AP1/AP3/AP5 each exposed one live STA (`AssocMac5g/6g/24g`)
    - `wl sta_info` reported `RRM capability = 0x0` on all three bands
    - `ubus-cli "WiFi.AccessPoint.{1,3,5}.AssociatedDevice.1.Capabilities?"` read back `"" / "BTM,QOS_MAP,PMF" / ""`
  - source evidence:
    - pWHM `wld_assocDev_copyAssocDevInfoFromIEs()` publishes parsed STA capability bits from `pWirelessDevIE->capabilities`
    - workbook H-column sample references a different STA capability profile (`4A:0A:A5:80:23:7B`) with `RRM,BTM,QOS_MAP,PMF`
    - current deterministic lab STA therefore cannot reproduce the workbook row-13 capability shape
  - `D020 FrequencyCapabilities` → live/source-confirmed `Fail/Fail/Fail` via run `20260402T095404127199`
  - workbook row 20 still expects raw `Pass/Pass/Pass`, so compare remains mismatched on all three bands
  - live evidence:
    - AP1 getter stayed `""` while `wl sta_info` reported `Frequency Bands Supported: 5G` and the normalized driver token was `5GHz`
    - AP3 getter stayed `6GHz` while `wl sta_info` reported `Frequency Bands Supported: 6G` and the normalized driver token was `6GHz`
    - AP5 getter stayed `""` while `wl sta_info` reported `Frequency Bands Supported: 2.4G` and the normalized driver token was `2.4GHz`
    - the first retry failed at `step9_24g_sta_join` with a serialwrap timeout, but the second retry completed all three bands and preserved the same fail-shaped mismatch
  - source evidence:
    - `wld_accesspoint.odl` declares `FrequencyCapabilities` as a read-only string
    - `whm_brcm_scb_stats()` publishes rates/bytes/packets/retries/failures/RSSI but does not map the driver's `Frequency Bands Supported` line into LLAPI
    - current firmware therefore cannot reproduce workbook row 20's `2.4GHz,5GHz,6GHz` shape on AP1/AP3/AP5
- Latest validated commands/tests:
  - `uv run pytest -q plugins/wifi_llapi/tests/test_command_resolver.py plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'driver_capture_shell_step_does_not_use_synthesized_readback or execute_step_capture_prefers_synthesized_readback_query or pending_method_calibration_cases_use_runtime_supported_contracts or execute_step_command_fallback_priority or status_only_sta_checks_do_not_override_deterministic_band_connect or verify_sta_band_connectivity_prefers_case_status_checks'` → `6 passed`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'D010 or pending_method_calibration_cases_use_runtime_supported_contracts or status_only_sta_checks_do_not_override_deterministic_band_connect or verify_sta_band_connectivity_prefers_case_status_checks'` → `3 passed`
  - `uv run pytest -q` → `1599 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D010-authenticationstate --dut-fw-ver BGW720-B0-403` → `Pass/Pass/Pass`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'D011 or pending_readonly_associateddevice_cases_use_live_cross_checks or pending_readonly_associateddevice_cases_evaluate_live_examples or pre_skip_aligned_manual_cases_avoid_stale_sample_values'` → `3 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D011-avgsignalstrength --dut-fw-ver BGW720-B0-403` → live evidence `Fail/Fail/Fail` (`evaluation_verdict=Pass`, final projected status `Fail`)
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'D012 or pending_readonly_associateddevice_cases_use_live_cross_checks or pending_readonly_associateddevice_cases_evaluate_live_examples or pre_skip_aligned_manual_cases_avoid_stale_sample_values'` → `3 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D012-avgsignalstrengthbychain --dut-fw-ver BGW720-B0-403` → `Pass/Pass/Pass` via run `20260402T040807394935` (`AvgSignalStrengthByChain=-30 / -86 / -13`)
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'D013 or pending_readonly_associateddevice_cases_use_live_cross_checks or pending_readonly_associateddevice_cases_evaluate_live_examples or pre_skip_aligned_manual_cases_avoid_stale_sample_values'` → `3 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D013-capabilities --dut-fw-ver BGW720-B0-403` → live evidence `Fail/Fail/Fail` (`evaluation_verdict=Pass`, final projected status `Fail`)
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'env_command_succeeded_allows_macaddress_shell_pipeline or D015 or D016 or pending_readonly_associateddevice_cases_use_live_cross_checks or pending_readonly_associateddevice_cases_evaluate_live_examples'` → `3 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D015-connectionduration --dut-fw-ver BGW720-B0-403` → `Pass/Pass/Pass` via run `20260402T054957340010`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D016-downlinkbandwidth --dut-fw-ver BGW720-B0-403` → `Pass/Pass/Pass` via run `20260402T060543524189`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'pending_readonly_associateddevice_cases_use_live_cross_checks or pending_readonly_associateddevice_cases_evaluate_live_examples'` → `2 passed, 1200 deselected`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D017-downlinkmcs --dut-fw-ver BGW720-B0-403` → `Pass/Pass/Pass` via run `20260402T063003376730`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'pending_boolean_and_frequency_cases_use_supported_contracts or pending_boolean_and_frequency_cases_evaluate_live_examples'` → `2 passed, 1200 deselected`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D018-downlinkshortguard --dut-fw-ver BGW720-B0-403` → first rerun exposed driver-capture shape issue (`20260402T070911215127`); second rerun passed `Pass/Pass/Pass` via run `20260402T071356233843`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py` → `1202 passed`
  - `uv run pytest -q` → `1599 passed`
  - `uv run python -m testpilot.cli wifi-llapi build-template-report --source-xlsx 0401.xlsx` → rebuilt `plugins/wifi_llapi/reports/templates/wifi_llapi_template.xlsx`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_excel_template.py` → `8 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D020-frequencycapabilities --dut-fw-ver BGW720-B0-403` → live/source-confirmed `Fail/Fail/Fail` via run `20260402T095404127199` (`evaluation_verdict=Pass`, pass after retry 2/2)
  - `uv run python scripts/compare_0401_answers.py ... 20260402T095404127199 --output-md compare-0401.md --output-json compare-0401.json` → compare refreshed; summary stayed `263 / 420`, while `D020` actual raw updated to `Fail / Fail / Fail`
  - `uv run pytest -q plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py -k 'pending_inactive_and_bandwidth_cases'` → `2 passed`
  - `uv run python -m testpilot.cli run wifi_llapi --case wifi-llapi-D023-inactive --dut-fw-ver BGW720-B0-403` → `Pass/Pass/Pass` via run `20260402T105808547293`
  - `uv run python scripts/compare_0401_answers.py ... 20260402T105808547293 --output-md compare-0401.md --output-json compare-0401.json` → compare refreshed to `264 / 420`
  - `uv run pytest -q` → `1599 passed`
- Runtime guard rail (must keep):
  - `_env_command_succeeded()` must treat `AssociatedDevice...MACAddress?` as a pure MAC getter only for plain ubus getter commands.
  - Shell pipelines like `STA_MAC=$(ubus-cli "...MACAddress?" | sed ...) && wl ... | sed ...` must fall through to normal success handling so long-command driver cross-checks are not misclassified as failed MAC getters.
- Resolver guard rail (must keep):
  - `CommandResolver.prefer_synthesized_readback()` may synthesize only for raw commands that are non-executable prose/ubus fragments, or executable commands whose first token is `ubus-cli`.
  - Driver shell capture steps (`wl`, `iw`, shell pipelines with `sed` replacements such as `AssocMac5g=\1`) must never be rewritten into wildcard synthesized queries.
- Next ready repo handoff case:
  - `D024 LastDataDownlinkRate`
  - `D023` is now aligned: run `20260402T105808547293` rewrote the stale row-20/6G-skip YAML into a true row-23 three-band case and produced actual raw `Pass / Pass / Pass`
  - `D020` remains the latest verified fail-shaped mismatch: run `20260402T095404127199` preserved actual raw `Fail / Fail / Fail` while the driver normalization stably emits `5GHz / 6GHz / 2.4GHz`
  - `D014 ChargeableUserId` remains workbook-gated `To be tested` / Radius-blocked, so it is not the next actionable live rewrite target
  - `D324` `BytesSent`
  - `D330` `MulticastPacketsReceived`
  - `D331` `MulticastPacketsSent`
  - `D332` `PacketsReceived`
  - `D333` `PacketsSent`
  - `D335` `UnicastPacketsReceived`
  - `D336` `UnicastPacketsSent`
  - the current verified `WiFi.SSID.4.Stats.*` truth source is `/proc/net/dev_extstats` `wl0`
  - verified field mapping:
    - `BytesReceived=$2`
    - `PacketsReceived=$3`
    - `MulticastPacketsReceived=$9`
    - `BytesSent=$10`
    - `PacketsSent=$11`
    - `MulticastPacketsSent=$18`
    - `UnicastPacketsReceived=$21`
    - `UnicastPacketsSent=$22`
    - `BroadcastPacketsReceived=$23`
    - `BroadcastPacketsSent=$24`
  - aligned YAML now keeps workbook row identity only in `source.row`; stale `wifi-llapi-rXXX-*` aliases are removed during live rewrite
- Second live-aligned multiband SSID stats subset is now rewritten against the verified sequential 5G -> 6G -> 2.4G probe:
  - mirrored `getSSIDStats()` rows `D300-D316`
  - direct rows with workbook-open verdicts: `D325-D329`, `D334`, `D337`, `D406`, `D407`
  - direct workbook `Not Supported`: `D495`
  - SSID-level WMM rows `D496-D527`
  - all 69 SSID-level stats cases now use the same sequential single-link band flow and remove stale `wifi-llapi-rXXX-*` aliases
  - direct/getSSIDStats()/driver equality is encoded explicitly for the metric families that have a verified `/proc/net/dev_extstats` mapping
  - retry / failed-retrans / unknown-proto counters keep workbook-gated `To be tested` / `Not Supported` semantics instead of being forced into pass-style criteria
  - SSID-level WMM fields stay `0` on 5G/6G/2.4G while radio-level alternatives remain available via `wl -i wlX wme_counters`
  - the 2.4G leg keeps the STA traffic attempt in the recipe even when ping still drops; final judgment uses the DUT-side counter reread consistency
- Workbook-gated blocker from the same batch:
- `D014` `ChargeableUserId` remains open because workbook `v4.0.3` is still `To be tested/To be tested/To be tested` and BCM comments say the current project lacks Radius method support
- Remaining multi-agent survey blocker from the same 10-case 5G batch:
  - none in `D020/D023`; next survey target shifts to `D024`
- Template alignment status:
  - `plugins/wifi_llapi/reports/templates/wifi_llapi_template.xlsx` has been rebuilt from repo-root `0401.xlsx`
  - `plugins/wifi_llapi/reports/templates/wifi_llapi_template.manifest.json` now records `source_workbook=0401.xlsx`
  - the previous row-shifted template was the root cause of the recent alignment warnings; current template/object/api alignment now matches workbook rows again
- Latest single-case checkpoints after the 5G counter family follow-up:
  - `D054` `TxErrors`
    - same-STA direct getter + AssociatedDevice snapshot + `wl sta_info tx failures` equality
    - workbook verdict remains `To be tested`
  - `D055` `TxMulticastPacketCount`
    - DUT broadcast probe increases COM1 `wl0` RX packets/bytes, but both LLAPI and driver `tx mcast/bcast` counters remain `0`
    - workbook verdict remains `To be tested`
  - `D057` `TxUnicastPacketCount`
    - LLAPI direct getter and AssociatedDevice snapshot stay `0`
    - same STA still reports positive sibling `TxPacketCount` and positive driver `tx ucast pkts`
    - workbook verdict is now encoded as `Fail`
  - `D183` `TPCMode`
    - WLD ODL enum declares `Auto/Off/Ap/Sta/ApSta`
    - live DUT rejects `Off`, accepts `Ap/Sta/ApSta` through ubus readback, and still keeps `wl0 tpc_mode=0`
    - this targeted source/live checkpoint is recorded as a fail-shaped mismatch; primary sweep counts remain unchanged until the workbook verdict ledger is reconciled

## Per-case operator loop

For every individual case, use this exact loop:

1. Identify the workbook row and the matching YAML case file.
2. Write down the expected result for 5G / 6G / 2.4G from `L/M/N`.
3. Clean workbook `G/H` into an executable manual flow.
4. Decide what kind of readback this case needs:
   - direct readback
   - writable-control -> read-only verification
   - refresh/trigger -> readback
   - side-effect verification
   - traffic/counter delta verification
5. Restore the DUT/STA baseline required for this case.
6. Verify preconditions explicitly before the test command.
7. Run the trigger/control/test commands through serialwrap.
8. Capture the exact evidence needed for verdict.
9. Compare the live result with workbook expectation.
10. If mismatch:
    - sanitize command flow
    - source cross-check
    - rerun
11. If still mismatch:
    - record blocker evidence
    - do not rewrite YAML as solved
12. If match:
    - if the workbook result is `To be tested` or `Not Support` / `Not Supported`, only rewrite YAML when the live evidence clearly supports that same non-pass verdict; keep the non-pass semantics explicit
    - otherwise rewrite YAML
    - add/update regression guard
    - run tests

## Evidence that must be captured

For each live-validated case, preserve enough evidence to explain the verdict later:

- workbook row and case id
- exact serialwrap commands used
- exact trigger/control command used if the case is read-only or lazy-populated
- before/after readback values
- band / interface / MAC / BSSID context when identity matters
- side-effect proof when the API is method-style
- blocker reason when the case cannot be aligned

## Completion rule for a single case

A case is only considered aligned when all of the following are true:

- [ ] Workbook expected result is identified.
- [ ] Executable manual serialwrap procedure is normalized from workbook `G/H`.
- [ ] Live serialwrap evidence matches workbook expectation.
- [ ] For setter/method cases, the actual side effect or downstream state change is verified.
- [ ] YAML is rewritten to the validated manual flow.
- [ ] Regression coverage is added or updated where needed.
- [ ] Repo tests pass after the change.

If any item above is not satisfied, the case stays open or moves to blocker tracking.

## Master todo list

### Phase CAL-PRE: Rebuild current DUT / STA band mapping

- [x] `CAL-000` Stop using A0/B0 as the DUT/STA distinction rule.
- [x] `CAL-000a` Discover the current STA interfaces and MAC addresses for 2.4G / 5G / 6G from live evidence.
- [x] `CAL-000b` Re-map each STA band/interface to the DUT AP/BSSID it actually connects to in the current lab.
- [x] `CAL-000c` Record the verified DUT AP <-> STA interface/BSSID/MAC mapping and use it as the baseline for later case validation.
- [ ] `CAL-000d` Sync the verified, working DUT/STA band mapping and environment setup back into the relevant YAML environment settings.
- [ ] `CAL-000e` Push shared verified environment settings into the baseline first, and keep only truly case-specific environment differences in the individual case YAML files.
- [x] `CAL-000f` Verify baseline success criteria: 6G STA->AP association, STA DHCP IP acquisition, and successful ping from STA to DUT(AP).
- [x] `CAL-000g` Ensure the baseline keeps only the intended single-band link active and does not leave 2.4G/5G/6G connected at the same time.
- [ ] `CAL-000h` For each test case, switch from the verified single-band baseline to the specific band environment required by that case.

### Phase CAL-0: Inventory and mapping

- [ ] `CAL-001` Extract every `Wifi_LLAPI` workbook row into a normalized inventory.
- [ ] `CAL-002` Map each workbook row to the corresponding YAML case file.
- [ ] `CAL-003` Tag each row with expected result type:
  - `Pass`
  - `Fail`
  - `Not Supported`
  - `Skip`
  - `To be tested`
- [ ] `CAL-004` Tag each row with validation family:
  - `AccessPoint methods`
  - `AssociatedDevice telemetry`
  - `Security / SSID / WPS`
  - `Radio / AP / SSID config`
  - `Stats / counters`
- [ ] `CAL-005` Tag required bands, topology assumptions, and extra dependencies.
- [ ] `CAL-006` Produce the execution batch order and dependency list.

### Phase CAL-1: Workbook recipe sanitation

- [ ] `CAL-101` Clean workbook `G/H` into executable manual commands.
- [ ] `CAL-102` Strip transcript artifacts:
  - prompt fragments
  - wrapped lines
  - copied sample output inside commands
  - malformed placeholders
  - invalid arguments created by line wrapping
- [ ] `CAL-103` Identify the real truth source per case:
  - `ubus-cli` readback
  - `wl assoclist`
  - `wl sta_info`
  - `iw dev ... link`
  - hostapd config/logs
  - interface/IP state
  - traffic/counter deltas
- [ ] `CAL-104` Flag rows that require source cross-check before live rerun.
- [ ] `CAL-105` Flag rows that need special infra or topology:
  - single roaming STA
  - Radius
  - traffic generator
  - multi-band neighbor visibility
- [ ] `CAL-106` Flag rows that need a prerequisite refresh / trigger action before readback.

### Phase CAL-2: AssociatedDevice batch

- Progress note:
  - the first verified 6G getter-only subset is aligned: `D009`, `D010`, `D016`, `D019`, `D027`
  - the second verified 5G subset is aligned: `D011`, `D015`, `D017`, `D018`
  - the third verified 5G subset is aligned: `D021`, `D022`, `D024`, `D025`, `D026`
  - regression guards were added for these patterns in `tests/test_wifi_llapi_plugin_runtime.py`
  - `D019` workbook `v4.0.3` expectation is confirmed as `Pass/Pass/Pass`; the older YAML `To be tested` reference was stale
  - `D014` remains blocker-only because workbook `v4.0.3` is still `To be tested` and the current lab has no Radius-backed path to validate `ChargeableUserId`
  - `D013` and `D020` now preserve explicit fail-shaped contracts after live + source cross-check; `D023` is now live-aligned as a row-23 three-band pass case

## Pause / resume handoff（2026-04-02）

- Work objective:
  - continue the workbook-driven `0401.xlsx` single-case calibration loop for `wifi_llapi`
  - preserve repo-only handoff so work can resume cleanly after a WSL backup pause
- Work completed in this checkpoint:
  - closed `D020 FrequencyCapabilities` as a verified fail-shaped mismatch (`Fail / Fail / Fail`)
  - rebuilt `compare-0401` with `D020` overlay and kept summary stable at `263 / 420`
  - identified `D023 Inactive` as stale row mapping (`source.row=20`) plus stale 6G skip semantics
  - rewrote `D023` into a true row-23 three-band pass-style case
  - updated runtime tests and revalidated with targeted pytest
  - live-ran `D023` successfully on AP1/AP3/AP5 and rebuilt `compare-0401` to `264 / 420`
  - re-ran full suite successfully (`1599 passed`)
  - locked calibration authority to workbook `G/H` and explicitly ignored `F`
  - re-ran preflight guardrails: multiline block-scalar ban passed, serialwrap 120-char staging tests passed
  - added official-case `>120` char command inventory guardrail; current tracked inventory = `597`
  - re-ran full suite again after the new guardrail (`1600 passed`)
  - attempted fresh live full-run preflight, but serialwrap daemon reported `0` devices / `0` sessions and the environment exposed no `/dev/ttyUSB*` or `/dev/serial/by-id`, so live Phase 3 is blocked pending DUT/STA UART return
- Progress record:
  - latest aligned case: `D023 Inactive` via run `20260402T105808547293`
  - latest compare summary: `264 / 420` full matches, `156` mismatches
  - latest stable fail-shaped mismatches: `D011`, `D013`, `D020`
  - next ready case after resume: `D024 LastDataDownlinkRate`
  - current live blocker: no serial devices present; `COM0/COM1` do not exist, so fresh full run and subsequent live calibration cannot start
- Resume instructions:
  - start from this file plus `compare-0401.{md,json}`
  - use `compare-0401.{md,json}` rebuilt through `20260402T105808547293`
  - before any live run, restore UART visibility so serialwrap can see `/dev/ttyUSB*` / `/dev/serial/by-id`, then rebuild `COM0/COM1` sessions and confirm `session self-test` passes
  - resume with offline survey of `D024`, then run the standard single-case live loop
- [ ] `CAL-201` Validate object identity semantics:
  - STA MAC vs AP BSSID
  - object instance vs wildcard query
  - band/interface mapping
- [ ] `CAL-202` Validate state/time style fields:
  - `AuthenticationState`
  - `AssociationTime`
  - `ConnectionDuration`
  - similar read-only state/timestamp fields
- [ ] `CAL-202a` Find and verify prerequisite trigger calls for lazy-populated AssociatedDevice read paths.
- [ ] `CAL-203` Validate signal/rate/bandwidth style fields:
  - RSSI / signal strength
  - bandwidth
  - MCS / guard interval / related link metrics
- [ ] `CAL-204` Validate capability-style fields:
  - feature/capability strings
  - frequency/band support
- [ ] `CAL-205` Rewrite matched AssociatedDevice YAML cases.
- [ ] `CAL-206` Add regression guards for AssociatedDevice anti-patterns.

### Phase CAL-3: AccessPoint method batch

- [ ] `CAL-301` Validate disconnect/control methods:
  - `kickStation`
  - `kickStationReason`
  - similar method-style cases
- [ ] `CAL-302` Validate roaming / measurement / neighbor methods:
  - `sendBssTransferRequest`
  - `sendRemoteMeasumentRequest`
  - neighbor-related APIs
- [ ] `CAL-303` For each method case, confirm:
  - command shape is executable
  - arguments are correct
  - return/error behavior matches workbook expectation
  - side effects are verified by live evidence
- [ ] `CAL-304` Rewrite matched AccessPoint method YAML cases.
- [ ] `CAL-305` Add regression guards for method-command anti-patterns.
- [ ] `CAL-306` Record topology-dependent blockers that cannot be resolved in the current lab.

### Phase CAL-4: Security / SSID / WPS batch

- [ ] `CAL-401` Validate security mode and encryption related cases.
- [ ] `CAL-402` Validate key / passphrase / MFP / SHA / related security cases.
- [ ] `CAL-403` Validate SSID-level state and identity cases.
- [ ] `CAL-404` Validate WPS cases and separate true support gaps from workbook placeholders.
- [ ] `CAL-405` Rewrite matched Security / SSID / WPS YAML cases.
- [ ] `CAL-406` Add regression guards for skip/not-supported/security semantics.

### Phase CAL-5: Radio / AP / SSID configuration batch

- [ ] `CAL-501` Validate enable/status/channel/class/bandwidth related cases.
- [ ] `CAL-502` Validate thresholds and control fields:
  - fragmentation
  - RTS
  - guard interval
  - beamforming
  - MU-MIMO
  - related radio capabilities
- [ ] `CAL-503` Validate roaming / MBO / interworking / discovery / mobility related config cases.
- [ ] `CAL-504` Confirm which fields are read-only, writable, unsupported, or workbook-specific expectations.
- [ ] `CAL-505` Rewrite matched Radio / AP / SSID YAML cases.
- [ ] `CAL-506` Add regression guards for config-case write/readback anti-patterns.

### Phase CAL-6: Stats and counters batch

- Progress note:
  - the first verified `WiFi.SSID.{i}.Stats.` 5G subset is aligned: `D321`, `D322`, `D323`, `D324`, `D330`, `D331`, `D332`, `D333`, `D335`, `D336`
  - all ten now point at workbook `0310-BGW720-300_LLAPI_Test_Report.xlsx` with real workbook rows `245/246/247/248/254/255/256/257/259/260`
  - all ten were converted from stale sample-value / `=0` pseudo-tests into getter-only equality checks between:
    - `WiFi.SSID.4.Stats.<Field>?`
    - `WiFi.SSID.4.getSSIDStats()`
    - `/proc/net/dev_extstats` `wl0`
  - aligned SSID stats YAML no longer retains `wifi-llapi-rXXX-*` aliases; workbook row identity now lives only in `source.row`
  - regression guards were added for this subset in `tests/test_wifi_llapi_plugin_runtime.py`
  - the remaining mirrored SSID stats rows are also now aligned to the multiband sequential recipe:
    - `getSSIDStats()` `Pass`: `D300-D307`, `D309-D312`, `D314-D315`
    - direct workbook-open (`To be tested`): `D325-D329`, `D334`, `D337`, `D406`, `D407`
    - direct / `getSSIDStats()` workbook `Not Supported`: `D308`, `D313`, `D316`, `D495`
    - SSID-level WMM workbook `Not Supported`: `D496-D527`
  - multiband live evidence proved:
    - 5G `SSID.4`, 6G `SSID.6`, and 2.4G `SSID.8` can all be judged from the same direct ↔ getSSIDStats() reread pattern
    - for mapped fields, `/proc/net/dev_extstats` stays aligned on all three bands
    - SSID-level WMM counters stay `0` on all three bands even though radio-level WMM counters exist separately
  - regression guards now cover multiband direct / getSSIDStats() / WMM categories instead of the earlier 5G-only subset
- [ ] `CAL-601` Validate which counter cases are meaningful without extra traffic.
- [ ] `CAL-602` For traffic-dependent counters, define the minimal reproducible traffic method before judging YAML.
- [ ] `CAL-602a` If the needed traffic/beacon generator or console tool is unavailable, fall back to numeric cross-check and note the limitation in the audit report.
- [ ] `CAL-603` Validate packet/byte/retry/multicast/broadcast style counters.
- [ ] `CAL-604` Separate true `To be tested` / infra-missing cases from bad YAML criteria.
- [ ] `CAL-604a` If workbook says `To be tested` or `Not Supported`, only rewrite YAML when the live evidence confirms the same non-pass verdict and the YAML keeps that verdict explicit.
- [ ] `CAL-605` Rewrite matched Stats/Counters YAML cases.
- [ ] `CAL-606` Add regression guards for counter delta and evidence rules.

### Phase CAL-7: Blocker ledger and closeout

- [ ] `CAL-701` Maintain a blocker ledger with:
  - case id
  - workbook row
  - live evidence summary
  - probable cause
  - missing prerequisite
  - whether source cross-check changed the conclusion
- [ ] `CAL-702` Keep a list of cases already aligned and rewritten.
- [ ] `CAL-703` Run targeted tests after each batch rewrite.
- [ ] `CAL-704` Run full `pytest` at stable checkpoints.
- [ ] `CAL-705` Reassess whether enough calibration is complete to resume broader full-run validation work.
- [ ] `CAL-706` Produce a markdown audit report at `plugins/wifi_llapi/reports/audit-report-YYMMDD-hhmmss.md`.
- [ ] `CAL-707` Ensure the audit report uses collapsible markdown sections for:
  - aligned items
  - YAML calibration content
  - pass/fail standard adjustments and reasons
  - blocker items and reasons
  - supporting evidence
  - `Per-case 摘要表（zh-tw）` for every aligned batch
    - include a summary table with: case id, workbook row, API, verdict, DUT log interval, STA log interval
    - include one subsection per aligned case
    - each per-case subsection must contain fenced code blocks for:
      - STA commands
      - DUT commands
      - pass-judgment log excerpt / log interval
    - when line intervals are known, keep the `Lxxx-Lyyy` notation in the report so later updates follow the same evidence style
    - do not collapse this per-case evidence into prose-only summaries; the command and log blocks are mandatory once a case is marked aligned

## Working rules during execution

- Do not mark a case complete based only on:
  - old YAML
  - run1 output
  - workbook sample numbers copied as pass criteria
  - old A0/B0-based assumptions about which board or interface is playing STA vs DUT
- Prefer direct evidence over assumptions:
  - if a field is dynamic, validate it dynamically
  - if identity matters, validate the exact object instance
  - if a method claims a side effect, verify the side effect separately
  - if a field is read-only, validate it through the writable control path that changes it
  - if a read path is lazy-populated, validate it through the required refresh or trigger call before judging the readback
- If the workbook and current lab disagree:
  - first sanitize the workbook procedure
  - then cross-check source
  - then rerun
  - only then decide whether the case is a blocker
- If the workbook row is `To be tested` or `Not Support` / `Not Supported`:
  - do not convert the case into a fake `Pass`
  - if the YAML is updated, keep the workbook non-pass verdict explicit and evidence-backed
- Do not rely on tools that are not actually present on the console:
  - if the command is missing, remove that method from consideration
  - do not write nonexistent-tool flows into YAML
