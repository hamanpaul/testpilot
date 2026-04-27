# wifi_llapi case YAML syntax

## Purpose and scope

This document is the reference for `plugins/wifi_llapi/cases/*.yaml` and the Wave 1 counter-delta extension.
It describes the syntax used by discoverable official `wifi_llapi` cases, the validation rules enforced today, and the new delta-oriented `pass_criteria` shape.
It is not a migration guide and does not cover sample-case rollout planning.

## Discovery and file-level rules

- Discoverable official cases live under `plugins/wifi_llapi/cases/`.
- `load_cases_dir()` loads `*.yaml` / `*.yml` and skips files whose stem starts with `_`.
- Use `_*.yaml` only for fixtures, templates, or legacy compatibility artifacts.
- `wifi_llapi` cases must not use removed oracle metadata:
  - top-level `results_reference`
  - `source.baseline`
  - `source.report`
  - `source.sheet`

## Top-level field reference

### Required by schema

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Case identifier. Official inventory uses `wifi-llapi-D###-...` or legacy `d###-...` forms. |
| `name` | string | Human-readable case name. |
| `topology` | mapping | Must contain `topology.devices`. |
| `steps` | list[mapping] | Non-empty ordered step list. |
| `pass_criteria` | list[mapping] | Non-empty verdict rule list. |

### Optional fields used by current official cases

