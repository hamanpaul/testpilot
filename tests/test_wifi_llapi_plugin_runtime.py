"""Runtime behavior tests for wifi_llapi plugin execution/evaluation."""

from __future__ import annotations

from pathlib import Path
import sys
import types
from typing import Any

import yaml

from testpilot.core.plugin_loader import PluginLoader
from testpilot.schema.case_schema import load_case


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


def test_env_command_succeeds_for_iw_link_with_ssid_metrics():
    plugin = _load_plugin()

    result = {
        "returncode": 0,
        "stdout": (
            "SSID: TestPilot_5G\n"
            "freq: 5180\n"
            "RX: 266 bytes (2 packets)\n"
            "TX: 0 bytes (7 packets)\n"
            "signal: -41 dBm\n"
            "tx bitrate: 649.9 MBit/s\n"
        ),
        "stderr": "",
        "elapsed": 0.01,
    }

    assert plugin._env_command_succeeded("iw dev wl0 link", result) is True


def test_case_yaml_band_baselines_reset_radio_defaults():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    required_resets = {
        "ubus-cli WiFi.SSID.4.SSID={{SSID_5G}}": [
            "ubus-cli WiFi.Radio.1.BeaconPeriod=100",
            "ubus-cli WiFi.Radio.1.DTIMPeriod=3",
            "ubus-cli WiFi.Radio.1.DriverConfig.FragmentationThreshold=-1",
            "ubus-cli WiFi.Radio.1.DriverConfig.RtsThreshold=-1",
            "ubus-cli WiFi.Radio.1.DriverConfig.TPCMode=Auto",
            "ubus-cli WiFi.Radio.1.ExplicitBeamFormingEnabled=1",
            "ubus-cli WiFi.Radio.1.ImplicitBeamFormingEnabled=1",
            "ubus-cli WiFi.Radio.1.OfdmaEnable=1",
            "ubus-cli WiFi.Radio.1.ObssCoexistenceEnable=0",
            "ubus-cli WiFi.Radio.1.OperatingStandards=ax",
            "ubus-cli WiFi.Radio.1.RxChainCtrl=-1",
            "ubus-cli WiFi.Radio.1.TxChainCtrl=-1",
            "ubus-cli WiFi.Radio.1.Vendor.Brcm.RegulatoryDomainRev=0",
            "ubus-cli WiFi.Radio.1.Sensing.Enable=1",
            "ubus-cli WiFi.Radio.1.IEEE80211ax.BssColorPartial=0",
            "ubus-cli WiFi.Radio.1.IEEE80211ax.NonSRGOBSSPDMaxOffset=0",
            "ubus-cli WiFi.Radio.1.IEEE80211ax.PSRDisallowed=0",
            "ubus-cli WiFi.Radio.1.IEEE80211ax.SRGOBSSPDMaxOffset=0",
            "ubus-cli WiFi.Radio.1.IEEE80211ax.SRGOBSSPDMinOffset=0",
            "ubus-cli WiFi.Radio.1.LongRetryLimit=6",
            "ubus-cli WiFi.Radio.1.MultiUserMIMOEnabled=1",
            "ubus-cli WiFi.Radio.1.TargetWakeTimeEnable=1",
            "ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=",
            "ubus-cli WiFi.AccessPoint.2.IEEE80211u.QoSMapSet=",
        ],
        "ubus-cli WiFi.SSID.6.SSID={{SSID_6G}}": [
            "ubus-cli WiFi.Radio.2.BeaconPeriod=100",
            "ubus-cli WiFi.Radio.2.DTIMPeriod=3",
            "ubus-cli WiFi.Radio.2.DriverConfig.FragmentationThreshold=-1",
            "ubus-cli WiFi.Radio.2.DriverConfig.RtsThreshold=-1",
            "ubus-cli WiFi.Radio.2.DriverConfig.TPCMode=Auto",
            "ubus-cli WiFi.Radio.2.ExplicitBeamFormingEnabled=1",
            "ubus-cli WiFi.Radio.2.ImplicitBeamFormingEnabled=1",
            "ubus-cli WiFi.Radio.2.OfdmaEnable=1",
            "ubus-cli WiFi.Radio.2.ObssCoexistenceEnable=0",
            "ubus-cli WiFi.Radio.2.OperatingStandards=ax",
            "ubus-cli WiFi.Radio.2.RxChainCtrl=-1",
            "ubus-cli WiFi.Radio.2.TxChainCtrl=-1",
            "ubus-cli WiFi.Radio.2.Vendor.Brcm.RegulatoryDomainRev=0",
            "ubus-cli WiFi.Radio.2.Sensing.Enable=1",
            "ubus-cli WiFi.Radio.2.IEEE80211ax.BssColorPartial=0",
            "ubus-cli WiFi.Radio.2.IEEE80211ax.NonSRGOBSSPDMaxOffset=0",
            "ubus-cli WiFi.Radio.2.IEEE80211ax.PSRDisallowed=0",
            "ubus-cli WiFi.Radio.2.IEEE80211ax.SRGOBSSPDMaxOffset=0",
            "ubus-cli WiFi.Radio.2.IEEE80211ax.SRGOBSSPDMinOffset=0",
            "ubus-cli WiFi.Radio.2.LongRetryLimit=6",
            "ubus-cli WiFi.Radio.2.MultiUserMIMOEnabled=1",
            "ubus-cli WiFi.Radio.2.TargetWakeTimeEnable=1",
            "ubus-cli WiFi.AccessPoint.3.IEEE80211u.QoSMapSet=",
            "ubus-cli WiFi.AccessPoint.4.IEEE80211u.QoSMapSet=",
        ],
        "ubus-cli WiFi.SSID.8.SSID={{SSID_24G}}": [
            "ubus-cli WiFi.Radio.3.BeaconPeriod=100",
            "ubus-cli WiFi.Radio.3.DTIMPeriod=3",
            "ubus-cli WiFi.Radio.3.DriverConfig.FragmentationThreshold=-1",
            "ubus-cli WiFi.Radio.3.DriverConfig.RtsThreshold=-1",
            "ubus-cli WiFi.Radio.3.DriverConfig.TPCMode=Auto",
            "ubus-cli WiFi.Radio.3.ExplicitBeamFormingEnabled=1",
            "ubus-cli WiFi.Radio.3.ImplicitBeamFormingEnabled=1",
            "ubus-cli WiFi.Radio.3.OfdmaEnable=1",
            "ubus-cli WiFi.Radio.3.ObssCoexistenceEnable=0",
            "ubus-cli WiFi.Radio.3.OperatingStandards=ax",
            "ubus-cli WiFi.Radio.3.RxChainCtrl=-1",
            "ubus-cli WiFi.Radio.3.TxChainCtrl=-1",
            "ubus-cli WiFi.Radio.3.Vendor.Brcm.RegulatoryDomainRev=0",
            "ubus-cli WiFi.Radio.3.Sensing.Enable=1",
            "ubus-cli WiFi.Radio.3.IEEE80211ax.BssColorPartial=0",
            "ubus-cli WiFi.Radio.3.IEEE80211ax.NonSRGOBSSPDMaxOffset=0",
            "ubus-cli WiFi.Radio.3.IEEE80211ax.PSRDisallowed=0",
            "ubus-cli WiFi.Radio.3.IEEE80211ax.SRGOBSSPDMaxOffset=0",
            "ubus-cli WiFi.Radio.3.IEEE80211ax.SRGOBSSPDMinOffset=0",
            "ubus-cli WiFi.Radio.3.LongRetryLimit=6",
            "ubus-cli WiFi.Radio.3.MultiUserMIMOEnabled=1",
            "ubus-cli WiFi.Radio.3.TargetWakeTimeEnable=1",
            "ubus-cli WiFi.AccessPoint.5.IEEE80211u.QoSMapSet=",
            "ubus-cli WiFi.AccessPoint.6.IEEE80211u.QoSMapSet=",
        ],
    }

    for path in sorted(cases_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        sta_env_setup = str(data.get("sta_env_setup") or "")
        if not sta_env_setup:
            continue
        for anchor, expected_lines in required_resets.items():
            if anchor not in sta_env_setup:
                continue
            for expected in expected_lines:
                assert expected in sta_env_setup, (
                    f"{path.name} missing radio baseline reset: {expected}"
                )


def test_pre_skip_aligned_manual_cases_avoid_stale_sample_values():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    # Post-skip cases are still pending review; keep this guard focused on the
    # pre-skip YAMLs that the audit report already treats as aligned.
    d013 = yaml.safe_load(
        (cases_dir / "D013_avgsignalstrength.yaml").read_text(encoding="utf-8")
    )
    d013_commands = "\n".join(str(step.get("command", "")) for step in d013["steps"])
    assert d013["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d013["source"]["row"] == 8
    assert d013["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.AvgSignalStrength?"'
    assert "AvgSignalStrength=" not in d013["hlapi_command"]
    assert "DriverSmoothedRSSI=" in d013_commands
    assert any(
        criterion["field"] == "result.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d013["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi.DriverSmoothedRSSI"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d013["pass_criteria"]
    )

    d017 = yaml.safe_load(
        (cases_dir / "D017_connectionduration.yaml").read_text(encoding="utf-8")
    )
    d017_commands = "\n".join(str(step.get("command", "")) for step in d017["steps"])
    assert d017["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d017["source"]["row"] == 12
    assert "ConnectionDuration?" in d017["hlapi_command"]
    assert "ConnectionDuration=8229" not in d017["hlapi_command"]
    assert "DriverConnectionSeconds=" in d017_commands
    assert any(
        criterion["field"] == "result_after_wait.ConnectionDuration"
        and criterion["operator"] == ">"
        and criterion["reference"] == "result.ConnectionDuration"
        for criterion in d017["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_duration.DriverConnectionSeconds"
        and criterion["operator"] == ">="
        and criterion["reference"] == "result_after_wait.ConnectionDuration"
        for criterion in d017["pass_criteria"]
    )

    d019 = yaml.safe_load(
        (cases_dir / "D019_downlinkmcs.yaml").read_text(encoding="utf-8")
    )
    d019_commands = "\n".join(str(step.get("command", "")) for step in d019["steps"])
    assert d019["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d019["source"]["row"] == 14
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d019_commands
    assert 'WiFi.SSID.4.BSSID?' in d019_commands
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkMCS?' in d019_commands
    assert "DriverDownlinkMCS=" in d019_commands
    assert any(
        criterion["field"] == "ap_bssid.BSSID"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d019["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.DownlinkMCS"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_mcs.DriverDownlinkMCS"
        for criterion in d019["pass_criteria"]
    )

    d011 = yaml.safe_load(
        (cases_dir / "D011_associationtime.yaml").read_text(encoding="utf-8")
    )
    d011_commands = "\n".join(str(step.get("command", "")) for step in d011["steps"])
    assert d011["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d011["source"]["row"] == 6
    assert "AssociationTime?" in d011["hlapi_command"]
    assert "AssociationTime=" not in d011["hlapi_command"]
    assert "AssocMAC=" in d011_commands
    assert "ConnectionSeconds=" in d011_commands
    assert any(
        criterion["field"] == "result.AssociationTime"
        and criterion["operator"] == "regex"
        for criterion in d011["pass_criteria"]
    )

    d012 = yaml.safe_load(
        (cases_dir / "D012_authenticationstate.yaml").read_text(encoding="utf-8")
    )
    d012_commands = "\n".join(str(step.get("command", "")) for step in d012["steps"])
    assert d012["source"]["row"] == 7
    assert "AuthenticationState?" in d012["hlapi_command"]
    assert "AuthenticationState=" not in d012["hlapi_command"]
    assert "DriverAuthState=" in d012_commands
    assert any(
        criterion["field"] == "result.AuthenticationState"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_state.DriverAuthState"
        for criterion in d012["pass_criteria"]
    )

    d018 = yaml.safe_load(
        (cases_dir / "D018_downlinkbandwidth.yaml").read_text(encoding="utf-8")
    )
    d018_commands = "\n".join(str(step.get("command", "")) for step in d018["steps"])
    assert d018["source"]["row"] == 13
    assert "DownlinkBandwidth?" in d018["hlapi_command"]
    assert "DownlinkBandwidth=0" not in d018["hlapi_command"]
    assert "DriverBandwidth=" in d018_commands
    assert any(
        criterion["field"] == "result.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bandwidth.DriverBandwidth"
        for criterion in d018["pass_criteria"]
    )

    d021 = yaml.safe_load(
        (cases_dir / "D021_encryptionmode_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert d021["source"]["row"] == 16
    assert d021["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert d021["results_reference"]["v4.0.3"]["6g"] == "Pass"
    assert d021["results_reference"]["v4.0.3"]["2.4g"] == "Pass"
    assert "EncryptionMode?" in d021["hlapi_command"]
    assert "EncryptionMode=AES" not in d021["hlapi_command"]
    assert any(
        criterion["field"] == "result.EncryptionMode"
        and criterion["operator"] == "equals"
        and criterion["value"] == "Default"
        for criterion in d021["pass_criteria"]
    )

    d023 = yaml.safe_load(
        (cases_dir / "D023_hecapabilities_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d023_commands = "\n".join(str(step.get("command", "")) for step in d023["steps"])
    assert d023["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d023["source"]["row"] == 18
    assert d023["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.HeCapabilities?"'
    assert "HeCapabilities=" not in d023["hlapi_command"]
    assert "DriverHeMuBfe=1" in d023_commands
    assert any(
        criterion["field"] == "result.HeCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SU&MU-BFE"
        for criterion in d023["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_he.DriverHeMuBfe"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d023["pass_criteria"]
    )

    d024 = yaml.safe_load(
        (cases_dir / "D024_htcapabilities_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d024_commands = "\n".join(str(step.get("command", "")) for step in d024["steps"])
    assert d024["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d024["source"]["row"] == 19
    assert d024["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.HtCapabilities?"'
    assert "HtCapabilities=40MHz,SGI20,SGI40" not in d024["hlapi_command"]
    assert "DriverHt40MHz=1" in d024_commands
    assert "DriverHtSgi20=1" in d024_commands
    assert "DriverHtSgi40=1" in d024_commands
    assert any(
        criterion["field"] == "result.HtCapabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "40MHz,SGI20,SGI40"
        for criterion in d024["pass_criteria"]
    )

    d026 = yaml.safe_load(
        (cases_dir / "D026_lastdatadownlinkrate.yaml").read_text(encoding="utf-8")
    )
    d026_commands = "\n".join(str(step.get("command", "")) for step in d026["steps"])
    assert d026["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d026["source"]["row"] == 21
    assert d026["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LastDataDownlinkRate?"'
    assert "LastDataDownlinkRate=1733333" not in d026["hlapi_command"]
    assert 'WiFi.SSID.4.BSSID?' in d026_commands
    assert "DriverLastDownlinkRateRounded=" in d026_commands
    assert any(
        criterion["field"] == "ap_bssid.BSSID"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d026["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.LastDataDownlinkRate"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_rate.DriverLastDownlinkRateRounded"
        for criterion in d026["pass_criteria"]
    )

    d027 = yaml.safe_load(
        (cases_dir / "D027_lastdatauplinkrate.yaml").read_text(encoding="utf-8")
    )
    d027_commands = "\n".join(str(step.get("command", "")) for step in d027["steps"])
    assert d027["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d027["source"]["row"] == 22
    assert d027["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LastDataUplinkRate?"'
    assert "LastDataUplinkRate=1733333" not in d027["hlapi_command"]
    assert 'WiFi.SSID.4.BSSID?' in d027_commands
    assert "DriverLastUplinkRateRounded=" in d027_commands
    assert any(
        criterion["field"] == "result.LastDataUplinkRate"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_rate.DriverLastUplinkRateRounded"
        for criterion in d027["pass_criteria"]
    )

    d028 = yaml.safe_load(
        (cases_dir / "D028_linkbandwidth.yaml").read_text(encoding="utf-8")
    )
    d028_commands = "\n".join(str(step.get("command", "")) for step in d028["steps"])
    assert d028["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d028["source"]["row"] == 23
    assert d028["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LinkBandwidth?"'
    assert "LinkBandwidth=160MHz" not in d028["hlapi_command"]
    assert 'WiFi.Radio.1.OperatingChannelBandwidth?' in d028_commands
    assert "DriverLinkBandwidth=" in d028_commands
    assert any(
        criterion["field"] == "result.LinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "radio_bw.OperatingChannelBandwidth"
        for criterion in d028["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.LinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw.DriverLinkBandwidth"
        for criterion in d028["pass_criteria"]
    )

    d029 = yaml.safe_load(
        (cases_dir / "D029_macaddress_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d029_commands = "\n".join(str(step.get("command", "")) for step in d029["steps"])
    assert d029["source"]["row"] == 24
    assert "MACAddress?" in d029["hlapi_command"]
    assert "MACAddress=AA:6B:30:4E:8E:5C" not in d029["hlapi_command"]
    assert "StaMAC=" in d029_commands
    assert "AssocMAC=" in d029_commands
    assert any(
        criterion["field"] == "assoc_driver.AssocMAC"
        and criterion["reference"] == "sta_status.STAMAC"
        for criterion in d029["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.MACAddress"
        and criterion["reference"] == "assoc_driver.AssocMAC"
        for criterion in d029["pass_criteria"]
    )

    multiband_direct_cases = {
        "D323_broadcastpacketsreceived.yaml": {"row": 245, "api": "BroadcastPacketsReceived", "driver": "DriverBroadcastPacketsReceived", "awk_field": "$23", "expected": "Pass"},
        "D324_broadcastpacketssent.yaml": {"row": 246, "api": "BroadcastPacketsSent", "driver": "DriverBroadcastPacketsSent", "awk_field": "$24", "expected": "Pass"},
        "D325_bytesreceived_ssid_stats.yaml": {"row": 247, "api": "BytesReceived", "driver": "DriverBytesReceived", "awk_field": "$2", "expected": "Pass"},
        "D326_bytessent_ssid_stats.yaml": {"row": 248, "api": "BytesSent", "driver": "DriverBytesSent", "awk_field": "$10", "expected": "Pass"},
        "D327_discardpacketsreceived.yaml": {"row": 249, "api": "DiscardPacketsReceived", "driver": "DriverDiscardPacketsReceived", "awk_field": "$5", "expected": "To be tested"},
        "D328_discardpacketssent.yaml": {"row": 250, "api": "DiscardPacketsSent", "driver": "DriverDiscardPacketsSent", "awk_field": "$13", "expected": "To be tested"},
        "D329_errorsreceived_ssid_stats.yaml": {"row": 251, "api": "ErrorsReceived", "driver": "DriverErrorsReceived", "awk_field": "$4", "expected": "To be tested"},
        "D330_errorssent_ssid_stats.yaml": {"row": 252, "api": "ErrorsSent", "driver": "DriverErrorsSent", "awk_field": "$12", "expected": "To be tested"},
        "D331_failedretranscount_ssid_stats.yaml": {"row": 253, "api": "FailedRetransCount", "expected": "To be tested"},
        "D332_multicastpacketsreceived.yaml": {"row": 254, "api": "MulticastPacketsReceived", "driver": "DriverMulticastPacketsReceived", "awk_field": "$9", "expected": "Pass"},
        "D333_multicastpacketssent.yaml": {"row": 255, "api": "MulticastPacketsSent", "driver": "DriverMulticastPacketsSent", "awk_field": "$18", "expected": "Pass"},
        "D334_packetsreceived_ssid_stats.yaml": {"row": 256, "api": "PacketsReceived", "driver": "DriverPacketsReceived", "awk_field": "$3", "expected": "Pass"},
        "D335_packetssent_ssid_stats.yaml": {"row": 257, "api": "PacketsSent", "driver": "DriverPacketsSent", "awk_field": "$11", "expected": "Pass"},
        "D336_retranscount_ssid_stats.yaml": {"row": 258, "api": "RetransCount", "expected": "To be tested"},
        "D337_unicastpacketsreceived.yaml": {"row": 259, "api": "UnicastPacketsReceived", "driver": "DriverUnicastPacketsReceived", "awk_field": "$21", "expected": "Pass"},
        "D338_unicastpacketssent.yaml": {"row": 260, "api": "UnicastPacketsSent", "driver": "DriverUnicastPacketsSent", "awk_field": "$22", "expected": "Pass"},
        "D339_unknownprotopacketsreceived_ssid_stats.yaml": {"row": 261, "api": "UnknownProtoPacketsReceived", "expected": "To be tested"},
        "D408_multipleretrycount_ssid_stats.yaml": {"row": 301, "api": "MultipleRetryCount", "expected": "To be tested"},
        "D409_retrycount_ssid_stats_basic.yaml": {"row": 302, "api": "RetryCount", "expected": "To be tested"},
        "D497_retrycount_ssid_stats_verified.yaml": {"row": 362, "api": "RetryCount", "expected": "Not Supported"},
    }

    for filename, meta in multiband_direct_cases.items():
        case_data = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        assert "aliases" not in case_data
        assert case_data["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.SSID.{{i}}.Stats.{meta["api"]}?"'
        assert "5G -> 6G -> 2.4G sequentially" in case_data["test_environment"]
        assert "attempt STA-generated traffic" in case_data["test_environment"]
        assert f"WiFi.SSID.4.Stats.{meta['api']}?" in commands
        assert f"WiFi.SSID.6.Stats.{meta['api']}?" in commands
        assert f"WiFi.SSID.8.Stats.{meta['api']}?" in commands
        assert f"GetSSIDStats{meta['api']}5g=" in commands
        assert f"GetSSIDStats{meta['api']}6g=" in commands
        assert f"GetSSIDStats{meta['api']}24g=" in commands
        assert "AssocMac5g=" in commands
        assert "AssocMac6g=" in commands
        assert "AssocMac24g=" in commands
        assert case_data["results_reference"]["v4.0.3"]["5g"] == meta["expected"]
        assert case_data["results_reference"]["v4.0.3"]["6g"] == meta["expected"]
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == meta["expected"]
        assert any(
            criterion["field"] == "assoc_5g.AssocMac5g"
            and criterion["operator"] == "equals"
            and criterion["value"] == "2c:59:17:00:04:85"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == f"direct_5g.{meta['api']}"
            and criterion["operator"] == "equals"
            and criterion["reference"] == f"getssid_5g.GetSSIDStats{meta['api']}5g"
            for criterion in case_data["pass_criteria"]
        )
        if "driver" in meta:
            assert f"{meta['driver']}5g=" in commands
            assert f"{meta['driver']}6g=" in commands
            assert f"{meta['driver']}24g=" in commands
            assert meta["awk_field"] in commands
            assert any(
                criterion["field"] == f"direct_5g.{meta['api']}"
                and criterion["operator"] == "equals"
                and criterion["reference"] == f"driver_5g.{meta['driver']}5g"
                for criterion in case_data["pass_criteria"]
            )
        elif meta["expected"] == "Not Supported":
            assert any(
                criterion["field"] == f"direct_5g.{meta['api']}"
                and criterion["operator"] == "equals"
                and str(criterion.get("value")) == "0"
                for criterion in case_data["pass_criteria"]
            )

    multiband_getssid_cases = {
        "D302_getssidstats_broadcastpacketsreceived.yaml": {"row": 225, "api": "BroadcastPacketsReceived", "driver": "DriverBroadcastPacketsReceived", "awk_field": "$23", "expected": "Pass"},
        "D303_getssidstats_broadcastpacketssent.yaml": {"row": 226, "api": "BroadcastPacketsSent", "driver": "DriverBroadcastPacketsSent", "awk_field": "$24", "expected": "Pass"},
        "D304_getssidstats_bytesreceived.yaml": {"row": 227, "api": "BytesReceived", "driver": "DriverBytesReceived", "awk_field": "$2", "expected": "Pass"},
        "D305_getssidstats_bytessent.yaml": {"row": 228, "api": "BytesSent", "driver": "DriverBytesSent", "awk_field": "$10", "expected": "Pass"},
        "D306_getssidstats_discardpacketsreceived.yaml": {"row": 229, "api": "DiscardPacketsReceived", "driver": "DriverDiscardPacketsReceived", "awk_field": "$5", "expected": "Pass"},
        "D307_getssidstats_discardpacketssent.yaml": {"row": 230, "api": "DiscardPacketsSent", "driver": "DriverDiscardPacketsSent", "awk_field": "$13", "expected": "Pass"},
        "D308_getssidstats_errorsreceived.yaml": {"row": 231, "api": "ErrorsReceived", "driver": "DriverErrorsReceived", "awk_field": "$4", "expected": "Pass"},
        "D309_getssidstats_errorssent.yaml": {"row": 232, "api": "ErrorsSent", "driver": "DriverErrorsSent", "awk_field": "$12", "expected": "Pass"},
        "D310_getssidstats_failedretranscount.yaml": {"row": 233, "api": "FailedRetransCount", "expected": "Not Supported"},
        "D311_getssidstats_multicastpacketsreceived.yaml": {"row": 234, "api": "MulticastPacketsReceived", "driver": "DriverMulticastPacketsReceived", "awk_field": "$9", "expected": "Pass"},
        "D312_getssidstats_multicastpacketssent.yaml": {"row": 235, "api": "MulticastPacketsSent", "driver": "DriverMulticastPacketsSent", "awk_field": "$18", "expected": "Pass"},
        "D313_getssidstats_packetsreceived.yaml": {"row": 236, "api": "PacketsReceived", "driver": "DriverPacketsReceived", "awk_field": "$3", "expected": "Pass"},
        "D314_getssidstats_packetssent.yaml": {"row": 237, "api": "PacketsSent", "driver": "DriverPacketsSent", "awk_field": "$11", "expected": "Pass"},
        "D315_getssidstats_retranscount.yaml": {"row": 238, "api": "RetransCount", "expected": "Not Supported"},
        "D316_getssidstats_unicastpacketsreceived.yaml": {"row": 239, "api": "UnicastPacketsReceived", "driver": "DriverUnicastPacketsReceived", "awk_field": "$21", "expected": "Pass"},
        "D317_getssidstats_unicastpacketssent.yaml": {"row": 240, "api": "UnicastPacketsSent", "driver": "DriverUnicastPacketsSent", "awk_field": "$22", "expected": "Pass"},
        "D318_getssidstats_unknownprotopacketsreceived.yaml": {"row": 241, "api": "UnknownProtoPacketsReceived", "expected": "Not Supported"},
    }

    for filename, meta in multiband_getssid_cases.items():
        case_data = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        assert "aliases" not in case_data
        assert case_data["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["hlapi_command"] == 'ubus-cli "WiFi.SSID.{i}.getSSIDStats()"'
        assert "5G -> 6G -> 2.4G sequentially" in case_data["test_environment"]
        assert f"GetSSIDStats{meta['api']}5g=" in commands
        assert f"GetSSIDStats{meta['api']}6g=" in commands
        assert f"GetSSIDStats{meta['api']}24g=" in commands
        assert f"WiFi.SSID.4.Stats.{meta['api']}?" in commands
        assert f"WiFi.SSID.6.Stats.{meta['api']}?" in commands
        assert f"WiFi.SSID.8.Stats.{meta['api']}?" in commands
        assert case_data["results_reference"]["v4.0.3"]["5g"] == meta["expected"]
        assert case_data["results_reference"]["v4.0.3"]["6g"] == meta["expected"]
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == meta["expected"]
        assert any(
            criterion["field"] == f"method_5g.GetSSIDStats{meta['api']}5g"
            and criterion["operator"] == "equals"
            and criterion["reference"] == f"direct_5g.{meta['api']}"
            for criterion in case_data["pass_criteria"]
        )
        if "driver" in meta:
            assert f"{meta['driver']}5g=" in commands
            assert f"{meta['driver']}6g=" in commands
            assert f"{meta['driver']}24g=" in commands
            assert meta["awk_field"] in commands
            assert any(
                criterion["field"] == f"method_5g.GetSSIDStats{meta['api']}5g"
                and criterion["operator"] == "equals"
                and criterion["reference"] == f"driver_5g.{meta['driver']}5g"
                for criterion in case_data["pass_criteria"]
            )
        else:
            assert any(
                criterion["field"] == f"method_5g.GetSSIDStats{meta['api']}5g"
                and criterion["operator"] == "equals"
                and str(criterion.get("value")) == "0"
                for criterion in case_data["pass_criteria"]
            )

    for case_num in range(498, 530):
        filename = next(cases_dir.glob(f"D{case_num}_*.yaml"))
        case_data = yaml.safe_load(filename.read_text(encoding="utf-8"))
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        ac = case_data["source"]["api"]
        metric = case_data["source"]["object"].split("Stats.", 1)[1].rstrip(".")
        assert "aliases" not in case_data
        assert case_data["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
        assert case_data["source"]["row"] == case_num - 135
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.SSID.{{i}}.Stats.{metric}.{ac}?"'
        assert "\\n" not in case_data["test_procedure"]
        assert "Not Supported" in case_data["test_procedure"]
        assert "wme_counters" in case_data["verification_command"]
        assert case_data["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
        assert case_data["results_reference"]["v4.0.3"]["6g"] == "Not Supported"
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "Not Supported"
        assert f"WiFi.SSID.4.Stats.{metric}.{ac}?" in commands
        assert f"WiFi.SSID.6.Stats.{metric}.{ac}?" in commands
        assert f"WiFi.SSID.8.Stats.{metric}.{ac}?" in commands
        assert any(
            criterion["field"] == f"result_5g.{ac}5g"
            and criterion["operator"] == "equals"
            and str(criterion.get("value")) == "0"
            for criterion in case_data["pass_criteria"]
        )


def test_pending_method_calibration_cases_use_runtime_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D006-kickstation",
        "wifi-llapi-D007-kickstationreason",
        "wifi-llapi-D008-sendbsstransferrequest",
        "wifi-llapi-D009-sendremotemeasumentrequest",
    }.issubset(discoverable_ids)

    d006 = load_case(cases_dir / "D006_kickstation.yaml")
    d006_commands = "\n".join(str(step.get("command", "")) for step in d006["steps"])
    d006_links = {link["band"] for link in d006["topology"]["links"]}
    assert "aliases" not in d006
    assert d006_links == {"5g", "2.4g"}
    assert "changed_from" not in {str(criterion.get("operator")) for criterion in d006["pass_criteria"]}
    assert not any("compare_to" in criterion for criterion in d006["pass_criteria"])
    assert 'WiFi.AccessPoint.1.kickStation(MACAddress=2C:59:17:00:04:85)' in d006_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:85"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_5g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_5g.DisassociationTime"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_24g.AssocMac24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:97"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_24g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_24g.DisassociationTime"
        for criterion in d006["pass_criteria"]
    )

    d007 = load_case(cases_dir / "D007_kickstationreason.yaml")
    d007_commands = "\n".join(str(step.get("command", "")) for step in d007["steps"])
    d007_links = {link["band"] for link in d007["topology"]["links"]}
    assert d007_links == {"5g", "2.4g"}
    assert "changed_from" not in {str(criterion.get("operator")) for criterion in d007["pass_criteria"]}
    assert not any("compare_to" in criterion for criterion in d007["pass_criteria"])
    assert "kickStationReason(macaddress=2C:59:17:00:04:85,reason=1)" in d007_commands
    assert "kickStationReason(macaddress=2C:59:17:00:04:97,reason=1)" in d007_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:85"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_5g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_5g.DisassociationTime"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_24g.AssocMac24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:97"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_24g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_24g.DisassociationTime"
        for criterion in d007["pass_criteria"]
    )

    d008 = load_case(cases_dir / "D008_sendbsstransferrequest.yaml")
    d008_commands = "\n".join(str(step.get("command", "")) for step in d008["steps"])
    assert "config" not in d008["topology"]["devices"]["STA"]
    assert "WiFi.AccessPoint.1.MBOEnable=1" in d008_commands
    assert "WiFi.AccessPoint.5.MBOEnable=1" in d008_commands
    assert "wl -i wl0 join TestPilot_5G imode bss" in d008_commands
    assert "wl -i wl2 join TestPilot_24G imode bss" in d008_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:85"
        for criterion in d008["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "[-1]"
        for criterion in d008["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "[-1]"
        for criterion in d008["pass_criteria"]
    )

    d009 = load_case(cases_dir / "D009_sendremotemeasumentrequest.yaml")
    d009_commands = "\n".join(str(step.get("command", "")) for step in d009["steps"])
    assert "config" not in d009["topology"]["devices"]["STA"]
    assert "sendRemoteMeasumentRequest" in d009_commands
    assert "sendRemoteMeasurementRequest" not in d009_commands
    assert "wl -i wl0 join TestPilot_5G imode bss" in d009_commands
    assert "wl -i wl2 join TestPilot_24G imode bss" in d009_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:85"
        for criterion in d009["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?s)\[\s*\[\s*\]\s*\]"
        for criterion in d009["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?s)\[\s*\[\s*\]\s*\]"
        for criterion in d009["pass_criteria"]
    )


def test_pending_readonly_associateddevice_cases_use_live_cross_checks():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D014-avgsignalstrengthbychain",
        "wifi-llapi-D015-capabilities",
    }.issubset(discoverable_ids)

    d014 = load_case(cases_dir / "D014_avgsignalstrengthbychain.yaml")
    d014_commands = "\n".join(str(step.get("command", "")) for step in d014["steps"])
    d014_links = {link["band"] for link in d014["topology"]["links"]}
    assert d014_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d014_commands
    assert "wl -i wl2 assoclist" in d014_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:85"
        for criterion in d014["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.AvgSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-?[0-9]+$"
        for criterion in d014["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AvgSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-?[0-9]+$"
        for criterion in d014["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.AvgSignalStrengthByChain"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d014["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AvgSignalStrengthByChain"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d014["pass_criteria"]
    )

    d015 = load_case(cases_dir / "D015_capabilities.yaml")
    d015_commands = "\n".join(str(step.get("command", "")) for step in d015["steps"])
    d015_links = {link["band"] for link in d015["topology"]["links"]}
    assert d015_links == {"5g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities?' in d015_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.Capabilities?' in d015_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:85"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.Capabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "BTM"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.Capabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "QOS_MAP"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.Capabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "PMF"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.Capabilities"
        and criterion["operator"] == "not_contains"
        and criterion["value"] == "RRM"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_24g.AssocMac24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:97"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.Capabilities"
        and criterion["operator"] == "empty"
        for criterion in d015["pass_criteria"]
    )


def test_pending_readonly_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d014 = load_case(cases_dir / "D014_avgsignalstrengthbychain.yaml")
    d014_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.AvgSignalStrengthByChain=-34",
                "captured": {"AvgSignalStrengthByChain": "-34"},
                "timing": 0.01,
            },
            "step4_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "captured": {"AssocMac24g": "2c:59:17:00:04:97"},
                "timing": 0.01,
            },
            "step5_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.AvgSignalStrengthByChain=-16",
                "captured": {"AvgSignalStrengthByChain": "-16"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d014, d014_results) is True

    d014_fail_results = {
        "steps": {
            **d014_results["steps"],
            "step5_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.AvgSignalStrengthByChain=3",
                "captured": {"AvgSignalStrengthByChain": "3"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d014, d014_fail_results) is False

    d015 = load_case(cases_dir / "D015_capabilities.yaml")
    d015_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities="BTM,QOS_MAP,PMF"',
                "captured": {"Capabilities": "BTM,QOS_MAP,PMF"},
                "timing": 0.01,
            },
            "step4_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "captured": {"AssocMac24g": "2c:59:17:00:04:97"},
                "timing": 0.01,
            },
            "step5_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.Capabilities=""',
                "captured": {"Capabilities": ""},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d015, d015_results) is True

    d015_fail_results = {
        "steps": {
            **d015_results["steps"],
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities="BTM,QOS_MAP,PMF,RRM"',
                "captured": {"Capabilities": "BTM,QOS_MAP,PMF,RRM"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d015, d015_fail_results) is False


def test_pending_boolean_and_frequency_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D020-downlinkshortguard",
        "wifi-llapi-D022-frequencycapabilities",
    }.issubset(discoverable_ids)

    d020 = load_case(cases_dir / "D020_downlinkshortguard.yaml")
    d020_commands = "\n".join(str(step.get("command", "")) for step in d020["steps"])
    d020_links = {link["band"] for link in d020["topology"]["links"]}
    assert d020_links == {"5g", "2.4g"}
    assert "operator: in" not in yaml.safe_dump(d020["pass_criteria"])
    assert "wl -i wl0 assoclist" in d020_commands
    assert "wl -i wl2 assoclist" in d020_commands
    assert any(
        criterion["field"] == "result_5g.DownlinkShortGuard"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d020["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.DownlinkShortGuard"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d020["pass_criteria"]
    )

    d022 = load_case(cases_dir / "D022_frequencycapabilities.yaml")
    d022_commands = "\n".join(str(step.get("command", "")) for step in d022["steps"])
    d022_links = {link["band"] for link in d022["topology"]["links"]}
    assert d022_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d022_commands
    assert "wl -i wl2 assoclist" in d022_commands
    assert any(
        criterion["field"] == "result_5g.FrequencyCapabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "5GHz"
        for criterion in d022["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.FrequencyCapabilities"
        and criterion["operator"] == "empty"
        for criterion in d022["pass_criteria"]
    )


def test_pending_boolean_and_frequency_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d020 = load_case(cases_dir / "D020_downlinkshortguard.yaml")
    d020_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkShortGuard=1",
                "captured": {"DownlinkShortGuard": "1"},
                "timing": 0.01,
            },
            "step4_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "captured": {"AssocMac24g": "2c:59:17:00:04:97"},
                "timing": 0.01,
            },
            "step5_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkShortGuard=1",
                "captured": {"DownlinkShortGuard": "1"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d020, d020_results) is True

    d020_fail_results = {
        "steps": {
            **d020_results["steps"],
            "step5_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkShortGuard=0",
                "captured": {"DownlinkShortGuard": "0"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d020, d020_fail_results) is False

    d022 = load_case(cases_dir / "D022_frequencycapabilities.yaml")
    d022_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.FrequencyCapabilities="5GHz"',
                "captured": {"FrequencyCapabilities": "5GHz"},
                "timing": 0.01,
            },
            "step4_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "captured": {"AssocMac24g": "2c:59:17:00:04:97"},
                "timing": 0.01,
            },
            "step5_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.FrequencyCapabilities=",
                "captured": {"FrequencyCapabilities": ""},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d022, d022_results) is True

    d022_fail_results = {
        "steps": {
            **d022_results["steps"],
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.FrequencyCapabilities="2.4GHz"',
                "captured": {"FrequencyCapabilities": "2.4GHz"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d022, d022_fail_results) is False


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


def test_extract_key_values_captures_bare_empty_value():
    plugin = _load_plugin()
    parsed = plugin._extract_key_values(
        "WiFi.AccessPoint.5.AssociatedDevice.1.FrequencyCapabilities=\n"
    )
    assert parsed["WiFi.AccessPoint.5.AssociatedDevice.1.FrequencyCapabilities"] == ""


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


def test_evaluate_supports_reference_field(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-reference-field",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [
            {"id": "s1", "capture": "sta_status"},
            {"id": "s2", "capture": "result"},
        ],
        "pass_criteria": [
            {
                "field": "result.MACAddress",
                "operator": "equals",
                "reference": "sta_status.STAMAC",
            },
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": "STAMAC=2C:59:17:00:04:86",
                "captured": {"STAMAC": "2C:59:17:00:04:86"},
                "timing": 0.01,
            },
            "s2": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:04:86"',
                "captured": {"MACAddress": "2C:59:17:00:04:86"},
                "timing": 0.01,
            },
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
