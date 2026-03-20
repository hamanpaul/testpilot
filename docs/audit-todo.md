# Wifi_LLAPI Workbook Calibration Audit Todo

> Audit checklist for workbook-driven LLAPI calibration.
>
> `docs/todos.md` remains the project-wide board. This file expands the calibration work into a checkable execution list for review and evidence tracking.
>
> Any session SQL tracking is internal assistant scratchpad only. User-facing review artifacts for this work are this file and the final audit report.

## Calibration authority

- Acceptance baseline: `~/0310-BGW720-300_LLAPI_Test_Report.xlsx` `Wifi_LLAPI` sheet, BCM v4.0.3 result columns `L/M/N`.
- Additional interpretation source: workbook BCM comment columns `O/P`.
- Manual procedure seed: workbook `F/G` (`Test Steps` / `Command Output`).
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
2. Re-open `~/0310-BGW720-300_LLAPI_Test_Report.xlsx` and use `Wifi_LLAPI` BCM `L/M/N/O/P` as the baseline.
3. Rebuild the current STA 2.4G / 5G / 6G interface-to-DUT AP mapping from live MAC/BSSID evidence if it has not already been refreshed for this session.
4. Read the current repo handoff snapshot in this file plus the latest checkpoint section at the top of `plugins/wifi_llapi/reports/audit-report-260313-185447.md`; do not rely on session-local SQL as the primary resume source.
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
3. **YAML 重寫** — 對齊 `0310` workbook、填入 `source.row`、AP-only、live evidence
4. **Tests**
   - `load_case()` schema 驗證
   - targeted `pytest -k 'dXXX'`
   - runtime file `pytest tests/test_wifi_llapi_plugin_runtime.py`
   - full suite `pytest`
5. **Docs Sync** — 同步 `README.md`、`docs/plan.md`、`docs/todos.md`、`docs/audit-todo.md`、`audit-report`
6. **Precise Stage & Commit** — 只 stage 本案相關檔案，不混入其他 dirty YAML
7. **立刻進下一案** — 把下一個 ready case 標 `in_progress`，回到步驟 1

> commit、簡短進度回覆與 targeted tests pass 都不是停點。只要沒有明確 blocker、lab 失真、或使用者要求暫停，就必須在同一輪直接推進到下一個 ready single case。

## Current repo handoff snapshot（2026-03-20）

- Trusted/calibrated official cases: **212 / 415**
- Remaining official cases: **203**
- Active blockers:
  - `D037 OperatingStandard`
  - `D054 Tx_RetransmissionsFailed`
  - `D055 TxBytes`
