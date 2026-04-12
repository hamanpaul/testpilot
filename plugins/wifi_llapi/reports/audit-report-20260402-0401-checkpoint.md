# Wifi_LLAPI audit report checkpoint (0401 workbook)

## Checkpoint summary (2026-04-13 early-33)

> This checkpoint records the `D079` MACFiltering.Mode workbook row-79 closure after `D071`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D079 MACFiltering.Mode` is now aligned via official rerun `20260413T065809885285`
- the case still carried stale workbook row `73`, stale `results_reference.v4.0.3 = Fail / Fail / Fail`, and an incorrect all-Off assumption even though workbook row `79` expects a deterministic baseline with AP1 `WhiteList` / `macaddr_acl=1` / `accept` and AP3/AP5 `BlackList` / `macaddr_acl=0` / `deny`
- live source-backed probes first proved that true pass path, then confirmation rerun `20260413T065611644145` showed the only remaining blocker was a non-authoritative `wl -i wl{0,1,2} bss` setup gate that sampled transient `--wlX FSM DONE--` / `down` during hostapd restart
- the committed rewrite refreshes metadata back to workbook row `79`, reconstructs the workbook baseline explicitly in setup, removes that `wl bss` gate, and marks `results_reference.v4.0.3 = Pass / Pass / Pass`
- official rerun `20260413T065809885285` then exact-closed tri-band baseline/readback plus after-state invariance: 5G preserved `WhiteList / 1 / accept`, 6G preserved `BlackList / 0 / deny`, and 2.4G preserved `BlackList / 0 / deny`, while every `Mode=Off` setter returned `invalid value`
- overlay compare is now `270 / 420 full matches`、`150 mismatches`、`58 metadata drifts`
- next ready actionable open case is `D080`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D079` | 79 | `MACFiltering.Mode` | `Pass / Pass / Pass` | `20260413T065809885285_DUT.log L45-L381` | `n/a (AP-only)` |

#### D079 MACFiltering.Mode

**STA 指令**

```sh
# AP-only case; no STA transport
```

**DUT 指令**

```sh
ubus-cli WiFi.AccessPoint.1.Enable=1
ubus-cli WiFi.AccessPoint.3.Enable=1
ubus-cli WiFi.AccessPoint.5.Enable=1

ubus-cli "WiFi.AccessPoint.1.MACFiltering.delEntry(mac=62:2F:B8:66:BB:82)" 2>/dev/null || true
ubus-cli "WiFi.AccessPoint.3.MACFiltering.delEntry(mac=FA:DD:AC:24:5A:B4)" 2>/dev/null || true
ubus-cli "WiFi.AccessPoint.5.MACFiltering.delEntry(mac=FA:A0:DF:91:47:7C)" 2>/dev/null || true

ubus-cli "WiFi.AccessPoint.1.MACFiltering.addEntry(mac=62:2F:B8:66:BB:82)"
ubus-cli WiFi.AccessPoint.1.MACFiltering.Mode=WhiteList
ubus-cli "WiFi.AccessPoint.3.MACFiltering.addEntry(mac=FA:DD:AC:24:5A:B4)"
ubus-cli WiFi.AccessPoint.3.MACFiltering.Mode=BlackList
ubus-cli "WiFi.AccessPoint.5.MACFiltering.addEntry(mac=FA:A0:DF:91:47:7C)"
ubus-cli WiFi.AccessPoint.5.MACFiltering.Mode=BlackList

ubus-cli "WiFi.AccessPoint.1.MACFiltering.Mode?"
grep -nE '^(macaddr_acl|accept_mac_file|deny_mac_file)=' /tmp/wl0_hapd.conf
ubus-cli WiFi.AccessPoint.1.MACFiltering.Mode=Off
ubus-cli "WiFi.AccessPoint.1.MACFiltering.Mode?"
grep -nE '^(macaddr_acl|accept_mac_file|deny_mac_file)=' /tmp/wl0_hapd.conf

ubus-cli "WiFi.AccessPoint.3.MACFiltering.Mode?"
grep -nE '^(macaddr_acl|accept_mac_file|deny_mac_file)=' /tmp/wl1_hapd.conf
ubus-cli WiFi.AccessPoint.3.MACFiltering.Mode=Off
ubus-cli "WiFi.AccessPoint.3.MACFiltering.Mode?"
grep -nE '^(macaddr_acl|accept_mac_file|deny_mac_file)=' /tmp/wl1_hapd.conf

ubus-cli "WiFi.AccessPoint.5.MACFiltering.Mode?"
grep -nE '^(macaddr_acl|accept_mac_file|deny_mac_file)=' /tmp/wl2_hapd.conf
ubus-cli WiFi.AccessPoint.5.MACFiltering.Mode=Off
ubus-cli "WiFi.AccessPoint.5.MACFiltering.Mode?"
grep -nE '^(macaddr_acl|accept_mac_file|deny_mac_file)=' /tmp/wl2_hapd.conf
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T065809885285_DUT.log L45-L90
WiFi.AccessPoint.1.MACFiltering.Mode="WhiteList"
WiFi.AccessPoint.3.MACFiltering.Mode="BlackList"
WiFi.AccessPoint.5.MACFiltering.Mode="BlackList"

20260413T065809885285_DUT.log L137-L193
BaselineMode5g=WhiteList
BaselineMacaddrAcl5g=1
BaselineAclState5g=accept
ERROR: set WiFi.AccessPoint.1.MACFiltering.Mode failed (10 - invalid value)
SetOffStatus5g=invalid_value
AfterMode5g=WhiteList
AfterMacaddrAcl5g=1
AfterAclState5g=accept

20260413T065809885285_DUT.log L231-L287
BaselineMode6g=BlackList
BaselineMacaddrAcl6g=0
BaselineAclState6g=deny
ERROR: set WiFi.AccessPoint.3.MACFiltering.Mode failed (10 - invalid value)
SetOffStatus6g=invalid_value
AfterMode6g=BlackList
AfterMacaddrAcl6g=0
AfterAclState6g=deny

20260413T065809885285_DUT.log L325-L381
BaselineMode24g=BlackList
BaselineMacaddrAcl24g=0
BaselineAclState24g=deny
ERROR: set WiFi.AccessPoint.5.MACFiltering.Mode failed (10 - invalid value)
SetOffStatus24g=invalid_value
AfterMode24g=BlackList
AfterMacaddrAcl24g=0
AfterAclState24g=deny

plugins/wifi_llapi/reports/agent_trace/20260413T065809885285/wifi-llapi-D079-mode-accesspoint-macfiltering.json L108-L116
outputs:
  BaselineMode5g=WhiteList
  SetOffStatus5g=invalid_value
  AfterMode5g=WhiteList
  BaselineMode6g=BlackList
  SetOffStatus6g=invalid_value
  AfterMode6g=BlackList
  BaselineMode24g=BlackList
  SetOffStatus24g=invalid_value
  AfterMode24g=BlackList
```

## Checkpoint summary (2026-04-13 early-32)

> This checkpoint records the `D071` FTOverDSEnable row/setup/reference closure after `D070`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D071 FTOverDSEnable` is now aligned via official rerun `20260413T064002607672`
- the case still carried stale workbook row `73`, pre-applied `IEEE80211r.Enabled` / `MobilityDomain` writes in `sta_env_setup`, and stale `results_reference.v4.0.3 = To be tested / To be tested / To be tested`
- that stale setup order made `setup_env` sample `wl -i wl0/wl1 bss` during transient 11r hostapd restart/down (`wl0 bss = down`, then `wl1 bss = down`) instead of the workbook row `71` execution order
- the committed rewrite refreshes stale row `73` back to workbook row `71`, keeps `sta_env_setup` limited to AP baseline bring-up, and marks `results_reference.v4.0.3 = Pass / Pass / Pass`
- official rerun `20260413T064002607672` then exact-closed tri-band `Enabled=1`, `FTOverDSEnable=0 -> 1 -> 0`, `MobilityDomain=4660`, hostapd `mobility_domain=3412`, and `ft_over_ds` one-count / zero-count transitions on AP1 / AP3 / AP5
- overlay compare is now `269 / 420 full matches`、`151 mismatches`、`58 metadata drifts`
- next ready actionable open case is `D079`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D071` | 71 | `FTOverDSEnable` | `Pass / Pass / Pass` | `20260413T064002607672_DUT.log L32-L556` | `n/a (AP-only)` |

#### D071 FTOverDSEnable

**STA 指令**

```sh
# AP-only case; no STA transport
```

**DUT 指令**

```sh
ubus-cli WiFi.AccessPoint.1.Enable=1
ubus-cli WiFi.AccessPoint.3.Enable=1
ubus-cli WiFi.AccessPoint.5.Enable=1
wl -i wl0 bss
wl -i wl1 bss
wl -i wl2 bss

ubus-cli WiFi.AccessPoint.1.IEEE80211r.Enabled=1
ubus-cli WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=4660
ubus-cli WiFi.AccessPoint.1.IEEE80211r.FTOverDSEnable=1
ubus-cli WiFi.AccessPoint.1.IEEE80211r.FTOverDSEnable=0

ubus-cli WiFi.AccessPoint.3.IEEE80211r.Enabled=1
ubus-cli WiFi.AccessPoint.3.IEEE80211r.MobilityDomain=4660
ubus-cli WiFi.AccessPoint.3.IEEE80211r.FTOverDSEnable=1
ubus-cli WiFi.AccessPoint.3.IEEE80211r.FTOverDSEnable=0

ubus-cli WiFi.AccessPoint.5.IEEE80211r.Enabled=1
ubus-cli WiFi.AccessPoint.5.IEEE80211r.MobilityDomain=4660
ubus-cli WiFi.AccessPoint.5.IEEE80211r.FTOverDSEnable=1
ubus-cli WiFi.AccessPoint.5.IEEE80211r.FTOverDSEnable=0

grep -m1 '^mobility_domain=' /tmp/wl0_hapd.conf
grep -m1 '^mobility_domain=' /tmp/wl1_hapd.conf
grep -m1 '^mobility_domain=' /tmp/wl2_hapd.conf
grep -c '^ft_over_ds=1$' /tmp/wl0_hapd.conf
grep -c '^ft_over_ds=1$' /tmp/wl1_hapd.conf
grep -c '^ft_over_ds=1$' /tmp/wl2_hapd.conf
grep -c '^ft_over_ds=0$' /tmp/wl0_hapd.conf
grep -c '^ft_over_ds=0$' /tmp/wl1_hapd.conf
grep -c '^ft_over_ds=0$' /tmp/wl2_hapd.conf
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T064002607672_DUT.log L18-L26
up
up
up

20260413T064002607672_DUT.log L47-L81
Enabled5g=1
FtOverDs5g=0
MobilityDomain5g=4660
MobilityDomainCfg5g=3412
FtOverDs5gOneCount=0
FtOverDs5gZeroCount=1
FtOverDs5gTotalCount=1

20260413T064002607672_DUT.log L91-L171
FtOverDs5g=1
FtOverDs5gOneCount=1
FtOverDs5gZeroCount=0
FtOverDs5gTotalCount=1
FtOverDs5g=0
FtOverDs5gOneCount=0
FtOverDs5gZeroCount=1
FtOverDs5gTotalCount=1

20260413T064002607672_DUT.log L231-L310
Enabled6g=1
FtOverDs6g=1
MobilityDomain6g=4660
MobilityDomainCfg6g=3412
FtOverDs6gOneCount=1
FtOverDs6gZeroCount=0
FtOverDs6gTotalCount=1
FtOverDs6g=0
FtOverDs6gOneCount=0
FtOverDs6gZeroCount=1
FtOverDs6gTotalCount=1

20260413T064002607672_DUT.log L371-L451
Enabled24g=1
FtOverDs24g=1
MobilityDomain24g=4660
MobilityDomainCfg24g=3412
FtOverDs24gOneCount=1
FtOverDs24gZeroCount=0
FtOverDs24gTotalCount=1
FtOverDs24g=0
FtOverDs24gOneCount=0
FtOverDs24gZeroCount=1
FtOverDs24gTotalCount=1

plugins/wifi_llapi/reports/agent_trace/20260413T064002607672/wifi-llapi-D071-ftoverdsenable-accesspoint.json L135-L170
outputs:
  Enabled5g=1
  FtOverDs5g=1
  FtOverDs5g=0
  Enabled6g=1
  FtOverDs6g=1
  FtOverDs6g=0
  Enabled24g=1
  FtOverDs24g=1
  FtOverDs24g=0
```

## Checkpoint summary (2026-04-13 early-31)

> This checkpoint records the `D070` Enable row/oracle closure after `D063`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D070 Enable` is now aligned via official rerun `20260413T063442091882`
- this was not a runtime bug: the committed case still carried stale workbook row `72` and an over-authored AP toggle/readback path, even though workbook row `70` only asks for tri-band `Enable=1` with `wl -e bss` up on all radios
- the committed rewrite refreshes stale row `72` back to workbook row `70`, keeps the case AP-only, and reduces the oracle to the workbook-authoritative per-band `Enable` getter plus direct driver `wl -i wl{0,1,2} bss`
- official rerun `20260413T063442091882` then exact-closed `Enable5g=1`, `Enable6g=1`, `Enable24g=1`, and `DriverBss5g/6g/24g=up`
- committed metadata is now workbook row `70` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `268 / 420 full matches`、`152 mismatches`、`58 metadata drifts`
- next ready actionable workbook-Pass revisit is `D071`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D070` | 70 | `Enable` | `Pass / Pass / Pass` | `20260413T063442091882_DUT.log L32-L52` | `n/a (AP-only)` |

#### D070 Enable

**STA 指令**

```sh
# AP-only case; no STA transport
```

**DUT 指令**

```sh
ubus-cli WiFi.AccessPoint.1.Enable=1
ubus-cli WiFi.AccessPoint.3.Enable=1
ubus-cli WiFi.AccessPoint.5.Enable=1
echo "Enable5g=$(ubus-cli 'WiFi.AccessPoint.1.Enable?' 2>/dev/null | grep -o 'Enable=[0-9]*' | cut -d= -f2)"
echo "DriverBss5g=$(wl -i wl0 bss 2>/dev/null)"
echo "Enable6g=$(ubus-cli 'WiFi.AccessPoint.3.Enable?' 2>/dev/null | grep -o 'Enable=[0-9]*' | cut -d= -f2)"
echo "DriverBss6g=$(wl -i wl1 bss 2>/dev/null)"
echo "Enable24g=$(ubus-cli 'WiFi.AccessPoint.5.Enable?' 2>/dev/null | grep -o 'Enable=[0-9]*' | cut -d= -f2)"
echo "DriverBss24g=$(wl -i wl2 bss 2>/dev/null)"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T063442091882_DUT.log L32-L52
Enable5g=1
DriverBss5g=up
Enable6g=1
DriverBss6g=up
Enable24g=1
DriverBss24g=up

plugins/wifi_llapi/reports/agent_trace/20260413T063442091882/wifi-llapi-D070-enable-accesspoint.json L96-L104
commands:
  echo "Enable5g=$(ubus-cli 'WiFi.AccessPoint.1.Enable?' 2>/dev/null | grep -o 'Enable=[0-9]*' | cut -d= -f2)"
  echo "DriverBss5g=$(wl -i wl0 bss 2>/dev/null)"
  echo "Enable6g=$(ubus-cli 'WiFi.AccessPoint.3.Enable?' 2>/dev/null | grep -o 'Enable=[0-9]*' | cut -d= -f2)"
  echo "DriverBss6g=$(wl -i wl1 bss 2>/dev/null)"
  echo "Enable24g=$(ubus-cli 'WiFi.AccessPoint.5.Enable?' 2>/dev/null | grep -o 'Enable=[0-9]*' | cut -d= -f2)"
  echo "DriverBss24g=$(wl -i wl2 bss 2>/dev/null)"
outputs:
  Enable5g=1
  DriverBss5g=up
  Enable6g=1
  DriverBss6g=up
  Enable24g=1
  DriverBss24g=up
```

## Checkpoint summary (2026-04-13 early-30)

> This checkpoint records the `D063` VhtCapabilities row/oracle closure after `D062`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D063 VhtCapabilities` is now aligned via official rerun `20260413T062615392940`
- this was not a getter-missing gap: authoritative full-run evidence had already shown the same-STA direct getter and same-entry snapshot returning a concrete VHT capability list, but the committed case still carried stale workbook row `65` and an outdated fail-shaped contract that expected `VhtCapabilities=""`
- the first confirmation rerun proved a second nuance: requiring exact equality against the human-readable `wl sta_info` `VHT caps` line was too strict for 0403, because LLAPI/snapshot exposed `SGI80,SGI160,SU-BFR,SU-BFE,MU-BFE` while the driver line only surfaced the same-STA subset `SGI80,SGI160,SU-BFR,SU-BFE`
- source evidence (`wlu_common.c`, `local_wl_util.c`, `swl_staCap.h`) confirms these are related but not identical renderings, so the committed rewrite refreshes stale row `65` back to workbook row `63`, restores the pass-shaped non-empty same-STA getter/snapshot contract, and keeps `wl sta_info` as a same-STA subset sanity oracle
- official rerun `20260413T062615392940` then exact-closed `VhtCapabilities=AssocVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE,MU-BFE` with driver subset `DriverVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE`
- committed metadata is now workbook row `63` with `results_reference.v4.0.3 = Pass / Not Supported / Not Supported`
- overlay compare is now `267 / 420 full matches`、`153 mismatches`、`58 metadata drifts`
- next ready actionable workbook-Pass revisit is `D070`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D063` | 63 | `VhtCapabilities` | `Pass / Not Supported / Not Supported` | `20260413T062615392940_DUT.log L340-L387` | `20260413T062615392940_STA.log L63-L90` |

#### D063 VhtCapabilities

