"""case_schema — YAML test case schema validation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

# 必要的頂層欄位
REQUIRED_TOP_KEYS = {"id", "name", "topology", "steps", "pass_criteria"}

# topology 必要欄位
REQUIRED_TOPOLOGY_KEYS = {"devices"}

# step 必要欄位
REQUIRED_STEP_KEYS = {"id", "action", "target"}
ALLOWED_BRCM_SUCCESS_OPERATORS = {"equals", "one_of", "contains", "regex"}

REQUIRED_WIFI_BAND_BASELINE_BANDS = ("5g", "6g", "2.4g")


class CaseValidationError(Exception):
    """Test case YAML 驗證失敗。"""


def _validate_step_command(step: dict[str, Any], *, source: Path | str, index: int) -> None:
    command = step.get("command")
    if command is None:
        return
    if isinstance(command, str):
        return
    if isinstance(command, list) and all(isinstance(item, str) and item.strip() for item in command):
        return
    raise CaseValidationError(
        f"{source}: step[{index}] command must be a string or non-empty list of strings"
    )


def _require_non_empty_string(
    value: Any,
    *,
    source: Path | str,
    field: str,
) -> str:
    if not isinstance(value, str):
        raise CaseValidationError(f"{source}: {field} must be a non-empty string")
    text = value.strip()
    if not text:
        raise CaseValidationError(f"{source}: {field} must be a non-empty string")
    return text


def _validate_string_list(
    value: Any,
    *,
    source: Path | str,
    field: str,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        raise CaseValidationError(f"{source}: {field} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise CaseValidationError(f"{source}: {field} must be a non-empty list of strings")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise CaseValidationError(
                f"{source}: {field}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    return normalized


def _require_mapping(
    value: Any,
    *,
    source: Path | str,
    field: str,
    allow_empty: bool = True,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaseValidationError(f"{source}: {field} must be a mapping")
    if not value and not allow_empty:
        raise CaseValidationError(f"{source}: {field} must be a non-empty mapping")
    return dict(value)


def _require_string_mapping(
    value: Any,
    *,
    source: Path | str,
    field: str,
) -> dict[str, str]:
    mapping = _require_mapping(value, source=source, field=field)
    normalized: dict[str, str] = {}
    for key, item in mapping.items():
        if not isinstance(key, str) or not key.strip():
            raise CaseValidationError(f"{source}: {field} keys must be non-empty strings")
        normalized[key.strip()] = _require_non_empty_string(
            item,
            source=source,
            field=f"{field}.{key}",
        )
    return normalized


def _validate_wifi_band_baseline_profile(
    band: str,
    raw_profile: Any,
    *,
    source: Path | str,
) -> dict[str, Any]:
    if not isinstance(raw_profile, dict):
        raise CaseValidationError(f"{source}: profiles.{band} must be a mapping")

    profile = {
        "iface": _require_non_empty_string(raw_profile.get("iface"), source=source, field=f"profiles.{band}.iface"),
        "radio": _require_non_empty_string(raw_profile.get("radio"), source=source, field=f"profiles.{band}.radio"),
        "ap": _require_non_empty_string(raw_profile.get("ap"), source=source, field=f"profiles.{band}.ap"),
        "secondary_ap": _require_non_empty_string(
            raw_profile.get("secondary_ap"),
            source=source,
            field=f"profiles.{band}.secondary_ap",
        ),
        "ssid_index": _require_non_empty_string(
            raw_profile.get("ssid_index"),
            source=source,
            field=f"profiles.{band}.ssid_index",
        ),
        "ssid": _require_non_empty_string(raw_profile.get("ssid"), source=source, field=f"profiles.{band}.ssid"),
        "mode": _require_non_empty_string(raw_profile.get("mode"), source=source, field=f"profiles.{band}.mode"),
        "key": _require_non_empty_string(raw_profile.get("key"), source=source, field=f"profiles.{band}.key"),
        "mfp": _require_non_empty_string(raw_profile.get("mfp"), source=source, field=f"profiles.{band}.mfp"),
        "dut_secret_fields": _validate_string_list(
            raw_profile.get("dut_secret_fields"),
            source=source,
            field=f"profiles.{band}.dut_secret_fields",
        ),
        "dut_pre_start_commands": _validate_string_list(
            raw_profile.get("dut_pre_start_commands", []),
            source=source,
            field=f"profiles.{band}.dut_pre_start_commands",
            allow_empty=True,
        ),
        "dut_runtime_config_commands": _validate_string_list(
            raw_profile.get("dut_runtime_config_commands", []),
            source=source,
            field=f"profiles.{band}.dut_runtime_config_commands",
            allow_empty=True,
        ),
        "dut_runtime_ready_commands": _validate_string_list(
            raw_profile.get("dut_runtime_ready_commands", []),
            source=source,
            field=f"profiles.{band}.dut_runtime_ready_commands",
            allow_empty=True,
        ),
        "sta_global_config": _validate_string_list(
            raw_profile.get("sta_global_config"),
            source=source,
            field=f"profiles.{band}.sta_global_config",
        ),
        "sta_network_config": _validate_string_list(
            raw_profile.get("sta_network_config"),
            source=source,
            field=f"profiles.{band}.sta_network_config",
        ),
        "sta_pre_mode_commands": _validate_string_list(
            raw_profile.get("sta_pre_mode_commands", []),
            source=source,
            field=f"profiles.{band}.sta_pre_mode_commands",
            allow_empty=True,
        ),
        "sta_pre_start_commands": _validate_string_list(
            raw_profile.get("sta_pre_start_commands", []),
            source=source,
            field=f"profiles.{band}.sta_pre_start_commands",
            allow_empty=True,
        ),
        "sta_post_start_commands": _validate_string_list(
            raw_profile.get("sta_post_start_commands", []),
            source=source,
            field=f"profiles.{band}.sta_post_start_commands",
            allow_empty=True,
        ),
        "sta_ctrl_command": _require_non_empty_string(
            raw_profile.get("sta_ctrl_command"),
            source=source,
            field=f"profiles.{band}.sta_ctrl_command",
        ),
        "sta_connect_command": _require_non_empty_string(
            raw_profile.get("sta_connect_command"),
            source=source,
            field=f"profiles.{band}.sta_connect_command",
        ),
        "sta_status_command": _require_non_empty_string(
            raw_profile.get("sta_status_command"),
            source=source,
            field=f"profiles.{band}.sta_status_command",
        ),
    }
    driver_join = raw_profile.get("sta_driver_join_command")
    if driver_join not in (None, ""):
        profile["sta_driver_join_command"] = _require_non_empty_string(
            driver_join,
            source=source,
            field=f"profiles.{band}.sta_driver_join_command",
        )
    return profile


def load_case(path: Path | str) -> dict[str, Any]:
    """載入並驗證單一 test case YAML 檔。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"case file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise CaseValidationError(f"case must be a YAML mapping: {path}")

    validate_case(data, path)
    return data