- 執行順序：blockers 先保留在 blocker 清單，不插回目前從 `D087` 往後的 sequential queue；待其餘待校正案例收斂後再回頭處理
- Latest committed single-case checkpoints:
  - `D056 TxErrors` → workbook-aligned `To be tested` checkpoint (`9880918`)
  - `D057 TxMulticastPacketCount` → workbook-aligned `To be tested` checkpoint (`01fd2c3`), plus MAC normalization follow-up (`426de8a`)
  - `D059 TxUnicastPacketCount` → workbook-aligned **Fail-shaped mismatch** (`49640dd`)
  - `D060 UNIIBandsCapabilities` → workbook-aligned `Pass` checkpoint (`ff9ada2`, shared batch commit with `D046/D051/D058`)
  - `D061 UplinkBandwidth` → workbook-aligned `Pass` checkpoint (`538a741`)
  - `D062 UplinkMCS` → workbook-aligned `Pass` checkpoint (`c7470b2`)
  - `D063 UplinkShortGuard` → workbook-aligned `Pass` checkpoint (`8000121`)
  - `D064 VendorOUI` → workbook-aligned **Fail-shaped mismatch** checkpoint (`ed480e2`)
  - `D065 VhtCapabilities` → workbook-aligned **Fail-shaped mismatch** checkpoint (`fb6bcc0`)
  - `D066 APBridgeDisable` → workbook-aligned **Not Supported** checkpoint（5G AP-only toggle/readback diverges between northbound getter, hostapd config, and driver `ap_isolate`）
  - `D067 BridgeInterface` → workbook-aligned `Pass` checkpoint（AP-only multiband getter, hostapd bridge config, and live Linux bridge master all converge on `br-lan`）
  - `D068 DiscoveryMethodEnabled (FILS)` → workbook-aligned **Not Supported** checkpoint（AP-only multiband `FILS` writes are rejected as invalid, while `FILSDiscovery` is accepted and must be restored back to `Default`）
  - `D069 DiscoveryMethodEnabled (UPR)` → workbook-aligned mixed-band checkpoint（AP1/AP5 reject `UPR` as invalid and stay `Default`, while AP3 accepts `UPR` and reads back `UPR` before restore）
  - `D070 DiscoveryMethodEnabled (RNR)` → workbook-aligned mixed-band checkpoint（AP1/AP3/AP5 all accept/read back `RNR`, but only AP3 / wl1 hostapd `rnr=` flips from `0/0` to `1/0` before restore, so this is calibrated as 5G `Fail` / 6G `Pass` / 2.4G `Fail`）
  - `D072 Enable` → workbook-aligned AP-only multiband `To be tested` checkpoint（AP1/AP3/AP5 all cleanly toggled `Enable=1 -> 0 -> 1`, `Status` followed `Enabled -> Disabled -> Enabled`, driver `wl -i wlX bss` followed `up -> down -> up`, and hostapd `start_disabled` appeared only in the disabled phase）
  - `D073 FTOverDSEnable` → workbook-aligned AP-only multiband `To be tested` checkpoint（AP1/AP3/AP5 all required `IEEE80211r.Enabled=1` + `MobilityDomain=4660`, getter FT state stayed `0` at baseline, flipped to `1` on the setter, returned to `0` on restore, and hostapd `ft_over_ds` followed the same `0 -> 1 -> 0` path while `mobility_domain` stayed `3412`）
  - `D074 MobilityDomain` → workbook-aligned AP-only multiband `To be tested` checkpoint（AP1/AP3/AP5 all started from `IEEE80211r.Enabled=0` / `MobilityDomain=0`, the setter `MobilityDomain=27476` read back as decimal `27476`, and hostapd stored the same value as byte-swapped hex `546B` while `ft_over_ds` remained `0`）
  - `D077 InterworkingEnable` → workbook-aligned AP-only multiband `To be tested` checkpoint（AP1/AP3/AP5 all toggled `InterworkingEnable 0 -> 1 -> 0`, while each hostapd file kept two `interworking=` lines and converged `one/zero/total = 0/2/2 -> 1/1/2 -> 0/2/2`）
  - `D078 QoSMapSet` → workbook-aligned AP-only multiband `Not Supported` checkpoint（workbook row 70 / AP1/AP3/AP5 all started from `QoSMapSet=""` with no `qos_map_set=` line, but writing the requested DSCP map always collapsed both getter and hostapd to scalar `255` / `qos_map_set=255` before restore returned to `EMPTY / ABSENT`）
  - `D079 MacFilterAddressList` → workbook-aligned AP-only multiband `Pass` checkpoint（AP1/AP3/AP5 all started with an empty getter and empty `MACFiltering.Entry` tree, and after `MACFiltering.addEntry(mac=...)` / `delEntry(mac=...)` the bounded `sleep 2` readback showed the getter and entry tree converging together to the same band-specific MAC and then back to the empty baseline）
  - `D080 Entry` → workbook-aligned AP-only multiband `Pass` checkpoint（AP1/AP3/AP5 的 `MACFiltering.Entry.?` 都從 `No data found` 基線出發，`addEntry(mac=...)` 後收斂出單一 `Entry.Alias` / `Entry.MACAddress` 節點，`delEntry(mac=...)` 後回到 `No data found`；ACL file side effect 依 mode split 而不同，因此留給 D081 處理）
  - `D081 Mode` → workbook-aligned AP-only multiband `Fail` checkpoint（AP1 baseline 是 `BlackList` + `deny_mac_file=/tmp/hostap_wl0.acl`，AP3/AP5 baseline 都已是 `Off` 且 hostapd 無 ACL line，但 `ubus-cli WiFi.AccessPoint.{1|3|5}.MACFiltering.Mode=Off` 在三個 band 都仍回 `ERROR: ... invalid value`，並留下不變的 getter / hostapd ACL 狀態）
  - `D082 MaxAssociatedDevices` → workbook-aligned AP-only multiband `Fail` checkpoint（AP1/AP3/AP5 的 northbound getter 都會接受 setter 並 read back `32 -> 31 -> 32`，但 `/tmp/wl{0,1,2}_hapd.conf` 的兩條 `max_num_sta=` 都固定維持 `32`，因此目前仍未符合 workbook 記錄的 `Pass` 路徑）
  - `D083 MBOEnable` → workbook-aligned AP-only multiband `Fail` checkpoint（AP1/AP3/AP5 的 northbound getter 都會接受 `MBOEnable 0 -> 1 -> 0` readback，但 `/tmp/wl{0,1,2}_hapd.conf` 的 `mbo=` 在三個 band 都持續 absent，因此目前仍未符合 workbook 記錄的 `Pass` 路徑）
  - `D084 MultiAPType` → workbook-aligned AP-only multiband `Fail` checkpoint（AP1/AP3/AP5 的 northbound getter 與 `wl -i wlX map` 都會接受 `BackhaulBSS` 並在 restore 後回到 `FronthaulBSS,BackhaulBSS`，但 `/tmp/wl{0,1,2}_hapd.conf` 的 `multi_ap=` 在 setter 後只從 `3/3` 變成 `1/3`，沒有完整收斂到 backhaul-only）
  - `D085 Neighbour` → workbook-aligned AP-only multiband `Pass` checkpoint（AP1/AP3/AP5 都從空的 `Neighbour` tree 出發，`setNeighbourAP(BSSID=...,Channel=...)` 會收斂出單一 `Neighbour.1.BSSID/Channel`，`delNeighbourAP(BSSID=...)` 則會把 tree restore 回 empty baseline）
  - `D086 EncryptionMode` → workbook-aligned AP-only multiband `Not Supported` checkpoint（AP1/AP3/AP5 的 getter 都固定回 `EncryptionMode="Default"`，但 `/tmp/wl{0,1,2}_hapd.conf` 仍明確暴露 `WPA-PSK/SAE + CCMP` 的真實 security lines，符合 workbook `hardcode in pwhm`）
  - `D087 KeyPassPhrase` → workbook-aligned AP-only multiband `Pass` checkpoint（AP1/AP3/AP5 的 getter 與 hostapd `wpa_passphrase=` 都能在 quoted syntax 下收斂 `00000000 -> 0689388783 -> 00000000`，而 bare leading-zero setter 會被 misparse 成 `689388783.000000`；6G `sae_password=` 維持 baseline `00000000`）
  - `D088 MFPConfig` → workbook-aligned AP-only mixed-band checkpoint（AP1/AP5 的 getter 與 hostapd `ieee80211w=0` 都收斂到 `Disabled`，但 AP3 / wl1 仍固定 `MFPConfig="Disabled"` 與 `wpa_key_mgmt=SAE + ieee80211w=2` 的 live `Required` 狀態不一致）
  - `D089 ModeEnabled` → workbook-aligned AP-only multiband `Pass` checkpoint（AP1/AP3/AP5 的 setter `ModeEnabled=WPA3-Personal` 都被接受，getter 和 hostapd 在 wl0/wl1/wl2 都收斂到 `SAE` + `ieee80211w=2`，restore 到 WPA2-Personal 在 AP1/AP5 也都正常回復到 `WPA-PSK` + `ieee80211w=0`）
  - `D090 ModesSupported` → workbook-aligned AP-only multiband `Pass` checkpoint（read-only getter, setter returns error 15; 5G/2.4G 回傳完整 mode list 含 OWE，6G 只回 `None,WPA3-Personal,OWE`）
  - `D185 TPCMode` → source/live **Fail-shaped mismatch** checkpoint，現已納入 `148 / 415` 完成數
  - `D368 SRGBSSColorBitmap` → 0310 row 273 **Fail-shaped mismatch** checkpoint，現已納入 `148 / 415` 完成數（5G/6G/2.4G setters all accepted/read back `"1"`, but hostapd `he_spr_srg_bss_colors=` stayed absent on wl0/wl1/wl2）
  - `D371 SRGPartialBSSIDBitmap` → 0310 row 276 mixed-band checkpoint，現已納入 `148 / 415` 完成數（5G/6G setters accepted/read back `"1"` while hostapd `he_spr_srg_partial_bssid=` stayed absent; 2.4G setter failed with `error=4` / `parameter not found`）
