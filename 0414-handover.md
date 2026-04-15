**2026-04-15 superseding note：本檔下半部的大盤分析仍保留較早 snapshot；最新 strict compare 已更新為 `389 / 420 full matches`、`31` 筆 mismatch、`43` 筆 metadata drift。** 最新已提交 closure 已前進到 `D520 SSID WMM AC_BE Stats WmmPacketsReceived`（official rerun `20260415T145951312696`）：這筆 workbook-faithful **Pass alignment closure** 已把舊 source row `387` 退休，改回 workbook row `520` 的 direct `WiFi.SSID.{i}.Stats.WmmPacketsReceived.AC_BE?` getter，並補上 explicit `WiFi.SSID.{i}.getSSIDStats()` refresh 與 `wl0/wl1/wl2 wme_counters` `AC_BE` rx-frame cross-check；official rerun 在 tri-band 都 exact-close refresh/direct/driver 一致的 `0 / 0 / 0`，維持 `diagnostic_status=Pass`。較早的 focused official rerun `20260415T131457874117` 也已確認 `D508 SSID WMM AC_BE Stats WmmFailedBytesSent` 不能 land 成 workbook `Pass / Pass / Pass`：5G 仍 exact-close `0 / 0 / 0`、6G 仍 exact-close `708116 / 708116 / 708116`，但 2.4G 的 `getSSIDStats()` 與 direct getter 都固定回 `0`，而 `wl2 wme_counters` `AC_BE` tx failed bytes 穩定為 `90`，因此目前仍列 localized **2.4G zero-getter blocker**。到目前為止，SSID-level WMM family 已累積十三筆 closure 形狀：`D496`、`D499`、`D502`、`D505`、`D506`、`D507`、`D510`、`D512`、`D513`、`D517`、`D518`、`D519`、`D520`；十三者都證實 current SSID stats family 需要 explicit `getSSIDStats()` refresh 才能穩定重讀 direct Stats 值，再用 `wl wme_counters` 做 driver cross-check。既有 localized blockers `D490 Radio Stats WmmFailedBytesSent AC_BE`、`D481 Radio Stats WmmBytesReceived AC_VO`、`D482 Radio Stats WmmBytesSent AC_BE`、`D485 Radio Stats WmmBytesSent AC_VO`、`D454 getRadioStats().FailedRetransCount`、`D371 AccessPoint.AssociatedDevice.DisassociationTime` 之外，`D508` 仍維持 blocker；`D355-D357` 仍是 CSI-client placeholder backlog，`D359 AccessPoint.IsolationEnable` 仍暫停在 current single-STA lab shape，strict compare 仍先列出 `D414/D415` AssociatedDevice RRM，但 workbook `G` 已明示需要 dual-STA 802.11k split，所以暫維持 readiness review；systemic active blockers 仍以 `D047` authority conflict + shared 6G baseline manifestations（`D179`、`D181`）為主，`D211` / `D204` 仍是 parked clarification items，`D182` 仍因 shared 6G baseline path 暫停、`D302` 仍是 source-backed blocker。最新 verification 結果為 targeted runtime/budget guardrails `1251 passed`、full repo regression `1660 passed`；目前下一個 ready actionable 單案 survey target 轉到 `D521 SSID WMM AC_BK Stats WmmPacketsReceived`。

**先講結論：以目前 repo 內 `compare-0401` snapshot 為準，跟 workbook 的差距是 `122` 筆 mismatch、`58` 筆 metadata drift。** 如果只看 workbook `Pass` 目標，分兩種口徑：

| 口徑 | 數量 | 說明 |
| --- | ---: | --- |
| strict compare 未對齊 | `103` | workbook `R/S/T = Pass / Pass / Pass`，但目前 compare 還沒 full-match |
| actionable workbook-pass gap | `34` | 真正還沒被校正到 `evaluation_verdict=Pass` 的 pass backlog |
| mixed workbook-pass open | `5` | workbook 只有部分 band 是 `Pass` 的 open cases |
| all-nonpass open | `14` | workbook 本來就不是全 Pass，但目前 compare 仍未對齊 |

