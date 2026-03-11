from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from testpilot.cli import main
from testpilot.yaml_command_audit import (
    audit_string_field,
    build_yaml_command_audit_report,
)


def _write_case(path: Path) -> None:
    path.write_text(
        """
id: wifi-llapi-D999-audit
name: audit
hlapi_command: ubus-cli WiFi.Radio.1.Enable=1
verification_command: |
  wl -i wl0 status; wl -i wl1 status
  printf 'a;b'
steps:
  - id: step1
    command: iw dev wl0 set type managed; ifconfig wl0 up
  - id: step2
    command: '[ -z "$STA_MAC" ] && STA_MAC="$(wl -i wl0 assoclist | awk "NR==1{print $2}")"'
pass_criteria:
  - field: step1.output
    operator: contains
    value: ok
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_audit_string_field_respects_quoted_semicolon() -> None:
    findings = audit_string_field("printf 'a;b'")
    assert findings == []


def test_build_yaml_command_audit_report_detects_chained_lines(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    _write_case(cases_dir / "D999_audit.yaml")

    report = build_yaml_command_audit_report(cases_dir)

    assert report["files_scanned"] == 1
    assert report["matches_count"] == 3

    by_field = {item["field_path"]: item for item in report["matches"]}
    assert by_field["verification_command"]["chained_lines"][0]["suggested_commands"] == [
        "wl -i wl0 status",
        "wl -i wl1 status",
    ]
    assert by_field["steps[0].command"]["chained_lines"][0]["suggested_commands"] == [
        "iw dev wl0 set type managed",
        "ifconfig wl0 up",
    ]
    assert by_field["steps[1].command"]["chained_lines"][0]["operators"] == ["&&"]


def test_cli_audit_yaml_commands_outputs_preview_and_report(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    cases_dir = project_root / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    _write_case(cases_dir / "D999_audit.yaml")
    (project_root / "configs").mkdir(parents=True, exist_ok=True)
    (project_root / "configs" / "testbed.yaml").write_text("testbed: {}\n", encoding="utf-8")

    out_path = project_root / "audit-report.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--root",
            str(project_root),
            "wifi-llapi",
            "audit-yaml-commands",
            "--limit",
            "2",
            "--out",
            str(out_path),
        ],
    )

    assert result.exit_code == 0

    preview = json.loads(result.output)
    assert preview["matches_count"] == 3
    assert preview["matches_returned"] == 2
    assert preview["truncated"] is True
    assert preview["report_path"] == str(out_path)

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["matches_count"] == 3
    assert len(written["matches"]) == 3
