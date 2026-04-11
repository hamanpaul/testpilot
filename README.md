# TestPilot

> **[English](#english)** ｜ **[繁體中文](#繁體中文)**

---

## English

Plugin-based test automation framework for embedded device verification (prplOS / OpenWrt).

### Overview

TestPilot is a plugin-based test automation framework for prplOS / OpenWrt embedded devices. The architecture splits into two planes:

- **Deterministic verdict kernel** — test execution, evidence collection, pass/fail verdicts, and report projection.
- **Copilot SDK control plane** — session management, custom agents, advisory audit, and hook-governed safe remediation.

Core principle: **the Copilot SDK handles the control plane; it does NOT decide the final verdict.**

`wifi_llapi` currently supports in-run safe remediation between retry attempts. Scope is limited to environment repair only: serial session recovery, STA reconnect, band baseline rebuild, and environment re-verify. It does not rewrite YAML semantics, step commands, or pass criteria.

### Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **[serialwrap](https://github.com/paulc-arc/serialwrap)** — UART serial multiplexer for DUT / STA communication

After installing serialwrap, set the binary path via environment variable:

```bash
export SERIALWRAP_BIN=/path/to/serialwrap
```

Or add to `configs/testbed.yaml`:

```yaml
testbed:
  serialwrap_binary: /path/to/serialwrap
```

> Resolution order: `SERIALWRAP_BIN` env var → `testbed.yaml` config → error exit.

### Quick Start

```bash
uv pip install -e ".[dev]"                              # Install
cp configs/testbed.yaml.example configs/testbed.yaml    # First-time config
testpilot list-cases wifi_llapi                         # Verify
testpilot run wifi_llapi --dut-fw-ver BGW720-B0-403     # Run
```

### CLI Entry Points

You can use either the installed `testpilot` command or the Python module entry point.

`run` syntax is `testpilot run PLUGIN_NAME [--case CASE_ID] [--dut-fw-ver FW_VER]`. `PLUGIN_NAME` is required because TestPilot supports multiple plugins.

```bash
testpilot --version
python -m testpilot.cli --version
python -m testpilot.cli list-plugins
python -m testpilot.cli list-cases wifi_llapi
python -m testpilot.cli wifi-llapi baseline-qualify --band 5g
python -m testpilot.cli run wifi_llapi --case wifi-llapi-D004-kickstation
```

### Authentication

TestPilot supports two LLM backends. The auth chain tries each in order:

| Priority | Method | How to activate |
|----------|--------|-----------------|
| 1 | **Azure OpenAI (BYOK)** | `testpilot --azure run wifi_llapi` (interactive prompt) |
| 2 | **Azure OpenAI (env vars)** | Set `COPILOT_PROVIDER_*` env vars (see below) |
| 3 | **GitHub Copilot OAuth** | Default — no flags needed |

If all methods fail, the program exits with an error message.

#### Azure OpenAI Setup

**Option A: Interactive prompt (`--azure` flag)**

```bash
testpilot --azure run wifi_llapi --dut-fw-ver BGW720-B0-403
```

You will be asked for:
1. **Azure Endpoint URL** — e.g. `https://your-resource.openai.azure.com`
2. **Azure API Key** — your Azure OpenAI key (hidden input)
3. **Deployment Name** — e.g. `gpt-4o` (the Azure model deployment name)

**Option B: Environment variables**

```bash
export COPILOT_PROVIDER_TYPE=azure
export COPILOT_PROVIDER_BASE_URL=https://your-resource.openai.azure.com
export COPILOT_PROVIDER_API_KEY=your-api-key-here
export COPILOT_MODEL=gpt-4o
# Optional (default: 2024-10-21):
export COPILOT_PROVIDER_AZURE_API_VERSION=2024-10-21

testpilot run wifi_llapi --dut-fw-ver BGW720-B0-403
```

> **Tip:** Add the `export` lines to your shell profile (`~/.bashrc`, `~/.zshrc`) so you don't need `--azure` each time.

> **Security:** Never commit API keys to version control. Use environment variables or a `.env` file (already in `.gitignore`).

#### GitHub Copilot OAuth (Default)

If no Azure credentials are found, TestPilot falls through to GitHub Copilot OAuth via the Copilot SDK. No extra setup is required if you already have GitHub Copilot access.

### Running Tests

```bash
# Qualify reusable DUT/STA baseline before full runs
testpilot wifi-llapi baseline-qualify \
  --repeat-count 5 \
  --soak-minutes 15

# Single case (smoke test)
testpilot run wifi_llapi \
  --case wifi-llapi-D004-kickstation \
  --dut-fw-ver BGW720-B0-403

# Full suite (420 discoverable official cases)
testpilot run wifi_llapi --dut-fw-ver BGW720-B0-403

# Rebuild workbook compare against 0401.xlsx after selected live overlays
python scripts/compare_0401_answers.py \
  20260401T152827516151 \
  20260401T230006391661 \
  20260401T232631531561 \
  20260402T013838223177 \
  20260402T020432759837 \
  20260402T021317975166 \
  20260402T021716841976 \
  20260402T023927691290 \
  20260402T030604339596 \
  20260402T034832813249 \
  20260402T040807394935 \
  20260402T051006378317 \
  20260402T054957340010 \
  20260402T060543524189 \
  20260402T063003376730 \
  20260402T071356233843 \
  20260402T095404127199 \
  20260402T105808547293 \
  --output-md compare-0401.md \
  --output-json compare-0401.json

# With Azure OpenAI
testpilot --azure run wifi_llapi --dut-fw-ver BGW720-B0-403
```

Baseline experiment authority and current lab findings live in `docs/wifi-baseline-exp.md`.

### Report Outputs

| Track | Format | Purpose |
|-------|--------|---------|
| External delivery | `xlsx` | Pass / Fail only, written to Excel report |
| Internal diagnostics | `md` | Human-readable summary with per-case commands, output, log line references, and diagnostic status |
| Structured data | `json` | Machine-readable with summary stats, diagnostic status, remediation history, and log line numbers |
| UART RAW log | `DUT.log` / `STA.log` | serialwrap WAL decoded per-run UART communication records |

Output files location: `plugins/wifi_llapi/reports/`

Current workbook-calibration campaign artifacts live at repo root:

- `compare-0401.md`
- `compare-0401.json`
- answer authority: `0401.xlsx`
- workbook procedure authority for calibration: `Wifi_LLAPI` columns `G/H`
- baseline experiment authority: `docs/wifi-baseline-exp.md`
- current lab readiness status: multi-band baseline qualification is complete — `5G/6G/2.4G` all passed `baseline-qualify --repeat-count 5 --soak-minutes 15`; custom-6G hardening made `D019/D027` plain `Pass`, and the old `D032` `sta_band_not_ready` environment failure is gone. Clean-start dual-`firstboot` rerun `20260409T182347586948` had already cleared the last known `D028-D033` cold-start blocker; the newer dual-`firstboot` rerun `20260409T205434740233` then kept `D004/D005` at plain `Pass` and `D006` at `pass after retry (2/2)`, so the old `D005/D006 FailEnv` prefix no longer reproduces. The current detached full-run compare baseline is now `run_id=20260411T074146043202`; the earlier `20260409T213837737224` start is retained only as historical evidence
- latest targeted checkpoint: the 6G OCV hot path now uses a stabilization loop that re-patches `ocv=0`, restarts wl1 hostapd, and re-checks `ocv/socket/bss` together before continuing. Regression after this change: targeted tests `5 passed`, plugin runtime `1222 passed`, full suite `1627 passed`
- latest calibration checkpoint: workbook replay plus source-backed triage proved `D111 getStationStats() AssociationTime` was failing because repo parsing left a spurious trailing quote on `AssociationTime = "YYYY-MM-DDTHH:MM:SSZ",`; after fixing `_extract_key_values()` ordering, live single-case rerun `20260410T110659169758` became plain `Pass`, targeted parser/D111 tests are `4 passed`, and full plugin runtime regression is `1223 passed`. The next patch-driven case, `D211 OperatingStandards`, has now also been replayed against workbook row `211`: getters switch between `be` and `ax`, but AX phase still keeps EHT alive (`wl0/wl1/wl2 eht features=127`, 6G secondary hostapd still `ieee80211be=1`), so D211 remains blocked/fail-shaped and the next ready case in the current repo inventory is `D262`
- latest direct-stats continuation after that: `D324 BytesSent` is reopened and now treated as blocked. The earlier exact-close rerun `20260411T010328768651` is no longer durable: detached full run `20260411T074146043202` already drifted on 6G, and fresh isolated rerun `20260411T190338070996` re-proved `direct == getSSIDStats()` while invalidating base `wlX if_counters txbyte` on multiple bands (`5G 131874002 / 131874002 / 131873776`, `6G 81927301 / 81927301 / 81927045`, `2.4G 132049765 / 132049765 / 131682800`). Active 0403 source trace now shows `whm_brcm_vap_update_ap_stats()` can merge matching `wds*` peer stats into public `BytesSent`, so the case stays blocked until a live `wlX + Σwds* txbyte` oracle is captured and validated
- latest direct-stats continuation after that: `D330 MulticastPacketsReceived` is now aligned in the local repo state. Isolated rerun `20260411T191809490680` closed the active 0403 source-backed formula `max((rxmulti + matching wds_rxmulti) - BroadcastPacketsReceived, 0)` on all three bands; attempt 1 hit `/tmp/_tp_cmd.sh: line 2: syntax error: unterminated quoted string`, but attempt 2 exact-closed `direct / getSSIDStats / driver-formula = 0 / 0 / 0` on 5G, 6G, and 2.4G, and the committed metadata is now refreshed from stale row `254` to workbook row `330`
- latest direct-stats continuation after that: `D331 MulticastPacketsSent` is now formally blocked in `plugins/wifi_llapi/reports/D331_block.md`. Two source-backed trial reruns (`20260411T192138186700` / `20260411T192524301950`) proved the stale workbook `/proc/net/dev_extstats` `$18` compare should stay rejected, but 5G still held a fixed `driver = direct + 4` drift (`260377 / 260381`, `260613 / 260617`) even after the subtraction term was moved into the same `getSSIDStats()` snapshot, so the formula rewrite is still not durable enough to commit as a pass oracle
- latest direct-stats continuation after that: `D325 DiscardPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Workbook row `325`'s old `/proc/net/dev_extstats` field `$5` compare had already failed in real runner replay `20260411T010859993578` (`565 / 3854 / 356`-style stale proc drift), and the active 0403 source path was already proven by `D304` to overwrite this field from `whm_brcm_get_if_stats()` / `wl if_counters rxdiscard`; after rewriting the direct-property case to that oracle, real runner rerun `20260411T011321267947` exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is now refreshed from stale row `249` to workbook row `325`, targeted validation is green (`1 passed` official-case guardrail), full repo regression is green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D326`
- latest direct-stats continuation after that: `D326 DiscardPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Workbook row `326`'s old `/proc/net/dev_extstats` field `$13` compare failed in real runner replay `20260411T012137925510` (`184 / 3467 / 87`-style stale proc drift), while the active 0403 source path is now re-confirmed by both the fresh D326 survey and the already aligned `D305` oracle: `whm_brcm_get_if_stats()` writes `DiscardPacketsSent` from `wl if_counters txdiscard`; after rewriting the direct-property case to that source-backed readback, real runner rerun `20260411T012538161460` exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is now refreshed from stale row `250` to workbook row `326`, targeted validation is green (`1 passed` official-case guardrail), full repo regression is green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D327`
- latest direct-stats continuation after that: `D327 ErrorsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Workbook row `327`'s legacy `/proc/net/dev_extstats` field `$4` compare still exact-closed at zero in real runner replay `20260411T013241354703`, but the active 0403 source path is now re-confirmed by both the fresh D327 survey and the already aligned `D306` oracle: `whm_brcm_get_if_stats()` writes `ErrorsReceived` from `wl if_counters rxerror`; after refreshing the direct-property case to that source-backed readback, real runner rerun `20260411T013801878458` still exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is now refreshed from stale row `251` to workbook row `327`, targeted validation is green (`1 passed` official-case guardrail), full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D328`
- latest direct-stats continuation after that: `D328 ErrorsSent` is now aligned as a plain `Pass/Pass/Pass` row. The first real runner replay (`20260411T014458979418`) still exact-closed the legacy `/proc/net/dev_extstats` field `$12` compare at zero, but active 0403 source is now re-confirmed by the fresh D328 survey and the already aligned `D307` path: `whm_brcm_get_if_stats()` seeds `ErrorsSent` from `wl if_counters txerror`, with optional WDS accumulation in `whm_brcm_vap_ap_stats_accu()`. A focused live probe also showed this is a real moving counter rather than a fixed workbook sample (`5G=1`, `6G=3347`, `2.4G=0` across direct/getSSIDStats/txerror). After refreshing the direct-property case to the source-backed `txerror` readback, real runner rerun `20260411T015126498621` still exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is now refreshed from stale row `252` to workbook row `328`, targeted validation is green (`1 passed` official-case guardrail), full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D329`
- latest direct-stats continuation after that: `D329 FailedRetransCount` is now aligned as a plain `Pass/Pass/Pass` row. The first real runner replay (`20260411T015905984272`) exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. Active 0403 source is now re-confirmed by the fresh D329 survey and the already aligned `D308` path: `whm_brcm_get_if_stats()` writes `FailedRetransCount` from `wl if_counters txretransfail`, with optional WDS accumulation in `whm_brcm_vap_ap_stats_accu()`. A focused live probe then exact-closed `direct / getSSIDStats / txretransfail` at `0 / 0 / 0` on 5G, 6G, and 2.4G, while also showing there is no active `wds*` peer in the current baseline. After refreshing the direct-property case to the source-backed `txretransfail` readback, real runner rerun `20260411T020534026608` still exact-closed on all three bands: 5G `0 / 0 / 0`, 6G `0 / 0 / 0`, and 2.4G `0 / 0 / 0` across direct/getSSIDStats/if_counters. The committed metadata is now refreshed from stale row `253` to workbook row `329`, targeted validation is green (`1 passed` official-case guardrail), full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D334`
- latest direct-stats continuation after that: `D334 RetransCount` is now aligned as a plain `Pass/Pass/Pass` row. The first real runner replay (`20260411T021238026451`) exact-closed direct Stats and getSSIDStats(), but it still lacked an independent driver oracle and the original extractor could ambiguously match `FailedRetransCount`. Active 0403 source is now re-confirmed by the fresh D334 survey at `wldm_SSID_TrafficStats()` -> `wl if_counters txretrans`, without WDS accumulation on the direct-property path. A focused live probe then closed the source-backed low-32 driver view at 5G `4294967295`, 6G `4294963915`, and 2.4G `0` across direct/getSSIDStats/low-32(txretrans). After refreshing the direct-property case to use anchored `getSSIDStats()` extraction plus the low-32 `txretrans` oracle, real runner rerun `20260411T022030741126` passed on retry: attempt 1 still saw a transient 6G drift (`4294967294` vs driver `0`), but attempt 2 exact-closed all three bands at `0 / 0 / 0`. The committed metadata is now refreshed from stale row `258` to workbook row `334`, targeted validation is green (`1 passed` official-case guardrail), the command-budget inventory now tracks `630` long official-case commands, full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D337`
- latest direct-stats continuation after that: `D337 UnknownProtoPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. The first real runner replay (`20260411T023258929853`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. Active 0403 source is now re-confirmed by the fresh D337 survey at `wldm_SSID_TrafficStats()` -> `wl if_counters rxbadprotopkts`, without WDS accumulation on the direct-property path. A focused live probe then exact-closed `direct / getSSIDStats / rxbadprotopkts` at `0 / 0 / 0` on 5G, 6G, and 2.4G; the adjacent getSSIDStats-family `rxunknownprotopkts` view also stayed `0` on all three bands, which explains why the workbook-era direct/getSSIDStats replay still exact-closed despite the counter-family split. After refreshing the direct-property case to that source-backed `rxbadprotopkts` oracle, real runner rerun `20260411T024443960794` exact-closed all three bands at `0 / 0 / 0`. The committed metadata is now refreshed from stale row `261` to workbook row `337`, targeted validation is green (`1 passed` official-case guardrail), the command-budget inventory now tracks `633` long official-case commands, full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D406`
- latest direct-stats continuation after that: `D406 MultipleRetryCount` is now aligned as a plain `Pass/Pass/Pass` row. The first real runner replay (`20260411T025549740195`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but it still lacked an independent driver oracle. Active 0403 source is now re-confirmed at `wldm_SSID_TrafficStats()` -> `wl if_counters txretrie`; a focused live probe then exact-closed `direct / getSSIDStats / txretrie` at `0 / 0 / 0` on 5G, 6G, and 2.4G, while `ls /sys/class/net | grep '^wds'` stayed empty in the current baseline. After refreshing the direct-property case to use anchored `getSSIDStats()` extraction plus the `txretrie` driver oracle, real runner rerun `20260411T025954644775` exact-closed all three bands at `0 / 0 / 0`. The committed metadata is now refreshed from stale row `301` to workbook row `406`, targeted validation is green (`1225 passed` guardrails), the command-budget inventory now tracks `636` long official-case commands, full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D407`
- latest direct-stats continuation after that: `D407 RetryCount` is now aligned as a plain `Pass/Pass/Pass` row. The first real runner replay (`20260411T031324456196`) already exact-closed direct Stats and getSSIDStats() at zero on all three bands, but the workbook-era extractor still ambiguously matched `MultipleRetryCount` and there was no independent driver oracle. Active 0403 source is now re-confirmed at `wldm_SSID_TrafficStats()` -> `wl if_counters txretry`; a focused live probe then exact-closed `direct / getSSIDStats / txretry` at `0 / 0 / 0` on 5G, 6G, and 2.4G, while `ls /sys/class/net | grep '^wds'` again stayed empty in the current baseline. After refreshing the direct-property case to use anchored `RetryCount` extraction plus the `txretry` driver oracle, real runner rerun `20260411T031645170662` exact-closed all three bands at `0 / 0 / 0`. The committed metadata is now refreshed from stale row `302` to workbook row `407`, targeted validation is green (`1225 passed` guardrails), the command-budget inventory now tracks `642` long official-case commands, full repo regression remains green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D528`
- latest spectrum continuation after that: `D528 getSpectrumInfo bandwidth` is now aligned as a plain `Pass/Pass/Pass` row. The workbook-era case failed in replay `20260411T032529278022` because it still required a numeric-only regex even though active 0403 source returns a string-shaped bandwidth field through `_getSpectrumInfo()` -> `s_prepareSpectrumOutput()` -> `amxc_var_add_key(cstring_t, "bandwidth", swl_bandwidth_str[llEntry->bandwidth])`; the sync refresh path `wifiGen_rad_getSpectrumInfo(..., update=false)` further seeds survey-derived spectrum entries with `SWL_BW_20MHZ` in `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()`. After locking the case to the source-backed public shape `bandwidth="20MHz"` and updating the spectrum guardrail fixture accordingly, real runner rerun `20260411T034134858534` exact-closed on all three bands, targeted validation stayed green (`1225 passed` guardrails), full repo regression stayed green (`1634 passed`), and the next ready patch-driven workbook-Pass case in the current repo inventory is `D529`
- latest spectrum continuation after that: `D532 getSpectrumInfo ourUsage` and `D533 getSpectrumInfo availability` are now aligned as plain `Pass/Pass/Pass` rows. Active 0403 still serializes both fields through `_getSpectrumInfo()` -> `s_prepareSpectrumOutputWithChanFilter()`, while `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` derives `ourUsage` from `ourTime / total_time` and `availability` from survey idle/free airtime ratios. Isolated reruns `20260411T183356920330` and `20260411T183405281629` both passed, and recomputing workbook compare against detached full run `20260411T074146043202` with the current local YAML overlay moved the snapshot to `220 / 420 full matches`, `200 mismatches`, and `67 metadata drifts`. Interpreted via `evaluation_verdict` instead of stale per-band `results_reference`, `77` workbook-Pass gaps still remain, with the patch-scope true-open set now at `D277`, `D281-D287`, `D290`, `D295`, `D322-D324`, `D330-D333`, and `D335-D336`; `D295 scan()` is now formalized in `plugins/wifi_llapi/reports/D295_block.md`, and `D324 BytesSent` is now likewise formalized in `plugins/wifi_llapi/reports/D324_block.md`
- latest row-drift refresh after that checkpoint: `D262 getRadioAirStats():void` initially showed 6G `[""]` only because `WiFi.Radio.2.Status="Down"`; source-backed triage on `_getRadioAirStats()` confirmed this method early-returns when the radio is not active. After `wifi-llapi baseline-qualify --band 6g --repeat-count 1 --soak-minutes 0` restored all three radios to `Status="Up"`, live single-case rerun `20260410T115313185471` became plain `Pass`, and the case metadata is now refreshed to workbook row `262`
- latest Radio.Stats green-lock after that: `D263 getRadioStats() BroadcastPacketsReceived` also reran plain `Pass` at `20260410T115954628992`; although workbook row `263` still shows a stale sample `BroadcastPacketsReceived = 0`, 0403 patch note `17) Radio.Stats, SSID.Stats issues` says Radio.Stats now uses reworked bcast/mcast counters from dev_ext, and the live run returned numeric `BroadcastPacketsReceived = 363 / 142 / 113` on 5G / 6G / 2.4G. The case metadata is now refreshed to workbook row `263`
- latest adjacent Radio.Stats green-lock after that: `D264 getRadioStats() BroadcastPacketsSent` reran plain `Pass` at `20260410T120300247819`; workbook row `264` still shows a stale sample `BroadcastPacketsSent = 0`, but the same 0403 Radio.Stats rework means the authoritative 0403 shape is the live numeric counter, which reran as `921 / 1080 / 1168` on 5G / 6G / 2.4G. The case metadata is now refreshed to workbook row `264`, and the next ready case in the current repo inventory is `D265`
- latest adjacent Radio.Stats green-lock after that: `D265 getRadioStats() BytesReceived` reran plain `Pass` at `20260410T120916047799`; workbook row `265` still mentions a `/proc/net/dev` cross-check heuristic, but 0403 reactivated `BytesReceived` directly from driver `if_counters.rxbyte`, so the authoritative 0403 shape is still the live numeric counter rather than the older proc-file heuristic. The case metadata is now refreshed to workbook row `265`, and the next ready case in the current repo inventory is `D266`
- latest adjacent Radio.Stats green-lock after that: `D266 getRadioStats() BytesSent` reran plain `Pass` at `20260410T122049771373`; source-backed triage shows 0403 ultimately refreshes radio `BytesSent` through `whm_brcm_rad_get_counters_fromfile()` and driver `wl ... counters` `txbyte`, and live compare proved 5G/2.4G API values match driver `txbyte` while 6G happens to match `/proc/net/dev` instead of `wl1 counters`. That mixed outcome means workbook row `266`'s `/proc/net/dev` heuristic is no longer a stable 0403 oracle, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `266`, and the next ready case in the current repo inventory is `D267`
- latest adjacent Radio.Stats green-lock after that: `D267 getRadioStats() DiscardPacketsReceived` reran plain `Pass` at `20260410T122535158860`; workbook row `267` still asks for API-to-`/proc/net/dev` `RX_drop-pkg` minimal discrepancy, but live compare came back mixed across bands: API=`0 / 3752 / 0`, `/proc/net/dev`=`565 / 3752 / 356`, and driver `wl ... counters` `rxdropped`=`0 / 0 / 0` on 5G / 6G / 2.4G. Together with the 0403 source flow (`ifstats->rxdiscard` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later), that means `/proc/net/dev` is not a stable three-band oracle for this field, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `267`, and the next ready case in the current repo inventory is `D268`
- latest adjacent Radio.Stats green-lock after that: `D268 getRadioStats() DiscardPacketsSent` reran plain `Pass` at `20260410T122928854759`; workbook row `268` still asks for API-to-`/proc/net/dev` `TX_drop-pkg` minimal discrepancy, but live compare again came back mixed across bands: API=`0 / 3469 / 0`, `/proc/net/dev`=`184 / 3467 / 87`, and driver `wl ... counters` `txdropped`=`0 / 0 / 0` on 5G / 6G / 2.4G. Together with the 0403 source flow (`ifstats->txdiscard` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later), that means `/proc/net/dev` is not a stable three-band oracle for this field either, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `268`, and the next ready case in the current repo inventory is `D269`
- latest adjacent Radio.Stats green-lock after that: `D269 getRadioStats() ErrorsReceived` reran plain `Pass` at `20260410T123405993813`; workbook row `269` still records `ErrorsReceived = 0 / 0 / 0` and points to `/proc/net/dev` `RX_Error-pkg`, but live compare again came back mixed across bands: API=`8 / 0 / 8`, `/proc/net/dev`=`0 / 0 / 0`, and driver `wl ... counters` `rxerror`=`8 / 8 / 8` on 5G / 6G / 2.4G. Together with the 0403 source flow (`ifstats->rxerror` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later), that means workbook zero/proc evidence is not a stable three-band oracle for this field either, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `269`, and the next ready case in the current repo inventory is `D270`
- latest adjacent Radio.Stats green-lock after that: `D270 getRadioStats() ErrorsSent` reran plain `Pass` at `20260410T123844750130`; unlike the three cases before it, workbook row `270`'s zero/proc heuristic still lines up cleanly on 0403: API=`0 / 0 / 0`, `/proc/net/dev`=`0 / 0 / 0`, and driver `wl ... counters` `txerror`=`0 / 0 / 0` on 5G / 6G / 2.4G. That means this one is row drift only rather than a proc-vs-driver split, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `270`, and the next ready case in the current repo inventory is `D271`
- latest adjacent Radio.Stats green-lock after that: `D271 getRadioStats() MulticastPacketsReceived` reran plain `Pass` at `20260410T124521685886`; workbook row `271` still points to `/proc/net/dev` `RX_multipkg`, but live compare again came back mixed across bands: API=`0 / 142 / 0`, `/proc/net/dev`=`363 / 142 / 113`, and driver `wl ... counters` `d11_rxmulti`=`10 / 0 / 0` on 5G / 6G / 2.4G. Together with the 0403 source flow (`ifstats->rxmulti` first, `whm_brcm_rad_get_counters_fromfile()` overwrite later, then broadcast subtraction merge), that means `/proc/net/dev` is not a stable three-band oracle for this field either, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `271`, and the next ready case in the current repo inventory is `D272`
- latest adjacent Radio.Stats green-lock after that: `D272 getRadioStats() MulticastPacketsSent` reran plain `Pass` at `20260410T125050031171`; workbook row `272` still points to `/proc/net/dev_extstats` `TX_multipkg`, but live compare showed API=`89594 / 91022 / 92958`, `dev_extstats`=`7260 / 2880 / 2260`, and driver `wl ... counters` `d11_txmulti`=`90551 / 28627 / 94162` on 5G / 6G / 2.4G. Together with the 0403 TX-side source flow (`txframe` first, `d11_txmulti/d11_txbcast` overwrite next, then broadcast subtraction merge), that means the old `dev_extstats` heuristic is no longer a stable three-band oracle, so the current numeric-counter validation remains the right semantic. The case metadata is now refreshed to workbook row `272`, and the next ready case in the current repo inventory is `D273`
- latest adjacent Radio.Stats green-lock after that: `D273 getRadioStats() PacketsReceived`, `D274 getRadioStats() PacketsSent`, `D275 getRadioStats() UnicastPacketsReceived`, and `D276 getRadioStats() UnicastPacketsSent` all reran plain `Pass` at `20260410T125433470613` / `20260410T125437398493` / `20260410T125441250801` / `20260410T125445239119`; live compare showed the family stays mixed on 0403: 5G/2.4G generally follow driver `wl ... counters` frame-based values (or the derived unicast subtraction), while 6G still diverges toward older proc-shaped or zero-shaped outputs. That means workbook rows `273-276` are still stale-oracle row-drift cases rather than candidates for narrowing the regex checks. The case metadata is now refreshed to workbook rows `273-276`, and the next ready case in the current repo inventory is `D277`
- latest scan-case blocker after that: `D277 getScanResults() Bandwidth` is still blocked, and the current shape is now sharper than the earlier raw `returncode=124` probe. A repo-side scan timeout fallback now exists in `command_resolver.py`, and local regression stayed green (`30 passed` resolver tests, `1223 passed` full plugin runtime file), but the isolated live rerun still does not complete authoritatively: WAL evidence shows the run reaches raw `WiFi.Radio.2.getScanResults()`, then serialwrap recovery injects `^C`, DUT prints `Please press Enter to activate this console.`, and `COM0` drops to `ATTACHED / PROMPT_TIMEOUT` until recovery returns it to `READY`. So the current blocker is still transport-side scan capture rather than a proven Bandwidth semantic mismatch; workbook row `277`'s BSSID-targeted compare remains pending and `D277` stays unmodified
- latest scan-case alignment after that: `D278 getScanResults() BSSID` reran plain `Pass` at `20260410T135946424063` with workbook-style target compare. The case now extracts the first target BSSID from each LLAPI scan and cross-checks the same BSSID against `iw dev wl0/wl1/wl2 scan`; live evidence matched on all three bands (`38:88:71:2f:f6:a7` on 5G, `3a:06:e6:2b:a3:1a` on 6G, `8c:19:b5:6e:85:e1` on 2.4G). The YAML row metadata is now refreshed from `280` to workbook row `278`
- latest scan-case alignment after that: `D279 getScanResults() Channel` reran plain `Pass` at `20260410T140714322443` after tightening the LLAPI parse to the real `Channel =` line and comparing it against an `iw dev wl0/wl1/wl2 scan` frequency-to-channel conversion for the same target BSSID. Live evidence now matches authoritatively on all three bands (`36/36` on 5G, `5/5` on 6G, `1/1` on 2.4G). The YAML row metadata is now refreshed from `281` to workbook row `279`
- latest scan-case alignment after that: `D280 getScanResults() EncryptionMode` reran plain `Pass` at `20260410T143122662554` after converting the case to a workbook-style first-WPA-target compare. 0403 source still constrains neighboring WiFi `EncryptionMode` to the enum family `TKIP / AES / TKIPandAES / None`, but the live getter continues to emit `Default`; the isolated rerun now locks that fail-shaped mismatch authoritatively on all three bands against the same-target `iw dev wl0/wl1/wl2 scan` cipher evidence (`38:88:71:2f:f6:a7` / `3a:06:e6:2b:a3:1a` / `8c:19:b5:6e:85:e1`, all `Pairwise ciphers: CCMP` -> normalized `AES`, while LLAPI stays `Default`). The YAML row metadata is now refreshed from `282` to workbook row `280`
- latest scan-case blocker after that: `D281 getScanResults() Noise` still has no live-authoritative replay. A temporary workbook-style first-WPA-target compare was trialed because 0403 source still parses neighboring `Noise` from `wl -i wlX escanresults`, but two isolated reruns (`20260410T155529962490` / `20260410T155932807150`) were not stable enough to freeze semantics: the first replay matched 5G (`-100/-100`) but never emitted same-target `WlNoise6g` and drifted on 2.4G (`-80` vs `-77`), while the second replay lost same-target `WlNoise` on both 5G and 6G and still drifted on 2.4G (`-80` vs `-79`). So the rewrite was rejected, the committed YAML remains unchanged at stale row `283`
- latest scan-case blocker after that: `D282 getScanResults() OperatingStandards` also failed to close as a committed rewrite. The trial isolated rerun `20260410T163026194231` did prove new live shapes (`5G a,n,ac,ax`, `6G ax,be`, `2.4G b,g,n,ax`), but it still could not produce a deterministic all-band same-target replay: 5G no longer matched the earlier EHT-shaped survey target, 6G emitted no same-target `WlOperatingStandards6g`, and 2.4G drifted to `LLAPI b,g,n,ax` vs `wl b,g,n,ax,be`. Controlled baseline probes stayed inconsistent as well (`testpilot5G` LLAPI `a,n,ac,ax,be` vs wl `a,n,ac,ax`; `testpilot6G` absent in the replay snapshot; `testpilot2G` absent in LLAPI while wl still exposed an EHT-capable baseline BSSID). So the D282 rewrite was rejected, the committed YAML stays unchanged at stale row `284`, and the next ready case in the current repo inventory is `D283`
- latest scan-case blocker after that: `D283 getScanResults() RSSI` is now also blocked on the same raw 6G scan transport path as D277. Source trace still keeps the field on the neighboring scan parser (`RSSI: ` token -> `ap_SignalStrength`), and both historical full-run evidence (`20260409T213837737224`) and a fresh isolated rerun (`20260410T164405221878`) stayed transport-shaped rather than semantic: the full run already failed at `step_6g_scan`, while the isolated rerun never produced step output after `setup_env`, left the per-case `agent_trace` directory empty, and briefly pushed `COM0` back to `ATTACHED / PROMPT_TIMEOUT` before self-test restored `READY`. So no YAML rewrite landed, the committed case stays unchanged, and the next ready case in the current repo inventory is `D284`
- latest scan-case blocker after that: `D284 getScanResults() SecurityModeEnabled` also failed to close as a committed rewrite. Source trace still maps neighboring `SecurityModeEnabled` from `AKM Suites` / `RSN` in `_wldm_get_securitymode_encryptionmode()`, and the first isolated rerun `20260410T170750425931` did prove same-target replay on 5G (`38:88:71:2f:f6:a7` -> `WPA2-Personal`) and 2.4G (`8c:19:b5:6e:85:e1` -> `WPA2-WPA3-Personal`), but 6G would not freeze to one BSSID: LLAPI chose `3a:06:e6:2b:a3:1a` (`.ROAMTEST_RSNO_P10P_1`) while same-target `iw` emitted `IwSecurityMode6g=None`, and follow-up manual probes showed LLAPI can also expose `2C:59:17:00:19:96` (`OpenWrt_1`) as another `WPA3-Personal` target while `iw` prefers that associated BSSID instead. A second isolated rerun `20260410T171358112868` then tried an associated-BSSID selector, but the 6G LLAPI step emitted no `LlapiBssid6g`, so the `iw` step placeholder could not resolve. The trial rewrite was therefore rejected, the committed YAML stays unchanged at stale row `286`, full plugin runtime regression after revert is still `1223 passed`, and the next ready case in the current repo inventory is `D285`
- latest scan-case blocker after that: `D285 getScanResults() SignalNoiseRatio` also failed to close as a committed rewrite. `compare-0401.md` maps the case to workbook row `285`, but the committed YAML still stays at stale row `287`; source survey also showed 0403 neighboring scan internals still center on `RSSI` / `SignalStrength` plus `Noise` (`wldm_lib_wifi.h`, `wldm_lib_wifi.c`), while `wld_radio.odl` and public `wld.h` expose a derived `SignalNoiseRatio` field at the scan-result model layer. Live standalone LLAPI replay did prove the field is populated on 6G (`3A:06:E6:2B:A3:1A`, `RSSI=-93`, `Noise=-97`, `SignalNoiseRatio=4`) and 2.4G (`8C:19:B5:6E:85:E1`, `RSSI=-46`, `Noise=-80`, `SignalNoiseRatio=34`), but source-backed same-target replay still would not freeze: direct `wl -i wl1 escanresults` could not find the 6G LLAPI first BSSID at all, while a same-target 2.4G raw probe did find `8C:19:B5:6E:85:E1` yet reported `RSSI=-54 dBm`, `noise=-75 dBm`, `SNR=21 dB`, drifting far from LLAPI `34`. The trial rewrite was therefore rejected, the committed YAML stays unchanged at stale row `287`, and the next ready case in the current repo inventory is `D286`
- latest scan-case blocker after that: `D286 getScanResults() SignalStrength` also failed to close as a committed rewrite. Source trace still keeps neighboring `SignalStrength` on the same `RSSI: ` token path as `D283` (`wldm_lib_wifi.c` fills `ap_SignalStrength` directly from raw RSSI), so a workbook-style same-target replay was trialed against `iw`/raw scan evidence. The isolated rerun `20260410T181105027445` stayed deterministic but still did not close: 5G replay held the same target `38:88:71:2f:f6:a7` yet drifted `LLAPI=-64` vs `iw=-65` on both attempts, 6G never emitted a same-target `IwSignalStrength6g` for `3a:06:e6:2b:a3:1a`, and 2.4G drifted badly on the same target `8c:19:b5:6e:85:e1` (`LLAPI=-46` vs `iw=-55/-56`). Follow-up raw `wl -i wl0/wl1/wl2 escanresults` probes then confirmed only partial closure: 5G same-target raw RSSI does match at `-64`, but 6G still cannot find `3A:06:E6:2B:A3:1A` at all and 2.4G same-target raw RSSI still drifts at `-54 dBm`. The trial rewrite was therefore rejected, `D286` was reverted to its original generic shape with stale row `288`, and the next ready case in the current repo inventory is `D287`
- latest scan-case blocker after that: `D287 getScanResults() SSID` also failed to close as a committed rewrite. Source trace still keeps neighboring `SSID` on the same raw `SSID: ` token path, and the workbook-style same-target trial did prove the parser/evidence path is sound on 5G and 2.4G: rerun `20260410T182739821870` locked `38:88:71:2f:f6:a7` -> `Verizon_Z4RY7R` and `8c:19:b5:6e:85:e1` -> `TMOBILE-85DF-TDK-2G` identically across LLAPI and `iw`. But 6G still would not close: LLAPI exposed `3a:06:e6:2b:a3:1a` -> `.ROAMTEST_RSNO_P10P_1`, while same-target `iw` emitted no `IwSSID6g`, and a direct raw `wl -i wl1 escanresults | grep -m1 -B2 -A1 'BSSID: 3A:06:E6:2B:A3:1A'` probe also came back empty. The trial rewrite was therefore rejected, `D287` was reverted to its original generic shape with stale row `289`, and the next ready case in the current repo inventory is `D288`
- latest scan-case alignment after that: `D288 getScanResults() WPSConfigMethodsSupported` reran plain `Pass` at `20260410T183630583633`. Source survey had already shown 0403 still exposes `WPSConfigMethodsSupported` in the scan-result model while the neighboring scan live payload returns an empty-string shape on all three bands; the remaining gap was repo-side parsing, because the raw ubus transcript leaves empty strings as `WPSConfigMethodsSupported = "",` and `_extract_key_values()` does not capture that trailing-comma form. The committed case now uses an explicit extractor command to normalize each band to `WPSConfigMethodsSupported=`, the YAML row metadata is refreshed from stale row `290` to workbook row `288`, targeted D288 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready case in the current repo inventory is `D289`
- latest scan-case alignment after that: `D289 getScanResults() Radio` is now aligned as a source-backed fail-shaped absence. The active 0403 scan model `wld_radio.odl` `scanresult_t` does not define `Radio`, and the active HAL neighboring struct `wifi_neighbor_ap2_t` also comments out `ap_Radio`, so the live getter has no backing field to populate. The committed case now uses an explicit extractor command to normalize the missing member to `Radio=`, isolated rerun `20260410T185434305989` emitted `Radio=` on all three bands with `diagnostic_status=Pass`, the YAML row metadata is refreshed from stale row `291` to workbook row `289`, full plugin runtime regression remains `1223 passed`, and the next ready case in the current repo inventory is `D290`
- latest scan-case blocker after that: `D290 getScanResults() CentreChannel` could not be closed as a committed rewrite. Source-backed survey confirmed the field is real on 0403 (`wld_radio.odl` declares `CentreChannel`, `wld_rad_scan.c` copies `ssid->centreChannel`, and `wld_nl80211_parser.c` computes it through `swl_chanspec_getCentreChannel()` with a 20MHz fallback), and isolated rerun `20260410T190709112740` did prove live LLAPI values on all three bands (`42 / 31 / 3`). But the required same-target independent oracle would not close: 5G and 2.4G same-target `iw` replay only yielded `BSS + freq`, never a recoverable centre-channel value, while 6G produced no same-target `iw` block at all; the debug rerun `20260410T191029019821` confirmed the same gap. The trial rewrite was therefore rejected, `D290` was reverted to its original generic shape with stale row `292`, the blocker record lives in `plugins/wifi_llapi/reports/D290_block.md`, post-revert full plugin runtime regression remains `1223 passed`, and the next ready case in the current repo inventory is `D295`
- latest action-method alignment after that: `D295 scan()` is now aligned as a plain `Pass/Pass/Pass` row. The stale metadata is refreshed from row `220` to workbook row `295`, and live serialwrap replay on `COM0` proved all three radios are already `Enable=1` / `Status="Up"` before invocation. More importantly, each band now has a driver-backed oracle that closes without replaying the oversized full payload: `WiFi.Radio.1.scan()` returned and the first 5G BSSID `38:88:71:2F:F6:A7` matched `wl0 escanresults`, `WiFi.Radio.2.scan()` returned and the first 6G BSSID `6E:15:DB:9E:33:72` matched `wl1 escanresults`, and `WiFi.Radio.3.scan()` returned and the first 2.4G BSSID `2E:59:17:00:06:F8` matched `wl2 escanresults`. A direct post-scan `getScanResults()` follow-up did reproduce the old prompt-timeout risk on COM0, so the committed oracle stays on `scan() returned + same-target driver-cache match` rather than chaining a second oversized read. The next ready patch-driven workbook-Pass case in the current repo inventory is `D298`
- latest action-method alignment after that: `D298 startScan()` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_radio.odl`, which declares `startScan()` plus its error modes (`radio unavailable`, `scan already running`), and the 0403 live path in `wldm_lib_wifi.c` shows the method drives `wldm_xbrcm_scan(..., "scan")` before fetching `num_scan_results` and `scan_results`. Manual serialwrap replay on `COM0` now matches that contract on all three bands: `WiFi.Radio.1.startScan()` / `WiFi.Radio.2.startScan()` / `WiFi.Radio.3.startScan()` each returned `[ "" ]`, while the post-call driver cache stayed populated on every band (`wl0` first BSSID `A8:A2:37:4F:8C:5C`, `wl1` first BSSID `6E:15:DB:9E:33:72`, `wl2` first BSSID `62:82:FE:58:AC:B5`). The committed metadata is refreshed from stale row `223` to workbook row `298`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D299`
- latest action-method alignment after that: `D299 stopScan()` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_radio.odl` (`void stopScan()`), in `wld_rad_scan.c` where `_stopScan()` delegates to `wld_scan_stop(pR)`, and in `wld_scan_stop()` where the active scan path requires `wld_scan_isRunning()` before calling `pRad->pFA->mfn_wrad_stop_scan(pRad)`; the public nl80211 surface also exposes the abort path through `wld_rad_nl80211_abortScan()` / `wld_nl80211_abortScan(...)`. Live serialwrap replay on `COM0` then closed a source-backed state-bit oracle on all three bands using `WiFi.Radio.N.ScanResults.ScanInProgress`: 5G proved `0 -> startScan() -> 1 -> stopScan() -> 0` and a second restart loop returned to `1/0` again, while 6G and 2.4G each proved `0 -> 1 -> 0` with shorter per-band probes. One longer combined 6G+2.4G probe did hit `PROMPT_TIMEOUT_RECOVERED`, so the committed oracle deliberately stays on short per-band `startScan() -> ScanInProgress=1 -> stopScan() -> ScanInProgress=0` replays. The committed metadata is refreshed from stale row `224` to workbook row `299`, targeted D299 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D300`
- latest getSSIDStats alignment after that: `D300 getSSIDStats() BroadcastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, which exposes both `Stats.BroadcastPacketsReceived` and `htable getSSIDStats()`; `wld_ssid.c` then routes `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()`, where the 0403 `false && (pAP->status != APSTI_ENABLED)` fallback path keeps `wld_updateVAPStats(pAP, NULL)` live, and `wld_statsmon.c` fills `BroadcastPacketsReceived` from `rxBroadcastPackets`. Live serialwrap replay on `COM0` closed a three-way numeric oracle on every band: 5G matched `363 / 363 / 363`, 6G matched `144 / 144 / 144`, and 2.4G matched `113 / 113 / 113` across extracted `getSSIDStats()`, direct `WiFi.SSID.{i}.Stats.BroadcastPacketsReceived?`, and `/proc/net/dev_extstats` field `$23` for `wl0/wl1/wl2`. One longer all-band extraction probe did hit `PROMPT_TIMEOUT_RECOVERED`, so the committed oracle stays on short per-band probes. The committed metadata is refreshed from stale row `225` to workbook row `300`, targeted D300 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D301`
- latest getSSIDStats alignment after that: `D301 getSSIDStats() BroadcastPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, which exposes both `Stats.BroadcastPacketsSent` and `htable getSSIDStats()`; `wld_ssid.c` then routes `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()`, where the 0403 fallback path still keeps `wld_updateVAPStats(pAP, NULL)` live, and `wld_statsmon.c` fills `BroadcastPacketsSent` from `txBroadcastPackets`. Live serialwrap replay on `COM0` closed the matching three-way numeric oracle on every band: 5G matched `1432 / 1432 / 1432`, 6G matched `1590 / 1590 / 1590`, and 2.4G matched `1680 / 1680 / 1680` across extracted `getSSIDStats()`, direct `WiFi.SSID.{i}.Stats.BroadcastPacketsSent?`, and `/proc/net/dev_extstats` field `$24` for `wl0/wl1/wl2`. The committed metadata is refreshed from stale row `226` to workbook row `301`, targeted D301 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D302`
- latest getSSIDStats blocker after that: `D302 getSSIDStats() BytesReceived` could not be closed as a committed rewrite. Active 0403 source still shows this field is real (`wld_ssid.c` copies endpoint `rxbyte` into `pStats->BytesReceived`, while `wld_statsmon.c` also aggregates `pSrc->rxBytes` into the SSID stats path), and live replay did prove `direct Stats == getSSIDStats()` on all three bands (`139402/139402`, `43232/43232`, `33066/33066`, with a focused 5G rerun still at `139618/139618`). The old D323-style `/proc/net/dev[_extstats] $2` oracle is now confirmed stale, and a later vendor-path trace through `whm_brcm_vap_update_ap_stats()` / `whm_brcm_get_if_stats()` showed the current 0403 override actually reads `wl if_counters rxbyte`: that newer oracle closes exactly on 6G/2.4G and narrows 5G to a stable `+104` delta (`140482` getter vs `140378` `if_counters`). But because the independent oracle still does not close all three bands, promoting D302 would still fall back to an API-only close. The trial rewrite was therefore rejected, the committed YAML stays unchanged at stale row `227`, and the blocker record lives in `plugins/wifi_llapi/reports/D302_block.md`
- latest getSSIDStats blocker after that: `D303 getSSIDStats() BytesSent` also could not be closed as a committed rewrite. Active 0403 source still shows this field is real (`wld_ssid.c` copies endpoint `txbyte` into `pStats->BytesSent`, while `wld_statsmon.c` aggregates `pSrc->txBytes`), and live replay did partially close the method path: 5G and 2.4G held `direct Stats == getSSIDStats()` (`95452542` and `67883586`), while 6G first drifted slightly (`60438235` vs `60439059`) but a focused rerun re-closed at `60582625 / 60582625`. But every attempted independent oracle still drifted: `/proc/net/dev` and `/proc/net/dev_extstats` field `$10` stayed around `66798080 / 64667313 / 66738514` and `66750876 / 64691013 / 66691690`, `wl counters txbyte` stayed materially higher (`114950286 / 80944128 / 77082489`), sub-interface counters `wl0.1/wl1.1/wl2.1` were blank / zero-like, and `AssociatedDevice.*.TxBytes` also did not map cleanly. So the old D324-style proc oracle is currently stale for D303, and promoting this case now would again fall back to an API-only close. The trial rewrite was therefore rejected, the committed YAML stays unchanged at stale row `228`, the blocker record lives in `plugins/wifi_llapi/reports/D303_block.md`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D304`
- latest getSSIDStats alignment after that: `D304 getSSIDStats() DiscardPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `DiscardPacketsReceived` from `wl if_counters rxdiscard`. Live serialwrap replay on `COM0` then closed a three-way numeric oracle on every band: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters rxdiscard = 0 / 0 / 0`. The older D325-style `/proc/net/dev_extstats` field `$5` path stayed stale at `565 / 3752 / 356`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes rather than the proc-file heuristic. The committed metadata is refreshed from stale row `229` to workbook row `304`, targeted D304 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D305`
- latest getSSIDStats alignment after that: `D305 getSSIDStats() DiscardPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `DiscardPacketsSent` from `wl if_counters txdiscard`. Live serialwrap replay on `COM0` then closed the matching three-way numeric oracle on every band: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters txdiscard = 0 / 0 / 0`. The older D326-style `/proc/net/dev_extstats` field `$13` path stayed stale at `184 / 3467 / 87`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes rather than the proc-file heuristic. The committed metadata is refreshed from stale row `230` to workbook row `305`, targeted D305 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D306`
- latest getSSIDStats alignment after that: `D306 getSSIDStats() ErrorsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `ErrorsReceived` from `wl if_counters rxerror`. Live serialwrap replay on `COM0` then closed a four-way numeric oracle on every band: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters rxerror / /proc/net/dev_extstats $4 = 0 / 0 / 0 / 0`. The committed metadata is refreshed from stale row `231` to workbook row `306`, targeted D306 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D307`
- latest getSSIDStats alignment after that: `D307 getSSIDStats() ErrorsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds base-VAP `ErrorsSent` from `wl if_counters txerror` and `whm_brcm_vap_ap_stats_accu()` then accumulates matching `wds*` interface stats back into `SSID.stats`. Live serialwrap replay on `COM0` closed that source-backed oracle: 5G matched `direct/getSSIDStats/wds0.0.1 if_counters txerror = 56 / 56 / 56`, a focused 6G rerun matched `direct/getSSIDStats/wds1.0.1 if_counters txerror = 46 / 46 / 46`, and 2.4G held `direct/getSSIDStats/wl2 if_counters txerror = 0 / 0 / 0` with no matching WDS peer. The older D328-style `/proc/net/dev_extstats` field `$12` heuristic stayed at `0` on the base wl interfaces and is therefore stale for 5G/6G in the current 0403 baseline. The committed metadata is refreshed from stale row `232` to workbook row `307`, targeted D307 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D308`
- latest getSSIDStats alignment after that: `D308 getSSIDStats() FailedRetransCount` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` overwrites `FailedRetransCount` from `wl if_counters txretransfail`; if any matching `wds*` interface exists, the same `whm_brcm_vap_ap_stats_accu()` path would accumulate it, but the current live baseline stayed at zero. Live serialwrap replay on `COM0` then closed the matching three-way numeric oracle on every band: 5G, 6G, and 2.4G all matched `direct Stats / getSSIDStats() / wl if_counters txretransfail = 0 / 0 / 0`. The committed metadata is refreshed from stale row `233` to workbook row `308`, targeted D308 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D309`
- latest getSSIDStats alignment after that: `D309 getSSIDStats() MulticastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `MulticastPacketsReceived` from `wl if_counters rxmulti`, `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface stats, and `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsReceived` before clamping the field at zero. Live serialwrap replay on `COM0` closed that source-backed formula on every band: 5G matched `direct / getSSIDStats / wl0 if_counters rxmulti / BroadcastPacketsReceived = 0 / 0 / 10 / 363`, 6G matched `0 / 0 / 0 / 145`, and 2.4G matched `0 / 0 / 0 / 113`, so all three bands authoritatively land at `max((rxmulti + matching wds_rxmulti) - BroadcastPacketsReceived, 0) = 0`. The older D330-style `/proc/net/dev_extstats` field `$9` heuristic stayed stale at `363 / 146 / 113`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters + broadcast-subtraction` probes. The committed metadata is refreshed from stale row `234` to workbook row `309`, targeted D309 tests are `3 passed`, full plugin runtime regression remains `1223 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D310`
- latest getSSIDStats alignment after that: `D310 getSSIDStats() MulticastPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `MulticastPacketsSent` from `wl if_counters txmulti`, `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface stats, and `whm_brcm_vap.c` then subtracts `tmp_stats.BroadcastPacketsSent` before clamping the field at zero. Live serialwrap replay on `COM0` closed that source-backed formula on every band: 5G matched `direct / getSSIDStats / wl0 if_counters txmulti / BroadcastPacketsSent = 135098 / 135098 / 136632 / 1534`, 6G matched `76033 / 76033 / 77722 / 1689`, and 2.4G matched `150648 / 150648 / 152429 / 1781`, so all three bands authoritatively land at `max((txmulti + matching wds_txmulti) - BroadcastPacketsSent, 0)`. The older D331-style `/proc/net/dev_extstats` field `$18` heuristic stayed stale at `154277 / 148836 / 154585`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters + broadcast-subtraction` probes. The committed metadata is refreshed from stale row `235` to workbook row `310`, targeted D310 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D311`
- latest getSSIDStats alignment after that: `D311 getSSIDStats() PacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `PacketsReceived` from `wl if_counters rxframe` and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface packet counts before the final SSID stats snapshot is returned. Live serialwrap replay on `COM0` closed that source-backed oracle on every band: 5G matched `direct / getSSIDStats / wl0 if_counters rxframe / wds0.0.1 rxframe = 1082 / 1082 / 1080 / 2`, 6G matched `292 / 292 / 292 / 0`, and 2.4G matched `220 / 220 / 220 / 0`. The older D332-style `/proc/net/dev_extstats` field `$3` heuristic stayed stale at `1086 / 438 / 333`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters + WDS accumulation` probes. The committed metadata is refreshed from stale row `236` to workbook row `311`, targeted D311 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D312`
- latest getSSIDStats alignment after that: `D312 getSSIDStats() PacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` first seeds `PacketsSent` from `wl if_counters txframe` and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface packet counts before the final SSID stats snapshot is returned. Live serialwrap replay on `COM0` closed that source-backed oracle on every band: 5G matched `direct / getSSIDStats / wl0 if_counters txframe / wds0.0.1 txframe = 192311 / 192311 / 157138 / 35173`, 6G matched `91211 / 91211 / 89703 / 1510`, and 2.4G matched `156926 / 156926 / 156926 / 0`. The older D333-style `/proc/net/dev_extstats` field `$11` heuristic is no longer an all-band authority: 5G stayed at the base `wl0` counter `157138`, 6G drifted to `151237`, and only 2.4G still exact-closed because no matching WDS peer existed. The committed oracle therefore stays on short per-band `direct/getSSIDStats/if_counters + WDS accumulation` probes. The committed metadata is refreshed from stale row `237` to workbook row `312`, targeted D312 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D313`
- latest getSSIDStats alignment after that: `D313 getSSIDStats() RetransCount` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`, where `whm_brcm_get_if_stats()` seeds `RetransCount` from `wl if_counters txretrans` and `whm_brcm_vap_ap_stats_accu()` would accumulate matching `wds*` interface values when present. Live serialwrap replay on `COM0` closed that source-backed oracle on every band: 5G, 6G, and 2.4G all matched `direct / getSSIDStats / wl if_counters txretrans / matching wds txretrans = 0 / 0 / 0 / 0`. The adjacent D334 direct case already carries the same 0403 zero-shape comment (`direct Stats matched getSSIDStats(), but workbook v4.0.3 still remains To be tested`), so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters` probes rather than the stale wording. The committed metadata is refreshed from stale row `238` to workbook row `313`, targeted D313 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D314`
- latest getSSIDStats alignment after that: `D314 getSSIDStats() UnicastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` first seeds `PacketsReceived` from `wl if_counters rxframe`, seeds `MulticastPacketsReceived` from `wl if_counters rxmulti`, and derives `UnicastPacketsReceived = PacketsReceived - MulticastPacketsReceived` before `whm_brcm_vap.c` later subtracts broadcast packets from the visible multicast field only. Live serialwrap replay on `COM0` closed that source-backed oracle on every band: 5G matched `direct / getSSIDStats / wl0 if_counters rxframe / wl0 if_counters rxmulti / wds0.0.1 rxframe / wds0.0.1 rxmulti = 1084 / 1084 / 1092 / 10 / 2 / 0`, 6G matched `292 / 292 / 292 / 0 / 0 / 0`, and 2.4G matched `220 / 220 / 220 / 0 / 0 / 0`. The older D335-style `/proc/net/dev_extstats` field `$21` heuristic stayed stale at `360 / 146 / 107`, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/(rxframe + WDS rxframe) - (raw rxmulti + WDS rxmulti)` probes. The committed metadata is refreshed from stale row `239` to workbook row `314`, targeted D314 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D315`
- latest getSSIDStats alignment after that: `D315 getSSIDStats() UnicastPacketsSent` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` first seeds `PacketsSent` from `wl if_counters txframe`, seeds `MulticastPacketsSent` from `wl if_counters txmulti`, and derives `UnicastPacketsSent = PacketsSent - MulticastPacketsSent` before `whm_brcm_vap.c` later subtracts broadcast packets from the visible multicast field only. Live serialwrap replay on `COM0` closed that source-backed oracle on every band: the focused 5G rerun matched `direct / getSSIDStats / wl0 if_counters txframe / wl0 if_counters txmulti / wds0.0.1 txframe / wds0.0.1 txmulti = 55992 / 55992 / 159684 / 140207 / 36515 / 0`, 6G matched `13317 / 13317 / 92193 / 81711 / 2835 / 0`, and 2.4G matched `2338 / 2338 / 159419 / 157081 / 0 / 0`. The older D336-style `/proc/net/dev_extstats` field `$22` heuristic stayed stale at `0` on all three bands, so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/(txframe + WDS txframe) - (raw txmulti + WDS txmulti)` probes. The committed metadata is refreshed from stale row `240` to workbook row `315`, targeted D315 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D316`
- latest getSSIDStats alignment after that: `D316 getSSIDStats() UnknownProtoPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, and the active 0403 path again runs `_SSID_getSSIDStats()` through `s_updateSsidStatsValues()` into `whm_brcm_vap_update_ap_stats()`: `whm_brcm_get_if_stats()` seeds `UnknownProtoPacketsReceived` from `wl if_counters rxunknownprotopkts`, `whm_brcm_vap_copy_stats()` preserves that field for the base VAP snapshot, and `whm_brcm_vap_ap_stats_accu()` can accumulate matching `wds*` interface values before the final SSID stats snapshot is returned. Live serialwrap replay on `COM0` closed that source-backed oracle on every band: 5G matched `direct / getSSIDStats / wl0 if_counters rxunknownprotopkts / wds0.0.1 rxunknownprotopkts = 0 / 0 / 0 / 0`, 6G matched `0 / 0 / 0 / 0`, and 2.4G matched `0 / 0 / 0 / 0`. The adjacent D337 direct case still stays workbook-gated as `To be tested`, but its v4.0.3 comment already records the same multiband zero-shape (`direct Stats matched getSSIDStats()`), so the committed oracle deliberately stays on short per-band `direct/getSSIDStats/if_counters + WDS accumulation` probes. The committed metadata is refreshed from stale row `241` to workbook row `316`, targeted D316 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D317`
- latest SSID property alignment after that: `D317 BSSID` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, where `WiFi.SSID.{i}.BSSID` is exposed as a read-only SSID property, and `dm_info.c` still advertises the same `BSSID` field on the active `WiFi.SSID` object. Live serialwrap replay on `COM0` then closed the independent oracle on every band by matching the property against both interface views: 5G `ubus BSSID / iw dev wl0 info addr / wl -i wl0 cur_etheraddr = 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95`, 6G matched `2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96`, and 2.4G matched `2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7`. The workbook v4.0.3 comment already states the same `matching iw dev info` shape, so the committed oracle deliberately stays on short per-band `ubus BSSID -> iw dev info -> wl cur_etheraddr` probes. The committed metadata is refreshed from stale row `242` to workbook row `317`, targeted D317 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D319`
- latest SSID property alignment after that: `D319 MACAddress` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, where `WiFi.SSID.{i}.MACAddress` remains exposed as a read-only SSID property on the active object model. Live serialwrap replay on `COM0` then closed a four-way independent oracle on every band by matching the property against three interface views: 5G `ubus MACAddress / iw dev wl0 info addr / ifconfig wl0 HWaddr / wl -i wl0 cur_etheraddr = 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95 / 2c:59:17:00:19:95`, 6G matched `2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96 / 2c:59:17:00:19:96`, and 2.4G matched `2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7 / 2c:59:17:00:19:a7`. The committed oracle therefore stays on short per-band `ubus MACAddress -> iw dev info -> ifconfig -> wl cur_etheraddr` probes. The committed metadata is refreshed from stale row `321` to workbook row `319`, targeted D319 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D320`
- latest SSID property alignment after that: `D320 SSID` is now aligned as a plain `Pass/Pass/Pass` row. Source-backed support is explicit in `wld_ssid.odl`, where `WiFi.SSID.{i}.SSID` remains exposed as a read-only SSID property on the active object model. Live serialwrap replay on `COM0` then closed the independent oracle on every band by matching the getter against the driver SSID view: 5G `ubus SSID / wl -i wl0 ssid = testpilot5G / testpilot5G`, 6G matched `testpilot6G / testpilot6G`, and 2.4G matched `testpilot2G / testpilot2G`. The committed oracle therefore stays on short per-band `ubus SSID -> wl ssid` probes. The committed metadata is refreshed from stale row `322` to workbook row `320`, targeted D320 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D321`
- latest SSID stats direct-property alignment after that: `D321 BroadcastPacketsReceived` is now aligned as a plain `Pass/Pass/Pass` row. Active 0403 source-backed support is already consistent with the previously closed D300 family, and live serialwrap replay on `COM0` closed the full three-way direct-property oracle on every band: 5G `direct Stats / getSSIDStats / /proc/net/dev_extstats $23 = 363 / 363 / 363`, 6G matched `147 / 147 / 147`, and 2.4G matched `113 / 113 / 113`. The committed oracle therefore stays on short per-band `Stats.BroadcastPacketsReceived -> getSSIDStats().BroadcastPacketsReceived -> /proc $23` probes instead of the older noisy multi-step traffic procedure. The committed metadata is refreshed from stale row `245` to workbook row `321`, targeted D321 tests are `3 passed`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D322`
- latest direct-stats runner revalidation after that: the authored `getSSIDStats()` shell pipelines for `D321/D322` are now preserved instead of being overwritten by synthesized plain readback queries, and the full repo regression is green at `1634 passed`. With that resolver fix in place, live rerun `20260411T002336420469` proved `D321 BroadcastPacketsReceived` really passes in the runner as-authored (`364/364/364`, `149/149/149`, `113/113/113` across direct/getSSIDStats//proc), while sibling `D322 BroadcastPacketsSent` remains blocked: both attempts exact-closed `direct == getSSIDStats()` on all bands, but 5G kept drifting at `direct / getSSIDStats / /proc $24 = 1644 / 1644 / 1645` then `1647 / 1647 / 1648`. Active 0403 source also shows `whm_brcm_vap_update_ap_stats()` restores the final public `BroadcastPacketsSent` from `tmp_stats`, so the current `/proc $24` equality is still treated as a stale heuristic rather than a committed oracle. The blocker handoff now lives in `plugins/wifi_llapi/reports/D322_block.md`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D323`
- latest direct-stats runner revalidation after that: `D323 BytesReceived` must also stay blocked. A real runner rerun (`20260411T004129362633`) now proves the authored `getSSIDStats()` pipeline executes correctly and `direct == getSSIDStats()` exact-closes on all three bands, but the old `/proc/net/dev_extstats` `$2` oracle still drifts everywhere: 5G `149042/149042/112186` then `149318/149318/112482`, 6G `46082/46082/49162` then `46652/46652/49772`, and 2.4G `33066/33066/35326` on both attempts. Active 0403 source again shows `whm_brcm_vap_update_ap_stats()` restores the final public `BytesReceived` from `tmp_stats`, so this direct-property row inherits the same stale-oracle problem already proven in `D302`. The blocker handoff now lives in `plugins/wifi_llapi/reports/D323_block.md`, and the next ready patch-driven workbook-Pass case in the current repo inventory is `D324`
### System Architecture

```mermaid
graph TB
    subgraph User["User"]
        cli["Terminal / CLI"]
    end

    subgraph CP["Copilot SDK Control Plane"]
        sdk["SDK Client<br/>create / resume / delete"]
        hooks["Hooks<br/>on_session_start / on_pre_tool_use<br/>on_post_tool_use / on_error_occurred"]
        agents["Custom Agents<br/>operator / case-auditor<br/>remediation-planner / run-summarizer"]
        skills["Skills<br/>wifi diagnostics / remediation policy"]
        mcp["Selective MCP<br/>GitHub / KB / lab inventory"]
    end

    subgraph Kernel["Deterministic Verdict Kernel"]
        orch["Orchestrator<br/>case loop / retry / timeout / trace"]
        cfg["TestbedConfig + CaseSchema"]
        plugin["Plugin Hooks<br/>setup_env / verify_env<br/>execute_step / evaluate / teardown"]
        yaml["YAML Cases"]
        transport["Transport<br/>serialwrap / adb / ssh / network"]
        evidence["Evidence Store<br/>selection trace / attempts / canonical result"]
        report["Report Projection<br/>xlsx / md / json"]
    end

    cli --> sdk
    cli --> orch

    sdk --> hooks
    sdk --> agents
    sdk --> skills
    sdk --> mcp

    orch --> cfg
    orch --> plugin
    plugin --> yaml
    plugin --> transport
    orch --> evidence
    evidence --> report

    agents -.-> evidence
    agents -.-> report
```

### Test Execution Flow

```mermaid
flowchart TD
    START([cli run plugin_name]) --> LOAD[PluginLoader.load]
    LOAD --> DISCOVER[plugin.discover_cases]
    DISCOVER --> FILTER{--case filter?}
    FILTER -->|Yes| SUBSET[Filter matching cases]
    FILTER -->|No| ALL[All discoverable cases]
    SUBSET --> LOOP
    ALL --> LOOP

    LOOP[For each case in queue] --> SELECT[RunnerSelector: resolve agent/model]
    SELECT --> SESSION[CopilotSession: create per-case session]
    SESSION --> SETUP[plugin.setup_env]
    SETUP -->|fail| RECORD_FAIL[Record verdict=Fail]
    SETUP -->|ok| VERIFY[plugin.verify_env]
    VERIFY -->|fail| RECORD_FAIL
    VERIFY -->|ok| STEPS

    subgraph STEPS["Execute Steps"]
        STEP_LOOP[For each step in case.steps] --> EXEC[plugin.execute_step]
        EXEC --> CAPTURE[Capture output + timing]
        CAPTURE --> STEP_OK{step success?}
        STEP_OK -->|Yes| STEP_LOOP
        STEP_OK -->|No| STEP_FAIL[Break with comment]
    end

    STEPS --> EVAL[plugin.evaluate]
    EVAL --> TEARDOWN[plugin.teardown]
    TEARDOWN --> WRITE_EVIDENCE[Write to Evidence Store]
    WRITE_EVIDENCE --> WRITE_XLSX[Fill xlsx report row]
    WRITE_XLSX --> NEXT{more cases?}
    RECORD_FAIL --> TEARDOWN
    STEP_FAIL --> EVAL

    NEXT -->|Yes| RETRY{retry policy?}
    NEXT -->|No| DONE([Generate final report])
    RETRY -->|retry| LOOP
    RETRY -->|continue| LOOP
```

### Creating a New Plugin

1. Copy the template: `cp -r plugins/_template plugins/my_plugin`
2. Edit `plugins/my_plugin/plugin.py` — implement `name`, `discover_cases()`, `execute_step()`, `evaluate()`
3. Add YAML test cases to `plugins/my_plugin/cases/`
4. Verify: `testpilot list-plugins` → `testpilot list-cases my_plugin`

See the [Plugin Development Guide](docs/plugin-dev-guide.md) for full details.

### Agent / Model Policy

1. Priority 1: `copilot + gpt-5.4 + high`
2. Priority 2: `copilot + sonnet-4.6 + high`
3. Priority 3: `copilot + gpt-5-mini + high`
4. Execution mode: `per_case + sequential (max_concurrency=1)`
5. Failure policy: `retry_then_fail_and_continue`, timeout scales with retry attempts
6. Auto-downgrade when top priority is unavailable, with `selection trace` preserved

### Project Structure

```text
testpilot/
├── README.md
├── AGENTS.md
├── scripts/
│   └── install.sh               # One-click install script
├── docs/
│   ├── plan.md                  # Master plan
│   ├── spec.md                  # System spec + architecture diagrams
│   ├── todos.md                 # Single source of truth for todos
│   ├── audit-guide.md           # Calibration guide
│   └── audit-todo.md            # Calibration handoff tracker
├── src/testpilot/
│   ├── cli.py                   # CLI entry point (Click)
│   ├── core/
│   │   ├── azure_auth.py        # Azure OpenAI BYOK auth
│   │   ├── orchestrator.py      # Thin facade
│   │   ├── copilot_session.py   # SDK session manager
│   │   ├── plugin_base.py       # PluginBase (abstract)
│   │   └── plugin_loader.py     # sys.path-safe loader
│   ├── reporting/               # xlsx / md / json reporters
│   └── transport/               # serialwrap / adb / ssh / network
├── plugins/
│   ├── _template/               # Plugin skeleton
│   └── wifi_llapi/              # 420 official YAML cases
├── configs/
│   └── testbed.yaml.example
└── tests/                       # Engine tests
```

### Development & Testing

```bash
uv pip install -e ".[dev]"    # Install (first time only)
uv run pytest -q              # Run full test suite (currently 1600 tests)
```

### License

MIT

---

## 繁體中文

plugin-based 嵌入式裝置測試自動化框架（prplOS / OpenWrt）。

### 概述

TestPilot 是一套 plugin-based 嵌入式裝置測試自動化框架，面向 prplOS / OpenWrt 裝置。系統架構分為兩個平面：

- **Deterministic verdict kernel**：負責測試執行、證據蒐集、pass/fail 判定與報表投影
- **Copilot SDK control plane**：負責 session 管理、custom agents、advisory audit、hook-governed safe remediation

核心原則：**Copilot SDK 負責 control plane，不負責最終 verdict**。

`wifi_llapi` 目前已支援 retry attempt 之間的 in-run safe remediation；範圍只限環境修復：serial session recover、STA reconnect、band baseline rebuild、env re-verify，不會改寫 YAML semantics、step 指令或 pass criteria。

### 環境需求

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Python 套件管理工具
- **[serialwrap](https://github.com/paulc-arc/serialwrap)** — DUT / STA UART 通訊用序列埠多工器

安裝 serialwrap 後，透過環境變數指定路徑：

```bash
export SERIALWRAP_BIN=/path/to/serialwrap
```

或在 `configs/testbed.yaml` 中設定：

```yaml
testbed:
  serialwrap_binary: /path/to/serialwrap
```

> 解析優先序：`SERIALWRAP_BIN` 環境變數 → `testbed.yaml` 設定 → 錯誤結束。

### 快速開始

```bash
uv pip install -e ".[dev]"                              # 安裝
cp configs/testbed.yaml.example configs/testbed.yaml    # 首次設定
testpilot list-cases wifi_llapi                         # 驗證
testpilot run wifi_llapi --dut-fw-ver BGW720-B0-403     # 執行
```

### CLI 入口

可使用安裝後的 `testpilot` 指令，或直接用 Python module 入口。

`run` 指令格式為 `testpilot run PLUGIN_NAME [--case CASE_ID] [--dut-fw-ver FW_VER]`。由於 TestPilot 是多 plugin 架構，`PLUGIN_NAME` 為必填參數。

```bash
testpilot --version
python -m testpilot.cli --version
python -m testpilot.cli list-plugins
python -m testpilot.cli list-cases wifi_llapi
python -m testpilot.cli wifi-llapi baseline-qualify --band 5g
python -m testpilot.cli run wifi_llapi --case wifi-llapi-D004-kickstation
```

### 認證方式

TestPilot 支援兩種 LLM backend，認證順序如下：

| 優先序 | 方式 | 啟用方法 |
|--------|------|----------|
| 1 | **Azure OpenAI (BYOK)** | `testpilot --azure run wifi_llapi`（互動式詢問） |
| 2 | **Azure OpenAI (環境變數)** | 設定 `COPILOT_PROVIDER_*` 環境變數（見下方） |
| 3 | **GitHub Copilot OAuth** | 預設行為，不需額外參數 |

所有方式皆失敗時，程式會顯示錯誤訊息後結束。

#### Azure OpenAI 設定

**方法 A：互動式詢問（`--azure` 參數）**

```bash
testpilot --azure run wifi_llapi --dut-fw-ver BGW720-B0-403
```

系統會依序詢問：
1. **Azure Endpoint URL** — 例如 `https://your-resource.openai.azure.com`
2. **Azure API Key** — 你的 Azure OpenAI 金鑰（隱藏輸入）
3. **Deployment Name** — 例如 `gpt-4o`（Azure model 部署名稱）

**方法 B：環境變數**

```bash
export COPILOT_PROVIDER_TYPE=azure
export COPILOT_PROVIDER_BASE_URL=https://your-resource.openai.azure.com
export COPILOT_PROVIDER_API_KEY=your-api-key-here
export COPILOT_MODEL=gpt-4o
# 可選（預設：2024-10-21）：
export COPILOT_PROVIDER_AZURE_API_VERSION=2024-10-21

testpilot run wifi_llapi --dut-fw-ver BGW720-B0-403
```

> **提示：** 將 `export` 行加入 shell profile（`~/.bashrc`、`~/.zshrc`），即可免去每次加 `--azure`。

> **安全性：** 不要將 API key 提交至版本控制。使用環境變數或 `.env` 檔案（已加入 `.gitignore`）。

#### GitHub Copilot OAuth（預設）

若未偵測到 Azure 認證資訊，TestPilot 會自動透過 Copilot SDK 走 GitHub Copilot OAuth。已有 GitHub Copilot 存取權限者無需額外設定。

### 執行測試

```bash
# full run 前先做 DUT/STA baseline qualification
testpilot wifi-llapi baseline-qualify \
  --repeat-count 5 \
  --soak-minutes 15

# 單一 case（smoke test）
testpilot run wifi_llapi \
  --case wifi-llapi-D004-kickstation \
  --dut-fw-ver BGW720-B0-403

# 全量執行（420 筆 discoverable 官方案例）
testpilot run wifi_llapi --dut-fw-ver BGW720-B0-403

# 以 0401.xlsx 重新產生 compare 報告（疊加已完成的 live overlay）
python scripts/compare_0401_answers.py \
  20260401T152827516151 \
  20260401T230006391661 \
  20260401T232631531561 \
  20260402T013838223177 \
  20260402T020432759837 \
  20260402T021317975166 \
  20260402T021716841976 \
  20260402T023927691290 \
  20260402T030604339596 \
  20260402T034832813249 \
  20260402T040807394935 \
  20260402T051006378317 \
  20260402T054957340010 \
  20260402T060543524189 \
  20260402T063003376730 \
  20260402T071356233843 \
  20260402T095404127199 \
  20260402T105808547293 \
  --output-md compare-0401.md \
  --output-json compare-0401.json

# 使用 Azure OpenAI
testpilot --azure run wifi_llapi --dut-fw-ver BGW720-B0-403
```

### 報告產出

| 軌道 | 格式 | 用途 |
|------|------|------|
| 對外交付 | `xlsx` | Pass / Fail only，寫入 Excel 報告 |
| 內部診斷 | `md` | 人可讀摘要，含 per-case 指令、輸出、log 行號引用與 diagnostic status |
| 結構化資料 | `json` | 機器可讀，含 summary 統計、diagnostic status、remediation history 與 log 行號 |
| UART RAW log | `DUT.log` / `STA.log` | serialwrap WAL 解碼，per-run DUT/STA 原始 UART 通訊記錄 |

輸出位置：`plugins/wifi_llapi/reports/`

目前 workbook 校正活動的 repo-root 產物：

- `compare-0401.md`
- `compare-0401.json`
- answer authority：`0401.xlsx`
- baseline experiment authority：`docs/wifi-baseline-exp.md`
- current lab readiness status：multi-band baseline qualification 已完成（`5G/6G/2.4G` 全部通過 `baseline-qualify --repeat-count 5 --soak-minutes 15`）；後續 custom 6G hardening 已讓 `D019/D027` 在 clean-start rerun 變成 plain `Pass`，舊的 `D032 sta_band_not_ready` 環境失敗也已消失。clean-start dual-`firstboot` rerun `20260409T182347586948` 已先清掉最後已知的 `D028-D033` 冷開機 blocker；更後面的 dual-`firstboot` rerun `20260409T205434740233` 再把 `D004/D005` 維持為 plain `Pass`、把 `D006` 收斂成 `pass after retry (2/2)`，因此舊的 `D005/D006 FailEnv` prefix 已不再重現。目前 detached full-run compare baseline 已更新為 `run_id=20260411T074146043202`；較早的 `20260409T213837737224` 僅保留作歷史證據
- latest targeted checkpoint：6G OCV hot path 現在改成 stabilization loop：每輪都會重新 patch `ocv=0`、重啟 wl1 hostapd，並把 `ocv/socket/bss` 三個訊號一起短窗口驗證後才放行。這個修正的回歸結果為：targeted tests `5 passed`、plugin runtime `1222 passed`、full suite `1627 passed`
- latest calibration checkpoint：workbook replay 與 source-backed triage 已證明 `D111 getStationStats() AssociationTime` 的失敗根因是 repo 端解析把 `AssociationTime = "YYYY-MM-DDTHH:MM:SSZ",` 留下多餘尾端 `"`；修正 `_extract_key_values()` 的處理順序後，live 單案 rerun `20260410T110659169758` 已變成 plain `Pass`，targeted parser/D111 tests 為 `4 passed`，完整 plugin runtime regression 為 `1223 passed`
- latest spectrum follow-up：`D532 getSpectrumInfo ourUsage` 與 `D533 getSpectrumInfo availability` 已在 isolated rerun `20260411T183356920330` / `20260411T183405281629` 重新驗成 plain `Pass`。0403 active source 仍分別經 `_getSpectrumInfo()` -> `s_prepareSpectrumOutputWithChanFilter()` serialize 這兩個欄位，並由 `wld_rad_nl80211_updateUsageStatsFromSurveyInfo()` 以 survey airtime 衍生 `ourUsage` 與 `availability`，因此先前 workbook-era 的 fail-shaped carry-over 已確認是 stale `results_reference`
- latest compare checkpoint：以 current local YAML overlay 重新對 detached full run `20260411T074146043202` 執行 compare 後，快照已更新為 `220 / 420 full matches`、`200 mismatches`、`67 metadata drifts`；若改用 `evaluation_verdict` 解讀真正 workbook-Pass 缺口，尚有 `77` 個 cases 未收斂，其中 patch-scope true-open set 為 `D277`、`D281-D287`、`D290`、`D295`、`D322-D324`、`D330-D333`、`D335-D336`
- latest runtime blocker follow-up：`D295 scan()` 雖然先前曾以 `scan() returned + same-target driver-cache match` 對齊，但最新 isolated rerun `20260411T183430680092` 又在 `setup_env` 後掛住、沒有 step output，因此這一案目前必須回到 runtime-hang triage，而不能繼續視為已完全關閉

### 系統架構

```mermaid
graph TB
    subgraph User["使用者"]
        cli["Terminal / CLI"]
    end

    subgraph CP["Copilot SDK Control Plane"]
        sdk["SDK Client<br/>create / resume / delete"]
        hooks["Hooks<br/>on_session_start / on_pre_tool_use<br/>on_post_tool_use / on_error_occurred"]
        agents["Custom Agents<br/>operator / case-auditor<br/>remediation-planner / run-summarizer"]
        skills["Skills<br/>wifi diagnostics / remediation policy"]
        mcp["Selective MCP<br/>GitHub / KB / lab inventory"]
    end

    subgraph Kernel["Deterministic Verdict Kernel"]
        orch["Orchestrator<br/>case loop / retry / timeout / trace"]
        cfg["TestbedConfig + CaseSchema"]
        plugin["Plugin Hooks<br/>setup_env / verify_env<br/>execute_step / evaluate / teardown"]
        yaml["YAML Cases"]
        transport["Transport<br/>serialwrap / adb / ssh / network"]
        evidence["Evidence Store<br/>selection trace / attempts / canonical result"]
        report["Report Projection<br/>xlsx / md / json"]
    end

    cli --> sdk
    cli --> orch

    sdk --> hooks
    sdk --> agents
    sdk --> skills
    sdk --> mcp

    orch --> cfg
    orch --> plugin
    plugin --> yaml
    plugin --> transport
    orch --> evidence
    evidence --> report

    agents -.-> evidence
    agents -.-> report
```

### 測試流程圖

```mermaid
flowchart TD
    START([cli run plugin_name]) --> LOAD[PluginLoader.load]
    LOAD --> DISCOVER[plugin.discover_cases]
    DISCOVER --> FILTER{--case filter?}
    FILTER -->|Yes| SUBSET[Filter matching cases]
    FILTER -->|No| ALL[All discoverable cases]
    SUBSET --> LOOP
    ALL --> LOOP

    LOOP[For each case in queue] --> SELECT[RunnerSelector: resolve agent/model]
    SELECT --> SESSION[CopilotSession: create per-case session]
    SESSION --> SETUP[plugin.setup_env]
    SETUP -->|fail| RECORD_FAIL[Record verdict=Fail]
    SETUP -->|ok| VERIFY[plugin.verify_env]
    VERIFY -->|fail| RECORD_FAIL
    VERIFY -->|ok| STEPS

    subgraph STEPS["Execute Steps"]
        STEP_LOOP[For each step in case.steps] --> EXEC[plugin.execute_step]
        EXEC --> CAPTURE[Capture output + timing]
        CAPTURE --> STEP_OK{step success?}
        STEP_OK -->|Yes| STEP_LOOP
        STEP_OK -->|No| STEP_FAIL[Break with comment]
    end

    STEPS --> EVAL[plugin.evaluate]
    EVAL --> TEARDOWN[plugin.teardown]
    TEARDOWN --> WRITE_EVIDENCE[Write to Evidence Store]
    WRITE_EVIDENCE --> WRITE_XLSX[Fill xlsx report row]
    WRITE_XLSX --> NEXT{more cases?}
    RECORD_FAIL --> TEARDOWN
    STEP_FAIL --> EVAL

    NEXT -->|Yes| RETRY{retry policy?}
    NEXT -->|No| DONE([Generate final report])
    RETRY -->|retry| LOOP
    RETRY -->|continue| LOOP
```

### 建立新 Plugin

1. 複製 template：`cp -r plugins/_template plugins/my_plugin`
2. 編輯 `plugins/my_plugin/plugin.py` — 實作 `name`、`discover_cases()`、`execute_step()`、`evaluate()`
3. 在 `plugins/my_plugin/cases/` 新增 YAML 測試案例
4. 驗證：`testpilot list-plugins` → `testpilot list-cases my_plugin`

詳細說明請參考 [Plugin 開發指南](docs/plugin-dev-guide.md)。

### Agent / Model 策略

1. 第一優先：`copilot + gpt-5.4 + high`
2. 第二優先：`copilot + sonnet-4.6 + high`
3. 第三優先：`copilot + gpt-5-mini + high`
4. 執行模式：`per_case + sequential(max_concurrency=1)`
5. 失敗策略：`retry_then_fail_and_continue`，timeout 隨 retry attempt 調整
6. 第一優先不可用時可自動降級，保留 `selection trace`

### 專案結構

```text
testpilot/
├── README.md
├── AGENTS.md
├── scripts/
│   └── install.sh               # 一鍵安裝腳本
├── docs/
│   ├── plan.md                  # 主計畫
│   ├── spec.md                  # 系統規格 + 架構圖
│   ├── todos.md                 # 唯一待辦看板
│   ├── audit-guide.md           # 校正指南
│   └── audit-todo.md            # 校正交接追蹤
├── src/testpilot/
│   ├── cli.py                   # CLI 入口（Click）
│   ├── core/
│   │   ├── azure_auth.py        # Azure OpenAI BYOK 認證
│   │   ├── orchestrator.py      # 薄 facade
│   │   ├── copilot_session.py   # SDK session 管理
│   │   ├── plugin_base.py       # PluginBase（抽象基類）
│   │   └── plugin_loader.py     # sys.path-safe loader
│   ├── reporting/               # xlsx / md / json reporters
│   └── transport/               # serialwrap / adb / ssh / network
├── plugins/
│   ├── _template/               # Plugin 骨架
│   └── wifi_llapi/              # 420 筆 official YAML cases
├── configs/
│   └── testbed.yaml.example
└── tests/                       # 引擎核心測試
```

### 開發與測試

```bash
uv pip install -e ".[dev]"    # 安裝（僅首次）
uv run pytest -q              # 執行全部測試（目前 1600 筆）
```

### 授權

MIT