**`0315~0403 patch-scope` 舊 18 筆 open-set，現在 strict compare 還剩 `3` 筆掛著：`D277`、`D290`、`D336`。** 另外 `15` 筆已不再 open：`D281-D287`、`D295`、`D322`、`D324`、`D330-D333`、`D335`。

## 1. 沒對齊的原因：分門別類統計

### A. 以「全部 122 筆 mismatch」來看

| 類別 | 數量 | 代表範圍 / 說明 |
| --- | ---: | --- |
| Radio / DriverConfig / WMM / Sensing backlog | `70` | 主體還在 `D180-D201`、`D203-D214`、`D251`、`D257`、`D296-D297`、`D354-D357`、`D478-D493` 等；多數是 0403 路徑還沒逐案 replay 到 workbook pass |
| SSID / SSID Stats backlog | `31` | 主要集中在 `D302-D337` 一帶的 stats/counter 類 |
| AccessPoint / Neighbour / AssocDevice backlog | `18` | 包含 `D020`、`D047`、`D202`、`D207`、`D359`、`D370-D371`、`D414-D415`、`D427-D438` |
| 環境／基線 blocker | `2` | `D179`、`D277` |
| 獨立 oracle 不足 / model gap | `1` | `D290` |

### B. 只看「真正還在追 workbook pass 的 34 筆 actionable gap」

| 類別 | 數量 | 範圍 |
| --- | ---: | --- |
| Radio backlog | `21` | `D296-D297`、`D355-D357`、`D478-D493` |
| AccessPoint backlog | `9` | `D020`、`D427`、`D429-D435` |
| SSID Stats backlog | `2` | `D328`、`D336` |
| 環境 blocker | `1` | `D277` |
| oracle / model gap | `1` | `D290` |

## 2. block items 有哪些？原因是什麼？

### A. 目前 repo handoff 認定的 active blockers（真的會卡住下一輪 single-case flow）

| case | 原因 |
| --- | --- |
| `D047 SupportedHe160MCS` | **authority conflict**：workbook `R/S/T`、legacy `I/J/K`、row note、0403 source/runtime 彼此衝突；現在不能硬改成 workbook-pass semantics |
| `D179 Radio.Ampdu` | **6G DUT+STA baseline bring-up blocker**：DUT-only replay 已被 workbook row 179 否決；改成 DUT+STA 後又卡在 6G `verify_env` / `wl1 bss` / `STA not connected` |

### B. 目前 compare 還呈現 open、且 repo 裡有 blocker-style evidence 的項目（7 筆）

| case | 狀態 / 原因 |
| --- | --- |
| `D047` | workbook/source authority conflict |
| `D179` | 6G baseline bring-up blocker |
| `D211` | **0315/0403 行為沒變**：getter 可切 `be -> ax`，但 runtime beacon / EHT 仍維持 enabled，無法達成 workbook step 6 |
| `D277` | full `getScanResults()` 5G/6G 輸出經 serialwrap 容易 timeout / recovery prompt；**block note 已有 historical resolving evidence，但 current compare snapshot 還把它算 open** |
| `D290` | `CentreChannel` 沒有 deterministic independent oracle；LLAPI 有值，但 same-target `iw scan` 拿不到可穩定對位的 centre channel |
| `D302` | `BytesReceived` 缺穩定獨立 5G oracle；`direct == getSSIDStats`，但 driver/proc 對位仍漂移，不能只靠 API 自證 |
| `D336` | **block note 是 historical resolved note，但 current compare overlay 仍把它算 open**；本質比較像 overlay/snapshot 尚未完全 fold-in resolving rerun |

## 3. `0315~0403 patch-scope` 還差多少？

### 原始 patch-scope open set
`D277`、`D281-D287`、`D290`、`D295`、`D322`、`D324`、`D330-D333`、`D335-D336`  共 `18` 筆。

### 目前狀態