- Latest validated commands:
  - `load_case(plugins/wifi_llapi/cases/D090_modessupported.yaml)` → `steps=6`
  - `uv run pytest -q tests/test_wifi_llapi_plugin_runtime.py -k 'd090'` → `3 passed`
  - `uv run pytest -q tests/test_wifi_llapi_plugin_runtime.py` → `239 passed`
  - `uv run pytest -q` → `292 passed`
  - `serialwrap COM0 D090 ModesSupported probe` → AP1/AP5 return full mode list; AP3 returns restricted `None,WPA3-Personal,OWE`; setter on all bands returns `error=15 (read-only)`
- Next ready repo handoff case:
  - `D091 PreSharedKey` → workbook-aligned AP-only multiband `Pass(5G)/Not Supported(6G)/Pass(2.4G)` checkpoint（PreSharedKey 64-char hex setter/readback accepted on 5G/2.4G; 6G setter accepted but WPA3-only semantics → Not Supported; hostapd wpa_psk= only appears via KeyPassPhrase route）
  - `load_case(plugins/wifi_llapi/cases/D091_presharedkey_accesspoint_security.yaml)` → `steps=12`
  - `serialwrap COM0 D091 PreSharedKey probe` → AP1/AP5 setter+readback pass; AP3 setter accepted but 6G WPA3-only; hostapd wpa_psk never appears via PreSharedKey API alone
  - `D092 RekeyingInterval` → workbook-aligned AP-only multiband `Fail` checkpoint（setter accepted + getter reads back 3600 on all 3 bands, but hostapd wpa_group_rekey does not consistently update; 5G/6G stay 0, 2.4G partially converges）
  - `load_case(plugins/wifi_llapi/cases/D092_rekeyinginterval.yaml)` → `steps=12`
  - `serialwrap COM0 D092 RekeyingInterval probe` → AP1/AP3/AP5 setter+readback pass; hostapd wpa_group_rekey diverges on all bands
  - `D093 SHA256Enable` → workbook-aligned AP-only multiband `Fail` checkpoint（setter accepted + getter reads back 1 on all 3 bands, but hostapd wpa_key_mgmt stays WPA-PSK/SAE without gaining SHA256 suffix）
  - `load_case(plugins/wifi_llapi/cases/D093_sha256enable.yaml)` → `steps=12`
  - `serialwrap COM0 D093 SHA256Enable probe` → AP1/AP3/AP5 setter+readback pass; hostapd wpa_key_mgmt unchanged on all bands
  - `D094 WEPKey` → workbook-aligned AP-only multiband `Fail` checkpoint（setter accepted + getter reads back AABBCCDDEEFF0 on all 3 bands, but hostapd has NO wep lines under WPA2/WPA3 ModeEnabled）
  - `load_case(plugins/wifi_llapi/cases/D094_wepkey_accesspoint_security.yaml)` → `steps=12`
  - `serialwrap COM0 D094 WEPKey probe` → AP1/AP3/AP5 setter+readback pass; hostapd has zero WEP lines
  - `D095 SSIDAdvertisementEnabled` → workbook-aligned AP-only multiband `Pass` checkpoint（setter=0 causes hostapd ignore_broadcast_ssid to flip 0→2 on all 3 bands; restore=1 brings it back to 0）
  - `load_case(plugins/wifi_llapi/cases/D095_ssidadvertisementenabled.yaml)` → `steps=12, pass_criteria=15`
  - `serialwrap COM0 D095 SSIDAdvertisementEnabled probe` → AP1/AP3/AP5 setter+readback+hostapd full round-trip pass
  - `D096 Status` → workbook-aligned AP-only multiband `Pass` checkpoint（read-only getter, Status="Enabled" + driver bss=up on all 3 bands）
  - `load_case(plugins/wifi_llapi/cases/D096_status_accesspoint.yaml)` → `steps=3, pass_criteria=6`
  - `serialwrap COM0 D096 Status probe` → AP1/AP3/AP5 Status="Enabled" + wl bss=up
  - `D097 UAPSDCapability` → workbook-aligned AP-only multiband `Pass` checkpoint（read-only capability getter, UAPSDCapability=1 on all 3 bands, setter returns error 15 read-only; hostapd uapsd_advertisement_enabled=0 / driver wme_apsd=0 = not active but capability present）
  - `load_case(plugins/wifi_llapi/cases/D097_uapsdcapability.yaml)` → `steps=3, pass_criteria=3`
  - `serialwrap COM0 D097 UAPSDCapability probe` → AP1/AP3/AP5 UAPSDCapability=1 + hostapd wmm/uapsd + driver wme_apsd cross-check
  - `D098 UAPSDEnable` → workbook-aligned AP-only multiband `Pass` checkpoint（setter 0→1→0 全 3 band 都收斂：northbound getter、hostapd uapsd_advertisement_enabled first BSS、driver wme_apsd 同步翻轉；workbook 標 Not Support 但實際 API 完整運作）
  - `load_case(plugins/wifi_llapi/cases/D098_uapsdenable.yaml)` → `steps=3, pass_criteria=15`
  - `serialwrap COM0 D098 UAPSDEnable probe` → AP1/AP3/AP5 baseline=0, setter=1 accepted, hostapd/driver flip, restore=0 converges
  - `D099 VendorIE` → workbook-aligned AP-only multiband `Not Supported` checkpoint（VendorIEs.Enable=0 exists but createVendorIE() returns ERROR: call (null) failed with status 1 on all 3 bands）
  - `load_case(plugins/wifi_llapi/cases/D099_vendorie.yaml)` → `steps=3, pass_criteria=6`
  - `serialwrap COM0 D099 VendorIE probe` → AP1/AP3/AP5 Enable=0 + createVendorIE() error on all bands
