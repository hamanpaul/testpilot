# D181 FragmentationThreshold blocker

## Status

- case: `D181 Radio.FragmentationThreshold`
- workbook row: `181`
- current state: **blocked as the same shared DUT+STA 6G baseline bring-up failure already exposed by D179**
- next ready non-blocked compare-open case: `D190 Radio.ExplicitBeamFormingEnabled`

## Why this is blocked

Workbook row `181` is a setter family row, not a bare tri-band getter. The trial rewrite therefore moved toward workbook-faithful `DUT + STA` replay: per-band STA association, baseline getter `-1`, setter `1500`, traffic trigger, direct getter + `wl fragthresh` equality, then restore to `-1`.

That rewritten shape was intentionally **not** left landed in the repo because the live trial never produced authoritative step-level proof. The clean-start rerun started as `20260414T111023418516`, but it never reached the D181 case-step phase: `verify_env` kept failing in the shared 6G recovery path, so the run stopped before any final FragmentationThreshold evidence was captured.

## Trial rerun evidence

### 1. The current blocker is environment, not settled row semantics

The repeated shell evidence during the stopped rerun was:

```text
verify_env: d181-radio-fragmentationthreshold bss[1] not ready yet (down), retrying...
sta_baseline_bss[1] not ready after 60s cmd=wl -i wl1 bss
STA band baseline/connect failed
6G restart attempt=1 unstable (pre_ocv=True post_ocv=True socket=False process=True bss=False), retrying
6G restart attempt=2 unstable (pre_ocv=True post_ocv=False socket=False process=True bss=False), retrying
6G restart attempt=3 unstable (pre_ocv=True post_ocv=False socket=False process=True bss=False), retrying
6G ocv fix did not stabilize wl1 after retries
```

These are the same 6G baseline symptoms already seen in the clean-start `D179` blocker path: `wl1 bss` does not stay up long enough for the STA 6G baseline to settle, so the case never reaches setter/readback execution.

### 2. The rerun did not become an authoritative closure artifact

- partial xlsx only:
  - `plugins/wifi_llapi/reports/20260414_BGW720-0403_wifi_LLAPI_20260414T111023418516.xlsx`
- no report markdown/json was emitted for run `20260414T111023418516`
- `plugins/wifi_llapi/reports/agent_trace/20260414T111023418516/` exists but is empty

Because the run died during environment recovery, this is blocker evidence only. It is not a valid workbook closure for row `181`.

## Why the rewrite was rolled back

The repo calibration rule is explicit: only update YAML after the live result matches the workbook baseline. Since rerun `20260414T111023418516` never reached a valid tri-band setter/readback result, the provisional `DUT + STA` setter rewrite for `D181` was rolled back, and the sibling `D182 Radio.RtsThreshold` trial rewrite was not carried forward either.

## Required follow-up

1. Stabilize the shared 6G `DUT + STA` baseline outside the case loop until `wl1 bss` stays up and STA 6G reconnects cleanly after the current OCV repair path.
2. Re-run `D181` with the active STA baseline intact and capture real per-band setter/readback/restore evidence.
3. Only after `D181` reaches authoritative step-level evidence should `D182` be retried, because it depends on the same tri-band STA baseline path.