| 狀態 | 數量 | 項目 |
| --- | ---: | --- |
| strict compare 仍 open | `3` | `D277`、`D290`、`D336` |
| 已不再 open | `15` | `D281-D287`、`D295`、`D322`、`D324`、`D330-D333`、`D335` |

### 這 3 筆各自原因

| case | 原因 |
| --- | --- |
| `D277` | 5G/6G full scan payload capture 經 serialwrap 不穩；不過它同時帶有「historical 已解、current compare 未 fold-in」的成分 |
| `D290` | 目前 patch-scope 裡**最乾淨的真 blocker**：缺 stable centre-channel oracle |
| `D336` | resolving rerun note 已存在，但 current compare overlay 尚未把那次 resolving trace 納回來 |

## 4. skip / 非-pass 類 items 有哪些？原因是什麼？

### 已對齊的 skip-like items

- `44` 筆：`D014`、`D048`、`D107`、`D117-D148`、`D152`、`D294`、`D360`、`D575`、`D577-D581`
- 原因：workbook 本來就是 `To be tested` / `Skip` 類，校正策略是**保留 non-pass semantics，不偽造 Pass**。

### 已對齊的 not-supported-like items

- `32` 筆：`D029-D033`、`D036`、`D038`、`D040`、`D042`、`D052`、`D055`、`D064`、`D066-D068`、`D075-D076`、`D084`、`D086`、`D089`、`D091`、`D096-D097`、`D100`、`D102`、`D106`、`D448`、`D451-D453`、`D495`、`D576`
- 原因：workbook 明示 `Not Supported`，目前 live/source 也已被寫回成相符的 non-pass 形狀。

### 已對齊的 fail-like items

- `14` 筆：`D019`、`D037`、`D051`、`D057`、`D183`、`D259`、`D352-D353`、`D366`、`D369`、`D447`、`D449-D450`、`D464`
- 原因：這些 row 本來就是 fail-shaped authority；現在是 **live exact-close fail semantics**，不是 bug。

### 已對齊的 mixed non-pass items

- `12` 筆：`D022`、`D028`、`D049-D050`、`D063`、`D092`、`D101`、`D103-D105`、`D108`、`D494`
- 原因：workbook 本身就是 mixed semantics（部分 band pass、部分 not-supported/skip/fail），repo 已對齊成 workbook 指定的混合形狀。

## 5. 一句話總結

- **如果你看 strict compare**：現在還有 `122` 筆沒 full-match，`103` 筆是全 Pass row 還沒對齊。
- **如果你看真正該優先追的 workbook-pass backlog**：現在是 `34` 筆，主體集中在 **Radio backlog (`21`) + AP/Neighbour backlog (`9`)**。
- **如果你看 `0315~0403 patch-scope` 舊 open set**：`18` 裡面現在只剩 `3` 筆還掛在 current compare，上面最像真正 blocker 的是 `D290`；`D277`、`D336` 帶有 compare overlay 尚未完全 fold-in resolving rerun 的成分。

## 補充：新 agent 必須知道的準則與環境要件

### 1. Repo / branch / authority files

- 目前已 push 的分支：`repair/wifi-llapi-baseline-case-audit`
- 最新已 push commit：`c2db948` (`fix(wifi_llapi): align D053/D178 and block D179`)
- 目前 strict compare authority：
  - `compare-0401.md`
  - `compare-0401.json`
- workbook authority：
  - repo root `0401.xlsx`
  - answer authority = `Wifi_LLAPI` sheet `R/S/T`
  - procedure authority = `Wifi_LLAPI` sheet `G/H`
- baseline experiment authority：`docs/wifi-baseline-exp.md`
- repo handoff truth files（下一個 agent 開始前至少先讀這些）：
  - `README.md`
  - `docs/audit-todo.md`
  - `docs/plan.md`
  - `plugins/wifi_llapi/reports/audit-report-20260402-0401-checkpoint.md`
  - `plugins/wifi_llapi/reports/D047_block.md`
  - `plugins/wifi_llapi/reports/D179_block.md`
  - `plugins/wifi_llapi/reports/D181_block.md`