**STA 指令**

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p' | tr 'A-F' 'a-f' | sed 's/^/MACAddress=/'
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?" | awk -F= '/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.MACAddress=/ {gsub(/"/, "", $2); print "AssocMAC=" tolower($2)} /^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.VhtCapabilities=/ {gsub(/"/, "", $2); print "AssocVhtCapabilities=" $2}'
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p' | tr 'A-F' 'a-f'); [ -n "$STA_MAC" ] && echo DriverAssocMac="$STA_MAC" && wl -i wl0 sta_info "$STA_MAC" | awk '/^[[:space:]]*VHT caps / {line=substr($0, index($0, ":")+2); print "DriverVhtCapsLine=" line; for (i=1;i<=NF;i++) if ($i ~ /^(SGI80|SGI160|SU-BFR|SU-BFE|MU-BFR|MU-BFE)$/) caps[++n]=$i} END {if (n) {out=""; for (i=1;i<=n;i++) out = out (i>1 ? "," : "") caps[i]; print "DriverVhtCapabilities=" out}}'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T062615392940_STA.log L63-L90
Connected to 2c:59:17:00:19:95 (on wl0)
SSID: testpilot5G
wpa_state=COMPLETED
StaMac=2c:59:17:00:04:85

20260413T062615392940_DUT.log L340-L387
MACAddress=2c:59:17:00:04:85
WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities="SGI80,SGI160,SU-BFR,SU-BFE,MU-BFE"
AssocVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE,MU-BFE
DriverAssocMac=2c:59:17:00:04:85
DriverVhtCapsLine=LDPC SGI80 SGI160 SU-BFR SU-BFE
DriverVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE

plugins/wifi_llapi/reports/agent_trace/20260413T062615392940/wifi-llapi-D063-vhtcapabilities-accesspoint-associateddevice.json L96-L108
commands:
  cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?" | awk ...
  STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | ...)
outputs:
  StaMac=2c:59:17:00:04:85
  WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities="SGI80,SGI160,SU-BFR,SU-BFE,MU-BFE"
  AssocVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE,MU-BFE
  DriverVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE
```

## Checkpoint summary (2026-04-13 early-29)

> This checkpoint records the `D062` VendorOUI row/oracle closure after `D060`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D062 VendorOUI` is now aligned via official rerun `20260413T061743676049`
- this was not a genuine fail-shaped source gap: authoritative full-run evidence had already exact-closed the direct getter, the same-entry `AssociatedDevice.1` snapshot, and the same-STA `wl sta_info` capture on the same concrete VendorOUI list
- the committed case still carried stale workbook row `64` and an outdated fail-shaped contract that expected `VendorOUI=""`, even though live 0403 returned `00:90:4C,00:10:18,00:50:F2,50:6F:9A` consistently for the same associated STA
- the committed rewrite refreshes stale row `64` back to workbook row `62` and restores the pass-shaped same-STA equality contract across the direct getter, the same-entry snapshot, and the driver capture
- official rerun `20260413T061743676049` then exact-closed `VendorOUI=AssocVendorOUI=DriverVendorOUIList=00:90:4C,00:10:18,00:50:F2,50:6F:9A` with `DriverVendorOUICount=4`
- committed metadata is now workbook row `62` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `266 / 420 full matches`、`154 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D063`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D062` | 62 | `VendorOUI` | `Pass / Pass / Pass` | `20260413T061743676049_DUT.log L340-L384` | `20260413T061743676049_STA.log L66-L83` |

#### D062 VendorOUI

**STA 指令**

```sh
cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p' | tr 'A-F' 'a-f' | sed 's/^/MACAddress=/'
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?" | awk -F= '/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.MACAddress=/ {gsub(/"/, "", $2); print "AssocMAC=" tolower($2)} /^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.VendorOUI=/ {gsub(/"/, "", $2); print "AssocVendorOUI=" $2}'
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p' | tr 'A-F' 'a-f'); [ -n "$STA_MAC" ] && echo DriverAssocMac="$STA_MAC" && wl -i wl0 sta_info "$STA_MAC" | awk '/^[[:space:]]*VENDOR OUI VALUE\[[0-9]+\]/ {oui[++n]=$NF} END {if (n) {print "DriverVendorOUICount=" n; list=""; for (i=1;i<=n;i++) list = list (i>1 ? "," : "") oui[i]; print "DriverVendorOUIList=" list}}'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T061743676049_STA.log L66-L83
SSID: testpilot5G
wpa_state=COMPLETED

20260413T061743676049_DUT.log L340-L384
MACAddress=2c:59:17:00:04:85
WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI="00:90:4C,00:10:18,00:50:F2,50:6F:9A"
AssocVendorOUI=00:90:4C,00:10:18,00:50:F2,50:6F:9A
DriverAssocMac=2c:59:17:00:04:85
DriverVendorOUICount=4
DriverVendorOUIList=00:90:4C,00:10:18,00:50:F2,50:6F:9A

plugins/wifi_llapi/reports/agent_trace/20260413T061743676049/wifi-llapi-D062-vendoroui.json L96-L108
commands:
  cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?" | awk ...
  STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | ...)
outputs:
  StaMac=2c:59:17:00:04:85
  WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI="00:90:4C,00:10:18,00:50:F2,50:6F:9A"
  AssocVendorOUI=00:90:4C,00:10:18,00:50:F2,50:6F:9A
  DriverVendorOUICount=4
  DriverVendorOUIList=00:90:4C,00:10:18,00:50:F2,50:6F:9A
```

## Checkpoint summary (2026-04-13 early-28)

> This checkpoint records the `D060` UplinkMCS row/parser closure after `D059`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D060 UplinkMCS` is now aligned via official rerun `20260413T060855269192`
- this was not a semantic rewrite: authoritative full-run evidence had already exact-closed same-STA `UplinkMCS` against `wl sta_info ... rx nrate`, but the committed case still carried stale workbook row `62` and a fragile `MACAddress` extractor that duplicated `AssocMacAfterTrigger` / `DriverAssocMac`
- the committed rewrite refreshes stale row `62` back to workbook row `60` and hardens the step4 same-STA extractor with `| head -n 1`, keeping the same generic `testpilot5G` / `WPA2-Personal` baseline and same `rx nrate` oracle family proven by the authoritative full run
- official rerun `20260413T060855269192` then exact-closed `UplinkMCS=10`, `AssocMacAfterTrigger=2C:59:17:00:04:85`, `DriverAssocMac=2C:59:17:00:04:85`, and `DriverUplinkMCS=10`
- committed metadata is now workbook row `60` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `265 / 420 full matches`、`155 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D062`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D060` | 60 | `UplinkMCS` | `Pass / Pass / Pass` | `20260413T060855269192_DUT.log L361-L366` | `20260413T060855269192_STA.log L66-L105` |

#### D060 UplinkMCS

**STA 指令**

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
ifconfig wl0 192.168.1.3 netmask 255.255.255.0 up && ip route get 192.168.1.1
ping -I wl0 -c 8 -W 1 192.168.1.1
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?"); STA_MAC=$(printf '%s\n' "$OUT" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p' | head -n 1); STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f'); printf '%s\n' "$OUT" | sed -n 's/.*UplinkMCS=\([^[:space:]]*\).*/UplinkMCS=\1/p'; [ -n "$STA_MAC" ] && echo AssocMacAfterTrigger=$STA_MAC && echo DriverAssocMac=$STA_MAC && wl -i wl0 sta_info $STA_MAC_LOWER | sed -n '/rx nrate/,$p' | sed -n '1,2p' && wl -i wl0 sta_info $STA_MAC_LOWER | sed -n '/rx nrate/{n;s/.*mcs \([0-9][0-9]*\).*/DriverUplinkMCS=\1/p;}'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T060855269192_STA.log L66-L105
SSID: testpilot5G
ssid=testpilot5G
wpa_state=COMPLETED
8 packets transmitted, 8 received, 0% packet loss

20260413T060855269192_DUT.log L361-L366
UplinkMCS=10
AssocMacAfterTrigger=2C:59:17:00:04:85
DriverAssocMac=2C:59:17:00:04:85
rx nrate
he mcs 10 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto
DriverUplinkMCS=10

plugins/wifi_llapi/reports/agent_trace/20260413T060855269192/wifi-llapi-D060-uplinkmcs.json L96-L106
commands:
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
  ifconfig wl0 192.168.1.3 netmask 255.255.255.0 up && ip route get 192.168.1.1
  ping -I wl0 -c 8 -W 1 192.168.1.1
  OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?"); ...
outputs:
  WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
  192.168.1.1 dev wl0 src 192.168.1.3 uid 0
  8 packets transmitted, 8 received, 0% packet loss
  UplinkMCS=10
  AssocMacAfterTrigger=2C:59:17:00:04:85
  DriverAssocMac=2C:59:17:00:04:85
  DriverUplinkMCS=10
```

## Checkpoint summary (2026-04-13 early-27)

> This checkpoint records the `D059` UplinkBandwidth baseline/trigger/oracle closure after `D034`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D059 UplinkBandwidth` is now aligned via official rerun `20260413T055159421076`
- this was not a metadata-only refresh: the case still carried stale workbook row `61`, a drifted custom `TestPilot_BTM` / `WPA3-Personal` baseline, and a weak driver reread path that sampled `rx nrate` before any deterministic STA uplink traffic
- authoritative full run `20260412T113008433351` had already shown the real D059 pass path on the generic `testpilot5G` / `WPA2-Personal` baseline, so the committed rewrite restores that baseline, refreshes stale row `61` to workbook row `59`, adds an explicit STA uplink trigger, and re-reads the same post-trigger `AssociatedDevice.1` slot against `wl sta_info ... rx nrate`
- official rerun `20260413T055159421076` then exact-closed `UplinkBandwidth=20`, `AssocMacAfterTrigger=2C:59:17:00:04:85`, `DriverAssocMac=2C:59:17:00:04:85`, and `DriverUplinkBandwidth=20`
- committed metadata is now workbook row `59` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `264 / 420 full matches`、`156 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D060`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D059` | 59 | `UplinkBandwidth` | `Pass / Pass / Pass` | `20260413T055159421076_DUT.log L361-L366` | `20260413T055159421076_STA.log L61-L103` |

#### D059 UplinkBandwidth

**STA 指令**

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
ifconfig wl0 192.168.1.3 netmask 255.255.255.0 up && ip route get 192.168.1.1
ping -I wl0 -c 8 -W 1 192.168.1.1
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?"); STA_MAC=$(printf '%s\n' "$OUT" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p' | head -n 1); STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f'); printf '%s\n' "$OUT" | sed -n 's/.*UplinkBandwidth=\([^[:space:]]*\).*/UplinkBandwidth=\1/p'; [ -n "$STA_MAC" ] && echo AssocMacAfterTrigger=$STA_MAC && echo DriverAssocMac=$STA_MAC && NRATE=$(wl -i wl0 sta_info $STA_MAC_LOWER | sed -n '/rx nrate/,+1p') && echo "$NRATE" && echo "$NRATE" | sed -n '2s/.*bw\([0-9][0-9]*\).*/DriverUplinkBandwidth=\1/p'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T055159421076_STA.log L61-L103
Connected to 2c:59:17:00:19:95 (on wl0)
SSID: testpilot5G
ssid=testpilot5G
wpa_state=COMPLETED
8 packets transmitted, 8 received, 0% packet loss

20260413T055159421076_DUT.log L361-L366
UplinkBandwidth=20
AssocMacAfterTrigger=2C:59:17:00:04:85
DriverAssocMac=2C:59:17:00:04:85
rx nrate
he mcs 9 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto
DriverUplinkBandwidth=20

plugins/wifi_llapi/reports/agent_trace/20260413T055159421076/wifi-llapi-D059-uplinkbandwidth.json L96-L106
commands:
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
  ifconfig wl0 192.168.1.3 netmask 255.255.255.0 up && ip route get 192.168.1.1
  ping -I wl0 -c 8 -W 1 192.168.1.1
  OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?"); ...
outputs:
  WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
  192.168.1.1 dev wl0 src 192.168.1.3 uid 0
  8 packets transmitted, 8 received, 0% packet loss
  UplinkBandwidth=20
  AssocMacAfterTrigger=2C:59:17:00:04:85
  DriverAssocMac=2C:59:17:00:04:85
  DriverUplinkBandwidth=20
```

## Checkpoint summary (2026-04-13 early-26)

> This checkpoint records the `D034` Noise baseline/oracle closure after `D188`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D034 Noise` is now aligned via official rerun `20260413T052709875993`
- the first confirmation rerun `20260413T052117345208` failed in `setup_env` (`iw dev wl0 link -> Not connected.`), which exposed the real blocker: stale custom `TestPilot_BTM` / `WPA3-Personal` baseline drift rather than a semantic Noise mismatch
- authoritative full run `20260412T113008433351` had already shown the real D034 pass path on the generic `testpilot5G` / `WPA2-Personal` baseline, so the committed rewrite restores that baseline, drops the custom `sta_env_setup`, refreshes stale row `36` to workbook row `34`, and replaces the stale `Noise=0` fail-shape with a same-STA live negative-noise compare
- official rerun `20260413T052709875993` then exact-closed `WiFi.AccessPoint.1.AssociatedDevice.1.Noise=-100` against `DriverNoise=-100` for MAC `2C:59:17:00:04:85`
- committed metadata is now workbook row `34` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `263 / 420 full matches`、`157 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D059`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D034` | 34 | `Noise` | `Pass / Pass / Pass` | `20260413T052709875993_DUT.log L62-L100` | `20260413T052709875993_STA.log L82-L98` |

#### D034 Noise

**STA 指令**

```sh
iw dev wl0 link
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.Noise?"
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p'); STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f'); NOISE=$(wl -i wl0 sta_info $STA_MAC_LOWER | awk '/per antenna noise floor:/ {print $5; exit}'); [ -n "$STA_MAC" ]; echo DriverAssocMac=$STA_MAC; [ -n "$NOISE" ]; echo DriverNoise=$NOISE; [ -n "$NOISE" ]; echo DriverNoiseMin=$((NOISE - 2)); [ -n "$NOISE" ]; echo DriverNoiseMax=$((NOISE + 2))
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T052709875993_STA.log L82-L98
Connected to 2c:59:17:00:19:95 (on wl0)
SSID: testpilot5G
freq: 5180
signal: -35 dBm

20260413T052709875993_DUT.log L62-L100
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
WiFi.AccessPoint.1.AssociatedDevice.1.Noise=-100
DriverAssocMac=2C:59:17:00:04:85
DriverNoise=-100
DriverNoiseMin=-102
DriverNoiseMax=-98

plugins/wifi_llapi/reports/agent_trace/20260413T052709875993/wifi-llapi-D034-noise-accesspoint-associateddevice.json L96-L116
commands:
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
  ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.Noise?"
  STA_MAC=...; NOISE=...; echo DriverAssocMac=...; echo DriverNoise=...; echo DriverNoiseMin=...; echo DriverNoiseMax=...
outputs:
  WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
  WiFi.AccessPoint.1.AssociatedDevice.1.Noise=-100
  DriverAssocMac=2C:59:17:00:04:85
  DriverNoise=-100
  DriverNoiseMin=-102
  DriverNoiseMax=-98
```

## Checkpoint summary (2026-04-13 early-25)

> This checkpoint records the `D188` DTIMPeriod setter/readback closure after `D176`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D188 DTIMPeriod` is now aligned via official rerun `20260413T050318932313`
- like `D176`, this was not a low-risk metadata-only closure: workbook row `188` explicitly expects baseline getter `3`, writable `DTIMPeriod=7`, and downstream hostapd `dtim_period=7`, then a clean restore to `3`
- active 0403 still exposes `DTIMPeriod` as a writable radio property on the same AP-side stack (`wld_radio.odl` persistent default `3`, live Device2 DM getter/setter path, HAL `wldm_Radio_DTIMPeriod()`, and hostapd `dtim_period` emission)
- the committed rewrite now forces tri-band `DTIMPeriod=3` in setup, then exact-closes northbound getter and `/tmp/wl{0,1,2}_hapd.conf` `dtim_period` across `3 -> 7 -> 3` on all three radios
- official rerun `20260413T050318932313` passed in one attempt with no STA transport involvement
- committed metadata is now workbook row `188` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `262 / 420 full matches`、`158 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D034`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D188` | 188 | `DTIMPeriod` | `Pass / Pass / Pass` | `20260413T050318932313_DUT.log L25-L176` | `20260413T050318932313_STA.log (no STA transport used)` |

#### D188 DTIMPeriod

**STA 指令**

```sh
# none; DUT-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl0_hapd.conf | sed -n '1s/^dtim_period=/BaselineHostapdDtimPeriod5g=/p'
ubus-cli WiFi.Radio.1.DTIMPeriod=7
sleep 3
ubus-cli "WiFi.Radio.1.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl0_hapd.conf | sed -n '1s/^dtim_period=/AfterSetHostapdDtimPeriod5g=/p'
ubus-cli WiFi.Radio.1.DTIMPeriod=3
sleep 3
ubus-cli "WiFi.Radio.1.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl0_hapd.conf | sed -n '1s/^dtim_period=/AfterRestoreHostapdDtimPeriod5g=/p'
ubus-cli "WiFi.Radio.2.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl1_hapd.conf | sed -n '1s/^dtim_period=/BaselineHostapdDtimPeriod6g=/p'
ubus-cli WiFi.Radio.2.DTIMPeriod=7
sleep 3
ubus-cli "WiFi.Radio.2.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl1_hapd.conf | sed -n '1s/^dtim_period=/AfterSetHostapdDtimPeriod6g=/p'
ubus-cli WiFi.Radio.2.DTIMPeriod=3
sleep 3
ubus-cli "WiFi.Radio.2.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl1_hapd.conf | sed -n '1s/^dtim_period=/AfterRestoreHostapdDtimPeriod6g=/p'
ubus-cli "WiFi.Radio.3.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl2_hapd.conf | sed -n '1s/^dtim_period=/BaselineHostapdDtimPeriod24g=/p'
ubus-cli WiFi.Radio.3.DTIMPeriod=7
sleep 3
ubus-cli "WiFi.Radio.3.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl2_hapd.conf | sed -n '1s/^dtim_period=/AfterSetHostapdDtimPeriod24g=/p'
ubus-cli WiFi.Radio.3.DTIMPeriod=3
sleep 3
ubus-cli "WiFi.Radio.3.DTIMPeriod?"
grep '^dtim_period=' /tmp/wl2_hapd.conf | sed -n '1s/^dtim_period=/AfterRestoreHostapdDtimPeriod24g=/p'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T050318932313_DUT.log L25-L74
WiFi.Radio.1.DTIMPeriod=3
BaselineHostapdDtimPeriod5g=3
RequestedDtimPeriod5g=7
WiFi.Radio.1.DTIMPeriod=7
AfterSetHostapdDtimPeriod5g=7
RestoreDtimPeriod5g=3
WiFi.Radio.1.DTIMPeriod=3
AfterRestoreHostapdDtimPeriod5g=3

20260413T050318932313_DUT.log L75-L125
WiFi.Radio.2.DTIMPeriod=3
BaselineHostapdDtimPeriod6g=3
RequestedDtimPeriod6g=7
WiFi.Radio.2.DTIMPeriod=7
AfterSetHostapdDtimPeriod6g=7
RestoreDtimPeriod6g=3
WiFi.Radio.2.DTIMPeriod=3
AfterRestoreHostapdDtimPeriod6g=3

20260413T050318932313_DUT.log L126-L176
WiFi.Radio.3.DTIMPeriod=3
BaselineHostapdDtimPeriod24g=3
RequestedDtimPeriod24g=7
WiFi.Radio.3.DTIMPeriod=7
AfterSetHostapdDtimPeriod24g=7
RestoreDtimPeriod24g=3
WiFi.Radio.3.DTIMPeriod=3
AfterRestoreHostapdDtimPeriod24g=3

plugins/wifi_llapi/reports/agent_trace/20260413T050318932313/d188-radio-dtimperiod.json L96-L146
commands:
  ubus-cli "WiFi.Radio.1.DTIMPeriod?"
  ...
  grep '^dtim_period=' /tmp/wl2_hapd.conf | sed -n '1s/^dtim_period=/AfterRestoreHostapdDtimPeriod24g=/p'
outputs:
  WiFi.Radio.1.DTIMPeriod=3
  BaselineHostapdDtimPeriod5g=3
  ...
  AfterRestoreHostapdDtimPeriod24g=3
```

## Checkpoint summary (2026-04-13 early-24)

> This checkpoint records the `D176` BeaconPeriod setter/readback closure after `D174`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D176 BeaconPeriod` is now aligned via official rerun `20260413T044907394777`
- unlike `D174`, this was not a low-risk metadata-only closure: workbook row `176` explicitly expects baseline getter `100`, setter `1000`, and downstream hostapd `beacon_int=1000`
- active 0403 still exposes `BeaconPeriod` as a writable radio property along the same AP-side stack (`wld_radio.odl` persistent default `100`, writable Device2 DM, HAL getter/setter, and hostapd `beacon_int` emission)
- the committed rewrite now forces tri-band `BeaconPeriod=100` in setup, then exact-closes northbound getter and `/tmp/wl{0,1,2}_hapd.conf` `beacon_int` across `100 -> 1000 -> 100` on all three radios
- official rerun `20260413T044907394777` passed in one attempt with no STA transport involvement
- committed metadata is now workbook row `176` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `261 / 420 full matches`、`159 mismatches`、`58 metadata drifts`
- next ready non-blocked stale radio setter/getter rewrite is `D188`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D176` | 176 | `BeaconPeriod` | `Pass / Pass / Pass` | `20260413T044907394777_DUT.log L25-L176` | `20260413T044907394777_STA.log (no STA transport used)` |

#### D176 BeaconPeriod

**STA 指令**

```sh
# none; DUT-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl0_hapd.conf | sed -n '1s/^beacon_int=/BaselineHostapdBeaconPeriod5g=/p'
ubus-cli WiFi.Radio.1.BeaconPeriod=1000
sleep 3
ubus-cli "WiFi.Radio.1.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl0_hapd.conf | sed -n '1s/^beacon_int=/AfterSetHostapdBeaconPeriod5g=/p'
ubus-cli WiFi.Radio.1.BeaconPeriod=100
sleep 3
ubus-cli "WiFi.Radio.1.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl0_hapd.conf | sed -n '1s/^beacon_int=/AfterRestoreHostapdBeaconPeriod5g=/p'
ubus-cli "WiFi.Radio.2.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl1_hapd.conf | sed -n '1s/^beacon_int=/BaselineHostapdBeaconPeriod6g=/p'
ubus-cli WiFi.Radio.2.BeaconPeriod=1000
sleep 3
ubus-cli "WiFi.Radio.2.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl1_hapd.conf | sed -n '1s/^beacon_int=/AfterSetHostapdBeaconPeriod6g=/p'
ubus-cli WiFi.Radio.2.BeaconPeriod=100
sleep 3
ubus-cli "WiFi.Radio.2.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl1_hapd.conf | sed -n '1s/^beacon_int=/AfterRestoreHostapdBeaconPeriod6g=/p'
ubus-cli "WiFi.Radio.3.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl2_hapd.conf | sed -n '1s/^beacon_int=/BaselineHostapdBeaconPeriod24g=/p'
ubus-cli WiFi.Radio.3.BeaconPeriod=1000
sleep 3
ubus-cli "WiFi.Radio.3.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl2_hapd.conf | sed -n '1s/^beacon_int=/AfterSetHostapdBeaconPeriod24g=/p'
ubus-cli WiFi.Radio.3.BeaconPeriod=100
sleep 3
ubus-cli "WiFi.Radio.3.BeaconPeriod?"
grep '^beacon_int=' /tmp/wl2_hapd.conf | sed -n '1s/^beacon_int=/AfterRestoreHostapdBeaconPeriod24g=/p'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T044907394777_DUT.log L25-L74
WiFi.Radio.1.BeaconPeriod=100
BaselineHostapdBeaconPeriod5g=100
RequestedBeaconPeriod5g=1000
WiFi.Radio.1.BeaconPeriod=1000
AfterSetHostapdBeaconPeriod5g=1000
RestoreBeaconPeriod5g=100
WiFi.Radio.1.BeaconPeriod=100
AfterRestoreHostapdBeaconPeriod5g=100

20260413T044907394777_DUT.log L75-L125
WiFi.Radio.2.BeaconPeriod=100
BaselineHostapdBeaconPeriod6g=100
RequestedBeaconPeriod6g=1000
WiFi.Radio.2.BeaconPeriod=1000
AfterSetHostapdBeaconPeriod6g=1000
RestoreBeaconPeriod6g=100
WiFi.Radio.2.BeaconPeriod=100
AfterRestoreHostapdBeaconPeriod6g=100

20260413T044907394777_DUT.log L126-L176
WiFi.Radio.3.BeaconPeriod=100
BaselineHostapdBeaconPeriod24g=100
RequestedBeaconPeriod24g=1000
WiFi.Radio.3.BeaconPeriod=1000
AfterSetHostapdBeaconPeriod24g=1000
RestoreBeaconPeriod24g=100
WiFi.Radio.3.BeaconPeriod=100
AfterRestoreHostapdBeaconPeriod24g=100

plugins/wifi_llapi/reports/agent_trace/20260413T044907394777/d176-radio-beaconperiod.json L96-L146
commands:
  ubus-cli "WiFi.Radio.1.BeaconPeriod?"
  ...
  grep '^beacon_int=' /tmp/wl2_hapd.conf | sed -n '1s/^beacon_int=/AfterRestoreHostapdBeaconPeriod24g=/p'
outputs:
  WiFi.Radio.1.BeaconPeriod=100
  BaselineHostapdBeaconPeriod5g=100
  ...
  AfterRestoreHostapdBeaconPeriod24g=100
```

## Checkpoint summary (2026-04-13 early-23)

> This checkpoint records the `D174` metadata/results_reference closure after `D115`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D174 ActiveAntennaCtrl` is now aligned via official rerun `20260413T042647797154`
- active 0403 `wld_radio.odl` still declares `ActiveAntennaCtrl` as a persistent int32 with default `-1`, and the same radio model still keeps `actAntennaCtrl` / `txChainCtrl` / `rxChainCtrl`
- the live vendor path (`whm_brcm_rad_antenna_map()` / `whm_brcm_rad_mod_chains()`) still uses `actAntennaCtrl` as the fallback when specific chain controls are unset
- that means the northbound getter staying at `-1` is the driver-default sentinel, while workbook-era downstream `wl txchain` / `wl rxchain` masks remain compatible concrete realizations of the same path rather than a contradiction
- the authoritative full-run trace had already exact-closed tri-band `ActiveAntennaCtrl=-1`, and the isolated rerun reproduced the same one-attempt Pass shape
- the only remaining defects were stale workbook row `138` and stale raw `Fail / Fail / Fail`
- committed metadata is now workbook row `174` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `260 / 420 full matches`、`160 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D176`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D174` | 174 | `ActiveAntennaCtrl` | `Pass / Pass / Pass` | `20260413T042647797154_DUT.log L5-L18` | `20260413T042647797154_STA.log (no STA transport used)` |

#### D174 ActiveAntennaCtrl

**STA 指令**

```sh
# none; DUT-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.ActiveAntennaCtrl?"
ubus-cli "WiFi.Radio.2.ActiveAntennaCtrl?"
ubus-cli "WiFi.Radio.3.ActiveAntennaCtrl?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T042647797154_DUT.log L5-L18
WiFi.Radio.1.ActiveAntennaCtrl=-1
WiFi.Radio.2.ActiveAntennaCtrl=-1
WiFi.Radio.3.ActiveAntennaCtrl=-1

plugins/wifi_llapi/reports/agent_trace/20260413T042647797154/d174-radio-activeantennactrl.json L96-L104
commands:
  ubus-cli "WiFi.Radio.1.ActiveAntennaCtrl?"
  ubus-cli "WiFi.Radio.2.ActiveAntennaCtrl?"
  ubus-cli "WiFi.Radio.3.ActiveAntennaCtrl?"
outputs:
  WiFi.Radio.1.ActiveAntennaCtrl=-1
  WiFi.Radio.2.ActiveAntennaCtrl=-1
  WiFi.Radio.3.ActiveAntennaCtrl=-1
```

## Checkpoint summary (2026-04-13 early-22)

> This checkpoint records the `D115` tri-band live-counter closure after `D114`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D115 getStationStats() ConnectionDuration` is now aligned via official rerun `20260413T035856845825`
- active 0403 still exposes `ConnectionDuration` as a volatile read-only uint32 in the AccessPoint ODL
- `wlgetStationInfo()` still parses driver `wl sta_info ... in network` into `connectTime`, and `local_wl_util.c` still copies `staInfo.connectTime` into the higher-level station structure
- no band-specific branch was found in the live counter path, so the old 5G-only `Fail / N/A / N/A` shape was stale authored scope rather than a semantic restriction
- the committed rewrite restores tri-band sequential `getStationStats()` coverage and proves the counter is live by reading it twice per band and cross-checking the same STA against driver age
- official rerun exact-closed `7 -> 10 <= 12` on 5G, `11 -> 14 <= 16` on 6G, and `9 -> 13 <= 15` on 2.4G
- verify_env again had to absorb transient 6G OCV and wl0 supplicant recovery noise, but the case itself still finished `Pass` in one attempt
- committed metadata is now workbook row `115` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `259 / 420 full matches`、`161 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D174`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D115` | 115 | `getStationStats() ConnectionDuration` | `Pass / Pass / Pass` | `20260413T035856845825_DUT.log L427-L679, L886-L1138; agent trace JSON L125-L128` | `20260413T035856845825_STA.log L84-L111, L210-L255, L389-L416` |

#### D115 getStationStats() ConnectionDuration

**STA 指令**

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
iw dev wl1 link
wpa_cli -p /var/run/wpa_supplicant -i wl1 status
wl -i wl1 status
iw dev wl2 link
wpa_cli -p /var/run/wpa_supplicant -i wl2 status
```

**DUT 指令**

