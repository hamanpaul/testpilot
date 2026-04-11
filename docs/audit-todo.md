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

## Latest repo handoff snapshot（2026-04-11）

- Current detached full-run compare baseline: `20260411T074146043202`
- Recomputed compare with the current local YAML overlay now sits at:
  - `220 / 420 full matches`
  - `200 mismatches`
  - `67 metadata drifts`
- Interpreted via `evaluation_verdict` rather than stale synthesized per-band `results_reference`, the remaining workbook-Pass gaps are:
  - `77` total workbook-Pass gaps
  - `12` patch-scope true-open cases in the current repo inventory: `D281-D287`, `D290`, `D295`, `D324`, `D331`, `D333`
  - this detached compare snapshot is still pre-`D330` rewrite evidence; the local repo state below is newer than the detached run results
- Latest aligned spectrum follow-up:
  - `D532 getSpectrumInfo ourUsage` rerun `20260411T183356920330` = `Pass`
  - `D533 getSpectrumInfo availability` rerun `20260411T183405281629` = `Pass`
  - both cases are now being carried as plain `Pass/Pass/Pass` instead of the stale fail-shaped workbook carry-over
- Latest aligned direct-stats follow-up:
  - `D330 MulticastPacketsReceived` isolated rerun `20260411T191809490680` now closes the active 0403 source-backed formula `max((rxmulti + matching wds_rxmulti) - BroadcastPacketsReceived, 0)` on 5G / 6G / 2.4G
  - attempt 1 failed at the temp-script layer with `/tmp/_tp_cmd.sh: line 2: syntax error: unterminated quoted string`, but attempt 2 exact-closed `direct / getSSIDStats / driver-formula = 0 / 0 / 0` on all three bands
  - the case YAML is now refreshed from stale row `254` to workbook row `330`
  - `D332 PacketsReceived` stale workbook replay `20260411T194312398713` re-proved both `/proc/net/dev_extstats` `$3` drift (`5G 2234/2237` vs direct `2000/2002`) and loose `getSSIDStats()` overmatch (`expected=0`)
  - after refreshing the case to workbook row `332`, anchoring the `getSSIDStats()` extraction, and switching the driver oracle to `wl if_counters rxframe + matching wds rxframe`, rerun `20260411T194647490016` passed in one attempt
  - `D335 UnicastPacketsReceived` stale workbook replay `20260411T200329824574` re-proved `/proc/net/dev_extstats` `$21` drift on all three bands (`5G 2001/746`, `6G 788/391`, `2.4G 483/235` across direct/getSSIDStats vs proc)
  - active 0403 source explicitly derives `UnicastPacketsReceived = PacketsReceived - MulticastPacketsReceived` in `whm_brcm_api_ext.c`, then copies/accumulates that field in `whm_brcm_vap.c`; after switching the case to `(wl if_counters rxframe + matching wds rxframe) - (wl if_counters rxmulti + matching wds rxmulti)`, rerun `20260411T200851584762` exact-closed on 5G / 6G / 2.4G as `2003/2003/2003`, `794/794/794`, and `483/483/483`
- Latest reopened runtime blocker:
  - `D295 scan()` is now formalized in `plugins/wifi_llapi/reports/D295_block.md`
  - committed DUT-only topology can fall back to `WiFi.Radio.{1,2,3}.Status="Dormant"` and then `scan()/startScan()` return `status 1 - unknown error`
  - local `STA + links` topology experiment rerun `20260411T185559873987` only moved the failure deeper into `verify_env` / 6G OCV restart and still produced no step output
- Latest reopened direct-stats blocker:
  - `D324 BytesSent` is now formalized in `plugins/wifi_llapi/reports/D324_block.md`
  - isolated rerun `20260411T190338070996` re-proved `direct == getSSIDStats()` but invalidated base `wlX if_counters txbyte` as a durable all-band oracle
  - source trace now points at `whm_brcm_vap_update_ap_stats()` merging matching `wds*` peer stats into public `BytesSent`
- Latest new direct-stats blocker:
  - `D331 MulticastPacketsSent` is now formalized in `plugins/wifi_llapi/reports/D331_block.md`
  - trial reruns `20260411T192138186700` and `20260411T192524301950` both rejected the stale workbook `/proc/net/dev_extstats` `$18` path, but 5G still stayed at a fixed `driver = direct + 4` drift (`259962 / 259966`, `260097 / 260101`, then `260377 / 260381`, `260613 / 260617`)
  - the superseding official rerun `20260411T234124237416` then proved the rewrite is still not durable in the real runner path: 5G drift widened to `286001 / 286006` and then `286140 / 286192`, while 6G/2.4G only exact-closed on the second attempt
  - focused DUT-only probes still exact-close the same formula outside the runner, so the local rewrite was rolled back and `D331` remains blocked until a runner-stable oracle exists
  - `D333 PacketsSent` is now formalized in `plugins/wifi_llapi/reports/D333_block.md`
  - stale replay `20260411T194816992700` re-proved both the loose `getSSIDStats()` overmatch (`26411/26413`) and the non-authoritative workbook `/proc/net/dev_extstats` `$11` path
  - source-backed trial rerun `20260411T195140855058` exact-closed 6G/2.4G, but 5G still held a fixed `driver = direct + 5` drift (`293527 / 293532`, `293669 / 293674`)
  - the superseding official rerun `20260411T235643720137` then re-proved that same runner-path `+5` on 5G (`319230 / 319235 / 319235`, `319376 / 319376 / 319381`), while focused DUT-only probes still exact-closed outside the runner, so the local rewrite was rolled back and the blocker stands
  - `D336 UnicastPacketsSent` is now aligned, while `plugins/wifi_llapi/reports/D336_block.md` is kept as historical trial evidence
  - stale replay `20260411T201639103833` re-proved workbook `/proc/net/dev_extstats` `$22` as an all-band zero-shaped stale oracle (`26434/0`, `21540/0`, `10563/0`)
  - the resolving official rerun `20260412T000744842751` passed after switching the driver oracle to the unsigned 0403 formula `((txframe + matching wds txframe) - (d11_txmulti + matching wds d11_txmulti)) & 0xffffffff`: attempt 1 still drifted on 6G by `+1` (`24709 / 24710 / 24710`), but attempt 2 exact-closed 5G/6G/2.4G (`27172/27172/27172`, `24703/24703/24703`, `17117/17117/17117`)