### 2. Source authority 與常用 src path

- firmware/source authority：`/home/build20/BGW720-0403-VERIFY`
- survey 時優先看的 source 區：
  - ODL / data-model declaration：
    - `targets/BGW720-300/fs.install/etc/amx/wld/*.odl`
  - pWHM / radio / scan / stats core path：
    - `pwhm-v7.6.38/src/**/*.c`
  - vendor override / Broadcom behavior：
    - `mods/mod-whm-brcm/src/*.c`
- 常見實際熱點：
  - scan / center-channel / scanresult export：
    - `pwhm-v7.6.38/src/RadMgt/wld_rad_scan.c`
    - `pwhm-v7.6.38/src/nl80211/wld_nl80211_parser.c`
  - counter / stats / vendor formula：
    - `mods/mod-whm-brcm/src/whm_brcm_api_ext.c`
    - `mods/mod-whm-brcm/src/whm_brcm_vap.c`
  - runtime getter / stats update：
    - `pwhm-v7.6.38/src/wld_ssid.c`
    - `pwhm-v7.6.38/src/wld_statsmon.c`
- source survey 最少要回答 5 件事：
  1. ODL 宣告在哪
  2. getter / setter / method 的 active runtime path 在哪
  3. 是否有 vendor override
  4. 合法的 driver / air / side-effect oracle 是什麼
  5. workbook 舊命令（例如 `/proc/net/dev_extstats`）是否已被 0403 source/live 證偽為 stale

### 3. fleet survey / multi-agent 使用規則

- sub-agent / fleet / `/agent` 只可做 **offline survey**：
  - workbook row 對 source path 映射
  - ODL / runtime / vendor override tracing
  - compare / YAML / historical blocker note 彙整
  - repo-wide grep / pattern analysis
- sub-agent **不可**做：
  - serialwrap live UART 操作
  - DUT/STA baseline 建置
  - 最終 pass/fail verdict
- 正確順序：
  1. 先讀 workbook `G/H`
  2. 再看 current YAML / current compare case
  3. 再做 source survey
  4. 最後才做 live serialwrap replay
- 如果 source / workbook / live 三者有衝突，**不得先改 YAML**；先落 blocker 或補 source-backed evidence。

### 4. Driver behavior / API alignment 規則

- **read-only getter**：
  - 不可把 direct set 當測試
  - 先找到真正驅動該值的 writable LLAPI / external command
  - 再驗證 readback + driver/air side effect
- **setter / method case**：
  - API readback 不足以宣告 pass
  - 一定要有 driver behavior、air behavior、或 downstream state change oracle
- **counter / stats case**：
  - 優先做 same-window tight capture
  - 同一步拿 direct getter + method snapshot + driver oracle
  - 避免把 getter / snapshot / driver 拆成多步，官方 runner 容易 drift
- **scan case**：
  - 必須是 same-target、same-scan、independent oracle
  - 若 `iw scan` / driver 沒有 deterministic 對位訊號，就應該 block，不可 API-only close
- **workbook 舊 oracle 已被 0403 證偽時**：
  - 不可因為 workbook `H` 寫過就繼續沿用
  - 例如 `/proc/net/dev_extstats`、某些 human-readable `wl sta_info` token、或 stale proc/counter 欄位，若 source/live 已證偽，就要以 0403 active path 為準
- **注意 historical block note**：
  - `plugins/wifi_llapi/reports/*_block.md` 不全是 active blocker
  - `D277`、`D281-D287`、`D331`、`D333`、`D336` 這類檔案有些已退成 historical resolution note
  - 目前是否真 open，要以 `compare-0401` + `docs/audit-todo.md` 最新 snapshot 為準

### 5. Lab / environment 要件

- board mapping：
  - `COM0 = DUT/AP`
  - `COM1 = STA`
- 若環境疑似被前一輪污染，必須 clean start：
  - `firstboot -y; sync; sync; sync; reboot -f`