| Field | Type | Notes |
| --- | --- | --- |
| `source` | mapping | Official cases use `source.row`, `source.object`, and `source.api`. Runtime alignment uses `(source.object, source.api)` as the canonical lookup key and may rewrite `source.row` / `id`. |
| `llapi_support` | string | `Support`, `Not Supported`, `Skip`, or `Blocked`. See [llapi_support semantics](#llapi_support-semantics). |
| `bands` | list[string] | Usually `5g`, `6g`, `2.4g`. Prefer canonical spellings in YAML. |
| `verification_command` | string or list[string] | Human-readable audit / cross-check command list. |
| `test_environment` | string | Human-readable lab context. |
| `implemented_by` | string | Implementation ownership marker such as `pWHM` or `N/A`. |
| `version` | string | Case revision string. |
| `platform` | mapping | Commonly `platform.prplos` and `platform.bdk`. |
| `hlapi_command` | string | HLAPI command under test. |
| `test_procedure` | string | Human-readable execution summary. |
| `setup_steps` | string | Human-readable setup summary. |
| `sta_env_setup` | string | Executable or semi-structured DUT/STA environment setup notes. |
| `aliases` | list[string] | Legacy compatibility names. Do not rely on row-derived aliases as the source of truth; `source.row` is the row reference. |

### Topology structure

`topology` is a mapping with at least:

- `devices` (required): non-empty mapping of device name to device config
- `links` (optional): link inventory used by human readers and some workflows

Current `wifi_llapi` cases typically use device names such as `DUT` and `STA`, with fields like `role`, `transport`, and `selector`.

## Step field reference

### Required step fields

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique within the case. |
| `action` | string | Current case inventory uses `exec`, `read`, `wait`, and `skip`. |
| `target` | string | Usually a key from `topology.devices`, such as `DUT` or `STA`. |

### Optional step fields

| Field | Type | Notes |
| --- | --- | --- |
| `command` | string or list[string] | Must be a string or a non-empty list of non-empty strings when present. |
| `capture` | string | Capture name exposed to later step templating and `pass_criteria` field paths. |
| `depends_on` | string | Must reference an earlier step `id`. |
| `description` | string | Human-readable step purpose. |
| `expected` | string | Human-readable expectation; currently descriptive only. |
| `band` | string | Commonly `5g`, `6g`, or `2.4g`. |
| `reason` | string | Freeform rationale or blocker note. |
| `duration` | number | Used by `action: wait`. |
| `phase` | string | Wave 1 field for delta-aware cases: `baseline`, `trigger`, or `verify`. Optional; default is `verify`. |

### Step action notes

| `action` | Execution expectation |
| --- | --- |
| `exec` | Execute the command and optionally capture parsed output. |
| `read` | Same runtime path as `exec`; use when the step is semantically a readback/probe. |
| `wait` | Sleep for `duration` seconds; no shell command is required. |
| `skip` | Do not execute a real test command; runtime returns a synthetic skip echo. |

## pass_criteria shapes

`pass_criteria` is an ordered non-empty list. Each entry is a mapping.

### 1. `field + value`

Use this shape for direct comparison against a literal value.

```yaml
pass_criteria:
  - field: result.Enable
    operator: equals
    value: "1"
```

Supported companion fields:

- `description` (optional)
- `band` (optional)

### 2. `field + reference`

Use this shape when the expected value comes from another captured field.

```yaml
pass_criteria:
  - field: after_5g.DisassociationTime
    operator: !=
    reference: before_5g.DisassociationTime
```

Supported companion fields:

- `description` (optional)
- `band` (optional)

### 3. `delta` with optional `reference_delta`

Use this shape for counter-style validation across phases.

```yaml
pass_criteria:
  - delta:
      baseline: baseline_api.BytesSent
      verify: verify_api.BytesSent
    operator: delta_nonzero
```

```yaml
pass_criteria:
  - delta:
      baseline: baseline_api.PacketsSent
      verify: verify_api.PacketsSent
    reference_delta:
      baseline: baseline_drv.DriverPacketsSent
      verify: verify_drv.DriverPacketsSent
    operator: delta_match
    tolerance_pct: 10
```

Supported companion fields:

- `description` (optional)
- `band` (optional)
- `tolerance_pct` (optional number, `delta_match` only; defaults to `0`)

Rules:

- `delta.baseline` and `delta.verify` must be non-empty field paths.
- `reference_delta` is required for `delta_match` and omitted for `delta_nonzero`.
- Delta evaluation is numeric at runtime. Non-numeric endpoint values fail the case.
- Delta cases require valid `phase` ordering in `steps`. See [schema validation rules](#schema-validation-rules).

## Operator reference

### Canonical operators for case authors

| Operator | Shape | Meaning |
| --- | --- | --- |
| `equals` | `field + value` or `field + reference` | Equality check. |
| `!=` | `field + value` or `field + reference` | Inequality check. |
| `contains` | `field + value` | Expected substring must appear. |
| `not_contains` | `field + value` | Expected substring must not appear. |
| `regex` | `field + value` | Regular-expression match. |
| `not_empty` | `field + value` or `field + reference` | Actual value must be non-empty. |
| `empty` | `field + value` or `field + reference` | Actual value must be empty. |
| `>=` | `field + value` or `field + reference` | Numeric compare when both sides are numeric, otherwise string compare. |
| `<=` | `field + value` or `field + reference` | Numeric compare when both sides are numeric, otherwise string compare. |
| `>` | `field + value` or `field + reference` | Numeric compare when both sides are numeric, otherwise string compare. |
| `<` | `field + value` or `field + reference` | Numeric compare when both sides are numeric, otherwise string compare. |
| `delta_nonzero` | `delta` | `verify - baseline` must be greater than zero. |
| `delta_match` | `delta + reference_delta` | API delta and reference delta must both be positive and match within optional tolerance. |

### Legacy compatibility accepted by current runtime

Current runtime also accepts several legacy aliases still present in the repo or code path:

- `not_equals` as the historical form of `!=`
- `==` and `eq` as aliases for `equals`
- `ne` as an alias for `!=`
- `matches` as an alias for `regex`

For new YAML, prefer the canonical operators in the table above.

### Legacy placeholder still present in current inventory

| Operator | Status | Notes |
| --- | --- | --- |
| `skip` | Legacy inventory artifact | Present in some existing `Skip` / `Blocked` placeholder cases, but it is not a normal `_compare()` operator for new runnable YAML. Do not use it for new case authoring unless the runtime is explicitly taught to evaluate it. |

## llapi_support semantics

`llapi_support` is documentation and runtime-status metadata. It does not replace `steps` or `pass_criteria`; the case body still defines execution behavior.

| Value | Meaning | Expected case shape |
| --- | --- | --- |
| `Support` | The LLAPI path is intended to run normally. | Real executable steps (`exec` / `read` / `wait`) plus normal `pass_criteria`. |
| `Not Supported` | The LLAPI is expected to fail or return an unsupported indication, but the case is still runnable. | Real executable steps plus `pass_criteria` that assert the expected unsupported response (for example `function not found`). |
| `Skip` | The case is intentionally not executed in the current lab or workflow. | Existing inventory may still use legacy placeholder shapes such as `action: skip`; do not treat `operator: skip` as a normal comparison pattern for new YAML. |
| `Blocked` | The case is not currently runnable because of a known blocker. | May be a hand-authored placeholder case, or an auto-blocked case such as invalid delta schema. |

Wave 1 delta-specific note:

- If a case contains delta criteria with invalid schema or invalid phase ordering, discovery / runtime prep may rewrite `llapi_support` to `Blocked` and attach `blocked_reason: invalid_delta_schema: ...` before execution.

## Schema validation rules

### General validation

The current schema enforces the following baseline rules:

1. Required top-level fields: `id`, `name`, `topology`, `steps`, `pass_criteria`.
2. `topology` must be a mapping.
3. `topology.devices` must be a non-empty mapping.
4. `steps` must be a non-empty list.
5. Every step must be a mapping.
6. Every step must include `id`, `action`, and `target`.
7. Step `id` values must be unique within the case.
8. `command`, when present, must be a string or a non-empty list of non-empty strings.
9. `depends_on` must reference an earlier step; forward references are invalid.
10. `pass_criteria` must be a non-empty list.
11. `results_reference`, `source.baseline`, `source.report`, and `source.sheet` are forbidden in `wifi_llapi` cases.

### Delta-specific validation

When any `pass_criteria` entry contains `delta`, the plugin adds these checks:

1. `operator` must be `delta_nonzero` or `delta_match`.
2. `delta` must be a mapping with non-empty `baseline` and `verify` strings.
3. `reference_delta` must be a mapping with non-empty `baseline` and `verify` strings for `delta_match`.
4. `phase` values, when used, must be one of `baseline`, `trigger`, or `verify`.
5. Delta cases must include at least one `phase: trigger` step.
6. `baseline` steps must appear before the first `trigger` step.
7. All `verify` steps must appear after a `trigger` step, and no later `trigger` step may appear after verification has started.
8. A delta case with invalid delta schema is blocked before normal execution/alignment.

### Delta runtime validity

The following checks happen at evaluation time rather than YAML schema load time:

1. Delta endpoint field paths must resolve to numeric values.
2. `delta_nonzero` requires `verify - baseline > 0`.
3. `delta_match` requires both deltas to be positive.
4. `delta_match` compares the two positive deltas and applies optional `tolerance_pct`.

## Delta-related reason codes

| Reason code | Trigger |
| --- | --- |
| `invalid_delta_schema` | The case definition fails delta schema or phase-order validation before execution. |
| `delta_value_not_numeric` | A delta endpoint resolves to a missing or non-numeric runtime value. |
| `delta_zero` | A `delta_nonzero` check produced a zero or negative delta. |
| `delta_zero_side` | A `delta_match` check had a zero or negative API-side or reference-side delta. |
| `delta_mismatch` | A `delta_match` check produced two positive deltas that differ beyond tolerance. |

## Worked examples

### Example 1: standard executable case

```yaml
id: wifi-llapi-D004-kickstation
name: kickStation() - WiFi.AccessPoint.{i}.
version: "1.1"
source:
  row: 4
  object: "WiFi.AccessPoint.{i}."
  api: "kickStation()"
llapi_support: Support
bands:
  - 5g
  - 6g
  - 2.4g
topology:
  devices:
    DUT:
      role: ap
      transport: serial
      selector: COM1
    STA:
      role: sta
      transport: serial
      selector: COM0
steps:
  - id: step1_5g_assoc
    action: exec
    target: DUT
    band: 5g
    command: "wl -i wl0 assoclist | sed -n 's/^assoclist /AssocMac5g=/p'"
    capture: assoc_5g
  - id: step2_5g_before
    action: exec
    target: DUT
    band: 5g
    command: 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.DisassociationTime?"'
    depends_on: step1_5g_assoc
    capture: before_5g
  - id: step3_5g_kick
    action: exec
    target: DUT
    band: 5g
    command: 'ubus-cli "WiFi.AccessPoint.1.kickStation(MACAddress={{assoc_5g.AssocMac5g}})"'
    depends_on: step2_5g_before
  - id: step4_5g_after
    action: exec
    target: DUT
    band: 5g
    command: 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.DisassociationTime?"'
    depends_on: step3_5g_kick
    capture: after_5g
pass_criteria:
  - field: assoc_5g.AssocMac5g
    operator: regex
    value: (?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$
    description: 5G STA must be associated before kickStation()
  - field: after_5g.DisassociationTime
    operator: !=
    reference: before_5g.DisassociationTime
    band: 5g
    description: DisassociationTime must change after kickStation()
verification_command:
  - 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"'
  - 'wl -i wl0 assoclist'
```

### Example 2: counter-delta case

```yaml
id: wifi-llapi-delta-match-pass
name: PacketsSent
version: "1.0"
source:
  row: 6
  object: "WiFi.SSID.{i}.Stats."
  api: "PacketsSent"
llapi_support: Support
bands:
  - 2.4g
topology:
  devices:
    DUT:
      role: ap
      transport: serial
steps:
  - id: baseline_api
    action: exec
    target: DUT
    phase: baseline
    command: 'ubus-cli "WiFi.SSID.8.Stats.PacketsSent?"'
    capture: baseline_api
  - id: baseline_drv
    action: exec
    target: DUT
    phase: baseline
    command: "wl -i wl2 counters | grep '^txframe '"
    capture: baseline_drv
  - id: trigger_traffic
    action: exec
    target: DUT
    phase: trigger
    command: "echo traffic-24g"
  - id: verify_api
    action: exec
    target: DUT
    phase: verify
    command: 'ubus-cli "WiFi.SSID.8.Stats.PacketsSent?"'
    capture: verify_api
  - id: verify_drv
    action: exec
    target: DUT
    phase: verify
    command: "wl -i wl2 counters | grep '^txframe '"
    capture: verify_drv
pass_criteria:
  - delta:
      baseline: baseline_api.PacketsSent
      verify: verify_api.PacketsSent
    reference_delta:
      baseline: baseline_drv.TxFrames
      verify: verify_drv.TxFrames
    operator: delta_match
    tolerance_pct: 10
```

### Example 3: auto-blocked delta case

```yaml
id: wifi-llapi-delta-invalid-order
name: PacketsSent invalid phase ordering
source:
  row: 313
  object: "WiFi.SSID.{i}.Stats."
  api: "PacketsSent"
bands:
  - 2.4g
llapi_support: Support
topology:
  devices:
    DUT:
      role: ap
      transport: serial
      selector: COM1
steps:
  - id: baseline_api
    action: exec
    target: DUT
    phase: baseline
    command: 'ubus-cli "WiFi.SSID.8.Stats.PacketsSent?"'
    capture: baseline_api
  - id: verify_api
    action: exec
    target: DUT
    phase: verify
    command: 'ubus-cli "WiFi.SSID.8.Stats.PacketsSent?"'
    capture: verify_api
  - id: trigger_traffic
    action: exec
    target: DUT
    phase: trigger
    command: "echo traffic-24g"
pass_criteria:
  - delta:
      baseline: baseline_api.PacketsSent
      verify: verify_api.PacketsSent
    operator: delta_nonzero
```

Discovery / runtime prep blocks this case before execution with:

- `llapi_support: Blocked`
- `blocked_reason: invalid_delta_schema: verify step must follow trigger`

## Authoring notes

- Keep new official case files discoverable and row-indexed; reserve `_*.yaml` for non-discoverable fixtures.
- Prefer canonical band names: `5g`, `6g`, `2.4g`.
- Prefer canonical operators from this document for new edits, even if legacy aliases still execute.
- For delta cases, explicitly annotate every step with `phase`. Omitted `phase` defaults to `verify` and can invalidate a case if the step appears before the trigger window.
- For official inventory cases, treat `source.row`, `source.object`, and `source.api` as required authoring metadata even though only the base YAML schema is formally required.