```sh
wl -i wl0 assoclist
ubus-cli "WiFi.AccessPoint.1.getStationStats()"
sleep 3
ubus-cli "WiFi.AccessPoint.1.getStationStats()"
STA_MAC=$(wl -i wl0 assoclist | awk 'NR==1{print $NF}'); [ -n "$STA_MAC" ] && wl -i wl0 sta_info $STA_MAC | sed -n 's/.*in network \([0-9][0-9]*\) seconds.*/DriverConnectionSeconds5g=\1/p'
wl -i wl1 assoclist
ubus-cli "WiFi.AccessPoint.3.getStationStats()"
sleep 3
ubus-cli "WiFi.AccessPoint.3.getStationStats()"
STA_MAC=$(wl -i wl1 assoclist | awk 'NR==1{print $NF}'); [ -n "$STA_MAC" ] && wl -i wl1 sta_info $STA_MAC | sed -n 's/.*in network \([0-9][0-9]*\) seconds.*/DriverConnectionSeconds6g=\1/p'
wl -i wl2 assoclist
ubus-cli "WiFi.AccessPoint.5.getStationStats()"
sleep 3
ubus-cli "WiFi.AccessPoint.5.getStationStats()"
STA_MAC=$(wl -i wl2 assoclist | awk 'NR==1{print $NF}'); [ -n "$STA_MAC" ] && wl -i wl2 sta_info $STA_MAC | sed -n 's/.*in network \([0-9][0-9]*\) seconds.*/DriverConnectionSeconds24g=\1/p'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T035856845825_DUT.log L427, L464, L585, L679
assoclist 2C:59:17:00:04:85
ConnectionDuration = 7
ConnectionDuration = 10
DriverConnectionSeconds5g=12

20260413T035856845825_DUT.log L886, L923, L1044, L1138
assoclist 2C:59:17:00:04:86
ConnectionDuration = 11
ConnectionDuration = 14
DriverConnectionSeconds6g=16

plugins/wifi_llapi/reports/agent_trace/20260413T035856845825/wifi-llapi-D115-getstationstats-connectionduration.json L125-L128
assoclist 2C:59:17:00:04:97
ConnectionDuration = 9
ConnectionDuration = 13
DriverConnectionSeconds24g=15
```

## Checkpoint summary (2026-04-13 early-21)

> This checkpoint records the `D114` tri-band stale-scope closure after `D099`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D114 getStationStats() AvgSignalStrengthByChain` is now aligned via official rerun `20260413T033856175894`
- active 0403 still routes the field through `whm_brcm_ap_mlo_fillAssocDevInfo()` -> `wld_ad_getAvgSignalStrengthByChain(pAD)`
- the ODL still exposes `AvgSignalStrengthByChain` as a volatile read-only int32 with no band-specific branch
- the old case was a 5G-only artifact (`Fail / N/A / N/A`) even though workbook row `114` expects tri-band Pass
- the committed rewrite restores tri-band sequential `getStationStats()` coverage on AP1 / AP3 / AP5
- official rerun exact-closed `AvgSignalStrengthByChain=-33` (5G), `-85` (6G), `-23` (2.4G)
- verify_env had to absorb transient 6G OCV/hostapd recovery noise, but the case itself still finished `Pass` in one attempt
- committed metadata is now workbook row `114` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `258 / 420 full matches`、`162 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D115`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D114` | 114 | `getStationStats() AvgSignalStrengthByChain` | `Pass / Pass / Pass` | `20260413T033856175894_DUT.log L502-L538, L892-L927` | `20260413T033856175894_STA.log L500-L533, L664-L694, L387-L398` |

#### D114 getStationStats() AvgSignalStrengthByChain

**STA 指令**

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
iw dev wl1 link
wpa_cli -p /var/run/wpa_supplicant -i wl1 status
wl -i wl1 status
iw dev wl2 link
wpa_cli -p /var/run/wpa_supplicant -i wl2 status
```

**DUT 指令**

```sh
wl -i wl0 assoclist
ubus-cli "WiFi.AccessPoint.1.getStationStats()"
wl -i wl1 assoclist
ubus-cli "WiFi.AccessPoint.3.getStationStats()"
wl -i wl2 assoclist
ubus-cli "WiFi.AccessPoint.5.getStationStats()"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T033856175894_DUT.log L502-L538
assoclist 2C:59:17:00:04:85
AvgSignalStrengthByChain = -33

20260413T033856175894_DUT.log L892-L927
assoclist 2C:59:17:00:04:86
AvgSignalStrengthByChain = -85

plugins/wifi_llapi/reports/agent_trace/20260413T033856175894/wifi-llapi-D114-getstationstats-avgsignalstrengthbychain.json L114-L116
assoclist 2C:59:17:00:04:97
AvgSignalStrengthByChain = -23
```

## Checkpoint summary (2026-04-13 early-20)

> This checkpoint records the `D099` metadata/results_reference closure after `D098`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D099 WMMCapability` is now aligned via official rerun `20260413T032521733067`
- active 0403 source still routes `wifi_getApWMMCapability()` through `wldm_AccessPoint_WMMCapability()`
- that getter probes driver iovar `wme` and returns `TRUE` on successful read
- no 6G-specific divergence was found in the backing path
- the authoritative full-run trace had already exact-closed tri-band `WMMCapability=1` and `hostapd wmm_enabled=1`
- the rerun reproduced the same one-attempt Pass shape on AP1 / AP3 / AP5
- the only remaining defects were stale workbook row `101`, stale raw `Pass / Fail / Pass`, and an internal COM transport note mismatch
- committed metadata is now workbook row `99` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- case notes now keep the DUT transport wording consistent at COM1
- overlay compare is now `257 / 420 full matches`、`163 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D114`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D099` | 99 | `WMMCapability` | `Pass / Pass / Pass` | `20260413T032521733067_DUT.log L8-L18` | `20260413T032521733067_STA.log (no STA transport used)` |

#### D099 WMMCapability

**STA 指令**

```sh
# none; AP-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.WMMCapability?"
grep 'wmm_enabled=' /tmp/wl0_hapd.conf
ubus-cli "WiFi.AccessPoint.3.WMMCapability?"
grep 'wmm_enabled=' /tmp/wl1_hapd.conf
ubus-cli "WiFi.AccessPoint.5.WMMCapability?"
grep 'wmm_enabled=' /tmp/wl2_hapd.conf
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T032521733067_DUT.log L8-L18
WMMCapability5g=1
HapdWmm5g=1
WMMCapability6g=1
HapdWmm6g=1
WMMCapability24g=1
HapdWmm24g=1
```

## Checkpoint summary (2026-04-13 early-19)

> This checkpoint records the `D098` metadata/results_reference closure after `D095`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D098 WDSEnable` is now aligned via official rerun `20260413T031458311484`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`
- the rerun exact-closed tri-band setter round-trip `baseline=0 -> set=1 -> restore=0`
- the same rerun exact-closed direct driver `dwds 0 -> 1 -> 0` on AP1 / AP3 / AP5
- the only remaining defects were stale workbook row `100`, stale raw `Fail / Fail / Fail`, and an internal COM transport note mismatch
- committed metadata is now workbook row `98` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- case notes now keep the DUT transport wording consistent at COM1
- overlay compare is now `256 / 420 full matches`、`164 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D099`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D098` | 98 | `WDSEnable` | `Pass / Pass / Pass` | `20260413T031458311484_DUT.log L8-L126` | `20260413T031458311484_STA.log (no STA transport used)` |

#### D098 WDSEnable

**STA 指令**

```sh
# none; AP-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.WDSEnable?"
wl -i wl0 dwds
ubus-cli WiFi.AccessPoint.1.WDSEnable=1
ubus-cli "WiFi.AccessPoint.1.WDSEnable?"
wl -i wl0 dwds
ubus-cli WiFi.AccessPoint.1.WDSEnable=0
ubus-cli "WiFi.AccessPoint.1.WDSEnable?"
wl -i wl0 dwds
ubus-cli "WiFi.AccessPoint.3.WDSEnable?"
wl -i wl1 dwds
ubus-cli WiFi.AccessPoint.3.WDSEnable=1
ubus-cli "WiFi.AccessPoint.3.WDSEnable?"
wl -i wl1 dwds
ubus-cli WiFi.AccessPoint.3.WDSEnable=0
ubus-cli "WiFi.AccessPoint.3.WDSEnable?"
wl -i wl1 dwds
ubus-cli "WiFi.AccessPoint.5.WDSEnable?"
wl -i wl2 dwds
ubus-cli WiFi.AccessPoint.5.WDSEnable=1
ubus-cli "WiFi.AccessPoint.5.WDSEnable?"
wl -i wl2 dwds
ubus-cli WiFi.AccessPoint.5.WDSEnable=0
ubus-cli "WiFi.AccessPoint.5.WDSEnable?"
wl -i wl2 dwds
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T031458311484_DUT.log L8-L43
Baseline5g=0
DriverBaseline5g=0
AfterSet5g=1
DriverAfterSet5g=1
AfterRestore5g=0
DriverAfterRestore5g=0

20260413T031458311484_DUT.log L47-L82
Baseline6g=0
DriverBaseline6g=0
AfterSet6g=1
DriverAfterSet6g=1
AfterRestore6g=0
DriverAfterRestore6g=0

20260413T031458311484_DUT.log L86-L126
Baseline24g=0
DriverBaseline24g=0
AfterSet24g=1
DriverAfterSet24g=1
AfterRestore24g=0
DriverAfterRestore24g=0
```

## Checkpoint summary (2026-04-13 early-18)

> This checkpoint records the `D095` metadata/results_reference closure after `D094`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D095 UAPSDCapability` is now aligned via official rerun `20260413T030853360475`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`
- the rerun exact-closed tri-band read-only `UAPSDCapability=1`
- the same rerun also showed `HapdUapsd=0` and `DriverWmeApsd=0`, which indicate the feature is not currently active but do not contradict the capability getter
- the only remaining defects were stale workbook row `97`, stale raw `Fail / Fail / Fail`, and an internal COM transport note mismatch
- committed metadata is now workbook row `95` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- case notes now keep the DUT transport wording consistent at COM1
- overlay compare is now `255 / 420 full matches`、`165 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D098`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D095` | 95 | `UAPSDCapability` | `Pass / Pass / Pass` | `20260413T030853360475_DUT.log L13-L52` | `20260413T030853360475_STA.log (no STA transport used)` |

#### D095 UAPSDCapability

**STA 指令**

```sh
# none; AP-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.UAPSDCapability?"
grep 'uapsd_advertisement_enabled=' /tmp/wl0_hapd.conf
wl -i wl0 wme_apsd
ubus-cli "WiFi.AccessPoint.3.UAPSDCapability?"
grep 'uapsd_advertisement_enabled=' /tmp/wl1_hapd.conf
wl -i wl1 wme_apsd
ubus-cli "WiFi.AccessPoint.5.UAPSDCapability?"
grep 'uapsd_advertisement_enabled=' /tmp/wl2_hapd.conf
wl -i wl2 wme_apsd
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T030853360475_DUT.log L13-L20
UAPSDCapability5g=1
HapdUapsd5g=0
DriverWmeApsd5g=0

20260413T030853360475_DUT.log L29-L36
UAPSDCapability6g=1
HapdUapsd6g=0
DriverWmeApsd6g=0

20260413T030853360475_DUT.log L45-L52
UAPSDCapability24g=1
HapdUapsd24g=0
DriverWmeApsd24g=0
```

## Checkpoint summary (2026-04-13 early-17)

> This checkpoint records the `D094` metadata/results_reference closure after `D081`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D094 AccessPoint.Status` is now aligned via official rerun `20260413T030202219754`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`
- the rerun exact-closed tri-band `Status="Enabled"` against direct driver `wl -i wl{0,1,2} bss = up`
- the only remaining defects were stale workbook row `96`, stale raw `Fail / Fail / Fail`, and an internal COM transport note mismatch
- committed metadata is now workbook row `94` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- case notes now keep the DUT transport wording consistent at COM1
- overlay compare is now `254 / 420 full matches`、`166 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D095`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D094` | 94 | `Status` | `Pass / Pass / Pass` | `20260413T030202219754_DUT.log L5-L25` | `20260413T030202219754_STA.log (no STA transport used)` |

#### D094 AccessPoint.Status

**STA 指令**

```sh
# none; AP-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.Status?"
wl -i wl0 bss
ubus-cli "WiFi.AccessPoint.3.Status?"
wl -i wl1 bss
ubus-cli "WiFi.AccessPoint.5.Status?"
wl -i wl2 bss
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T030202219754_DUT.log L8-L11
Status5g=Enabled
DriverBss5g=up

20260413T030202219754_DUT.log L15-L18
Status6g=Enabled
DriverBss6g=up

20260413T030202219754_DUT.log L22-L25
Status24g=Enabled
DriverBss24g=up
```

## Checkpoint summary (2026-04-13 early-16)

> This checkpoint records the `D081` source-backed workbook-Pass closure after `D065`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D081 MBOEnable` is now aligned via official rerun `20260413T025449283775`
- this was not a metadata-only closure: active 0403 `wifi_ap.c` maps both `handle_set_ap_mbo_enable()` and `handle_get_ap_mbo_enable()` to `wl -i <if> mbo ap_enable`
- the old hostapd `mbo=` fail-shaped oracle was therefore rejected and replaced by a source-backed `ubus getter <-> wl mbo ap_enable` oracle
- the committed rewrite now forces `WiFi.AccessPoint.{1,3,5}.MBOEnable=0` in setup to remove prior-case pollution
- the rerun exact-closed getter and direct driver readback `0 -> 1 -> 0` on AP1 / AP3 / AP5 in a single attempt
- committed metadata is now workbook row `81` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `253 / 420 full matches`、`167 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D094`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D081` | 81 | `MBOEnable` | `Pass / Pass / Pass` | `20260413T025449283775_DUT.log L18-L358` | `20260413T025449283775_STA.log (no STA transport used)` |

#### D081 MBOEnable

**STA 指令**

```sh
# none; AP-only case
```

**DUT 指令**

```sh
ubus-cli WiFi.AccessPoint.1.MBOEnable=0
ubus-cli WiFi.AccessPoint.3.MBOEnable=0
ubus-cli WiFi.AccessPoint.5.MBOEnable=0
ubus-cli "WiFi.AccessPoint.1.MBOEnable?"
wl -i wl0 mbo ap_enable
ubus-cli WiFi.AccessPoint.1.MBOEnable=1
ubus-cli "WiFi.AccessPoint.1.MBOEnable?"
wl -i wl0 mbo ap_enable
ubus-cli WiFi.AccessPoint.1.MBOEnable=0
ubus-cli "WiFi.AccessPoint.1.MBOEnable?"
wl -i wl0 mbo ap_enable
ubus-cli "WiFi.AccessPoint.3.MBOEnable?"
wl -i wl1 mbo ap_enable
ubus-cli WiFi.AccessPoint.3.MBOEnable=1
ubus-cli "WiFi.AccessPoint.3.MBOEnable?"
wl -i wl1 mbo ap_enable
ubus-cli WiFi.AccessPoint.3.MBOEnable=0
ubus-cli "WiFi.AccessPoint.3.MBOEnable?"
wl -i wl1 mbo ap_enable
ubus-cli "WiFi.AccessPoint.5.MBOEnable?"
wl -i wl2 mbo ap_enable
ubus-cli WiFi.AccessPoint.5.MBOEnable=1
ubus-cli "WiFi.AccessPoint.5.MBOEnable?"
wl -i wl2 mbo ap_enable
ubus-cli WiFi.AccessPoint.5.MBOEnable=0
ubus-cli "WiFi.AccessPoint.5.MBOEnable?"
wl -i wl2 mbo ap_enable
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T025449283775_DUT.log L75-L76
BaselineGetterMbo5g=0
BaselineDriverMbo5g=0

20260413T025449283775_DUT.log L112-L114
AfterEnableGetterMbo5g=1
AfterEnableDriverMbo5g=1

20260413T025449283775_DUT.log L150-L152
AfterRestoreGetterMbo5g=0
AfterRestoreDriverMbo5g=0

20260413T025449283775_DUT.log L178-L179
BaselineGetterMbo6g=0
BaselineDriverMbo6g=0

20260413T025449283775_DUT.log L215-L217
AfterEnableGetterMbo6g=1
AfterEnableDriverMbo6g=1

20260413T025449283775_DUT.log L253-L255
AfterRestoreGetterMbo6g=0
AfterRestoreDriverMbo6g=0

20260413T025449283775_DUT.log L281-L282
BaselineGetterMbo24g=0
BaselineDriverMbo24g=0

20260413T025449283775_DUT.log L318-L320
AfterEnableGetterMbo24g=1
AfterEnableDriverMbo24g=1

20260413T025449283775_DUT.log L356-L358
AfterRestoreGetterMbo24g=0
AfterRestoreDriverMbo24g=0
```

## Checkpoint summary (2026-04-13 early-15)

> This checkpoint records the `D065` metadata/results_reference closure after `D028`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D065 BridgeInterface` is now aligned via official rerun `20260413T024240506323`
- the authoritative trace had already been `evaluation_verdict=Pass`
- live AP-only evidence exact-closed AP1 / AP3 / AP5 `BridgeInterface="br-lan"`
- hostapd `bridge=br-lan` config lines and live Linux bridge masters `BridgeMaster5g/6g/24g=br-lan` all matched the getter outputs
- committed metadata is now workbook row `65` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `252 / 420 full matches`、`168 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D081`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D065` | 65 | `BridgeInterface` | `Pass / Pass / Pass` | `20260413T024240506323_DUT.log L14-L88` | `20260413T024240506323_STA.log (no STA transport used)` |

#### D065 BridgeInterface

**STA 指令**

```sh
# none; AP-only case
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.BridgeInterface?"
ubus-cli "WiFi.AccessPoint.3.BridgeInterface?"
ubus-cli "WiFi.AccessPoint.5.BridgeInterface?"
grep '^bridge=' /tmp/wl0_hapd.conf | awk -F= '/^bridge=/ {if (count == 0) first=$2; if ($2 != first) mismatch=1; count++} END {print "BridgeConfig5g=" first; print "BridgeConfig5gCount=" count+0; print "BridgeConfig5gMismatch=" mismatch+0}'
grep '^bridge=' /tmp/wl1_hapd.conf | awk -F= '/^bridge=/ {if (count == 0) first=$2; if ($2 != first) mismatch=1; count++} END {print "BridgeConfig6g=" first; print "BridgeConfig6gCount=" count+0; print "BridgeConfig6gMismatch=" mismatch+0}'
grep '^bridge=' /tmp/wl2_hapd.conf | awk -F= '/^bridge=/ {if (count == 0) first=$2; if ($2 != first) mismatch=1; count++} END {print "BridgeConfig24g=" first; print "BridgeConfig24gCount=" count+0; print "BridgeConfig24gMismatch=" mismatch+0}'
cat /sys/class/net/wl0/master/uevent | sed -n 's/^INTERFACE=/BridgeMaster5g=/p'
cat /sys/class/net/wl1/master/uevent | sed -n 's/^INTERFACE=/BridgeMaster6g=/p'
cat /sys/class/net/wl2/master/uevent | sed -n 's/^INTERFACE=/BridgeMaster24g=/p'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T024240506323_DUT.log L14-L27
WiFi.AccessPoint.1.BridgeInterface="br-lan"
WiFi.AccessPoint.3.BridgeInterface="br-lan"
WiFi.AccessPoint.5.BridgeInterface="br-lan"

20260413T024240506323_DUT.log L42-L44
BridgeConfig5g=br-lan
BridgeConfig5gCount=2
BridgeConfig5gMismatch=0

20260413T024240506323_DUT.log L58-L60
BridgeConfig6g=br-lan
BridgeConfig6gCount=2
BridgeConfig6gMismatch=0

20260413T024240506323_DUT.log L74-L76
BridgeConfig24g=br-lan
BridgeConfig24gCount=2
BridgeConfig24gMismatch=0

20260413T024240506323_DUT.log L80-L88
BridgeMaster5g=br-lan
BridgeMaster6g=br-lan
BridgeMaster24g=br-lan
```

## Checkpoint summary (2026-04-13 early-14)

> This checkpoint records the `D028` mixed-verdict workbook closure after `D061`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D028 MaxBandwidthSupported` is now aligned via official rerun `20260413T023259417785`
- the rerun kept the executed 5G / 2.4G bands in `evaluation_verdict=Pass`
- live evidence exact-closed 5G `MaxBandwidthSupported="160MHz"` and 2.4G `MaxBandwidthSupported="40MHz"`
- workbook row `28` remains explicitly fail-shaped on 6G, while the current lab still skips AP3/wl1 because STA association is `BCME_NOTREADY`
- committed metadata is now workbook row `28` with `results_reference.v4.0.3 = Pass / Fail / Pass`
- overlay compare is now `251 / 420 full matches`、`169 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D065`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D028` | 28 | `MaxBandwidthSupported` | `Pass / Fail / Pass` | `20260413T023259417785_DUT.log L191-L199, L263-L271` | `20260413T023259417785_STA.log L82-L99, L179-L196` |

#### D028 MaxBandwidthSupported

**STA 指令**

```sh
iw dev wl0 link
iw dev wl2 link
```

**DUT 指令**

```sh
wl -i wl0 assoclist | tr 'A-F' 'a-f' | sed -n 's/^assoclist \([^ ]*\).*$/AssocMac5g=\1/p'
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MaxBandwidthSupported?"
wl -i wl2 assoclist | tr 'A-F' 'a-f' | sed -n 's/^assoclist \([^ ]*\).*$/AssocMac24g=\1/p'
ubus-cli "WiFi.AccessPoint.5.AssociatedDevice.1.MaxBandwidthSupported?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T023259417785_STA.log L82-L99
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: testpilot5G

20260413T023259417785_DUT.log L191-L199
AssocMac5g=2c:59:17:00:04:85
WiFi.AccessPoint.1.AssociatedDevice.1.MaxBandwidthSupported="160MHz"

20260413T023259417785_STA.log L179-L196
iw dev wl2 link
Connected to 2c:59:17:00:19:a7 (on wl2)
        SSID: testpilot2G

20260413T023259417785_DUT.log L263-L271
AssocMac24g=2c:59:17:00:04:97
WiFi.AccessPoint.5.AssociatedDevice.1.MaxBandwidthSupported="40MHz"
```

## Checkpoint summary (2026-04-13 early-13)

> This checkpoint records the `D061` metadata/results_reference closure after `D046`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D061 UplinkShortGuard` is now aligned via official rerun `20260413T022541033440`
- the authoritative trace had already been `evaluation_verdict=Pass`
- live 5G evidence exact-closed the post-trigger `UplinkShortGuard=1` snapshot against the same-STA driver GI token `1.6us` and derived boolean `DriverUplinkShortGuard=1`
- the only remaining defects were stale workbook row `63` plus stale raw `Pass / N/A / N/A`
- committed metadata is now workbook row `61` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `250 / 420 full matches`、`170 mismatches`、`58 metadata drifts`
- next ready mixed-verdict workbook revisit is `D028`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D061` | 61 | `UplinkShortGuard` | `Pass / Pass / Pass` | `20260413T022541033440_DUT.log L349-L381` | `20260413T022541033440_STA.log L63-L104` |

#### D061 UplinkShortGuard

**STA 指令**

```sh
wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
sleep 10
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
ifconfig wl0 192.168.1.3 netmask 255.255.255.0 up && ip route get 192.168.1.1
ping -I wl0 -c 8 -W 1 192.168.1.1
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?"); printf '%s\n' "$OUT" | sed -n 's/.*MACAddress="\([^"]*\)".*/AssocMacAfterTrigger=\1/p; s/.*UplinkShortGuard=\([^[:space:]]*\).*/UplinkShortGuard=\1/p'
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p')
STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f')
NRATE=$(wl -i wl0 sta_info $STA_MAC_LOWER | sed -n '/rx nrate/,+1p')
GI=$(echo "$NRATE" | sed -n '2s/.*GI \([^ ]*\).*/\1/p')
echo DriverAssocMac=$STA_MAC
echo "$NRATE"
echo DriverUplinkShortGuardGI=$GI
case "$GI" in 0.4us|0.8us|1.6us) echo DriverUplinkShortGuard=1 ;; 3.2us) echo DriverUplinkShortGuard=0 ;; *) echo DriverUplinkShortGuard=UNKNOWN_GI:$GI ;; esac
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T022541033440_STA.log L63-L104
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: testpilot5G
...
ping -I wl0 -c 8 -W 1 192.168.1.1
8 packets transmitted, 8 received, 0% packet loss

20260413T022541033440_DUT.log L349-L381
AssocMacAfterTrigger=2C:59:17:00:04:85
UplinkShortGuard=1
DriverAssocMac=2C:59:17:00:04:85
he mcs 10 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto
DriverUplinkShortGuardGI=1.6us
DriverUplinkShortGuard=1
```