- Continuation guard rails:
  - only committed YAML / docs count as trusted handoff state
  - do not infer progress from any local unstaged experiment outside these committed checkpoints
  - reuse `D058 TxPacketCount` as the positive same-STA tx-packet prior art when judging `D059`/`D060` family cases
  - `D185` / `D368` / `D371` 已從待校正池移出並折入完成數；最新 main-sweep checkpoint 則前進到 `D119`，下一個 ready sequential case 為 `D176`
  - `D100` WDSEnable — 3-band setter round-trip with `wl dwds` driver convergence
  - `D101` WMMCapability — 3-band read-only getter, `wmm_enabled=1` on all bands
  - `D102` WMMEnable — 3-band setter round-trip, hostapd `wmm_enabled` converges; workbook marks Not Support
  - `D103` ConfigMethodsEnabled — mixed-band setter: 5G/2.4G Pass, 6G Fail (no hostapd config_methods)
  - `D104` ConfigMethodsSupported — 3-band read-only getter, full method list; workbook marks Not Support
  - `D105` Configured — 3-band read-only getter, `Configured=1`
  - `D106` WPS.Enable — mixed-band setter: 5G/2.4G Pass (wps_state converges), 6G Not Supported (wps_state stays 0)
  - `D107` PairingInProgress — 3-band read-only getter, `PairingInProgress=0`
  - `D108` RelayCredentialsEnable — 3-band read-only getter, `RelayCredentialsEnable=0`; workbook marks Not Support
  - `D109` SelfPIN — 3-band setter round-trip, `90455865→12345678→90455865` converges

