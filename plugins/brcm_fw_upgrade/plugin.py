from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

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
