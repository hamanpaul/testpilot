"""Runtime behavior tests for wifi_llapi plugin execution/evaluation."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import sys
import types
from typing import Any

import pytest
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


def test_pending_inactive_and_bandwidth_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D025-inactive",
        "wifi-llapi-D030-maxbandwidthsupported",
    }.issubset(discoverable_ids)

    d025 = load_case(cases_dir / "D025_inactive.yaml")
    d025_commands = "\n".join(str(step.get("command", "")) for step in d025["steps"])
    d025_links = {link["band"] for link in d025["topology"]["links"]}
    assert d025_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d025_commands
    assert "wl -i wl2 assoclist" in d025_commands
    assert any(
        criterion["field"] == "result_5g.Inactive"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^\d+$"
        for criterion in d025["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.Inactive"
        and criterion["operator"] == ">="
        and str(criterion["value"]) == "0"
        for criterion in d025["pass_criteria"]
    )

    d030 = load_case(cases_dir / "D030_maxbandwidthsupported.yaml")
    d030_commands = "\n".join(str(step.get("command", "")) for step in d030["steps"])
    d030_links = {link["band"] for link in d030["topology"]["links"]}
    assert d030_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d030_commands
    assert "wl -i wl2 assoclist" in d030_commands
    assert any(
        criterion["field"] == "result_5g.MaxBandwidthSupported"
        and criterion["operator"] == "equals"
        and criterion["value"] == "160MHz"
        for criterion in d030["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.MaxBandwidthSupported"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^(20MHz|40MHz|80MHz|160MHz|Unknown)$"
        for criterion in d030["pass_criteria"]
    )
    assert d030["results_reference"]["v4.0.3"]["2.4g"] == "STA-Discrepancy"


def test_pending_inactive_and_bandwidth_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d025 = load_case(cases_dir / "D025_inactive.yaml")
    d025_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.Inactive=14",
                "captured": {"Inactive": "14"},
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
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.Inactive=9",
                "captured": {"Inactive": "9"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d025, d025_results) is True

    d025_fail_results = {
        "steps": {
            **d025_results["steps"],
            "step5_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.Inactive=ERROR",
                "captured": {"Inactive": "ERROR"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d025, d025_fail_results) is False

    d030 = load_case(cases_dir / "D030_maxbandwidthsupported.yaml")
    d030_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MaxBandwidthSupported="160MHz"',
                "captured": {"MaxBandwidthSupported": "160MHz"},
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
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.MaxBandwidthSupported="Unknown"',
                "captured": {"MaxBandwidthSupported": "Unknown"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d030, d030_results) is True

    d030_fail_results = {
        "steps": {
            **d030_results["steps"],
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MaxBandwidthSupported="80MHz"',
                "captured": {"MaxBandwidthSupported": "80MHz"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d030, d030_fail_results) is False


def test_pending_not_supported_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D031-mode-accesspoint-associateddevice",
        "wifi-llapi-D032-mugroupid",
    }.issubset(discoverable_ids)

    d031 = load_case(cases_dir / "D031_mode_accesspoint_associateddevice.yaml")
    d031_commands = "\n".join(str(step.get("command", "")) for step in d031["steps"])
    d031_links = {link["band"] for link in d031["topology"]["links"]}
    assert d031_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d031_commands
    assert "wl -i wl2 assoclist" in d031_commands
    assert any(
        criterion["field"] == "result_5g.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d031["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "doesn't exist in odl"
        for criterion in d031["pass_criteria"]
    )
    assert d031["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d031["results_reference"]["v4.0.3"]["2.4g"] == "Not Supported"

    d032 = load_case(cases_dir / "D032_mugroupid.yaml")
    d032_commands = "\n".join(str(step.get("command", "")) for step in d032["steps"])
    d032_links = {link["band"] for link in d032["topology"]["links"]}
    assert d032_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d032_commands
    assert "wl -i wl2 assoclist" in d032_commands
    assert any(
        criterion["field"] == "result_5g.MUGroupId"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d032["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_24g.AssocMac24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2c:59:17:00:04:97"
        for criterion in d032["pass_criteria"]
    )
    assert d032["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d032["results_reference"]["v4.0.3"]["2.4g"] == "Not Supported"


def test_pending_not_supported_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d031 = load_case(cases_dir / "D031_mode_accesspoint_associateddevice.yaml")
    d031_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": '[\n  {\n    "error": 4,\n    "message": "mode doesn\'t exist in odl"\n  }\n]\n',
                "timing": 0.01,
            },
            "step4_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "timing": 0.01,
            },
            "step5_24g": {
                "success": True,
                "output": '[\n  {\n    "error": 4,\n    "message": "mode doesn\'t exist in odl"\n  }\n]\n',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d031, d031_results) is True

    d031_fail_results = {
        "steps": {
            **d031_results["steps"],
            "step5_24g": {
                "success": True,
                "output": '[\n  {\n    "error": 7,\n    "message": "unexpected error"\n  }\n]\n',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d031, d031_fail_results) is False

    d032 = load_case(cases_dir / "D032_mugroupid.yaml")
    d032_results = {
        "steps": {
            "step1_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_5g": {
                "success": True,
                "output": '[\n  {\n    "WiFi.AccessPoint.1.AssociatedDevice.1.MUGroupId": 0\n  }\n]\n',
                "timing": 0.01,
            },
            "step4_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "timing": 0.01,
            },
            "step5_24g": {
                "success": True,
                "output": '[\n  {\n    "WiFi.AccessPoint.5.AssociatedDevice.1.MUGroupId": 0\n  }\n]\n',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d032, d032_results) is True

    d032_fail_results = {
        "steps": {
            **d032_results["steps"],
            "step2_5g": {
                "success": True,
                "output": '[\n  {\n    "WiFi.AccessPoint.1.AssociatedDevice.1.MUGroupId": 1\n  }\n]\n',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d032, d032_fail_results) is False


def test_pending_mu_stub_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D033-mumimotxpktscount",
        "wifi-llapi-D034-mumimotxpktspercentage",
        "wifi-llapi-D035-muuserpositionid",
    }.issubset(discoverable_ids)

    mu_cases = {
        "D033_mumimotxpktscount.yaml": ("MUMimoTxPktsCount", "wifi-llapi-D033-mumimotxpktscount", 33),
        "D034_mumimotxpktspercentage.yaml": ("MUMimoTxPktsPercentage", "wifi-llapi-D034-mumimotxpktspercentage", 34),
        "D035_muuserpositionid.yaml": ("MUUserPositionId", "wifi-llapi-D035-muuserpositionid", 35),
    }
    for filename, (api_name, case_id, source_row) in mu_cases.items():
        case_data = load_case(cases_dir / filename)
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        links = {link["band"] for link in case_data["topology"]["links"]}
        assert case_data["id"] == case_id
        assert case_data["source"]["row"] == source_row
        assert links == {"5g", "2.4g"}
        assert "wl -i wl0 assoclist" in commands
        assert "wl -i wl2 assoclist" in commands
        assert f'WiFi.AccessPoint.1.AssociatedDevice.1.{api_name}?' in commands
        assert f'WiFi.AccessPoint.5.AssociatedDevice.1.{api_name}?' in commands
        assert case_data["llapi_support"] == "Not Supported"
        assert case_data["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
        assert case_data["results_reference"]["v4.0.3"]["6g"] == "Skip"
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "Not Supported"
        assert any(
            criterion["field"] == "assoc_5g.AssocMac5g"
            and criterion["operator"] == "equals"
            and criterion["value"] == "2c:59:17:00:04:85"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == f"result_5g.{api_name}"
            and criterion["operator"] == "equals"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "assoc_24g.AssocMac24g"
            and criterion["operator"] == "equals"
            and criterion["value"] == "2c:59:17:00:04:97"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == f"result_24g.{api_name}"
            and criterion["operator"] == "equals"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )


def test_pending_mu_stub_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    mu_cases = {
        "D033_mumimotxpktscount.yaml": "MUMimoTxPktsCount",
        "D034_mumimotxpktspercentage.yaml": "MUMimoTxPktsPercentage",
        "D035_muuserpositionid.yaml": "MUUserPositionId",
    }

    for filename, api_name in mu_cases.items():
        case_data = load_case(cases_dir / filename)
        pass_results = {
            "steps": {
                "step1_5g_assoc": {
                    "success": True,
                    "output": "AssocMac5g=2c:59:17:00:04:85",
                    "timing": 0.01,
                },
                "step2_5g": {
                    "success": True,
                    "output": f'[\n  {{\n    "WiFi.AccessPoint.1.AssociatedDevice.1.{api_name}": 0\n  }}\n]\n',
                    "timing": 0.01,
                },
                "step4_24g_assoc": {
                    "success": True,
                    "output": "AssocMac24g=2c:59:17:00:04:97",
                    "timing": 0.01,
                },
                "step5_24g": {
                    "success": True,
                    "output": f'[\n  {{\n    "WiFi.AccessPoint.5.AssociatedDevice.1.{api_name}": 0\n  }}\n]\n',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, pass_results) is True

        fail_results = {
            "steps": {
                **pass_results["steps"],
                "step5_24g": {
                    "success": True,
                    "output": f'[\n  {{\n    "WiFi.AccessPoint.5.AssociatedDevice.1.{api_name}": 1\n  }}\n]\n',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, fail_results) is False


def test_pending_failure_shaped_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D036-noise-accesspoint-associateddevice",
        "wifi-llapi-D038-powersave",
        "wifi-llapi-D042-rxmulticastpacketcount",
    }.issubset(discoverable_ids)

    failure_cases = {
        "D036_noise_accesspoint_associateddevice.yaml": {
            "id": "wifi-llapi-D036-noise-accesspoint-associateddevice",
            "row": 36,
            "api": "Noise",
            "driver_token": "DriverNoise=",
            "driver_field": "driver_noise.DriverNoise",
            "driver_operator": "<",
            "driver_value": "0",
        },
        "D038_powersave.yaml": {
            "id": "wifi-llapi-D038-powersave",
            "row": 38,
            "api": "PowerSave",
            "driver_token": "DriverPowerSaveFlags=",
            "driver_field": "driver_flags.DriverPowerSaveFlags",
            "driver_operator": "contains",
            "driver_value": "APSD_BE",
        },
        "D042_rxmulticastpacketcount.yaml": {
            "id": "wifi-llapi-D042-rxmulticastpacketcount",
            "row": 42,
            "api": "RxMulticastPacketCount",
            "driver_token": "DriverRxMulticastPacketCount=",
            "driver_field": "driver_counter.DriverRxMulticastPacketCount",
            "driver_operator": ">",
            "driver_value": "0",
        },
    }

    for filename, meta in failure_cases.items():
        raw_case = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        case_data = load_case(cases_dir / filename)
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        links = {link["band"] for link in case_data["topology"]["links"]}

        assert "aliases" not in raw_case
        assert case_data["id"] == meta["id"]
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["source"]["baseline"] == "BCM v4.0.3"
        assert case_data["bands"] == ["5g"]
        assert links == {"5g"}
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}?"'
        assert "MACAddress?" in commands
        assert "DriverAssocMac=" in commands
        assert meta["driver_token"] in commands
        assert any(
            criterion["field"] == f'result.{meta["api"]}'
            and criterion["operator"] == "equals"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == f'{meta["driver_field"].rsplit(".", 1)[0]}.DriverAssocMac'
            and criterion["operator"] == "equals"
            and criterion["reference"] == "assoc_entry.MACAddress"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == meta["driver_field"]
            and criterion["operator"] == meta["driver_operator"]
            and str(criterion["value"]) == meta["driver_value"]
            for criterion in case_data["pass_criteria"]
        )
        if filename == "D042_rxmulticastpacketcount.yaml":
            assert any(step.get("target") == "STA" for step in case_data["steps"])
            assert "ProbeTxPackets=" in commands
            assert any(
                criterion["field"] == "probe.ProbeTxPackets"
                and criterion["operator"] == ">"
                and str(criterion["value"]) == "0"
                for criterion in case_data["pass_criteria"]
            )
        assert case_data["results_reference"]["v4.0.3"]["5g"] == "Fail"
        assert case_data["results_reference"]["v4.0.3"]["6g"] == "N/A"
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_pending_failure_shaped_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d036 = load_case(cases_dir / "D036_noise_accesspoint_associateddevice.yaml")
    d036_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.Noise=0",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverNoise=-85",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d036, d036_results) is True

    d036_fail_results = {
        "steps": {
            **d036_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverNoise=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d036, d036_fail_results) is False

    d036_mismatch_results = {
        "steps": {
            **d036_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverNoise=-85",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d036, d036_mismatch_results) is False

    d038 = load_case(cases_dir / "D038_powersave.yaml")
    d038_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.PowerSave=0",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverPowerSaveFlags=APSD_BE,APSD_BK,APSD_VI,APSD_VO",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d038, d038_results) is True

    d038_fail_results = {
        "steps": {
            **d038_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverPowerSaveFlags=WME",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d038, d038_fail_results) is False

    d038_mismatch_results = {
        "steps": {
            **d038_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverPowerSaveFlags=APSD_BE,APSD_BK,APSD_VI,APSD_VO",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d038, d038_mismatch_results) is False

    d042 = load_case(cases_dir / "D042_rxmulticastpacketcount.yaml")
    d042_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "5 packets transmitted, 0 received, 100% packet loss, time 4103ms\nProbeTxPackets=5",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.RxMulticastPacketCount=0",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverRxMulticastPacketCount=10",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d042, d042_results) is True

    d042_fail_results = {
        "steps": {
            **d042_results["steps"],
            "step2": {
                "success": True,
                "output": "",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverRxMulticastPacketCount=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d042, d042_fail_results) is False

    d042_mismatch_results = {
        "steps": {
            **d042_results["steps"],
            "step4": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverRxMulticastPacketCount=10",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d042, d042_mismatch_results) is False

def test_pending_counter_stub_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D039-retransmissions",
        "wifi-llapi-D040-rx-retransmissions",
        "wifi-llapi-D044-rxunicastpacketcount",
    }.issubset(discoverable_ids)

    counter_cases = {
        "D039_retransmissions.yaml": {
            "id": "wifi-llapi-D039-retransmissions",
            "row": 39,
            "api": "Retransmissions",
            "driver_token": "DriverRetransmissions=",
            "driver_field": "driver_counter.DriverRetransmissions",
        },
        "D040_rx_retransmissions.yaml": {
            "id": "wifi-llapi-D040-rx-retransmissions",
            "row": 40,
            "api": "Rx_Retransmissions",
            "driver_token": "DriverRxRetransmissions=",
            "driver_field": "driver_counter.DriverRxRetransmissions",
        },
        "D044_rxunicastpacketcount.yaml": {
            "id": "wifi-llapi-D044-rxunicastpacketcount",
            "row": 44,
            "api": "RxUnicastPacketCount",
            "driver_token": "DriverRxUnicastPacketCount=",
            "driver_field": "driver_counter.DriverRxUnicastPacketCount",
        },
    }

    for filename, meta in counter_cases.items():
        raw_case = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        case_data = load_case(cases_dir / filename)
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        links = {link["band"] for link in case_data["topology"]["links"]}

        assert "aliases" not in raw_case
        assert case_data["id"] == meta["id"]
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["source"]["baseline"] == "BCM v4.0.3"
        assert case_data["bands"] == ["5g"]
        assert links == {"5g"}
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}?"'
        assert "MACAddress?" in commands
        assert "DriverAssocMac=" in commands
        assert meta["driver_token"] in commands
        assert any(
            criterion["field"] == f'result.{meta["api"]}'
            and criterion["operator"] == "equals"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "driver_counter.DriverAssocMac"
            and criterion["operator"] == "equals"
            and criterion["reference"] == "assoc_entry.MACAddress"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == meta["driver_field"]
            and criterion["operator"] == ">"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert case_data["results_reference"]["v4.0.3"]["5g"] == "Fail"
        assert case_data["results_reference"]["v4.0.3"]["6g"] == "N/A"
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_pending_counter_stub_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    counter_cases = {
        "D039_retransmissions.yaml": {
            "api": "Retransmissions",
            "driver_output": "DriverRetransmissions=65",
            "driver_fail_output": "DriverRetransmissions=0",
        },
        "D040_rx_retransmissions.yaml": {
            "api": "Rx_Retransmissions",
            "driver_output": "DriverRxRetransmissions=21",
            "driver_fail_output": "DriverRxRetransmissions=0",
        },
        "D044_rxunicastpacketcount.yaml": {
            "api": "RxUnicastPacketCount",
            "driver_output": "DriverRxUnicastPacketCount=114",
            "driver_fail_output": "DriverRxUnicastPacketCount=0",
        },
    }

    for filename, meta in counter_cases.items():
        case_data = load_case(cases_dir / filename)
        pass_results = {
            "steps": {
                "step1": {
                    "success": True,
                    "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    "timing": 0.01,
                },
                "step2": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=0',
                    "timing": 0.01,
                },
                "step3": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_output"]}',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, pass_results) is True

        fail_results = {
            "steps": {
                **pass_results["steps"],
                "step3": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_fail_output"]}',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, fail_results) is False

        mismatch_results = {
            "steps": {
                **pass_results["steps"],
                "step3": {
                    "success": True,
                    "output": f'DriverAssocMac=AA:AA:AA:AA:AA:AA\n{meta["driver_output"]}',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, mismatch_results) is False


def test_pending_counter_pass_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D041-rxbytes",
        "wifi-llapi-D043-rxpacketcount",
        "wifi-llapi-D058-txpacketcount",
        "wifi-llapi-D061-uplinkbandwidth",
    }.issubset(discoverable_ids)

    pass_cases = {
        "D041_rxbytes.yaml": {
            "id": "wifi-llapi-D041-rxbytes",
            "row": 41,
            "api": "RxBytes",
            "driver_token": "DriverRxBytes=",
            "driver_field": "driver_counter.DriverRxBytes",
        },
        "D043_rxpacketcount.yaml": {
            "id": "wifi-llapi-D043-rxpacketcount",
            "row": 43,
            "api": "RxPacketCount",
            "driver_token": "DriverRxPacketCount=",
            "driver_field": "driver_counter.DriverRxPacketCount",
        },
        "D058_txpacketcount.yaml": {
            "id": "wifi-llapi-D058-txpacketcount",
            "row": 58,
            "api": "TxPacketCount",
            "driver_token": "DriverTxPacketCount=",
            "driver_field": "driver_counter.DriverTxPacketCount",
        },
        "D061_uplinkbandwidth.yaml": {
            "id": "wifi-llapi-D061-uplinkbandwidth",
            "row": 61,
            "api": "UplinkBandwidth",
            "driver_token": "DriverUplinkBandwidth=",
            "driver_field": "driver_counter.DriverUplinkBandwidth",
        },
    }

    for filename, meta in pass_cases.items():
        raw_case = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        case_data = load_case(cases_dir / filename)
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        links = {link["band"] for link in case_data["topology"]["links"]}

        assert "aliases" not in raw_case
        assert case_data["id"] == meta["id"]
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["source"]["baseline"] == "BCM v4.0.3"
        assert case_data["bands"] == ["5g"]
        assert links == {"5g"}
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}?"'
        assert "MACAddress?" in commands
        assert "DriverAssocMac=" in commands
        assert meta["driver_token"] in commands
        if filename == "D061_uplinkbandwidth.yaml":
            assert "sed -n '/rx nrate/,$p'" in commands
            assert "head -n 1" in commands
        assert any(
            criterion["field"] == f'result.{meta["api"]}'
            and criterion["operator"] == "regex"
            and criterion["value"] == "^[0-9]+$"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == f'result.{meta["api"]}'
            and criterion["operator"] == ">"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "driver_counter.DriverAssocMac"
            and criterion["operator"] == "equals"
            and criterion["reference"] == "assoc_entry.MACAddress"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == meta["driver_field"]
            and criterion["operator"] == ">"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == f'result.{meta["api"]}'
            and criterion["operator"] == "equals"
            and criterion["reference"] == meta["driver_field"]
            for criterion in case_data["pass_criteria"]
        )
        assert case_data["results_reference"]["v4.0.3"]["5g"] == "Pass"
        assert case_data["results_reference"]["v4.0.3"]["6g"] == "N/A"
        assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_pending_counter_pass_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    pass_cases = {
        "D041_rxbytes.yaml": {
            "api": "RxBytes",
            "driver_output": "DriverRxBytes=723",
            "driver_fail_output": "DriverRxBytes=0",
        },
        "D043_rxpacketcount.yaml": {
            "api": "RxPacketCount",
            "driver_output": "DriverRxPacketCount=7",
            "driver_fail_output": "DriverRxPacketCount=0",
        },
        "D058_txpacketcount.yaml": {
            "api": "TxPacketCount",
            "driver_output": "DriverTxPacketCount=12956",
            "driver_fail_output": "DriverTxPacketCount=0",
        },
        "D061_uplinkbandwidth.yaml": {
            "api": "UplinkBandwidth",
            "driver_output": "DriverUplinkBandwidth=20",
            "driver_fail_output": "DriverUplinkBandwidth=0",
        },
    }

    for filename, meta in pass_cases.items():
        case_data = load_case(cases_dir / filename)
        pass_results = {
            "steps": {
                "step1": {
                    "success": True,
                    "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    "timing": 0.01,
                },
                "step2": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}={meta["driver_output"].split("=", 1)[1]}',
                    "timing": 0.01,
                },
                "step3": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_output"]}',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, pass_results) is True

        fail_results = {
            "steps": {
                **pass_results["steps"],
                "step3": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_fail_output"]}',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, fail_results) is False

        zero_results = {
            "steps": {
                **pass_results["steps"],
                "step2": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=0',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, zero_results) is False

        mismatch_results = {
            "steps": {
                **pass_results["steps"],
                "step3": {
                    "success": True,
                    "output": f'DriverAssocMac=AA:AA:AA:AA:AA:AA\n{meta["driver_output"]}',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, mismatch_results) is False


def test_d062_uplinkmcs_uses_zero_valid_same_sta_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    raw_case = yaml.safe_load((cases_dir / "D062_uplinkmcs.yaml").read_text(encoding="utf-8"))
    case_data = load_case(cases_dir / "D062_uplinkmcs.yaml")
    commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
    links = {link["band"] for link in case_data["topology"]["links"]}

    assert "wifi-llapi-D062-uplinkmcs" in {case["id"] for case in plugin.discover_cases()}
    assert "aliases" not in raw_case
    assert case_data["id"] == "wifi-llapi-D062-uplinkmcs"
    assert case_data["source"]["row"] == 62
    assert case_data["source"]["baseline"] == "BCM v4.0.3"
    assert case_data["bands"] == ["5g"]
    assert links == {"5g"}
    assert case_data["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.UplinkMCS?"'
    assert len(case_data["steps"]) == 4
    assert "MACAddress?" in commands
    assert "ping -I wl0 -c 8 -W 1 192.168.1.1" in commands
    assert "AssocMacAfterTrigger=" in commands
    assert "DriverAssocMac=" in commands
    assert "DriverUplinkMCS=" in commands
    assert "sed -n '/rx nrate/{n;s/.*mcs \\([0-9][0-9]*\\).*/DriverUplinkMCS=\\1/p;}'" in commands
    assert any(
        criterion["field"] == "result.AssocMacAfterTrigger"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9]+$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "result.AssocMacAfterTrigger"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.DriverUplinkMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9]+$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkMCS"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "result.DriverUplinkMCS"
        for criterion in case_data["pass_criteria"]
    )
    assert not any(
        criterion["field"] == "result.UplinkMCS" and criterion["operator"] == ">"
        for criterion in case_data["pass_criteria"]
    )
    assert case_data["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert case_data["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d062_uplinkmcs_evaluate_accepts_zero_when_driver_matches():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D062_uplinkmcs.yaml")

    pass_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "192.168.1.1 dev wl0 src 192.168.1.3 uid 0",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "8 packets transmitted, 8 received, 0% packet loss",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "UplinkMCS=0\nAssocMacAfterTrigger=2C:59:17:00:04:85\nDriverAssocMac=2C:59:17:00:04:85\nDriverUplinkMCS=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, pass_results) is True

    fail_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkMCS=0\nAssocMacAfterTrigger=2C:59:17:00:04:85\nDriverAssocMac=2C:59:17:00:04:85\nDriverUplinkMCS=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, fail_results) is False

    mismatch_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkMCS=0\nAssocMacAfterTrigger=AA:AA:AA:AA:AA:AA\nDriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverUplinkMCS=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, mismatch_results) is False


def test_d063_uplinkshortguard_uses_same_sta_gi_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    raw_case = yaml.safe_load((cases_dir / "D063_uplinkshortguard.yaml").read_text(encoding="utf-8"))
    case_data = load_case(cases_dir / "D063_uplinkshortguard.yaml")
    commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
    links = {link["band"] for link in case_data["topology"]["links"]}

    assert "wifi-llapi-D063-uplinkshortguard" in {case["id"] for case in plugin.discover_cases()}
    assert "aliases" not in raw_case
    assert case_data["id"] == "wifi-llapi-D063-uplinkshortguard"
    assert case_data["source"]["row"] == 63
    assert case_data["source"]["baseline"] == "BCM v4.0.3"
    assert case_data["bands"] == ["5g"]
    assert links == {"5g"}
    assert case_data["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.UplinkShortGuard?"'
    assert len(case_data["steps"]) == 5
    assert "MACAddress?" in commands
    assert "ping -I wl0 -c 8 -W 1 192.168.1.1" in commands
    assert "AssocMacAfterTrigger=" in commands
    assert "DriverAssocMac=" in commands
    assert "DriverUplinkShortGuardGI=" in commands
    assert "DriverUplinkShortGuard=" in commands
    assert 'case "$GI" in 0.4us|0.8us|1.6us) echo DriverUplinkShortGuard=1 ;; 3.2us) echo DriverUplinkShortGuard=0 ;; *) echo DriverUplinkShortGuard=UNKNOWN_GI:$GI ;; esac' in commands
    assert any(
        criterion["field"] == "result.AssocMacAfterTrigger"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkShortGuard"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-1]$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_counter.DriverUplinkShortGuardGI"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9.]+us$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_counter.DriverUplinkShortGuard"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-1]$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkShortGuard"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_counter.DriverUplinkShortGuard"
        for criterion in case_data["pass_criteria"]
    )
    assert not any(
        criterion["field"] == "result.UplinkShortGuard" and criterion["operator"] == "contains"
        for criterion in case_data["pass_criteria"]
    )
    assert case_data["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert case_data["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert case_data["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d063_uplinkshortguard_evaluate_uses_driver_gi_mapping():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D063_uplinkshortguard.yaml")

    pass_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "192.168.1.1 dev wl0 src 192.168.1.3 uid 0",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "8 packets transmitted, 8 received, 0% packet loss",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "UplinkShortGuard=1\nAssocMacAfterTrigger=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUplinkShortGuardGI=1.6us\nDriverUplinkShortGuard=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, pass_results) is True

    zero_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkShortGuard=0\nAssocMacAfterTrigger=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUplinkShortGuardGI=3.2us\nDriverUplinkShortGuard=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, zero_results) is True

    fail_results = {
        "steps": {
            **pass_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUplinkShortGuardGI=3.2us\nDriverUplinkShortGuard=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, fail_results) is False

    mismatch_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkShortGuard=1\nAssocMacAfterTrigger=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverUplinkShortGuardGI=1.6us\nDriverUplinkShortGuard=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, mismatch_results) is False

    unmapped_gi_results = {
        "steps": {
            **pass_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUplinkShortGuardGI=6.4us\nDriverUplinkShortGuard=UNKNOWN_GI:6.4us",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, unmapped_gi_results) is False


def test_pending_d046_d051_d060_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D046-signalnoiseratio",
        "wifi-llapi-D051-supportedmcs",
        "wifi-llapi-D060-uniibandscapabilities",
    }.issubset(discoverable_ids)

    d046_raw = yaml.safe_load((cases_dir / "D046_signalnoiseratio.yaml").read_text(encoding="utf-8"))
    d046 = load_case(cases_dir / "D046_signalnoiseratio.yaml")
    d046_commands = "\n".join(str(step.get("command", "")) for step in d046["steps"])
    assert "aliases" not in d046_raw
    assert d046["source"]["row"] == 46
    assert d046["source"]["baseline"] == "BCM v4.0.3"
    assert d046["bands"] == ["5g"]
    assert "DriverSignal=" in d046_commands
    assert "DriverNoise=" in d046_commands
    assert "DriverSignalNoiseRatio=" in d046_commands
    assert any(
        criterion["field"] == "result.SignalNoiseRatio"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9]+$"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalNoiseRatio"
        and criterion["operator"] == ">="
        and criterion["reference"] == "driver_snr.DriverSignalNoiseRatioMin"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalNoiseRatio"
        and criterion["operator"] == "<="
        and criterion["reference"] == "driver_snr.DriverSignalNoiseRatioMax"
        for criterion in d046["pass_criteria"]
    )
    assert d046["results_reference"]["v4.0.3"]["5g"] == "Pass"

    d051_raw = yaml.safe_load((cases_dir / "D051_supportedmcs.yaml").read_text(encoding="utf-8"))
    d051 = load_case(cases_dir / "D051_supportedmcs.yaml")
    d051_commands = "\n".join(str(step.get("command", "")) for step in d051["steps"])
    assert "aliases" not in d051_raw
    assert d051["source"]["row"] == 51
    assert d051["source"]["baseline"] == "BCM v4.0.3"
    assert d051["bands"] == ["5g"]
    assert "DriverHeCapsPresent=1" in d051_commands
    assert "DriverMCSSetPresent=1" in d051_commands
    assert "DriverHeSetPresent=1" in d051_commands
    assert any(
        criterion["field"] == "result.SupportedMCS"
        and criterion["operator"] == "empty"
        for criterion in d051["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverMCSSetPresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d051["pass_criteria"]
    )
    assert d051["results_reference"]["v4.0.3"]["5g"] == "Fail"

    d060_raw = yaml.safe_load(
        (cases_dir / "D060_uniibandscapabilities.yaml").read_text(encoding="utf-8")
    )
    d060 = load_case(cases_dir / "D060_uniibandscapabilities.yaml")
    d060_commands = "\n".join(str(step.get("command", "")) for step in d060["steps"])
    assert "aliases" not in d060_raw
    assert d060["source"]["row"] == 60
    assert d060["source"]["baseline"] == "BCM v4.0.3"
    assert d060["bands"] == ["5g"]
    assert "DriverUNIIBandsCapabilities=" in d060_commands
    assert "iw dev wl0 info" in d060_commands
    assert "tr '[:lower:]' '[:upper:]'" in d060_commands
    assert any(
        criterion["field"] == "driver_capability.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d060["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverUNIIBandsCapabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "U-NII-1,U-NII-2A,U-NII-2C,U-NII-3"
        for criterion in d060["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UNIIBandsCapabilities"
        and criterion["operator"] == "contains"
        and criterion["reference"] == "driver_capability.DriverUNIIBandsCapabilities"
        for criterion in d060["pass_criteria"]
    )
    assert d060["results_reference"]["v4.0.3"]["5g"] == "Pass"


def test_pending_d046_d051_d060_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d046 = load_case(cases_dir / "D046_signalnoiseratio.yaml")
    d046_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "MACAddress=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.SignalNoiseRatio=63",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignal=-36\nDriverNoise=-99\nDriverSignalNoiseRatio=63\nDriverSignalNoiseRatioMin=61\nDriverSignalNoiseRatioMax=65",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d046, d046_results) is True

    d046_fail_results = {
        "steps": {
            **d046_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignal=-32\nDriverNoise=-99\nDriverSignalNoiseRatio=67\nDriverSignalNoiseRatioMin=65\nDriverSignalNoiseRatioMax=69",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d046, d046_fail_results) is False

    d051 = load_case(cases_dir / "D051_supportedmcs.yaml")
    d051_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.SupportedMCS=""',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d051, d051_results) is True

    d051_fail_results = {
        "steps": {
            **d051_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d051, d051_fail_results) is False

    d060 = load_case(cases_dir / "D060_uniibandscapabilities.yaml")
    d060_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.UNIIBandsCapabilities="U-NII-1,U-NII-2A,U-NII-2C,U-NII-3,U-NII-4"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUNIIBandsCapabilities=U-NII-1,U-NII-2A,U-NII-2C,U-NII-3",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d060, d060_results) is True

    d060_fail_results = {
        "steps": {
            **d060_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUNIIBandsCapabilities=U-NII-1,U-NII-2A,U-NII-2C",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d060, d060_fail_results) is False


def test_pending_security_and_signal_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D045-securitymodeenabled",
        "wifi-llapi-D047-signalstrength-accesspoint-associateddevice",
    }.issubset(discoverable_ids)

    d045_raw = yaml.safe_load(
        (cases_dir / "D045_securitymodeenabled.yaml").read_text(encoding="utf-8")
    )
    d045 = load_case(cases_dir / "D045_securitymodeenabled.yaml")
    d045_commands = "\n".join(str(step.get("command", "")) for step in d045["steps"])
    d045_links = {link["band"] for link in d045["topology"]["links"]}

    assert "aliases" not in d045_raw
    assert d045["id"] == "wifi-llapi-D045-securitymodeenabled"
    assert d045["source"]["row"] == 45
    assert d045["source"]["baseline"] == "BCM v4.0.3"
    assert d045["bands"] == ["5g"]
    assert d045_links == {"5g"}
    assert (
        d045["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SecurityModeEnabled?"'
    )
    assert "MACAddress?" in d045_commands
    assert "DriverAssocMac=" in d045_commands
    assert "DriverSecurityModeEnabled=" in d045_commands
    assert any(
        criterion["field"] == "driver_security.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_security.DriverSecurityModeEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "WPA3-Personal"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SecurityModeEnabled"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_security.DriverSecurityModeEnabled"
        for criterion in d045["pass_criteria"]
    )
    assert d045["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert d045["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d045["results_reference"]["v4.0.3"]["2.4g"] == "N/A"

    d047_raw = yaml.safe_load(
        (cases_dir / "D047_signalstrength_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d047 = load_case(cases_dir / "D047_signalstrength_accesspoint_associateddevice.yaml")
    d047_commands = "\n".join(str(step.get("command", "")) for step in d047["steps"])
    d047_links = {link["band"] for link in d047["topology"]["links"]}

    assert "aliases" not in d047_raw
    assert d047["id"] == "wifi-llapi-D047-signalstrength-accesspoint-associateddevice"
    assert d047["source"]["row"] == 47
    assert d047["source"]["baseline"] == "BCM v4.0.3"
    assert d047["bands"] == ["5g"]
    assert d047_links == {"5g"}
    assert (
        d047["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength?"'
    )
    assert "MACAddress?" in d047_commands
    assert "DriverAssocMac=" in d047_commands
    assert "DriverSignalStrength=" in d047_commands
    assert "DriverSignalStrengthMin=" in d047_commands
    assert "DriverSignalStrengthMax=" in d047_commands
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-[0-9]+$"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverSignalStrength"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-[0-9]+$"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverSignalStrength"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == ">="
        and criterion["reference"] == "driver_signal.DriverSignalStrengthMin"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == "<="
        and criterion["reference"] == "driver_signal.DriverSignalStrengthMax"
        for criterion in d047["pass_criteria"]
    )
    assert d047["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert d047["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d047["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_pending_security_and_signal_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d045 = load_case(cases_dir / "D045_securitymodeenabled.yaml")
    d045_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.SecurityModeEnabled="WPA3-Personal"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSecurityModeEnabled=WPA3-Personal",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_results) is True

    d045_fail_results = {
        "steps": {
            **d045_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSecurityModeEnabled=WPA2-Personal",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_fail_results) is False

    d045_mismatch_results = {
        "steps": {
            **d045_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverSecurityModeEnabled=WPA3-Personal",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_mismatch_results) is False

    d047 = load_case(cases_dir / "D047_signalstrength_accesspoint_associateddevice.yaml")
    d047_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength=-36",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrength=-36\nDriverSignalStrengthMin=-38\nDriverSignalStrengthMax=-34",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_results) is True

    d047_fail_results = {
        "steps": {
            **d047_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrength=-32\nDriverSignalStrengthMin=-34\nDriverSignalStrengthMax=-30",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_fail_results) is False

    d047_zero_results = {
        "steps": {
            **d047_results["steps"],
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_zero_results) is False

    d047_mismatch_results = {
        "steps": {
            **d047_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverSignalStrength=-36\nDriverSignalStrengthMin=-38\nDriverSignalStrengthMax=-34",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_mismatch_results) is False

    d047_missing_driver_value_results = {
        "steps": {
            **d047_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrengthMin=-38\nDriverSignalStrengthMax=-34",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_missing_driver_value_results) is False


def test_d048_signalstrengthbychain_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D048-signalstrengthbychain" in discoverable_ids

    d048_raw = yaml.safe_load(
        (cases_dir / "D048_signalstrengthbychain.yaml").read_text(encoding="utf-8")
    )
    d048 = load_case(cases_dir / "D048_signalstrengthbychain.yaml")
    d048_commands = "\n".join(str(step.get("command", "")) for step in d048["steps"])
    d048_links = {link["band"] for link in d048["topology"]["links"]}

    assert "aliases" not in d048_raw
    assert d048["id"] == "wifi-llapi-D048-signalstrengthbychain"
    assert d048["source"]["row"] == 48
    assert d048["source"]["baseline"] == "BCM v4.0.3"
    assert d048["bands"] == ["5g"]
    assert d048_links == {"5g"}
    assert (
        d048["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain?"'
    )
    assert "cat /sys/class/net/wl0/address" in d048_commands
    assert "MACAddress?" in d048_commands
    assert "DriverAssocMac=" in d048_commands
    assert "DriverSignalStrengthByChain=" in d048_commands
    assert "per antenna average rssi of rx data frames" in d048_commands
    assert "paste -sd, -" in d048_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0$"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0$"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrengthByChain"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_signal.DriverSignalStrengthByChain"
        for criterion in d048["pass_criteria"]
    )
    assert d048["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert d048["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d048["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d048_signalstrengthbychain_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d048 = load_case(cases_dir / "D048_signalstrengthbychain.yaml")

    d048_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain="-28.0,-33.0,-36.0,-32.0"',
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrengthByChain=-28.0,-33.0,-36.0,-32.0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_results) is True

    d048_fail_results = {
        "steps": {
            **d048_results["steps"],
            "step4": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrengthByChain=-28.0,-33.0,-35.0,-32.0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_fail_results) is False

    d048_scalar_results = {
        "steps": {
            **d048_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain="-33.0"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_scalar_results) is False

    d048_mismatch_results = {
        "steps": {
            **d048_results["steps"],
            "step4": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverSignalStrengthByChain=-28.0,-33.0,-36.0,-32.0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_mismatch_results) is False

    d048_wrong_sta_results = {
        "steps": {
            **d048_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_wrong_sta_results) is False


def test_d049_supportedhe160mcs_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D049-supportedhe160mcs" in discoverable_ids

    d049_raw = yaml.safe_load(
        (cases_dir / "D049_supportedhe160mcs.yaml").read_text(encoding="utf-8")
    )
    d049 = load_case(cases_dir / "D049_supportedhe160mcs.yaml")
    d049_commands = "\n".join(str(step.get("command", "")) for step in d049["steps"])
    d049_links = {link["band"] for link in d049["topology"]["links"]}

    assert "aliases" not in d049_raw
    assert d049["id"] == "wifi-llapi-D049-supportedhe160mcs"
    assert d049["source"]["row"] == 49
    assert d049["source"]["baseline"] == "BCM v4.0.3"
    assert d049["llapi_support"] == "Not Supported"
    assert d049["bands"] == ["5g"]
    assert d049_links == {"5g"}
    assert (
        d049["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS?"'
    )
    assert "cat /sys/class/net/wl0/address" in d049_commands
    assert "MACAddress?" in d049_commands
    assert 'SupportedHe160MCS?" 2>&1' in d049_commands
    assert "error=" in d049_commands
    assert "message=" in d049_commands
    assert "DriverRxSupportedHe160MCS=" in d049_commands
    assert "DriverTxSupportedHe160MCS=" in d049_commands
    assert "DriverHeCapsPresent=1" in d049_commands
    assert "DriverMCSSetPresent=1" in d049_commands
    assert "DriverHeSetPresent=1" in d049_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "parameter not found"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.SiblingAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverRxSupportedHe160MCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverHeSetPresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d049["pass_criteria"]
    )
    assert d049["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d049["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d049["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d049_supportedhe160mcs_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d049 = load_case(cases_dir / "D049_supportedhe160mcs.yaml")

    d049_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "ERROR: get WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS failed (4 - parameter not found)\nerror=4\nmessage=parameter not found",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedHe160MCS=11,11,11,11\nDriverTxSupportedHe160MCS=11,11,11,11",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d049, d049_results) is True

    d049_wrong_error_results = {
        "steps": {
            **d049_results["steps"],
            "step3": {
                "success": True,
                "output": "error=7\nmessage=unexpected error",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d049, d049_wrong_error_results) is False

    d049_missing_sibling_results = {
        "steps": {
            **d049_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverTxSupportedHe160MCS=11,11,11,11",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d049, d049_missing_sibling_results) is False

    d049_wrong_sta_results = {
        "steps": {
            **d049_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d049, d049_wrong_sta_results) is False


def test_d050_supportedhemcs_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D050-supportedhemcs" in discoverable_ids

    d050_raw = yaml.safe_load(
        (cases_dir / "D050_supportedhemcs.yaml").read_text(encoding="utf-8")
    )
    d050 = load_case(cases_dir / "D050_supportedhemcs.yaml")
    d050_commands = "\n".join(str(step.get("command", "")) for step in d050["steps"])
    d050_links = {link["band"] for link in d050["topology"]["links"]}

    assert "aliases" not in d050_raw
    assert d050["id"] == "wifi-llapi-D050-supportedhemcs"
    assert d050["source"]["row"] == 50
    assert d050["source"]["baseline"] == "BCM v4.0.3"
    assert d050["llapi_support"] == "Not Supported"
    assert d050["bands"] == ["5g"]
    assert d050_links == {"5g"}
    assert (
        d050["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHeMCS?"'
    )
    assert "cat /sys/class/net/wl0/address" in d050_commands
    assert "MACAddress?" in d050_commands
    assert 'SupportedHeMCS?" 2>&1' in d050_commands
    assert "error=" in d050_commands
    assert "message=" in d050_commands
    assert "DriverRxSupportedHeMCS=" in d050_commands
    assert "DriverTxSupportedHeMCS=" in d050_commands
    assert "DriverHeCapsPresent=1" in d050_commands
    assert "DriverMCSSetPresent=1" in d050_commands
    assert "DriverHeSetPresent=1" in d050_commands
    assert "DriverHeMcsLinePresent=1" in d050_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "parameter not found"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.SiblingAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverRxSupportedHeMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverTxSupportedHeMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverHeMcsLinePresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d050["pass_criteria"]
    )
    assert d050["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d050["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d050["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d050_supportedhemcs_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d050 = load_case(cases_dir / "D050_supportedhemcs.yaml")

    d050_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "ERROR: get WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHeMCS failed (4 - parameter not found)\nerror=4\nmessage=parameter not found",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedHeMCS=11,11,11,11\nDriverTxSupportedHeMCS=11,11,11,11",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1\nDriverHeMcsLinePresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_results) is True

    d050_wrong_error_results = {
        "steps": {
            **d050_results["steps"],
            "step3": {
                "success": True,
                "output": "error=7\nmessage=unexpected error",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_wrong_error_results) is False

    d050_missing_sibling_results = {
        "steps": {
            **d050_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverTxSupportedHeMCS=11,11,11,11",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_missing_sibling_results) is False

    d050_missing_tx_sibling_results = {
        "steps": {
            **d050_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedHeMCS=11,11,11,11",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_missing_tx_sibling_results) is False

    d050_missing_driver_line_results = {
        "steps": {
            **d050_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_missing_driver_line_results) is False

    d050_wrong_driver_assoc_results = {
        "steps": {
            **d050_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1\nDriverHeMcsLinePresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_wrong_driver_assoc_results) is False

    d050_wrong_sta_results = {
        "steps": {
            **d050_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_wrong_sta_results) is False


def test_d052_supportedvhtmcs_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D052-supportedvhtmcs" in discoverable_ids

    d052_raw = yaml.safe_load(
        (cases_dir / "D052_supportedvhtmcs.yaml").read_text(encoding="utf-8")
    )
    d052 = load_case(cases_dir / "D052_supportedvhtmcs.yaml")
    d052_commands = "\n".join(str(step.get("command", "")) for step in d052["steps"])
    d052_links = {link["band"] for link in d052["topology"]["links"]}

    assert "aliases" not in d052_raw
    assert d052["id"] == "wifi-llapi-D052-supportedvhtmcs"
    assert d052["source"]["row"] == 52
    assert d052["source"]["baseline"] == "BCM v4.0.3"
    assert d052["llapi_support"] == "Not Supported"
    assert d052["bands"] == ["5g"]
    assert d052_links == {"5g"}
    assert (
        d052["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedVhtMCS?"'
    )
    assert "cat /sys/class/net/wl0/address" in d052_commands
    assert "MACAddress?" in d052_commands
    assert 'SupportedVhtMCS?" 2>&1' in d052_commands
    assert "error=" in d052_commands
    assert "message=" in d052_commands
    assert "DriverRxSupportedVhtMCS=" in d052_commands
    assert "DriverTxSupportedVhtMCS=" in d052_commands
    assert "DriverVhtCapsPresent=1" in d052_commands
    assert "DriverMCSSetPresent=1" in d052_commands
    assert "DriverVhtSetPresent=1" in d052_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "parameter not found"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverRxSupportedVhtMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverTxSupportedVhtMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d052["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverVhtSetPresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d052["pass_criteria"]
    )
    assert d052["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d052["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d052["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d052_supportedvhtmcs_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d052 = load_case(cases_dir / "D052_supportedvhtmcs.yaml")

    d052_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "ERROR: get WiFi.AccessPoint.1.AssociatedDevice.1.SupportedVhtMCS failed (4 - parameter not found)\nerror=4\nmessage=parameter not found",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedVhtMCS=9,9,9,9\nDriverTxSupportedVhtMCS=9,9,9,9",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverVhtCapsPresent=1\nDriverMCSSetPresent=1\nDriverVhtSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d052, d052_results) is True

    d052_wrong_error_results = {
        "steps": {
            **d052_results["steps"],
            "step3": {
                "success": True,
                "output": "error=7\nmessage=unexpected error",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d052, d052_wrong_error_results) is False

    d052_missing_rx_sibling_results = {
        "steps": {
            **d052_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverTxSupportedVhtMCS=9,9,9,9",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d052, d052_missing_rx_sibling_results) is False

    d052_missing_tx_sibling_results = {
        "steps": {
            **d052_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedVhtMCS=9,9,9,9",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d052, d052_missing_tx_sibling_results) is False

    d052_wrong_driver_assoc_results = {
        "steps": {
            **d052_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverVhtCapsPresent=1\nDriverMCSSetPresent=1\nDriverVhtSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d052, d052_wrong_driver_assoc_results) is False

    d052_wrong_sta_results = {
        "steps": {
            **d052_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d052, d052_wrong_sta_results) is False


def test_d056_txerrors_uses_same_sta_driver_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D056-txerrors" in discoverable_ids

    d056_raw = yaml.safe_load((cases_dir / "D056_txerrors.yaml").read_text(encoding="utf-8"))
    d056 = load_case(cases_dir / "D056_txerrors.yaml")
    d056_commands = "\n".join(str(step.get("command", "")) for step in d056["steps"])
    d056_links = {link["band"] for link in d056["topology"]["links"]}

    assert "aliases" not in d056_raw
    assert d056["id"] == "wifi-llapi-D056-txerrors"
    assert d056["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d056["source"]["row"] == 56
    assert d056["source"]["baseline"] == "BCM v4.0.3"
    assert d056["llapi_support"] == "Support"
    assert d056["bands"] == ["5g"]
    assert d056_links == {"5g"}
    assert d056["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors?"'
    assert "cat /sys/class/net/wl0/address" in d056_commands
    assert "MACAddress?" in d056_commands
    assert 'TxErrors?"' in d056_commands
    assert "AssocTxErrors=" in d056_commands
    assert "DriverTxPkts=" in d056_commands
    assert "DriverTxErrors=" in d056_commands
    assert "DriverRetries=" in d056_commands
    assert "DriverRetryExhausted=" in d056_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d056["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d056["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxErrors"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+$"
        for criterion in d056["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxErrors"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_snapshot.AssocTxErrors"
        for criterion in d056["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d056["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxErrors"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_capture.DriverTxErrors"
        for criterion in d056["pass_criteria"]
    )
    assert d056["results_reference"]["v4.0.3"]["5g"] == "To be tested"
    assert d056["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d056["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d056_txerrors_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d056 = load_case(cases_dir / "D056_txerrors.yaml")

    d056_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors=0",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "AssocMAC=2C:59:17:00:04:85\nAssocTxErrors=0",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverTxPkts=14207\nDriverTxErrors=0\nDriverRetries=29226\nDriverRetryExhausted=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d056, d056_results) is True

    d056_missing_snapshot_results = {
        "steps": {
            **d056_results["steps"],
            "step4": {
                "success": True,
                "output": "AssocMAC=2C:59:17:00:04:85",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d056, d056_missing_snapshot_results) is False

    d056_wrong_driver_results = {
        "steps": {
            **d056_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverTxPkts=14207\nDriverTxErrors=1\nDriverRetries=29226\nDriverRetryExhausted=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d056, d056_wrong_driver_results) is False

    d056_wrong_driver_assoc_results = {
        "steps": {
            **d056_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverTxPkts=14207\nDriverTxErrors=0\nDriverRetries=29226\nDriverRetryExhausted=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d056, d056_wrong_driver_assoc_results) is False

    d056_wrong_sta_results = {
        "steps": {
            **d056_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d056, d056_wrong_sta_results) is False


def test_d057_txmulticastpacketcount_uses_same_sta_delivery_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D057-txmulticastpacketcount" in discoverable_ids

    d057_raw = yaml.safe_load((cases_dir / "D057_txmulticastpacketcount.yaml").read_text(encoding="utf-8"))
    d057 = load_case(cases_dir / "D057_txmulticastpacketcount.yaml")
    d057_commands = "\n".join(str(step.get("command", "")) for step in d057["steps"])
    d057_links = {link["band"] for link in d057["topology"]["links"]}

    assert "aliases" not in d057_raw
    assert d057["id"] == "wifi-llapi-D057-txmulticastpacketcount"
    assert d057["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d057["source"]["row"] == 57
    assert d057["source"]["baseline"] == "BCM v4.0.3"
    assert d057["llapi_support"] == "Support"
    assert d057["bands"] == ["5g"]
    assert d057_links == {"5g"}
    assert d057["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount?"'
    assert "cat /sys/class/net/wl0/address" in d057_commands
    assert "tr 'A-F' 'a-f'" in d057_commands
    assert "StaRxPacketsBefore=" in d057_commands
    assert "StaRxBytesBefore=" in d057_commands
    assert "MACAddress?" in d057_commands
    assert "ping -b -I br-lan -c 10 -W 1 192.168.1.255" in d057_commands
    assert "ProbeTxPackets=" in d057_commands
    assert "StaRxPacketsAfter=" in d057_commands
    assert "StaRxBytesAfter=" in d057_commands
    assert "AssocTxMulticastPacketCount=" in d057_commands
    assert "DriverTxMulticastPacketCount=" in d057_commands
    assert "DriverTxMulticastBytes=" in d057_commands
    assert 'AssocMAC=' in d057_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "probe.ProbeTxPackets"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sta_after.StaRxPacketsAfter"
        and criterion["operator"] == ">"
        and criterion.get("reference") == "sta_identity.StaRxPacketsBefore"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sta_after.StaRxBytesAfter"
        and criterion["operator"] == ">"
        and criterion.get("reference") == "sta_identity.StaRxBytesBefore"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxMulticastPacketCount"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxMulticastPacketCount"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_snapshot.AssocTxMulticastPacketCount"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_counter.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_entry.MACAddress"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_counter.DriverTxMulticastPacketCount"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d057["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_counter.DriverTxMulticastBytes"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d057["pass_criteria"]
    )
    assert d057["results_reference"]["v4.0.3"]["5g"] == "To be tested"
    assert d057["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d057["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d057_txmulticastpacketcount_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txmulticastpacketcount.yaml")

    d057_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "\n".join(
                    [
                        "StaMac=2c:59:17:00:04:85",
                        "StaRxPacketsBefore=136067",
                        "StaRxBytesBefore=15249537",
                    ]
                ),
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "MACAddress=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "10 packets transmitted, 0 received, 100% packet loss, time 9034ms\nProbeTxPackets=10",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "StaRxPacketsAfter=136077\nStaRxBytesAfter=15250517",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount=0",
                "timing": 0.01,
            },
            "step6": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocTxMulticastPacketCount=0",
                "timing": 0.01,
            },
            "step7": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverTxMulticastPacketCount=0\nDriverTxMulticastBytes=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d057, d057_results) is True

    d057_no_delivery_results = {
        "steps": {
            **d057_results["steps"],
            "step4": {
                "success": True,
                "output": "StaRxPacketsAfter=136067\nStaRxBytesAfter=15249537",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d057, d057_no_delivery_results) is False

    d057_wrong_llapi_results = {
        "steps": {
            **d057_results["steps"],
            "step5": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount=3",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d057, d057_wrong_llapi_results) is False

    d057_wrong_driver_results = {
        "steps": {
            **d057_results["steps"],
            "step7": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverTxMulticastPacketCount=2\nDriverTxMulticastBytes=196",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d057, d057_wrong_driver_results) is False

    d057_wrong_assoc_results = {
        "steps": {
            **d057_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=aa:aa:aa:aa:aa:aa",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d057, d057_wrong_assoc_results) is False

    d057_mixed_case_llapi_results = {
        "steps": {
            **d057_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step6": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocTxMulticastPacketCount=0",
                "timing": 0.01,
            },
            "step7": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverTxMulticastPacketCount=0\nDriverTxMulticastBytes=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d057, d057_mixed_case_llapi_results) is True


def test_d059_txunicastpacketcount_uses_same_sta_failure_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D059-txunicastpacketcount" in discoverable_ids

    d059_raw = yaml.safe_load((cases_dir / "D059_txunicastpacketcount.yaml").read_text(encoding="utf-8"))
    d059 = load_case(cases_dir / "D059_txunicastpacketcount.yaml")
    d059_commands = "\n".join(str(step.get("command", "")) for step in d059["steps"])
    d059_links = {link["band"] for link in d059["topology"]["links"]}

    assert "aliases" not in d059_raw
    assert d059["id"] == "wifi-llapi-D059-txunicastpacketcount"
    assert d059["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d059["source"]["row"] == 59
    assert d059["source"]["baseline"] == "BCM v4.0.3"
    assert d059["llapi_support"] == "Support"
    assert d059["bands"] == ["5g"]
    assert d059_links == {"5g"}
    assert d059["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxUnicastPacketCount?"'
    assert "cat /sys/class/net/wl0/address" in d059_commands
    assert "tr 'A-F' 'a-f'" in d059_commands
    assert "MACAddress?" in d059_commands
    assert 'TxUnicastPacketCount?"' in d059_commands
    assert "AssocTxUnicastPacketCount=" in d059_commands
    assert "AssocTxPacketCount=" in d059_commands
    assert "DriverTxPacketCount=" in d059_commands
    assert "DriverTxUnicastPacketCount=" in d059_commands
    assert "DriverTxBytes=" in d059_commands
    assert "DriverTxUnicastBytes=" in d059_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxUnicastPacketCount"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.TxUnicastPacketCount"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_snapshot.AssocTxUnicastPacketCount"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_snapshot.AssocTxPacketCount"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_entry.MACAddress"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverTxPacketCount"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_snapshot.AssocTxPacketCount"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "driver_capture.DriverTxPacketCount"
        for criterion in d059["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverTxUnicastPacketCount"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d059["pass_criteria"]
    )
    assert d059["results_reference"]["v4.0.3"]["5g"] == "Fail"
    assert d059["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d059["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d059_txunicastpacketcount_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d059 = load_case(cases_dir / "D059_txunicastpacketcount.yaml")

    d059_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "MACAddress=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxUnicastPacketCount=0",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "\n".join(
                    [
                        "AssocMAC=2c:59:17:00:04:85",
                        "AssocTxUnicastPacketCount=0",
                        "AssocTxPacketCount=90442",
                    ]
                ),
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "\n".join(
                    [
                        "DriverAssocMac=2c:59:17:00:04:85",
                        "DriverTxPacketCount=90442",
                        "DriverTxUnicastPacketCount=90442",
                        "DriverTxBytes=0",
                        "DriverTxUnicastBytes=0",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d059, d059_results) is True

    d059_wrong_llapi_results = {
        "steps": {
            **d059_results["steps"],
            "step3": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxUnicastPacketCount=7",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d059, d059_wrong_llapi_results) is False

    d059_missing_total_results = {
        "steps": {
            **d059_results["steps"],
            "step4": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocTxUnicastPacketCount=0\nAssocTxPacketCount=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d059, d059_missing_total_results) is False

    d059_wrong_driver_results = {
        "steps": {
            **d059_results["steps"],
            "step5": {
                "success": True,
                "output": "\n".join(
                    [
                        "DriverAssocMac=2c:59:17:00:04:85",
                        "DriverTxPacketCount=90442",
                        "DriverTxUnicastPacketCount=0",
                        "DriverTxBytes=0",
                        "DriverTxUnicastBytes=0",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d059, d059_wrong_driver_results) is False

    d059_wrong_assoc_results = {
        "steps": {
            **d059_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=aa:aa:aa:aa:aa:aa",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d059, d059_wrong_assoc_results) is False


def test_d064_vendoroui_uses_same_sta_failure_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D064-vendoroui" in discoverable_ids

    d064_raw = yaml.safe_load((cases_dir / "D064_vendoroui.yaml").read_text(encoding="utf-8"))
    d064 = load_case(cases_dir / "D064_vendoroui.yaml")
    d064_commands = "\n".join(str(step.get("command", "")) for step in d064["steps"])
    d064_links = {link["band"] for link in d064["topology"]["links"]}

    assert "aliases" not in d064_raw
    assert d064["id"] == "wifi-llapi-D064-vendoroui"
    assert d064["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d064["source"]["row"] == 64
    assert d064["source"]["baseline"] == "BCM v4.0.3"
    assert d064["llapi_support"] == "Support"
    assert d064["bands"] == ["5g"]
    assert d064_links == {"5g"}
    assert d064["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"'
    assert "cat /sys/class/net/wl0/address" in d064_commands
    assert "tr 'A-F' 'a-f'" in d064_commands
    assert "MACAddress?" in d064_commands
    assert 'VendorOUI?"' in d064_commands
    assert "AssocVendorOUI=" in d064_commands
    assert "DriverVendorOUICount=" in d064_commands
    assert "DriverVendorOUIList=" in d064_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VendorOUI"
        and criterion["operator"] == "empty"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VendorOUI"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_snapshot.AssocVendorOUI"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVendorOUICount"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVendorOUIList"
        and criterion["operator"] == "not_equals"
        and criterion.get("reference") == "result.VendorOUI"
        for criterion in d064["pass_criteria"]
    )
    assert d064["results_reference"]["v4.0.3"]["5g"] == "Fail"
    assert d064["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d064["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d064_vendoroui_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_vendoroui.yaml")

    d064_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "MACAddress=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI=""',
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocVendorOUI=",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "\n".join(
                    [
                        "DriverAssocMac=2c:59:17:00:04:85",
                        "DriverVendorOUICount=4",
                        "DriverVendorOUIList=00:90:4C,00:10:18,00:50:F2,50:6F:9A",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_results) is True

    d064_wrong_llapi_results = {
        "steps": {
            **d064_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI="00:50:F2"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_wrong_llapi_results) is False

    d064_missing_driver_results = {
        "steps": {
            **d064_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverVendorOUICount=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_missing_driver_results) is False

    d064_wrong_assoc_results = {
        "steps": {
            **d064_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=aa:aa:aa:aa:aa:aa",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_wrong_assoc_results) is False


def test_d065_vhtcapabilities_uses_same_sta_failure_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D065-vhtcapabilities-accesspoint-associateddevice" in discoverable_ids

    d065_raw = yaml.safe_load(
        (cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d065 = load_case(cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml")
    d065_commands = "\n".join(str(step.get("command", "")) for step in d065["steps"])
    d065_links = {link["band"] for link in d065["topology"]["links"]}

    assert "aliases" not in d065_raw
    assert d065["id"] == "wifi-llapi-D065-vhtcapabilities-accesspoint-associateddevice"
    assert d065["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d065["source"]["row"] == 65
    assert d065["source"]["baseline"] == "BCM v4.0.3"
    assert d065["llapi_support"] == "Support"
    assert d065["bands"] == ["5g"]
    assert d065_links == {"5g"}
    assert d065["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"'
    assert "cat /sys/class/net/wl0/address" in d065_commands
    assert "tr 'A-F' 'a-f'" in d065_commands
    assert "MACAddress?" in d065_commands
    assert 'VhtCapabilities?"' in d065_commands
    assert "AssocVhtCapabilities=" in d065_commands
    assert "DriverVhtCapsLine=" in d065_commands
    assert "DriverVhtCapabilities=" in d065_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VhtCapabilities"
        and criterion["operator"] == "empty"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VhtCapabilities"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_snapshot.AssocVhtCapabilities"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SGI80"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SGI160"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SU-BFE"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "not_equals"
        and criterion.get("reference") == "result.VhtCapabilities"
        for criterion in d065["pass_criteria"]
    )
    assert d065["results_reference"]["v4.0.3"]["5g"] == "Fail"
    assert d065["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d065["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d065_vhtcapabilities_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml")

    d065_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "StaMac=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "MACAddress=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities=""',
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocVhtCapabilities=",
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "\n".join(
                    [
                        "DriverAssocMac=2c:59:17:00:04:85",
                        "DriverVhtCapsLine=LDPC SGI80 SGI160 SU-BFR SU-BFE",
                        "DriverVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_results) is True

    d065_wrong_llapi_results = {
        "steps": {
            **d065_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities="SGI80,SGI160,SU-BFE"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_wrong_llapi_results) is False

    d065_missing_driver_results = {
        "steps": {
            **d065_results["steps"],
            "step5": {
                "success": True,
                "output": "\n".join(
                    [
                        "DriverAssocMac=2c:59:17:00:04:85",
                        "DriverVhtCapsLine=LDPC SGI80 SU-BFR SU-BFE",
                        "DriverVhtCapabilities=SGI80,SU-BFR,SU-BFE",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_missing_driver_results) is False

    d065_wrong_assoc_results = {
        "steps": {
            **d065_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=aa:aa:aa:aa:aa:aa",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_wrong_assoc_results) is False


def test_d066_apbridgedisable_uses_ap_only_unsupported_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D066-apbridgedisable" in discoverable_ids

    d066_raw = yaml.safe_load((cases_dir / "D066_apbridgedisable.yaml").read_text(encoding="utf-8"))
    d066 = load_case(cases_dir / "D066_apbridgedisable.yaml")
    d066_commands = "\n".join(str(step.get("command", "")) for step in d066["steps"])

    assert "aliases" not in d066_raw
    assert d066["id"] == "wifi-llapi-D066-apbridgedisable"
    assert d066["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d066["source"]["row"] == 66
    assert d066["source"]["baseline"] == "BCM v4.0.3"
    assert d066["llapi_support"] == "Not Supported"
    assert d066["bands"] == ["5g"]
    assert set(d066["topology"]["devices"]) == {"DUT"}
    assert d066["topology"]["links"] == []
    assert d066["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.APBridgeDisable?"'
    assert "STA:" not in d066.get("sta_env_setup", "")
    assert "WPA2-Personal" in d066.get("sta_env_setup", "")
    assert "APBridgeDisable=1" in d066_commands
    assert "DriverApIsolateOn=" in d066_commands
    assert "HostapdApIsolateZeroCount=" in d066_commands
    assert "APBridgeDisable=0" in d066_commands
    assert "DriverApIsolateOff=" in d066_commands
    assert "DriverBssState=" in d066_commands
    assert any(
        criterion["field"] == "result_on.APBridgeDisable"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d066["pass_criteria"]
    )
    assert any(
        criterion["field"] == "hostapd_after_on.HostapdApIsolate"
        and criterion["operator"] == "not_equals"
        and criterion.get("reference") == "result_on.APBridgeDisable"
        for criterion in d066["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_off.DriverApIsolateOff"
        and criterion["operator"] == "not_equals"
        and criterion.get("reference") == "result_off.APBridgeDisable"
        for criterion in d066["pass_criteria"]
    )
    assert any(
        criterion["field"] == "bss_status.DriverBssState"
        and criterion["operator"] == "equals"
        and criterion["value"] == "up"
        for criterion in d066["pass_criteria"]
    )
    assert d066["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d066["results_reference"]["v4.0.3"]["6g"] == "N/A"
    assert d066["results_reference"]["v4.0.3"]["2.4g"] == "N/A"


def test_d066_apbridgedisable_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_apbridgedisable.yaml")

    assert plugin.setup_env(d066, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert all("wpa_cli" not in command for command in recorder.transports[0].executed_commands)
    assert any(
        command == "ubus-cli WiFi.AccessPoint.1.APBridgeDisable=0"
        for command in recorder.transports[0].executed_commands
    )
    plugin.teardown(d066, topology)


def test_d066_apbridgedisable_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_apbridgedisable.yaml")

    d066_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": "WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.APBridgeDisable=1",
                "timing": 0.01,
            },
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.APBridgeDisable=1",
                "timing": 0.01,
            },
            "step3": {
                "success": True,
                "output": "DriverApIsolateOn=1",
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "\n".join(
                    [
                        "HostapdApIsolate=0",
                        "HostapdApIsolate=0",
                        "HostapdApIsolateZeroCount=2",
                    ]
                ),
                "timing": 0.01,
            },
            "step5": {
                "success": True,
                "output": "WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.APBridgeDisable=0",
                "timing": 0.01,
            },
            "step6": {
                "success": True,
                "output": "waited 5.000s",
                "timing": 5.0,
            },
            "step7": {
                "success": True,
                "output": "WiFi.AccessPoint.1.APBridgeDisable=0",
                "timing": 0.01,
            },
            "step8": {
                "success": True,
                "output": "DriverApIsolateOff=1",
                "timing": 0.01,
            },
            "step9": {
                "success": True,
                "output": "DriverBssState=up",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_results) is True

    d066_wrong_enable_results = {
        "steps": {
            **d066_results["steps"],
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.APBridgeDisable=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_enable_results) is False

    d066_wrong_hostapd_results = {
        "steps": {
            **d066_results["steps"],
            "step4": {
                "success": True,
                "output": "\n".join(
                    [
                        "HostapdApIsolate=1",
                        "HostapdApIsolate=1",
                        "HostapdApIsolateZeroCount=0",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_hostapd_results) is False

    d066_wrong_driver_results = {
        "steps": {
            **d066_results["steps"],
            "step8": {
                "success": True,
                "output": "DriverApIsolateOff=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_driver_results) is False

    d066_bss_down_results = {
        "steps": {
            **d066_results["steps"],
            "step9": {
                "success": True,
                "output": "DriverBssState=down",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_bss_down_results) is False


def test_d067_bridgeinterface_uses_ap_only_multiband_pass_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D067-bridgeinterface" in discoverable_ids

    d067_raw = yaml.safe_load((cases_dir / "D067_bridgeinterface.yaml").read_text(encoding="utf-8"))
    d067 = load_case(cases_dir / "D067_bridgeinterface.yaml")
    d067_commands = "\n".join(str(step.get("command", "")) for step in d067["steps"])

    assert "aliases" not in d067_raw
    assert d067["id"] == "wifi-llapi-D067-bridgeinterface"
    assert d067["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d067["source"]["row"] == 67
    assert d067["source"]["baseline"] == "BCM v4.0.3"
    assert d067["llapi_support"] == "Support"
    assert d067["bands"] == ["5g", "6g", "2.4g"]
    assert set(d067["topology"]["devices"]) == {"DUT"}
    assert d067["topology"]["links"] == []
    assert d067["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.BridgeInterface?"'
    assert "wl -i wl0 bss" in d067.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d067.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d067.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.BridgeInterface?"' in d067_commands
    assert 'WiFi.AccessPoint.3.BridgeInterface?"' in d067_commands
    assert 'WiFi.AccessPoint.5.BridgeInterface?"' in d067_commands
    assert "BridgeConfig5g=" in d067_commands
    assert "BridgeConfig6g=" in d067_commands
    assert "BridgeConfig24g=" in d067_commands
    assert "BridgeConfig5gMismatch=" in d067_commands
    assert "BridgeConfig6gMismatch=" in d067_commands
    assert "BridgeConfig24gMismatch=" in d067_commands
    assert "BridgeMaster5g=" in d067_commands
    assert "BridgeMaster6g=" in d067_commands
    assert "BridgeMaster24g=" in d067_commands
    assert any(
        criterion["field"] == "result_5g.BridgeInterface"
        and criterion["operator"] == "equals"
        and criterion["value"] == "br-lan"
        for criterion in d067["pass_criteria"]
    )
    assert any(
        criterion["field"] == "config_6g.BridgeConfig6g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "result_6g.BridgeInterface"
        for criterion in d067["pass_criteria"]
    )
    assert any(
        criterion["field"] == "config_5g.BridgeConfig5gMismatch"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d067["pass_criteria"]
    )
    assert any(
        criterion["field"] == "bridge_state.BridgeMaster24g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "result_24g.BridgeInterface"
        for criterion in d067["pass_criteria"]
    )
    assert d067["results_reference"]["v4.0.3"]["5g"] == "Pass"
    assert d067["results_reference"]["v4.0.3"]["6g"] == "Pass"
    assert d067["results_reference"]["v4.0.3"]["2.4g"] == "Pass"


def test_d067_bridgeinterface_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_bridgeinterface.yaml")

    assert plugin.setup_env(d067, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d067, topology)


def test_d067_bridgeinterface_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_bridgeinterface.yaml")

    d067_results = {
        "steps": {
            "step1_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.BridgeInterface="br-lan"',
                "timing": 0.01,
            },
            "step2_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.BridgeInterface="br-lan"',
                "timing": 0.01,
            },
            "step3_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.BridgeInterface="br-lan"',
                "timing": 0.01,
            },
            "step4_5g_config": {
                "success": True,
                "output": "BridgeConfig5g=br-lan\nBridgeConfig5gCount=2\nBridgeConfig5gMismatch=0",
                "timing": 0.01,
            },
            "step5_6g_config": {
                "success": True,
                "output": "BridgeConfig6g=br-lan\nBridgeConfig6gCount=2\nBridgeConfig6gMismatch=0",
                "timing": 0.01,
            },
            "step6_24g_config": {
                "success": True,
                "output": "BridgeConfig24g=br-lan\nBridgeConfig24gCount=2\nBridgeConfig24gMismatch=0",
                "timing": 0.01,
            },
            "step7_bridge_state": {
                "success": True,
                "output": "\n".join(
                    [
                        "BridgeMaster5g=br-lan",
                        "BridgeMaster6g=br-lan",
                        "BridgeMaster24g=br-lan",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_results) is True

    d067_wrong_6g_results = {
        "steps": {
            **d067_results["steps"],
            "step2_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.BridgeInterface="br-guest"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_wrong_6g_results) is False

    d067_wrong_config_count_results = {
        "steps": {
            **d067_results["steps"],
            "step5_6g_config": {
                "success": True,
                "output": "BridgeConfig6g=br-lan\nBridgeConfig6gCount=1\nBridgeConfig6gMismatch=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_wrong_config_count_results) is False

    d067_mixed_config_results = {
        "steps": {
            **d067_results["steps"],
            "step4_5g_config": {
                "success": True,
                "output": "BridgeConfig5g=br-guest\nBridgeConfig5gCount=2\nBridgeConfig5gMismatch=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_mixed_config_results) is False

    d067_missing_member_results = {
        "steps": {
            **d067_results["steps"],
            "step7_bridge_state": {
                "success": True,
                "output": "BridgeMaster5g=br-lan\nBridgeMaster6g=br-lan",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_missing_member_results) is False

    d067_wrong_bridge_name_results = {
        "steps": {
            **d067_results["steps"],
            "step7_bridge_state": {
                "success": True,
                "output": "\n".join(
                    [
                        "BridgeMaster5g=br-lan",
                        "BridgeMaster6g=br-lan",
                        "BridgeMaster24g=br-guest",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_wrong_bridge_name_results) is False


def test_d068_discoverymethodenabled_accesspoint_fils_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d068_raw = yaml.safe_load(
        (cases_dir / "D068_discoverymethodenabled_accesspoint_fils.yaml").read_text(encoding="utf-8")
    )
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_fils.yaml")
    d068_commands = "\n".join(str(step.get("command", "")) for step in d068["steps"])

    assert "aliases" not in d068_raw
    assert d068["id"] == "wifi-llapi-D068-discoverymethodenabled-accesspoint-fils"
    assert d068["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d068["source"]["row"] == 68
    assert d068["source"]["baseline"] == "BCM v4.0.3"
    assert d068["llapi_support"] == "Support"
    assert d068["bands"] == ["5g", "6g", "2.4g"]
    assert set(d068["topology"]["devices"]) == {"DUT"}
    assert d068["topology"]["links"] == []
    assert d068["hlapi_command"] == 'ubus-cli WiFi.AccessPoint.1.DiscoveryMethodEnabled=FILS'
    assert "wl -i wl0 bss" in d068.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d068.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d068.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.DiscoveryMethodEnabled?"' in d068_commands
    assert "DiscoveryMethodEnabled=FILS" in d068_commands
    assert "DiscoveryMethodEnabled=FILSDiscovery" in d068_commands
    assert any(
        criterion["field"] == "invalid_5g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "invalid value"
        for criterion in d068["pass_criteria"]
    )
    assert any(
        criterion["field"] == "set_alt_6g.DiscoveryMethodEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "FILSDiscovery"
        for criterion in d068["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_alt_6g.DiscoveryMethodEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "FILSDiscovery"
        for criterion in d068["pass_criteria"]
    )
    assert d068["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d068["results_reference"]["v4.0.3"]["6g"] == "Not Supported"
    assert d068["results_reference"]["v4.0.3"]["2.4g"] == "Not Supported"


def test_d068_discoverymethodenabled_accesspoint_fils_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_fils.yaml")

    assert plugin.setup_env(d068, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d068, topology)


def test_d068_discoverymethodenabled_accesspoint_fils_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_fils.yaml")

    d068_results = {
        "steps": {
            "step1_default_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step2_default_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step3_default_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step4_invalid_5g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.1.DiscoveryMethodEnabled failed (10 - invalid value)",
                "timing": 0.01,
            },
            "step5_invalid_6g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.3.DiscoveryMethodEnabled failed (10 - invalid value)",
                "timing": 0.01,
            },
            "step6_invalid_24g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.5.DiscoveryMethodEnabled failed (10 - invalid value)",
                "timing": 0.01,
            },
            "step7_after_invalid_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step8_after_invalid_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step9_after_invalid_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step10_set_alt_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
            "step11_set_alt_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
            "step12_set_alt_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
            "step13_after_alt_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
            "step14_after_alt_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
            "step15_after_alt_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
            "step16_restore_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step17_restore_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step18_restore_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_results) is True

    d068_wrong_invalid_results = {
        "steps": {
            **d068_results["steps"],
            "step5_invalid_6g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.3.DiscoveryMethodEnabled failed (1 - permission denied)",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_invalid_results) is False

    d068_wrong_alt_results = {
        "steps": {
            **d068_results["steps"],
            "step15_after_alt_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_alt_results) is False

    d068_wrong_set_alt_results = {
        "steps": {
            **d068_results["steps"],
            "step11_set_alt_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_set_alt_results) is False

    d068_wrong_restore_results = {
        "steps": {
            **d068_results["steps"],
            "step16_restore_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_restore_results) is False


def test_d069_discoverymethodenabled_accesspoint_upr_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d069_raw = yaml.safe_load(
        (cases_dir / "D069_discoverymethodenabled_accesspoint_upr.yaml").read_text(encoding="utf-8")
    )
    d069 = load_case(cases_dir / "D069_discoverymethodenabled_accesspoint_upr.yaml")
    d069_commands = "\n".join(str(step.get("command", "")) for step in d069["steps"])

    assert "aliases" not in d069_raw
    assert d069["id"] == "wifi-llapi-D069-discoverymethodenabled-accesspoint-upr"
    assert d069["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d069["source"]["row"] == 69
    assert d069["source"]["baseline"] == "BCM v4.0.3"
    assert d069["llapi_support"] == "Support"
    assert d069["bands"] == ["5g", "6g", "2.4g"]
    assert set(d069["topology"]["devices"]) == {"DUT"}
    assert d069["topology"]["links"] == []
    assert d069["hlapi_command"] == 'ubus-cli WiFi.AccessPoint.1.DiscoveryMethodEnabled=UPR'
    assert "wl -i wl0 bss" in d069.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d069.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d069.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.DiscoveryMethodEnabled?"' in d069_commands
    assert "DiscoveryMethodEnabled=UPR" in d069_commands
    assert any(
        criterion["field"] == "set_upr_6g.DiscoveryMethodEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "UPR"
        for criterion in d069["pass_criteria"]
    )
    assert any(
        criterion["field"] == "set_upr_5g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "invalid value"
        for criterion in d069["pass_criteria"]
    )
    assert d069["results_reference"]["v4.0.3"]["5g"] == "Not Supported"
    assert d069["results_reference"]["v4.0.3"]["6g"] == "Pass"
    assert d069["results_reference"]["v4.0.3"]["2.4g"] == "Not Supported"


def test_d069_discoverymethodenabled_accesspoint_upr_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d069 = load_case(cases_dir / "D069_discoverymethodenabled_accesspoint_upr.yaml")

    assert plugin.setup_env(d069, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d069, topology)


def test_d069_discoverymethodenabled_accesspoint_upr_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d069 = load_case(cases_dir / "D069_discoverymethodenabled_accesspoint_upr.yaml")

    d069_results = {
        "steps": {
            "step1_default_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step2_default_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step3_default_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step4_set_upr_5g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.1.DiscoveryMethodEnabled failed (10 - invalid value)",
                "timing": 0.01,
            },
            "step5_set_upr_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="UPR"',
                "timing": 0.01,
            },
            "step6_set_upr_24g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.5.DiscoveryMethodEnabled failed (10 - invalid value)",
                "timing": 0.01,
            },
            "step7_after_upr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step8_after_upr_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="UPR"',
                "timing": 0.01,
            },
            "step9_after_upr_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step10_restore_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step11_restore_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step12_restore_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d069, d069_results) is True

    d069_wrong_5g_results = {
        "steps": {
            **d069_results["steps"],
            "step4_set_upr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="UPR"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d069, d069_wrong_5g_results) is False

    d069_wrong_6g_results = {
        "steps": {
            **d069_results["steps"],
            "step8_after_upr_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d069, d069_wrong_6g_results) is False

    d069_wrong_restore_results = {
        "steps": {
            **d069_results["steps"],
            "step11_restore_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="UPR"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d069, d069_wrong_restore_results) is False


def test_d070_discoverymethodenabled_accesspoint_rnr_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d070_raw = yaml.safe_load(
        (cases_dir / "D070_discoverymethodenabled_accesspoint_rnr.yaml").read_text(encoding="utf-8")
    )
    d070 = load_case(cases_dir / "D070_discoverymethodenabled_accesspoint_rnr.yaml")
    d070_commands = "\n".join(str(step.get("command", "")) for step in d070["steps"])

    assert "aliases" not in d070_raw
    assert d070["id"] == "wifi-llapi-D070-discoverymethodenabled-accesspoint-rnr"
    assert d070["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d070["source"]["row"] == 70
    assert d070["source"]["baseline"] == "BCM v4.0.3"
    assert d070["llapi_support"] == "Support"
    assert d070["bands"] == ["5g", "6g", "2.4g"]
    assert set(d070["topology"]["devices"]) == {"DUT"}
    assert d070["topology"]["links"] == []
    assert d070["hlapi_command"] == 'ubus-cli WiFi.AccessPoint.1.DiscoveryMethodEnabled=RNR'
    assert "wl -i wl0 bss" in d070.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d070.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d070.get("sta_env_setup", "")
    assert "RnrEnabled6gCount=" in d070_commands
    assert "RnrTotal24gCount=" in d070_commands
    assert any(
        criterion["field"] == "cfg_6g_after.RnrEnabled6gCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d070["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_5g_after.RnrTotal5gCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d070["pass_criteria"]
    )
    assert d070["results_reference"]["v4.0.3"]["5g"] == "Fail"
    assert d070["results_reference"]["v4.0.3"]["6g"] == "Pass"
    assert d070["results_reference"]["v4.0.3"]["2.4g"] == "Fail"


def test_d070_discoverymethodenabled_accesspoint_rnr_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_discoverymethodenabled_accesspoint_rnr.yaml")

    assert plugin.setup_env(d070, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d070, topology)


def test_d070_discoverymethodenabled_accesspoint_rnr_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_discoverymethodenabled_accesspoint_rnr.yaml")

    d070_results = {
        "steps": {
            "step1_default_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step2_default_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step3_default_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step4_set_rnr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="RNR"',
                "timing": 0.01,
            },
            "step5_set_rnr_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="RNR"',
                "timing": 0.01,
            },
            "step6_set_rnr_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.DiscoveryMethodEnabled="RNR"',
                "timing": 0.01,
            },
            "step7_after_rnr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="RNR"',
                "timing": 0.01,
            },
            "step8_after_rnr_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="RNR"',
                "timing": 0.01,
            },
            "step9_after_rnr_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="RNR"',
                "timing": 0.01,
            },
            "step10_cfg_5g_after": {
                "success": True,
                "output": "RnrEnabled5gCount=0\nRnrDisabled5gCount=0\nRnrTotal5gCount=0",
                "timing": 0.01,
            },
            "step11_cfg_6g_after": {
                "success": True,
                "output": "RnrEnabled6gCount=1\nRnrDisabled6gCount=1\nRnrTotal6gCount=2",
                "timing": 0.01,
            },
            "step12_cfg_24g_after": {
                "success": True,
                "output": "RnrEnabled24gCount=0\nRnrDisabled24gCount=0\nRnrTotal24gCount=0",
                "timing": 0.01,
            },
            "step13_restore_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step14_restore_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step15_restore_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
            "step16_cfg_6g_restore": {
                "success": True,
                "output": "RnrEnabled6gCount=0\nRnrDisabled6gCount=2\nRnrTotal6gCount=2",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_results) is True

    d070_wrong_6g_config_results = {
        "steps": {
            **d070_results["steps"],
            "step11_cfg_6g_after": {
                "success": True,
                "output": "RnrEnabled6gCount=0\nRnrDisabled6gCount=2\nRnrTotal6gCount=2",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_wrong_6g_config_results) is False

    d070_wrong_5g_getter_results = {
        "steps": {
            **d070_results["steps"],
            "step7_after_rnr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_wrong_5g_getter_results) is False

    d070_wrong_restore_results = {
        "steps": {
            **d070_results["steps"],
            "step16_cfg_6g_restore": {
                "success": True,
                "output": "RnrEnabled6gCount=1\nRnrDisabled6gCount=1\nRnrTotal6gCount=2",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_wrong_restore_results) is False


def test_d072_enable_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d072_raw = yaml.safe_load((cases_dir / "D072_enable_accesspoint.yaml").read_text(encoding="utf-8"))
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")
    d072_commands = "\n".join(str(step.get("command", "")) for step in d072["steps"])

    assert "aliases" not in d072_raw
    assert d072["id"] == "wifi-llapi-D072-enable-accesspoint"
    assert d072["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d072["source"]["row"] == 72
    assert d072["source"]["baseline"] == "BCM v4.0.3"
    assert d072["llapi_support"] == "Support"
    assert d072["bands"] == ["5g", "6g", "2.4g"]
    assert set(d072["topology"]["devices"]) == {"DUT"}
    assert d072["topology"]["links"] == []
    assert d072["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.Enable=1"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d072.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in d072.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.Enable=1" in d072.get("sta_env_setup", "")
    assert "DriverBssState6g=" in d072_commands
    assert "StartDisabled24gTotalCount=" in d072_commands
    assert any(
        criterion["field"] == "cfg_disable_6g.StartDisabled6gOneCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d072["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_enable_24g.StartDisabled24gTotalCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d072["pass_criteria"]
    )
    assert d072["results_reference"]["v4.0.3"]["5g"] == "To be tested"
    assert d072["results_reference"]["v4.0.3"]["6g"] == "To be tested"
    assert d072["results_reference"]["v4.0.3"]["2.4g"] == "To be tested"


def test_d072_enable_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")

    assert plugin.setup_env(d072, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d072, topology)


def test_d072_enable_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")

    d072_results = {
        "steps": {
            "step1_default_5g": {"success": True, "output": "WiFi.AccessPoint.1.Enable=1", "timing": 0.01},
            "step2_default_6g": {"success": True, "output": "WiFi.AccessPoint.3.Enable=1", "timing": 0.01},
            "step3_default_24g": {"success": True, "output": "WiFi.AccessPoint.5.Enable=1", "timing": 0.01},
            "step4_disable_5g": {
                "success": True,
                "output": "WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.Enable=0",
                "timing": 0.01,
            },
            "step5_state_disable_5g": {
                "success": True,
                "output": 'Enable5g=0\nStatus5g="Disabled"',
                "timing": 0.01,
            },
            "step6_bss_disable_5g": {"success": True, "output": "DriverBssState5g=down", "timing": 0.01},
            "step7_cfg_disable_5g": {
                "success": True,
                "output": "StartDisabled5g=1\nStartDisabled5gOneCount=1\nStartDisabled5gZeroCount=0\nStartDisabled5gTotalCount=1",
                "timing": 0.01,
            },
            "step8_enable_5g": {
                "success": True,
                "output": "WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.Enable=1",
                "timing": 0.01,
            },
            "step9_state_enable_5g": {
                "success": True,
                "output": 'Enable5g=1\nStatus5g="Enabled"',
                "timing": 0.01,
            },
            "step10_bss_enable_5g": {"success": True, "output": "DriverBssState5g=up", "timing": 0.01},
            "step11_cfg_enable_5g": {
                "success": True,
                "output": "StartDisabled5gOneCount=0\nStartDisabled5gZeroCount=0\nStartDisabled5gTotalCount=0",
                "timing": 0.01,
            },
            "step12_disable_6g": {
                "success": True,
                "output": "WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.Enable=0",
                "timing": 0.01,
            },
            "step13_state_disable_6g": {
                "success": True,
                "output": 'Enable6g=0\nStatus6g="Disabled"',
                "timing": 0.01,
            },
            "step14_bss_disable_6g": {"success": True, "output": "DriverBssState6g=down", "timing": 0.01},
            "step15_cfg_disable_6g": {
                "success": True,
                "output": "StartDisabled6g=1\nStartDisabled6gOneCount=1\nStartDisabled6gZeroCount=0\nStartDisabled6gTotalCount=1",
                "timing": 0.01,
            },
            "step16_enable_6g": {
                "success": True,
                "output": "WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.Enable=1",
                "timing": 0.01,
            },
            "step17_state_enable_6g": {
                "success": True,
                "output": 'Enable6g=1\nStatus6g="Enabled"',
                "timing": 0.01,
            },
            "step18_bss_enable_6g": {"success": True, "output": "DriverBssState6g=up", "timing": 0.01},
            "step19_cfg_enable_6g": {
                "success": True,
                "output": "StartDisabled6gOneCount=0\nStartDisabled6gZeroCount=0\nStartDisabled6gTotalCount=0",
                "timing": 0.01,
            },
            "step20_disable_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.Enable=0",
                "timing": 0.01,
            },
            "step21_state_disable_24g": {
                "success": True,
                "output": 'Enable24g=0\nStatus24g="Disabled"',
                "timing": 0.01,
            },
            "step22_bss_disable_24g": {"success": True, "output": "DriverBssState24g=down", "timing": 0.01},
            "step23_cfg_disable_24g": {
                "success": True,
                "output": "StartDisabled24g=1\nStartDisabled24gOneCount=1\nStartDisabled24gZeroCount=0\nStartDisabled24gTotalCount=1",
                "timing": 0.01,
            },
            "step24_enable_24g": {
                "success": True,
                "output": "WiFi.AccessPoint.5.\nWiFi.AccessPoint.5.Enable=1",
                "timing": 0.01,
            },
            "step25_state_enable_24g": {
                "success": True,
                "output": 'Enable24g=1\nStatus24g="Enabled"',
                "timing": 0.01,
            },
            "step26_bss_enable_24g": {"success": True, "output": "DriverBssState24g=up", "timing": 0.01},
            "step27_cfg_enable_24g": {
                "success": True,
                "output": "StartDisabled24gOneCount=0\nStartDisabled24gZeroCount=0\nStartDisabled24gTotalCount=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_results) is True

    d072_wrong_6g_bss_results = {
        "steps": {
            **d072_results["steps"],
            "step14_bss_disable_6g": {
                "success": True,
                "output": "DriverBssState6g=up",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_wrong_6g_bss_results) is False

    d072_wrong_24g_cfg_results = {
        "steps": {
            **d072_results["steps"],
            "step23_cfg_disable_24g": {
                "success": True,
                "output": "StartDisabled24gOneCount=0\nStartDisabled24gZeroCount=0\nStartDisabled24gTotalCount=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_wrong_24g_cfg_results) is False

    d072_wrong_5g_restore_results = {
        "steps": {
            **d072_results["steps"],
            "step9_state_enable_5g": {
                "success": True,
                "output": 'Enable5g=1\nStatus5g="Disabled"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_wrong_5g_restore_results) is False


def test_d073_ftoverdsenable_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d073_raw = yaml.safe_load((cases_dir / "D073_ftoverdsenable.yaml").read_text(encoding="utf-8"))
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")
    d073_commands = "\n".join(str(step.get("command", "")) for step in d073["steps"])

    assert "aliases" not in d073_raw
    assert d073["id"] == "wifi-llapi-D073-ftoverdsenable-accesspoint"
    assert d073["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d073["source"]["row"] == 73
    assert d073["source"]["baseline"] == "BCM v4.0.3"
    assert d073["llapi_support"] == "Support"
    assert d073["implemented_by"] == "pWHM"
    assert d073["bands"] == ["5g", "6g", "2.4g"]
    assert set(d073["topology"]["devices"]) == {"DUT"}
    assert d073["topology"]["links"] == []
    assert d073["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.IEEE80211r.FTOverDSEnable=1"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d073.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.IEEE80211r.Enabled=1" in d073.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.IEEE80211r.MobilityDomain=4660" in d073.get("sta_env_setup", "")
    assert "MobilityDomainCfg6g=" in d073_commands
    assert "FtOverDs24gTotalCount=" in d073_commands
    assert any(
        criterion["field"] == "cfg_set_ft_6g.FtOverDs6gOneCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d073["pass_criteria"]
    )
    assert any(
        criterion["field"] == "state_cleanup_24g.MobilityDomain24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d073["pass_criteria"]
    )
    assert d073["results_reference"]["v4.0.3"]["5g"] == "To be tested"
    assert d073["results_reference"]["v4.0.3"]["6g"] == "To be tested"
    assert d073["results_reference"]["v4.0.3"]["2.4g"] == "To be tested"


def test_d073_ftoverdsenable_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")

    assert plugin.setup_env(d073, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.IEEE80211r.Enabled=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.IEEE80211r.Enabled=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.IEEE80211r.Enabled=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=4660") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.IEEE80211r.MobilityDomain=4660") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.IEEE80211r.MobilityDomain=4660") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d073, topology)


def test_d073_ftoverdsenable_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")

    def state_output(suffix: str, enabled: int, ft: int, mobility_domain: int) -> str:
        return "\n".join(
            [
                f"Enabled{suffix}={enabled}",
                f"FtOverDs{suffix}={ft}",
                f"MobilityDomain{suffix}={mobility_domain}",
            ]
        )

    def cfg_output(suffix: str, mobility_domain_hex: str, one_count: int, zero_count: int, total_count: int) -> str:
        return "\n".join(
            [
                f"MobilityDomainCfg{suffix}={mobility_domain_hex}",
                f"FtOverDs{suffix}OneCount={one_count}",
                f"FtOverDs{suffix}ZeroCount={zero_count}",
                f"FtOverDs{suffix}TotalCount={total_count}",
            ]
        )

    def setter_output(ap_index: int, field: str, value: int) -> str:
        return f"WiFi.AccessPoint.{ap_index}.IEEE80211r.\nWiFi.AccessPoint.{ap_index}.IEEE80211r.{field}={value}"

    d073_steps: dict[str, dict[str, Any]] = {}
    for suffix, ap_index, base in (("5g", 1, 1), ("6g", 3, 11), ("24g", 5, 21)):
        d073_steps[f"step{base}_prereq_enabled_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "Enabled", 1),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 1}_prereq_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 4660),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 2}_state_prereq_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0, 4660),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 3}_cfg_prereq_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "3412", 0, 1, 1),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 4}_set_ft_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "FTOverDSEnable", 1),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 5}_state_set_ft_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 1, 4660),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 6}_cfg_set_ft_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "3412", 1, 0, 1),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 7}_restore_ft_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "FTOverDSEnable", 0),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 8}_state_restore_ft_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0, 4660),
            "timing": 0.01,
        }
        d073_steps[f"step{base + 9}_cfg_restore_ft_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "3412", 0, 1, 1),
            "timing": 0.01,
        }

    for suffix, ap_index, base in (("5g", 1, 31), ("6g", 3, 33), ("24g", 5, 35)):
        d073_steps[f"step{base}_cleanup_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 0) + f"\nWiFi.AccessPoint.{ap_index}.IEEE80211r.Enabled=0",
            "timing": 0.01,
        }
        d073_steps[f"step{base + 1}_state_cleanup_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 0, 0, 0),
            "timing": 0.01,
        }

    d073_results = {"steps": d073_steps}
    assert plugin.evaluate(d073, d073_results) is True

    d073_wrong_6g_cfg_results = {
        "steps": {
            **d073_steps,
            "step17_cfg_set_ft_6g": {
                "success": True,
                "output": cfg_output("6g", "3412", 0, 1, 1),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d073, d073_wrong_6g_cfg_results) is False

    d073_wrong_24g_cleanup_results = {
        "steps": {
            **d073_steps,
            "step36_state_cleanup_24g": {
                "success": True,
                "output": state_output("24g", 0, 0, 4660),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d073, d073_wrong_24g_cleanup_results) is False

    d073_wrong_5g_prereq_results = {
        "steps": {
            **d073_steps,
            "step4_cfg_prereq_5g": {
                "success": True,
                "output": cfg_output("5g", "3412", 0, 0, 0),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d073, d073_wrong_5g_prereq_results) is False


def test_d074_mobilitydomain_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"

    d074_raw = yaml.safe_load((cases_dir / "D074_mobilitydomain.yaml").read_text(encoding="utf-8"))
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")
    d074_commands = "\n".join(str(step.get("command", "")) for step in d074["steps"])

    assert "aliases" not in d074_raw
    assert d074["id"] == "wifi-llapi-D074-mobilitydomain-accesspoint"
    assert d074["source"]["report"] == "0310-BGW720-300_LLAPI_Test_Report.xlsx"
    assert d074["source"]["row"] == 74
    assert d074["source"]["baseline"] == "BCM v4.0.3"
    assert d074["llapi_support"] == "Support"
    assert d074["implemented_by"] == "pWHM"
    assert d074["bands"] == ["5g", "6g", "2.4g"]
    assert set(d074["topology"]["devices"]) == {"DUT"}
    assert d074["topology"]["links"] == []
    assert d074["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=27476"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d074.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in d074.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.Enable=1" in d074.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d074.get("sta_env_setup", "")
    assert "MobilityDomainCfg6g=" in d074_commands
    assert "FtOverDs24gTotalCount=" in d074_commands
    assert any(
        criterion["field"] == "cfg_set_mobilitydomain_6g.MobilityDomainCfg6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "546B"
        for criterion in d074["pass_criteria"]
    )
    assert any(
        criterion["field"] == "state_cleanup_24g.MobilityDomain24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d074["pass_criteria"]
    )
    assert d074["results_reference"]["v4.0.3"]["5g"] == "To be tested"
    assert d074["results_reference"]["v4.0.3"]["6g"] == "To be tested"
    assert d074["results_reference"]["v4.0.3"]["2.4g"] == "To be tested"


def test_d074_mobilitydomain_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")

    assert plugin.setup_env(d074, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("IEEE80211r.Enabled=1" not in command for command in executed_commands)
    assert all("IEEE80211r.MobilityDomain=27476" not in command for command in executed_commands)
    plugin.teardown(d074, topology)


def test_d074_mobilitydomain_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")

    def state_output(suffix: str, enabled: int, mobility_domain: int) -> str:
        return "\n".join(
            [
                f"Enabled{suffix}={enabled}",
                f"MobilityDomain{suffix}={mobility_domain}",
            ]
        )

    def cfg_output(suffix: str, mobility_domain_hex: str, zero_count: int, total_count: int) -> str:
        return "\n".join(
            [
                f"MobilityDomainCfg{suffix}={mobility_domain_hex}",
                f"FtOverDs{suffix}ZeroCount={zero_count}",
                f"FtOverDs{suffix}TotalCount={total_count}",
            ]
        )

    def setter_output(ap_index: int, field: str, value: int) -> str:
        return f"WiFi.AccessPoint.{ap_index}.IEEE80211r.\nWiFi.AccessPoint.{ap_index}.IEEE80211r.{field}={value}"

    d074_steps: dict[str, dict[str, Any]] = {}
    for suffix, ap_index, base in (("5g", 1, 1), ("6g", 3, 10), ("24g", 5, 19)):
        d074_steps[f"step{base}_enable_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "Enabled", 1),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 1}_state_enabled_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 2}_set_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 27476),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 3}_state_set_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 27476),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 4}_cfg_set_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "546B", 1, 1),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 5}_restore_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 0),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 6}_state_restore_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 7}_cleanup_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "Enabled", 0),
            "timing": 0.01,
        }
        d074_steps[f"step{base + 8}_state_cleanup_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 0, 0),
            "timing": 0.01,
        }

    d074_results = {"steps": d074_steps}
    assert plugin.evaluate(d074, d074_results) is True

    d074_wrong_6g_cfg_results = {
        "steps": {
            **d074_steps,
            "step14_cfg_set_mobilitydomain_6g": {
                "success": True,
                "output": cfg_output("6g", "6B54", 1, 1),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d074, d074_wrong_6g_cfg_results) is False

    d074_wrong_24g_cleanup_results = {
        "steps": {
            **d074_steps,
            "step27_state_cleanup_24g": {
                "success": True,
                "output": state_output("24g", 0, 27476),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d074, d074_wrong_24g_cleanup_results) is False

    d074_wrong_5g_enabled_results = {
        "steps": {
            **d074_steps,
            "step2_state_enabled_5g": {
                "success": True,
                "output": state_output("5g", 1, 27476),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d074, d074_wrong_5g_enabled_results) is False


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


def test_extract_key_values_captures_ubus_json_array_object():
    plugin = _load_plugin()
    parsed = plugin._extract_key_values(
        '[\n  {\n    "WiFi.AccessPoint.1.AssociatedDevice.1.MUGroupId": 0\n  }\n]\n'
    )
    assert parsed["WiFi.AccessPoint.1.AssociatedDevice.1.MUGroupId"] == 0


def test_extract_key_values_captures_ubus_json_array_error():
    plugin = _load_plugin()
    parsed = plugin._extract_key_values(
        '[\n  {\n    "error": 4,\n    "message": "mode doesn\'t exist in odl"\n  }\n]\n'
    )
    assert parsed["error"] == 4
    assert parsed["message"] == "mode doesn't exist in odl"


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


@pytest.mark.parametrize(
    "filename",
    [
        "D046_signalnoiseratio.yaml",
        "D051_supportedmcs.yaml",
        "D045_securitymodeenabled.yaml",
        "D047_signalstrength_accesspoint_associateddevice.yaml",
        "D048_signalstrengthbychain.yaml",
        "D049_supportedhe160mcs.yaml",
        "D050_supportedhemcs.yaml",
        "D052_supportedvhtmcs.yaml",
        "D056_txerrors.yaml",
        "D057_txmulticastpacketcount.yaml",
        "D058_txpacketcount.yaml",
        "D059_txunicastpacketcount.yaml",
        "D061_uplinkbandwidth.yaml",
        "D060_uniibandscapabilities.yaml",
    ],
)
def test_sta_env_setup_parser_preserves_single_line_wpa_supplicant_template(filename: str):
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / filename)

    parsed = plugin._iter_env_script_commands(case_data["sta_env_setup"])
    commands = [command for _, command in parsed]

    assert (
        "printf 'ctrl_interface=/var/run/wpa_supplicant\\nupdate_config=1\\nsae_pwe=2\\nnetwork={\\nssid=\"TestPilot_BTM\"\\nkey_mgmt=SAE\\nsae_password=\"testpilot6g\"\\nieee80211w=2\\nscan_ssid=1\\n}\\n' > /tmp/wpa_wl0.conf"
        in commands
    )
    assert "rm -f /var/run/wpa_supplicant/wl0 2>/dev/null || true" in commands
    assert "mkdir -p /var/run/wpa_supplicant" in commands
    assert "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant" in commands
    assert "update_config=1" not in commands
    assert "sae_pwe=2" not in commands
    assert "network={" not in commands


def test_sta_env_setup_parser_preserves_single_line_wpa_supplicant_psk_template():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D062_uplinkmcs.yaml")

    parsed = plugin._iter_env_script_commands(case_data["sta_env_setup"])
    commands = [command for _, command in parsed]

    assert (
        "printf 'ctrl_interface=/var/run/wpa_supplicant\\nupdate_config=1\\nnetwork={\\nssid=\"testpilot5G\"\\npsk=\"00000000\"\\nkey_mgmt=WPA-PSK\\nscan_ssid=1\\n}\\n' > /tmp/wpa_wl0.conf"
        in commands
    )
    assert "rm -f /var/run/wpa_supplicant/wl0 2>/dev/null || true" in commands
    assert "mkdir -p /var/run/wpa_supplicant" in commands
    assert "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant" in commands
    assert "update_config=1" not in commands
    assert "network={" not in commands


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


@pytest.mark.parametrize(
    ("filename", "step_index", "driver_token"),
    [
        ("D036_noise_accesspoint_associateddevice.yaml", 2, "DriverNoise="),
        ("D039_retransmissions.yaml", 2, "DriverRetransmissions="),
        ("D041_rxbytes.yaml", 2, "DriverRxBytes="),
        ("D042_rxmulticastpacketcount.yaml", 3, "DriverRxMulticastPacketCount="),
        ("D046_signalnoiseratio.yaml", 2, "DriverSignalNoiseRatio="),
        ("D045_securitymodeenabled.yaml", 2, "DriverSecurityModeEnabled="),
        ("D047_signalstrength_accesspoint_associateddevice.yaml", 2, "DriverSignalStrength="),
        ("D048_signalstrengthbychain.yaml", 3, "DriverSignalStrengthByChain="),
        ("D050_supportedhemcs.yaml", 4, "DriverHeMcsLinePresent="),
        ("D052_supportedvhtmcs.yaml", 4, "DriverVhtSetPresent="),
        ("D056_txerrors.yaml", 4, "DriverTxErrors="),
        ("D051_supportedmcs.yaml", 2, "DriverMCSSetPresent="),
        ("D058_txpacketcount.yaml", 2, "DriverTxPacketCount="),
        ("D061_uplinkbandwidth.yaml", 2, "DriverUplinkBandwidth="),
        ("D062_uplinkmcs.yaml", 3, "DriverUplinkMCS="),
        ("D063_uplinkshortguard.yaml", 4, "DriverUplinkShortGuardGI="),
        ("D064_vendoroui.yaml", 4, "DriverVendorOUIList="),
        (
            "D065_vhtcapabilities_accesspoint_associateddevice.yaml",
            4,
            "DriverVhtCapabilities=",
        ),
        ("D060_uniibandscapabilities.yaml", 2, "DriverUNIIBandsCapabilities="),
    ],
)
def test_sanitize_cli_fragment_preserves_nested_quotes_for_associateddevice_driver_checks(
    filename: str, step_index: int, driver_token: str
):
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / filename)
    command = case_data["steps"][step_index]["command"]

    assert '[ -n "$STA_MAC" ]' in command
    assert "DriverAssocMac=" in command
    assert driver_token in command
    assert plugin._sanitize_cli_fragment(command) == command
    assert plugin._extract_cli_fragments(command) == [command]

    verification_commands = plugin._extract_cli_fragments(case_data["verification_command"])
    if filename == "D048_signalstrengthbychain.yaml":
        assert len(verification_commands) == 3
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
        assert verification_commands[1].startswith('ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.')
        assert verification_commands[2] == command
    elif filename in {
        "D049_supportedhe160mcs.yaml",
        "D050_supportedhemcs.yaml",
        "D052_supportedvhtmcs.yaml",
        "D056_txerrors.yaml",
    }:
        assert len(verification_commands) == 4
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
        if filename == "D056_txerrors.yaml":
            assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors?"'
            assert "AssocTxErrors=" in verification_commands[2]
        else:
            assert verification_commands[1].startswith('OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.')
            assert "SiblingAssocMac=" in verification_commands[2]
        assert verification_commands[3] == command
    elif filename == "D064_vendoroui.yaml":
        assert len(verification_commands) == 4
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'"
        assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"'
        assert "AssocVendorOUI=" in verification_commands[2]
        assert verification_commands[3] == command
    elif filename == "D065_vhtcapabilities_accesspoint_associateddevice.yaml":
        assert len(verification_commands) == 4
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'"
        assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"'
        assert "AssocVhtCapabilities=" in verification_commands[2]
        assert verification_commands[3] == command
    else:
        assert len(verification_commands) == 2
        assert verification_commands[0].startswith('ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.')
        assert verification_commands[1] == command


def test_d049_supportedhe160mcs_verification_fragments_preserve_error_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d049 = load_case(cases_dir / "D049_supportedhe160mcs.yaml")

    step3_command = d049["steps"][2]["command"]
    step5_command = d049["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d049["verification_command"])

    assert "SupportedHe160MCS?" in step3_command
    assert "error=" in step3_command
    assert "message=" in step3_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
    assert verification_commands[1] == step3_command
    assert "DriverRxSupportedHe160MCS=" in verification_commands[2]
    assert verification_commands[3] == step5_command


def test_d050_supportedhemcs_verification_fragments_preserve_error_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d050 = load_case(cases_dir / "D050_supportedhemcs.yaml")

    step3_command = d050["steps"][2]["command"]
    step5_command = d050["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d050["verification_command"])

    assert "SupportedHeMCS?" in step3_command
    assert "error=" in step3_command
    assert "message=" in step3_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
    assert verification_commands[1] == step3_command
    assert "DriverRxSupportedHeMCS=" in verification_commands[2]
    assert verification_commands[3] == step5_command


def test_d052_supportedvhtmcs_verification_fragments_preserve_error_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d052 = load_case(cases_dir / "D052_supportedvhtmcs.yaml")

    step3_command = d052["steps"][2]["command"]
    step5_command = d052["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d052["verification_command"])

    assert "SupportedVhtMCS?" in step3_command
    assert "error=" in step3_command
    assert "message=" in step3_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
    assert verification_commands[1] == step3_command
    assert "DriverRxSupportedVhtMCS=" in verification_commands[2]
    assert verification_commands[3] == step5_command


def test_d056_txerrors_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d056 = load_case(cases_dir / "D056_txerrors.yaml")

    step3_command = d056["steps"][2]["command"]
    step5_command = d056["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d056["verification_command"])

    assert step3_command == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors?"'
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
    assert verification_commands[1] == step3_command
    assert "AssocTxErrors=" in verification_commands[2]
    assert verification_commands[3] == step5_command


def test_d057_txmulticastpacketcount_verification_fragments_preserve_delivery_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txmulticastpacketcount.yaml")

    step3_command = d057["steps"][2]["command"]
    step6_command = d057["steps"][5]["command"]
    step7_command = d057["steps"][6]["command"]
    verification_commands = plugin._extract_cli_fragments(d057["verification_command"])

    assert "ProbeTxPackets=" in step3_command
    assert "AssocTxMulticastPacketCount=" in step6_command
    assert plugin._sanitize_cli_fragment(step7_command) == step7_command
    assert plugin._extract_cli_fragments(step7_command) == [step7_command]
    assert step3_command in verification_commands
    assert any("StaRxPacketsBefore=" in fragment for fragment in verification_commands)
    assert any("StaRxPacketsAfter=" in fragment for fragment in verification_commands)
    assert 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount?"' in verification_commands
    assert step6_command in verification_commands
    assert step7_command in verification_commands


def test_d057_txmulticastpacketcount_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txmulticastpacketcount.yaml")
    step2_command = d057["steps"][1]["command"]
    pipeline = step2_command.split("|", 1)[1].strip()
    sample_output = 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"'

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "MACAddress=2c:59:17:00:04:85"


def test_d057_txmulticastpacketcount_snapshot_sed_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txmulticastpacketcount.yaml")
    step6_command = d057["steps"][5]["command"]
    pipeline = step6_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
            "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount=0",
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "AssocMAC=2c:59:17:00:04:85",
        "AssocTxMulticastPacketCount=0",
    ]


def test_d059_txunicastpacketcount_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d059 = load_case(cases_dir / "D059_txunicastpacketcount.yaml")

    step3_command = d059["steps"][2]["command"]
    step4_command = d059["steps"][3]["command"]
    step5_command = d059["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d059["verification_command"])

    assert step3_command == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxUnicastPacketCount?"'
    assert "AssocTxPacketCount=" in step4_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'"
    assert verification_commands[1] == step3_command
    assert verification_commands[2] == step4_command
    assert verification_commands[3] == step5_command


def test_d059_txunicastpacketcount_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d059 = load_case(cases_dir / "D059_txunicastpacketcount.yaml")
    step2_command = d059["steps"][1]["command"]
    pipeline = step2_command.split("|", 1)[1].strip()
    sample_output = 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"'

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "MACAddress=2c:59:17:00:04:85"


def test_d059_txunicastpacketcount_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d059 = load_case(cases_dir / "D059_txunicastpacketcount.yaml")
    step4_command = d059["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
            "WiFi.AccessPoint.1.AssociatedDevice.1.TxUnicastPacketCount=0",
            "WiFi.AccessPoint.1.AssociatedDevice.1.TxPacketCount=90442",
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "AssocMAC=2c:59:17:00:04:85",
        "AssocTxUnicastPacketCount=0",
        "AssocTxPacketCount=90442",
    ]


def test_d064_vendoroui_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_vendoroui.yaml")

    step1_command = d064["steps"][0]["command"]
    step3_command = d064["steps"][2]["command"]
    step4_command = d064["steps"][3]["command"]
    step5_command = d064["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d064["verification_command"])

    assert step3_command == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"'
    assert "AssocVendorOUI=" in step4_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step3_command
    assert verification_commands[2] == step4_command
    assert verification_commands[3] == step5_command


def test_d064_vendoroui_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_vendoroui.yaml")
    step2_command = d064["steps"][1]["command"]
    pipeline = step2_command.split("|", 1)[1].strip()
    sample_output = 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"'

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "MACAddress=2c:59:17:00:04:85"


def test_d064_vendoroui_snapshot_fragment_executes_with_empty_value():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_vendoroui.yaml")
    step4_command = d064["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
            'WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI=""',
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "AssocMAC=2c:59:17:00:04:85",
        "AssocVendorOUI=",
    ]


def test_d064_vendoroui_driver_capture_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_vendoroui.yaml")
    step5_command = d064["steps"][4]["command"]
    awk_fragment = "awk " + step5_command.rsplit("| awk ", 1)[1]
    sample_output = "\n".join(
        [
            "\t state: AUTHENTICATED ASSOCIATED AUTHORIZED",
            "VENDOR OUI VALUE[0] 00:90:4C",
            "VENDOR OUI VALUE[1] 00:10:18",
            "VENDOR OUI VALUE[2] 00:50:F2",
            "VENDOR OUI VALUE[3] 50:6F:9A",
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {awk_fragment}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "DriverVendorOUICount=4",
        "DriverVendorOUIList=00:90:4C,00:10:18,00:50:F2,50:6F:9A",
    ]


def test_d065_vhtcapabilities_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml")

    step1_command = d065["steps"][0]["command"]
    step3_command = d065["steps"][2]["command"]
    step4_command = d065["steps"][3]["command"]
    step5_command = d065["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d065["verification_command"])

    assert step3_command == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"'
    assert "AssocVhtCapabilities=" in step4_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step3_command
    assert verification_commands[2] == step4_command
    assert verification_commands[3] == step5_command


def test_d065_vhtcapabilities_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml")
    step2_command = d065["steps"][1]["command"]
    pipeline = step2_command.split("|", 1)[1].strip()
    sample_output = 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"'

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "MACAddress=2c:59:17:00:04:85"


def test_d065_vhtcapabilities_snapshot_fragment_executes_with_empty_value():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml")
    step4_command = d065["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
            'WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities=""',
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "AssocMAC=2c:59:17:00:04:85",
        "AssocVhtCapabilities=",
    ]


def test_d065_vhtcapabilities_driver_capture_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_vhtcapabilities_accesspoint_associateddevice.yaml")
    step5_command = d065["steps"][4]["command"]
    awk_fragment = "awk " + step5_command.rsplit("| awk ", 1)[1]
    sample_output = "\n".join(
        [
            "\t HT caps 0x86f: LDPC 40MHz SGI20 SGI40",
            "\t VHT caps 0x67: LDPC SGI80 SGI160 SU-BFR SU-BFE",
            "\t HE caps 0xc6639: LDPC HE-HTC SU-BFR SU&MU-BFE",
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {awk_fragment}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "DriverVhtCapsLine=LDPC SGI80 SGI160 SU-BFR SU-BFE",
        "DriverVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE",
    ]


def test_d066_apbridgedisable_verification_fragments_preserve_toggle_and_cross_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_apbridgedisable.yaml")

    step1_command = d066["steps"][0]["command"]
    step2_command = d066["steps"][1]["command"]
    step3_command = d066["steps"][2]["command"]
    step4_command = d066["steps"][3]["command"]
    step5_command = d066["steps"][4]["command"]
    step8_command = d066["steps"][7]["command"]
    step9_command = d066["steps"][8]["command"]
    verification_commands = plugin._extract_cli_fragments(d066["verification_command"])

    assert step2_command == 'ubus-cli "WiFi.AccessPoint.1.APBridgeDisable?"'
    assert plugin._sanitize_cli_fragment(step4_command) == step4_command
    assert plugin._extract_cli_fragments(step4_command) == [step4_command]
    assert len(verification_commands) == 8
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step2_command
    assert verification_commands[2] == step3_command
    assert verification_commands[3] == step4_command
    assert verification_commands[4] == step5_command
    assert verification_commands[5] == "sleep 5"
    assert verification_commands[6] == step8_command
    assert verification_commands[7] == step9_command


def test_d066_apbridgedisable_hostapd_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_apbridgedisable.yaml")
    step4_command = d066["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(["ap_isolate=0", "ap_isolate=0"])

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "HostapdApIsolate=0",
        "HostapdApIsolate=0",
        "HostapdApIsolateZeroCount=2",
    ]


def test_d066_apbridgedisable_driver_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_apbridgedisable.yaml")
    step8_command = d066["steps"][7]["command"]
    pipeline = step8_command.split("|", 1)[1].strip()
    sample_output = "1"

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "DriverApIsolateOff=1"


def test_d067_bridgeinterface_verification_fragments_preserve_getters_and_cross_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_bridgeinterface.yaml")

    step1_command = d067["steps"][0]["command"]
    step2_command = d067["steps"][1]["command"]
    step3_command = d067["steps"][2]["command"]
    step4_command = d067["steps"][3]["command"]
    step5_command = d067["steps"][4]["command"]
    step6_command = d067["steps"][5]["command"]
    step7_command = d067["steps"][6]["command"]
    verification_commands = plugin._extract_cli_fragments(d067["verification_command"])

    step7_fragments = [fragment.strip() for fragment in step7_command.split("&&")]
    assert len(verification_commands) == 9
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step2_command
    assert verification_commands[2] == step3_command
    assert verification_commands[3] == step4_command
    assert verification_commands[4] == step5_command
    assert verification_commands[5] == step6_command
    assert verification_commands[6:] == step7_fragments


def test_d067_bridgeinterface_hostapd_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_bridgeinterface.yaml")
    step4_command = d067["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(["bridge=br-lan", "bridge=br-lan"])

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "BridgeConfig5g=br-lan",
        "BridgeConfig5gCount=2",
        "BridgeConfig5gMismatch=0",
    ]

    mismatch_output = "\n".join(["bridge=br-guest", "bridge=br-lan"])
    mismatch_proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{mismatch_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert mismatch_proc.returncode == 0, mismatch_proc.stderr
    assert mismatch_proc.stdout.strip().splitlines() == [
        "BridgeConfig5g=br-guest",
        "BridgeConfig5gCount=2",
        "BridgeConfig5gMismatch=1",
    ]


def test_d067_bridgeinterface_bridge_master_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_bridgeinterface.yaml")
    step7_command = d067["steps"][6]["command"]
    fragments = [fragment.strip() for fragment in step7_command.split("&&")]
    outputs = []
    for fragment, expected in zip(
        fragments,
        [
            "BridgeMaster5g=br-lan",
            "BridgeMaster6g=br-lan",
            "BridgeMaster24g=br-lan",
        ],
    ):
        pipeline = fragment.split("|", 1)[1].strip()
        proc = subprocess.run(
            [
                "sh",
                "-lc",
                f"cat <<'EOF' | {pipeline}\nINTERFACE=br-lan\nEOF",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        outputs.append(proc.stdout.strip())

    assert outputs == [
        "BridgeMaster5g=br-lan",
        "BridgeMaster6g=br-lan",
        "BridgeMaster24g=br-lan",
    ]


def test_d068_discoverymethodenabled_accesspoint_fils_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_fils.yaml")

    verification_commands = plugin._extract_cli_fragments(d068["verification_command"])

    expected_commands = [
        d068["steps"][0]["command"],
        d068["steps"][1]["command"],
        d068["steps"][2]["command"],
        d068["steps"][3]["command"],
        d068["steps"][4]["command"],
        d068["steps"][5]["command"],
        d068["steps"][9]["command"],
        d068["steps"][10]["command"],
        d068["steps"][11]["command"],
        d068["steps"][15]["command"],
        d068["steps"][16]["command"],
        d068["steps"][17]["command"],
    ]

    assert len(verification_commands) == 13
    assert verification_commands[:-1] == expected_commands
    assert verification_commands[-1] == 'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?"'


def test_d069_discoverymethodenabled_accesspoint_upr_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d069 = load_case(cases_dir / "D069_discoverymethodenabled_accesspoint_upr.yaml")

    verification_commands = plugin._extract_cli_fragments(d069["verification_command"])
    expected_commands = [
        d069["steps"][0]["command"],
        d069["steps"][1]["command"],
        d069["steps"][2]["command"],
        d069["steps"][3]["command"],
        d069["steps"][4]["command"],
        d069["steps"][5]["command"],
        'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?"',
        d069["steps"][9]["command"],
        d069["steps"][10]["command"],
        d069["steps"][11]["command"],
    ]

    assert len(verification_commands) == 11
    assert verification_commands[:-1] == expected_commands
    assert verification_commands[-1] == 'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?" | sed -n \'1,20p\''


def test_d070_discoverymethodenabled_accesspoint_rnr_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_discoverymethodenabled_accesspoint_rnr.yaml")

    verification_commands = plugin._extract_cli_fragments(d070["verification_command"])
    expected_commands = [
        d070["steps"][0]["command"],
        d070["steps"][1]["command"],
        d070["steps"][2]["command"],
        d070["steps"][3]["command"],
        d070["steps"][4]["command"],
        d070["steps"][5]["command"],
        'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?"',
        d070["steps"][9]["command"],
        d070["steps"][10]["command"],
        d070["steps"][11]["command"],
        d070["steps"][12]["command"],
        d070["steps"][13]["command"],
        d070["steps"][14]["command"],
        'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?" | sed -n \'1,20p\'',
        d070["steps"][15]["command"] + " | sed -n '1,20p'",
    ]

    assert verification_commands == expected_commands


def test_d070_discoverymethodenabled_accesspoint_rnr_config_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_discoverymethodenabled_accesspoint_rnr.yaml")
    step11_command = d070["steps"][10]["command"]
    sample_output = "\n".join(["rnr=1", "rnr=0"])

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output + "\n")
        temp_path = handle.name

    try:
        adapted_command = step11_command.replace("/tmp/wl1_hapd.conf", temp_path)
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "RnrEnabled6gCount=1",
        "RnrDisabled6gCount=1",
        "RnrTotal6gCount=2",
    ]


def test_d072_enable_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")

    verification_commands = plugin._extract_cli_fragments(d072["verification_command"])
    expected_commands = [
        d072["steps"][0]["command"],
        d072["steps"][1]["command"],
        d072["steps"][2]["command"],
        d072["steps"][3]["command"],
        d072["steps"][4]["command"],
        d072["steps"][5]["command"],
        d072["steps"][6]["command"],
        d072["steps"][7]["command"],
        d072["steps"][8]["command"] + " | sed -n '1,20p'",
        d072["steps"][9]["command"] + " | sed -n '1,20p'",
        d072["steps"][10]["command"] + " | sed -n '1,20p'",
        d072["steps"][11]["command"],
        d072["steps"][12]["command"],
        d072["steps"][13]["command"],
        d072["steps"][14]["command"],
        d072["steps"][15]["command"],
        d072["steps"][16]["command"] + " | sed -n '1,20p'",
        d072["steps"][17]["command"] + " | sed -n '1,20p'",
        d072["steps"][18]["command"] + " | sed -n '1,20p'",
        d072["steps"][19]["command"],
        d072["steps"][20]["command"],
        d072["steps"][21]["command"],
        d072["steps"][22]["command"],
        d072["steps"][23]["command"],
        d072["steps"][24]["command"] + " | sed -n '1,20p'",
        d072["steps"][25]["command"] + " | sed -n '1,20p'",
        d072["steps"][26]["command"] + " | sed -n '1,20p'",
    ]

    assert verification_commands == expected_commands


def test_d072_enable_accesspoint_state_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")
    step5_command = d072["steps"][4]["command"]
    pipeline = step5_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            "WiFi.AccessPoint.1.Enable=0",
            'WiFi.AccessPoint.1.Status="Disabled"',
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | {pipeline}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Enable5g=0",
        'Status5g="Disabled"',
    ]


def test_d072_enable_accesspoint_disable_config_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")
    step7_command = d072["steps"][6]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("start_disabled=1\n")
        temp_path = handle.name

    try:
        adapted_command = step7_command.replace("/tmp/wl0_hapd.conf", temp_path)
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "StartDisabled5g=1",
        "StartDisabled5gOneCount=1",
        "StartDisabled5gZeroCount=0",
        "StartDisabled5gTotalCount=1",
    ]


def test_d072_enable_accesspoint_enable_config_fragment_executes_without_start_disabled():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_enable_accesspoint.yaml")
    step11_command = d072["steps"][10]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("")
        temp_path = handle.name

    try:
        adapted_command = step11_command.replace("/tmp/wl0_hapd.conf", temp_path)
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "StartDisabled5gOneCount=0",
        "StartDisabled5gZeroCount=0",
        "StartDisabled5gTotalCount=0",
    ]


def test_d073_ftoverdsenable_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")

    verification_commands = plugin._extract_cli_fragments(d073["verification_command"])
    step_commands = [step["command"] for step in d073["steps"]]

    def fragments(command: str, suffix: str = "") -> list[str]:
        return [f"{part.strip()}{suffix}" for part in command.split(";") if part.strip()]

    expected_commands = []
    for start in (0, 10, 20):
        expected_commands.extend(
            [
                step_commands[start],
                step_commands[start + 1],
            ]
        )
        expected_commands.extend(fragments(step_commands[start + 2]))
        expected_commands.extend(fragments(step_commands[start + 3]))
        expected_commands.extend(
            [
                step_commands[start + 4],
            ]
        )
        expected_commands.extend(fragments(step_commands[start + 5], " | sed -n '1,20p'"))
        expected_commands.extend(fragments(step_commands[start + 6], " | sed -n '1,20p'"))
        expected_commands.append(step_commands[start + 7])
        expected_commands.extend(fragments(step_commands[start + 8], " | sed -n '1,21p'"))
        expected_commands.extend(fragments(step_commands[start + 9], " | sed -n '1,21p'"))
    for start in (30, 32, 34):
        expected_commands.extend(fragments(step_commands[start]))
        expected_commands.extend(fragments(step_commands[start + 1], " | sed -n '1,22p'"))

    assert verification_commands == expected_commands


def test_d073_ftoverdsenable_accesspoint_state_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")
    step3_command = d073["steps"][2]["command"]
    sample_output = "\n".join(
        [
            "WiFi.AccessPoint.1.IEEE80211r.Enabled=1",
            "WiFi.AccessPoint.1.IEEE80211r.FTOverDSEnable=0",
            "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=4660",
        ]
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = (
            step3_command.replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?"', f"cat {temp_path}")
            .replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.FTOverDSEnable?"', f"cat {temp_path}")
            .replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain?"', f"cat {temp_path}")
        )
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Enabled5g=1",
        "FtOverDs5g=0",
        "MobilityDomain5g=4660",
    ]


def test_d073_ftoverdsenable_accesspoint_config_snapshot_zero_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")
    step4_command = d073["steps"][3]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("mobility_domain=3412\nft_over_ds=0\n")
        temp_path = handle.name

    try:
        adapted_command = step4_command.replace("/tmp/wl0_hapd.conf", temp_path)
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "MobilityDomainCfg5g=3412",
        "FtOverDs5gOneCount=0",
        "FtOverDs5gZeroCount=1",
        "FtOverDs5gTotalCount=1",
    ]


def test_d073_ftoverdsenable_accesspoint_config_snapshot_one_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d073 = load_case(cases_dir / "D073_ftoverdsenable.yaml")
    step7_command = d073["steps"][6]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("mobility_domain=3412\nft_over_ds=1\n")
        temp_path = handle.name

    try:
        adapted_command = step7_command.replace("/tmp/wl0_hapd.conf", temp_path)
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "MobilityDomainCfg5g=3412",
        "FtOverDs5gOneCount=1",
        "FtOverDs5gZeroCount=0",
        "FtOverDs5gTotalCount=1",
    ]


def test_d074_mobilitydomain_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")

    verification_commands = plugin._extract_cli_fragments(d074["verification_command"])
    step_commands = [step["command"] for step in d074["steps"]]

    def fragments(command: str, suffix: str = "") -> list[str]:
        return [f"{part.strip()}{suffix}" for part in command.split(";") if part.strip()]

    expected_commands = []
    for start in (0, 9, 18):
        expected_commands.append(step_commands[start])
        expected_commands.extend(fragments(step_commands[start + 1]))
        expected_commands.append(step_commands[start + 2])
        expected_commands.extend(fragments(step_commands[start + 3], " | sed -n '1,20p'"))
        expected_commands.extend(fragments(step_commands[start + 4]))
        expected_commands.append(step_commands[start + 5])
        expected_commands.extend(fragments(step_commands[start + 6], " | sed -n '1,21p'"))
        expected_commands.append(step_commands[start + 7])
        expected_commands.extend(fragments(step_commands[start + 8], " | sed -n '1,22p'"))

    assert verification_commands == expected_commands


def test_d074_mobilitydomain_accesspoint_state_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")
    step2_command = d074["steps"][1]["command"]
    sample_output = "\n".join(
        [
            "WiFi.AccessPoint.1.IEEE80211r.Enabled=1",
            "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=0",
        ]
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = (
            step2_command.replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?"', f"cat {temp_path}")
            .replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain?"', f"cat {temp_path}")
        )
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Enabled5g=1",
        "MobilityDomain5g=0",
    ]


def test_d074_mobilitydomain_accesspoint_config_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")
    step5_command = d074["steps"][4]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("mobility_domain=546B\nft_over_ds=0\n")
        temp_path = handle.name

    try:
        adapted_command = step5_command.replace("/tmp/wl0_hapd.conf", temp_path)
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "MobilityDomainCfg5g=546B",
        "FtOverDs5gZeroCount=1",
        "FtOverDs5gTotalCount=1",
    ]


def test_d074_mobilitydomain_accesspoint_cleanup_state_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    d074 = load_case(cases_dir / "D074_mobilitydomain.yaml")
    step9_command = d074["steps"][8]["command"]
    sample_output = "\n".join(
        [
            "WiFi.AccessPoint.1.IEEE80211r.Enabled=0",
            "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=0",
        ]
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = (
            step9_command.replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?"', f"cat {temp_path}")
            .replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain?"', f"cat {temp_path}")
        )
        proc = subprocess.run(
            ["sh", "-lc", adapted_command],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Enabled5g=0",
        "MobilityDomain5g=0",
    ]


@pytest.mark.parametrize(
    ("filename", "sample_output", "expected_lines"),
    [
        (
            "D049_supportedhe160mcs.yaml",
            "\n".join(
                [
                    'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    'WiFi.AccessPoint.1.AssociatedDevice.1.RxSupportedHe160MCS="11,11,11,11"',
                    'WiFi.AccessPoint.1.AssociatedDevice.1.TxSupportedHe160MCS="11,11,11,11"',
                ]
            ),
            [
                "SiblingAssocMac=2C:59:17:00:04:85",
                "DriverRxSupportedHe160MCS=11,11,11,11",
                "DriverTxSupportedHe160MCS=11,11,11,11",
            ],
        ),
        (
            "D050_supportedhemcs.yaml",
            "\n".join(
                [
                    'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    'WiFi.AccessPoint.1.AssociatedDevice.1.RxSupportedHeMCS="11,11,11,11"',
                    'WiFi.AccessPoint.1.AssociatedDevice.1.TxSupportedHeMCS="11,11,11,11"',
                ]
            ),
            [
                "SiblingAssocMac=2C:59:17:00:04:85",
                "DriverRxSupportedHeMCS=11,11,11,11",
                "DriverTxSupportedHeMCS=11,11,11,11",
            ],
        ),
        (
            "D052_supportedvhtmcs.yaml",
            "\n".join(
                [
                    'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    'WiFi.AccessPoint.1.AssociatedDevice.1.RxSupportedVhtMCS="9,9,9,9"',
                    'WiFi.AccessPoint.1.AssociatedDevice.1.TxSupportedVhtMCS="9,9,9,9"',
                ]
            ),
            [
                "SiblingAssocMac=2C:59:17:00:04:85",
                "DriverRxSupportedVhtMCS=9,9,9,9",
                "DriverTxSupportedVhtMCS=9,9,9,9",
            ],
        ),
        (
            "D056_txerrors.yaml",
            "\n".join(
                [
                    'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors=0",
                ]
            ),
            [
                "AssocMAC=2C:59:17:00:04:85",
                "AssocTxErrors=0",
            ],
        ),
    ],
)
def test_associateddevice_sibling_sed_fragments_execute(
    filename: str, sample_output: str, expected_lines: list[str]
):
    cases_dir = Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / filename)
    step4_command = case_data["steps"][3]["command"]
    sed_script = step4_command.split("| sed -n ", 1)[1]

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f"cat <<'EOF' | sed -n {sed_script}\n{sample_output}\nEOF",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == expected_lines


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
