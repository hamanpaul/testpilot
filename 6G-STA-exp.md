# 6G STA debug 經驗紀錄

> 目的：把這幾次 debug 6G STA 的**試錯過程、當時的判斷、被推翻的假設、實際指令、關鍵輸出、目前推論與下一步方向**完整記下來。  
> 這份檔案不是只寫「最後結論」，而是刻意保留「繞過的彎路」，避免下次從頭再踩一次。

## 1. 角色與環境對照

- **DUT**：COM0
- **STA**：COM1
- **DUT 6G AP**：`WiFi.AccessPoint.3` / `WiFi.SSID.6` / `wl1`
- **DUT 6G secondary BSS / VIF**：`WiFi.AccessPoint.4` / `WiFi.SSID.7` / `wl1.1`
- **STA 6G client iface**：`wl1`
- **主要操作通道**：serialwrap
- **主要控制面**：`ubus-cli` / TR-181 / `wld`
- **主要 runtime 檔案**：
  - DUT：`/tmp/wl1_hapd.conf`
  - STA：`/tmp/wpa_wl1.conf` 或 `/tmp/wpa_wl1_6g.conf`

## 2. 最值得先記住的結論

1. **6GHz 不能當成 5G 的延伸來想。**  
   `WPA2-Personal` setter 可能回 OK，但 runtime 仍會回到 `WPA3/SAE`。不要浪費時間反覆測「6G 先改 WPA2 看看」這條路。

2. **`status_code=49` 幾乎不是單純密碼錯。**  
   這一輪多次證據都指向：STA 有掃到 AP，也真的送出 connect request，但 DUT 端直接 reject。重點要查的是 **DUT 端 EHT/MLO/secondary BSS/runtime config**，不是只盯著 `sae_password`。

3. **`AP4.Enable=0` 不等於 `wl1.1` 消失。**  
   getter 可以顯示 AP4 disabled，但 `wl1.1 / OpenWrt_2` 仍可能留在 live hostapd/runtime 裡，這件事反覆出現過很多次。

4. **`OperatingStandards=ax` 只修 primary，不保證 secondary 也一起變乾淨。**  
   我們多次看到 primary stanza 已變 `ieee80211be=0`，但 secondary stanza 還是 `ieee80211be=1`。

5. **`ocv=0` 是已驗證有效的 live fix，但不是完整 supported solution。**  
   它能解掉 `mfp_ocv` 造成的 11 秒 BSS loop；但只要 `wld` 重生 `wl1_hapd.conf`，這個 fix 就會被覆蓋。

6. **不要在 AP 已起來後再手動 `wl -i wl1 chanspec 6g1/80`。**  
   之前已經證實這會把 DUT `wl1` 的 BSS 打成 `down`，hostapd 還可能繼續回 `state=ENABLED`，造成非常誤導的假象。

7. **新版 DUT firmware 的行為跟之前 live-good 狀態不同。**  
   這一輪（DUT 更新 FW、STA 沒更新）最大的差異是：  
   - `wl1_hapd.conf` 會重新長出 secondary stanza  
   - `sae_pwe=1` / `ieee80211be=1` 會被重新帶回來  
   - 有時 `hostapd` process 在，但 `hostapd_cli` 接不上 control socket  
   - 直接 patch `/tmp/wl1_hapd.conf` 的效果不像之前那麼可控

## 3. 常見失敗特徵速查

### 3.1 STA 端

- `wpa_state=SCANNING`
- `wpa_state=DISCONNECTED`
- `CTRL-EVENT-ASSOC-REJECT status_code=49`
- `CTRL-EVENT-ASSOC-REJECT status_code=1`
- `BSS is ml_capable:1`
- `iw dev wl1 link` → `Not connected.`

### 3.2 DUT 端

- `wl_host_event: WLC_E_BSSCFG_UP for idx[0] ifname[wl1] mld_unit[255]`
- `wl1: dhd_prot_ioctl: status ret value is -23 iov=mfp_ocv`
- `CFG80211-ERROR) wl_validate_set_ocv_cap : ocv_cap unsupported -23`
- `hostapd_cli -i wl1 status` 接不上
- `/tmp/wl1_hapd.conf` 重新長出：
  - `bss=wl1.1`
  - `ssid=OpenWrt_2`
  - `ieee80211be=1`
  - `sae_pwe=1`

