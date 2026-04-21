from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from plugins.brcm_fw_upgrade.strategies.flash import run_flash_sequence
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

    def _verify_runtime_state(
        self,
        *,
        shell: Any,
        profile: dict[str, Any],
        build_time_expected: str,
        image_tag_expected: str,
    ) -> dict[str, str]:
        proc_version = shell.run(profile["commands"]["proc_version"])
        image_state = shell.run(profile["commands"]["image_state"])
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
        return {"build_time": build_time_actual, "image_tag": image_tag_actual}

    def _resolve_case(self, case_id: str) -> dict[str, Any]:
        for case in self.discover_cases():
            if case["id"] == case_id:
                return case
        raise KeyError(f"unknown case id: {case_id}")

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
        fw_name = runtime_overrides["FW_NAME"]
        build_time_expected = runtime_overrides["EXPECTED_BUILD_TIME"]
        image_tag_expected = runtime_overrides["EXPECTED_IMAGE_TAG"]
        evidence: dict[str, Any] = {"phases": []}

        for phase in topology["phases"]:
            if phase in {"precheck", "transfer_dut", "transfer_sta"}:
                evidence["phases"].append({"id": phase, "status": "not_implemented_in_task_4"})
            elif phase == "flash_sta":
                evidence["phases"].append(
                    {
                        "id": phase,
                        "transcript": run_flash_sequence(
                            shells["STA"],
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
                        "transcript": run_flash_sequence(
                            shells["DUT"],
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