- serialwrap caveats：
  - multiline command 在 line mode 下不可靠
  - probing 時優先用 **單行分號串接**
  - reboot / recover 後，`session list` 先顯示 `READY` 也不代表馬上可用；最好再做 `self-test`
- baseline 預設：
  - 5G：`testpilot5G` / `WPA2-Personal` / `00000000`
  - 2.4G：`testpilot2G` / `WPA2-Personal` / `00000000`
  - 6G：`testpilot6G` / `WPA3-Personal` / `SAE` / `00000000`
- baseline acceptance：
  - STA 必須能完成 6G STA->AP 連線
  - 要拿到 DHCP IP
  - 要能 ping DUT(AP)
- 不要同時維持三個 band 都連上；基線是 single-band baseline，再切到該 case 的 target band

### 6. Workflow hard rules

- 嚴格 single-case mode：一次只做一個 official case
- 不要 batch 未解案例
- 不要寫 ad-hoc acceleration script 跳過 evidence loop
- YAML writeback gate：
  - 只有當 live result 已經和 workbook baseline 對上，才可以改 YAML
- 每次 closure / blocker 後都要同步：
  - `README.md`
  - `docs/audit-todo.md`
  - `docs/plan.md`
  - `plugins/wifi_llapi/reports/audit-report-20260402-0401-checkpoint.md`
- commit / push 不是停點；沒有 blocker 時要直接進下一個 ready case

### 7. 下一位 agent 開工時的最短路徑

1. 先讀本檔 `0414-handover.md`
2. 再讀 `docs/audit-todo.md` 最新 snapshot
3. 再讀 `plugins/wifi_llapi/reports/D179_block.md`
4. 再讀 `plugins/wifi_llapi/reports/D181_block.md`
5. 看 `compare-0401.md` 的 `D179` / `D181` / `D190` 段
6. 若不先重開 6G baseline bring-up，就直接從 `D190 Radio.ExplicitBeamFormingEnabled` 開始

### 8. 當前 continuation anchor

- latest aligned cases:
  - `D261 getRadioAirStats() TxTime`
  - `D257 getRadioAirStats() Load`
  - `D251 Radio.Vendor.RegulatoryDomainRev`
  - `D214 Radio.RIFSEnabled`
  - `D212 Radio.PossibleChannels`
  - `D209 Radio.OperatingChannelBandwidth`
  - `D208 Radio.OfdmaEnable`
  - `D207 Radio.ObssCoexistenceEnable`
  - `D205 Radio.MultiUserMIMOSupported`
  - `D203 Radio.MaxChannelBandwidth`
  - `D202 Radio.Interference`
  - `D201 Radio.ImplicitBeamFormingSupported`
  - `D200 Radio.ImplicitBeamFormingEnabled`
  - `D199 Radio.IEEE80211rSupported`
  - `D198 Radio.IEEE80211kSupported`
  - `D197 Radio.IEEE80211hSupported`
  - `D196 Radio.IEEE80211hEnabled`
  - `D195 Radio.IEEE80211_Caps`
  - `D194 Radio.HeCapsSupported`
  - `D193 Radio.HeCapsEnabled`
  - `D192 Radio.GuardInterval`
  - `D191 Radio.ExplicitBeamFormingSupported`
  - `D190 Radio.ExplicitBeamFormingEnabled`
  - `D180 Radio.Amsdu`
  - `D184 Radio.NrActiveRxAntenna`
  - `D185 Radio.NrActiveTxAntenna`
  - `D186 Radio.NrRxAntenna`
  - `D187 Radio.NrTxAntenna`
- latest closure after baseline recovery:
  - `D261 getRadioAirStats() TxTime`
- latest parked clarification item:
  - `D211 Radio.OperatingStandards`
  - `D204 Radio.MultiUserMIMOEnabled`
- active blockers（repo handoff current view）：
  - `D047`
  - `D179`
  - `D181`
- strict compare snapshot：
  - `327 / 420 full matches`
  - `93 mismatches`
  - `58 metadata drifts`
- next ready non-blocked compare-open case：
  - `D308 getSSIDStats() FailedRetransCount`