## 4. 時間序整理：這幾輪到底試了什麼

---

## 4.1 最早期：先排除 5G/2.4G baseline 問題

最一開始不是直接碰 6G，而是先確認 serialwrap、DUT baseline、STA baseline、Group 2/Group 3 驗證都正常。

### 做過的事

```bash
ubus-cli "WiFi.SSID.4.SSID?"
iw dev wl0 link
ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.?"
wl -i wl0 assoclist
```

### 當時得到的結論

- 5G / 2.4G baseline 沒問題
- serialwrap 本身不是 blocker
- 問題集中在 **6G path**

### 這一步的價值

這一步很重要，因為它先把「transport 壞了」「整個 DUT/STA 都亂掉」這些大方向排掉，後面才能專心盯 6G。

---

## 4.2 第一個大坑：STA 自己其實是 AP mode，不是真的 client

使用者把兩台 factory default 後，我們一開始以為只要手動 `iw dev wl1 set type managed` 就能開始當 STA。  
後來證明這想法太天真：**STA 端的 `wld + hostapd` 會把 `wl1` 拉回 AP**。

### 代表性指令

```bash
iw dev
ps | grep -E 'hostapd|wpa_supplicant' | grep -v grep
ubus-cli "WiFi.AccessPoint.3.Enable?"
```

### 關鍵觀察

- factory default 後 STA 端 `wl0/wl1/wl2` 都是 `type AP`
- STA 端有：
  - `wld -D`
  - `hostapd -ddt /tmp/wl1_hapd.conf`
- `WiFi.AccessPoint.3.Enable=1` 指的是 **STA 自己的 6G AP**

### 當時的推論

- 只做：

```bash
iw dev wl1 set type managed
```

  不會持久
- 真正要讓 `wl1` 長期當 STA，需要至少做到下面其中一種：
  1. 讓 STA 自己的 `AP3` 在 control-plane 上關掉
  2. 讓 `wld` 不再把 `wl1` 視為 AP
  3. 找到正確 TR-181 setter，而不是只碰 `iw`

### 這一步避免的坑

- 不要再把「切 managed mode」當作終點
- 沒先處理 STA 自己的 AP role，就算 `wpa_supplicant` 起來也會很快被蓋回去

---

## 4.3 第二個大坑：以為 6G 可以先退回 WPA2 試試看

這條路浪費過時間，後來證實沒必要再重做。

### 試過的指令

```bash
ubus-cli WiFi.AccessPoint.3.Security.ModeEnabled=WPA2-Personal
ubus-cli "WiFi.AccessPoint.3.Security.ModeEnabled?"
grep -nE 'wpa|sae' /tmp/wl1_hapd.conf
```

### 關鍵現象

- setter 回 OK
- 但 getter 讀回還是 `WPA3-Personal`
- `wl1_hapd.conf` 仍是 `wpa_key_mgmt=SAE`

### 結論

- DUT 6G stack 會**強制收斂回 WPA3/SAE**
- 這符合 6GHz/Wi-Fi 6E 現實限制
- **之後不要再把「先降 WPA2」當主要排錯方向**

---

## 4.4 第一輪 status=49：STA 掃得到、connect 也送得出去，但 DUT 直接拒絕

這時開始進入真正的 6G compatibility 排錯。

### 代表性指令與輸出

```bash
wpa_cli -i wl1 status
iw dev wl1 link
tail -n 120 /tmp/wpa_wl1.log
wl -i wl1 assoclist
```

STA 端看到的關鍵訊息：

```text
nl80211: Connect request send successfully
CTRL-EVENT-ASSOC-REJECT status_code=49
```

DUT 端看到的關鍵訊息：

```text
WiFi.AccessPoint.3.Enable=1
WiFi.AccessPoint.3.Security.ModeEnabled="WPA3-Personal"
WiFi.AccessPoint.3.Security.MFPConfig="Required"
WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"
```

### 當時的判斷