Current verified live baseline findings from this session:

- DUT `COM0`:
  - 5G = `wl0` / `AccessPoint.1` / `SSID.4` / SSID `testpilot5G` / BSSID `2c:59:17:00:19:95` / `WPA2-Personal` / passphrase `00000000`
  - 6G = `wl1` / `AccessPoint.3` / `SSID.6` / SSID `testpilot6G` / BSSID `2c:59:17:00:19:96` / `WPA3-Personal` / `key_mgmt=SAE` / SAE passphrase `00000000`
  - 2.4G = `wl2` / `AccessPoint.5` / `SSID.8` / SSID `testpilot2G` / BSSID `2c:59:17:00:19:a7` / `WPA2-Personal` / passphrase `00000000`
- STA `COM1` candidate managed interfaces:
  - 5G = `wl0` / MAC `2c:59:17:00:04:85`
  - 6G = `wl1` / MAC `2c:59:17:00:04:86`
  - 2.4G = `wl2` / MAC `2c:59:17:00:04:97`
- Current `D060-D079` batch triage:
  - `D060/D061` are already committed 0310/5G-only live-aligned cases and do not need to be re-done before the next handoff step
  - `D062` is now a committed 0310/5G-only live-aligned pass case; use the same-STA post-trigger snapshot + `wl sta_info ... rx nrate` `mcs` equality pattern as the prior art
  - `D063` is now a committed 0310/5G-only live-aligned pass case; reuse its same-STA post-trigger snapshot + driver GI mapping pattern (`0.4us/0.8us/1.6us => 1`, `3.2us => 0`, unknown GI fail-closed) as the immediate prior art
  - `D064` is now a committed 0310/5G-only live-aligned fail case; reuse its same-STA direct getter + snapshot empty-string cross-check against non-empty `wl sta_info` vendor OUI list as the immediate prior art
  - `D065` is now a committed 0310/5G-only live-aligned fail case; reuse its same-STA direct getter + snapshot empty-string cross-check against normalized driver-side `VHT caps` tokens as the immediate prior art
  - `D066` is now a committed 0310/5G-only AP-only live-aligned Not Supported case; reuse its APBridgeDisable toggle/readback versus `hostapd.conf`/driver divergence pattern as the immediate prior art for remaining AccessPoint setter families
  - `D067` is now a committed 0310/AP-only multiband live-aligned pass case; reuse its direct getter + hostapd `bridge=` + `/sys/class/net/*/master/uevent` cross-check pattern for remaining read-only AccessPoint bridge-family getters
  - `D068` is now a committed 0310/AP-only multiband live-aligned Not Supported case; reuse its `Default -> FILS invalid -> FILSDiscovery accepted -> restore Default` pattern for the remaining `DiscoveryMethodEnabled` enum families
  - `D069` is now a committed 0310/AP-only multiband mixed-band case; reuse its `Default -> 5G invalid / 6G UPR accepted / 2.4G invalid -> restore Default` pattern for remaining `DiscoveryMethodEnabled` enum families with split band behavior
  - `D070` is now a committed 0310/AP-only multiband mixed-band case; reuse its northbound `RNR` readback versus hostapd `rnr=` divergence pattern when a setter appears accepted on every band but only one band changes real config state
  - `D072` is now a committed 0310/AP-only multiband `To be tested` case; reuse its `Enable=1 -> 0 -> 1` plus `Status` / `wl bss` / `start_disabled` convergence pattern for the remaining AP enable-style setter families
  - `D073` is now a committed 0310/AP-only multiband `To be tested` case; reuse its `IEEE80211r.Enabled=1` + `MobilityDomain=4660` prerequisite pattern plus `FTOverDSEnable` / hostapd `ft_over_ds` `0 -> 1 -> 0` convergence and decimal-vs-hex MobilityDomain cross-check for the remaining 11r AccessPoint setter families
  - `D074` is now a committed 0310/AP-only multiband `To be tested` case; reuse its `IEEE80211r.Enabled=1` prerequisite plus `MobilityDomain=27476` decimal readback and hostapd byte-swapped hex `546B` cross-check for the remaining 11r AccessPoint setter families
  - `D077` is now a committed 0310/AP-only multiband `To be tested` case; reuse its IEEE80211u `InterworkingEnable` getter `0 -> 1 -> 0` plus hostapd two-line `interworking` count convergence `0/2/2 -> 1/1/2 -> 0/2/2` for the remaining IEEE80211u AccessPoint setter families
  - `D078` is now a committed 0310/AP-only multiband `Not Supported` case; reuse its `QoSMapSet EMPTY -> 255 -> EMPTY` northbound collapse plus hostapd `ABSENT -> qos_map_set=255 -> ABSENT` pattern for the remaining IEEE80211u AccessPoint setter families that may be implemented fail-shaped rather than pass-shaped
  - `D079` is now a committed 0310/AP-only multiband pass case; reuse its `MACFiltering.addEntry(mac=...)` / `MACFiltering.delEntry(mac=...)` flow, plus the bounded `sleep 2` northbound getter convergence and same-band `MACFiltering.Entry` tree cross-check, as the immediate prior art for the remaining MAC filtering AccessPoint family