- Latest aligned scan-results follow-up:
  - `D277 getScanResults() Bandwidth` isolated rerun `20260411T205454026707` is now authoritative and no longer blocked
  - pre-reducing `getScanResults()` to the first scan object removed the old 6G full-payload broker recovery path, so the case now completes with `diagnostic_status=Pass`
  - the new same-target replay closes against `wl escanresults` Chanspec bandwidth on 5G / 6G / 2.4G as `80/80`, `320/160`, and `20/20`, so the committed case now carries a source-backed `Pass / Fail / Pass` verdict shape at workbook row `277`
  - `D281 getScanResults() Noise` remains blocked, but the blocker is now narrowed to the active 0403 authority model rather than a missing parser. Parser-fix trial `20260411T211133728869` still failed locally because the same-target `wl` block was not captured, while sanitized rerun `20260411T211327344984` showed the real shape: 5G exact-close (`-100/-100`), 6G repeatable drift (`-97/-102`, then `-97/-103`), and 2.4G non-durable drift (`-78/-76`, then `-78/-78`)
  - the superseding source trace shows public `getScanResults().Noise` is copied from `lastScanResults` after `s_updateScanResultsWithSpectrumInfo()` back-fills per-channel `noiselevel`, so direct `wl escanresults` `noise:` is not the authoritative 0403 oracle for this row. Because public `getSpectrumInfo()` is still empty in the current lab state, the committed YAML stays unchanged at stale row `283`; see `plugins/wifi_llapi/reports/D281_block.md`
  - `D282 getScanResults() OperatingStandards` also remains blocked, but the active public path is now narrowed correctly. Current 0403 source trace shows the ubus getter uses nl80211 scan results parsed from beacon/probe IEs, copies `pWirelessDevIE->operatingStandards` into `wld_scanResultSSID_t.operatingStandards`, caches that in `lastScanResults`, and serializes it with `swl_radStd_toChar(..., SWL_RADSTD_FORMAT_STANDARD, 0)` rather than relying on legacy `_wldm_get_standards()`
  - the existing isolated rerun `20260410T163026194231` therefore remains blocked for a more precise reason: 5G exact-closes, 6G still has no same-target external replay block, and 2.4G still drifts to an extra external `be` (`b,g,n,ax` vs `b,g,n,ax,be`), which looks more like a supported/capability-family replay than a same-source replay of the active public `OperatingStandards` bitmask. The committed YAML stays unchanged at stale row `284`; see `plugins/wifi_llapi/reports/D282_block.md`
  - `D283 getScanResults() RSSI` and `D286 getScanResults() SignalStrength` are now treated as the same active public `ssid->rssi` field family. Fresh isolated rerun `20260411T214050136894` proved the committed D283 generic case still hangs after `setup_env` (no step output, no report files, empty `agent_trace/20260411T214050136894/`, and `COM0` falling into a recoverable `TARGET_UNRESPONSIVE` state), while new source tracing shows both public fields are exported from the same `ssid->rssi` value on the active nl80211/wld path
  - `D286_block.md` is now corrected to that same source model, but its existing live replay evidence still stays blocked (`5G -64/-65`, missing 6G same-target replay, 2.4G `-46` vs `-55/-56` / raw `-54`). So D283 remains blocked on the committed full-payload transport shape, D286 remains blocked on the shared semantic replay gap, and the next resume pointer moves to `D287`
  - `D287 getScanResults() SSID` also remains blocked, but the authority model is now corrected. Active 0403 public `SSID` is carried in the parsed scan-result model (`pWirelessDevIE->ssid` -> `wld_scanResultSSID_t.ssid` -> `wld_rad_scan.c` public `SSID`) rather than being treated as a pure raw `SSID:` helper field
  - the existing isolated rerun `20260410T182739821870` therefore stays blocked for a narrower reason: 5G and 2.4G exact-close on the same target BSSID, but 6G still exposes `3a:06:e6:2b:a3:1a` / `.ROAMTEST_RSNO_P10P_1` on LLAPI while both `iw` and direct raw `wl -i wl1 escanresults` fail to replay that same target. The committed YAML stays unchanged at stale row `289`; see `plugins/wifi_llapi/reports/D287_block.md`
  - `D290 getScanResults() CentreChannel` is now aligned and no longer blocked. The old blocker only lacked the right same-target replay path: after one-shot environment repair (`wifi-llapi baseline-qualify --repeat-count 1 --soak-minutes 0`), fresh isolated rerun `20260411T220324862766` closed same-target raw `wl escanresults` Chanspec replay on all three bands
  - the committed case now carries a source-backed `Pass / Fail / Pass` shape at workbook row `290`: 5G exact-closes `42/42`, 2.4G exact-closes `1/1`, and 6G is locked as the same-target fail-shaped mismatch `LlapiCentreChannel6g=31` vs `WlCentreChannel6g=15` on BSSID `6e:15:db:9e:33:72`
  - `D529 getSpectrumInfo channel` is now aligned. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "channel", llEntry->channel)`, and fresh isolated rerun `20260411T221613327385` plus repeated direct probes now lock the first serialized spectrum-entry channels at `36 / 2 / 1` on `5g / 6g / 2.4g`
  - the committed case now fixes the template metadata shape (`object=WiFi.Radio.{i}.`, `api=getSpectrumInfo()`), replaces the old generic numeric regex with explicit first-entry channel extractors, keeps workbook row `529`, and remains plain `Pass / Pass / Pass`
  - `D530 getSpectrumInfo noiselevel` is now aligned, but it stays a dynamic numeric case rather than a fixed-value case. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(int32_t, "noiselevel", llEntry->noiselevel)`, so the field is a survey-driven live reading
  - the first exact-value trial was rejected after 2.4G drifted across retries/reruns (`-75 / -77 / -78`), so the committed case only fixes the template metadata shape (`object=WiFi.Radio.{i}.`, `api=getSpectrumInfo()`), preserves the source-correct numeric regex pass shape, and is green-locked by isolated rerun `20260411T222349217612`
  - `D531 getSpectrumInfo accesspoints` is now aligned, and it follows the same metadata-only dynamic numeric pattern. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "accesspoints", llEntry->nrCoChannelAP)`, so the field is a survey-driven co-channel AP count rather than a fixed constant
  - the committed case therefore only fixes the template metadata shape (`object=WiFi.Radio.{i}.`, `api=getSpectrumInfo()`), preserves the source-correct numeric regex pass shape, and is green-locked by isolated rerun `20260411T223140870454`
  - `D532 getSpectrumInfo ourUsage` is now aligned, and it follows the same metadata-only dynamic numeric pattern. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "ourUsage", llEntry->ourUsage)`, while `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives the live percentage from survey airtime (`ourTime / total_time`)
  - isolated rerun `20260411T223658523608` passed cleanly with the generic numeric verdict shape. That rerun also triggered a workbook re-check: `0401.xlsx` confirms the whole spectrum batch had stale `source.row` drift, so `D528-D533` are now corrected to the actual workbook rows `528-533` instead of the old `530-535` carry-over
  - `D533 getSpectrumInfo availability` is now aligned as the last metadata-only dynamic numeric case in this batch. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "availability", llEntry->availability)`, while `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives the live percentage from survey idle/free-time timing; isolated rerun `20260411T224035464927` passed cleanly with the generic numeric verdict shape
  - `D322 BroadcastPacketsSent` is now aligned. The earlier blocker shape turned out to be runner timing, not stale authority: official rerun `20260412T002445088386` kept the workbook `/proc $24` oracle but added a short post-`verify_env` settle (`sleep 2`), after which attempt 2 exact-closed all three bands (`4596/4596/4596`, `4772/4772/4772`, `5121/5121/5121`). The committed metadata is now refreshed from stale row `246` to workbook row `322`, and `plugins/wifi_llapi/reports/D322_block.md` is retained only as historical trial evidence
  - `D323 BytesReceived` is now aligned. The earlier blocker turned out to be a stale workbook `/proc/net/dev_extstats` `$2` heuristic plus an incorrect source explanation: corrected 0403 tracing now shows `whm_brcm_get_if_stats()` seeds `BytesReceived` from `wl if_counters rxbyte`, `whm_brcm_vap_ap_stats_accu()` adds matching `wds*` `rxbyte`, and `whm_brcm_vap_update_ap_stats()` does not restore `BytesReceived` from `tmp_stats`. After rewriting the case to that source-backed oracle, official rerun `20260411T231952006453` exact-closed 5G/6G/2.4G at `276282/276282/276282`, `122610/122610/122610`, and `73193/73193/73193`; the committed metadata is now refreshed from stale row `247` to workbook row `323`, and `plugins/wifi_llapi/reports/D323_block.md` is retained as historical resolution notes
- Practical next resume order:
  1. resume the remaining unresolved queue from `D331`, `D333`
  2. keep `D331` / `D333` blocked unless their drifts are explained with deterministic source-backed corrections
  3. revisit `D281-D287` only if new same-source external replay evidence appears

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
  - formerly workbook-open direct rows now aligned: `D325-D329`, `D334`, `D337`, `D406`, `D407`
  - remaining direct workbook-open rows: none
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
  - the third verified 5G subset is currently aligned only for `D021`, `D022`
  - offline survey confirms `0401.xlsx` row drift for `D024` / `D025` / `D026` (`24` / `25` / `26` in workbook vs `21` / `22` / `23` in current YAML metadata), so these three remain pending the next live rewrite instead of being counted as aligned
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
  - added official-case `>120` char command inventory guardrail; current tracked inventory = `612`
  - re-ran full suite again after the offline-survey regression guard (`1601 passed`)
  - attempted fresh live full-run preflight, but serialwrap daemon reported `0` devices / `0` sessions and the environment exposed no `/dev/ttyUSB*` or `/dev/serial/by-id`, so live Phase 3 is blocked pending DUT/STA UART return
- Progress record:
  - latest aligned case: `D276 getRadioStats() UnicastPacketsSent` via run `20260410T125445239119`
  - latest blocked case: `D277 getScanResults() Bandwidth`
  - latest compare summary: `264 / 420` full matches, `156` mismatches (still the last rebuilt compare snapshot; not yet recomputed after the post-summary D111 rerun)
  - latest stable fail-shaped mismatches: `D011`, `D013`, `D020`
  - latest parser-backed fix: workbook replay on live DUT/STA proved `D111` already returns `AssociationTime = "YYYY-MM-DDTHH:MM:SSZ",`; the full-run fail shape came from `plugins/wifi_llapi/plugin.py::_extract_key_values()` stripping quotes before trailing commas, leaving a spurious tail `"` in `stats_output.AssociationTime`
  - latest regression after the D272-D276 row refresh: targeted method-stats tests `132 passed`; full `plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py` now `1223 passed`
  - latest D211 live replay verdict: workbook row `211` BE/AX getters both followed setter, but AX phase still kept `wl0/wl1/wl2 eht features=127`; 6G `/tmp/wl1_hapd.conf` also kept secondary `ieee80211be=1` after `OperatingStandards=ax`
  - latest D211 source-backed triage: getter/setter authority includes `{nvifname}_oper_stands`, but the hostapd MLO path still injects `ieee80211be=1`; 0315 and 0403 copies of `whm_brcm_conf_map.c` / `whm_brcm_rad_mlo.c` are unchanged for this behavior
  - D211 remains blocked/fail-shaped; details recorded in `plugins/wifi_llapi/reports/D211_block.md`
  - latest D262 source-backed revalidation: `_getRadioAirStats()` returns `amxd_status_ok` early when `wld_rad_isActive(pR)` is false, so the first raw replay only showed 6G `[""]` while `WiFi.Radio.2.Status="Down"`; after `wifi-llapi baseline-qualify --band 6g --repeat-count 1 --soak-minutes 0` restored all three radios to `Status="Up"`, D262 rerun `20260410T115313185471` became plain `Pass`
  - D262 YAML row drift is now refreshed from `264` to workbook row `262`
  - latest D263 source-backed revalidation: workbook row `263` still shows a stale sample `BroadcastPacketsReceived = 0`, but 0403 patch note `17) Radio.Stats, SSID.Stats issues` explicitly says radio counters were reworked to use dev_ext bcast/mcast data; live rerun `20260410T115954628992` returned numeric `BroadcastPacketsReceived = 363 / 142 / 113` on 5G / 6G / 2.4G, matching the current regex-based counter-field validation instead of the old sample-zero illustration
  - D263 YAML row drift is now refreshed from `265` to workbook row `263`
  - latest D264 source-backed revalidation: workbook row `264` still shows a stale sample `BroadcastPacketsSent = 0`, but it is covered by the same 0403 `Radio.Stats, SSID.Stats issues` rework; live rerun `20260410T120300247819` returned numeric `BroadcastPacketsSent = 921 / 1080 / 1168` on 5G / 6G / 2.4G, so the current regex-based counter-field validation remains aligned with 0403 semantics
  - D264 YAML row drift is now refreshed from `266` to workbook row `264`
  - latest D265 source-backed revalidation: workbook row `265` still describes a `/proc/net/dev` cross-check heuristic, but 0403 reactivated `BytesReceived` from driver `if_counters.rxbyte` in `whm_brcm_api_ext.c`; live rerun `20260410T120916047799` returned numeric `BytesReceived` on all three radios, so the current regex-based numeric validation stays aligned with 0403 semantics while the old `/proc/net/dev` note is no longer the authoritative oracle
  - D265 YAML row drift is now refreshed from `267` to workbook row `265`
  - latest D266 source-backed revalidation: 0403 `whm_brcm_rad.c` ultimately refreshes radio `BytesSent` through `whm_brcm_rad_get_counters_fromfile()` and parses driver `wl ... counters` `txbyte`; live compare showed 5G/2.4G API values matched driver `wl counters txbyte`, while 6G happened to line up with `/proc/net/dev` `TX_byte` instead of `wl1 counters`, proving the workbook `/proc/net/dev` heuristic is not a stable oracle on 0403 even though the case still returns valid numeric counter values
  - D266 YAML row drift is now refreshed from `268` to workbook row `266`
  - latest D267 source-backed revalidation: workbook row `267` still asks for API-to-`/proc/net/dev` `RX_drop-pkg` minimal discrepancy, but live compare showed `DiscardPacketsReceived` returned `0 / 3752 / 0` on 5G / 6G / 2.4G while `/proc/net/dev` returned `565 / 3752 / 356` and driver `wl ... counters` `rxdropped` stayed `0 / 0 / 0`; together with the 0403 source flow (`ifstats->rxdiscard` first, `whm_brcm_rad_get_counters_fromfile()` overwrite attempt later), that proves `/proc/net/dev` is not a stable three-band oracle for this field on 0403, so the current numeric validation remains the correct semantic
  - D267 YAML row drift is now refreshed from `269` to workbook row `267`
  - latest D268 source-backed revalidation: workbook row `268` still asks for API-to-`/proc/net/dev` `TX_drop-pkg` minimal discrepancy, but live compare showed `DiscardPacketsSent` returned `0 / 3469 / 0` on 5G / 6G / 2.4G while `/proc/net/dev` returned `184 / 3467 / 87` and driver `wl ... counters` `txdropped` stayed `0 / 0 / 0`; together with the 0403 source flow (`ifstats->txdiscard` first, `whm_brcm_rad_get_counters_fromfile()` overwrite attempt later), that proves `/proc/net/dev` is not a stable three-band oracle for this field on 0403 either, so the current numeric validation remains the correct semantic
  - D268 YAML row drift is now refreshed from `270` to workbook row `268`
  - latest D269 source-backed revalidation: workbook row `269` still records `ErrorsReceived = 0 / 0 / 0` and points to `/proc/net/dev` `RX_Error-pkg`, but live compare showed API `ErrorsReceived = 8 / 0 / 8`, `/proc/net/dev = 0 / 0 / 0`, and driver `wl ... counters` `rxerror = 8 / 8 / 8` on 5G / 6G / 2.4G; together with the 0403 source flow (`ifstats->rxerror` first, `whm_brcm_rad_get_counters_fromfile()` overwrite attempt later), that proves workbook zero/proc evidence is not a stable three-band oracle for this field either, so the current numeric validation remains the correct semantic
  - D269 YAML row drift is now refreshed from `271` to workbook row `269`
  - latest D270 source-backed revalidation: workbook row `270` still records `ErrorsSent = 0 / 0 / 0` and points to `/proc/net/dev` `TX_Error-pkg`; live compare matched that cleanly on 0403 with API `ErrorsSent = 0 / 0 / 0`, `/proc/net/dev = 0 / 0 / 0`, and driver `wl ... counters` `txerror = 0 / 0 / 0`, so this case reduces to row drift only and the current numeric validation remains aligned with workbook/source semantics
  - D270 YAML row drift is now refreshed from `272` to workbook row `270`
  - latest D271 source-backed revalidation: workbook row `271` still points to `/proc/net/dev` `RX_multipkg`, but live compare showed `MulticastPacketsReceived` returned `0 / 142 / 0` on 5G / 6G / 2.4G while `/proc/net/dev` returned `363 / 142 / 113` and driver `wl ... counters` `d11_rxmulti` returned `10 / 0 / 0`; together with the 0403 source flow (`ifstats->rxmulti` first, `whm_brcm_rad_get_counters_fromfile()` overwrite, then broadcast subtraction merge), that proves workbook proc evidence is not a stable three-band oracle for this field either, so the current numeric validation remains the correct semantic
  - D271 YAML row drift is now refreshed from `273` to workbook row `271`
  - latest D272 source-backed revalidation: workbook row `272` still points to `/proc/net/dev_extstats` `TX_multipkg`, but live compare showed `MulticastPacketsSent` returned `89594 / 91022 / 92958` on 5G / 6G / 2.4G while `dev_extstats` returned `7260 / 2880 / 2260` and driver `wl ... counters` `d11_txmulti` returned `90551 / 28627 / 94162`; together with the 0403 TX-side source flow (`txframe` first, `d11_txmulti/d11_txbcast` overwrite next, then broadcast subtraction merge), that proves the old `dev_extstats` heuristic is not a stable three-band oracle either, so the current numeric validation remains the correct semantic
  - D272 YAML row drift is now refreshed from `274` to workbook row `272`
  - latest D273 source-backed revalidation: workbook row `273` still points to `/proc/net/dev` `RX_pkg`, but live compare showed `PacketsReceived` returned `935 / 432 / 220` on 5G / 6G / 2.4G while `/proc/net/dev` returned `1086 / 432 / 333` and driver `wl ... counters` `rxframe` returned `935 / 288 / 220`; that proves `/proc/net/dev` is not a stable three-band oracle for this field on 0403, so the current numeric validation remains the correct semantic
  - D273 YAML row drift is now refreshed from `275` to workbook row `273`
  - latest D274 source-backed revalidation: workbook row `274` still points to `/proc/net/dev` `TX_pkg`, but live compare showed `PacketsSent` returned `125099 / 92000 / 109840` on 5G / 6G / 2.4G while `/proc/net/dev` returned `97904 / 92000 / 97690` and driver `wl ... counters` `txframe` returned `125099 / 53906 / 109840`; together with the 0403 TX-side source flow (`txframe` first, `d11_txmulti/d11_txbcast` overwrite next), that proves `/proc/net/dev` is not a stable three-band oracle for this field either, so the current numeric validation remains the correct semantic
  - D274 YAML row drift is now refreshed from `276` to workbook row `274`
  - latest D275 source-backed revalidation: workbook row `275` still carries the older proc/sample-zero heuristic for `UnicastPacketsReceived`, but live compare showed API `926 / 0 / 220` while driver `wl ... counters` returned `rxframe = 936 / 288 / 220` and `d11_rxmulti = 10 / 0 / 0`; 5G/2.4G line up with the derived `rxframe - d11_rxmulti` shape, while 6G still collapses to zero, so the workbook proc/zero heuristic is not a stable 0403 oracle and the current numeric validation remains the correct semantic
  - D275 YAML row drift is now refreshed from `277` to workbook row `275`
  - latest D276 source-backed revalidation: workbook row `276` still carries the older proc/sample-zero heuristic for `UnicastPacketsSent`, but live compare showed API `34089 / 0 / 14988` while driver `wl ... counters` returned `txframe = 125177 / 53985 / 109891` and `d11_txmulti = 91088 / 29256 / 94903`; 5G/2.4G line up with the derived `txframe - d11_txmulti` shape, while 6G still collapses to zero, so the workbook proc/zero heuristic is not a stable 0403 oracle and the current numeric validation remains the correct semantic
  - D276 YAML row drift is now refreshed from `278` to workbook row `276`
  - latest D277 blocker: workbook row `277` is a BSSID-targeted scan-compare case. The initial DUT gate issue was recoverable, and the earlier direct probes did narrow the shape to raw 5G/6G full scan capture, but the new repo-side scan timeout fallback still did not produce an authoritative isolated replay: WAL evidence showed the rerun reached raw `WiFi.Radio.2.getScanResults()`, then serialwrap recovery injected `^C`, DUT printed `Please press Enter to activate this console.`, and `COM0` fell back to `ATTACHED / PROMPT_TIMEOUT` until manual recovery returned it to `READY`; this is therefore still a transport-side scan-capture blocker rather than a proven scan semantic mismatch
  - D277 remains unmodified (`source.row=279` still stale) until a clean isolated replay can compare workbook row `277`'s target BSSID against live `iw dev wlX scan`; details recorded in `plugins/wifi_llapi/reports/D277_block.md`
  - latest D278 alignment: workbook row `278` reran plain `Pass` at `20260410T135946424063` after rewriting the case to a workbook-style BSSID compare. The new live path first captures the target BSSID from each LLAPI scan result, then cross-checks the same target against `iw dev wl0/wl1/wl2 scan`; all three bands matched authoritatively (`38:88:71:2f:f6:a7` on 5G, `3a:06:e6:2b:a3:1a` on 6G, `8c:19:b5:6e:85:e1` on 2.4G)
  - D278 YAML row drift is now refreshed from `280` to workbook row `278`
  - latest D279 alignment: workbook row `279` reran plain `Pass` at `20260410T140714322443` after converting the case to a workbook-style target BSSID + `iw freq -> channel` compare. The first live attempt exposed that a loose `/Channel = /` parser was accidentally reading `CentreChannel`; after tightening the LLAPI parse to the real `Channel =` line, the isolated rerun matched authoritatively on all three bands (`36/36` on 5G, `5/5` on 6G, `1/1` on 2.4G)
  - D279 YAML row drift is now refreshed from `281` to workbook row `279`
  - latest D280 alignment: workbook row `280` reran plain `Pass` at `20260410T143122662554` after converting the case to a workbook-style first-WPA-target compare. 0403 source still constrains neighboring WiFi `EncryptionMode` to `TKIP / AES / TKIPandAES / None` (`wlcsm_lib_api.h`, `wlcsm_lib_wl.c`, `wldm_lib_wifi.c`), but the live getter continues to emit `Default`; the isolated rerun now locks that fail-shaped mismatch authoritatively on all three bands against the same-target `iw dev wl0/wl1/wl2 scan` cipher evidence (`38:88:71:2f:f6:a7` / `3a:06:e6:2b:a3:1a` / `8c:19:b5:6e:85:e1`, all `Pairwise ciphers: CCMP` -> normalized `AES`, while LLAPI stays `Default`)
  - D280 YAML row drift is now refreshed from `282` to workbook row `280`
  - latest D281 blocker: the old direct-`wl escanresults` authority model has now been superseded. Parser-fix trial `20260411T211133728869` first proved the rewrite still had a local same-target capture bug, and sanitized rerun `20260411T211327344984` then showed the durable live shape: 5G exact-closes against same-target `wl escanresults` noise (`-100/-100`), 6G keeps a repeatable drift (`-97/-102`, then `-97/-103`), and 2.4G is still non-durable (`-78/-76`, then `-78/-78`)
  - current 0403 source trace shows public `getScanResults().Noise` is copied from `wifiGen_rad_getScanResults()` after `s_updateScanResultsWithSpectrumInfo()` back-fills each matching-channel scan result with spectrum `noiselevel`, while the generic scan-result parser itself does not populate `noise`. So direct `wl escanresults` `noise:` is no longer treated as the authoritative oracle for this row; public `getSpectrumInfo()` is still empty in the present lab state, so the committed YAML stays unchanged (`source.row=283` still stale) until a replayable spectrum-backed oracle exists
  - details recorded in `plugins/wifi_llapi/reports/D281_block.md`
  - latest D282 blocker: the old legacy-helper explanation has now been superseded. Active 0403 source trace shows the current public ubus getter uses nl80211 scan results parsed from beacon/probe IEs (`swl_80211_parseInfoElementsBuffer(...)`), copies `pWirelessDevIE->operatingStandards` into `wld_scanResultSSID_t.operatingStandards`, caches that in `lastScanResults`, and serializes it with `swl_radStd_toChar(..., SWL_RADSTD_FORMAT_STANDARD, 0)`; the old Broadcom `_wldm_get_standards()` helper is therefore no longer treated as the active public authority for this row
  - the existing isolated rerun `20260410T163026194231` still blocks the rewrite, but for a narrower reason: 5G exact-closes at `a,n,ac,ax`, 6G still emits no same-target `WlOperatingStandards6g`, and 2.4G still drifts to an extra external `be` (`LLAPI b,g,n,ax` vs `wl b,g,n,ax,be`). Because no durable same-source oracle replays the same parsed IE bitmask semantics on all three bands, the committed YAML stays unchanged (`source.row=284` still stale)
  - details recorded in `plugins/wifi_llapi/reports/D282_block.md`
  - latest D283 blocker: source trace keeps RSSI on the same neighboring scan path (`RSSI: ` token -> `ap_SignalStrength`), and both historical full-run evidence plus the new isolated rerun keep failing before semantic replay. Full run `20260409T213837737224` already recorded `step_6g_scan command failed` / `serialwrap cmd status timeout`; isolated rerun `20260410T164405221878` then hung after `setup_env`, emitted no step output, wrote no per-case `agent_trace` JSON, and briefly pushed `COM0` back to `ATTACHED / PROMPT_TIMEOUT` until self-test restored `READY`
  - details recorded in `plugins/wifi_llapi/reports/D283_block.md`
  - latest D284 blocker: source trace still maps neighboring `SecurityModeEnabled` from `AKM Suites` / `RSN`, and isolated rerun `20260410T170750425931` did prove same-target replay on 5G (`38:88:71:2f:f6:a7` -> `WPA2-Personal`) plus 2.4G (`8c:19:b5:6e:85:e1` -> `WPA2-WPA3-Personal`), but 6G would not freeze to one BSSID: LLAPI chose `3a:06:e6:2b:a3:1a` (`.ROAMTEST_RSNO_P10P_1`) while same-target `iw` emitted `IwSecurityMode6g=None`, and follow-up manual probes showed LLAPI can also expose `2C:59:17:00:19:96` (`OpenWrt_1`) as another `WPA3-Personal` target while `iw` prefers that associated BSSID instead
  - second isolated rerun `20260410T171358112868` tried an associated-BSSID selector, but the 6G LLAPI step emitted no `LlapiBssid6g`, which left `step_6g_iw_scan` with an unresolved runtime placeholder; D284 therefore remains blocked, the trial rewrite was rejected, the committed YAML stays unchanged (`source.row=286` still stale), post-revert plugin runtime regression is `1223 passed`, and details are recorded in `plugins/wifi_llapi/reports/D284_block.md`
  - latest D285 blocker: `compare-0401.md` still maps the case to workbook row `285`, but the committed YAML stays at stale row `287`; source survey showed 0403 neighboring scan internals still expose `RSSI` / `SignalStrength` plus `Noise`, while `wld_radio.odl` and public `wld.h` expose a derived `SignalNoiseRatio` only at the scan-result model layer
  - standalone LLAPI replay did prove the field exists (`3A:06:E6:2B:A3:1A` -> `RSSI=-93`, `Noise=-97`, `SignalNoiseRatio=4` on 6G; `8C:19:B5:6E:85:E1` -> `RSSI=-46`, `Noise=-80`, `SignalNoiseRatio=34` on 2.4G), but source-backed same-target replay still would not close: direct `wl -i wl1 escanresults` could not find the 6G LLAPI first BSSID at all, while a same-target 2.4G raw `wl -i wl2 escanresults` probe did find `8C:19:B5:6E:85:E1` yet reported `RSSI=-54 dBm`, `noise=-75 dBm`, `SNR=21 dB`, drifting far from LLAPI `34`
  - D285 therefore remains blocked, the trial rewrite was rejected, the committed YAML stays unchanged (`source.row=287` still stale), and details are recorded in `plugins/wifi_llapi/reports/D285_block.md`
  - latest D286 blocker: source trace still keeps neighboring `SignalStrength` on the raw `RSSI: ` token path, so a workbook-style same-target compare was trialed against `iw`/raw scan evidence. Isolated rerun `20260410T181105027445` stayed deterministic but did not close: 5G same-target `38:88:71:2f:f6:a7` remained `LLAPI=-64` vs `iw=-65` on both attempts, 6G `3a:06:e6:2b:a3:1a` emitted no same-target `IwSignalStrength6g`, and 2.4G `8c:19:b5:6e:85:e1` drifted to `LLAPI=-46` vs `iw=-55/-56`
  - follow-up raw `wl -i wl0/wl1/wl2 escanresults` probes only partially closed the gap: 5G same-target raw RSSI matched at `-64`, but 6G still could not find `3A:06:E6:2B:A3:1A` and 2.4G same-target raw RSSI still drifted at `-54 dBm`; D286 therefore remains blocked, the trial rewrite was rejected, the committed YAML was reverted to its original generic shape (`source.row=288` still stale), and details are recorded in `plugins/wifi_llapi/reports/D286_block.md`
  - latest D287 blocker: source trace still keeps neighboring `SSID` on the raw `SSID: ` token path, and the workbook-style same-target trial did prove the parser/evidence path is sound on 5G and 2.4G: isolated rerun `20260410T182739821870` locked `38:88:71:2f:f6:a7` -> `Verizon_Z4RY7R` and `8c:19:b5:6e:85:e1` -> `TMOBILE-85DF-TDK-2G` identically across LLAPI and `iw`
  - 6G still would not close: LLAPI exposed `3a:06:e6:2b:a3:1a` -> `.ROAMTEST_RSNO_P10P_1`, but same-target `iw` emitted no `IwSSID6g`, and direct raw `wl -i wl1 escanresults | grep -m1 -B2 -A1 'BSSID: 3A:06:E6:2B:A3:1A'` also came back empty; D287 therefore remains blocked, the trial rewrite was rejected, the committed YAML was reverted to its original generic shape (`source.row=289` still stale), and details are recorded in `plugins/wifi_llapi/reports/D287_block.md`
  - latest D288 alignment: source survey had already shown 0403 still exposes `WPSConfigMethodsSupported` in the scan-result model while the neighboring scan live payload returns an empty-string shape on all three bands; the remaining gap was repo-side parsing, because the raw ubus transcript keeps empty strings as `WPSConfigMethodsSupported = "",` and `_extract_key_values()` does not capture that trailing-comma form. The committed case now uses an explicit extractor command to normalize each band to `WPSConfigMethodsSupported=`, isolated rerun `20260410T183630583633` passed on all three bands, the YAML row metadata is refreshed from stale row `290` to workbook row `288`, and validation stayed green (`3 passed` targeted D288 tests, `1223 passed` full plugin runtime file)
  - latest D289 alignment: the active 0403 scan model `wld_radio.odl` `scanresult_t` does not define `Radio`, and the active HAL neighboring struct `wifi_neighbor_ap2_t` also comments out `ap_Radio`, so the live getter has no backing field to populate. The committed case now uses an explicit extractor command to normalize the missing member to `Radio=`, isolated rerun `20260410T185434305989` emitted `Radio=` on all three bands with `diagnostic_status=Pass`, the YAML row metadata is refreshed from stale row `291` to workbook row `289`, and validation stayed green (`3 passed` targeted D289 tests, `1223 passed` full plugin runtime file)
  - latest D290 blocker: source-backed survey confirmed `CentreChannel` is a real 0403 field (`wld_radio.odl` declares it, `wld_rad_scan.c` copies `ssid->centreChannel`, and `wld_nl80211_parser.c` computes it via `swl_chanspec_getCentreChannel()` with a 20MHz fallback), and isolated trial rerun `20260410T190709112740` did prove live LLAPI values on all three bands (`42 / 31 / 3`)
  - but the workbook-style same-target independent oracle still would not close: 5G and 2.4G same-target `iw` replay only yielded `BSS + freq`, never enough data to recover centre channel, while 6G emitted no same-target `iw` block at all; debug rerun `20260410T191029019821` confirmed the same gap, so D290 remains blocked, the trial rewrite was rejected, the committed YAML was reverted to its original generic shape (`source.row=292` still stale), and details are recorded in `plugins/wifi_llapi/reports/D290_block.md`
  - latest D295 alignment: the stale action-method metadata is now refreshed from row `220` to workbook row `295`, and live serialwrap replay proved all three radios already satisfy the preconditions (`Enable=1`, `Status="Up"`). The final oracle stays intentionally small and driver-backed: `WiFi.Radio.1.scan()` returned and the first 5G BSSID `38:88:71:2F:F6:A7` matched `wl0 escanresults`, `WiFi.Radio.2.scan()` returned and the first 6G BSSID `6E:15:DB:9E:33:72` matched `wl1 escanresults`, and `WiFi.Radio.3.scan()` returned and the first 2.4G BSSID `2E:59:17:00:06:F8` matched `wl2 escanresults`
  - a direct post-scan `getScanResults()` follow-up still pushed `COM0` into `PROMPT_TIMEOUT`, but serialwrap self-test recovered the console back to `READY`; therefore the committed D295 oracle stays on `scan() returned + same-target driver-cache match` rather than chaining a second oversized read
  - latest D298 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_radio.odl`, which declares `startScan()` and documents the failure modes (`Unable to start scan`, `A scan is already running`); the 0403 live path in `wldm_lib_wifi.c` then shows the method driving `wldm_xbrcm_scan(..., "scan")` before fetching `num_scan_results` plus `scan_results`
  - manual serialwrap replay now matches that contract on all three bands: `WiFi.Radio.1/2/3.startScan()` each returned `[ "" ]`, while the post-call driver cache stayed populated with visible BSSIDs on every band (`wl0` first BSSID `A8:A2:37:4F:8C:5C`, `wl1` first BSSID `6E:15:DB:9E:33:72`, `wl2` first BSSID `62:82:FE:58:AC:B5`); the committed YAML metadata is therefore refreshed from stale row `223` to workbook row `298`
  - latest D299 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_radio.odl` (`void stopScan()`), in `src/RadMgt/wld_rad_scan.c` where `_stopScan()` delegates to `wld_scan_stop(pR)`, and in `wld_scan_stop()` where the active scan path requires `wld_scan_isRunning()` before calling `pRad->pFA->mfn_wrad_stop_scan(pRad)`; the public nl80211 surface also exposes `wld_rad_nl80211_abortScan()` / `wld_nl80211_abortScan(...)`
  - live serialwrap replay then closed the `ScanResults.ScanInProgress` state-bit oracle on all three bands: 5G proved `0 -> startScan() -> 1 -> stopScan() -> 0` and a second restart loop returned to `1/0` again, while 6G and 2.4G each proved `0 -> 1 -> 0` with short probes; a longer combined 6G+2.4G probe did hit `PROMPT_TIMEOUT_RECOVERED`, so the committed oracle stays on short per-band replays. The committed YAML metadata is therefore refreshed from stale row `224` to workbook row `299`, and validation stayed green (`3 passed` targeted D299 tests, `1223 passed` full plugin runtime file)
  - latest D300 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, which exposes both `Stats.BroadcastPacketsReceived` and `htable getSSIDStats()`; `src/wld_ssid.c` then routes `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()`, where the 0403 `false && (pAP->status != APSTI_ENABLED)` fallback path keeps `wld_updateVAPStats(pAP, NULL)` live, and `src/wld_statsmon.c` fills `BroadcastPacketsReceived` from `rxBroadcastPackets`
  - live serialwrap replay then closed a three-way numeric oracle on all three bands: 5G matched `363 / 363 / 363`, 6G matched `144 / 144 / 144`, and 2.4G matched `113 / 113 / 113` across extracted `getSSIDStats()`, direct `WiFi.SSID.{i}.Stats.BroadcastPacketsReceived?`, and `/proc/net/dev_extstats` field `$23` for `wl0/wl1/wl2`; one longer all-band extraction probe did hit `PROMPT_TIMEOUT_RECOVERED`, so the committed oracle stays on short per-band probes. The committed YAML metadata is therefore refreshed from stale row `225` to workbook row `300`, and validation stayed green (`3 passed` targeted D300 tests, `1223 passed` full plugin runtime file)
  - latest D301 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, which exposes both `Stats.BroadcastPacketsSent` and `htable getSSIDStats()`; `src/wld_ssid.c` then routes `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()`, where the 0403 fallback path still keeps `wld_updateVAPStats(pAP, NULL)` live, and `src/wld_statsmon.c` fills `BroadcastPacketsSent` from `txBroadcastPackets`
  - live serialwrap replay then closed the matching three-way numeric oracle on all three bands: 5G matched `1432 / 1432 / 1432`, 6G matched `1590 / 1590 / 1590`, and 2.4G matched `1680 / 1680 / 1680` across extracted `getSSIDStats()`, direct `WiFi.SSID.{i}.Stats.BroadcastPacketsSent?`, and `/proc/net/dev_extstats` field `$24` for `wl0/wl1/wl2`. The committed YAML metadata is therefore refreshed from stale row `226` to workbook row `301`, and validation stayed green (`3 passed` targeted D301 tests, `1223 passed` full plugin runtime file)
  - latest D302 blocker: active 0403 source still shows `BytesReceived` is real (`wld_ssid.c` copies endpoint `rxbyte`, while `wld_statsmon.c` aggregates `pSrc->rxBytes`), and live replay did prove `direct Stats == getSSIDStats()` on all three bands (`139402 / 139402`, `43232 / 43232`, `33066 / 33066`, with a focused 5G rerun still at `139618 / 139618`)
  - however, the independent oracle would not close: the old D323-style `/proc/net/dev` / `/proc/net/dev_extstats` field `$2` path is now confirmed stale, and a later source trace through `whm_brcm_vap_update_ap_stats()` / `whm_brcm_get_if_stats()` showed the current 0403 override actually reads `wl if_counters rxbyte`. That newer oracle exact-closes on 6G/2.4G and narrows 5G to a stable `+104` delta (`140482` getter vs `140378` `if_counters`), but still does not close all three bands. The trial rewrite was therefore rejected, committed metadata stays unchanged at stale row `227`, and the blocker handoff lives in `plugins/wifi_llapi/reports/D302_block.md`
  - latest D303 blocker: active 0403 source still shows `BytesSent` is real (`wld_ssid.c` copies endpoint `txbyte`, while `wld_statsmon.c` aggregates `pSrc->txBytes`), and live replay partially closed the method path: 5G and 2.4G held `direct Stats == getSSIDStats()` (`95452542` / `67883586`), while 6G first drifted slightly (`60438235` vs `60439059`) and only re-closed on a focused rerun (`60582625 / 60582625`)
  - however, the independent oracle would not close either: `/proc/net/dev` / `/proc/net/dev_extstats` field `$10` stayed around `66798080 / 64667313 / 66738514` and `66750876 / 64691013 / 66691690`, `wl counters txbyte` stayed materially higher (`114950286 / 80944128 / 77082489`), `wl0.1/wl1.1/wl2.1` sub-interface counters were blank / zero-like, and `AssociatedDevice.*.TxBytes` also failed to map cleanly. The trial rewrite was therefore rejected, committed metadata stays unchanged at stale row `228`, and the blocker handoff lives in `plugins/wifi_llapi/reports/D303_block.md`
  - latest D304 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `DiscardPacketsReceived` from `wl if_counters rxdiscard`
  - live serialwrap replay then closed a three-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters rxdiscard = 0 / 0 / 0`; the older D325-style `/proc/net/dev_extstats` field `$5` path stayed stale at `565 / 3752 / 356`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes. The committed YAML metadata is therefore refreshed from stale row `229` to workbook row `304`, and validation stayed green (`3 passed` targeted D304 tests, `1223 passed` full plugin runtime file)
  - latest D305 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `DiscardPacketsSent` from `wl if_counters txdiscard`
  - live serialwrap replay then closed the matching three-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters txdiscard = 0 / 0 / 0`; the older D326-style `/proc/net/dev_extstats` field `$13` path stayed stale at `184 / 3467 / 87`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes. The committed YAML metadata is therefore refreshed from stale row `230` to workbook row `305`, and validation stayed green (`3 passed` targeted D305 tests, `1223 passed` full plugin runtime file)
  - latest D306 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `ErrorsReceived` from `wl if_counters rxerror`
  - live serialwrap replay then closed a four-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters rxerror / /proc/net/dev_extstats $4 = 0 / 0 / 0 / 0`. The committed YAML metadata is therefore refreshed from stale row `231` to workbook row `306`, and validation stayed green (`3 passed` targeted D306 tests, `1223 passed` full plugin runtime file)
  - latest D307 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds base-VAP `ErrorsSent` from `wl if_counters txerror` and `whm_brcm_vap_ap_stats_accu()` then accumulates matching `wds*` interface stats back into `SSID.stats`
  - live serialwrap replay then closed that source-backed oracle: 5G matched `direct / getSSIDStats / wds0.0.1 if_counters txerror = 56 / 56 / 56`, a focused 6G rerun matched `direct / getSSIDStats / wds1.0.1 if_counters txerror = 46 / 46 / 46`, and 2.4G held `direct / getSSIDStats / wl2 if_counters txerror = 0 / 0 / 0` with no matching WDS peer. The older D328-style `/proc/net/dev_extstats` field `$12` heuristic stayed at `0` on the base wl interfaces and is therefore stale for 5G/6G in the current 0403 baseline. The committed YAML metadata is therefore refreshed from stale row `232` to workbook row `307`, and validation stayed green (`3 passed` targeted D307 tests, `1223 passed` full plugin runtime file)
  - latest D308 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `FailedRetransCount` from `wl if_counters txretransfail`; if any matching `wds*` interface exists, the same `whm_brcm_vap_ap_stats_accu()` path would accumulate it, but the current live baseline stayed at zero
  - live serialwrap replay then closed the matching three-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct / getSSIDStats / wl if_counters txretransfail = 0 / 0 / 0`. The committed YAML metadata is therefore refreshed from stale row `233` to workbook row `308`, and validation stayed green (`3 passed` targeted D308 tests, `1223 passed` full plugin runtime file)
  - latest D309 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `MulticastPacketsReceived` from `wl if_counters rxmulti`, `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface stats, and `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsReceived` before clamping the field at zero
  - live serialwrap replay then closed that source-backed formula on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxmulti / BroadcastPacketsReceived = 0 / 0 / 10 / 363`, 6G matched `0 / 0 / 0 / 145`, and 2.4G matched `0 / 0 / 0 / 113`, so every band authoritatively lands at `max((rxmulti + matching wds_rxmulti) - BroadcastPacketsReceived, 0) = 0`. The older D330-style `/proc/net/dev_extstats` field `$9` heuristic stayed stale at `363 / 146 / 113`. The committed YAML metadata is therefore refreshed from stale row `234` to workbook row `309`, and validation stayed green (`3 passed` targeted D309 tests, `1223 passed` full plugin runtime file)
  - latest D310 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `MulticastPacketsSent` from `wl if_counters txmulti`, `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface stats, and `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsSent` before clamping the field at zero
  - live serialwrap replay then closed that source-backed formula on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters txmulti / BroadcastPacketsSent = 135098 / 135098 / 136632 / 1534`, 6G matched `76033 / 76033 / 77722 / 1689`, and 2.4G matched `150648 / 150648 / 152429 / 1781`, so every band authoritatively lands at `max((txmulti + matching wds_txmulti) - BroadcastPacketsSent, 0)`. The older D331-style `/proc/net/dev_extstats` field `$18` heuristic stayed stale at `154277 / 148836 / 154585`. The committed YAML metadata is therefore refreshed from stale row `235` to workbook row `310`, and targeted validation stayed green (`3 passed` targeted D310 tests)
  - latest D311 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `PacketsReceived` from `wl if_counters rxframe` and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface packet counts before the final SSID stats snapshot is returned
  - live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxframe / wds0.0.1 rxframe = 1082 / 1082 / 1080 / 2`, 6G matched `292 / 292 / 292 / 0`, and 2.4G matched `220 / 220 / 220 / 0`. The older D332-style `/proc/net/dev_extstats` field `$3` heuristic stayed stale at `1086 / 438 / 333`. The committed YAML metadata is therefore refreshed from stale row `236` to workbook row `311`, and targeted validation stayed green (`3 passed` targeted D311 tests)
  - latest D312 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `PacketsSent` from `wl if_counters txframe` and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface packet counts before the final SSID stats snapshot is returned
  - live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters txframe / wds0.0.1 txframe = 192311 / 192311 / 157138 / 35173`, 6G matched `91211 / 91211 / 89703 / 1510`, and 2.4G matched `156926 / 156926 / 156926 / 0`. The older D333-style `/proc/net/dev_extstats` field `$11` is no longer an all-band authority: 5G stayed at base `wl0` txframe, 6G drifted to `151237`, and only 2.4G still exact-closed because no matching WDS peer existed. The committed YAML metadata is therefore refreshed from stale row `237` to workbook row `312`, and targeted validation stayed green (`3 passed` targeted D312 tests)
  - latest D313 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` seeds `RetransCount` from `wl if_counters txretrans` and `whm_brcm_vap_ap_stats_accu()` would accumulate matching `wds*` interface values when present
  - live serialwrap replay then closed that source-backed oracle on all three bands: 5G, 6G, and 2.4G all matched `direct / getSSIDStats / wl if_counters txretrans / matching wds txretrans = 0 / 0 / 0 / 0`. The adjacent D334 direct case already records the same 0403 zero-shape comment (`direct Stats matched getSSIDStats(), but workbook v4.0.3 still remains To be tested`), so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes rather than the stale wording. The committed YAML metadata is therefore refreshed from stale row `238` to workbook row `313`, and targeted validation stayed green (`3 passed` targeted D313 tests)
  - latest D314 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` first seeds `PacketsReceived` from `wl if_counters rxframe`, seeds `MulticastPacketsReceived` from `wl if_counters rxmulti`, and derives `UnicastPacketsReceived = PacketsReceived - MulticastPacketsReceived` before `whm_brcm_vap.c` later adjusts only the visible multicast field
  - live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxframe / wl0 if_counters rxmulti / wds0.0.1 rxframe / wds0.0.1 rxmulti = 1084 / 1084 / 1092 / 10 / 2 / 0`, 6G matched `292 / 292 / 292 / 0 / 0 / 0`, and 2.4G matched `220 / 220 / 220 / 0 / 0 / 0`. The older D335-style `/proc/net/dev_extstats` field `$21` heuristic stayed stale at `360 / 146 / 107`. The committed YAML metadata is therefore refreshed from stale row `239` to workbook row `314`, and targeted validation stayed green (`3 passed` targeted D314 tests)
  - latest D315 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` first seeds `PacketsSent` from `wl if_counters txframe`, seeds `MulticastPacketsSent` from `wl if_counters txmulti`, and derives `UnicastPacketsSent = PacketsSent - MulticastPacketsSent` before `whm_brcm_vap.c` later adjusts only the visible multicast field
  - live serialwrap replay then closed that source-backed oracle on all three bands: focused 5G rerun matched `direct / getSSIDStats / wl0 if_counters txframe / wl0 if_counters txmulti / wds0.0.1 txframe / wds0.0.1 txmulti = 55992 / 55992 / 159684 / 140207 / 36515 / 0`, 6G matched `13317 / 13317 / 92193 / 81711 / 2835 / 0`, and 2.4G matched `2338 / 2338 / 159419 / 157081 / 0 / 0`. The older D336-style `/proc/net/dev_extstats` field `$22` heuristic stayed stale at `0` on all three bands. The committed YAML metadata is therefore refreshed from stale row `240` to workbook row `315`, and targeted validation stayed green (`3 passed` targeted D315 tests)
  - latest D316 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` seeds `UnknownProtoPacketsReceived` from `wl if_counters rxunknownprotopkts`, `whm_brcm_vap_copy_stats()` preserves the base VAP field, and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface values before the final SSID stats snapshot is returned
  - live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxunknownprotopkts / wds0.0.1 rxunknownprotopkts = 0 / 0 / 0 / 0`, 6G matched `0 / 0 / 0 / 0`, and 2.4G matched `0 / 0 / 0 / 0`. The adjacent D337 direct case still stays workbook-gated as `To be tested`, but its v4.0.3 comment already records the same multiband zero-shape (`direct Stats matched getSSIDStats()`). The committed YAML metadata is therefore refreshed from stale row `241` to workbook row `316`, and targeted validation stayed green (`3 passed` targeted D316 tests)
  - latest D317 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, where `WiFi.SSID.{i}.BSSID` is exposed as a read-only SSID property, and `dm_info.c` still advertises the same `BSSID` field on the active `WiFi.SSID` object
  - live serialwrap replay then closed the independent oracle on all three bands by matching the property against both interface views: 5G `ubus BSSID / iw dev wl0 info addr / wl -i wl0 cur_etheraddr = 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95`, 6G matched `2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96`, and 2.4G matched `2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7`. The workbook v4.0.3 comment already states the same `matching iw dev info` shape. The committed YAML metadata is therefore refreshed from stale row `242` to workbook row `317`, and targeted validation stayed green (`3 passed` targeted D317 tests)
  - latest D319 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, where `WiFi.SSID.{i}.MACAddress` remains exposed as a read-only SSID property on the active object model
  - live serialwrap replay then closed a four-way independent oracle on all three bands by matching the property against three interface views: 5G `ubus MACAddress / iw dev wl0 info addr / ifconfig wl0 HWaddr / wl -i wl0 cur_etheraddr = 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95`, 6G matched `2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96`, and 2.4G matched `2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7`. The committed YAML metadata is therefore refreshed from stale row `321` to workbook row `319`, and targeted validation stayed green (`3 passed` targeted D319 tests)
  - latest D320 alignment: source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, where `WiFi.SSID.{i}.SSID` remains exposed as a read-only SSID property on the active object model
  - live serialwrap replay then closed the independent oracle on all three bands by matching the getter against the driver SSID view: 5G `ubus SSID / wl -i wl0 ssid = testpilot5G / testpilot5G`, 6G matched `testpilot6G / testpilot6G`, and 2.4G matched `testpilot2G / testpilot2G`. The committed YAML metadata is therefore refreshed from stale row `322` to workbook row `320`, and targeted validation stayed green (`3 passed` targeted D320 tests)
  - latest D321 alignment: active 0403 source-backed support stays consistent with the already closed D300 family, and live serialwrap replay closed the full three-way direct-property oracle on all three bands: 5G `direct Stats / getSSIDStats / /proc/net/dev_extstats $23 = 363 / 363 / 363`, 6G matched `147 / 147 / 147`, and 2.4G matched `113 / 113 / 113`
  - the committed YAML metadata is therefore refreshed from stale row `245` to workbook row `321`, and targeted validation stayed green (`3 passed` targeted D321 tests)
  - D211 remains the latest semantic blocked/fail-shaped mismatch
  - latest D334 alignment: the first real runner replay `20260411T021238026451` already exact-closed direct Stats and getSSIDStats(), but it still lacked an independent driver oracle and the original extractor could ambiguously match `FailedRetransCount`. The active 0403 source-backed path is now re-confirmed by the fresh D334 survey at `wldm_SSID_TrafficStats()` -> `wl if_counters txretrans`, with no WDS accumulation on the direct-property path. A focused live probe then exact-closed `direct / getSSIDStats / low-32(txretrans)` at 5G `4294967295`, 6G `4294963915`, and 2.4G `0`. After refreshing the case to use anchored `getSSIDStats()` extraction plus the low-32 driver oracle, real runner rerun `20260411T022030741126` passed on retry: attempt 1 saw a transient 6G drift (`4294967294` vs driver `0`), but attempt 2 exact-closed `direct / getSSIDStats / if_counters` on all three bands (`0 / 0 / 0`, `0 / 0 / 0`, `0 / 0 / 0`). The committed YAML metadata is therefore refreshed from stale row `258` to workbook row `334`, targeted validation stayed green, the command-budget inventory moved to `630`, and full repo regression stayed green at `1634 passed`
  - next ready case after resume: `D529`
  - `D024` offline survey is complete: workbook authority is row `24`, workbook `G/H` and the source model both point to DUT `wl -i wl0 sta_info $STA_MAC` `rate of last tx pkt` as the AP -> STA truth source
  - `D025` offline survey is complete: workbook authority is row `25`, workbook `G/H` and the source model both point to DUT `wl -i wl0 sta_info $STA_MAC` `rate of last rx pkt` as the STA -> AP truth source
  - `D026` offline survey is complete: workbook authority is row `26`, workbook `G/H` and the source evidence both point to DUT `wl -i wl0 sta_info $STA_MAC` `link bandwidth = XX MHZ` plus `WiFi.Radio.1.OperatingChannelBandwidth` as the truth sources
  - old run `20260401T152827516151` already captured matching LLAPI / driver values for `D024`, `D025`, and `D026`; the historical `step4` fail shape is therefore treated as consistent with the older shell-pipeline success-classifier bug that is now covered by runtime regression guards
  - current YAML metadata for this slice is still stale: `D024/D025/D026` remain at row `21/22/23` and should be rewritten live to workbook row `24/25/26`
  - current active focus is no longer generic UART recovery; serialwrap `COM0/COM1` are back in `READY`, but `D277` and `D283` still show the raw-6G-scan transport blocker while `D284` is now a separate 6G same-target replay blocker caused by LLAPI / `iw` target drift across multiple `WPA3-Personal` BSSIDs. The next patch-driven workbook-Pass queue present in the current repo inventory after the D277/D283/D284 blockers plus the D278/D279/D280 alignments is `D285-D290`, `D295`, `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D285` is now also blocked; after the D277/D281/D282/D283/D284/D285 blocker set plus the D278/D279/D280 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D286-D290`, then `D295`, `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D286` is now also blocked; after the D277/D281/D282/D283/D284/D285/D286 blocker set plus the D278/D279/D280 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D287-D290`, then `D295`, `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D287` is now also blocked; after the D277/D281/D282/D283/D284/D285/D286/D287 blocker set plus the D278/D279/D280 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D288-D290`, then `D295`, `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D288` is now aligned; after the D277/D281/D282/D283/D284/D285/D286/D287 blocker set plus the D278/D279/D280/D288 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D289-D290`, then `D295`, `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D289` is now aligned as a fail-shaped absence; after the D277/D281/D282/D283/D284/D285/D286/D287 blocker set plus the D278/D279/D280/D288/D289 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D290`, then `D295`, `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D290` is now also blocked; after the D277/D281/D282/D283/D284/D285/D286/D287/D290 blocker set plus the D278/D279/D280/D288/D289 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D295`, then `D298-D299`, `D300-D337`, `D528-D533`
  - superseding continuation: `D295` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290 blocker set plus the D278/D279/D280/D288/D289/D295 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D298-D299`, then `D300-D337`, `D528-D533`
  - superseding continuation: `D298` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290 blocker set plus the D278/D279/D280/D288/D289/D295/D298 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D299`, then `D300-D337`, `D528-D533`
  - superseding continuation: `D299` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D300-D337`, then `D528-D533`
  - superseding continuation: `D300` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D301-D337`, then `D528-D533`
  - superseding continuation: `D301` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D302-D337`, then `D528-D533`
  - superseding continuation: `D302` is now blocked; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D303-D337`, then `D528-D533`
  - superseding continuation: `D303` is now blocked; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302/D303 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D304-D337`, then `D528-D533`
  - superseding continuation: `D304` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302/D303 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301/D304 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D305-D337`, then `D528-D533`
  - superseding continuation: `D305` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302/D303 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301/D304/D305 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D306-D337`, then `D528-D533`
  - superseding continuation: `D306` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302/D303 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301/D304/D305/D306 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D307-D337`, then `D528-D533`
  - superseding continuation: `D307` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302/D303 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301/D304/D305/D306/D307 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D308-D337`, then `D528-D533`
  - superseding continuation: `D308` is now aligned as plain `Pass/Pass/Pass`; after the D277/D281/D282/D283/D284/D285/D286/D287/D290/D302/D303 blocker set plus the D278/D279/D280/D288/D289/D295/D298/D299/D300/D301/D304/D305/D306/D307/D308 alignments, the next patch-driven workbook-Pass queue in the current repo inventory starts from `D309-D337`, then `D528-D533`
- Resume instructions:
  - start from this file plus `compare-0401.{md,json}` and `plugins/wifi_llapi/reports/0410summary.md`
  - use `compare-0401.{md,json}` rebuilt through `20260402T105808547293`, but treat `D111` as already revalidated by run `20260410T110659169758`
  - before any further live run, confirm serialwrap `COM0/COM1` remain `READY` and `session self-test` still passes
  - keep D211 at blocked/fail-shaped until a later FW drop proves AX phase can really clear EHT from runtime beacon/config behavior
  - resume by continuing the patch-driven workbook-Pass queue from `D285`, while keeping `D277`/`D283` blocked until raw 6G scan capture no longer drives serialwrap recovery / the DUT activation prompt, `D281` blocked until same-target `Noise` replay becomes deterministic, `D282` blocked until `OperatingStandards` has an all-band same-target replay that survives both ambient-target and controlled-baseline probes, and `D284` blocked until 6G `SecurityModeEnabled` can freeze one replayable target across LLAPI and `iw`; after that, return to the stale-row slice `D024` row `24` → `D025` row `25` → `D026` row `26`
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D286`, while keeping `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D287`, while keeping `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D288`, while keeping `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D289`, while keeping `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D290`, while keeping `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D295`, while keeping `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D298`, while keeping `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D299`, while keeping `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D300`, while keeping `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D301`, while keeping `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D302`, while keeping `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D303`, while keeping `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D304`, while keeping `D303` blocked until `BytesSent` can close a source-backed all-band independent oracle beyond the current proc/wl/adlist mismatch, `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D305`, while keeping `D303` blocked until `BytesSent` can close a source-backed all-band independent oracle beyond the current proc/wl/adlist mismatch, `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D306`, while keeping `D303` blocked until `BytesSent` can close a source-backed all-band independent oracle beyond the current proc/wl/adlist mismatch, `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D307`, while keeping `D303` blocked until `BytesSent` can close a source-backed all-band independent oracle beyond the current proc/wl/adlist mismatch, `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D308`, while keeping `D303` blocked until `BytesSent` can close a source-backed all-band independent oracle beyond the current proc/wl/adlist mismatch, `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D309`, while keeping `D303` blocked until `BytesSent` can close a source-backed all-band independent oracle beyond the current proc/wl/adlist mismatch, `D302` blocked until `BytesReceived` can close a source-backed all-band independent oracle beyond the current `if_counters` partial close (`6G/2.4G` exact, `5G` stable `+104`) plus the stale proc/wl/adlist mismatches, `D290` blocked until neighboring `CentreChannel` can close a source-backed same-target replay with an independent oracle beyond `BSS + freq`, `D287` blocked until neighboring `SSID` can close a source-backed same-target replay without the current 6G target-miss, `D286` blocked until neighboring `SignalStrength` can close a source-backed same-target replay without the current 6G target-miss / 2.4G RSSI drift, and `D285` blocked until neighboring `SignalNoiseRatio` can close a source-backed same-target replay without the current 6G target-miss / 2.4G SNR drift
  - superseding resume note: continue the patch-driven workbook-Pass queue from `D329`, while keeping `D322` blocked until `BroadcastPacketsSent` has a source-backed independent oracle beyond the current unstable `/proc/net/dev_extstats` `$24` heuristic
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
  - superseding progress note: `D321` has now been rerun through the real `testpilot run` path after the direct-stats resolver fix, and it exact-closed on all three bands at `364/364/364`, `149/149/149`, and `113/113/113` across direct/getSSIDStats//proc (`run_id=20260411T002336420469`)
  - superseding progress note: `D322` must be removed from the earlier "verified subset"; after the same resolver fix it no longer fails on missing `getssid_*` capture, but the live rerun still shows a stable 5G `+1` drift on `/proc $24` (`1644/1644/1645`, then `1647/1647/1648`) while 6G/2.4G exact-close. Active 0403 source in `whm_brcm_vap.c` restores final public `BroadcastPacketsSent` from `tmp_stats`, so `/proc $24` is still treated as a stale heuristic. The blocker handoff is now `plugins/wifi_llapi/reports/D322_block.md`
  - superseding progress note: `D323` is restored into the verified subset. The earlier blocker turned out to be a stale workbook `/proc/net/dev_extstats` `$2` heuristic plus an incorrect source explanation; corrected 0403 tracing now shows the direct-property row is backed by `wl if_counters rxbyte` plus matching `wds*` accumulation, and official rerun `20260411T231952006453` exact-closed on all three bands (`276282/276282/276282`, `122610/122610/122610`, `73193/73193/73193`). The committed metadata is refreshed from stale row `247` to workbook row `323`, and `plugins/wifi_llapi/reports/D323_block.md` is retained as historical resolution notes
  - superseding progress note: `D324` is now positively aligned. Real runner replay `20260411T005329099506` first proved the workbook `/proc $10` criterion was stale, but active 0403 source trace plus follow-up serialwrap probes closed the real oracle at `wl if_counters txbyte`; after rewriting the case to that source-backed readback, real runner rerun `20260411T010328768651` exact-closed on all three bands (`79412272/79412272/79412272`, `47109866/47109866/47109866`, `79349200/79349200/79349200`). The committed metadata is refreshed from stale row `248` to workbook row `324`
  - superseding progress note: `D325` is now positively aligned. The prior real runner replay `20260411T010859993578` proved the workbook `/proc $5` criterion was stale, but the active 0403 source-backed path stays consistent with aligned `D304` at `whm_brcm_get_if_stats()` / `wl if_counters rxdiscard`; after rewriting the direct-property case to that oracle, real runner rerun `20260411T011321267947` exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `249` to workbook row `325`
  - superseding progress note: `D326` is now positively aligned. The prior real runner replay `20260411T012137925510` proved the workbook `/proc $13` criterion was stale, but the active 0403 source-backed path is now re-confirmed by the fresh D326 survey and aligned `D305` at `whm_brcm_get_if_stats()` / `wl if_counters txdiscard`; after rewriting the direct-property case to that oracle, real runner rerun `20260411T012538161460` exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `250` to workbook row `326`
  - superseding progress note: `D327` is now positively aligned. The first real runner replay `20260411T013241354703` already exact-closed the legacy `/proc $4` compare at zero, but the active 0403 source-backed path is now re-confirmed by the fresh D327 survey and aligned `D306` at `whm_brcm_get_if_stats()` / `wl if_counters rxerror`; after refreshing the direct-property case to that oracle, real runner rerun `20260411T013801878458` still exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `251` to workbook row `327`
  - superseding progress note: `D328` is now positively aligned. The first real runner replay `20260411T014458979418` already exact-closed the legacy `/proc $12` compare at zero, but the active 0403 source-backed path is now re-confirmed by the fresh D328 survey and aligned `D307` at `whm_brcm_get_if_stats()` / `wl if_counters txerror`, with optional `wds*` accumulation. A focused live probe also showed the field is a moving counter (`5G=1`, `6G=3347`, `2.4G=0` across direct/getSSIDStats/txerror). After refreshing the direct-property case to that oracle, real runner rerun `20260411T015126498621` still exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `252` to workbook row `328`, and the next ready stats row is `D329`
  - superseding progress note: `D329` is now positively aligned. The first real runner replay `20260411T015905984272` already exact-closed direct Stats and getSSIDStats() at zero, but it still lacked an independent driver oracle. The active 0403 source-backed path is now re-confirmed by the fresh D329 survey and aligned `D308` at `whm_brcm_get_if_stats()` / `wl if_counters txretransfail`, with optional `wds*` accumulation only when a matching peer exists. A focused live probe then exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`) and confirmed the current baseline has no active `wds*` peer. After refreshing the direct-property case to that oracle, real runner rerun `20260411T020534026608` still exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `253` to workbook row `329`, and the next ready stats row is `D334`
  - superseding progress note: `D334` is now positively aligned. The first real runner replay `20260411T021238026451` already exact-closed direct Stats and getSSIDStats(), but it still lacked an independent driver oracle and the original extractor could ambiguously match `FailedRetransCount`. The active 0403 source-backed path is now re-confirmed by the fresh D334 survey at `wldm_SSID_TrafficStats()` / `wl if_counters txretrans`, without WDS accumulation on the direct-property path. A focused live probe then exact-closed the low-32 driver view at 5G `4294967295`, 6G `4294963915`, and 2.4G `0`. After refreshing the direct-property case to that oracle, real runner rerun `20260411T022030741126` passed on retry: attempt 1 saw a transient 6G drift (`4294967294` vs driver `0`), but attempt 2 exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `258` to workbook row `334`, and the next ready stats row is `D337`
  - superseding progress note: `D337` is now positively aligned. The first real runner replay `20260411T023258929853` already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. The active 0403 source-backed path is now re-confirmed by the fresh D337 survey at `wldm_SSID_TrafficStats()` / `wl if_counters rxbadprotopkts`, without WDS accumulation on the direct-property path. A focused live probe then exact-closed `direct / getSSIDStats / rxbadprotopkts` on all three bands (`0/0/0`, `0/0/0`, `0/0/0`), while the adjacent getSSIDStats-family `rxunknownprotopkts` view also stayed zero on all three bands. After refreshing the direct-property case to that oracle, real runner rerun `20260411T024443960794` exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `261` to workbook row `337`, and the next ready stats row is `D406`
  - superseding progress note: `D406` is now positively aligned. The first real runner replay `20260411T025549740195` already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. The active 0403 source-backed path is now re-confirmed at `wldm_SSID_TrafficStats()` / `wl if_counters txretrie`. A focused live probe then exact-closed `direct / getSSIDStats / txretrie` on all three bands (`0/0/0`, `0/0/0`, `0/0/0`), while the current baseline still showed no active `wds*` peer. After refreshing the direct-property case to that oracle, real runner rerun `20260411T025954644775` exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `301` to workbook row `406`, and the next ready stats row is `D407`
  - superseding progress note: `D407` is now positively aligned. The first real runner replay `20260411T031324456196` already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but the workbook-era extractor still ambiguously matched `MultipleRetryCount` and there was no independent driver oracle. The active 0403 source-backed path is now re-confirmed at `wldm_SSID_TrafficStats()` / `wl if_counters txretry`. A focused live probe then exact-closed `direct / getSSIDStats / txretry` on all three bands (`0/0/0`, `0/0/0`, `0/0/0`), while the current baseline still showed no active `wds*` peer. After refreshing the direct-property case to that oracle, real runner rerun `20260411T031645170662` exact-closed on all three bands (`0/0/0`, `0/0/0`, `0/0/0`). The committed metadata is refreshed from stale row `302` to workbook row `407`, and the next ready patch-driven workbook-Pass case is `D528`
  - superseding progress note: `D528` is now positively aligned. The workbook-era replay `20260411T032529278022` already proved the old numeric-only regex was stale because active 0403 returned `bandwidth="20MHz"` on all three bands. The active 0403 source-backed path is now closed at `_getSpectrumInfo()` / `s_prepareSpectrumOutput()` / `amxc_var_add_key(cstring_t, "bandwidth", swl_bandwidth_str[llEntry->bandwidth])`, while the sync refresh path `wifiGen_rad_getSpectrumInfo(..., update=false)` seeds survey-derived spectrum entries with `SWL_BW_20MHZ` in `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()`. After refreshing the case to the exact public string shape and updating the spectrum guardrail fixture, real runner rerun `20260411T034134858534` exact-closed on all three bands (`20MHz`, `20MHz`, `20MHz`), official-case guardrails stayed green at `1225 passed`, full repo regression stayed green at `1634 passed`, and the next ready patch-driven workbook-Pass case is `D529`
  - the remaining mirrored SSID stats rows are also now aligned to the multiband sequential recipe:
    - `getSSIDStats()` `Pass`: `D300-D307`, `D309-D312`, `D314-D315`
    - direct workbook-open (`To be tested`): none
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