- 這不是單純 SSID/密碼/PMF 不匹配
- 因為：
  - SSID 對
  - WPA3 對
  - SAEPassphrase 對
  - PMF 對
- 所以開始懷疑：
  - **11be / EHT / MLO**
  - secondary BSS 干擾
  - 6GHz profile 不相容

---

## 4.5 試錯矩陣：MultiAPType / OperatingStandards / 舊 key / SAE 參數

這段是最容易繞遠路的一段，所以一定要記。

### 嘗試 A：`MultiAPType=None`

```bash
ubus-cli WiFi.AccessPoint.3.MultiAPType=None
```

觀察：

- `multi_ap=2` → `multi_ap=0`
- 但**仍然不能連**

當時學到的事：

- `FronthaulBSS` 可能是問題之一，但**不是唯一根因**

### 嘗試 B：`OperatingStandards=ax`

```bash
ubus-cli WiFi.Radio.2.OperatingStandards=ax
grep -nE '^(ieee80211be|bss=|ssid=)' /tmp/wl1_hapd.conf
```

觀察：

```text
Line 8: ieee80211be=0
Line 53: ieee80211be=1
bss=wl1.1
ssid=OpenWrt_2
```

也就是說：

- primary stanza 變成 `ieee80211be=0`
- 但 secondary stanza 還是 `ieee80211be=1`

這個觀察超重要，因為它說明：

- **`OperatingStandards=ax` 只能修 primary，不會自動把 secondary 清乾淨**

### 嘗試 C：直接 sed 掉 `ieee80211be=1` 與 secondary stanza

```bash
sed -i "s/ieee80211be=1/ieee80211be=0/g" /tmp/wl1_hapd.conf
sed -i "/^bss=wl1\.1$/,\$d" /tmp/wl1_hapd.conf
hostapd_cli -i wl1 reload
```

觀察：

- `wl1.1` 確實可被刪掉
- `hostapd_cli reload` 也成功
- **但仍然沒有直接換來穩定連線**

這一步的教訓：

- Secondary BSS 確實是問題的一部分
- 但只修它，還不夠

### 嘗試 D：`sae_pwe=1` / `2` / `0`

我們後來逐漸收斂到一件事：

- DUT 預設 `sae_pwe=1`（H2E only）
- Broadcom STA dhd 對 H2E 路徑不可靠

因此試過：

```bash
# DUT
sed -i "s/^sae_pwe=.*/sae_pwe=2/" /tmp/wl1_hapd.conf

# STA
sed -i "s/^sae_pwe=.*/sae_pwe=0/" /tmp/wpa_wl1_6g.conf
```

### 重要教訓

- `status_code=49 -> status_code=1` 是**有進步**
- 但不代表問題解完
- 不要看到 `49` 變 `1` 就太早宣布成功

---

## 4.6 真正 live 成功的那次：不是 EHT 本身，而是 `mfp_ocv` + BSS down

這是目前最關鍵的一次成功經驗。

### 先發現的症狀

雖然 hostapd 顯示 `state=ENABLED`，但 DUT `wl1` 其實是 down。

代表性觀察：

```bash
wl -i wl1 bss
wl -i wl1 status
```

看到：

```text
wl -i wl1 bss = down
hostapd_cli status = ENABLED
```

### 原因 1：`wl chanspec` 會把 BSS 打下來

之前為了「強制確認頻道」，跑過：

```bash
wl -i wl1 chanspec 6g1/80
```

後來證明這是壞招：

- 它會把 firmware 的 BSS 弄成 `down`
- hostapd 還可能繼續顯示 `ENABLED`
- 之後 STA 會掃不到或連不起來

### 修復 1：把 BSS 拉回來

```bash
wl -i wl1 bss up
```

之後確認 TBTT / beacon 有在動，這是那一輪真正恢復 AP 發送的轉捩點。

### 原因 2：`mfp_ocv` 不支援，造成 11 秒 BSS loop

關鍵 dmesg：

```text
wl1: dhd_prot_ioctl: status ret value is -23 iov=mfp_ocv
CFG80211-ERROR) wl_validate_set_ocv_cap : ocv_cap unsupported -23
WLC_E_BSSCFG_UP for idx[0] ifname[wl1] mld_unit[255]
```

