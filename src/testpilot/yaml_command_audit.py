"""Audit wifi_llapi YAML fields for chained shell commands."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

DEFAULT_AUDIT_FIELDS = (
    "command",
    "verification_command",
    "hlapi_command",
    "setup_steps",
    "sta_env_setup",
)


@dataclass(slots=True)
class ChainedLine:
    line_no: int
    operators: list[str]
    raw_line: str
    suggested_commands: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_no": self.line_no,
            "operators": list(self.operators),
            "raw_line": self.raw_line,
            "suggested_commands": list(self.suggested_commands),
        }


def _split_shell_chain(line: str) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    operators: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escape = False
    i = 0

    while i < len(line):
        ch = line[i]
        if escape:
            buf.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\":
            buf.append(ch)
            escape = True
            i += 1
            continue

        if quote is not None:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue

        if ch in {"'", '"'}:
            quote = ch
            buf.append(ch)
            i += 1
            continue

        if ch == ";":
            command = "".join(buf).strip()
            if command:
                commands.append(command)
                operators.append(";")
            buf = []
            i += 1
            continue

        if ch == "&" and i + 1 < len(line) and line[i + 1] == "&":
            command = "".join(buf).strip()
            if command:
                commands.append(command)
                operators.append("&&")
            buf = []
            i += 2
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        commands.append(tail)
    return commands, operators


def _iter_string_fields(
    node: Any,
    *,
    target_fields: set[str],
    path: str = "",
):
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}" if path else key_text
            if key_text in target_fields and isinstance(value, str):
                yield next_path, key_text, value
            yield from _iter_string_fields(value, target_fields=target_fields, path=next_path)
        return

    if isinstance(node, list):
        for index, item in enumerate(node):
            next_path = f"{path}[{index}]"
            yield from _iter_string_fields(item, target_fields=target_fields, path=next_path)


def audit_string_field(value: str) -> list[ChainedLine]:
    findings: list[ChainedLine] = []
    for line_no, raw_line in enumerate(value.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        commands, operators = _split_shell_chain(stripped)
        if len(commands) <= 1 or not operators:
            continue
        findings.append(
            ChainedLine(
                line_no=line_no,
                operators=operators,
                raw_line=stripped,
                suggested_commands=commands,
            )
        )
    return findings


def build_yaml_command_audit_report(
    cases_dir: Path | str,
    *,
    target_fields: tuple[str, ...] = DEFAULT_AUDIT_FIELDS,
) -> dict[str, Any]:
    root = Path(cases_dir)
    fields = tuple(dict.fromkeys(str(field).strip() for field in target_fields if str(field).strip()))
    matches: list[dict[str, Any]] = []

    yaml_files = sorted(root.glob("*.yaml"))
    for path in yaml_files:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue

        case_id = str(payload.get("id", path.stem))
        for field_path, field_name, value in _iter_string_fields(
            payload,
            target_fields=set(fields),
        ):
            chained_lines = audit_string_field(value)
            if not chained_lines:
                continue
            matches.append(
                {
                    "file": str(path),
                    "case_id": case_id,
                    "field_name": field_name,
                    "field_path": field_path,
                    "chained_lines_count": len(chained_lines),
                    "chained_lines": [item.to_dict() for item in chained_lines],
                }
            )

    return {
        "status": "ok",
        "cases_dir": str(root),
        "target_fields": list(fields),
        "files_scanned": len(yaml_files),
        "matches_count": len(matches),
        "matches": matches,
    }


def write_yaml_command_audit_report(
    report_path: Path | str,
    report: dict[str, Any],
) -> Path:
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
