from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from plugins.brcm_fw_upgrade.strategies.flash import run_flash_sequence
from plugins.brcm_fw_upgrade.strategies.transfer import render_md5_command, select_transfer_method
from plugins.brcm_fw_upgrade.strategies.verify import extract_named_group
from testpilot.core.plugin_base import PluginBase
from testpilot.schema.case_schema import (
    CaseValidationError,
    load_brcm_fw_upgrade_platform_profiles,
    load_brcm_fw_upgrade_topologies,
    validate_brcm_fw_upgrade_case,
)


class Plugin(PluginBase):
    def __init__(self) -> None:
        root = Path(__file__).parent
        self.platform_profiles = load_brcm_fw_upgrade_platform_profiles(root / "platform_profiles.yaml")
        self.topologies = load_brcm_fw_upgrade_topologies(root / "topology_baselines.yaml")

    @property
    def name(self) -> str:
        return "brcm_fw_upgrade"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def cases_dir(self) -> Path:
        return Path(__file__).parent / "cases"

    def discover_cases(self) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        for yaml_file in sorted(self.cases_dir.glob("*.yaml")):
            if yaml_file.stem.startswith("_"):
                continue
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise CaseValidationError(f"{yaml_file}: case must be a YAML mapping")
            validate_brcm_fw_upgrade_case(data, yaml_file)
            case = dict(data)
            platform_profile = case["platform_profile"]
            if platform_profile not in self.platform_profiles:
                raise CaseValidationError(f"{yaml_file}: unknown platform_profile: {platform_profile}")
            profile = self.platform_profiles[platform_profile]
            topology_ref = case["topology_ref"]
            if topology_ref not in self.topologies:
                raise CaseValidationError(f"{yaml_file}: unknown topology_ref: {topology_ref}")
            gate_ids = {gate["id"] for gate in case["success_gates"]}
            for gate in case["success_gates"]:
                verifier = gate["verifier"]
                if verifier not in profile["success_parsers"]:
                    raise CaseValidationError(f"{yaml_file}: unknown verifier for profile {platform_profile}: {verifier}")
            required_for_pass = set(case["evidence"]["required_for_pass"])
            allowed_requirements = gate_ids | set(profile["log_markers"].keys())
            unknown_requirements = sorted(required_for_pass - allowed_requirements)
            if unknown_requirements:
                raise CaseValidationError(
                    f"{yaml_file}: unknown evidence requirement(s): {unknown_requirements}"
                )
            phases = self.topologies[topology_ref]["phases"]
            case["steps"] = [{"id": phase, "action": "phase", "target": "controller"} for phase in phases]
            cases.append(case)
        return cases

    def execute_step(self, case: dict[str, Any], step: dict[str, Any], topology: Any) -> dict[str, Any]:
        return {"success": True, "output": "", "captured": {}, "timing": 0.0}

    def evaluate(self, case: dict[str, Any], results: dict[str, Any]) -> bool:
        return True

    def _resolve_template_value(self, raw: str, runtime_overrides: dict[str, str]) -> str:
        if not isinstance(raw, str):
            raise RuntimeError(f"expected template value to be a string, got {type(raw).__name__}")
        if raw.startswith("{{") and raw.endswith("}}"):
            key = raw[2:-2]
            value = runtime_overrides.get(key)
            if not value:
                raise RuntimeError(f"missing runtime override: {key}")
            return value
        return raw

    def _resolve_runtime_inputs(
        self,
        case: dict[str, Any],
        runtime_overrides: dict[str, str],
    ) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for key, raw in case.get("runtime_inputs", {}).items():
            resolved[key] = self._resolve_template_value(raw, runtime_overrides)
        return resolved

    def _resolve_artifacts(
        self,
        case: dict[str, Any],
        runtime_overrides: dict[str, str],
    ) -> dict[str, Any]:
        artifacts = case.get("artifacts", {})
        active_role = artifacts.get("active_image_role")
        if not isinstance(active_role, str) or not active_role:
            raise RuntimeError("missing active_image_role")
        resolved_paths = {
            key: self._resolve_template_value(value, runtime_overrides)
            for key, value in artifacts.items()
            if key != "active_image_role"
        }
        if active_role not in resolved_paths:
            raise RuntimeError(f"active artifact role not found: {active_role}")
        active_path = resolved_paths[active_role]
        active_path_obj = Path(active_path)
        if not active_path.strip():
            raise RuntimeError("active artifact path is empty")
        if not active_path_obj.exists():
            raise RuntimeError(f"active artifact path does not exist: {active_path}")
        if not active_path_obj.is_file():
            raise RuntimeError(f"active artifact path is not a file: {active_path}")
        return {
            "paths": resolved_paths,
            "active_role": active_role,
            "active_path": active_path,
            "active_filename": active_path_obj.name,
        }

    def _required_devices(self, topology: dict[str, Any]) -> list[str]:
        return [
            device
            for device, config in topology["devices"].items()
            if isinstance(config, dict) and config.get("required", False)
        ]

    def _build_precheck_phase(
        self,
        *,
        topology: dict[str, Any],
        shells: dict[str, Any],
        runtime_inputs: dict[str, str],
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        required_devices = self._required_devices(topology)
        missing_devices = [device for device in required_devices if device not in shells]
        if missing_devices:
            raise RuntimeError(f"missing required shells: {missing_devices}")
        return {
            "id": "precheck",
            "required_devices": required_devices,
            "available_devices": sorted(shells.keys()),
            "runtime_inputs": runtime_inputs,
            "artifacts": artifacts["paths"],
            "active_image_role": artifacts["active_role"],
            "active_artifact_path": artifacts["active_path"],
            "active_artifact_filename": artifacts["active_filename"],
            "fw_name_binding": {
                "declared_fw_name": runtime_inputs["fw_name"],
                "artifact_filename": artifacts["active_filename"],
            },
        }

    def _build_transfer_phase(
        self,
        *,
        phase_id: str,
        target: str,
        profile: dict[str, Any],
        topology: dict[str, Any],
        shells: dict[str, Any],
        artifact_path: str,
    ) -> dict[str, Any]:
        if target not in shells:
            raise RuntimeError(f"missing shell for transfer target: {target}")
        transfer_method = select_transfer_method(
            profile["capabilities"],
            sta_present="STA" in topology["devices"],
        )
        evidence = {
            "id": phase_id,
            "target": target,
            "artifact_path": artifact_path,
            "artifact_filename": Path(artifact_path).name,
            "transfer_method": transfer_method,
            "shell_ready": True,
        }
        if "md5" in profile["commands"]:
            evidence["md5_command"] = render_md5_command(profile["commands"]["md5"], path=artifact_path)
        return evidence

    def _verify_runtime_state(
        self,
        *,
        shell: Any,
        profile: dict[str, Any],
        build_time_expected: str,
        image_tag_expected: str,
    ) -> dict[str, Any]:
        commands = profile["commands"]
        ready_probe_command = commands.get("ready_probe", commands["proc_version"])
        ready_probe_attempts = int(commands.get("ready_probe_attempts", "1"))
        ready_probe_retry_delay_seconds = float(commands.get("ready_probe_retry_delay_seconds", "0"))
        if ready_probe_attempts < 1:
            raise RuntimeError(f"ready_probe_attempts must be >= 1, got {ready_probe_attempts}")
        if ready_probe_retry_delay_seconds < 0:
            raise RuntimeError(
                f"ready_probe_retry_delay_seconds must be >= 0, got {ready_probe_retry_delay_seconds}"
            )
        ready_probe_history: list[dict[str, Any]] = []
        ready_probe_output = ""
        for attempt in range(1, ready_probe_attempts + 1):
            attempt_record: dict[str, Any] = {
                "attempt": attempt,
                "command": ready_probe_command,
            }
            try:
                ready_probe_output = shell.run(ready_probe_command)
            except Exception as exc:
                attempt_record["error"] = str(exc)
                attempt_record["status"] = "error"
                ready_probe_history.append(attempt_record)
            else:
                attempt_record["output"] = ready_probe_output
                attempt_record["status"] = "ready" if ready_probe_output.strip() else "empty"
                ready_probe_history.append(attempt_record)
                if ready_probe_output.strip():
                    break
            if attempt < ready_probe_attempts and ready_probe_retry_delay_seconds > 0:
                time.sleep(ready_probe_retry_delay_seconds)
                ready_probe_history[-1]["slept_seconds"] = ready_probe_retry_delay_seconds
        else:
            raise RuntimeError(
                f"ready probe failed after {ready_probe_attempts} attempts: {ready_probe_history}"
            )
        proc_version = shell.run(commands["proc_version"])
        image_state = shell.run(commands["image_state"])
        build_time_actual = extract_named_group(
            profile["success_parsers"]["proc_version_build_time"],
            proc_version,
            "build_time",
        )
        image_tag_actual = extract_named_group(
            profile["success_parsers"]["image_tag"],
            image_state,
            "image_tag",
        ).strip()
        if build_time_actual != build_time_expected:
            raise RuntimeError(
                f"build time mismatch: expected {build_time_expected!r}, got {build_time_actual!r}"
            )
        if image_tag_actual != image_tag_expected:
            raise RuntimeError(
                f"image tag mismatch: expected {image_tag_expected!r}, got {image_tag_actual!r}"
            )
        return {
            "ready_probe": {
                "command": ready_probe_command,
                "retry_delay_seconds": ready_probe_retry_delay_seconds,
                "attempts": ready_probe_history,
                "output": ready_probe_output,
            },
            "build_time": build_time_actual,
            "image_tag": image_tag_actual,
        }

    def _resolve_case(self, case_id: str) -> dict[str, Any]:
        for case in self.discover_cases():
            if case["id"] == case_id:
                return case
        raise KeyError(f"unknown case id: {case_id}")

    def run_cases(
        self,
        topology: dict[str, Any],
        *,
        case_ids: list[str] | None,
        runtime_overrides: dict[str, str],
    ) -> dict[str, Any]:
        discovered_cases = self.discover_cases()
        cases_by_id = {str(case["id"]): case for case in discovered_cases}
        requested_case_ids = case_ids or list(cases_by_id)
        unknown_case_ids = [case_id for case_id in requested_case_ids if case_id not in cases_by_id]
        if unknown_case_ids:
            raise ValueError(f"unknown case id(s): {', '.join(unknown_case_ids)}")

        topology_name = topology.get("name", "unnamed") if isinstance(topology, dict) else "unnamed"
        results = []
        for case_id in requested_case_ids:
            case = cases_by_id[case_id]
            results.append(
                {
                    "case_id": case_id,
                    "platform_profile": case["platform_profile"],
                    "topology_ref": case["topology_ref"],
                    "topology_name": topology_name,
                    "runtime_overrides": dict(runtime_overrides),
                }
            )

        return {
            "status": "ok",
            "selected_case_ids": requested_case_ids,
            "results": results,
        }

    def run_case(
        self,
        *,
        case_id: str,
        shells: dict[str, Any],
        runtime_overrides: dict[str, str],
    ) -> dict[str, Any]:
        case = self._resolve_case(case_id)
        profile = self.platform_profiles[case["platform_profile"]]
        topology = self.topologies[case["topology_ref"]]
        runtime_inputs = self._resolve_runtime_inputs(case, runtime_overrides)
        artifacts = self._resolve_artifacts(case, runtime_overrides)
        fw_name = artifacts["active_filename"]
        if runtime_inputs["fw_name"] != fw_name:
            raise RuntimeError(
                f"fw_name does not match active artifact filename: {runtime_inputs['fw_name']!r} != {fw_name!r}"
            )
        build_time_expected = runtime_inputs["expected_build_time"]
        image_tag_expected = runtime_inputs["expected_image_tag"]
        evidence: dict[str, Any] = {"phases": []}

        for phase in topology["phases"]:
            if phase == "precheck":
                evidence["phases"].append(
                    self._build_precheck_phase(
                        topology=topology,
                        shells=shells,
                        runtime_inputs=runtime_inputs,
                        artifacts=artifacts,
                    )
                )
            elif phase == "transfer_dut":
                evidence["phases"].append(
                    self._build_transfer_phase(
                        phase_id=phase,
                        target="DUT",
                        profile=profile,
                        topology=topology,
                        shells=shells,
                        artifact_path=artifacts["active_path"],
                    )
                )
            elif phase == "transfer_sta":
                evidence["phases"].append(
                    self._build_transfer_phase(
                        phase_id=phase,
                        target="STA",
                        profile=profile,
                        topology=topology,
                        shells=shells,
                        artifact_path=artifacts["active_path"],
                    )
                )
            elif phase == "flash_sta":
                evidence["phases"].append(
                    {
                        "id": phase,
                        "artifact_path": artifacts["active_path"],
                        "artifact_filename": artifacts["active_filename"],
                        "transcript": run_flash_sequence(
                            shells["STA"],
                            commands=profile["commands"],
                            fw_name=fw_name,
                            flash_marker=profile["log_markers"]["flash_complete"],
                        ),
                    }
                )
            elif phase == "verify_sta":
                evidence["phases"].append(
                    {
                        "id": phase,
                        "checks": self._verify_runtime_state(
                            shell=shells["STA"],
                            profile=profile,
                            build_time_expected=build_time_expected,
                            image_tag_expected=image_tag_expected,
                        ),
                    }
                )
            elif phase == "flash_dut":
                evidence["phases"].append(
                    {
                        "id": phase,
                        "artifact_path": artifacts["active_path"],
                        "artifact_filename": artifacts["active_filename"],
                        "transcript": run_flash_sequence(
                            shells["DUT"],
                            commands=profile["commands"],
                            fw_name=fw_name,
                            flash_marker=profile["log_markers"]["flash_complete"],
                        ),
                    }
                )
            elif phase == "verify_dut":
                evidence["phases"].append(
                    {
                        "id": phase,
                        "checks": self._verify_runtime_state(
                            shell=shells["DUT"],
                            profile=profile,
                            build_time_expected=build_time_expected,
                            image_tag_expected=image_tag_expected,
                        ),
                    }
                )
            else:
                raise RuntimeError(f"unsupported phase in task 4 runtime pipeline: {phase}")

        return {"verdict": True, "comment": "", "evidence": evidence}