這時真正的 live-good fix 是：

```bash
sed -i '/^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf
kill $(pgrep -f wl1_hapd 2>/dev/null) 2>/dev/null; true
hostapd -ddt -B /tmp/wl1_hapd.conf
```

### 成功時 STA 的關鍵設定

```text
sae_password="00000000"
sae_pwe=2
ieee80211w=2
scan_ssid=1
```

### 成功證據

STA：

```text
wpa_state=COMPLETED
Connected to 2c:59:17:00:19:96
SSID: testpilot6G
freq: 5955
```

DUT：

```text
wl -i wl1 assoclist
2C:59:17:00:04:86 [AUTH][ASSOC][AUTHORIZED][WMM][MFP]
```

### 這輪最重要的 lesson

- **不要把 `mld_unit=255` 當根因本身**
- 真正已驗證的 live root cause 是：
  - `mfp_ocv` 不支援
  - 外加某次手動 `wl chanspec` 把 BSS 打 down

---

## 4.7 為什麼後來一定要改 `testpilot` 程式碼

原因很單純：live 手動改 `/tmp/wl1_hapd.conf` 沒辦法持久。

### 問題

只要有任何會讓 DUT 6G AP 重新起來的動作，例如：

```bash
ubus-cli WiFi.AccessPoint.3.Enable=1
/etc/init.d/wld_gen start
```

`wld` 都會把 `/tmp/wl1_hapd.conf` 重生，然後把 `ocv=0` 蓋掉。

### 所以後來做的 repo fix

在 `plugins/wifi_llapi/plugin.py` 新增 `_apply_6g_ocv_fix()`，並掛到：

- `_run_sta_band_baseline`
- `_reload_dut_wifi_stack`
- `_bounce_dut_band`

### 設計原則

- 用 polling 等 `wl1_hapd.conf` 生好
- 強制 replace-or-insert `ocv=0`
- 再重啟 wl1 hostapd

### 驗證結果

```text
uv run pytest -q plugins/wifi_llapi/tests/  -> 1257 passed
uv run pytest -q                             -> 1603 passed
commit: 099db14
```

這表示：

- repo 端對「已知 `mfp_ocv` loop」這件事已經有持久修正
- 但**不等於新版 DUT firmware 現在的所有 6G 問題都消失**

---

## 4.8 ubus-only 路線：為什麼最後判定「supported path 不夠」

這一段很關鍵，因為它界定了什麼是「已證明行不通的方向」。

### 試過的 supported path

#### `DiscoveryMethodEnabled=RNR`

```bash
ubus-cli "WiFi.AccessPoint.3.DiscoveryMethodEnabled=RNR"
```

觀察：

- getter 的確變成 `RNR`
- `wl1_hapd.conf` 的確出現 `rnr=1`
- 但同時：
  - `ocv=0` 消失
  - link 掉
  - `wl1.1 / OpenWrt_2` 又回來

#### 檢查 Security 節點

```bash
ubus-cli "WiFi.AccessPoint.3.Security.?"
```

看到的只有：

- `ModeEnabled`
- `MFPConfig`
- `SAEPassphrase`
- `KeyPassPhrase`

**沒有任何 OCV setter**

### 這段最後的結論

1. `ubus-cli` / TR-181 的 supported path **沒有 OCV knob**
2. `AP4.Enable=0` / `SSID7.Enable=0` 的 getter 乾淨，不代表 runtime 真的乾淨
3. 所以「完全不用 live patch、只靠 ubus setter 就恢復 6G」這條路，在當時的 contaminated DUT 上是 **有界 blocker**

---

## 4.9 factory reset 階段：為什麼需要重置 DUT

當時要回答的問題是：

> 現在看到的各種怪象，到底是之前手動 patch 殘留造成的，還是 backend 本來就會這樣？

所以做了 factory reset。

### 指令

```bash
firstboot -y
sync
sync
sync
reboot -f
```

### 後果與恢復過程

- COM0 一度變成：
  - `TARGET_UNRESPONSIVE`
  - `ATTACHED_NOT_READY / PROMPT_TIMEOUT`
- 後來透過 serialwrap recovery 拉回 `READY`

### 這段的教訓

