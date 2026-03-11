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
        if command.startswith("iw dev wl") and " link" in command:
            if self.config.get("simulate_sta_link_fail") and "wl1" in command:
                return {
                    "returncode": 1,
                    "stdout": "Not connected.",
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": "Connected to 2c:59:17:00:19:95",
                "stderr": "",
                "elapsed": 0.01,
            }
        if command.startswith("wl -i wl") and "assoclist" in command:
            if self.config.get("simulate_assoclist_empty") and "wl1" in command:
                return {
                    "returncode": 0,
                    "stdout": "assoclist ",
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": "assoclist 84:0d:8e:aa:bb:cc",
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
    assert result_1["command"].startswith("ubus-cli")
    assert "WiFi.Radio.1.?" in result_1["command"]
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
    assert result_2["command"].startswith("ubus-cli")
    assert "WiFi.Radio.1.?" in result_2["command"]
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


def test_verify_env_sta_band_gate_pass(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-sta-band-pass",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        STA env setup baseline:
          iw dev wl0 set type managed
        DUT association evidence:
          wl -i wl0 assoclist
        """,
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": "echo ok"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert plugin.verify_env(case, topology=topology) is True
    plugin.teardown(case, topology=topology)


def test_verify_env_sta_band_gate_fail_on_link(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-sta-band-fail",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb", "simulate_sta_link_fail": True},
            }
        },
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": "echo ok"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert plugin.verify_env(case, topology=topology) is False
    plugin.teardown(case, topology=topology)


def test_evaluate_missing_field_does_not_use_transcript_noise(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-missing-field-noise",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result"}],
        "pass_criteria": [
            {"field": "result.SHA256Enable", "operator": "contains", "value": "0"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": "__TP_RC_123abc__=1\nroot@prplOS:/#\n>\n",
                "captured": {},
                "timing": 0.01,
            }
        }
    }

    # Missing field fallback should not be satisfied by random transcript noise.
    assert plugin.evaluate(case, results) is False
    plugin.teardown(case, topology=topology)


def test_evaluate_ignores_serialwrap_rc_noise_in_captured_field(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-rc-noise",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result"}],
        "pass_criteria": [
            {"field": "result.RekeyingInterval", "operator": "contains", "value": "0"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True

    # Two outputs differ only by random __TP_RC marker content.
    # Both must be evaluated consistently and should not pass via random digits.
    noisy_outputs = [
        "\\n'; ubus-cli 'WiFi.AccessPoint.{i}.Security.\\r\\r\\nRekeyingInterval=' Get Command:; __tp_rc=$?; printf '__TP_RC_6c0a68115164__=%s\\n",
        "\\n'; ubus-cli 'WiFi.AccessPoint.{i}.Security.\\r\\r\\nRekeyingInterval=' Get Command:; __tp_rc=$?; printf '__TP_RC_cf2ad4efe36d__=%s\\n",
    ]

    for text in noisy_outputs:
        results = {
            "steps": {
                "s1": {
                    "success": True,
                    "output": text,
                    "captured": plugin._extract_key_values(text),
                    "timing": 0.01,
                }
            }
        }
        assert plugin.evaluate(case, results) is False

    plugin.teardown(case, topology=topology)


def test_extract_key_values_preserves_prompted_comma_separated_value():
    plugin = _load_plugin()
    parsed = plugin._extract_key_values(
        '> WiFi.AccessPoint.1.WPS.ConfigMethodsEnabled="PhysicalPushButton,VirtualPushButton"\n'
    )
    assert (
        parsed["WiFi.AccessPoint.1.WPS.ConfigMethodsEnabled"]
        == "PhysicalPushButton,VirtualPushButton"
    )


def test_execute_step_capture_prefers_synthesized_readback_query(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-synth-readback",
        "source": {
            "object": "WiFi.AccessPoint.{i}.AssociatedDevice.{i}.",
            "api": "Capabilities",
        },
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [
            {
                "id": "step2",
                "action": "exec",
                "target": "DUT",
                "capture": "result",
                "command": (
                    "Verify Associated station Capabilities "
                    'ubus-cli WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities="RRM,BTM,QOS_MAP,PMF" '
                    'ubus-cli WiFi.AccessPoint.3.AssociatedDevice.1.Capabilities="RRM,BTM,QOS_MAP,PMF"'
                ),
            }
        ],
        "pass_criteria": [
            {"field": "result.Capabilities", "operator": "contains", "value": "RRM,BTM,QOS_MAP"}
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    dut = plugin._transports["DUT"]

    def fake_execute(command: str, timeout: float = 30.0) -> dict[str, Any]:
        del timeout
        dut.executed_commands.append(command)
        if command == 'ubus-cli "WiFi.AccessPoint.*.AssociatedDevice.*.Capabilities?"':
            return {
                "returncode": 0,
                "stdout": 'WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities="RRM,BTM,QOS_MAP,PMF"',
                "stderr": "",
                "elapsed": 0.01,
            }
        return {"returncode": 1, "stdout": "", "stderr": "unexpected", "elapsed": 0.01}

    monkeypatch.setattr(dut, "execute", fake_execute)
    result = plugin.execute_step(case, case["steps"][0], topology=topology)

    assert result["success"] is True
    assert result["fallback_reason"] == "synthesized_capture_query"
    assert result["command"] == 'ubus-cli "WiFi.AccessPoint.*.AssociatedDevice.*.Capabilities?"'
    assert result["captured"]["WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities"] == "RRM,BTM,QOS_MAP,PMF"
    plugin.teardown(case, topology=topology)


def test_execute_step_runs_multi_command_sequence(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-multi-command",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [
            {
                "id": "step1",
                "action": "exec",
                "target": "DUT",
                "command": (
                    "Set all radios to 50 percent: "
                    "ubus-cli WiFi.Radio.1.TransmitPower=50; "
                    "ubus-cli WiFi.Radio.2.TransmitPower=50; "
                    "ubus-cli WiFi.Radio.3.TransmitPower=50"
                ),
            }
        ],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    result = plugin.execute_step(case, case["steps"][0], topology=topology)
    dut = plugin._transports["DUT"]

    assert result["success"] is True
    assert result["fallback_reason"] == "extract_from_step_text"
    assert dut.executed_commands[-3:] == [
        "ubus-cli WiFi.Radio.1.TransmitPower=50",
        "ubus-cli WiFi.Radio.2.TransmitPower=50",
        "ubus-cli WiFi.Radio.3.TransmitPower=50",
    ]
    assert result["command"] == "\n".join(dut.executed_commands[-3:])
    plugin.teardown(case, topology=topology)


def test_evaluate_normalizes_quote_only_mismatch(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-quote-normalize",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result"}],
        "pass_criteria": [
            {"field": "result.SSID", "operator": "contains", "value": '"prplOS"'},
            {"field": "result.NASIdentifier", "operator": "equals", "value": '"ABC123"'},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.SSID="prplOS"\nWiFi.AccessPoint.1.NASIdentifier="ABC123"',
                "captured": {
                    "SSID": "prplOS",
                    "NASIdentifier": "ABC123",
                },
                "timing": 0.01,
            }
        }
    }
    assert plugin.evaluate(case, results) is True
    plugin.teardown(case, topology=topology)


def test_sta_env_setup_parser_preserves_wpa_cli_quoted_value():
    plugin = _load_plugin()
    parsed = plugin._iter_env_script_commands(
        """
        STA section:
          wpa_cli -i wl1 set_network 0 sae_password '"B0StaTest1234"'
        """
    )
    assert parsed == [("STA", "wpa_cli -i wl1 set_network 0 sae_password '\"B0StaTest1234\"'")]


def test_run_sta_band_connect_sequence_keeps_6g_ctrl_alive(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["STA"] = object()
    commands: list[tuple[str, str]] = []
    connect_calls: list[tuple[str, str, str]] = []

    def fake_run_required_command(*, transport, case_id, label, command, timeout=30.0):
        del transport, case_id, timeout
        commands.append((label, command))
        return True

    def fake_connect_with_retry(
        *,
        transport,
        case_id,
        label,
        connect_cmd,
        verify_cmd,
        attempts=3,
        sleep_seconds=3,
    ):
        del transport, case_id, attempts, sleep_seconds
        connect_calls.append((label, connect_cmd, verify_cmd))
        return True

    monkeypatch.setattr(plugin, "_run_required_command", fake_run_required_command)
    monkeypatch.setattr(plugin, "_connect_with_retry", fake_connect_with_retry)

    assert plugin._run_sta_band_connect_sequence({"id": "wifi-llapi-runtime-sequence"}) is True

    command_values = [command for _, command in commands]
    assert "iw dev wl0 disconnect 2>/dev/null || true" in command_values
    assert "iw dev wl1 disconnect 2>/dev/null || true" in command_values
    assert "iw dev wl2 disconnect 2>/dev/null || true" in command_values
    assert command_values.count("killall wpa_supplicant 2>/dev/null || true") == 2
    assert not any(label.startswith("sta_6g_net.") for label, _ in commands)
    assert any(
        command.startswith("printf 'ctrl_interface=/var/run/wpa_supplicant")
        and 'ssid="B0_6G_AP"' in command
        and 'sae_password="B0StaTest1234"' in command
        for label, command in commands
        if label.startswith("sta_6g_prep.")
    )
    assert (
        "sta_6g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping | grep -q PONG",
    ) in connect_calls
    assert (
        "sta_6g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 reconnect",
        "iw dev wl1 link | grep -q 'Connected to '",
    ) in connect_calls