- Critical lab rule:
  - `COM1` is another `prplOS` / B0-class board, not a simple STA dongle
  - before using `ping 192.168.1.1` as DUT reachability evidence, move `COM1 br-lan` off `192.168.1.0/24` (for example `192.168.88.1/24`), otherwise the ping is a false-positive self-hit
- Current 5G recovery status:
  - `COM1 wl0` now reconnects to DUT AP1 `2c:59:17:00:19:95` with SSID `testpilot5G`
  - `wpa_cli` reaches `wpa_state=COMPLETED` with `key_mgmt=WPA2-PSK`
  - DUT `wl -i wl0 assoclist` and `WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?` both confirm the same STA `2C:59:17:00:04:85`
- Proven 6G baseline flow:
  - 6G baseline policy is now fixed to `testpilot6G` + `WPA3-Personal` + `key_mgmt=SAE` + password `00000000`
  - DUT readback and `hostapd_cli -i wl1 get_config` both confirm the non-open WPA3/SAE configuration
  - COM1 `wl1` revalidation against the new `00000000` credential is still pending; keep the older DHCP/routed-ping evidence as historical context only
- 5G and 2.4G current state:
  - 5G `wl0` L2 association is re-verified on the rebuilt `testpilot5G` baseline
  - 2.4G `wl2` baseline config (`testpilot2G` + `WPA2-Personal/00000000`) is re-applied on the DUT, but COM1 `wl2` association has not been rerun after this reboot/recovery step
  - DHCP/routing is not yet applied automatically on these bands, so any traffic-dependent case still needs explicit L3 setup or a blocker note