def load_wifi_band_baselines(path: Path | str) -> dict[str, dict[str, Any]]:
    """載入並驗證 wifi_llapi 共用 band baseline YAML。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"wifi baseline file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise CaseValidationError(f"wifi baseline file must be a YAML mapping: {path}")

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise CaseValidationError(f"{path}: profiles must be a mapping")

    missing = [band for band in REQUIRED_WIFI_BAND_BASELINE_BANDS if band not in profiles]
    if missing:
        raise CaseValidationError(f"{path}: missing wifi baseline profiles: {missing}")

    return {
        band: _validate_wifi_band_baseline_profile(band, profiles[band], source=path)
        for band in REQUIRED_WIFI_BAND_BASELINE_BANDS
    }


def load_brcm_fw_upgrade_platform_profiles(path: Path | str) -> dict[str, dict[str, Any]]:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise CaseValidationError(f"{path}: profiles must be a mapping")
    profiles: dict[str, dict[str, Any]] = {}
    for name, raw_profile in data["profiles"].items():
        if not isinstance(raw_profile, dict):
            raise CaseValidationError(f"{path}: profiles.{name} must be a mapping")
        profiles[name] = {
            "family": _require_non_empty_string(
                raw_profile.get("family"),
                source=path,
                field=f"profiles.{name}.family",
            ),
            "board": _require_non_empty_string(
                raw_profile.get("board"),
                source=path,
                field=f"profiles.{name}.board",
            ),
            "os_flavor": _require_non_empty_string(
                raw_profile.get("os_flavor"),
                source=path,
                field=f"profiles.{name}.os_flavor",
            ),
            "login_strategy": _require_non_empty_string(
                raw_profile.get("login_strategy"),
                source=path,
                field=f"profiles.{name}.login_strategy",
            ),
            "capabilities": _require_mapping(
                raw_profile.get("capabilities", {}),
                source=path,
                field=f"profiles.{name}.capabilities",
            ),
            "commands": _require_string_mapping(
                raw_profile.get("commands", {}),
                source=path,
                field=f"profiles.{name}.commands",
            ),
            "success_parsers": _require_string_mapping(
                raw_profile.get("success_parsers", {}),
                source=path,
                field=f"profiles.{name}.success_parsers",
            ),
            "log_markers": _require_string_mapping(
                raw_profile.get("log_markers", {}),
                source=path,
                field=f"profiles.{name}.log_markers",
            ),
        }
    return profiles


def load_brcm_fw_upgrade_topologies(path: Path | str) -> dict[str, dict[str, Any]]:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not isinstance(data.get("topologies"), dict):
        raise CaseValidationError(f"{path}: topologies must be a mapping")
    topologies: dict[str, dict[str, Any]] = {}
    for name, raw_topology in data["topologies"].items():
        if not isinstance(raw_topology, dict):
            raise CaseValidationError(f"{path}: topologies.{name} must be a mapping")
        devices = _require_mapping(
            raw_topology.get("devices"),
            source=path,
            field=f"topologies.{name}.devices",
            allow_empty=False,
        )
        phases = raw_topology.get("phases")
        for device_name, raw_device in devices.items():
            if not isinstance(raw_device, dict):
                raise CaseValidationError(
                    f"{path}: topologies.{name}.devices.{device_name} must be a mapping"
                )
        topologies[name] = {
            "devices": devices,
            "phases": _validate_string_list(
                phases,
                source=path,
                field=f"topologies.{name}.phases",
            ),
        }
    return topologies


def validate_brcm_fw_upgrade_case(case: dict[str, Any], source: Path | str = "<unknown>") -> None:
    required = {
        "id",
        "name",
        "platform_profile",
        "topology_ref",
        "artifacts",
        "runtime_inputs",
        "success_gates",
        "evidence",
    }
    missing = required - set(case.keys())
    if missing:
        raise CaseValidationError(f"{source}: missing required keys: {missing}")
    _require_non_empty_string(case.get("id"), source=source, field="id")
    _require_non_empty_string(case.get("name"), source=source, field="name")
    _require_non_empty_string(case.get("platform_profile"), source=source, field="platform_profile")
    _require_non_empty_string(case.get("topology_ref"), source=source, field="topology_ref")
    if not isinstance(case["artifacts"], dict):
        raise CaseValidationError(f"{source}: artifacts must be a mapping")
    artifact_required = {"forward_image", "rollback_image", "active_image_role"}
    artifact_missing = artifact_required - set(case["artifacts"].keys())
    if artifact_missing:
        raise CaseValidationError(f"{source}: artifacts missing required keys: {artifact_missing}")
    for artifact_field in artifact_required:
        _require_non_empty_string(case["artifacts"].get(artifact_field), source=source, field=f"artifacts.{artifact_field}")
    concrete_artifact_keys = set(case["artifacts"].keys()) - {"active_image_role"}
    if case["artifacts"]["active_image_role"] not in concrete_artifact_keys:
        raise CaseValidationError(
            f"{source}: artifacts.active_image_role must reference a defined artifact key"
        )
    if not isinstance(case["runtime_inputs"], dict):
        raise CaseValidationError(f"{source}: runtime_inputs must be a mapping")
    runtime_required = {"fw_name", "expected_image_tag", "expected_build_time"}
    runtime_missing = runtime_required - set(case["runtime_inputs"].keys())
    if runtime_missing:
        raise CaseValidationError(f"{source}: runtime_inputs missing required keys: {runtime_missing}")
    for runtime_field in runtime_required:
        _require_non_empty_string(
            case["runtime_inputs"].get(runtime_field),
            source=source,
            field=f"runtime_inputs.{runtime_field}",
        )
    if not isinstance(case["success_gates"], list) or not case["success_gates"]:
        raise CaseValidationError(f"{source}: success_gates must be a non-empty list")
    gate_ids: set[str] = set()
    for index, gate in enumerate(case["success_gates"]):
        if not isinstance(gate, dict):
            raise CaseValidationError(f"{source}: success_gates[{index}] must be a mapping")
        gate_required = {"id", "verifier", "operator", "expected"}
        gate_missing = gate_required - set(gate.keys())
        if gate_missing:
            raise CaseValidationError(f"{source}: success_gates[{index}] missing required keys: {gate_missing}")
        gate_id = _require_non_empty_string(gate.get("id"), source=source, field=f"success_gates[{index}].id")
        if gate_id in gate_ids:
            raise CaseValidationError(f"{source}: duplicate success gate id: {gate_id}")
        gate_ids.add(gate_id)
        _require_non_empty_string(
            gate.get("verifier"),
            source=source,
            field=f"success_gates[{index}].verifier",
        )
        _require_non_empty_string(
            gate.get("operator"),
            source=source,
            field=f"success_gates[{index}].operator",
        )
        operator = gate["operator"].strip()
        if operator not in ALLOWED_BRCM_SUCCESS_OPERATORS:
            raise CaseValidationError(
                f"{source}: success_gates[{index}].operator must be one of {sorted(ALLOWED_BRCM_SUCCESS_OPERATORS)}"
            )
        if operator == "one_of":
            _validate_string_list(
                gate.get("expected"),
                source=source,
                field=f"success_gates[{index}].expected",
            )
        else:
            _require_non_empty_string(
                gate.get("expected"),
                source=source,
                field=f"success_gates[{index}].expected",
            )
    if not isinstance(case["evidence"], dict):
        raise CaseValidationError(f"{source}: evidence must be a mapping")
    evidence_required = {"capture", "required_for_pass"}
    evidence_missing = evidence_required - set(case["evidence"].keys())
    if evidence_missing:
        raise CaseValidationError(f"{source}: evidence missing required keys: {evidence_missing}")
    _validate_string_list(case["evidence"].get("capture"), source=source, field="evidence.capture")
    required_for_pass = _validate_string_list(
        case["evidence"].get("required_for_pass"),
        source=source,
        field="evidence.required_for_pass",
    )


def validate_case(case: dict[str, Any], source: Path | str = "<unknown>") -> None:
    """驗證 test case dict 結構。"""
    missing = REQUIRED_TOP_KEYS - set(case.keys())
    if missing:
        raise CaseValidationError(f"{source}: missing required keys: {missing}")

    # topology
    topo = case["topology"]
    if not isinstance(topo, dict):
        raise CaseValidationError(f"{source}: topology must be a mapping")
    topo_missing = REQUIRED_TOPOLOGY_KEYS - set(topo.keys())
    if topo_missing:
        raise CaseValidationError(f"{source}: topology missing keys: {topo_missing}")

    # devices
    devices = topo["devices"]
    if not isinstance(devices, dict) or not devices:
        raise CaseValidationError(f"{source}: topology.devices must be a non-empty mapping")

    # steps
    steps = case["steps"]
    if not isinstance(steps, list) or not steps:
        raise CaseValidationError(f"{source}: steps must be a non-empty list")
    step_ids: set[str] = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise CaseValidationError(f"{source}: step[{i}] must be a mapping")
        step_missing = REQUIRED_STEP_KEYS - set(step.keys())
        if step_missing:
            raise CaseValidationError(f"{source}: step[{i}] missing keys: {step_missing}")
        _validate_step_command(step, source=source, index=i)
        sid = step["id"]
        if sid in step_ids:
            raise CaseValidationError(f"{source}: duplicate step id: {sid}")
        step_ids.add(sid)
        # depends_on 參照檢查
        dep = step.get("depends_on")
        if dep and dep not in step_ids:
            raise CaseValidationError(f"{source}: step[{i}] depends_on '{dep}' not found before it")

    # pass_criteria
    criteria = case["pass_criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise CaseValidationError(f"{source}: pass_criteria must be a non-empty list")


def load_cases_dir(cases_dir: Path | str) -> list[dict[str, Any]]:
    """載入 cases/ 目錄下所有 .yaml/.yml 檔（排除 _template）。"""
    cases_dir = Path(cases_dir)
    cases: list[dict[str, Any]] = []
    if not cases_dir.is_dir():
        return cases
    for p in sorted(cases_dir.glob("*.y*ml")):
        if p.stem.startswith("_"):
            continue
        try:
            cases.append(load_case(p))
        except Exception:
            log.exception("failed to load case: %s", p)
    return cases
