"""Runtime behavior tests for wifi_llapi plugin execution/evaluation."""

from __future__ import annotations

from pathlib import Path
import sys
import types
from typing import Any

from testpilot.core.plugin_loader import PluginLoader


class _FakeTopology:
    def __init__(self) -> None:
        self._devices = {
            "DUT": {
                "transport": "serial",
                "serial_port": "/dev/ttyUSB0",
                "host": "192.168.10.1",
            },
            "STA": {
                "transport": "adb",
                "adb_serial": "ABCDEF123",
                "host": "192.168.10.2",
            },
        }
        self.variables = {
            "DUT_IP": "192.168.10.1",
            "TEST_VAR": "WiFi.Radio.1.?",
        }

    def get_device(self, role: str) -> dict[str, Any]:
        return dict(self._devices[role])

    def resolve(self, text: str) -> str:
        result = text
        for key, value in self.variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


class _FakeTransport:
    def __init__(self, transport_type: str, config: dict[str, Any]) -> None:
        self.transport_type = transport_type
        self.config = dict(config)
        self._connected = False
        self.connect_kwargs: dict[str, Any] = {}
        self.executed_commands: list[str] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, **kwargs: Any) -> None:
        self._connected = True
        self.connect_kwargs = dict(kwargs)

    def disconnect(self) -> None:
        self._connected = False

    def execute(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
        del timeout
        self.executed_commands.append(command)
        if command.startswith("echo \"__testpilot_env_gate__\""):
            return {
                "returncode": 0,
                "stdout": "__testpilot_env_gate__",
                "stderr": "",
                "elapsed": 0.01,
            }
        return {
            "returncode": 0,
            "stdout": f"OK:{command}",
            "stderr": "",
            "elapsed": 0.02,
        }


class _FactoryRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.transports: list[_FakeTransport] = []

    def create_transport(self, transport_type: str, config: dict[str, Any]) -> _FakeTransport:
        self.calls.append((transport_type, dict(config)))
        transport = _FakeTransport(transport_type, config)
        self.transports.append(transport)
        return transport


def _load_plugin() -> Any:
    root = Path(__file__).resolve().parents[1]
    loader = PluginLoader(root / "plugins")
    return loader.load("wifi_llapi")


def _install_fake_factory(monkeypatch, recorder: _FactoryRecorder) -> None:
    module = types.ModuleType("testpilot.transport.factory")
    module.create_transport = recorder.create_transport
    monkeypatch.setitem(sys.modules, "testpilot.transport.factory", module)


def test_execute_step_command_fallback_priority(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-fallback",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "hlapi_command": "ubus-cli {{TEST_VAR}}",
        "verification_command": "iw dev",
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [
            {"id": "s1", "capture": "result"},
            {"id": "s2"},
            {"id": "s3"},
            {"id": "s4"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert len(recorder.calls) == 2
    assert {call[0] for call in recorder.calls} == {"serial", "adb"}

    # 1) 優先從自然語言中抽取 ubus-cli/wl/iw 等命令片段
    result_1 = plugin.execute_step(
        case,
        {
            "id": "s1",
            "action": "exec",
            "target": "DUT",
            "command": "請執行以下動作：ubus-cli {{TEST_VAR}} | grep Radio",
        },
        topology=topology,
    )
    assert result_1["success"] is True
    assert result_1["command"].startswith("ubus-cli WiFi.Radio.1.?")
    assert result_1["fallback_reason"] == "extract_from_step_text"

    # 2) 無可執行片段時，fallback 到 hlapi_command
    result_2 = plugin.execute_step(
        case,
        {
            "id": "s2",
            "action": "exec",
            "target": "DUT",
            "command": "請確認 DUT 狀態",
        },
        topology=topology,
    )
    assert result_2["success"] is True
    assert result_2["command"] == "ubus-cli WiFi.Radio.1.?"
    assert result_2["fallback_reason"] == "fallback_hlapi_command"

    # 3) 無 hlapi_command 時 fallback 到 verification_command
    case_no_hlapi = dict(case)
    case_no_hlapi["hlapi_command"] = ""
    result_3 = plugin.execute_step(
        case_no_hlapi,
        {
            "id": "s3",
            "action": "exec",
            "target": "DUT",
            "command": "這是一段不可執行說明文字",
        },
        topology=topology,
    )
    assert result_3["success"] is True
    assert result_3["command"] == "iw dev"
    assert result_3["fallback_reason"] == "fallback_verification_command"

    # 4) 最後 fallback 到可重現 skip echo
    case_skip = dict(case_no_hlapi)
    case_skip["verification_command"] = ""
    result_4 = plugin.execute_step(
        case_skip,
        {
            "id": "s4",
            "action": "exec",
            "target": "DUT",
            "command": "純自然語言，沒有任何可執行指令",
        },
        topology=topology,
    )
    assert result_4["success"] is True
    assert "[skip] non-executable step s4" in result_4["command"]
    assert result_4["fallback_reason"] == "fallback_skip_echo"

    plugin.teardown(case, topology=topology)


def test_evaluate_pass_criteria_basic_operators_and_field_fallback(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-evaluate",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result"}, {"id": "s2"}],
        "pass_criteria": [
            {"field": "result.Mode", "operator": "contains", "value": "A"},
            {"field": "result.Mode", "operator": "equals", "value": "AP"},
            {"field": "result", "operator": "regex", "value": r"Channel=36"},
            {"field": "missing.field", "operator": "not_contains", "value": "FATAL"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True

    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": "Mode=AP\\nChannel=36",
                "captured": {"Mode": "AP", "Channel": "36"},
                "timing": 0.01,
            },
            "s2": {
                "success": True,
                "output": "health=OK",
                "captured": {},
                "timing": 0.01,
            },
        }
    }

    assert plugin.evaluate(case, results) is True

    fail_case = dict(case)
    fail_case["pass_criteria"] = [
        {"field": "result.Mode", "operator": "equals", "value": "STA"}
    ]
    assert plugin.evaluate(fail_case, results) is False

    plugin.teardown(case, topology=topology)