- reboot/factory default 後，不要急著判斷功能好壞
- 先確認 serialwrap session 真正 READY，再開始讀狀態

---

## 4.10 這一輪（DUT 已更新 FW、STA 沒更新）：新的試錯與新現象

這一輪跟之前最大的不同，是 **DUT firmware 換了，但 STA 沒換**。

### 4.10.1 一開始先做的事

先確認 serialwrap 和 COM0/COM1。

結果：

- COM1 一開始 `TARGET_UNRESPONSIVE`，recover 後正常
- COM0 有 human interactive session，但 recover 後 line command 可用

### 4.10.2 先抓新 DUT / 新 STA 的真實起始狀態

代表性指令：

```bash
ubus-cli "WiFi.SSID.6.SSID?"
ubus-cli "WiFi.AccessPoint.3.Security.ModeEnabled?"
ubus-cli "WiFi.AccessPoint.3.Security.MFPConfig?"
wl -i wl1 bss
grep -nE '^(interface=|bss=|ssid=|multi_ap=|ieee80211be=|sae_pwe=|ieee80211w=|ocv=)' /tmp/wl1_hapd.conf
iw dev
ps | grep -E 'hostapd|wpa_supplicant'
```

### 當下看到的關鍵差異

DUT：

```text
WiFi.SSID.6.SSID="OpenWrt_1"
WiFi.AccessPoint.3.Security.ModeEnabled="WPA3-Personal"
WiFi.AccessPoint.3.Security.MFPConfig="Disabled"
```

`/tmp/wl1_hapd.conf`：

```text
8:ieee80211be=0
16:ssid=OpenWrt_1
34:ieee80211w=2
35:sae_pwe=1
50:multi_ap=3
52:ieee80211be=1
55:bss=wl1.1
60:ssid=OpenWrt_2
```

STA：

```text
wl1  type AP
wl1.1 type AP
沒有 wpa_supplicant
```

### 這一步的結論

- 新 DUT firmware 的 6G 預設形狀又回到：
  - primary + secondary 雙 stanza
  - `sae_pwe=1`
  - `ieee80211be=1` 殘留
- STA 端則回到 AP role，需要重新拉成 client

---

## 4.11 這一輪先做的 baseline rebuild：把 DUT/STA 拉回「理論上能連」的形狀

### DUT side

```bash
ubus-cli WiFi.AccessPoint.4.Enable=0
ubus-cli WiFi.AccessPoint.3.MultiAPType=None
ubus-cli WiFi.SSID.6.SSID=testpilot6G
ubus-cli WiFi.AccessPoint.3.Security.ModeEnabled=WPA3-Personal
ubus-cli 'WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"'
ubus-cli 'WiFi.AccessPoint.3.Security.KeyPassPhrase="00000000"'
ubus-cli WiFi.AccessPoint.3.Security.MFPConfig=Required
ubus-cli WiFi.AccessPoint.3.Enable=1
```

之後再 patch：

```bash
sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf
sed -i 's/^sae_pwe=.*/sae_pwe=2/g' /tmp/wl1_hapd.conf
sed -i 's/^ieee80211be=.*/ieee80211be=0/g' /tmp/wl1_hapd.conf
sed -i '/^bss=wl1\.1$/,$d' /tmp/wl1_hapd.conf
```

### STA side

```bash
ubus-cli WiFi.AccessPoint.3.Enable=0
ubus-cli WiFi.AccessPoint.4.Enable=0
wpa_cli -i wl1 terminate 2>/dev/null || true
rm -f /var/run/wpa_supplicant/wl1 2>/dev/null || true
iw dev wl1.1 del 2>/dev/null || true
iw dev wl1 disconnect 2>/dev/null || true
ifconfig wl1 down
wl -i wl1 ap 0
iw dev wl1 set type managed
wl -i wl1 up
ifconfig wl1 up
```

然後建立：

```text
ctrl_interface=/var/run/wpa_supplicant
update_config=1
sae_pwe=2
network={
ssid="testpilot6G"
key_mgmt=SAE
sae_password="00000000"
ieee80211w=2
scan_ssid=1
}
```

### 這一步當下的感覺

