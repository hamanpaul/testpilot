"""CommandResolver — command resolution and heuristic fallback logic.

Extracted from plugin.py to demonstrate recommended plugin file
organisation.  The class relies on the parent *Plugin* instance for
helper methods but is otherwise self‑contained.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
import shlex
from typing import Any

from testpilot.yaml_command_audit import (
    shell_chain_is_split_safe,
    split_shell_chain,
)


class CommandResolver:
    """Isolates command resolution and heuristic fallback from execute_step."""

    def __init__(self, plugin: Any) -> None:
        self._plugin = plugin

    @staticmethod
    def as_mapping(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def extract_cli_fragments(self, text: str) -> list[str]:
        if not text:
            return []

        p = self._plugin
        token_pattern = "|".join(re.escape(token) for token in p.ROOT_COMMAND_TOKENS)
        root_pattern = re.compile(rf"(?<![A-Za-z0-9_])(?:{token_pattern})\b")
        commands: list[str] = []
        seen: set[str] = set()
        for raw_line in str(text).splitlines():
            normalized = p._normalize_command_text(raw_line)
            if not normalized:
                continue

            if p._looks_shell_command(normalized):
                raw_parts = self.split_safe_shell_commands(normalized)
            else:
                matches = list(root_pattern.finditer(normalized))
                if not matches:
                    continue
                if len(matches) > 1:
                    raw_parts = []
                    for index, match in enumerate(matches):
                        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
                        fragment = normalized[match.start():end].strip().strip("`'\"")
                        fragment = re.sub(r";.*$", "", fragment).strip()
                        fragment = re.sub(r",?\s*(?:and|then)\s*$", "", fragment, flags=re.IGNORECASE)
                        fragment = fragment.rstrip("，。,; ")
                        if fragment:
                            raw_parts.extend(self.split_safe_shell_commands(fragment))
                else:
                    fragment = normalized[matches[0].start():].strip().strip("`'\"")
                    fragment = fragment.rstrip("，。;")
                    raw_parts = self.split_safe_shell_commands(fragment)
                    if len(raw_parts) == 1 and raw_parts[0] == fragment and ";" in fragment:
                        raw_parts = re.split(rf";\s*(?=(?:{token_pattern})\b)", fragment)

            for part in raw_parts:
                sanitized = self.sanitize_cli_fragment(part)
                if not sanitized or not self.looks_executable(sanitized) or sanitized in seen:
                    continue
                commands.append(sanitized)
                seen.add(sanitized)
        return commands

    def prefer_synthesized_readback(
        self,
        case: dict[str, Any],
        step: dict[str, Any],
        raw_command: str,
        candidate_commands: list[str],
    ) -> str | None:
        p = self._plugin
        capture_name = str(step.get("capture", "")).strip()
        if not capture_name:
            return None

        synthesized = p._synthesize_readback_command(case, capture_name)
        if not synthesized:
            return None

        normalized = p._normalize_command_text(raw_command).lower()
        if candidate_commands and any("?" in command for command in candidate_commands):
            return None
        if not self.command_starts_executable(raw_command):
            return synthesized
        if len(candidate_commands) > 1:
            return synthesized
        if normalized.count("wifi.") >= 3:
            return synthesized
        if " > " in normalized and normalized.count("wifi.") >= 2:
            return synthesized
        if any(
            marker in normalized
            for marker in (
                "verify ",
                "read back",
                "read-only api",
                "get ",
                "check ",
                "using wireshark",
                "repeat step",
                "_x0001_",
            )
        ):
            return synthesized
        if candidate_commands and all("=" in command and "?" not in command for command in candidate_commands):
            return synthesized
        return None

    def sanitize_cli_fragment(self, fragment: str) -> str:
        p = self._plugin
        text = p._normalize_command_text(fragment)
        if not text:
            return ""

        text = text.lstrip("`'\"; ")

        # Remove console prompt tails appended from captured transcript.
        prompt_match = re.search(r"\s+root@[^:]+:[^#\n]*#.*$", text)
        if prompt_match:
            text = text[:prompt_match.start()].strip()

        # Transcript often embeds "command > expected-output"; keep command side only.
        if " > " in text:
            left, right = text.split(" > ", 1)
            right = right.lstrip()
            if right.startswith(("WiFi.", "ERROR", "root@")):
                text = left.strip()

        # Some Excel-derived prose appends expected samples after a real readback query.
        if text.count("WiFi.") > 1 or "?" in text or "|" in text:
            text = re.sub(r"\s+WiFi\.[A-Za-z0-9_.{}-]+\s*=\s*.*$", "", text).strip()

        text = p._truncate_ubus_function_tail(text)

        if p._looks_shell_command(text):
            stripped = text.strip()
            # Complex shell fragments may legitimately contain an odd total number of quote
            # characters across nested sed/grep expressions; preserve them as-authored.
            if (
                "$(" in stripped
                or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", stripped)
                or any(op in stripped for op in ("&&", "||", ";", "|"))
            ):
                return stripped
            return p._quote_ubus_operand(stripped)

        # In malformed transcript strings, quotes are often unbalanced; remove them to recover.
        if text.count('"') % 2 == 1:
            text = text.replace('"', "")
        if text.count("'") % 2 == 1:
            text = text.replace("'", "")

        try:
            tokens = shlex.split(text, posix=True)
        except ValueError:
            return text

        trimmed = p._trim_transcript_tokens(tokens)
        if not trimmed:
            return p._quote_ubus_operand(text)
        return p._quote_ubus_operand(p._join_shell_tokens(trimmed))

    def split_safe_shell_commands(self, command: str) -> list[str]:
        p = self._plugin
        normalized = p._normalize_command_text(command)
        if not normalized:
            return []

        commands, operators = split_shell_chain(normalized)
        if shell_chain_is_split_safe(
            commands,
            operators,
            executable_hints=p._shell_executable_hints(),
        ):
            return [item.strip() for item in commands if item.strip()]
        return [normalized]

    def looks_executable(self, command: str) -> bool:
        p = self._plugin
        stripped = command.strip()
        if not stripped:
            return False
        first = stripped.split(maxsplit=1)[0].strip("`'\"")
        first_base = first.rsplit("/", 1)[-1]
        if first_base in p.EXECUTABLE_TOKENS:
            if first_base in p.INTERACTIVE_ROOT_TOKENS and len(stripped.split()) == 1:
                return False
            return p._looks_plausible_cli_command(stripped)
        return p._looks_shell_command(stripped)

    def command_starts_executable(self, command: str) -> bool:
        stripped = command.strip()
        if not stripped:
            return False
        return self._plugin._looks_shell_command(stripped)

    @staticmethod
    def is_unexecutable_result(result: dict[str, Any]) -> bool:
        rc = int(result.get("returncode", 1))
        if rc in (126, 127):
            return True
        combined = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
        return ("not found" in combined) or ("unknown command" in combined) or ("syntax error" in combined)

    def select_fallback_commands(
        self,
        case: dict[str, Any],
        original_command: str,
        topology: Any,
        step_id: str,
    ) -> tuple[list[str], str]:
        p = self._plugin
        fragment_commands = [
            p._resolve_text(topology, command)
            for command in self.extract_cli_fragments(original_command)
        ]
        if fragment_commands:
            return fragment_commands, "extract_from_step_text"

        for field in ("verification_command", "hlapi_command"):
            raw = str(case.get(field, "")).strip()
            if not raw:
                continue
            fallback_commands = [
                p._resolve_text(topology, command)
                for command in self.extract_cli_fragments(raw)
            ]
            if not fallback_commands:
                fallback = self.sanitize_cli_fragment(p._first_non_empty_line(raw))
                if fallback and self.looks_executable(fallback):
                    fallback_commands = [
                        p._resolve_text(topology, command)
                        for command in self.split_safe_shell_commands(fallback)
                    ]
            if not fallback_commands:
                continue
            if field == "hlapi_command" and not all(
                p._is_runtime_hlapi_command(command) for command in fallback_commands
            ):
                continue
            return fallback_commands, f"fallback_{field}"

        return [f'echo "[skip] non-executable step {step_id}"'], "fallback_skip_echo"

    def resolve(
        self,
        case: dict[str, Any],
        step: dict[str, Any],
        topology: Any,
    ) -> tuple[list[str], str]:
        """Return (commands_to_run, fallback_reason)."""
        step_id = str(step.get("id", "step"))
        raw_command = str(step.get("command", "")).strip()
        capture_name = str(step.get("capture", "")).strip()
        resolved_command = self._plugin._resolve_text(topology, raw_command)
        command_to_run = resolved_command
        commands_to_run: list[str] = []
        fallback_reason = ""

        candidate_commands = [
            self._plugin._resolve_text(topology, command)
            for command in self.extract_cli_fragments(command_to_run)
        ]
        preferred_capture_command = self.prefer_synthesized_readback(
            case, step, raw_command, candidate_commands
        )
        if preferred_capture_command:
            commands_to_run = [self._plugin._resolve_text(topology, preferred_capture_command)]
            fallback_reason = "synthesized_capture_query"
        elif candidate_commands:
            commands_to_run = candidate_commands
            if len(candidate_commands) > 1 or candidate_commands[0] != command_to_run:
                fallback_reason = "extract_from_step_text"
        else:
            command_to_run = self.sanitize_cli_fragment(command_to_run)
            if command_to_run:
                commands_to_run = self.split_safe_shell_commands(command_to_run)

        if not commands_to_run or not all(self.looks_executable(cmd) for cmd in commands_to_run):
            if not capture_name and not self.command_starts_executable(raw_command):
                commands_to_run = [f'echo "[skip] non-executable step {step_id}"']
                fallback_reason = "fallback_skip_echo"
            else:
                commands_to_run, fallback_reason = self.select_fallback_commands(
                    case, raw_command, topology, step_id
                )

        return commands_to_run, fallback_reason

    def handle_runtime_fallback(
        self,
        case: dict[str, Any],
        step: dict[str, Any],
        topology: Any,
        result: Mapping[str, Any],
        current_commands: list[str],
        current_fallback_reason: str,
    ) -> tuple[list[str], str] | None:
        """Return new (commands, reason) if retry needed, or None."""
        if current_fallback_reason:
            return None
        result_map = self.as_mapping(result)
        if not self.is_unexecutable_result(result_map):
            return None
        raw_command = str(step.get("command", "")).strip()
        step_id = str(step.get("id", "step"))
        fallback_commands, reason = self.select_fallback_commands(
            case, raw_command, topology, step_id
        )
        if fallback_commands != current_commands:
            return fallback_commands, reason
        return None