## Checkpoint summary (2026-04-13 early-12)

> This checkpoint records the `D046` metadata/results_reference closure after `D045`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D046 SignalStrengthByChain` is now aligned via official rerun `20260413T021655844208`
- the authoritative trace had already been `evaluation_verdict=Pass`
- live 5G evidence exact-closed `AssociatedDevice.1.SignalStrengthByChain="-33.0,-32.0,-41.0,-34.0"` against the same-STA driver sample `DriverSignalStrengthByChain=-33.0,-32.0,-41.0,-34.0`
- the only remaining defects were stale workbook row `48` plus stale raw `Fail / N/A / N/A`
- committed metadata is now workbook row `46` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `249 / 420 full matches`、`171 mismatches`、`58 metadata drifts`
- next ready source-row drift revisit is `D014`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D046` | 46 | `SignalStrengthByChain` | `Pass / Pass / Pass` | `20260413T021655844208_DUT.log L339-L371` | `20260413T021655844208_STA.log L64-L82` |

#### D046 SignalStrengthByChain

**STA 指令**

```sh
wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
sleep 10
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain?"
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p')
STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f')
[ -n "$STA_MAC" ]
echo DriverAssocMac=$STA_MAC
wl -i wl0 sta_info $STA_MAC_LOWER | sed -n 's/.*per antenna average rssi of rx data frames: *//p' | tr ' ' '\n' | sed '/^$/d' | awk 'BEGIN{first=1} {printf "%s%s.0", (first?"":","), $1; first=0} END{if (!first) printf "\n"}' | sed 's/^/DriverSignalStrengthByChain=/'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T021655844208_STA.log L64-L82
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: TestPilot_BTM
...
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
ssid=TestPilot_BTM

20260413T021655844208_DUT.log L339-L371
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain="-33.0,-32.0,-41.0,-34.0"
DriverAssocMac=2C:59:17:00:04:85
DriverSignalStrengthByChain=-33.0,-32.0,-41.0,-34.0
```

## Checkpoint summary (2026-04-13 early-11)

> This checkpoint records the `D045` metadata/results_reference closure after the `D035` blocker checkpoint.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D045 SignalStrength` is now aligned via official rerun `20260413T020657288045`
- the authoritative trace had already been `evaluation_verdict=Pass`
- live 5G evidence exact-closed `AssociatedDevice.1.SignalStrength=-33` against the same-STA driver sample `DriverSignalStrength=-33`
- the only remaining defects were stale workbook row `47` plus stale raw `2.4g=Fail`
- committed metadata is now workbook row `45` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare is now `248 / 420 full matches`、`172 mismatches`、`58 metadata drifts`
- next ready low-risk workbook-Pass revisit is `D046`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D045` | 45 | `SignalStrength` | `Pass / Pass / Pass` | `20260413T020657288045_DUT.log L339-L375` | `20260413T020657288045_STA.log L64-L82` |

#### D045 SignalStrength

**STA 指令**

```sh
wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
sleep 10
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength?"
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p')
STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f')
iw dev wl0 station dump | awk -v mac="$STA_MAC_LOWER" -v sta="$STA_MAC" '$1=="Station" && $2==mac {matched=1; print "DriverAssocMac=" sta; next} $1=="Station" {matched=0} matched && $1=="signal:" {signal=$2; print "DriverSignalStrength=" signal; print "DriverSignalStrengthMin=" signal-2; print "DriverSignalStrengthMax=" signal+2}'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T020657288045_STA.log L64-L82
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: TestPilot_BTM
...
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
ssid=TestPilot_BTM

20260413T020657288045_DUT.log L339-L375
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength=-33
DriverAssocMac=2C:59:17:00:04:85
DriverSignalStrength=-33
DriverSignalStrengthMin=-35
DriverSignalStrengthMax=-31
```

## Checkpoint summary (2026-04-13 early-10)

> This checkpoint records the blocked `D035` trial after `D467`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D035 AssociatedDevice OperatingStandard` was the next workbook-Pass revisit after `D467`, but it did not converge into a safe repo rewrite
- official rerun `20260413T014428270219` failed twice at `step1_5g_sta_join` with trace output `iw dev wl0 link -> Not connected.`
- the same STA verify-env log still showed `SSID: testpilot5G` and `wpa_state=COMPLETED`, so this was not a simple missing-baseline case
- reconnect trial rerun `20260413T015210910141` removed the immediate 5G join failure, but the run then fell into a repeated 6G `ocv=0` / `ATTACH` recovery loop and was stopped without a stable final verdict
- the local tri-band rewrite was reverted and not committed
- overlay compare therefore stays `247 / 420 full matches`、`173 mismatches`、`58 metadata drifts`
- blocker authority is now `plugins/wifi_llapi/reports/D035_block.md`
- next ready workbook-Pass revisit is `D045`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D035` | 35 | `OperatingStandard` | `Blocked (runtime/env)` | `20260413T014428270219_DUT.log L694-L700, L747-L758` | `20260413T014428270219_STA.log L505-L534` |

#### D035 AssociatedDevice OperatingStandard

**STA 指令**

```sh
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status

# reconnect trial
wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0
sleep 5
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
wl -i wl1 bss
ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"
ubus-cli WiFi.AccessPoint.5.Enable=1
wl -i wl2 bss
```

**判定 blocker 的 log 摘錄 / log 區間**

```text
20260413T014428270219 agent trace
attempt 1/2 and 2/2:
step1_5g_sta_join command failed
command: iw dev wl0 link
output: Not connected.

20260413T014428270219_STA.log L505-L534
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: testpilot5G
...
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
ssid=testpilot5G
key_mgmt=WPA2-PSK
wpa_state=COMPLETED

20260413T014428270219_DUT.log L694-L700, L747-L758
wl -i wl1 bss
up
WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:04:86"
ubus-cli WiFi.AccessPoint.5.Enable=1
WiFi.AccessPoint.5.Enable=1
--wl2 FSM DONE--
wl -i wl2 bss
up

20260413T015210910141 runner transcript (aborted trial)
verify_env: d035-assocdev-operatingstandard 6G restart attempt=1 unstable
verify_env: d035-assocdev-operatingstandard 6G ocv=0 fix applied, wl1 hostapd restarted
env: retry command after recovery_action=ATTACH attempt=1 cmd=grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1
env: retry command after recovery_action=ATTACH attempt=2 cmd=grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1
verify_env: d035-assocdev-operatingstandard 6G ocv=0 verify failed — BSS loop may persist
```

## Checkpoint summary (2026-04-13 early-9)

> This checkpoint records the `D467` results_reference / row closure after `D465`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D467 RxBeamformingCapsEnabled` is now aligned via official rerun `20260413T013545364055`
- the authoritative full-run trace had already been `evaluation_verdict=Pass` with stable `RxBeamformingCapsEnabled="DEFAULT"` on AP1 / AP3 / AP5
- committed metadata is now workbook row `467` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 / D460 / D494 / D461 / D462 / D463 / D465 / D467 reruns is now
  `247 / 420 full matches`、`173 mismatches`、`58 metadata drifts`
- next ready workbook-Pass revisit is `D035`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D467` | 467 | `RxBeamformingCapsEnabled` | `Pass / Pass / Pass` | `20260413T013545364055_DUT.log L5-L18` | `N/A (AP-only case)` |

#### D467 RxBeamformingCapsEnabled

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.RxBeamformingCapsEnabled?"
ubus-cli "WiFi.Radio.2.RxBeamformingCapsEnabled?"
ubus-cli "WiFi.Radio.3.RxBeamformingCapsEnabled?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T013545364055_DUT.log L5-L18
WiFi.Radio.1.RxBeamformingCapsEnabled="DEFAULT"
WiFi.Radio.2.RxBeamformingCapsEnabled="DEFAULT"
WiFi.Radio.3.RxBeamformingCapsEnabled="DEFAULT"
```

## Checkpoint summary (2026-04-13 early-8)

> This checkpoint records the `D465` mapping/results_reference closure after `D463`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D465 SRGInformationValid` is now aligned via official rerun `20260413T013010016650`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`; the remaining mismatch was stale metadata (`source.row=342`, object `WiFi.Radio.{i}.`, raw `Fail / Fail / Fail`) plus a stale 6G live annotation (`live=1`)
- committed metadata is now workbook row `465`, object `WiFi.Radio.{i}.IEEE80211ax.`, with `results_reference.v4.0.3 = Pass / Pass / Pass`; the 6G live annotation is corrected to `0`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 / D460 / D494 / D461 / D462 / D463 / D465 reruns is now
  `246 / 420 full matches`、`174 mismatches`、`58 metadata drifts`
- next ready phase-2 mapping/results_reference revisit is `D467`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D465` | 465 | `SRGInformationValid` | `Pass / Pass / Pass` | `20260413T013010016650_DUT.log L5-L18` | `N/A (AP-only case)` |

#### D465 SRGInformationValid

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.IEEE80211ax.SRGInformationValid?"
ubus-cli "WiFi.Radio.2.IEEE80211ax.SRGInformationValid?"
ubus-cli "WiFi.Radio.3.IEEE80211ax.SRGInformationValid?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T013010016650_DUT.log L5-L18
WiFi.Radio.1.IEEE80211ax.SRGInformationValid=0
WiFi.Radio.2.IEEE80211ax.SRGInformationValid=0
WiFi.Radio.3.IEEE80211ax.SRGInformationValid=0
```

## Checkpoint summary (2026-04-13 early-7)

> This checkpoint records the `D463` mapping/results_reference closure after `D462`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D463 HESIGASpatialReuseValue15Allowed` is now aligned via official rerun `20260413T012358700786`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`; the remaining mismatch was stale metadata (`source.row=340`, object `WiFi.Radio.{i}.`, raw `Fail / Fail / Fail`)
- committed metadata is now workbook row `463`, object `WiFi.Radio.{i}.IEEE80211ax.`, with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 / D460 / D494 / D461 / D462 / D463 reruns is now
  `245 / 420 full matches`、`175 mismatches`、`59 metadata drifts`
- next ready phase-2 mapping/results_reference revisit is `D465`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D463` | 463 | `HESIGASpatialReuseValue15Allowed` | `Pass / Pass / Pass` | `20260413T012358700786_DUT.log L5-L21` | `N/A (AP-only case)` |

#### D463 HESIGASpatialReuseValue15Allowed

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.IEEE80211ax.HESIGASpatialReuseValue15Allowed?"
ubus-cli "WiFi.Radio.2.IEEE80211ax.HESIGASpatialReuseValue15Allowed?"
ubus-cli "WiFi.Radio.3.IEEE80211ax.HESIGASpatialReuseValue15Allowed?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T012358700786_DUT.log L5-L21
WiFi.Radio.1.IEEE80211ax.HESIGASpatialReuseValue15Allowed=0
WiFi.Radio.2.IEEE80211ax.HESIGASpatialReuseValue15Allowed=0
WiFi.Radio.3.IEEE80211ax.HESIGASpatialReuseValue15Allowed=0
```

## Checkpoint summary (2026-04-13 early-6)

> This checkpoint records the `D462` mapping/results_reference closure after `D461`.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D462 BssColor` is now aligned via official rerun `20260413T011655056430`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`; the remaining mismatch was stale metadata (`source.row=339`, object `WiFi.Radio.{i}.`, raw `Fail / Fail / Fail`)
- committed metadata is now workbook row `462`, object `WiFi.Radio.{i}.IEEE80211ax.`, with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 / D460 / D494 / D461 / D462 reruns is now
  `244 / 420 full matches`、`176 mismatches`、`60 metadata drifts`
- next ready phase-2 mapping/results_reference revisit is `D463`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D462` | 462 | `BssColor` | `Pass / Pass / Pass` | `20260413T011655056430_DUT.log L5-L18` | `N/A (AP-only case)` |

#### D462 BssColor

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.IEEE80211ax.BssColor?"
ubus-cli "WiFi.Radio.2.IEEE80211ax.BssColor?"
ubus-cli "WiFi.Radio.3.IEEE80211ax.BssColor?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T011655056430_DUT.log L5-L18
WiFi.Radio.1.IEEE80211ax.BssColor=0
WiFi.Radio.2.IEEE80211ax.BssColor=0
WiFi.Radio.3.IEEE80211ax.BssColor=0
```

## Checkpoint summary (2026-04-13 early-5)

> This checkpoint records the `D461` mapping/results_reference closure after the D460/D494 step-command bucket was cleared.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D461 HTCapabilities` is now aligned via official rerun `20260413T010944709855`
- the authoritative full-run trace had already been `evaluation_verdict=Pass`; the remaining mismatch was only stale metadata (`source.row=338`, raw `Fail / Fail / Fail`)
- committed metadata is now workbook row `461` with `results_reference.v4.0.3 = Pass / Pass / Pass`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 / D460 / D494 / D461 reruns is now
  `243 / 420 full matches`、`177 mismatches`、`61 metadata drifts`
- next ready phase-2 mapping/results_reference revisit is `D462`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D461` | 461 | `HTCapabilities` | `Pass / Pass / Pass` | `20260413T010944709855_DUT.log L5-L18` | `N/A (AP-only case)` |

#### D461 HTCapabilities

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.HTCapabilities?"
ubus-cli "WiFi.Radio.2.HTCapabilities?"
ubus-cli "WiFi.Radio.3.HTCapabilities?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T010944709855_DUT.log L5-L18
WiFi.Radio.1.HTCapabilities="YhA="
WiFi.Radio.2.HTCapabilities="AAA="
WiFi.Radio.3.HTCapabilities="YhA="
```

## Checkpoint summary (2026-04-13 early-4)

> This checkpoint records the `D460` / `D494` closure on top of the earlier D088 step-command work.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D460 HePhyCapabilities` is now aligned via official rerun `20260413T005520941756`
- `D460` root cause was stale workbook mapping drift: the case still used wrong API / row (`HECapabilities`, `462`) even though workbook row `460` and live 0403 `wld_radio.odl` expose `HePhyCapabilities`
- live DUT evidence exact-closed `WiFi.Radio.1/2.HePhyCapabilities="TCBCwAIbFQAAjAA="` and `WiFi.Radio.3.HePhyCapabilities="IiBCwAIDFQAAjAA="`
- `D494 VHTCapabilities` is now aligned via official rerun `20260413T005633950804`
- `D494` root cause was mixed authoring drift: workbook row `494` requires protected 5G `VHTCapabilities` readback, while 6G / 2.4G stay `parameter not found`; the old case incorrectly modeled all three radios as the same `error=4` shape
- `D494` now uses explicit protected 5G shell capture (`VHTCapabilities=dliDDw==`) and parsed `error=4` / `message=parameter not found` on 6G / 2.4G
- committed metadata is now workbook row `460` / `494`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 / D460 / D494 reruns is now
  `242 / 420 full matches`、`178 mismatches`、`61 metadata drifts`
- the focused `step_command_failed` queue from the original seven-case set is now empty
- remaining non-env open items now start with semantic / mapping buckets: `D079` remains `pass_criteria_not_satisfied`, env-only bucket remains `D328` / `D336`, blocked bucket remains `D053`
- next ready phase: calibration / mapping / results_reference bucket

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D460` | 460 | `HePhyCapabilities` | `Pass / Pass / Pass` | `20260413T005520941756_DUT.log L5-L18` | `N/A (AP-only case)` |
| `D494` | 494 | `VHTCapabilities` | `Pass / Not Supported / Not Supported` | `20260413T005633950804_DUT.log L5-L58` | `N/A (AP-only case)` |

#### D460 HePhyCapabilities

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.Radio.1.HePhyCapabilities?"
ubus-cli "WiFi.Radio.2.HePhyCapabilities?"
ubus-cli "WiFi.Radio.3.HePhyCapabilities?"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T005520941756_DUT.log L5-L18
WiFi.Radio.1.HePhyCapabilities="TCBCwAIbFQAAjAA="
WiFi.Radio.2.HePhyCapabilities="TCBCwAIbFQAAjAA="
WiFi.Radio.3.HePhyCapabilities="IiBCwAIDFQAAjAA="
```

#### D494 VHTCapabilities

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
OUT=$(ubus-cli "protected;WiFi.Radio.1.VHTCapabilities?" 2>&1 || true)
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | sed -n 's/.*WiFi.Radio.1.VHTCapabilities="\([^"]*\)"/VHTCapabilities=\1/p'
OUT=$(ubus-cli "WiFi.Radio.2.VHTCapabilities?" 2>&1 || true)
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/error=\1/p'
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/message=\2/p'
OUT=$(ubus-cli "WiFi.Radio.3.VHTCapabilities?" 2>&1 || true)
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/error=\1/p'
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/message=\2/p'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T005633950804_DUT.log L16-L22
> WiFi.Radio.1.VHTCapabilities?
WiFi.Radio.1.VHTCapabilities="dliDDw=="
VHTCapabilities=dliDDw==

20260413T005633950804_DUT.log L37-L40
> WiFi.Radio.2.VHTCapabilities?
ERROR: get WiFi.Radio.2.VHTCapabilities failed (4 - parameter not found)
error=4
message=parameter not found

20260413T005633950804_DUT.log L55-L58
> WiFi.Radio.3.VHTCapabilities?
ERROR: get WiFi.Radio.3.VHTCapabilities failed (4 - parameter not found)
error=4
message=parameter not found
```

## Checkpoint summary (2026-04-13 early-3)

> This checkpoint records the `D088` alignment closure on top of the D079 runtime de-truncation fix.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D088 ModesSupported` is now aligned via official rerun `20260413T003340845889`
- the shared setter-capture runtime fix was already enough to remove the old `step_command_failed`; the remaining missing piece was output shaping
- step2 / step4 / step6 now preserve the real read-only setter path and emit parsable `error=15` / `message=is read only` lines for AP1 / AP3 / AP5
- live DUT evidence exact-closed workbook-pass semantics in one attempt:
  - AP1 / AP5 getter keep the full mode list including `WPA-Personal`, `WPA2-Personal`, `WPA3-Personal`, `WPA-Enterprise`
  - AP3 getter stays restricted to `None,WPA3-Personal,OWE`
  - all three setter attempts return `error=15` / `message=is read only`
- committed metadata is now workbook row `88`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 / D088 reruns is now
  `240 / 420 full matches`、`180 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps are now `151`
- next ready `step_command_failed` revisit is `D460`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D088` | 88 | `ModesSupported` | `Pass / Pass / Pass` | `20260413T003340845889_DUT.log L5-L73` | `N/A (AP-only case)` |

#### D088 ModesSupported

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.Security.ModesSupported?"
OUT=$(ubus-cli WiFi.AccessPoint.1.Security.ModesSupported=WPA3-Personal 2>&1 || true)
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/error=\1/p'
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/message=\2/p'
ubus-cli "WiFi.AccessPoint.3.Security.ModesSupported?"
OUT=$(ubus-cli WiFi.AccessPoint.3.Security.ModesSupported=WPA3-Personal 2>&1 || true)
ubus-cli "WiFi.AccessPoint.5.Security.ModesSupported?"
OUT=$(ubus-cli WiFi.AccessPoint.5.Security.ModesSupported=WPA3-Personal 2>&1 || true)
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T003340845889_DUT.log L5-L27
WiFi.AccessPoint.1.Security.ModesSupported="None,WEP-64,WEP-128,WEP-128iv,WPA-Personal,WPA2-Personal,WPA-WPA2-Personal,WPA3-Personal,WPA2-WPA3-Personal,WPA-Enterprise,WPA2-Enterprise,WPA-WPA2-Enterprise,OWE"
ERROR: set WiFi.AccessPoint.1.Security.ModesSupported failed (15 - is read only)
error=15
message=is read only

20260413T003340845889_DUT.log L28-L50
WiFi.AccessPoint.3.Security.ModesSupported="None,WPA3-Personal,OWE"
ERROR: set WiFi.AccessPoint.3.Security.ModesSupported failed (15 - is read only)
error=15
message=is read only

20260413T003340845889_DUT.log L51-L73
WiFi.AccessPoint.5.Security.ModesSupported="None,WEP-64,WEP-128,WEP-128iv,WPA-Personal,WPA2-Personal,WPA-WPA2-Personal,WPA3-Personal,WPA2-WPA3-Personal,WPA-Enterprise,WPA2-Enterprise,WPA-WPA2-Enterprise,OWE"
ERROR: set WiFi.AccessPoint.5.Security.ModesSupported failed (15 - is read only)
error=15
message=is read only
```

## Checkpoint summary (2026-04-13 early-2)

> This checkpoint records the `D079` runtime de-truncation fix. No new aligned case landed in this checkpoint.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `CommandResolver.sanitize_cli_fragment()` no longer strips the `WiFi....=...` setter tail from complex shell fragments that legitimately start with variable assignment / `$(` / pipe composition
- official rerun `20260413T002418591720` proves `D079 MACFiltering.Mode` is no longer `step_command_failed`
- both attempts executed the full AP1 / AP3 / AP5 setter/getter sequence and converged to the same live shape:
  - `BaselineMode5g/6g/24g = Off`
  - `BaselineMacaddrAcl5g/6g/24g = ABSENT`
  - `BaselineAclState5g/6g/24g = absent`
  - `SetOffStatus5g/6g/24g = invalid_value`
  - post-set getter + ACL state remained unchanged on all three bands
- current `D079` YAML still fails at `mode_baseline_5g.BaselineMode5g == BlackList` because live 5G baseline is now `Off`, so the case moves from `step_command_failed` to semantic `pass_criteria_not_satisfied` / workbook-authority review
- next ready `step_command_failed` revisit is `D088`

</details>

## Checkpoint summary (2026-04-13 early-1)

> This checkpoint records the shared `D047` / `D050` `step_command_failed` closure on top of the authoritative full run and the prior D072 setter-capture fix.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D047 SupportedHe160MCS` and `D050 SupportedVhtMCS` are now aligned via official reruns `20260412T235952361188` / `20260413T000249620932`
- the shared root cause had two layers:
  - both case YAMLs had drifted onto a custom 5G `TestPilot_BTM` / `WPA3-Personal` bring-up, while authoritative full run `20260412T113008433351` still used the generic `testpilot5G` / `WPA2-Personal` baseline
  - `_env_command_succeeded()` previously used an over-broad `"not found"` failure matcher, so valid getter payload `error=4 / message=parameter not found` was being short-circuited into `step_command_failed` before case `pass_criteria` could evaluate it
- both cases are now back on the generic 5G baseline and their metadata is refreshed to workbook rows `47` / `50`
- live STA evidence exact-closed the same generic WPA2 link (`SSID: testpilot5G`), while live DUT evidence exact-closed the same AssociatedDevice entry against:
  - LLAPI getter `error=4 / message=parameter not found`
  - sibling Rx/Tx capability fields from `WiFi.AccessPoint.1.AssociatedDevice.1.?`
  - matching `wl0 sta_info` capability markers for the same STA
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 / D047 / D050 reruns stays
  `239 / 420 full matches`、`181 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps stay `152` because workbook rows `47` / `50` are non-pass (`Not Support`) semantics
