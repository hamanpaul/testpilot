from __future__ import annotations

from pathlib import Path

from testpilot.schema.case_schema import load_case


def test_official_case_command_lengths_fit_transport_budget_summary():
    """Track long official-case commands that rely on serialwrap temp-script staging."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    threshold = 120
    violations: list[str] = []
    for yaml_path in sorted(cases_dir.glob("D*.yaml")):
        case = load_case(yaml_path)
        for step in case.get("steps", []):
            if not isinstance(step, dict):
                continue
            step_id = step.get("id", "?")
            command = step.get("command", "")
            if isinstance(command, str):
                if len(command) > threshold:
                    violations.append(f"{yaml_path.name}:{step_id}:command:{len(command)}")
            elif isinstance(command, list):
                for index, item in enumerate(command, start=1):
                    if isinstance(item, str) and len(item) > threshold:
                        violations.append(
                            f"{yaml_path.name}:{step_id}:command[{index}]:{len(item)}"
                        )
        for field in ("verification_command", "hlapi_command"):
            value = case.get(field, "")
            if isinstance(value, str):
                if len(value) > threshold:
                    violations.append(f"{yaml_path.name}:{field}:{len(value)}")
            elif isinstance(value, list):
                for index, item in enumerate(value, start=1):
                    if isinstance(item, str) and len(item) > threshold:
                        violations.append(f"{yaml_path.name}:{field}[{index}]:{len(item)}")

    assert len(violations) == 717, (
        "Official-case >120-char command inventory changed; "
        "review whether this was an intended calibration update.\n"
        + "\n".join(violations[:40])
    )
