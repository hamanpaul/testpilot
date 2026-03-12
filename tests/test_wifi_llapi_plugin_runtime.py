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
        if command.startswith("hostapd -t /tmp/wl"):
            if self.config.get("simulate_hostapd_config_fail") and "wl0" in command:
                return {
                    "returncode": 0,
                    "stdout": (
                        "Line 21: Invalid qos_map_set '255'\n"
                        "1 errors found in configuration file '/tmp/wl0_hapd.conf'\n"
                        "Failed to initialize interface"
                    ),
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "elapsed": 0.01,
            }
        if command == "/etc/init.d/wld_gen start":
            if self.config.get("simulate_wld_gen_fail"):
                return {
                    "returncode": 1,
                    "stdout": "wld_gen: failed to apply configuration",
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": "wld_gen: start completed",
                "stderr": "",
                "elapsed": 0.01,
            }
        if command.startswith("wpa_cli ") and command.endswith(" ping"):
            return {
                "returncode": 0,
                "stdout": "PONG",
                "stderr": "",
                "elapsed": 0.01,
            }
        if command.startswith("wpa_cli ") and command.endswith(" status"):
            return {
                "returncode": 0,
                "stdout": "wpa_state=COMPLETED",
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
        if command.startswith("wl -i wl") and command.endswith(" bss"):
            if self.config.get("simulate_bss_down") and "wl0" in command:
                return {
                    "returncode": 0,
                    "stdout": "down",
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": "up",
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
        if command.startswith('ubus-cli "WiFi.AccessPoint.') and "AssociatedDevice.*.MACAddress?" in command:
            if self.config.get("simulate_assoc_query_fail"):
                return {
                    "returncode": 0,
                    "stdout": "No data found",
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="84:0d:8e:aa:bb:cc"',
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

    # 2) 無 capture 的純說明步驟不再誤用 verification_command，直接 skip
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
    assert "[skip] non-executable step s2" in result_2["command"]
    assert result_2["fallback_reason"] == "fallback_skip_echo"

    # 3) 即使 hlapi_command 被清空，非 capture 的純說明步驟仍維持 skip
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
    assert "[skip] non-executable step s3" in result_3["command"]
    assert result_3["fallback_reason"] == "fallback_skip_echo"

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


def test_setup_env_runs_yaml_sta_env_setup(monkeypatch):
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
        DUT 5G setup:
          ubus-cli WiFi.Radio.1.Enable=1
          ubus-cli WiFi.AccessPoint.1.Security.MFPConfig=Disabled
        STA 5G setup:
          iw dev wl0 set type managed
          ifconfig wl0 up
          iw dev wl0 link
        DUT association evidence:
          wl -i wl0 assoclist
        """,
        "verification_command": 'wl -i wl0 assoclist',
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [
            {
                "id": "s1",
                "command": 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"',
            }
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    sta = next(
        transport for transport in recorder.transports if transport.transport_type == "adb"
    )
    assert dut.executed_commands[:3] == [
        "ubus-cli WiFi.Radio.1.Enable=1",
        "ubus-cli WiFi.AccessPoint.1.Security.MFPConfig=Disabled",
        "wl -i wl0 assoclist",
    ]
    assert sta.executed_commands == [
        "iw dev wl0 set type managed",
        "ifconfig wl0 up",
        "iw dev wl0 link",
    ]
    assert plugin.verify_env(case, topology=topology) is True
    assert "ubus-cli WiFi.Radio.1.RegulatoryDomain=CA" not in dut.executed_commands
    assert "/etc/init.d/wld_gen start" not in dut.executed_commands
    assert "wl -i wl0 bss" not in dut.executed_commands
    plugin.teardown(case, topology=topology)


def test_verify_env_only_runs_generic_gates(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-generic-verify",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial", "simulate_bss_down": True},
                "STA": {"transport": "adb"},
            }
        },
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": "echo ok"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert plugin.verify_env(case, topology=topology) is True
    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    assert dut.executed_commands == ['echo "__testpilot_env_gate__"']
    plugin.teardown(case, topology=topology)


def test_setup_env_fails_on_yaml_sta_link_check(monkeypatch):
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
        "sta_env_setup": """
        STA 6G verify:
          iw dev wl1 link
        """,
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": "echo ok"}],
    }

    assert plugin.setup_env(case, topology=topology) is False
    plugin.teardown(case, topology=topology)


def test_setup_env_fails_on_yaml_dut_command_failure(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-sta-band-wld-gen-fail",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial", "simulate_wld_gen_fail": True},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        DUT apply:
          /etc/init.d/wld_gen start
        """,
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": "echo ok"}],
    }

    assert plugin.setup_env(case, topology=topology) is False
    plugin.teardown(case, topology=topology)


def test_run_required_command_retries_after_recovery_signal():
    plugin = _load_plugin()
    calls: list[str] = []

    class _RecoveryTransport:
        def execute(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
            del timeout
            calls.append(command)
            if len(calls) == 1:
                return {
                    "returncode": 1,
                    "stdout": "^C",
                    "stderr": "",
                    "elapsed": 0.01,
                    "recovery_action": "CTRL_C",
                }
            return {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "elapsed": 0.01,
                "recovery_action": None,
            }

    ok = plugin._run_required_command(
        transport=_RecoveryTransport(),
        case_id="wifi-llapi-env-retry",
        label="prep.killall",
        command="killall wpa_supplicant 2>/dev/null || true",
        timeout=20.0,
    )

    assert ok is True
    assert calls == [
        "killall wpa_supplicant 2>/dev/null || true",
        "killall wpa_supplicant 2>/dev/null || true",
    ]


def test_run_required_command_retries_multiple_recovery_signals():
    plugin = _load_plugin()
    calls: list[str] = []

    class _RecoveryTransport:
        def execute(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
            del timeout
            calls.append(command)
            if len(calls) < 3:
                return {
                    "returncode": 124,
                    "stdout": "",
                    "stderr": "serialwrap cmd status timeout: abc",
                    "elapsed": 0.01,
                    "recovery_action": "ATTACH",
                }
            return {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "elapsed": 0.01,
                "recovery_action": None,
            }

    ok = plugin._run_required_command(
        transport=_RecoveryTransport(),
        case_id="wifi-llapi-env-retry-multi",
        label="prep.qosmap",
        command="ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=",
        timeout=20.0,
    )

    assert ok is True
    assert calls == [
        "ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=",
        "ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=",
        "ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=",
    ]


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
                "output": "root@prplOS:/#\n>\n",
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

    # Two outputs differ only by transcript garbage formatting.
    # Both must be evaluated consistently and should not pass via noise.
    noisy_outputs = [
        "\\n'; ubus-cli 'WiFi.AccessPoint.{i}.Security.\\r\\r\\nRekeyingInterval=' Get Command:",
        "\\n'; ubus-cli 'WiFi.AccessPoint.{i}.Security.\\r\\r\\nRekeyingInterval=' Get Command: root@prplOS:/#",
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


def test_evaluate_ignores_command_echo_with_expected_value(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-command-echo-noise",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result"}],
        "pass_criteria": [
            {
                "field": "result.AssociationTime",
                "operator": "contains",
                "value": "2021-06-04T16:05:34Z",
            },
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": (
                    "ubus-cli 'WiFi.AccessPoint.{i}.AssociatedDevice.{i}.AssociationTime=2021-06-04T16:05:34Z'\n"
                    "> WiFi.AccessPoint.{i}.AssociatedDevice.{i}.AssociationTime=2021-06-04T16:05:34Z\n"
                    "ERROR: Syntax error\n"
                    'ubus-cli "WiFi.AccessPoint.*.AssociatedDevice.*.AssociationTime?"\n'
                    "> WiFi.AccessPoint.*.AssociatedDevice.*.AssociationTime?\n"
                    "No data found"
                ),
                "captured": {},
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
        if command == 'ubus-cli "WiFi.AccessPoint.*.?" | grep -E "AssociatedDevice\\.[0-9]+\\.Capabilities"':
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
    assert result["command"] == (
        'ubus-cli "WiFi.AccessPoint.*.?" | grep -E "AssociatedDevice\\.[0-9]+\\.Capabilities"'
    )
    assert result["captured"]["WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities"] == "RRM,BTM,QOS_MAP,PMF"
    plugin.teardown(case, topology=topology)


def test_execute_step_strips_command_echo_before_capture(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-strip-command-echo",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [
            {
                "id": "step1",
                "action": "exec",
                "target": "DUT",
                "capture": "result",
                "command": 'ubus-cli "WiFi.AccessPoint.1.Security.MFPConfig?"',
            }
        ],
        "pass_criteria": [
            {"field": "result.MFPConfig", "operator": "equals", "value": "Required"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    dut = plugin._transports["DUT"]

    def fake_execute(command: str, timeout: float = 30.0) -> dict[str, Any]:
        del timeout
        dut.executed_commands.append(command)
        return {
            "returncode": 0,
            "stdout": (
                'ubus-cli "WiFi.AccessPoint.1.Security.MFPConfig?"\n'
                "> WiFi.AccessPoint.1.Security.MFPConfig?\n"
                'WiFi.AccessPoint.1.Security.MFPConfig="Required"\n'
            ),
            "stderr": "",
            "elapsed": 0.01,
        }

    monkeypatch.setattr(dut, "execute", fake_execute)
    result = plugin.execute_step(case, case["steps"][0], topology=topology)

    assert result["success"] is True
    assert result["output"] == 'WiFi.AccessPoint.1.Security.MFPConfig="Required"'
    assert result["captured"]["WiFi.AccessPoint.1.Security.MFPConfig"] == "Required"
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


def test_extract_cli_fragments_prefers_concrete_getter_from_set_get_prose():
    plugin = _load_plugin()
    text = (
        'Set/Get Security Mode Set Command: ubus-cli WiFi.AccessPoint.{i}.Security.ModeEnabled="""" '
        'Get command: ubus-cli WiFi.AccessPoint.{i}.Security.ModeEnabled?'
    )

    assert plugin._looks_executable("ubus-cli") is False
    assert plugin._extract_cli_fragments(text) == [
        'ubus-cli "WiFi.AccessPoint.{i}.Security.ModeEnabled?"'
    ]


def test_sanitize_cli_fragment_quotes_ubus_operand_with_parentheses():
    plugin = _load_plugin()

    assert plugin._sanitize_cli_fragment(
        "ubus-cli WiFi.AccessPoint.1.kickStation(macaddress=AA:BB:CC:DD:EE:FF)"
    ) == 'ubus-cli "WiFi.AccessPoint.1.kickStation(macaddress=AA:BB:CC:DD:EE:FF)"'


def test_sanitize_cli_fragment_truncates_prose_tail_after_ubus_function():
    plugin = _load_plugin()

    assert plugin._sanitize_cli_fragment(
        "ubus-cli WiFi.Radio.{i}.getRadioStats()PacketsReceived : 1793,"
    ) == 'ubus-cli "WiFi.Radio.{i}.getRadioStats()"'


def test_synthesize_readback_command_uses_parent_query_for_associated_device():
    plugin = _load_plugin()
    case = {
        "source": {
            "object": "WiFi.AccessPoint.{i}.AssociatedDevice.{i}.",
            "api": "AssociationTime",
        },
        "pass_criteria": [
            {"field": "result.AssociationTime", "operator": "contains", "value": "x"},
        ],
    }

    assert plugin._synthesize_readback_command(case, "result") == (
        'ubus-cli "WiFi.AccessPoint.*.?" | grep -E "AssociatedDevice\\.[0-9]+\\.AssociationTime"'
    )


def test_synthesize_readback_command_skips_non_get_method():
    plugin = _load_plugin()
    case = {
        "source": {
            "object": "WiFi.AccessPoint.{i}.",
            "api": "kickStation()",
        },
        "pass_criteria": [
            {"field": "result.kickStation()", "operator": "contains", "value": "x"},
        ],
    }

    assert plugin._synthesize_readback_command(case, "result") is None


def test_extract_cli_fragments_splits_multi_command_prose_line():
    plugin = _load_plugin()
    text = (
        "Run wl -i wl0 beacon_info, wl -i wl1 beacon_info, and wl -i wl2 beacon_info; "
        "compare the HE capabilities payload."
    )

    assert plugin._extract_cli_fragments(text) == [
        "wl -i wl0 beacon_info",
        "wl -i wl1 beacon_info",
        "wl -i wl2 beacon_info",
    ]


def test_extract_cli_fragments_ignores_prose_after_ubus_keyword():
    plugin = _load_plugin()
    text = "3) Read back with ubus-cli after each set; do not use wl txpwr_percent as verification."

    assert plugin._extract_cli_fragments(text) == []


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
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
    ) in connect_calls
    assert (
        "sta_6g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 reconnect",
        "iw dev wl1 link",
    ) in connect_calls


def test_run_sta_band_connect_sequence_limits_to_selected_band(monkeypatch):
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

    case = {
        "id": "wifi-llapi-runtime-5g-only",
        "verification_command": "wl -i wl0 assoclist",
        "steps": [
            {
                "id": "s1",
                "command": 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"',
            }
        ],
    }

    assert plugin._run_sta_band_connect_sequence(case) is True

    command_values = [command for _, command in commands]
    assert "iw dev wl0 disconnect 2>/dev/null || true" in command_values
    assert "iw dev wl1 disconnect 2>/dev/null || true" not in command_values
    assert "iw dev wl2 disconnect 2>/dev/null || true" not in command_values
    assert connect_calls == [("sta_5g", "iw dev wl0 connect B0_5G_AP", "iw dev wl0 link")]
