"""Audit wifi_llapi YAML fields for chained shell commands."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shlex
from typing import Any

import yaml

DEFAULT_AUDIT_FIELDS = (
    "command",
    "verification_command",
    "hlapi_command",
    "setup_steps",
    "sta_env_setup",
)
DEFAULT_EXECUTABLE_HINTS = frozenset(
    {
        "ubus-cli",
        "wl",
        "iw",
        "ifconfig",
        "wpa_cli",
        "ping",
        "arping",
        "iperf",
        "cat",
        "echo",
        "printf",
        "sleep",
        "killall",
        "grep",
        "sed",
        "awk",
        "true",
        "false",
        "wpa_supplicant",
    }
)

_SHELL_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_STATEFUL_SHELL_TOKENS = frozenset(
    {
        "[",
        "test",
        "cd",
        "export",
        "unset",
        "local",
        "readonly",
        "declare",
        "source",
        ".",
        "eval",
    }
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


def split_shell_chain(line: str) -> tuple[list[str], list[str]]:
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


def first_shell_token(command: str) -> str:
    stripped = command.strip()
    if not stripped:
        return ""
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return stripped.split(maxsplit=1)[0]
    return tokens[0] if tokens else ""


def looks_like_shell_command(command: str, *, executable_hints: set[str] | None = None) -> bool:
    token = first_shell_token(command)
    if not token:
        return False

    if _SHELL_ASSIGNMENT_RE.match(token):
        return True

    token_base = token.rsplit("/", 1)[-1]
    hints = executable_hints or set()
    return token in _STATEFUL_SHELL_TOKENS or token_base in hints or "/" in token or token.startswith(".")


def shell_chain_is_split_safe(
    commands: list[str],
    operators: list[str],
    *,
    executable_hints: set[str] | None = None,
) -> bool:
    if len(commands) <= 1 or len(commands) != len(operators) + 1:
        return False

    if any(op not in {";", "&&"} for op in operators):
        return False

    for command in commands:
        token = first_shell_token(command)
        if not token:
            return False
        if _SHELL_ASSIGNMENT_RE.match(token):
            return False
        if token in _STATEFUL_SHELL_TOKENS:
            return False
        if not looks_like_shell_command(command, executable_hints=executable_hints):
            return False

    return True


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
        commands, operators = split_shell_chain(stripped)
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


def build_yaml_command_split_report(
    cases_dir: Path | str,
    *,
    target_fields: tuple[str, ...] = DEFAULT_AUDIT_FIELDS,
    executable_hints: set[str] | None = None,
) -> dict[str, Any]:
    audit_report = build_yaml_command_audit_report(cases_dir, target_fields=target_fields)
    hints = executable_hints or set(DEFAULT_EXECUTABLE_HINTS)

    rewritable_matches: list[dict[str, Any]] = []
    blocked_matches: list[dict[str, Any]] = []
    rewritable_lines_count = 0
    blocked_lines_count = 0

    for item in audit_report["matches"]:
        safe_lines: list[dict[str, Any]] = []
        unsafe_lines: list[dict[str, Any]] = []
        for line in item["chained_lines"]:
            is_safe = shell_chain_is_split_safe(
                list(line["suggested_commands"]),
                list(line["operators"]),
                executable_hints=hints,
            )
            payload = dict(line)
            payload["split_safe"] = is_safe
            if is_safe:
                safe_lines.append(payload)
                rewritable_lines_count += 1
            else:
                unsafe_lines.append(payload)
                blocked_lines_count += 1

        enriched = {
            "file": item["file"],
            "case_id": item["case_id"],
            "field_name": item["field_name"],
            "field_path": item["field_path"],
            "rewritable_lines_count": len(safe_lines),
            "blocked_lines_count": len(unsafe_lines),
            "rewritable_lines": safe_lines,
            "blocked_lines": unsafe_lines,
        }
        if safe_lines:
            rewritable_matches.append(enriched)
        if unsafe_lines:
            blocked_matches.append(enriched)

    return {
        "status": "ok",
        "cases_dir": audit_report["cases_dir"],
        "target_fields": list(audit_report["target_fields"]),
        "files_scanned": audit_report["files_scanned"],
        "matches_count": audit_report["matches_count"],
        "rewritable_matches_count": len(rewritable_matches),
        "blocked_matches_count": len(blocked_matches),
        "rewritable_lines_count": rewritable_lines_count,
        "blocked_lines_count": blocked_lines_count,
        "rewritable_matches": rewritable_matches,
        "blocked_matches": blocked_matches,
    }


def _literal_block_indent(line: str) -> str:
    leading = line[: len(line) - len(line.lstrip(" "))]
    remainder = line[len(leading):]
    if remainder.startswith("- "):
        return f"{leading}    "
    return f"{leading}  "


def _rewrite_yaml_commands_in_text(text: str, rewritable_matches: list[dict[str, Any]]) -> tuple[str, int, list[dict[str, Any]]]:
    lines = text.splitlines()
    replacements_by_raw: dict[str, list[list[str]]] = {}
    for item in rewritable_matches:
        for line in item["rewritable_lines"]:
            raw_line = str(line["raw_line"]).strip()
            commands = [str(command).strip() for command in line["suggested_commands"] if str(command).strip()]
            if not raw_line or not commands:
                continue
            replacements_by_raw.setdefault(raw_line, []).append(commands)

    applied = 0
    rewritten: list[str] = []
    for original in lines:
        stripped = original.strip()
        queued = replacements_by_raw.get(stripped)
        if queued:
            commands = queued.pop(0)
            indent = original[: len(original) - len(original.lstrip(" "))]
            rewritten.extend(f"{indent}{command}" for command in commands)
            applied += 1
            continue

        replaced_inline = False
        for raw_line, pending in replacements_by_raw.items():
            if not pending or raw_line not in original:
                continue
            prefix, sep, suffix = original.partition(raw_line)
            if not sep:
                continue
            if suffix.strip():
                continue
            if not prefix.rstrip().endswith(":"):
                continue
            commands = pending.pop(0)
            rewritten.append(f"{prefix.rstrip()} |")
            indent = _literal_block_indent(original)
            rewritten.extend(f"{indent}{command}" for command in commands)
            applied += 1
            replaced_inline = True
            break
        if replaced_inline:
            continue

        rewritten.append(original)

    unresolved: list[dict[str, Any]] = []
    for raw_line, pending in replacements_by_raw.items():
        if pending:
            unresolved.append(
                {
                    "raw_line": raw_line,
                    "remaining_occurrences": len(pending),
                    "suggested_commands": pending[0],
                }
            )

    new_text = "\n".join(rewritten)
    if text.endswith("\n"):
        new_text += "\n"
    return new_text, applied, unresolved


def rewrite_yaml_chained_commands(
    cases_dir: Path | str,
    *,
    target_fields: tuple[str, ...] = DEFAULT_AUDIT_FIELDS,
    executable_hints: set[str] | None = None,
    apply_changes: bool = False,
) -> dict[str, Any]:
    split_report = build_yaml_command_split_report(
        cases_dir,
        target_fields=target_fields,
        executable_hints=executable_hints,
    )
    rewritable_by_file: dict[str, list[dict[str, Any]]] = {}
    for item in split_report["rewritable_matches"]:
        rewritable_by_file.setdefault(item["file"], []).append(item)

    rewritten_files: list[dict[str, Any]] = []
    unresolved_files: list[dict[str, Any]] = []
    total_applied = 0

    for file_path, matches in sorted(rewritable_by_file.items()):
        path = Path(file_path)
        original_text = path.read_text(encoding="utf-8")
        rewritten_text, applied, unresolved = _rewrite_yaml_commands_in_text(original_text, matches)
        total_applied += applied
        file_payload = {
            "file": str(path),
            "applied_lines": applied,
            "rewritable_matches": len(matches),
            "changed": rewritten_text != original_text,
        }
        if apply_changes and rewritten_text != original_text:
            path.write_text(rewritten_text, encoding="utf-8")
        rewritten_files.append(file_payload)
        if unresolved:
            unresolved_files.append(
                {
                    "file": str(path),
                    "unresolved_lines": unresolved,
                }
            )

    return {
        "status": "ok",
        "apply_changes": apply_changes,
        "cases_dir": split_report["cases_dir"],
        "target_fields": list(split_report["target_fields"]),
        "files_scanned": split_report["files_scanned"],
        "matches_count": split_report["matches_count"],
        "rewritable_matches_count": split_report["rewritable_matches_count"],
        "blocked_matches_count": split_report["blocked_matches_count"],
        "rewritable_lines_count": split_report["rewritable_lines_count"],
        "blocked_lines_count": split_report["blocked_lines_count"],
        "applied_lines_count": total_applied,
        "rewritten_files_count": sum(1 for item in rewritten_files if item["changed"]),
        "rewritten_files": rewritten_files,
        "unresolved_files_count": len(unresolved_files),
        "unresolved_files": unresolved_files,
        "blocked_matches": split_report["blocked_matches"],
    }


def write_yaml_command_audit_report(
    report_path: Path | str,
    report: dict[str, Any],
) -> Path:
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