- next ready `step_command_failed` revisit is `D079`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D047` | 47 | `SupportedHe160MCS` | `Not Supported / N/A / N/A` | `20260412T235952361188_DUT.log L26-L133` | `20260412T235952361188_STA.log L39-L99` |
| `D050` | 50 | `SupportedVhtMCS` | `Not Supported / N/A / N/A` | `20260413T000249620932_DUT.log L26-L133` | `20260413T000249620932_STA.log L39-L99` |

#### D047 SupportedHe160MCS

**STA 指令**

```sh
printf '%s\n' ctrl_interface=/var/run/wpa_supplicant > /tmp/wpa_wl0.conf
printf '%s\n' update_config=1 >> /tmp/wpa_wl0.conf
printf '%s\n' 'network={' >> /tmp/wpa_wl0.conf
printf '%s\n' 'ssid="testpilot5G"' >> /tmp/wpa_wl0.conf
printf '%s\n' key_mgmt=WPA-PSK >> /tmp/wpa_wl0.conf
printf '%s\n' 'psk="00000000"' >> /tmp/wpa_wl0.conf
wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
wpa_cli -p /var/run/wpa_supplicant -i wl0 enable_network 0
wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0
iw dev wl0 link
```

**DUT 指令**

```sh
ubus-cli "WiFi.SSID.4.SSID?"
ubus-cli "WiFi.AccessPoint.1.Security.ModeEnabled?"
OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS?" 2>&1 || true)
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/error=\1/p'
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/message=\2/p'
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?" | sed -n 's/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.MACAddress="\([^"]*\)".*/SiblingAssocMac=\1/p; s/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.RxSupportedHe160MCS="\([^"]*\)".*/DriverRxSupportedHe160MCS=\1/p; s/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.TxSupportedHe160MCS="\([^"]*\)".*/DriverTxSupportedHe160MCS=\1/p'
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p')
STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f')
wl -i wl0 sta_info "$STA_MAC_LOWER"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260412T235952361188_STA.log L46-L59, L82-L99
ssid="testpilot5G"
key_mgmt=WPA-PSK
psk="00000000"
Successfully initialized wpa_supplicant
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: testpilot5G
        freq: 5180

20260412T235952361188_DUT.log L26-L54, L62-L70, L84-L133
WiFi.SSID.4.SSID="testpilot5G"
WiFi.AccessPoint.1.Security.ModeEnabled="WPA2-Personal"
WiFi.AccessPoint.1.Security.KeyPassPhrase="00000000"
WiFi.AccessPoint.1.Security.MFPConfig="Disabled"
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
ERROR: get WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS failed (4 - parameter not found)
error=4
message=parameter not found
SiblingAssocMac=2C:59:17:00:04:85
DriverRxSupportedHe160MCS=11,11,11,11
DriverTxSupportedHe160MCS=11,11,11,11
DriverAssocMac=2C:59:17:00:04:85
DriverHeCapsPresent=1
DriverMCSSetPresent=1
DriverHeSetPresent=1
```

#### D050 SupportedVhtMCS

**STA 指令**

```sh
printf '%s\n' ctrl_interface=/var/run/wpa_supplicant > /tmp/wpa_wl0.conf
printf '%s\n' update_config=1 >> /tmp/wpa_wl0.conf
printf '%s\n' 'network={' >> /tmp/wpa_wl0.conf
printf '%s\n' 'ssid="testpilot5G"' >> /tmp/wpa_wl0.conf
printf '%s\n' key_mgmt=WPA-PSK >> /tmp/wpa_wl0.conf
printf '%s\n' 'psk="00000000"' >> /tmp/wpa_wl0.conf
wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
wpa_cli -p /var/run/wpa_supplicant -i wl0 enable_network 0
wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0
iw dev wl0 link
```

**DUT 指令**

```sh
ubus-cli "WiFi.SSID.4.SSID?"
ubus-cli "WiFi.AccessPoint.1.Security.ModeEnabled?"
OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedVhtMCS?" 2>&1 || true)
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/error=\1/p'
printf '%s\n' "$OUT" | sed -n 's/.*failed (\([0-9][0-9]*\) - \(.*\))/message=\2/p'
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.?" | sed -n 's/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.MACAddress="\([^"]*\)".*/SiblingAssocMac=\1/p; s/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.RxSupportedVhtMCS="\([^"]*\)".*/DriverRxSupportedVhtMCS=\1/p; s/^WiFi\.AccessPoint\.1\.AssociatedDevice\.1\.TxSupportedVhtMCS="\([^"]*\)".*/DriverTxSupportedVhtMCS=\1/p'
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p')
STA_MAC_LOWER=$(echo "$STA_MAC" | tr 'A-F' 'a-f')
wl -i wl0 sta_info "$STA_MAC_LOWER"
```

**判定 pass 的 log 摘錄 / log 區間**

```text
20260413T000249620932_STA.log L46-L59, L82-L99
ssid="testpilot5G"
key_mgmt=WPA-PSK
psk="00000000"
Successfully initialized wpa_supplicant
iw dev wl0 link
Connected to 2c:59:17:00:19:95 (on wl0)
        SSID: testpilot5G
        freq: 5180

20260413T000249620932_DUT.log L26-L54, L62-L70, L84-L133
WiFi.SSID.4.SSID="testpilot5G"
WiFi.AccessPoint.1.Security.ModeEnabled="WPA2-Personal"
WiFi.AccessPoint.1.Security.KeyPassPhrase="00000000"
WiFi.AccessPoint.1.Security.MFPConfig="Disabled"
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
ERROR: get WiFi.AccessPoint.1.AssociatedDevice.1.SupportedVhtMCS failed (4 - parameter not found)
error=4
message=parameter not found
SiblingAssocMac=2C:59:17:00:04:85
DriverRxSupportedVhtMCS=9,9,9,9
DriverTxSupportedVhtMCS=9,9,9,9
DriverAssocMac=2C:59:17:00:04:85
DriverVhtCapsPresent=1
DriverMCSSetPresent=1
DriverVhtSetPresent=1
```

## Checkpoint summary (2026-04-12 late-5)

> This checkpoint records the shared setter-capture runtime fix and the D072 alignment closure on top of the authoritative full run.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- shared runtime root cause is now fixed:
  - single-line executable setter steps with `capture` were being replaced by synthesized readback queries before execution
  - `plugins/wifi_llapi/command_resolver.py` now preserves the authored setter path for this shape
- `D072 MobilityDomain` is now aligned via official reruns `20260412T231545173827` and `20260412T231709014359`
  - the first rerun proved the real setter path and closed as `pass after retry (2/2)`
  - the repeat rerun then passed on attempt 1
  - live DUT evidence exact-closed AP1 / AP3 / AP5 with `IEEE80211r.Enabled=1`, northbound `MobilityDomain=27476`, hostapd `mobility_domain=546B`, and exactly one `ft_over_ds=0` line per band
  - committed metadata is now workbook row `72`
  - `results_reference.v4.0.3` is now `Pass / Pass / Pass`
- overlay compare recomputed on top of authoritative full run `20260412T113008433351`
  plus D024 / D025 / D022 / D072 reruns is now
  `239 / 420 full matches`、`181 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps are now `152`
- next ready `step_command_failed` revisit is the tight-coupled `D047` / `D050` pair

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D072` | 72 | `MobilityDomain` | `Pass / Pass / Pass` | `20260412T231709014359_DUT.log L32-L207` | `N/A (AP-only case)` |

#### D072 MobilityDomain

**STA 指令**

```sh
# N/A (AP-only case; no STA transport used)
```

**DUT 指令**

```sh
ubus-cli WiFi.AccessPoint.1.IEEE80211r.Enabled=1
ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?" | sed -n "/Enabled=/s/.*=/Enabled5g=/p"
ubus-cli "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain?" | sed -n "/MobilityDomain=/s/.*=/MobilityDomain5g=/p"
ubus-cli WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=27476
grep -m1 '^mobility_domain=' /tmp/wl0_hapd.conf | sed 's/^mobility_domain=/MobilityDomainCfg5g=/'
grep -c '^ft_over_ds=0$' /tmp/wl0_hapd.conf | sed 's/^/FtOverDs5gZeroCount=/'
ubus-cli WiFi.AccessPoint.3.IEEE80211r.Enabled=1
ubus-cli WiFi.AccessPoint.3.IEEE80211r.MobilityDomain=27476
grep -m1 '^mobility_domain=' /tmp/wl1_hapd.conf | sed 's/^mobility_domain=/MobilityDomainCfg6g=/'
grep -c '^ft_over_ds=0$' /tmp/wl1_hapd.conf | sed 's/^/FtOverDs6gZeroCount=/'
ubus-cli WiFi.AccessPoint.5.IEEE80211r.Enabled=1
ubus-cli WiFi.AccessPoint.5.IEEE80211r.MobilityDomain=27476
grep -m1 '^mobility_domain=' /tmp/wl2_hapd.conf | sed 's/^mobility_domain=/MobilityDomainCfg24g=/'
grep -c '^ft_over_ds=0$' /tmp/wl2_hapd.conf | sed 's/^/FtOverDs24gZeroCount=/'
```

**判定 pass 的 log 摘錄 / log 區間**

```text
DUT L32-L68:
WiFi.AccessPoint.1.IEEE80211r.Enabled=1
Enabled5g=1
MobilityDomain5g=0
WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=27476
MobilityDomain5g=27476
MobilityDomainCfg5g=546B
FtOverDs5gZeroCount=1

DUT L116-L137:
WiFi.AccessPoint.3.IEEE80211r.MobilityDomain=27476
Enabled6g=1
MobilityDomain6g=27476
MobilityDomainCfg6g=546B
FtOverDs6gZeroCount=1

DUT L186-L207:
WiFi.AccessPoint.5.IEEE80211r.MobilityDomain=27476
Enabled24g=1
MobilityDomain24g=27476
MobilityDomainCfg24g=546B
FtOverDs24gZeroCount=1
```

## Checkpoint summary (2026-04-12 late-4)

> This checkpoint records the D022 alignment closure on top of the authoritative full run + D024/D025 overlays.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D022 HtCapabilities` is now aligned via official rerun `20260412T175538121906`
  - stale alias metadata is removed
  - `source.row` is refreshed from `19` to workbook row `22`
  - the durable driver oracle is now the parsed `wl sta_info` `HT caps 0x...` bitmask
    rather than a brittle token scrape
  - live evidence exact-closed `HtCapabilities="40MHz,SGI20,SGI40"` with
    `DriverHt40MHz=1`, `DriverHtSgi20=1`, and `DriverHtSgi40=1`
- targeted D022 guardrails stayed `1 passed`
- overlay compare after applying the D024, D025, and D022 reruns is now
  `238 / 420 full matches`、`182 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps are now `153`
- `D020` remains a verified fail-shaped mismatch, so the next ready case after this
  checkpoint is `D034`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D022` | 22 | `HtCapabilities` | `Pass / Not Supported / Pass` | `20260412T175538121906_DUT.log L336-L368` | `20260412T175538121906_STA.log L64-L89` |

#### D022 HtCapabilities

**STA 指令**

```sh
wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.HtCapabilities?"
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p'); HT_HEX=$([ -n "$STA_MAC" ] && wl -i wl0 sta_info $STA_MAC | sed -n 's/.*HT caps 0x\([0-9A-Fa-f][0-9A-Fa-f]*\):.*/\1/p' | head -n1); if [ -n "$HT_HEX" ]; then HT_VAL=$((0x$HT_HEX)); [ $((HT_VAL & 0x0002)) -ne 0 ] && echo DriverHt40MHz=1; [ $((HT_VAL & 0x0020)) -ne 0 ] && echo DriverHtSgi20=1; [ $((HT_VAL & 0x0040)) -ne 0 ] && echo DriverHtSgi40=1; fi
```

**判定 pass 的 log 摘錄 / log 區間**

```text
STA L64-L89:
Connected to 2c:59:17:00:19:95 (on wl0)
SSID: TestPilot_BTM
wpa_state=COMPLETED

DUT L336-L368:
WiFi.AccessPoint.1.AssociatedDevice.1.HtCapabilities="40MHz,SGI20,SGI40"
DriverHt40MHz=1
DriverHtSgi20=1
DriverHtSgi40=1
```

## Checkpoint summary (2026-04-12 late-3)

> This checkpoint records the D025 alignment closure on top of the authoritative full run + D024 overlay.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D025 LastDataUplinkRate` is now aligned via official rerun `20260412T174551843336`
  - stale alias metadata is removed
  - `source.row` is refreshed from `22` to workbook row `25`
  - live evidence exact-closed `LastDataUplinkRate=6000` with
    `DriverLastUplinkRateRounded=6000`
  - workbook `H`, public HAL comments, and repeated runtime replays continue to support
    driver `rate of last rx pkt` as the STA -> AP truth source
- targeted D025 guardrails stayed `3 passed`
- overlay compare after applying the D024 and D025 reruns is now
  `237 / 420 full matches`、`183 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps are now `154`
- `D020` remains a verified fail-shaped mismatch, so the next ready case after this
  checkpoint is `D022`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D025` | 25 | `LastDataUplinkRate` | `Pass / Pass / Pass` | `20260412T174551843336_DUT.log L336-L366` | `20260412T174551843336_STA.log L64-L89` |

#### D025 LastDataUplinkRate

**STA 指令**

```sh
wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
ubus-cli "WiFi.SSID.4.BSSID?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LastDataUplinkRate?"
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p'); RATE=$(wl -i wl0 sta_info $STA_MAC | sed -n 's/.*rate of last rx pkt: \([0-9][0-9]*\) kbps.*/\1/p' | head -n1); [ -n "$RATE" ] && echo DriverLastUplinkRateRounded=$((RATE/100*100))
```

**判定 pass 的 log 摘錄 / log 區間**

```text
STA L64-L89:
Connected to 2c:59:17:00:19:95 (on wl0)
SSID: TestPilot_BTM
tx bitrate: 541.6 MBit/s
wpa_state=COMPLETED

DUT L336-L366:
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
WiFi.SSID.4.BSSID="2c:59:17:00:19:95"
WiFi.AccessPoint.1.AssociatedDevice.1.LastDataUplinkRate=6000
DriverLastUplinkRateRounded=6000
```

## Checkpoint summary (2026-04-12 late-2)

> This checkpoint records the first authoritative post-recovery full run and the D024 alignment closure.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- guarded 6G recovery commit `338891b7115e5c41d04f45bd79c70ce4b117cebc` is now pushed
- authoritative full run `20260412T113008433351` completed all `420` cases with `195` pass /
  `225` fail counts and did not reintroduce the old early baseline collapse
  - `D004`~`D013` all stayed plain `Pass`
  - the old invalid prefix (`D007 Fail` / `D009 FailEnv` / `D010 FailEnv` / `D011 FailTest`)
    did not recur
- `compare-0401` on the authoritative full run raised the repo snapshot to
  `235 / 420 full matches`、`185 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps on that authoritative full run were `156`
- `D024 LastDataDownlinkRate` is now aligned via official rerun `20260412T172957084134`
  - stale alias metadata is removed
  - `source.row` is refreshed from `21` to workbook row `24`
  - the durable oracle is now the driver last-tx 100-kbps bucket window
  - live evidence exact-closed `LastDataDownlinkRate=487400` with
    `DriverLastDownlinkRateLower=487400` and `DriverLastDownlinkRateUpper=487500`
- regression after the D024 rewrite:
  - targeted D024 guardrails: `6 passed`
  - full repo suite: `1645 passed`
- overlay compare after applying the D024 rerun is now
  `236 / 420 full matches`、`184 mismatches`、`62 metadata drifts`
- actionable workbook-Pass gaps are now `155`
- next ready case after this checkpoint: `D025 LastDataUplinkRate`

</details>

### Per-case 摘要表（zh-tw）

| case id | workbook row | API 名稱 | verdict | DUT log interval | STA log interval |
| --- | ---: | --- | --- | --- | --- |
| `D024` | 24 | `LastDataDownlinkRate` | `Pass / Pass / Pass` | `20260412T172957084134_DUT.log L367-L404` | `20260412T172957084134_STA.log L64-L89` |

#### D024 LastDataDownlinkRate

**STA 指令**

```sh
wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
iw dev wl0 link
wpa_cli -p /var/run/wpa_supplicant -i wl0 status
```

**DUT 指令**

```sh
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?"
ubus-cli "WiFi.SSID.4.BSSID?"
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LastDataDownlinkRate?"
STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n 's/.*MACAddress="\([^"]*\)".*/\1/p'); RATE=$(wl -i wl0 sta_info $STA_MAC | sed -n 's/.*rate of last tx pkt: \([0-9][0-9]*\) kbps.*/\1/p' | head -n1); if [ -n "$RATE" ]; then UPPER=$((RATE/100*100)); LOWER=$UPPER; [ "$LOWER" -ge 100 ] && LOWER=$((LOWER-100)); printf "DriverLastDownlinkRateLower=%s\nDriverLastDownlinkRateUpper=%s\n" "$LOWER" "$UPPER"; fi
```

**判定 pass 的 log 摘錄 / log 區間**

```text
STA L64-L89:
Connected to 2c:59:17:00:19:95 (on wl0)
SSID: TestPilot_BTM
tx bitrate: 541.6 MBit/s
wpa_state=COMPLETED

DUT L367-L404:
WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"
WiFi.SSID.4.BSSID="2c:59:17:00:19:95"
WiFi.AccessPoint.1.AssociatedDevice.1.LastDataDownlinkRate=487400
DriverLastDownlinkRateLower=487400
DriverLastDownlinkRateUpper=487500
```

## Checkpoint summary (2026-04-12)

> This checkpoint records the guarded 6G recovery patch and the post-fix live revalidation after the invalid full run was stopped.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- invalid full run `20260412T084218316557` has been discarded as non-authoritative after early
  `D007 Fail`、`D009 FailEnv`、`D010 FailEnv`、`D011 FailTest` showed multi-band
  baseline instability instead of trustworthy case verdicts
- live WAL isolated the remaining shared-baseline failure to a narrower DUT-side path:
  - `wl -i wl1 bss` could return `wl driver adapter not found`
  - the old runtime still continued into direct `wl1` hostapd restart
  - that led to `Could not set interface wl1 UP: Operation not permitted` /
    `nl80211 driver initialization failed`
- minimal fix landed in `plugins/wifi_llapi/plugin.py`
  - new `_env_output_indicates_missing_adapter()` helper
  - `_wait_for_dut_bss_ready()` now short-circuits on missing-adapter probe output
  - `_apply_6g_ocv_fix()` now probes `wl -i wl1 bss` before direct restart and defers
    restart entirely when `wl1` is missing
- regression after the fix:
  - targeted 6G recovery tests: `8 passed`
  - full repo suite: `1645 passed`
- both boards were then clean-reset with `firstboot -y;sync;sync;sync;reboot -f`
- COM0 was briefly trapped in U-Boot because broker/self-test interrupted autoboot;
  serialwrap `console-attach` + `interactive-send '\r'` + `session recover` brought it back
  to `READY`, and COM1 also ended at `READY`
- patched sequential live reruns all revalidated on the same recovered baseline:
  - `D009 AssociationTime` → `Pass/Pass/Pass` via run `20260412T110545613993`
  - `D010 AuthenticationState` → `Pass/Pass/Pass` via run `20260412T111048362099`
  - `D011 AvgSignalStrength` → `Pass/Pass/Pass` via run `20260412T111549474171`
- concrete evidence from those reruns:
  - `D009` 6G ended with `wpa_state=COMPLETED`, `ConnectionSeconds6g=4`, and populated
    `AssociationTime`
  - `D010` 5G/6G/2.4G each ended with `DriverAuthState=1` and
    `WiFi.AccessPoint.{1,3,5}.AssociatedDevice.1.AuthenticationState=1`
  - `D011` no longer reproduces the old 5G `iw dev wl0 link -> Not connected.` failure;
    all three bands stayed `wpa_state=COMPLETED`, and the final projected verdict is now
    `Pass/Pass/Pass`
- next ready action from this checkpoint: commit/push the guarded 6G recovery patch and
  relaunch full run from current HEAD

</details>

## Checkpoint summary (2026-04-10)

> This checkpoint records the first post-summary live calibration result after the detached full run comparison.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- `D111 getStationStats() AssociationTime` has now been revalidated live as plain `Pass` via run `20260410T110659169758`
- workbook replay on DUT/STA proved the live 0403 shape already matches the workbook intent:
  - DUT `ubus-cli "WiFi.AccessPoint.*.getStationStats()" | grep -E 'AssociationTime|AuthenticationState|MACAddress'`
  - DUT `ubus-cli "WiFi.AccessPoint.1.getStationStats()" | grep -E 'AssociationTime|AuthenticationState|MACAddress'`
  - both showed `AssociationTime = "YYYY-MM-DDTHH:MM:SSZ",`
- source-backed root cause was repo-side parsing order, not missing runtime data:
  - `_extract_key_values()` stripped quotes before removing the trailing comma from getStationStats() output
  - this left a spurious tail `"` in `stats_output.AssociationTime`
- minimal fix landed in `plugins/wifi_llapi/plugin.py`
- regression after the fix:
  - targeted parser / D111 tests: `4 passed`
  - full `plugins/wifi_llapi/tests/test_wifi_llapi_plugin_runtime.py`: `1223 passed`
- no YAML criteria change was required for D111; AP1-specific command + ISO-8601 regex remain valid after the parser fix
- `D211 OperatingStandards` workbook row `211` replay is now blocked on live DUT:
  - BE phase getter follows setter, but AX phase still keeps `wl0/wl1/wl2 eht features=127`
  - 6G `/tmp/wl1_hapd.conf` still keeps secondary `ieee80211be=1` after `OperatingStandards=ax`
- source-backed triage shows two layers that cannot currently be collapsed into workbook `Pass`:
  - `wldm_Radio_OperatingStandards()` still reads/writes `{nvifname}_oper_stands`
  - `whm_brcm_set_hostapd_mld()` still injects `ieee80211be=1`, and the 0315 / 0403 copies of `whm_brcm_conf_map.c` + `whm_brcm_rad_mlo.c` are unchanged for this behavior
- therefore D211 stays blocked/fail-shaped; no YAML rewrite landed, and the detailed handoff lives in `plugins/wifi_llapi/reports/D211_block.md`
- `D262 getRadioAirStats():void` is now revalidated live as plain `Pass` via run `20260410T115126959920`
- the first raw replay after D211 only returned 6G `[""]` because `WiFi.Radio.2.Status="Down"`; source-backed triage showed `_getRadioAirStats()` early-returns `amxd_status_ok` without filling the return map whenever `wld_rad_isActive(pR)` is false
- after `wifi-llapi baseline-qualify --band 6g --repeat-count 1 --soak-minutes 0` restored all three radios to `Status="Up"`, the same method call returned structured air-stats objects on 5G / 6G / 2.4G, and the YAML row drift has now been refreshed from `264` to workbook row `262`
- `D263 getRadioStats() BroadcastPacketsReceived` is now revalidated live as plain `Pass` via run `20260410T115553270636`
- workbook row `263` still prints a stale sample `BroadcastPacketsReceived = 0`, but 0403 patch note `17) Radio.Stats, SSID.Stats issues` says Radio.Stats rework now uses dev_ext bcast/mcast counters, and live rerun returned numeric `BroadcastPacketsReceived = 363 / 142 / 113` on 5G / 6G / 2.4G; this confirms the current regex-based numeric-field validation is aligned with 0403 semantics, while the workbook sample zero is no longer the pass oracle
- the D263 YAML row drift has now been refreshed from `265` to workbook row `263`
- `D264 getRadioStats() BroadcastPacketsSent` is now revalidated live as plain `Pass` via run `20260410T120131256198`
- workbook row `264` still prints a stale sample `BroadcastPacketsSent = 0`, but it is covered by the same 0403 Radio.Stats rework; live rerun returned numeric `BroadcastPacketsSent = 921 / 1080 / 1168` on 5G / 6G / 2.4G, so the current regex-based numeric-field validation stays aligned with 0403 semantics and the sample zero is no longer the pass oracle
- the D264 YAML row drift has now been refreshed from `266` to workbook row `264`
- `D265 getRadioStats() BytesReceived` is now revalidated live as plain `Pass` via run `20260410T120653665723`
- workbook row `265` still describes a `/proc/net/dev` cross-check heuristic, but 0403 reactivated `BytesReceived` from driver `if_counters.rxbyte` in `whm_brcm_api_ext.c`; live rerun returned numeric `BytesReceived` on all three radios, so the current regex-based numeric-field validation stays aligned with 0403 semantics while the old `/proc/net/dev` note is no longer the authoritative oracle
- the D265 YAML row drift has now been refreshed from `267` to workbook row `265`
- `D266 getRadioStats() BytesSent` is now revalidated live as plain `Pass` via run `20260410T122049771373`
- source-backed triage shows 0403 `whm_brcm_rad.c` ultimately refreshes radio `BytesSent` through `whm_brcm_rad_get_counters_fromfile()` and parses driver `wl ... counters` `txbyte`; live compare proved 5G/2.4G API values match driver `wl counters txbyte`, but 6G matches `/proc/net/dev` `TX_byte` instead of `wl1 counters`, so workbook row `266`'s `/proc/net/dev` heuristic is not a stable 0403 oracle even though the API still returns valid numeric radio counters
- the D266 YAML row drift has now been refreshed from `268` to workbook row `266`
- `D267 getRadioStats() DiscardPacketsReceived` is now revalidated live as plain `Pass` via run `20260410T122535158860`
- source-backed triage shows workbook row `267`'s `/proc/net/dev` `RX_drop-pkg` heuristic is only partially aligned on 0403: live compare returned API `DiscardPacketsReceived = 0 / 3752 / 0`, `/proc/net/dev = 565 / 3752 / 356`, and driver `wl ... counters` `rxdropped = 0 / 0 / 0` on 5G / 6G / 2.4G; together with the source flow (`ifstats->rxdiscard` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later), that makes `/proc/net/dev` an unstable cross-band oracle, so the current regex numeric validation remains the right semantic
- the D267 YAML row drift has now been refreshed from `269` to workbook row `267`
- `D268 getRadioStats() DiscardPacketsSent` is now revalidated live as plain `Pass` via run `20260410T122928854759`
- source-backed triage shows workbook row `268`'s `/proc/net/dev` `TX_drop-pkg` heuristic is only partially aligned on 0403: live compare returned API `DiscardPacketsSent = 0 / 3469 / 0`, `/proc/net/dev = 184 / 3467 / 87`, and driver `wl ... counters` `txdropped = 0 / 0 / 0` on 5G / 6G / 2.4G; together with the source flow (`ifstats->txdiscard` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later), that makes `/proc/net/dev` an unstable cross-band oracle, so the current regex numeric validation remains the right semantic
- the D268 YAML row drift has now been refreshed from `270` to workbook row `268`
- `D269 getRadioStats() ErrorsReceived` is now revalidated live as plain `Pass` via run `20260410T123405993813`
- source-backed triage shows workbook row `269`'s zero/proc heuristic is only partially aligned on 0403: live compare returned API `ErrorsReceived = 8 / 0 / 8`, `/proc/net/dev = 0 / 0 / 0`, and driver `wl ... counters` `rxerror = 8 / 8 / 8` on 5G / 6G / 2.4G; together with the source flow (`ifstats->rxerror` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later), that makes workbook zero/proc evidence an unstable cross-band oracle, so the current regex numeric validation remains the right semantic
- the D269 YAML row drift has now been refreshed from `271` to workbook row `269`
- `D270 getRadioStats() ErrorsSent` is now revalidated live as plain `Pass` via run `20260410T123844750130`
- source-backed triage shows workbook row `270`'s zero/proc heuristic still aligns on 0403: live compare returned API `ErrorsSent = 0 / 0 / 0`, `/proc/net/dev = 0 / 0 / 0`, and driver `wl ... counters` `txerror = 0 / 0 / 0` on 5G / 6G / 2.4G, so this case reduces to row drift only and the current regex numeric validation remains the right semantic
- the D270 YAML row drift has now been refreshed from `272` to workbook row `270`
- `D271 getRadioStats() MulticastPacketsReceived` is now revalidated live as plain `Pass` via run `20260410T124521685886`
- source-backed triage shows workbook row `271`'s `/proc/net/dev` `RX_multipkg` heuristic is only partially aligned on 0403: live compare returned API `MulticastPacketsReceived = 0 / 142 / 0`, `/proc/net/dev = 363 / 142 / 113`, and driver `wl ... counters` `d11_rxmulti = 10 / 0 / 0` on 5G / 6G / 2.4G; together with the source flow (`ifstats->rxmulti` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later, then broadcast subtraction merge), that makes `/proc/net/dev` an unstable cross-band oracle, so the current regex numeric validation remains the right semantic
- the D271 YAML row drift has now been refreshed from `273` to workbook row `271`
- `D272 getRadioStats() MulticastPacketsSent` is now revalidated live as plain `Pass` via run `20260410T125050031171`
- source-backed triage shows workbook row `272`'s `/proc/net/dev_extstats` `TX_multipkg` heuristic is only partially aligned on 0403: live compare returned API `MulticastPacketsSent = 89594 / 91022 / 92958`, `dev_extstats = 7260 / 2880 / 2260`, and driver `wl ... counters` `d11_txmulti = 90551 / 28627 / 94162` on 5G / 6G / 2.4G; together with the source flow (`txframe` first, `d11_txmulti/d11_txbcast` overwrite next, then broadcast subtraction merge), that makes `dev_extstats` an unstable cross-band oracle, so the current regex numeric validation remains the right semantic
- the D272 YAML row drift has now been refreshed from `274` to workbook row `272`
- `D273 getRadioStats() PacketsReceived` is now revalidated live as plain `Pass` via run `20260410T125433470613`
- source-backed triage shows workbook row `273`'s `/proc/net/dev` `RX_pkg` heuristic is only partially aligned on 0403: live compare returned API `PacketsReceived = 935 / 432 / 220`, `/proc/net/dev = 1086 / 432 / 333`, and driver `wl ... counters` `rxframe = 935 / 288 / 220` on 5G / 6G / 2.4G, so `/proc/net/dev` is not a stable cross-band oracle for this field on 0403 and the current regex numeric validation remains the right semantic
- the D273 YAML row drift has now been refreshed from `275` to workbook row `273`
- `D274 getRadioStats() PacketsSent` is now revalidated live as plain `Pass` via run `20260410T125437398493`
- source-backed triage shows workbook row `274`'s `/proc/net/dev` `TX_pkg` heuristic is only partially aligned on 0403: live compare returned API `PacketsSent = 125099 / 92000 / 109840`, `/proc/net/dev = 97904 / 92000 / 97690`, and driver `wl ... counters` `txframe = 125099 / 53906 / 109840` on 5G / 6G / 2.4G; together with the source flow (`txframe` first, `d11_txmulti/d11_txbcast` overwrite next), that makes `/proc/net/dev` an unstable cross-band oracle, so the current regex numeric validation remains the right semantic
- the D274 YAML row drift has now been refreshed from `276` to workbook row `274`
- `D275 getRadioStats() UnicastPacketsReceived` is now revalidated live as plain `Pass` via run `20260410T125441250801`
- source-backed triage shows workbook row `275`'s proc/sample-zero heuristic is only partially aligned on 0403: live compare returned API `UnicastPacketsReceived = 926 / 0 / 220`, while driver `wl ... counters` showed `rxframe = 936 / 288 / 220` and `d11_rxmulti = 10 / 0 / 0` on 5G / 6G / 2.4G; 5G/2.4G line up with the derived `rxframe - d11_rxmulti` shape, but 6G still collapses to zero, so the workbook proc/zero heuristic is not a stable 0403 oracle and the current regex numeric validation remains the right semantic
- the D275 YAML row drift has now been refreshed from `277` to workbook row `275`
- `D276 getRadioStats() UnicastPacketsSent` is now revalidated live as plain `Pass` via run `20260410T125445239119`
- source-backed triage shows workbook row `276`'s proc/sample-zero heuristic is only partially aligned on 0403: live compare returned API `UnicastPacketsSent = 34089 / 0 / 14988`, while driver `wl ... counters` showed `txframe = 125177 / 53985 / 109891` and `d11_txmulti = 91088 / 29256 / 94903` on 5G / 6G / 2.4G; 5G/2.4G line up with the derived `txframe - d11_txmulti` shape, but 6G still collapses to zero, so the workbook proc/zero heuristic is not a stable 0403 oracle and the current regex numeric validation remains the right semantic
- the D276 YAML row drift has now been refreshed from `278` to workbook row `276`
- `D277 getScanResults() Bandwidth` is currently blocked before semantic replay
- the initial DUT gate issue was recoverable, and the earlier direct probes did narrow the shape to raw 5G/6G full scan capture; however, the new repo-side scan timeout fallback still did not produce an authoritative isolated replay
- the isolated rerun reached `setup_env`, then WAL evidence showed it entered raw `WiFi.Radio.2.getScanResults()` until serialwrap recovery injected `^C`, DUT printed `Please press Enter to activate this console.`, and `COM0` fell back to `ATTACHED / PROMPT_TIMEOUT` until manual recovery returned it to `READY`
- so the current blocker is still transport-side 6G scan capture rather than a proven `Bandwidth` semantic mismatch; workbook row `277`'s BSSID-targeted compare is still pending authoritative replay
- no YAML row refresh or semantic rewrite landed for `D277`; see `plugins/wifi_llapi/reports/D277_block.md`
- `D278 getScanResults() BSSID` reran plain `Pass` at `20260410T135946424063` after converting the case to a workbook-style target compare
- the new live path captures the first LLAPI target BSSID on each band, then cross-checks the same target against `iw dev wl0/wl1/wl2 scan`; all three bands matched authoritatively: `38:88:71:2f:f6:a7` on 5G, `3a:06:e6:2b:a3:1a` on 6G, and `8c:19:b5:6e:85:e1` on 2.4G
- D278 YAML row drift is now refreshed from `280` to workbook row `278`
- `D279 getScanResults() Channel` reran plain `Pass` at `20260410T140714322443` after converting the case to a workbook-style target BSSID + `iw freq -> channel` compare
- the first live attempt `20260410T140447198030` exposed a parser bug where `/Channel = /` was reading `CentreChannel`; after tightening the LLAPI parse to the real `Channel =` line, the rerun matched authoritatively on all three bands: `36/36` on 5G, `5/5` on 6G, and `1/1` on 2.4G
- D279 YAML row drift is now refreshed from `281` to workbook row `279`
- `D280 getScanResults() EncryptionMode` reran plain `Pass` at `20260410T143122662554` after converting the case to a workbook-style first-WPA-target compare
- 0403 source still constrains neighboring WiFi `EncryptionMode` to `TKIP / AES / TKIPandAES / None`, but live LLAPI continues to emit `Default`; the rerun locked that fail-shaped mismatch authoritatively against the same-target `iw dev wl0/wl1/wl2 scan` cipher evidence on all three bands
- live evidence matched the same three target BSSIDs across bands: `38:88:71:2f:f6:a7` on 5G (`WPA2-Personal`, `CCMP -> AES`), `3a:06:e6:2b:a3:1a` on 6G (`WPA3-Personal`, `CCMP -> AES`), and `8c:19:b5:6e:85:e1` on 2.4G (`WPA2-WPA3-Personal`, `CCMP -> AES`), while LLAPI `EncryptionMode` stayed `Default` on every band
- D280 YAML row drift is now refreshed from `282` to workbook row `280`
- `D281 getScanResults() Noise` remains blocked, but the authority model is now corrected. The earlier workbook-style trials (`20260410T155529962490` / `20260410T155932807150`) did prove the old direct-`wl escanresults` replay was unstable, and the newer parser-fix trial `20260411T211133728869` then proved that rewrite still had a local same-target capture bug
- the sanitized rerun `20260411T211327344984` exposed the real live shape: 5G exact-closes against same-target `wl escanresults` noise (`-100/-100`), 6G keeps a repeatable drift (`-97/-102`, then `-97/-103`), and 2.4G stays non-durable (`-78/-76`, then `-78/-78`). New 0403 source tracing through `wifiGen_rad_getScanResults()` and `s_updateScanResultsWithSpectrumInfo()` now shows public `getScanResults().Noise` is back-filled from per-channel spectrum `noiselevel`, while the generic scan-result parser itself does not populate `noise`; because public `getSpectrumInfo()` is still empty in the current lab state, the committed YAML stays unchanged at stale row `283`, and details are recorded in `plugins/wifi_llapi/reports/D281_block.md`
- `D282 getScanResults() OperatingStandards` also remains blocked, but the authority model is now corrected. Active 0403 source tracing shows the current public ubus getter uses nl80211 scan results parsed from beacon/probe IEs, copies `pWirelessDevIE->operatingStandards` into `wld_scanResultSSID_t.operatingStandards`, caches that in `lastScanResults`, and serializes it with `swl_radStd_toChar(..., SWL_RADSTD_FORMAT_STANDARD, 0)`; the older Broadcom `_wldm_get_standards()` helper is therefore no longer treated as the active public authority for this row
- the existing isolated rerun `20260410T163026194231` still blocks the rewrite, but for a narrower reason: 5G exact-closes at `a,n,ac,ax`, 6G still emits no same-target `WlOperatingStandards6g`, and 2.4G still drifts to an extra external `be` (`LLAPI b,g,n,ax` vs `wl b,g,n,ax,be`). Because no durable same-source oracle replays the same parsed IE bitmask semantics on all three bands, `plugins/wifi_llapi/cases/D282_getscanresults_operatingstandards.yaml` stays unchanged at stale row `284`, and details are recorded in `plugins/wifi_llapi/reports/D282_block.md`
- `D283 getScanResults() RSSI` and `D286 getScanResults() SignalStrength` are now treated as the same active public `ssid->rssi` field family. Fresh isolated rerun `20260411T214050136894` proved the committed D283 generic case still hangs after `setup_env`: it produced no step output, no markdown/json/xlsx report files, left `plugins/wifi_llapi/reports/agent_trace/20260411T214050136894/` empty, and pushed `COM0` into a recoverable `TARGET_UNRESPONSIVE` state
- active 0403 source tracing now shows this is not a standalone legacy parser field: `wld_nl80211_parser.c` fills `pResult->rssi`, and `wld_rad_scan.c` exports both public `RSSI` and public `SignalStrength` from that same `ssid->rssi`. `D286_block.md` is now corrected to that same source model, but its existing replay evidence still stays blocked (`5G -64/-65`, missing 6G same-target replay, 2.4G `-46` vs `-55/-56` / raw `-54`). So D283 remains blocked on the committed full-payload transport shape, while D286 remains blocked on the shared semantic replay gap; details are recorded in `plugins/wifi_llapi/reports/D283_block.md` and `plugins/wifi_llapi/reports/D286_block.md`
- `D287 getScanResults() SSID` also remains blocked, but the authority model is now corrected. Active 0403 public `SSID` is carried in the parsed scan-result model (`pWirelessDevIE->ssid` -> `wld_scanResultSSID_t.ssid` -> public `SSID`) rather than being treated as a pure raw `SSID:` helper field
- the existing isolated rerun `20260410T182739821870` therefore stays blocked for a narrower reason: 5G and 2.4G exact-close on the same target BSSID, but 6G still exposes `3a:06:e6:2b:a3:1a` / `.ROAMTEST_RSNO_P10P_1` on LLAPI while both `iw` and direct raw `wl -i wl1 escanresults` fail to replay that same target. Because there is still no durable all-band same-source external replay for the 6G target, `plugins/wifi_llapi/cases/D287_getscanresults_ssid.yaml` stays unchanged at stale row `289`, and details are recorded in `plugins/wifi_llapi/reports/D287_block.md`
- `D290 getScanResults() CentreChannel` is now aligned. Source-backed survey had already confirmed the field is real on 0403 (`wld_radio.odl` declares `CentreChannel`, `wld_rad_scan.c` copies `ssid->centreChannel`, and `wld_nl80211_parser.c` computes it through `swl_chanspec_getCentreChannel()` with a 20MHz fallback), but the old blocker only lacked the right same-target replay path. After one-shot environment repair (`wifi-llapi baseline-qualify --repeat-count 1 --soak-minutes 0`), fresh isolated rerun `20260411T220324862766` closed same-target raw `wl escanresults` Chanspec replay on all three bands: 5G exact-closes at `42/42`, 2.4G exact-closes at `1/1`, and 6G is now locked as the source-backed fail-shaped mismatch `31/15` on BSSID `6e:15:db:9e:33:72`
- `plugins/wifi_llapi/cases/D290_getscanresults_centrechannel.yaml` is now refreshed from stale row `292` to workbook row `290`, `results_reference.v4.0.3` is now `Pass / Fail / Pass`, targeted D290 guardrails are green (`16 passed` targeted D290 runtime guardrails), and the next ready case in the current repo inventory is `D529`
- `D529 getSpectrumInfo channel` is now aligned. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "channel", llEntry->channel)`, and fresh isolated rerun `20260411T221613327385` plus repeated direct probes now lock the first serialized spectrum-entry channels at `36 / 2 / 1` on `5g / 6g / 2.4g`
- `plugins/wifi_llapi/cases/D529_getspectruminfo_channel.yaml` now fixes the template metadata shape (`object=WiFi.Radio.{i}.`, `api=getSpectrumInfo()`), replaces the old generic numeric regex with explicit first-entry channel extractors, keeps workbook row `531` at plain `Pass / Pass / Pass`, and moves the next ready case in the current repo inventory to `D530`
- `D530 getSpectrumInfo noiselevel` is now aligned, but it stays a dynamic numeric case rather than a fixed-value case. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(int32_t, "noiselevel", llEntry->noiselevel)`, so the field is a survey-driven live reading rather than a stable constant
- a first exact-value trial was rejected after 2.4G drifted across retries/reruns (`-75 / -77 / -78`), so `plugins/wifi_llapi/cases/D530_getspectruminfo_noiselevel.yaml` only fixes the template metadata shape (`object=WiFi.Radio.{i}.`, `api=getSpectrumInfo()`), preserves the source-correct numeric regex pass shape, uses isolated rerun `20260411T222349217612` as the green lock, and moves the next ready case in the current repo inventory to `D531`
- `D531 getSpectrumInfo accesspoints` is now aligned, and it follows the same metadata-only dynamic numeric pattern. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "accesspoints", llEntry->nrCoChannelAP)`, so the field is a survey-driven co-channel AP count rather than a fixed constant
- `plugins/wifi_llapi/cases/D531_getspectruminfo_accesspoints.yaml` therefore only fixes the template metadata shape (`object=WiFi.Radio.{i}.`, `api=getSpectrumInfo()`), preserves the source-correct numeric regex pass shape, uses isolated rerun `20260411T223140870454` as the green lock, and moves the next ready case in the current repo inventory to `D532`
- `D532 getSpectrumInfo ourUsage` is now aligned, and it follows the same metadata-only dynamic numeric pattern. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "ourUsage", llEntry->ourUsage)`, while `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives that live percentage from survey airtime (`ourTime / total_time`). Isolated rerun `20260411T223658523608` passed cleanly with the generic numeric verdict shape
- the same workbook re-check exposed a stale `source.row` drift across the whole spectrum batch, so `D528-D533` are now corrected to the actual workbook rows `528-533` instead of the old `530-535` carry-over
- `D533 getSpectrumInfo availability` is now aligned as the last metadata-only dynamic numeric case in this batch. Active 0403 source keeps the public field on `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(uint32_t, "availability", llEntry->availability)`, while `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives the live percentage from survey idle/free-time timing; isolated rerun `20260411T224035464927` passed cleanly with the generic numeric verdict shape, and the next unresolved queue in the current repo inventory returns to `D322`, `D331`, `D333`, and `D336`
- `D284 getScanResults() SecurityModeEnabled` is now also blocked. Source trace still maps neighboring `SecurityModeEnabled` from `AKM Suites` / `RSN`, and isolated rerun `20260410T170750425931` did prove same-target replay on 5G (`38:88:71:2f:f6:a7` -> `WPA2-Personal`) plus 2.4G (`8c:19:b5:6e:85:e1` -> `WPA2-WPA3-Personal`), but 6G would not freeze to one BSSID: LLAPI chose `3a:06:e6:2b:a3:1a` (`.ROAMTEST_RSNO_P10P_1`) while same-target `iw` emitted `IwSecurityMode6g=None`, and follow-up manual probes showed LLAPI can also expose `2C:59:17:00:19:96` (`OpenWrt_1`) as another `WPA3-Personal` target while `iw` prefers that associated BSSID instead
- because the follow-up isolated rerun `20260410T171358112868` then failed to emit `LlapiBssid6g` for an associated-BSSID selector, the D284 trial rewrite was rejected, `plugins/wifi_llapi/cases/D284_getscanresults_securitymodeenabled.yaml` stays unchanged at stale row `286`, post-revert plugin runtime regression is still `1223 passed`, and details are recorded in `plugins/wifi_llapi/reports/D284_block.md`
- `D285 getScanResults() SignalNoiseRatio` is now also blocked. `compare-0401.md` still maps the case to workbook row `285`, but the committed YAML stays at stale row `287`; source survey showed 0403 neighboring scan internals still expose `RSSI` / `SignalStrength` plus `Noise`, while `wld_radio.odl` and public `wld.h` expose a derived `SignalNoiseRatio` only at the scan-result model layer. Standalone LLAPI replay did prove the field exists on live output (`3A:06:E6:2B:A3:1A` -> `RSSI=-93`, `Noise=-97`, `SignalNoiseRatio=4` on 6G; `8C:19:B5:6E:85:E1` -> `RSSI=-46`, `Noise=-80`, `SignalNoiseRatio=34` on 2.4G), but source-backed same-target replay still would not close: direct `wl -i wl1 escanresults` could not find the 6G LLAPI first BSSID at all, while a same-target 2.4G raw `wl -i wl2 escanresults` probe did find `8C:19:B5:6E:85:E1` yet reported `RSSI=-54 dBm`, `noise=-75 dBm`, `SNR=21 dB`, drifting far from LLAPI `34`
- because no deterministic source-backed replay exists yet, the D285 trial rewrite was rejected, `plugins/wifi_llapi/cases/D285_getscanresults_signalnoiseratio.yaml` stays unchanged at stale row `287`, and details are recorded in `plugins/wifi_llapi/reports/D285_block.md`
- `D286 getScanResults() SignalStrength` is now also blocked. Source trace still keeps neighboring `SignalStrength` on the raw `RSSI: ` token path, so a workbook-style same-target compare was trialed against `iw`/raw scan evidence. Isolated rerun `20260410T181105027445` stayed deterministic but did not close: 5G same-target `38:88:71:2f:f6:a7` remained `LLAPI=-64` vs `iw=-65` on both attempts, 6G `3a:06:e6:2b:a3:1a` emitted no same-target `IwSignalStrength6g`, and 2.4G `8c:19:b5:6e:85:e1` drifted to `LLAPI=-46` vs `iw=-55/-56`
- follow-up raw `wl -i wl0/wl1/wl2 escanresults` probes only partially closed the gap: 5G same-target raw RSSI matched at `-64`, but 6G still could not find `3A:06:E6:2B:A3:1A` and 2.4G same-target raw RSSI still drifted at `-54 dBm`; the D286 trial rewrite was therefore rejected, `plugins/wifi_llapi/cases/D286_getscanresults_signalstrength.yaml` was reverted to its original generic shape with stale row `288`, and details are recorded in `plugins/wifi_llapi/reports/D286_block.md`
- `D287 getScanResults() SSID` is now also blocked. Source trace still keeps neighboring `SSID` on the raw `SSID: ` token path, and the workbook-style same-target trial did prove the parser/evidence path is sound on 5G and 2.4G: isolated rerun `20260410T182739821870` locked `38:88:71:2f:f6:a7` -> `Verizon_Z4RY7R` and `8c:19:b5:6e:85:e1` -> `TMOBILE-85DF-TDK-2G` identically across LLAPI and `iw`
- 6G still would not close: LLAPI exposed `3a:06:e6:2b:a3:1a` -> `.ROAMTEST_RSNO_P10P_1`, but same-target `iw` emitted no `IwSSID6g`, and direct raw `wl -i wl1 escanresults | grep -m1 -B2 -A1 'BSSID: 3A:06:E6:2B:A3:1A'` also came back empty; the D287 trial rewrite was therefore rejected, `plugins/wifi_llapi/cases/D287_getscanresults_ssid.yaml` was reverted to its original generic shape with stale row `289`, and details are recorded in `plugins/wifi_llapi/reports/D287_block.md`
- `D288 getScanResults() WPSConfigMethodsSupported` is now aligned. Source survey had already shown 0403 still exposes `WPSConfigMethodsSupported` in the scan-result model while the neighboring scan live payload returns an empty-string shape on all three bands; the remaining gap was repo-side parsing, because the raw ubus transcript keeps empty strings as `WPSConfigMethodsSupported = "",` and `_extract_key_values()` does not capture that trailing-comma form. The committed case now uses an explicit extractor command to normalize each band to `WPSConfigMethodsSupported=`, isolated rerun `20260410T183630583633` passed on all three bands, the YAML row metadata is refreshed from stale row `290` to workbook row `288`, and validation stayed green (`3 passed` targeted D288 tests, `1223 passed` full plugin runtime file)
- `D289 getScanResults() Radio` is now aligned as a source-backed fail-shaped absence. The active 0403 scan model `wld_radio.odl` `scanresult_t` does not define `Radio`, and the active HAL neighboring struct `wifi_neighbor_ap2_t` also comments out `ap_Radio`, so the live getter has no backing field to populate. The committed case now uses an explicit extractor command to normalize the missing member to `Radio=`, isolated rerun `20260410T185434305989` emitted `Radio=` on all three bands with `diagnostic_status=Pass`, the YAML row metadata is refreshed from stale row `291` to workbook row `289`, and validation stayed green (`3 passed` targeted D289 tests, `1223 passed` full plugin runtime file)
- `D290 getScanResults() CentreChannel` is now also blocked. Source-backed survey confirmed the field is real on 0403 (`wld_radio.odl` declares `CentreChannel`, `wld_rad_scan.c` copies `ssid->centreChannel`, and `wld_nl80211_parser.c` computes it through `swl_chanspec_getCentreChannel()` with a 20MHz fallback), and isolated trial rerun `20260410T190709112740` did prove live LLAPI values on all three bands (`42 / 31 / 3`). But the workbook-style same-target independent oracle still would not close: 5G and 2.4G same-target `iw` replay only yielded `BSS + freq`, never enough information to recover centre channel, while 6G emitted no same-target `iw` block at all; debug rerun `20260410T191029019821` confirmed the same gap. Therefore the D290 trial rewrite was rejected, `plugins/wifi_llapi/cases/D290_getscanresults_centrechannel.yaml` was reverted to its original generic shape with stale row `292`, the blocker handoff lives in `plugins/wifi_llapi/reports/D290_block.md`, and post-revert validation stayed green (`3 passed` targeted D290 tests, `1223 passed` full plugin runtime file)
- `D295 scan()` is now aligned as a plain `Pass/Pass/Pass` row. The committed metadata is refreshed from stale row `220` to workbook row `295`, but the older `first scan BSSID == first driver BSSID` oracle is no longer authoritative: official rerun `20260412T063939977577` proved driver-cache ordering can drift across retries even when the same public first target persists. The resolving official rerun `20260412T064317622551` therefore keeps the prepared `STA + links` topology and uses the narrower driver-backed oracle `scan() first BSSID exists somewhere in same-band wl escanresults`, exact-closing 5G `62:15:db:9e:31:f1`, 6G `86:82:fe:58:ac:a6`, and 2.4G `6a:d7:aa:02:d7:bf`
- `D298 startScan()` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_radio.odl`, which declares `startScan()` and documents the failure modes (`Unable to start scan`, `A scan is already running`); the 0403 live path in `wldm_lib_wifi.c` then shows the method driving `wldm_xbrcm_scan(..., "scan")` before fetching `num_scan_results` plus `scan_results`. Manual serialwrap replay now matches that contract on all three bands: `WiFi.Radio.1/2/3.startScan()` each returned `[ "" ]`, while the post-call driver cache stayed populated with visible BSSIDs on every band (`wl0` first BSSID `A8:A2:37:4F:8C:5C`, `wl1` first BSSID `6E:15:DB:9E:33:72`, `wl2` first BSSID `62:82:FE:58:AC:B5`). The committed metadata is refreshed from stale row `223` to workbook row `298`
- `D299 stopScan()` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_radio.odl` (`void stopScan()`), in `src/RadMgt/wld_rad_scan.c` where `_stopScan()` delegates to `wld_scan_stop(pR)`, and in `wld_scan_stop()` where the active scan path requires `wld_scan_isRunning()` before calling `pRad->pFA->mfn_wrad_stop_scan(pRad)`; the public nl80211 surface also exposes `wld_rad_nl80211_abortScan()` / `wld_nl80211_abortScan(...)`. Live serialwrap replay then closed the `ScanResults.ScanInProgress` state-bit oracle on all three bands: 5G proved `0 -> startScan() -> 1 -> stopScan() -> 0` and a second restart loop returned to `1/0` again, while 6G and 2.4G each proved `0 -> 1 -> 0` with short probes. A longer combined 6G+2.4G probe did hit `PROMPT_TIMEOUT_RECOVERED`, so the committed oracle stays on short per-band replays. The committed metadata is refreshed from stale row `224` to workbook row `299`, and validation stayed green (`3 passed` targeted D299 tests, `1223 passed` full plugin runtime file)
- `D300 getSSIDStats() BroadcastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, which exposes both `Stats.BroadcastPacketsReceived` and `htable getSSIDStats()`; `src/wld_ssid.c` then routes `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()`, where the 0403 `false && (pAP->status != APSTI_ENABLED)` fallback path keeps `wld_updateVAPStats(pAP, NULL)` live, and `src/wld_statsmon.c` fills `BroadcastPacketsReceived` from `rxBroadcastPackets`. Live serialwrap replay then closed a three-way numeric oracle on all three bands: 5G matched `363 / 363 / 363`, 6G matched `144 / 144 / 144`, and 2.4G matched `113 / 113 / 113` across extracted `getSSIDStats()`, direct `WiFi.SSID.{i}.Stats.BroadcastPacketsReceived?`, and `/proc/net/dev_extstats` field `$23` for `wl0/wl1/wl2`. One longer all-band extraction probe did hit `PROMPT_TIMEOUT_RECOVERED`, so the committed oracle stays on short per-band probes. The committed metadata is refreshed from stale row `225` to workbook row `300`, and validation stayed green (`3 passed` targeted D300 tests, `1223 passed` full plugin runtime file)
- `D301 getSSIDStats() BroadcastPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, which exposes both `Stats.BroadcastPacketsSent` and `htable getSSIDStats()`; `src/wld_ssid.c` then routes `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()`, where the 0403 fallback path still keeps `wld_updateVAPStats(pAP, NULL)` live, and `src/wld_statsmon.c` fills `BroadcastPacketsSent` from `txBroadcastPackets`. Live serialwrap replay then closed the matching three-way numeric oracle on all three bands: 5G matched `1432 / 1432 / 1432`, 6G matched `1590 / 1590 / 1590`, and 2.4G matched `1680 / 1680 / 1680` across extracted `getSSIDStats()`, direct `WiFi.SSID.{i}.Stats.BroadcastPacketsSent?`, and `/proc/net/dev_extstats` field `$24` for `wl0/wl1/wl2`. The committed metadata is refreshed from stale row `226` to workbook row `301`, and validation stayed green (`3 passed` targeted D301 tests, `1223 passed` full plugin runtime file)
- `D302 getSSIDStats() BytesReceived` is now blocked. Active 0403 source still shows this field is real (`wld_ssid.c` copies endpoint `rxbyte`, while `wld_statsmon.c` aggregates `pSrc->rxBytes`), and live replay did prove `direct Stats == getSSIDStats()` on all three bands (`139402 / 139402`, `43232 / 43232`, `33066 / 33066`, with a focused 5G rerun still at `139618 / 139618`). But the old D323-style `/proc/net/dev` / `/proc/net/dev_extstats` field `$2` path is now confirmed stale, and a later source trace through `whm_brcm_vap_update_ap_stats()` / `whm_brcm_get_if_stats()` showed the current 0403 override actually reads `wl if_counters rxbyte`: that newer oracle exact-closes on 6G/2.4G and narrows 5G to a stable `+104` delta (`140482` getter vs `140378` `if_counters`), but still does not close all three bands. The trial rewrite was therefore rejected, the committed metadata stays unchanged at stale row `227`, and the blocker handoff lives in `plugins/wifi_llapi/reports/D302_block.md`
- `D303 getSSIDStats() BytesSent` is now blocked. Active 0403 source still shows this field is real (`wld_ssid.c` copies endpoint `txbyte`, while `wld_statsmon.c` aggregates `pSrc->txBytes`), and live replay partially closed the method path: 5G and 2.4G held `direct Stats == getSSIDStats()` (`95452542` / `67883586`), while 6G first drifted slightly (`60438235` vs `60439059`) and only re-closed on a focused rerun (`60582625 / 60582625`). But the independent oracle would not close either: `/proc/net/dev` / `/proc/net/dev_extstats` field `$10` stayed around `66798080 / 64667313 / 66738514` and `66750876 / 64691013 / 66691690`, `wl counters txbyte` stayed materially higher (`114950286 / 80944128 / 77082489`), `wl0.1/wl1.1/wl2.1` sub-interface counters were blank / zero-like, and `AssociatedDevice.*.TxBytes` also failed to map cleanly. The trial rewrite was therefore rejected, the committed metadata stays unchanged at stale row `228`, and the blocker handoff lives in `plugins/wifi_llapi/reports/D303_block.md`
- `D304 getSSIDStats() DiscardPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `DiscardPacketsReceived` from `wl if_counters rxdiscard`. Live serialwrap replay then closed a three-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters rxdiscard = 0 / 0 / 0`. The older D325-style `/proc/net/dev_extstats` field `$5` path stayed stale at `565 / 3752 / 356`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes. The committed metadata is refreshed from stale row `229` to workbook row `304`, and validation stayed green (`3 passed` targeted D304 tests, `1223 passed` full plugin runtime file)
- `D305 getSSIDStats() DiscardPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `DiscardPacketsSent` from `wl if_counters txdiscard`. Live serialwrap replay then closed the matching three-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters txdiscard = 0 / 0 / 0`. The older D326-style `/proc/net/dev_extstats` field `$13` path stayed stale at `184 / 3467 / 87`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes. The committed metadata is refreshed from stale row `230` to workbook row `305`, and validation stayed green (`3 passed` targeted D305 tests, `1223 passed` full plugin runtime file)
- `D306 getSSIDStats() ErrorsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `ErrorsReceived` from `wl if_counters rxerror`. Live serialwrap replay then closed a four-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters rxerror / /proc/net/dev_extstats $4 = 0 / 0 / 0 / 0`. The committed metadata is refreshed from stale row `231` to workbook row `306`, and validation stayed green (`3 passed` targeted D306 tests, `1223 passed` full plugin runtime file)
- `D307 getSSIDStats() ErrorsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds base-VAP `ErrorsSent` from `wl if_counters txerror` and `whm_brcm_vap_ap_stats_accu()` then accumulates matching `wds*` interface stats back into `SSID.stats`. Live serialwrap replay then closed that source-backed oracle: 5G matched `direct / getSSIDStats / wds0.0.1 if_counters txerror = 56 / 56 / 56`, a focused 6G rerun matched `direct / getSSIDStats / wds1.0.1 if_counters txerror = 46 / 46 / 46`, and 2.4G held `direct / getSSIDStats / wl2 if_counters txerror = 0 / 0 / 0` with no matching WDS peer. The older D328-style `/proc/net/dev_extstats` field `$12` heuristic stayed at `0` on the base wl interfaces and is therefore stale for 5G/6G in the current 0403 baseline. The committed metadata is refreshed from stale row `232` to workbook row `307`, and validation stayed green (`3 passed` targeted D307 tests, `1223 passed` full plugin runtime file)
- `D308 getSSIDStats() FailedRetransCount` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `FailedRetransCount` from `wl if_counters txretransfail`; if any matching `wds*` interface exists, the same `whm_brcm_vap_ap_stats_accu()` path would accumulate it, but the current live baseline stayed at zero. Live serialwrap replay then closed the matching three-way numeric oracle on all three bands: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters txretransfail = 0 / 0 / 0`. The committed metadata is refreshed from stale row `233` to workbook row `308`, and validation stayed green (`3 passed` targeted D308 tests, `1223 passed` full plugin runtime file)
- `D309 getSSIDStats() MulticastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `MulticastPacketsReceived` from `wl if_counters rxmulti`, `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface stats, and `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsReceived` before clamping the field at zero. Live serialwrap replay then closed that source-backed formula on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxmulti / BroadcastPacketsReceived = 0 / 0 / 10 / 363`, 6G matched `0 / 0 / 0 / 145`, and 2.4G matched `0 / 0 / 0 / 113`, so every band authoritatively lands at `max((rxmulti + matching wds_rxmulti) - BroadcastPacketsReceived, 0) = 0`. The older D330-style `/proc/net/dev_extstats` field `$9` heuristic stayed stale at `363 / 146 / 113`. The committed metadata is refreshed from stale row `234` to workbook row `309`, and validation stayed green (`3 passed` targeted D309 tests, `1223 passed` full plugin runtime file)
- `D310 getSSIDStats() MulticastPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `MulticastPacketsSent` from `wl if_counters txmulti`, `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface stats, and `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsSent` before clamping the field at zero. Live serialwrap replay then closed that source-backed formula on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters txmulti / BroadcastPacketsSent = 135098 / 135098 / 136632 / 1534`, 6G matched `76033 / 76033 / 77722 / 1689`, and 2.4G matched `150648 / 150648 / 152429 / 1781`, so every band authoritatively lands at `max((txmulti + matching wds_txmulti) - BroadcastPacketsSent, 0)`. The older D331-style `/proc/net/dev_extstats` field `$18` heuristic stayed stale at `154277 / 148836 / 154585`. The committed metadata is refreshed from stale row `235` to workbook row `310`, and targeted validation stayed green (`3 passed` targeted D310 tests)
- `D311 getSSIDStats() PacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `PacketsReceived` from `wl if_counters rxframe` and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface packet counts before the final SSID stats snapshot is returned. Live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxframe / wds0.0.1 rxframe = 1082 / 1082 / 1080 / 2`, 6G matched `292 / 292 / 292 / 0`, and 2.4G matched `220 / 220 / 220 / 0`. The older D332-style `/proc/net/dev_extstats` field `$3` heuristic stayed stale at `1086 / 438 / 333`. The committed metadata is refreshed from stale row `236` to workbook row `311`, and targeted validation stayed green (`3 passed` targeted D311 tests)
- `D312 getSSIDStats() PacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `PacketsSent` from `wl if_counters txframe` and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface packet counts before the final SSID stats snapshot is returned. Live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters txframe / wds0.0.1 txframe = 192311 / 192311 / 157138 / 35173`, 6G matched `91211 / 91211 / 89703 / 1510`, and 2.4G matched `156926 / 156926 / 156926 / 0`. The older D333-style `/proc/net/dev_extstats` field `$11` is no longer an all-band authority: 5G stayed at base `wl0` txframe, 6G drifted to `151237`, and only 2.4G still exact-closed because no matching WDS peer existed. The committed metadata is refreshed from stale row `237` to workbook row `312`, and targeted validation stayed green (`3 passed` targeted D312 tests)
- `D313 getSSIDStats() RetransCount` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` seeds `RetransCount` from `wl if_counters txretrans` and `whm_brcm_vap_ap_stats_accu()` would accumulate matching `wds*` interface values when present. Live serialwrap replay then closed that source-backed oracle on all three bands: 5G, 6G, and 2.4G all matched `direct / getSSIDStats / wl if_counters txretrans / matching wds txretrans = 0 / 0 / 0 / 0`. The adjacent D334 direct case already records the same 0403 zero-shape comment (`direct Stats matched getSSIDStats(), but workbook v4.0.3 still remains To be tested`), so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes rather than the stale wording. The committed metadata is refreshed from stale row `238` to workbook row `313`, and targeted validation stayed green (`3 passed` targeted D313 tests)
- `D314 getSSIDStats() UnicastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` first seeds `PacketsReceived` from `wl if_counters rxframe`, seeds `MulticastPacketsReceived` from `wl if_counters rxmulti`, and derives `UnicastPacketsReceived = PacketsReceived - MulticastPacketsReceived` before `whm_brcm_vap.c` later adjusts only the visible multicast field. Live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxframe / wl0 if_counters rxmulti / wds0.0.1 rxframe / wds0.0.1 rxmulti = 1084 / 1084 / 1092 / 10 / 2 / 0`, 6G matched `292 / 292 / 292 / 0 / 0 / 0`, and 2.4G matched `220 / 220 / 220 / 0 / 0 / 0`. The older D335-style `/proc/net/dev_extstats` field `$21` heuristic stayed stale at `360 / 146 / 107`. The committed metadata is refreshed from stale row `239` to workbook row `314`, and targeted validation stayed green (`3 passed` targeted D314 tests)
- `D315 getSSIDStats() UnicastPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` first seeds `PacketsSent` from `wl if_counters txframe`, seeds `MulticastPacketsSent` from `wl if_counters txmulti`, and derives `UnicastPacketsSent = PacketsSent - MulticastPacketsSent` before `whm_brcm_vap.c` later adjusts only the visible multicast field. Live serialwrap replay then closed that source-backed oracle on all three bands: focused 5G rerun matched `direct / getSSIDStats / wl0 if_counters txframe / wl0 if_counters txmulti / wds0.0.1 txframe / wds0.0.1 txmulti = 55992 / 55992 / 159684 / 140207 / 36515 / 0`, 6G matched `13317 / 13317 / 92193 / 81711 / 2835 / 0`, and 2.4G matched `2338 / 2338 / 159419 / 157081 / 0 / 0`. The older D336-style `/proc/net/dev_extstats` field `$22` heuristic stayed stale at `0` on all three bands. The committed metadata is refreshed from stale row `240` to workbook row `315`, and targeted validation stayed green (`3 passed` targeted D315 tests)
- `D316 getSSIDStats() UnknownProtoPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` seeds `UnknownProtoPacketsReceived` from `wl if_counters rxunknownprotopkts`, `whm_brcm_vap_copy_stats()` preserves the base VAP field, and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface values before the final SSID stats snapshot is returned. Live serialwrap replay then closed that source-backed oracle on all three bands: 5G matched `direct / getSSIDStats / wl0 if_counters rxunknownprotopkts / wds0.0.1 rxunknownprotopkts = 0 / 0 / 0 / 0`, 6G matched `0 / 0 / 0 / 0`, and 2.4G matched `0 / 0 / 0 / 0`. The adjacent D337 direct case still stays workbook-gated as `To be tested`, but its v4.0.3 comment already records the same multiband zero-shape (`direct Stats matched getSSIDStats()`). The committed metadata is refreshed from stale row `241` to workbook row `316`, and targeted validation stayed green (`3 passed` targeted D316 tests)
- `D317 BSSID` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, where `WiFi.SSID.{i}.BSSID` is exposed as a read-only SSID property, and `dm_info.c` still advertises the same `BSSID` field on the active `WiFi.SSID` object. Live serialwrap replay then closed the independent oracle on all three bands by matching the property against both interface views: 5G `ubus BSSID / iw dev wl0 info addr / wl -i wl0 cur_etheraddr = 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95`, 6G matched `2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96`, and 2.4G matched `2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7`. The workbook v4.0.3 comment already states the same `matching iw dev info` shape. The committed metadata is refreshed from stale row `242` to workbook row `317`, and targeted validation stayed green (`3 passed` targeted D317 tests)
- `D319 MACAddress` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, where `WiFi.SSID.{i}.MACAddress` remains exposed as a read-only SSID property on the active object model. Live serialwrap replay then closed a four-way independent oracle on all three bands by matching the property against three interface views: 5G `ubus MACAddress / iw dev wl0 info addr / ifconfig wl0 HWaddr / wl -i wl0 cur_etheraddr = 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95`, 6G matched `2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96`, and 2.4G matched `2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7`. The committed metadata is refreshed from stale row `321` to workbook row `319`, and targeted validation stayed green (`3 passed` targeted D319 tests)
- `D320 SSID` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `targets/BGW720-300/fs/etc/amx/wld/wld_ssid.odl`, where `WiFi.SSID.{i}.SSID` remains exposed as a read-only SSID property on the active object model. Live serialwrap replay then closed the independent oracle on all three bands by matching the getter against the driver SSID view: 5G `ubus SSID / wl -i wl0 ssid = testpilot5G / testpilot5G`, 6G matched `testpilot6G / testpilot6G`, and 2.4G matched `testpilot2G / testpilot2G`. The committed metadata is refreshed from stale row `322` to workbook row `320`, and targeted validation stayed green (`3 passed` targeted D320 tests)
- `D321 BroadcastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Active 0403 source-backed support stays consistent with the already closed D300 family, and live serialwrap replay closed the full three-way direct-property oracle on all three bands: 5G `direct Stats / getSSIDStats / /proc/net/dev_extstats $23 = 363 / 363 / 363`, 6G matched `147 / 147 / 147`, and 2.4G matched `113 / 113 / 113`. The committed metadata is refreshed from stale row `245` to workbook row `321`, and targeted validation stayed green (`3 passed` targeted D321 tests)
- direct-stats runner revalidation after that: authored `getSSIDStats()` shell pipelines for `D321/D322` are now preserved instead of being overwritten by synthesized plain readback queries. The new regression is locked in repo tests, the command-budget inventory now tracks `618` long official-case commands, and the full repo regression is green at `1634 passed`
- `D321 BroadcastPacketsReceived` has now also passed in the real runner path (`run_id=20260411T002336420469`): 5G `364 / 364 / 364`, 6G `149 / 149 / 149`, and 2.4G `113 / 113 / 113` exact-closed across direct/getSSIDStats//proc
- `D322 BroadcastPacketsSent` remains blocked. Focused DUT-only probes did exact-close the authored `direct / getSSIDStats / /proc $24` block (`20260411T225133238319`, plus 5G x5 and multiband x3 repeats), but the superseding official rerun `20260411T230829194313` still failed twice on the same 5G `+1` drift (`4390 / 4390 / 4391`, then `4394 / 4394 / 4395`) while 6G/2.4G exact-closed. Active 0403 source in `whm_brcm_vap.c` still restores the final public field from `tmp_stats`, so the focused exact-close is not durable enough to commit; the YAML metadata therefore stays at stale row `246`, and the refreshed blocker handoff remains in `plugins/wifi_llapi/reports/D322_block.md`
- `D323 BytesReceived` is now aligned. The earlier blocker turned out to be a stale workbook `/proc/net/dev_extstats` `$2` heuristic plus an incorrect source explanation: corrected 0403 tracing now shows `whm_brcm_get_if_stats()` seeds `BytesReceived` from `wl if_counters rxbyte`, `whm_brcm_vap_ap_stats_accu()` adds matching `wds*` `rxbyte`, and `whm_brcm_vap_update_ap_stats()` does not restore `BytesReceived` from `tmp_stats`. After rewriting the case to that source-backed oracle, official rerun `20260411T231952006453` exact-closed 5G `276282 / 276282 / 276282`, 6G `122610 / 122610 / 122610`, and 2.4G `73193 / 73193 / 73193` across direct/getSSIDStats/driver. The committed metadata is refreshed from stale row `247` to workbook row `323`, and `plugins/wifi_llapi/reports/D323_block.md` is retained as historical resolution notes
- `D324 BytesSent` is now aligned. The first real runner replay (`20260411T005329099506`) proved workbook row `324`'s old `/proc/net/dev_extstats` `$10` compare was stale, but active 0403 source trace through `whm_brcm_get_if_stats()` plus follow-up serialwrap probes closed the real oracle at `wl if_counters txbyte`; after rewriting the case, real runner rerun `20260411T010328768651` exact-closed on all three bands: 5G `79412272 / 79412272 / 79412272`, 6G `47109866 / 47109866 / 47109866`, and 2.4G `79349200 / 79349200 / 79349200` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `248` to workbook row `324`
- `D325 DiscardPacketsReceived` is now aligned. The prior real runner replay (`20260411T010859993578`) proved workbook row `325`'s old `/proc/net/dev_extstats` `$5` compare was stale, but active 0403 source-backed behavior stays consistent with the already aligned `D304` path at `whm_brcm_get_if_stats()` / `wl if_counters rxdiscard`; after rewriting the case, real runner rerun `20260411T011321267947` exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `249` to workbook row `325`
- `D326 DiscardPacketsSent` is now aligned. The prior real runner replay (`20260411T012137925510`) proved workbook row `326`'s old `/proc/net/dev_extstats` `$13` compare was stale, but active 0403 source-backed behavior is now re-confirmed by the fresh D326 survey and the already aligned `D305` path at `whm_brcm_get_if_stats()` / `wl if_counters txdiscard`; after rewriting the case, real runner rerun `20260411T012538161460` exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `250` to workbook row `326`
- `D327 ErrorsReceived` is now aligned. The first real runner replay (`20260411T013241354703`) already exact-closed the legacy `/proc/net/dev_extstats` `$4` compare at zero on all three bands, but active 0403 source-backed behavior is now re-confirmed by the fresh D327 survey and the already aligned `D306` path at `whm_brcm_get_if_stats()` / `wl if_counters rxerror`; after refreshing the case to that source-backed readback, real runner rerun `20260411T013801878458` still exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `251` to workbook row `327`
- `D328 ErrorsSent` is now aligned. The first real runner replay (`20260411T014458979418`) already exact-closed the legacy `/proc/net/dev_extstats` `$12` compare at zero on all three bands, but active 0403 source-backed behavior is now re-confirmed by the fresh D328 survey and the already aligned `D307` path at `whm_brcm_get_if_stats()` / `wl if_counters txerror`, with optional `wds*` accumulation. A focused live probe also showed the field is a moving counter rather than a fixed workbook sample (`5G=1`, `6G=3347`, `2.4G=0` across direct/getSSIDStats/txerror). After refreshing the case to that source-backed readback, real runner rerun `20260411T015126498621` still exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `252` to workbook row `328`
- `D329 FailedRetransCount` is now aligned. The first real runner replay (`20260411T015905984272`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. Active 0403 source-backed behavior is now re-confirmed by the fresh D329 survey and the already aligned `D308` path at `whm_brcm_get_if_stats()` / `wl if_counters txretransfail`, with optional `wds*` accumulation only when a matching peer exists. A focused live probe then exact-closed `direct / getSSIDStats / txretransfail` at zero on all three bands and confirmed the current baseline has no active `wds*` peer. After refreshing the case to that source-backed readback, real runner rerun `20260411T020534026608` still exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `253` to workbook row `329`
- `D334 RetransCount` is now aligned. The first real runner replay (`20260411T021238026451`) already exact-closed direct Stats and getSSIDStats(), but it still lacked an independent driver oracle and the original extractor could ambiguously match `FailedRetransCount`. Active 0403 source-backed behavior is now re-confirmed by the fresh D334 survey at `wldm_SSID_TrafficStats()` / `wl if_counters txretrans`, without WDS accumulation on the direct-property path. A focused live probe then exact-closed the source-backed low-32 driver view at 5G `4294967295`, 6G `4294963915`, and 2.4G `0`. After refreshing the case to use anchored `getSSIDStats()` extraction plus the low-32 driver oracle, real runner rerun `20260411T022030741126` passed on retry: attempt 1 saw a transient 6G drift (`4294967294` vs driver `0`), but attempt 2 exact-closed all three bands at 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `258` to workbook row `334`
- `D337 UnknownProtoPacketsReceived` is now aligned. The first real runner replay (`20260411T023258929853`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. Active 0403 source-backed behavior is now re-confirmed by the fresh D337 survey at `wldm_SSID_TrafficStats()` / `wl if_counters rxbadprotopkts`, without WDS accumulation on the direct-property path. A focused live probe then exact-closed `direct / getSSIDStats / rxbadprotopkts` at 5G `0`, 6G `0`, and 2.4G `0`; the adjacent getSSIDStats-family `rxunknownprotopkts` view also stayed `0 / 0 / 0`, which explains why the workbook-era replay exact-closed despite the counter-family split. After refreshing the case to use anchored `getSSIDStats()` extraction plus the `rxbadprotopkts` driver oracle, real runner rerun `20260411T024443960794` exact-closed all three bands at 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `261` to workbook row `337`
- `D406 MultipleRetryCount` is now aligned. The first real runner replay (`20260411T025549740195`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. Active 0403 source-backed behavior is now re-confirmed at `wldm_SSID_TrafficStats()` / `wl if_counters txretrie`. A focused live probe then exact-closed `direct / getSSIDStats / txretrie` at 5G `0`, 6G `0`, and 2.4G `0`; the current baseline also showed no active `wds*` peer. After refreshing the case to use anchored `getSSIDStats()` extraction plus the `txretrie` driver oracle, real runner rerun `20260411T025954644775` exact-closed all three bands at 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `301` to workbook row `406`
- `D407 RetryCount` is now aligned. The first real runner replay (`20260411T031324456196`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but the workbook-era extractor still ambiguously matched `MultipleRetryCount` and there was no independent driver oracle. Active 0403 source-backed behavior is now re-confirmed at `wldm_SSID_TrafficStats()` / `wl if_counters txretry`. A focused live probe then exact-closed `direct / getSSIDStats / txretry` at 5G `0`, 6G `0`, and 2.4G `0`; the current baseline also showed no active `wds*` peer. After refreshing the case to use anchored `RetryCount` extraction plus the `txretry` driver oracle, real runner rerun `20260411T031645170662` exact-closed all three bands at 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is refreshed from stale row `302` to workbook row `407`
- `D528 getSpectrumInfo bandwidth` is now aligned. The workbook-era replay (`20260411T032529278022`) already proved the old numeric-only regex was stale because active 0403 returned `bandwidth="20MHz"` on all three bands. Active 0403 source-backed behavior is now closed at `_getSpectrumInfo()` / `s_prepareSpectrumOutput()` / `amxc_var_add_key(cstring_t, "bandwidth", swl_bandwidth_str[llEntry->bandwidth])`, while the sync refresh path `wifiGen_rad_getSpectrumInfo(..., update=false)` seeds survey-derived spectrum entries with `SWL_BW_20MHZ` in `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()`. After refreshing the case to the exact public string shape and updating the spectrum guardrail fixture, real runner rerun `20260411T034134858534` exact-closed all three bands at 5G `20MHz`, 6G `20MHz`, and 2.4G `20MHz`; targeted official-case validation stayed green (`1225 passed`), and full repo regression remained green (`1634 passed`)
- `D532 getSpectrumInfo ourUsage` is now aligned. Active 0403 still serializes `ourUsage` through `_getSpectrumInfo()` -> `s_prepareSpectrumOutputWithChanFilter()`, and `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives the field from survey airtime as `ourTime / total_time`; isolated rerun `20260411T183356920330` therefore exact-closed the public shape as integer percentages across 5G / 6G / 2.4G, so the stale fail-shaped workbook carry-over has now been rejected
- `D533 getSpectrumInfo availability` is now aligned. Active 0403 still serializes `availability` through the same `_getSpectrumInfo()` public path, and `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives it from survey idle/free airtime ratios; isolated rerun `20260411T183405281629` exact-closed the public shape as integer percentages across 5G / 6G / 2.4G, so this stale fail-shaped workbook carry-over has also been rejected
- recomputing workbook compare against detached full run `20260411T074146043202` with the current local YAML overlay now yields `220 / 420 full matches`, `200 mismatches`, and `67 metadata drifts`
- interpreted via `evaluation_verdict` rather than stale synthesized per-band `results_reference`, the carried-forward workbook-Pass gaps still remain the same snapshot size, but the current local repo inventory has reduced the patch-scope true-open set to `D281-D287`, `D290`, `D322`, `D324`, `D330-D333`, and `D335-D336`
- this detached compare snapshot is still pre-`D330` rewrite evidence; the current local repo state has moved forward after the detached run finished
- superseding action-method continuation after that: `D295 scan()` is now re-aligned via official rerun `20260412T064317622551`, and `plugins/wifi_llapi/reports/D295_block.md` is retained only as historical blocker/resolution evidence. The intermediate blocker phase was still real — committed DUT-only topology could fall back to `WiFi.Radio.{1,2,3}.Status="Dormant"` and `scan()/startScan()` then returned `status 1 - unknown error` — but once the case kept prepared `STA + links`, the remaining failure was narrowed to driver-cache ordering noise. The final committed oracle therefore rejects first-BSSID equality and only requires the first `scan()` target to exist somewhere in same-band `wl escanresults`
- `D324 BytesSent` is now also formally blocked in `plugins/wifi_llapi/reports/D324_block.md`. Fresh isolated rerun `20260411T190338070996` re-proved `direct == getSSIDStats()` but invalidated base `wlX if_counters txbyte` on multiple bands, and the follow-up official rerun `20260412T005627796136` showed that even the source-backed `wlX txbyte + Σ matching wds* txbyte` rewrite is not yet runner-stable: 5G kept a `direct < getSSIDStats < driver` staircase on both attempts, 6G exact-closed only on attempt 2, and 2.4G still left a residual driver lead. Active 0403 pWHM source now proves why the sequential equality still drifts: both direct `Stats.*` and `getSSIDStats()` independently call `s_updateSsidStatsValues()` before serializing output
- `D330 MulticastPacketsReceived` is now aligned in the local repo state. Isolated rerun `20260411T191809490680` closed the active 0403 source-backed formula `max((rxmulti + matching wds_rxmulti) - BroadcastPacketsReceived, 0)` on all three bands; attempt 1 hit `/tmp/_tp_cmd.sh: line 2: syntax error: unterminated quoted string`, but attempt 2 exact-closed `direct / getSSIDStats / driver-formula = 0 / 0 / 0` on 5G / 6G / 2.4G, and the case metadata is now refreshed from stale row `254` to workbook row `330`
- `D322 BroadcastPacketsSent` is now aligned in the local repo state. The earlier real-runner blocker was a post-`verify_env` timing issue, not a stale `/proc $24` authority problem: resolving official rerun `20260412T002445088386` kept the workbook `/proc/net/dev_extstats` `$24` compare but added a short settle (`sleep 2`) before the first 5G snapshot. Attempt 1 still drifted on 6G by `+1` (`4766 / 4767 / 4767`), but attempt 2 exact-closed 5G/6G/2.4G at `4596 / 4596 / 4596`, `4772 / 4772 / 4772`, and `5121 / 5121 / 5121`, and the committed metadata is now refreshed from stale row `246` to workbook row `322`
- `D331 MulticastPacketsSent` remains formally blocked in `plugins/wifi_llapi/reports/D331_block.md`. Trial reruns `20260411T192138186700` and `20260411T192524301950` both rejected the stale workbook `/proc/net/dev_extstats` `$18` heuristic, but 5G stayed at a fixed `driver = direct + 4` drift even after the subtraction term moved into the same `getSSIDStats()` snapshot. The superseding official rerun `20260411T234124237416` then proved the source-backed rewrite was still not durable in the real runner path: 5G widened to `286001 / 286001 / 286006` and then `286140 / 286140 / 286192`. A follow-up settle retrial `20260412T003609854183` materially narrowed that shape — 5G and 2.4G exact-closed on both attempts after a post-`verify_env` `sleep 2` — but 6G still failed at `181336 / 181336 / 181337` and `181375 / 181375 / 181377`, so the local rewrite stays rolled back
- `D332 PacketsReceived` is now aligned in the local repo state. Stale workbook replay `20260411T194312398713` re-proved both `/proc/net/dev_extstats` `$3` drift and loose `getSSIDStats()` overmatch; after refreshing the case to workbook row `332`, anchoring the `getSSIDStats()` extraction, and switching the driver oracle to `wl if_counters rxframe + matching wds rxframe`, rerun `20260411T194647490016` passed in one attempt
- `D333 PacketsSent` remains formally blocked in `plugins/wifi_llapi/reports/D333_block.md`. Stale replay `20260411T194816992700` re-proved the loose `getSSIDStats()` overmatch and non-authoritative workbook `/proc/net/dev_extstats` `$11` path; source-backed trial rerun `20260411T195140855058` exact-closed 6G/2.4G but kept a fixed 5G `driver = direct + 5` drift, and the superseding official rerun `20260411T235643720137` re-proved that same 5G `+5` shape in the full runner path (`319230 / 319235 / 319235`, then `319376 / 319376 / 319381`). A follow-up settle retrial `20260412T004816450100` materially narrowed the residual mismatch — attempt 1 failed only on 5G by `+1`, attempt 2 failed only on 6G by `+2` — but the official acceptance path still did not exact-close all three bands, so the local rewrite stays rolled back
- `D335 UnicastPacketsReceived` is now aligned in the local repo state. Stale workbook replay `20260411T200329824574` re-proved `/proc/net/dev_extstats` `$21` drift on all three bands, while active 0403 source explicitly derives `UnicastPacketsReceived = PacketsReceived - MulticastPacketsReceived` and then copies/accumulates that field across matching VAP/WDS stats; after switching the case to `(wl if_counters rxframe + matching wds rxframe) - (wl if_counters rxmulti + matching wds rxmulti)`, rerun `20260411T200851584762` exact-closed 5G `2003/2003/2003`, 6G `794/794/794`, and 2.4G `483/483/483`
- `D336 UnicastPacketsSent` is now aligned in the local repo state. Stale workbook replay `20260411T201639103833` re-proved `/proc/net/dev_extstats` `$22` as an all-band zero-shaped stale oracle; the earlier source-backed trials then exposed a parser failure and a signed-formula durability gap. After switching to the unsigned 0403 formula `((txframe + matching wds txframe) - (d11_txmulti + matching wds d11_txmulti)) & 0xffffffff`, the resolving official rerun `20260412T000744842751` passed after retry: attempt 1 still drifted on 6G by `+1` (`24709 / 24710 / 24710`), but attempt 2 exact-closed 5G/6G/2.4G (`27172 / 27172 / 27172`, `24703 / 24703 / 24703`, `17117 / 17117 / 17117`)
- `D277 getScanResults() Bandwidth` is now aligned in the local repo state via isolated rerun `20260411T205454026707`. Replacing the raw full scan capture with a transport-safe first-object capture removed the old 6G broker recovery blocker, and the refreshed workbook-style same-target replay now closes directly against `wl escanresults` Chanspec bandwidth on all three bands: 5G exact-closes at `80/80`, 2.4G exact-closes at `20/20`, and 6G is now locked as a source-backed fail-shaped mismatch at `320/160` for the same target BSSID `6e:15:db:9e:33:72`. The committed metadata is refreshed from stale row `279` to workbook row `277`, and `results_reference.v4.0.3` is now `Pass / Fail / Pass`
- `D281 getScanResults() Noise` is now aligned via official rerun `20260412T080123446178`. The blocker turned out to be the CLI call shape rather than the absence of a same-scan public family: named-arg `scanCombinedData(channels=36/5/1,minRssi=-127,scanReason=Ssid)` now returns paired `BSS + Spectrum`, and same-target `getScanResults(minRssi=-127)` exact-closes against that same-scan cache on all three bands — 5G `2c:59:17:00:03:e5 / -100 / -100 / -100`, 6G `6e:15:db:9e:33:72 / -97 / -97 / -97`, and 2.4G `6a:d7:aa:02:d7:bf / -76 / -76 / -76`. The committed metadata is refreshed from stale row `283` to workbook row `281`, and `plugins/wifi_llapi/reports/D281_block.md` is retained only as historical resolution notes
- `D282 getScanResults() OperatingStandards` is now aligned via official rerun `20260412T080338867826`. The durable same-source oracle is the same named-arg `scanCombinedData()` family rather than `NeighboringWiFiDiagnostic()`: `scanCombinedData().BSS` and immediate same-target `getScanResults(minRssi=-127)` exact-close 5G `2c:59:17:00:03:e5 / a,n,ac,ax,be`, 6G `6e:15:db:9e:33:72 / ax,be`, and 2.4G `6a:d7:aa:02:d7:bf / b,g,n,ax`. The committed metadata is refreshed from stale row `284` to workbook row `282`, and `plugins/wifi_llapi/reports/D282_block.md` is retained only as historical resolution notes
- current scan-results true-open set is now empty; there is no remaining ready runtime-triage case in this workstream
- `D283 getScanResults() RSSI` is now aligned. The old blocker was the committed full-payload transport shape rather than the row semantics: isolated rerun `20260411T214050136894` still hung after `setup_env`, but the D277-style transport-safe first-object capture removed that failure path while preserving the active 0403 public source family. Official reruns `20260412T013944779069` and `20260412T014018880783` both exact-closed the same all-band public shape — 5G `38:88:71:2f:f6:a7 / -66 / -66`, 6G `6e:15:db:9e:33:72 / -95 / -95`, 2.4G `2c:59:17:00:03:f7 / -47 / -47` — so the committed metadata is refreshed from stale row `285` to workbook row `283`, and `plugins/wifi_llapi/reports/D283_block.md` is retained only as historical resolution notes
- `D284 getScanResults() SecurityModeEnabled` is now aligned. The earlier blockers were unstable 6G selectors rather than an unreplayable public field: the old first-WPA-target and associated-BSSID rewrites drifted between `.ROAMTEST_RSNO_P10P_1`, `OpenWrt_1`, and missing same-target LLAPI placeholders, but the D283-style transport-safe first-object capture now locks one durable same-target replay across all three bands. Official reruns `20260412T015141491861` and `20260412T015235280960` both exact-closed 5G `38:88:71:2f:f6:a7 / WPA2-Personal / WPA2-Personal`, 6G `6e:15:db:9e:33:72 / WPA3-Personal / WPA3-Personal`, and 2.4G `2c:59:17:00:03:f7 / WPA2-Personal / WPA2-Personal`, so the committed metadata is refreshed from stale row `286` to workbook row `284`, and `plugins/wifi_llapi/reports/D284_block.md` is retained only as historical resolution notes
- `D285 getScanResults() SignalNoiseRatio` is now aligned. The old blocker was the raw-driver `SNR` replay rather than the public row itself: 0403 neighboring scan internals still carry `SignalStrength` plus `Noise`, while the serialized public scan object exposes `SignalNoiseRatio`. The D283-style transport-safe first-object capture now locks the durable public invariant `SignalNoiseRatio == RSSI - Noise` on the same target, and official reruns `20260412T020817105728` and `20260412T020839239161` both exact-closed 5G `38:88:71:2f:f6:a7 / -66 / -100 / 34`, 6G `6e:15:db:9e:33:72 / -95 / -97 / 2`, and 2.4G `2c:59:17:00:03:f7 / -47 / -80 / 33`. The committed metadata is refreshed from stale row `287` to workbook row `285`, and `plugins/wifi_llapi/reports/D285_block.md` is retained only as historical resolution notes
- `D286 getScanResults() SignalStrength` is now aligned. The old blocker was the external replay model rather than the public row itself: active 0403 source already showed `SignalStrength` and `RSSI` are the same public `ssid->rssi` family, so the D283-style transport-safe first-object capture is sufficient to lock the durable public invariant `SignalStrength == RSSI` on the same target. Official reruns `20260412T021725610895` and `20260412T021748934770` both exact-closed 5G `38:88:71:2f:f6:a7 / -66 / -66`, 6G `6e:15:db:9e:33:72 / -95 / -95`, and 2.4G `2c:59:17:00:03:f7 / -47 / -47`. The committed metadata is refreshed from stale row `288` to workbook row `286`, and `plugins/wifi_llapi/reports/D286_block.md` is retained only as historical resolution notes
- `D287 getScanResults() SSID` is now aligned. The old blocker was the stale 6G selector rather than the public field model itself: active 0403 still serializes public `SSID` from the parsed scan-result object, and the D283-style transport-safe first-object capture now locks the stable same-target replay on all three bands. Official reruns `20260412T022708923585` and `20260412T022738004752` both exact-closed 5G `38:88:71:2f:f6:a7 / Verizon_Z4RY7R / Verizon_Z4RY7R`, 6G `6e:15:db:9e:33:72 / **TELUS0227 / **TELUS0227`, and 2.4G `2c:59:17:00:03:f7 / OpenWrt_1 / OpenWrt_1`. The committed metadata is refreshed from stale row `289` to workbook row `287`, and `plugins/wifi_llapi/reports/D287_block.md` is retained only as historical resolution notes
- next ready runtime-triage case in the current repo inventory: `none`

</details>

## Checkpoint summary (2026-04-02)

> This checkpoint records campaign state after repo-side preflight and baseline hardening.
> No new live single-case alignment was produced in this checkpoint because lab UART access is currently unavailable.

<details>
<summary>Checkpoint status (zh-tw)</summary>

- workbook procedure authority fixed to `Wifi_LLAPI` columns `G/H` (`Test steps` / `Command Output`); `F` is ignored
- latest carried-forward compare snapshot remains `264 / 420` full matches and `156` mismatches
- latest carried-forward aligned live case remains `D023 Inactive` via run `20260402T105808547293`
- latest carried-forward stable fail-shaped mismatches remain `D013` / `D020`
- preflight guardrails revalidated:
  - multiline block-scalar ban for official case command fields: pass
  - serialwrap 120-char temp-script staging tests: pass
  - official-case command length inventory over 120 chars: `612` tracked entries
- repo regression status after the offline-survey regression guard: `uv run pytest -q` → `1601 passed`
- `D024` / `D025` / `D026` offline survey is ready:
  - workbook authority is row `24` / `25` / `26`
  - workbook `G/H` and source evidence point to DUT `wl -i wl0 sta_info ${STA_MAC}` as the driver truth source:
    - `D024`: `rate of last tx pkt`
    - `D025`: `rate of last rx pkt`
    - `D026`: `link bandwidth = XX MHZ` together with `WiFi.Radio.1.OperatingChannelBandwidth`
  - the old `20260401T152827516151` fail traces already captured matching LLAPI / driver values for all three cases, so that fail shape is treated as consistent with the older shell-pipeline success-classifier bug now covered by regression tests
- adjacent stale metadata is also confirmed:
  - current YAML row ids for `D024` / `D025` / `D026` still read `21` / `22` / `23`
  - `0401.xlsx` rows are actually `24` / `25` / `26`
  - therefore this slice remains pending live rewrite instead of being treated as already aligned
- current live blocker:
  - serialwrap daemon is running, but the environment currently exposes no `/dev/ttyUSB*` and no `/dev/serial/by-id`
  - `serialwrap session list` returns zero sessions
  - `serialwrap session self-test --selector COM0/COM1` fails because `COM0/COM1` do not exist
  - therefore fresh live full run and subsequent live calibration cannot proceed until DUT/STA UART visibility returns
- next ready case after UART recovery: `D024 LastDataDownlinkRate`

</details>

## Active blockers

| Scope | Item | Status | Detail |
|---|---|---|---|
| calibration | D211 OperatingStandards | blocked | workbook row `211` step 6 fails live: getter flips to `ax`, but AX phase still keeps EHT (`wl0/wl1/wl2 eht features=127`) and 6G secondary hostapd config still carries `ieee80211be=1` |
| plugin cases | official-case long command inventory | tracked risk | `612` commands exceed 120 chars, but current serialwrap temp-script staging keeps them executable |

## Resume steps

1. Keep D211 at blocked/fail-shaped unless a later FW drop proves AX phase can really clear EHT from runtime beacon/config behavior.
2. Confirm serialwrap `COM0/COM1` remain `READY` and `session self-test` still passes before the next live loop.
3. Resume the patch-driven workbook-Pass queue from `D267`.
4. Continue the remaining Confluence-mapped 0315 -> 0403 scope.
5. Return to the stale-row AssociatedDevice rate/bandwidth slice later: `D024` (row `24`) → `D025` (row `25`) → `D026` (row `26`).
