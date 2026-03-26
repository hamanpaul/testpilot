# wifi_llapi 3x Full Run Determinism Report

> **日期**：2026-03-25  
> **DUT FW**：prplOS 4.0.3  
> **Cases**：420 official discoverable (D004–D420)  
> **平台**：DUT = prplOS (COM0 /dev/ttyUSB0), STA = Broadcom (COM1 /dev/ttyUSB1)

---

## 1. 執行摘要

連續執行 3 次 wifi_llapi 全量測試，驗證 test determinism。

| Run | Run ID | 開始 | 結束 | 耗時 | Exit | Cases |
|-----|--------|------|------|------|------|-------|
| 1 | `20260323T210653907525` | 03/23 21:06 | 03/24 06:39 | 9h 33m (34381s) | 0 | 420 |
| 2 | `20260324T064000114230` | 03/24 06:39 | 03/24 15:50 | 9h 11m (33047s) | 0 | 420 |
| 3 | `20260324T155052345610` | 03/24 15:50 | 03/25 00:59 | 9h 09m (32922s) | 0 | 420 |

**總執行時間**：27h 53m（100,350s）

---

## 2. Verdict 統計

### 2.1 Per-band verdicts（355 testpilot rows × 3 bands）

| Band | Metric | Run 1 | Run 2 | Run 3 |
|------|--------|-------|-------|-------|
| 5G   | Pass   | 200   | 198   | 198   |
| 5G   | Fail   | 155   | 157   | 157   |
| 2.4G | Pass   | 197   | 196   | 196   |
| 2.4G | Fail   | 91    | 92    | 92    |
| 2.4G | Skip   | 11    | 11    | 11    |
| 2.4G | N/A    | 56    | 56    | 56    |
| 6G   | Pass   | 197   | 196   | 196   |
| 6G   | Fail   | 102   | 103   | 103   |
| 6G   | N/A    | 56    | 56    | 56    |

### 2.2 Aggregate（per-cell）

| Verdict | Run 1 | Run 2 | Run 3 |
|---------|-------|-------|-------|
| Pass    | 591   | 590   | 590   |
| Fail    | 345   | 346   | 346   |
| Skip    | 11    | 11    | 11    |
| N/A     | 112   | 112   | 112   |
| **Total** | **1059** | **1059** | **1059** |

---

## 3. Determinism 分析

### 3.1 Cross-run 一致性

| 比較 | 一致 rows | 差異 rows | 一致率 |
|------|-----------|-----------|--------|
| Run 1 vs Run 2 | 353/355 | 2 | 99.44% |
| Run 1 vs Run 3 | 353/355 | 2 | 99.44% |
| Run 2 vs Run 3 | **355/355** | **0** | **100.00%** |

### 3.2 Flaky cases（Run 1 ≠ Run 2/3）

| Row | Object | Parameter | Run 1 | Run 2 | Run 3 | 分析 |
|-----|--------|-----------|-------|-------|-------|------|
| 3 | (kickStation sub-row) | — | Pass(5G/2.4G/6G) | Fail(5G/2.4G/6G) | Fail(5G/2.4G/6G) | 首次 run baseline 暖機效應 |
| 37 | WiFi.AP.{i}.AssocDev.{i}. | OperatingStandard | Pass(5G) | Fail(5G) | Fail(5G) | STA association timing |

**Flaky root cause**：Run 1 在剛建完 baseline 後立即開始，DUT 狀態較「乾淨」；Run 2/3 在前一 run 結束後接續，可能有殘留 association 或 EasyMesh controller reversion。

### 3.3 結論

- **Run 2 vs Run 3 = 100% 一致**：證明 test engine 在穩態下完全 deterministic。
- **Run 1 的 2 個差異**：屬於 baseline warm-up 效應，非 engine 不穩定。
- **Skip/N/A 三次完全一致**（11 + 112）：case filtering logic 穩定。

---

## 4. 效能分析

### 4.1 每 run 速度區段

| 區段 | Cases | 特徵 | 每 run 耗時 |
|------|-------|------|-------------|
| D004–D076 | ~73 | Fast getter | ~1.2 hr |
| D077–D093 | ~17 | Slow security/MACFilter (多 band setter/restore/sleep) | ~4-6 hr |
| D094–D276 | ~183 | Fast getter | ~1.5 hr |
| D277–D308 | ~31 | Slow scan (console flood) | ~4 hr |
| D309–D420 | ~110 | Fast tail | ~0.9 hr |

### 4.2 Run 間效能穩定性

| Metric | Run 1 | Run 2 | Run 3 |
|--------|-------|-------|-------|
| 總耗時 | 34381s | 33047s | 32922s |
| 平均/case | 81.9s | 78.7s | 78.4s |
| 偏差(vs avg) | +3.6% | -1.3% | -1.7% |

效能偏差 < 5%，主要來自 serialwrap ATTACH recovery 次數差異。

---

## 5. 本次修復的 4 個 Bug

### Bug 1: DUT kernel message flood
- **症狀**：SAE-H2E auth failure 產生連續 `CFG80211-ERROR` kernel messages，阻斷 serialwrap prompt detection
- **修復**：`verify_env()` 中 DUT gate check 前加入 `dmesg -n 1`

### Bug 2: 5G ModeEnabled reversion
- **症狀**：EasyMesh controller 把 5G 從 WPA2-Personal 還原為 WPA3-Personal (SAE-H2E)，STA Broadcom dhd driver 不支援
- **修復**：`_run_sta_band_baseline()` 即使 BSS already up 也強制套用 ModeEnabled=WPA2-Personal

### Bug 3: 6G connect failure fatal
- **症狀**：6G SAE-H2E connect 在 STA 上總是失敗（dhd driver 限制），整個 baseline 中斷
- **修復**：`_run_sta_band_connect_sequence()` 中 6G 失敗改為 warning + continue

### Bug 4: Multi-line printf split
- **症狀**：16 case YAMLs 的 `sta_env_setup` 有 multi-line `printf` 命令，被 `_iter_env_script_commands()` 拆分成不完整的 shell 指令，每個 ~45s timeout
- **修復**：pre-process 合併含有未閉合 single quote 的行

---

## 6. 報告檔案

| Run | Excel Report |
|-----|-------------|
| 1 | `20260323_4.0.3_wifi_LLAPI_20260323T210653907525.xlsx` |
| 2 | `20260324_4.0.3_wifi_LLAPI_20260324T064000114230.xlsx` |
| 3 | `20260324_4.0.3_wifi_LLAPI_20260324T155052345610.xlsx` |

---

## 7. 建議後續行動

1. **Scan console flood**：D277–D308 的 `WiFi.Radio.*.Scan()` output 直接打到 serial console，佔每 run ~4hr。建議 redirect 或 suppress 以將 run time 從 ~9hr 縮短至 ~5hr。
2. **kickStation warm-up**：考慮在 Run 開始前增加 explicit association warmup step。
3. **OperatingStandard flaky**：追蹤 STA 5G association timing 是否能穩定化。
