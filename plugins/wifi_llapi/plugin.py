"""wifi_llapi plugin — Wifi LLAPI test automation for prplOS/Broadcom."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
import re
import time
from typing import Any

from testpilot.core.plugin_base import PluginBase
from testpilot.schema.case_schema import load_cases_dir
from testpilot.transport.base import StubTransport

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

    def __init__(self) -> None:
        self._transports: dict[str, Any] = {}
        self._device_specs: dict[str, dict[str, Any]] = {}

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
        if not text:
            return None
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for token in self.CLI_FALLBACK_TOKENS:
            pattern = re.compile(rf"\b{re.escape(token)}\b")
            for line in lines:
                match = pattern.search(line)
                if not match:
                    continue
                fragment = line[match.start():].strip().strip("`'\"")
                fragment = fragment.rstrip("，。;")
                if fragment:
                    return fragment
        return None

    def _looks_executable(self, command: str) -> bool:
        stripped = command.strip()
        if not stripped:
            return False
        if any(symbol in stripped for symbol in ("|", ";", "&&", "||", "$(", "`")):
            return True
        first = stripped.split(maxsplit=1)[0].strip("`'\"")
        if first in self.CLI_FALLBACK_TOKENS:
            return True
        return bool(re.fullmatch(r"[A-Za-z0-9_./:-]+", first))

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

    def _select_fallback_command(
        self,
        case: dict[str, Any],
        original_command: str,
        topology: Any,
        step_id: str,
    ) -> tuple[str, str]:
        fragment = self._extract_cli_fragment(original_command)
        if fragment:
            return self._resolve_text(topology, fragment), "extract_from_step_text"

        for field in ("hlapi_command", "verification_command"):
            raw = str(case.get(field, "")).strip()
            if not raw:
                continue
            fallback = self._extract_cli_fragment(raw) or self._first_non_empty_line(raw)
            if fallback:
                return self._resolve_text(topology, fallback), f"fallback_{field}"

        return f'echo "[skip] non-executable step {step_id}"', "fallback_skip_echo"

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
        except Exception:
            pass

        pattern = re.compile(r"([A-Za-z0-9_.()/-]+)\s*[:=]\s*\"?([^\"\n,]+)\"?")
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            for key, value in pattern.findall(line):
                captured[key] = value.strip()

        return captured

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
            output = str(item.get("output", ""))
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

        if op in {"contains"}:
            return expected_text in actual_text
        if op in {"not_contains"}:
            return expected_text not in actual_text
        if op in {"equals", "==", "eq"}:
            return actual_text == expected_text
        if op in {"!=", "not_equals", "ne"}:
            return actual_text != expected_text
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

    def setup_env(self, case: dict[str, Any], topology: Any) -> bool:
        """佈建 WiFi 測試環境。"""
        case_id = str(case.get("id", ""))
        if self._transports:
            self.teardown(case, topology)

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
        return all_connected and bool(self._transports)

    def verify_env(self, case: dict[str, Any], topology: Any) -> bool:
        """驗證 WiFi 連線就緒。"""
        case_id = str(case.get("id", ""))
        dut = self._transports.get("DUT")
        if dut is None:
            log.warning("[%s] verify_env: %s missing DUT transport", self.name, case_id)
            return False

        gate_result = dut.execute('echo "__testpilot_env_gate__"', timeout=10.0)
        if int(gate_result.get("returncode", 1)) != 0:
            log.warning("[%s] verify_env: %s DUT gate failed", self.name, case_id)
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
        resolved_command = self._resolve_text(topology, raw_command)
        command_to_run = resolved_command
        fallback_reason = ""

        # 若 step 文字中夾帶可執行片段（例如自然語言描述 + ubus-cli），優先抽取可執行部分。
        extracted = self._extract_cli_fragment(command_to_run)
        if extracted and extracted != command_to_run:
            command_to_run = extracted
            fallback_reason = "extract_from_step_text"

        if not command_to_run or not self._looks_executable(command_to_run):
            command_to_run, fallback_reason = self._select_fallback_command(
                case, raw_command, topology, step_id
            )

        try:
            result = transport.execute(command_to_run, timeout=timeout)
        except Exception as exc:
            log.warning("[%s] execute_step failed: %s.%s err=%s", self.name, case.get("id"), step_id, exc)
            return {
                "success": False,
                "output": str(exc),
                "captured": {},
                "timing": 0.0,
                "command": command_to_run,
                "fallback_reason": fallback_reason,
            }

        if not fallback_reason and self._is_unexecutable_result(self._as_mapping(result)):
            fallback_command, reason = self._select_fallback_command(case, raw_command, topology, step_id)
            if fallback_command != command_to_run:
                command_to_run = fallback_command
                fallback_reason = reason
                result = transport.execute(command_to_run, timeout=timeout)

        result_map = self._as_mapping(result)
        stdout = str(result_map.get("stdout", ""))
        stderr = str(result_map.get("stderr", ""))
        output = "\n".join(chunk for chunk in (stdout, stderr) if chunk).strip()
        captured = self._extract_key_values(output)
        elapsed = self._to_float(result_map.get("elapsed"), 0.0)
        returncode = int(result_map.get("returncode", 1))

        return {
            "success": returncode == 0,
            "output": output,
            "captured": captured,
            "timing": elapsed,
            "returncode": returncode,
            "command": command_to_run,
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
            if actual is None:
                log.warning("[%s] evaluate: field not found (%s), fallback aggregate output", self.name, field)
                actual = aggregate_output

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
        log.info("[%s] teardown: %s done", self.name, case_id)
