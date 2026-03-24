"""wifi_llapi plugin — Wifi LLAPI test automation for prplOS/Broadcom."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
import re
import shlex
import time
from typing import Any

from testpilot.core.plugin_base import PluginBase
from testpilot.schema.case_schema import load_cases_dir
from testpilot.transport.base import StubTransport
from testpilot.yaml_command_audit import (
    looks_like_shell_command,
    shell_chain_is_split_safe,
    split_shell_chain,
)

log = logging.getLogger(__name__)


class Plugin(PluginBase):
    """Wifi LLAPI 測試 plugin。

    測試 prplOS WiFi.Radio / WiFi.AccessPoint 的 LLAPI 介面，
    透過 ubus-cli 與 wl 指令驗證參數讀寫與功能正確性。
    """

    CLI_FALLBACK_TOKENS = (
        "ubus-cli",
        "wl",
        "iw",
        "ifconfig",
        "wpa_cli",
        "ping",
        "arping",
        "iperf",
        "cat",
    )
    EXECUTABLE_TOKENS = CLI_FALLBACK_TOKENS + (
        "echo",
        "printf",
        "sleep",
        "killall",
        "rm",
        "mkdir",
        "grep",
        "sed",
        "awk",
        "true",
        "false",
        "wpa_supplicant",
    )
    ROOT_COMMAND_TOKENS = CLI_FALLBACK_TOKENS + (
        "echo",
        "printf",
        "sleep",
        "killall",
        "rm",
        "mkdir",
        "true",
        "false",
        "wpa_supplicant",
    )
    INTERACTIVE_ROOT_TOKENS = ("ubus-cli", "wpa_cli")

    def __init__(self) -> None:
        self._transports: dict[str, Any] = {}
        self._device_specs: dict[str, dict[str, Any]] = {}
        self._sta_env_verified = False

    @property
    def name(self) -> str:
        return "wifi_llapi"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def cases_dir(self) -> Path:
        return Path(__file__).parent / "cases"

    def discover_cases(self) -> list[dict[str, Any]]:
        return load_cases_dir(self.cases_dir)

    @staticmethod
    def _first_non_empty_line(text: str) -> str:
        for raw in text.splitlines():
            line = raw.strip()
            if line:
                return line
        return ""

    @staticmethod
    def _to_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_number(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_mapping(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _resolve_text(self, topology: Any, text: str) -> str:
        resolver = getattr(topology, "resolve", None)
        if callable(resolver):
            try:
                return str(resolver(text))
            except Exception:  # pragma: no cover - defensive
                log.exception("[%s] resolve failed, keep original text", self.name)
        return text

    def _load_factory(self) -> Any:
        try:
            module = importlib.import_module("testpilot.transport.factory")
        except Exception as exc:
            log.warning(
                "[%s] testpilot.transport.factory unavailable, fallback StubTransport: %s",
                self.name,
                exc,
            )
            return None

        create_transport = getattr(module, "create_transport", None)
        if not callable(create_transport):
            log.warning("[%s] create_transport not callable, fallback StubTransport", self.name)
            return None
        return create_transport

    def _create_transport_instance(self, transport_type: str, merged_config: dict[str, Any]) -> Any:
        create_transport = self._load_factory()
        if create_transport is None:
            return StubTransport()

        kwargs_wo_transport = dict(merged_config)
        kwargs_wo_transport.pop("transport", None)
        with_transport = dict(kwargs_wo_transport)
        with_transport.setdefault("transport", transport_type)

        attempts = (
            lambda: create_transport(transport_type, merged_config),
            lambda: create_transport(transport=transport_type, config=merged_config),
            lambda: create_transport(transport_type, **kwargs_wo_transport),
            lambda: create_transport(**with_transport),
        )

        for attempt in attempts:
            try:
                transport = attempt()
            except TypeError:
                continue
            except Exception as exc:
                log.warning("[%s] create_transport(%s) failed: %s", self.name, transport_type, exc)
                return StubTransport()
            if transport is not None:
                return transport

        log.warning("[%s] create_transport signature mismatch, fallback StubTransport", self.name)
        return StubTransport()

    def _connect_transport(self, device: str, transport: Any, merged_config: dict[str, Any]) -> bool:
        connect_kwargs = dict(merged_config)
        for key in ("transport", "role", "config"):
            connect_kwargs.pop(key, None)
        try:
            try:
                transport.connect(**connect_kwargs)
            except TypeError:
                transport.connect()
        except Exception as exc:
            log.warning("[%s] connect failed for %s: %s", self.name, device, exc)
            return False

        return bool(getattr(transport, "is_connected", True))

    def _extract_cli_fragment(self, text: str) -> str | None:
        fragments = self._extract_cli_fragments(text)
        if fragments:
            return fragments[0]
        return None

    @staticmethod
    def _normalize_command_text(text: str) -> str:
        cleaned = str(text or "").replace("\r", " ")
        cleaned = re.sub(r"_x[0-9A-Fa-f]{4}_", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def _shell_executable_hints(cls) -> set[str]:
        return {token.rsplit("/", 1)[-1] for token in cls.EXECUTABLE_TOKENS}

    @classmethod
    def _looks_shell_command(cls, command: str) -> bool:
        normalized = cls._normalize_command_text(command)
        first = normalized.split(maxsplit=1)[0].strip("`'\"") if normalized else ""
        if "/" in first and not first.startswith(("/", "./", "../", "~/")):
            return False
        return looks_like_shell_command(
            normalized,
            executable_hints=cls._shell_executable_hints(),
        )

    def _split_safe_shell_commands(self, command: str) -> list[str]:
        normalized = self._normalize_command_text(command)
        if not normalized:
            return []

        commands, operators = split_shell_chain(normalized)
        if shell_chain_is_split_safe(
            commands,
            operators,
            executable_hints=self._shell_executable_hints(),
        ):
            return [item.strip() for item in commands if item.strip()]
        return [normalized]

    def _extract_cli_fragments(self, text: str) -> list[str]:
        if not text:
            return []

        token_pattern = "|".join(re.escape(token) for token in self.ROOT_COMMAND_TOKENS)
        root_pattern = re.compile(rf"(?<![A-Za-z0-9_])(?:{token_pattern})\b")
        commands: list[str] = []
        seen: set[str] = set()
        for raw_line in str(text).splitlines():
            normalized = self._normalize_command_text(raw_line)
            if not normalized:
                continue

            if self._looks_shell_command(normalized):
                raw_parts = self._split_safe_shell_commands(normalized)
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
                            raw_parts.extend(self._split_safe_shell_commands(fragment))
                else:
                    fragment = normalized[matches[0].start():].strip().strip("`'\"")
                    fragment = fragment.rstrip("，。;")
                    raw_parts = self._split_safe_shell_commands(fragment)
                    if len(raw_parts) == 1 and raw_parts[0] == fragment and ";" in fragment:
                        raw_parts = re.split(rf";\s*(?=(?:{token_pattern})\b)", fragment)

            for part in raw_parts:
                sanitized = self._sanitize_cli_fragment(part)
                if not sanitized or not self._looks_executable(sanitized) or sanitized in seen:
                    continue
                commands.append(sanitized)
                seen.add(sanitized)
        return commands

    @staticmethod
    def _join_shell_tokens(tokens: list[str]) -> str:
        operators = {"|", "||", "&&", ";", "(", ")", ">", ">>", "<", "2>", "2>>"}
        safe_unquoted = re.compile(r"[A-Za-z0-9_./:@%+=,-]+$")
        parts: list[str] = []
        for token in tokens:
            if token in operators:
                parts.append(token)
                continue
            if safe_unquoted.fullmatch(token):
                parts.append(token)
            else:
                parts.append(shlex.quote(token))
        return " ".join(parts).strip()

    def _trim_transcript_tokens(self, tokens: list[str]) -> list[str]:
        if not tokens:
            return []

        cleaned: list[str] = []
        seen_pipe = False
        seen_wifi_assignment = False

        for token in tokens:
            if token in {";", "&&", "||"}:
                break
            if token in {">", ">>", "<", "1>", "2>", "2>>"}:
                break
            if token in self.CLI_FALLBACK_TOKENS and cleaned:
                # Stop at next command; each step should execute one command deterministically.
                break
            if token.startswith("//") or token.startswith("#"):
                break
            if token.startswith("root@"):
                break

            lowered = token.lower()
            if lowered.startswith(("error:", "grep:", "root@")):
                break

            if token.startswith("WiFi.") and "=" in token:
                allow_first_assignment = (
                    bool(cleaned)
                    and cleaned[0] == "ubus-cli"
                    and not seen_pipe
                    and not seen_wifi_assignment
                )
                if not allow_first_assignment:
                    break
                seen_wifi_assignment = True
                cleaned.append(token)
                continue

            cleaned.append(token)
            if token == "|":
                seen_pipe = True

        return cleaned

    def _sanitize_cli_fragment(self, fragment: str) -> str:
        text = self._normalize_command_text(fragment)
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

        text = self._truncate_ubus_function_tail(text)

        if self._looks_shell_command(text):
            stripped = text.strip()
            # Complex shell fragments may legitimately contain an odd total number of quote
            # characters across nested sed/grep expressions; preserve them as-authored.
            if (
                "$(" in stripped
                or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", stripped)
                or any(op in stripped for op in ("&&", "||", ";", "|"))
            ):
                return stripped
            return self._quote_ubus_operand(stripped)

        # In malformed transcript strings, quotes are often unbalanced; remove them to recover.
        if text.count('"') % 2 == 1:
            text = text.replace('"', "")
        if text.count("'") % 2 == 1:
            text = text.replace("'", "")

        try:
            tokens = shlex.split(text, posix=True)
        except ValueError:
            return text

        trimmed = self._trim_transcript_tokens(tokens)
        if not trimmed:
            return self._quote_ubus_operand(text)
        return self._quote_ubus_operand(self._join_shell_tokens(trimmed))

    @staticmethod
    def _truncate_ubus_function_tail(text: str) -> str:
        stripped = text.strip()
        prefix = "ubus-cli WiFi."
        if not stripped.startswith(prefix) or "(" not in stripped:
            return stripped

        operand_start = len("ubus-cli ")
        depth = 0
        seen_open = False
        end_index: int | None = None
        for index, ch in enumerate(stripped[operand_start:], start=operand_start):
            if ch == "(":
                depth += 1
                seen_open = True
                continue
            if ch == ")" and depth > 0:
                depth -= 1
                if depth == 0 and seen_open:
                    end_index = index
                    break

        if end_index is None:
            return stripped

        tail = stripped[end_index + 1 :].lstrip()
        if not tail:
            return stripped
        if tail.startswith(("|", ">", ";", "&&", "||", "2>")):
            return stripped
        return stripped[: end_index + 1]

    @staticmethod
    def _quote_ubus_operand(command: str) -> str:
        stripped = command.strip()
        if not stripped.startswith("ubus-cli "):
            return stripped

        parts = stripped.split(maxsplit=2)
        if len(parts) < 2:
            return stripped

        operand = parts[1].strip("`'\"")
        if not operand.startswith("WiFi."):
            return stripped
        if not any(ch in operand for ch in ("(", ")", "?", "*")):
            return stripped

        remainder = f" {parts[2]}" if len(parts) > 2 else ""
        return f'ubus-cli "{operand}"{remainder}'.strip()

    @staticmethod
    def _command_starts_executable(command: str) -> bool:
        stripped = command.strip()
        if not stripped:
            return False
        return Plugin._looks_shell_command(stripped)

    @staticmethod
    def _field_name_from_capture(case: dict[str, Any], capture_name: str) -> str:
        if not capture_name:
            return ""
        prefix = f"{capture_name}."
        for criterion in case.get("pass_criteria", []):
            if not isinstance(criterion, dict):
                continue
            field = str(criterion.get("field", "")).strip()
            if not field.startswith(prefix):
                continue
            suffix = field[len(prefix):].strip()
            if suffix:
                return suffix.rstrip("()").split(".")[-1]
        return ""

    def _synthesize_readback_command(self, case: dict[str, Any], capture_name: str) -> str | None:
        source = self._as_mapping(case.get("source"))
        object_path = str(source.get("object", "")).strip()
        if not object_path:
            return None
        if not object_path.endswith("."):
            object_path = f"{object_path}."
        object_path = object_path.replace("{i}", "*")

        field_name = self._field_name_from_capture(case, capture_name)
        source_api = str(source.get("api", "")).strip()
        if source_api.endswith("()") and not source_api.lower().startswith("get"):
            return None
        api = field_name or source_api
        if not api:
            return None
        if source_api.endswith("()"):
            return f'ubus-cli "{object_path}{api}"'
        if "AssociatedDevice.*." in object_path and field_name:
            parent_object = object_path.split("AssociatedDevice.*.", 1)[0]
            return (
                f'ubus-cli "{parent_object}?" '
                f'| grep -E "AssociatedDevice\\.[0-9]+\\.{re.escape(field_name)}"'
            )
        return f'ubus-cli "{object_path}{api.rstrip("?")}?"'

    def _prefer_synthesized_readback(
        self,
        case: dict[str, Any],
        step: dict[str, Any],
        raw_command: str,
        candidate_commands: list[str],
    ) -> str | None:
        capture_name = str(step.get("capture", "")).strip()
        if not capture_name:
            return None

        synthesized = self._synthesize_readback_command(case, capture_name)
        if not synthesized:
            return None

        normalized = self._normalize_command_text(raw_command).lower()
        if candidate_commands and any("?" in command for command in candidate_commands):
            return None
        if not self._command_starts_executable(raw_command):
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

    def _looks_executable(self, command: str) -> bool:
        stripped = command.strip()
        if not stripped:
            return False
        first = stripped.split(maxsplit=1)[0].strip("`'\"")
        first_base = first.rsplit("/", 1)[-1]
        if first_base in self.EXECUTABLE_TOKENS:
            if first_base in self.INTERACTIVE_ROOT_TOKENS and len(stripped.split()) == 1:
                return False
            return self._looks_plausible_cli_command(stripped)
        return self._looks_shell_command(stripped)

    @staticmethod
    def _looks_plausible_cli_command(command: str) -> bool:
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()
        if not tokens:
            return False

        first = tokens[0].strip("`'\"").rsplit("/", 1)[-1]
        rest = tokens[1:]
        prose_tokens = {
            "again",
            "after",
            "against",
            "and",
            "as",
            "compare",
            "command",
            "confirm",
            "do",
            "get",
            "set",
            "then",
            "using",
            "verification",
            "when",
            "with",
        }
        normalized_rest = {token.strip("`'\" ,;:.").lower() for token in rest if token.strip("`'\" ,;:.")}
        if first == "ubus-cli":
            if not rest:
                return False
            second = rest[0].strip("`'\"")
            if not second.startswith("WiFi."):
                return False
            return not bool(normalized_rest.intersection(prose_tokens))
        if first in {"wl", "iw", "wpa_cli"}:
            return bool(rest) and not bool(normalized_rest.intersection(prose_tokens))
        return True

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            lines = [f"{key}={val}" for key, val in value.items()]
            return "\n".join(lines)
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value)

    @classmethod
    def _preview_value(cls, value: Any, limit: int = 240) -> str:
        text = cls._stringify(value).replace("\n", "\\n")
        if len(text) <= limit:
            return text
        return f"{text[:limit]}...(truncated {len(text) - limit} chars)"

    @classmethod
    def _is_runtime_hlapi_command(cls, command: str) -> bool:
        normalized = cls._normalize_command_text(command)
        if not normalized or not cls._command_starts_executable(normalized):
            return False

        lower = normalized.lower()
        if "get command:" in lower or "set command:" in lower:
            return False
        if re.search(r"\([^)]*:[A-Za-z]", normalized):
            return False
        if re.search(r"\)\s+[A-Za-z0-9_.-]", normalized) and "?" not in normalized and "=" not in normalized:
            return False

        payload = normalized.split(maxsplit=1)[1] if " " in normalized else ""
        if not payload:
            return False
        return "?" in payload or "=" in payload or payload.endswith(")")

    def _select_fallback_commands(
        self,
        case: dict[str, Any],
        original_command: str,
        topology: Any,
        step_id: str,
    ) -> tuple[list[str], str]:
        fragment_commands = [
            self._resolve_text(topology, command)
            for command in self._extract_cli_fragments(original_command)
        ]
        if fragment_commands:
            return fragment_commands, "extract_from_step_text"

        for field in ("verification_command", "hlapi_command"):
            raw = str(case.get(field, "")).strip()
            if not raw:
                continue
            fallback_commands = [
                self._resolve_text(topology, command)
                for command in self._extract_cli_fragments(raw)
            ]
            if not fallback_commands:
                fallback = self._sanitize_cli_fragment(self._first_non_empty_line(raw))
                if fallback and self._looks_executable(fallback):
                    fallback_commands = [
                        self._resolve_text(topology, command)
                        for command in self._split_safe_shell_commands(fallback)
                    ]
            if not fallback_commands:
                continue
            if field == "hlapi_command" and not all(
                self._is_runtime_hlapi_command(command) for command in fallback_commands
            ):
                continue
            return fallback_commands, f"fallback_{field}"

        return [f'echo "[skip] non-executable step {step_id}"'], "fallback_skip_echo"

    @staticmethod
    def _is_unexecutable_result(result: dict[str, Any]) -> bool:
        rc = int(result.get("returncode", 1))
        if rc in (126, 127):
            return True
        combined = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
        return ("not found" in combined) or ("unknown command" in combined) or ("syntax error" in combined)

    @staticmethod
    def _extract_key_values(output: str) -> dict[str, Any]:
        captured: dict[str, Any] = {}
        if not output:
            return captured

        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    captured[str(key)] = value
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            captured[str(key)] = value
        except Exception:
            pass

        logical_lines: list[str] = []
        pending = ""
        line_start_pattern = re.compile(r"^[> ]*[A-Za-z0-9_.()/-]+\s*[:=]")
        for raw in output.splitlines():
            candidate = raw.strip()
            if not candidate:
                continue
            if pending and not line_start_pattern.match(candidate):
                pending = f"{pending}{candidate}"
                continue
            if pending:
                logical_lines.append(pending)
            pending = candidate
        if pending:
            logical_lines.append(pending)

        for line in logical_lines:
            line = line.strip()
            if not line:
                continue
            line = line.lstrip("> ").strip()
            line = re.sub(r"^['\"];\s*", "", line)
            if not line:
                continue
            match = re.match(r"([A-Za-z0-9_.()/-]+)\s*[:=]\s*(.*)$", line)
            if not match:
                continue
            key, value = match.groups()
            normalized = value.strip().strip("'\"")
            # Strip trailing ubus object/array delimiters left by
            # method-call outputs like getRadioAirStats() / getRadioStats().
            normalized = re.sub(r"[,}\]]+$", "", normalized).strip()
            if normalized or value.strip() in {"", '""', "''"}:
                captured[key] = normalized

        return captured

    @classmethod
    def _is_command_echo_line(cls, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped.startswith(">"):
            return True

        first = stripped.split(maxsplit=1)[0].strip("`'\"")
        first_base = first.rsplit("/", 1)[-1]
        return first_base in cls.EXECUTABLE_TOKENS

    @classmethod
    def _normalize_transcript_noise(cls, text: str) -> str:
        if not text:
            return ""
        lines: list[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            line = re.sub(r"^['\"];\s*", "", line)
            line = line.strip()
            if not line:
                continue
            if cls._is_command_echo_line(line):
                continue
            if line in {">", "$", "#"}:
                continue
            if line.startswith("root@"):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _field_fallback_output(self, aggregate_output: str, field: str) -> str:
        cleaned = self._normalize_transcript_noise(aggregate_output)
        if not cleaned:
            return ""
        key = field.split(".")[-1].strip() if field else ""
        key = key.rstrip("()")
        if not key:
            return cleaned

        pattern = re.compile(rf"(^|[.\s]){re.escape(key)}([:=.\s(]|$)", re.IGNORECASE)
        matched = [line for line in cleaned.splitlines() if pattern.search(line)]
        if matched:
            return "\n".join(matched).strip()
        return ""

    def _resolve_field(self, payload: dict[str, Any], field: str) -> Any:
        current: Any = payload
        for part in field.split("."):
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                    continue
                suffix_matches = [
                    value
                    for key, value in current.items()
                    if isinstance(key, str) and (key == part or key.endswith(f".{part}"))
                ]
                if len(suffix_matches) == 1:
                    current = suffix_matches[0]
                    continue
            return None
        return current

    def _build_eval_context(self, case: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
        step_results = self._as_mapping(results.get("steps"))
        context: dict[str, Any] = {"steps": {}, "_aggregate_output": ""}
        aggregate_lines: list[str] = []
        aggregate_fields: dict[str, Any] = {}

        steps_meta: dict[str, dict[str, Any]] = {}
        for step in case.get("steps", []):
            if not isinstance(step, dict):
                continue
            step_id = str(step.get("id", "")).strip()
            if step_id:
                steps_meta[step_id] = step

        for step_id, result in step_results.items():
            sid = str(step_id)
            item = self._as_mapping(result)
            output = self._normalize_transcript_noise(str(item.get("output", "")))
            parsed = self._extract_key_values(output)
            user_captured = item.get("captured")
            if isinstance(user_captured, dict):
                parsed.update(user_captured)

            step_context = {
                "success": bool(item.get("success", False)),
                "output": output,
                "captured": parsed,
                "returncode": item.get("returncode"),
            }
            context["steps"][sid] = step_context
            context[sid] = step_context
            aggregate_fields.update(parsed)

            if output:
                aggregate_lines.append(output)

            capture_name = str(steps_meta.get(sid, {}).get("capture", "")).strip()
            if capture_name:
                context[capture_name] = parsed if parsed else output

        aggregate_output = "\n".join(aggregate_lines).strip()
        context["_aggregate_output"] = aggregate_output
        if "result" not in context:
            context["result"] = aggregate_fields if aggregate_fields else aggregate_output
        return context

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        op = operator.strip().lower()
        actual_text = self._stringify(actual)
        expected_text = self._stringify(expected)
        normalized_actual = actual_text.strip().strip("'\"")
        normalized_expected = expected_text.strip().strip("'\"")

        if op in {"contains"}:
            return expected_text in actual_text or normalized_expected in normalized_actual
        if op in {"not_contains"}:
            return expected_text not in actual_text and normalized_expected not in normalized_actual
        if op in {"equals", "==", "eq"}:
            return actual_text == expected_text or normalized_actual == normalized_expected
        if op in {"!=", "not_equals", "ne"}:
            return actual_text != expected_text and normalized_actual != normalized_expected
        if op in {"regex", "matches"}:
            try:
                return re.search(expected_text, actual_text) is not None
            except re.error:
                log.warning("[%s] invalid regex: %s", self.name, expected_text)
                return False
        if op in {"not_empty"}:
            return bool(actual_text.strip())
        if op in {"empty"}:
            return not actual_text.strip()
        if op in {">", ">=", "<", "<="}:
            left_num = self._to_number(actual)
            right_num = self._to_number(expected)
            if left_num is not None and right_num is not None:
                if op == ">":
                    return left_num > right_num
                if op == ">=":
                    return left_num >= right_num
                if op == "<":
                    return left_num < right_num
                return left_num <= right_num
            if op == ">":
                return actual_text > expected_text
            if op == ">=":
                return actual_text >= expected_text
            if op == "<":
                return actual_text < expected_text
            return actual_text <= expected_text

        log.warning("[%s] unsupported operator: %s", self.name, operator)
        return False

    def _resolve_ping_target(self, topology: Any, device_name: str) -> str | None:
        device_cfg: dict[str, Any] = {}
        try:
            getter = getattr(topology, "get_device", None)
            if callable(getter):
                got = getter(device_name)
                if isinstance(got, dict):
                    device_cfg = got
        except Exception:
            device_cfg = {}

        for key in ("host", "ip", "management_ip", "lan_ip", "wan_ip"):
            value = device_cfg.get(key)
            if value:
                return self._resolve_text(topology, str(value))

        variables = getattr(topology, "variables", {})
        if isinstance(variables, dict):
            for key in (f"{device_name}_IP", f"{device_name.lower()}_ip"):
                if key in variables and variables[key]:
                    return self._resolve_text(topology, str(variables[key]))
        return None

    def _iter_env_script_commands(self, script: str) -> list[tuple[str, str]]:
        commands: list[tuple[str, str]] = []
        target = "STA"

        # Pre-process: join continuation lines with unbalanced single quotes
        # (e.g. multi-line printf '...\n...\n...' → single line).
        raw_lines: list[str] = []
        pending: str | None = None
        for raw in script.splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            if pending is not None:
                pending = pending + "\n" + stripped
                if pending.count("'") % 2 == 0:
                    raw_lines.append(pending)
                    pending = None
            elif stripped.count("'") % 2 != 0:
                pending = stripped
            else:
                raw_lines.append(stripped)
        if pending is not None:
            raw_lines.append(pending)

        for line in raw_lines:
            lower_line = line.lower()
            if lower_line.endswith(":"):
                if "dut" in lower_line:
                    target = "DUT"
                    continue
                if "sta" in lower_line:
                    target = "STA"
                    continue

            # Keep exact quoted command for sta_env_setup lines that already
            # begin with an executable token (e.g. wpa_cli with nested quotes).
            first_token = line.split(maxsplit=1)[0].strip("`'\"")
            if first_token in self.CLI_FALLBACK_TOKENS or self._looks_shell_command(line):
                resolved_commands = self._split_safe_shell_commands(line)
            else:
                resolved_commands = self._extract_cli_fragments(line)
            for command in resolved_commands:
                if command:
                    commands.append((target, command))
        return commands

    def _run_yaml_env_script(
        self,
        case: dict[str, Any],
        topology: Any,
        *,
        field_name: str,
    ) -> bool:
        script = case.get(field_name)
        if not isinstance(script, str) or not script.strip():
            return True

        case_id = str(case.get("id", ""))
        for index, (target_name, raw_command) in enumerate(
            self._iter_env_script_commands(script),
            start=1,
        ):
            transport = self._transports.get(target_name)
            if transport is None:
                log.warning(
                    "[%s] setup_env: %s %s[%d] missing target transport=%s",
                    self.name,
                    case_id,
                    field_name,
                    index,
                    target_name,
                )
                return False

            command = self._resolve_text(topology, raw_command)
            result = self._execute_env_command(transport, command, timeout=45.0)
            if not self._env_command_succeeded(command, result):
                log.warning(
                    "[%s] setup_env: %s %s[%d] failed target=%s rc=%s cmd=%s out=%s",
                    self.name,
                    case_id,
                    field_name,
                    index,
                    target_name,
                    int(result.get("returncode", 1)),
                    self._preview_value(command, limit=96),
                    self._preview_value(self._env_output_text(result)),
                )
                return False
        return True

    def _run_sta_env_setup(self, case: dict[str, Any], topology: Any) -> bool:
        return self._run_yaml_env_script(case, topology, field_name="sta_env_setup")

    @classmethod
    def _env_output_text(cls, result: dict[str, Any]) -> str:
        stdout = str(result.get("stdout", "") or "")
        stderr = str(result.get("stderr", "") or "")
        return cls._normalize_transcript_noise(
            "\n".join(chunk for chunk in (stdout, stderr) if chunk).strip()
        )

    @classmethod
    def _env_command_succeeded(cls, command: str, result: dict[str, Any]) -> bool:
        output = cls._env_output_text(result)
        lowered_output = output.lower()
        normalized_command = cls._normalize_command_text(command)
        lowered_command = normalized_command.lower()

        if any(
            marker in lowered_output
            for marker in (
                "no data found",
                "syntax error",
                "unknown command",
                "/bin/ash:",
                "not found",
            )
        ):
            return False

        if "iw dev wl" in lowered_command and " link" in lowered_command:
            if "not connected" in lowered_output:
                return False
            return "connected to " in lowered_output or (
                "ssid:" in lowered_output
                and any(
                    marker in lowered_output
                    for marker in (
                        "signal:",
                        "tx bitrate",
                        "rx:",
                        "tx:",
                    )
                )
            )
        if "wpa_cli" in lowered_command and " ping" in lowered_command:
            return "PONG" in output.upper()
        if "wpa_cli" in lowered_command and " status" in lowered_command:
            return "wpa_state=COMPLETED" in output
        if lowered_command.startswith("hostapd -t "):
            return not any(
                marker in lowered_output
                for marker in (
                    "errors found in configuration file",
                    "failed to set up interface",
                    "failed to initialize interface",
                    "invalid ",
                )
            )
        if lowered_command.startswith("wl -i wl") and lowered_command.endswith(" bss"):
            return output.strip().lower() == "up"
        if "associateddevice" in lowered_command and "macaddress?" in lowered_command:
            return bool(re.search(r"([0-9a-f]{2}:){5}[0-9a-f]{2}", output, re.IGNORECASE))
        if "ubus-cli" in lowered_command and "?" in normalized_command:
            return bool(output.strip())

        return int(result.get("returncode", 1)) == 0

    def _run_required_command(
        self,
        *,
        transport: Any,
        case_id: str,
        label: str,
        command: str,
        timeout: float = 30.0,
    ) -> bool:
        result = self._execute_env_command(transport, command, timeout=timeout)
        if self._env_command_succeeded(command, result):
            return True
        rc = int(result.get("returncode", 1))
        log.warning(
            "[%s] verify_env: %s %s failed rc=%s cmd=%s out=%s",
            self.name,
            case_id,
            label,
            rc,
            self._preview_value(command, limit=120),
            self._preview_value(self._env_output_text(result)),
        )
        return False

    def _selected_sta_bands(self, case: dict[str, Any]) -> tuple[str, ...]:
        marker_chunks: list[str] = []
        for key in ("hlapi_command", "verification_command"):
            value = case.get(key)
            if isinstance(value, str) and value.strip():
                marker_chunks.append(value)

        source = self._as_mapping(case.get("source"))
        source_object = source.get("object")
        if isinstance(source_object, str) and source_object.strip():
            marker_chunks.append(source_object)

        steps = case.get("steps")
        if isinstance(steps, list):
            for step in steps:
                step_mapping = self._as_mapping(step)
                for key in ("command", "target", "capture"):
                    value = step_mapping.get(key)
                    if isinstance(value, str) and value.strip():
                        marker_chunks.append(value)

        pass_criteria = case.get("pass_criteria")
        if isinstance(pass_criteria, list):
            for criterion in pass_criteria:
                criterion_mapping = self._as_mapping(criterion)
                field = criterion_mapping.get("field")
                if isinstance(field, str) and field.strip():
                    marker_chunks.append(field)

        haystack = "\n".join(marker_chunks)
        band_patterns = (
            ("5g", (r"WiFi\.AccessPoint\.(?:1|2)\b", r"\bwl0(?:\.\d+)?\b")),
            ("6g", (r"WiFi\.AccessPoint\.(?:3|4)\b", r"\bwl1(?:\.\d+)?\b")),
            ("2.4g", (r"WiFi\.AccessPoint\.(?:5|6)\b", r"\bwl2(?:\.\d+)?\b")),
        )
        selected = [
            band
            for band, patterns in band_patterns
            if any(re.search(pattern, haystack) for pattern in patterns)
        ]
        return tuple(selected or ("5g", "6g", "2.4g"))

    def _has_explicit_wifi_bands(self, case: dict[str, Any]) -> bool:
        """Return True when the case explicitly references WiFi AP/radio bands."""
        marker_chunks: list[str] = []
        for key in ("hlapi_command", "verification_command"):
            value = case.get(key)
            if isinstance(value, str) and value.strip():
                marker_chunks.append(value)
        source = self._as_mapping(case.get("source"))
        source_object = source.get("object")
        if isinstance(source_object, str) and source_object.strip():
            marker_chunks.append(source_object)
        steps = case.get("steps")
        if isinstance(steps, list):
            for step in steps:
                step_mapping = self._as_mapping(step)
                for key in ("command", "target", "capture"):
                    value = step_mapping.get(key)
                    if isinstance(value, str) and value.strip():
                        marker_chunks.append(value)
        pass_criteria = case.get("pass_criteria")
        if isinstance(pass_criteria, list):
            for criterion in pass_criteria:
                criterion_mapping = self._as_mapping(criterion)
                field = criterion_mapping.get("field")
                if isinstance(field, str) and field.strip():
                    marker_chunks.append(field)
        haystack = "\n".join(marker_chunks)
        band_patterns = (
            r"WiFi\.AccessPoint\.(?:1|2|3|4|5|6)\b",
            r"\bwl[012](?:\.\d+)?\b",
            r"WiFi\.Radio\.\d",
            r"WiFi\.SSID\.\d",
        )
        return any(re.search(p, haystack) for p in band_patterns)

    def _connect_with_retry(
        self,
        *,
        transport: Any,
        case_id: str,
        label: str,
        connect_cmd: str,
        verify_cmd: str,
        attempts: int = 3,
        sleep_seconds: int = 3,
    ) -> bool:
        for attempt in range(1, max(1, attempts) + 1):
            self._run_required_command(
                transport=transport,
                case_id=case_id,
                label=f"{label}.connect.{attempt}",
                command=connect_cmd,
                timeout=20.0,
            )
            self._run_required_command(
                transport=transport,
                case_id=case_id,
                label=f"{label}.sleep.{attempt}",
                command=f"sleep {sleep_seconds}",
                timeout=max(5.0, float(sleep_seconds + 2)),
            )
            verify_result = self._execute_env_command(transport, verify_cmd, timeout=20.0)
            if self._env_command_succeeded(verify_cmd, verify_result):
                return True
            log.warning(
                "[%s] verify_env: %s %s verify attempt=%d failed",
                self.name,
                case_id,
                label,
                attempt,
            )
        return False

    def _run_sta_band_connect_sequence(self, case: dict[str, Any]) -> bool:
        case_id = str(case.get("id", ""))
        sta = self._transports.get("STA")
        if sta is None:
            return False
        wpa_cli = "wpa_cli -i wl1"
        selected_bands = set(self._selected_sta_bands(case))

        # Suppress kernel console messages to prevent UART prompt detection issues
        # (Broadcom dhd driver floods console during WiFi mode switches).
        self._execute_env_command(sta, "dmesg -n 1", timeout=5.0)

        # 5G (WPA2-Personal via wpa_supplicant)
        if "5g" in selected_bands:
            five_g_prep = (
                "ubus-cli WiFi.AccessPoint.1.Enable=0",
                "ubus-cli WiFi.AccessPoint.2.Enable=0",
                "killall wpa_supplicant 2>/dev/null || true",
                "iw dev wl0.1 del 2>/dev/null || true",
                "iw dev wl0 disconnect 2>/dev/null || true",
                "ifconfig wl0 down",
                "wl -i wl0 ap 0",
                "wl -i wl0 up",
                "ifconfig wl0 up",
                "rm -rf /var/run/wpa_supplicant",
                "mkdir -p /var/run/wpa_supplicant",
                "printf 'ctrl_interface=/var/run/wpa_supplicant\\nupdate_config=1\\nnetwork={\\nssid=\"TestPilot_BTM\"\\nkey_mgmt=WPA-PSK\\npsk=\"00000000\"\\n}\\n' > /tmp/wpa_wl0.conf",
                "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf",
                "sleep 5",
            )
            for idx, cmd in enumerate(five_g_prep, start=1):
                if not self._run_required_command(
                    transport=sta,
                    case_id=case_id,
                    label=f"sta_5g_prep.{idx}",
                    command=cmd,
                ):
                    return False
            if not self._connect_with_retry(
                transport=sta,
                case_id=case_id,
                label="sta_5g",
                connect_cmd="wpa_cli -i wl0 reconnect",
                verify_cmd="iw dev wl0 link",
                attempts=3,
                sleep_seconds=5,
            ):
                return False

        # 6G (SAE) — non-fatal: STA Broadcom dhd driver may not support
        # SAE-H2E required by DUT 6G; failure is logged but does not block.
        if "6g" in selected_bands:
            six_g_prep = (
                "ubus-cli WiFi.AccessPoint.3.Enable=0",
                "ubus-cli WiFi.AccessPoint.4.Enable=0",
                "wpa_cli -i wl1 terminate 2>/dev/null || true",
                "rm -f /var/run/wpa_supplicant/wl1 2>/dev/null || true",
                "iw dev wl1.1 del 2>/dev/null || true",
                "iw dev wl1 disconnect 2>/dev/null || true",
                "ifconfig wl1 down",
                "wl -i wl1 ap 0",
                "wl -i wl1 up",
                "ifconfig wl1 up",
                "mkdir -p /var/run/wpa_supplicant",
                "printf 'ctrl_interface=/var/run/wpa_supplicant\\nupdate_config=1\\nsae_pwe=2\\nnetwork={\\nssid=\"testpilot6G\"\\nkey_mgmt=SAE\\nsae_password=\"00000000\"\\nieee80211w=2\\nscan_ssid=1\\n}\\n' > /tmp/wpa_wl1.conf",
                "wpa_supplicant -B -D nl80211 -i wl1 -c /tmp/wpa_wl1.conf",
                "sleep 5",
            )
            six_g_ok = True
            for idx, cmd in enumerate(six_g_prep, start=1):
                if not self._run_required_command(
                    transport=sta,
                    case_id=case_id,
                    label=f"sta_6g_prep.{idx}",
                    command=cmd,
                ):
                    six_g_ok = False
                    break
            if six_g_ok:
                six_g_ok = self._connect_with_retry(
                    transport=sta,
                    case_id=case_id,
                    label="sta_6g_ctrl",
                    connect_cmd=f"{wpa_cli} ping",
                    verify_cmd=f"{wpa_cli} ping",
                    attempts=3,
                    sleep_seconds=1,
                )
            if six_g_ok:
                six_g_ok = self._connect_with_retry(
                    transport=sta,
                    case_id=case_id,
                    label="sta_6g",
                    connect_cmd=f"{wpa_cli} reconnect",
                    verify_cmd="iw dev wl1 link",
                    attempts=3,
                    sleep_seconds=8,
                )
            if six_g_ok:
                self._run_required_command(
                    transport=sta,
                    case_id=case_id,
                    label="sta_6g_status",
                    command=f"{wpa_cli} status",
                    timeout=20.0,
                )
            if not six_g_ok:
                log.warning(
                    "[%s] verify_env: %s 6G connect failed (SAE-H2E likely unsupported), continuing",
                    self.name,
                    case_id,
                )

        # 2.4G (WPA2-Personal via wpa_supplicant)
        if "2.4g" in selected_bands:
            two_g_prep = (
                "ubus-cli WiFi.AccessPoint.5.Enable=0",
                "ubus-cli WiFi.AccessPoint.6.Enable=0",
                "wpa_cli -i wl2 terminate 2>/dev/null || true",
                "iw dev wl2.1 del 2>/dev/null || true",
                "iw dev wl2 disconnect 2>/dev/null || true",
                "ifconfig wl2 down",
                "wl -i wl2 ap 0",
                "wl -i wl2 up",
                "ifconfig wl2 up",
                "rm -f /var/run/wpa_supplicant/wl2 2>/dev/null || true",
                "mkdir -p /var/run/wpa_supplicant",
                "printf 'ctrl_interface=/var/run/wpa_supplicant\\nupdate_config=1\\nnetwork={\\nssid=\"testpilot2G\"\\nkey_mgmt=WPA-PSK\\npsk=\"00000000\"\\n}\\n' > /tmp/wpa_wl2.conf",
                "wpa_supplicant -B -D nl80211 -i wl2 -c /tmp/wpa_wl2.conf",
                "sleep 5",
            )
            for idx, cmd in enumerate(two_g_prep, start=1):
                if not self._run_required_command(
                    transport=sta,
                    case_id=case_id,
                    label=f"sta_24g_prep.{idx}",
                    command=cmd,
                ):
                    return False
            if not self._connect_with_retry(
                transport=sta,
                case_id=case_id,
                label="sta_24g",
                connect_cmd="wpa_cli -i wl2 reconnect",
                verify_cmd="iw dev wl2 link",
                attempts=3,
                sleep_seconds=5,
            ):
                return False
        return True

    def _run_sta_band_baseline(self, case: dict[str, Any]) -> bool:
        case_id = str(case.get("id", ""))
        dut = self._transports.get("DUT")
        if dut is None:
            return False
        selected_bands = set(self._selected_sta_bands(case))

        # Check if BSS is already up — skip DUT config if radios are active.
        # We accept factory SSIDs (EasyMesh may override 5G SSID changes).
        bss_map = {"5g": "wl0", "6g": "wl1", "2.4g": "wl2"}
        all_up = True
        for band in selected_bands:
            iface = bss_map.get(band)
            if iface:
                result = self._execute_env_command(dut, f"wl -i {iface} bss", timeout=10.0)
                if "up" not in self._env_output_text(result).strip().lower():
                    all_up = False
                    break
        if all_up:
            log.info("[%s] verify_env: %s BSS already up, skipping DUT baseline", self.name, case_id)
            # Always ensure 5G is WPA2-Personal even when BSS is up.
            # EasyMesh may revert ModeEnabled to WPA3-Personal (SAE-H2E),
            # which is incompatible with the STA Broadcom dhd driver.
            if "5g" in selected_bands:
                self._execute_env_command(
                    dut,
                    "ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA2-Personal",
                    timeout=15.0,
                )
            return True

        # DUT baseline: enable Radio/AP, set security and KeyPassPhrase.
        # We do NOT change SSIDs — EasyMesh controller overrides 5G SSID;
        # factory SSIDs (TestPilot_BTM/testpilot6G/testpilot2G) are accepted.
        # 5G must be forced to WPA2-Personal (factory SAE-H2E incompatible with STA).
        dut_commands: list[str] = []
        if "5g" in selected_bands:
            dut_commands.extend(
                (
                    "ubus-cli WiFi.Radio.1.Enable=1",
                    "ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA2-Personal",
                    'ubus-cli \'WiFi.AccessPoint.1.Security.KeyPassPhrase="00000000"\'',
                    "ubus-cli WiFi.AccessPoint.1.Enable=1",
                )
            )
        if "6g" in selected_bands:
            dut_commands.extend(
                (
                    "ubus-cli WiFi.Radio.2.Enable=1",
                    'ubus-cli \'WiFi.AccessPoint.3.Security.KeyPassPhrase="00000000"\'',
                    "ubus-cli WiFi.AccessPoint.3.Enable=1",
                )
            )
        if "2.4g" in selected_bands:
            dut_commands.extend(
                (
                    "ubus-cli WiFi.Radio.3.Enable=1",
                    'ubus-cli \'WiFi.AccessPoint.5.Security.KeyPassPhrase="00000000"\'',
                    "ubus-cli WiFi.AccessPoint.5.Enable=1",
                )
            )
        # Apply DUT config (no wld_gen — boot sequence handles radio init).
        for index, command in enumerate(dut_commands, start=1):
            result = self._execute_env_command(dut, command, timeout=30.0)
            if not self._env_command_succeeded(command, result):
                log.warning(
                    "[%s] verify_env: %s sta_baseline[%d] failed rc=%s cmd=%s out=%s",
                    self.name,
                    case_id,
                    index,
                    int(result.get("returncode", 1)),
                    command,
                    self._preview_value(self._env_output_text(result)),
                )
                return False

        # Wait for hostapd to reload after DUT config changes.
        self._execute_env_command(dut, "sleep 5", timeout=10.0)

        bss_commands: list[str] = []
        if "5g" in selected_bands:
            bss_commands.append("wl -i wl0 bss")
        if "6g" in selected_bands:
            bss_commands.append("wl -i wl1 bss")
        if "2.4g" in selected_bands:
            bss_commands.append("wl -i wl2 bss")
        # Retry BSS readiness — after reboot, radios may need extra time.
        bss_max_wait = 60.0
        bss_poll_interval = 5.0
        for index, command in enumerate(bss_commands, start=1):
            deadline = time.monotonic() + bss_max_wait
            ready = False
            while time.monotonic() < deadline:
                result = self._execute_env_command(dut, command, timeout=20.0)
                out = self._env_output_text(result).strip().lower()
                if "up" in out:
                    ready = True
                    break
                log.info(
                    "[%s] verify_env: %s bss[%d] not ready yet (%s), retrying...",
                    self.name, case_id, index, out,
                )
                self._execute_env_command(dut, f"sleep {int(bss_poll_interval)}", timeout=bss_poll_interval + 5)
            if not ready:
                log.warning(
                    "[%s] verify_env: %s sta_baseline_bss[%d] not ready after %.0fs cmd=%s",
                    self.name, case_id, index, bss_max_wait, command,
                )
        return True

    def _verify_sta_band_connectivity(self, case: dict[str, Any]) -> bool:
        case_id = str(case.get("id", ""))
        sta = self._transports.get("STA")
        dut = self._transports.get("DUT")
        if sta is None or dut is None:
            return True

        selected_bands = set(self._selected_sta_bands(case))
        checks: list[tuple[str, str, str]] = []
        if "5g" in selected_bands:
            checks.append(("5g", "wl0", "1"))
        if "6g" in selected_bands:
            checks.append(("6g", "wl1", "3"))
        if "2.4g" in selected_bands:
            checks.append(("2.4g", "wl2", "5"))
        for band, sta_iface, ap_index in checks:
            link_command = f"iw dev {sta_iface} link"
            link_result = self._execute_env_command(sta, link_command, timeout=15.0)
            link_stdout = self._env_output_text(link_result)
            link_ok = self._env_command_succeeded(link_command, link_result)
            if not link_ok:
                log.warning(
                    "[%s] verify_env: %s STA %s link check failed (iface=%s, rc=%s): %s",
                    self.name,
                    case_id,
                    band,
                    sta_iface,
                    int(link_result.get("returncode", 1)),
                    self._preview_value(link_stdout),
                )
                return False

            assoc_command = f'ubus-cli "WiFi.AccessPoint.{ap_index}.AssociatedDevice.*.MACAddress?"'
            assoc_result = self._execute_env_command(dut, assoc_command, timeout=15.0)
            assoc_stdout = self._env_output_text(assoc_result)
            assoc_ok = self._env_command_succeeded(assoc_command, assoc_result)
            if not assoc_ok:
                log.warning(
                    "[%s] verify_env: %s DUT %s associated-device check failed (AP=%s, rc=%s): %s",
                    self.name,
                    case_id,
                    band,
                    ap_index,
                    int(assoc_result.get("returncode", 1)),
                    self._preview_value(assoc_stdout),
                )
                return False
        return True

    def _ensure_sta_band_ready(self, case: dict[str, Any], topology: Any) -> bool:
        del topology
        if not self._run_sta_band_baseline(case):
            return False
        if not self._run_sta_band_connect_sequence(case):
            return False
        if not self._verify_sta_band_connectivity(case):
            return False
        return True

    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        """佈建 WiFi 測試環境。"""
        case_id = str(case.get("id", ""))
        if self._transports:
            self.teardown(case, topology)
        self._sta_env_verified = False

        topo = self._as_mapping(case.get("topology"))
        devices = self._as_mapping(topo.get("devices"))
        if not devices:
            log.warning("[%s] setup_env: %s topology.devices is empty", self.name, case_id)
            return False

        all_connected = True
        for device_name, case_device_cfg in devices.items():
            dev_name = str(device_name)
            case_cfg = case_device_cfg if isinstance(case_device_cfg, dict) else {}

            testbed_cfg: dict[str, Any] = {}
            try:
                getter = getattr(topology, "get_device", None)
                if callable(getter):
                    got = getter(dev_name)
                    if isinstance(got, dict):
                        testbed_cfg = dict(got)
            except KeyError:
                log.warning("[%s] setup_env: %s missing in testbed config, degrade", self.name, dev_name)
            except Exception:
                log.exception("[%s] setup_env: get_device failed for %s", self.name, dev_name)

            merged = dict(testbed_cfg)
            merged.update(case_cfg)
            transport_type = str(
                case_cfg.get("transport") or testbed_cfg.get("transport") or "stub"
            ).strip() or "stub"

            transport = self._create_transport_instance(transport_type, merged)
            connected = self._connect_transport(dev_name, transport, merged)
            if not connected:
                all_connected = False
                log.warning("[%s] setup_env: %s connect failed", self.name, dev_name)

            self._transports[dev_name] = transport
            self._device_specs[dev_name] = merged

        log.info(
            "[%s] setup_env: %s connected=%s devices=%s",
            self.name,
            case_id,
            all_connected,
            sorted(self._transports.keys()),
        )
        if not (all_connected and bool(self._transports)):
            return False
        if not self._run_sta_env_setup(case, topology):
            return False
        self._sta_env_verified = True
        return True

    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        """驗證 WiFi 連線就緒。"""
        case_id = str(case.get("id", ""))
        dut = self._transports.get("DUT")
        if dut is None:
            log.warning("[%s] verify_env: %s missing DUT transport", self.name, case_id)
            return False

        # Suppress kernel console messages on DUT to prevent UART flood
        # (Broadcom dhd driver generates continuous messages that break prompt detection).
        self._execute_env_command(dut, "dmesg -n 1", timeout=5.0)

        gate_result = self._execute_env_command(dut, 'echo "__testpilot_env_gate__"', timeout=10.0)
        if int(gate_result.get("returncode", 1)) != 0:
            log.warning("[%s] verify_env: %s DUT gate failed", self.name, case_id)
            return False

        # Run default band baseline only when the case does NOT provide its
        # own sta_env_setup AND explicitly references WiFi AP/radio bands.
        has_custom_env = bool(
            isinstance(case.get("sta_env_setup"), str)
            and case["sta_env_setup"].strip()
        )
        needs_wifi = self._has_explicit_wifi_bands(case)
        sta = self._transports.get("STA")
        if not has_custom_env and needs_wifi and sta is not None:
            # Suppress kernel console messages on STA too.
            self._execute_env_command(sta, "dmesg -n 1", timeout=5.0)
            if not self._ensure_sta_band_ready(case, topology):
                log.warning("[%s] verify_env: %s STA band baseline/connect failed", self.name, case_id)
                return False

        env_verify = case.get("env_verify")
        if not isinstance(env_verify, list):
            return True

        for index, item in enumerate(env_verify):
            if not isinstance(item, dict):
                log.warning("[%s] verify_env: env_verify[%d] invalid, skip", self.name, index)
                continue

            action = str(item.get("action", "")).strip().lower()
            if action != "ping":
                log.warning("[%s] verify_env: unsupported action=%s, skip", self.name, action)
                continue

            src_name = str(item.get("from", "")).strip()
            dst_name = str(item.get("to", "")).strip()
            expect = str(item.get("expect", "pass")).strip().lower()
            src_transport = self._transports.get(src_name)

            if not src_name or not dst_name or src_transport is None:
                log.warning(
                    "[%s] verify_env: ping gate missing endpoint transport (%s -> %s), skip",
                    self.name,
                    src_name,
                    dst_name,
                )
                continue

            target = self._resolve_ping_target(topology, dst_name)
            if not target:
                log.warning(
                    "[%s] verify_env: cannot resolve ping target for %s, skip", self.name, dst_name
                )
                continue

            command = self._resolve_text(topology, f"ping -c 1 {target}")
            ping_result = src_transport.execute(command, timeout=10.0)
            passed = int(ping_result.get("returncode", 1)) == 0

            if expect in {"pass", "ok", "true", "1"} and not passed:
                log.warning("[%s] verify_env: ping expected pass but failed (%s -> %s)", self.name, src_name, dst_name)
                return False
            if expect in {"fail", "false", "0"} and passed:
                log.warning("[%s] verify_env: ping expected fail but passed (%s -> %s)", self.name, src_name, dst_name)
                return False

        return True

    @staticmethod
    def _should_retry_env_command(result: dict[str, Any]) -> bool:
        if int(result.get("returncode", 0)) == 0:
            return False
        if str(result.get("recovery_action", "")).strip():
            return True

        stdout = str(result.get("stdout", "")).strip()
        stderr = str(result.get("stderr", "")).strip()
        return stdout in {"^C", "^D"} or stderr in {"^C", "^D"}

    def _execute_env_command(self, transport: Any, command: str, *, timeout: float) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for attempt in range(1, 4):
            result = self._as_mapping(transport.execute(command, timeout=timeout))
            if not self._should_retry_env_command(result):
                return result
            if attempt >= 3:
                return result

            log.info(
                "[%s] env: retry command after recovery_action=%s attempt=%d cmd=%s",
                self.name,
                result.get("recovery_action"),
                attempt,
                self._preview_value(command, limit=96),
            )
            time.sleep(0.2)
        return result

    def execute_step(self, case: dict[str, Any], step: dict[str, Any], topology: Any) -> dict[str, Any]:
        """執行單一 ubus-cli / wl 測試步驟。"""
        step_id = str(step.get("id", "step"))
        action = str(step.get("action", "exec")).strip().lower()
        target_name = str(step.get("target", "DUT")).strip() or "DUT"
        timeout = self._to_float(step.get("timeout"), 30.0)

        if action == "wait":
            duration = max(0.0, self._to_float(step.get("duration"), 0.0))
            start = time.monotonic()
            time.sleep(duration)
            elapsed = time.monotonic() - start
            return {
                "success": True,
                "output": f"waited {duration:.3f}s",
                "captured": {"duration": duration},
                "timing": elapsed,
            }

        transport = self._transports.get(target_name) or self._transports.get("DUT")
        if transport is None:
            return {
                "success": False,
                "output": f"transport not found for target={target_name}",
                "captured": {},
                "timing": 0.0,
            }

        raw_command = str(step.get("command", "")).strip()
        capture_name = str(step.get("capture", "")).strip()
        resolved_command = self._resolve_text(topology, raw_command)
        command_to_run = resolved_command
        commands_to_run: list[str] = []
        fallback_reason = ""

        candidate_commands = [
            self._resolve_text(topology, command)
            for command in self._extract_cli_fragments(command_to_run)
        ]
        preferred_capture_command = self._prefer_synthesized_readback(
            case, step, raw_command, candidate_commands
        )
        if preferred_capture_command:
            commands_to_run = [self._resolve_text(topology, preferred_capture_command)]
            fallback_reason = "synthesized_capture_query"
        elif candidate_commands:
            commands_to_run = candidate_commands
            if len(candidate_commands) > 1 or candidate_commands[0] != command_to_run:
                fallback_reason = "extract_from_step_text"
        else:
            command_to_run = self._sanitize_cli_fragment(command_to_run)
            if command_to_run:
                commands_to_run = self._split_safe_shell_commands(command_to_run)

        if not commands_to_run or not all(self._looks_executable(command) for command in commands_to_run):
            if not capture_name and not self._command_starts_executable(raw_command):
                commands_to_run = [f'echo "[skip] non-executable step {step_id}"']
                fallback_reason = "fallback_skip_echo"
            else:
                commands_to_run, fallback_reason = self._select_fallback_commands(
                    case, raw_command, topology, step_id
                )

        outputs: list[str] = []
        captured: dict[str, Any] = {}
        total_elapsed = 0.0
        success = True
        final_returncode = 0

        index = 0
        while index < len(commands_to_run):
            command_to_run = commands_to_run[index]
            try:
                result = transport.execute(command_to_run, timeout=timeout)
            except Exception as exc:
                log.warning(
                    "[%s] execute_step failed: %s.%s[%d] err=%s",
                    self.name,
                    case.get("id"),
                    step_id,
                    index + 1,
                    exc,
                )
                return {
                    "success": False,
                    "output": str(exc),
                    "captured": {},
                    "timing": total_elapsed,
                    "command": "\n".join(commands_to_run).strip(),
                    "fallback_reason": fallback_reason,
                }

            result_map = self._as_mapping(result)
            if index == 0 and len(commands_to_run) == 1 and not fallback_reason and self._is_unexecutable_result(result_map):
                fallback_commands, reason = self._select_fallback_commands(case, raw_command, topology, step_id)
                if fallback_commands != commands_to_run:
                    commands_to_run = fallback_commands
                    fallback_reason = reason
                    outputs = []
                    captured = {}
                    total_elapsed = 0.0
                    success = True
                    final_returncode = 0
                    index = 0
                    continue

            stdout = str(result_map.get("stdout", ""))
            stderr = str(result_map.get("stderr", ""))
            output = self._normalize_transcript_noise(
                "\n".join(chunk for chunk in (stdout, stderr) if chunk).strip()
            )
            if output:
                outputs.append(output)
                captured.update(self._extract_key_values(output))
            total_elapsed += self._to_float(result_map.get("elapsed"), 0.0)
            final_returncode = int(result_map.get("returncode", 1))
            success = success and final_returncode == 0
            if final_returncode != 0:
                break
            index += 1

        return {
            "success": success,
            "output": "\n".join(outputs).strip(),
            "captured": captured,
            "timing": total_elapsed,
            "returncode": final_returncode,
            "command": "\n".join(commands_to_run).strip(),
            "fallback_reason": fallback_reason,
        }

    def evaluate(self, case: dict[str, Any], results: dict[str, Any]) -> bool:
        """評估通過條件。"""
        context = self._build_eval_context(case, results)
        aggregate_output = str(context.get("_aggregate_output", ""))
        criteria = case.get("pass_criteria")
        if not isinstance(criteria, list) or not criteria:
            return False

        for idx, criterion in enumerate(criteria):
            if not isinstance(criterion, dict):
                log.warning("[%s] evaluate: invalid criteria[%d]", self.name, idx)
                return False

            field = str(criterion.get("field", "")).strip()
            operator = str(criterion.get("operator", "contains"))
            expected = criterion.get("value")
            reference = str(criterion.get("reference", "")).strip()

            actual = self._resolve_field(context, field) if field else None
            # Unwrap step context: when field resolves to a step_context dict
            # with a single captured value, use that value directly so regex /
            # equals criteria match the extracted data rather than the whole dict.
            if isinstance(actual, dict) and "captured" in actual and "output" in actual:
                captured = actual.get("captured")
                if isinstance(captured, dict) and len(captured) == 1:
                    actual = next(iter(captured.values()))
            if actual is None:
                log.warning("[%s] evaluate: field not found (%s), fallback aggregate output", self.name, field)
                actual = self._field_fallback_output(aggregate_output, field)

            if expected is None and reference:
                expected = self._resolve_field(context, reference)
                if expected is None:
                    log.warning(
                        "[%s] evaluate: reference not found (%s), fallback aggregate output",
                        self.name,
                        reference,
                    )
                    expected = aggregate_output

            if not self._compare(actual, operator, expected):
                log.info(
                    "[%s] evaluate failed: field=%s op=%s expected=%s actual=%s",
                    self.name,
                    field,
                    operator,
                    self._preview_value(expected),
                    self._preview_value(actual),
                )
                return False

        return True

    def teardown(self, case: dict[str, Any], topology: Any) -> None:
        """清理環境。"""
        case_id = str(case.get("id", ""))
        for device_name, transport in list(self._transports.items()):
            try:
                disconnect = getattr(transport, "disconnect", None)
                if callable(disconnect):
                    disconnect()
            except Exception as exc:
                log.warning("[%s] teardown: disconnect failed for %s: %s", self.name, device_name, exc)
        self._transports.clear()
        self._device_specs.clear()
        self._sta_env_verified = False
        log.info("[%s] teardown: %s done", self.name, case_id)
