"""wifi_llapi plugin — Wifi LLAPI test automation for prplOS/Broadcom."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
import re
import shlex
import subprocess
import time
from typing import Any, Sequence

from testpilot.core.case_utils import stringify_step_command, step_command_lines
from testpilot.core.plugin_base import PluginBase
from testpilot.serialwrap_binary import resolve_serialwrap_binary
from testpilot.schema.case_schema import load_cases_dir, load_wifi_band_baselines
from testpilot.transport.base import StubTransport
from testpilot.yaml_command_audit import looks_like_shell_command

from baseline_qualifier import BaselineQualifier
from command_resolver import CommandResolver

log = logging.getLogger(__name__)


class Plugin(PluginBase):
    """Wifi LLAPI 測試 plugin。

    測試 prplOS WiFi.Radio / WiFi.AccessPoint 的 LLAPI 介面，
    透過 ubus-cli 與 wl 指令驗證參數讀寫與功能正確性。
    """

    TESTBED_BINDING_KEYS = (
        "selector",
        "alias",
        "session_id",
        "serial_port",
        "baudrate",
        "host",
        "user",
        "password",
        "port",
        "adb_serial",
    )

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
    STATEFUL_SHELL_TOKENS = {
        "if",
        "then",
        "elif",
        "else",
        "fi",
        "for",
        "while",
        "until",
        "do",
        "done",
        "case",
        "esac",
        "{",
        "}",
    }
    BAND_BASELINES_FILE = Path(__file__).parent / "band-baselines.yaml"
    DEFAULT_BAND_BASELINES: dict[str, dict[str, Any]] = {}
    ASSOC_MAC_CAPTURE_FIELD_RE = re.compile(r"^AssocMac(?:5g|6g|24g)$", re.IGNORECASE)
    MAC_ADDRESS_RE = re.compile(r"([0-9a-f]{2}:){5}[0-9a-f]{2}", re.IGNORECASE)

    def __init__(self) -> None:
        self._transports: dict[str, Any] = {}
        self._device_specs: dict[str, dict[str, Any]] = {}
        self._sta_env_verified = False
        self._command_resolver = CommandResolver(self)
        self.DEFAULT_BAND_BASELINES = load_wifi_band_baselines(self.BAND_BASELINES_FILE)
        self._sta_available_bands: tuple[str, ...] = ("5g", "6g", "2.4g")

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

    # -- reporter overrides ----------------------------------------------------

    def create_reporter(self) -> Any:
        from testpilot.reporting.reporter import MarkdownReporter

        return MarkdownReporter()

    def report_formats(self) -> list[str]:
        return ["xlsx", "md", "json"]

    # -- helpers ---------------------------------------------------------------

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
        return CommandResolver.as_mapping(value)

    @staticmethod
    def _snapshot_mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
            if isinstance(payload, dict):
                return dict(payload)
        return {}

    @staticmethod
    def _normalize_band_name(value: Any) -> str:
        text = str(value or "").strip().lower()
        aliases = {
            "5g": "5g",
            "6g": "6g",
            "2.4g": "2.4g",
            "24g": "2.4g",
            "2g": "2.4g",
        }
        return aliases.get(text, "")

    def _band_baseline_profile(self, band: str) -> dict[str, Any] | None:
        normalized_band = self._normalize_band_name(band)
        profile = self.DEFAULT_BAND_BASELINES.get(normalized_band)
        if not isinstance(profile, dict):
            return None
        return dict(profile)

    @staticmethod
    def _render_baseline_template(text: str, profile: dict[str, Any]) -> str:
        rendered = str(text)
        for key, value in profile.items():
            if isinstance(value, (str, int, float)):
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered

    def _profile_command(self, profile: dict[str, Any], field: str) -> str:
        return self._render_baseline_template(str(profile.get(field, "")), profile)

    def _profile_command_list(self, profile: dict[str, Any], field: str) -> list[str]:
        raw_commands = profile.get(field, [])
        if not isinstance(raw_commands, list):
            return []
        return [self._render_baseline_template(str(command), profile) for command in raw_commands]

    def _sta_wpa_config_path(self, profile: dict[str, Any]) -> str:
        return f"/tmp/wpa_{profile['iface']}.conf"

    def _sta_wpa_config_commands(self, profile: dict[str, Any]) -> list[str]:
        config_path = self._sta_wpa_config_path(profile)
        lines = [
            *profile.get("sta_global_config", []),
            "network={",
            *profile.get("sta_network_config", []),
            "}",
        ]
        commands: list[str] = []
        for index, raw_line in enumerate(lines):
            line = self._render_baseline_template(str(raw_line), profile)
            redirect = ">" if index == 0 else ">>"
            commands.append(f"printf '%s\\n' {shlex.quote(line)} {redirect} {config_path}")
        return commands

    def _dut_baseline_commands(self, profile: dict[str, Any]) -> list[str]:
        ap = str(profile["ap"])
        commands = [
            f"ubus-cli WiFi.Radio.{profile['radio']}.Enable=1",
            f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
            f"ubus-cli WiFi.AccessPoint.{ap}.Enable=0",
            f"ubus-cli WiFi.SSID.{profile['ssid_index']}.SSID={profile['ssid']}",
            f"ubus-cli WiFi.AccessPoint.{ap}.Security.ModeEnabled={profile['mode']}",
        ]
        for field in profile.get("dut_secret_fields", []):
            commands.append(
                f'ubus-cli \'WiFi.AccessPoint.{ap}.Security.{field}="{profile["key"]}"\''
            )
        commands.extend(
            [
                f"ubus-cli WiFi.AccessPoint.{ap}.Security.MFPConfig={profile['mfp']}",
                f"ubus-cli WiFi.AccessPoint.{ap}.Enable=1",
            ]
        )
        return commands

    def _case_declared_bands(self, case: dict[str, Any]) -> tuple[str, ...]:
        for key in ("_force_sta_bands", "bands"):
            raw = case.get(key)
            normalized: list[str] = []
            if isinstance(raw, list):
                normalized = [
                    band
                    for item in raw
                    if (band := self._normalize_band_name(item))
                ]
            elif isinstance(raw, dict):
                for name, spec in raw.items():
                    band = self._normalize_band_name(name)
                    if not band:
                        continue
                    if isinstance(spec, dict) and spec.get("enabled") is False:
                        continue
                    normalized.append(band)
            if normalized:
                seen: list[str] = []
                for band in normalized:
                    if band not in seen:
                        seen.append(band)
                return tuple(seen)
        return ()

    def _record_runtime_failure(
        self,
        case: dict[str, Any],
        *,
        phase: str,
        comment: str,
        category: str,
        reason_code: str,
        device: str = "",
        band: str = "",
        command: str = "",
        output: str = "",
        evidence: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        case["_last_failure"] = {
            "case_id": str(case.get("id", "")),
            "attempt_index": int(case.get("_attempt_index", 1)),
            "phase": phase,
            "comment": comment,
            "category": category,
            "reason_code": reason_code,
            "device": device,
            "band": self._normalize_band_name(band),
            "command": command,
            "output": output,
            "evidence": [str(item) for item in (evidence or []) if str(item).strip()],
            "metadata": dict(metadata or {}),
        }

    def _topology_device_config(self, topology: Any, device_name: str) -> dict[str, Any]:
        try:
            getter = getattr(topology, "get_device", None)
            if callable(getter):
                got = getter(device_name)
                if isinstance(got, dict):
                    return dict(got)
        except KeyError:
            return {}
        except Exception:
            log.exception("[%s] topology get_device failed for %s", self.name, device_name)
        devices = getattr(topology, "devices", {})
        if isinstance(devices, dict):
            cfg = devices.get(device_name)
            if isinstance(cfg, dict):
                return dict(cfg)
        return {}

    def _band_from_text(self, text: str) -> str:
        normalized = self._normalize_command_text(text)
        if re.search(r"\bwl0(?:\.\d+)?\b|WiFi\.AccessPoint\.(?:1|2)\b", normalized):
            return "5g"
        if re.search(r"\bwl1(?:\.\d+)?\b|WiFi\.AccessPoint\.(?:3|4)\b", normalized):
            return "6g"
        if re.search(r"\bwl2(?:\.\d+)?\b|WiFi\.AccessPoint\.(?:5|6)\b", normalized):
            return "2.4g"
        return ""

    @classmethod
    def _script_references_band(cls, text: str, band: Any) -> bool:
        normalized_band = cls._normalize_band_name(band)
        if normalized_band == "5g":
            pattern = r"\bwl0(?:\.\d+)?\b|WiFi\.AccessPoint\.(?:1|2)\b"
        elif normalized_band == "6g":
            pattern = r"\bwl1(?:\.\d+)?\b|WiFi\.AccessPoint\.(?:3|4)\b"
        elif normalized_band == "2.4g":
            pattern = r"\bwl2(?:\.\d+)?\b|WiFi\.AccessPoint\.(?:5|6)\b"
        else:
            return False
        return bool(re.search(pattern, cls._normalize_command_text(text)))

    def _case_for_bands(self, case: dict[str, Any], bands: tuple[str, ...]) -> dict[str, Any]:
        scoped = dict(case)
        scoped["_force_sta_bands"] = list(bands)
        return scoped

    def _resolve_text(self, topology: Any, text: str) -> str:
        resolver = getattr(topology, "resolve", None)
        if callable(resolver):
            try:
                return str(resolver(text))
            except Exception:  # pragma: no cover - defensive
                log.exception("[%s] resolve failed, keep original text", self.name)
        return text

    def _resolve_runtime_text(self, case: dict[str, Any], topology: Any, text: str) -> str:
        step_results = self._as_mapping(case.get("_step_results"))
        context = self._build_eval_context(case, {"steps": step_results}) if step_results else {}

        def _apply_runtime_placeholders(candidate: str) -> str:
            if not step_results or "{{" not in candidate:
                return candidate

            def _repl(match: re.Match[str]) -> str:
                field = match.group(1).strip()
                if not field:
                    return match.group(0)
                value = self._resolve_field(context, field)
                if isinstance(value, dict) and "captured" in value and "output" in value:
                    captured = value.get("captured")
                    if isinstance(captured, dict) and len(captured) == 1:
                        value = next(iter(captured.values()))
                if value is None:
                    return match.group(0)
                return self._stringify(value).strip()

            return re.sub(r"\{\{\s*([^{}]+?)\s*\}\}", _repl, candidate)

        runtime_first = _apply_runtime_placeholders(text)
        resolved = self._resolve_text(topology, runtime_first)
        return _apply_runtime_placeholders(resolved)

    @staticmethod
    def _has_unresolved_placeholder(text: str) -> bool:
        return bool(re.search(r"\{\{\s*[^{}]+\s*\}\}", text))

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
            setattr(transport, "_testpilot_last_connect_error", str(exc))
            log.warning("[%s] connect failed for %s: %s", self.name, device, exc)
            return False

        return bool(getattr(transport, "is_connected", True))

    def _open_case_transports(
        self,
        case: dict[str, Any],
        topology: Any,
        *,
        run_case_setup: bool,
    ) -> bool:
        topo = self._as_mapping(case.get("topology"))
        devices = self._as_mapping(topo.get("devices"))
        case_id = str(case.get("id", ""))
        if not devices:
            self._record_runtime_failure(
                case,
                phase="setup_env",
                comment="topology.devices is empty",
                category="configuration",
                reason_code="invalid_topology",
            )
            log.warning("[%s] setup_env: %s topology.devices is empty", self.name, case_id)
            return False

        all_connected = True
        for device_name, case_device_cfg in devices.items():
            dev_name = str(device_name)
            case_cfg = case_device_cfg if isinstance(case_device_cfg, dict) else {}
            testbed_cfg = self._topology_device_config(topology, dev_name)

            merged = dict(testbed_cfg)
            merged.update(case_cfg)
            for binding_key in self.TESTBED_BINDING_KEYS:
                value = testbed_cfg.get(binding_key)
                if value not in (None, ""):
                    merged[binding_key] = value
            transport_type = str(
                case_cfg.get("transport") or testbed_cfg.get("transport") or "stub"
            ).strip() or "stub"

            transport = self._create_transport_instance(transport_type, merged)
            connected = self._connect_transport(dev_name, transport, merged)
            if not connected:
                all_connected = False
                err = str(getattr(transport, "_testpilot_last_connect_error", "") or "")
                lowered = err.lower()
                category = "session" if "serialwrap" in lowered or transport_type in {"serial", "serialwrap"} else "environment"
                reason_code = "serial_session_not_ready" if ("not ready" in lowered or "attached" in lowered) else "transport_connect_failed"
                self._record_runtime_failure(
                    case,
                    phase="setup_env",
                    comment=f"{dev_name} connect failed",
                    category=category,
                    reason_code=reason_code,
                    device=dev_name,
                    output=err,
                    metadata={"transport": transport_type},
                )
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

        if run_case_setup:
            if self._sta_env_setup_has_unresolved_placeholders(case):
                log.info(
                    "[%s] setup_env: %s sta_env_setup contains unresolved placeholders; "
                    "skip runtime replay and rely on deterministic auto-baseline",
                    self.name,
                    case_id,
                )
            elif self._has_custom_env_setup(case) and not self._run_sta_env_setup(case, topology):
                last_failure = self._snapshot_mapping(case.get("_last_failure"))
                if str(last_failure.get("phase", "")).strip().lower() != "setup_env":
                    self._record_runtime_failure(
                        case,
                        phase="setup_env",
                        comment="sta_env_setup failed",
                        category="configuration",
                        reason_code="sta_env_setup_failed",
                    )
                return False
        return True

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
        return self._command_resolver.split_safe_shell_commands(command)

    def _extract_cli_fragments(self, text: str) -> list[str]:
        return self._command_resolver.extract_cli_fragments(text)

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
        return self._command_resolver.sanitize_cli_fragment(fragment)

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

    @classmethod
    def _first_mac_address(cls, text: str) -> str:
        match = cls.MAC_ADDRESS_RE.search(str(text or ""))
        if match is None:
            return ""
        return match.group(0).lower()

    @staticmethod
    def _band_from_assoc_capture_field(field_name: str) -> str:
        lowered = str(field_name).strip().lower()
        if lowered.endswith("24g"):
            return "2.4g"
        if lowered.endswith("6g"):
            return "6g"
        if lowered.endswith("5g"):
            return "5g"
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
        return self._command_resolver.prefer_synthesized_readback(
            case, step, raw_command, candidate_commands
        )

    def _looks_executable(self, command: str) -> bool:
        return self._command_resolver.looks_executable(command)

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
        return self._command_resolver.select_fallback_commands(
            case, original_command, topology, step_id
        )

    @staticmethod
    def _is_unexecutable_result(result: dict[str, Any]) -> bool:
        return CommandResolver.is_unexecutable_result(result)

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
            match = re.match(r"([A-Za-z_][A-Za-z0-9_.()/-]*)\s*[:=]\s*(.*)$", line)
            if not match:
                continue
            key, value = match.groups()
            # Strip trailing ubus object/array delimiters first so quotes
            # immediately before commas/brackets still get normalized away.
            normalized = re.sub(r"[,}\]]+$", "", value).strip()
            normalized = normalized.strip("'\"")
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
        context: dict[str, Any] = {"steps": {}, "_aggregate_output": "", "_capture_raw": {}}
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
                context["_capture_raw"][capture_name] = output
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
        compact_actual = self._normalize_compare_text(actual_text)
        compact_expected = self._normalize_compare_text(expected_text)
        actual_mac = self._first_mac_address(actual_text)
        expected_mac = self._first_mac_address(expected_text)

        if op in {"contains"}:
            return (
                expected_text in actual_text
                or normalized_expected in normalized_actual
                or compact_expected in compact_actual
            )
        if op in {"not_contains"}:
            return (
                expected_text not in actual_text
                and normalized_expected not in normalized_actual
                and compact_expected not in compact_actual
            )
        if op in {"equals", "==", "eq"}:
            return (
                actual_text == expected_text
                or normalized_actual == normalized_expected
                or compact_actual == compact_expected
                or (actual_mac and expected_mac and actual_mac == expected_mac)
            )
        if op in {"!=", "not_equals", "ne"}:
            return (
                actual_text != expected_text
                and normalized_actual != normalized_expected
                and compact_actual != compact_expected
                and not (actual_mac and expected_mac and actual_mac == expected_mac)
            )
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

    @staticmethod
    def _normalize_compare_text(value: str) -> str:
        normalized = value.strip().strip("'\"")
        normalized = re.sub(r"([\[\{\(])\s+", r"\1", normalized)
        normalized = re.sub(r"\s+([\]\}\)])", r"\1", normalized)
        return normalized

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

    @staticmethod
    def _preprocess_script_lines(script: str) -> list[str]:
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
        return raw_lines

    def _iter_env_script_commands(self, script: str) -> list[tuple[str, str]]:
        commands: list[tuple[str, str]] = []
        target = "STA"

        for line in self._preprocess_script_lines(script):
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

    def _split_step_command_sequence(self, command: str) -> list[str]:
        if "\n" not in str(command):
            return [str(command)]

        logical_lines = self._preprocess_script_lines(str(command))
        if self._multiline_step_requires_single_shell(logical_lines):
            return ["\n".join(logical_lines).strip()]

        commands: list[str] = []
        for line in logical_lines:
            if line.lower().endswith(":"):
                continue
            first_token = line.split(maxsplit=1)[0].strip("`'\"")
            if first_token in self.CLI_FALLBACK_TOKENS or self._looks_shell_command(line):
                resolved_commands = self._split_safe_shell_commands(line)
            else:
                resolved_commands = self._extract_cli_fragments(line)
            for resolved in resolved_commands:
                if resolved:
                    commands.append(resolved)
        return commands or [str(command)]

    @classmethod
    def _multiline_step_requires_single_shell(cls, logical_lines: list[str]) -> bool:
        if len(logical_lines) <= 1:
            return False

        for line in logical_lines:
            stripped = line.strip()
            if not stripped or stripped.lower().endswith(":"):
                continue
            first_token = stripped.split(maxsplit=1)[0].strip("`'\"")
            token_base = first_token.rsplit("/", 1)[-1]
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", first_token):
                return True
            if token_base in cls.STATEFUL_SHELL_TOKENS:
                return True
        return False

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
        custom_wifi_gate_pending = field_name == "sta_env_setup" and self._has_explicit_wifi_bands(case)
        custom_6g_ocv_pending = (
            field_name == "sta_env_setup"
            and (
                "6g" in self._selected_sta_bands(case)
                or self._script_references_band(script, "6g")
            )
        )
        sta_wpa_hygiene_ifaces: set[str] = set()
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

            command = self._canonicalize_env_command(
                self._resolve_text(topology, raw_command)
            )
            if (
                custom_wifi_gate_pending
                and str(target_name).strip().upper() == "STA"
                and (
                    self._is_explicit_sta_connect_step(command)
                    or self._is_sta_link_check_command(command)
                )
            ):
                if custom_6g_ocv_pending:
                    dut_transport = self._transports.get("DUT")
                    if dut_transport is not None:
                        self._apply_6g_ocv_fix(dut_transport, case_id)
                    custom_6g_ocv_pending = False
                if not self._ensure_selected_dut_bss_ready(case):
                    return False
                custom_wifi_gate_pending = False
            if str(target_name).strip().upper() == "STA":
                iface = self._sta_wpa_supplicant_iface(command)
                if iface and iface not in sta_wpa_hygiene_ifaces:
                    for offset, hygiene_command in enumerate(
                        (
                            "killall wpa_supplicant 2>/dev/null || true",
                            "rm -rf /var/run/wpa_supplicant",
                            "mkdir -p /var/run/wpa_supplicant",
                        ),
                        start=1,
                    ):
                        if not self._run_required_command(
                            transport=transport,
                            case_id=case_id,
                            label=f"{field_name}[{index}].wpa_hygiene.{offset}",
                            command=hygiene_command,
                            timeout=20.0,
                        ):
                            return False
                    sta_wpa_hygiene_ifaces.add(iface)
            result = self._execute_env_command(transport, command, timeout=45.0)
            if not self._env_command_succeeded(command, result):
                if field_name == "sta_env_setup":
                    normalized_command = self._normalize_command_text(command).lower()
                    reason_code = "sta_env_setup_failed"
                    category = "configuration"
                    if self._is_explicit_sta_connect_step(command):
                        reason_code = "sta_band_connect_failed"
                        category = "environment"
                    elif (
                        "iw dev wl" in normalized_command and " link" in normalized_command
                    ) or re.fullmatch(r"wl -i wl[012](?:\.\d+)? status", normalized_command):
                        reason_code = "sta_band_link_failed"
                        category = "environment"
                    self._record_runtime_failure(
                        case,
                        phase="setup_env",
                        comment="sta_env_setup failed",
                        category=category,
                        reason_code=reason_code,
                        device=target_name,
                        band=self._band_from_text(command),
                        command=command,
                        output=self._env_output_text(result),
                        metadata={"field_name": field_name, "index": index},
                    )
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
            if (
                str(target_name).strip().upper() == "DUT"
                and (sync_command := self._wpa3_key_sync_command(command))
            ):
                if not self._run_required_command(
                    transport=transport,
                    case_id=case_id,
                    label=f"{field_name}[{index}].sync_psk",
                    command=sync_command,
                    timeout=30.0,
                ):
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
                "failed to open config file",
                "failed to read or parse configuration",
                "failed to connect to non-global ctrl_ifname",
                "ifconfig: bad address",
                "ping: so_bindtodevice",
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
        if re.fullmatch(r"wl -i wl[012](?:\.\d+)? bss", lowered_command):
            return output.strip().lower() == "up"
        if re.fullmatch(r"wl -i wl[012](?:\.\d+)? status", lowered_command):
            if "not associated" in lowered_output:
                return False
            return any(
                marker in lowered_output
                for marker in (
                    "ssid:",
                    "bssid:",
                    "mode:",
                    "channel:",
                )
            )
        if "sta_info" in lowered_command:
            return bool(output.strip())
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

    @classmethod
    def _is_sta_link_check_command(cls, command: str) -> bool:
        normalized = cls._normalize_command_text(command).lower()
        if "iw dev wl" in normalized and " link" in normalized:
            return True
        return bool(re.fullmatch(r"wl -i wl[012](?:\.\d+)? status", normalized))

    @classmethod
    def _wpa3_key_sync_command(cls, command: str) -> str | None:
        normalized = cls._normalize_command_text(command)
        match = re.search(
            r"WiFi\.AccessPoint\.(\d+)\.Security\.SAEPassphrase=(.+)$",
            normalized,
            re.IGNORECASE,
        )
        if match is None:
            return None
        ap_index, passphrase = match.groups()
        return f"ubus-cli WiFi.AccessPoint.{ap_index}.Security.KeyPassPhrase={passphrase}"

    @classmethod
    def _sta_wpa_supplicant_iface(cls, command: str) -> str | None:
        normalized = cls._normalize_command_text(command)
        match = re.search(
            r"\bwpa_supplicant\b.*\s-i\s+(wl[012](?:\.\d+)?)\b",
            normalized,
            re.IGNORECASE,
        )
        if match is None:
            return None
        return match.group(1)

    @classmethod
    def _canonicalize_env_command(cls, command: str) -> str:
        text = str(command or "")
        if "\n" not in text:
            return text
        return cls._canonicalize_multiline_printf(text)

    @staticmethod
    def _canonicalize_multiline_printf(command: str) -> str:
        match = re.fullmatch(r"printf '([\s\S]*)'\s*>\s*(\S+)", command.strip())
        if match is None:
            return command
        body, target = match.groups()
        escaped_body = body.replace("\\", "\\\\").replace("\n", "\\n")
        return f"printf '%b' {shlex.quote(escaped_body)} > {target}"

    @staticmethod
    def _wrap_multiline_shell_command(command: str) -> str:
        text = str(command or "").strip()
        if "\n" not in text:
            return text
        escaped_body = text.replace("\\", "\\\\").replace("\n", "\\n")
        return f"printf '%b' {shlex.quote(escaped_body)} | sh"

    def _selected_sta_bands(self, case: dict[str, Any]) -> tuple[str, ...]:
        declared = self._case_declared_bands(case)
        if declared:
            return declared
        marker_chunks: list[str] = []
        for key in ("hlapi_command", "verification_command"):
            value = case.get(key)
            if isinstance(value, list):
                marker_chunks.extend(v for v in value if isinstance(v, str) and v.strip())
            elif isinstance(value, str) and value.strip():
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
                    if isinstance(value, list):
                        marker_chunks.extend(v for v in value if isinstance(v, str) and v.strip())
                    elif isinstance(value, str) and value.strip():
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
        return tuple(selected or self._sta_available_bands)

    @staticmethod
    def _has_custom_env_setup(case: dict[str, Any]) -> bool:
        return bool(
            isinstance(case.get("sta_env_setup"), str)
            and case["sta_env_setup"].strip()
            and not Plugin._sta_env_setup_has_unresolved_placeholders(case)
        )

    @classmethod
    def _sta_env_setup_has_unresolved_placeholders(cls, case: dict[str, Any]) -> bool:
        script = case.get("sta_env_setup")
        if not isinstance(script, str) or not script.strip():
            return False
        normalized = cls._normalize_command_text(script)
        return bool(
            re.search(r"\bwlx\b", normalized, re.IGNORECASE)
            or re.search(r"\b192\.168\.1\.x\b", normalized, re.IGNORECASE)
        )

    def _should_auto_prepare_wifi_bands(self, case: dict[str, Any]) -> bool:
        return (
            not self._has_custom_env_setup(case)
            and self._has_explicit_wifi_bands(case)
            and self._transports.get("STA") is not None
        )

    def _has_explicit_wifi_bands(self, case: dict[str, Any]) -> bool:
        """Return True when the case explicitly references WiFi AP/radio bands."""
        if self._case_declared_bands(case):
            return True
        marker_chunks: list[str] = []
        for key in ("hlapi_command", "verification_command"):
            value = case.get(key)
            if isinstance(value, list):
                marker_chunks.extend(v for v in value if isinstance(v, str) and v.strip())
            elif isinstance(value, str) and value.strip():
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
                    if isinstance(value, list):
                        marker_chunks.extend(v for v in value if isinstance(v, str) and v.strip())
                    elif isinstance(value, str) and value.strip():
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

    def _sta_band_iface(self, band: str) -> str | None:
        profile = self._band_baseline_profile(band)
        if profile is None:
            return None
        iface = str(profile.get("iface", "")).strip()
        return iface or None

    @classmethod
    def _is_explicit_sta_connect_step(cls, command: str) -> bool:
        normalized = cls._normalize_command_text(command)
        lowered = normalized.lower()
        if "wpa_cli" in lowered and " status" in lowered:
            return False
        patterns = (
            r"\bwl\s+-i\s+wl[012](?:\.\d+)?\s+join\b",
            r"\biw\s+dev\s+wl[012](?:\.\d+)?\s+connect\b",
            r"(?:^|[;&|]\s*)wpa_supplicant\b",
            r"\bwpa_cli\b.*\b(reconnect|reassociate|select_network|enable_network)\b",
        )
        return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns)

    def _case_sta_band_connect_commands(self, case: dict[str, Any], band: str) -> list[str]:
        steps = case.get("steps")
        if not isinstance(steps, list):
            return []

        normalized_band = str(band).strip().lower()
        iface = self._sta_band_iface(normalized_band)
        for step in steps:
            step_mapping = self._as_mapping(step)
            if str(step_mapping.get("action", "")).strip().lower() != "exec":
                continue
            if str(step_mapping.get("target", "")).strip().upper() != "STA":
                continue

            command_lines = step_command_lines(step_mapping.get("command"))
            if not command_lines:
                continue
            command = stringify_step_command(step_mapping.get("command"))

            step_band = str(step_mapping.get("band", "")).strip().lower()
            if step_band and step_band != normalized_band:
                continue
            if not step_band and iface and not re.search(rf"\b{re.escape(iface)}(?:\.\d+)?\b", command):
                continue
            if not self._is_explicit_sta_connect_step(command):
                continue

            collected: list[str] = []
            for command_line in command_lines:
                collected.extend(
                    resolved_command
                    for _, resolved_command in self._iter_env_script_commands(command_line)
                )
            if collected:
                return collected
        return []

    def _sta_band_client_prep_commands(self, band: str) -> list[str]:
        normalized_band = str(band).strip().lower()
        profile = self._band_baseline_profile(normalized_band)
        if profile is None:
            return []
        iface = str(profile["iface"]).strip()
        ap_commands = (
            f"ubus-cli WiFi.AccessPoint.{profile['ap']}.Enable=0",
            f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
        )
        pre_mode_commands = self._profile_command_list(profile, "sta_pre_mode_commands")
        pre_start_commands = self._profile_command_list(profile, "sta_pre_start_commands")
        if not pre_mode_commands and normalized_band != "6g":
            pre_mode_commands = [f"ifconfig {iface} down"]
        if not pre_start_commands and normalized_band != "6g":
            pre_start_commands = [f"wl -i {iface} up", f"ifconfig {iface} up"]
        return [
            *ap_commands,
            "sleep 3",
            f"wpa_cli -i {iface} terminate 2>/dev/null || true",
            f"iw dev {iface}.1 del 2>/dev/null || true",
            f"iw dev {iface} disconnect 2>/dev/null || true",
            *(
                []
                if normalized_band == "6g"
                else [f"wl -i {iface} ap 0"]
            ),
            *pre_mode_commands,
            f"iw dev {iface} set type managed",
            *pre_start_commands,
        ]

    def _case_sta_band_verify_command(self, commands: list[str], band: str) -> str:
        iface = self._sta_band_iface(band)
        if iface is None:
            return ""
        for command in commands:
            normalized = self._normalize_command_text(command)
            lowered = normalized.lower()
            if re.fullmatch(rf"iw dev {re.escape(iface)}(?:\.\d+)? link", lowered):
                return normalized
            if re.fullmatch(rf"wl -i {re.escape(iface)}(?:\.\d+)? status", lowered):
                return normalized
            if "wpa_cli" in lowered and f"-i {iface}" in lowered and " status" in lowered:
                return normalized
        return f"iw dev {iface} link"

    def _case_sta_band_status_commands(self, case: dict[str, Any], band: str) -> list[str]:
        steps = case.get("steps")
        if not isinstance(steps, list):
            return []

        normalized_band = str(band).strip().lower()
        iface = self._sta_band_iface(normalized_band)
        if iface is None:
            return []

        collected: list[str] = []
        for step in steps:
            step_mapping = self._as_mapping(step)
            if str(step_mapping.get("action", "")).strip().lower() != "exec":
                continue
            if str(step_mapping.get("target", "")).strip().upper() != "STA":
                continue

            step_band = str(step_mapping.get("band", "")).strip().lower()
            if step_band and step_band != normalized_band:
                continue

            command_lines = step_command_lines(step_mapping.get("command"))
            for command_line in command_lines:
                for _, resolved_command in self._iter_env_script_commands(command_line):
                    normalized = self._normalize_command_text(resolved_command)
                    lowered = normalized.lower()
                    if re.fullmatch(rf"iw dev {re.escape(iface)}(?:\.\d+)? link", lowered):
                        collected.append(normalized)
                    elif re.fullmatch(rf"wl -i {re.escape(iface)}(?:\.\d+)? status", lowered):
                        collected.append(normalized)
                    elif "wpa_cli" in lowered and f"-i {iface}" in lowered and " status" in lowered:
                        collected.append(normalized)
        return collected

    def _sta_band_verify_command(self, case: dict[str, Any], band: str) -> str:
        commands = self._case_sta_band_connect_commands(case, band)
        if commands:
            verify_command = self._case_sta_band_verify_command(commands, band)
            if verify_command:
                return verify_command
        iface = self._sta_band_iface(band)
        return f"iw dev {iface} link" if iface else ""

    def _run_case_sta_band_connect_sequence(
        self,
        *,
        case: dict[str, Any],
        band: str,
        transport: Any,
    ) -> bool | None:
        commands = self._case_sta_band_connect_commands(case, band)
        iface = self._sta_band_iface(band)
        if not commands or iface is None:
            return None

        case_id = str(case.get("id", ""))
        label_band = str(band).replace(".", "")
        prep_commands = self._sta_band_client_prep_commands(band)
        verify_cmd = self._case_sta_band_verify_command(commands, band)
        for attempt in range(1, 4):
            prep_failed = False
            for index, command in enumerate(prep_commands, start=1):
                if not self._run_required_command(
                    transport=transport,
                    case_id=case_id,
                    label=f"sta_{label_band}_case_prep.{attempt}.{index}",
                    command=command,
                ):
                    prep_failed = True
                    break
            if prep_failed:
                continue

            command_failed = False
            for index, command in enumerate(commands, start=1):
                if not self._run_required_command(
                    transport=transport,
                    case_id=case_id,
                    label=f"sta_{label_band}_case.{attempt}.{index}",
                    command=command,
                ):
                    command_failed = True
                    break
            if command_failed:
                continue

            verify_result = self._execute_env_command(transport, verify_cmd, timeout=20.0)
            if self._env_command_succeeded(verify_cmd, verify_result):
                return True
            log.warning(
                "[%s] verify_env: %s sta_%s case step verify attempt=%d failed",
                self.name,
                case_id,
                label_band,
                attempt,
            )
        return False

    def _connect_with_retry(
        self,
        *,
        transport: Any,
        case_id: str,
        label: str,
        connect_cmd: str,
        verify_cmd: str | Sequence[str],
        attempts: int = 3,
        sleep_seconds: int = 3,
    ) -> bool:
        verify_commands = (
            (verify_cmd,)
            if isinstance(verify_cmd, str)
            else tuple(command for command in verify_cmd if command)
        )
        if not verify_commands:
            return False
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
            for candidate_verify_cmd in verify_commands:
                verify_result = self._execute_env_command(
                    transport,
                    candidate_verify_cmd,
                    timeout=20.0,
                )
                if self._env_command_succeeded(candidate_verify_cmd, verify_result):
                    return True
            log.warning(
                "[%s] verify_env: %s %s verify attempt=%d failed",
                self.name,
                case_id,
                label,
                attempt,
            )
        return False

    def _wait_for_6g_sta_ap_teardown(
        self,
        *,
        transport: Any,
        case_id: str,
        iface: str,
        attempts: int = 10,
        sleep_seconds: float = 1.0,
    ) -> bool:
        for attempt in range(1, max(1, attempts) + 1):
            bss_result = self._execute_env_command(transport, f"wl -i {iface} bss", timeout=10.0)
            bss_output = self._env_output_text(bss_result).strip().lower()
            vif_result = self._execute_env_command(
                transport, f"iw dev {iface}.1 info", timeout=10.0
            )
            vif_output = self._env_output_text(vif_result).strip()
            vif_present = int(vif_result.get("returncode", 1)) == 0 and bool(vif_output)
            if bss_output.endswith("down"):
                if vif_present:
                    self._execute_env_command(
                        transport, f"iw dev {iface}.1 del 2>/dev/null || true", timeout=10.0
                    )
                return True
            if vif_present:
                self._execute_env_command(
                    transport, f"iw dev {iface}.1 del 2>/dev/null || true", timeout=10.0
                )
            if not bss_output.endswith("down"):
                self._execute_env_command(
                    transport, f"iw dev {iface} disconnect 2>/dev/null || true", timeout=10.0
                )
            time.sleep(max(0.0, sleep_seconds))

        log.warning(
            "[%s] verify_env: %s sta_6g teardown did not settle (iface=%s, bss=%s, vif_present=%s)",
            self.name,
            case_id,
            iface,
            self._preview_value(bss_output or "<empty>", limit=64),
            vif_present,
        )
        return False

    def _capture_assoc_mac_fallback(
        self,
        *,
        case: dict[str, Any],
        step: dict[str, Any],
        target_name: str,
        transport: Any,
        timeout: float,
    ) -> tuple[dict[str, Any], str, str] | None:
        if str(target_name).strip().upper() != "DUT":
            return None

        capture_name = str(step.get("capture", "")).strip()
        if not capture_name:
            return None
        field_name = self._field_name_from_capture(case, capture_name)
        if not self.ASSOC_MAC_CAPTURE_FIELD_RE.fullmatch(field_name):
            return None

        band = self._normalize_band_name(step.get("band"))
        if not band:
            band = self._band_from_text(stringify_step_command(step.get("command")))
        if not band:
            band = self._band_from_assoc_capture_field(field_name)
        profile = self._band_baseline_profile(band)
        if not isinstance(profile, dict):
            return None

        ap_index = str(profile.get("ap", "")).strip()
        if not ap_index:
            return None
        fallback_command = f'ubus-cli "WiFi.AccessPoint.{ap_index}.AssociatedDevice.*.MACAddress?"'
        result = self._execute_env_command(transport, fallback_command, timeout=max(timeout, 15.0))
        if not self._env_command_succeeded(fallback_command, result):
            return None

        mac = self._first_mac_address(self._env_output_text(result))
        if not mac:
            return None
        return {field_name: mac}, f"{field_name}={mac}", fallback_command

    def _run_sta_band_connect_sequence(self, case: dict[str, Any]) -> bool:
        case_id = str(case.get("id", ""))
        sta = self._transports.get("STA")
        if sta is None:
            return False
        selected_bands = self._selected_sta_bands(case)

        # Suppress kernel console messages to prevent UART prompt detection issues
        # (Broadcom dhd driver floods console during WiFi mode switches).
        self._execute_env_command(sta, "dmesg -n 1", timeout=5.0)

        # 5G (WPA2-Personal via wpa_supplicant)
        if "5g" in selected_bands:
            profile = self._band_baseline_profile("5g")
            if profile is None:
                return False
            iface = str(profile["iface"])
            ctrl_command = self._profile_command(profile, "sta_ctrl_command")
            connect_command = self._profile_command(profile, "sta_connect_command")
            case_sequence_ok = self._run_case_sta_band_connect_sequence(
                case=case,
                band="5g",
                transport=sta,
            )
            if case_sequence_ok is False:
                log.warning(
                    "[%s] verify_env: %s sta_5g case sequence failed, falling back to deterministic baseline connect",
                    self.name,
                    case_id,
                )
            if case_sequence_ok is not True:
                five_g_prep = (
                    f"ubus-cli WiFi.AccessPoint.{profile['ap']}.Enable=0",
                    f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
                    "killall wpa_supplicant 2>/dev/null || true",
                    f"iw dev {iface}.1 del 2>/dev/null || true",
                    f"iw dev {iface} disconnect 2>/dev/null || true",
                    f"ifconfig {iface} down",
                    f"wl -i {iface} down",
                    f"wl -i {iface} ap 0",
                    f"iw dev {iface} set type managed",
                    f"wl -i {iface} up",
                    f"ifconfig {iface} up",
                    "rm -rf /var/run/wpa_supplicant",
                    "mkdir -p /var/run/wpa_supplicant",
                    *self._sta_wpa_config_commands(profile),
                    f"wpa_supplicant -B -D nl80211 -i {iface} -c {self._sta_wpa_config_path(profile)} -C /var/run/wpa_supplicant",
                    "sleep 5",
                    *(
                        self._render_baseline_template(command, profile)
                        for command in profile.get("sta_post_start_commands", [])
                    ),
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
                    label="sta_5g_ctrl",
                    connect_cmd=ctrl_command,
                    verify_cmd=ctrl_command,
                    attempts=3,
                    sleep_seconds=1,
                ):
                    return False
                if not self._connect_with_retry(
                    transport=sta,
                    case_id=case_id,
                    label="sta_5g",
                    connect_cmd=connect_command,
                    verify_cmd=f"iw dev {iface} link",
                    attempts=3,
                    sleep_seconds=5,
                ):
                    driver_join_command = self._profile_command(profile, "sta_driver_join_command")
                    if not driver_join_command:
                        return False
                    if not self._connect_with_retry(
                        transport=sta,
                        case_id=case_id,
                        label="sta_5g_driver",
                        connect_cmd=driver_join_command,
                        verify_cmd=f"wl -i {iface} status",
                        attempts=3,
                        sleep_seconds=5,
                    ):
                        return False

        # 6G (SAE) — non-fatal: STA Broadcom dhd driver may not support
        # SAE-H2E required by DUT 6G; failure is logged but does not block.
        if "6g" in selected_bands:
            profile = self._band_baseline_profile("6g")
            if profile is None:
                return False
            iface = str(profile["iface"])
            ctrl_command = self._profile_command(profile, "sta_ctrl_command")
            connect_command = self._profile_command(profile, "sta_connect_command")
            status_command = self._profile_command(profile, "sta_status_command")
            pre_mode_commands = self._profile_command_list(profile, "sta_pre_mode_commands")
            pre_start_commands = self._profile_command_list(profile, "sta_pre_start_commands")
            six_g_prep = (
                f"ubus-cli WiFi.AccessPoint.{profile['ap']}.Enable=0",
                f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
                "sleep 3",
                f"wpa_cli -i {iface} terminate 2>/dev/null || true",
                f"rm -f /var/run/wpa_supplicant/{iface} 2>/dev/null || true",
                f"iw dev {iface}.1 del 2>/dev/null || true",
                f"iw dev {iface} disconnect 2>/dev/null || true",
                *pre_mode_commands,
                f"iw dev {iface} set type managed",
                *pre_start_commands,
                "mkdir -p /var/run/wpa_supplicant",
                *self._sta_wpa_config_commands(profile),
                f"wpa_supplicant -B -D nl80211 -i {iface} -c {self._sta_wpa_config_path(profile)} -C /var/run/wpa_supplicant",
                "sleep 5",
                *(
                    self._render_baseline_template(command, profile)
                    for command in profile.get("sta_post_start_commands", [])
                ),
            )
            six_g_ok = True
            for idx, cmd in enumerate(six_g_prep[:7], start=1):
                if not self._run_required_command(
                    transport=sta,
                    case_id=case_id,
                    label=f"sta_6g_prep.{idx}",
                    command=cmd,
                ):
                    six_g_ok = False
                    break
            if six_g_ok:
                six_g_ok = self._wait_for_6g_sta_ap_teardown(
                    transport=sta,
                    case_id=case_id,
                    iface=iface,
                )
            if six_g_ok:
                for idx, cmd in enumerate(six_g_prep[7:], start=8):
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
                    connect_cmd=ctrl_command,
                    verify_cmd=ctrl_command,
                    attempts=3,
                    sleep_seconds=1,
                )
            if six_g_ok:
                six_g_ok = self._connect_with_retry(
                    transport=sta,
                    case_id=case_id,
                    label="sta_6g",
                    connect_cmd=connect_command,
                    verify_cmd=(
                        f"iw dev {iface} link",
                        status_command,
                        f"wl -i {iface} status",
                    ),
                    attempts=3,
                    sleep_seconds=8,
                )
            if six_g_ok:
                self._run_required_command(
                    transport=sta,
                    case_id=case_id,
                    label="sta_6g_status",
                    command=status_command,
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
            profile = self._band_baseline_profile("2.4g")
            if profile is None:
                return False
            iface = str(profile["iface"])
            ctrl_command = self._profile_command(profile, "sta_ctrl_command")
            connect_command = self._profile_command(profile, "sta_connect_command")
            case_sequence_ok = self._run_case_sta_band_connect_sequence(
                case=case,
                band="2.4g",
                transport=sta,
            )
            if case_sequence_ok is False:
                log.warning(
                    "[%s] verify_env: %s sta_24g case sequence failed, falling back to deterministic baseline connect",
                    self.name,
                    case_id,
                )
            if case_sequence_ok is not True:
                two_g_prep = (
                    f"ubus-cli WiFi.AccessPoint.{profile['ap']}.Enable=0",
                    f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
                    f"wpa_cli -i {iface} terminate 2>/dev/null || true",
                    f"iw dev {iface}.1 del 2>/dev/null || true",
                    f"iw dev {iface} disconnect 2>/dev/null || true",
                    f"ifconfig {iface} down",
                    f"wl -i {iface} down",
                    f"wl -i {iface} ap 0",
                    f"iw dev {iface} set type managed",
                    f"wl -i {iface} up",
                    f"ifconfig {iface} up",
                    f"rm -f /var/run/wpa_supplicant/{iface} 2>/dev/null || true",
                    "mkdir -p /var/run/wpa_supplicant",
                    *self._sta_wpa_config_commands(profile),
                    f"wpa_supplicant -B -D nl80211 -i {iface} -c {self._sta_wpa_config_path(profile)} -C /var/run/wpa_supplicant",
                    "sleep 5",
                    *(
                        self._render_baseline_template(command, profile)
                        for command in profile.get("sta_post_start_commands", [])
                    ),
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
                    label="sta_24g_ctrl",
                    connect_cmd=ctrl_command,
                    verify_cmd=ctrl_command,
                    attempts=3,
                    sleep_seconds=1,
                ):
                    return False
                if not self._connect_with_retry(
                    transport=sta,
                    case_id=case_id,
                    label="sta_24g",
                    connect_cmd=connect_command,
                    verify_cmd=(
                        f"iw dev {iface} link",
                        f"wl -i {iface} status",
                    ),
                    attempts=3,
                    sleep_seconds=8,
                ):
                    return False
        return True

    def _run_sta_band_baseline(self, case: dict[str, Any]) -> bool:
        case_id = str(case.get("id", ""))
        dut = self._transports.get("DUT")
        if dut is None:
            return False
        selected_bands = self._selected_sta_bands(case)

        # Baseline repair must converge to deterministic SSID/security, not merely
        # "BSS is up". Otherwise remediation may succeed transiently but the next
        # attempt still inherits a drifted AP profile.
        all_up = True
        for band in selected_bands:
            profile = self._band_baseline_profile(band)
            if profile is None:
                return False
            result = self._execute_env_command(dut, f"wl -i {profile['iface']} bss", timeout=10.0)
            if "up" not in self._env_output_text(result).strip().lower():
                all_up = False
                break
        if all_up:
            log.info(
                "[%s] verify_env: %s BSS already up, re-applying deterministic DUT baseline",
                self.name,
                case_id,
            )

        dut_commands: list[str] = []
        for band in selected_bands:
            profile = self._band_baseline_profile(band)
            if profile is None:
                return False
            dut_commands.extend(self._dut_baseline_commands(profile))
        # Apply DUT config. We avoid forcing wld_gen here because live DUT runs
        # may drop BSS into prolonged down state during remediation loops.
        for index, command in enumerate(dut_commands, start=1):
            result = self._execute_env_command(dut, command, timeout=30.0)
            if not self._env_command_succeeded(command, result):
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment=f"sta_baseline[{index}] failed",
                    category="environment",
                    reason_code="dut_band_rebaseline_failed",
                    device="DUT",
                    band=self._band_from_text(command),
                    command=command,
                    output=self._env_output_text(result),
                )
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

        # For 6G: patch ocv=0 into hapd.conf after wld regeneration to prevent mfp_ocv BSS loop.
        if "6g" in selected_bands:
            self._apply_6g_ocv_fix(dut, case_id)

        # Wait for hostapd to reload after DUT config changes.
        self._execute_env_command(dut, "sleep 5", timeout=10.0)
        return self._ensure_selected_dut_bss_ready(case)

    def _selected_dut_bss_checks(self, case: dict[str, Any]) -> list[tuple[str, str]]:
        selected_bands = self._selected_sta_bands(case)
        bss_checks: list[tuple[str, str]] = []
        for band in selected_bands:
            iface = self._sta_band_iface(band)
            if iface:
                bss_checks.append((band, f"wl -i {iface} bss"))
        return bss_checks

    def _ensure_selected_dut_bss_ready(self, case: dict[str, Any]) -> bool:
        case_id = str(case.get("id", ""))
        dut = self._transports.get("DUT")
        if dut is None:
            return False

        bss_checks = self._selected_dut_bss_checks(case)
        bss_max_wait = 60.0
        bss_poll_interval = 5.0
        for index, (band, command) in enumerate(bss_checks, start=1):
            if self._wait_for_dut_bss_ready(
                case,
                dut,
                case_id=case_id,
                band=band,
                index=index,
                command=command,
                timeout_seconds=bss_max_wait,
                poll_interval=bss_poll_interval,
            ):
                continue
            needs_stack_reload = self._has_custom_env_setup(case) or band == "6g"
            if needs_stack_reload:
                reloaded = self._reload_dut_wifi_stack(case, dut, case_id=case_id, band=band)
                if reloaded and self._wait_for_dut_bss_ready(
                    case,
                    dut,
                    case_id=case_id,
                    band=band,
                    index=index,
                    command=command,
                    timeout_seconds=30.0,
                    poll_interval=bss_poll_interval,
                ):
                    continue
            if not self._bounce_dut_band(case, dut, case_id=case_id, band=band):
                return False
            if not self._wait_for_dut_bss_ready(
                case,
                dut,
                case_id=case_id,
                band=band,
                index=index,
                command=command,
                timeout_seconds=30.0,
                poll_interval=bss_poll_interval,
            ):
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment=f"DUT {band} BSS remained down after baseline bounce",
                    category="environment",
                    reason_code="dut_band_bss_not_ready",
                    device="DUT",
                    band=band,
                    command=command,
                )
                log.warning(
                    "[%s] verify_env: %s sta_baseline_bss[%d] still not ready after DUT bounce cmd=%s",
                    self.name,
                    case_id,
                    index,
                    command,
                )
                return False
        return True

    def _reload_dut_wifi_stack(
        self,
        case: dict[str, Any],
        dut: Any,
        *,
        case_id: str,
        band: str,
    ) -> bool:
        log.info(
            "[%s] verify_env: %s DUT %s BSS still down, reloading wld_gen",
            self.name,
            case_id,
            band,
        )
        command = "/etc/init.d/wld_gen start"
        result = self._execute_env_command(dut, command, timeout=60.0)
        if self._env_command_succeeded(command, result):
            self._execute_env_command(dut, "sleep 5", timeout=10.0)
            if band == "6g":
                self._apply_6g_ocv_fix(dut, case_id)
            return True
        self._record_runtime_failure(
            case,
            phase="verify_env",
            comment="dut wifi stack reload failed",
            category="environment",
            reason_code="dut_wifi_stack_reload_failed",
            device="DUT",
            band=band,
            command=command,
            output=self._env_output_text(result),
        )
        log.warning(
            "[%s] verify_env: %s dut_wifi_stack_reload failed band=%s rc=%s out=%s",
            self.name,
            case_id,
            band,
            int(result.get("returncode", 1)),
            self._preview_value(self._env_output_text(result)),
        )
        return False

    def _wait_for_dut_bss_ready(
        self,
        case: dict[str, Any],
        dut: Any,
        *,
        case_id: str,
        band: str,
        index: int,
        command: str,
        timeout_seconds: float,
        poll_interval: float,
    ) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            result = self._execute_env_command(dut, command, timeout=20.0)
            out = self._env_output_text(result).strip().lower()
            if "up" in out:
                return True
            log.info(
                "[%s] verify_env: %s bss[%d] not ready yet (%s), retrying...",
                self.name,
                case_id,
                index,
                out,
            )
            self._execute_env_command(dut, f"sleep {int(poll_interval)}", timeout=poll_interval + 5)
        log.warning(
            "[%s] verify_env: %s sta_baseline_bss[%d] not ready after %.0fs cmd=%s",
            self.name,
            case_id,
            index,
            timeout_seconds,
            command,
        )
        return False

    def _apply_6g_ocv_fix(self, dut: Any, case_id: str) -> None:
        """Patch ocv=0 into /tmp/wl1_hapd.conf and restart hostapd to prevent mfp_ocv BSS loop.

        BCM 6G firmware returns -23 (UNSUPPORTED) for the mfp_ocv IOCTL when ieee80211w=2
        is configured with SAE. Inserting ocv=0 prevents the IOCTL call and stops the
        ~11-second BSS loop. Must be called after every wld-triggered 6G hostapd restart.
        Only wl1 is targeted because AP4 (wl1.1) is disabled in the 6G baseline.
        """
        # Poll until wld regenerates wl1_hapd.conf with ieee80211w= present (MFP/SAE config).
        poll_cmd = "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT"
        ready = False
        for _ in range(6):
            result = self._execute_env_command(dut, poll_cmd, timeout=5.0)
            if "READY" in self._env_output_text(result):
                ready = True
                break
            self._execute_env_command(dut, "sleep 2", timeout=5.0)
        if not ready:
            log.warning(
                "[%s] verify_env: %s 6G wl1_hapd.conf ieee80211w= not found after 12s, patching anyway",
                self.name,
                case_id,
            )
        # Replace-or-insert: delete any existing ocv= line, then add ocv=0 after ieee80211w=.
        # This corrects both missing and wrong (ocv=1) values.
        patch_cmd = "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf"
        verify_cmd = "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1"
        hostapd_socket_cmd = "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT"
        hostapd_process_cmd = "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT"
        bss_cmd = "wl -i wl1 bss"

        def patch_and_verify() -> bool:
            self._execute_env_command(dut, patch_cmd, timeout=10.0)
            verify_result = self._execute_env_command(dut, verify_cmd, timeout=5.0)
            return "ocv=0" in self._env_output_text(verify_result)

        def restart_hostapd() -> None:
            # wl1 can drift back to managed mode after wld/hostapd crashes; restore AP mode first.
            for cmd in (
                "pid=$(pgrep -f '/tmp/wl1_hapd.conf' 2>/dev/null | head -n1); if [ -n \"$pid\" ]; then kill \"$pid\" 2>/dev/null || true; fi",
                "sleep 2",
                "rm -f /var/run/hostapd/wl1 /var/run/hostapd/wl1.1",
                "wl -i wl1 ap 1",
                "wl -i wl1 up",
                "ifconfig wl1 up",
                "hostapd -ddt -B /tmp/wl1_hapd.conf",
                "sleep 2",
            ):
                self._execute_env_command(dut, cmd, timeout=15.0)

        stabilized = False
        for attempt in range(1, 4):
            if not patch_and_verify():
                log.warning(
                    "[%s] verify_env: %s 6G ocv=0 verify failed — BSS loop may persist",
                    self.name,
                    case_id,
                )
            # On current lab firmware, restarting wl1 hostapd can leave stale control
            # sockets behind, flip wl1 back to managed mode, and trigger a wld rewrite
            # that drops ocv=0. Restore AP mode first and keep looping until ocv and the
            # DUT BSS stay present together, plus either the hostapd control socket or the
            # restarted hostapd process is visible.
            restart_hostapd()
            for cmd in (
                "wl -i wl1 bss up",
                "sleep 2",
                "sleep 3",
            ):
                self._execute_env_command(dut, cmd, timeout=15.0)
            ocv_ok = "ocv=0" in self._env_output_text(
                self._execute_env_command(dut, verify_cmd, timeout=5.0)
            )
            socket_ok = "READY" in self._env_output_text(
                self._execute_env_command(dut, hostapd_socket_cmd, timeout=5.0)
            )
            process_ok = "READY" in self._env_output_text(
                self._execute_env_command(dut, hostapd_process_cmd, timeout=5.0)
            )
            bss_ok = self._env_output_text(
                self._execute_env_command(dut, bss_cmd, timeout=5.0)
            ).strip().lower() == "up"
            if ocv_ok and (socket_ok or process_ok) and bss_ok:
                stabilized = True
                break
            log.info(
                "[%s] verify_env: %s 6G restart attempt=%d unstable "
                "(ocv=%s socket=%s process=%s bss=%s), retrying",
                self.name,
                case_id,
                attempt,
                ocv_ok,
                socket_ok,
                process_ok,
                bss_ok,
            )
        if not stabilized:
            log.warning(
                "[%s] verify_env: %s 6G ocv fix did not stabilize wl1 after retries",
                self.name,
                case_id,
            )
        log.info("[%s] verify_env: %s 6G ocv=0 fix applied, wl1 hostapd restarted", self.name, case_id)

    def _bounce_dut_band(
        self,
        case: dict[str, Any],
        dut: Any,
        *,
        case_id: str,
        band: str,
    ) -> bool:
        profile = self._band_baseline_profile(band)
        if profile is None:
            return False
        bounce_commands = (
            f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
            f"ubus-cli WiFi.AccessPoint.{profile['ap']}.Enable=0",
            "sleep 2",
            f"ubus-cli WiFi.Radio.{profile['radio']}.Enable=1",
            f"ubus-cli WiFi.AccessPoint.{profile['secondary_ap']}.Enable=0",
            f"ubus-cli WiFi.AccessPoint.{profile['ap']}.Enable=1",
            "sleep 5",
        )
        log.info("[%s] verify_env: %s DUT %s BSS down, bouncing AP.%s", self.name, case_id, band, profile["ap"])
        for index, command in enumerate(bounce_commands, start=1):
            result = self._execute_env_command(dut, command, timeout=20.0)
            if self._env_command_succeeded(command, result):
                continue
            self._record_runtime_failure(
                case,
                phase="verify_env",
                comment=f"dut_bounce[{index}] failed",
                category="environment",
                reason_code="dut_band_bounce_failed",
                device="DUT",
                band=band,
                command=command,
                output=self._env_output_text(result),
            )
            log.warning(
                "[%s] verify_env: %s dut_bounce[%d] failed band=%s rc=%s cmd=%s out=%s",
                self.name,
                case_id,
                index,
                band,
                int(result.get("returncode", 1)),
                command,
                self._preview_value(self._env_output_text(result)),
            )
            return False
        if band == "6g":
            self._apply_6g_ocv_fix(dut, case_id)
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
            status_commands = self._case_sta_band_status_commands(case, band)
            candidate_commands = status_commands or [
                f"iw dev {sta_iface} link",
                f"wl -i {sta_iface} status",
            ]
            deduped_commands: list[str] = []
            seen_commands: set[str] = set()
            for candidate_command in candidate_commands:
                key = candidate_command.lower()
                if key in seen_commands:
                    continue
                seen_commands.add(key)
                deduped_commands.append(candidate_command)

            link_command = deduped_commands[0]
            link_result = self._execute_env_command(sta, link_command, timeout=15.0)
            link_stdout = self._env_output_text(link_result)
            link_ok = self._env_command_succeeded(link_command, link_result)
            if not link_ok:
                for fallback_command in deduped_commands[1:]:
                    fallback_result = self._execute_env_command(sta, fallback_command, timeout=15.0)
                    fallback_stdout = self._env_output_text(fallback_result)
                    if self._env_command_succeeded(fallback_command, fallback_result):
                        link_command = fallback_command
                        link_result = fallback_result
                        link_stdout = fallback_stdout
                        link_ok = True
                        break
            elif status_commands:
                for status_command in deduped_commands[1:]:
                    self._execute_env_command(sta, status_command, timeout=15.0)
            if not link_ok:
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment=f"STA {band} link check failed",
                    category="environment",
                    reason_code="sta_band_link_failed",
                    device="STA",
                    band=band,
                    command=link_command,
                    output=link_stdout,
                )
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
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment=f"DUT {band} associated-device check failed",
                    category="environment",
                    reason_code="dut_assoc_check_failed",
                    device="DUT",
                    band=band,
                    command=assoc_command,
                    output=assoc_stdout,
                )
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

    def _prepare_case_band(self, case: dict[str, Any], topology: Any, band: str) -> bool:
        normalized_band = self._normalize_band_name(band)
        if not normalized_band:
            return True
        scoped_case = self._case_for_bands(case, (normalized_band,))
        if not self._ensure_sta_band_ready(scoped_case, topology):
            return False
        case["_active_step_band"] = normalized_band
        return True

    def _read_sta_available_bands(self, topology: Any) -> None:
        """Read sta_available_bands from testbed.variables and cache in self._sta_available_bands."""
        raw = getattr(topology, "raw", {})
        if not isinstance(raw, dict):
            return
        variables = raw.get("testbed", {}).get("variables", {})
        if not isinstance(variables, dict):
            return
        raw_val = variables.get("sta_available_bands")
        if isinstance(raw_val, list):
            parsed = tuple(str(b).strip().lower() for b in raw_val if str(b).strip())
            if parsed:
                self._sta_available_bands = parsed
        elif isinstance(raw_val, str) and raw_val.strip():
            parsed = tuple(b.strip().lower() for b in raw_val.split(",") if b.strip())
            if parsed:
                self._sta_available_bands = parsed

    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        """佈建 WiFi 測試環境。"""
        if self._transports:
            self.teardown(case, topology)
        self._sta_env_verified = False
        case.pop("_active_step_band", None)
        self._read_sta_available_bands(topology)
        case.pop("_last_failure", None)
        if not self._open_case_transports(case, topology, run_case_setup=True):
            return False
        self._sta_env_verified = True
        return True

    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        """驗證 WiFi 連線就緒。"""
        case_id = str(case.get("id", ""))
        dut = self._transports.get("DUT")
        if dut is None:
            self._record_runtime_failure(
                case,
                phase="verify_env",
                comment="missing DUT transport",
                category="environment",
                reason_code="missing_dut_transport",
                device="DUT",
            )
            log.warning("[%s] verify_env: %s missing DUT transport", self.name, case_id)
            return False

        # Suppress kernel console messages on DUT to prevent UART flood
        # (Broadcom dhd driver generates continuous messages that break prompt detection).
        self._execute_env_command(dut, "dmesg -n 1", timeout=5.0)

        gate_result = self._execute_env_command(dut, 'echo "__testpilot_env_gate__"', timeout=10.0)
        if int(gate_result.get("returncode", 1)) != 0:
            self._record_runtime_failure(
                case,
                phase="verify_env",
                comment="DUT gate failed",
                category="environment",
                reason_code="dut_gate_failed",
                device="DUT",
                command='echo "__testpilot_env_gate__"',
                output=self._env_output_text(gate_result),
            )
            log.warning("[%s] verify_env: %s DUT gate failed", self.name, case_id)
            return False

        # Run default band baseline only when the case does NOT provide its
        # own sta_env_setup AND explicitly references WiFi AP/radio bands.
        sta = self._transports.get("STA")
        if self._should_auto_prepare_wifi_bands(case) and sta is not None:
            # Suppress kernel console messages on STA too.
            self._execute_env_command(sta, "dmesg -n 1", timeout=5.0)
            selected_bands = self._selected_sta_bands(case)
            initial_band = selected_bands[0] if selected_bands else ""
            if not self._prepare_case_band(case, topology, initial_band):
                selected_bands = self._selected_sta_bands(case)
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment="STA band baseline/connect failed",
                    category="environment",
                    reason_code="sta_band_not_ready",
                    device="STA",
                    band=selected_bands[0] if len(selected_bands) == 1 else "",
                    metadata={"bands": list(selected_bands)},
                )
                log.warning("[%s] verify_env: %s STA band baseline/connect failed", self.name, case_id)
                return False

            # Cold-boot multi-band cases are the most likely to expose first-switch
            # drift, so pre-warm the remaining bands once without making them hard
            # verify_env blockers. execute_step() still re-prepares bands on demand.
            for warmup_band in selected_bands[1:]:
                if self._normalize_band_name(warmup_band) == self._normalize_band_name(initial_band):
                    continue
                if not self._prepare_case_band(case, topology, warmup_band):
                    log.info(
                        "[%s] verify_env: %s warm-up band %s deferred to execute_step",
                        self.name,
                        case_id,
                        warmup_band,
                    )

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
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment=f"ping expected pass but failed ({src_name} -> {dst_name})",
                    category="environment",
                    reason_code="ping_gate_failed",
                    device=src_name,
                    command=command,
                    output=str(ping_result.get("stdout", "") or ping_result.get("stderr", "")),
                )
                log.warning("[%s] verify_env: ping expected pass but failed (%s -> %s)", self.name, src_name, dst_name)
                return False
            if expect in {"fail", "false", "0"} and passed:
                self._record_runtime_failure(
                    case,
                    phase="verify_env",
                    comment=f"ping expected fail but passed ({src_name} -> {dst_name})",
                    category="environment",
                    reason_code="ping_gate_unexpected_pass",
                    device=src_name,
                    command=command,
                    output=str(ping_result.get("stdout", "") or ping_result.get("stderr", "")),
                )
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
        skip_echo = f'[skip] non-executable step {step_id}'

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

        if action == "skip":
            return {
                "success": True,
                "output": skip_echo,
                "captured": {},
                "timing": 0.0,
                "command": f'echo "{skip_echo}"',
                "fallback_reason": "fallback_skip_echo",
                "returncode": 0,
            }

        transport = self._transports.get(target_name) or self._transports.get("DUT")
        if transport is None:
            self._record_runtime_failure(
                case,
                phase="execute_step",
                comment=f"transport not found for target={target_name}",
                category="environment",
                reason_code="missing_step_transport",
                device=target_name,
            )
            return {
                "success": False,
                "output": f"transport not found for target={target_name}",
                "captured": {},
                "timing": 0.0,
            }

        if self._should_auto_prepare_wifi_bands(case):
            selected_bands = self._selected_sta_bands(case)
            step_band = self._normalize_band_name(step.get("band"))
            if not step_band:
                step_band = self._band_from_text(stringify_step_command(step.get("command")))
            active_band = self._normalize_band_name(case.get("_active_step_band"))
            if len(selected_bands) > 1 and step_band and step_band != active_band:
                if not self._prepare_case_band(case, topology, step_band):
                    self._record_runtime_failure(
                        case,
                        phase="execute_step",
                        comment=f"failed to prepare band {step_band} before {step_id}",
                        category="environment",
                        reason_code="sta_band_not_ready",
                        device="STA",
                        band=step_band,
                        metadata={"step_id": step_id},
                    )
                    return {
                        "success": False,
                        "output": f"failed to prepare band {step_band} before {step_id}",
                        "captured": {},
                        "timing": 0.0,
                        "returncode": 1,
                    }

        commands_to_run, fallback_reason = self._command_resolver.resolve(case, step, topology)
        expanded_commands: list[str] = []
        for command_to_run in commands_to_run:
            expanded_commands.extend(self._split_step_command_sequence(command_to_run))
        commands_to_run = expanded_commands or commands_to_run
        commands_to_run = [
            self._wrap_multiline_shell_command(command_to_run)
            for command_to_run in commands_to_run
        ]

        outputs: list[str] = []
        captured: dict[str, Any] = {}
        total_elapsed = 0.0
        success = True
        final_returncode = 0
        capture_name = str(step.get("capture", "")).strip()

        index = 0
        while index < len(commands_to_run):
            command_to_run = commands_to_run[index]
            if self._has_unresolved_placeholder(command_to_run):
                self._record_runtime_failure(
                    case,
                    phase="execute_step",
                    comment=f"unresolved runtime placeholder: {command_to_run}",
                    category="configuration",
                    reason_code="unresolved_runtime_placeholder",
                    device=target_name,
                    band=self._band_from_text(command_to_run),
                    command=command_to_run,
                )
                return {
                    "success": False,
                    "output": f"unresolved runtime placeholder: {command_to_run}",
                    "captured": {},
                    "timing": total_elapsed,
                    "returncode": 1,
                    "command": "\n".join(commands_to_run).strip(),
                    "fallback_reason": fallback_reason,
                }
            try:
                result = transport.execute(command_to_run, timeout=timeout)
            except Exception as exc:
                self._record_runtime_failure(
                    case,
                    phase="execute_step",
                    comment=str(exc),
                    category="environment",
                    reason_code="step_transport_exception",
                    device=target_name,
                    band=self._band_from_text(command_to_run),
                    command=command_to_run,
                )
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

            result_map = self._command_resolver.as_mapping(result)
            if index == 0 and len(commands_to_run) == 1:
                retry = self._command_resolver.handle_runtime_fallback(
                    case, step, topology, result_map, commands_to_run, fallback_reason
                )
                if retry is not None:
                    commands_to_run, fallback_reason = retry
                    expanded_commands = []
                    for fallback_command in commands_to_run:
                        expanded_commands.extend(self._split_step_command_sequence(fallback_command))
                    commands_to_run = expanded_commands or commands_to_run
                    commands_to_run = [
                        self._wrap_multiline_shell_command(fallback_command)
                        for fallback_command in commands_to_run
                    ]
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
            command_success = self._env_command_succeeded(command_to_run, result_map)
            success = success and command_success
            if not command_success:
                band = self._band_from_text(command_to_run)
                reason_code = (
                    "sta_band_connect_failed"
                    if target_name.upper() == "STA" and self._is_explicit_sta_connect_step(command_to_run)
                    else "step_command_failed"
                )
                category = "environment" if reason_code == "sta_band_connect_failed" else "test"
                self._record_runtime_failure(
                    case,
                    phase="execute_step",
                    comment=f"{step_id} command failed",
                    category=category,
                    reason_code=reason_code,
                    device=target_name,
                    band=band,
                    command=command_to_run,
                    output=output,
                    metadata={"step_id": step_id},
                )
                if final_returncode == 0:
                    final_returncode = 1
                break
            index += 1

        expected_capture_field = self._field_name_from_capture(case, capture_name)
        if success and capture_name and expected_capture_field and expected_capture_field not in captured:
            capture_fallback = self._capture_assoc_mac_fallback(
                case=case,
                step=step,
                target_name=target_name,
                transport=transport,
                timeout=timeout,
            )
            if capture_fallback is not None:
                fallback_captured, fallback_output, fallback_command = capture_fallback
                captured.update(fallback_captured)
                if fallback_output:
                    outputs.append(fallback_output)
                fallback_reason = (
                    f"{fallback_reason}+capture_assoc_mac_query"
                    if fallback_reason
                    else "capture_assoc_mac_query"
                )
                log.info(
                    "[%s] execute_step: %s.%s fallback capture via %s",
                    self.name,
                    case.get("id"),
                    step_id,
                    self._preview_value(fallback_command, limit=96),
                )

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
            capture_raw = self._as_mapping(context.get("_capture_raw"))
            if field and "." not in field and isinstance(actual, dict):
                raw_output = capture_raw.get(field)
                if isinstance(raw_output, str) and raw_output:
                    actual = raw_output
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
                self._record_runtime_failure(
                    case,
                    phase="evaluate",
                    comment="pass_criteria not satisfied",
                    category="test",
                    reason_code="pass_criteria_not_satisfied",
                    output=self._preview_value(actual),
                    metadata={
                        "field": field,
                        "operator": operator,
                        "expected": self._preview_value(expected),
                        "actual": self._preview_value(actual),
                    },
                )
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

    def _remediation_bands(self, case: dict[str, Any], snapshot: dict[str, Any]) -> tuple[str, ...]:
        if (band := self._normalize_band_name(snapshot.get("band"))):
            return (band,)
        metadata = snapshot.get("metadata")
        if isinstance(metadata, dict):
            bands = metadata.get("bands")
            if isinstance(bands, list):
                normalized = [
                    band_name
                    for item in bands
                    if (band_name := self._normalize_band_name(item))
                ]
                if normalized:
                    return tuple(normalized)
        return self._selected_sta_bands(case)

    def _serial_recovery_selector(self, device_name: str, topology: Any) -> tuple[str, str | None]:
        cfg = self._topology_device_config(topology, device_name)
        transport_type = str(cfg.get("transport", "")).strip().lower()
        if transport_type not in {"serial", "serialwrap"}:
            return transport_type, None
        for key in ("selector", "alias", "session_id", "serial_port"):
            value = str(cfg.get(key, "") or "").strip()
            if value:
                return transport_type, value
        return transport_type, None

    def _recover_serial_session(self, device_name: str, topology: Any) -> dict[str, Any]:
        transport_type, selector = self._serial_recovery_selector(device_name, topology)
        if transport_type not in {"serial", "serialwrap"}:
            return {
                "success": False,
                "comment": f"{device_name} transport is not serial",
            }
        if not selector:
            return {
                "success": False,
                "comment": f"{device_name} selector not configured",
            }

        raw_topology = getattr(topology, "raw", {})
        configured_bin = ""
        if isinstance(raw_topology, dict):
            testbed = raw_topology.get("testbed", {})
            if isinstance(testbed, dict):
                configured_bin = str(testbed.get("serialwrap_binary", "") or "")

        binary = resolve_serialwrap_binary(
            configured_bin or None,
            config_label="testbed.serialwrap_binary",
        )
        commands = (
            [binary, "session", "recover", "--selector", selector],
            [binary, "session", "attach", "--selector", selector],
        )
        stderr_chunks: list[str] = []
        for args in commands:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=15.0,
            )
            if completed.returncode != 0:
                stderr_chunks.append((completed.stderr or "").strip() or (completed.stdout or "").strip())
                return {
                    "success": False,
                    "comment": "; ".join(chunk for chunk in stderr_chunks if chunk),
                }
        return {
            "success": True,
            "comment": f"{device_name} serial session recovered",
        }

    def build_remediation_decision(
        self,
        case: dict[str, Any],
        failure_snapshot: Any,
        topology: Any,
        *,
        runner: dict[str, Any] | None = None,
        remediation_policy: dict[str, Any] | None = None,
    ) -> Any:
        del runner, remediation_policy
        snapshot = self._snapshot_mapping(failure_snapshot)
        category = str(snapshot.get("category", "")).strip().lower()
        if category not in {"environment", "session"}:
            return None

        reason = str(snapshot.get("reason_code", "")).strip().lower()
        case_id = str(case.get("id", "") or snapshot.get("case_id", ""))
        attempt_index = int(snapshot.get("attempt_index", case.get("_attempt_index", 1)))
        bands = self._remediation_bands(case, snapshot)
        primary_band = bands[0] if len(bands) == 1 else ""
        actions: list[dict[str, Any]] = []
        summary = str(snapshot.get("comment", "environment remediation requested") or "environment remediation requested")

        device = str(snapshot.get("device", "")).strip()
        _, selector = self._serial_recovery_selector(device or "DUT", topology)
        if reason in {"serial_session_not_ready", "transport_connect_failed"} and selector:
            actions.extend(
                [
                    {
                        "executor_key": "serial_session_recover",
                        "description": f"recover serial session for {device or 'DUT'}",
                        "device": device or "DUT",
                    },
                    {
                        "executor_key": "case_env_reverify",
                        "description": "rerun environment verification after session recovery",
                    },
                ]
            )
        elif reason in {"sta_band_connect_failed"}:
            actions.extend(
                [
                    {
                        "executor_key": "sta_band_reconnect",
                        "description": "reconnect STA band and re-check link",
                        "band": primary_band,
                        "params": {"bands": list(bands)},
                    },
                    {
                        "executor_key": "case_env_reverify",
                        "description": "rerun environment verification after reconnect",
                    },
                ]
            )
        elif reason in {
            "sta_band_not_ready",
            "sta_band_link_failed",
            "dut_assoc_check_failed",
            "ping_gate_failed",
            "ping_gate_unexpected_pass",
        }:
            actions.extend(
                [
                    {
                        "executor_key": "sta_band_rebaseline",
                        "description": "rebuild STA band baseline and reconnect",
                        "band": primary_band,
                        "params": {"bands": list(bands)},
                    },
                    {
                        "executor_key": "dut_band_rebaseline",
                        "description": "re-apply DUT band baseline",
                        "band": primary_band,
                        "params": {"bands": list(bands)},
                    },
                    {
                        "executor_key": "case_env_reverify",
                        "description": "rerun environment verification after baseline repair",
                    },
                ]
            )
        elif reason in {"dut_gate_failed"}:
            actions.append(
                {
                    "executor_key": "case_env_reverify",
                    "description": "rerun environment verification",
                }
            )
        else:
            return None

        return {
            "case_id": case_id,
            "attempt_index": attempt_index,
            "summary": summary,
            "source": "builtin-fallback",
            "approved": True,
            "actions": actions,
        }

    def execute_remediation(
        self,
        case: dict[str, Any],
        decision: Any,
        topology: Any,
    ) -> dict[str, Any]:
        decision_map = self._snapshot_mapping(decision)
        raw_actions = decision_map.get("actions")
        actions = raw_actions if isinstance(raw_actions, list) else []
        if not actions:
            return {
                "success": False,
                "verify_after": None,
                "comment": "no remediation actions",
                "actions": [],
            }

        executed_actions: list[dict[str, Any]] = []
        verify_after: bool | None = None
        opened_transports = False
        all_success = True
        comment_parts: list[str] = []
        custom_env_setup = self._has_custom_env_setup(case)
        custom_env_reapplied = False

        try:
            for raw_action in actions:
                action = self._snapshot_mapping(raw_action)
                executor_key = str(action.get("executor_key", "")).strip()
                if executor_key == "serial_session_recover":
                    result = self._recover_serial_session(
                        str(action.get("device", "") or "DUT"),
                        topology,
                    )
                    executed_actions.append({
                        "executor_key": executor_key,
                        "device": str(action.get("device", "") or "DUT"),
                        "success": bool(result.get("success", False)),
                        "comment": str(result.get("comment", "") or ""),
                    })
                    all_success = all_success and bool(result.get("success", False))
                    if result.get("comment"):
                        comment_parts.append(str(result["comment"]))
                    if not result.get("success", False):
                        break
                    continue

                if not opened_transports:
                    opened_transports = self._open_case_transports(case, topology, run_case_setup=False)
                    if not opened_transports:
                        return {
                            "success": False,
                            "verify_after": None,
                            "comment": "failed to open transports for remediation",
                            "actions": executed_actions,
                        }

                params = action.get("params")
                bands_value = params.get("bands") if isinstance(params, dict) else None
                if isinstance(bands_value, (list, tuple, set)):
                    bands_raw = bands_value
                elif bands_value in (None, ""):
                    bands_raw = ()
                else:
                    bands_raw = (bands_value,)
                bands = tuple(
                    band
                    for item in bands_raw
                    if (band := self._normalize_band_name(item))
                )
                if not bands:
                    band = self._normalize_band_name(action.get("band"))
                    bands = (band,) if band else self._selected_sta_bands(case)
                scoped_case = self._case_for_bands(case, bands)

                success = False
                if executor_key == "sta_band_reconnect":
                    success = bool(self._run_sta_band_connect_sequence(scoped_case))
                    if success:
                        success = bool(self._verify_sta_band_connectivity(scoped_case))
                elif executor_key == "sta_band_rebaseline":
                    if custom_env_setup:
                        success = bool(self._run_sta_env_setup(case, topology))
                        custom_env_reapplied = custom_env_reapplied or success
                    else:
                        success = bool(self._ensure_sta_band_ready(scoped_case, topology))
                elif executor_key == "dut_band_rebaseline":
                    if custom_env_setup:
                        success = True if custom_env_reapplied else bool(self._run_sta_env_setup(case, topology))
                        custom_env_reapplied = custom_env_reapplied or success
                    else:
                        success = bool(self._run_sta_band_baseline(scoped_case))
                elif executor_key == "case_env_reverify":
                    success = bool(self.verify_env(case, topology))
                    verify_after = success

                executed_actions.append({
                    "executor_key": executor_key,
                    "band": bands[0] if len(bands) == 1 else "",
                    "params": {"bands": list(bands)},
                    "success": success,
                    "comment": "ok" if success else "failed",
                })
                all_success = all_success and success
                if not success:
                    comment_parts.append(f"{executor_key} failed")
                    break
        finally:
            if opened_transports:
                self.teardown(case, topology)

        if all_success and not comment_parts:
            comment_parts.append("remediation applied")
        return {
            "success": all_success,
            "verify_after": verify_after,
            "comment": "; ".join(comment_parts),
            "actions": executed_actions,
        }

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

    def qualify_baseline(
        self,
        topology: Any,
        *,
        bands: tuple[str, ...] = (),
        repeat_count: int = 5,
        soak_minutes: int = 15,
    ) -> dict[str, Any]:
        """Qualify reusable DUT/STA baseline connectivity for selected bands."""
        qualifier = BaselineQualifier(self, topology)
        return qualifier.run(
            bands=bands,
            repeat_count=repeat_count,
            soak_minutes=soak_minutes,
        )