- First live-aligned `AssociatedDevice` getter cases now rewritten against the verified 6G baseline:
  - `D011` `AssociationTime`
  - `D012` `AuthenticationState`
  - `D018` `DownlinkBandwidth`
  - `D021` `EncryptionMode`
  - `D029` `MACAddress`
  - all five now point at workbook `0310-BGW720-300_LLAPI_Test_Report.xlsx`
  - all five use getter-only validation instead of writing sample values into read-only LLAPIs
  - `D029` now compares the DUT readback against live COM1 + `wl1 assoclist` identity using `reference`-based criteria
- Second live-aligned `AssociatedDevice` subset now rewritten against the verified 5G WPA3 baseline:
  - `D013` `AvgSignalStrength` (`Fail` is the expected workbook verdict; LLAPI stays `0` while driver RSSI is live)
  - `D017` `ConnectionDuration`
  - `D019` `DownlinkMCS`
  - `D019` is now explicitly tied to driver `tx nrate` (`AP -> STA`) instead of the stale workbook sample output
- Third live-aligned `AssociatedDevice` subset now rewritten against the verified 5G WPA3 baseline after a multi-agent survey pass:
  - `D023` `HeCapabilities`
  - `D024` `HtCapabilities`
  - `D026` `LastDataDownlinkRate`
  - `D027` `LastDataUplinkRate`
  - `D028` `LinkBandwidth`
  - `D026` / `D027` normalize the driver last-packet rate to 100-kbps granularity before comparing it with LLAPI
- First live-aligned `WiFi.SSID.{i}.Stats.` subset now rewritten against the verified 5G WPA3 baseline after a multi-agent survey + serialwrap validation pass:
  - `D323` `BroadcastPacketsReceived`
  - `D324` `BroadcastPacketsSent`
  - `D325` `BytesReceived`
  - `D326` `BytesSent`
  - `D332` `MulticastPacketsReceived`
  - `D333` `MulticastPacketsSent`
  - `D334` `PacketsReceived`
  - `D335` `PacketsSent`
  - `D337` `UnicastPacketsReceived`
  - `D338` `UnicastPacketsSent`
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
  - mirrored `getSSIDStats()` rows `D302-D318`
  - direct rows with workbook-open verdicts: `D327-D331`, `D336`, `D339`, `D408`, `D409`
  - direct workbook `Not Supported`: `D497`
  - SSID-level WMM rows `D498-D529`
  - all 69 SSID-level stats cases now use the same sequential single-link band flow and remove stale `wifi-llapi-rXXX-*` aliases
  - direct/getSSIDStats()/driver equality is encoded explicitly for the metric families that have a verified `/proc/net/dev_extstats` mapping
  - retry / failed-retrans / unknown-proto counters keep workbook-gated `To be tested` / `Not Supported` semantics instead of being forced into pass-style criteria
  - SSID-level WMM fields stay `0` on 5G/6G/2.4G while radio-level alternatives remain available via `wl -i wlX wme_counters`
  - the 2.4G leg keeps the STA traffic attempt in the recipe even when ping still drops; final judgment uses the DUT-side counter reread consistency
