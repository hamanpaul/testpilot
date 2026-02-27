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


class CaseValidationError(Exception):
    """Test case YAML 驗證失敗。"""


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