表面上看起來一切都對了，理論上該能連。

但實際沒有。

---

## 4.12 這一輪新的關鍵發現：STA 現在「看得到 AP，但仍被拒」

這是非常重要的新進展，因為它把「掃不到」與「被拒絕」區分開來了。

### 代表性指令

```bash
wpa_cli -i wl1 scan_results
tail -n 160 /tmp/wpa_wl1.log
```

### 關鍵輸出

```text
2c:59:17:00:19:96    5955    -85    [WPA2-SAE-CCMP][SAE-H2E][ESS]    testpilot6G
```

STA debug log：

```text
wl1: Trying to associate with 2c:59:17:00:19:96 (SSID='testpilot6G' freq=5955 MHz)
nl80211: Connect request send successfully
BSS is ml_capable:1
Connect event (status=49)
CTRL-EVENT-ASSOC-REJECT bssid=2c:59:17:00:19:96 status_code=49
```

### 這代表什麼

- 不是「STA 掃不到 testpilot6G」
- 也不是「BSSID 錯」
- 也不是「scan_freq 不對」
- 而是：
  - STA 真的掃到
  - 真的發出 connect
  - DUT/driver path 真的把它 reject 掉

### 當下最重要的推論

- 問題重心回到 **DUT 端 runtime/EHT/MLO/secondary BSS**
- 不是單純 RF visibility

---

## 4.13 這一輪也試過 `sae_pwe=0` + `scan_freq=5955` + pin BSSID，仍失敗

因為早期有一輪是 `sae_pwe=2` / `0` 造成 `49 -> 1` 的變化，所以這一輪也重新試過 H&P only 路線。

### STA config

```text
sae_pwe=0
bssid=2c:59:17:00:19:96
scan_freq=5955
key_mgmt=SAE
sae_password="00000000"
ieee80211w=2
scan_ssid=1
```

### 結果

仍然：

```text
status_code=49
wpa_state=DISCONNECTED
```

### 這一步的價值

它證明了：

- 這一輪的新 DUT firmware 問題，**不是單靠切 `sae_pwe=0` 就能過**
- 所以不能再把 H2E/H&P 當唯一根因

---

## 4.14 這一輪還看到一個新問題：manual hostapd 路徑本身也變得不可靠

有幾次我們為了強制吃 patch 後的 `wl1_hapd.conf`，直接手動起 hostapd。

### 試過的指令

```bash
hostapd -ddt -B -f /tmp/wl1_hapd.log /tmp/wl1_hapd.conf
```

### 看到的問題

1. 有時 `pgrep -af hostapd` 看得到 process，但：

```bash
hostapd_cli -i wl1 status
```

卻回：

```text
Failed to connect to hostapd - wpa_ctrl_open: No such file or directory
```

2. 如果往 config 裡硬塞：

```text
he_oper_chwidth=1
he_oper_centr_freq_seg0_idx=7
ieee80211ax=1
```

則 upstream `hostapd` 直接報：

```text
unknown configuration item 'he_oper_chwidth'
unknown configuration item 'he_oper_centr_freq_seg0_idx'
unknown configuration item 'ieee80211ax'
```

3. 還看過：

```text
nl80211: Beacon set failed: -114 (Operation already in progress)
Failed to set beacon parameters
Interface initialization failed
```

### 這一步的結論

- 新 DUT firmware 上，**manual hostapd 不再是可靠的「真實 runtime 代表」**
- 很可能：
  - wld 有自己的 spawn/control path
  - `/tmp/wl1_hapd.conf` 只是部分 runtime 來源
  - 或 hostapd socket/control 行為跟之前不一樣

換句話說：

> 「我手動把 `/tmp/wl1_hapd.conf` patch 成我想要的樣子」  
> **不再保證 active runtime 就真的是那個樣子**

---

## 4.15 這一輪新的根本線索：`OperatingStandards=ax` 仍只修 primary，secondary 又會自己長回來

### 指令

```bash
ubus-cli WiFi.Radio.2.OperatingStandards=ax
grep -nE '^(ieee80211be|sae_pwe|multi_ap|bss=|ssid=|ocv=)' /tmp/wl1_hapd.conf
```

### 輸出