- Workbook-gated blocker from the same batch:
- `D016` `ChargeableUserId` remains open because workbook `v4.0.3` is still `To be tested/To be tested/To be tested` and BCM comments say the current project lacks Radius method support
- Multi-agent survey blockers from the same 10-case 5G batch:
  - `D014` `AvgSignalStrengthByChain`
  - `D015` `Capabilities`
  - `D020` `DownlinkShortGuard`
  - `D022` `FrequencyCapabilities`
  - `D025` `Inactive`
- Latest single-case checkpoints after the 5G counter family follow-up:
  - `D056` `TxErrors`
    - same-STA direct getter + AssociatedDevice snapshot + `wl sta_info tx failures` equality
    - workbook verdict remains `To be tested`
  - `D057` `TxMulticastPacketCount`
    - DUT broadcast probe increases COM1 `wl0` RX packets/bytes, but both LLAPI and driver `tx mcast/bcast` counters remain `0`
    - workbook verdict remains `To be tested`
  - `D059` `TxUnicastPacketCount`
    - LLAPI direct getter and AssociatedDevice snapshot stay `0`
    - same STA still reports positive sibling `TxPacketCount` and positive driver `tx ucast pkts`
    - workbook verdict is now encoded as `Fail`
  - `D185` `TPCMode`
    - WLD ODL enum declares `Auto/Off/Ap/Sta/ApSta`
    - live DUT rejects `Off`, accepts `Ap/Sta/ApSta` through ubus readback, and still keeps `wl0 tpc_mode=0`
    - this targeted source/live checkpoint is recorded as a fail-shaped mismatch; primary sweep counts remain unchanged until the workbook verdict ledger is reconciled

## Per-case operator loop

For every individual case, use this exact loop:

1. Identify the workbook row and the matching YAML case file.
2. Write down the expected result for 5G / 6G / 2.4G from `L/M/N`.
3. Clean workbook `F/G` into an executable manual flow.
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
- [ ] Executable manual serialwrap procedure is normalized from workbook `F/G`.
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

- [ ] `CAL-101` Clean workbook `F/G` into executable manual commands.
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
  - the first verified 6G getter-only subset is aligned: `D011`, `D012`, `D018`, `D021`, `D029`
  - the second verified 5G subset is aligned: `D013`, `D017`, `D019`
  - the third verified 5G subset is aligned: `D023`, `D024`, `D026`, `D027`, `D028`
  - regression guards were added for these patterns in `tests/test_wifi_llapi_plugin_runtime.py`
  - `D021` workbook `v4.0.3` expectation is confirmed as `Pass/Pass/Pass`; the older YAML `To be tested` reference was stale
  - `D016` remains blocker-only because workbook `v4.0.3` is still `To be tested` and the current lab has no Radius-backed path to validate `ChargeableUserId`
  - `D014`, `D015`, `D020`, `D022`, and `D025` remain blocker-only after live + source cross-check and were intentionally not rewritten
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
  - the first verified `WiFi.SSID.{i}.Stats.` 5G subset is aligned: `D323`, `D324`, `D325`, `D326`, `D332`, `D333`, `D334`, `D335`, `D337`, `D338`
  - all ten now point at workbook `0310-BGW720-300_LLAPI_Test_Report.xlsx` with real workbook rows `245/246/247/248/254/255/256/257/259/260`
  - all ten were converted from stale sample-value / `=0` pseudo-tests into getter-only equality checks between:
    - `WiFi.SSID.4.Stats.<Field>?`
    - `WiFi.SSID.4.getSSIDStats()`
    - `/proc/net/dev_extstats` `wl0`
  - aligned SSID stats YAML no longer retains `wifi-llapi-rXXX-*` aliases; workbook row identity now lives only in `source.row`
  - regression guards were added for this subset in `tests/test_wifi_llapi_plugin_runtime.py`
  - the remaining mirrored SSID stats rows are also now aligned to the multiband sequential recipe:
    - `getSSIDStats()` `Pass`: `D302-D309`, `D311-D314`, `D316-D317`
    - direct workbook-open (`To be tested`): `D327-D331`, `D336`, `D339`, `D408`, `D409`
    - direct / `getSSIDStats()` workbook `Not Supported`: `D310`, `D315`, `D318`, `D497`
    - SSID-level WMM workbook `Not Supported`: `D498-D529`
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