```text
8:ieee80211be=0
16:ssid=testpilot6G
36:sae_pwe=1
52:multi_ap=0
54:ieee80211be=1
57:bss=wl1.1
62:ssid=OpenWrt_2
82:sae_pwe=1
98:multi_ap=3
100:ieee80211be=1
```

### 這說明了什麼

- primary 確實吃到 `ax`
- 但 secondary 又把：
  - `ieee80211be=1`
  - `sae_pwe=1`
  - `wl1.1`
  帶回來了

### 這一輪目前最可信的推論

- **真正的 root cause 很可能不是單一欄位，而是 secondary 6G BSS / MLO / EHT profile 殘留**
- 只要 secondary 還在，STA 就可能被 DUT 當成不相容 station 直接 reject

---

## 5. 目前最有價值的推論（依可信度排序）

### 5.1 高可信：DUT 新 firmware 仍在生成 secondary 6G EHT/MLO runtime

證據：

- `OperatingStandards=ax` 後 secondary 仍是 `ieee80211be=1`
- `wl1.1` 反覆被生回來
- STA log 顯示 `BSS is ml_capable:1`
- `status_code=49` 是 AP-side reject，不像是單純 credential 問題

### 5.2 高可信：`ocv=0` 仍是必要條件，但不是這一輪唯一條件

證據：

- 舊輪已證明 `ocv=0` 可解 `mfp_ocv` BSS loop
- 這一輪如果只 patch `ocv=0`，仍無法直接保證連線成功

所以現在的理解應是：

- `ocv=0` 是**必要但不充分**

### 5.3 中高可信：這一輪 active runtime 不完全受 `/tmp/wl1_hapd.conf` 手動 patch 控制

證據：

- `hostapd_cli` 有時接不上
- manual hostapd 有時初始化失敗
- wld 重新 enable AP 後會重生 secondary/EHT 內容

### 5.4 中可信：新 DUT firmware 的 wld / hostapd bring-up path 跟之前 live-good 行為不同

目前沒有完全證明，但症狀高度可疑：

- 同樣的 `sed` / `hostapd` / `ocv=0` 手法，這輪不像之前那麼穩定
- 可能需要比對新舊 firmware 的 wld/hostapd config generation 差異

### 5.5 低可信：單純 RF / country / scan 問題

這條現在應該放低優先度，因為：

- `wpa_cli scan_results` 已經明確看得到：

```text
2c:59:17:00:19:96  5955  ...  testpilot6G
```

所以「根本看不到 AP」不是這輪主因。

## 6. 已經證明不值得再走的方向

### 6.1 不要再拿 6G 測 WPA2

理由：

- setter 可回 OK
- runtime 還是會回 SAE/WPA3

### 6.2 不要把 `AP4.Enable=0` 當成 secondary 已清乾淨

理由：

- getter 很乾淨
- runtime 卻還可能留 `wl1.1/OpenWrt_2`

### 6.3 不要再隨手 `wl -i wl1 chanspec 6g1/80`

理由：

- 已證明會把 BSS 打 down

### 6.4 不要把 manual hostapd 當成最終答案

理由：

- 這輪已看到：
  - control socket 不可靠
  - beacon set -114
  - config parse mismatch

### 6.5 不要把 `status 49 -> status 1` 視為問題解決

理由：

- 這只表示某些 incompatibility 被挪開了
- 不代表已經能 COMPLETED

## 7. 目前最有價值的指令集合

### 7.1 快速判斷 STA 還是不是 AP mode

```bash
iw dev
ps | grep -E 'hostapd|wpa_supplicant' | grep -v grep
ubus-cli "WiFi.AccessPoint.3.Enable?"
```

### 7.2 快速判斷 DUT 6G runtime 乾不乾淨

```bash
ubus-cli "WiFi.Radio.2.OperatingStandards?"
ubus-cli "WiFi.AccessPoint.3.MultiAPType?"
ubus-cli "WiFi.AccessPoint.4.Enable?"
grep -nE '^(ieee80211be|sae_pwe|multi_ap|bss=|ssid=|ocv=|mlo_aff_link_kde)' /tmp/wl1_hapd.conf
```

### 7.3 快速判斷是「掃不到」還是「掃得到但被拒」

```bash
wpa_cli -i wl1 scan_results
wpa_cli -i wl1 status
tail -n 160 /tmp/wpa_wl1.log
wl -i wl1 assoclist
```

如果看到：

```text
scan_results 有 testpilot6G
Connect request send successfully
CTRL-EVENT-ASSOC-REJECT status_code=49
```

那就代表：

- STA 看得到 AP
- 問題在 AP-side reject，不是 scan 本身

### 7.4 快速判斷有沒有 `mfp_ocv` loop

```bash
logread | grep -E 'mfp_ocv|WLC_E_BSSCFG_UP|mld_unit'
```

## 8. 建議的下一步方向（避免再走散）

1. **先找哪個 backend / setter 會讓 secondary `wl1.1` 和 `ieee80211be=1` 再生。**  
   現在最該做的是找「根源控制面」，不是一直 patch `/tmp/wl1_hapd.conf`。

2. **比對新 DUT firmware 與之前 live-good 那版的 wld/hostapd config generation 差異。**  
   這一輪的行為已經不像單純同一套 runtime。

3. **在 wld-managed 路徑下抓 fresh assoc log，而不是只看 manual hostapd。**  
   要證明到底是哪一段 AP-side policy/driver path 在回 `49`。

4. **把 secondary/EHT/MLO 殘留問題釐清後，再重新跑 STA matrix。**  
   在那之前，`sae_pwe=2` / `0` 只是局部試探，不是主戰場。

5. **如果要再做 live workaround，先確認現在 runtime 是不是還真的吃 `/tmp/wl1_hapd.conf`。**  
   這件事在新 DUT firmware 上不能再直接假設。

## 9. 目前我認為最接近真相的總結

如果只用一句話總結目前這幾輪的經驗：

> **6G STA 真正難的不是把 STA `wpa_supplicant` 寫對，而是讓 DUT 6G AP 真的落在一個「沒有 secondary EHT/MLO 殘留、沒有 `mfp_ocv` loop、且 active runtime 真跟你以為的一樣」的狀態。**

目前已知：

- 舊輪曾成功連上，證明 **硬體不是絕對做不到**
- 但新 DUT firmware 這輪的 runtime 形狀變了
- `status_code=49`、`wl1.1`、`ieee80211be=1`、`sae_pwe=1`、`mlo_aff_link_kde` 這些線索應該被視為**同一個家族的問題**

因此：

- 下一輪不要再把重心放在「再改一次 STA config 看看」
- 應該把重心放在：
  - **DUT backend 如何生成 6G runtime**
  - **secondary BSS 為什麼關不乾淨**
  - **新 firmware 的 active hostapd path 到底在哪**

---

## 10. 附：這一輪最值得保留的逐字訊號

### STA 成功看到 AP，但被拒

```text
2c:59:17:00:19:96    5955    -85    [WPA2-SAE-CCMP][SAE-H2E][ESS]    testpilot6G
```

```text
wl1: Trying to associate with 2c:59:17:00:19:96 (SSID='testpilot6G' freq=5955 MHz)
nl80211: Connect request send successfully
BSS is ml_capable:1
CTRL-EVENT-ASSOC-REJECT bssid=2c:59:17:00:19:96 status_code=49
```

### DUT 新 firmware 又把 secondary 帶回來

```text
8:ieee80211be=0
16:ssid=testpilot6G
36:sae_pwe=1
52:multi_ap=0
54:ieee80211be=1
57:bss=wl1.1
62:ssid=OpenWrt_2
82:sae_pwe=1
98:multi_ap=3
100:ieee80211be=1
```

### 舊輪真正成功的基礎條件

```text
DUT:
  ocv=0
  sae_pwe=2
  ieee80211be=0
  secondary stanza removed
STA:
  sae_password="00000000"
  sae_pwe=2
  ieee80211w=2
  scan_ssid=1
結果:
  wpa_state=COMPLETED
  freq=5955
```

### 一定要記住的壞指令

```bash
wl -i wl1 chanspec 6g1/80
```

它曾經直接把 DUT BSS 打成 `down`，後面一連串假象都從這裡開始。
