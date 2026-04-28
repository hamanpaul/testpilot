"""Runtime behavior tests for wifi_llapi plugin execution/evaluation."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile
import sys
import types
from typing import Any

import pytest
import yaml

from testpilot.core.case_utils import case_band_results
from testpilot.core.plugin_loader import PluginLoader
from testpilot.schema.case_schema import load_case, validate_wifi_llapi_case


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
        if command.startswith("wl -i wl") and command.endswith(" status"):
            if self.config.get("simulate_wl_status_fail"):
                return {
                    "returncode": 0,
                    "stdout": 'Not associated. Last associated with SSID: ""',
                    "stderr": "",
                    "elapsed": 0.01,
                }
            return {
                "returncode": 0,
                "stdout": 'SSID: "TestPilot_5G"\nMode: Managed\nBSSID: 2C:59:17:00:04:85\nChannel: 36',
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
    root = Path(__file__).resolve().parents[3]
    loader = PluginLoader(root / "plugins")
    return loader.load("wifi_llapi")


_ASSOC_MAC_REGEX = r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"


def _has_assoc_mac_regex(case_data: dict[str, Any], field: str) -> bool:
    return any(
        criterion["field"] == field
        and criterion["operator"] == "regex"
        and criterion["value"] == _ASSOC_MAC_REGEX
        for criterion in case_data["pass_criteria"]
    )


def _expected_case_band_results(case: dict[str, Any], verdict: bool) -> tuple[str, str, str]:
    status = "Pass" if verdict else "Fail"
    bands = case.get("bands")
    if not isinstance(bands, list) or not bands:
        return status, status, status
    normalized = {str(band).strip().lower() for band in bands}
    return (
        status if "5g" in normalized else "N/A",
        status if "6g" in normalized else "N/A",
        status if "2.4g" in normalized else "N/A",
    )


def test_plugin_loads_shared_wifi_band_baselines_yaml():
    plugin = _load_plugin()

    assert plugin.DEFAULT_BAND_BASELINES["5g"]["ssid"] == "testpilot5G"
    assert plugin.DEFAULT_BAND_BASELINES["5g"]["dut_secret_fields"] == ["KeyPassPhrase"]
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["iface"] == "wl1"
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["dut_secret_fields"] == [
        "SAEPassphrase",
        "KeyPassPhrase",
    ]
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["dut_pre_start_commands"] == [
        "ubus-cli WiFi.AccessPoint.3.MultiAPType=None"
    ]
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["dut_runtime_config_commands"] == [
        "sed -i 's/^sae_pwe=.*/sae_pwe=2/g' /tmp/wl1_hapd.conf",
        "sed -i 's/^ieee80211be=.*/ieee80211be=0/g' /tmp/wl1_hapd.conf",
        "sed -i '/^bss=wl1\\.1$/,$d' /tmp/wl1_hapd.conf",
    ]
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["dut_runtime_ready_commands"] == [
        "grep -q '^sae_pwe=2$' /tmp/wl1_hapd.conf",
        '! grep -Eq "^ieee80211be=1$" /tmp/wl1_hapd.conf',
        '! grep -Eq "^bss=wl1\\.1$" /tmp/wl1_hapd.conf',
        '! grep -Eq "^multi_ap=[1-9]" /tmp/wl1_hapd.conf',
    ]
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["sta_pre_mode_commands"] == [
        "ifconfig {{iface}} down",
        "wl -i {{iface}} down",
        "wl -i {{iface}} ap 0",
    ]
    assert plugin.DEFAULT_BAND_BASELINES["6g"]["sta_pre_start_commands"] == [
        "wl -i {{iface}} up",
        "ifconfig {{iface}} up",
    ]
    assert plugin.DEFAULT_BAND_BASELINES["2.4g"]["ssid"] == "testpilot2G"


def test_discover_cases_uses_wifi_llapi_validator(monkeypatch):
    plugin = _load_plugin()
    captured: dict[str, Any] = {}

    def fake_load_cases_dir(cases_dir: Path, *, validator=None) -> list[dict[str, Any]]:
        captured["cases_dir"] = cases_dir
        captured["validator"] = validator
        return []

    monkeypatch.setitem(plugin.discover_cases.__globals__, "load_cases_dir", fake_load_cases_dir)

    assert plugin.discover_cases() == []
    assert captured["cases_dir"] == plugin.cases_dir
    assert captured["validator"] is validate_wifi_llapi_case


def _install_fake_factory(monkeypatch, recorder: _FactoryRecorder) -> None:
    module = types.ModuleType("testpilot.transport.factory")
    module.create_transport = recorder.create_transport
    monkeypatch.setitem(sys.modules, "testpilot.transport.factory", module)


def _stringify_command(command: str | list[str]) -> str:
    """Normalize a step command (str or list[str]) into a single string."""
    if isinstance(command, list):
        return "\n".join(command)
    return command


def _expected_step_fragments(plugin: Any, command: str | list[str], suffix: str = "") -> list[str]:
    fragments: list[str] = []
    for part in plugin._split_step_command_sequence(_stringify_command(command)):
        rendered = f"{part}{suffix}" if suffix else part
        fragments.extend(plugin._extract_cli_fragments(rendered))
    return fragments


def _execute_step_shell_sequence(
    plugin: Any,
    command: str | list[str],
    replacements: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    returncode = 0
    cmd_str = _stringify_command(command)

    for part in plugin._split_step_command_sequence(cmd_str):
        adapted = part
        for original, replacement in replacements.items():
            adapted = adapted.replace(original, replacement)
        proc = subprocess.run(
            ["sh", "-lc", adapted],
            check=False,
            capture_output=True,
            text=True,
        )
        stdout_chunks.append(proc.stdout)
        stderr_chunks.append(proc.stderr)
        returncode = proc.returncode
        if proc.returncode != 0:
            break

    return subprocess.CompletedProcess(
        args=["sh", "-lc", cmd_str],
        returncode=returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def test_qualify_baseline_reaches_repeat_target(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    qualifier_cls = plugin.qualify_baseline.__globals__["BaselineQualifier"]

    setup_calls: list[str] = []
    verify_calls: list[str] = []
    teardown_calls: list[str] = []

    def fake_setup(case: dict[str, Any], topology: Any) -> bool:
        del topology
        setup_calls.append(str(case.get("id", "")))
        plugin._transports = {"DUT": object(), "STA": object()}
        return True

    def fake_verify(case: dict[str, Any], topology: Any) -> bool:
        del topology
        verify_calls.append(str(case.get("id", "")))
        return True

    def fake_teardown(case: dict[str, Any], topology: Any) -> None:
        del topology
        teardown_calls.append(str(case.get("id", "")))
        plugin._transports.clear()

    def fake_snapshot(self, case: dict[str, Any], band: str, *, phase: str) -> dict[str, Any]:
        del self, case, band
        return {
            "phase": phase,
            "trusted": True,
            "issues": [],
            "hard_failures": [],
            "commands": {},
        }

    def fake_soak(self, case: dict[str, Any], band: str, soak_minutes: int) -> dict[str, Any]:
        del self, case, band, soak_minutes
        return {
            "success": True,
            "duration_seconds": 0,
            "checks": [],
        }

    monkeypatch.setattr(plugin, "setup_env", fake_setup)
    monkeypatch.setattr(plugin, "verify_env", fake_verify)
    monkeypatch.setattr(plugin, "teardown", fake_teardown)
    monkeypatch.setattr(qualifier_cls, "_collect_snapshot", fake_snapshot)
    monkeypatch.setattr(qualifier_cls, "_run_soak", fake_soak)

    result = plugin.qualify_baseline(
        topology,
        bands=("5g",),
        repeat_count=2,
        soak_minutes=0,
    )

    assert result["overall_status"] == "stable"
    assert len(result["bands"]) == 1
    assert result["bands"][0]["band"] == "5g"
    assert result["bands"][0]["stable"] is True
    assert result["bands"][0]["completed_rounds"] == 2
    assert len(result["bands"][0]["rounds"]) == 2
    assert setup_calls == [
        "wifi-llapi-baseline-qualify-5g",
        "wifi-llapi-baseline-qualify-5g",
    ]
    assert verify_calls == [
        "wifi-llapi-baseline-qualify-5g",
        "wifi-llapi-baseline-qualify-5g",
    ]
    assert teardown_calls == [
        "wifi-llapi-baseline-qualify-5g",
        "wifi-llapi-baseline-qualify-5g",
    ]


def test_qualify_baseline_uses_factory_reset_for_untrusted_preflight(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    qualifier_cls = plugin.qualify_baseline.__globals__["BaselineQualifier"]

    def fake_setup(case: dict[str, Any], topology: Any) -> bool:
        del case, topology
        plugin._transports = {"DUT": object(), "STA": object()}
        return True

    def fake_verify(case: dict[str, Any], topology: Any) -> bool:
        del case, topology
        return True

    def fake_teardown(case: dict[str, Any], topology: Any) -> None:
        del case, topology
        plugin._transports.clear()

    snapshots = iter(
        [
            {
                "phase": "preflight",
                "trusted": False,
                "issues": ["dut_gate_failed"],
                "hard_failures": [],
                "commands": {},
            },
            {
                "phase": "preflight-recheck",
                "trusted": False,
                "issues": ["dut_gate_failed"],
                "hard_failures": [],
                "commands": {},
            },
            {
                "phase": "preflight-after-reset",
                "trusted": True,
                "issues": [],
                "hard_failures": [],
                "commands": {},
            },
            {
                "phase": "post-verify",
                "trusted": True,
                "issues": [],
                "hard_failures": [],
                "commands": {},
            },
        ]
    )
    reset_calls: list[str] = []

    def fake_snapshot(self, case: dict[str, Any], band: str, *, phase: str) -> dict[str, Any]:
        del self, case, band, phase
        return next(snapshots)

    def fake_recover(self, case: dict[str, Any], *, devices: tuple[str, ...], reason: str) -> dict[str, Any]:
        del self, case, devices
        return {
            "success": True,
            "reason": reason,
        }

    def fake_reset(self, case: dict[str, Any], *, reason: str) -> dict[str, Any]:
        del self, case
        reset_calls.append(reason)
        return {
            "success": True,
            "reason": reason,
            "devices": [],
        }

    def fake_soak(self, case: dict[str, Any], band: str, soak_minutes: int) -> dict[str, Any]:
        del self, case, band, soak_minutes
        return {
            "success": True,
            "duration_seconds": 0,
            "checks": [],
        }

    monkeypatch.setattr(plugin, "setup_env", fake_setup)
    monkeypatch.setattr(plugin, "verify_env", fake_verify)
    monkeypatch.setattr(plugin, "teardown", fake_teardown)
    monkeypatch.setattr(qualifier_cls, "_collect_snapshot", fake_snapshot)
    monkeypatch.setattr(qualifier_cls, "_recover_and_reopen", fake_recover)
    monkeypatch.setattr(qualifier_cls, "_factory_reset_and_reopen", fake_reset)
    monkeypatch.setattr(qualifier_cls, "_run_soak", fake_soak)

    result = plugin.qualify_baseline(
        topology,
        bands=("6g",),
        repeat_count=1,
        soak_minutes=0,
    )

    assert result["overall_status"] == "stable"
    assert reset_calls == ["preflight_untrusted"]
    round_result = result["bands"][0]["rounds"][0]
    assert round_result["preflight_restore"]["strategy"] == "factory_reset"
    assert round_result["success"] is True


def test_qualify_baseline_records_runtime_exception_instead_of_crashing(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    qualifier_cls = plugin.qualify_baseline.__globals__["BaselineQualifier"]

    def fake_setup(case: dict[str, Any], topology: Any) -> bool:
        del case, topology
        plugin._transports = {"DUT": object(), "STA": object()}
        return True

    def fake_verify(case: dict[str, Any], topology: Any) -> bool:
        del case, topology
        raise RuntimeError("serialwrap cmd submit failed")

    def fake_teardown(case: dict[str, Any], topology: Any) -> None:
        del case, topology
        plugin._transports.clear()

    def fake_snapshot(self, case: dict[str, Any], band: str, *, phase: str) -> dict[str, Any]:
        del self, case, band
        return {
            "phase": phase,
            "trusted": True,
            "issues": [],
            "hard_failures": [],
            "commands": {},
        }

    def fake_recover(self, case: dict[str, Any], *, devices: tuple[str, ...], reason: str) -> dict[str, Any]:
        del self, case, devices, reason
        return {
            "success": False,
            "recovery": {"devices": []},
        }

    def fake_reset(self, case: dict[str, Any], *, reason: str) -> dict[str, Any]:
        del self, case, reason
        return {
            "success": False,
            "devices": [],
        }

    monkeypatch.setattr(plugin, "setup_env", fake_setup)
    monkeypatch.setattr(plugin, "verify_env", fake_verify)
    monkeypatch.setattr(plugin, "teardown", fake_teardown)
    monkeypatch.setattr(qualifier_cls, "_collect_snapshot", fake_snapshot)
    monkeypatch.setattr(qualifier_cls, "_recover_and_reopen", fake_recover)
    monkeypatch.setattr(qualifier_cls, "_factory_reset_and_reopen", fake_reset)

    result = plugin.qualify_baseline(
        topology,
        bands=("6g",),
        repeat_count=1,
        soak_minutes=0,
    )

    assert result["overall_status"] == "unstable"
    last_failure = result["bands"][0]["last_failure"]
    assert last_failure["phase"] == "verify_env"
    assert last_failure["reason_code"] == "runtime_exception"
    assert "serialwrap cmd submit failed" in last_failure["output"]


def test_collect_snapshot_keeps_secondary_6g_bss_as_warning(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    qualifier_cls = plugin.qualify_baseline.__globals__["BaselineQualifier"]
    qualifier = qualifier_cls(plugin, topology)
    plugin._transports = {"DUT": object(), "STA": object()}

    def fake_snapshot_command(transport: Any, command: str, timeout: float = 10.0) -> dict[str, Any]:
        del transport, timeout
        output = ""
        if command == 'echo "__testpilot_baseline_gate__"':
            output = "__testpilot_baseline_gate__"
        elif command == "iw dev":
            output = "Interface wl1\ntype managed\n"
        elif command == "iw dev wl1 link":
            output = "Connected to 2c:59:17:00:19:96 (on wl1)\nSSID: testpilot6G\nfreq: 5955"
        elif command == "wl -i wl1 status":
            output = 'SSID: "testpilot6G"\nMode: Managed'
        elif command == "grep -nE '^(ssid=|wpa_key_mgmt=|sae_pwe=|ieee80211w=|ocv=|ieee80211be=|bss=|multi_ap=|mld_unit=|mlo_aff_link_kde=)' /tmp/wl1_hapd.conf 2>/dev/null || true":
            output = "\n".join(
                [
                    "16:ssid=testpilot6G",
                    "23:wpa_key_mgmt=SAE",
                    "34:ieee80211w=2",
                    "35:ocv=0",
                    "36:sae_pwe=1",
                    "57:bss=wl1.1",
                ]
            )
        return {
            "command": command,
            "returncode": 0,
            "status": "done",
            "success": True,
            "output": output,
        }

    monkeypatch.setattr(qualifier, "_snapshot_command", fake_snapshot_command)

    snapshot = qualifier._collect_snapshot({}, "6g", phase="post-verify")

    assert "dut_secondary_bss_present" in snapshot["issues"]
    assert "dut_ocv_not_zero" not in snapshot["issues"]
    assert snapshot["hard_failures"] == []


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


def test_execute_step_supports_multiline_shell_sequence(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-multiline-step",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "steps": [
            {
                "id": "s1",
                "target": "DUT",
                "command": (
                    "STA_MAC=aa:bb:cc:dd:ee:ff\n"
                    "STA_MAC_LOWER=$(echo \"$STA_MAC\" | tr 'A-F' 'a-f')\n"
                    "echo DriverAssocMac=$STA_MAC\n"
                    "echo DriverAssocMacLower=$STA_MAC_LOWER"
                ),
            }
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True
    result = plugin.execute_step(case, case["steps"][0], topology=topology)
    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    wrapped_command = plugin._wrap_multiline_shell_command(case["steps"][0]["command"])
    assert result["success"] is True
    assert dut.executed_commands == [wrapped_command]
    assert result["command"] == wrapped_command
    plugin.teardown(case, topology=topology)


def test_execute_step_skip_action_bypasses_band_prepare(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-skip-band-prepare",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            },
            "links": [
                {"from": "STA", "to": "DUT", "band": "5g"},
                {"from": "STA", "to": "DUT", "band": "6g"},
                {"from": "STA", "to": "DUT", "band": "2.4g"},
            ],
        },
        "steps": [
            {
                "id": "skip6g",
                "action": "skip",
                "target": "DUT",
                "band": "6g",
                "reason": "explicit skip should not trigger band prepare",
            }
        ],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    prepare_calls: list[str] = []

    def fake_prepare(case_arg: dict[str, Any], topology_arg: Any, band: str) -> bool:
        del case_arg, topology_arg
        prepare_calls.append(str(band))
        return False

    assert plugin.setup_env(case, topology=topology) is True
    monkeypatch.setattr(plugin, "_prepare_case_band", fake_prepare)

    result = plugin.execute_step(case, case["steps"][0], topology=topology)

    assert result["success"] is True
    assert result["command"] == 'echo "[skip] non-executable step skip6g"'
    assert result["output"] == "[skip] non-executable step skip6g"
    assert result["fallback_reason"] == "fallback_skip_echo"
    assert prepare_calls == []
    plugin.teardown(case, topology=topology)


def test_execute_step_resolves_runtime_capture_placeholders(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-placeholders",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [
            {"id": "step_assoc", "capture": "assoc_5g"},
            {
                "id": "step_kick",
                "target": "DUT",
                "command": 'ubus-cli "WiFi.AccessPoint.1.kickStation(MACAddress={{assoc_5g.AssocMac5g}})"',
            },
        ],
        "_step_results": {
            "step_assoc": {
                "success": True,
                "output": "AssocMac5g=84:0d:8e:aa:bb:cc",
                "captured": {"AssocMac5g": "84:0d:8e:aa:bb:cc"},
                "returncode": 0,
            }
        },
    }

    assert plugin.setup_env(case, topology=topology) is True

    result = plugin.execute_step(case, case["steps"][1], topology=topology)

    assert result["success"] is True
    dut_transport = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    assert (
        dut_transport.executed_commands[-1]
        == 'ubus-cli "WiFi.AccessPoint.1.kickStation(MACAddress=84:0d:8e:aa:bb:cc)"'
    )

    plugin.teardown(case, topology=topology)


def test_execute_step_fails_on_unresolved_runtime_placeholder(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-unresolved-placeholder",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [
            {
                "id": "step_kick",
                "target": "DUT",
                "command": 'ubus-cli "WiFi.AccessPoint.5.kickStation(MACAddress={{assoc_24g.AssocMac24g}})"',
            }
        ],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    assert plugin.setup_env(case, topology=topology) is True

    result = plugin.execute_step(case, case["steps"][0], topology=topology)

    assert result["success"] is False
    assert result["returncode"] == 1
    assert "unresolved runtime placeholder" in result["output"]
    dut_transport = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    assert dut_transport.executed_commands == []

    plugin.teardown(case, topology=topology)


def test_execute_step_marks_wl_status_not_associated_as_failure(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-wl-status-fail",
        "topology": {"devices": {"STA": {"transport": "adb"}}},
        "steps": [
            {
                "id": "step_join",
                "action": "exec",
                "target": "STA",
                "command": (
                    "wl -i wl2 down; sleep 1; wl -i wl2 up; sleep 1; "
                    "wl -i wl2 join TestPilot_24G imode bss; sleep 3; wl -i wl2 status"
                ),
            }
        ],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    sta_transport = next(
        transport for transport in recorder.transports if transport.transport_type == "adb"
    )
    sta_transport.config["simulate_wl_status_fail"] = True

    result = plugin.execute_step(case, case["steps"][0], topology=topology)

    assert result["success"] is False
    assert result["returncode"] == 1
    assert "Not associated" in result["output"]
    assert sta_transport.executed_commands[-1] == "wl -i wl2 status"

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


def test_evaluate_contains_normalizes_multiline_bracket_output(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-evaluate-bracket-output",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result_5g"}],
        "pass_criteria": [
            {"field": "result_5g", "operator": "contains", "value": "[-1]"},
            {"field": "result_5g", "operator": "not_contains", "value": "ERROR"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True

    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": "WiFi.AccessPoint.1.sendBssTransferRequest() returned\n[\n-1\n]\n",
                "captured": {},
                "timing": 0.01,
            }
        }
    }

    assert plugin.evaluate(case, results) is True

    plugin.teardown(case, topology=topology)


def test_evaluate_base_capture_uses_raw_output_instead_of_polluted_kv_dict(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-evaluate-capture-raw",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [{"id": "s1", "capture": "result_5g"}],
        "pass_criteria": [
            {"field": "result_5g", "operator": "contains", "value": "[-1]"},
        ],
    }

    assert plugin.setup_env(case, topology=topology) is True

    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": (
                    "WiFi.AccessPoint.1.MBOEnable=1\n"
                    "AssocMac5g=2c:59:17:00:19:95\n"
                    "00:19:95,target=2c:59:17:00:19:a7,class=1,channel=36,wait=0\n"
                    "WiFi.AccessPoint.1.sendBssTransferRequest() returned\n"
                    "[\n-1\n]\n"
                ),
                "captured": {
                    "WiFi.AccessPoint.1.MBOEnable": "1",
                    "AssocMac5g": "2c:59:17:00:19:95",
                },
                "timing": 0.01,
            }
        }
    }

    assert plugin.evaluate(case, results) is True

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
    assert dut.executed_commands[:4] == [
        "ubus-cli WiFi.Radio.1.Enable=1",
        "ubus-cli WiFi.AccessPoint.1.Security.MFPConfig=Disabled",
        "wl -i wl0 bss",
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
    assert "wl -i wl0 bss" in dut.executed_commands
    plugin.teardown(case, topology=topology)


def test_setup_env_applies_6g_ocv_fix_before_custom_sta_connect(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    events: list[tuple[str, str, str]] = []

    def fake_apply_6g_ocv_fix(dut, case_id):
        events.append(("ocv", dut.transport_type, case_id))

    def fake_ensure_selected_dut_bss_ready(case):
        events.append(("ensure_bss", "", str(case.get("id", ""))))
        return True

    monkeypatch.setattr(plugin, "_apply_6g_ocv_fix", fake_apply_6g_ocv_fix)
    monkeypatch.setattr(plugin, "_ensure_selected_dut_bss_ready", fake_ensure_selected_dut_bss_ready)

    case = {
        "id": "wifi-llapi-runtime-custom-6g-ocv-hook",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        DUT 6G setup:
          ubus-cli WiFi.AccessPoint.3.Enable=1
        STA 6G setup:
          iw dev wl1 set type managed
          ifconfig wl1 up
        STA 6G connect verify:
          wpa_cli -p /var/run/wpa_supplicant -i wl1 reconnect
          iw dev wl1 link
        """,
        "verification_command": "iw dev wl1 link",
        "steps": [{"id": "s1", "command": "iw dev wl1 link"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert events == [
        ("ocv", "serial", "wifi-llapi-runtime-custom-6g-ocv-hook"),
        ("ensure_bss", "", "wifi-llapi-runtime-custom-6g-ocv-hook"),
    ]
    plugin.teardown(case, topology=topology)


def test_setup_env_syncs_psk_from_custom_wpa3_sae_passphrase(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-custom-wpa3-cleanup",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        DUT 5G baseline:
          ubus-cli WiFi.SSID.4.SSID=TestPilot_BTM
          ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA3-Personal
          ubus-cli WiFi.AccessPoint.1.Security.SAEPassphrase=testpilot6g
          ubus-cli WiFi.AccessPoint.1.Security.MFPConfig=Required
          ubus-cli WiFi.AccessPoint.1.Enable=1
        STA 5G verify:
          iw dev wl0 link
        """,
        "verification_command": 'wl -i wl0 assoclist',
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"'}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    sae_index = dut.executed_commands.index(
        "ubus-cli WiFi.AccessPoint.1.Security.SAEPassphrase=testpilot6g"
    )
    assert (
        dut.executed_commands[sae_index + 1]
        == "ubus-cli WiFi.AccessPoint.1.Security.KeyPassPhrase=testpilot6g"
    )
    plugin.teardown(case, topology=topology)


def test_setup_env_syncs_psk_from_quoted_custom_wpa3_sae_passphrase(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-custom-wpa3-quoted-cleanup",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
            }
        },
        "sta_env_setup": """
        DUT 6G baseline:
          ubus-cli WiFi.AccessPoint.3.Security.ModeEnabled=WPA3-Personal
          ubus-cli 'WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"'
          ubus-cli WiFi.AccessPoint.3.Enable=1
        """,
        "verification_command": 'wl -i wl1 assoclist',
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": 'ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"'}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    sae_index = dut.executed_commands.index(
        'ubus-cli \'WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"\''
    )
    assert (
        dut.executed_commands[sae_index + 1]
        == 'ubus-cli \'WiFi.AccessPoint.3.Security.KeyPassPhrase="00000000"\''
    )
    plugin.teardown(case, topology=topology)


def test_setup_env_skips_placeholder_sta_env_setup_and_leaves_auto_baseline_available(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    replayed: list[str] = []

    def fake_run_sta_env_setup(case, topology):
        del case, topology
        replayed.append("sta_env_setup")
        return True

    monkeypatch.setattr(plugin, "_run_sta_env_setup", fake_run_sta_env_setup)

    case = {
        "id": "wifi-llapi-runtime-placeholder-sta-env",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        5G example:
          iw dev wl0 set type managed
        Traffic attempt:
          ifconfig wlX 192.168.1.X netmask 255.255.255.0 up
          ping -I wlX -c 5 -W 1 192.168.1.1
        """,
        "verification_command": "wl -i wl0 assoclist",
        "steps": [
            {
                "id": "s1",
                "action": "exec",
                "target": "DUT",
                "command": "wl -i wl0 assoclist",
            }
        ],
    }

    assert plugin._has_custom_env_setup(case) is False
    assert plugin.setup_env(case, topology=topology) is True
    assert plugin._should_auto_prepare_wifi_bands(case) is True
    assert replayed == []
    sta = next(
        transport for transport in recorder.transports if transport.transport_type == "adb"
    )
    assert sta.executed_commands == []
    plugin.teardown(case, topology=topology)


def test_setup_env_runs_wpa_supplicant_hygiene_once_per_iface(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-custom-wpa-hygiene",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        DUT 5G baseline:
          ubus-cli WiFi.AccessPoint.1.Enable=1
        STA 5G setup:
          wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
          wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect
          iw dev wl0 link
        """,
        "verification_command": 'wl -i wl0 assoclist',
        "steps": [{"id": "s1", "command": 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"'}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    sta = next(
        transport for transport in recorder.transports if transport.transport_type == "adb"
    )
    assert sta.executed_commands[:5] == [
        "killall wpa_supplicant 2>/dev/null || true",
        "rm -rf /var/run/wpa_supplicant",
        "mkdir -p /var/run/wpa_supplicant",
        "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect",
    ]
    plugin.teardown(case, topology=topology)


def test_setup_env_canonicalizes_multiline_printf_for_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-custom-multiline-printf",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "sta_env_setup": """
        DUT 5G baseline:
          ubus-cli WiFi.AccessPoint.1.Enable=1
        STA 5G setup:
          printf 'ctrl_interface=/var/run/wpa_supplicant
        update_config=1
        sae_pwe=2
        network={
        ssid="TestPilot_BTM"
        key_mgmt=SAE
        sae_password="testpilot6g"
        ieee80211w=2
        scan_ssid=1
        }
        ' > /tmp/wpa_wl0.conf
          wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant
          iw dev wl0 link
        """,
        "verification_command": 'wl -i wl0 assoclist',
        "steps": [{"id": "s1", "command": 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"'}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    sta = next(
        transport for transport in recorder.transports if transport.transport_type == "adb"
    )
    printf_command = next(
        command for command in sta.executed_commands if command.startswith("printf '%b'")
    )
    assert "\\nkey_mgmt=SAE\\n" in printf_command
    assert "/tmp/wpa_wl0.conf" in printf_command
    assert "\n" not in printf_command
    plugin.teardown(case, topology=topology)


def test_custom_env_bss_wait_reloads_wld_gen_before_ap_bounce(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["DUT"] = object()
    waits: list[tuple[float, str]] = []
    reloads: list[str] = []
    bounces: list[str] = []

    case = {
        "id": "wifi-llapi-runtime-custom-wpa3-bss-reload",
        "sta_env_setup": "DUT 5G baseline:\n  ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA3-Personal",
        "verification_command": "wl -i wl0 assoclist",
        "steps": [{"id": "s1", "band": "5g", "command": "wl -i wl0 assoclist"}],
    }

    def fake_wait(*args, **kwargs):
        waits.append((kwargs["timeout_seconds"], kwargs["band"]))
        return len(waits) > 1

    def fake_reload(case_arg, dut_arg, *, case_id, band):
        del case_arg, dut_arg, case_id
        reloads.append(band)
        return True

    def fake_bounce(case_arg, dut_arg, *, case_id, band):
        del case_arg, dut_arg, case_id
        bounces.append(band)
        return True

    monkeypatch.setattr(plugin, "_wait_for_dut_bss_ready", fake_wait)
    monkeypatch.setattr(plugin, "_reload_dut_wifi_stack", fake_reload)
    monkeypatch.setattr(plugin, "_bounce_dut_band", fake_bounce)

    assert plugin._ensure_selected_dut_bss_ready(case) is True
    assert waits == [(60.0, "5g"), (30.0, "5g")]
    assert reloads == ["5g"]
    assert bounces == []


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
    assert dut.executed_commands == ['dmesg -n 1', 'echo "__testpilot_env_gate__"']
    plugin.teardown(case, topology=topology)


def test_setup_env_prefers_testbed_binding_over_case_selector(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    topology._devices["DUT"] = {
        "transport": "serial",
        "selector": "COM0",
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 115200,
    }
    topology._devices["STA"] = {
        "transport": "serial",
        "selector": "COM1",
        "serial_port": "/dev/ttyUSB1",
        "baudrate": 115200,
    }
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-testbed-binding-priority",
        "topology": {
            "devices": {
                "DUT": {
                    "transport": "serial",
                    "selector": "COM1",
                    "serial_port": "/dev/ttyUSB9",
                },
                "STA": {
                    "transport": "serial",
                    "selector": "COM0",
                    "serial_port": "/dev/ttyUSB8",
                },
            }
        },
        "steps": [],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert recorder.calls[0][1]["selector"] == "COM0"
    assert recorder.calls[0][1]["serial_port"] == "/dev/ttyUSB0"
    assert recorder.calls[1][1]["selector"] == "COM1"
    assert recorder.calls[1][1]["serial_port"] == "/dev/ttyUSB1"
    assert plugin._device_specs["DUT"]["selector"] == "COM0"
    assert plugin._device_specs["STA"]["selector"] == "COM1"
    plugin.teardown(case, topology=topology)


def test_ensure_selected_dut_bss_ready_reload_6g_before_bounce(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    plugin._transports["DUT"] = dut
    waits: list[tuple[float, str]] = []
    reloads: list[str] = []
    bounces: list[str] = []

    case = {
        "id": "wifi-llapi-runtime-generic-6g-bss-reload",
        "steps": [{"id": "s1", "band": "6g", "command": "wl -i wl1 assoclist"}],
    }

    def fake_wait(*args, **kwargs):
        waits.append((kwargs["timeout_seconds"], kwargs["band"]))
        return len(waits) > 1

    def fake_reload(case_arg, dut_arg, *, case_id, band):
        del case_arg, dut_arg, case_id
        reloads.append(band)
        return True

    def fake_bounce(case_arg, dut_arg, *, case_id, band):
        del case_arg, dut_arg, case_id
        bounces.append(band)
        return True

    monkeypatch.setattr(plugin, "_wait_for_dut_bss_ready", fake_wait)
    monkeypatch.setattr(plugin, "_reload_dut_wifi_stack", fake_reload)
    monkeypatch.setattr(plugin, "_bounce_dut_band", fake_bounce)

    assert plugin._ensure_selected_dut_bss_ready(case) is True
    assert waits == [(60.0, "6g"), (30.0, "6g")]
    assert reloads == ["6g"]
    assert bounces == []


def test_wait_for_dut_bss_ready_short_circuits_on_missing_adapter(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "wl -i wl1 bss":
            return {"returncode": 1, "stdout": "", "stderr": "wl: wl driver adapter not found"}
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    assert (
        plugin._wait_for_dut_bss_ready(
            {"id": "wifi-llapi-runtime-missing-adapter"},
            dut,
            case_id="wifi-llapi-runtime-missing-adapter",
            band="6g",
            index=1,
            command="wl -i wl1 bss",
            timeout_seconds=60.0,
            poll_interval=5.0,
        )
        is False
    )
    assert executed == ["wl -i wl1 bss"]


def test_execute_remediation_tolerates_null_band_params(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-remediation-null-bands",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            }
        },
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
        "steps": [{"id": "s1", "command": "echo ok"}],
    }

    result = plugin.execute_remediation(
        case,
        {
            "actions": [
                {
                    "executor_key": "case_env_reverify",
                    "params": {"bands": None},
                }
            ]
        },
        topology=topology,
    )

    assert result["success"] is True
    assert result["verify_after"] is True
    assert result["actions"][0]["executor_key"] == "case_env_reverify"
    assert result["actions"][0]["params"] == {"bands": ["5g", "6g", "2.4g"]}
    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    assert dut.executed_commands == ['dmesg -n 1', 'echo "__testpilot_env_gate__"']


def test_execute_remediation_opens_transports_without_rerunning_case_setup(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    opened: list[bool] = []

    def fake_open(case, topo, *, run_case_setup):
        del case, topo
        opened.append(run_case_setup)
        return True

    monkeypatch.setattr(plugin, "_open_case_transports", fake_open)
    monkeypatch.setattr(plugin, "verify_env", lambda case, topology: True)

    result = plugin.execute_remediation(
        {"id": "wifi-llapi-runtime-remediation-open-only", "steps": []},
        {"actions": [{"executor_key": "case_env_reverify"}]},
        topology=topology,
    )

    assert result["success"] is True
    assert opened == [False]


def test_execute_remediation_replays_custom_sta_env_setup(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    replayed: list[str] = []

    monkeypatch.setattr(plugin, "_open_case_transports", lambda case, topo, *, run_case_setup: True)
    monkeypatch.setattr(plugin, "verify_env", lambda case, topology: True)
    monkeypatch.setattr(plugin, "_run_sta_band_baseline", lambda case: False)
    monkeypatch.setattr(plugin, "_ensure_sta_band_ready", lambda case, topology: False)

    def fake_run_sta_env_setup(case, topology):
        del case, topology
        replayed.append("sta_env_setup")
        return True

    monkeypatch.setattr(plugin, "_run_sta_env_setup", fake_run_sta_env_setup)

    result = plugin.execute_remediation(
        {
            "id": "wifi-llapi-runtime-remediation-custom-env",
            "sta_env_setup": "STA 5G setup:\n  iw dev wl0 link",
            "steps": [],
        },
        {
            "actions": [
                {"executor_key": "sta_band_rebaseline", "params": {"bands": ["5g"]}},
                {"executor_key": "dut_band_rebaseline", "params": {"bands": ["5g"]}},
                {"executor_key": "case_env_reverify"},
            ]
        },
        topology=topology,
    )

    assert result["success"] is True
    assert replayed == ["sta_env_setup"]
    assert [action["executor_key"] for action in result["actions"]] == [
        "sta_band_rebaseline",
        "dut_band_rebaseline",
        "case_env_reverify",
    ]
    assert [action["success"] for action in result["actions"]] == [True, True, True]


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
    failure = case.get("_last_failure")
    assert isinstance(failure, dict)
    assert failure["phase"] == "setup_env"
    assert failure["category"] == "environment"
    assert failure["reason_code"] == "sta_band_link_failed"
    assert failure["device"] == "STA"
    assert failure["band"] == "6g"
    assert failure["command"] == "iw dev wl1 link"
    decision = plugin.build_remediation_decision(case, failure, topology)
    assert decision is not None
    assert [action["executor_key"] for action in decision["actions"]] == [
        "sta_band_rebaseline",
        "dut_band_rebaseline",
        "case_env_reverify",
    ]
    plugin.teardown(case, topology=topology)


def test_verify_env_reapplies_deterministic_generic_baseline(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-generic-baseline",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            },
            "links": [
                {"from": "STA", "to": "DUT", "band": "5g"},
                {"from": "STA", "to": "DUT", "band": "2.4g"},
            ],
        },
        "hlapi_command": 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MaxBandwidthSupported?"',
        "steps": [
            {"id": "s1", "band": "5g", "command": "wl -i wl0 assoclist"},
            {"id": "s2", "band": "2.4g", "command": "wl -i wl2 assoclist"},
        ],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert plugin.verify_env(case, topology=topology) is True

    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    sta = next(
        transport for transport in recorder.transports if transport.transport_type == "adb"
    )
    assert "ubus-cli WiFi.SSID.4.SSID=testpilot5G" in dut.executed_commands
    assert "ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA2-Personal" in dut.executed_commands
    assert "ubus-cli WiFi.AccessPoint.1.Security.MFPConfig=Disabled" in dut.executed_commands
    assert "iw dev wl0 set type managed" in sta.executed_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 enable_network 0" in sta.executed_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0" in sta.executed_commands
    assert "ubus-cli WiFi.SSID.8.SSID=testpilot2G" in dut.executed_commands
    assert "ubus-cli WiFi.AccessPoint.5.Security.ModeEnabled=WPA2-Personal" in dut.executed_commands
    assert "ubus-cli WiFi.AccessPoint.5.Security.MFPConfig=Disabled" in dut.executed_commands
    assert "iw dev wl2 set type managed" in sta.executed_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 enable_network 0" in sta.executed_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 select_network 0" in sta.executed_commands
    assert case["_active_step_band"] == "2.4g"

    first_result = plugin.execute_step(case, case["steps"][0], topology=topology)
    assert first_result["success"] is True
    assert case["_active_step_band"] == "5g"

    result = plugin.execute_step(case, case["steps"][1], topology=topology)
    assert result["success"] is True
    assert case["_active_step_band"] == "2.4g"
    plugin.teardown(case, topology=topology)


def test_verify_env_defers_failed_band_warmup_to_execute_step(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-generic-band-warmup-defer",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            },
            "links": [
                {"from": "STA", "to": "DUT", "band": "5g"},
                {"from": "STA", "to": "DUT", "band": "6g"},
                {"from": "STA", "to": "DUT", "band": "2.4g"},
            ],
        },
        "steps": [
            {"id": "s1", "band": "5g", "command": "wl -i wl0 assoclist"},
            {"id": "s2", "band": "6g", "command": "wl -i wl1 assoclist"},
            {"id": "s3", "band": "2.4g", "command": "wl -i wl2 assoclist"},
        ],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    calls: list[str] = []

    def fake_prepare(case_arg, topology_arg, band):
        del topology_arg
        normalized = plugin._normalize_band_name(band)
        calls.append(normalized)
        if normalized == "6g":
            return False
        case_arg["_active_step_band"] = normalized
        return True

    assert plugin.setup_env(case, topology=topology) is True
    monkeypatch.setattr(plugin, "_prepare_case_band", fake_prepare)

    assert plugin.verify_env(case, topology=topology) is True
    assert calls == ["5g", "6g", "2.4g"]
    assert case["_active_step_band"] == "2.4g"
    plugin.teardown(case, topology=topology)


def test_verify_env_falls_back_to_driver_assoclist_when_public_assoc_missing(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    topology._devices["DUT"]["simulate_assoc_query_fail"] = True
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-6g-assoclist-fallback",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            },
            "links": [{"from": "STA", "to": "DUT", "band": "6g"}],
        },
        "steps": [{"id": "s1", "band": "6g", "command": "wl -i wl1 assoclist"}],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    assert plugin.verify_env(case, topology=topology) is True

    dut = next(
        transport for transport in recorder.transports if transport.transport_type == "serial"
    )
    assert 'ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"' in dut.executed_commands
    assert "wl -i wl1 assoclist" in dut.executed_commands
    plugin.teardown(case, topology=topology)


def test_verify_env_uses_longer_generic_6g_connect_settle(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    case = {
        "id": "wifi-llapi-runtime-6g-settle-window",
        "topology": {
            "devices": {
                "DUT": {"transport": "serial"},
                "STA": {"transport": "adb"},
            },
            "links": [{"from": "STA", "to": "DUT", "band": "6g"}],
        },
        "steps": [{"id": "s1", "band": "6g", "command": "wl -i wl1 assoclist"}],
        "pass_criteria": [{"field": "result", "operator": "contains", "value": "OK"}],
    }

    calls: list[tuple[str, int]] = []

    def fake_run_required_command(**kwargs):
        return True

    def fake_wait_for_6g_sta_ap_teardown(**kwargs):
        return True

    def fake_connect_with_retry(*, label, sleep_seconds, **kwargs):
        calls.append((label, sleep_seconds))
        return True

    monkeypatch.setattr(plugin, "_run_required_command", fake_run_required_command)
    monkeypatch.setattr(plugin, "_wait_for_6g_sta_ap_teardown", fake_wait_for_6g_sta_ap_teardown)
    monkeypatch.setattr(plugin, "_connect_with_retry", fake_connect_with_retry)

    assert plugin.setup_env(case, topology=topology) is True
    assert plugin._run_sta_band_connect_sequence(case) is True

    assert ("sta_6g", 15) in calls
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


def test_env_command_succeeded_allows_macaddress_shell_pipeline():
    plugin = _load_plugin()
    command = (
        'STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" '
        '| sed -n \'s/.*MACAddress="\\([^"]*\\)".*/\\1/p\'); '
        '[ -n "$STA_MAC" ] && wl -i wl0 sta_info $STA_MAC '
        '| sed -n \'s/.*in network \\([0-9][0-9]*\\) seconds.*/DriverConnectionSeconds5g=\\1/p\''
    )
    result = {"returncode": 0, "stdout": "DriverConnectionSeconds5g=54", "stderr": ""}

    assert plugin._env_command_succeeded(command, result) is True


def test_env_command_succeeded_allows_parameter_not_found_getter_output():
    plugin = _load_plugin()
    command = 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS?"'
    result = {
        "returncode": 1,
        "stdout": (
            "ERROR: get WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS "
            "failed (4 - parameter not found)\nerror=4\nmessage=parameter not found"
        ),
        "stderr": "",
    }

    assert plugin._env_command_succeeded(command, result) is True


@pytest.mark.parametrize(
    ("command", "stdout"),
    [
        (
            "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant",
            "Failed to open config file '/tmp/wpa_wl0.conf', error: No such file or directory",
        ),
        (
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect",
            "Failed to connect to non-global ctrl_ifname: wl0  error: No such file or directory",
        ),
        (
            "ifconfig wlX 192.168.1.X netmask 255.255.255.0 up",
            "ifconfig: bad address '192.168.1.X'",
        ),
        (
            "ping -I wlX -c 5 -W 1 192.168.1.1",
            "ping: SO_BINDTODEVICE wlX: No such device",
        ),
    ],
)
def test_env_command_succeeded_rejects_placeholder_and_wpa_failures(command: str, stdout: str):
    plugin = _load_plugin()
    result = {"returncode": 0, "stdout": stdout, "stderr": ""}

    assert plugin._env_command_succeeded(command, result) is False


@pytest.mark.parametrize(
    ("band", "ap", "secondary_ap", "ssid_index", "ssid", "mode"),
    [
        ("5g", "1", "2", "4", "testpilot5G", "WPA2-Personal"),
        ("6g", "3", "4", "6", "testpilot6G", "WPA3-Personal"),
        ("2.4g", "5", "6", "8", "testpilot2G", "WPA2-Personal"),
    ],
)
def test_dut_baseline_commands_disable_primary_before_reconfig(
    band, ap, secondary_ap, ssid_index, ssid, mode
):
    plugin = _load_plugin()

    profile = plugin._band_baseline_profile(band)
    assert profile is not None

    commands = plugin._dut_baseline_commands(profile)
    assert commands.index(f"ubus-cli WiFi.AccessPoint.{secondary_ap}.Enable=0") < commands.index(
        f"ubus-cli WiFi.AccessPoint.{ap}.Enable=0"
    )
    assert commands.index(f"ubus-cli WiFi.AccessPoint.{ap}.Enable=0") < commands.index(
        f"ubus-cli WiFi.SSID.{ssid_index}.SSID={ssid}"
    )
    assert commands.index(f"ubus-cli WiFi.AccessPoint.{ap}.Enable=0") < commands.index(
        f"ubus-cli WiFi.AccessPoint.{ap}.Security.ModeEnabled={mode}"
    )
    assert commands[-1] == f"ubus-cli WiFi.AccessPoint.{ap}.Enable=1"


def test_run_sta_band_baseline_disables_primary_before_reconfig(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    plugin._transports["DUT"] = dut
    executed: list[str] = []

    monotonic_values = iter(range(0, 200, 10))
    plugin_module = sys.modules[plugin.__class__.__module__]
    monkeypatch.setattr(plugin_module.time, "monotonic", lambda: next(monotonic_values))

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "wl -i wl0 bss":
            if "ubus-cli WiFi.AccessPoint.1.Enable=0" not in executed:
                return {"returncode": 0, "stdout": "down", "stderr": ""}
            return {"returncode": 0, "stdout": "up", "stderr": ""}
        if command == "wl -i wl2 bss":
            if "ubus-cli WiFi.AccessPoint.5.Enable=0" not in executed:
                return {"returncode": 0, "stdout": "down", "stderr": ""}
            return {"returncode": 0, "stdout": "up", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    case = {
        "id": "wifi-llapi-runtime-bss-bounce",
        "topology": {
            "links": [
                {"from": "STA", "to": "DUT", "band": "5g"},
                {"from": "STA", "to": "DUT", "band": "2.4g"},
            ]
        },
        "steps": [
            {"id": "s1", "band": "5g", "command": "wl -i wl0 assoclist"},
            {"id": "s2", "band": "2.4g", "command": "wl -i wl2 assoclist"},
        ],
    }

    assert plugin._run_sta_band_baseline(case) is True
    assert "ubus-cli WiFi.AccessPoint.1.Enable=0" in executed
    assert "ubus-cli WiFi.AccessPoint.2.Enable=0" in executed
    assert executed.index("ubus-cli WiFi.AccessPoint.1.Enable=0") < executed.index(
        "ubus-cli WiFi.SSID.4.SSID=testpilot5G"
    )
    assert executed.count("ubus-cli WiFi.Radio.1.Enable=1") == 1
    assert executed.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert "ubus-cli WiFi.AccessPoint.5.Enable=0" in executed
    assert executed.index("ubus-cli WiFi.AccessPoint.5.Enable=0") < executed.index(
        "ubus-cli WiFi.SSID.8.SSID=testpilot2G"
    )
    assert executed.count("ubus-cli WiFi.Radio.3.Enable=1") == 1
    assert executed.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert "ubus-cli WiFi.AccessPoint.6.Enable=0" in executed


def test_run_sta_band_baseline_sets_6g_sae_passphrase(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    plugin._transports["DUT"] = dut
    executed: list[str] = []

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "up", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
    monkeypatch.setattr(plugin, "_ensure_selected_dut_bss_ready", lambda case: True)

    case = {
        "id": "wifi-llapi-runtime-6g-baseline",
        "topology": {
            "links": [
                {"from": "STA", "to": "DUT", "band": "6g"},
            ]
        },
        "steps": [
            {"id": "s1", "band": "6g", "command": "wl -i wl1 assoclist"},
        ],
    }

    assert plugin._run_sta_band_baseline(case) is True
    assert "ubus-cli WiFi.Radio.2.Enable=1" in executed
    assert "ubus-cli WiFi.AccessPoint.4.Enable=0" in executed
    assert "ubus-cli WiFi.AccessPoint.3.MultiAPType=None" in executed
    assert "ubus-cli WiFi.AccessPoint.3.Security.ModeEnabled=WPA3-Personal" in executed
    assert "ubus-cli 'WiFi.AccessPoint.3.Security.SAEPassphrase=\"00000000\"'" in executed
    assert "ubus-cli 'WiFi.AccessPoint.3.Security.KeyPassPhrase=\"00000000\"'" in executed
    assert "ubus-cli WiFi.AccessPoint.3.Security.MFPConfig=Required" in executed
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in executed
    assert executed.index("ubus-cli WiFi.AccessPoint.3.MultiAPType=None") < executed.index(
        "ubus-cli WiFi.AccessPoint.3.Enable=1"
    )


def test_bounce_dut_band_disables_secondary_ap_before_reenable(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        return {"returncode": 0, "stdout": "", "stderr": ""}

    ocv_fix_calls: list[tuple[Any, str]] = []

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
    monkeypatch.setattr(
        plugin,
        "_apply_6g_ocv_fix",
        lambda transport, case_id: ocv_fix_calls.append((transport, case_id)),
    )

    case = {"id": "wifi-llapi-runtime-6g-bounce"}

    assert plugin._bounce_dut_band(case, dut, case_id="wifi-llapi-runtime-6g-bounce", band="6g") is True
    assert executed == [
        "ubus-cli WiFi.AccessPoint.4.Enable=0",
        "ubus-cli WiFi.AccessPoint.3.Enable=0",
        "sleep 2",
        "ubus-cli WiFi.Radio.2.Enable=1",
        "ubus-cli WiFi.AccessPoint.4.Enable=0",
        "ubus-cli WiFi.AccessPoint.3.Enable=1",
        "sleep 5",
    ]
    assert ocv_fix_calls == [(dut, "wifi-llapi-runtime-6g-bounce")]


def test_apply_6g_ocv_fix_cleans_control_sockets_and_forces_bss_up(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []
    runtime_config_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_config_commands"
    )
    runtime_ready_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_ready_commands"
    )

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1":
            return {"returncode": 0, "stdout": "ocv=0\nocv=0\n", "stderr": ""}
        if command == "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "up", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    plugin._apply_6g_ocv_fix(dut, "wifi-llapi-runtime-6g-ocv")

    assert executed == [
        "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT",
        *runtime_config_commands,
        "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "wl -i wl1 bss",
        "pid=$(pgrep -f '/tmp/wl1_hapd.conf' 2>/dev/null | head -n1); if [ -n \"$pid\" ]; then kill \"$pid\" 2>/dev/null || true; fi",
        "sleep 2",
        "rm -f /var/run/hostapd/wl1 /var/run/hostapd/wl1.1",
        "wl -i wl1 ap 1",
        "wl -i wl1 up",
        "ifconfig wl1 up",
        "hostapd -ddt -B /tmp/wl1_hapd.conf",
        "sleep 2",
        "wl -i wl1 bss up",
        "sleep 2",
        "sleep 3",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT",
        "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT",
        "wl -i wl1 bss",
        *runtime_ready_commands,
    ]


def test_apply_6g_ocv_fix_restarts_again_when_ocv_disappears_after_restart(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []
    runtime_config_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_config_commands"
    )
    runtime_ready_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_ready_commands"
    )
    verify_outputs = iter(("ocv=0\n", "", "ocv=0\n", "ocv=0\n"))
    socket_outputs = iter(("WAIT", "READY"))
    process_outputs = iter(("WAIT", "READY"))
    bss_outputs = iter(("down", "down", "down", "up"))

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1":
            return {"returncode": 0, "stdout": next(verify_outputs), "stderr": ""}
        if command == "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": next(socket_outputs), "stderr": ""}
        if command == "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": next(process_outputs), "stderr": ""}
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": next(bss_outputs), "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    plugin._apply_6g_ocv_fix(dut, "wifi-llapi-runtime-6g-ocv-restart")

    restart_commands = [
        "pid=$(pgrep -f '/tmp/wl1_hapd.conf' 2>/dev/null | head -n1); if [ -n \"$pid\" ]; then kill \"$pid\" 2>/dev/null || true; fi",
        "sleep 2",
        "rm -f /var/run/hostapd/wl1 /var/run/hostapd/wl1.1",
        "wl -i wl1 ap 1",
        "wl -i wl1 up",
        "ifconfig wl1 up",
        "hostapd -ddt -B /tmp/wl1_hapd.conf",
        "sleep 2",
    ]
    assert executed == [
        "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT",
        *runtime_config_commands,
        "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "wl -i wl1 bss",
        *restart_commands,
        "wl -i wl1 bss up",
        "sleep 2",
        "sleep 3",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT",
        "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT",
        "wl -i wl1 bss",
        *runtime_ready_commands,
        *runtime_config_commands,
        "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "wl -i wl1 bss",
        *restart_commands,
        "wl -i wl1 bss up",
        "sleep 2",
        "sleep 3",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT",
        "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT",
        "wl -i wl1 bss",
        *runtime_ready_commands,
    ]


def test_apply_6g_ocv_fix_accepts_running_hostapd_without_socket(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []
    runtime_config_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_config_commands"
    )
    runtime_ready_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_ready_commands"
    )

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1":
            return {"returncode": 0, "stdout": "ocv=0\n", "stderr": ""}
        if command == "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "WAIT", "stderr": ""}
        if command == "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "up", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    plugin._apply_6g_ocv_fix(dut, "wifi-llapi-runtime-6g-ocv-process-fallback")

    restart_commands = [
        "pid=$(pgrep -f '/tmp/wl1_hapd.conf' 2>/dev/null | head -n1); if [ -n \"$pid\" ]; then kill \"$pid\" 2>/dev/null || true; fi",
        "sleep 2",
        "rm -f /var/run/hostapd/wl1 /var/run/hostapd/wl1.1",
        "wl -i wl1 ap 1",
        "wl -i wl1 up",
        "ifconfig wl1 up",
        "hostapd -ddt -B /tmp/wl1_hapd.conf",
        "sleep 2",
    ]
    assert executed == [
        "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT",
        *runtime_config_commands,
        "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "wl -i wl1 bss",
        *restart_commands,
        "wl -i wl1 bss up",
        "sleep 2",
        "sleep 3",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT",
        "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT",
        "wl -i wl1 bss",
        *runtime_ready_commands,
    ]


def test_apply_6g_ocv_fix_accepts_post_restart_ocv_probe_drop_when_process_and_bss_survive(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []
    runtime_config_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_config_commands"
    )
    runtime_ready_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_ready_commands"
    )
    verify_outputs = iter(("ocv=0\n", ""))

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1":
            return {"returncode": 0, "stdout": next(verify_outputs), "stderr": ""}
        if command == "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "WAIT", "stderr": ""}
        if command == "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "up", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    plugin._apply_6g_ocv_fix(dut, "wifi-llapi-runtime-6g-ocv-post-probe-drop")

    restart_commands = [
        "pid=$(pgrep -f '/tmp/wl1_hapd.conf' 2>/dev/null | head -n1); if [ -n \"$pid\" ]; then kill \"$pid\" 2>/dev/null || true; fi",
        "sleep 2",
        "rm -f /var/run/hostapd/wl1 /var/run/hostapd/wl1.1",
        "wl -i wl1 ap 1",
        "wl -i wl1 up",
        "ifconfig wl1 up",
        "hostapd -ddt -B /tmp/wl1_hapd.conf",
        "sleep 2",
    ]
    assert executed == [
        "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT",
        *runtime_config_commands,
        "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "wl -i wl1 bss",
        *restart_commands,
        "wl -i wl1 bss up",
        "sleep 2",
        "sleep 3",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "test -S /var/run/hostapd/wl1 && echo READY || echo WAIT",
        "pgrep -f '/tmp/wl1_hapd.conf' >/dev/null && echo READY || echo WAIT",
        "wl -i wl1 bss",
        *runtime_ready_commands,
    ]


def test_apply_6g_ocv_fix_defers_restart_when_wl1_adapter_missing(monkeypatch):
    plugin = _load_plugin()
    dut = object()
    executed: list[str] = []
    runtime_config_commands = plugin._profile_command_list(
        plugin.DEFAULT_BAND_BASELINES["6g"], "dut_runtime_config_commands"
    )

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        assert transport is dut
        executed.append(command)
        if command == "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT":
            return {"returncode": 0, "stdout": "READY", "stderr": ""}
        if command == "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1":
            return {"returncode": 0, "stdout": "ocv=0\n", "stderr": ""}
        if command == "wl -i wl1 bss":
            return {"returncode": 1, "stdout": "", "stderr": "wl: wl driver adapter not found"}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    plugin._apply_6g_ocv_fix(dut, "wifi-llapi-runtime-6g-ocv-missing-adapter")

    assert executed == [
        "grep -q ieee80211w /tmp/wl1_hapd.conf 2>/dev/null && echo READY || echo WAIT",
        *runtime_config_commands,
        "sed -i '/^ocv=/d; /^ieee80211w=/a ocv=0' /tmp/wl1_hapd.conf",
        "grep '^ocv=0' /tmp/wl1_hapd.conf 2>&1",
        "wl -i wl1 bss",
    ]


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


def test_env_command_succeeds_for_wl_join_imode_bss():
    plugin = _load_plugin()

    result = {
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "elapsed": 0.01,
    }

    assert plugin._env_command_succeeded("wl -i wl0 join TestPilot_5G imode bss", result) is True


def test_env_command_succeeds_for_wl_status_when_associated():
    plugin = _load_plugin()

    result = {
        "returncode": 0,
        "stdout": (
            "SSID: TestPilot_24G\n"
            "Mode: Managed RSSI: -57 dBm noise: -91 dBm Channel: 1\n"
            "BSSID: 2c:59:17:00:19:95 Capability: ESS ShortSlot\n"
        ),
        "stderr": "",
        "elapsed": 0.01,
    }

    assert plugin._env_command_succeeded("wl -i wl2 status", result) is True


def test_env_command_fails_for_wl_status_when_not_associated():
    plugin = _load_plugin()

    result = {
        "returncode": 0,
        "stdout": "Not associated. Last associated with BSSID: 00:00:00:00:00:00\n",
        "stderr": "",
        "elapsed": 0.01,
    }

    assert plugin._env_command_succeeded("wl -i wl2 status", result) is False


def test_connect_with_retry_accepts_fallback_verify_commands(monkeypatch):
    plugin = _load_plugin()
    command_log: list[tuple[str, str]] = []
    verify_log: list[str] = []

    def fake_run_required_command(*, transport, case_id, label, command, timeout=30.0):
        del transport, case_id, timeout
        command_log.append((label, command))
        return True

    def fake_execute_env_command(transport, command, *, timeout=20.0):
        del transport, timeout
        verify_log.append(command)
        if command == "iw dev wl2 link":
            return {"returncode": 0, "stdout": "Not connected.\n", "stderr": ""}
        if command == "wl -i wl2 status":
            return {
                "returncode": 0,
                "stdout": (
                    "SSID: testpilot2G\n"
                    "Mode: Managed RSSI: -55 dBm noise: -92 dBm Channel: 1\n"
                    "BSSID: 2c:59:17:00:19:95 Capability: ESS ShortSlot\n"
                ),
                "stderr": "",
            }
        raise AssertionError(f"unexpected verify command: {command}")

    monkeypatch.setattr(plugin, "_run_required_command", fake_run_required_command)
    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    assert plugin._connect_with_retry(
        transport=object(),
        case_id="wifi-llapi-runtime-24g-fallback",
        label="sta_24g",
        connect_cmd="wpa_cli -p /var/run/wpa_supplicant -i wl2 select_network 0",
        verify_cmd=("iw dev wl2 link", "wl -i wl2 status"),
        attempts=3,
        sleep_seconds=8,
    )

    assert command_log == [
        ("sta_24g.connect.1", "wpa_cli -p /var/run/wpa_supplicant -i wl2 select_network 0"),
        ("sta_24g.sleep.1", "sleep 8"),
    ]
    assert verify_log == ["iw dev wl2 link", "wl -i wl2 status"]


def test_case_yaml_band_baselines_reset_radio_defaults():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
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
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    # Post-skip cases are still pending review; keep this guard focused on the
    # pre-skip YAMLs that the audit report already treats as aligned.
    d011 = yaml.safe_load(
        (cases_dir / "D011_avgsignalstrength.yaml").read_text(encoding="utf-8")
    )
    d011_commands = "\n".join(str(step.get("command", "")) for step in d011["steps"])
    assert d011["source"]["row"] == 11
    assert "AvgSignalStrength?" in d011["hlapi_command"]
    assert "AvgSignalStrength=0" not in d011["hlapi_command"]
    assert "AssocMac5g=" in d011_commands
    assert "AssocMac6g=" in d011_commands
    assert "AssocMac24g=" in d011_commands
    assert "DriverSmoothedRSSI5g=" in d011_commands
    assert "DriverSmoothedRSSI6g=" in d011_commands
    assert "DriverSmoothedRSSI24g=" in d011_commands
    assert any(
        criterion["field"] == "result_5g.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi_5g.DriverSmoothedRSSI5g"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi_6g.DriverSmoothedRSSI6g"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi_24g.DriverSmoothedRSSI24g"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )

    d015 = yaml.safe_load(
        (cases_dir / "D015_connectionduration.yaml").read_text(encoding="utf-8")
    )
    d015_commands = "\n".join(str(step.get("command", "")) for step in d015["steps"])
    d015_links = {link["band"] for link in d015["topology"]["links"]}
    assert d015["source"]["row"] == 15
    assert "ConnectionDuration?" in d015["hlapi_command"]
    assert "ConnectionDuration=8229" not in d015["hlapi_command"]
    assert d015_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d015_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress?' in d015_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress?' in d015_commands
    assert "DriverConnectionSeconds5g=" in d015_commands
    assert "DriverConnectionSeconds6g=" in d015_commands
    assert "DriverConnectionSeconds24g=" in d015_commands
    assert any(
        criterion["field"] == "result_after_wait_5g.ConnectionDuration"
        and criterion["operator"] == ">"
        and criterion["reference"] == "result_5g.ConnectionDuration"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_duration_6g.DriverConnectionSeconds6g"
        and criterion["operator"] == ">="
        and criterion["reference"] == "result_after_wait_6g.ConnectionDuration"
        for criterion in d015["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_duration_24g.DriverConnectionSeconds24g"
        and criterion["operator"] == ">="
        and criterion["reference"] == "result_after_wait_24g.ConnectionDuration"
        for criterion in d015["pass_criteria"]
    )

    d017 = yaml.safe_load(
        (cases_dir / "D017_downlinkmcs.yaml").read_text(encoding="utf-8")
    )
    d017_commands = "\n".join(str(step.get("command", "")) for step in d017["steps"])
    d017_links = {link["band"] for link in d017["topology"]["links"]}
    assert d017["source"]["row"] == 17
    assert d017["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.{i}.AssociatedDevice.1.DownlinkMCS?"'
    assert d017_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d017_commands
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkMCS?' in d017_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress?' in d017_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.DownlinkMCS?' in d017_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress?' in d017_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkMCS?' in d017_commands
    assert "DriverDownlinkMCS5g=" in d017_commands
    assert "DriverDownlinkMCS6g=" in d017_commands
    assert "DriverDownlinkMCS24g=" in d017_commands
    assert any(
        criterion["field"] == "result_5g.DownlinkMCS"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_mcs_5g.DriverDownlinkMCS5g"
        for criterion in d017["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.DownlinkMCS"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_mcs_6g.DriverDownlinkMCS6g"
        for criterion in d017["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.DownlinkMCS"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_mcs_24g.DriverDownlinkMCS24g"
        for criterion in d017["pass_criteria"]
    )

    d009 = yaml.safe_load(
        (cases_dir / "D009_associationtime.yaml").read_text(encoding="utf-8")
    )
    d009_commands = "\n".join(str(step.get("command", "")) for step in d009["steps"])
    assert d009["source"]["row"] == 9
    assert "AssociationTime?" in d009["hlapi_command"]
    assert "AssociationTime=" not in d009["hlapi_command"]
    assert "AssocMac5g=" in d009_commands
    assert "AssocMac6g=" in d009_commands
    assert "AssocMac24g=" in d009_commands
    assert "ConnectionSeconds5g=" in d009_commands
    assert "ConnectionSeconds6g=" in d009_commands
    assert "ConnectionSeconds24g=" in d009_commands
    assert any(
        criterion["field"] == "result_5g.AssociationTime"
        and criterion["operator"] == "regex"
        for criterion in d009["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.AssociationTime"
        and criterion["operator"] == "regex"
        for criterion in d009["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AssociationTime"
        and criterion["operator"] == "regex"
        for criterion in d009["pass_criteria"]
    )

    d010 = yaml.safe_load(
        (cases_dir / "D010_authenticationstate.yaml").read_text(encoding="utf-8")
    )
    d010_commands = "\n".join(str(step.get("command", "")) for step in d010["steps"])
    assert d010["source"]["row"] == 10
    assert "AuthenticationState?" in d010["hlapi_command"]
    assert "AuthenticationState=" not in d010["hlapi_command"]
    assert "AssocMac5g=" in d010_commands
    assert "AssocMac6g=" in d010_commands
    assert "AssocMac24g=" in d010_commands
    assert "DriverAuthState5g=" in d010_commands
    assert "DriverAuthState6g=" in d010_commands
    assert "DriverAuthState24g=" in d010_commands
    assert any(
        criterion["field"] == "result_5g.AuthenticationState"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_state_5g.DriverAuthState5g"
        for criterion in d010["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.AuthenticationState"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_state_6g.DriverAuthState6g"
        for criterion in d010["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AuthenticationState"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_state_24g.DriverAuthState24g"
        for criterion in d010["pass_criteria"]
    )

    d016 = yaml.safe_load(
        (cases_dir / "D016_downlinkbandwidth.yaml").read_text(encoding="utf-8")
    )
    d016_commands = "\n".join(str(step.get("command", "")) for step in d016["steps"])
    d016_links = {link["band"] for link in d016["topology"]["links"]}
    assert d016["source"]["row"] == 16
    assert "DownlinkBandwidth?" in d016["hlapi_command"]
    assert "DownlinkBandwidth=0" not in d016["hlapi_command"]
    assert d016_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d016_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress?' in d016_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress?' in d016_commands
    assert "DriverDownlinkBandwidth5g=" in d016_commands
    assert "DriverDownlinkBandwidth6g=" in d016_commands
    assert "DriverDownlinkBandwidth24g=" in d016_commands
    assert any(
        criterion["field"] == "result_5g.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw_5g.DriverDownlinkBandwidth5g"
        for criterion in d016["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw_6g.DriverDownlinkBandwidth6g"
        for criterion in d016["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw_24g.DriverDownlinkBandwidth24g"
        for criterion in d016["pass_criteria"]
    )

    d019 = yaml.safe_load(
        (cases_dir / "D019_encryptionmode_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert d019["source"]["row"] == 19
    assert "aliases" not in d019
    assert case_band_results(d019, True) == _expected_case_band_results(d019, True)
    assert "EncryptionMode?" in d019["hlapi_command"]
    assert "EncryptionMode=AES" not in d019["hlapi_command"]
    assert any(
        criterion["field"] == "result.EncryptionMode"
        and criterion["operator"] == "equals"
        and criterion["value"] == "Default"
        for criterion in d019["pass_criteria"]
    )

    d021 = yaml.safe_load(
        (cases_dir / "D021_hecapabilities_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d021_commands = "\n".join(str(step.get("command", "")) for step in d021["steps"])
    assert d021["source"]["row"] == 21
    assert d021["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.HeCapabilities?"'
    assert "HeCapabilities=" not in d021["hlapi_command"]
    assert "DriverHeMuBfe=1" in d021_commands
    assert any(
        criterion["field"] == "result.HeCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SU&MU-BFE"
        for criterion in d021["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_he.DriverHeMuBfe"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d021["pass_criteria"]
    )

    d022 = yaml.safe_load(
        (cases_dir / "D022_htcapabilities_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d022_commands = "\n".join(str(step.get("command", "")) for step in d022["steps"])
    assert d022["source"]["row"] == 22
    assert "aliases" not in d022
    assert d022["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.HtCapabilities?"'
    assert "HtCapabilities=40MHz,SGI20,SGI40" not in d022["hlapi_command"]
    assert "DriverHt40MHz=1" in d022_commands
    assert "DriverHtSgi20=1" in d022_commands
    assert "DriverHtSgi40=1" in d022_commands
    assert "HT caps 0x" in d022_commands
    assert "0x0002" in d022_commands
    assert "0x0020" in d022_commands
    assert "0x0040" in d022_commands
    assert any(
        criterion["field"] == "result.HtCapabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "40MHz,SGI20,SGI40"
        for criterion in d022["pass_criteria"]
    )

    d024 = yaml.safe_load(
        (cases_dir / "D024_lastdatadownlinkrate.yaml").read_text(encoding="utf-8")
    )
    d024_commands = "\n".join(str(step.get("command", "")) for step in d024["steps"])
    assert d024["source"]["row"] == 24
    assert d024["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LastDataDownlinkRate?"'
    assert "LastDataDownlinkRate=1733333" not in d024["hlapi_command"]
    assert 'WiFi.SSID.4.BSSID?' in d024_commands
    assert "DriverLastDownlinkRateLower=" in d024_commands
    assert "DriverLastDownlinkRateUpper=" in d024_commands
    assert "rate of last tx pkt" in d024_commands
    assert any(
        criterion["field"] == "ap_bssid.BSSID"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d024["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.LastDataDownlinkRate"
        and criterion["operator"] == ">="
        and criterion["reference"] == "driver_rate.DriverLastDownlinkRateLower"
        for criterion in d024["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.LastDataDownlinkRate"
        and criterion["operator"] == "<="
        and criterion["reference"] == "driver_rate.DriverLastDownlinkRateUpper"
        for criterion in d024["pass_criteria"]
    )

    d025 = yaml.safe_load(
        (cases_dir / "D025_lastdatauplinkrate.yaml").read_text(encoding="utf-8")
    )
    d025_commands = "\n".join(str(step.get("command", "")) for step in d025["steps"])
    assert d025["source"]["row"] == 25
    assert "aliases" not in d025
    assert d025["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LastDataUplinkRate?"'
    assert "LastDataUplinkRate=1733333" not in d025["hlapi_command"]
    assert 'WiFi.SSID.4.BSSID?' in d025_commands
    assert "DriverLastUplinkRateRounded=" in d025_commands
    assert any(
        criterion["field"] == "result.LastDataUplinkRate"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_rate.DriverLastUplinkRateRounded"
        for criterion in d025["pass_criteria"]
    )

    d026 = yaml.safe_load(
        (cases_dir / "D026_linkbandwidth.yaml").read_text(encoding="utf-8")
    )
    d026_commands = "\n".join(str(step.get("command", "")) for step in d026["steps"])
    assert d026["source"]["row"] == 26
    assert d026["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.LinkBandwidth?"'
    assert "LinkBandwidth=160MHz" not in d026["hlapi_command"]
    assert 'WiFi.Radio.1.OperatingChannelBandwidth?' in d026_commands
    assert "DriverLinkBandwidth=" in d026_commands
    assert any(
        criterion["field"] == "result.LinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "radio_bw.OperatingChannelBandwidth"
        for criterion in d026["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.LinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw.DriverLinkBandwidth"
        for criterion in d026["pass_criteria"]
    )

    d027 = yaml.safe_load(
        (cases_dir / "D027_macaddress_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d027_commands = "\n".join(str(step.get("command", "")) for step in d027["steps"])
    assert d027["source"]["row"] == 27
    assert "MACAddress?" in d027["hlapi_command"]
    assert "MACAddress=AA:6B:30:4E:8E:5C" not in d027["hlapi_command"]
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl1 status" in d027_commands
    assert "AssocMAC=" in d027_commands
    assert any(
        criterion["field"] == "assoc_driver.AssocMAC"
        and criterion["reference"] == "sta_status.address"
        for criterion in d027["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.MACAddress"
        and criterion["reference"] == "assoc_driver.AssocMAC"
        for criterion in d027["pass_criteria"]
    )

    multiband_direct_cases = {
        "D321_broadcastpacketsreceived.yaml": {"row": 321, "api": "BroadcastPacketsReceived", "driver": "DriverBroadcastPacketsReceived", "awk_field": "$23", "expected": "Pass"},
        "D322_broadcastpacketssent.yaml": {"row": 322, "api": "BroadcastPacketsSent", "driver": "DriverBroadcastPacketsSent", "awk_field": "$24", "expected": "Pass"},
        "D323_bytesreceived_ssid_stats.yaml": {"row": 323, "api": "BytesReceived", "driver": "DriverBytesReceived", "awk_field": "rxbyte", "expected": "Pass"},
        "D324_bytessent_ssid_stats.yaml": {
            "row": 324,
            "api": "BytesSent",
            "driver": "DriverBytesSent",
            "awk_field": "txbyte",
            "expected": "Pass",
            "assoc_field": "snapshot_5g.AssocMac5g",
            "direct_field": "snapshot_5g.DirectBytesSent5g",
            "get_ref": "snapshot_5g.GetSSIDStatsBytesSent5g",
            "driver_ref": "snapshot_5g.DriverBytesSent5g",
        },
        "D325_discardpacketsreceived.yaml": {"row": 325, "api": "DiscardPacketsReceived", "driver": "DriverDiscardPacketsReceived", "awk_field": "rxdiscard", "expected": "Pass"},
        "D326_discardpacketssent.yaml": {"row": 326, "api": "DiscardPacketsSent", "driver": "DriverDiscardPacketsSent", "awk_field": "txdiscard", "expected": "Pass"},
        "D327_errorsreceived_ssid_stats.yaml": {"row": 327, "api": "ErrorsReceived", "driver": "DriverErrorsReceived", "awk_field": "rxerror", "expected": "Skip"},
        "D328_errorssent_ssid_stats.yaml": {"row": 328, "api": "ErrorsSent", "driver": "DriverErrorsSent", "awk_field": "txerror", "expected": "Pass"},
        "D329_failedretranscount_ssid_stats.yaml": {"row": 329, "api": "FailedRetransCount", "driver": "DriverFailedRetransCount", "awk_field": "txretransfail", "expected": "Fail"},
        "D330_multicastpacketsreceived.yaml": {"row": 330, "api": "MulticastPacketsReceived", "driver": "DriverMulticastPacketsReceived", "awk_field": "rxmulti", "expected": "Pass"},
        "D331_multicastpacketssent.yaml": {
            "row": 331,
            "api": "MulticastPacketsSent",
            "driver": "DriverMulticastPacketsSent",
            "awk_field": "txmulti",
            "expected": "Pass",
            "assoc_field": "snapshot_5g.AssocMac5g",
            "direct_field": "snapshot_5g.DirectMulticastPacketsSent5g",
            "get_ref": "snapshot_5g.GetSSIDStatsMulticastPacketsSent5g",
            "driver_ref": "snapshot_5g.DriverMulticastPacketsSent5g",
        },
        "D332_packetsreceived_ssid_stats.yaml": {"row": 332, "api": "PacketsReceived", "driver": "DriverPacketsReceived", "awk_field": "rxframe", "expected": "Pass"},
        "D333_packetssent_ssid_stats.yaml": {
            "row": 333,
            "api": "PacketsSent",
            "driver": "DriverPacketsSent",
            "awk_field": "txframe",
            "expected": "Pass",
            "assoc_field": "snapshot_5g.AssocMac5g",
            "direct_field": "snapshot_5g.DirectPacketsSent5g",
            "get_ref": "snapshot_5g.GetSSIDStatsPacketsSent5g",
            "driver_ref": "snapshot_5g.DriverPacketsSent5g",
        },
        "D334_retranscount_ssid_stats.yaml": {"row": 334, "api": "RetransCount", "driver": "DriverRetransCount", "awk_field": "txretrans", "expected": "Fail"},
        "D335_unicastpacketsreceived.yaml": {"row": 335, "api": "UnicastPacketsReceived", "driver": "DriverUnicastPacketsReceived", "awk_field": "rxframe", "expected": "Pass"},
        "D336_unicastpacketssent.yaml": {
            "row": 336,
            "api": "UnicastPacketsSent",
            "driver": "DriverUnicastPacketsSent",
            "awk_field": "d11_txfrag",
            "expected": "Pass",
            "assoc_field": "snapshot_5g.AssocMac5g",
            "direct_field": "snapshot_5g.DirectUnicastPacketsSent5g",
            "get_ref": "snapshot_5g.GetSSIDStatsUnicastPacketsSent5g",
            "driver_ref": "snapshot_5g.DriverUnicastPacketsSent5g",
        },
        "D337_unknownprotopacketsreceived_ssid_stats.yaml": {"row": 337, "api": "UnknownProtoPacketsReceived", "driver": "DriverUnknownProtoPacketsReceived", "awk_field": "rxbadprotopkts", "expected": "Skip"},
        "D406_multipleretrycount_ssid_stats.yaml": {"row": 406, "api": "MultipleRetryCount", "driver": "DriverMultipleRetryCount", "awk_field": "txretrie", "expected": "Pass"},
        "D407_retrycount_ssid_stats.yaml": {"row": 407, "api": "RetryCount", "driver": "DriverRetryCount", "awk_field": "txretry", "expected": "Pass"},
        "D495_retrycount_ssid_stats_verified.yaml": {"row": 495, "api": "RetryCount", "expected": "Not Supported"},
    }

    for filename, meta in multiband_direct_cases.items():
        case_data = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        assoc_field = meta.get("assoc_field", "assoc_5g.AssocMac5g")
        direct_field = meta.get("direct_field", f"direct_5g.{meta['api']}")
        get_ref = meta.get("get_ref", f"getssid_5g.GetSSIDStats{meta['api']}5g")
        assert "aliases" not in case_data
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
        assert _has_assoc_mac_regex(case_data, assoc_field)
        assert any(
            criterion["field"] == direct_field
            and criterion["operator"] == "equals"
            and criterion["reference"] == get_ref
            for criterion in case_data["pass_criteria"]
        )
        if "driver" in meta:
            driver_ref = meta.get("driver_ref", f"driver_5g.{meta['driver']}5g")
            assert f"{meta['driver']}5g=" in commands
            assert f"{meta['driver']}6g=" in commands
            assert f"{meta['driver']}24g=" in commands
            assert meta["awk_field"] in commands
            assert any(
                criterion["field"] == direct_field
                and criterion["operator"] == "equals"
                and criterion["reference"] == driver_ref
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
        "D300_getssidstats_broadcastpacketsreceived.yaml": {"row": 300, "api": "BroadcastPacketsReceived", "expected": "Pass"},
        "D301_getssidstats_broadcastpacketssent.yaml": {"row": 301, "api": "BroadcastPacketsSent", "expected": "Pass"},
        "D302_getssidstats_bytesreceived.yaml": {"row": 227, "api": "BytesReceived", "expected": "Fail"},
        "D303_getssidstats_bytessent.yaml": {"row": 228, "api": "BytesSent", "expected": "Pass"},
        "D304_getssidstats_discardpacketsreceived.yaml": {"row": 304, "api": "DiscardPacketsReceived", "expected": "Pass"},
        "D305_getssidstats_discardpacketssent.yaml": {"row": 305, "api": "DiscardPacketsSent", "expected": "Pass"},
        "D306_getssidstats_errorsreceived.yaml": {"row": 306, "api": "ErrorsReceived", "expected": "Pass"},
        "D307_getssidstats_errorssent.yaml": {"row": 307, "api": "ErrorsSent", "expected": "Pass"},
        "D308_getssidstats_failedretranscount.yaml": {"row": 308, "api": "FailedRetransCount", "expected": "Not Supported", "name": "FailedRetransCount — WiFi.SSID.{i}.getSSIDStats()."},
        "D309_getssidstats_multicastpacketsreceived.yaml": {"row": 309, "api": "MulticastPacketsReceived", "expected": "Pass"},
        "D310_getssidstats_multicastpacketssent.yaml": {"row": 310, "api": "MulticastPacketsSent", "expected": "Pass"},
        "D311_getssidstats_packetsreceived.yaml": {"row": 311, "api": "PacketsReceived", "expected": "Pass"},
        "D312_getssidstats_packetssent.yaml": {"row": 312, "api": "PacketsSent", "expected": "Pass"},
        "D314_getssidstats_unicastpacketsreceived.yaml": {"row": 314, "api": "UnicastPacketsReceived", "expected": "Pass"},
        "D315_getssidstats_unicastpacketssent.yaml": {"row": 315, "api": "UnicastPacketsSent", "expected": "Pass"},
        "D316_getssidstats_unknownprotopacketsreceived.yaml": {"row": 316, "api": "UnknownProtoPacketsReceived", "expected": "Not Supported", "name": "UnknownProtoPacketsReceived — WiFi.SSID.{i}.getSSIDStats()."},
    }

    for filename, meta in multiband_getssid_cases.items():
        case_data = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        dnum = filename.split("_")[0]  # e.g. "D300"
        num = dnum[1:]  # e.g. "302"
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        assert "aliases" not in case_data
        assert case_data["id"] == f"d{num}-getssidstats-{meta['api'].lower()}"
        assert case_data["name"] == meta.get("name", f"D{num} getSSIDStats {meta['api']}")
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["source"]["api"] == "getSSIDStats()"
        assert 'WiFi.SSID.4.getSSIDStats()' in commands
        assert 'WiFi.SSID.6.getSSIDStats()' in commands
        assert 'WiFi.SSID.8.getSSIDStats()' in commands
        assert len(case_data["steps"]) == 3
        if meta["expected"] == "Not Supported":
            assert any(
                criterion["field"] == f"stats_5g.{meta['api']}"
                and criterion["operator"] == "equals"
                and str(criterion.get("value")) == "0"
                for criterion in case_data["pass_criteria"]
            )
            assert any(
                criterion["field"] == f"stats_6g.{meta['api']}"
                and criterion["operator"] == "equals"
                and str(criterion.get("value")) == "0"
                for criterion in case_data["pass_criteria"]
            )
            assert any(
                criterion["field"] == f"stats_24g.{meta['api']}"
                and criterion["operator"] == "equals"
                and str(criterion.get("value")) == "0"
                for criterion in case_data["pass_criteria"]
            )
        else:
            assert any(
                criterion["field"] == f"stats_5g.{meta['api']}"
                and criterion["operator"] == "regex"
                and criterion["value"] == r"^\d+$"
                for criterion in case_data["pass_criteria"]
            )
            assert any(
                criterion["field"] == f"stats_6g.{meta['api']}"
                and criterion["operator"] == "regex"
                for criterion in case_data["pass_criteria"]
            )
            assert any(
                criterion["field"] == f"stats_24g.{meta['api']}"
                and criterion["operator"] == "regex"
                for criterion in case_data["pass_criteria"]
            )

    # Cases not listed default to all-Pass.
    _wmm_expected = {
        499: ("Fail", "Fail", "Fail"),
        502: ("Fail", "Fail", "Fail"),
        505: ("Fail", "Fail", "Fail"),
        506: ("Fail", "Fail", "Fail"),
        507: ("Fail", "Fail", "Fail"),
        508: ("Fail", "Fail", "Fail"),
        524: ("Fail", "Fail", "Fail"),
    }
    for case_num in range(496, 528):
        if case_num in {496, 499, 502, 505, 506, 507, 510, 512, 513, 517, 518, 519, 520, 521, 522, 523, 525, 526, 527}:
            continue
        filename = next(cases_dir.glob(f"D{case_num}_*.yaml"))
        case_data = yaml.safe_load(filename.read_text(encoding="utf-8"))
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        ac = case_data["source"]["api"]
        metric = case_data["source"]["object"].split("Stats.", 1)[1].rstrip(".")
        assert "aliases" not in case_data
        assert case_data["source"]["row"] == case_num
        assert case_data["bands"] == ["5g", "6g", "2.4g"]
        exp5, exp6, exp24 = _wmm_expected.get(case_num, ("Pass", "Pass", "Pass"))
        assert f"WiFi.SSID.4.Stats.{metric}.{ac}?" in commands
        assert f"WiFi.SSID.6.Stats.{metric}.{ac}?" in commands
        assert f"WiFi.SSID.8.Stats.{metric}.{ac}?" in commands
        assert any(
            criterion["field"] == f"getter_5g.{ac}"
            and criterion["operator"] == "regex"
            for criterion in case_data["pass_criteria"]
        )


def test_pending_method_calibration_cases_use_runtime_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D004-kickstation",
        "wifi-llapi-D005-kickstationreason",
        "wifi-llapi-D006-sendbsstransferrequest",
        "wifi-llapi-D007-sendremotemeasumentrequest",
    }.issubset(discoverable_ids)

    d004 = load_case(cases_dir / "D004_kickstation.yaml")
    d004_commands = "\n".join(str(step.get("command", "")) for step in d004["steps"])
    d004_links = {link["band"] for link in d004["topology"]["links"]}
    assert "aliases" not in d004
    assert d004_links == {"5g", "6g", "2.4g"}
    assert "changed_from" not in {str(criterion.get("operator")) for criterion in d004["pass_criteria"]}
    assert not any("compare_to" in criterion for criterion in d004["pass_criteria"])
    assert "kickStation(MACAddress={{assoc_5g.AssocMac5g}})" in d004_commands
    assert "kickStation(MACAddress={{assoc_6g.AssocMac6g}})" in d004_commands
    assert "kickStation(MACAddress={{assoc_24g.AssocMac24g}})" in d004_commands
    assert "iw dev wl0 link" in d004_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 status" in d004_commands
    assert "iw dev wl2 link" in d004_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 status" in d004_commands
    assert "wl -i wl0 join TestPilot_5G imode bss" not in d004_commands
    assert "wl -i wl2 join TestPilot_24G imode bss" not in d004_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d004["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_5g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_5g.DisassociationTime"
        for criterion in d004["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_6g.AssocMac6g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d004["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_6g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_6g.DisassociationTime"
        for criterion in d004["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_24g.AssocMac24g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d004["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_24g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_24g.DisassociationTime"
        for criterion in d004["pass_criteria"]
    )

    d005 = load_case(cases_dir / "D005_kickstationreason.yaml")
    d005_commands = "\n".join(str(step.get("command", "")) for step in d005["steps"])
    d005_links = {link["band"] for link in d005["topology"]["links"]}
    assert d005_links == {"5g", "6g", "2.4g"}
    assert "changed_from" not in {str(criterion.get("operator")) for criterion in d005["pass_criteria"]}
    assert not any("compare_to" in criterion for criterion in d005["pass_criteria"])
    assert "kickStationReason(macaddress={{assoc_5g.AssocMac5g}},reason=1)" in d005_commands
    assert "kickStationReason(macaddress={{assoc_6g.AssocMac6g}},reason=1)" in d005_commands
    assert "kickStationReason(macaddress={{assoc_24g.AssocMac24g}},reason=1)" in d005_commands
    assert "iw dev wl0 link" in d005_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 status" in d005_commands
    assert "iw dev wl2 link" in d005_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 status" in d005_commands
    assert "wl -i wl0 join TestPilot_5G imode bss" not in d005_commands
    assert "wl -i wl2 join TestPilot_24G imode bss" not in d005_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d005["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_5g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_5g.DisassociationTime"
        for criterion in d005["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_6g.AssocMac6g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d005["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_6g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_6g.DisassociationTime"
        for criterion in d005["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_24g.AssocMac24g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d005["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_24g.DisassociationTime"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "before_24g.DisassociationTime"
        for criterion in d005["pass_criteria"]
    )

    d006 = load_case(cases_dir / "D006_sendbsstransferrequest.yaml")
    d006_commands = "\n".join(str(step.get("command", "")) for step in d006["steps"])
    d006_links = {link["band"] for link in d006["topology"]["links"]}
    assert "config" not in d006["topology"]["devices"]["STA"]
    assert d006_links == {"5g", "6g", "2.4g"}
    assert "WiFi.AccessPoint.1.MBOEnable=1" in d006_commands
    assert "WiFi.AccessPoint.3.MBOEnable=1" in d006_commands
    assert "WiFi.AccessPoint.5.MBOEnable=1" in d006_commands
    assert "iw dev wl0 link" in d006_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 status" in d006_commands
    assert "iw dev wl1 link" in d006_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl1 status" in d006_commands
    assert "iw dev wl2 link" in d006_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 status" in d006_commands
    assert "wl -i wl0 join TestPilot_5G imode bss" not in d006_commands
    assert "wl -i wl2 join TestPilot_24G imode bss" not in d006_commands
    assert "sendBssTransferRequest(mac={{assoc_5g.AssocMac5g}}" in d006_commands
    assert "sendBssTransferRequest(mac={{assoc_6g.AssocMac6g}}" in d006_commands
    assert "sendBssTransferRequest(mac={{assoc_24g.AssocMac24g}}" in d006_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "[-1]"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_6g.AssocMac6g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "[-1]"
        for criterion in d006["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "[-1]"
        for criterion in d006["pass_criteria"]
    )

    d007 = load_case(cases_dir / "D007_sendremotemeasumentrequest.yaml")
    d007_commands = "\n".join(str(step.get("command", "")) for step in d007["steps"])
    d007_links = {link["band"] for link in d007["topology"]["links"]}
    assert "config" not in d007["topology"]["devices"]["STA"]
    assert d007_links == {"5g", "6g", "2.4g"}
    assert "sendRemoteMeasumentRequest" in d007_commands
    assert "sendRemoteMeasurementRequest" not in d007_commands
    assert "iw dev wl0 link" in d007_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 status" in d007_commands
    assert "iw dev wl1 link" in d007_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl1 status" in d007_commands
    assert "iw dev wl2 link" in d007_commands
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 status" in d007_commands
    assert "wl -i wl0 join TestPilot_5G imode bss" not in d007_commands
    assert "wl -i wl2 join TestPilot_24G imode bss" not in d007_commands
    assert "sendRemoteMeasumentRequest(mac={{assoc_5g.AssocMac5g}}" in d007_commands
    assert "sendRemoteMeasumentRequest(mac={{assoc_6g.AssocMac6g}}" in d007_commands
    assert "sendRemoteMeasumentRequest(mac={{assoc_24g.AssocMac24g}}" in d007_commands
    assert any(
        criterion["field"] == "assoc_5g.AssocMac5g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?s)\[\s*\[\s*\]\s*\]"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_6g.AssocMac6g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?s)\[\s*\[\s*\]\s*\]"
        for criterion in d007["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"(?s)\[\s*\[\s*\]\s*\]"
        for criterion in d007["pass_criteria"]
    )


def test_assoc_mac_preconditions_do_not_hardcode_sample_station_macs():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    hardcoded_mac = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")

    for case_path in sorted(cases_dir.glob("*.yaml")):
        case_data = load_case(case_path)
        for criterion in case_data.get("pass_criteria", []):
            field = str(criterion.get("field", "")).strip()
            operator = str(criterion.get("operator", "")).strip().lower()
            value = str(criterion.get("value", "")).strip()
            if "AssocMac" not in field:
                continue
            assert not (
                operator == "equals" and hardcoded_mac.fullmatch(value)
            ), f"{case_path.name} still hardcodes assoc MAC precondition: {field}={value}"


def test_pending_readonly_associateddevice_cases_use_live_cross_checks():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D011-avgsignalstrength",
        "wifi-llapi-D012-avgsignalstrengthbychain",
        "wifi-llapi-D013-capabilities",
        "wifi-llapi-D016-downlinkbandwidth",
    }.issubset(discoverable_ids)

    d011 = load_case(cases_dir / "D011_avgsignalstrength.yaml")
    d011_commands = "\n".join(str(step.get("command", "")) for step in d011["steps"])
    d011_links = {link["band"] for link in d011["topology"]["links"]}
    assert d011_links == {"5g", "6g", "2.4g"}
    assert "wl -i wl0 assoclist" in d011_commands
    assert "wl -i wl1 assoclist" in d011_commands
    assert "wl -i wl2 assoclist" in d011_commands
    assert _has_assoc_mac_regex(d011, "assoc_5g.AssocMac5g")
    assert _has_assoc_mac_regex(d011, "assoc_6g.AssocMac6g")
    assert _has_assoc_mac_regex(d011, "assoc_24g.AssocMac24g")
    assert any(
        criterion["field"] == "result_5g.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi_5g.DriverSmoothedRSSI5g"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi_6g.DriverSmoothedRSSI6g"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AvgSignalStrength"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rssi_24g.DriverSmoothedRSSI24g"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d011["pass_criteria"]
    )

    d012 = load_case(cases_dir / "D012_avgsignalstrengthbychain.yaml")
    d012_commands = "\n".join(str(step.get("command", "")) for step in d012["steps"])
    d012_links = {link["band"] for link in d012["topology"]["links"]}
    assert d012["source"]["row"] == 12
    assert "AvgSignalStrengthByChain?" in d012["hlapi_command"]
    assert d012_links == {"5g", "6g", "2.4g"}
    assert "wl -i wl0 assoclist" in d012_commands
    assert "wl -i wl1 assoclist" in d012_commands
    assert "wl -i wl2 assoclist" in d012_commands
    assert _has_assoc_mac_regex(d012, "assoc_5g.AssocMac5g")
    assert _has_assoc_mac_regex(d012, "assoc_6g.AssocMac6g")
    assert any(
        criterion["field"] == "result_5g.AvgSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-?[0-9]+$"
        for criterion in d012["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.AvgSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-?[0-9]+$"
        for criterion in d012["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AvgSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-?[0-9]+$"
        for criterion in d012["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.AvgSignalStrengthByChain"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d012["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.AvgSignalStrengthByChain"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d012["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.AvgSignalStrengthByChain"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d012["pass_criteria"]
    )

    d013 = load_case(cases_dir / "D013_capabilities.yaml")
    d013_commands = "\n".join(str(step.get("command", "")) for step in d013["steps"])
    d013_links = {link["band"] for link in d013["topology"]["links"]}
    assert d013["source"]["row"] == 13
    assert d013["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.{i}.AssociatedDevice.1.Capabilities?"'
    assert d013_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities?' in d013_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.Capabilities?' in d013_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.Capabilities?' in d013_commands
    assert "DriverRrmCapability5g=" in d013_commands
    assert "DriverRrmCapability6g=" in d013_commands
    assert "DriverRrmCapability24g=" in d013_commands
    assert _has_assoc_mac_regex(d013, "assoc_5g.AssocMac5g")
    assert _has_assoc_mac_regex(d013, "assoc_6g.AssocMac6g")
    assert _has_assoc_mac_regex(d013, "assoc_24g.AssocMac24g")
    assert any(
        criterion["field"] == "driver_rrm_5g.DriverRrmCapability5g"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0x32"
        for criterion in d013["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rrm_6g.DriverRrmCapability6g"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0x0"
        for criterion in d013["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_rrm_24g.DriverRrmCapability24g"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0x32"
        for criterion in d013["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.Capabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "RRM,BTM,QOS_MAP"
        for criterion in d013["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.Capabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "BTM,QOS_MAP,PMF"
        for criterion in d013["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.Capabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "RRM,BTM,QOS_MAP"
        for criterion in d013["pass_criteria"]
    )

    d016_raw = yaml.safe_load(
        (cases_dir / "D016_downlinkbandwidth.yaml").read_text(encoding="utf-8")
    )
    d016 = load_case(cases_dir / "D016_downlinkbandwidth.yaml")
    d016_commands = "\n".join(str(step.get("command", "")) for step in d016["steps"])
    d016_links = {link["band"] for link in d016["topology"]["links"]}
    assert "aliases" not in d016_raw
    assert d016["id"] == "wifi-llapi-D016-downlinkbandwidth"
    assert d016["source"]["row"] == 16
    assert d016["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.{i}.AssociatedDevice.1.DownlinkBandwidth?"'
    assert d016_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkBandwidth?' in d016_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.DownlinkBandwidth?' in d016_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkBandwidth?' in d016_commands
    assert "DriverDownlinkBandwidth5g=" in d016_commands
    assert "DriverDownlinkBandwidth6g=" in d016_commands
    assert "DriverDownlinkBandwidth24g=" in d016_commands
    assert any(
        criterion["field"] == "result_5g.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw_5g.DriverDownlinkBandwidth5g"
        for criterion in d016["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw_6g.DriverDownlinkBandwidth6g"
        for criterion in d016["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.DownlinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_bw_24g.DriverDownlinkBandwidth24g"
        for criterion in d016["pass_criteria"]
    )


def test_pending_readonly_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d011 = load_case(cases_dir / "D011_avgsignalstrength.yaml")
    d011_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:19:95",
                "captured": {"AssocMac5g": "2c:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_driver_rssi": {
                "success": True,
                "output": "DriverSmoothedRSSI5g=-27",
                "captured": {"DriverSmoothedRSSI5g": "-27"},
                "timing": 0.01,
            },
            "step4_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.AvgSignalStrength=0",
                "captured": {"AvgSignalStrength": "0"},
                "timing": 0.01,
            },
            "step6_6g_assoc": {
                "success": True,
                "output": "AssocMac6g=2c:59:17:00:19:96",
                "captured": {"AssocMac6g": "2c:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step7_6g_driver_rssi": {
                "success": True,
                "output": "DriverSmoothedRSSI6g=-23",
                "captured": {"DriverSmoothedRSSI6g": "-23"},
                "timing": 0.01,
            },
            "step8_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.AvgSignalStrength=0",
                "captured": {"AvgSignalStrength": "0"},
                "timing": 0.01,
            },
            "step10_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:19:a7",
                "captured": {"AssocMac24g": "2c:59:17:00:19:a7"},
                "timing": 0.01,
            },
            "step11_24g_driver_rssi": {
                "success": True,
                "output": "DriverSmoothedRSSI24g=-31",
                "captured": {"DriverSmoothedRSSI24g": "-31"},
                "timing": 0.01,
            },
            "step12_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.AvgSignalStrength=0",
                "captured": {"AvgSignalStrength": "0"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d011, d011_results) is True

    d011_unexpected_pass_results = {
        "steps": {
            **d011_results["steps"],
            "step8_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.AvgSignalStrength=-23",
                "captured": {"AvgSignalStrength": "-23"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d011, d011_unexpected_pass_results) is False

    d012 = load_case(cases_dir / "D012_avgsignalstrengthbychain.yaml")
    d012_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step3_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.AvgSignalStrengthByChain=-34",
                "captured": {"AvgSignalStrengthByChain": "-34"},
                "timing": 0.01,
            },
            "step5_6g_assoc": {
                "success": True,
                "output": "AssocMac6g=2c:59:17:00:04:86",
                "captured": {"AssocMac6g": "2c:59:17:00:04:86"},
                "timing": 0.01,
            },
            "step6_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.AvgSignalStrengthByChain=-57",
                "captured": {"AvgSignalStrengthByChain": "-57"},
                "timing": 0.01,
            },
            "step8_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "captured": {"AssocMac24g": "2c:59:17:00:04:97"},
                "timing": 0.01,
            },
            "step9_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.AvgSignalStrengthByChain=-16",
                "captured": {"AvgSignalStrengthByChain": "-16"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d012, d012_results) is True

    d012_fail_results = {
        "steps": {
            **d012_results["steps"],
            "step6_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.AvgSignalStrengthByChain=0",
                "captured": {"AvgSignalStrengthByChain": "0"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d012, d012_fail_results) is False

    d013 = load_case(cases_dir / "D013_capabilities.yaml")
    d013_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:19:95",
                "captured": {"AssocMac5g": "2c:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_rrm": {
                "success": True,
                "output": "DriverRrmCapability5g=0x32",
                "captured": {"DriverRrmCapability5g": "0x32"},
                "timing": 0.01,
            },
            "step4_5g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.Capabilities="RRM,BTM,QOS_MAP"',
                "captured": {"Capabilities": "RRM,BTM,QOS_MAP"},
                "timing": 0.01,
            },
            "step6_6g_assoc": {
                "success": True,
                "output": "AssocMac6g=2c:59:17:00:19:96",
                "captured": {"AssocMac6g": "2c:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step7_6g_rrm": {
                "success": True,
                "output": "DriverRrmCapability6g=0x0",
                "captured": {"DriverRrmCapability6g": "0x0"},
                "timing": 0.01,
            },
            "step8_6g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.Capabilities="BTM,QOS_MAP,PMF"',
                "captured": {"Capabilities": "BTM,QOS_MAP,PMF"},
                "timing": 0.01,
            },
            "step10_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:19:a7",
                "captured": {"AssocMac24g": "2c:59:17:00:19:a7"},
                "timing": 0.01,
            },
            "step11_24g_rrm": {
                "success": True,
                "output": "DriverRrmCapability24g=0x32",
                "captured": {"DriverRrmCapability24g": "0x32"},
                "timing": 0.01,
            },
            "step12_24g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.Capabilities="RRM,BTM,QOS_MAP"',
                "captured": {"Capabilities": "RRM,BTM,QOS_MAP"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d013, d013_results) is True

    d013_fail_results = {
        "steps": {
            **d013_results["steps"],
            "step8_6g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.Capabilities="RRM,BTM,QOS_MAP"',
                "captured": {"Capabilities": "RRM,BTM,QOS_MAP"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d013, d013_fail_results) is False

    d015 = load_case(cases_dir / "D015_connectionduration.yaml")
    d015_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:19:95"',
                "captured": {"MACAddress": "2C:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.ConnectionDuration=13",
                "captured": {"ConnectionDuration": "13"},
                "timing": 0.01,
            },
            "step4_5g_get_after_wait": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.ConnectionDuration=17",
                "captured": {"ConnectionDuration": "17"},
                "timing": 0.01,
            },
            "step5_5g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds5g=18",
                "captured": {"DriverConnectionSeconds5g": "18"},
                "timing": 0.01,
            },
            "step7_6g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:19:96"',
                "captured": {"MACAddress": "2C:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step8_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.ConnectionDuration=11",
                "captured": {"ConnectionDuration": "11"},
                "timing": 0.01,
            },
            "step9_6g_get_after_wait": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.ConnectionDuration=15",
                "captured": {"ConnectionDuration": "15"},
                "timing": 0.01,
            },
            "step10_6g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds6g=16",
                "captured": {"DriverConnectionSeconds6g": "16"},
                "timing": 0.01,
            },
            "step12_24g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress="2C:59:17:00:19:A7"',
                "captured": {"MACAddress": "2C:59:17:00:19:A7"},
                "timing": 0.01,
            },
            "step13_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.ConnectionDuration=20",
                "captured": {"ConnectionDuration": "20"},
                "timing": 0.01,
            },
            "step14_24g_get_after_wait": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.ConnectionDuration=24",
                "captured": {"ConnectionDuration": "24"},
                "timing": 0.01,
            },
            "step15_24g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds24g=31",
                "captured": {"DriverConnectionSeconds24g": "31"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d015, d015_results) is True

    d015_fail_results = {
        "steps": {
            **d015_results["steps"],
            "step10_6g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds6g=14",
                "captured": {"DriverConnectionSeconds6g": "14"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d015, d015_fail_results) is False

    d016 = load_case(cases_dir / "D016_downlinkbandwidth.yaml")
    d016_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:19:95"',
                "captured": {"MACAddress": "2C:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkBandwidth=80",
                "captured": {"DownlinkBandwidth": "80"},
                "timing": 0.01,
            },
            "step4_5g_driver_bw": {
                "success": True,
                "output": "DriverDownlinkBandwidth5g=80",
                "captured": {"DriverDownlinkBandwidth5g": "80"},
                "timing": 0.01,
            },
            "step6_6g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:19:96"',
                "captured": {"MACAddress": "2C:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step7_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.DownlinkBandwidth=160",
                "captured": {"DownlinkBandwidth": "160"},
                "timing": 0.01,
            },
            "step8_6g_driver_bw": {
                "success": True,
                "output": "DriverDownlinkBandwidth6g=160",
                "captured": {"DriverDownlinkBandwidth6g": "160"},
                "timing": 0.01,
            },
            "step10_24g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress="2C:59:17:00:19:A7"',
                "captured": {"MACAddress": "2C:59:17:00:19:A7"},
                "timing": 0.01,
            },
            "step11_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkBandwidth=20",
                "captured": {"DownlinkBandwidth": "20"},
                "timing": 0.01,
            },
            "step12_24g_driver_bw": {
                "success": True,
                "output": "DriverDownlinkBandwidth24g=20",
                "captured": {"DriverDownlinkBandwidth24g": "20"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d016, d016_results) is True

    d016_fail_results = {
        "steps": {
            **d016_results["steps"],
            "step8_6g_driver_bw": {
                "success": True,
                "output": "DriverDownlinkBandwidth6g=80",
                "captured": {"DriverDownlinkBandwidth6g": "80"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d016, d016_fail_results) is False

    d017 = load_case(cases_dir / "D017_downlinkmcs.yaml")
    d017_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:19:95"',
                "captured": {"MACAddress": "2C:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkMCS=11",
                "captured": {"DownlinkMCS": "11"},
                "timing": 0.01,
            },
            "step4_5g_driver_mcs": {
                "success": True,
                "output": "DriverDownlinkMCS5g=11",
                "captured": {"DriverDownlinkMCS5g": "11"},
                "timing": 0.01,
            },
            "step6_6g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:19:96"',
                "captured": {"MACAddress": "2C:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step7_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.DownlinkMCS=10",
                "captured": {"DownlinkMCS": "10"},
                "timing": 0.01,
            },
            "step8_6g_driver_mcs": {
                "success": True,
                "output": "DriverDownlinkMCS6g=10",
                "captured": {"DriverDownlinkMCS6g": "10"},
                "timing": 0.01,
            },
            "step10_24g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress="2C:59:17:00:19:A7"',
                "captured": {"MACAddress": "2C:59:17:00:19:A7"},
                "timing": 0.01,
            },
            "step11_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkMCS=9",
                "captured": {"DownlinkMCS": "9"},
                "timing": 0.01,
            },
            "step12_24g_driver_mcs": {
                "success": True,
                "output": "DriverDownlinkMCS24g=9",
                "captured": {"DriverDownlinkMCS24g": "9"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d017, d017_results) is True

    d017_fail_results = {
        "steps": {
            **d017_results["steps"],
            "step8_6g_driver_mcs": {
                "success": True,
                "output": "DriverDownlinkMCS6g=8",
                "captured": {"DriverDownlinkMCS6g": "8"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d017, d017_fail_results) is False


def test_pending_boolean_and_frequency_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D018-downlinkshortguard",
        "wifi-llapi-D020-frequencycapabilities",
    }.issubset(discoverable_ids)

    d018 = load_case(cases_dir / "D018_downlinkshortguard.yaml")
    d018_commands = "\n".join(str(step.get("command", "")) for step in d018["steps"])
    d018_links = {link["band"] for link in d018["topology"]["links"]}
    assert d018["source"]["row"] == 18
    assert d018["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.{i}.AssociatedDevice.1.DownlinkShortGuard?"'
    assert d018_links == {"5g", "6g", "2.4g"}
    assert "operator: in" not in yaml.safe_dump(d018["pass_criteria"])
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d018_commands
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkShortGuard?' in d018_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress?' in d018_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.DownlinkShortGuard?' in d018_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress?' in d018_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkShortGuard?' in d018_commands
    assert "DriverDownlinkShortGuardGI5g=" in d018_commands
    assert "DriverDownlinkShortGuard5g=" in d018_commands
    assert "DriverDownlinkShortGuardGI6g=" in d018_commands
    assert "DriverDownlinkShortGuard6g=" in d018_commands
    assert "DriverDownlinkShortGuardGI24g=" in d018_commands
    assert "DriverDownlinkShortGuard24g=" in d018_commands
    assert "sed -n '/tx nrate/{n;s/.*GI \\([^ ]*\\).*/\\1/p;}'" in d018_commands
    assert 'case "$GI" in 0.4us|0.8us|1.6us) echo DriverDownlinkShortGuard5g=1 ;; 3.2us) echo DriverDownlinkShortGuard5g=0 ;; *) echo DriverDownlinkShortGuard5g=UNKNOWN_GI:$GI ;; esac' in d018_commands
    assert any(
        criterion["field"] == "result_5g.DownlinkShortGuard"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_shortguard_5g.DriverDownlinkShortGuard5g"
        for criterion in d018["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.DownlinkShortGuard"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_shortguard_6g.DriverDownlinkShortGuard6g"
        for criterion in d018["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.DownlinkShortGuard"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_shortguard_24g.DriverDownlinkShortGuard24g"
        for criterion in d018["pass_criteria"]
    )

    d020 = load_case(cases_dir / "D020_frequencycapabilities.yaml")
    d020_commands = "\n".join(str(step.get("command", "")) for step in d020["steps"])
    d020_links = {link["band"] for link in d020["topology"]["links"]}
    assert d020["source"]["row"] == 20
    assert d020["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.{i}.AssociatedDevice.1.FrequencyCapabilities?"'
    assert d020_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d020_commands
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.FrequencyCapabilities?' in d020_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress?' in d020_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.FrequencyCapabilities?' in d020_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress?' in d020_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.FrequencyCapabilities?' in d020_commands
    assert "DriverFrequencyBandsRaw5g=" in d020_commands
    assert "DriverFrequencyCapabilities5g=" in d020_commands
    assert "DriverFrequencyBandsRaw6g=" in d020_commands
    assert "DriverFrequencyCapabilities6g=" in d020_commands
    assert "DriverFrequencyBandsRaw24g=" in d020_commands
    assert "DriverFrequencyCapabilities24g=" in d020_commands
    assert "Frequency Bands Supported" in d020_commands
    assert "2.4GHz" in d020_commands
    assert "5GHz" in d020_commands
    assert "6GHz" in d020_commands
    assert any(
        criterion["field"] == "driver_frequency_5g.DriverFrequencyBandsRaw5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "5G"
        for criterion in d020["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_frequency_6g.DriverFrequencyCapabilities6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "6GHz"
        for criterion in d020["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_5g.FrequencyCapabilities"
        and criterion["operator"] == "empty"
        for criterion in d020["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.FrequencyCapabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "6GHz"
        for criterion in d020["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.FrequencyCapabilities"
        and criterion["operator"] == "empty"
        for criterion in d020["pass_criteria"]
    )


def test_d370_assocdev_active_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}

    d370 = load_case(cases_dir / "D370_active.yaml")
    d370_commands = "\n".join(str(step.get("command", "")) for step in d370["steps"])
    d370_links = {link["band"] for link in d370["topology"]["links"]}

    assert d370["id"] in discoverable_ids
    assert d370["source"]["row"] == 370
    assert d370["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.{i}.AssociatedDevice.1.Active?"'
    assert d370_links == {"5g", "6g", "2.4g"}
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?' in d370_commands
    assert 'WiFi.AccessPoint.1.AssociatedDevice.1.Active?' in d370_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress?' in d370_commands
    assert 'WiFi.AccessPoint.3.AssociatedDevice.1.Active?' in d370_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress?' in d370_commands
    assert 'WiFi.AccessPoint.5.AssociatedDevice.1.Active?' in d370_commands
    assert "wl -i wl0 assoclist" in d370_commands
    assert "wl -i wl1 assoclist" in d370_commands
    assert "wl -i wl2 assoclist" in d370_commands
    assert any(
        criterion["field"] == "driver_assoc_5g.DriverAssocMac5g"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_5g.MACAddress"
        for criterion in d370["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.Active"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d370["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.Active"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d370["pass_criteria"]
    )


def test_d377_radio_maxbitrate_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d377 = load_case(cases_dir / "D377_maxbitrate.yaml")

    assert d377["source"]["row"] == 377
    assert d377["llapi_support"] == "Not Supported"
    assert case_band_results(d377, True) == _expected_case_band_results(d377, True)


def test_d379_radio_mcs_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d379 = load_case(cases_dir / "D379_mcs.yaml")

    assert d379["source"]["row"] == 379
    assert case_band_results(d379, True) == _expected_case_band_results(d379, True)


def test_d380_radio_multiaptypessupported_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d380 = load_case(cases_dir / "D380_multiaptypessupported.yaml")

    assert d380["source"]["row"] == 380
    assert case_band_results(d380, True) == _expected_case_band_results(d380, True)


def test_d384_radio_radcapabilitieshtstr_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d384 = load_case(cases_dir / "D384_radcapabilitieshtstr.yaml")

    assert d384["source"]["row"] == 384
    assert case_band_results(d384, True) == _expected_case_band_results(d384, True)


def test_d385_radio_radcapabilitiesvhtstr_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d385 = load_case(cases_dir / "D385_radcapabilitiesvhtstr.yaml")

    assert d385["source"]["row"] == 385
    assert case_band_results(d385, True) == _expected_case_band_results(d385, True)


def test_d396_getradiostats_errorsreceived_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d396 = load_case(cases_dir / "D396_errorsreceived_radio_stats.yaml")

    assert d396["source"]["row"] == 396
    assert d396["source"]["object"] == "WiFi.Radio.{i}.Stats."
    assert d396["source"]["api"] == "ErrorsReceived"
    assert case_band_results(d396, True) == _expected_case_band_results(d396, True)


def test_d397_getradiostats_errorssent_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d397 = load_case(cases_dir / "D397_errorssent_radio_stats.yaml")

    assert d397["source"]["row"] == 397
    assert d397["source"]["object"] == "WiFi.Radio.{i}.Stats."
    assert d397["source"]["api"] == "ErrorsSent"
    assert case_band_results(d397, True) == _expected_case_band_results(d397, True)


def test_d455_getradiostats_multipleretrycount_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d455_raw = yaml.safe_load(
        (cases_dir / "D455_multipleretrycount_radio_stats.yaml").read_text(encoding="utf-8")
    )
    d455 = load_case(cases_dir / "D455_multipleretrycount_radio_stats.yaml")
    d455_commands = "\n".join(str(step.get("command", "")) for step in d455["steps"])

    assert "aliases" not in d455_raw
    assert d455["id"] == "d455-getradiostats-multipleretrycount"
    assert d455["source"]["row"] == 455
    assert d455["source"]["object"] == "WiFi.Radio.{i}."
    assert d455["source"]["api"] == "getRadioStats()"
    assert d455["hlapi_command"] == 'ubus-cli "WiFi.Radio.{i}.getRadioStats()"'
    assert d455["llapi_support"] == "Support"
    assert d455["implemented_by"] == "pWHM"
    assert d455["bands"] == ["5g", "6g", "2.4g"]
    assert set(d455["topology"]["devices"]) == {"DUT"}
    assert d455["topology"]["links"] == []
    assert len(d455["steps"]) == 6
    assert 'ubus-cli "WiFi.Radio.1.getRadioStats()"' in d455_commands
    assert "DriverMultipleRetryCount5g=" in d455_commands
    assert "DriverMultipleRetryCount6g=" in d455_commands
    assert "DriverMultipleRetryCount24g=" in d455_commands
    assert any(
        criterion["field"] == "method_5g.MultipleRetryCount"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_5g.DriverMultipleRetryCount5g"
        for criterion in d455["pass_criteria"]
    )
    assert any(
        criterion["field"] == "method_6g.MultipleRetryCount"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_6g.DriverMultipleRetryCount6g"
        for criterion in d455["pass_criteria"]
    )
    assert any(
        criterion["field"] == "method_24g.MultipleRetryCount"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_24g.DriverMultipleRetryCount24g"
        for criterion in d455["pass_criteria"]
    )
    assert case_band_results(d455, True) == _expected_case_band_results(d455, True)


def test_d455_getradiostats_multipleretrycount_setup_env(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d455 = load_case(cases_dir / "D455_multipleretrycount_radio_stats.yaml")

    assert plugin.setup_env(d455, topology=topology) is True
    plugin.teardown(d455, topology)


def test_d455_getradiostats_multipleretrycount_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d455 = load_case(cases_dir / "D455_multipleretrycount_radio_stats.yaml")

    def method_output(radio: str, value: str) -> str:
        return "\n".join(
            [
                f"WiFi.Radio.{radio}.getRadioStats() returned",
                "[",
                "{",
                f"MultipleRetryCount = {value},",
                "}",
                "]",
            ]
        )

    d455_results = {
        "steps": {
            "step1_method_5g": {
                "success": True,
                "output": method_output("1", "0"),
                "timing": 0.01,
            },
            "step2_driver_5g": {
                "success": True,
                "output": "DriverMultipleRetryCount5g=0",
                "timing": 0.01,
            },
            "step3_method_6g": {
                "success": True,
                "output": method_output("2", "0"),
                "timing": 0.01,
            },
            "step4_driver_6g": {
                "success": True,
                "output": "DriverMultipleRetryCount6g=0",
                "timing": 0.01,
            },
            "step5_method_24g": {
                "success": True,
                "output": method_output("3", "0"),
                "timing": 0.01,
            },
            "step6_driver_24g": {
                "success": True,
                "output": "DriverMultipleRetryCount24g=0",
                "timing": 0.01,
            },
        }
    }

    assert plugin.evaluate(d455, d455_results) is True


def test_pending_boolean_and_frequency_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d018 = load_case(cases_dir / "D018_downlinkshortguard.yaml")
    d018_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:19:95"',
                "captured": {"MACAddress": "2C:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.DownlinkShortGuard=1",
                "captured": {"DownlinkShortGuard": "1"},
                "timing": 0.01,
            },
            "step4_5g_driver_shortguard": {
                "success": True,
                "output": "DriverAssocMac5g=2C:59:17:00:19:95\nDriverDownlinkShortGuardGI5g=1.6us\nDriverDownlinkShortGuard5g=1",
                "captured": {
                    "DriverAssocMac5g": "2C:59:17:00:19:95",
                    "DriverDownlinkShortGuardGI5g": "1.6us",
                    "DriverDownlinkShortGuard5g": "1",
                },
                "timing": 0.01,
            },
            "step6_6g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:19:96"',
                "captured": {"MACAddress": "2C:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step7_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.DownlinkShortGuard=1",
                "captured": {"DownlinkShortGuard": "1"},
                "timing": 0.01,
            },
            "step8_6g_driver_shortguard": {
                "success": True,
                "output": "DriverAssocMac6g=2C:59:17:00:19:96\nDriverDownlinkShortGuardGI6g=0.8us\nDriverDownlinkShortGuard6g=1",
                "captured": {
                    "DriverAssocMac6g": "2C:59:17:00:19:96",
                    "DriverDownlinkShortGuardGI6g": "0.8us",
                    "DriverDownlinkShortGuard6g": "1",
                },
                "timing": 0.01,
            },
            "step10_24g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress="2C:59:17:00:19:A7"',
                "captured": {"MACAddress": "2C:59:17:00:19:A7"},
                "timing": 0.01,
            },
            "step11_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.DownlinkShortGuard=1",
                "captured": {"DownlinkShortGuard": "1"},
                "timing": 0.01,
            },
            "step12_24g_driver_shortguard": {
                "success": True,
                "output": "DriverAssocMac24g=2C:59:17:00:19:A7\nDriverDownlinkShortGuardGI24g=0.8us\nDriverDownlinkShortGuard24g=1",
                "captured": {
                    "DriverAssocMac24g": "2C:59:17:00:19:A7",
                    "DriverDownlinkShortGuardGI24g": "0.8us",
                    "DriverDownlinkShortGuard24g": "1",
                },
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d018, d018_results) is True

    d018_fail_results = {
        "steps": {
            **d018_results["steps"],
            "step12_24g_driver_shortguard": {
                "success": True,
                "output": "DriverAssocMac24g=2C:59:17:00:19:A7\nDriverDownlinkShortGuardGI24g=3.2us\nDriverDownlinkShortGuard24g=0",
                "captured": {
                    "DriverAssocMac24g": "2C:59:17:00:19:A7",
                    "DriverDownlinkShortGuardGI24g": "3.2us",
                    "DriverDownlinkShortGuard24g": "0",
                },
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d018, d018_fail_results) is False

    d020 = load_case(cases_dir / "D020_frequencycapabilities.yaml")
    d020_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:19:95"',
                "captured": {"MACAddress": "2C:59:17:00:19:95"},
                "timing": 0.01,
            },
            "step3_5g_driver_frequency": {
                "success": True,
                "output": "DriverAssocMac5g=2C:59:17:00:19:95\nDriverFrequencyBandsRaw5g=5G\nDriverFrequencyCapabilities5g=5GHz",
                "captured": {
                    "DriverAssocMac5g": "2C:59:17:00:19:95",
                    "DriverFrequencyBandsRaw5g": "5G",
                    "DriverFrequencyCapabilities5g": "5GHz",
                },
                "timing": 0.01,
            },
            "step4_5g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.FrequencyCapabilities=""',
                "captured": {"FrequencyCapabilities": ""},
                "timing": 0.01,
            },
            "step6_6g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:19:96"',
                "captured": {"MACAddress": "2C:59:17:00:19:96"},
                "timing": 0.01,
            },
            "step7_6g_driver_frequency": {
                "success": True,
                "output": "DriverAssocMac6g=2C:59:17:00:19:96\nDriverFrequencyBandsRaw6g=6G\nDriverFrequencyCapabilities6g=6GHz",
                "captured": {
                    "DriverAssocMac6g": "2C:59:17:00:19:96",
                    "DriverFrequencyBandsRaw6g": "6G",
                    "DriverFrequencyCapabilities6g": "6GHz",
                },
                "timing": 0.01,
            },
            "step8_6g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.FrequencyCapabilities="6GHz"',
                "captured": {"FrequencyCapabilities": "6GHz"},
                "timing": 0.01,
            },
            "step10_24g_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.MACAddress="2C:59:17:00:19:A7"',
                "captured": {"MACAddress": "2C:59:17:00:19:A7"},
                "timing": 0.01,
            },
            "step11_24g_driver_frequency": {
                "success": True,
                "output": "DriverAssocMac24g=2C:59:17:00:19:A7\nDriverFrequencyBandsRaw24g=2.4G\nDriverFrequencyCapabilities24g=2.4GHz",
                "captured": {
                    "DriverAssocMac24g": "2C:59:17:00:19:A7",
                    "DriverFrequencyBandsRaw24g": "2.4G",
                    "DriverFrequencyCapabilities24g": "2.4GHz",
                },
                "timing": 0.01,
            },
            "step12_24g_get": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.AssociatedDevice.1.FrequencyCapabilities=""',
                "captured": {"FrequencyCapabilities": ""},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d020, d020_results) is True

    d020_fail_results = {
        "steps": {
            **d020_results["steps"],
            "step7_6g_driver_frequency": {
                "success": True,
                "output": "DriverAssocMac6g=2C:59:17:00:19:96\nDriverFrequencyBandsRaw6g=5G\nDriverFrequencyCapabilities6g=5GHz",
                "captured": {
                    "DriverAssocMac6g": "2C:59:17:00:19:96",
                    "DriverFrequencyBandsRaw6g": "5G",
                    "DriverFrequencyCapabilities6g": "5GHz",
                },
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d020, d020_fail_results) is False


def test_pending_inactive_and_bandwidth_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D023-inactive",
        "wifi-llapi-D028-maxbandwidthsupported",
    }.issubset(discoverable_ids)

    d023 = load_case(cases_dir / "D023_inactive.yaml")
    d023_commands = "\n".join(str(step.get("command", "")) for step in d023["steps"])
    d023_links = {link["band"] for link in d023["topology"]["links"]}
    assert d023["source"]["row"] == 23
    assert d023_links == {"5g", "6g", "2.4g"}
    assert "wl -i wl0 assoclist" in d023_commands
    assert "wl -i wl1 assoclist" in d023_commands
    assert "wl -i wl2 assoclist" in d023_commands
    assert any(
        criterion["field"] == "result_5g.Inactive"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^\d+$"
        for criterion in d023["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_6g.Inactive"
        and criterion["operator"] == ">="
        and str(criterion["value"]) == "0"
        for criterion in d023["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.Inactive"
        and criterion["operator"] == ">="
        and str(criterion["value"]) == "0"
        for criterion in d023["pass_criteria"]
    )

    d028 = load_case(cases_dir / "D028_maxbandwidthsupported.yaml")
    d028_commands = "\n".join(str(step.get("command", "")) for step in d028["steps"])
    d028_links = {link["band"] for link in d028["topology"]["links"]}
    assert d028["source"]["row"] == 28
    assert d028_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d028_commands
    assert "wl -i wl2 assoclist" in d028_commands
    assert any(
        criterion["field"] == "result_5g.MaxBandwidthSupported"
        and criterion["operator"] == "equals"
        and criterion["value"] == "160MHz"
        for criterion in d028["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.MaxBandwidthSupported"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^(20MHz|40MHz|80MHz|160MHz|Unknown)$"
        for criterion in d028["pass_criteria"]
    )


def test_pending_inactive_and_bandwidth_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d023 = load_case(cases_dir / "D023_inactive.yaml")
    d023_results = {
        "steps": {
            "step2_5g_assoc": {
                "success": True,
                "output": "AssocMac5g=2c:59:17:00:04:85",
                "captured": {"AssocMac5g": "2c:59:17:00:04:85"},
                "timing": 0.01,
            },
            "step3_5g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.Inactive=14",
                "captured": {"Inactive": "14"},
                "timing": 0.01,
            },
            "step5_6g_assoc": {
                "success": True,
                "output": "AssocMac6g=2c:59:17:00:04:86",
                "captured": {"AssocMac6g": "2c:59:17:00:04:86"},
                "timing": 0.01,
            },
            "step6_6g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.3.AssociatedDevice.1.Inactive=2",
                "captured": {"Inactive": "2"},
                "timing": 0.01,
            },
            "step8_24g_assoc": {
                "success": True,
                "output": "AssocMac24g=2c:59:17:00:04:97",
                "captured": {"AssocMac24g": "2c:59:17:00:04:97"},
                "timing": 0.01,
            },
            "step9_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.Inactive=9",
                "captured": {"Inactive": "9"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d023, d023_results) is True

    d023_fail_results = {
        "steps": {
            **d023_results["steps"],
            "step9_24g_get": {
                "success": True,
                "output": "WiFi.AccessPoint.5.AssociatedDevice.1.Inactive=ERROR",
                "captured": {"Inactive": "ERROR"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d023, d023_fail_results) is False

    d028 = load_case(cases_dir / "D028_maxbandwidthsupported.yaml")
    d028_results = {
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
    assert plugin.evaluate(d028, d028_results) is True

    d028_fail_results = {
        "steps": {
            **d028_results["steps"],
            "step2_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MaxBandwidthSupported="80MHz"',
                "captured": {"MaxBandwidthSupported": "80MHz"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d028, d028_fail_results) is False


def test_pending_not_supported_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D029-mode-accesspoint-associateddevice",
        "wifi-llapi-D030-mugroupid",
    }.issubset(discoverable_ids)

    d029 = load_case(cases_dir / "D029_mode_accesspoint_associateddevice.yaml")
    d029_commands = "\n".join(str(step.get("command", "")) for step in d029["steps"])
    d029_links = {link["band"] for link in d029["topology"]["links"]}
    assert d029_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d029_commands
    assert "wl -i wl2 assoclist" in d029_commands
    assert any(
        criterion["field"] == "result_5g.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d029["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result_24g.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "doesn't exist in odl"
        for criterion in d029["pass_criteria"]
    )

    d030 = load_case(cases_dir / "D030_mugroupid.yaml")
    d030_commands = "\n".join(str(step.get("command", "")) for step in d030["steps"])
    d030_links = {link["band"] for link in d030["topology"]["links"]}
    assert d030["source"]["row"] == 30
    assert d030_links == {"5g", "2.4g"}
    assert "wl -i wl0 assoclist" in d030_commands
    assert "wl -i wl2 assoclist" in d030_commands
    assert any(
        criterion["field"] == "result_5g.MUGroupId"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d030["pass_criteria"]
    )
    assert _has_assoc_mac_regex(d030, "assoc_24g.AssocMac24g")
    assert case_band_results(d030, True) == _expected_case_band_results(d030, True)


def test_pending_not_supported_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d029 = load_case(cases_dir / "D029_mode_accesspoint_associateddevice.yaml")
    d029_results = {
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
    assert plugin.evaluate(d029, d029_results) is True

    d029_fail_results = {
        "steps": {
            **d029_results["steps"],
            "step5_24g": {
                "success": True,
                "output": '[\n  {\n    "error": 7,\n    "message": "unexpected error"\n  }\n]\n',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d029, d029_fail_results) is False

    d030 = load_case(cases_dir / "D030_mugroupid.yaml")
    d030_results = {
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
    assert plugin.evaluate(d030, d030_results) is True

    d030_fail_results = {
        "steps": {
            **d030_results["steps"],
            "step2_5g": {
                "success": True,
                "output": '[\n  {\n    "WiFi.AccessPoint.1.AssociatedDevice.1.MUGroupId": 1\n  }\n]\n',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d030, d030_fail_results) is False


def test_pending_mu_stub_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D031-mumimotxpktscount",
        "wifi-llapi-D032-mumimotxpktspercentage",
        "wifi-llapi-D033-muuserpositionid",
    }.issubset(discoverable_ids)

    mu_cases = {
        "D031_mumimotxpktscount.yaml": ("MUMimoTxPktsCount", "wifi-llapi-D031-mumimotxpktscount", 31),
        "D032_mumimotxpktspercentage.yaml": ("MUMimoTxPktsPercentage", "wifi-llapi-D032-mumimotxpktspercentage", 32),
        "D033_muuserpositionid.yaml": ("MUUserPositionId", "wifi-llapi-D033-muuserpositionid", 33),
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
        _mu_rr = {
            "D031_mumimotxpktscount.yaml": ("Fail", "Fail", "Fail"),
            "D032_mumimotxpktspercentage.yaml": ("Not Supported", "Not Supported", "Not Supported"),
            "D033_muuserpositionid.yaml": ("Not Supported", "Not Supported", "Not Supported"),
        }
        exp5, exp6, exp24 = _mu_rr[filename]
        assert _has_assoc_mac_regex(case_data, "assoc_5g.AssocMac5g")
        assert any(
            criterion["field"] == f"result_5g.{api_name}"
            and criterion["operator"] == "equals"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert _has_assoc_mac_regex(case_data, "assoc_24g.AssocMac24g")
        assert any(
            criterion["field"] == f"result_24g.{api_name}"
            and criterion["operator"] == "equals"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )


def test_pending_mu_stub_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    mu_cases = {
        "D031_mumimotxpktscount.yaml": "MUMimoTxPktsCount",
        "D032_mumimotxpktspercentage.yaml": "MUMimoTxPktsPercentage",
        "D033_muuserpositionid.yaml": "MUUserPositionId",
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
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D036-powersave",
        "wifi-llapi-D040-rxmulticastpacketcount",
    }.issubset(discoverable_ids)

    d036 = load_case(cases_dir / "D036_powersave.yaml")
    assert any(
        criterion["field"] == "result.PowerSave"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "0"
        for criterion in d036["pass_criteria"]
    )

    d040_raw = yaml.safe_load((cases_dir / "D040_rxmulticastpacketcount.yaml").read_text(encoding="utf-8"))
    d040 = load_case(cases_dir / "D040_rxmulticastpacketcount.yaml")
    d040_commands = "\n".join(str(step.get("command", "")) for step in d040["steps"])
    d040_links = {link["band"] for link in d040["topology"]["links"]}

    assert "aliases" not in d040_raw
    assert d040["id"] == "wifi-llapi-D040-rxmulticastpacketcount"
    assert d040["source"]["row"] == 40
    assert d040["llapi_support"] == "Support"
    assert d040["bands"] == ["5g"]
    assert d040_links == {"5g"}
    assert d040["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.RxMulticastPacketCount?"'
    assert [step["phase"] for step in d040["steps"]] == [
        "baseline",
        "baseline",
        "baseline",
        "baseline",
        "trigger",
        "verify",
        "verify",
    ]
    assert [step["capture"] for step in d040["steps"] if step.get("capture")] == [
        "assoc_entry",
        "sta_ip",
        "api_before_5g",
        "drv_before_5g",
        "trigger_probe",
        "api_after_5g",
        "drv_after_5g",
    ]
    assert "ifconfig wl0 192.168.1.3" in d040_commands
    assert "TriggerTxPackets=" in d040_commands
    assert "DriverAssocMac=" in d040_commands
    assert "DriverRxMulticastPacketCount=" in d040_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "regex"
        for criterion in d040["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sta_ip.StaIp"
        and criterion["operator"] == "regex"
        for criterion in d040["pass_criteria"]
    )
    assert any(
        criterion["field"] == "trigger_probe.TriggerTxPackets"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d040["pass_criteria"]
    )
    assert any(
        criterion["field"] == "drv_before_5g.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d040["pass_criteria"]
    )
    assert any(
        criterion["field"] == "drv_after_5g.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d040["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_nonzero"
        and criterion.get("delta")
        == {
            "baseline": "api_before_5g.RxMulticastPacketCount",
            "verify": "api_after_5g.RxMulticastPacketCount",
        }
        for criterion in d040["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_match"
        and criterion.get("delta")
        == {
            "baseline": "api_before_5g.RxMulticastPacketCount",
            "verify": "api_after_5g.RxMulticastPacketCount",
        }
        and criterion.get("reference_delta")
        == {
            "baseline": "drv_before_5g.DriverRxMulticastPacketCount",
            "verify": "drv_after_5g.DriverRxMulticastPacketCount",
        }
        and criterion.get("tolerance_pct") == 10
        for criterion in d040["pass_criteria"]
    )
    assert not any(
        criterion.get("field") == "result.RxMulticastPacketCount"
        and criterion.get("operator") == "equals"
        and str(criterion.get("value")) == "0"
        for criterion in d040["pass_criteria"]
    )


def test_pending_failure_shaped_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d036 = load_case(cases_dir / "D036_powersave.yaml")
    d036_results = {
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
    assert plugin.evaluate(d036, d036_results) is True

    d036_fail_results = {
        "steps": {
            **d036_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverPowerSaveFlags=WME",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d036, d036_fail_results) is False

    d040 = load_case(cases_dir / "D040_rxmulticastpacketcount.yaml")
    d040_results = {
        "steps": {
            "step1_resolve_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step2_prepare_probe_target": {
                "success": True,
                "output": "StaIp=192.168.1.3",
                "timing": 0.01,
            },
            "step3_api_baseline": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.RxMulticastPacketCount=10",
                "timing": 0.01,
            },
            "step4_drv_baseline": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverRxMulticastPacketCount=10",
                "timing": 0.01,
            },
            "step5_trigger": {
                "success": True,
                "output": "5 packets transmitted, 0 received, 100% packet loss, time 4103ms\nTriggerTxPackets=5",
                "timing": 0.01,
            },
            "step6_api_verify": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.RxMulticastPacketCount=15",
                "timing": 0.01,
            },
            "step7_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverRxMulticastPacketCount=15",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d040, d040_results) is True

    d040_zero_results = {
        "steps": {
            **d040_results["steps"],
            "step6_api_verify": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.RxMulticastPacketCount=10",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d040, d040_zero_results) is False

    d040_mismatch_results = {
        "steps": {
            **d040_results["steps"],
            "step7_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverRxMulticastPacketCount=30",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d040, d040_mismatch_results) is False

    d040_assoc_mismatch_results = {
        "steps": {
            **d040_results["steps"],
            "step7_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverRxMulticastPacketCount=15",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d040, d040_assoc_mismatch_results) is False


def test_pending_counter_pass_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D039-rxbytes",
        "wifi-llapi-D041-rxpacketcount",
        "wifi-llapi-D042-rxunicastpacketcount",
    }.issubset(discoverable_ids)

    pass_cases = {
        "D039_rxbytes.yaml": {
            "id": "wifi-llapi-D039-rxbytes",
            "row": 39,
            "api": "RxBytes",
            "driver_before": "drv_before_5g.DriverRxBytes",
            "driver_after": "drv_after_5g.DriverRxBytes",
            "driver_token": "DriverRxBytes=",
            "trigger_command": "ping -I wl0 -c 8 -s 1400 -W 1 {{dut_ip.DutIp}}",
        },
        "D041_rxpacketcount.yaml": {
            "id": "wifi-llapi-D041-rxpacketcount",
            "row": 41,
            "api": "RxPacketCount",
            "driver_before": "drv_before_5g.DriverRxPacketCount",
            "driver_after": "drv_after_5g.DriverRxPacketCount",
            "driver_token": "DriverRxPacketCount=",
            "trigger_command": "ping -I wl0 -c 8 -s 1400 -W 1 {{dut_ip.DutIp}}",
        },
        "D042_rxunicastpacketcount.yaml": {
            "id": "wifi-llapi-D042-rxunicastpacketcount",
            "row": 42,
            "api": "RxUnicastPacketCount",
            "driver_before": "drv_before_5g.DriverRxUnicastPacketCount",
            "driver_after": "drv_after_5g.DriverRxUnicastPacketCount",
            "driver_token": "DriverRxUnicastPacketCount=",
            "trigger_command": "ping -I wl0 -c 8 -s 1400 -W 1 {{dut_ip.DutIp}}",
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
        assert case_data["bands"] == ["5g"]
        assert links == {"5g"}
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}?"'
        assert [step["phase"] for step in case_data["steps"]] == [
            "baseline",
            "baseline",
            "baseline",
            "baseline",
            "baseline",
            "trigger",
            "verify",
            "verify",
        ]
        assert "MACAddress?" in commands
        assert "ifconfig wl0 192.168.1.3" in commands
        assert 'print "StaIp="' in commands
        assert "DutIp=" in commands
        assert meta["trigger_command"] in commands
        assert "DriverAssocMac=" in commands
        assert meta["driver_token"] in commands
        assert [step["capture"] for step in case_data["steps"] if step.get("capture")] == [
            "assoc_entry",
            "sta_ip",
            "dut_ip",
            "api_before_5g",
            "drv_before_5g",
            "trigger_probe",
            "api_after_5g",
            "drv_after_5g",
        ]
        assert case_data["steps"][1]["id"] == "step2_prepare_probe_target"
        assert case_data["steps"][1]["target"] == "STA"
        assert case_data["steps"][1]["command"] == [
            "ifconfig wl0 192.168.1.3 netmask 255.255.255.0 up",
            "ip -4 addr show dev wl0 | awk '/inet / {sub(/\\/24$/, \"\", $2); print \"StaIp=\" $2; exit}'",
        ]
        assert case_data["steps"][2]["id"] == "step3_resolve_probe_target"
        assert case_data["steps"][2]["depends_on"] == "step2_prepare_probe_target"
        assert case_data["steps"][5]["id"] == "step6_trigger"
        assert case_data["steps"][5]["depends_on"] == "step5_drv_baseline"
        assert any(
            criterion["field"] == "sta_ip.StaIp" and criterion["operator"] == "regex"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "dut_ip.DutIp" and criterion["operator"] == "regex"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "trigger_probe.TriggerTxPackets"
            and criterion["operator"] == ">"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "drv_before_5g.DriverAssocMac"
            and criterion["operator"] == "equals"
            and criterion["reference"] == "assoc_entry.MACAddress"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "drv_after_5g.DriverAssocMac"
            and criterion["operator"] == "equals"
            and criterion["reference"] == "assoc_entry.MACAddress"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion.get("operator") == "delta_nonzero"
            and criterion.get("delta")
            == {
                "baseline": f'api_before_5g.{meta["api"]}',
                "verify": f'api_after_5g.{meta["api"]}',
            }
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion.get("operator") == "delta_match"
            and criterion.get("delta")
            == {
                "baseline": f'api_before_5g.{meta["api"]}',
                "verify": f'api_after_5g.{meta["api"]}',
            }
            and criterion.get("reference_delta")
            == {
                "baseline": meta["driver_before"],
                "verify": meta["driver_after"],
            }
            and criterion.get("tolerance_pct") == 10
            for criterion in case_data["pass_criteria"]
        )
        assert not any(
            criterion.get("field") == f'result.{meta["api"]}'
            and criterion.get("operator") == "equals"
            and str(criterion.get("value")) == "0"
            for criterion in case_data["pass_criteria"]
        )


def test_pending_counter_pass_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    pass_cases = {
        "D039_rxbytes.yaml": {
            "api": "RxBytes",
            "driver_field": "DriverRxBytes",
        },
        "D041_rxpacketcount.yaml": {
            "api": "RxPacketCount",
            "driver_field": "DriverRxPacketCount",
        },
        "D042_rxunicastpacketcount.yaml": {
            "api": "RxUnicastPacketCount",
            "driver_field": "DriverRxUnicastPacketCount",
        },
    }

    for filename, meta in pass_cases.items():
        case_data = load_case(cases_dir / filename)
        pass_results = {
            "steps": {
                "step1_resolve_assoc": {
                    "success": True,
                    "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                    "timing": 0.01,
                },
                "step2_prepare_probe_target": {
                    "success": True,
                    "output": "StaIp=192.168.1.3",
                    "timing": 0.01,
                },
                "step3_resolve_probe_target": {
                    "success": True,
                    "output": "DutIp=192.168.1.1",
                    "timing": 0.01,
                },
                "step4_api_baseline": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=10',
                    "timing": 0.01,
                },
                "step5_drv_baseline": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_field"]}=100',
                    "timing": 0.01,
                },
                "step6_trigger": {
                    "success": True,
                    "output": '8 packets transmitted, 8 received, 0% packet loss\nTriggerTxPackets=8',
                    "timing": 0.01,
                },
                "step7_api_verify": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=16',
                    "timing": 0.01,
                },
                "step8_drv_verify": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_field"]}=106',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, pass_results) is True

        zero_results = {
            "steps": {
                **pass_results["steps"],
                "step7_api_verify": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=10',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, zero_results) is False

        mismatch_results = {
            "steps": {
                **pass_results["steps"],
                "step8_drv_verify": {
                    "success": True,
                    "output": f'DriverAssocMac=2C:59:17:00:04:85\n{meta["driver_field"]}=130',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, mismatch_results) is False

        assoc_mismatch_results = {
            "steps": {
                **pass_results["steps"],
                "step8_drv_verify": {
                    "success": True,
                    "output": f'DriverAssocMac=AA:AA:AA:AA:AA:AA\n{meta["driver_field"]}=106',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, assoc_mismatch_results) is False

        missing_sta_ip_results = {
            "steps": {
                **pass_results["steps"],
                "step2_prepare_probe_target": {
                    "success": True,
                    "output": "StaIp=",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, missing_sta_ip_results) is False


def test_d059_uplinkbandwidth_uses_positive_same_sta_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    raw_case = yaml.safe_load((cases_dir / "D059_uplinkbandwidth.yaml").read_text(encoding="utf-8"))
    case_data = load_case(cases_dir / "D059_uplinkbandwidth.yaml")
    commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
    links = {link["band"] for link in case_data["topology"]["links"]}

    assert "wifi-llapi-D059-uplinkbandwidth" in {case["id"] for case in plugin.discover_cases()}
    assert "aliases" not in raw_case
    assert case_data["id"] == "wifi-llapi-D059-uplinkbandwidth"
    assert case_data["source"]["row"] == 59
    assert case_data["bands"] == ["5g"]
    assert links == {"5g"}
    assert case_data["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.UplinkBandwidth?"'
    assert len(case_data["steps"]) == 4
    assert case_data["topology"]["devices"]["STA"]["config"][0]["ssid"] == "testpilot5G"
    assert case_data["topology"]["devices"]["STA"]["config"][0]["key"] == "00000000"
    assert "MACAddress?" in commands
    assert "ping -I wl0 -c 8 -W 1 192.168.1.1" in commands
    assert "AssocMacAfterTrigger=" in commands
    assert "DriverAssocMac=" in commands
    assert "DriverUplinkBandwidth=" in commands
    assert "sed -n '/rx nrate/,+1p'" in commands
    assert "sed -n '2s/.*bw\\([0-9][0-9]*\\).*/DriverUplinkBandwidth=\\1/p'" in commands
    assert any(
        criterion["field"] == "result.AssocMacAfterTrigger"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkBandwidth"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9]+$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkBandwidth"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "result.AssocMacAfterTrigger"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.DriverUplinkBandwidth"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9]+$"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.DriverUplinkBandwidth"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in case_data["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UplinkBandwidth"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "result.DriverUplinkBandwidth"
        for criterion in case_data["pass_criteria"]
    )


def test_d059_uplinkbandwidth_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D059_uplinkbandwidth.yaml")

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
                "output": "UplinkBandwidth=20\nAssocMacAfterTrigger=2C:59:17:00:04:85\nDriverAssocMac=2C:59:17:00:04:85\nrx nrate\nhe mcs 10 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto\nDriverUplinkBandwidth=20",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, pass_results) is True

    driver_fail_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkBandwidth=20\nAssocMacAfterTrigger=2C:59:17:00:04:85\nDriverAssocMac=2C:59:17:00:04:85\nrx nrate\nhe mcs 10 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto\nDriverUplinkBandwidth=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, driver_fail_results) is False

    zero_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkBandwidth=0\nAssocMacAfterTrigger=2C:59:17:00:04:85\nDriverAssocMac=2C:59:17:00:04:85\nrx nrate\nhe mcs 10 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto\nDriverUplinkBandwidth=20",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, zero_results) is False

    mismatch_results = {
        "steps": {
            **pass_results["steps"],
            "step4": {
                "success": True,
                "output": "UplinkBandwidth=20\nAssocMacAfterTrigger=AA:AA:AA:AA:AA:AA\nDriverAssocMac=AA:AA:AA:AA:AA:AA\nrx nrate\nhe mcs 10 Nss 4 Tx Exp 0 bw20 ldpc 2xLTF GI 1.6us auto\nDriverUplinkBandwidth=20",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, mismatch_results) is False


def test_d060_uplinkmcs_uses_zero_valid_same_sta_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    raw_case = yaml.safe_load((cases_dir / "D060_uplinkmcs.yaml").read_text(encoding="utf-8"))
    case_data = load_case(cases_dir / "D060_uplinkmcs.yaml")
    commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
    links = {link["band"] for link in case_data["topology"]["links"]}

    assert "wifi-llapi-D060-uplinkmcs" in {case["id"] for case in plugin.discover_cases()}
    assert "aliases" not in raw_case
    assert case_data["id"] == "wifi-llapi-D060-uplinkmcs"
    assert case_data["source"]["row"] == 60
    assert case_data["bands"] == ["5g"]
    assert links == {"5g"}
    assert case_data["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.UplinkMCS?"'
    assert len(case_data["steps"]) == 4
    assert "MACAddress?" in commands
    assert "ping -I wl0 -c 8 -W 1 192.168.1.1" in commands
    assert "AssocMacAfterTrigger=" in commands
    assert "DriverAssocMac=" in commands
    assert "DriverUplinkMCS=" in commands
    assert "sed -n 's/.*MACAddress=\"\\([^\"]*\\)\".*/\\1/p' | head -n 1" in commands
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
    


def test_d060_uplinkmcs_evaluate_accepts_zero_when_driver_matches():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D060_uplinkmcs.yaml")

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


def test_d061_uplinkshortguard_uses_same_sta_gi_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    raw_case = yaml.safe_load((cases_dir / "D061_uplinkshortguard.yaml").read_text(encoding="utf-8"))
    case_data = load_case(cases_dir / "D061_uplinkshortguard.yaml")
    commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
    links = {link["band"] for link in case_data["topology"]["links"]}

    assert "wifi-llapi-D061-uplinkshortguard" in {case["id"] for case in plugin.discover_cases()}
    assert "aliases" not in raw_case
    assert case_data["id"] == "wifi-llapi-D061-uplinkshortguard"
    assert case_data["source"]["row"] == 61
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
    


def test_d061_uplinkshortguard_evaluate_uses_driver_gi_mapping():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D061_uplinkshortguard.yaml")

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


def test_pending_d044_d049_d058_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D044-signalnoiseratio",
        "wifi-llapi-D049-supportedmcs",
        "wifi-llapi-D058-uniibandscapabilities",
    }.issubset(discoverable_ids)

    d044_raw = yaml.safe_load((cases_dir / "D044_signalnoiseratio.yaml").read_text(encoding="utf-8"))
    d044 = load_case(cases_dir / "D044_signalnoiseratio.yaml")
    d044_commands = "\n".join(str(step.get("command", "")) for step in d044["steps"])
    assert "aliases" not in d044_raw
    assert d044["source"]["row"] == 44
    assert d044["bands"] == ["5g"]
    assert "DriverSignal=" in d044_commands
    assert "DriverNoise=" in d044_commands
    assert "DriverSignalNoiseRatio=" in d044_commands
    assert any(
        criterion["field"] == "result.SignalNoiseRatio"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[0-9]+$"
        for criterion in d044["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalNoiseRatio"
        and criterion["operator"] == ">="
        and criterion["reference"] == "driver_snr.DriverSignalNoiseRatioMin"
        for criterion in d044["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalNoiseRatio"
        and criterion["operator"] == "<="
        and criterion["reference"] == "driver_snr.DriverSignalNoiseRatioMax"
        for criterion in d044["pass_criteria"]
    )

    d049_raw = yaml.safe_load((cases_dir / "D049_supportedmcs.yaml").read_text(encoding="utf-8"))
    d049 = load_case(cases_dir / "D049_supportedmcs.yaml")
    d049_commands = "\n".join(str(step.get("command", "")) for step in d049["steps"])
    assert "aliases" not in d049_raw
    assert d049["source"]["row"] == 49
    assert d049["bands"] == ["5g"]
    assert "DriverHeCapsPresent=1" in d049_commands
    assert "DriverMCSSetPresent=1" in d049_commands
    assert "DriverHeSetPresent=1" in d049_commands
    assert any(
        criterion["field"] == "result.SupportedMCS"
        and criterion["operator"] == "empty"
        for criterion in d049["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverMCSSetPresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d049["pass_criteria"]
    )

    d058_raw = yaml.safe_load(
        (cases_dir / "D058_uniibandscapabilities.yaml").read_text(encoding="utf-8")
    )
    d058 = load_case(cases_dir / "D058_uniibandscapabilities.yaml")
    d058_commands = "\n".join(str(step.get("command", "")) for step in d058["steps"])
    assert "aliases" not in d058_raw
    assert d058["source"]["row"] == 58
    assert d058["bands"] == ["5g"]
    assert "DriverUNIIBandsCapabilities=" in d058_commands
    assert "iw dev wl0 info" in d058_commands
    assert "tr '[:lower:]' '[:upper:]'" in d058_commands
    assert any(
        criterion["field"] == "driver_capability.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d058["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverUNIIBandsCapabilities"
        and criterion["operator"] == "equals"
        and criterion["value"] == "U-NII-1,U-NII-2A,U-NII-2C,U-NII-3"
        for criterion in d058["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.UNIIBandsCapabilities"
        and criterion["operator"] == "contains"
        and criterion["reference"] == "driver_capability.DriverUNIIBandsCapabilities"
        for criterion in d058["pass_criteria"]
    )


def test_pending_d044_d049_d058_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d044 = load_case(cases_dir / "D044_signalnoiseratio.yaml")
    d044_results = {
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
    assert plugin.evaluate(d044, d044_results) is True

    d044_fail_results = {
        "steps": {
            **d044_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignal=-32\nDriverNoise=-99\nDriverSignalNoiseRatio=67\nDriverSignalNoiseRatioMin=65\nDriverSignalNoiseRatioMax=69",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d044, d044_fail_results) is False

    d049 = load_case(cases_dir / "D049_supportedmcs.yaml")
    d049_results = {
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
    assert plugin.evaluate(d049, d049_results) is True

    d049_fail_results = {
        "steps": {
            **d049_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d049, d049_fail_results) is False

    d058 = load_case(cases_dir / "D058_uniibandscapabilities.yaml")
    d058_results = {
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
    assert plugin.evaluate(d058, d058_results) is True

    d058_fail_results = {
        "steps": {
            **d058_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverUNIIBandsCapabilities=U-NII-1,U-NII-2A,U-NII-2C",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d058, d058_fail_results) is False


def test_pending_security_and_signal_associateddevice_cases_use_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D043-securitymodeenabled",
        "wifi-llapi-D045-signalstrength-accesspoint-associateddevice",
    }.issubset(discoverable_ids)

    d043_raw = yaml.safe_load(
        (cases_dir / "D043_securitymodeenabled.yaml").read_text(encoding="utf-8")
    )
    d043 = load_case(cases_dir / "D043_securitymodeenabled.yaml")
    d043_commands = "\n".join(str(step.get("command", "")) for step in d043["steps"])
    d043_links = {link["band"] for link in d043["topology"]["links"]}

    assert "aliases" not in d043_raw
    assert d043["id"] == "wifi-llapi-D043-securitymodeenabled"
    assert d043["source"]["row"] == 43
    assert d043["bands"] == ["5g"]
    assert d043_links == {"5g"}
    assert (
        d043["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SecurityModeEnabled?"'
    )
    assert "MACAddress?" in d043_commands
    assert "DriverAssocMac=" in d043_commands
    assert "DriverSecurityModeEnabled=" in d043_commands
    assert any(
        criterion["field"] == "driver_security.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d043["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_security.DriverSecurityModeEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "WPA3-Personal"
        for criterion in d043["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SecurityModeEnabled"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_security.DriverSecurityModeEnabled"
        for criterion in d043["pass_criteria"]
    )

    d045_raw = yaml.safe_load(
        (cases_dir / "D045_signalstrength_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d045 = load_case(cases_dir / "D045_signalstrength_accesspoint_associateddevice.yaml")
    d045_commands = "\n".join(str(step.get("command", "")) for step in d045["steps"])
    d045_links = {link["band"] for link in d045["topology"]["links"]}

    assert "aliases" not in d045_raw
    assert d045["id"] == "wifi-llapi-D045-signalstrength-accesspoint-associateddevice"
    assert d045["source"]["row"] == 45
    assert d045["bands"] == ["5g"]
    assert d045_links == {"5g"}
    assert (
        d045["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength?"'
    )
    assert "MACAddress?" in d045_commands
    assert "DriverAssocMac=" in d045_commands
    assert "DriverSignalStrength=" in d045_commands
    assert "DriverSignalStrengthMin=" in d045_commands
    assert "DriverSignalStrengthMax=" in d045_commands
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-[0-9]+$"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverSignalStrength"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^-[0-9]+$"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverSignalStrength"
        and criterion["operator"] == "<"
        and str(criterion["value"]) == "0"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == ">="
        and criterion["reference"] == "driver_signal.DriverSignalStrengthMin"
        for criterion in d045["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrength"
        and criterion["operator"] == "<="
        and criterion["reference"] == "driver_signal.DriverSignalStrengthMax"
        for criterion in d045["pass_criteria"]
    )


def test_pending_security_and_signal_associateddevice_cases_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d043 = load_case(cases_dir / "D043_securitymodeenabled.yaml")
    d043_results = {
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
    assert plugin.evaluate(d043, d043_results) is True

    d043_fail_results = {
        "steps": {
            **d043_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSecurityModeEnabled=WPA2-Personal",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d043, d043_fail_results) is False

    d043_mismatch_results = {
        "steps": {
            **d043_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverSecurityModeEnabled=WPA3-Personal",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d043, d043_mismatch_results) is False

    d045 = load_case(cases_dir / "D045_signalstrength_accesspoint_associateddevice.yaml")
    d045_results = {
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
    assert plugin.evaluate(d045, d045_results) is True

    d045_fail_results = {
        "steps": {
            **d045_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrength=-32\nDriverSignalStrengthMin=-34\nDriverSignalStrengthMax=-30",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_fail_results) is False

    d045_zero_results = {
        "steps": {
            **d045_results["steps"],
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrength=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_zero_results) is False

    d045_mismatch_results = {
        "steps": {
            **d045_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverSignalStrength=-36\nDriverSignalStrengthMin=-38\nDriverSignalStrengthMax=-34",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_mismatch_results) is False

    d045_missing_driver_value_results = {
        "steps": {
            **d045_results["steps"],
            "step3": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrengthMin=-38\nDriverSignalStrengthMax=-34",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d045, d045_missing_driver_value_results) is False


def test_d046_signalstrengthbychain_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D046-signalstrengthbychain" in discoverable_ids

    d046_raw = yaml.safe_load(
        (cases_dir / "D046_signalstrengthbychain.yaml").read_text(encoding="utf-8")
    )
    d046 = load_case(cases_dir / "D046_signalstrengthbychain.yaml")
    d046_commands = "\n".join(str(step.get("command", "")) for step in d046["steps"])
    d046_links = {link["band"] for link in d046["topology"]["links"]}

    assert "aliases" not in d046_raw
    assert d046["id"] == "wifi-llapi-D046-signalstrengthbychain"
    assert d046["source"]["row"] == 46
    assert d046["bands"] == ["5g"]
    assert d046_links == {"5g"}
    assert (
        d046["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain?"'
    )
    assert "cat /sys/class/net/wl0/address" in d046_commands
    assert "MACAddress?" in d046_commands
    assert "DriverAssocMac=" in d046_commands
    assert "DriverSignalStrengthByChain=" in d046_commands
    assert "per antenna average rssi of rx data frames" in d046_commands
    assert 'awk \'BEGIN{first=1}' in d046_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0$"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_signal.DriverSignalStrengthByChain"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0,-[0-9]+\.0$"
        for criterion in d046["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.SignalStrengthByChain"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "driver_signal.DriverSignalStrengthByChain"
        for criterion in d046["pass_criteria"]
    )


def test_d046_signalstrengthbychain_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d046 = load_case(cases_dir / "D046_signalstrengthbychain.yaml")

    d046_results = {
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
    assert plugin.evaluate(d046, d046_results) is True

    d046_fail_results = {
        "steps": {
            **d046_results["steps"],
            "step4": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverSignalStrengthByChain=-28.0,-33.0,-35.0,-32.0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d046, d046_fail_results) is False

    d046_scalar_results = {
        "steps": {
            **d046_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.SignalStrengthByChain="-33.0"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d046, d046_scalar_results) is False

    d046_mismatch_results = {
        "steps": {
            **d046_results["steps"],
            "step4": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverSignalStrengthByChain=-28.0,-33.0,-36.0,-32.0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d046, d046_mismatch_results) is False

    d046_wrong_sta_results = {
        "steps": {
            **d046_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d046, d046_wrong_sta_results) is False


def test_d047_supportedhe160mcs_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D047-supportedhe160mcs" in discoverable_ids

    d047_raw = yaml.safe_load(
        (cases_dir / "D047_supportedhe160mcs.yaml").read_text(encoding="utf-8")
    )
    d047 = load_case(cases_dir / "D047_supportedhe160mcs.yaml")
    d047_commands = "\n".join(str(step.get("command", "")) for step in d047["steps"])
    d047_links = {link["band"] for link in d047["topology"]["links"]}

    assert "aliases" not in d047_raw
    assert "sta_env_setup" not in d047_raw
    assert d047["id"] == "wifi-llapi-D047-supportedhe160mcs"
    assert d047["source"]["row"] == 47
    assert d047["llapi_support"] == "Not Supported"
    assert d047["bands"] == ["5g"]
    assert d047_links == {"5g"}
    assert "sta_env_setup" not in d047
    assert (
        d047["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHe160MCS?"'
    )
    assert "cat /sys/class/net/wl0/address" in d047_commands
    assert "MACAddress?" in d047_commands
    assert 'SupportedHe160MCS?" 2>&1' in d047_commands
    assert "error=" in d047_commands
    assert "message=" in d047_commands
    assert "DriverRxSupportedHe160MCS=" in d047_commands
    assert "DriverTxSupportedHe160MCS=" in d047_commands
    assert "DriverHeCapsPresent=1" in d047_commands
    assert "DriverMCSSetPresent=1" in d047_commands
    assert "DriverHeSetPresent=1" in d047_commands
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "parameter not found"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.SiblingAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverRxSupportedHe160MCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d047["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverHeSetPresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d047["pass_criteria"]
    )


def test_d047_supportedhe160mcs_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d047 = load_case(cases_dir / "D047_supportedhe160mcs.yaml")

    d047_results = {
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
    assert plugin.evaluate(d047, d047_results) is True

    d047_wrong_error_results = {
        "steps": {
            **d047_results["steps"],
            "step3": {
                "success": True,
                "output": "error=7\nmessage=unexpected error",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_wrong_error_results) is False

    d047_missing_sibling_results = {
        "steps": {
            **d047_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverTxSupportedHe160MCS=11,11,11,11",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_missing_sibling_results) is False

    d047_wrong_sta_results = {
        "steps": {
            **d047_results["steps"],
            "step1": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d047, d047_wrong_sta_results) is False


def test_d048_supportedhemcs_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D048-supportedhemcs" in discoverable_ids

    d048_raw = yaml.safe_load(
        (cases_dir / "D048_supportedhemcs.yaml").read_text(encoding="utf-8")
    )
    d048 = load_case(cases_dir / "D048_supportedhemcs.yaml")
    d048_commands = "\n".join(str(step.get("command", "")) for step in d048["steps"])
    d048_links = {link["band"] for link in d048["topology"]["links"]}

    assert "aliases" not in d048_raw
    assert d048["id"] == "wifi-llapi-D048-supportedhemcs"
    assert d048["source"]["row"] == 48
    assert d048["llapi_support"] == "Not Supported"
    assert d048["bands"] == ["5g"]
    assert d048_links == {"5g"}
    assert (
        d048["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedHeMCS?"'
    )
    assert "cat /sys/class/net/wl0/address" in d048_commands
    assert "MACAddress?" in d048_commands
    assert 'SupportedHeMCS?" 2>&1' in d048_commands
    assert "error=" in d048_commands
    assert "message=" in d048_commands
    assert "DriverRxSupportedHeMCS=" in d048_commands
    assert "DriverTxSupportedHeMCS=" in d048_commands
    assert "DriverHeCapsPresent=1" in d048_commands
    assert "DriverMCSSetPresent=1" in d048_commands
    assert "DriverHeSetPresent=1" in d048_commands
    assert "DriverHeMcsLinePresent=1" in d048_commands
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
        criterion["field"] == "result.error"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "4"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.message"
        and criterion["operator"] == "contains"
        and criterion["value"] == "parameter not found"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.SiblingAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverRxSupportedHeMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverTxSupportedHeMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d048["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capability.DriverHeMcsLinePresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d048["pass_criteria"]
    )
    


def test_d048_supportedhemcs_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d048 = load_case(cases_dir / "D048_supportedhemcs.yaml")

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
    assert plugin.evaluate(d048, d048_results) is True

    d048_wrong_error_results = {
        "steps": {
            **d048_results["steps"],
            "step3": {
                "success": True,
                "output": "error=7\nmessage=unexpected error",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_wrong_error_results) is False

    d048_missing_sibling_results = {
        "steps": {
            **d048_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverTxSupportedHeMCS=11,11,11,11",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_missing_sibling_results) is False

    d048_missing_tx_sibling_results = {
        "steps": {
            **d048_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedHeMCS=11,11,11,11",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_missing_tx_sibling_results) is False

    d048_missing_driver_line_results = {
        "steps": {
            **d048_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_missing_driver_line_results) is False

    d048_wrong_driver_assoc_results = {
        "steps": {
            **d048_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverHeCapsPresent=1\nDriverMCSSetPresent=1\nDriverHeSetPresent=1\nDriverHeMcsLinePresent=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d048, d048_wrong_driver_assoc_results) is False

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


def test_d050_supportedvhtmcs_uses_supported_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D050-supportedvhtmcs" in discoverable_ids

    d050_raw = yaml.safe_load(
        (cases_dir / "D050_supportedvhtmcs.yaml").read_text(encoding="utf-8")
    )
    d050 = load_case(cases_dir / "D050_supportedvhtmcs.yaml")
    d050_commands = "\n".join(str(step.get("command", "")) for step in d050["steps"])
    d050_links = {link["band"] for link in d050["topology"]["links"]}

    assert "aliases" not in d050_raw
    assert "sta_env_setup" not in d050_raw
    assert d050["id"] == "wifi-llapi-D050-supportedvhtmcs"
    assert d050["source"]["row"] == 50
    assert d050["llapi_support"] == "Not Supported"
    assert d050["bands"] == ["5g"]
    assert d050_links == {"5g"}
    assert "sta_env_setup" not in d050
    assert (
        d050["hlapi_command"]
        == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.SupportedVhtMCS?"'
    )
    assert "cat /sys/class/net/wl0/address" in d050_commands
    assert "MACAddress?" in d050_commands
    assert 'SupportedVhtMCS?" 2>&1' in d050_commands
    assert "error=" in d050_commands
    assert "message=" in d050_commands
    assert "DriverRxSupportedVhtMCS=" in d050_commands
    assert "DriverTxSupportedVhtMCS=" in d050_commands
    assert "DriverVhtCapsPresent=1" in d050_commands
    assert "DriverMCSSetPresent=1" in d050_commands
    assert "DriverVhtSetPresent=1" in d050_commands
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
        criterion["field"] == "sibling_support.DriverRxSupportedVhtMCS"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^[0-9]+(,[0-9]+)*$"
        for criterion in d050["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sibling_support.DriverTxSupportedVhtMCS"
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
        criterion["field"] == "driver_capability.DriverVhtSetPresent"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d050["pass_criteria"]
    )


def test_d050_supportedvhtmcs_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d050 = load_case(cases_dir / "D050_supportedvhtmcs.yaml")

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

    d050_missing_rx_sibling_results = {
        "steps": {
            **d050_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverTxSupportedVhtMCS=9,9,9,9",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_missing_rx_sibling_results) is False

    d050_missing_tx_sibling_results = {
        "steps": {
            **d050_results["steps"],
            "step4": {
                "success": True,
                "output": "SiblingAssocMac=2C:59:17:00:04:85\nDriverRxSupportedVhtMCS=9,9,9,9",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d050, d050_missing_tx_sibling_results) is False

    d050_wrong_driver_assoc_results = {
        "steps": {
            **d050_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverVhtCapsPresent=1\nDriverMCSSetPresent=1\nDriverVhtSetPresent=1",
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


def test_d054_txerrors_uses_manual_delta_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D054-txerrors" in discoverable_ids

    d054_raw = yaml.safe_load((cases_dir / "D054_txerrors.yaml").read_text(encoding="utf-8"))
    d054 = load_case(cases_dir / "D054_txerrors.yaml")
    d054_commands = "\n".join(str(step.get("command", "")) for step in d054["steps"])
    d054_links = {link["band"] for link in d054["topology"]["links"]}

    assert "aliases" not in d054_raw
    assert d054["id"] == "wifi-llapi-D054-txerrors"
    assert d054["source"]["row"] == 54
    assert d054["llapi_support"] == "Support"
    assert d054["bands"] == ["5g"]
    assert d054_links == {"5g"}
    assert d054["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors?"'
    assert "cat /sys/class/net/wl0/address" in d054_commands
    assert "MACAddress?" in d054_commands
    assert 'TxErrors?"' in d054_commands
    assert "manual" in d054["test_procedure"].lower()
    assert "external" in d054["test_procedure"].lower()
    assert "DriverTxErrors=" in d054_commands
    assert [step["phase"] for step in d054["steps"]] == [
        "baseline",
        "baseline",
        "baseline",
        "baseline",
        "trigger",
        "verify",
        "verify",
    ]
    assert d054["steps"][4]["action"] == "wait"
    assert d054["steps"][4]["duration"] == 30
    assert any(
        criterion["field"] == "sta_identity.StaMac"
        and criterion["operator"] == "regex"
        and criterion["value"] == r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
        for criterion in d054["pass_criteria"]
    )
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "sta_identity.StaMac"
        for criterion in d054["pass_criteria"]
    )
    assert any(
        criterion["field"] == "drv_before_5g.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d054["pass_criteria"]
    )
    assert any(
        criterion["field"] == "drv_after_5g.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "assoc_entry.MACAddress"
        for criterion in d054["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_nonzero"
        and criterion.get("delta")
        == {
            "baseline": "api_before_5g.TxErrors",
            "verify": "api_after_5g.TxErrors",
        }
        for criterion in d054["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_match"
        and criterion.get("reference_delta")
        == {
            "baseline": "drv_before_5g.DriverTxErrors",
            "verify": "drv_after_5g.DriverTxErrors",
        }
        for criterion in d054["pass_criteria"]
    )


def test_d054_txerrors_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d054 = load_case(cases_dir / "D054_txerrors.yaml")

    d054_results = {
        "steps": {
            "step1_resolve_sta": {
                "success": True,
                "output": "StaMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_resolve_assoc": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
                "timing": 0.01,
            },
            "step3_api_baseline": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors=2",
                "timing": 0.01,
            },
            "step4_drv_baseline": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverTxErrors=20",
                "timing": 0.01,
            },
            "step5_trigger_window": {
                "success": True,
                "output": "ManualTriggerWindow=30",
                "timing": 30.0,
            },
            "step6_api_verify": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors=8",
                "timing": 0.01,
            },
            "step7_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverTxErrors=26",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d054, d054_results) is True

    d054_zero_delta_results = {
        "steps": {
            **d054_results["steps"],
            "step6_api_verify": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors=2",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d054, d054_zero_delta_results) is False

    d054_wrong_driver_delta_results = {
        "steps": {
            **d054_results["steps"],
            "step7_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=2C:59:17:00:04:85\nDriverTxErrors=40",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d054, d054_wrong_driver_delta_results) is False

    d054_wrong_driver_assoc_results = {
        "steps": {
            **d054_results["steps"],
            "step7_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=AA:AA:AA:AA:AA:AA\nDriverTxErrors=26",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d054, d054_wrong_driver_assoc_results) is False

    d054_wrong_sta_results = {
        "steps": {
            **d054_results["steps"],
            "step1_resolve_sta": {
                "success": True,
                "output": "StaMac=AA:AA:AA:AA:AA:AA",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d054, d054_wrong_sta_results) is False


def test_d055_txmulticastpacketcount_uses_same_sta_delivery_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D055-txmulticastpacketcount" in discoverable_ids

    d055_raw = yaml.safe_load((cases_dir / "D055_txmulticastpacketcount.yaml").read_text(encoding="utf-8"))
    d055 = load_case(cases_dir / "D055_txmulticastpacketcount.yaml")
    d055_commands = "\n".join(str(step.get("command", "")) for step in d055["steps"])
    d055_links = {link["band"] for link in d055["topology"]["links"]}

    assert "aliases" not in d055_raw
    assert d055["id"] == "wifi-llapi-D055-txmulticastpacketcount"
    assert d055["source"]["row"] == 55
    assert d055["llapi_support"] == "Support"
    assert d055["bands"] == ["5g"]
    assert d055_links == {"5g"}
    assert d055["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount?"'
    assert [step["phase"] for step in d055["steps"]] == [
        "baseline",
        "baseline",
        "baseline",
        "baseline",
        "trigger",
        "verify",
        "verify",
        "verify",
    ]
    assert "StaRxPacketsBefore=" in d055_commands
    assert "StaRxBytesBefore=" in d055_commands
    assert "ProbeTxPackets=" in d055_commands
    assert "StaRxPacketsAfter=" in d055_commands
    assert "StaRxBytesAfter=" in d055_commands
    assert "DriverTxMulticastPacketCount=" in d055_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion["field"] == "probe.ProbeTxPackets"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sta_after.StaRxPacketsAfter"
        and criterion["operator"] == ">"
        and criterion.get("reference") == "sta_identity.StaRxPacketsBefore"
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion["field"] == "sta_after.StaRxBytesAfter"
        and criterion["operator"] == ">"
        and criterion.get("reference") == "sta_identity.StaRxBytesBefore"
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion["field"] == "drv_before_5g.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_entry.MACAddress"
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion["field"] == "drv_after_5g.DriverAssocMac"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_entry.MACAddress"
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_nonzero"
        and criterion.get("delta")
        == {
            "baseline": "api_before_5g.TxMulticastPacketCount",
            "verify": "api_after_5g.TxMulticastPacketCount",
        }
        for criterion in d055["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_match"
        and criterion.get("reference_delta")
        == {
            "baseline": "drv_before_5g.DriverTxMulticastPacketCount",
            "verify": "drv_after_5g.DriverTxMulticastPacketCount",
        }
        for criterion in d055["pass_criteria"]
    )
    assert not any(
        criterion.get("field") == "result.TxMulticastPacketCount"
        and criterion.get("operator") == "equals"
        and str(criterion.get("value")) == "0"
        for criterion in d055["pass_criteria"]
    )


def test_d055_txmulticastpacketcount_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d055 = load_case(cases_dir / "D055_txmulticastpacketcount.yaml")

    d055_results = {
        "steps": {
            "step1_sta_identity": {
                "success": True,
                "output": "StaMac=2c:59:17:00:04:85\nStaRxPacketsBefore=136067\nStaRxBytesBefore=15249537",
                "timing": 0.01,
            },
            "step2_assoc_entry": {
                "success": True,
                "output": "MACAddress=2c:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3_api_baseline": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount=10",
                "timing": 0.01,
            },
            "step4_drv_baseline": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverTxMulticastPacketCount=10",
                "timing": 0.01,
            },
            "step5_trigger": {
                "success": True,
                "output": "10 packets transmitted, 0 received, 100% packet loss, time 9034ms\nProbeTxPackets=10",
                "timing": 0.01,
            },
            "step6_sta_after": {
                "success": True,
                "output": "StaRxPacketsAfter=136077\nStaRxBytesAfter=15250517",
                "timing": 0.01,
            },
            "step7_api_verify": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount=14",
                "timing": 0.01,
            },
            "step8_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverTxMulticastPacketCount=14",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d055, d055_results) is True

    d055_no_delivery_results = {
        "steps": {
            **d055_results["steps"],
            "step6_sta_after": {
                "success": True,
                "output": "StaRxPacketsAfter=136067\nStaRxBytesAfter=15249537",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d055, d055_no_delivery_results) is False

    d055_zero_results = {
        "steps": {
            **d055_results["steps"],
            "step7_api_verify": {
                "success": True,
                "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxMulticastPacketCount=10",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d055, d055_zero_results) is False

    d055_wrong_driver_results = {
        "steps": {
            **d055_results["steps"],
            "step8_drv_verify": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverTxMulticastPacketCount=30",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d055, d055_wrong_driver_results) is False


def test_d057_txunicastpacketcount_uses_same_sta_failure_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert {
        "wifi-llapi-D056-txpacketcount",
        "wifi-llapi-D057-txunicastpacketcount",
    }.issubset(discoverable_ids)

    pass_cases = {
        "D056_txpacketcount.yaml": {
            "id": "wifi-llapi-D056-txpacketcount",
            "row": 56,
            "api": "TxPacketCount",
            "driver_before": "drv_before_5g.DriverTxPacketCount",
            "driver_after": "drv_after_5g.DriverTxPacketCount",
            "driver_token": "DriverTxPacketCount=",
            "ssid": "TestPilot_BTM",
        },
        "D057_txunicastpacketcount.yaml": {
            "id": "wifi-llapi-D057-txunicastpacketcount",
            "row": 57,
            "api": "TxUnicastPacketCount",
            "driver_before": "drv_before_5g.DriverTxUnicastPacketCount",
            "driver_after": "drv_after_5g.DriverTxUnicastPacketCount",
            "driver_token": "DriverTxUnicastPacketCount=",
            "ssid": "testpilot5G",
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
        assert case_data["llapi_support"] == "Support"
        assert case_data["bands"] == ["5g"]
        assert links == {"5g"}
        assert case_data["hlapi_command"] == f'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}?"'
        assert [step["phase"] for step in case_data["steps"]] == [
            "baseline",
            "baseline",
            "baseline",
            "baseline",
            "trigger",
            "verify",
            "verify",
        ]
        assert "wpa_state=" in commands
        assert "StaIp=" in commands
        assert "TriggerTxPackets=" in commands
        assert "DriverAssocMac=" in commands
        assert meta["driver_token"] in commands
        assert any(
            criterion["field"] == "sta_ready_5g.wpa_state"
            and criterion["operator"] == "equals"
            and criterion["value"] == "COMPLETED"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "sta_ready_5g.ssid"
            and criterion["operator"] == "equals"
            and criterion["value"] == meta["ssid"]
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "assoc_entry.MACAddress"
            and criterion["operator"] == "equals"
            and criterion.get("reference") == "sta_ready_5g.StaMac"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion["field"] == "trigger_probe.TriggerTxPackets"
            and criterion["operator"] == ">"
            and str(criterion["value"]) == "0"
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion.get("operator") == "delta_nonzero"
            and criterion.get("delta")
            == {
                "baseline": f'api_before_5g.{meta["api"]}',
                "verify": f'api_after_5g.{meta["api"]}',
            }
            for criterion in case_data["pass_criteria"]
        )
        assert any(
            criterion.get("operator") == "delta_match"
            and criterion.get("reference_delta")
            == {
                "baseline": meta["driver_before"],
                "verify": meta["driver_after"],
            }
            for criterion in case_data["pass_criteria"]
        )
        assert not any(
            criterion.get("field") == f'result.{meta["api"]}'
            and criterion.get("operator") == "equals"
            and str(criterion.get("value")) == "0"
            for criterion in case_data["pass_criteria"]
        )


def test_d057_txunicastpacketcount_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    pass_cases = {
        "D056_txpacketcount.yaml": {
            "api": "TxPacketCount",
            "driver_field": "DriverTxPacketCount",
            "ssid": "TestPilot_BTM",
            "key_mgmt": "SAE",
        },
        "D057_txunicastpacketcount.yaml": {
            "api": "TxUnicastPacketCount",
            "driver_field": "DriverTxUnicastPacketCount",
            "ssid": "testpilot5G",
            "key_mgmt": "WPA2-PSK",
        },
    }

    for filename, meta in pass_cases.items():
        case_data = load_case(cases_dir / filename)
        pass_results = {
            "steps": {
                "step1_sta_ready": {
                    "success": True,
                    "output": "ssid={ssid}\nkey_mgmt={key_mgmt}\nwpa_state=COMPLETED\nStaMac=2c:59:17:00:04:85\nStaIp=192.168.1.3".format(**meta),
                    "timing": 0.01,
                },
                "step2_assoc_entry": {
                    "success": True,
                    "output": 'MACAddress=2c:59:17:00:04:85',
                    "timing": 0.01,
                },
                "step3_api_baseline": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=10',
                    "timing": 0.01,
                },
                "step4_drv_baseline": {
                    "success": True,
                    "output": f'DriverAssocMac=2c:59:17:00:04:85\n{meta["driver_field"]}=100',
                    "timing": 0.01,
                },
                "step5_trigger": {
                    "success": True,
                    "output": '8 packets transmitted, 8 received, 0% packet loss\nTriggerTxPackets=8',
                    "timing": 0.01,
                },
                "step6_api_verify": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=16',
                    "timing": 0.01,
                },
                "step7_drv_verify": {
                    "success": True,
                    "output": f'DriverAssocMac=2c:59:17:00:04:85\n{meta["driver_field"]}=106',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, pass_results) is True

        zero_results = {
            "steps": {
                **pass_results["steps"],
                "step6_api_verify": {
                    "success": True,
                    "output": f'WiFi.AccessPoint.1.AssociatedDevice.1.{meta["api"]}=10',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, zero_results) is False

        mismatch_results = {
            "steps": {
                **pass_results["steps"],
                "step7_drv_verify": {
                    "success": True,
                    "output": f'DriverAssocMac=2c:59:17:00:04:85\n{meta["driver_field"]}=130',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, mismatch_results) is False

        assoc_mismatch_results = {
            "steps": {
                **pass_results["steps"],
                "step7_drv_verify": {
                    "success": True,
                    "output": f'DriverAssocMac=aa:aa:aa:aa:aa:aa\n{meta["driver_field"]}=106',
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case_data, assoc_mismatch_results) is False


def test_d053_txbytes_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D053-txbytes" in discoverable_ids

    d053_raw = yaml.safe_load((cases_dir / "D053_txbytes.yaml").read_text(encoding="utf-8"))
    d053 = load_case(cases_dir / "D053_txbytes.yaml")
    d053_commands = "\n".join(str(step.get("command", "")) for step in d053["steps"])
    d053_links = {link["band"] for link in d053["topology"]["links"]}

    assert "aliases" not in d053_raw
    assert d053["id"] == "wifi-llapi-D053-txbytes"
    assert d053["source"]["row"] == 53
    assert d053["llapi_support"] == "Support"
    assert d053["bands"] == ["5g", "6g", "2.4g"]
    assert d053_links == {"5g", "6g", "2.4g"}
    assert d053["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxBytes?"'
    assert len(d053["steps"]) == 21
    assert [step["phase"] for step in d053["steps"]] == [
        "baseline", "baseline", "baseline", "baseline", "trigger", "verify", "verify",
        "baseline", "baseline", "baseline", "baseline", "trigger", "verify", "verify",
        "baseline", "baseline", "baseline", "baseline", "trigger", "verify", "verify",
    ]
    assert "TriggerTxPackets5g=" in d053_commands
    assert "TriggerTxPackets6g=" in d053_commands
    assert "TriggerTxPackets24g=" in d053_commands
    assert "DriverTxBytes5g=" in d053_commands
    assert "DriverTxBytes6g=" in d053_commands
    assert "DriverTxBytes24g=" in d053_commands
    assert any(
        criterion["field"] == "sta_ready_5g.wpa_state"
        and criterion["operator"] == "equals"
        and criterion["value"] == "COMPLETED"
        for criterion in d053["pass_criteria"]
    )
    assert any(
        criterion.get("field") == "assoc_entry_6g.AssocMac6g"
        and criterion.get("operator") == "equals"
        and criterion.get("reference") == "sta_ready_6g.StaMac6g"
        for criterion in d053["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_nonzero"
        and criterion.get("delta")
        == {
            "baseline": "api_before_24g.TxBytes",
            "verify": "api_after_24g.TxBytes",
        }
        for criterion in d053["pass_criteria"]
    )
    assert any(
        criterion.get("operator") == "delta_match"
        and criterion.get("reference_delta")
        == {
            "baseline": "drv_before_6g.DriverTxBytes6g",
            "verify": "drv_after_6g.DriverTxBytes6g",
        }
        for criterion in d053["pass_criteria"]
    )


def test_d053_txbytes_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d053 = load_case(cases_dir / "D053_txbytes.yaml")

    d053_results = {
        "steps": {
            "step1_5g_sta_ready": {"success": True, "output": "wpa_state=COMPLETED\nssid=testpilot5G\nStaMac5g=2c:59:17:00:04:85\nStaIp5g=192.168.1.3", "timing": 0.01},
            "step2_5g_assoc_entry": {"success": True, "output": "AssocMac5g=2c:59:17:00:04:85", "timing": 0.01},
            "step3_5g_api_baseline": {"success": True, "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxBytes=10", "timing": 0.01},
            "step4_5g_drv_baseline": {"success": True, "output": "DriverAssocMac5g=2c:59:17:00:04:85\nDriverTxBytes5g=100", "timing": 0.01},
            "step5_5g_trigger": {"success": True, "output": "TriggerTxPackets5g=8", "timing": 0.01},
            "step6_5g_api_verify": {"success": True, "output": "WiFi.AccessPoint.1.AssociatedDevice.1.TxBytes=18", "timing": 0.01},
            "step7_5g_drv_verify": {"success": True, "output": "DriverAssocMac5g=2c:59:17:00:04:85\nDriverTxBytes5g=108", "timing": 0.01},
            "step8_6g_sta_ready": {"success": True, "output": "wpa_state=COMPLETED\nssid=testpilot6G\nStaMac6g=2c:59:17:00:04:86\nStaIp6g=192.168.1.3", "timing": 0.01},
            "step9_6g_assoc_entry": {"success": True, "output": "AssocMac6g=2c:59:17:00:04:86", "timing": 0.01},
            "step10_6g_api_baseline": {"success": True, "output": "WiFi.AccessPoint.3.AssociatedDevice.1.TxBytes=20", "timing": 0.01},
            "step11_6g_drv_baseline": {"success": True, "output": "DriverAssocMac6g=2c:59:17:00:04:86\nDriverTxBytes6g=200", "timing": 0.01},
            "step12_6g_trigger": {"success": True, "output": "TriggerTxPackets6g=8", "timing": 0.01},
            "step13_6g_api_verify": {"success": True, "output": "WiFi.AccessPoint.3.AssociatedDevice.1.TxBytes=28", "timing": 0.01},
            "step14_6g_drv_verify": {"success": True, "output": "DriverAssocMac6g=2c:59:17:00:04:86\nDriverTxBytes6g=208", "timing": 0.01},
            "step15_24g_sta_ready": {"success": True, "output": "wpa_state=COMPLETED\nssid=testpilot2G\nStaMac24g=2c:59:17:00:04:97\nStaIp24g=192.168.1.3", "timing": 0.01},
            "step16_24g_assoc_entry": {"success": True, "output": "AssocMac24g=2c:59:17:00:04:97", "timing": 0.01},
            "step17_24g_api_baseline": {"success": True, "output": "WiFi.AccessPoint.5.AssociatedDevice.1.TxBytes=30", "timing": 0.01},
            "step18_24g_drv_baseline": {"success": True, "output": "DriverAssocMac24g=2c:59:17:00:04:97\nDriverTxBytes24g=300", "timing": 0.01},
            "step19_24g_trigger": {"success": True, "output": "TriggerTxPackets24g=8", "timing": 0.01},
            "step20_24g_api_verify": {"success": True, "output": "WiFi.AccessPoint.5.AssociatedDevice.1.TxBytes=38", "timing": 0.01},
            "step21_24g_drv_verify": {"success": True, "output": "DriverAssocMac24g=2c:59:17:00:04:97\nDriverTxBytes24g=308", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d053, d053_results) is True

    d053_wrong_6g_driver_results = {
        "steps": {
            **d053_results["steps"],
            "step14_6g_drv_verify": {
                "success": True,
                "output": "DriverAssocMac6g=2c:59:17:00:04:86\nDriverTxBytes6g=260",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d053, d053_wrong_6g_driver_results) is False


def test_d062_vendoroui_uses_same_sta_pass_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D062-vendoroui" in discoverable_ids

    d062_raw = yaml.safe_load((cases_dir / "D062_vendoroui.yaml").read_text(encoding="utf-8"))
    d062 = load_case(cases_dir / "D062_vendoroui.yaml")
    d062_commands = "\n".join(str(step.get("command", "")) for step in d062["steps"])
    d062_links = {link["band"] for link in d062["topology"]["links"]}

    assert "aliases" not in d062_raw
    assert d062["id"] == "wifi-llapi-D062-vendoroui"
    assert d062["source"]["row"] == 62
    assert d062["llapi_support"] == "Support"
    assert d062["bands"] == ["5g"]
    assert d062_links == {"5g"}
    assert d062["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"'
    assert "cat /sys/class/net/wl0/address" in d062_commands
    assert "tr 'A-F' 'a-f'" in d062_commands
    assert "MACAddress?" in d062_commands
    assert 'VendorOUI?"' in d062_commands
    assert "AssocVendorOUI=" in d062_commands
    assert "DriverVendorOUICount=" in d062_commands
    assert "DriverVendorOUIList=" in d062_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d062["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VendorOUI"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^([0-9A-Fa-f]{2}:){2}[0-9A-Fa-f]{2}(,([0-9A-Fa-f]{2}:){2}[0-9A-Fa-f]{2})*$"
        for criterion in d062["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VendorOUI"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_snapshot.AssocVendorOUI"
        for criterion in d062["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVendorOUICount"
        and criterion["operator"] == ">"
        and str(criterion["value"]) == "0"
        for criterion in d062["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVendorOUIList"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "result.VendorOUI"
        for criterion in d062["pass_criteria"]
    )


def test_d062_vendoroui_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d062 = load_case(cases_dir / "D062_vendoroui.yaml")

    d062_results = {
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
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI="00:90:4C,00:10:18,00:50:F2,50:6F:9A"',
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocVendorOUI=00:90:4C,00:10:18,00:50:F2,50:6F:9A",
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
    assert plugin.evaluate(d062, d062_results) is True

    d062_wrong_llapi_results = {
        "steps": {
            **d062_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI=""',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d062, d062_wrong_llapi_results) is False

    d062_missing_driver_results = {
        "steps": {
            **d062_results["steps"],
            "step5": {
                "success": True,
                "output": "DriverAssocMac=2c:59:17:00:04:85\nDriverVendorOUICount=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d062, d062_missing_driver_results) is False

    d062_wrong_assoc_results = {
        "steps": {
            **d062_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=aa:aa:aa:aa:aa:aa",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d062, d062_wrong_assoc_results) is False


def test_d063_vhtcapabilities_uses_same_sta_pass_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D063-vhtcapabilities-accesspoint-associateddevice" in discoverable_ids

    d063_raw = yaml.safe_load(
        (cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml").read_text(
            encoding="utf-8"
        )
    )
    d063 = load_case(cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml")
    d063_commands = "\n".join(str(step.get("command", "")) for step in d063["steps"])
    d063_links = {link["band"] for link in d063["topology"]["links"]}

    assert "aliases" not in d063_raw
    assert d063["id"] == "wifi-llapi-D063-vhtcapabilities-accesspoint-associateddevice"
    assert d063["source"]["row"] == 63
    assert d063["llapi_support"] == "Support"
    assert d063["bands"] == ["5g"]
    assert d063_links == {"5g"}
    assert d063["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"'
    assert "cat /sys/class/net/wl0/address" in d063_commands
    assert "tr 'A-F' 'a-f'" in d063_commands
    assert "MACAddress?" in d063_commands
    assert 'VhtCapabilities?"' in d063_commands
    assert "AssocVhtCapabilities=" in d063_commands
    assert "DriverVhtCapsLine=" in d063_commands
    assert "DriverVhtCapabilities=" in d063_commands
    assert any(
        criterion["field"] == "assoc_entry.MACAddress"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "sta_identity.StaMac"
        for criterion in d063["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VhtCapabilities"
        and criterion["operator"] == "regex"
        and criterion["value"] == "^[A-Z0-9-]+(,[A-Z0-9-]+)*$"
        for criterion in d063["pass_criteria"]
    )
    assert any(
        criterion["field"] == "result.VhtCapabilities"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "assoc_snapshot.AssocVhtCapabilities"
        for criterion in d063["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SGI80"
        for criterion in d063["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SGI160"
        for criterion in d063["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "contains"
        and criterion["value"] == "SU-BFE"
        for criterion in d063["pass_criteria"]
    )
    assert not any(
        criterion["field"] == "driver_capture.DriverVhtCapabilities"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "result.VhtCapabilities"
        for criterion in d063["pass_criteria"]
    )


def test_d063_vhtcapabilities_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d063 = load_case(cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml")

    d063_results = {
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
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities="SGI80,SGI160,SU-BFR,SU-BFE"',
                "timing": 0.01,
            },
            "step4": {
                "success": True,
                "output": "AssocMAC=2c:59:17:00:04:85\nAssocVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE",
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
    assert plugin.evaluate(d063, d063_results) is True

    d063_wrong_llapi_results = {
        "steps": {
            **d063_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities=""',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d063, d063_wrong_llapi_results) is False

    d063_missing_driver_results = {
        "steps": {
            **d063_results["steps"],
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
    assert plugin.evaluate(d063, d063_missing_driver_results) is False

    d063_wrong_assoc_results = {
        "steps": {
            **d063_results["steps"],
            "step2": {
                "success": True,
                "output": "MACAddress=aa:aa:aa:aa:aa:aa",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d063, d063_wrong_assoc_results) is False


def test_d064_apbridgedisable_uses_ap_only_unsupported_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D064-apbridgedisable" in discoverable_ids

    d064_raw = yaml.safe_load((cases_dir / "D064_apbridgedisable.yaml").read_text(encoding="utf-8"))
    d064 = load_case(cases_dir / "D064_apbridgedisable.yaml")
    d064_commands = "\n".join(str(step.get("command", "")) for step in d064["steps"])

    assert "aliases" not in d064_raw
    assert d064["id"] == "wifi-llapi-D064-apbridgedisable"
    assert d064["source"]["row"] == 64
    assert d064["llapi_support"] == "Not Supported"
    assert d064["bands"] == ["5g"]
    assert set(d064["topology"]["devices"]) == {"DUT"}
    assert d064["topology"]["links"] == []
    assert d064["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.APBridgeDisable?"'
    assert "STA:" not in d064.get("sta_env_setup", "")
    assert "WPA2-Personal" in d064.get("sta_env_setup", "")
    assert "APBridgeDisable=1" in d064_commands
    assert "DriverApIsolateOn=" in d064_commands
    assert "HostapdApIsolateZeroCount=" in d064_commands
    assert "APBridgeDisable=0" in d064_commands
    assert "DriverApIsolateOff=" in d064_commands
    assert "DriverBssState=" in d064_commands
    assert any(
        criterion["field"] == "result_on.APBridgeDisable"
        and criterion["operator"] == "equals"
        and str(criterion["value"]) == "1"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "hostapd_after_on.HostapdApIsolate"
        and criterion["operator"] == "not_equals"
        and criterion.get("reference") == "result_on.APBridgeDisable"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_off.DriverApIsolateOff"
        and criterion["operator"] == "not_equals"
        and criterion.get("reference") == "result_off.APBridgeDisable"
        for criterion in d064["pass_criteria"]
    )
    assert any(
        criterion["field"] == "bss_status.DriverBssState"
        and criterion["operator"] == "equals"
        and criterion["value"] == "up"
        for criterion in d064["pass_criteria"]
    )


def test_d064_apbridgedisable_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_apbridgedisable.yaml")

    assert plugin.setup_env(d064, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert all("wpa_cli" not in command for command in recorder.transports[0].executed_commands)
    assert any(
        command == "ubus-cli WiFi.AccessPoint.1.APBridgeDisable=0"
        for command in recorder.transports[0].executed_commands
    )
    plugin.teardown(d064, topology)


def test_d064_apbridgedisable_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_apbridgedisable.yaml")

    d064_results = {
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
    assert plugin.evaluate(d064, d064_results) is True

    d064_wrong_enable_results = {
        "steps": {
            **d064_results["steps"],
            "step2": {
                "success": True,
                "output": "WiFi.AccessPoint.1.APBridgeDisable=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_wrong_enable_results) is False

    d064_wrong_hostapd_results = {
        "steps": {
            **d064_results["steps"],
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
    assert plugin.evaluate(d064, d064_wrong_hostapd_results) is False

    d064_wrong_driver_results = {
        "steps": {
            **d064_results["steps"],
            "step8": {
                "success": True,
                "output": "DriverApIsolateOff=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_wrong_driver_results) is False

    d064_bss_down_results = {
        "steps": {
            **d064_results["steps"],
            "step9": {
                "success": True,
                "output": "DriverBssState=down",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d064, d064_bss_down_results) is False


def test_d065_bridgeinterface_uses_ap_only_multiband_pass_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "wifi-llapi-D065-bridgeinterface" in discoverable_ids

    d065_raw = yaml.safe_load((cases_dir / "D065_bridgeinterface.yaml").read_text(encoding="utf-8"))
    d065 = load_case(cases_dir / "D065_bridgeinterface.yaml")
    d065_commands = "\n".join(str(step.get("command", "")) for step in d065["steps"])

    assert "aliases" not in d065_raw
    assert d065["id"] == "wifi-llapi-D065-bridgeinterface"
    assert d065["source"]["row"] == 65
    assert d065["llapi_support"] == "Support"
    assert d065["bands"] == ["5g", "6g", "2.4g"]
    assert set(d065["topology"]["devices"]) == {"DUT"}
    assert d065["topology"]["links"] == []
    assert d065["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.BridgeInterface?"'
    assert "wl -i wl0 bss" in d065.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d065.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d065.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.BridgeInterface?"' in d065_commands
    assert 'WiFi.AccessPoint.3.BridgeInterface?"' in d065_commands
    assert 'WiFi.AccessPoint.5.BridgeInterface?"' in d065_commands
    assert "BridgeConfig5g=" in d065_commands
    assert "BridgeConfig6g=" in d065_commands
    assert "BridgeConfig24g=" in d065_commands
    assert "BridgeConfig5gMismatch=" in d065_commands
    assert "BridgeConfig6gMismatch=" in d065_commands
    assert "BridgeConfig24gMismatch=" in d065_commands
    assert "BridgeMaster5g=" in d065_commands
    assert "BridgeMaster6g=" in d065_commands
    assert "BridgeMaster24g=" in d065_commands
    assert any(
        criterion["field"] == "result_5g.BridgeInterface"
        and criterion["operator"] == "equals"
        and criterion["value"] == "br-lan"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "config_6g.BridgeConfig6g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "result_6g.BridgeInterface"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "config_5g.BridgeConfig5gMismatch"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d065["pass_criteria"]
    )
    assert any(
        criterion["field"] == "bridge_state.BridgeMaster24g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "result_24g.BridgeInterface"
        for criterion in d065["pass_criteria"]
    )


def test_d065_bridgeinterface_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_bridgeinterface.yaml")

    assert plugin.setup_env(d065, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d065, topology)


def test_d065_bridgeinterface_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_bridgeinterface.yaml")

    d065_results = {
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
    assert plugin.evaluate(d065, d065_results) is True

    d065_wrong_6g_results = {
        "steps": {
            **d065_results["steps"],
            "step2_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.BridgeInterface="br-guest"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_wrong_6g_results) is False

    d065_wrong_config_count_results = {
        "steps": {
            **d065_results["steps"],
            "step5_6g_config": {
                "success": True,
                "output": "BridgeConfig6g=br-lan\nBridgeConfig6gCount=1\nBridgeConfig6gMismatch=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_wrong_config_count_results) is False

    d065_mixed_config_results = {
        "steps": {
            **d065_results["steps"],
            "step4_5g_config": {
                "success": True,
                "output": "BridgeConfig5g=br-guest\nBridgeConfig5gCount=2\nBridgeConfig5gMismatch=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_mixed_config_results) is False

    d065_missing_member_results = {
        "steps": {
            **d065_results["steps"],
            "step7_bridge_state": {
                "success": True,
                "output": "BridgeMaster5g=br-lan\nBridgeMaster6g=br-lan",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d065, d065_missing_member_results) is False

    d065_wrong_bridge_name_results = {
        "steps": {
            **d065_results["steps"],
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
    assert plugin.evaluate(d065, d065_wrong_bridge_name_results) is False


def test_d068_discoverymethodenabled_accesspoint_fils_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d066_raw = yaml.safe_load(
        (cases_dir / "D066_discoverymethodenabled_accesspoint_fils.yaml").read_text(encoding="utf-8")
    )
    d066 = load_case(cases_dir / "D066_discoverymethodenabled_accesspoint_fils.yaml")
    d066_commands = "\n".join(str(step.get("command", "")) for step in d066["steps"])

    assert "aliases" not in d066_raw
    assert d066["id"] == "wifi-llapi-D066-discoverymethodenabled-accesspoint-fils"
    assert d066["source"]["row"] == 66
    assert d066["llapi_support"] == "Support"
    assert d066["bands"] == ["5g", "6g", "2.4g"]
    assert set(d066["topology"]["devices"]) == {"DUT"}
    assert d066["topology"]["links"] == []
    assert d066["hlapi_command"] == 'ubus-cli WiFi.AccessPoint.1.DiscoveryMethodEnabled=FILS'
    assert "wl -i wl0 bss" in d066.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d066.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d066.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.DiscoveryMethodEnabled?"' in d066_commands
    assert "DiscoveryMethodEnabled=FILS" in d066_commands
    assert "DiscoveryMethodEnabled=FILSDiscovery" in d066_commands
    assert any(
        criterion["field"] == "invalid_5g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "invalid value"
        for criterion in d066["pass_criteria"]
    )
    assert any(
        criterion["field"] == "set_alt_6g.DiscoveryMethodEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "FILSDiscovery"
        for criterion in d066["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_alt_6g.DiscoveryMethodEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "FILSDiscovery"
        for criterion in d066["pass_criteria"]
    )


def test_d068_discoverymethodenabled_accesspoint_fils_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_discoverymethodenabled_accesspoint_fils.yaml")

    assert plugin.setup_env(d066, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d066, topology)


def test_d068_discoverymethodenabled_accesspoint_fils_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_discoverymethodenabled_accesspoint_fils.yaml")

    d066_results = {
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
    assert plugin.evaluate(d066, d066_results) is True

    d066_wrong_invalid_results = {
        "steps": {
            **d066_results["steps"],
            "step5_invalid_6g": {
                "success": True,
                "output": "ERROR: set WiFi.AccessPoint.3.DiscoveryMethodEnabled failed (1 - permission denied)",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_invalid_results) is False

    d066_wrong_alt_results = {
        "steps": {
            **d066_results["steps"],
            "step15_after_alt_24g": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_alt_results) is False

    d066_wrong_set_alt_results = {
        "steps": {
            **d066_results["steps"],
            "step11_set_alt_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_set_alt_results) is False

    d066_wrong_restore_results = {
        "steps": {
            **d066_results["steps"],
            "step16_restore_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="FILSDiscovery"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d066, d066_wrong_restore_results) is False


def test_d068_discoverymethodenabled_accesspoint_upr_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d067_raw = yaml.safe_load(
        (cases_dir / "D067_discoverymethodenabled_accesspoint_upr.yaml").read_text(encoding="utf-8")
    )
    d067 = load_case(cases_dir / "D067_discoverymethodenabled_accesspoint_upr.yaml")
    d067_commands = "\n".join(str(step.get("command", "")) for step in d067["steps"])

    assert "aliases" not in d067_raw
    assert d067["id"] == "wifi-llapi-D067-discoverymethodenabled-accesspoint-upr"
    assert d067["source"]["row"] == 67
    assert d067["llapi_support"] == "Support"
    assert d067["bands"] == ["5g", "6g", "2.4g"]
    assert set(d067["topology"]["devices"]) == {"DUT"}
    assert d067["topology"]["links"] == []
    assert d067["hlapi_command"] == 'ubus-cli WiFi.AccessPoint.1.DiscoveryMethodEnabled=UPR'
    assert "wl -i wl0 bss" in d067.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d067.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d067.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.DiscoveryMethodEnabled?"' in d067_commands
    assert "DiscoveryMethodEnabled=UPR" in d067_commands
    assert any(
        criterion["field"] == "set_upr_6g.DiscoveryMethodEnabled"
        and criterion["operator"] == "equals"
        and criterion["value"] == "UPR"
        for criterion in d067["pass_criteria"]
    )
    assert any(
        criterion["field"] == "set_upr_5g"
        and criterion["operator"] == "contains"
        and criterion["value"] == "invalid value"
        for criterion in d067["pass_criteria"]
    )


def test_d068_discoverymethodenabled_accesspoint_upr_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_discoverymethodenabled_accesspoint_upr.yaml")

    assert plugin.setup_env(d067, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d067, topology)


def test_d068_discoverymethodenabled_accesspoint_upr_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_discoverymethodenabled_accesspoint_upr.yaml")

    d067_results = {
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
    assert plugin.evaluate(d067, d067_results) is True

    d067_wrong_5g_results = {
        "steps": {
            **d067_results["steps"],
            "step4_set_upr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.\nWiFi.AccessPoint.1.DiscoveryMethodEnabled="UPR"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_wrong_5g_results) is False

    d067_wrong_6g_results = {
        "steps": {
            **d067_results["steps"],
            "step8_after_upr_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_wrong_6g_results) is False

    d067_wrong_restore_results = {
        "steps": {
            **d067_results["steps"],
            "step11_restore_6g": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.\nWiFi.AccessPoint.3.DiscoveryMethodEnabled="UPR"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d067, d067_wrong_restore_results) is False


def test_d068_discoverymethodenabled_accesspoint_rnr_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d068_raw = yaml.safe_load(
        (cases_dir / "D068_discoverymethodenabled_accesspoint_rnr.yaml").read_text(encoding="utf-8")
    )
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_rnr.yaml")
    d068_commands = "\n".join(str(step.get("command", "")) for step in d068["steps"])

    assert "aliases" not in d068_raw
    assert d068["id"] == "wifi-llapi-D068-discoverymethodenabled-accesspoint-rnr"
    assert d068["source"]["row"] == 70
    assert d068["llapi_support"] == "Support"
    assert d068["bands"] == ["5g", "6g", "2.4g"]
    assert set(d068["topology"]["devices"]) == {"DUT"}
    assert d068["topology"]["links"] == []
    assert d068["hlapi_command"] == 'ubus-cli WiFi.AccessPoint.1.DiscoveryMethodEnabled=RNR'
    assert "wl -i wl0 bss" in d068.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d068.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d068.get("sta_env_setup", "")
    assert "RnrEnabled6gCount=" in d068_commands
    assert "RnrTotal24gCount=" in d068_commands
    assert any(
        criterion["field"] == "cfg_6g_after.RnrEnabled6gCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d068["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_5g_after.RnrTotal5gCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d068["pass_criteria"]
    )


def test_d068_discoverymethodenabled_accesspoint_rnr_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_rnr.yaml")

    assert plugin.setup_env(d068, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d068, topology)


def test_d068_discoverymethodenabled_accesspoint_rnr_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_rnr.yaml")

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
    assert plugin.evaluate(d068, d068_results) is True

    d068_wrong_6g_config_results = {
        "steps": {
            **d068_results["steps"],
            "step11_cfg_6g_after": {
                "success": True,
                "output": "RnrEnabled6gCount=0\nRnrDisabled6gCount=2\nRnrTotal6gCount=2",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_6g_config_results) is False

    d068_wrong_5g_getter_results = {
        "steps": {
            **d068_results["steps"],
            "step7_after_rnr_5g": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.DiscoveryMethodEnabled="Default"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_5g_getter_results) is False

    d068_wrong_restore_results = {
        "steps": {
            **d068_results["steps"],
            "step16_cfg_6g_restore": {
                "success": True,
                "output": "RnrEnabled6gCount=1\nRnrDisabled6gCount=1\nRnrTotal6gCount=2",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d068, d068_wrong_restore_results) is False


def test_d366_srgbsscolorbitmap_radio_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d366_raw = yaml.safe_load((cases_dir / "D366_srgbsscolorbitmap.yaml").read_text(encoding="utf-8"))
    d366 = load_case(cases_dir / "D366_srgbsscolorbitmap.yaml")
    d366_commands = "\n".join(str(step.get("command", "")) for step in d366["steps"])

    assert "aliases" not in d366_raw
    assert d366["id"] == "wifi-llapi-D366-srgbsscolorbitmap"
    assert d366["source"]["row"] == 366
    assert d366["llapi_support"] == "Support"
    assert d366["bands"] == ["5g", "6g", "2.4g"]
    assert set(d366["topology"]["devices"]) == {"DUT"}
    assert d366["topology"]["links"] == []
    assert d366["hlapi_command"] == 'ubus-cli WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap="1"'
    assert "wl -i wl0 bss" in d366.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d366.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d366.get("sta_env_setup", "")
    assert 'WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap?"' in d366_commands
    assert 'WiFi.Radio.2.IEEE80211ax.SRGBSSColorBitmap="1"' in d366_commands
    assert "HostapdSrgBssColorLines=" in d366_commands
    assert any(
        criterion["field"] == "after_6g.SRGBSSColorBitmap"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d366["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_24g_after.HostapdSrgBssColorLines"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d366["pass_criteria"]
    )


def test_d366_srgbsscolorbitmap_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d366 = load_case(cases_dir / "D366_srgbsscolorbitmap.yaml")

    assert plugin.setup_env(d366, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d366, topology)


def test_d366_srgbsscolorbitmap_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d366 = load_case(cases_dir / "D366_srgbsscolorbitmap.yaml")

    d366_results = {
        "steps": {
            "step1_default_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
            "step2_default_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
            "step3_default_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
            "step4_set_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.\nWiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap="1"',
                "timing": 0.01,
            },
            "step5_set_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.\nWiFi.Radio.2.IEEE80211ax.SRGBSSColorBitmap="1"',
                "timing": 0.01,
            },
            "step6_set_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.\nWiFi.Radio.3.IEEE80211ax.SRGBSSColorBitmap="1"',
                "timing": 0.01,
            },
            "step7_after_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap="1"',
                "timing": 0.01,
            },
            "step8_after_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.SRGBSSColorBitmap="1"',
                "timing": 0.01,
            },
            "step9_after_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.SRGBSSColorBitmap="1"',
                "timing": 0.01,
            },
            "step10_cfg_5g_after": {
                "success": True,
                "output": "HostapdSrgBssColorLines=0",
                "timing": 0.01,
            },
            "step11_cfg_6g_after": {
                "success": True,
                "output": "HostapdSrgBssColorLines=0",
                "timing": 0.01,
            },
            "step12_cfg_24g_after": {
                "success": True,
                "output": "HostapdSrgBssColorLines=0",
                "timing": 0.01,
            },
            "step13_restore_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.\nWiFi.Radio.1.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
            "step14_restore_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.\nWiFi.Radio.2.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
            "step15_restore_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.\nWiFi.Radio.3.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d366, d366_results) is True

    d366_wrong_cfg_results = {
        "steps": {
            **d366_results["steps"],
            "step11_cfg_6g_after": {
                "success": True,
                "output": "HostapdSrgBssColorLines=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d366, d366_wrong_cfg_results) is False

    d366_wrong_24g_getter_results = {
        "steps": {
            **d366_results["steps"],
            "step9_after_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.SRGBSSColorBitmap=""',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d366, d366_wrong_24g_getter_results) is False


def test_d369_srgpartialbssidbitmap_radio_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d369_raw = yaml.safe_load((cases_dir / "D369_srgpartialbssidbitmap.yaml").read_text(encoding="utf-8"))
    d369 = load_case(cases_dir / "D369_srgpartialbssidbitmap.yaml")
    d369_commands = "\n".join(str(step.get("command", "")) for step in d369["steps"])

    assert "aliases" not in d369_raw
    assert d369["id"] == "wifi-llapi-D369-srgpartialbssidbitmap"
    assert d369["source"]["row"] == 369
    assert d369["llapi_support"] == "Support"
    assert d369["bands"] == ["5g", "6g", "2.4g"]
    assert set(d369["topology"]["devices"]) == {"DUT"}
    assert d369["topology"]["links"] == []
    assert d369["hlapi_command"] == 'ubus-cli WiFi.Radio.1.IEEE80211ax.SRGPartialBSSIDBitmap="1"'
    assert "wl -i wl0 bss" in d369.get("sta_env_setup", "")
    assert "wl -i wl1 bss" in d369.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d369.get("sta_env_setup", "")
    assert 'WiFi.Radio.1.IEEE80211ax.SRGPartialBSSIDBitmap?"' in d369_commands
    assert "HostapdSrgPartialBssidLines=" in d369_commands
    assert "error=" in d369_commands
    assert "message=" in d369_commands
    assert any(
        criterion["field"] == "invalid_24g.error"
        and criterion["operator"] == "equals"
        and criterion["value"] == "4"
        for criterion in d369["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_6g_after.HostapdSrgPartialBssidLines"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d369["pass_criteria"]
    )


def test_d369_srgpartialbssidbitmap_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d369 = load_case(cases_dir / "D369_srgpartialbssidbitmap.yaml")

    assert plugin.setup_env(d369, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    assert recorder.transports[0].executed_commands.count("wl -i wl0 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl1 bss") == 1
    assert recorder.transports[0].executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d369, topology)


def test_d369_srgpartialbssidbitmap_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d369 = load_case(cases_dir / "D369_srgpartialbssidbitmap.yaml")

    d369_results = {
        "steps": {
            "step1_default_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
            "step2_default_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
            "step3_default_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
            "step4_set_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.\nWiFi.Radio.1.IEEE80211ax.SRGPartialBSSIDBitmap="1"',
                "timing": 0.01,
            },
            "step5_set_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.\nWiFi.Radio.2.IEEE80211ax.SRGPartialBSSIDBitmap="1"',
                "timing": 0.01,
            },
            "step6_invalid_24g": {
                "success": True,
                "output": "ERROR: set WiFi.Radio.3.IEEE80211ax.SRGPartialBSSIDBitmap failed (4 - parameter not found)\nerror=4\nmessage=parameter not found",
                "timing": 0.01,
            },
            "step7_after_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.SRGPartialBSSIDBitmap="1"',
                "timing": 0.01,
            },
            "step8_after_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.SRGPartialBSSIDBitmap="1"',
                "timing": 0.01,
            },
            "step9_after_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
            "step10_cfg_5g_after": {
                "success": True,
                "output": "HostapdSrgPartialBssidLines=0",
                "timing": 0.01,
            },
            "step11_cfg_6g_after": {
                "success": True,
                "output": "HostapdSrgPartialBssidLines=0",
                "timing": 0.01,
            },
            "step12_cfg_24g_after": {
                "success": True,
                "output": "HostapdSrgPartialBssidLines=0",
                "timing": 0.01,
            },
            "step13_restore_5g": {
                "success": True,
                "output": 'WiFi.Radio.1.IEEE80211ax.\nWiFi.Radio.1.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
            "step14_restore_6g": {
                "success": True,
                "output": 'WiFi.Radio.2.IEEE80211ax.\nWiFi.Radio.2.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
            "step15_restore_24g": {
                "success": True,
                "output": 'WiFi.Radio.3.IEEE80211ax.\nWiFi.Radio.3.IEEE80211ax.SRGPartialBSSIDBitmap=""',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d369, d369_results) is True

    d369_wrong_error_results = {
        "steps": {
            **d369_results["steps"],
            "step6_invalid_24g": {
                "success": True,
                "output": "ERROR: set WiFi.Radio.3.IEEE80211ax.SRGPartialBSSIDBitmap failed (0 - unexpected)\nerror=0\nmessage=unexpected",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d369, d369_wrong_error_results) is False

    d369_wrong_6g_cfg_results = {
        "steps": {
            **d369_results["steps"],
            "step11_cfg_6g_after": {
                "success": True,
                "output": "HostapdSrgPartialBssidLines=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d369, d369_wrong_6g_cfg_results) is False


def test_d070_enable_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d070_raw = yaml.safe_load((cases_dir / "D070_enable_accesspoint.yaml").read_text(encoding="utf-8"))
    d070 = load_case(cases_dir / "D070_enable_accesspoint.yaml")
    d070_commands = "\n".join(str(step.get("command", "")) for step in d070["steps"])

    assert "aliases" not in d070_raw
    assert d070["id"] == "wifi-llapi-D070-enable-accesspoint"
    assert d070["source"]["row"] == 70
    assert d070["llapi_support"] == "Support"
    assert d070["bands"] == ["5g", "6g", "2.4g"]
    assert set(d070["topology"]["devices"]) == {"DUT"}
    assert d070["topology"]["links"] == []
    assert d070["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.Enable=1"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d070.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in d070.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.Enable=1" in d070.get("sta_env_setup", "")
    assert len(d070["steps"]) == 3
    assert "Enable5g=" in d070_commands
    assert "DriverBss6g=" in d070_commands
    assert "Enable24g=" in d070_commands
    assert any(
        criterion["field"] == "enable_6g.Enable6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d070["pass_criteria"]
    )
    assert any(
        criterion["field"] == "enable_24g.DriverBss24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "up"
        for criterion in d070["pass_criteria"]
    )


def test_d070_enable_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_enable_accesspoint.yaml")

    assert plugin.setup_env(d070, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d070, topology)


def test_d070_enable_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_enable_accesspoint.yaml")

    d070_results = {
        "steps": {
            "step1_enable_5g": {
                "success": True,
                "output": "Enable5g=1\nDriverBss5g=up",
                "timing": 0.01,
            },
            "step2_enable_6g": {
                "success": True,
                "output": "Enable6g=1\nDriverBss6g=up",
                "timing": 0.01,
            },
            "step3_enable_24g": {
                "success": True,
                "output": "Enable24g=1\nDriverBss24g=up",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_results) is True

    d070_wrong_6g_bss_results = {
        "steps": {
            **d070_results["steps"],
            "step2_enable_6g": {
                "success": True,
                "output": "Enable6g=1\nDriverBss6g=down",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_wrong_6g_bss_results) is False

    d070_wrong_24g_enable_results = {
        "steps": {
            **d070_results["steps"],
            "step3_enable_24g": {
                "success": True,
                "output": "Enable24g=0\nDriverBss24g=up",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_wrong_24g_enable_results) is False

    d070_wrong_5g_bss_results = {
        "steps": {
            **d070_results["steps"],
            "step1_enable_5g": {
                "success": True,
                "output": "Enable5g=1\nDriverBss5g=down",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d070, d070_wrong_5g_bss_results) is False


def test_d071_ftoverdsenable_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d071_raw = yaml.safe_load((cases_dir / "D071_ftoverdsenable.yaml").read_text(encoding="utf-8"))
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")
    d071_commands = "\n".join(str(step.get("command", "")) for step in d071["steps"])

    assert "aliases" not in d071_raw
    assert d071["id"] == "wifi-llapi-D071-ftoverdsenable-accesspoint"
    assert d071["source"]["row"] == 71
    assert d071["llapi_support"] == "Support"
    assert d071["implemented_by"] == "pWHM"
    assert d071["bands"] == ["5g", "6g", "2.4g"]
    assert set(d071["topology"]["devices"]) == {"DUT"}
    assert d071["topology"]["links"] == []
    assert d071["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.IEEE80211r.FTOverDSEnable=1"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d071.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in d071.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.IEEE80211r.MobilityDomain=4660" not in d071.get("sta_env_setup", "")
    assert "MobilityDomainCfg6g=" in d071_commands
    assert "FtOverDs24gTotalCount=" in d071_commands
    assert any(
        criterion["field"] == "cfg_set_ft_6g.FtOverDs6gOneCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d071["pass_criteria"]
    )
    assert any(
        criterion["field"] == "state_cleanup_24g.MobilityDomain24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d071["pass_criteria"]
    )


def test_d071_ftoverdsenable_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")

    assert plugin.setup_env(d071, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    plugin.teardown(d071, topology)


def test_d071_ftoverdsenable_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")

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

    d071_steps: dict[str, dict[str, Any]] = {}
    for suffix, ap_index, base in (("5g", 1, 1), ("6g", 3, 11), ("24g", 5, 21)):
        d071_steps[f"step{base}_prereq_enabled_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "Enabled", 1),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 1}_prereq_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 4660),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 2}_state_prereq_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0, 4660),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 3}_cfg_prereq_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "3412", 0, 1, 1),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 4}_set_ft_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "FTOverDSEnable", 1),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 5}_state_set_ft_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 1, 4660),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 6}_cfg_set_ft_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "3412", 1, 0, 1),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 7}_restore_ft_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "FTOverDSEnable", 0),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 8}_state_restore_ft_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0, 4660),
            "timing": 0.01,
        }
        d071_steps[f"step{base + 9}_cfg_restore_ft_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "3412", 0, 1, 1),
            "timing": 0.01,
        }

    for suffix, ap_index, base in (("5g", 1, 31), ("6g", 3, 33), ("24g", 5, 35)):
        d071_steps[f"step{base}_cleanup_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 0) + f"\nWiFi.AccessPoint.{ap_index}.IEEE80211r.Enabled=0",
            "timing": 0.01,
        }
        d071_steps[f"step{base + 1}_state_cleanup_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 0, 0, 0),
            "timing": 0.01,
        }

    d071_results = {"steps": d071_steps}
    assert plugin.evaluate(d071, d071_results) is True

    d071_wrong_6g_cfg_results = {
        "steps": {
            **d071_steps,
            "step17_cfg_set_ft_6g": {
                "success": True,
                "output": cfg_output("6g", "3412", 0, 1, 1),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d071, d071_wrong_6g_cfg_results) is False

    d071_wrong_24g_cleanup_results = {
        "steps": {
            **d071_steps,
            "step36_state_cleanup_24g": {
                "success": True,
                "output": state_output("24g", 0, 0, 4660),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d071, d071_wrong_24g_cleanup_results) is False

    d071_wrong_5g_prereq_results = {
        "steps": {
            **d071_steps,
            "step4_cfg_prereq_5g": {
                "success": True,
                "output": cfg_output("5g", "3412", 0, 0, 0),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d071, d071_wrong_5g_prereq_results) is False


def test_d072_mobilitydomain_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d072_raw = yaml.safe_load((cases_dir / "D072_mobilitydomain.yaml").read_text(encoding="utf-8"))
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")
    d072_commands = "\n".join(str(step.get("command", "")) for step in d072["steps"])

    assert "aliases" not in d072_raw
    assert d072["id"] == "wifi-llapi-D072-mobilitydomain-accesspoint"
    assert d072["source"]["row"] == 72
    assert d072["llapi_support"] == "Support"
    assert d072["implemented_by"] == "pWHM"
    assert d072["bands"] == ["5g", "6g", "2.4g"]
    assert set(d072["topology"]["devices"]) == {"DUT"}
    assert d072["topology"]["links"] == []
    assert d072["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.IEEE80211r.MobilityDomain=27476"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d072.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in d072.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.Enable=1" in d072.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d072.get("sta_env_setup", "")
    assert "MobilityDomainCfg6g=" in d072_commands
    assert "FtOverDs24gTotalCount=" in d072_commands
    assert any(
        criterion["field"] == "cfg_set_mobilitydomain_6g.MobilityDomainCfg6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "546B"
        for criterion in d072["pass_criteria"]
    )
    assert any(
        criterion["field"] == "state_cleanup_24g.MobilityDomain24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d072["pass_criteria"]
    )


def test_d072_mobilitydomain_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")

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
    assert all("IEEE80211r.Enabled=1" not in command for command in executed_commands)
    assert all("IEEE80211r.MobilityDomain=27476" not in command for command in executed_commands)
    plugin.teardown(d072, topology)


def test_d072_mobilitydomain_setter_step_keeps_original_command():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")

    commands, reason = plugin._command_resolver.resolve(
        d072,
        d072["steps"][0],
        _FakeTopology(),
    )

    assert commands == ["ubus-cli WiFi.AccessPoint.1.IEEE80211r.Enabled=1"]
    assert reason == ""


def test_d072_mobilitydomain_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")

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

    d072_steps: dict[str, dict[str, Any]] = {}
    for suffix, ap_index, base in (("5g", 1, 1), ("6g", 3, 10), ("24g", 5, 19)):
        d072_steps[f"step{base}_enable_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "Enabled", 1),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 1}_state_enabled_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 2}_set_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 27476),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 3}_state_set_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 27476),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 4}_cfg_set_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, "546B", 1, 1),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 5}_restore_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "MobilityDomain", 0),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 6}_state_restore_mobilitydomain_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1, 0),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 7}_cleanup_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, "Enabled", 0),
            "timing": 0.01,
        }
        d072_steps[f"step{base + 8}_state_cleanup_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 0, 0),
            "timing": 0.01,
        }

    d072_results = {"steps": d072_steps}
    assert plugin.evaluate(d072, d072_results) is True

    d072_wrong_6g_cfg_results = {
        "steps": {
            **d072_steps,
            "step14_cfg_set_mobilitydomain_6g": {
                "success": True,
                "output": cfg_output("6g", "6B54", 1, 1),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_wrong_6g_cfg_results) is False

    d072_wrong_24g_cleanup_results = {
        "steps": {
            **d072_steps,
            "step27_state_cleanup_24g": {
                "success": True,
                "output": state_output("24g", 0, 27476),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_wrong_24g_cleanup_results) is False

    d072_wrong_5g_enabled_results = {
        "steps": {
            **d072_steps,
            "step2_state_enabled_5g": {
                "success": True,
                "output": state_output("5g", 1, 27476),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d072, d072_wrong_5g_enabled_results) is False


def test_d075_interworkingenable_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d075_raw = yaml.safe_load((cases_dir / "D075_interworkingenable.yaml").read_text(encoding="utf-8"))
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")
    d075_commands = "\n".join(str(step.get("command", "")) for step in d075["steps"])

    assert "aliases" not in d075_raw
    assert d075["id"] == "wifi-llapi-D075-interworkingenable-accesspoint"
    assert d075["source"]["row"] == 77
    assert d075["llapi_support"] == "Support"
    assert d075["implemented_by"] == "pWHM"
    assert d075["bands"] == ["5g", "6g", "2.4g"]
    assert set(d075["topology"]["devices"]) == {"DUT"}
    assert d075["topology"]["links"] == []
    assert d075["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.IEEE80211u.InterworkingEnable=1"
    assert "ubus-cli WiFi.AccessPoint.1.Enable=1" in d075.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.Enable=1" in d075.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.Enable=1" in d075.get("sta_env_setup", "")
    assert "wl -i wl2 bss" in d075.get("sta_env_setup", "")
    assert "Interworking6gTotalCount=" in d075_commands
    assert "Interworking24gZeroCount=" in d075_commands
    assert any(
        criterion["field"] == "cfg_set_interworking_6g.Interworking6gOneCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d075["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_restore_interworking_24g.Interworking24gZeroCount"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2"
        for criterion in d075["pass_criteria"]
    )


def test_d075_interworkingenable_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")

    assert plugin.setup_env(d075, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("IEEE80211u.InterworkingEnable=" not in command for command in executed_commands)
    plugin.teardown(d075, topology)


def test_d075_interworkingenable_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")

    def state_output(suffix: str, interworking: int) -> str:
        return f"Interworking{suffix}={interworking}"

    def cfg_output(suffix: str, one_count: int, zero_count: int, total_count: int) -> str:
        return "\n".join(
            [
                f"Interworking{suffix}OneCount={one_count}",
                f"Interworking{suffix}ZeroCount={zero_count}",
                f"Interworking{suffix}TotalCount={total_count}",
            ]
        )

    def setter_output(ap_index: int, value: int) -> str:
        return (
            f"WiFi.AccessPoint.{ap_index}.IEEE80211u.\n"
            f"WiFi.AccessPoint.{ap_index}.IEEE80211u.InterworkingEnable={value}"
        )

    d075_steps: dict[str, dict[str, Any]] = {}
    for suffix, ap_index, base in (("5g", 1, 1), ("6g", 3, 9), ("24g", 5, 17)):
        d075_steps[f"step{base}_state_baseline_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 0),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 1}_cfg_baseline_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, 0, 2, 2),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 2}_set_interworking_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, 1),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 3}_state_set_interworking_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 1),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 4}_cfg_set_interworking_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, 1, 1, 2),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 5}_restore_interworking_{suffix}"] = {
            "success": True,
            "output": setter_output(ap_index, 0),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 6}_state_restore_interworking_{suffix}"] = {
            "success": True,
            "output": state_output(suffix, 0),
            "timing": 0.01,
        }
        d075_steps[f"step{base + 7}_cfg_restore_interworking_{suffix}"] = {
            "success": True,
            "output": cfg_output(suffix, 0, 2, 2),
            "timing": 0.01,
        }

    d075_results = {"steps": d075_steps}
    assert plugin.evaluate(d075, d075_results) is True

    d075_wrong_6g_cfg_results = {
        "steps": {
            **d075_steps,
            "step13_cfg_set_interworking_6g": {
                "success": True,
                "output": cfg_output("6g", 0, 2, 2),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d075, d075_wrong_6g_cfg_results) is False

    d075_wrong_24g_restore_results = {
        "steps": {
            **d075_steps,
            "step23_state_restore_interworking_24g": {
                "success": True,
                "output": state_output("24g", 1),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d075, d075_wrong_24g_restore_results) is False

    d075_wrong_5g_baseline_results = {
        "steps": {
            **d075_steps,
            "step2_cfg_baseline_5g": {
                "success": True,
                "output": cfg_output("5g", 0, 1, 1),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d075, d075_wrong_5g_baseline_results) is False


def test_d076_qosmapset_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    requested = "0,7,8,15,255,25 5,255,255,255,255,16,23,24,31,255,255"

    d076_raw = yaml.safe_load((cases_dir / "D076_qosmapset.yaml").read_text(encoding="utf-8"))
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")
    d076_commands = "\n".join(str(step.get("command", "")) for step in d076["steps"])

    assert "aliases" not in d076_raw
    assert d076["id"] == "wifi-llapi-D076-qosmapset-accesspoint"
    assert d076["source"]["row"] == 70
    assert d076["llapi_support"] == "Not Supported"
    assert d076["implemented_by"] == "pWHM"
    assert d076["bands"] == ["5g", "6g", "2.4g"]
    assert set(d076["topology"]["devices"]) == {"DUT"}
    assert d076["topology"]["links"] == []
    assert d076["hlapi_command"] == (
        f'ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet="{requested}"'
    )
    assert "ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=" in d076.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.3.IEEE80211u.QoSMapSet=" in d076.get("sta_env_setup", "")
    assert "ubus-cli WiFi.AccessPoint.5.IEEE80211u.QoSMapSet=" in d076.get("sta_env_setup", "")
    assert "RequestedQoSMapSet6g=" in d076_commands
    assert "QoSMapSetCfg24gCount=" in d076_commands
    assert any(
        criterion["field"] == "cfg_set_qosmap_6g.QoSMapSetCfg6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "255"
        for criterion in d076["pass_criteria"]
    )
    assert any(
        criterion["field"] == "cfg_restore_qosmap_24g.QoSMapSetCfg24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d076["pass_criteria"]
    )


def test_d076_qosmapset_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")

    assert plugin.setup_env(d076, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.IEEE80211u.QoSMapSet=") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.IEEE80211u.QoSMapSet=") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all(
        "0,7,8,15,255,25 5,255,255,255,255,16,23,24,31,255,255" not in command
        for command in executed_commands
    )
    plugin.teardown(d076, topology)


def test_d076_qosmapset_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")
    requested = "0,7,8,15,255,25 5,255,255,255,255,16,23,24,31,255,255"

    def state_output(suffix: str, value: str) -> str:
        return f"QoSMapSet{suffix}={value}"

    def cfg_output(suffix: str, count: int, value: str) -> str:
        return "\n".join(
            [
                f"QoSMapSetCfg{suffix}Count={count}",
                f"QoSMapSetCfg{suffix}={value}",
            ]
        )

    def set_output(suffix: str, setter_value: str = "255") -> str:
        return "\n".join(
            [
                f"RequestedQoSMapSet{suffix}={requested}",
                f"SetterQoSMapSet{suffix}={setter_value}",
            ]
        )

    def restore_output(suffix: str) -> str:
        return f"RestoreQoSMapSet{suffix}=EMPTY"

    d076_steps: dict[str, dict[str, Any]] = {}
    for suffix, band_key, base in (("5g", "5g", 1), ("6g", "6g", 9), ("24g", "24g", 17)):
        d076_steps[f"step{base}_state_baseline_{band_key}"] = {
            "success": True,
            "output": state_output(suffix, "EMPTY"),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 1}_cfg_baseline_{band_key}"] = {
            "success": True,
            "output": cfg_output(suffix, 0, "ABSENT"),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 2}_set_qosmap_{band_key}"] = {
            "success": True,
            "output": set_output(suffix),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 3}_state_set_qosmap_{band_key}"] = {
            "success": True,
            "output": state_output(suffix, "255"),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 4}_cfg_set_qosmap_{band_key}"] = {
            "success": True,
            "output": cfg_output(suffix, 1, "255"),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 5}_restore_qosmap_{band_key}"] = {
            "success": True,
            "output": restore_output(suffix),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 6}_state_restore_qosmap_{band_key}"] = {
            "success": True,
            "output": state_output(suffix, "EMPTY"),
            "timing": 0.01,
        }
        d076_steps[f"step{base + 7}_cfg_restore_qosmap_{band_key}"] = {
            "success": True,
            "output": cfg_output(suffix, 0, "ABSENT"),
            "timing": 0.01,
        }

    d076_results = {"steps": d076_steps}
    assert plugin.evaluate(d076, d076_results) is True

    d076_wrong_6g_set_results = {
        "steps": {
            **d076_steps,
            "step11_set_qosmap_6g": {
                "success": True,
                "output": set_output("6g", setter_value=requested),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d076, d076_wrong_6g_set_results) is False

    d076_wrong_24g_restore_results = {
        "steps": {
            **d076_steps,
            "step24_cfg_restore_qosmap_24g": {
                "success": True,
                "output": cfg_output("24g", 1, "255"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d076, d076_wrong_24g_restore_results) is False

    d076_wrong_5g_baseline_results = {
        "steps": {
            **d076_steps,
            "step1_state_baseline_5g": {
                "success": True,
                "output": state_output("5g", "255"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d076, d076_wrong_5g_baseline_results) is False


def test_d077_macfilteraddresslist_accesspoint_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d077_raw = yaml.safe_load((cases_dir / "D077_macfilteraddresslist.yaml").read_text(encoding="utf-8"))
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")
    d077_commands = "\n".join(str(step.get("command", "")) for step in d077["steps"])

    assert "aliases" not in d077_raw
    assert d077["id"] == "wifi-llapi-D077-macfilteraddresslist-accesspoint"
    assert d077["source"]["row"] == 77
    assert d077["llapi_support"] == "Support"
    assert d077["implemented_by"] == "pWHM"
    assert d077["bands"] == ["5g", "6g", "2.4g"]
    assert set(d077["topology"]["devices"]) == {"DUT"}
    assert d077["topology"]["links"] == []
    assert d077["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.MACFilterAddressList?"'
    assert (
        'ubus-cli "WiFi.AccessPoint.1.MACFiltering.delEntry(mac=62:2F:B8:66:BB:82)"'
        in d077.get("sta_env_setup", "")
    )
    assert (
        'ubus-cli "WiFi.AccessPoint.3.MACFiltering.delEntry(mac=FA:DD:AC:24:5A:B4)"'
        in d077.get("sta_env_setup", "")
    )
    assert (
        'ubus-cli "WiFi.AccessPoint.5.MACFiltering.delEntry(mac=FA:A0:DF:91:47:7C)"'
        in d077.get("sta_env_setup", "")
    )
    assert "RequestedMac6g=" in d077_commands
    assert "EntryMac24g=" in d077_commands
    assert any(
        criterion["field"] == "state_add_entry_6g.MACFilterAddressList6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "FA:DD:AC:24:5A:B4"
        for criterion in d077["pass_criteria"]
    )
    assert any(
        criterion["field"] == "entry_delete_24g.EntryCount24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d077["pass_criteria"]
    )


def test_d077_macfilteraddresslist_accesspoint_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")

    assert plugin.setup_env(d077, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.1.MACFiltering.delEntry(mac=62:2F:B8:66:BB:82)" 2>/dev/null || true'
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.3.MACFiltering.delEntry(mac=FA:DD:AC:24:5A:B4)" 2>/dev/null || true'
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.5.MACFiltering.delEntry(mac=FA:A0:DF:91:47:7C)" 2>/dev/null || true'
        )
        == 1
    )
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d077, topology)


def test_d077_macfilteraddresslist_accesspoint_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")

    def list_output(suffix: str, value: str) -> str:
        return f"MACFilterAddressList{suffix}={value}"

    def entry_output(suffix: str, count: int, value: str) -> str:
        return "\n".join(
            [
                f"EntryCount{suffix}={count}",
                f"EntryMac{suffix}={value}",
            ]
        )

    def add_output(suffix: str, mac: str) -> str:
        return f"RequestedMac{suffix}={mac}"

    def delete_output(suffix: str, mac: str) -> str:
        return f"DeletedMac{suffix}={mac}"

    d077_steps: dict[str, dict[str, Any]] = {}
    for suffix, band_key, mac, base in (
        ("5g", "5g", "62:2F:B8:66:BB:82", 1),
        ("6g", "6g", "FA:DD:AC:24:5A:B4", 9),
        ("24g", "24g", "FA:A0:DF:91:47:7C", 17),
    ):
        d077_steps[f"step{base}_state_baseline_{band_key}"] = {
            "success": True,
            "output": list_output(suffix, "EMPTY"),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 1}_entry_baseline_{band_key}"] = {
            "success": True,
            "output": entry_output(suffix, 0, "EMPTY"),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 2}_add_entry_{band_key}"] = {
            "success": True,
            "output": add_output(suffix, mac),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 3}_state_add_entry_{band_key}"] = {
            "success": True,
            "output": list_output(suffix, mac),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 4}_entry_add_{band_key}"] = {
            "success": True,
            "output": entry_output(suffix, 1, mac),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 5}_delete_entry_{band_key}"] = {
            "success": True,
            "output": delete_output(suffix, mac),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 6}_state_delete_entry_{band_key}"] = {
            "success": True,
            "output": list_output(suffix, "EMPTY"),
            "timing": 0.01,
        }
        d077_steps[f"step{base + 7}_entry_delete_{band_key}"] = {
            "success": True,
            "output": entry_output(suffix, 0, "EMPTY"),
            "timing": 0.01,
        }

    d077_results = {"steps": d077_steps}
    assert plugin.evaluate(d077, d077_results) is True

    d077_wrong_6g_state_results = {
        "steps": {
            **d077_steps,
            "step12_state_add_entry_6g": {
                "success": True,
                "output": list_output("6g", "EMPTY"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d077, d077_wrong_6g_state_results) is False

    d077_wrong_24g_delete_results = {
        "steps": {
            **d077_steps,
            "step24_entry_delete_24g": {
                "success": True,
                "output": entry_output("24g", 1, "FA:A0:DF:91:47:7C"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d077, d077_wrong_24g_delete_results) is False

    d077_wrong_5g_baseline_results = {
        "steps": {
            **d077_steps,
            "step2_entry_baseline_5g": {
                "success": True,
                "output": entry_output("5g", 1, "62:2F:B8:66:BB:82"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d077, d077_wrong_5g_baseline_results) is False


def test_d078_entry_accesspoint_macfiltering_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d078_raw = yaml.safe_load((cases_dir / "D078_entry.yaml").read_text(encoding="utf-8"))
    d078 = load_case(cases_dir / "D078_entry.yaml")
    d078_commands = "\n".join(str(step.get("command", "")) for step in d078["steps"])

    assert "aliases" not in d078_raw
    assert d078["id"] == "wifi-llapi-D078-entry-accesspoint-macfiltering"
    assert d078["source"]["row"] == 78
    assert d078["llapi_support"] == "Support"
    assert d078["implemented_by"] == "pWHM"
    assert d078["bands"] == ["5g", "6g", "2.4g"]
    assert set(d078["topology"]["devices"]) == {"DUT"}
    assert d078["topology"]["links"] == []
    assert d078["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.MACFiltering.Entry.?"'
    assert (
        'ubus-cli "WiFi.AccessPoint.1.MACFiltering.delEntry(mac=62:2F:B8:66:BB:82)"'
        in d078.get("sta_env_setup", "")
    )
    assert (
        'ubus-cli "WiFi.AccessPoint.3.MACFiltering.delEntry(mac=FA:DD:AC:24:5A:B4)"'
        in d078.get("sta_env_setup", "")
    )
    assert (
        'ubus-cli "WiFi.AccessPoint.5.MACFiltering.delEntry(mac=FA:A0:DF:91:47:7C)"'
        in d078.get("sta_env_setup", "")
    )
    assert "EntryAlias24g=" in d078_commands
    assert any(
        criterion["field"] == "entry_add_6g.EntryMac6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "FA:DD:AC:24:5A:B4"
        for criterion in d078["pass_criteria"]
    )
    assert any(
        criterion["field"] == "entry_delete_24g.EntryAlias24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "EMPTY"
        for criterion in d078["pass_criteria"]
    )


def test_d078_entry_accesspoint_macfiltering_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d078 = load_case(cases_dir / "D078_entry.yaml")

    assert plugin.setup_env(d078, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.1.MACFiltering.delEntry(mac=62:2F:B8:66:BB:82)" 2>/dev/null || true'
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.3.MACFiltering.delEntry(mac=FA:DD:AC:24:5A:B4)" 2>/dev/null || true'
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.5.MACFiltering.delEntry(mac=FA:A0:DF:91:47:7C)" 2>/dev/null || true'
        )
        == 1
    )
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d078, topology)


def test_d078_entry_accesspoint_macfiltering_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d078 = load_case(cases_dir / "D078_entry.yaml")

    def entry_output(suffix: str, count: int, alias: str, value: str) -> str:
        return "\n".join(
            [
                f"EntryCount{suffix}={count}",
                f"EntryAlias{suffix}={alias}",
                f"EntryMac{suffix}={value}",
            ]
        )

    def add_output(suffix: str, mac: str) -> str:
        return f"RequestedMac{suffix}={mac}"

    def delete_output(suffix: str, mac: str) -> str:
        return f"DeletedMac{suffix}={mac}"

    d078_steps: dict[str, dict[str, Any]] = {}
    for suffix, band_key, mac, alias, base in (
        ("5g", "5g", "62:2F:B8:66:BB:82", "cpe-Entry-5", 1),
        ("6g", "6g", "FA:DD:AC:24:5A:B4", "cpe-Entry-4", 6),
        ("24g", "24g", "FA:A0:DF:91:47:7C", "cpe-Entry-4", 11),
    ):
        d078_steps[f"step{base}_entry_baseline_{band_key}"] = {
            "success": True,
            "output": entry_output(suffix, 0, "EMPTY", "EMPTY"),
            "timing": 0.01,
        }
        d078_steps[f"step{base + 1}_add_entry_{band_key}"] = {
            "success": True,
            "output": add_output(suffix, mac),
            "timing": 0.01,
        }
        d078_steps[f"step{base + 2}_entry_add_{band_key}"] = {
            "success": True,
            "output": entry_output(suffix, 1, alias, mac),
            "timing": 0.01,
        }
        d078_steps[f"step{base + 3}_delete_entry_{band_key}"] = {
            "success": True,
            "output": delete_output(suffix, mac),
            "timing": 0.01,
        }
        d078_steps[f"step{base + 4}_entry_delete_{band_key}"] = {
            "success": True,
            "output": entry_output(suffix, 0, "EMPTY", "EMPTY"),
            "timing": 0.01,
        }

    d078_results = {"steps": d078_steps}
    assert plugin.evaluate(d078, d078_results) is True

    d078_wrong_6g_add_results = {
        "steps": {
            **d078_steps,
            "step8_entry_add_6g": {
                "success": True,
                "output": entry_output("6g", 0, "EMPTY", "EMPTY"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d078, d078_wrong_6g_add_results) is False

    d078_wrong_24g_alias_results = {
        "steps": {
            **d078_steps,
            "step13_entry_add_24g": {
                "success": True,
                "output": entry_output("24g", 1, "EMPTY", "FA:A0:DF:91:47:7C"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d078, d078_wrong_24g_alias_results) is False

    d078_wrong_5g_delete_results = {
        "steps": {
            **d078_steps,
            "step5_entry_delete_5g": {
                "success": True,
                "output": entry_output("5g", 1, "cpe-Entry-5", "62:2F:B8:66:BB:82"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d078, d078_wrong_5g_delete_results) is False


def test_d079_mode_accesspoint_macfiltering_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d079_raw = yaml.safe_load(
        (cases_dir / "D079_mode_accesspoint_macfiltering.yaml").read_text(encoding="utf-8")
    )
    d079 = load_case(cases_dir / "D079_mode_accesspoint_macfiltering.yaml")
    d079_commands = "\n".join(str(step.get("command", "")) for step in d079["steps"])

    assert "aliases" not in d079_raw
    assert d079["id"] == "wifi-llapi-D079-mode-accesspoint-macfiltering"
    assert d079["source"]["row"] == 79
    assert d079["llapi_support"] == "Support"
    assert d079["implemented_by"] == "pWHM"
    assert d079["bands"] == ["5g", "6g", "2.4g"]
    assert set(d079["topology"]["devices"]) == {"DUT"}
    assert d079["topology"]["links"] == []
    assert d079["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.MACFiltering.Mode=Off"
    assert "killall wpa_supplicant" not in d079.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.1.MACFiltering.Mode=WhiteList' in d079.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.3.MACFiltering.Mode=BlackList' in d079.get("sta_env_setup", "")
    assert 'WiFi.AccessPoint.5.MACFiltering.Mode=BlackList' in d079.get("sta_env_setup", "")
    assert "SetOffStatus24g=" in d079_commands
    assert any(
        criterion["field"] == "set_off_5g.SetOffStatus5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "invalid_value"
        for criterion in d079["pass_criteria"]
    )
    assert any(
        criterion["field"] == "mode_after_set_6g.AfterAclState6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "deny"
        for criterion in d079["pass_criteria"]
    )


def test_d079_mode_accesspoint_macfiltering_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d079 = load_case(cases_dir / "D079_mode_accesspoint_macfiltering.yaml")

    assert plugin.setup_env(d079, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.1.MACFiltering.delEntry(mac=62:2F:B8:66:BB:82)" 2>/dev/null || true'
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.3.MACFiltering.delEntry(mac=FA:DD:AC:24:5A:B4)" 2>/dev/null || true'
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli "WiFi.AccessPoint.5.MACFiltering.delEntry(mac=FA:A0:DF:91:47:7C)" 2>/dev/null || true'
        )
        == 1
    )
    assert executed_commands.count('ubus-cli "WiFi.AccessPoint.1.MACFiltering.addEntry(mac=62:2F:B8:66:BB:82)"') == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.MACFiltering.Mode=WhiteList") == 1
    assert executed_commands.count('ubus-cli "WiFi.AccessPoint.3.MACFiltering.addEntry(mac=FA:DD:AC:24:5A:B4)"') == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.MACFiltering.Mode=BlackList") == 1
    assert executed_commands.count('ubus-cli "WiFi.AccessPoint.5.MACFiltering.addEntry(mac=FA:A0:DF:91:47:7C)"') == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.MACFiltering.Mode=BlackList") == 1
    assert executed_commands.count("sleep 2") == 1
    assert all(not command.startswith("wl -i wl") for command in executed_commands)
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d079, topology)


def test_d079_mode_accesspoint_macfiltering_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d079 = load_case(cases_dir / "D079_mode_accesspoint_macfiltering.yaml")

    def mode_output(prefix: str, mode: str, macaddr_acl: str, acl_state: str, phase: str) -> str:
        return "\n".join(
            [
                f"{phase}Mode{prefix}={mode}",
                f"{phase}MacaddrAcl{prefix}={macaddr_acl}",
                f"{phase}AclState{prefix}={acl_state}",
            ]
        )

    def set_output(prefix: str, status: str) -> str:
        if status == "invalid_value":
            return "\n".join(
                [
                    "ERROR: set WiFi.AccessPoint.X.MACFiltering.Mode failed (10 - invalid value)",
                    f"SetOffStatus{prefix}=invalid_value",
                ]
            )
        return f'SetOffStatus{prefix}=accepted'

    d079_results = {
        "steps": {
            "step1_mode_baseline_5g": {
                "success": True,
                "output": mode_output("5g", "WhiteList", "1", "accept", "Baseline"),
                "timing": 0.01,
            },
            "step2_set_off_5g": {
                "success": True,
                "output": set_output("5g", "invalid_value"),
                "timing": 0.01,
            },
            "step3_mode_after_set_5g": {
                "success": True,
                "output": mode_output("5g", "WhiteList", "1", "accept", "After"),
                "timing": 0.01,
            },
            "step4_mode_baseline_6g": {
                "success": True,
                "output": mode_output("6g", "BlackList", "0", "deny", "Baseline"),
                "timing": 0.01,
            },
            "step5_set_off_6g": {
                "success": True,
                "output": set_output("6g", "invalid_value"),
                "timing": 0.01,
            },
            "step6_mode_after_set_6g": {
                "success": True,
                "output": mode_output("6g", "BlackList", "0", "deny", "After"),
                "timing": 0.01,
            },
            "step7_mode_baseline_24g": {
                "success": True,
                "output": mode_output("24g", "BlackList", "0", "deny", "Baseline"),
                "timing": 0.01,
            },
            "step8_set_off_24g": {
                "success": True,
                "output": set_output("24g", "invalid_value"),
                "timing": 0.01,
            },
            "step9_mode_after_set_24g": {
                "success": True,
                "output": mode_output("24g", "BlackList", "0", "deny", "After"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d079, d079_results) is True

    d079_wrong_5g_after_results = {
        "steps": {
            **d079_results["steps"],
            "step3_mode_after_set_5g": {
                "success": True,
                "output": mode_output("5g", "Off", "ABSENT", "absent", "After"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d079, d079_wrong_5g_after_results) is False

    d079_wrong_6g_setter_results = {
        "steps": {
            **d079_results["steps"],
            "step5_set_off_6g": {
                "success": True,
                "output": set_output("6g", "accepted"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d079, d079_wrong_6g_setter_results) is False

    d079_wrong_24g_acl_results = {
        "steps": {
            **d079_results["steps"],
            "step9_mode_after_set_24g": {
                "success": True,
                "output": mode_output("24g", "BlackList", "1", "accept", "After"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d079, d079_wrong_24g_acl_results) is False


def test_d080_maxassociateddevices_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d080_raw = yaml.safe_load((cases_dir / "D080_maxassociateddevices.yaml").read_text(encoding="utf-8"))
    d080 = load_case(cases_dir / "D080_maxassociateddevices.yaml")
    d080_commands = "\n".join(str(step.get("command", "")) for step in d080["steps"])

    assert "aliases" not in d080_raw
    assert d080["id"] == "wifi-llapi-D080-maxassociateddevices"
    assert d080["source"]["row"] == 80
    assert d080["llapi_support"] == "Support"
    assert d080["implemented_by"] == "Vendor Module"
    assert d080["bands"] == ["5g", "6g", "2.4g"]
    assert set(d080["topology"]["devices"]) == {"DUT"}
    assert d080["topology"]["links"] == []
    assert d080["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.MaxAssociatedDevices=32"
    assert "killall wpa_supplicant" not in d080.get("sta_env_setup", "")
    assert "SetterEchoMax24g=" in d080_commands
    assert "AfterTempHostapdMax24g=" in d080_commands
    assert any(
        criterion["field"] == "max_after_temp_5g.AfterTempHostapdMax5g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "max_after_temp_5g.AfterTempGetterMax5g"
        for criterion in d080["pass_criteria"]
    )
    assert any(
        criterion["field"] == "set_temp_6g.SetterEchoMax6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "31"
        for criterion in d080["pass_criteria"]
    )
    assert any(
        criterion["field"] == "max_after_restore_24g.AfterRestoreHostapdCount24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2"
        for criterion in d080["pass_criteria"]
    )


def test_d080_maxassociateddevices_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d080 = load_case(cases_dir / "D080_maxassociateddevices.yaml")

    assert plugin.setup_env(d080, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d080, topology)


def test_d080_maxassociateddevices_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d080 = load_case(cases_dir / "D080_maxassociateddevices.yaml")

    def baseline_output(prefix: str) -> str:
        return "\n".join(
            [
                f"BaselineGetterMax{prefix}=32",
                f"BaselineHostapdMax{prefix}=32",
                f"BaselineHostapdCount{prefix}=2",
            ]
        )

    def request_output(prefix: str, phase: str) -> str:
        if phase == "temp":
            return "\n".join(
                [
                    f"RequestedTempMax{prefix}=31",
                    f"SetterEchoMax{prefix}=31",
                ]
            )
        return "\n".join(
            [
                f"RestoreMax{prefix}=32",
                f"RestoreEchoMax{prefix}=32",
            ]
        )

    def after_temp_output(prefix: str, getter: str, hostapd: str, count: str) -> str:
        return "\n".join(
            [
                f"AfterTempGetterMax{prefix}={getter}",
                f"AfterTempHostapdMax{prefix}={hostapd}",
                f"AfterTempHostapdCount{prefix}={count}",
            ]
        )

    def after_restore_output(prefix: str, getter: str, hostapd: str, count: str) -> str:
        return "\n".join(
            [
                f"AfterRestoreGetterMax{prefix}={getter}",
                f"AfterRestoreHostapdMax{prefix}={hostapd}",
                f"AfterRestoreHostapdCount{prefix}={count}",
            ]
        )

    d080_results = {
        "steps": {
            "step1_max_baseline_5g": {"success": True, "output": baseline_output("5g"), "timing": 0.01},
            "step2_set_temp_5g": {"success": True, "output": request_output("5g", "temp"), "timing": 0.01},
            "step3_max_after_temp_5g": {
                "success": True,
                "output": after_temp_output("5g", "31", "31", "2"),
                "timing": 0.01,
            },
            "step4_restore_5g": {"success": True, "output": request_output("5g", "restore"), "timing": 0.01},
            "step5_max_after_restore_5g": {
                "success": True,
                "output": after_restore_output("5g", "32", "32", "2"),
                "timing": 0.01,
            },
            "step6_max_baseline_6g": {"success": True, "output": baseline_output("6g"), "timing": 0.01},
            "step7_set_temp_6g": {"success": True, "output": request_output("6g", "temp"), "timing": 0.01},
            "step8_max_after_temp_6g": {
                "success": True,
                "output": after_temp_output("6g", "31", "31", "2"),
                "timing": 0.01,
            },
            "step9_restore_6g": {"success": True, "output": request_output("6g", "restore"), "timing": 0.01},
            "step10_max_after_restore_6g": {
                "success": True,
                "output": after_restore_output("6g", "32", "32", "2"),
                "timing": 0.01,
            },
            "step11_max_baseline_24g": {"success": True, "output": baseline_output("24g"), "timing": 0.01},
            "step12_set_temp_24g": {"success": True, "output": request_output("24g", "temp"), "timing": 0.01},
            "step13_max_after_temp_24g": {
                "success": True,
                "output": after_temp_output("24g", "31", "31", "2"),
                "timing": 0.01,
            },
            "step14_restore_24g": {"success": True, "output": request_output("24g", "restore"), "timing": 0.01},
            "step15_max_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "32", "32", "2"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d080, d080_results) is True

    d080_wrong_6g_temp_getter = {
        "steps": {
            **d080_results["steps"],
            "step8_max_after_temp_6g": {
                "success": True,
                "output": after_temp_output("6g", "32", "32", "2"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d080, d080_wrong_6g_temp_getter) is False

    d080_wrong_5g_hostapd_stale = {
        "steps": {
            **d080_results["steps"],
            "step3_max_after_temp_5g": {
                "success": True,
                "output": after_temp_output("5g", "31", "32", "2"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d080, d080_wrong_5g_hostapd_stale) is False

    d080_missing_24g_setter_echo = {
        "steps": {
            **d080_results["steps"],
            "step12_set_temp_24g": {
                "success": True,
                "output": "RequestedTempMax24g=31\nSetterEchoMax24g=EMPTY",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d080, d080_missing_24g_setter_echo) is False

    d080_wrong_24g_restore = {
        "steps": {
            **d080_results["steps"],
            "step15_max_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "31", "32", "2"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d080, d080_wrong_24g_restore) is False


def test_d081_mboenable_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d081_raw = yaml.safe_load((cases_dir / "D081_mboenable.yaml").read_text(encoding="utf-8"))
    d081 = load_case(cases_dir / "D081_mboenable.yaml")
    d081_commands = "\n".join(str(step.get("command", "")) for step in d081["steps"])

    assert "aliases" not in d081_raw
    assert d081["id"] == "wifi-llapi-D081-mboenable"
    assert d081["source"]["row"] == 81
    assert d081["llapi_support"] == "Support"
    assert d081["implemented_by"] == "Vendor Module"
    assert d081["bands"] == ["5g", "6g", "2.4g"]
    assert set(d081["topology"]["devices"]) == {"DUT"}
    assert d081["topology"]["links"] == []
    assert d081["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.MBOEnable=0"
    assert "killall wpa_supplicant" not in d081.get("sta_env_setup", "")
    assert "AfterEnableDriverMbo24g=" in d081_commands
    assert "wl -i wl0 mbo ap_enable" in d081_commands
    assert "sleep 5;" in d081_commands
    assert any(
        criterion["field"] == "mbo_after_enable_5g.AfterEnableDriverMbo5g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "mbo_after_enable_5g.AfterEnableGetterMbo5g"
        for criterion in d081["pass_criteria"]
    )
    assert any(
        criterion["field"] == "mbo_after_restore_24g.AfterRestoreDriverMbo24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d081["pass_criteria"]
    )


def test_d081_mboenable_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d081 = load_case(cases_dir / "D081_mboenable.yaml")

    assert plugin.setup_env(d081, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.MBOEnable=0") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.MBOEnable=0") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.MBOEnable=0") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d081, topology)


def test_d081_mboenable_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d081 = load_case(cases_dir / "D081_mboenable.yaml")

    def baseline_output(prefix: str) -> str:
        return "\n".join(
            [
                f"BaselineGetterMbo{prefix}=0",
                f"BaselineDriverMbo{prefix}=0",
            ]
        )

    def enable_output(prefix: str) -> str:
        return f"RequestedEnableMbo{prefix}=1"

    def restore_output(prefix: str) -> str:
        return f"RestoreMbo{prefix}=0"

    def after_enable_output(prefix: str, getter: str, driver: str) -> str:
        return "\n".join(
            [
                f"AfterEnableGetterMbo{prefix}={getter}",
                f"AfterEnableDriverMbo{prefix}={driver}",
            ]
        )

    def after_restore_output(prefix: str, getter: str, driver: str) -> str:
        return "\n".join(
            [
                f"AfterRestoreGetterMbo{prefix}={getter}",
                f"AfterRestoreDriverMbo{prefix}={driver}",
            ]
        )

    d081_results = {
        "steps": {
            "step1_mbo_baseline_5g": {"success": True, "output": baseline_output("5g"), "timing": 0.01},
            "step2_mbo_enable_5g": {"success": True, "output": enable_output("5g"), "timing": 0.01},
            "step3_mbo_after_enable_5g": {
                "success": True,
                "output": after_enable_output("5g", "1", "1"),
                "timing": 0.01,
            },
            "step4_mbo_restore_5g": {"success": True, "output": restore_output("5g"), "timing": 0.01},
            "step5_mbo_after_restore_5g": {
                "success": True,
                "output": after_restore_output("5g", "0", "0"),
                "timing": 0.01,
            },
            "step6_mbo_baseline_6g": {"success": True, "output": baseline_output("6g"), "timing": 0.01},
            "step7_mbo_enable_6g": {"success": True, "output": enable_output("6g"), "timing": 0.01},
            "step8_mbo_after_enable_6g": {
                "success": True,
                "output": after_enable_output("6g", "1", "1"),
                "timing": 0.01,
            },
            "step9_mbo_restore_6g": {"success": True, "output": restore_output("6g"), "timing": 0.01},
            "step10_mbo_after_restore_6g": {
                "success": True,
                "output": after_restore_output("6g", "0", "0"),
                "timing": 0.01,
            },
            "step11_mbo_baseline_24g": {"success": True, "output": baseline_output("24g"), "timing": 0.01},
            "step12_mbo_enable_24g": {"success": True, "output": enable_output("24g"), "timing": 0.01},
            "step13_mbo_after_enable_24g": {
                "success": True,
                "output": after_enable_output("24g", "1", "1"),
                "timing": 0.01,
            },
            "step14_mbo_restore_24g": {"success": True, "output": restore_output("24g"), "timing": 0.01},
            "step15_mbo_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "0", "0"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d081, d081_results) is True

    d081_wrong_6g_enable_getter = {
        "steps": {
            **d081_results["steps"],
            "step8_mbo_after_enable_6g": {
                "success": True,
                "output": after_enable_output("6g", "0", "1"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d081, d081_wrong_6g_enable_getter) is False

    d081_wrong_5g_driver_mismatch = {
        "steps": {
            **d081_results["steps"],
            "step3_mbo_after_enable_5g": {
                "success": True,
                "output": after_enable_output("5g", "1", "0"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d081, d081_wrong_5g_driver_mismatch) is False

    d081_wrong_24g_restore = {
        "steps": {
            **d081_results["steps"],
            "step15_mbo_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "1", "0"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d081, d081_wrong_24g_restore) is False


def test_d082_multiaptype_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d082_raw = yaml.safe_load((cases_dir / "D082_multiaptype.yaml").read_text(encoding="utf-8"))
    d082 = load_case(cases_dir / "D082_multiaptype.yaml")
    d082_commands = "\n".join(str(step.get("command", "")) for step in d082["steps"])

    assert "aliases" not in d082_raw
    assert d082["id"] == "wifi-llapi-D082-multiaptype"
    assert d082["source"]["row"] == 82
    assert d082["llapi_support"] == "Support"
    assert d082["implemented_by"] == "Vendor Module"
    assert d082["bands"] == ["5g", "6g", "2.4g"]
    assert set(d082["topology"]["devices"]) == {"DUT"}
    assert d082["topology"]["links"] == []
    assert d082["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.MultiAPType=FronthaulBSS"
    assert "killall wpa_supplicant" not in d082.get("sta_env_setup", "")
    assert "AfterSetDriverMap24g=" in d082_commands
    assert "MultiAPType=FronthaulBSS" in d082_commands
    assert "WiFi.AccessPoint.2.MultiAPType=FronthaulBSS" in d082_commands
    assert "WiFi.AccessPoint.4.MultiAPType=FronthaulBSS" in d082_commands
    assert "WiFi.AccessPoint.6.MultiAPType=FronthaulBSS" in d082_commands
    assert "MultiAPType=\"FronthaulBSS,BackhaulBSS\"" in d082_commands
    assert any(
        criterion["field"] == "multiap_after_set_5g.AfterSetHostapdFronthaulCount5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2"
        for criterion in d082["pass_criteria"]
    )
    assert any(
        criterion["field"] == "multiap_after_restore_24g.AfterRestoreDriverMap24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0x3: Fronthaul-BSS Backhaul-BSS"
        for criterion in d082["pass_criteria"]
    )
    assert any(
        criterion["field"] == "multiap_after_set_24g.AfterSetDriverMap24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0x1: Fronthaul-BSS"
        for criterion in d082["pass_criteria"]
    )


def test_d082_multiaptype_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d082 = load_case(cases_dir / "D082_multiaptype.yaml")

    assert plugin.setup_env(d082, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.2.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.4.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.6.Enable=1") == 1
    assert executed_commands.count("ubus-cli 'WiFi.AccessPoint.1.MultiAPType=\"FronthaulBSS,BackhaulBSS\"'") == 1
    assert executed_commands.count("ubus-cli 'WiFi.AccessPoint.2.MultiAPType=\"FronthaulBSS,BackhaulBSS\"'") == 1
    assert executed_commands.count("ubus-cli 'WiFi.AccessPoint.3.MultiAPType=\"FronthaulBSS,BackhaulBSS\"'") == 1
    assert executed_commands.count("ubus-cli 'WiFi.AccessPoint.4.MultiAPType=\"FronthaulBSS,BackhaulBSS\"'") == 1
    assert executed_commands.count("ubus-cli 'WiFi.AccessPoint.5.MultiAPType=\"FronthaulBSS,BackhaulBSS\"'") == 1
    assert executed_commands.count("ubus-cli 'WiFi.AccessPoint.6.MultiAPType=\"FronthaulBSS,BackhaulBSS\"'") == 1
    assert executed_commands.count("sleep 10") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d082, topology)


def test_d082_multiaptype_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d082 = load_case(cases_dir / "D082_multiaptype.yaml")

    def baseline_output(prefix: str) -> str:
        return "\n".join(
            [
                f"BaselineGetterMultiAp{prefix}=FronthaulBSS,BackhaulBSS",
                f"BaselineHostapdFronthaulCount{prefix}=0",
                f"BaselineHostapdBothCount{prefix}=2",
                f"BaselineHostapdTotalCount{prefix}=2",
                f"BaselineDriverMap{prefix}=0x3: Fronthaul-BSS Backhaul-BSS",
            ]
        )

    def set_output(prefix: str) -> str:
        return f"RequestedMultiApType{prefix}=FronthaulBSS"

    def restore_output(prefix: str) -> str:
        return f"RestoreMultiApType{prefix}=FronthaulBSS,BackhaulBSS"

    def after_set_output(prefix: str, getter: str, fronthaul_count: str, both_count: str, total: str, driver: str) -> str:
        return "\n".join(
            [
                f"AfterSetGetterMultiAp{prefix}={getter}",
                f"AfterSetHostapdFronthaulCount{prefix}={fronthaul_count}",
                f"AfterSetHostapdBothCount{prefix}={both_count}",
                f"AfterSetHostapdTotalCount{prefix}={total}",
                f"AfterSetDriverMap{prefix}={driver}",
            ]
        )

    def after_restore_output(prefix: str, getter: str, fronthaul_count: str, both_count: str, total: str, driver: str) -> str:
        return "\n".join(
            [
                f"AfterRestoreGetterMultiAp{prefix}={getter}",
                f"AfterRestoreHostapdFronthaulCount{prefix}={fronthaul_count}",
                f"AfterRestoreHostapdBothCount{prefix}={both_count}",
                f"AfterRestoreHostapdTotalCount{prefix}={total}",
                f"AfterRestoreDriverMap{prefix}={driver}",
            ]
        )

    d082_results = {
        "steps": {
            "step1_multiap_baseline_5g": {"success": True, "output": baseline_output("5g"), "timing": 0.01},
            "step2_multiap_set_fronthaul_5g": {"success": True, "output": set_output("5g"), "timing": 0.01},
            "step3_multiap_after_set_5g": {
                "success": True,
                "output": after_set_output("5g", "FronthaulBSS", "2", "0", "2", "0x1: Fronthaul-BSS"),
                "timing": 0.01,
            },
            "step4_multiap_restore_5g": {"success": True, "output": restore_output("5g"), "timing": 0.01},
            "step5_multiap_after_restore_5g": {
                "success": True,
                "output": after_restore_output("5g", "FronthaulBSS,BackhaulBSS", "0", "2", "2", "0x3: Fronthaul-BSS Backhaul-BSS"),
                "timing": 0.01,
            },
            "step6_multiap_baseline_6g": {"success": True, "output": baseline_output("6g"), "timing": 0.01},
            "step7_multiap_set_fronthaul_6g": {"success": True, "output": set_output("6g"), "timing": 0.01},
            "step8_multiap_after_set_6g": {
                "success": True,
                "output": after_set_output("6g", "FronthaulBSS", "2", "0", "2", "0x1: Fronthaul-BSS"),
                "timing": 0.01,
            },
            "step9_multiap_restore_6g": {"success": True, "output": restore_output("6g"), "timing": 0.01},
            "step10_multiap_after_restore_6g": {
                "success": True,
                "output": after_restore_output("6g", "FronthaulBSS,BackhaulBSS", "0", "2", "2", "0x3: Fronthaul-BSS Backhaul-BSS"),
                "timing": 0.01,
            },
            "step11_multiap_baseline_24g": {"success": True, "output": baseline_output("24g"), "timing": 0.01},
            "step12_multiap_set_fronthaul_24g": {"success": True, "output": set_output("24g"), "timing": 0.01},
            "step13_multiap_after_set_24g": {
                "success": True,
                "output": after_set_output("24g", "FronthaulBSS", "2", "0", "2", "0x1: Fronthaul-BSS"),
                "timing": 0.01,
            },
            "step14_multiap_restore_24g": {"success": True, "output": restore_output("24g"), "timing": 0.01},
            "step15_multiap_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "FronthaulBSS,BackhaulBSS", "0", "2", "2", "0x3: Fronthaul-BSS Backhaul-BSS"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d082, d082_results) is True

    d082_wrong_6g_hostapd_stale_dual_role = {
        "steps": {
            **d082_results["steps"],
            "step8_multiap_after_set_6g": {
                "success": True,
                "output": after_set_output("6g", "FronthaulBSS", "1", "1", "2", "0x1: Fronthaul-BSS"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d082, d082_wrong_6g_hostapd_stale_dual_role) is False

    d082_wrong_5g_driver = {
        "steps": {
            **d082_results["steps"],
            "step3_multiap_after_set_5g": {
                "success": True,
                "output": after_set_output("5g", "FronthaulBSS", "2", "0", "2", "0x3: Fronthaul-BSS Backhaul-BSS"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d082, d082_wrong_5g_driver) is False

    d082_wrong_24g_restore = {
        "steps": {
            **d082_results["steps"],
            "step15_multiap_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "FronthaulBSS", "0", "2", "2", "0x3: Fronthaul-BSS Backhaul-BSS"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d082, d082_wrong_24g_restore) is False


def test_d083_neighbour_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d083_raw = yaml.safe_load((cases_dir / "D083_neighbour.yaml").read_text(encoding="utf-8"))
    d083 = load_case(cases_dir / "D083_neighbour.yaml")
    d083_commands = "\n".join(str(step.get("command", "")) for step in d083["steps"])

    assert "aliases" not in d083_raw
    assert d083["id"] == "wifi-llapi-D083-neighbour"
    assert d083["source"]["row"] == 83
    assert d083["llapi_support"] == "Support"
    assert d083["implemented_by"] == "pWHM"
    assert d083["bands"] == ["5g", "6g", "2.4g"]
    assert set(d083["topology"]["devices"]) == {"DUT"}
    assert d083["topology"]["links"] == []
    assert d083["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.Neighbour"
    assert "killall wpa_supplicant" not in d083.get("sta_env_setup", "")
    assert 'setNeighbourAP(BSSID=11:22:33:44:55:77,Channel=1)' in d083_commands
    assert 'delNeighbourAP(BSSID=11:22:33:44:55:88)' in d083_commands
    assert "AfterDeleteBssid24g=ABSENT" in d083_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddChannel6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "1"
        for criterion in d083["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteBssidCount5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d083["pass_criteria"]
    )


def test_d083_neighbour_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d083 = load_case(cases_dir / "D083_neighbour.yaml")

    assert plugin.setup_env(d083, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d083, topology)


def test_d083_neighbour_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d083 = load_case(cases_dir / "D083_neighbour.yaml")

    def baseline_output(prefix: str) -> str:
        return "\n".join(
            [
                f"BaselineBssidCount{prefix}=0",
                f"BaselineChannelCount{prefix}=0",
                f"BaselineBssid{prefix}=ABSENT",
                f"BaselineChannel{prefix}=ABSENT",
            ]
        )

    def add_output(prefix: str, bssid: str, channel: str) -> str:
        return "\n".join([f"RequestedBssid{prefix}={bssid}", f"RequestedChannel{prefix}={channel}"])

    def after_add_output(prefix: str, bssid: str, channel: str) -> str:
        return "\n".join(
            [
                f"AfterAddBssidCount{prefix}=1",
                f"AfterAddChannelCount{prefix}=1",
                f"AfterAddBssid{prefix}={bssid}",
                f"AfterAddChannel{prefix}={channel}",
            ]
        )

    def delete_output(prefix: str, bssid: str) -> str:
        return f"DeleteBssid{prefix}={bssid}"

    def after_delete_output(prefix: str) -> str:
        return "\n".join(
            [
                f"AfterDeleteBssidCount{prefix}=0",
                f"AfterDeleteChannelCount{prefix}=0",
                f"AfterDeleteBssid{prefix}=ABSENT",
                f"AfterDeleteChannel{prefix}=ABSENT",
            ]
        )

    d083_results = {
        "steps": {
            "step1_neighbour_baseline_5g": {"success": True, "output": baseline_output("5g"), "timing": 0.01},
            "step2_neighbour_add_5g": {
                "success": True,
                "output": add_output("5g", "11:22:33:44:55:66", "36"),
                "timing": 0.01,
            },
            "step3_neighbour_after_add_5g": {
                "success": True,
                "output": after_add_output("5g", "11:22:33:44:55:66", "36"),
                "timing": 0.01,
            },
            "step4_neighbour_delete_5g": {
                "success": True,
                "output": delete_output("5g", "11:22:33:44:55:66"),
                "timing": 0.01,
            },
            "step5_neighbour_after_delete_5g": {
                "success": True,
                "output": after_delete_output("5g"),
                "timing": 0.01,
            },
            "step6_neighbour_baseline_6g": {"success": True, "output": baseline_output("6g"), "timing": 0.01},
            "step7_neighbour_add_6g": {
                "success": True,
                "output": add_output("6g", "11:22:33:44:55:77", "1"),
                "timing": 0.01,
            },
            "step8_neighbour_after_add_6g": {
                "success": True,
                "output": after_add_output("6g", "11:22:33:44:55:77", "1"),
                "timing": 0.01,
            },
            "step9_neighbour_delete_6g": {
                "success": True,
                "output": delete_output("6g", "11:22:33:44:55:77"),
                "timing": 0.01,
            },
            "step10_neighbour_after_delete_6g": {
                "success": True,
                "output": after_delete_output("6g"),
                "timing": 0.01,
            },
            "step11_neighbour_baseline_24g": {"success": True, "output": baseline_output("24g"), "timing": 0.01},
            "step12_neighbour_add_24g": {
                "success": True,
                "output": add_output("24g", "11:22:33:44:55:88", "11"),
                "timing": 0.01,
            },
            "step13_neighbour_after_add_24g": {
                "success": True,
                "output": after_add_output("24g", "11:22:33:44:55:88", "11"),
                "timing": 0.01,
            },
            "step14_neighbour_delete_24g": {
                "success": True,
                "output": delete_output("24g", "11:22:33:44:55:88"),
                "timing": 0.01,
            },
            "step15_neighbour_after_delete_24g": {
                "success": True,
                "output": after_delete_output("24g"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d083, d083_results) is True

    d083_wrong_5g_baseline = {
        "steps": {
            **d083_results["steps"],
            "step1_neighbour_baseline_5g": {
                "success": True,
                "output": "\n".join(
                    [
                        "BaselineBssidCount5g=1",
                        "BaselineChannelCount5g=1",
                        "BaselineBssid5g=11:22:33:44:55:66",
                        "BaselineChannel5g=36",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d083, d083_wrong_5g_baseline) is False

    d083_wrong_6g_channel = {
        "steps": {
            **d083_results["steps"],
            "step8_neighbour_after_add_6g": {
                "success": True,
                "output": after_add_output("6g", "11:22:33:44:55:77", "5"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d083, d083_wrong_6g_channel) is False

    d083_wrong_24g_delete = {
        "steps": {
            **d083_results["steps"],
            "step15_neighbour_after_delete_24g": {
                "success": True,
                "output": "\n".join(
                    [
                        "AfterDeleteBssidCount24g=1",
                        "AfterDeleteChannelCount24g=1",
                        "AfterDeleteBssid24g=11:22:33:44:55:88",
                        "AfterDeleteChannel24g=11",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d083, d083_wrong_24g_delete) is False


def test_d427_neighbour_bssid_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d427_raw = yaml.safe_load((cases_dir / "D427_bssid_accesspoint_neighbour.yaml").read_text(encoding="utf-8"))
    d427 = load_case(cases_dir / "D427_bssid_accesspoint_neighbour.yaml")
    d427_commands = "\n".join(str(step.get("command", "")) for step in d427["steps"])

    assert "aliases" not in d427_raw
    assert d427["id"] == "d427-skip-neighbour-bssid"
    assert d427["source"]["row"] == 427
    assert d427["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d427["source"]["api"] == "BSSID"
    assert d427["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.BSSID?"'
    assert d427["llapi_support"] == "Support"
    assert d427["implemented_by"] == "pWHM"
    assert d427["bands"] == ["5g", "6g", "2.4g"]
    assert set(d427["topology"]["devices"]) == {"DUT"}
    assert d427["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d427.get("sta_env_setup", "")
    assert 'setNeighbourAP(BSSID=11:22:33:44:55:77,Channel=1)' in d427_commands
    assert 'delNeighbourAP(BSSID=11:22:33:44:55:88)' in d427_commands
    assert "AfterDeleteBssid24g=ABSENT" in d427_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddBssid6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "11:22:33:44:55:77"
        for criterion in d427["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteBssidCount5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d427["pass_criteria"]
    )


def test_d429_neighbour_colocatedap_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d429_raw = yaml.safe_load((cases_dir / "D429_colocatedap.yaml").read_text(encoding="utf-8"))
    d429 = load_case(cases_dir / "D429_colocatedap.yaml")
    d429_commands = "\n".join(str(step.get("command", "")) for step in d429["steps"])

    assert "aliases" not in d429_raw
    assert d429["id"] == "d429-skip-neighbour-colocatedap"
    assert d429["source"]["row"] == 429
    assert d429["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d429["source"]["api"] == "ColocatedAP"
    assert d429["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.ColocatedAP?"'
    assert d429["llapi_support"] == "Support"
    assert d429["implemented_by"] == "pWHM"
    assert d429["bands"] == ["5g", "6g", "2.4g"]
    assert set(d429["topology"]["devices"]) == {"DUT"}
    assert d429["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d429.get("sta_env_setup", "")
    assert "(BSSID|Channel|ColocatedAP)" in d429_commands
    assert "AfterAddColocatedAP5g=%s" in d429_commands
    assert "AfterDeleteColocatedAP24g=ABSENT" in d429_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddColocatedAP6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d429["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteColocatedAP5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d429["pass_criteria"]
    )


def test_d430_neighbour_information_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d430_raw = yaml.safe_load((cases_dir / "D430_information.yaml").read_text(encoding="utf-8"))
    d430 = load_case(cases_dir / "D430_information.yaml")
    d430_commands = "\n".join(str(step.get("command", "")) for step in d430["steps"])

    assert "aliases" not in d430_raw
    assert d430["id"] == "d430-skip-neighbour-information"
    assert d430["source"]["row"] == 430
    assert d430["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d430["source"]["api"] == "Information"
    assert d430["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.Information?"'
    assert d430["llapi_support"] == "Support"
    assert d430["implemented_by"] == "pWHM"
    assert d430["bands"] == ["5g", "6g", "2.4g"]
    assert set(d430["topology"]["devices"]) == {"DUT"}
    assert d430["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d430.get("sta_env_setup", "")
    assert "grep 'Neighbour.'" in d430_commands
    assert "AfterAddInformation5g=%s" in d430_commands
    assert "AfterDeleteInformation24g=ABSENT" in d430_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddInformation6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d430["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteInformation5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d430["pass_criteria"]
    )


def test_d431_neighbour_nasidentifier_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d431_raw = yaml.safe_load((cases_dir / "D431_nasidentifier.yaml").read_text(encoding="utf-8"))
    d431 = load_case(cases_dir / "D431_nasidentifier.yaml")
    d431_commands = "\n".join(str(step.get("command", "")) for step in d431["steps"])

    assert "aliases" not in d431_raw
    assert d431["id"] == "d431-skip-neighbour-nasidentifier"
    assert d431["source"]["row"] == 431
    assert d431["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d431["source"]["api"] == "NASIdentifier"
    assert d431["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.NASIdentifier?"'
    assert d431["llapi_support"] == "Support"
    assert d431["implemented_by"] == "pWHM"
    assert d431["bands"] == ["5g", "6g", "2.4g"]
    assert set(d431["topology"]["devices"]) == {"DUT"}
    assert d431["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d431.get("sta_env_setup", "")
    assert "grep 'Neighbour.'" in d431_commands
    assert 'AfterAddNASIdentifier5g="%s"' in d431_commands
    assert "AfterDeleteNASIdentifier24g=ABSENT" in d431_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddNASIdentifier6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == '""'
        for criterion in d431["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteNASIdentifier5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d431["pass_criteria"]
    )


def test_d432_neighbour_operatingclass_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d432_raw = yaml.safe_load((cases_dir / "D432_operatingclass.yaml").read_text(encoding="utf-8"))
    d432 = load_case(cases_dir / "D432_operatingclass.yaml")
    d432_commands = "\n".join(str(step.get("command", "")) for step in d432["steps"])

    assert "aliases" not in d432_raw
    assert d432["id"] == "d432-skip-neighbour-operatingclass"
    assert d432["source"]["row"] == 432
    assert d432["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d432["source"]["api"] == "OperatingClass"
    assert d432["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.OperatingClass?"'
    assert d432["llapi_support"] == "Support"
    assert d432["implemented_by"] == "pWHM"
    assert d432["bands"] == ["5g", "6g", "2.4g"]
    assert set(d432["topology"]["devices"]) == {"DUT"}
    assert d432["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d432.get("sta_env_setup", "")
    assert "grep 'Neighbour.'" in d432_commands
    assert "HotSpot2.OperatingClass" in d432.get("test_environment", "")
    assert "AfterAddOperatingClass5g=%s" in d432_commands
    assert "AfterDeleteOperatingClass24g=ABSENT" in d432_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddOperatingClass6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d432["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteOperatingClass5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d432["pass_criteria"]
    )


def test_d433_neighbour_phytype_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d433_raw = yaml.safe_load((cases_dir / "D433_phytype.yaml").read_text(encoding="utf-8"))
    d433 = load_case(cases_dir / "D433_phytype.yaml")
    d433_commands = "\n".join(str(step.get("command", "")) for step in d433["steps"])

    assert "aliases" not in d433_raw
    assert d433["id"] == "d433-skip-neighbour-phytype"
    assert d433["source"]["row"] == 433
    assert d433["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d433["source"]["api"] == "PhyType"
    assert d433["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.PhyType?"'
    assert d433["llapi_support"] == "Support"
    assert d433["implemented_by"] == "pWHM"
    assert d433["bands"] == ["5g", "6g", "2.4g"]
    assert set(d433["topology"]["devices"]) == {"DUT"}
    assert d433["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d433.get("sta_env_setup", "")
    assert "grep 'Neighbour.'" in d433_commands
    assert "AfterAddPhyType5g=%s" in d433_commands
    assert "AfterDeletePhyType24g=ABSENT" in d433_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddPhyType6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d433["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeletePhyType5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d433["pass_criteria"]
    )


def test_d434_neighbour_r0khkey_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d434_raw = yaml.safe_load((cases_dir / "D434_r0khkey.yaml").read_text(encoding="utf-8"))
    d434 = load_case(cases_dir / "D434_r0khkey.yaml")
    d434_commands = "\n".join(str(step.get("command", "")) for step in d434["steps"])

    assert "aliases" not in d434_raw
    assert d434["id"] == "d434-skip-neighbour-r0khkey"
    assert d434["source"]["row"] == 434
    assert d434["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d434["source"]["api"] == "R0KHKey"
    assert d434["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.R0KHKey?"'
    assert d434["llapi_support"] == "Support"
    assert d434["implemented_by"] == "pWHM"
    assert d434["bands"] == ["5g", "6g", "2.4g"]
    assert set(d434["topology"]["devices"]) == {"DUT"}
    assert d434["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d434.get("sta_env_setup", "")
    assert "grep 'Neighbour.'" in d434_commands
    assert "IEEE80211r.R0KHKey" in d434.get("test_environment", "")
    assert 'AfterAddR0KHKey5g="%s"' in d434_commands
    assert "AfterDeleteR0KHKey24g=ABSENT" in d434_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddR0KHKey6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == '""'
        for criterion in d434["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteR0KHKey5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d434["pass_criteria"]
    )


def test_d435_neighbour_ssid_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d435_raw = yaml.safe_load(
        (cases_dir / "D435_ssid_accesspoint_neighbour.yaml").read_text(encoding="utf-8")
    )
    d435 = load_case(cases_dir / "D435_ssid_accesspoint_neighbour.yaml")
    d435_commands = "\n".join(str(step.get("command", "")) for step in d435["steps"])

    assert "aliases" not in d435_raw
    assert d435["id"] == "d435-skip-neighbour-ssid"
    assert d435["source"]["row"] == 435
    assert d435["source"]["object"] == "WiFi.AccessPoint.{i}.Neighbour.{i}."
    assert d435["source"]["api"] == "SSID"
    assert d435["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Neighbour.1.SSID?"'
    assert d435["llapi_support"] == "Support"
    assert d435["implemented_by"] == "pWHM"
    assert d435["bands"] == ["5g", "6g", "2.4g"]
    assert set(d435["topology"]["devices"]) == {"DUT"}
    assert d435["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d435.get("sta_env_setup", "")
    assert "grep 'Neighbour.'" in d435_commands
    assert "SSIDAdvertisementEnabled" in d435.get("test_environment", "")
    assert 'AfterAddSSID5g="%s"' in d435_commands
    assert "AfterDeleteSSID24g=ABSENT" in d435_commands
    assert any(
        criterion["field"] == "neighbour_after_add_6g.AfterAddSSID6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == '""'
        for criterion in d435["pass_criteria"]
    )
    assert any(
        criterion["field"] == "neighbour_after_delete_5g.AfterDeleteSSID5g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d435["pass_criteria"]
    )


def test_d436_owetransitioninterface_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d436_raw = yaml.safe_load(
        (cases_dir / "D436_owetransitioninterface.yaml").read_text(encoding="utf-8")
    )
    d436 = load_case(cases_dir / "D436_owetransitioninterface.yaml")
    d436_commands = "\n".join(str(step.get("command", "")) for step in d436["steps"])

    assert "aliases" not in d436_raw
    assert d436["id"] == "d436-security-owetransitioninterface"
    assert d436["source"]["row"] == 436
    assert d436["source"]["object"] == "WiFi.AccessPoint.{i}.Security."
    assert d436["source"]["api"] == "OWETransitionInterface"
    assert (
        d436["hlapi_command"]
        == "ubus-cli WiFi.AccessPoint.1.Security.OWETransitionInterface=DEFAULT_WL1_1"
    )
    assert d436["llapi_support"] == "Not Supported"
    assert d436["implemented_by"] == "pWHM"
    assert d436["bands"] == ["5g", "6g", "2.4g"]
    assert set(d436["topology"]["devices"]) == {"DUT"}
    assert d436["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d436.get("sta_env_setup", "")
    assert "AP1.ModeEnabled=OWE" in d436.get("test_procedure", "")
    assert "grep -m1 '^owe_transition_ifname=' /tmp/wl1_hapd.conf" in d436_commands
    assert 'AfterModeOweTransitionAp1="%s"' in d436_commands
    assert 'AfterResetOweTransitionAp6="%s"' in d436_commands
    assert any(
        criterion["field"] == "owe_transition_5g_mode_probe.AfterModeOweTransitionAp1"
        and criterion["operator"] == "not_equals"
        and criterion["reference"]
        == "owe_transition_5g_mode_probe.HostapdOweTransitionIfname5g"
        for criterion in d436["pass_criteria"]
    )
    assert any(
        criterion["field"] == "owe_transition_conf_24g.HostapdOweTransitionIfname24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "ABSENT"
        for criterion in d436["pass_criteria"]
    )


def test_d436_owetransitioninterface_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d436 = load_case(cases_dir / "D436_owetransitioninterface.yaml")

    assert plugin.setup_env(d436, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.1.Security.OWETransitionInterface="
        )
        == 1
    )
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.3.Security.OWETransitionInterface="
        )
        == 1
    )
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.5.Security.OWETransitionInterface="
        )
        == 1
    )
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA2-Personal"
        )
        == 1
    )
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.2.Security.ModeEnabled=WPA2-Personal"
        )
        == 1
    )
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d436, topology)


def test_d436_owetransitioninterface_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d436 = load_case(cases_dir / "D436_owetransitioninterface.yaml")

    def baseline_output() -> str:
        return "\n".join(
            [
                'BaselineOweTransitionAp1=""',
                'BaselineOweTransitionAp2=""',
                'BaselineOweTransitionAp3=""',
                'BaselineOweTransitionAp4=""',
                'BaselineOweTransitionAp5=""',
                'BaselineOweTransitionAp6=""',
                "BaselineModeEnabledAp1=WPA2-Personal",
                "BaselineModeEnabledAp2=WPA2-Personal",
            ]
        )

    def set_output() -> str:
        return "\n".join(
            [
                "RequestedOweTransitionAp1=DEFAULT_WL1_1",
                "RequestedOweTransitionAp3=DEFAULT_WL0_1",
                "RequestedOweTransitionAp5=DEFAULT_WL0_1",
            ]
        )

    def after_set_output() -> str:
        return "\n".join(
            [
                'AfterSetOweTransitionAp1="DEFAULT_WL1_1"',
                'AfterSetOweTransitionAp2=""',
                'AfterSetOweTransitionAp3="DEFAULT_WL0_1"',
                'AfterSetOweTransitionAp4=""',
                'AfterSetOweTransitionAp5="DEFAULT_WL0_1"',
                'AfterSetOweTransitionAp6=""',
            ]
        )

    def mode_probe_output(hostapd: str = "ABSENT") -> str:
        return "\n".join(
            [
                "RequestedModeEnabledAp1=OWE",
                "RequestedModeEnabledAp2=None",
                "AfterModeEnabledAp1=OWE",
                "AfterModeEnabledAp2=None",
                'AfterModeOweTransitionAp1="DEFAULT_WL1_1"',
                f"HostapdOweTransitionIfname5g={hostapd}",
                "AfterRestoreModeEnabledAp1=WPA2-Personal",
                "AfterRestoreModeEnabledAp2=WPA2-Personal",
            ]
        )

    def conf_output(ap: int, suffix: str, hostapd: str = "ABSENT") -> str:
        value = "DEFAULT_WL0_1"
        return "\n".join(
            [
                f'AfterConfOweTransitionAp{ap}="{value}"',
                f"HostapdOweTransitionIfname{suffix}={hostapd}",
            ]
        )

    def reset_output() -> str:
        return "\n".join(
            [
                'RestoreOweTransitionAp1=""',
                'RestoreOweTransitionAp3=""',
                'RestoreOweTransitionAp5=""',
            ]
        )

    def after_reset_output() -> str:
        return "\n".join(
            [
                'AfterResetOweTransitionAp1=""',
                'AfterResetOweTransitionAp2=""',
                'AfterResetOweTransitionAp3=""',
                'AfterResetOweTransitionAp4=""',
                'AfterResetOweTransitionAp5=""',
                'AfterResetOweTransitionAp6=""',
            ]
        )

    d436_results = {
        "steps": {
            "step1_owe_transition_baseline_all": {
                "success": True,
                "output": baseline_output(),
                "timing": 0.01,
            },
            "step2_owe_transition_set_all": {
                "success": True,
                "output": set_output(),
                "timing": 0.01,
            },
            "step3_owe_transition_after_set_all": {
                "success": True,
                "output": after_set_output(),
                "timing": 0.01,
            },
            "step4_owe_transition_5g_mode_probe": {
                "success": True,
                "output": mode_probe_output(),
                "timing": 0.01,
            },
            "step5_owe_transition_conf_6g": {
                "success": True,
                "output": conf_output(3, "6g"),
                "timing": 0.01,
            },
            "step6_owe_transition_conf_24g": {
                "success": True,
                "output": conf_output(5, "24g"),
                "timing": 0.01,
            },
            "step7_owe_transition_reset_all": {
                "success": True,
                "output": reset_output(),
                "timing": 0.01,
            },
            "step8_owe_transition_after_reset_all": {
                "success": True,
                "output": after_reset_output(),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d436, d436_results) is True

    d436_wrong_6g_backend = {
        "steps": {
            **d436_results["steps"],
            "step5_owe_transition_conf_6g": {
                "success": True,
                "output": conf_output(3, "6g", "DEFAULT_WL0_1"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d436, d436_wrong_6g_backend) is False


def test_d437_saepassphrase_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d437_raw = yaml.safe_load((cases_dir / "D437_saepassphrase.yaml").read_text(encoding="utf-8"))
    d437 = load_case(cases_dir / "D437_saepassphrase.yaml")
    d437_commands = "\n".join(str(step.get("command", "")) for step in d437["steps"])

    assert "aliases" not in d437_raw
    assert d437["id"] == "d437-security-saepassphrase"
    assert d437["source"]["row"] == 437
    assert d437["source"]["object"] == "WiFi.AccessPoint.{i}.Security."
    assert d437["source"]["api"] == "SAEPassphrase"
    assert d437["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.*.Security.SAEPassphrase=1234567890"'
    assert d437["llapi_support"] == "Support"
    assert d437["implemented_by"] == "pWHM"
    assert d437["bands"] == ["5g", "6g", "2.4g"]
    assert set(d437["topology"]["devices"]) == {"DUT"}
    assert d437["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d437.get("sta_env_setup", "")
    assert "WPA3-Personal" in d437.get("test_procedure", "")
    assert "grep -m1 '^sae_password=' /tmp/wl1_hapd.conf" in d437_commands
    assert 'AfterSetHostapdSAEPassphrase6g=%s' in d437_commands
    assert 'AfterRestoreHostapdSAEPassphrase24g=%s' in d437_commands
    assert 'WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"' in d437_commands
    assert any(
        criterion["field"] == "saepassphrase_after_set_6g.AfterSetHostapdSAEPassphrase6g"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "saepassphrase_after_set_6g.AfterSetGetterSAEPassphrase6g"
        for criterion in d437["pass_criteria"]
    )
    assert any(
        criterion["field"] == "saepassphrase_after_restore_5g.AfterRestoreHostapdSAEPassphrase5g"
        and criterion["operator"] == "equals"
        and criterion["reference"]
        == "saepassphrase_baseline_5g.BaselineHostapdSAEPassphrase5g"
        for criterion in d437["pass_criteria"]
    )


def test_d437_saepassphrase_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d437 = load_case(cases_dir / "D437_saepassphrase.yaml")

    assert plugin.setup_env(d437, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WPA2-Personal"
        )
        == 1
    )
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.3.Security.ModeEnabled=WPA3-Personal"
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli \'WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"\''
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli \'WiFi.AccessPoint.4.Security.SAEPassphrase="00000000"\''
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli \'WiFi.AccessPoint.3.Security.KeyPassPhrase="00000000"\''
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli \'WiFi.AccessPoint.4.Security.KeyPassPhrase="00000000"\''
        )
        == 1
    )
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Security.SAEPassphrase=password") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d437, topology)


def test_d437_saepassphrase_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d437 = load_case(cases_dir / "D437_saepassphrase.yaml")

    def baseline_output(mode: str, getter: str, hostapd: str, suffix: str) -> str:
        return "\n".join(
            [
                f"BaselineModeEnabled{suffix}={mode}",
                f"BaselineGetterSAEPassphrase{suffix}={getter}",
                f"BaselineHostapdSAEPassphrase{suffix}={hostapd}",
            ]
        )

    def after_set_output(suffix: str) -> str:
        return "\n".join(
            [
                f"AfterSetModeEnabled{suffix}=WPA3-Personal",
                f"AfterSetGetterSAEPassphrase{suffix}=1234567890",
                f"AfterSetHostapdSAEPassphrase{suffix}=1234567890",
            ]
        )

    def after_restore_output(mode: str, getter: str, hostapd: str, suffix: str) -> str:
        return "\n".join(
            [
                f"AfterRestoreModeEnabled{suffix}={mode}",
                f"AfterRestoreGetterSAEPassphrase{suffix}={getter}",
                f"AfterRestoreHostapdSAEPassphrase{suffix}={hostapd}",
            ]
        )

    d437_results = {
        "steps": {
            "step1_saepassphrase_baseline_5g": {
                "success": True,
                "output": baseline_output("WPA2-Personal", "password", "ABSENT", "5g"),
                "timing": 0.01,
            },
            "step2_saepassphrase_baseline_6g": {
                "success": True,
                "output": baseline_output("WPA3-Personal", "00000000", "00000000", "6g"),
                "timing": 0.01,
            },
            "step3_saepassphrase_baseline_24g": {
                "success": True,
                "output": baseline_output("WPA2-Personal", "password", "ABSENT", "24g"),
                "timing": 0.01,
            },
            "step4_saepassphrase_set_mode_all": {
                "success": True,
                "output": "RequestedModeEnabledAll=WPA3-Personal",
                "timing": 0.01,
            },
            "step5_saepassphrase_set_all": {
                "success": True,
                "output": "RequestedSAEPassphraseAll=1234567890",
                "timing": 0.01,
            },
            "step6_saepassphrase_after_set_5g": {
                "success": True,
                "output": after_set_output("5g"),
                "timing": 0.01,
            },
            "step7_saepassphrase_after_set_6g": {
                "success": True,
                "output": after_set_output("6g"),
                "timing": 0.01,
            },
            "step8_saepassphrase_after_set_24g": {
                "success": True,
                "output": after_set_output("24g"),
                "timing": 0.01,
            },
            "step9_saepassphrase_restore_baseline": {
                "success": True,
                "output": "restore=ok",
                "timing": 0.01,
            },
            "step10_saepassphrase_after_restore_5g": {
                "success": True,
                "output": after_restore_output("WPA2-Personal", "password", "ABSENT", "5g"),
                "timing": 0.01,
            },
            "step11_saepassphrase_after_restore_6g": {
                "success": True,
                "output": after_restore_output("WPA3-Personal", "00000000", "00000000", "6g"),
                "timing": 0.01,
            },
            "step12_saepassphrase_after_restore_24g": {
                "success": True,
                "output": after_restore_output("WPA2-Personal", "password", "ABSENT", "24g"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d437, d437_results) is True

    d437_wrong_24g_backend = {
        "steps": {
            **d437_results["steps"],
            "step8_saepassphrase_after_set_24g": {
                "success": True,
                "output": after_set_output("24g").replace(
                    "AfterSetHostapdSAEPassphrase24g=1234567890",
                    "AfterSetHostapdSAEPassphrase24g=ABSENT",
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d437, d437_wrong_24g_backend) is False


def test_d438_transitiondisable_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d438_raw = yaml.safe_load((cases_dir / "D438_transitiondisable.yaml").read_text(encoding="utf-8"))
    d438 = load_case(cases_dir / "D438_transitiondisable.yaml")
    d438_commands = "\n".join(str(step.get("command", "")) for step in d438["steps"])

    assert "aliases" not in d438_raw
    assert d438["id"] == "d438-security-transitiondisable"
    assert d438["source"]["row"] == 438
    assert d438["source"]["object"] == "WiFi.AccessPoint.{i}.Security."
    assert d438["source"]["api"] == "TransitionDisable"
    assert d438["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.*.Security.TransitionDisable=WPA3-Personal"'
    assert d438["llapi_support"] == "Support"
    assert d438["implemented_by"] == "pWHM"
    assert d438["bands"] == ["5g", "6g", "2.4g"]
    assert set(d438["topology"]["devices"]) == {"DUT"}
    assert d438["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d438.get("sta_env_setup", "")
    assert "transition_disable=1" in d438.get("test_environment", "")
    assert "grep -m1 '^transition_disable=' /tmp/wl1_hapd.conf" in d438_commands
    assert 'AfterEnhancedOpenHostapdTransitionDisable24g=%s' in d438_commands
    assert 'RestoreTransitionDisableAll=""' in d438_commands
    assert any(
        criterion["field"] == "transitiondisable_after_sae_pk_6g.AfterSaePkHostapdTransitionDisable6g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "2"
        for criterion in d438["pass_criteria"]
    )
    assert any(
        criterion["field"] == "transitiondisable_after_restore_24g.AfterRestoreHostapdTransitionDisable24g"
        and criterion["operator"] == "equals"
        and criterion["reference"]
        == "transitiondisable_baseline_24g.BaselineHostapdTransitionDisable24g"
        for criterion in d438["pass_criteria"]
    )


def test_d438_transitiondisable_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d438 = load_case(cases_dir / "D438_transitiondisable.yaml")

    assert plugin.setup_env(d438, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert (
        executed_commands.count(
            "ubus-cli WiFi.AccessPoint.3.Security.ModeEnabled=WPA3-Personal"
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli \'WiFi.AccessPoint.3.Security.SAEPassphrase="00000000"\''
        )
        == 1
    )
    assert (
        executed_commands.count(
            'ubus-cli \'WiFi.AccessPoint.3.Security.KeyPassPhrase="00000000"\''
        )
        == 1
    )
    assert (
        executed_commands.count('ubus-cli "WiFi.AccessPoint.*.Security.TransitionDisable="')
        == 1
    )
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d438, topology)


def test_d438_transitiondisable_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d438 = load_case(cases_dir / "D438_transitiondisable.yaml")

    def output(prefix: str, suffix: str, getter: str, hostapd: str) -> str:
        return "\n".join(
            [
                f'{prefix}GetterTransitionDisable{suffix}="{getter}"',
                f"{prefix}HostapdTransitionDisable{suffix}={hostapd}",
            ]
        )

    d438_results = {
        "steps": {
            "step1_transitiondisable_baseline_5g": {
                "success": True,
                "output": output("Baseline", "5g", "", "ABSENT"),
                "timing": 0.01,
            },
            "step2_transitiondisable_baseline_6g": {
                "success": True,
                "output": output("Baseline", "6g", "", "ABSENT"),
                "timing": 0.01,
            },
            "step3_transitiondisable_baseline_24g": {
                "success": True,
                "output": output("Baseline", "24g", "", "ABSENT"),
                "timing": 0.01,
            },
            "step4_transitiondisable_set_wpa3_personal": {
                "success": True,
                "output": 'RequestedTransitionDisableAll="WPA3-Personal"',
                "timing": 0.01,
            },
            "step5_transitiondisable_after_wpa3_personal_5g": {
                "success": True,
                "output": output("AfterWpa3Personal", "5g", "WPA3-Personal", "1"),
                "timing": 0.01,
            },
            "step6_transitiondisable_after_wpa3_personal_6g": {
                "success": True,
                "output": output("AfterWpa3Personal", "6g", "WPA3-Personal", "1"),
                "timing": 0.01,
            },
            "step7_transitiondisable_after_wpa3_personal_24g": {
                "success": True,
                "output": output("AfterWpa3Personal", "24g", "WPA3-Personal", "1"),
                "timing": 0.01,
            },
            "step8_transitiondisable_set_sae_pk": {
                "success": True,
                "output": 'RequestedTransitionDisableAll="SAE-PK"',
                "timing": 0.01,
            },
            "step9_transitiondisable_after_sae_pk_5g": {
                "success": True,
                "output": output("AfterSaePk", "5g", "SAE-PK", "2"),
                "timing": 0.01,
            },
            "step10_transitiondisable_after_sae_pk_6g": {
                "success": True,
                "output": output("AfterSaePk", "6g", "SAE-PK", "2"),
                "timing": 0.01,
            },
            "step11_transitiondisable_after_sae_pk_24g": {
                "success": True,
                "output": output("AfterSaePk", "24g", "SAE-PK", "2"),
                "timing": 0.01,
            },
            "step12_transitiondisable_set_enhanced_open": {
                "success": True,
                "output": 'RequestedTransitionDisableAll="EnhancedOpen"',
                "timing": 0.01,
            },
            "step13_transitiondisable_after_enhanced_open_5g": {
                "success": True,
                "output": output("AfterEnhancedOpen", "5g", "EnhancedOpen", "8"),
                "timing": 0.01,
            },
            "step14_transitiondisable_after_enhanced_open_6g": {
                "success": True,
                "output": output("AfterEnhancedOpen", "6g", "EnhancedOpen", "8"),
                "timing": 0.01,
            },
            "step15_transitiondisable_after_enhanced_open_24g": {
                "success": True,
                "output": output("AfterEnhancedOpen", "24g", "EnhancedOpen", "8"),
                "timing": 0.01,
            },
            "step16_transitiondisable_restore_default": {
                "success": True,
                "output": 'RestoreTransitionDisableAll=""',
                "timing": 0.01,
            },
            "step17_transitiondisable_after_restore_5g": {
                "success": True,
                "output": output("AfterRestore", "5g", "", "ABSENT"),
                "timing": 0.01,
            },
            "step18_transitiondisable_after_restore_6g": {
                "success": True,
                "output": output("AfterRestore", "6g", "", "ABSENT"),
                "timing": 0.01,
            },
            "step19_transitiondisable_after_restore_24g": {
                "success": True,
                "output": output("AfterRestore", "24g", "", "ABSENT"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d438, d438_results) is True

    d438_wrong_6g_backend = {
        "steps": {
            **d438_results["steps"],
            "step14_transitiondisable_after_enhanced_open_6g": {
                "success": True,
                "output": output("AfterEnhancedOpen", "6g", "EnhancedOpen", "1"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d438, d438_wrong_6g_backend) is False


def test_d084_encryptionmode_accesspoint_security_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d084_raw = yaml.safe_load((cases_dir / "D084_encryptionmode_accesspoint_security.yaml").read_text(encoding="utf-8"))
    d084 = load_case(cases_dir / "D084_encryptionmode_accesspoint_security.yaml")
    d084_commands = "\n".join(str(step.get("command", "")) for step in d084["steps"])

    assert "aliases" not in d084_raw
    assert d084["id"] == "wifi-llapi-D084-encryptionmode-accesspoint-security"
    assert d084["source"]["row"] == 84
    assert d084["hlapi_command"] == 'ubus-cli "WiFi.AccessPoint.1.Security.EncryptionMode?"'
    assert d084["llapi_support"] == "Not Supported"
    assert d084["implemented_by"] == "pWHM"
    assert d084["bands"] == ["5g", "6g", "2.4g"]
    assert set(d084["topology"]["devices"]) == {"DUT"}
    assert d084["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d084.get("sta_env_setup", "")
    assert "HostapdKeyMgmt6g=SAE" not in d084_commands
    assert "grep -m1 '^wpa_key_mgmt=' /tmp/wl1_hapd.conf" in d084_commands
    assert any(
        criterion["field"] == "encryption_mode_6g.EncryptionMode6g"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "security_hostapd_6g.HostapdPairwise6g"
        for criterion in d084["pass_criteria"]
    )
    assert any(
        criterion["field"] == "security_hostapd_24g.HostapdKeyMgmt24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "WPA-PSK"
        for criterion in d084["pass_criteria"]
    )


def test_d084_encryptionmode_accesspoint_security_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d084 = load_case(cases_dir / "D084_encryptionmode_accesspoint_security.yaml")

    assert plugin.setup_env(d084, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d084, topology)


def test_d084_encryptionmode_accesspoint_security_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d084 = load_case(cases_dir / "D084_encryptionmode_accesspoint_security.yaml")

    def mode_output(prefix: str, value: str) -> str:
        return f"ModeEnabled{prefix}={value}"

    def encryption_output(prefix: str, value: str) -> str:
        return f"EncryptionMode{prefix}={value}"

    def hostapd_output(prefix: str, keymgmt: str, pairwise: str, rsn: str) -> str:
        return "\n".join(
            [
                f"HostapdKeyMgmt{prefix}={keymgmt}",
                f"HostapdPairwise{prefix}={pairwise}",
                f"HostapdRsnPairwise{prefix}={rsn}",
            ]
        )

    d084_results = {
        "steps": {
            "step1_security_mode_5g": {"success": True, "output": mode_output("5g", "WPA2-Personal"), "timing": 0.01},
            "step2_encryption_mode_5g": {"success": True, "output": encryption_output("5g", "Default"), "timing": 0.01},
            "step3_security_hostapd_5g": {
                "success": True,
                "output": hostapd_output("5g", "WPA-PSK", "CCMP", "CCMP"),
                "timing": 0.01,
            },
            "step4_security_mode_6g": {"success": True, "output": mode_output("6g", "WPA3-Personal"), "timing": 0.01},
            "step5_encryption_mode_6g": {"success": True, "output": encryption_output("6g", "Default"), "timing": 0.01},
            "step6_security_hostapd_6g": {
                "success": True,
                "output": hostapd_output("6g", "SAE", "CCMP", "CCMP"),
                "timing": 0.01,
            },
            "step7_security_mode_24g": {"success": True, "output": mode_output("24g", "WPA2-Personal"), "timing": 0.01},
            "step8_encryption_mode_24g": {
                "success": True,
                "output": encryption_output("24g", "Default"),
                "timing": 0.01,
            },
            "step9_security_hostapd_24g": {
                "success": True,
                "output": hostapd_output("24g", "WPA-PSK", "CCMP", "CCMP"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d084, d084_results) is True

    d084_wrong_5g_encryption = {
        "steps": {
            **d084_results["steps"],
            "step2_encryption_mode_5g": {
                "success": True,
                "output": encryption_output("5g", "CCMP"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d084, d084_wrong_5g_encryption) is False

    d084_wrong_6g_hostapd = {
        "steps": {
            **d084_results["steps"],
            "step6_security_hostapd_6g": {
                "success": True,
                "output": hostapd_output("6g", "SAE", "Default", "Default"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d084, d084_wrong_6g_hostapd) is False

    d084_wrong_24g_mode = {
        "steps": {
            **d084_results["steps"],
            "step7_security_mode_24g": {
                "success": True,
                "output": mode_output("24g", "WPA3-Personal"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d084, d084_wrong_24g_mode) is False


def test_d085_keypassphrase_accesspoint_security_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d085_raw = yaml.safe_load((cases_dir / "D085_keypassphrase_accesspoint_security.yaml").read_text(encoding="utf-8"))
    d085 = load_case(cases_dir / "D085_keypassphrase_accesspoint_security.yaml")
    d085_commands = "\n".join(str(step.get("command", "")) for step in d085["steps"])

    assert "aliases" not in d085_raw
    assert d085["id"] == "wifi-llapi-D085-keypassphrase-accesspoint-security"
    assert d085["source"]["row"] == 85
    assert d085["hlapi_command"] == 'ubus-cli \'WiFi.AccessPoint.1.Security.KeyPassPhrase="0689388783"\''
    assert d085["llapi_support"] == "Support"
    assert d085["implemented_by"] == "pWHM"
    assert d085["bands"] == ["5g", "6g", "2.4g"]
    assert set(d085["topology"]["devices"]) == {"DUT"}
    assert d085["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d085.get("sta_env_setup", "")
    assert 'RequestedKeyPassPhrase5g=0689388783' in d085_commands
    assert "wpa_pairwise" in "\n".join(d085.get("verification_command", []))
    assert any(
        criterion["field"] == "keypassphrase_after_restore_24g.AfterRestoreHostapdKeyPassPhrase24g"
        and criterion["operator"] == "equals"
        and criterion["reference"] == "keypassphrase_after_restore_24g.AfterRestoreGetterKeyPassPhrase24g"
        for criterion in d085["pass_criteria"]
    )


def test_d085_keypassphrase_accesspoint_security_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d085 = load_case(cases_dir / "D085_keypassphrase_accesspoint_security.yaml")

    assert plugin.setup_env(d085, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d085, topology)


def test_d085_keypassphrase_accesspoint_security_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d085 = load_case(cases_dir / "D085_keypassphrase_accesspoint_security.yaml")

    def baseline_output(prefix: str, getter: str, hostapd: str) -> str:
        lines = [
            f"BaselineGetterKeyPassPhrase{prefix}={getter}",
            f"BaselineHostapdKeyPassPhrase{prefix}={hostapd}",
        ]
        return "\n".join(lines)

    def set_output(prefix: str, value: str) -> str:
        return f"RequestedKeyPassPhrase{prefix}={value}"

    def after_set_output(prefix: str, getter: str, hostapd: str) -> str:
        lines = [
            f"AfterSetGetterKeyPassPhrase{prefix}={getter}",
            f"AfterSetHostapdKeyPassPhrase{prefix}={hostapd}",
        ]
        return "\n".join(lines)

    def restore_output(prefix: str, value: str) -> str:
        return f"RestoreKeyPassPhrase{prefix}={value}"

    def after_restore_output(prefix: str, getter: str, hostapd: str) -> str:
        lines = [
            f"AfterRestoreGetterKeyPassPhrase{prefix}={getter}",
            f"AfterRestoreHostapdKeyPassPhrase{prefix}={hostapd}",
        ]
        return "\n".join(lines)

    d085_results = {
        "steps": {
            "step1_keypassphrase_baseline_5g": {
                "success": True,
                "output": baseline_output("5g", "00000000", "00000000"),
                "timing": 0.01,
            },
            "step2_keypassphrase_set_5g": {
                "success": True,
                "output": set_output("5g", "0689388783"),
                "timing": 0.01,
            },
            "step3_keypassphrase_after_set_5g": {
                "success": True,
                "output": after_set_output("5g", "0689388783", "0689388783"),
                "timing": 0.01,
            },
            "step4_keypassphrase_restore_5g": {
                "success": True,
                "output": restore_output("5g", "00000000"),
                "timing": 0.01,
            },
            "step5_keypassphrase_after_restore_5g": {
                "success": True,
                "output": after_restore_output("5g", "00000000", "00000000"),
                "timing": 0.01,
            },
            "step6_keypassphrase_baseline_6g": {
                "success": True,
                "output": baseline_output("6g", "00000000", "00000000"),
                "timing": 0.01,
            },
            "step7_keypassphrase_set_6g": {
                "success": True,
                "output": set_output("6g", "0689388783"),
                "timing": 0.01,
            },
            "step8_keypassphrase_after_set_6g": {
                "success": True,
                "output": after_set_output("6g", "0689388783", "0689388783"),
                "timing": 0.01,
            },
            "step9_keypassphrase_restore_6g": {
                "success": True,
                "output": restore_output("6g", "00000000"),
                "timing": 0.01,
            },
            "step10_keypassphrase_after_restore_6g": {
                "success": True,
                "output": after_restore_output("6g", "00000000", "00000000"),
                "timing": 0.01,
            },
            "step11_keypassphrase_baseline_24g": {
                "success": True,
                "output": baseline_output("24g", "00000000", "00000000"),
                "timing": 0.01,
            },
            "step12_keypassphrase_set_24g": {
                "success": True,
                "output": set_output("24g", "0689388783"),
                "timing": 0.01,
            },
            "step13_keypassphrase_after_set_24g": {
                "success": True,
                "output": after_set_output("24g", "0689388783", "0689388783"),
                "timing": 0.01,
            },
            "step14_keypassphrase_restore_24g": {
                "success": True,
                "output": restore_output("24g", "00000000"),
                "timing": 0.01,
            },
            "step15_keypassphrase_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "00000000", "00000000"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d085, d085_results) is True

    d085_wrong_5g_hostapd = {
        "steps": {
            **d085_results["steps"],
            "step3_keypassphrase_after_set_5g": {
                "success": True,
                "output": after_set_output("5g", "0689388783", "689388783.000000"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d085, d085_wrong_5g_hostapd) is False

    d085_wrong_24g_restore = {
        "steps": {
            **d085_results["steps"],
            "step15_keypassphrase_after_restore_24g": {
                "success": True,
                "output": after_restore_output("24g", "0689388783", "00000000"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d085, d085_wrong_24g_restore) is False


def test_d086_mfpconfig_accesspoint_security_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d086_raw = yaml.safe_load((cases_dir / "D086_mfpconfig_accesspoint_security.yaml").read_text(encoding="utf-8"))
    d086 = load_case(cases_dir / "D086_mfpconfig_accesspoint_security.yaml")
    d086_commands = "\n".join(str(step.get("command", "")) for step in d086["steps"])

    assert "aliases" not in d086_raw
    assert d086["id"] == "wifi-llapi-D086-mfpconfig-accesspoint-security"
    assert d086["source"]["row"] == 86
    assert d086["hlapi_command"] == "ubus-cli WiFi.AccessPoint.1.Security.MFPConfig=Disabled"
    assert d086["llapi_support"] == "Support"
    assert d086["implemented_by"] == "pWHM"
    assert d086["bands"] == ["5g", "6g", "2.4g"]
    assert set(d086["topology"]["devices"]) == {"DUT"}
    assert d086["topology"]["links"] == []
    assert "killall wpa_supplicant" not in d086.get("sta_env_setup", "")
    assert "grep -m1 '^ieee80211w=' /tmp/wl1_hapd.conf" in d086_commands
    assert 'case "$RAW" in 0) MFP=Disabled ;; 1) MFP=Optional ;; 2) MFP=Required ;;' in d086_commands
    assert any(
        criterion["field"] == "mfp_after_disable_6g.GetterMfpConfig6g"
        and criterion["operator"] == "not_equals"
        and criterion["reference"] == "mfp_after_disable_6g.HostapdMfpConfig6g"
        for criterion in d086["pass_criteria"]
    )
    assert any(
        criterion["field"] == "mfp_after_disable_24g.HostapdMfpRaw24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "0"
        for criterion in d086["pass_criteria"]
    )


def test_d086_mfpconfig_accesspoint_security_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d086 = load_case(cases_dir / "D086_mfpconfig_accesspoint_security.yaml")

    assert plugin.setup_env(d086, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert executed_commands.count("wl -i wl0 bss") == 1
    assert executed_commands.count("wl -i wl1 bss") == 1
    assert executed_commands.count("wl -i wl2 bss") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d086, topology)


def test_d086_mfpconfig_accesspoint_security_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d086 = load_case(cases_dir / "D086_mfpconfig_accesspoint_security.yaml")

    def mode_output(prefix: str, value: str) -> str:
        return f"ModeEnabled{prefix}={value}"

    def disable_output(prefix: str) -> str:
        return f"RequestedMfpConfig{prefix}=Disabled"

    def after_disable_output(prefix: str, getter: str, keymgmt: str, hostapd_mfp: str, raw: str) -> str:
        return "\n".join(
            [
                f"GetterMfpConfig{prefix}={getter}",
                f"HostapdKeyMgmt{prefix}={keymgmt}",
                f"HostapdMfpConfig{prefix}={hostapd_mfp}",
                f"HostapdMfpRaw{prefix}={raw}",
            ]
        )

    d086_results = {
        "steps": {
            "step1_security_mode_5g": {"success": True, "output": mode_output("5g", "WPA2-Personal"), "timing": 0.01},
            "step2_mfp_disable_5g": {"success": True, "output": disable_output("5g"), "timing": 0.01},
            "step3_mfp_after_disable_5g": {
                "success": True,
                "output": after_disable_output("5g", "Disabled", "WPA-PSK", "Disabled", "0"),
                "timing": 0.01,
            },
            "step4_security_mode_6g": {"success": True, "output": mode_output("6g", "WPA3-Personal"), "timing": 0.01},
            "step5_mfp_disable_6g": {"success": True, "output": disable_output("6g"), "timing": 0.01},
            "step6_mfp_after_disable_6g": {
                "success": True,
                "output": after_disable_output("6g", "Disabled", "SAE", "Required", "2"),
                "timing": 0.01,
            },
            "step7_security_mode_24g": {"success": True, "output": mode_output("24g", "WPA2-Personal"), "timing": 0.01},
            "step8_mfp_disable_24g": {"success": True, "output": disable_output("24g"), "timing": 0.01},
            "step9_mfp_after_disable_24g": {
                "success": True,
                "output": after_disable_output("24g", "Disabled", "WPA-PSK", "Disabled", "0"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d086, d086_results) is True

    d086_wrong_5g_hostapd = {
        "steps": {
            **d086_results["steps"],
            "step3_mfp_after_disable_5g": {
                "success": True,
                "output": after_disable_output("5g", "Disabled", "WPA-PSK", "Required", "2"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d086, d086_wrong_5g_hostapd) is False

    d086_wrong_6g_hostapd = {
        "steps": {
            **d086_results["steps"],
            "step6_mfp_after_disable_6g": {
                "success": True,
                "output": after_disable_output("6g", "Disabled", "SAE", "Disabled", "0"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d086, d086_wrong_6g_hostapd) is False

    d086_wrong_24g_getter = {
        "steps": {
            **d086_results["steps"],
            "step9_mfp_after_disable_24g": {
                "success": True,
                "output": after_disable_output("24g", "Optional", "WPA-PSK", "Disabled", "0"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d086, d086_wrong_24g_getter) is False


def test_d087_modeenabled_accesspoint_security_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d087 = load_case(cases_dir / "D087_modeenabled_accesspoint_security.yaml")
    assert d087["id"] == "wifi-llapi-D087-modeenabled-accesspoint-security"
    assert d087["source"]["row"] == 87
    assert d087["source"]["api"] == "ModeEnabled"
    assert d087["bands"] == ["5g", "6g", "2.4g"]
    assert len(d087["steps"]) == 12
    assert len(d087["pass_criteria"]) == 15
    step_ids = [s["id"] for s in d087["steps"]]
    for band_tag in ["5g", "6g", "24g"]:
        assert f"step1_baseline_5g" in step_ids or any(band_tag in sid for sid in step_ids)
    assert all(s.get("target") == "DUT" for s in d087["steps"])


def test_d087_modeenabled_accesspoint_security_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d087 = load_case(cases_dir / "D087_modeenabled_accesspoint_security.yaml")

    assert plugin.setup_env(d087, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.1.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.3.Enable=1") == 1
    assert executed_commands.count("ubus-cli WiFi.AccessPoint.5.Enable=1") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d087, topology)


def test_d087_modeenabled_accesspoint_security_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d087 = load_case(cases_dir / "D087_modeenabled_accesspoint_security.yaml")

    def baseline_output(band: str, mode: str, keymgmt: str, w: str) -> str:
        return "\n".join([
            f"BaselineModeEnabled{band}={mode}",
            f"BaselineKeyMgmt{band}={keymgmt}",
            f"BaselineIeee80211w{band}={w}",
        ])

    def set_output(band: str) -> str:
        return f"SetterRequest{band}=WPA3-Personal"

    def readback_output(band: str, mode: str, keymgmt: str, w: str) -> str:
        return "\n".join([
            f"GetterModeEnabled{band}={mode}",
            f"HostapdKeyMgmt{band}={keymgmt}",
            f"HostapdIeee80211w{band}={w}",
        ])

    d087_results = {
        "steps": {
            "step1_baseline_5g": {"success": True, "output": baseline_output("5g", "WPA2-Personal", "WPA-PSK FT-PSK", "0"), "timing": 0.01},
            "step2_set_5g": {"success": True, "output": set_output("5g"), "timing": 0.01},
            "step3_readback_5g": {"success": True, "output": readback_output("5g", "WPA3-Personal", "SAE FT-SAE", "2"), "timing": 0.01},
            "step4_restore_5g": {"success": True, "output": "", "timing": 0.01},
            "step5_baseline_6g": {"success": True, "output": baseline_output("6g", "WPA3-Personal", "SAE FT-SAE", "2"), "timing": 0.01},
            "step6_set_6g": {"success": True, "output": set_output("6g"), "timing": 0.01},
            "step7_readback_6g": {"success": True, "output": readback_output("6g", "WPA3-Personal", "SAE FT-SAE", "2"), "timing": 0.01},
            "step8_restore_6g": {"success": True, "output": "", "timing": 0.01},
            "step9_baseline_24g": {"success": True, "output": baseline_output("24g", "WPA2-Personal", "WPA-PSK FT-PSK", "0"), "timing": 0.01},
            "step10_set_24g": {"success": True, "output": set_output("24g"), "timing": 0.01},
            "step11_readback_24g": {"success": True, "output": readback_output("24g", "WPA3-Personal", "SAE FT-SAE", "2"), "timing": 0.01},
            "step12_restore_24g": {"success": True, "output": "", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d087, d087_results) is True

    # Wrong 5G readback (still WPA2-Personal after setter)
    d087_bad_5g = {
        "steps": {
            **d087_results["steps"],
            "step3_readback_5g": {"success": True, "output": readback_output("5g", "WPA2-Personal", "WPA-PSK", "0"), "timing": 0.01},
        }
    }
    assert plugin.evaluate(d087, d087_bad_5g) is False

    # Wrong 6G readback (unexpected mode)
    d087_bad_6g = {
        "steps": {
            **d087_results["steps"],
            "step7_readback_6g": {"success": True, "output": readback_output("6g", "WPA2-Personal", "SAE", "2"), "timing": 0.01},
        }
    }
    assert plugin.evaluate(d087, d087_bad_6g) is False

    # Wrong 2.4G readback (hostapd never leaves WPA-PSK family)
    d087_bad_24g_readback = {
        "steps": {
            **d087_results["steps"],
            "step11_readback_24g": {"success": True, "output": readback_output("24g", "WPA3-Personal", "WPA-PSK FT-PSK", "0"), "timing": 0.01},
        }
    }
    assert plugin.evaluate(d087, d087_bad_24g_readback) is False


def test_d088_modessupported_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d088 = load_case(cases_dir / "D088_modessupported.yaml")
    assert d088["id"] == "wifi-llapi-D088-modessupported"
    assert d088["source"]["row"] == 88
    assert d088["source"]["api"] == "ModesSupported"
    assert d088["bands"] == ["5g", "6g", "2.4g"]
    assert len(d088["steps"]) == 6
    assert len(d088["pass_criteria"]) == 13
    assert all(s.get("target") == "DUT" for s in d088["steps"])
    assert "STA" not in d088["topology"]["devices"]


def test_d088_modessupported_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d088 = load_case(cases_dir / "D088_modessupported.yaml")

    assert plugin.setup_env(d088, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d088, topology)


def test_d088_modessupported_setter_step_keeps_original_command():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d088 = load_case(cases_dir / "D088_modessupported.yaml")

    commands, reason = plugin._command_resolver.resolve(
        d088,
        d088["steps"][1],
        _FakeTopology(),
    )

    assert len(commands) == 1
    assert commands[0] == d088["steps"][1]["command"]
    assert "error=" in commands[0]
    assert "message=" in commands[0]
    assert reason == ""


def test_d088_modessupported_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d088 = load_case(cases_dir / "D088_modessupported.yaml")

    def setter_output(ap: int) -> str:
        return "\n".join(
            [
                f"ERROR: set WiFi.AccessPoint.{ap}.Security.ModesSupported failed (15 - is read only)",
                "error=15",
                "message=is read only",
            ]
        )

    d088_results = {
        "steps": {
            "step1": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.Security.ModesSupported="None,WEP-64,WEP-128,WEP-128iv,WPA-Personal,WPA2-Personal,WPA-WPA2-Personal,WPA3-Personal,WPA2-WPA3-Personal,WPA-Enterprise,WPA2-Enterprise,WPA-WPA2-Enterprise,OWE"',
                "timing": 0.01,
            },
            "step2": {"success": True, "output": setter_output(1), "timing": 0.01},
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.Security.ModesSupported="None,WPA3-Personal,OWE"',
                "timing": 0.01,
            },
            "step4": {"success": True, "output": setter_output(3), "timing": 0.01},
            "step5": {
                "success": True,
                "output": 'WiFi.AccessPoint.5.Security.ModesSupported="None,WEP-64,WEP-128,WEP-128iv,WPA-Personal,WPA2-Personal,WPA-WPA2-Personal,WPA3-Personal,WPA2-WPA3-Personal,WPA-Enterprise,WPA2-Enterprise,WPA-WPA2-Enterprise,OWE"',
                "timing": 0.01,
            },
            "step6": {"success": True, "output": setter_output(5), "timing": 0.01},
        }
    }
    assert plugin.evaluate(d088, d088_results) is True

    wrong_6g_results = {
        "steps": {
            **d088_results["steps"],
            "step3": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.Security.ModesSupported="None,WPA2-Personal,WPA3-Personal,OWE"',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d088, wrong_6g_results) is False


def test_d089_presharedkey_accesspoint_security_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d089 = load_case(cases_dir / "D089_presharedkey_accesspoint_security.yaml")
    assert d089["id"] == "wifi-llapi-D089-presharedkey-accesspoint-security"
    assert d089["source"]["row"] == 83
    assert d089["source"]["api"] == "PreSharedKey"
    assert d089["bands"] == ["5g", "6g", "2.4g"]
    assert len(d089["steps"]) == 12
    assert len(d089["pass_criteria"]) == 9
    assert all(s.get("target") == "DUT" for s in d089["steps"])
    assert "STA" not in d089["topology"]["devices"]


def test_d089_presharedkey_accesspoint_security_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d089 = load_case(cases_dir / "D089_presharedkey_accesspoint_security.yaml")

    assert plugin.setup_env(d089, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d089, topology)


def test_d089_presharedkey_accesspoint_security_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d089 = load_case(cases_dir / "D089_presharedkey_accesspoint_security.yaml")

    psk = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
    d089_results = {
        "steps": {
            "step1_baseline_5g": {"success": True, "output": "BaselinePreSharedKey5g=\nBaselineWpaPsk5g=", "timing": 0.01},
            "step2_set_5g": {"success": True, "output": f"PreSharedKey={psk}", "timing": 0.01},
            "step3_readback_5g": {"success": True, "output": f"GetterPreSharedKey5g={psk}", "timing": 0.01},
            "step4_restore_5g": {"success": True, "output": "RestoredPreSharedKey5g=", "timing": 0.01},
            "step5_baseline_6g": {"success": True, "output": "BaselinePreSharedKey6g=", "timing": 0.01},
            "step6_set_6g": {"success": True, "output": f"PreSharedKey={psk}", "timing": 0.01},
            "step7_readback_6g": {"success": True, "output": f"GetterPreSharedKey6g={psk}", "timing": 0.01},
            "step8_restore_6g": {"success": True, "output": "RestoredPreSharedKey6g=", "timing": 0.01},
            "step9_baseline_24g": {"success": True, "output": "BaselinePreSharedKey24g=\nBaselineWpaPsk24g=", "timing": 0.01},
            "step10_set_24g": {"success": True, "output": f"PreSharedKey={psk}", "timing": 0.01},
            "step11_readback_24g": {"success": True, "output": f"GetterPreSharedKey24g={psk}", "timing": 0.01},
            "step12_restore_24g": {"success": True, "output": "RestoredPreSharedKey24g=", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d089, d089_results) is True

    # Wrong readback on 5G (still empty after setter)
    d089_bad_5g = {
        "steps": {
            **d089_results["steps"],
            "step3_readback_5g": {"success": True, "output": "GetterPreSharedKey5g=", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d089, d089_bad_5g) is False

    # Restore didn't clear on 2.4G
    d089_bad_restore = {
        "steps": {
            **d089_results["steps"],
            "step12_restore_24g": {"success": True, "output": f"RestoredPreSharedKey24g={psk}", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d089, d089_bad_restore) is False


def test_d090_rekeyinginterval_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d090 = load_case(cases_dir / "D090_rekeyinginterval.yaml")
    assert d090["id"] == "wifi-llapi-D090-rekeyinginterval"
    assert d090["source"]["row"] == 90
    assert d090["source"]["api"] == "RekeyingInterval"
    assert d090["bands"] == ["5g", "6g", "2.4g"]
    assert len(d090["steps"]) == 12
    assert len(d090["pass_criteria"]) == 15
    assert all(s.get("target") == "DUT" for s in d090["steps"])
    assert "STA" not in d090["topology"]["devices"]


def test_d090_rekeyinginterval_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d090 = load_case(cases_dir / "D090_rekeyinginterval.yaml")

    assert plugin.setup_env(d090, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d090, topology)


def test_d090_rekeyinginterval_setter_step_keeps_original_command():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d090 = load_case(cases_dir / "D090_rekeyinginterval.yaml")

    for index, expected in [
        (1, "ubus-cli WiFi.AccessPoint.1.Security.RekeyingInterval=0"),
        (5, "ubus-cli WiFi.AccessPoint.3.Security.RekeyingInterval=0"),
        (9, "ubus-cli WiFi.AccessPoint.5.Security.RekeyingInterval=0"),
    ]:
        commands, reason = plugin._command_resolver.resolve(
            d090,
            d090["steps"][index],
            _FakeTopology(),
        )
        assert commands == [expected]
        assert reason == ""


def test_d090_rekeyinginterval_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d090 = load_case(cases_dir / "D090_rekeyinginterval.yaml")

    d090_results = {
        "steps": {
            "step1_baseline_5g": {"success": True, "output": "BaselineRekeyingInterval5g=0\nBaselineHostapdRekey5g=0", "timing": 0.01},
            "step2_set_5g": {"success": True, "output": "WiFi.AccessPoint.1.Security.\nWiFi.AccessPoint.1.Security.RekeyingInterval=0", "timing": 0.01},
            "step3_readback_5g": {"success": True, "output": "GetterRekeyingInterval5g=0\nHostapdRekey5g=0", "timing": 0.01},
            "step4_restore_5g": {"success": True, "output": "RestoredRekeyingInterval5g=0", "timing": 0.01},
            "step5_baseline_6g": {"success": True, "output": "BaselineRekeyingInterval6g=0\nBaselineHostapdRekey6g=0", "timing": 0.01},
            "step6_set_6g": {"success": True, "output": "WiFi.AccessPoint.3.Security.\nWiFi.AccessPoint.3.Security.RekeyingInterval=0", "timing": 0.01},
            "step7_readback_6g": {"success": True, "output": "GetterRekeyingInterval6g=0\nHostapdRekey6g=0", "timing": 0.01},
            "step8_restore_6g": {"success": True, "output": "RestoredRekeyingInterval6g=0", "timing": 0.01},
            "step9_baseline_24g": {"success": True, "output": "BaselineRekeyingInterval24g=0\nBaselineHostapdRekey24g=0", "timing": 0.01},
            "step10_set_24g": {"success": True, "output": "WiFi.AccessPoint.5.Security.\nWiFi.AccessPoint.5.Security.RekeyingInterval=0", "timing": 0.01},
            "step11_readback_24g": {"success": True, "output": "GetterRekeyingInterval24g=0\nHostapdRekey24g=0", "timing": 0.01},
            "step12_restore_24g": {"success": True, "output": "RestoredRekeyingInterval24g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d090, d090_results) is True

    # Baseline hostapd drift means workbook cross-check fails
    d090_bad_baseline = {
        "steps": {
            **d090_results["steps"],
            "step1_baseline_5g": {"success": True, "output": "BaselineRekeyingInterval5g=0\nBaselineHostapdRekey5g=3600", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d090, d090_bad_baseline) is False

    # Readback didn't stay at row-90 zero shape
    d090_bad_readback = {
        "steps": {
            **d090_results["steps"],
            "step7_readback_6g": {"success": True, "output": "GetterRekeyingInterval6g=3600\nHostapdRekey6g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d090, d090_bad_readback) is False

    # Restore didn't work
    d090_bad_restore = {
        "steps": {
            **d090_results["steps"],
            "step12_restore_24g": {"success": True, "output": "RestoredRekeyingInterval24g=3600", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d090, d090_bad_restore) is False


# ---------------------------------------------------------------------------
# D091 SHA256Enable — Fail-shaped mismatch (setter accepted, hostapd unchanged)
# ---------------------------------------------------------------------------

def test_d091_sha256enable_contract():
    """D091 YAML loads with 12 steps, 9 pass_criteria, row=93, all-band Fail."""
    from testpilot.schema.case_schema import load_case
    c = load_case("plugins/wifi_llapi/cases/D091_sha256enable.yaml")
    assert len(c["steps"]) == 12
    assert len(c["pass_criteria"]) == 9
    assert c["source"]["row"] == 93


def test_d091_sha256enable_setup_env_uses_only_dut_transport(monkeypatch):
    """D091 is DUT-only (no STA); setup_env should only request COM0."""
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d091 = load_case(cases_dir / "D091_sha256enable.yaml")

    assert plugin.setup_env(d091, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d091, topology)


def test_d091_sha256enable_evaluate_live_examples():
    """D091 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d091 = load_case(cases_dir / "D091_sha256enable.yaml")

    d091_results = {
        "steps": {
            "step1_baseline_5g": {"success": True, "output": "BaselineSHA256Enable5g=0\nBaselineWpaKeyMgmt5g=WPA-PSK", "timing": 0.01},
            "step2_set_5g": {"success": True, "output": "", "timing": 0.01},
            "step3_readback_5g": {"success": True, "output": "GetterSHA256Enable5g=1\nHostapdWpaKeyMgmt5g=WPA-PSK", "timing": 0.01},
            "step4_restore_5g": {"success": True, "output": "RestoredSHA256Enable5g=0", "timing": 0.01},
            "step5_baseline_6g": {"success": True, "output": "BaselineSHA256Enable6g=0\nBaselineWpaKeyMgmt6g=SAE", "timing": 0.01},
            "step6_set_6g": {"success": True, "output": "", "timing": 0.01},
            "step7_readback_6g": {"success": True, "output": "GetterSHA256Enable6g=1\nHostapdWpaKeyMgmt6g=SAE", "timing": 0.01},
            "step8_restore_6g": {"success": True, "output": "RestoredSHA256Enable6g=0", "timing": 0.01},
            "step9_baseline_24g": {"success": True, "output": "BaselineSHA256Enable24g=0\nBaselineWpaKeyMgmt24g=WPA-PSK", "timing": 0.01},
            "step10_set_24g": {"success": True, "output": "", "timing": 0.01},
            "step11_readback_24g": {"success": True, "output": "GetterSHA256Enable24g=1\nHostapdWpaKeyMgmt24g=WPA-PSK", "timing": 0.01},
            "step12_restore_24g": {"success": True, "output": "RestoredSHA256Enable24g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d091, d091_results) is True

    # Negative: if readback stays 0 on 5G, evaluation should fail
    d091_bad = {
        "steps": {
            **d091_results["steps"],
            "step3_readback_5g": {"success": True, "output": "GetterSHA256Enable5g=0\nHostapdWpaKeyMgmt5g=WPA-PSK", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d091, d091_bad) is False


# ---------------------------------------------------------------------------
# D092 WEPKey — Fail-shaped mismatch (setter accepted, no WEP in hostapd)
# ---------------------------------------------------------------------------

def test_d092_wepkey_contract():
    """D092 YAML loads with workbook row 92 and Pass/Not Supported/Pass semantics."""
    from testpilot.schema.case_schema import load_case
    c = load_case("plugins/wifi_llapi/cases/D092_wepkey_accesspoint_security.yaml")
    assert len(c["steps"]) == 12
    assert len(c["pass_criteria"]) == 21
    assert c["source"]["row"] == 92


def test_d092_wepkey_setup_env_uses_only_dut_transport(monkeypatch):
    """D092 is DUT-only (no STA); setup_env should only request COM0."""
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d092 = load_case(cases_dir / "D092_wepkey_accesspoint_security.yaml")

    assert plugin.setup_env(d092, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d092, topology)


def test_d092_wepkey_setter_steps_keep_original_commands():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d092 = load_case(cases_dir / "D092_wepkey_accesspoint_security.yaml")

    commands, reason = plugin._command_resolver.resolve(d092, d092["steps"][1], None)
    assert commands == [
        "ubus-cli WiFi.AccessPoint.1.Security.ModeEnabled=WEP-128",
        "sleep 2",
        "ubus-cli WiFi.AccessPoint.1.Security.WEPKey=AABBCCDDEEFF0",
    ]
    assert reason == ""

    commands, reason = plugin._command_resolver.resolve(d092, d092["steps"][9], None)
    assert commands == [
        "ubus-cli WiFi.AccessPoint.5.Security.ModeEnabled=WEP-128",
        "sleep 2",
        "ubus-cli WiFi.AccessPoint.5.Security.WEPKey=AABBCCDDEEFF0",
    ]
    assert reason == ""


def test_d092_wepkey_evaluate_live_examples():
    """D092 uses WEP-128 on 5G/2.4G and unsupported proof on 6G."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d092 = load_case(cases_dir / "D092_wepkey_accesspoint_security.yaml")

    d092_results = {
        "steps": {
            "step1_baseline_5g": {"success": True, "output": "ModesSupported5g=None,WEP-64,WEP-128,WEP-128iv,WPA-Personal\nBaselineModeEnabled5g=WPA2-Personal\nHostapdWep5g=ABSENT", "timing": 0.01},
            "step2_set_5g": {"success": True, "output": "WiFi.AccessPoint.1.Security.WEPKey=\"AABBCCDDEEFF0\"", "timing": 0.01},
            "step3_readback_5g": {"success": True, "output": "GetterModeEnabled5g=WEP-128\nGetterWEPKey5g=AABBCCDDEEFF0\nHostapdWepAfter5g=wep_key0=AABBCCDDEEFF0", "timing": 0.01},
            "step4_restore_5g": {"success": True, "output": "RestoredModeEnabled5g=WPA2-Personal\nRestoredHostapdWep5g=ABSENT", "timing": 0.01},
            "step5_baseline_6g": {"success": True, "output": "ModesSupported6g=None,WPA3-Personal,OWE\nBaselineModeEnabled6g=WPA3-Personal\nHostapdWep6g=ABSENT", "timing": 0.01},
            "step6_set_6g": {"success": True, "output": "SkippedSet6g=unsupported_by_modes_supported", "timing": 0.01},
            "step7_readback_6g": {"success": True, "output": "ModesSupportedAfter6g=None,WPA3-Personal,OWE\nGetterModeEnabled6g=WPA3-Personal\nHostapdWepAfter6g=ABSENT", "timing": 0.01},
            "step8_restore_6g": {"success": True, "output": "RestoredModeEnabled6g=WPA3-Personal\nRestoredHostapdWep6g=ABSENT", "timing": 0.01},
            "step9_baseline_24g": {"success": True, "output": "ModesSupported24g=None,WEP-64,WEP-128,WEP-128iv,WPA-Personal\nBaselineModeEnabled24g=WPA2-Personal\nHostapdWep24g=ABSENT", "timing": 0.01},
            "step10_set_24g": {"success": True, "output": "WiFi.AccessPoint.5.Security.WEPKey=\"AABBCCDDEEFF0\"", "timing": 0.01},
            "step11_readback_24g": {"success": True, "output": "GetterModeEnabled24g=WEP-128\nGetterWEPKey24g=AABBCCDDEEFF0\nHostapdWepAfter24g=wep_key0=AABBCCDDEEFF0", "timing": 0.01},
            "step12_restore_24g": {"success": True, "output": "RestoredModeEnabled24g=WPA2-Personal\nRestoredHostapdWep24g=ABSENT", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d092, d092_results) is True

    # Negative: if 5G never exposes wep_key after switching to WEP-128, evaluation should fail
    d092_bad = {
        "steps": {
            **d092_results["steps"],
            "step3_readback_5g": {"success": True, "output": "GetterModeEnabled5g=WEP-128\nGetterWEPKey5g=AABBCCDDEEFF0\nHostapdWepAfter5g=ABSENT", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d092, d092_bad) is False

    # Negative: if 6G suddenly claims WEP-128 support, unsupported proof should fail
    d092_bad_6g = {
        "steps": {
            **d092_results["steps"],
            "step7_readback_6g": {"success": True, "output": "ModesSupportedAfter6g=None,WEP-128,WPA3-Personal,OWE\nGetterModeEnabled6g=WPA3-Personal\nHostapdWepAfter6g=ABSENT", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d092, d092_bad_6g) is False


def test_d093_ssidadvertisementenabled_contract():
    """D093 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d093 = load_case(cases_dir / "D093_ssidadvertisementenabled.yaml")
    assert d093["source"]["row"] == 93
    assert d093["source"]["api"] == "SSIDAdvertisementEnabled"
    assert len(d093["steps"]) == 12
    assert len(d093["pass_criteria"]) == 15
    assert d093["bands"] == ["5g", "6g", "2.4g"]


def test_d093_ssidadvertisementenabled_setup_env_uses_only_dut_transport(monkeypatch):
    """D093 topology uses DUT-only; setup_env should not require STA."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d093 = load_case(cases_dir / "D093_ssidadvertisementenabled.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d093, topology=topo) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d093, topo)


def test_d093_ssidadvertisementenabled_setter_steps_keep_original_commands():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d093 = load_case(cases_dir / "D093_ssidadvertisementenabled.yaml")

    commands, reason = plugin._command_resolver.resolve(d093, d093["steps"][1], None)
    assert commands == ["ubus-cli WiFi.AccessPoint.1.SSIDAdvertisementEnabled=1"]
    assert reason == ""

    commands, reason = plugin._command_resolver.resolve(d093, d093["steps"][5], None)
    assert commands == ["ubus-cli WiFi.AccessPoint.3.SSIDAdvertisementEnabled=1"]
    assert reason == ""

    commands, reason = plugin._command_resolver.resolve(d093, d093["steps"][9], None)
    assert commands == ["ubus-cli WiFi.AccessPoint.5.SSIDAdvertisementEnabled=1"]
    assert reason == ""


def test_d093_ssidadvertisementenabled_evaluate_live_examples():
    """D093 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d093 = load_case(cases_dir / "D093_ssidadvertisementenabled.yaml")

    d093_results = {
        "steps": {
            "step1_baseline_5g": {"success": True, "output": "BaselineAdv5g=1\nBaselineHapd5g=0", "timing": 0.01},
            "step2_set_5g": {"success": True, "output": "", "timing": 0.01},
            "step3_readback_5g": {"success": True, "output": "GetterAdv5g=1\nHapdAfterSet5g=0", "timing": 0.01},
            "step4_restore_5g": {"success": True, "output": "RestoredAdv5g=1\nRestoredHapd5g=0", "timing": 0.01},
            "step5_baseline_6g": {"success": True, "output": "BaselineAdv6g=1\nBaselineHapd6g=0", "timing": 0.01},
            "step6_set_6g": {"success": True, "output": "", "timing": 0.01},
            "step7_readback_6g": {"success": True, "output": "GetterAdv6g=1\nHapdAfterSet6g=0", "timing": 0.01},
            "step8_restore_6g": {"success": True, "output": "RestoredAdv6g=1\nRestoredHapd6g=0", "timing": 0.01},
            "step9_baseline_24g": {"success": True, "output": "BaselineAdv24g=1\nBaselineHapd24g=0", "timing": 0.01},
            "step10_set_24g": {"success": True, "output": "", "timing": 0.01},
            "step11_readback_24g": {"success": True, "output": "GetterAdv24g=1\nHapdAfterSet24g=0", "timing": 0.01},
            "step12_restore_24g": {"success": True, "output": "RestoredAdv24g=1\nRestoredHapd24g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d093, d093_results) is True

    # Negative: if setter unexpectedly hides the SSID, evaluation should fail
    d093_bad = {
        "steps": {
            **d093_results["steps"],
            "step3_readback_5g": {"success": True, "output": "GetterAdv5g=0\nHapdAfterSet5g=2", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d093, d093_bad) is False


def test_d094_status_accesspoint_contract():
    """D094 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d094 = load_case(cases_dir / "D094_status_accesspoint.yaml")
    assert d094["source"]["row"] == 94
    assert d094["source"]["api"] == "Status"
    assert len(d094["steps"]) == 3
    assert len(d094["pass_criteria"]) == 6
    assert d094["bands"] == ["5g", "6g", "2.4g"]


def test_d094_status_accesspoint_setup_env(monkeypatch):
    """D094 is DUT-only; setup_env should only request COM0."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d094 = load_case(cases_dir / "D094_status_accesspoint.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d094, topology=topo) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d094, topo)


def test_d094_status_accesspoint_evaluate_live_examples():
    """D094 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d094 = load_case(cases_dir / "D094_status_accesspoint.yaml")

    d094_results = {
        "steps": {
            "step1_status_5g": {"success": True, "output": "Status5g=Enabled\nDriverBss5g=up", "timing": 0.01},
            "step2_status_6g": {"success": True, "output": "Status6g=Enabled\nDriverBss6g=up", "timing": 0.01},
            "step3_status_24g": {"success": True, "output": "Status24g=Enabled\nDriverBss24g=up", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d094, d094_results) is True

    # Negative: if Status is Disabled, should fail
    d094_bad = {
        "steps": {
            **d094_results["steps"],
            "step1_status_5g": {"success": True, "output": "Status5g=Disabled\nDriverBss5g=down", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d094, d094_bad) is False


def test_d095_uapsdcapability_contract():
    """D095 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d095 = load_case(cases_dir / "D095_uapsdcapability.yaml")
    assert d095["source"]["row"] == 95
    assert d095["source"]["api"] == "UAPSDCapability"
    assert len(d095["steps"]) == 3
    assert len(d095["pass_criteria"]) == 3
    assert d095["bands"] == ["5g", "6g", "2.4g"]


def test_d095_uapsdcapability_setup_env(monkeypatch):
    """D095 is DUT-only; setup_env should only request COM0."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d095 = load_case(cases_dir / "D095_uapsdcapability.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d095, topology=topo) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d095, topo)


def test_d095_uapsdcapability_evaluate_live_examples():
    """D095 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d095 = load_case(cases_dir / "D095_uapsdcapability.yaml")

    d095_results = {
        "steps": {
            "step1_uapsd_5g": {"success": True, "output": "UAPSDCapability5g=1\nHapdUapsd5g=0\nDriverWmeApsd5g=0", "timing": 0.01},
            "step2_uapsd_6g": {"success": True, "output": "UAPSDCapability6g=1\nHapdUapsd6g=0\nDriverWmeApsd6g=0", "timing": 0.01},
            "step3_uapsd_24g": {"success": True, "output": "UAPSDCapability24g=1\nHapdUapsd24g=0\nDriverWmeApsd24g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d095, d095_results) is True

    # Negative: if capability is 0, should fail
    d095_bad = {
        "steps": {
            **d095_results["steps"],
            "step1_uapsd_5g": {"success": True, "output": "UAPSDCapability5g=0\nHapdUapsd5g=0\nDriverWmeApsd5g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d095, d095_bad) is False


# ── Removed stale rows must stay absent after inventory alignment ───────────


@pytest.mark.parametrize(
    ("filename", "case_id"),
    [
        ("D096_uapsdenable.yaml", "wifi-llapi-D096-uapsdenable"),
        ("D097_vendorie.yaml", "wifi-llapi-D097-vendorie"),
        ("D100_wmmenable.yaml", "wifi-llapi-D100-wmmenable"),
        ("D102_configmethodssupported.yaml", "wifi-llapi-D102-configmethodssupported"),
        ("D106_relaycredentialsenable.yaml", "wifi-llapi-D106-relaycredentialsenable"),
        ("D474_channel_radio_37.yaml", "wifi-llapi-D474-channel-radio-37"),
    ],
)
def test_stale_deleted_cases_remain_absent(filename: str, case_id: str):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    assert not (cases_dir / filename).exists()
    discoverable = {case["id"] for case in plugin.discover_cases()}
    assert case_id not in discoverable


# ── D098 WDSEnable (Pass, all 3 bands setter round-trip) ────────────


def test_d098_wdsenable_contract():
    """D098 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D098_wdsenable.yaml")
    assert case["source"]["row"] == 98
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 18
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d098_wdsenable_setup_env(monkeypatch):
    """D098 is DUT-only; setup_env should only request COM0."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d098 = load_case(cases_dir / "D098_wdsenable.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d098, topology=topo) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d098, topo)


def test_d098_wdsenable_evaluate():
    """D098 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d098 = load_case(cases_dir / "D098_wdsenable.yaml")
    d098_results = {
        "steps": {
            "step_5g_setter_roundtrip": {
                "success": True,
                "output": (
                    "Baseline5g=0\nDriverBaseline5g=0\n"
                    "AfterSet5g=1\nDriverAfterSet5g=1\n"
                    "AfterRestore5g=0\nDriverAfterRestore5g=0"
                ),
                "timing": 0.01,
            },
            "step_6g_setter_roundtrip": {
                "success": True,
                "output": (
                    "Baseline6g=0\nDriverBaseline6g=0\n"
                    "AfterSet6g=1\nDriverAfterSet6g=1\n"
                    "AfterRestore6g=0\nDriverAfterRestore6g=0"
                ),
                "timing": 0.01,
            },
            "step_24g_setter_roundtrip": {
                "success": True,
                "output": (
                    "Baseline24g=0\nDriverBaseline24g=0\n"
                    "AfterSet24g=1\nDriverAfterSet24g=1\n"
                    "AfterRestore24g=0\nDriverAfterRestore24g=0"
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d098, d098_results) is True




def test_d099_wmmcapability_contract():
    """D099 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D099_wmmcapability.yaml")
    assert case["source"]["row"] == 99
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 6
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d099_wmmcapability_setup_env(monkeypatch):
    """D099 is DUT-only; setup_env should only request COM0."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d099 = load_case(cases_dir / "D099_wmmcapability.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d099, topology=topo) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    plugin.teardown(d099, topo)


def test_d099_wmmcapability_evaluate():
    """D099 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d099 = load_case(cases_dir / "D099_wmmcapability.yaml")
    results = {
        "steps": {
            "step_5g_getter": {
                "success": True,
                "output": "WMMCapability5g=1\nHapdWmm5g=1",
                "timing": 0.01,
            },
            "step_6g_getter": {
                "success": True,
                "output": "WMMCapability6g=1\nHapdWmm6g=1",
                "timing": 0.01,
            },
            "step_24g_getter": {
                "success": True,
                "output": "WMMCapability24g=1\nHapdWmm24g=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d099, results) is True


def test_d101_configmethodsenabled_contract():
    """D101 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D101_configmethodsenabled.yaml")
    assert case["source"]["row"] == 101
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 6


def test_d101_configmethodsenabled_setup_env(monkeypatch):
    """D101 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d101 = load_case(cases_dir / "D101_configmethodsenabled.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d101, topology=topo) is True
    plugin.teardown(d101, topo)


def test_d101_configmethodsenabled_stays_getter_only():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d101 = load_case(cases_dir / "D101_configmethodsenabled.yaml")

    commands, reason = plugin._command_resolver.resolve(d101, d101["steps"][0], None)
    assert reason == ""
    joined = "\n".join(commands)
    assert "WiFi.AccessPoint.1.WPS.ConfigMethodsEnabled?" in joined
    assert "WiFi.AccessPoint.1.WPS.ConfigMethodsEnabled=PushButton" not in joined
    assert "grep 'ConfigMethodsEnabled='" in joined
    assert "tr -d" in joined

    commands, reason = plugin._command_resolver.resolve(d101, d101["steps"][1], None)
    assert reason == ""
    joined = "\n".join(commands)
    assert "WiFi.AccessPoint.3.WPS.ConfigMethodsEnabled?" in joined
    assert "WiFi.AccessPoint.3.WPS.ConfigMethodsEnabled=PushButton" not in joined
    assert "grep 'ConfigMethodsEnabled='" in joined
    assert "tr -d" in joined

    commands, reason = plugin._command_resolver.resolve(d101, d101["steps"][2], None)
    assert reason == ""
    joined = "\n".join(commands)
    assert "WiFi.AccessPoint.5.WPS.ConfigMethodsEnabled?" in joined
    assert "WiFi.AccessPoint.5.WPS.ConfigMethodsEnabled=PushButton" not in joined
    assert "grep 'ConfigMethodsEnabled='" in joined
    assert "tr -d" in joined


def test_d101_configmethodsenabled_evaluate():
    """D101 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d101 = load_case(cases_dir / "D101_configmethodsenabled.yaml")
    results = {
        "steps": {
            "step_5g_getter": {
                "success": True,
                "output": (
                    "CfgEnabled5g=PhysicalPushButton,VirtualPushButton\n"
                    "HapdCfg5g=physical_push_button virtual_push_button"
                ),
                "timing": 0.01,
            },
            "step_6g_getter": {
                "success": True,
                "output": "CfgEnabled6g=None\nHapdCfg6g=",
                "timing": 0.01,
            },
            "step_24g_getter": {
                "success": True,
                "output": (
                    "CfgEnabled24g=PhysicalPushButton,VirtualPushButton\n"
                    "HapdCfg24g=physical_push_button virtual_push_button"
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d101, results) is True

    d101_bad = {
        "steps": {
            **results["steps"],
            "step_6g_getter": {
                "success": True,
                "output": "CfgEnabled6g=None\nHapdCfg6g=physical_push_button virtual_push_button",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d101, d101_bad) is False


def test_d103_configured_contract():
    """D103 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D103_configured.yaml")
    assert case["source"]["row"] == 103
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3


def test_d103_configured_evaluate():
    """D103 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d103 = load_case(cases_dir / "D103_configured.yaml")
    results = {
        "steps": {
            "step_5g_getter": {
                "success": True,
                "output": "Configured5g=1",
                "timing": 0.01,
            },
            "step_6g_getter": {
                "success": True,
                "output": "Configured6g=1",
                "timing": 0.01,
            },
            "step_24g_getter": {
                "success": True,
                "output": "Configured24g=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d103, results) is True


def test_d104_wps_enable_contract():
    """D104 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D104_enable_accesspoint_wps.yaml")
    assert case["source"]["row"] == 104
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 12
    step_24g = "\n".join(case["steps"][2]["command"])
    assert 'WiFi.AccessPoint.5.WPS.Enable=1' in step_24g
    assert any(
        criterion["field"] == "wps_24g.AfterSet24g" and criterion["value"] == "1"
        for criterion in case["pass_criteria"]
    )


def test_d104_wps_enable_setup_env(monkeypatch):
    """D104 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d104 = load_case(cases_dir / "D104_enable_accesspoint_wps.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d104, topology=topo) is True
    plugin.teardown(d104, topo)


def test_d104_wps_enable_evaluate():
    """D104 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d104 = load_case(cases_dir / "D104_enable_accesspoint_wps.yaml")
    results = {
        "steps": {
            "step_5g_setter": {
                "success": True,
                "output": "Baseline5g=0\nWpsState5gBaseline=0\nAfterSet5g=1\nWpsState5gAfter=2\nRestore5g=0\nWpsState5gRestore=0",
                "timing": 0.01,
            },
            "step_6g_setter": {
                "success": True,
                "output": "Baseline6g=0\nWpsState6gBaseline=0\nAfterSet6g=1\nWpsState6gAfter=0\nRestore6g=0\nWpsState6gRestore=0",
                "timing": 0.01,
            },
            "step_24g_setter": {
                "success": True,
                "output": "Baseline24g=0\nWpsState24gBaseline=0\nAfterSet24g=1\nWpsState24gAfter=2\nRestore24g=0\nWpsState24gRestore=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d104, results) is True


def test_d105_pairinginprogress_contract():
    """D105 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D105_pairinginprogress_accesspoint_wps.yaml")
    assert case["source"]["row"] == 105
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 5


def test_d105_pairinginprogress_evaluate():
    """D105 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d105 = load_case(cases_dir / "D105_pairinginprogress_accesspoint_wps.yaml")
    results = {
        "steps": {
            "step_5g_pbc": {
                "success": True,
                "output": "PairingInProgress5g=1\nPbcStatus5g=Active",
                "timing": 0.01,
            },
            "step_6g_pbc": {
                "success": True,
                "output": "PairingInProgress6g=0",
                "timing": 0.01,
            },
            "step_24g_pbc": {
                "success": True,
                "output": "PairingInProgress24g=1\nPbcStatus24g=Active",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d105, results) is True


def test_d107_selfpin_contract():
    """D107 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D107_selfpin.yaml")
    assert case["source"]["row"] == 107
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 9
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d107_selfpin_setup_env(monkeypatch):
    """D107 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d107 = load_case(cases_dir / "D107_selfpin.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d107, topology=topo) is True
    plugin.teardown(d107, topo)


def test_d107_selfpin_evaluate():
    """D107 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d107 = load_case(cases_dir / "D107_selfpin.yaml")
    results = {
        "steps": {
            "step_5g_setter": {
                "success": True,
                "output": "Baseline5g=90455865\nAfterSet5g=12345678\nRestore5g=90455865",
                "timing": 0.01,
            },
            "step_6g_setter": {
                "success": True,
                "output": "Baseline6g=90455865\nAfterSet6g=12345678\nRestore6g=90455865",
                "timing": 0.01,
            },
            "step_24g_setter": {
                "success": True,
                "output": "Baseline24g=90455865\nAfterSet24g=12345678\nRestore24g=90455865",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d107, results) is True



def test_d108_uuid_contract():
    """D108 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D108_uuid.yaml")
    assert case["source"]["row"] == 108
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 6
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d108_uuid_setup_env(monkeypatch):
    """D108 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d108 = load_case(cases_dir / "D108_uuid.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d108, topology=topo) is True
    plugin.teardown(d108, topo)


def test_d108_uuid_evaluate():
    """D108 all-pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d108 = load_case(cases_dir / "D108_uuid.yaml")
    results = {
        "steps": {
            "step1_5g": {
                "success": True,
                "output": "UUID5g=47584a4e-464c-f545-f64e-4e4547584a4e\nHostapdUuid5g=47584a4e-464c-f545-f64e-4e4547584a4e",
                "timing": 0.01,
            },
            "step2_6g": {
                "success": True,
                "output": "UUID6g=47584a4e-464c-f545-f64e-4e4547584a4e\nHostapdUuid6g=",
                "timing": 0.01,
            },
            "step3_24g": {
                "success": True,
                "output": "UUID24g=47584a4e-464c-f545-f64e-4e4547584a4e\nHostapdUuid24g=47584a4e-464c-f545-f64e-4e4547584a4e",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d108, results) is True


def test_d109_getstationstats_accesspoint_contract():
    """D109 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D109_getstationstats.yaml")
    assert case["source"]["row"] == 109
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 2
    assert len(case["pass_criteria"]) == 4
    assert case["bands"] == ["5g"]


def test_d109_getstationstats_accesspoint_setup_env(monkeypatch):
    """D109 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d109 = load_case(cases_dir / "D109_getstationstats.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d109, topology=topo) is True
    plugin.teardown(d109, topo)


def test_hostapd_cli_step_does_not_fallback_to_verification_command():
    plugin = _load_plugin()
    case = {
        "id": "wifi-llapi-hostapd-cli-regression",
        "verification_command": ['wl -i wl0 assoclist'],
        "steps": [
            {
                "id": "step1_hostapd",
                "command": "hostapd_cli -i wl0 all_sta 2>/dev/null | grep -m1 '^addr='",
            }
        ],
    }

    commands, reason = plugin._command_resolver.resolve(case, case["steps"][0], None)

    assert reason == ""
    assert commands == ["hostapd_cli -i wl0 all_sta 2>/dev/null | grep -m1 '^addr='"]


def test_d109_getstationstats_accesspoint_evaluate():
    """D109 all-pass criteria met with live-shaped getStationStats output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d109 = load_case(cases_dir / "D109_getstationstats.yaml")
    results = {
        "steps": {
            "step1_assoc_precheck": {
                "success": True,
                "output": "AssocMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_getstationstats": {
                "success": True,
                "output": "StationStatsMac=2C:59:17:00:04:85\nTopLevelActive=1\nStatsMatchesAssoc=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d109, results) is True


def test_d110_getstationstats_active_contract():
    """D110 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D110_getstationstats_active.yaml")
    assert case["source"]["row"] == 110
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 5
    assert case["bands"] == ["5g"]


def test_d110_getstationstats_active_setup_env(monkeypatch):
    """D110 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D110_getstationstats_active.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d110_getstationstats_active_evaluate():
    """D110 pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D110_getstationstats_active.yaml")
    results = {
        "steps": {
            "step1_assoc_precheck": {
                "success": True,
                "output": "AssocMac=2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_getstationstats": {
                "success": True,
                "output": "StationStatsMac=2C:59:17:00:04:85\nTopLevelActive=1\nStatsMatchesAssoc=1",
                "timing": 0.01,
            },
            "step3_sta_info_state": {
                "success": True,
                "output": "DriverStateLine=state:_AUTHENTICATED_ASSOCIATED_AUTHORIZED\nDriverAuthorized=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d115_getstationstats_associationtime_contract():
    """D115 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D111_getstationstats_associationtime.yaml")
    assert case["source"]["row"] == 111
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 2
    assert len(case["pass_criteria"]) == 2
    assert case["bands"] == ["5g"]


def test_d115_getstationstats_associationtime_setup_env(monkeypatch):
    """D115 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D111_getstationstats_associationtime.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d115_getstationstats_associationtime_evaluate():
    """D115 pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D111_getstationstats_associationtime.yaml")
    results = {
        "steps": {
            "step1_assoc_precheck": {
                "success": True,
                "output": "2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_getstationstats": {
                "success": True,
                "output": 'AssociationTime = "2026-03-19T10:18:49Z",',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d115_getstationstats_authenticationstate_contract():
    """D115 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D112_getstationstats_authenticationstate.yaml")
    assert case["source"]["row"] == 112
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 2
    assert len(case["pass_criteria"]) == 2
    assert case["bands"] == ["5g"]


def test_d115_getstationstats_authenticationstate_setup_env(monkeypatch):
    """D115 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D112_getstationstats_authenticationstate.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d115_getstationstats_authenticationstate_evaluate():
    """D115 pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D112_getstationstats_authenticationstate.yaml")
    results = {
        "steps": {
            "step1_assoc_precheck": {
                "success": True,
                "output": "2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_getstationstats": {
                "success": True,
                "output": "AuthenticationState=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d115_getstationstats_avgsignalstrength_contract():
    """D115 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D113_getstationstats_avgsignalstrength.yaml")
    assert case["source"]["row"] == 113
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 2
    assert len(case["pass_criteria"]) == 2
    assert case["bands"] == ["5g"]


def test_d115_getstationstats_avgsignalstrength_setup_env(monkeypatch):
    """D115 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D113_getstationstats_avgsignalstrength.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d115_getstationstats_avgsignalstrength_evaluate():
    """D115 pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D113_getstationstats_avgsignalstrength.yaml")
    results = {
        "steps": {
            "step1_assoc_precheck": {
                "success": True,
                "output": "2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step2_getstationstats": {
                "success": True,
                "output": "AvgSignalStrength=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d115_getstationstats_avgsignalstrengthbychain_contract():
    """D115 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D114_getstationstats_avgsignalstrengthbychain.yaml")
    assert case["source"]["row"] == 114
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert len(case["pass_criteria"]) == 9
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d115_getstationstats_avgsignalstrengthbychain_setup_env(monkeypatch):
    """D115 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D114_getstationstats_avgsignalstrengthbychain.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d115_getstationstats_avgsignalstrengthbychain_evaluate():
    """D115 pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D114_getstationstats_avgsignalstrengthbychain.yaml")
    results = {
        "steps": {
            "step1_5g_sta_join": {
                "success": True,
                "output": "Connected to testpilot5G",
                "timing": 0.01,
            },
            "step2_5g_assoc": {
                "success": True,
                "output": "2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3_5g_getstationstats": {
                "success": True,
                "output": "AvgSignalStrengthByChain=-34",
                "timing": 0.01,
            },
            "step4_6g_sta_join": {
                "success": True,
                "output": "Connected to testpilot6G",
                "timing": 0.01,
            },
            "step5_6g_assoc": {
                "success": True,
                "output": "2C:59:17:00:04:86",
                "timing": 0.01,
            },
            "step6_6g_getstationstats": {
                "success": True,
                "output": "AvgSignalStrengthByChain=-57",
                "timing": 0.01,
            },
            "step7_24g_sta_join": {
                "success": True,
                "output": "Connected to testpilot2G",
                "timing": 0.01,
            },
            "step8_24g_assoc": {
                "success": True,
                "output": "2C:59:17:00:04:87",
                "timing": 0.01,
            },
            "step9_24g_getstationstats": {
                "success": True,
                "output": "AvgSignalStrengthByChain=-16",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d115_getstationstats_connectionduration_contract():
    """D115 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D115_getstationstats_connectionduration.yaml")
    assert case["source"]["row"] == 115
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 15
    assert len(case["pass_criteria"]) == 12
    assert case["bands"] == ["5g", "6g", "2.4g"]
    d115_links = {link["band"] for link in case["topology"]["links"]}
    assert d115_links == {"5g", "6g", "2.4g"}
    d115_commands = "\n".join(str(step.get("command", "")) for step in case["steps"])
    assert 'WiFi.AccessPoint.3.getStationStats()' in d115_commands
    assert "DriverConnectionSeconds5g=" in d115_commands
    assert any(
        criterion["field"] == "result_after_wait_5g.ConnectionDuration"
        and criterion["reference"] == "result_5g.ConnectionDuration"
        for criterion in case["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_duration_6g.DriverConnectionSeconds6g"
        and criterion["reference"] == "result_after_wait_6g.ConnectionDuration"
        for criterion in case["pass_criteria"]
    )
    assert any(
        criterion["field"] == "driver_duration_24g.DriverConnectionSeconds24g"
        and criterion["reference"] == "result_after_wait_24g.ConnectionDuration"
        for criterion in case["pass_criteria"]
    )


def test_d115_getstationstats_connectionduration_setup_env(monkeypatch):
    """D115 needs STA + DUT."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D115_getstationstats_connectionduration.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d115_getstationstats_connectionduration_evaluate():
    """D115 pass criteria met with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D115_getstationstats_connectionduration.yaml")
    results = {
        "steps": {
            "step1_5g_sta_join": {
                "success": True,
                "output": "Connected to testpilot5G",
                "timing": 0.01,
            },
            "step2_5g_assoc": {
                "success": True,
                "output": "assoclist 2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step3_5g_getstationstats": {
                "success": True,
                "output": 'MACAddress="2C:59:17:00:04:85"\nActive=1\nConnectionDuration=13',
                "captured": {"ConnectionDuration": "13"},
                "timing": 0.01,
            },
            "step4_5g_getstationstats_after_wait": {
                "success": True,
                "output": "ConnectionDuration=17",
                "captured": {"ConnectionDuration": "17"},
                "timing": 0.01,
            },
            "step5_5g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds5g=18",
                "captured": {"DriverConnectionSeconds5g": "18"},
                "timing": 0.01,
            },
            "step6_6g_sta_join": {
                "success": True,
                "output": "Connected to testpilot6G",
                "timing": 0.01,
            },
            "step7_6g_assoc": {
                "success": True,
                "output": "assoclist 2C:59:17:00:04:86",
                "timing": 0.01,
            },
            "step8_6g_getstationstats": {
                "success": True,
                "output": "ConnectionDuration=11",
                "captured": {"ConnectionDuration": "11"},
                "timing": 0.01,
            },
            "step9_6g_getstationstats_after_wait": {
                "success": True,
                "output": "ConnectionDuration=15",
                "captured": {"ConnectionDuration": "15"},
                "timing": 0.01,
            },
            "step10_6g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds6g=16",
                "captured": {"DriverConnectionSeconds6g": "16"},
                "timing": 0.01,
            },
            "step11_24g_sta_join": {
                "success": True,
                "output": "Connected to testpilot2G",
                "timing": 0.01,
            },
            "step12_24g_assoc": {
                "success": True,
                "output": "assoclist 2C:59:17:00:04:97",
                "timing": 0.01,
            },
            "step13_24g_getstationstats": {
                "success": True,
                "output": "ConnectionDuration=20",
                "captured": {"ConnectionDuration": "20"},
                "timing": 0.01,
            },
            "step14_24g_getstationstats_after_wait": {
                "success": True,
                "output": "ConnectionDuration=24",
                "captured": {"ConnectionDuration": "24"},
                "timing": 0.01,
            },
            "step15_24g_driver_age": {
                "success": True,
                "output": "DriverConnectionSeconds24g=25",
                "captured": {"DriverConnectionSeconds24g": "25"},
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d117_enable_endpoint_contract():
    """D117 YAML loads, discovers, and has correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D117_enable_endpoint.yaml")
    assert case["source"]["row"] == 117
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d117_enable_endpoint_setup_env(monkeypatch):
    """D117 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d117 = load_case(cases_dir / "D117_enable_endpoint.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(d117, topology=topo) is True
    plugin.teardown(d117, topo)


def test_d117_enable_endpoint_evaluate():
    """D117 pass criteria met with 'No data found' output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d117 = load_case(cases_dir / "D117_enable_endpoint.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": 'WiFi.EndPoint.?\nNo data found',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d117, results) is True



def test_d118_getstats_encryptionmode_contract():
    """D118 getStats() EncryptionMode YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D118_getstats_encryptionmode.yaml")
    assert case["source"]["row"] == 106
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d118_getstats_encryptionmode_setup_env(monkeypatch):
    """D118 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D118_getstats_encryptionmode.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d118_getstats_encryptionmode_evaluate():
    """D118 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D118_getstats_encryptionmode.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d119_getstats_hecapabilities_contract():
    """D119 getStats() HeCapabilities YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D119_getstats_hecapabilities.yaml")
    assert case["source"]["row"] == 121
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d119_getstats_hecapabilities_setup_env(monkeypatch):
    """D119 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D119_getstats_hecapabilities.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d119_getstats_hecapabilities_evaluate():
    """D119 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D119_getstats_hecapabilities.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d120_getstats_htcapabilities_contract():
    """D120 getStats() HtCapabilities YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D120_getstats_htcapabilities.yaml")
    assert case["source"]["row"] == 122
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d120_getstats_htcapabilities_setup_env(monkeypatch):
    """D120 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D120_getstats_htcapabilities.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d120_getstats_htcapabilities_evaluate():
    """D120 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D120_getstats_htcapabilities.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d121_getstats_lastdatadownlinkrate_contract():
    """D121 getStats() LastDataDownlinkRate YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D121_getstats_lastdatadownlinkrate.yaml")
    assert case["source"]["row"] == 123
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d121_getstats_lastdatadownlinkrate_setup_env(monkeypatch):
    """D121 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D121_getstats_lastdatadownlinkrate.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d121_getstats_lastdatadownlinkrate_evaluate():
    """D121 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D121_getstats_lastdatadownlinkrate.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d122_getstats_lastdatauplinkrate_contract():
    """D122 getStats() LastDataUplinkRate YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D122_getstats_lastdatauplinkrate.yaml")
    assert case["source"]["row"] == 124
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d122_getstats_lastdatauplinkrate_setup_env(monkeypatch):
    """D122 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D122_getstats_lastdatauplinkrate.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d122_getstats_lastdatauplinkrate_evaluate():
    """D122 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D122_getstats_lastdatauplinkrate.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d123_getstats_linkbandwidth_contract():
    """D123 getStats() LinkBandwidth YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D123_getstats_linkbandwidth.yaml")
    assert case["source"]["row"] == 125
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d123_getstats_linkbandwidth_setup_env(monkeypatch):
    """D123 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D123_getstats_linkbandwidth.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d123_getstats_linkbandwidth_evaluate():
    """D123 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D123_getstats_linkbandwidth.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d124_getstats_maxrxspatialstreamssupported_contract():
    """D124 getStats() MaxRxSpatialStreamsSupported YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D124_getstats_maxrxspatialstreamssupported.yaml")
    assert case["source"]["row"] == 126
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d124_getstats_maxrxspatialstreamssupported_setup_env(monkeypatch):
    """D124 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D124_getstats_maxrxspatialstreamssupported.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d124_getstats_maxrxspatialstreamssupported_evaluate():
    """D124 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D124_getstats_maxrxspatialstreamssupported.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d125_getstats_maxtxspatialstreamssupported_contract():
    """D125 getStats() MaxTxSpatialStreamsSupported YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D125_getstats_maxtxspatialstreamssupported.yaml")
    assert case["source"]["row"] == 127
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d125_getstats_maxtxspatialstreamssupported_setup_env(monkeypatch):
    """D125 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D125_getstats_maxtxspatialstreamssupported.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d125_getstats_maxtxspatialstreamssupported_evaluate():
    """D125 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D125_getstats_maxtxspatialstreamssupported.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d126_getstats_noise_contract():
    """D126 getStats() Noise YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D126_getstats_noise.yaml")
    assert case["source"]["row"] == 128
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d126_getstats_noise_setup_env(monkeypatch):
    """D126 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D126_getstats_noise.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d126_getstats_noise_evaluate():
    """D126 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D126_getstats_noise.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d127_getstats_operatingstandard_contract():
    """D127 getStats() OperatingStandard YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D127_getstats_operatingstandard.yaml")
    assert case["source"]["row"] == 129
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d127_getstats_operatingstandard_setup_env(monkeypatch):
    """D127 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D127_getstats_operatingstandard.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d127_getstats_operatingstandard_evaluate():
    """D127 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D127_getstats_operatingstandard.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d128_getstats_retransmissions_contract():
    """D128 getStats() Retransmissions YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D128_getstats_retransmissions.yaml")
    assert case["source"]["row"] == 130
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d128_getstats_retransmissions_setup_env(monkeypatch):
    """D128 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D128_getstats_retransmissions.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d128_getstats_retransmissions_evaluate():
    """D128 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D128_getstats_retransmissions.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d129_getstats_rssi_contract():
    """D129 getStats() RSSI YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D129_getstats_rssi.yaml")
    assert case["source"]["row"] == 131
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d129_getstats_rssi_setup_env(monkeypatch):
    """D129 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D129_getstats_rssi.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d129_getstats_rssi_evaluate():
    """D129 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D129_getstats_rssi.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d130_getstats_rx_retransmissions_contract():
    """D130 getStats() Rx_Retransmissions YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D130_getstats_rx_retransmissions.yaml")
    assert case["source"]["row"] == 132
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d130_getstats_rx_retransmissions_setup_env(monkeypatch):
    """D130 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D130_getstats_rx_retransmissions.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d130_getstats_rx_retransmissions_evaluate():
    """D130 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D130_getstats_rx_retransmissions.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d131_getstats_rxbytes_contract():
    """D131 getStats() RxBytes YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D131_getstats_rxbytes.yaml")
    assert case["source"]["row"] == 133
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d131_getstats_rxbytes_setup_env(monkeypatch):
    """D131 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D131_getstats_rxbytes.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d131_getstats_rxbytes_evaluate():
    """D131 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D131_getstats_rxbytes.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d132_getstats_rxpacketcount_contract():
    """D132 getStats() RxPacketCount YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D132_getstats_rxpacketcount.yaml")
    assert case["source"]["row"] == 134
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d132_getstats_rxpacketcount_setup_env(monkeypatch):
    """D132 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D132_getstats_rxpacketcount.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d132_getstats_rxpacketcount_evaluate():
    """D132 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D132_getstats_rxpacketcount.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d133_getstats_securitymodeenabled_contract():
    """D133 getStats() SecurityModeEnabled YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D133_getstats_securitymodeenabled.yaml")
    assert case["source"]["row"] == 135
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d133_getstats_securitymodeenabled_setup_env(monkeypatch):
    """D133 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D133_getstats_securitymodeenabled.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d133_getstats_securitymodeenabled_evaluate():
    """D133 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D133_getstats_securitymodeenabled.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d134_getstats_supportedmcs_contract():
    """D134 getStats() SupportedMCS YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D134_getstats_supportedmcs.yaml")
    assert case["source"]["row"] == 136
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d134_getstats_supportedmcs_setup_env(monkeypatch):
    """D134 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D134_getstats_supportedmcs.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d134_getstats_supportedmcs_evaluate():
    """D134 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D134_getstats_supportedmcs.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d135_getstats_tx_retransmissions_contract():
    """D135 getStats() Tx_Retransmissions YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D135_getstats_tx_retransmissions.yaml")
    assert case["source"]["row"] == 137
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d135_getstats_tx_retransmissions_setup_env(monkeypatch):
    """D135 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D135_getstats_tx_retransmissions.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d135_getstats_tx_retransmissions_evaluate():
    """D135 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D135_getstats_tx_retransmissions.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d136_getstats_txbytes_contract():
    """D136 getStats() TxBytes YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D136_getstats_txbytes.yaml")
    assert case["source"]["row"] == 138
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d136_getstats_txbytes_setup_env(monkeypatch):
    """D136 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D136_getstats_txbytes.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d136_getstats_txbytes_evaluate():
    """D136 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D136_getstats_txbytes.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d137_getstats_txpacketcount_contract():
    """D137 getStats() TxPacketCount YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D137_getstats_txpacketcount.yaml")
    assert case["source"]["row"] == 139
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d137_getstats_txpacketcount_setup_env(monkeypatch):
    """D137 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D137_getstats_txpacketcount.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d137_getstats_txpacketcount_evaluate():
    """D137 pass criteria met with function not found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D137_getstats_txpacketcount.yaml")
    results = {
        "steps": {
            "step1_getstats_probe": {
                "success": True,
                "output": "ERROR: call (null) failed with status 3 - function not found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True



def test_d138_endpoint_intfname_contract():
    """D138 EndPoint IntfName YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D138_intfname.yaml")
    assert case["source"]["row"] == 126
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d138_endpoint_intfname_setup_env(monkeypatch):
    """D138 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D138_intfname.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d138_endpoint_intfname_evaluate():
    """D138 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D138_intfname.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d139_endpoint_multiapenable_contract():
    """D139 EndPoint MultiAPEnable YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D139_multiapenable.yaml")
    assert case["source"]["row"] == 127
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d139_endpoint_multiapenable_setup_env(monkeypatch):
    """D139 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D139_multiapenable.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d139_endpoint_multiapenable_evaluate():
    """D139 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D139_multiapenable.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d140_endpoint_enable_profile_wps_contract():
    """D140 EndPoint Enable YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D140_enable_profile_wps.yaml")
    assert case["source"]["row"] == 128
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d140_endpoint_enable_profile_wps_setup_env(monkeypatch):
    """D140 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D140_enable_profile_wps.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d140_endpoint_enable_profile_wps_evaluate():
    """D140 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D140_enable_profile_wps.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d141_endpoint_forcebssid_contract():
    """D141 EndPoint ForceBSSID YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D141_forcebssid.yaml")
    assert case["source"]["row"] == 129
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d141_endpoint_forcebssid_setup_env(monkeypatch):
    """D141 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D141_forcebssid.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d141_endpoint_forcebssid_evaluate():
    """D141 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D141_forcebssid.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d142_endpoint_keypassphrase_wps_security_contract():
    """D142 EndPoint KeyPassPhrase YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D142_keypassphrase_wps_security.yaml")
    assert case["source"]["row"] == 130
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d142_endpoint_keypassphrase_wps_security_setup_env(monkeypatch):
    """D142 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D142_keypassphrase_wps_security.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d142_endpoint_keypassphrase_wps_security_evaluate():
    """D142 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D142_keypassphrase_wps_security.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d143_endpoint_mfpconfig_wps_security_contract():
    """D143 EndPoint MFPConfig YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D143_mfpconfig_wps_security.yaml")
    assert case["source"]["row"] == 131
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d143_endpoint_mfpconfig_wps_security_setup_env(monkeypatch):
    """D143 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D143_mfpconfig_wps_security.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d143_endpoint_mfpconfig_wps_security_evaluate():
    """D143 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D143_mfpconfig_wps_security.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d144_endpoint_modeenabled_wps_security_contract():
    """D144 EndPoint ModeEnabled YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D144_modeenabled_wps_security.yaml")
    assert case["source"]["row"] == 132
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d144_endpoint_modeenabled_wps_security_setup_env(monkeypatch):
    """D144 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D144_modeenabled_wps_security.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d144_endpoint_modeenabled_wps_security_evaluate():
    """D144 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D144_modeenabled_wps_security.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d145_endpoint_presharedkey_wps_security_contract():
    """D145 EndPoint PreSharedKey YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D145_presharedkey_wps_security.yaml")
    assert case["source"]["row"] == 133
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d145_endpoint_presharedkey_wps_security_setup_env(monkeypatch):
    """D145 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D145_presharedkey_wps_security.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d145_endpoint_presharedkey_wps_security_evaluate():
    """D145 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D145_presharedkey_wps_security.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d146_endpoint_wepkey_wps_security_contract():
    """D146 EndPoint WEPKey YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D146_wepkey_wps_security.yaml")
    assert case["source"]["row"] == 134
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d146_endpoint_wepkey_wps_security_setup_env(monkeypatch):
    """D146 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D146_wepkey_wps_security.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d146_endpoint_wepkey_wps_security_evaluate():
    """D146 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D146_wepkey_wps_security.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d147_endpoint_ssid_profile_wps_contract():
    """D147 EndPoint SSID YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D147_ssid_profile_wps.yaml")
    assert case["source"]["row"] == 135
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d147_endpoint_ssid_profile_wps_setup_env(monkeypatch):
    """D147 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D147_ssid_profile_wps.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d147_endpoint_ssid_profile_wps_evaluate():
    """D147 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D147_ssid_profile_wps.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d148_endpoint_status_profile_wps_contract():
    """D148 EndPoint Status YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D148_status_profile_wps.yaml")
    assert case["source"]["row"] == 136
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d148_endpoint_status_profile_wps_setup_env(monkeypatch):
    """D148 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D148_status_profile_wps.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d148_endpoint_status_profile_wps_evaluate():
    """D148 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D148_status_profile_wps.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d152_endpoint_pairinginprogress_endpoint_wps_contract():
    """D152 EndPoint PairingInProgress YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D152_pairinginprogress_endpoint_wps.yaml")
    assert case["source"]["row"] == 137
    assert case["llapi_support"] == "Not Supported"
    assert len(case["steps"]) == 1
    assert len(case["pass_criteria"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d152_endpoint_pairinginprogress_endpoint_wps_setup_env(monkeypatch):
    """D152 is DUT-only."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D152_pairinginprogress_endpoint_wps.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d152_endpoint_pairinginprogress_endpoint_wps_evaluate():
    """D152 pass criteria met with No data found output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D152_pairinginprogress_endpoint_wps.yaml")
    results = {
        "steps": {
            "step1_endpoint_probe": {
                "success": True,
                "output": "WiFi.EndPoint.?" + "\n" + "No data found",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True
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


def test_extract_key_values_strips_quotes_before_trailing_comma():
    plugin = _load_plugin()
    parsed = plugin._extract_key_values('AssociationTime = "2026-03-19T10:18:49Z",\n')
    assert parsed["AssociationTime"] == "2026-03-19T10:18:49Z"


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


def test_execute_step_assoc_capture_falls_back_to_associated_device_query(monkeypatch):
    plugin = _load_plugin()
    dut = _FakeTransport("serial", {})
    plugin._transports["DUT"] = dut

    case = {
        "id": "wifi-llapi-runtime-assoc-fallback",
        "steps": [
            {
                "id": "step6_6g_assoc",
                "action": "exec",
                "target": "DUT",
                "band": "6g",
                "capture": "assoc_6g",
                "command": (
                    "wl -i wl1 assoclist | tr 'A-F' 'a-f' | "
                    "sed -n 's/^assoclist \\([^ ]*\\).*$/AssocMac6g=\\1/p'"
                ),
            }
        ],
        "pass_criteria": [
            {"field": "assoc_6g.AssocMac6g", "operator": "regex", "value": _ASSOC_MAC_REGEX}
        ],
    }

    monkeypatch.setattr(plugin, "_should_auto_prepare_wifi_bands", lambda _case: False)

    def fake_execute(command: str, timeout: float = 30.0) -> dict[str, Any]:
        del timeout
        dut.executed_commands.append(command)
        if command.startswith("wl -i wl1 assoclist"):
            return {"returncode": 0, "stdout": "assoclist ", "stderr": "", "elapsed": 0.01}
        if command == 'ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"':
            return {
                "returncode": 0,
                "stdout": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2C:59:17:00:19:96"',
                "stderr": "",
                "elapsed": 0.01,
            }
        return {"returncode": 1, "stdout": "", "stderr": "unexpected", "elapsed": 0.01}

    monkeypatch.setattr(dut, "execute", fake_execute)
    result = plugin.execute_step(case, case["steps"][0], topology=None)

    assert result["success"] is True
    assert result["fallback_reason"] == "capture_assoc_mac_query"
    assert result["captured"]["AssocMac6g"] == "2c:59:17:00:19:96"
    assert result["output"].endswith("AssocMac6g=2c:59:17:00:19:96")


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


def test_split_step_command_sequence_preserves_stateful_multiline_script():
    plugin = _load_plugin()
    command = "\n".join(
        [
            'STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?")',
            '[ -n "$STA_MAC" ] && wl -i wl0 sta_info $STA_MAC',
        ]
    )

    assert plugin._split_step_command_sequence(command) == [command]


def test_case_sta_band_connect_commands_accepts_command_list():
    plugin = _load_plugin()
    case = {
        "steps": [
            {
                "id": "step1_5g_sta_join",
                "action": "exec",
                "target": "STA",
                "band": "5g",
                "command": [
                    "wl -i wl0 down",
                    "sleep 1",
                    "wl -i wl0 up",
                    "sleep 1",
                    "wl -i wl0 join TestPilot_5G imode bss",
                    "sleep 3",
                    "wl -i wl0 status",
                ],
            }
        ]
    }

    assert plugin._case_sta_band_connect_commands(case, "5g") == [
        "wl -i wl0 down",
        "sleep 1",
        "wl -i wl0 up",
        "sleep 1",
        "wl -i wl0 join TestPilot_5G imode bss",
        "sleep 3",
        "wl -i wl0 status",
    ]


def test_execute_step_runs_stateful_multiline_script_as_single_command(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    command = "\n".join(
        [
            'STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" | sed -n \'s/.*MACAddress="\\([^"]*\\)".*/\\1/p\')',
            '[ -n "$STA_MAC" ] && echo "DriverAssocMac=$STA_MAC"',
        ]
    )
    case = {
        "id": "wifi-llapi-runtime-stateful-multiline",
        "topology": {"devices": {"DUT": {"transport": "serial"}}},
        "steps": [
            {
                "id": "step1",
                "action": "exec",
                "target": "DUT",
                "capture": "result",
                "command": command,
            }
        ],
        "pass_criteria": [{"field": "result.DriverAssocMac", "operator": "contains", "value": ":"}],
    }

    assert plugin.setup_env(case, topology=topology) is True
    dut = plugin._transports["DUT"]
    wrapped_command = plugin._wrap_multiline_shell_command(command)

    def fake_execute(command_to_run: str, timeout: float = 30.0) -> dict[str, Any]:
        del timeout
        dut.executed_commands.append(command_to_run)
        assert command_to_run == wrapped_command
        assert "\n" not in command_to_run
        assert "| sh" in command_to_run
        return {
            "returncode": 0,
            "stdout": "DriverAssocMac=2c:59:17:00:19:95",
            "stderr": "",
            "elapsed": 0.01,
        }

    monkeypatch.setattr(dut, "execute", fake_execute)
    result = plugin.execute_step(case, case["steps"][0], topology=topology)

    assert result["success"] is True
    assert dut.executed_commands[-1] == wrapped_command
    assert result["command"] == wrapped_command
    assert result["captured"]["DriverAssocMac"] == "2c:59:17:00:19:95"
    plugin.teardown(case, topology=topology)


def test_no_multiline_block_scalar_commands_in_official_cases():
    """All official case YAMLs must use single-line strings or list format.

    Multiline block scalars for command/verification_command/hlapi_command
    are banned to prevent serial transport truncation.
    """
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    violations: list[str] = []
    for yaml_path in sorted(cases_dir.glob("D*.yaml")):
        case = load_case(yaml_path)
        for step in case.get("steps", []):
            if not isinstance(step, dict):
                continue
            cmd = step.get("command", "")
            if isinstance(cmd, str) and "\n" in cmd:
                violations.append(f"{yaml_path.name}:{step.get('id', '?')} command")
        for field in ("verification_command", "hlapi_command"):
            val = case.get(field, "")
            if isinstance(val, str) and "\n" in val:
                violations.append(f"{yaml_path.name} {field}")
    assert violations == [], f"Multiline block scalars found:\n" + "\n".join(violations)


def test_manual_6g_sta_env_setup_uses_full_client_rebase_and_network_selection():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    required_commands = [
        "ifconfig wl1 down",
        "wl -i wl1 down",
        "wl -i wl1 ap 0",
        "iw dev wl1 set type managed",
        "wl -i wl1 up",
        "ifconfig wl1 up",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 enable_network 0",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 select_network 0",
    ]
    violations: list[str] = []

    for yaml_path in sorted(cases_dir.glob("D*.yaml")):
        case = load_case(yaml_path)
        sta_env_setup = case.get("sta_env_setup", "")
        if not isinstance(sta_env_setup, str):
            continue
        if "wpa_supplicant -B -D nl80211 -i wl1" not in sta_env_setup:
            continue
        missing = [command for command in required_commands if command not in sta_env_setup]
        if missing:
            violations.append(f"{yaml_path.name}: missing {', '.join(missing)}")

    assert violations == [], (
        "Manual 6G sta_env_setup missing full client rebase/network selection:\n"
        + "\n".join(violations)
    )


def test_evaluate_mac_equality_is_case_insensitive():
    plugin = _load_plugin()
    case = {
        "id": "wifi-llapi-runtime-mac-compare",
        "steps": [
            {"id": "s1", "capture": "assoc_driver"},
            {"id": "s2", "capture": "result"},
        ],
        "pass_criteria": [
            {
                "field": "result.MACAddress",
                "operator": "equals",
                "reference": "assoc_driver.AssocMAC",
            }
        ],
    }
    results = {
        "steps": {
            "s1": {
                "success": True,
                "output": "AssocMAC=2C:59:17:00:04:86",
                "captured": {"AssocMAC": "2C:59:17:00:04:86"},
                "timing": 0.01,
            },
            "s2": {
                "success": True,
                "output": 'WiFi.AccessPoint.3.AssociatedDevice.1.MACAddress="2c:59:17:00:04:86"',
                "captured": {"MACAddress": "2c:59:17:00:04:86"},
                "timing": 0.01,
            },
        }
    }

    assert plugin.evaluate(case, results) is True


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
        "D044_signalnoiseratio.yaml",
        "D049_supportedmcs.yaml",
        "D043_securitymodeenabled.yaml",
        "D045_signalstrength_accesspoint_associateddevice.yaml",
        "D046_signalstrengthbychain.yaml",
        "D048_supportedhemcs.yaml",
        "D054_txerrors.yaml",
        "D055_txmulticastpacketcount.yaml",
        "D056_txpacketcount.yaml",
        "D058_uniibandscapabilities.yaml",
    ],
)
def test_sta_env_setup_parser_preserves_single_line_wpa_supplicant_template(filename: str):
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
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


@pytest.mark.parametrize("filename", ["D059_uplinkbandwidth.yaml", "D060_uplinkmcs.yaml"])
def test_sta_env_setup_parser_preserves_single_line_wpa_supplicant_psk_template(filename: str):
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / filename)

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


def test_multiband_direct_stats_preserve_authored_getssid_pipeline_commands():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    for filename in (
        "D321_broadcastpacketsreceived.yaml",
        "D322_broadcastpacketssent.yaml",
    ):
        case_data = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        step = next(item for item in case_data["steps"] if item["id"] == "getssid_5g")

        commands, reason = plugin._command_resolver.resolve(case_data, step, topology=None)

        assert commands == [step["command"]]
        assert reason == ""


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
        ("D034_noise_accesspoint_associateddevice.yaml", 2, "DriverNoise="),
        ("D037_retransmissions.yaml", 3, "DriverRetransmissions="),
        ("D038_rx_retransmissions.yaml", 3, "DriverRxRetransmissions="),
        ("D039_rxbytes.yaml", 4, "DriverRxBytes="),
        ("D040_rxmulticastpacketcount.yaml", 3, "DriverRxMulticastPacketCount="),
        ("D042_rxunicastpacketcount.yaml", 4, "DriverRxUnicastPacketCount="),
        ("D044_signalnoiseratio.yaml", 2, "DriverSignalNoiseRatio="),
        ("D043_securitymodeenabled.yaml", 2, "DriverSecurityModeEnabled="),
        ("D045_signalstrength_accesspoint_associateddevice.yaml", 2, "DriverSignalStrength="),
        ("D046_signalstrengthbychain.yaml", 3, "DriverSignalStrengthByChain="),
        ("D048_supportedhemcs.yaml", 4, "DriverHeMcsLinePresent="),
        ("D050_supportedvhtmcs.yaml", 4, "DriverVhtSetPresent="),
        ("D051_tx_retransmissions.yaml", 3, "DriverTxRetransmissions="),
        ("D052_tx_retransmissionsfailed.yaml", 2, "DriverTxRetransmissionsFailed="),
        ("D054_txerrors.yaml", 3, "DriverTxErrors="),
        ("D049_supportedmcs.yaml", 2, "DriverMCSSetPresent="),
        ("D056_txpacketcount.yaml", 3, "DriverTxPacketCount="),
        ("D059_uplinkbandwidth.yaml", 3, "DriverUplinkBandwidth="),
        ("D060_uplinkmcs.yaml", 3, "DriverUplinkMCS="),
        ("D061_uplinkshortguard.yaml", 4, "DriverUplinkShortGuardGI="),
        ("D062_vendoroui.yaml", 4, "DriverVendorOUIList="),
        (
            "D063_vhtcapabilities_accesspoint_associateddevice.yaml",
            4,
            "DriverVhtCapabilities=",
        ),
        ("D058_uniibandscapabilities.yaml", 2, "DriverUNIIBandsCapabilities="),
    ],
)
def test_sanitize_cli_fragment_preserves_nested_quotes_for_associateddevice_driver_checks(
    filename: str, step_index: int, driver_token: str
):
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / filename)
    command = case_data["steps"][step_index]["command"]
    expected_fragments = (
        plugin._extract_cli_fragments(command)
        if "\n" in command
        else [command]
    )

    assert '[ -n "$STA_MAC" ]' in command
    assert "DriverAssocMac=" in command
    assert driver_token in command
    if "\n" in command:
        assert plugin._split_step_command_sequence(command) == [command.strip()]
        sanitized = plugin._sanitize_cli_fragment(command)
        assert "DriverAssocMac=" in sanitized
        assert driver_token in sanitized
    else:
        assert plugin._sanitize_cli_fragment(command) == command
    assert plugin._extract_cli_fragments(command) == expected_fragments

    verification_commands = plugin._extract_cli_fragments(case_data["verification_command"])
    if filename == "D046_signalstrengthbychain.yaml":
        assert len(verification_commands) >= 3
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
        assert verification_commands[1].startswith('ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.')
        assert driver_token in verification_commands[-1]
    elif filename in {
        "D047_supportedhe160mcs.yaml",
        "D048_supportedhemcs.yaml",
        "D050_supportedvhtmcs.yaml",
        "D052_tx_retransmissionsfailed.yaml",
    }:
        expected_length = 2 + len(expected_fragments) if filename == "D052_tx_retransmissionsfailed.yaml" else 3 + len(expected_fragments)
        assert len(verification_commands) == expected_length
        if filename == "D052_tx_retransmissionsfailed.yaml":
            assert verification_commands[0] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.Tx_RetransmissionsFailed?"'
            assert "wait 30 seconds" in verification_commands[1]
            assert verification_commands[2:] == expected_fragments
        else:
            assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
            assert verification_commands[1].startswith('OUT=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.')
            assert "SiblingAssocMac=" in verification_commands[2]
            assert verification_commands[3:] == expected_fragments
    elif filename == "D054_txerrors.yaml":
        assert len(verification_commands) == 3 + len(expected_fragments)
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
        assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors?"'
        assert "wait 30 seconds" in verification_commands[2]
        assert verification_commands[3:] == expected_fragments
    elif filename == "D062_vendoroui.yaml":
        assert len(verification_commands) == 3 + len(expected_fragments)
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'"
        assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"'
        assert "AssocVendorOUI=" in verification_commands[2]
        assert verification_commands[3:] == expected_fragments
    elif filename == "D063_vhtcapabilities_accesspoint_associateddevice.yaml":
        assert len(verification_commands) == 3 + len(expected_fragments)
        assert verification_commands[0] == "cat /sys/class/net/wl0/address | tr 'A-F' 'a-f' | sed 's/^/StaMac=/'"
        assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"'
        assert "AssocVhtCapabilities=" in verification_commands[2]
        assert verification_commands[3:] == expected_fragments
    else:
        assert len(verification_commands) >= 2
        assert verification_commands[0].startswith('ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.')
        assert driver_token in verification_commands[-1]


def test_d047_supportedhe160mcs_verification_fragments_preserve_error_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d047 = load_case(cases_dir / "D047_supportedhe160mcs.yaml")

    step3_command = d047["steps"][2]["command"]
    step5_command = d047["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d047["verification_command"])

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


def test_d048_supportedhemcs_verification_fragments_preserve_error_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d048 = load_case(cases_dir / "D048_supportedhemcs.yaml")

    step3_command = d048["steps"][2]["command"]
    step5_command = d048["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d048["verification_command"])

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


def test_d050_supportedvhtmcs_verification_fragments_preserve_error_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d050 = load_case(cases_dir / "D050_supportedvhtmcs.yaml")

    step3_command = d050["steps"][2]["command"]
    step5_command = d050["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d050["verification_command"])

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


def test_d079_macfiltering_setter_shell_fragment_is_preserved():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d079 = load_case(cases_dir / "D079_mode_accesspoint_macfiltering.yaml")

    step2_command = d079["steps"][1]["command"]

    assert 'WiFi.AccessPoint.1.MACFiltering.Mode=Off' in step2_command
    assert "invalid value" in step2_command
    assert plugin._sanitize_cli_fragment(step2_command) == step2_command
    assert plugin._extract_cli_fragments(step2_command) == [step2_command]


def test_d054_txerrors_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d054 = load_case(cases_dir / "D054_txerrors.yaml")

    step1_command = d054["steps"][0]["command"]
    step4_command = d054["steps"][3]["command"]
    step7_command = d054["steps"][6]["command"]
    verification_commands = plugin._extract_cli_fragments(d054["verification_command"])

    assert step1_command == "cat /sys/class/net/wl0/address | tr 'a-f' 'A-F' | sed 's/^/StaMac=/'"
    assert plugin._sanitize_cli_fragment(step4_command) == step4_command
    assert plugin._extract_cli_fragments(step4_command) == [step4_command]
    assert plugin._sanitize_cli_fragment(step7_command) == step7_command
    assert plugin._extract_cli_fragments(step7_command) == [step7_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.TxErrors?"'
    assert "wait 30 seconds" in verification_commands[2]
    assert verification_commands[3] == step7_command


def test_d055_txmulticastpacketcount_verification_fragments_preserve_delivery_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d055 = load_case(cases_dir / "D055_txmulticastpacketcount.yaml")

    step5_command = d055["steps"][4]["command"]
    step8_command = d055["steps"][7]["command"]
    verification_commands = plugin._extract_cli_fragments(d055["verification_command"])

    assert "ProbeTxPackets=" in step5_command
    assert plugin._sanitize_cli_fragment(step8_command) == step8_command
    assert plugin._extract_cli_fragments(step8_command) == [step8_command]
    assert len(verification_commands) == 6
    assert any("StaRxPacketsBefore=" in fragment for fragment in verification_commands)
    assert any("StaRxPacketsAfter=" in fragment for fragment in verification_commands)
    assert step5_command in verification_commands
    assert verification_commands[-1] == step8_command


def test_d055_txmulticastpacketcount_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d055 = load_case(cases_dir / "D055_txmulticastpacketcount.yaml")
    step2_command = d055["steps"][1]["command"]
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


def test_d055_txmulticastpacketcount_driver_fragment_mentions_counter():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d055 = load_case(cases_dir / "D055_txmulticastpacketcount.yaml")
    step8_command = d055["steps"][7]["command"]

    assert "DriverTxMulticastPacketCount=" in step8_command
    assert "DriverAssocMac=" in step8_command


def test_d057_txunicastpacketcount_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txunicastpacketcount.yaml")

    step5_command = d057["steps"][4]["command"]
    step7_command = d057["steps"][6]["command"]
    verification_commands = plugin._extract_cli_fragments(d057["verification_command"])

    assert "TriggerTxPackets=" in step5_command
    assert plugin._sanitize_cli_fragment(step7_command) == step7_command
    assert plugin._extract_cli_fragments(step7_command) == [step7_command]
    assert len(verification_commands) == 4
    assert verification_commands[2] == step5_command
    assert verification_commands[3] == step7_command


def test_d057_txunicastpacketcount_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txunicastpacketcount.yaml")
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


def test_d057_txunicastpacketcount_driver_fragment_mentions_driver_counter():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d057 = load_case(cases_dir / "D057_txunicastpacketcount.yaml")
    step7_command = d057["steps"][6]["command"]

    assert "DriverTxUnicastPacketCount=" in step7_command
    assert "DriverAssocMac=" in step7_command


def test_d053_txbytes_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d053 = load_case(cases_dir / "D053_txbytes.yaml")

    step7_command = d053["steps"][6]["command"]
    verification_commands = plugin._extract_cli_fragments(d053["verification_command"])

    assert "DriverTxBytes5g=" in step7_command
    assert plugin._sanitize_cli_fragment(step7_command) == step7_command
    assert plugin._extract_cli_fragments(step7_command) == [step7_command]
    assert len(verification_commands) == 12
    assert verification_commands[3] == step7_command


def test_d053_txbytes_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d053 = load_case(cases_dir / "D053_txbytes.yaml")
    step2_command = d053["steps"][1]["command"]
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
    assert proc.stdout.strip() == "AssocMac5g=2c:59:17:00:04:85"


def test_d062_vendoroui_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d062 = load_case(cases_dir / "D062_vendoroui.yaml")

    step1_command = d062["steps"][0]["command"]
    step3_command = d062["steps"][2]["command"]
    step4_command = d062["steps"][3]["command"]
    step5_command = d062["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d062["verification_command"])

    assert step3_command == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI?"'
    assert "AssocVendorOUI=" in step4_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step3_command
    assert verification_commands[2] == step4_command
    assert verification_commands[3] == step5_command


def test_d062_vendoroui_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d062 = load_case(cases_dir / "D062_vendoroui.yaml")
    step2_command = d062["steps"][1]["command"]
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


def test_d062_vendoroui_snapshot_fragment_executes_with_concrete_value():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d062 = load_case(cases_dir / "D062_vendoroui.yaml")
    step4_command = d062["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
            'WiFi.AccessPoint.1.AssociatedDevice.1.VendorOUI="00:90:4C,00:10:18,00:50:F2,50:6F:9A"',
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
        "AssocVendorOUI=00:90:4C,00:10:18,00:50:F2,50:6F:9A",
    ]


def test_d062_vendoroui_driver_capture_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d062 = load_case(cases_dir / "D062_vendoroui.yaml")
    step5_command = d062["steps"][4]["command"]
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


def test_d063_vhtcapabilities_verification_fragments_preserve_snapshot_and_driver_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d063 = load_case(cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml")

    step1_command = d063["steps"][0]["command"]
    step3_command = d063["steps"][2]["command"]
    step4_command = d063["steps"][3]["command"]
    step5_command = d063["steps"][4]["command"]
    verification_commands = plugin._extract_cli_fragments(d063["verification_command"])

    assert step3_command == 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities?"'
    assert "AssocVhtCapabilities=" in step4_command
    assert plugin._sanitize_cli_fragment(step5_command) == step5_command
    assert plugin._extract_cli_fragments(step5_command) == [step5_command]
    assert len(verification_commands) == 4
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step3_command
    assert verification_commands[2] == step4_command
    assert verification_commands[3] == step5_command


def test_d063_vhtcapabilities_macaddress_fragment_normalizes_case():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d063 = load_case(cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml")
    step2_command = d063["steps"][1]["command"]
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


def test_d063_vhtcapabilities_snapshot_fragment_executes_with_concrete_value():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d063 = load_case(cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml")
    step4_command = d063["steps"][3]["command"]
    pipeline = step4_command.split("|", 1)[1].strip()
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:04:85"',
            'WiFi.AccessPoint.1.AssociatedDevice.1.VhtCapabilities="SGI80,SGI160,SU-BFR,SU-BFE"',
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
        "AssocVhtCapabilities=SGI80,SGI160,SU-BFR,SU-BFE",
    ]


def test_d063_vhtcapabilities_driver_capture_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d063 = load_case(cases_dir / "D063_vhtcapabilities_accesspoint_associateddevice.yaml")
    step5_command = d063["steps"][4]["command"]
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


def test_d064_apbridgedisable_verification_fragments_preserve_toggle_and_cross_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_apbridgedisable.yaml")

    step1_command = d064["steps"][0]["command"]
    step2_command = d064["steps"][1]["command"]
    step3_command = d064["steps"][2]["command"]
    step4_command = d064["steps"][3]["command"]
    step5_command = d064["steps"][4]["command"]
    step8_command = d064["steps"][7]["command"]
    step9_command = d064["steps"][8]["command"]
    verification_commands = plugin._extract_cli_fragments(d064["verification_command"])

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


def test_d064_apbridgedisable_hostapd_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_apbridgedisable.yaml")
    step4_command = d064["steps"][3]["command"]
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


def test_d064_apbridgedisable_driver_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d064 = load_case(cases_dir / "D064_apbridgedisable.yaml")
    step8_command = d064["steps"][7]["command"]
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


def test_d065_bridgeinterface_verification_fragments_preserve_getters_and_cross_checks():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_bridgeinterface.yaml")

    step1_command = d065["steps"][0]["command"]
    step2_command = d065["steps"][1]["command"]
    step3_command = d065["steps"][2]["command"]
    step4_command = d065["steps"][3]["command"]
    step5_command = d065["steps"][4]["command"]
    step6_command = d065["steps"][5]["command"]
    step7_command = d065["steps"][6]["command"]
    verification_commands = plugin._extract_cli_fragments(d065["verification_command"])
    assert len(verification_commands) == 9
    assert verification_commands[0] == step1_command
    assert verification_commands[1] == step2_command
    assert verification_commands[2] == step3_command
    assert verification_commands[3] == step4_command
    assert verification_commands[4] == step5_command
    assert verification_commands[5] == step6_command
    assert verification_commands[6:] == _expected_step_fragments(plugin, step7_command)


def test_d065_bridgeinterface_hostapd_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_bridgeinterface.yaml")
    step4_command = d065["steps"][3]["command"]
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


def test_d065_bridgeinterface_bridge_master_fragment_executes():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d065 = load_case(cases_dir / "D065_bridgeinterface.yaml")
    step7_command = d065["steps"][6]["command"]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("INTERFACE=br-lan\n")
        temp_path = handle.name

    try:
        proc = _execute_step_shell_sequence(
            plugin,
            step7_command,
            {
                "/sys/class/net/wl0/master/uevent": temp_path,
                "/sys/class/net/wl1/master/uevent": temp_path,
                "/sys/class/net/wl2/master/uevent": temp_path,
            },
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "BridgeMaster5g=br-lan",
        "BridgeMaster6g=br-lan",
        "BridgeMaster24g=br-lan",
    ]


def test_d068_discoverymethodenabled_accesspoint_fils_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d066 = load_case(cases_dir / "D066_discoverymethodenabled_accesspoint_fils.yaml")

    verification_commands = plugin._extract_cli_fragments(d066["verification_command"])

    expected_commands = [
        d066["steps"][0]["command"],
        d066["steps"][1]["command"],
        d066["steps"][2]["command"],
        d066["steps"][3]["command"],
        d066["steps"][4]["command"],
        d066["steps"][5]["command"],
        d066["steps"][9]["command"],
        d066["steps"][10]["command"],
        d066["steps"][11]["command"],
        d066["steps"][15]["command"],
        d066["steps"][16]["command"],
        d066["steps"][17]["command"],
    ]

    assert len(verification_commands) == 13
    assert verification_commands[:-1] == expected_commands
    assert verification_commands[-1] == 'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?"'


def test_d068_discoverymethodenabled_accesspoint_upr_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d067 = load_case(cases_dir / "D067_discoverymethodenabled_accesspoint_upr.yaml")

    verification_commands = plugin._extract_cli_fragments(d067["verification_command"])
    expected_commands = [
        d067["steps"][0]["command"],
        d067["steps"][1]["command"],
        d067["steps"][2]["command"],
        d067["steps"][3]["command"],
        d067["steps"][4]["command"],
        d067["steps"][5]["command"],
        'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?"',
        d067["steps"][9]["command"],
        d067["steps"][10]["command"],
        d067["steps"][11]["command"],
    ]

    assert len(verification_commands) == 11
    assert verification_commands[:-1] == expected_commands
    assert verification_commands[-1] == 'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?" | sed -n \'1,20p\''


def test_d068_discoverymethodenabled_accesspoint_rnr_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_rnr.yaml")

    verification_commands = plugin._extract_cli_fragments(d068["verification_command"])
    expected_commands = [
        d068["steps"][0]["command"],
        d068["steps"][1]["command"],
        d068["steps"][2]["command"],
        d068["steps"][3]["command"],
        d068["steps"][4]["command"],
        d068["steps"][5]["command"],
        'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?"',
        d068["steps"][9]["command"],
        d068["steps"][10]["command"],
        d068["steps"][11]["command"],
        d068["steps"][12]["command"],
        d068["steps"][13]["command"],
        d068["steps"][14]["command"],
        'ubus-cli "WiFi.AccessPoint.*.DiscoveryMethodEnabled?" | sed -n \'1,20p\'',
        d068["steps"][15]["command"] + " | sed -n '1,20p'",
    ]

    assert verification_commands == expected_commands


def test_d068_discoverymethodenabled_accesspoint_rnr_config_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d068 = load_case(cases_dir / "D068_discoverymethodenabled_accesspoint_rnr.yaml")
    step11_command = d068["steps"][10]["command"]
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


def test_d070_enable_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_enable_accesspoint.yaml")

    verification_commands = plugin._extract_cli_fragments(d070["verification_command"])
    expected_commands = [
        d070["steps"][0]["command"][0],
        d070["steps"][0]["command"][1],
        d070["steps"][1]["command"][0],
        d070["steps"][1]["command"][1],
        d070["steps"][2]["command"][0],
        d070["steps"][2]["command"][1],
    ]

    assert verification_commands == expected_commands


def test_d070_enable_accesspoint_enable_fragment_parses_getter_value():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_enable_accesspoint.yaml")
    step1_command = d070["steps"][0]["command"][0]
    assert "WiFi.AccessPoint.1.Enable?" in step1_command
    pipeline = "grep -o 'Enable=[0-9]*' | cut -d= -f2"
    sample_output = "WiFi.AccessPoint.1.Enable=1"

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
    assert proc.stdout.strip() == "1"


def test_d070_enable_accesspoint_driver_fragment_preserves_cli():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d070 = load_case(cases_dir / "D070_enable_accesspoint.yaml")
    step1_driver_command = d070["steps"][0]["command"][1]

    assert step1_driver_command == 'echo "DriverBss5g=$(wl -i wl0 bss 2>/dev/null)"'
    assert plugin._sanitize_cli_fragment(step1_driver_command) == step1_driver_command
    assert plugin._extract_cli_fragments(step1_driver_command) == [step1_driver_command]


def test_d071_ftoverdsenable_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")

    verification_commands = plugin._extract_cli_fragments(d071["verification_command"])
    step_commands = [step["command"] for step in d071["steps"]]

    expected_commands = []
    for start in (0, 10, 20):
        expected_commands.extend(
            [
                step_commands[start],
                step_commands[start + 1],
            ]
        )
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 2]))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 3]))
        expected_commands.extend(
            [
                step_commands[start + 4],
            ]
        )
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 5], " | sed -n '1,20p'"))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 6], " | sed -n '1,20p'"))
        expected_commands.append(step_commands[start + 7])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 8], " | sed -n '1,21p'"))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 9], " | sed -n '1,21p'"))
    for start in (30, 32, 34):
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start]))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 1], " | sed -n '1,22p'"))

    assert verification_commands == expected_commands


def test_d071_ftoverdsenable_accesspoint_state_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")
    step3_command = d071["steps"][2]["command"]
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
            _stringify_command(step3_command)
            .replace('ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?"', f"cat {temp_path}")
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


def test_d071_ftoverdsenable_accesspoint_config_snapshot_zero_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")
    step4_command = d071["steps"][3]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("mobility_domain=3412\nft_over_ds=0\n")
        temp_path = handle.name

    try:
        adapted_command = _stringify_command(step4_command).replace("/tmp/wl0_hapd.conf", temp_path)
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


def test_d071_ftoverdsenable_accesspoint_config_snapshot_one_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d071 = load_case(cases_dir / "D071_ftoverdsenable.yaml")
    step7_command = d071["steps"][6]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("mobility_domain=3412\nft_over_ds=1\n")
        temp_path = handle.name

    try:
        adapted_command = _stringify_command(step7_command).replace("/tmp/wl0_hapd.conf", temp_path)
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


def test_d072_mobilitydomain_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")

    verification_commands = plugin._extract_cli_fragments(d072["verification_command"])
    step_commands = [step["command"] for step in d072["steps"]]

    expected_commands = []
    for start in (0, 9, 18):
        expected_commands.append(step_commands[start])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 1]))
        expected_commands.append(step_commands[start + 2])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 3], " | sed -n '1,20p'"))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 4]))
        expected_commands.append(step_commands[start + 5])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 6], " | sed -n '1,21p'"))
        expected_commands.append(step_commands[start + 7])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 8], " | sed -n '1,22p'"))

    assert verification_commands == expected_commands


def test_d072_mobilitydomain_accesspoint_state_snapshot_fragment_executes():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")
    step2_command = d072["steps"][1]["command"]
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
        proc = _execute_step_shell_sequence(
            plugin,
            step2_command,
            {
                'ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?"': f"cat {temp_path}",
                'ubus-cli "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain?"': f"cat {temp_path}",
            },
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Enabled5g=1",
        "MobilityDomain5g=0",
    ]


def test_d072_mobilitydomain_accesspoint_config_snapshot_fragment_executes():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")
    step5_command = d072["steps"][4]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("mobility_domain=546B\nft_over_ds=0\n")
        temp_path = handle.name

    try:
        proc = _execute_step_shell_sequence(
            plugin,
            step5_command,
            {"/tmp/wl0_hapd.conf": temp_path},
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "MobilityDomainCfg5g=546B",
        "FtOverDs5gZeroCount=1",
        "FtOverDs5gTotalCount=1",
    ]


def test_d072_mobilitydomain_accesspoint_cleanup_state_fragment_executes():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d072 = load_case(cases_dir / "D072_mobilitydomain.yaml")
    step9_command = d072["steps"][8]["command"]
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
        proc = _execute_step_shell_sequence(
            plugin,
            step9_command,
            {
                'ubus-cli "WiFi.AccessPoint.1.IEEE80211r.Enabled?"': f"cat {temp_path}",
                'ubus-cli "WiFi.AccessPoint.1.IEEE80211r.MobilityDomain?"': f"cat {temp_path}",
            },
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Enabled5g=0",
        "MobilityDomain5g=0",
    ]


def test_d075_interworkingenable_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")

    verification_commands = plugin._extract_cli_fragments(d075["verification_command"])
    step_commands = [step["command"] for step in d075["steps"]]

    expected_commands = []
    for start in (0, 8, 16):
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start]))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 1]))
        expected_commands.append(step_commands[start + 2])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 3], " | sed -n '1,20p'"))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 4], " | sed -n '1,20p'"))
        expected_commands.append(step_commands[start + 5])
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 6], " | sed -n '1,21p'"))
        expected_commands.extend(_expected_step_fragments(plugin, step_commands[start + 7], " | sed -n '1,21p'"))

    assert verification_commands == expected_commands


def test_d075_interworkingenable_accesspoint_state_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")
    step1_command = d075["steps"][0]["command"]
    sample_output = "WiFi.AccessPoint.1.IEEE80211u.InterworkingEnable=0\n"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = step1_command.replace(
            'ubus-cli "WiFi.AccessPoint.1.IEEE80211u.InterworkingEnable?"',
            f"cat {temp_path}",
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
    assert proc.stdout.strip().splitlines() == ["Interworking5g=0"]


def test_d075_interworkingenable_accesspoint_config_baseline_fragment_executes():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")
    step2_command = d075["steps"][1]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("interworking=0\ninterworking=0\n")
        temp_path = handle.name

    try:
        proc = _execute_step_shell_sequence(
            plugin,
            step2_command,
            {"/tmp/wl0_hapd.conf": temp_path},
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Interworking5gOneCount=0",
        "Interworking5gZeroCount=2",
        "Interworking5gTotalCount=2",
    ]


def test_d075_interworkingenable_accesspoint_config_set_fragment_executes():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d075 = load_case(cases_dir / "D075_interworkingenable.yaml")
    step5_command = d075["steps"][4]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("interworking=1\ninterworking=0\n")
        temp_path = handle.name

    try:
        proc = _execute_step_shell_sequence(
            plugin,
            step5_command,
            {"/tmp/wl0_hapd.conf": temp_path},
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "Interworking5gOneCount=1",
        "Interworking5gZeroCount=1",
        "Interworking5gTotalCount=2",
    ]


def test_d076_qosmapset_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")

    verification_commands = plugin._extract_cli_fragments(d076["verification_command"])
    step_commands = [step["command"] for step in d076["steps"]]

    def fragments(command: str, suffix: str = "") -> list[str]:
        rendered = f"{command}{suffix}" if suffix else command
        return plugin._extract_cli_fragments(rendered)

    expected_commands = []
    seen: set[str] = set()
    for start in (0, 8, 16):
        for command, suffix in (
            (step_commands[start], ""),
            (step_commands[start + 1], ""),
            (step_commands[start + 2], ""),
            (step_commands[start + 3], " | sed -n '1,20p'"),
            (step_commands[start + 4], " | sed -n '1,20p'"),
            (step_commands[start + 5], ""),
            (step_commands[start + 6], " | sed -n '1,21p'"),
            (step_commands[start + 7], " | sed -n '1,21p'"),
        ):
            for fragment in fragments(command, suffix):
                if fragment in seen:
                    continue
                expected_commands.append(fragment)
                seen.add(fragment)

    assert verification_commands == expected_commands


def test_d076_qosmapset_accesspoint_state_snapshot_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")
    step1_command = d076["steps"][0]["command"]
    sample_output = 'WiFi.AccessPoint.1.IEEE80211u.QoSMapSet=""\n'

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = step1_command.replace(
            'ubus-cli "WiFi.AccessPoint.1.IEEE80211u.QoSMapSet?"',
            f"cat {temp_path}",
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
    assert proc.stdout.strip().splitlines() == ["QoSMapSet5g=EMPTY"]


def test_d076_qosmapset_accesspoint_config_baseline_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")
    step2_command = d076["steps"][1]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("ssid=testpilot5G\n")
        temp_path = handle.name

    try:
        adapted_command = step2_command.replace("/tmp/wl0_hapd.conf", temp_path)
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
        "QoSMapSetCfg5gCount=0",
        "QoSMapSetCfg5g=ABSENT",
    ]


def test_d076_qosmapset_accesspoint_config_set_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d076 = load_case(cases_dir / "D076_qosmapset.yaml")
    step5_command = d076["steps"][4]["command"]

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write("qos_map_set=255\n")
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
        "QoSMapSetCfg5gCount=1",
        "QoSMapSetCfg5g=255",
    ]


def test_d077_macfilteraddresslist_accesspoint_verification_fragments_preserve_sequence():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")

    verification_commands = plugin._extract_cli_fragments(d077["verification_command"])
    step_commands = [step["command"] for step in d077["steps"]]

    def fragments(command: str, suffix: str = "") -> list[str]:
        rendered = f"{command}{suffix}" if suffix else command
        return plugin._extract_cli_fragments(rendered)

    expected_commands = []
    seen: set[str] = set()
    for start in (0, 8, 16):
        for command, suffix in (
            (step_commands[start], ""),
            (step_commands[start + 1], ""),
            (step_commands[start + 2], ""),
            (step_commands[start + 3], " | sed -n '1,20p'"),
            (step_commands[start + 4], " | sed -n '1,20p'"),
            (step_commands[start + 5], ""),
            (step_commands[start + 6], " | sed -n '1,20p'"),
            (step_commands[start + 7], " | sed -n '1,20p'"),
        ):
            for fragment in fragments(command, suffix):
                if fragment in seen:
                    continue
                expected_commands.append(fragment)
                seen.add(fragment)

    assert verification_commands == expected_commands


def test_d077_macfilteraddresslist_accesspoint_state_baseline_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")
    step1_command = d077["steps"][0]["command"]
    sample_output = 'WiFi.AccessPoint.1.MACFilterAddressList=""\n'

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = step1_command.replace(
            'ubus-cli "WiFi.AccessPoint.1.MACFilterAddressList?"',
            f"cat {temp_path}",
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
    assert proc.stdout.strip().splitlines() == ["MACFilterAddressList5g=EMPTY"]


def test_d077_macfilteraddresslist_accesspoint_entry_baseline_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")
    step2_command = d077["steps"][1]["command"]
    sample_output = 'WiFi.AccessPoint.1.MACFiltering.Mode="Off"\n'

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = step2_command.replace(
            'ubus-cli "WiFi.AccessPoint.1.?"',
            f"cat {temp_path}",
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
        "EntryCount5g=0",
        "EntryMac5g=EMPTY",
    ]


def test_d077_macfilteraddresslist_accesspoint_state_add_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")
    step4_command = d077["steps"][3]["command"]
    sample_output = 'WiFi.AccessPoint.1.MACFilterAddressList="62:2f:b8:66:bb:82"\n'

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = step4_command.replace(
            'ubus-cli "WiFi.AccessPoint.1.MACFilterAddressList?"',
            f"cat {temp_path}",
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
    assert proc.stdout.strip().splitlines() == ["MACFilterAddressList5g=62:2F:B8:66:BB:82"]


def test_d077_macfilteraddresslist_accesspoint_entry_add_fragment_executes():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d077 = load_case(cases_dir / "D077_macfilteraddresslist.yaml")
    step5_command = d077["steps"][4]["command"]
    sample_output = "\n".join(
        [
            'WiFi.AccessPoint.1.MACFiltering.Entry.1.Alias="cpe-Entry-1"',
            'WiFi.AccessPoint.1.MACFiltering.Entry.1.MACAddress="62:2f:b8:66:bb:82"',
        ]
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(sample_output)
        temp_path = handle.name

    try:
        adapted_command = step5_command.replace(
            'ubus-cli "WiFi.AccessPoint.1.?"',
            f"cat {temp_path}",
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
        "EntryCount5g=1",
        "EntryMac5g=62:2F:B8:66:BB:82",
    ]


@pytest.mark.parametrize(
    ("filename", "sample_output", "expected_lines"),
    [
        (
            "D047_supportedhe160mcs.yaml",
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
            "D048_supportedhemcs.yaml",
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
            "D050_supportedvhtmcs.yaml",
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
    ],
)
def test_associateddevice_sibling_sed_fragments_execute(
    filename: str, sample_output: str, expected_lines: list[str]
):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
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


def test_d054_driver_txerrors_command_extracts_sta_info_fields():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D054_txerrors.yaml")
    step4_command = case_data["steps"][3]["command"]
    sed_script = step4_command.split("| sed -n ", 1)[1]
    driver_output = "\n".join(
        [
            "rate of last tx pkt: 866000 Kbps",
            "    tx failures: 26",
            "idle 0 seconds",
        ]
    )

    proc = subprocess.run(
        [
            "sh",
            "-lc",
            f'STA_MAC="2C:59:17:00:04:85"; [ -n "$STA_MAC" ] && echo DriverAssocMac=$STA_MAC; cat <<\'EOF\' | sed -n {sed_script}\n{driver_output}\nEOF',
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines() == [
        "DriverAssocMac=2C:59:17:00:04:85",
        "DriverTxErrors=26",
    ]


def test_run_sta_band_connect_sequence_keeps_6g_ctrl_alive(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["STA"] = object()
    commands: list[tuple[str, str]] = []
    connect_calls: list[tuple[str, str, str]] = []

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del transport, timeout
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "down", "stderr": ""}
        if command == "iw dev wl1.1 info":
            return {"returncode": 1, "stdout": "", "stderr": "No such device"}
        return {"returncode": 0, "stdout": "", "stderr": ""}

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

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
    monkeypatch.setattr(plugin, "_run_required_command", fake_run_required_command)
    monkeypatch.setattr(plugin, "_connect_with_retry", fake_connect_with_retry)

    assert plugin._run_sta_band_connect_sequence({"id": "wifi-llapi-runtime-sequence"}) is True

    command_values = [command for _, command in commands]
    assert "iw dev wl0 disconnect 2>/dev/null || true" in command_values
    assert "iw dev wl1 disconnect 2>/dev/null || true" in command_values
    assert "iw dev wl2 disconnect 2>/dev/null || true" in command_values
    assert "iw dev wl0 set type managed" in command_values
    assert "iw dev wl1 set type managed" in command_values
    assert "iw dev wl2 set type managed" in command_values
    six_g_prep_commands = [
        command for label, command in commands if label.startswith("sta_6g_prep.")
    ]
    assert six_g_prep_commands[:3] == [
        "ubus-cli WiFi.AccessPoint.3.Enable=0",
        "ubus-cli WiFi.AccessPoint.4.Enable=0",
        "sleep 3",
    ]
    assert "ifconfig wl1 down" in six_g_prep_commands
    assert "wl -i wl1 down" in six_g_prep_commands
    assert "wl -i wl1 ap 0" in six_g_prep_commands
    assert "iw dev wl1 set type managed" in six_g_prep_commands
    assert "wl -i wl1 up" in six_g_prep_commands
    assert "ifconfig wl1 up" in six_g_prep_commands
    assert command_values.count("killall wpa_supplicant 2>/dev/null || true") == 1
    assert "wpa_cli -i wl1 terminate 2>/dev/null || true" in command_values
    assert "wpa_cli -i wl2 terminate 2>/dev/null || true" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 enable_network 0" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl1 enable_network 0" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl1 select_network 0" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 enable_network 0" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl2 select_network 0" in command_values
    assert "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant" in command_values
    assert "wpa_supplicant -B -D nl80211 -i wl1 -c /tmp/wpa_wl1.conf -C /var/run/wpa_supplicant" in command_values
    assert "wpa_supplicant -B -D nl80211 -i wl2 -c /tmp/wpa_wl2.conf -C /var/run/wpa_supplicant" in command_values
    assert not any(label.startswith("sta_6g_net.") for label, _ in commands)
    assert any(
        command == "printf '%s\\n' 'ssid=\"testpilot6G\"' >> /tmp/wpa_wl1.conf"
        for label, command in commands
        if label.startswith("sta_6g_prep.")
    )
    assert (
        "sta_5g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
    ) in connect_calls
    assert (
        "sta_5g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0",
        "iw dev wl0 link",
    ) in connect_calls
    assert (
        "sta_6g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
    ) in connect_calls
    assert (
        "sta_6g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 select_network 0",
        (
            "iw dev wl1 link",
            "wpa_cli -p /var/run/wpa_supplicant -i wl1 status",
            "wl -i wl1 status",
        ),
    ) in connect_calls
    assert (
        "sta_24g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 ping",
    ) in connect_calls
    assert (
        "sta_24g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 select_network 0",
        ("iw dev wl2 link", "wl -i wl2 status"),
    ) in connect_calls


def test_run_sta_band_connect_sequence_limits_to_selected_band(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["STA"] = object()
    commands: list[tuple[str, str]] = []
    connect_calls: list[tuple[str, str, str]] = []

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del transport, timeout
        return {"returncode": 0, "stdout": "", "stderr": ""}

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

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
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
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 enable_network 0" in command_values
    assert "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0" in command_values
    assert connect_calls == [
        (
            "sta_5g_ctrl",
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
        ),
        (
            "sta_5g",
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0",
            "iw dev wl0 link",
        ),
    ]


def _runtime_explicit_multiband_connect_case() -> dict[str, Any]:
    return {
        "id": "wifi-llapi-runtime-explicit-connect",
        "steps": [
            {
                "id": "step1_5g_sta_join",
                "action": "exec",
                "target": "STA",
                "band": "5g",
                "command": [
                    "wl -i wl0 down",
                    "sleep 1",
                    "wl -i wl0 up",
                    "sleep 1",
                    "wl -i wl0 join testpilot5G imode bss",
                    "sleep 3",
                    "wl -i wl0 status",
                ],
            },
            {
                "id": "step6_6g_sta_join",
                "action": "exec",
                "target": "STA",
                "band": "6g",
                "command": [
                    "iw dev wl1 link",
                    "wpa_cli -p /var/run/wpa_supplicant -i wl1 status",
                    "wl -i wl1 status",
                ],
            },
            {
                "id": "step11_24g_sta_join",
                "action": "exec",
                "target": "STA",
                "band": "2.4g",
                "command": [
                    "wl -i wl2 down",
                    "sleep 1",
                    "wl -i wl2 up",
                    "sleep 1",
                    "wl -i wl2 join testpilot2G imode bss",
                    "sleep 3",
                    "wl -i wl2 status",
                ],
            },
        ],
    }


def test_run_sta_band_connect_sequence_prefers_case_sta_join_steps(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["STA"] = object()
    commands: list[tuple[str, str]] = []
    connect_calls: list[tuple[str, str, str]] = []
    env_commands: list[str] = []

    case = _runtime_explicit_multiband_connect_case()

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del transport, timeout
        env_commands.append(command)
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "down", "stderr": ""}
        if command == "iw dev wl1.1 info":
            return {"returncode": 1, "stdout": "", "stderr": "No such device"}
        if command == "wl -i wl0 status":
            return {
                "returncode": 0,
                "stdout": (
                    "SSID: testpilot5G\n"
                    "Mode: Managed RSSI: -44 dBm noise: -91 dBm Channel: 36\n"
                    "BSSID: 2c:59:17:00:19:95 Capability: ESS ShortSlot\n"
                ),
                "stderr": "",
            }
        if command == "wl -i wl2 status":
            return {
                "returncode": 0,
                "stdout": (
                    "SSID: testpilot2G\n"
                    "Mode: Managed RSSI: -55 dBm noise: -92 dBm Channel: 1\n"
                    "BSSID: 2c:59:17:00:19:95 Capability: ESS ShortSlot\n"
                ),
                "stderr": "",
            }
        return {"returncode": 0, "stdout": "", "stderr": ""}

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

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
    monkeypatch.setattr(plugin, "_run_required_command", fake_run_required_command)
    monkeypatch.setattr(plugin, "_connect_with_retry", fake_connect_with_retry)

    assert plugin._run_sta_band_connect_sequence(case) is True

    command_values = [command for _, command in commands]
    assert "ubus-cli WiFi.AccessPoint.1.Enable=0" in command_values
    assert "ubus-cli WiFi.AccessPoint.2.Enable=0" in command_values
    assert "wl -i wl0 join testpilot5G imode bss" in command_values
    assert "iw dev wl0 set type managed" in command_values
    assert "iw dev wl1 set type managed" in command_values
    assert "wl -i wl1 up" in command_values
    assert "ifconfig wl1 up" in command_values
    assert "wpa_supplicant -B -D nl80211 -i wl1 -c /tmp/wpa_wl1.conf -C /var/run/wpa_supplicant" in command_values
    assert any('ssid="testpilot6G"' in command for command in command_values)
    assert "ubus-cli WiFi.AccessPoint.5.Enable=0" in command_values
    assert "ubus-cli WiFi.AccessPoint.6.Enable=0" in command_values
    assert "wl -i wl2 join testpilot2G imode bss" in command_values
    assert "iw dev wl2 set type managed" in command_values
    assert "printf '%s\\n' 'ssid=\"testpilot5G\"' >> /tmp/wpa_wl0.conf" not in command_values
    assert "printf '%s\\n' 'ssid=\"testpilot2G\"' >> /tmp/wpa_wl2.conf" not in command_values
    assert (
        "sta_5g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 reconnect",
        "iw dev wl0 link",
    ) not in connect_calls
    assert (
        "sta_6g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
    ) in connect_calls
    assert (
        "sta_6g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 select_network 0",
        (
            "iw dev wl1 link",
            "wpa_cli -p /var/run/wpa_supplicant -i wl1 status",
            "wl -i wl1 status",
        ),
    ) in connect_calls
    assert (
        "sta_24g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 reconnect",
        "iw dev wl2 link",
    ) not in connect_calls
    assert "wl -i wl0 status" in env_commands
    assert "wl -i wl2 status" in env_commands
    assert "iw dev wl0 link" not in env_commands
    assert "iw dev wl2 link" not in env_commands


def test_run_sta_band_connect_sequence_falls_back_after_case_sta_join_failure(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["STA"] = object()
    commands: list[tuple[str, str]] = []
    connect_calls: list[tuple[str, str, str]] = []
    env_commands: list[str] = []

    case = _runtime_explicit_multiband_connect_case()

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del transport, timeout
        env_commands.append(command)
        if command == "wl -i wl1 bss":
            return {"returncode": 0, "stdout": "down", "stderr": ""}
        if command == "iw dev wl1.1 info":
            return {"returncode": 1, "stdout": "", "stderr": "No such device"}
        if command in {"wl -i wl0 status", "wl -i wl2 status"}:
            return {
                "returncode": 0,
                "stdout": 'Not associated. Last associated with SSID: ""',
                "stderr": "",
            }
        return {"returncode": 0, "stdout": "", "stderr": ""}

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

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
    monkeypatch.setattr(plugin, "_run_required_command", fake_run_required_command)
    monkeypatch.setattr(plugin, "_connect_with_retry", fake_connect_with_retry)

    assert plugin._run_sta_band_connect_sequence(case) is True

    command_values = [command for _, command in commands]
    assert "wl -i wl0 join testpilot5G imode bss" in command_values
    assert "wl -i wl1 up" in command_values
    assert "ifconfig wl1 up" in command_values
    assert "wpa_supplicant -B -D nl80211 -i wl1 -c /tmp/wpa_wl1.conf -C /var/run/wpa_supplicant" in command_values
    assert any('ssid="testpilot6G"' in command for command in command_values)
    assert "wl -i wl2 join testpilot2G imode bss" in command_values
    assert "wl -i wl2 down" in command_values
    assert "printf '%s\\n' 'ssid=\"testpilot5G\"' >> /tmp/wpa_wl0.conf" in command_values
    assert "printf '%s\\n' 'psk=\"00000000\"' >> /tmp/wpa_wl0.conf" in command_values
    assert "printf '%s\\n' 'ssid=\"testpilot2G\"' >> /tmp/wpa_wl2.conf" in command_values
    assert "printf '%s\\n' 'psk=\"00000000\"' >> /tmp/wpa_wl2.conf" in command_values
    assert (
        "sta_5g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
    ) in connect_calls
    assert (
        "sta_5g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0",
        "iw dev wl0 link",
    ) in connect_calls
    assert (
        "sta_24g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 ping",
    ) in connect_calls
    assert (
        "sta_24g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl2 select_network 0",
        ("iw dev wl2 link", "wl -i wl2 status"),
    ) in connect_calls
    assert (
        "sta_6g_ctrl",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 ping",
    ) in connect_calls
    assert (
        "sta_6g",
        "wpa_cli -p /var/run/wpa_supplicant -i wl1 select_network 0",
        (
            "iw dev wl1 link",
            "wpa_cli -p /var/run/wpa_supplicant -i wl1 status",
            "wl -i wl1 status",
        ),
    ) in connect_calls
    assert env_commands.count("wl -i wl0 status") == 3
    assert env_commands.count("wl -i wl2 status") == 3


def test_run_sta_band_connect_sequence_falls_back_to_wl_join_after_5g_supplicant_failure(monkeypatch):
    plugin = _load_plugin()
    plugin._transports["STA"] = object()
    commands: list[tuple[str, str]] = []
    connect_calls: list[tuple[str, str, str]] = []

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del transport, timeout
        return {"returncode": 0, "stdout": "", "stderr": ""}

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
        return label != "sta_5g"

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)
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
    assert "killall wpa_supplicant 2>/dev/null || true" in command_values
    assert "iw dev wl0 disconnect 2>/dev/null || true" in command_values
    assert "wl -i wl0 down" in command_values
    assert "wl -i wl0 up" in command_values
    assert connect_calls == [
        (
            "sta_5g_ctrl",
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 ping",
        ),
        (
            "sta_5g",
            "wpa_cli -p /var/run/wpa_supplicant -i wl0 select_network 0",
            "iw dev wl0 link",
        ),
        (
            "sta_5g_driver",
            "wl -i wl0 join testpilot5G imode bss",
            "wl -i wl0 status",
        ),
    ]


def test_status_only_sta_checks_do_not_override_deterministic_band_connect():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d006 = load_case(cases_dir / "D006_sendbsstransferrequest.yaml")
    d007 = load_case(cases_dir / "D007_sendremotemeasumentrequest.yaml")

    for case in (d006, d007):
        assert plugin._case_sta_band_connect_commands(case, "5g") == []
        assert plugin._case_sta_band_connect_commands(case, "2.4g") == []
        assert plugin._sta_band_verify_command(case, "5g") == "iw dev wl0 link"
        assert plugin._sta_band_verify_command(case, "2.4g") == "iw dev wl2 link"


def test_is_explicit_sta_connect_step_ignores_wpa_cli_status_path():
    plugin = _load_plugin()

    assert plugin._is_explicit_sta_connect_step(
        "wpa_cli -p /var/run/wpa_supplicant -i wl0 status"
    ) is False
    assert plugin._is_explicit_sta_connect_step(
        "wpa_supplicant -B -D nl80211 -i wl0 -c /tmp/wpa_wl0.conf -C /var/run/wpa_supplicant"
    ) is True


def test_verify_sta_band_connectivity_prefers_case_status_checks(monkeypatch):
    plugin = _load_plugin()
    sta = object()
    dut = object()
    plugin._transports["STA"] = sta
    plugin._transports["DUT"] = dut
    sta_commands: list[str] = []
    dut_commands: list[str] = []

    case = _runtime_explicit_multiband_connect_case()

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        if transport is sta:
            sta_commands.append(command)
            if command == "wl -i wl0 status":
                return {
                    "returncode": 0,
                    "stdout": (
                        'SSID: "testpilot5G"\n'
                        "Mode: Managed RSSI: -28 dBm noise: -92 dBm Channel: 36\n"
                        "BSSID: 2C:59:17:00:04:85 Capability: ESS\n"
                    ),
                    "stderr": "",
                }
            if command == "wl -i wl1 status":
                return {
                    "returncode": 0,
                    "stdout": (
                        'SSID: "testpilot6G"\n'
                        "Mode: Managed RSSI: -28 dBm noise: -92 dBm Channel: 37\n"
                        "BSSID: 2C:59:17:00:04:91 Capability: ESS\n"
                    ),
                    "stderr": "",
                }
            if command == "wl -i wl2 status":
                return {
                    "returncode": 0,
                    "stdout": (
                        'SSID: "testpilot2G"\n'
                        "Mode: Managed RSSI: -11 dBm noise: -89 dBm Channel: 1\n"
                        "BSSID: 2C:59:17:00:04:97 Capability: ESS\n"
                    ),
                    "stderr": "",
                }
            return {"returncode": 0, "stdout": "", "stderr": ""}

        dut_commands.append(command)
        if "AssociatedDevice" in command:
            return {
                "returncode": 0,
                "stdout": "2c:59:17:00:04:85\n2c:59:17:00:04:91\n2c:59:17:00:04:97\n",
                "stderr": "",
            }
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    assert plugin._verify_sta_band_connectivity(case) is True

    assert "wl -i wl0 status" in sta_commands
    assert "wl -i wl1 status" in sta_commands
    assert "wl -i wl2 status" in sta_commands
    assert "iw dev wl0 link" not in sta_commands
    assert "iw dev wl1 link" in sta_commands
    assert "iw dev wl2 link" not in sta_commands
    assert 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"' in dut_commands
    assert 'ubus-cli "WiFi.AccessPoint.3.AssociatedDevice.*.MACAddress?"' in dut_commands
    assert 'ubus-cli "WiFi.AccessPoint.5.AssociatedDevice.*.MACAddress?"' in dut_commands


def test_verify_sta_band_connectivity_falls_back_to_driver_status(monkeypatch):
    plugin = _load_plugin()
    sta = object()
    dut = object()
    plugin._transports["STA"] = sta
    plugin._transports["DUT"] = dut
    sta_commands: list[str] = []
    dut_commands: list[str] = []

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

    def fake_execute_env_command(transport, command, *, timeout=30.0):
        del timeout
        if transport is sta:
            sta_commands.append(command)
            if command == "iw dev wl0 link":
                return {"returncode": 0, "stdout": "Not connected.\n", "stderr": ""}
            if command == "wl -i wl0 status":
                return {
                    "returncode": 0,
                    "stdout": (
                        'SSID: "testpilot5G"\n'
                        "Mode: Managed RSSI: -30 dBm noise: -91 dBm Channel: 36\n"
                        "BSSID: 00:00:00:00:00:00 Capability: ESS WEP RRM\n"
                    ),
                    "stderr": "",
                }
            return {"returncode": 0, "stdout": "", "stderr": ""}

        dut_commands.append(command)
        if "AssociatedDevice" in command:
            return {
                "returncode": 0,
                "stdout": 'WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress="2C:59:17:00:19:95"\n',
                "stderr": "",
            }
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(plugin, "_execute_env_command", fake_execute_env_command)

    assert plugin._verify_sta_band_connectivity(case) is True

    assert sta_commands[:2] == ["iw dev wl0 link", "wl -i wl0 status"]
    assert 'ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.*.MACAddress?"' in dut_commands


# ---------------------------------------------------------------------------
# D176 BeaconPeriod — setter + hostapd convergence
# ---------------------------------------------------------------------------


def test_d176_beaconperiod_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d176_raw = yaml.safe_load((cases_dir / "D176_beaconperiod.yaml").read_text(encoding="utf-8"))
    d176 = load_case(cases_dir / "D176_beaconperiod.yaml")
    d176_commands = "\n".join(str(step.get("command", "")) for step in d176["steps"])

    assert "aliases" not in d176_raw
    assert d176["id"] == "d176-radio-beaconperiod"
    assert d176["source"]["row"] == 176
    assert d176["hlapi_command"] == "ubus-cli WiFi.Radio.1.BeaconPeriod=1000"
    assert d176["bands"] == ["5g", "6g", "2.4g"]
    assert set(d176["topology"]["devices"]) == {"DUT"}
    assert d176["topology"]["links"] == []
    assert "ubus-cli WiFi.Radio.1.BeaconPeriod=100" in d176.get("sta_env_setup", "")
    assert "RequestedBeaconPeriod24g=1000" in d176_commands
    assert "grep '^beacon_int=' /tmp/wl1_hapd.conf" in d176_commands
    assert len(d176["steps"]) == 24
    assert len(d176["pass_criteria"]) == 33
    assert any(
        criterion["field"] == "after_set_hostapd_6g.AfterSetHostapdBeaconPeriod6g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "after_set_getter_6g.BeaconPeriod"
        for criterion in d176["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_restore_hostapd_24g.AfterRestoreHostapdBeaconPeriod24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "100"
        for criterion in d176["pass_criteria"]
    )


def test_d176_beaconperiod_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d176 = load_case(cases_dir / "D176_beaconperiod.yaml")

    assert plugin.setup_env(d176, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.Radio.1.BeaconPeriod=100") == 1
    assert executed_commands.count("ubus-cli WiFi.Radio.2.BeaconPeriod=100") == 1
    assert executed_commands.count("ubus-cli WiFi.Radio.3.BeaconPeriod=100") == 1
    assert executed_commands.count("sleep 3") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d176, topology)


def test_d176_beaconperiod_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d176 = load_case(cases_dir / "D176_beaconperiod.yaml")

    def getter_output(radio: int, value: str) -> str:
        return f"WiFi.Radio.{radio}.BeaconPeriod={value}"

    def hostapd_output(field: str, value: str) -> str:
        return f"{field}={value}"

    def set_output(prefix: str) -> str:
        return f"RequestedBeaconPeriod{prefix}=1000"

    def restore_output(prefix: str) -> str:
        return f"RestoreBeaconPeriod{prefix}=100"

    steps = {}
    for base_idx, prefix, radio in ((1, "5g", 1), (9, "6g", 2), (17, "24g", 3)):
        steps[f"step{base_idx}_beacon_baseline_getter_{prefix}"] = {
            "success": True,
            "output": getter_output(radio, "100"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 1}_beacon_baseline_hostapd_{prefix}"] = {
            "success": True,
            "output": hostapd_output(f"BaselineHostapdBeaconPeriod{prefix}", "100"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 2}_beacon_set_{prefix}"] = {
            "success": True,
            "output": set_output(prefix),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 3}_beacon_after_set_getter_{prefix}"] = {
            "success": True,
            "output": getter_output(radio, "1000"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 4}_beacon_after_set_hostapd_{prefix}"] = {
            "success": True,
            "output": hostapd_output(f"AfterSetHostapdBeaconPeriod{prefix}", "1000"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 5}_beacon_restore_{prefix}"] = {
            "success": True,
            "output": restore_output(prefix),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 6}_beacon_after_restore_getter_{prefix}"] = {
            "success": True,
            "output": getter_output(radio, "100"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 7}_beacon_after_restore_hostapd_{prefix}"] = {
            "success": True,
            "output": hostapd_output(f"AfterRestoreHostapdBeaconPeriod{prefix}", "100"),
            "timing": 0.01,
        }

    d176_results = {"steps": steps}
    assert plugin.evaluate(d176, d176_results) is True

    d176_wrong_6g_hostapd_after_set = {
        "steps": {
            **d176_results["steps"],
            "step13_beacon_after_set_hostapd_6g": {
                "success": True,
                "output": hostapd_output("AfterSetHostapdBeaconPeriod6g", "100"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d176, d176_wrong_6g_hostapd_after_set) is False

    d176_wrong_5g_getter_after_set = {
        "steps": {
            **d176_results["steps"],
            "step4_beacon_after_set_getter_5g": {
                "success": True,
                "output": getter_output(1, "100"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d176, d176_wrong_5g_getter_after_set) is False

    d176_wrong_24g_hostapd_restore = {
        "steps": {
            **d176_results["steps"],
            "step24_beacon_after_restore_hostapd_24g": {
                "success": True,
                "output": hostapd_output("AfterRestoreHostapdBeaconPeriod24g", "1000"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d176, d176_wrong_24g_hostapd_restore) is False


def test_d188_dtimperiod_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    d188_raw = yaml.safe_load((cases_dir / "D188_dtimperiod.yaml").read_text(encoding="utf-8"))
    d188 = load_case(cases_dir / "D188_dtimperiod.yaml")
    d188_commands = "\n".join(str(step.get("command", "")) for step in d188["steps"])

    assert "aliases" not in d188_raw
    assert d188["id"] == "d188-radio-dtimperiod"
    assert d188["source"]["row"] == 188
    assert d188["hlapi_command"] == "ubus-cli WiFi.Radio.1.DTIMPeriod=7"
    assert d188["bands"] == ["5g", "6g", "2.4g"]
    assert set(d188["topology"]["devices"]) == {"DUT"}
    assert d188["topology"]["links"] == []
    assert "ubus-cli WiFi.Radio.1.DTIMPeriod=3" in d188.get("sta_env_setup", "")
    assert "RequestedDtimPeriod24g=7" in d188_commands
    assert "grep '^dtim_period=' /tmp/wl1_hapd.conf" in d188_commands
    assert len(d188["steps"]) == 24
    assert len(d188["pass_criteria"]) == 33
    assert any(
        criterion["field"] == "after_set_hostapd_6g.AfterSetHostapdDtimPeriod6g"
        and criterion["operator"] == "equals"
        and criterion.get("reference") == "after_set_getter_6g.DTIMPeriod"
        for criterion in d188["pass_criteria"]
    )
    assert any(
        criterion["field"] == "after_restore_hostapd_24g.AfterRestoreHostapdDtimPeriod24g"
        and criterion["operator"] == "equals"
        and criterion["value"] == "3"
        for criterion in d188["pass_criteria"]
    )


def test_d188_dtimperiod_setup_env_uses_only_dut_transport(monkeypatch):
    plugin = _load_plugin()
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d188 = load_case(cases_dir / "D188_dtimperiod.yaml")

    assert plugin.setup_env(d188, topology=topology) is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "serial"
    executed_commands = recorder.transports[0].executed_commands
    assert executed_commands.count("ubus-cli WiFi.Radio.1.DTIMPeriod=3") == 1
    assert executed_commands.count("ubus-cli WiFi.Radio.2.DTIMPeriod=3") == 1
    assert executed_commands.count("ubus-cli WiFi.Radio.3.DTIMPeriod=3") == 1
    assert executed_commands.count("sleep 3") == 1
    assert all("STA" not in command for command in executed_commands)
    plugin.teardown(d188, topology)


def test_d188_dtimperiod_evaluate_live_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    d188 = load_case(cases_dir / "D188_dtimperiod.yaml")

    def getter_output(radio: int, value: str) -> str:
        return f"WiFi.Radio.{radio}.DTIMPeriod={value}"

    def hostapd_output(field: str, value: str) -> str:
        return f"{field}={value}"

    def set_output(prefix: str) -> str:
        return f"RequestedDtimPeriod{prefix}=7"

    def restore_output(prefix: str) -> str:
        return f"RestoreDtimPeriod{prefix}=3"

    steps = {}
    for base_idx, prefix, radio in ((1, "5g", 1), (9, "6g", 2), (17, "24g", 3)):
        steps[f"step{base_idx}_dtim_baseline_getter_{prefix}"] = {
            "success": True,
            "output": getter_output(radio, "3"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 1}_dtim_baseline_hostapd_{prefix}"] = {
            "success": True,
            "output": hostapd_output(f"BaselineHostapdDtimPeriod{prefix}", "3"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 2}_dtim_set_{prefix}"] = {
            "success": True,
            "output": set_output(prefix),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 3}_dtim_after_set_getter_{prefix}"] = {
            "success": True,
            "output": getter_output(radio, "7"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 4}_dtim_after_set_hostapd_{prefix}"] = {
            "success": True,
            "output": hostapd_output(f"AfterSetHostapdDtimPeriod{prefix}", "7"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 5}_dtim_restore_{prefix}"] = {
            "success": True,
            "output": restore_output(prefix),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 6}_dtim_after_restore_getter_{prefix}"] = {
            "success": True,
            "output": getter_output(radio, "3"),
            "timing": 0.01,
        }
        steps[f"step{base_idx + 7}_dtim_after_restore_hostapd_{prefix}"] = {
            "success": True,
            "output": hostapd_output(f"AfterRestoreHostapdDtimPeriod{prefix}", "3"),
            "timing": 0.01,
        }

    d188_results = {"steps": steps}
    assert plugin.evaluate(d188, d188_results) is True

    d188_wrong_6g_hostapd_after_set = {
        "steps": {
            **d188_results["steps"],
            "step13_dtim_after_set_hostapd_6g": {
                "success": True,
                "output": hostapd_output("AfterSetHostapdDtimPeriod6g", "3"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d188, d188_wrong_6g_hostapd_after_set) is False

    d188_wrong_5g_getter_after_set = {
        "steps": {
            **d188_results["steps"],
            "step4_dtim_after_set_getter_5g": {
                "success": True,
                "output": getter_output(1, "3"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d188, d188_wrong_5g_getter_after_set) is False

    d188_wrong_24g_hostapd_restore = {
        "steps": {
            **d188_results["steps"],
            "step24_dtim_after_restore_hostapd_24g": {
                "success": True,
                "output": hostapd_output("AfterRestoreHostapdDtimPeriod24g", "7"),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d188, d188_wrong_24g_hostapd_restore) is False


def test_d178_channelload_contract() -> None:
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d178 = load_case(cases_dir / "D178_channelload.yaml")

    assert d178["source"]["row"] == 178
    assert [step["id"] for step in d178["steps"]] == [
        "step_5g_tight_capture",
        "step_6g_tight_capture",
        "step_24g_tight_capture",
    ]
    assert len(d178["pass_criteria"]) == 9

    commands = "\n".join(str(step["command"]) for step in d178["steps"])
    assert "getRadioAirStats()" in commands
    assert "ChannelLoad?" in commands
    assert "survey dump" in commands
    assert "int((busy * 100) / active)" in commands


def test_d178_channelload_setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d178 = load_case(cases_dir / "D178_channelload.yaml")
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    assert plugin.setup_env(d178, topology=topology) is True

    plugin.teardown(d178, topology)


def test_d178_channelload_evaluate_requires_airload_and_floor_based_survey_match() -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d178 = load_case(cases_dir / "D178_channelload.yaml")

    good_results = {
        "steps": {
            "step_5g_tight_capture": {
                "success": True,
                "output": "\n".join(
                    [
                        "AirLoad5g=84",
                        "ChannelLoad5g=84",
                        "SurveyActiveMs5g=57",
                        "SurveyBusyMs5g=48",
                        "SurveyChannelLoad5g=84",
                    ]
                ),
                "timing": 0.01,
            },
            "step_6g_tight_capture": {
                "success": True,
                "output": "\n".join(
                    [
                        "AirLoad6g=62",
                        "ChannelLoad6g=62",
                        "SurveyActiveMs6g=50",
                        "SurveyBusyMs6g=31",
                        "SurveyChannelLoad6g=62",
                    ]
                ),
                "timing": 0.01,
            },
            "step_24g_tight_capture": {
                "success": True,
                "output": "\n".join(
                    [
                        "AirLoad24g=98",
                        "ChannelLoad24g=98",
                        "SurveyActiveMs24g=70",
                        "SurveyBusyMs24g=69",
                        "SurveyChannelLoad24g=98",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d178, good_results) is True

    wrong_flooring = {
        "steps": {
            **good_results["steps"],
            "step_24g_tight_capture": {
                "success": True,
                "output": "\n".join(
                    [
                        "AirLoad24g=98",
                        "ChannelLoad24g=98",
                        "SurveyActiveMs24g=70",
                        "SurveyBusyMs24g=69",
                        "SurveyChannelLoad24g=99",
                    ]
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d178, wrong_flooring) is False


def test_d179_ampdu_contract() -> None:
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d179 = load_case(cases_dir / "D179_ampdu.yaml")

    assert d179["source"]["row"] == 179
    assert sorted(d179["topology"]["devices"]) == ["DUT", "STA"]
    assert [link["band"] for link in d179["topology"]["links"]] == ["5g", "6g", "2.4g"]
    assert len(d179["steps"]) == 18
    assert d179["steps"][0]["id"] == "step1_ampdu_set_5g"
    assert d179["steps"][-1]["id"] == "step18_ampdu_after_restore_24g"
    assert len(d179["pass_criteria"]) == 15

    commands = "\n".join(str(step["command"]) for step in d179["steps"])
    assert "/etc/init.d/wld_gen start" in commands
    assert "wl -i wl0 ampdu" in commands
    assert "wl -i wl1 bss" in commands
    assert "wl -i wl2 ampdu" in commands


def test_d179_ampdu_setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d179 = load_case(cases_dir / "D179_ampdu.yaml")
    topology = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    assert plugin.setup_env(d179, topology=topology) is True

    plugin.teardown(d179, topology)


def test_d179_ampdu_evaluate_requires_tri_band_setter_effects() -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d179 = load_case(cases_dir / "D179_ampdu.yaml")

    good_results = {
        "steps": {
            "step2_ampdu_after_set_5g": {
                "success": True,
                "output": "AfterSetGetterAmpdu5g=1\nAfterSetDriverAmpdu5g=1",
                "timing": 0.01,
            },
            "step4_ampdu_after_set0_5g": {
                "success": True,
                "output": "AfterSet0GetterAmpdu5g=0\nAfterSet0DriverAmpdu5g=0",
                "timing": 0.01,
            },
            "step6_ampdu_after_restore_5g": {
                "success": True,
                "output": "AfterRestoreGetterAmpdu5g=-1",
                "timing": 0.01,
            },
            "step8_ampdu_after_set_6g": {
                "success": True,
                "output": "AfterSetGetterAmpdu6g=1\nAfterSetBss6g=up",
                "timing": 0.01,
            },
            "step10_ampdu_after_set0_6g": {
                "success": True,
                "output": "AfterSet0GetterAmpdu6g=0\nAfterSet0Bss6g=down",
                "timing": 0.01,
            },
            "step12_ampdu_after_restore_6g": {
                "success": True,
                "output": "AfterRestoreGetterAmpdu6g=-1",
                "timing": 0.01,
            },
            "step14_ampdu_after_set_24g": {
                "success": True,
                "output": "AfterSetGetterAmpdu24g=1\nAfterSetDriverAmpdu24g=1",
                "timing": 0.01,
            },
            "step16_ampdu_after_set0_24g": {
                "success": True,
                "output": "AfterSet0GetterAmpdu24g=0\nAfterSet0DriverAmpdu24g=0",
                "timing": 0.01,
            },
            "step18_ampdu_after_restore_24g": {
                "success": True,
                "output": "AfterRestoreGetterAmpdu24g=-1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d179, good_results) is True

    wrong_6g_disable = {
        "steps": {
            **good_results["steps"],
            "step10_ampdu_after_set0_6g": {
                "success": True,
                "output": "AfterSet0GetterAmpdu6g=0\nAfterSet0Bss6g=up",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d179, wrong_6g_disable) is False


def test_d214_rifsenabled_contract() -> None:
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d214 = load_case(cases_dir / "D214_rifsenabled.yaml")

    assert d214["source"]["row"] == 214
    assert sorted(d214["topology"]["devices"]) == ["DUT"]
    assert len(d214["steps"]) == 15
    assert d214["steps"][0]["id"] == "step1_rifs_default_5g"
    assert d214["steps"][-1]["id"] == "step15_rifs_after_restore_24g"

    commands = "\n".join(str(step["command"]) for step in d214["steps"])
    assert "RequestedRIFSEnabled5g=Auto" in commands
    assert 'WiFi.Radio.1.RIFSEnabled="Auto"' in commands
    assert "AfterRestoreRIFSEnabled24g" in commands


def test_d214_rifsenabled_setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d214 = load_case(cases_dir / "D214_rifsenabled.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    assert plugin.setup_env(d214, topology=topo) is True
    plugin.teardown(d214, topo)


def test_d214_rifsenabled_evaluate_requires_tri_band_setter_readback() -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d214 = load_case(cases_dir / "D214_rifsenabled.yaml")

    good_results = {
        "steps": {
            "step1_rifs_default_5g": {"success": True, "output": "DefaultRIFSEnabled5g=Default", "timing": 0.01},
            "step2_rifs_set_auto_5g": {"success": True, "output": "RequestedRIFSEnabled5g=Auto", "timing": 0.01},
            "step3_rifs_after_set_5g": {"success": True, "output": "AfterSetRIFSEnabled5g=Auto", "timing": 0.01},
            "step4_rifs_restore_5g": {"success": True, "output": "RestoreRIFSEnabled5g=Default", "timing": 0.01},
            "step5_rifs_after_restore_5g": {"success": True, "output": "AfterRestoreRIFSEnabled5g=Default", "timing": 0.01},
            "step6_rifs_default_6g": {"success": True, "output": "DefaultRIFSEnabled6g=Default", "timing": 0.01},
            "step7_rifs_set_auto_6g": {"success": True, "output": "RequestedRIFSEnabled6g=Auto", "timing": 0.01},
            "step8_rifs_after_set_6g": {"success": True, "output": "AfterSetRIFSEnabled6g=Auto", "timing": 0.01},
            "step9_rifs_restore_6g": {"success": True, "output": "RestoreRIFSEnabled6g=Default", "timing": 0.01},
            "step10_rifs_after_restore_6g": {"success": True, "output": "AfterRestoreRIFSEnabled6g=Default", "timing": 0.01},
            "step11_rifs_default_24g": {"success": True, "output": "DefaultRIFSEnabled24g=Default", "timing": 0.01},
            "step12_rifs_set_auto_24g": {"success": True, "output": "RequestedRIFSEnabled24g=Auto", "timing": 0.01},
            "step13_rifs_after_set_24g": {"success": True, "output": "AfterSetRIFSEnabled24g=Auto", "timing": 0.01},
            "step14_rifs_restore_24g": {"success": True, "output": "RestoreRIFSEnabled24g=Default", "timing": 0.01},
            "step15_rifs_after_restore_24g": {"success": True, "output": "AfterRestoreRIFSEnabled24g=Default", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d214, good_results) is True

    wrong_24g_after_set = {
        "steps": {
            **good_results["steps"],
            "step13_rifs_after_set_24g": {
                "success": True,
                "output": "AfterSetRIFSEnabled24g=Default",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d214, wrong_24g_after_set) is False


def test_d354_sensing_enable_contract() -> None:
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d354 = load_case(cases_dir / "D354_enable_radio.yaml")

    assert d354["source"]["row"] == 354
    assert d354["source"]["object"] == "WiFi.Radio.{i}.Sensing."
    assert d354["source"]["api"] == "Enable"
    assert sorted(d354["topology"]["devices"]) == ["DUT"]
    assert len(d354["steps"]) == 15
    assert d354["steps"][0]["id"] == "step1_sensing_default_5g"
    assert d354["steps"][-1]["id"] == "step15_sensing_after_restore_24g"

    commands = "\n".join(str(step["command"]) for step in d354["steps"])
    assert 'WiFi.Radio.1.Sensing.Enable?"' in commands
    assert "WiFi.Radio.2.Sensing.Enable=0" in commands
    assert "WiFi.Radio.3.Sensing.Enable=1" in commands


def test_d354_sensing_enable_setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d354 = load_case(cases_dir / "D354_enable_radio.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    assert plugin.setup_env(d354, topology=topo) is True
    plugin.teardown(d354, topo)


def test_d354_sensing_enable_evaluate_requires_tri_band_setter_readback() -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d354 = load_case(cases_dir / "D354_enable_radio.yaml")

    good_results = {
        "steps": {
            "step1_sensing_default_5g": {
                "success": True,
                "output": "WiFi.Radio.1.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step2_sensing_set_disable_5g": {
                "success": True,
                "output": "WiFi.Radio.1.Sensing.\nWiFi.Radio.1.Sensing.Enable=0",
                "timing": 0.01,
            },
            "step3_sensing_after_disable_5g": {
                "success": True,
                "output": "WiFi.Radio.1.Sensing.Enable=0",
                "timing": 0.01,
            },
            "step4_sensing_restore_5g": {
                "success": True,
                "output": "WiFi.Radio.1.Sensing.\nWiFi.Radio.1.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step5_sensing_after_restore_5g": {
                "success": True,
                "output": "WiFi.Radio.1.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step6_sensing_default_6g": {
                "success": True,
                "output": "WiFi.Radio.2.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step7_sensing_set_disable_6g": {
                "success": True,
                "output": "WiFi.Radio.2.Sensing.\nWiFi.Radio.2.Sensing.Enable=0",
                "timing": 0.01,
            },
            "step8_sensing_after_disable_6g": {
                "success": True,
                "output": "WiFi.Radio.2.Sensing.Enable=0",
                "timing": 0.01,
            },
            "step9_sensing_restore_6g": {
                "success": True,
                "output": "WiFi.Radio.2.Sensing.\nWiFi.Radio.2.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step10_sensing_after_restore_6g": {
                "success": True,
                "output": "WiFi.Radio.2.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step11_sensing_default_24g": {
                "success": True,
                "output": "WiFi.Radio.3.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step12_sensing_set_disable_24g": {
                "success": True,
                "output": "WiFi.Radio.3.Sensing.\nWiFi.Radio.3.Sensing.Enable=0",
                "timing": 0.01,
            },
            "step13_sensing_after_disable_24g": {
                "success": True,
                "output": "WiFi.Radio.3.Sensing.Enable=0",
                "timing": 0.01,
            },
            "step14_sensing_restore_24g": {
                "success": True,
                "output": "WiFi.Radio.3.Sensing.\nWiFi.Radio.3.Sensing.Enable=1",
                "timing": 0.01,
            },
            "step15_sensing_after_restore_24g": {
                "success": True,
                "output": "WiFi.Radio.3.Sensing.Enable=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d354, good_results) is True

    wrong_24g_after_disable = {
        "steps": {
            **good_results["steps"],
            "step13_sensing_after_disable_24g": {
                "success": True,
                "output": "WiFi.Radio.3.Sensing.Enable=1",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d354, wrong_24g_after_disable) is False


def test_d251_regulatorydomainrev_contract() -> None:
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d251 = load_case(cases_dir / "D251_regulatorydomain_radio_vendor.yaml")

    assert d251["source"]["row"] == 251
    assert sorted(d251["topology"]["devices"]) == ["DUT"]
    assert len(d251["steps"]) == 21
    assert d251["steps"][0]["id"] == "step1_regrev_default_5g"
    assert d251["steps"][-1]["id"] == "step21_regrev_after_restore_24g"

    commands = "\n".join(str(step["command"]) for step in d251["steps"])
    assert "RegulatoryDomainRev=8" in commands
    assert "RegDomSupported5g" in commands
    assert "wl -i wl0 country" in commands


def test_d251_regulatorydomainrev_setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d251 = load_case(cases_dir / "D251_regulatorydomain_radio_vendor.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)

    assert plugin.setup_env(d251, topology=topo) is True
    plugin.teardown(d251, topo)


def test_d251_regulatorydomainrev_evaluate_requires_rd_override_shape() -> None:
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    d251 = load_case(cases_dir / "D251_regulatorydomain_radio_vendor.yaml")

    good_results = {
        "steps": {
            "step1_regrev_default_5g": {"success": True, "output": "DefRegRev5g=0", "timing": 0.01},
            "step2_regrev_set_5g": {"success": True, "output": "ReqRegRev5g=8", "timing": 0.01},
            "step3_regrev_after_set_5g": {"success": True, "output": "AfterSetRegRev5g=8", "timing": 0.01},
            "step4_regdom_supported_5g": {"success": True, "output": "RegDomSupported5g=#a,CA/169", "timing": 0.01},
            "step5_country_5g": {"success": True, "output": "Country5g=#a (#a/0) <unknown>", "timing": 0.01},
            "step6_regrev_restore_5g": {"success": True, "output": "RestoreRegRev5g=0", "timing": 0.01},
            "step7_regrev_after_restore_5g": {"success": True, "output": "AfterRestoreRegRev5g=0", "timing": 0.01},
            "step8_regrev_default_6g": {"success": True, "output": "DefRegRev6g=0", "timing": 0.01},
            "step9_regrev_set_6g": {"success": True, "output": "ReqRegRev6g=8", "timing": 0.01},
            "step10_regrev_after_set_6g": {"success": True, "output": "AfterSetRegRev6g=8", "timing": 0.01},
            "step11_regdom_supported_6g": {"success": True, "output": "RegDomSupported6g=#a,CA/169", "timing": 0.01},
            "step12_country_6g": {"success": True, "output": "Country6g=#a (#a/0) <unknown>", "timing": 0.01},
            "step13_regrev_restore_6g": {"success": True, "output": "RestoreRegRev6g=0", "timing": 0.01},
            "step14_regrev_after_restore_6g": {"success": True, "output": "AfterRestoreRegRev6g=0", "timing": 0.01},
            "step15_regrev_default_24g": {"success": True, "output": "DefRegRev24g=0", "timing": 0.01},
            "step16_regrev_set_24g": {"success": True, "output": "ReqRegRev24g=8", "timing": 0.01},
            "step17_regrev_after_set_24g": {"success": True, "output": "AfterSetRegRev24g=8", "timing": 0.01},
            "step18_regdom_supported_24g": {"success": True, "output": "RegDomSupported24g=#a,CA/169", "timing": 0.01},
            "step19_country_24g": {"success": True, "output": "Country24g=#a (#a/0) <unknown>", "timing": 0.01},
            "step20_regrev_restore_24g": {"success": True, "output": "RestoreRegRev24g=0", "timing": 0.01},
            "step21_regrev_after_restore_24g": {"success": True, "output": "AfterRestoreRegRev24g=0", "timing": 0.01},
        }
    }
    assert plugin.evaluate(d251, good_results) is True

    wrong_country = {
        "steps": {
            **good_results["steps"],
            "step12_country_6g": {
                "success": True,
                "output": "Country6g=JP (JP/89) <unknown>",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(d251, wrong_country) is False


# Remaining WiFi.Radio.{i} read-only getter batch
# ---------------------------------------------------------------------------

# Parametrized table: (yaml_file, row, live_5g, live_6g, live_24g, llapi_path_template)
# llapi_path_template uses {r} for radio number (1=5g, 2=6g, 3=2.4g)
_RADIO_GETTER_CASES = [
    ("D174_activeantennactrl.yaml", 174, "-1", "-1", "-1", "WiFi.Radio.{r}.ActiveAntennaCtrl"),
    ("D180_amsdu.yaml", 180, "-1", "-1", "-1", "WiFi.Radio.{r}.DriverConfig.Amsdu"),
    ("D181_fragmentationthreshold.yaml", 144, "-1", "-1", "-1", "WiFi.Radio.{r}.DriverConfig.FragmentationThreshold"),
    ("D182_rtsthreshold.yaml", 145, "-1", "-1", "-1", "WiFi.Radio.{r}.DriverConfig.RtsThreshold"),
    ("D184_nractiverxantenna.yaml", 184, "4", "4", "4", "WiFi.Radio.{r}.DriverStatus.NrActiveRxAntenna"),
    ("D185_nractivetxantenna.yaml", 185, "4", "4", "4", "WiFi.Radio.{r}.DriverStatus.NrActiveTxAntenna"),
    ("D186_nrrxantenna.yaml", 186, "4", "4", "4", "WiFi.Radio.{r}.NrRxAntenna"),
    ("D187_nrtxantenna.yaml", 187, "4", "4", "4", "WiFi.Radio.{r}.NrTxAntenna"),
    ("D190_explicitbeamformingenabled.yaml", 190, "1", "1", "1", "WiFi.Radio.{r}.ExplicitBeamFormingEnabled"),
    ("D191_explicitbeamformingsupported.yaml", 191, "1", "1", "1", "WiFi.Radio.{r}.ExplicitBeamFormingSupported"),
    ("D192_guardinterval.yaml", 192, "Auto", "Auto", "Auto", "WiFi.Radio.{r}.GuardInterval"),
    # --- Batch 1: D193-D214 Radio config/capabilities ---
    ("D193_hecapsenabled.yaml", 193, "DEFAULT", "DEFAULT", "DEFAULT", "WiFi.Radio.{r}.HeCapsEnabled"),
    ("D194_hecapssupported.yaml", 194, "DL_OFDMA,UL_OFDMA,DL_MUMIMO,UL_MUMIMO", "DL_OFDMA,UL_OFDMA,DL_MUMIMO,UL_MUMIMO", "DL_OFDMA,UL_OFDMA,DL_MUMIMO,UL_MUMIMO", "WiFi.Radio.{r}.HeCapsSupported"),
    ("D195_ieee80211_caps.yaml", 195, "160MHz UAPSD WEP TKIP AES AES_CCM SAE EXPL_BF IMPL_BF MU_MIMO DFS_OFFLOAD OWE SAE_PWE WME", "320MHz 160MHz UAPSD SAE EXPL_BF IMPL_BF MU_MIMO OWE SAE_PWE WME", "UAPSD WEP TKIP AES AES_CCM SAE EXPL_BF IMPL_BF MU_MIMO OWE SAE_PWE WME", "WiFi.Radio.{r}.IEEE80211_Caps"),
    ("D196_ieee80211henabled.yaml", 196, "1", "0", "0", "WiFi.Radio.{r}.IEEE80211hEnabled"),
    ("D197_ieee80211hsupported.yaml", 197, "1", "0", "0", "WiFi.Radio.{r}.IEEE80211hSupported"),
    ("D198_ieee80211ksupported.yaml", 198, "1", "1", "1", "WiFi.Radio.{r}.IEEE80211kSupported"),
    ("D199_ieee80211rsupported.yaml", 199, "1", "1", "1", "WiFi.Radio.{r}.IEEE80211rSupported"),
    ("D200_implicitbeamformingenabled.yaml", 200, "1", "1", "1", "WiFi.Radio.{r}.ImplicitBeamFormingEnabled"),
    ("D201_implicitbeamformingsupported.yaml", 201, "1", "1", "1", "WiFi.Radio.{r}.ImplicitBeamFormingSupported"),
    ("D202_interference.yaml", 202, "0", "0", "0", "WiFi.Radio.{r}.Interference"),
    ("D203_maxchannelbandwidth.yaml", 203, "160MHz", "320MHz", "40MHz", "WiFi.Radio.{r}.MaxChannelBandwidth"),
    ("D204_multiusermimoenabled.yaml", 167, "1", "1", "0", "WiFi.Radio.{r}.MultiUserMIMOEnabled"),
    ("D205_multiusermimosupported.yaml", 205, "1", "1", "1", "WiFi.Radio.{r}.MultiUserMIMOSupported"),
    ("D207_obsscoexistenceenable.yaml", 207, "0", "0", "1", "WiFi.Radio.{r}.ObssCoexistenceEnable"),
    ("D208_ofdmaenable.yaml", 208, "1", "1", "1", "WiFi.Radio.{r}.OfdmaEnable"),
    ("D209_operatingchannelbandwidth.yaml", 209, "20MHz", "20MHz", "20MHz", "WiFi.Radio.{r}.OperatingChannelBandwidth"),
    ("D211_operatingstandards.yaml", 172, "be", "be", "be", "WiFi.Radio.{r}.OperatingStandards"),
    ("D212_possiblechannels.yaml", 212, "36,40,44,48", "1,5,9,13", "1,2,3,4", "WiFi.Radio.{r}.PossibleChannels"),
    ("D213_regulatorydomain_radio.yaml", 174, "#a", "#a", "#a", "WiFi.Radio.{r}.RegulatoryDomain"),
    # --- Batch 2: D215, D245-D251 Radio getters ---
    ("D215_rxchainctrl.yaml", 176, "-1", "-1", "-1", "WiFi.Radio.{r}.RxChainCtrl"),
    ("D245_supportedfrequencybands.yaml", 177, "5GHz", "6GHz", "2.4GHz", "WiFi.Radio.{r}.SupportedFrequencyBands"),
    ("D246_supportedstandards.yaml", 178, "a,n,an,ac,ax,be", "ax,be", "b,g,n,bg,gn,bgn,ax,be", "WiFi.Radio.{r}.SupportedStandards"),
    ("D247_targetwaketimeenable.yaml", 179, "1", "1", "1", "WiFi.Radio.{r}.TargetWakeTimeEnable"),
    ("D248_transmitpower.yaml", 180, "-1", "-1", "-1", "WiFi.Radio.{r}.TransmitPower"),
    ("D249_transmitpowersupported.yaml", 181, "1,2,3,100,-1", "1,2,3,100,-1", "1,2,3,100,-1", "WiFi.Radio.{r}.TransmitPowerSupported"),
    ("D250_txchainctrl.yaml", 182, "-1", "-1", "-1", "WiFi.Radio.{r}.TxChainCtrl"),
    # --- Batch 5a: Radio property getters ---
    ("D189_enable_radio_sensing.yaml", 264, "1", "1", "1", "WiFi.Radio.{r}.Sensing.Enable"),
    ("D376_longretrylimit.yaml", 279, "6", "6", "6", "WiFi.Radio.{r}.LongRetryLimit"),
    ("D377_maxbitrate.yaml", 377, "0", "0", "0", "WiFi.Radio.{r}.MaxBitRate"),
    ("D378_maxsupportedssids.yaml", 281, "8", "8", "8", "WiFi.Radio.{r}.MaxSupportedSSIDs"),
    ("D381_noise_radio.yaml", 284, "-100", "-97", "-79", "WiFi.Radio.{r}.Noise"),
    ("D382_operatingfrequencyband.yaml", 285, "5GHz", "6GHz", "2.4GHz", "WiFi.Radio.{r}.OperatingFrequencyBand"),
    ("D383_radcapabilitieshephysstr.yaml", 286, "40_80MHZ_5GHZ,160MHZ_5GHZ,FULL_UL_MU_MIMO,SU_BEAMFORMER,MU_BEAMFORMER", "40_80MHZ_5GHZ,160MHZ_5GHZ,FULL_UL_MU_MIMO,SU_BEAMFORMER,MU_BEAMFORMER", "40MHZ_2_4GHZ,FULL_UL_MU_MIMO,SU_BEAMFORMER,MU_BEAMFORMER", "WiFi.Radio.{r}.RadCapabilitiesHePhysStr"),
    ("D384_radcapabilitieshtstr.yaml", 384, "CAP_40,SHORT_GI_20,SHORT_GI_40,MODE_40", "", "CAP_40,SHORT_GI_20,SHORT_GI_40,MODE_40", "WiFi.Radio.{r}.RadCapabilitiesHTStr"),
    ("D385_radcapabilitiesvhtstr.yaml", 385, "RX_LDPC,SGI_80,SGI_160,SU_BFR,SU_BFE,LINK_ADAPT_CAP", "", "", "WiFi.Radio.{r}.RadCapabilitiesVHTStr"),
    ("D404_txbeamformingcapsavailable.yaml", 299, "VHT_SU_BF,HE_SU_BF,HE_MU_BF,EHT_SU_BF,EHT_MU_80_BF,EHT_MU_160_BF,EHT_MU_320_BF", "HE_SU_BF,HE_MU_BF,EHT_SU_BF,EHT_MU_80_BF,EHT_MU_160_BF,EHT_MU_320_BF", "HE_SU_BF,HE_MU_BF,EHT_SU_BF,EHT_MU_80_BF,EHT_MU_160_BF,EHT_MU_320_BF", "WiFi.Radio.{r}.TxBeamformingCapsAvailable"),
    ("D405_txbeamformingcapsenabled.yaml", 300, "DEFAULT", "DEFAULT", "DEFAULT", "WiFi.Radio.{r}.TxBeamformingCapsEnabled"),
    ("D460_hecapabilities_radio.yaml", 460, "TCBCwAIbFQAAjAA=", "TCBCwAIbFQAAjAA=", "IiBCwAIDFQAAjAA=", "WiFi.Radio.{r}.HePhyCapabilities"),
    ("D461_htcapabilities_radio.yaml", 461, "YhA=", "AAA=", "YhA=", "WiFi.Radio.{r}.HTCapabilities"),
    ("D467_rxbeamformingcapsenabled.yaml", 467, "DEFAULT", "DEFAULT", "DEFAULT", "WiFi.Radio.{r}.RxBeamformingCapsEnabled"),
    # --- Batch 5b: IEEE80211ax property getters ---
    ("D365_psrdisallowed.yaml", 272, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.PSRDisallowed"),
    ("D462_bsscolor.yaml", 462, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.BssColor"),
    ("D463_hesigaspatialreusevalue15allowed.yaml", 463, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.HESIGASpatialReuseValue15Allowed"),
    ("D464_nonsrgoffsetvalid.yaml", 464, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.NonSRGOffsetValid"),
    ("D465_srginformationvalid.yaml", 465, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.SRGInformationValid"),
    # --- Bulk calibration batch 6: additional Radio/IEEE80211ax getters ---
    ("D379_mcs.yaml", 379, "0", "0", "0", "WiFi.Radio.{r}.MCS"),
    ("D380_multiaptypessupported.yaml", 380, "FronthaulBSS,BackhaulBSS,BackhaulSTA", "FronthaulBSS,BackhaulBSS,BackhaulSTA", "FronthaulBSS,BackhaulBSS,BackhaulSTA", "WiFi.Radio.{r}.MultiAPTypesSupported"),
    ("D177_channel_radio_36.yaml", 430, "36", "1", "1", "WiFi.Radio.{r}.Channel"),
    ("D363_bsscolorpartial.yaml", 363, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.BssColorPartial"),
    ("D364_nonsrgobsspdmaxoffset.yaml", 364, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.NonSRGOBSSPDMaxOffset"),
    ("D367_srgobsspdmaxoffset.yaml", 367, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.SRGOBSSPDMaxOffset"),
    ("D368_srgobsspdminoffset.yaml", 370, "0", "0", "0", "WiFi.Radio.{r}.IEEE80211ax.SRGOBSSPDMinOffset"),
]

_RADIO_IDS = [t[0].split(".")[0] for t in _RADIO_GETTER_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,live_5g,live_6g,live_24g,path_tpl",
    _RADIO_GETTER_CASES,
    ids=_RADIO_IDS,
)
def test_radio_getter_contract(yaml_file, row, live_5g, live_6g, live_24g, path_tpl):
    """Radio getter YAML loads with correct metadata."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["llapi_support"] in ("Support", "Not Supported")
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize(
    "yaml_file,row,live_5g,live_6g,live_24g,path_tpl",
    _RADIO_GETTER_CASES,
    ids=_RADIO_IDS,
)
def test_radio_getter_setup_env(yaml_file, row, live_5g, live_6g, live_24g, path_tpl, monkeypatch):
    """Radio getter is DUT-only; setup_env succeeds without STA."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


@pytest.mark.parametrize(
    "yaml_file,row,live_5g,live_6g,live_24g,path_tpl",
    _RADIO_GETTER_CASES,
    ids=_RADIO_IDS,
)
def test_radio_getter_evaluate(yaml_file, row, live_5g, live_6g, live_24g, path_tpl):
    """Radio getter evaluate passes with live-shaped synthetic output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    api = path_tpl.rsplit(".", 1)[-1]
    needs_quote = not live_5g.lstrip("-").isdigit()
    def _fmt(radio_num, val):
        path = path_tpl.replace("{r}", str(radio_num))
        if needs_quote:
            return f'{path}="{val}"'
        return f"{path}={val}"
    results = {
        "steps": {
            "step_5g_getter": {"success": True, "output": _fmt(1, live_5g), "timing": 0.01},
            "step_6g_getter": {"success": True, "output": _fmt(2, live_6g), "timing": 0.01},
            "step_24g_getter": {"success": True, "output": _fmt(3, live_24g), "timing": 0.01},
        }
    }
    assert plugin.evaluate(case, results) is True


# --- Batch 2: Method-call stats cases (D256-D267) ---

_METHOD_STATS_CASES = [
    # (yaml_file, row, method, field, live_5g, live_6g, live_24g)
    # getRadioAirStats field cases — workbook Fail
    ("D256_getradioairstats_freetime.yaml", 258, "getRadioAirStats", "FreeTime", "0", "10", "3851"),
    ("D257_getradioairstats_load.yaml", 257, "getRadioAirStats", "Load", "84", "62", "96"),
    ("D258_getradioairstats_noise.yaml", 260, "getRadioAirStats", "Noise", "-100", "-97", "-79"),
    ("D259_getradioairstats_rxtime.yaml", 261, "getRadioAirStats", "RxTime", "0", "0", "0"),
    ("D260_getradioairstats_totaltime.yaml", 262, "getRadioAirStats", "TotalTime", "3", "26", "17"),
    ("D261_getradioairstats_txtime.yaml", 261, "getRadioAirStats", "TxTime", "0", "0", "1"),
    ("D267_getradiostats_discardpacketsreceived.yaml", 267, "getRadioStats", "DiscardPacketsReceived", "784", "175", "183"),
    # --- Batch 3: D268-D276 remaining getRadioStats fields ---
    ("D268_getradiostats_discardpacketssent.yaml", 268, "getRadioStats", "DiscardPacketsSent", "0", "0", "0"),
    ("D269_getradiostats_errorsreceive.yaml", 269, "getRadioStats", "ErrorsReceived", "20", "8", "13"),
    ("D270_getradiostats_errorssent.yaml", 270, "getRadioStats", "ErrorsSent", "0", "0", "0"),
    # --- Batch 5c: getRadioStats fields ---
    ("D394_bytesreceived_radio_stats.yaml", 289, "getRadioStats", "BytesReceived", "189265", "0", "0"),
    ("D395_bytessent_radio_stats.yaml", 290, "getRadioStats", "BytesSent", "588249079", "393557814", "393818836"),
    ("D396_errorsreceived_radio_stats.yaml", 396, "getRadioStats", "ErrorsReceived", "20", "8", "13"),
    ("D397_errorssent_radio_stats.yaml", 397, "getRadioStats", "ErrorsSent", "0", "0", "0"),
    ("D454_failedretranscount_radio_stats.yaml", 293, "getRadioStats", "FailedRetransCount", "48", "0", "0"),
    ("D456_noise_radio_stats.yaml", 456, "getRadioStats", "Noise", "-100", "-97", "-79"),
    ("D457_retranscount_radio_stats.yaml", 457, "getRadioStats", "RetransCount", "17234", "0", "0"),
    ("D458_retrycount_radio_stats.yaml", 458, "getRadioStats", "RetryCount", "0", "0", "0"),
    ("D403_temperature.yaml", 298, "getRadioStats", "Temperature", "82", "85", "80"),
    # --- Bulk calibration batch 6: additional getRadioAirStats/getRadioStats fields ---
    ("D447_getradioairstats_inttime.yaml", 449, "getRadioAirStats", "IntTime", "1", "16", "3"),
    ("D448_getradioairstats_longpreambleerrorpercentage.yaml", 450, "getRadioAirStats", "LongPreambleErrorPercentage", "0", "0", "0"),
    ("D449_getradioairstats_noisetime.yaml", 451, "getRadioAirStats", "NoiseTime", "0", "0", "0"),
    ("D450_getradioairstats_obsstime.yaml", 452, "getRadioAirStats", "ObssTime", "0", "0", "0"),
    ("D451_getradioairstats_shortpreambleerrorpercentage.yaml", 453, "getRadioAirStats", "ShortPreambleErrorPercentage", "0", "0", "0"),
    ("D452_getradioairstats_vendorstats_badplcp.yaml", 454, "getRadioAirStats", "VendorStats.Badplcp", "0", "0", "0"),
    ("D453_getradioairstats_vendorstats_glitch.yaml", 455, "getRadioAirStats", "VendorStats.glitch", "0", "0", "0"),
    ("D398_getradiostats_failedretranscount.yaml", 456, "getRadioStats", "FailedRetransCount", "86", "0", "0"),
    ("D399_getradiostats_multipleretrycount.yaml", 457, "getRadioStats", "MultipleRetryCount", "0", "0", "0"),
    ("D400_getradiostats_noise.yaml", 458, "getRadioStats", "Noise", "-100", "-97", "-79"),
    ("D401_getradiostats_retranscount.yaml", 459, "getRadioStats", "RetransCount", "26776", "0", "0"),
    ("D402_getradiostats_retrycount.yaml", 460, "getRadioStats", "RetryCount", "0", "0", "0"),
    ("D459_getradiostats_temperature.yaml", 459, "getRadioStats", "Temperature", "76", "85", "80"),
]

_WAVE3_RADIOSTATS_TRAFFIC_DELTA_CASES = {
    "D263_getradiostats_broadcastpacketsreceived.yaml": {
        "row": 263,
        "api": "BroadcastPacketsReceived",
        "driver_field": "DriverBroadcastPacketsReceived",
        "trigger_target": "STA",
        # broadcast Rx: STA-side arping ensures broadcast frames are generated
        "trigger_assert": "arping",
    },
    "D264_getradiostats_broadcastpacketssent.yaml": {
        "row": 264,
        "api": "BroadcastPacketsSent",
        "driver_field": "DriverBroadcastPacketsSent",
        "trigger_target": "DUT",
        # broadcast Tx: DUT-side arping ensures broadcast frames are sent
        "trigger_assert": "arping",
    },
    "D265_getradiostats_bytesreceived.yaml": {
        "row": 265,
        "api": "BytesReceived",
        "driver_field": "DriverBytesReceived",
        "trigger_target": "STA",
    },
    "D266_getradiostats_bytessent.yaml": {
        "row": 266,
        "api": "BytesSent",
        "driver_field": "DriverBytesSent",
        "trigger_target": "DUT",
    },
    "D271_getradiostats_multicastpacketsreceived.yaml": {
        "row": 271,
        "api": "MulticastPacketsReceived",
        "driver_field": "DriverMulticastPacketsReceived",
        "trigger_target": "STA",
        # multicast Rx: STA sends to all-hosts multicast group 224.0.0.1
        "trigger_assert": "224.0.0.1",
    },
    "D272_getradiostats_multicastpacketssent.yaml": {
        "row": 272,
        "api": "MulticastPacketsSent",
        "driver_field": "DriverMulticastPacketsSent",
        "trigger_target": "DUT",
        # multicast Tx: DUT sends to all-hosts multicast group 224.0.0.1
        "trigger_assert": "224.0.0.1",
    },
    "D273_getradiostats_packetsreceived.yaml": {
        "row": 273,
        "api": "PacketsReceived",
        "driver_field": "DriverPacketsReceived",
        "trigger_target": "STA",
    },
    "D274_getradiostats_packetssent.yaml": {
        "row": 274,
        "api": "PacketsSent",
        "driver_field": "DriverPacketsSent",
        "trigger_target": "DUT",
    },
    "D275_getradiostats_unicastpacketsreceived.yaml": {
        "row": 275,
        "api": "UnicastPacketsReceived",
        "driver_field": "DriverUnicastPacketsReceived",
        "trigger_target": "STA",
    },
    "D276_getradiostats_unicastpacketssent.yaml": {
        "row": 276,
        "api": "UnicastPacketsSent",
        "driver_field": "DriverUnicastPacketsSent",
        "trigger_target": "DUT",
        # D276 driver must use d11_txfrag/$4 extraction (aligned with D336 prior art)
        "drv_assert_contains": "d11_txfrag",
        "drv_assert_excludes": "d11_txmulti",
    },
}

_METHOD_IDS = [t[0].split(".")[0] for t in _METHOD_STATS_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,method,field,live_5g,live_6g,live_24g",
    _METHOD_STATS_CASES,
    ids=_METHOD_IDS,
)
def test_method_stats_contract(yaml_file, row, method, field, live_5g, live_6g, live_24g):
    """Method-call stats YAML loads with correct 3-band structure."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["llapi_support"] in ("Support", "Not Supported")
    assert len(case["steps"]) == 3
    if case["llapi_support"] == "Not Supported":
        assert len(case["pass_criteria"]) >= 1
    else:
        assert len(case["pass_criteria"]) == 3
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize(
    "yaml_file,row,method,field,live_5g,live_6g,live_24g",
    _METHOD_STATS_CASES,
    ids=_METHOD_IDS,
)
def test_method_stats_setup_env(yaml_file, row, method, field, live_5g, live_6g, live_24g, monkeypatch):
    """Method-call stats is DUT-only; setup_env succeeds without STA."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


@pytest.mark.parametrize(
    "yaml_file,row,method,field,live_5g,live_6g,live_24g",
    _METHOD_STATS_CASES,
    ids=_METHOD_IDS,
)
def test_method_stats_evaluate(yaml_file, row, method, field, live_5g, live_6g, live_24g):
    """Method-call stats evaluate passes with live-shaped ubus array output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    # Cases with 'skip' operator (e.g. D452/D453 VendorStats) are not
    # evaluable — the plugin does not implement skip; only test load/discover.
    ops = {c.get("operator") for c in case.get("pass_criteria", [])}
    if "skip" in ops:
        return
    if case.get("llapi_support") == "Not Supported":
        results = {"steps": {}}
        for step in case["steps"]:
            results["steps"][step["id"]] = {
                "success": True, "output": "{}", "timing": 0.01,
            }
        assert plugin.evaluate(case, results) is True
        return
    results = {"steps": {}}
    step_ids = [s["id"] for s in case["steps"]]
    for sid, r, val in zip(step_ids, ["1", "2", "3"], [live_5g, live_6g, live_24g]):
        output = (
            f"WiFi.Radio.{r}.{method}() [\n"
            f"    {{\n"
            f"        {field} = {val},\n"
            f"    }}\n"
            f"]"
        )
        results["steps"][sid] = {
            "success": True, "output": output, "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True


def test_wave3_getradiostats_counter_cases_use_multiband_delta_contracts():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"

    for filename, meta in _WAVE3_RADIOSTATS_TRAFFIC_DELTA_CASES.items():
        raw_case = yaml.safe_load((cases_dir / filename).read_text(encoding="utf-8"))
        case_data = load_case(cases_dir / filename)
        commands = "\n".join(str(step.get("command", "")) for step in case_data["steps"])
        links = {link["band"] for link in case_data["topology"]["links"]}
        phases = [step.get("phase") for step in case_data["steps"]]
        trigger_steps = [step for step in case_data["steps"] if step.get("phase") == "trigger"]

        assert "aliases" not in raw_case
        assert case_data["source"]["row"] == meta["row"]
        assert case_data["llapi_support"] == "Support"
        assert case_data["bands"] == ["5g", "6g", "2.4g"]
        assert {"DUT", "STA"}.issubset(case_data["topology"]["devices"])
        assert links == {"5g", "6g", "2.4g"}
        assert len(case_data["steps"]) >= 15
        assert phases.count("baseline") >= 6
        assert phases.count("trigger") == 3
        assert phases.count("verify") >= 6
        assert len(trigger_steps) == 3
        assert all(step["target"] == meta["trigger_target"] for step in trigger_steps)
        assert f'{meta["driver_field"]}5g=' in commands
        assert f'{meta["driver_field"]}6g=' in commands
        assert f'{meta["driver_field"]}24g=' in commands

        # Per-case trigger and driver formula assertions
        if "trigger_assert" in meta:
            trigger_commands = "\n".join(
                str(s.get("command", "")) for s in trigger_steps
            )
            assert meta["trigger_assert"] in trigger_commands, (
                f"{filename}: trigger_assert '{meta['trigger_assert']}' not found in trigger steps"
            )
        if "drv_assert_contains" in meta:
            assert meta["drv_assert_contains"] in commands, (
                f"{filename}: drv_assert_contains '{meta['drv_assert_contains']}' not found"
            )
        if "drv_assert_excludes" in meta:
            assert meta["drv_assert_excludes"] not in commands, (
                f"{filename}: drv_assert_excludes '{meta['drv_assert_excludes']}' unexpectedly present"
            )

        for capture_suffix in ("5g", "6g", "24g"):
            assert any(
                criterion.get("operator") == "delta_nonzero"
                and criterion.get("delta")
                == {
                    "baseline": f"api_before_{capture_suffix}.{meta['api']}",
                    "verify": f"api_after_{capture_suffix}.{meta['api']}",
                }
                for criterion in case_data["pass_criteria"]
            )
            assert any(
                criterion.get("operator") == "delta_match"
                and criterion.get("delta")
                == {
                    "baseline": f"api_before_{capture_suffix}.{meta['api']}",
                    "verify": f"api_after_{capture_suffix}.{meta['api']}",
                }
                and criterion.get("reference_delta")
                == {
                    "baseline": f"drv_before_{capture_suffix}.{meta['driver_field']}{capture_suffix}",
                    "verify": f"drv_after_{capture_suffix}.{meta['driver_field']}{capture_suffix}",
                }
                for criterion in case_data["pass_criteria"]
            )


# --- D262 getRadioAirStats():void ---

def test_d262_void_contract():
    """D262 getRadioAirStats Void YAML loads with correct 3-band structure."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D262_getradioairstats_void.yaml")
    assert case["source"]["row"] == 262
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3
    for pc in case["pass_criteria"]:
        assert pc["operator"] == "not_contains"


def test_d262_void_evaluate():
    """D262 void evaluate passes when output has no error."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D262_getradioairstats_void.yaml")
    results = {"steps": {}}
    for r, band in [("1", "5g"), ("2", "6g"), ("3", "24g")]:
        output = (
            f"WiFi.Radio.{r}.getRadioAirStats() returned\n"
            f"[\n    {{\n        FreeTime = 0,\n    }}\n]"
        )
        results["steps"][f"step_{band}_stats"] = {
            "success": True, "output": output, "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True


# --- Batch 3: getScanResults field cases (D277-D290) ---

_SCAN_RESULTS_CASES = [
    # (yaml_file, row, field)
    ("D277_getscanresults_bandwidth.yaml", 277, "Bandwidth"),
    ("D278_getscanresults_bssid.yaml", 278, "BSSID"),
    ("D279_getscanresults_channel.yaml", 279, "Channel"),
    ("D280_getscanresults_encryptionmode.yaml", 280, "EncryptionMode"),
    ("D281_getscanresults_noise.yaml", 281, "Noise"),
    ("D282_getscanresults_operatingstandards.yaml", 282, "OperatingStandards"),
    ("D283_getscanresults_rssi.yaml", 283, "RSSI"),
    ("D284_getscanresults_securitymodeenabled.yaml", 284, "SecurityModeEnabled"),
    ("D285_getscanresults_signalnoiseratio.yaml", 285, "SignalNoiseRatio"),
    ("D286_getscanresults_signalstrength.yaml", 286, "SignalStrength"),
    ("D287_getscanresults_ssid.yaml", 287, "SSID"),
    ("D288_getscanresults_wpsconfigmethodssupported.yaml", 288, "WPSConfigMethodsSupported"),
    ("D289_getscanresults_radio.yaml", 289, "Radio"),
    ("D290_getscanresults_centrechannel.yaml", 290, "CentreChannel"),
]

_SCAN_IDS = [t[0].split(".")[0] for t in _SCAN_RESULTS_CASES]


@pytest.mark.parametrize("yaml_file,row,field", _SCAN_RESULTS_CASES, ids=_SCAN_IDS)
def test_scan_results_contract(yaml_file, row, field):
    """getScanResults YAML loads with correct 3-band structure."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["llapi_support"] == "Support"
    if yaml_file == "D277_getscanresults_bandwidth.yaml":
        assert len(case["steps"]) == 3
        assert len(case["pass_criteria"]) == 10
    elif yaml_file == "D283_getscanresults_rssi.yaml":
        assert len(case["steps"]) == 3
        assert len(case["pass_criteria"]) == 9
    elif yaml_file == "D286_getscanresults_signalstrength.yaml":
        assert len(case["steps"]) == 3
        assert len(case["pass_criteria"]) == 9
    elif yaml_file == "D284_getscanresults_securitymodeenabled.yaml":
        assert len(case["steps"]) == 6
        assert len(case["pass_criteria"]) == 12
    elif yaml_file == "D285_getscanresults_signalnoiseratio.yaml":
        assert len(case["steps"]) == 3
        assert len(case["pass_criteria"]) == 12
    elif yaml_file == "D281_getscanresults_noise.yaml":
        assert len(case["steps"]) == 6
        assert len(case["pass_criteria"]) == 15
    elif yaml_file == "D282_getscanresults_operatingstandards.yaml":
        assert len(case["steps"]) == 6
        assert len(case["pass_criteria"]) == 9
    elif yaml_file == "D287_getscanresults_ssid.yaml":
        assert len(case["steps"]) == 6
        assert len(case["pass_criteria"]) == 12
    elif yaml_file == "D290_getscanresults_centrechannel.yaml":
        assert len(case["steps"]) == 3
        assert len(case["pass_criteria"]) == 10
    elif yaml_file == "D278_getscanresults_bssid.yaml":
        assert len(case["steps"]) == 6
        assert len(case["pass_criteria"]) == 6
    elif yaml_file == "D280_getscanresults_encryptionmode.yaml":
        assert len(case["steps"]) == 6
        assert len(case["pass_criteria"]) == 15
    else:
        assert len(case["steps"]) == 3
        assert len(case["pass_criteria"]) == 3
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize("yaml_file,row,field", _SCAN_RESULTS_CASES, ids=_SCAN_IDS)
def test_scan_results_setup_env(yaml_file, row, field, monkeypatch):
    """getScanResults is DUT-only; setup_env succeeds without STA."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


@pytest.mark.parametrize("yaml_file,row,field", _SCAN_RESULTS_CASES, ids=_SCAN_IDS)
def test_scan_results_evaluate(yaml_file, row, field):
    """getScanResults evaluate passes with live-shaped scan array output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    if yaml_file == "D277_getscanresults_bandwidth.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid5g=aa:bb:cc:dd:ee:01\n"
                        "LlapiBandwidth5g=80\n"
                        "WlBandwidth5g=80\n"
                    ),
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid6g=aa:bb:cc:dd:ee:02\n"
                        "LlapiBandwidth6g=320\n"
                        "WlBandwidth6g=160\n"
                    ),
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid24g=aa:bb:cc:dd:ee:03\n"
                        "LlapiBandwidth24g=20\n"
                        "WlBandwidth24g=20\n"
                    ),
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D290_getscanresults_centrechannel.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid5g=aa:bb:cc:dd:ee:01\n"
                        "LlapiCentreChannel5g=42\n"
                        "WlCentreChannel5g=42\n"
                    ),
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid6g=aa:bb:cc:dd:ee:02\n"
                        "LlapiCentreChannel6g=31\n"
                        "WlCentreChannel6g=15\n"
                    ),
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid24g=aa:bb:cc:dd:ee:03\n"
                        "LlapiCentreChannel24g=1\n"
                        "WlCentreChannel24g=1\n"
                    ),
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D278_getscanresults_bssid.yaml":
        results = {
            "steps": {
                "step_5g_scan": {"success": True, "output": "LlapiBssid5g=aa:bb:cc:dd:ee:01\n", "timing": 0.01},
                "step_5g_iw_scan": {"success": True, "output": "IwBssid5g=aa:bb:cc:dd:ee:01\n", "timing": 0.01},
                "step_6g_scan": {"success": True, "output": "LlapiBssid6g=aa:bb:cc:dd:ee:02\n", "timing": 0.01},
                "step_6g_iw_scan": {"success": True, "output": "IwBssid6g=aa:bb:cc:dd:ee:02\n", "timing": 0.01},
                "step_24g_scan": {"success": True, "output": "LlapiBssid24g=aa:bb:cc:dd:ee:03\n", "timing": 0.01},
                "step_24g_iw_scan": {"success": True, "output": "IwBssid24g=aa:bb:cc:dd:ee:03\n", "timing": 0.01},
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D280_getscanresults_encryptionmode.yaml":
        results = {
            "steps": {
                "step_5g_scan": {"success": True, "output": "LlapiBssid5g=aa:bb:cc:dd:ee:01\nLlapiEncryptionMode5g=Default\nLlapiSecurityMode5g=WPA2-Personal\n", "timing": 0.01},
                "step_5g_iw_scan": {"success": True, "output": "IwCipher5g=CCMP\nIwEncryptionMode5g=AES\n", "timing": 0.01},
                "step_6g_scan": {"success": True, "output": "LlapiBssid6g=aa:bb:cc:dd:ee:02\nLlapiEncryptionMode6g=Default\nLlapiSecurityMode6g=WPA3-Personal\n", "timing": 0.01},
                "step_6g_iw_scan": {"success": True, "output": "IwCipher6g=CCMP\nIwEncryptionMode6g=AES\n", "timing": 0.01},
                "step_24g_scan": {"success": True, "output": "LlapiBssid24g=aa:bb:cc:dd:ee:03\nLlapiEncryptionMode24g=Default\nLlapiSecurityMode24g=WPA2-Personal\n", "timing": 0.01},
                "step_24g_iw_scan": {"success": True, "output": "IwCipher24g=CCMP\nIwEncryptionMode24g=AES\n", "timing": 0.01},
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D279_getscanresults_channel.yaml":
        results = {
            "steps": {
                "step_5g_scan": {"success": True, "output": "Channel=36\nIwChannel=36\n", "timing": 0.01},
                "step_6g_scan": {"success": True, "output": "Channel=5\nIwChannel=5\n", "timing": 0.01},
                "step_24g_scan": {"success": True, "output": "Channel=1\nIwChannel=1\n", "timing": 0.01},
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D283_getscanresults_rssi.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": "LlapiBssid5g=aa:bb:cc:dd:ee:01\nLlapiRSSI5g=-64\nLlapiSignalStrength5g=-64\n",
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "LlapiBssid6g=aa:bb:cc:dd:ee:02\nLlapiRSSI6g=-93\nLlapiSignalStrength6g=-93\n",
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "LlapiBssid24g=aa:bb:cc:dd:ee:03\nLlapiRSSI24g=-46\nLlapiSignalStrength24g=-46\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D281_getscanresults_noise.yaml":
        results = {
            "steps": {
                "step_5g_combined": {
                    "success": True,
                    "output": (
                        "CombinedBssid5g=aa:bb:cc:dd:ee:01\n"
                        "CombinedChannel5g=36\n"
                        "CombinedNoise5g=-100\n"
                        "SpectrumNoise5g=-100\n"
                    ),
                    "timing": 0.01,
                },
                "step_5g_scan": {
                    "success": True,
                    "output": "LlapiNoise5g=-100\n",
                    "timing": 0.01,
                },
                "step_6g_combined": {
                    "success": True,
                    "output": (
                        "CombinedBssid6g=aa:bb:cc:dd:ee:02\n"
                        "CombinedChannel6g=5\n"
                        "CombinedNoise6g=-97\n"
                        "SpectrumNoise6g=-97\n"
                    ),
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "LlapiNoise6g=-97\n",
                    "timing": 0.01,
                },
                "step_24g_combined": {
                    "success": True,
                    "output": (
                        "CombinedBssid24g=aa:bb:cc:dd:ee:03\n"
                        "CombinedChannel24g=1\n"
                        "CombinedNoise24g=-81\n"
                        "SpectrumNoise24g=-81\n"
                    ),
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "LlapiNoise24g=-81\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D282_getscanresults_operatingstandards.yaml":
        results = {
            "steps": {
                "step_5g_combined": {
                    "success": True,
                    "output": (
                        "CombinedBssid5g=aa:bb:cc:dd:ee:01\n"
                        "CombinedOperatingStandards5g=a,n,ac,ax,be\n"
                    ),
                    "timing": 0.01,
                },
                "step_5g_scan": {
                    "success": True,
                    "output": "LlapiOperatingStandards5g=a,n,ac,ax,be\n",
                    "timing": 0.01,
                },
                "step_6g_combined": {
                    "success": True,
                    "output": (
                        "CombinedBssid6g=aa:bb:cc:dd:ee:02\n"
                        "CombinedOperatingStandards6g=ax,be\n"
                    ),
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "LlapiOperatingStandards6g=ax,be\n",
                    "timing": 0.01,
                },
                "step_24g_combined": {
                    "success": True,
                    "output": (
                        "CombinedBssid24g=aa:bb:cc:dd:ee:03\n"
                        "CombinedOperatingStandards24g=b,g,n,ax,be\n"
                    ),
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "LlapiOperatingStandards24g=b,g,n,ax,be\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D286_getscanresults_signalstrength.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": "LlapiBssid5g=aa:bb:cc:dd:ee:01\nLlapiRSSI5g=-64\nLlapiSignalStrength5g=-64\n",
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "LlapiBssid6g=aa:bb:cc:dd:ee:02\nLlapiRSSI6g=-93\nLlapiSignalStrength6g=-93\n",
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "LlapiBssid24g=aa:bb:cc:dd:ee:03\nLlapiRSSI24g=-46\nLlapiSignalStrength24g=-46\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D287_getscanresults_ssid.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": "LlapiBssid5g=aa:bb:cc:dd:ee:01\nLlapiSSID5g=Verizon_Z4RY7R\n",
                    "timing": 0.01,
                },
                "step_5g_iw_scan": {
                    "success": True,
                    "output": "IwSSID5g=Verizon_Z4RY7R\n",
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "LlapiBssid6g=aa:bb:cc:dd:ee:02\nLlapiSSID6g=TELUS0227\n",
                    "timing": 0.01,
                },
                "step_6g_iw_scan": {
                    "success": True,
                    "output": "IwSSID6g=TELUS0227\n",
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "LlapiBssid24g=aa:bb:cc:dd:ee:03\nLlapiSSID24g=TMOBILE-85DF-TDK-2G\n",
                    "timing": 0.01,
                },
                "step_24g_iw_scan": {
                    "success": True,
                    "output": "IwSSID24g=TMOBILE-85DF-TDK-2G\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D284_getscanresults_securitymodeenabled.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": "LlapiBssid5g=aa:bb:cc:dd:ee:01\nLlapiSecurityMode5g=WPA2-Personal\n",
                    "timing": 0.01,
                },
                "step_5g_iw_scan": {
                    "success": True,
                    "output": "IwAuth5g=PSK\nIwSecurityMode5g=WPA2-Personal\n",
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "LlapiBssid6g=aa:bb:cc:dd:ee:02\nLlapiSecurityMode6g=WPA3-Personal\n",
                    "timing": 0.01,
                },
                "step_6g_iw_scan": {
                    "success": True,
                    "output": "IwAuth6g=00-0f-ac:8\nIwSecurityMode6g=WPA3-Personal\n",
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "LlapiBssid24g=aa:bb:cc:dd:ee:03\nLlapiSecurityMode24g=WPA2-Personal\n",
                    "timing": 0.01,
                },
                "step_24g_iw_scan": {
                    "success": True,
                    "output": "IwAuth24g=PSK\nIwSecurityMode24g=WPA2-Personal\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D285_getscanresults_signalnoiseratio.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid5g=aa:bb:cc:dd:ee:01\n"
                        "LlapiRSSI5g=-65\n"
                        "LlapiNoise5g=-100\n"
                        "LlapiSignalNoiseRatio5g=35\n"
                        "DerivedSignalNoiseRatio5g=35\n"
                    ),
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid6g=aa:bb:cc:dd:ee:02\n"
                        "LlapiRSSI6g=-93\n"
                        "LlapiNoise6g=-97\n"
                        "LlapiSignalNoiseRatio6g=4\n"
                        "DerivedSignalNoiseRatio6g=4\n"
                    ),
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": (
                        "LlapiBssid24g=aa:bb:cc:dd:ee:03\n"
                        "LlapiRSSI24g=-46\n"
                        "LlapiNoise24g=-80\n"
                        "LlapiSignalNoiseRatio24g=34\n"
                        "DerivedSignalNoiseRatio24g=34\n"
                    ),
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D288_getscanresults_wpsconfigmethodssupported.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": "WPSConfigMethodsSupported=\n",
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "WPSConfigMethodsSupported=\n",
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "WPSConfigMethodsSupported=\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    if yaml_file == "D289_getscanresults_radio.yaml":
        results = {
            "steps": {
                "step_5g_scan": {
                    "success": True,
                    "output": "Radio=\n",
                    "timing": 0.01,
                },
                "step_6g_scan": {
                    "success": True,
                    "output": "Radio=\n",
                    "timing": 0.01,
                },
                "step_24g_scan": {
                    "success": True,
                    "output": "Radio=\n",
                    "timing": 0.01,
                },
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    val = "-42" if field in ("Noise", "RSSI", "SignalStrength") else "TestVal"
    if field == "WPSConfigMethodsSupported":
        val = ""
    results = {"steps": {}}
    for r, band in [("1", "5g"), ("2", "6g"), ("3", "24g")]:
        output = (
            f"WiFi.Radio.{r}.getScanResults() returned\n"
            f"[\n    [\n        {{\n"
            f"            {field} = {val},\n"
            f"        }}\n    ]\n]"
        )
        results["steps"][f"step_{band}_scan"] = {
            "success": True, "output": output, "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True



# --- Batch 4a: D294 getNaStationStats (Skip) ---

def test_d294_getnastationstats_contract():
    """D294 getNaStationStats loads as Skip case."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D294_getnastationstats.yaml")
    assert case["source"]["row"] == 219
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 1
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d294_getnastationstats_evaluate():
    """D294 evaluate passes when 'object not found' is in output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D294_getnastationstats.yaml")
    results = {"steps": {
        "step_probe": {
            "success": True,
            "output": 'ERROR: call (null) failed with status 2 - object not found\ngetNaStationStats() returned\n[\n    "",\n    {\n    }\n]',
            "timing": 0.5,
        }
    }}
    assert plugin.evaluate(case, results) is True


# --- Batch 4b: Action method cases (D295-D299) ---

_ACTION_METHOD_CASES = [
    # (yaml_file, row, method, verdict, pass_criteria_count)
    ("D295_scan.yaml", 295, "scan", "Pass", 3),
    ("D296_startacs.yaml", 296, "startACS", "Pass", 15),
    ("D297_startautochannelselection.yaml", 297, "startAutoChannelSelection", "Pass", 12),
    ("D298_startscan.yaml", 298, "startScan", "Pass", 3),
    ("D299_stopscan.yaml", 299, "stopScan", "Pass", 3),
]

_ACTION_IDS = [t[0].split(".")[0] for t in _ACTION_METHOD_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,method,verdict,pass_criteria_count", _ACTION_METHOD_CASES, ids=_ACTION_IDS
)
def test_action_method_contract(yaml_file, row, method, verdict, pass_criteria_count):
    """Action method YAML loads with correct 3-band structure."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == pass_criteria_count
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize(
    "yaml_file,row,method,verdict,pass_criteria_count", _ACTION_METHOD_CASES, ids=_ACTION_IDS
)
def test_action_method_setup_env(
    yaml_file, row, method, verdict, pass_criteria_count, monkeypatch
):
    """Action method setup_env succeeds with the authored topology."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


@pytest.mark.parametrize(
    "yaml_file,row,method,verdict,pass_criteria_count", _ACTION_METHOD_CASES, ids=_ACTION_IDS
)
def test_action_method_evaluate(yaml_file, row, method, verdict, pass_criteria_count):
    """Action method evaluate passes when authored outputs satisfy criteria."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    results = {"steps": {}}
    for r, band in [("1", "5g"), ("2", "6g"), ("3", "24g")]:
        if yaml_file == "D295_scan.yaml":
            suffix = "24g" if band == "24g" else band
            results["steps"][f"step_{band}"] = {
                "success": True,
                "output": (
                    f"ScanCheck{suffix}=ok\n"
                    f"ScanBSSID{suffix}=aa:bb:cc:dd:ee:{r}{r}\n"
                    f"DriverMatch{suffix}=aa:bb:cc:dd:ee:{r}{r}\n"
                ),
                "timing": 0.5,
            }
            continue
        if yaml_file == "D296_startacs.yaml":
            iface = {"5g": "wl0", "6g": "wl1", "24g": "wl2"}[band]
            results["steps"][f"step_{band}"] = {
                "success": True,
                "output": (
                    f"WiFi.Radio.{r}.AutoChannelEnable=1\n"
                    f"WiFi.Radio.{r}.startAutoChannelSelection() returned\n"
                    f"WiFi.Radio.{r}.startACS() returned\n"
                    f"Interface {iface}\n"
                ),
                "timing": 0.5,
            }
            continue
        if yaml_file == "D297_startautochannelselection.yaml":
            iface = {"5g": "wl0", "6g": "wl1", "24g": "wl2"}[band]
            results["steps"][f"step_{band}"] = {
                "success": True,
                "output": (
                    f"WiFi.Radio.{r}.AutoChannelEnable=1\n"
                    f"WiFi.Radio.{r}.startAutoChannelSelection() returned\n"
                    f"Interface {iface}\n"
                ),
                "timing": 0.5,
            }
            continue
        results["steps"][f"step_{band}"] = {
            "success": True,
            "output": f"WiFi.Radio.{r}.{method}() returned\n",
            "timing": 0.5,
        }
    assert plugin.evaluate(case, results) is True


# --- Batch 4c: getSSIDStats field cases (D300-D316) ---

_SSID_STATS_CASES = [
    # (yaml_file, row, field, verdict)
    ("D300_getssidstats_broadcastpacketsreceived.yaml", 300, "BroadcastPacketsReceived", "Pass"),
    ("D301_getssidstats_broadcastpacketssent.yaml", 301, "BroadcastPacketsSent", "Pass"),
    ("D302_getssidstats_bytesreceived.yaml", 227, "BytesReceived", "Fail"),
    ("D303_getssidstats_bytessent.yaml", 228, "BytesSent", "Pass"),
    ("D304_getssidstats_discardpacketsreceived.yaml", 304, "DiscardPacketsReceived", "Pass"),
    ("D305_getssidstats_discardpacketssent.yaml", 305, "DiscardPacketsSent", "Pass"),
    ("D306_getssidstats_errorsreceived.yaml", 306, "ErrorsReceived", "Pass"),
    ("D307_getssidstats_errorssent.yaml", 307, "ErrorsSent", "Pass"),
    ("D308_getssidstats_failedretranscount.yaml", 308, "FailedRetransCount", "Not Supported"),
    ("D309_getssidstats_multicastpacketsreceived.yaml", 309, "MulticastPacketsReceived", "Pass"),
    ("D310_getssidstats_multicastpacketssent.yaml", 310, "MulticastPacketsSent", "Pass"),
    ("D311_getssidstats_packetsreceived.yaml", 311, "PacketsReceived", "Pass"),
    ("D312_getssidstats_packetssent.yaml", 312, "PacketsSent", "Pass"),
    ("D314_getssidstats_unicastpacketsreceived.yaml", 314, "UnicastPacketsReceived", "Pass"),
    ("D315_getssidstats_unicastpacketssent.yaml", 315, "UnicastPacketsSent", "Pass"),
    ("D316_getssidstats_unknownprotopacketsreceived.yaml", 316, "UnknownProtoPacketsReceived", "Not Supported"),
]

_SSID_STATS_IDS = [t[0].split(".")[0] for t in _SSID_STATS_CASES]


@pytest.mark.parametrize("yaml_file,row,field,verdict", _SSID_STATS_CASES, ids=_SSID_STATS_IDS)
def test_ssid_stats_contract(yaml_file, row, field, verdict):
    """getSSIDStats YAML loads with correct 3-band structure."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize("yaml_file,row,field,verdict", _SSID_STATS_CASES, ids=_SSID_STATS_IDS)
def test_ssid_stats_setup_env(yaml_file, row, field, verdict, monkeypatch):
    """getSSIDStats is DUT-only; setup_env succeeds without STA."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


@pytest.mark.parametrize("yaml_file,row,field,verdict", _SSID_STATS_CASES, ids=_SSID_STATS_IDS)
def test_ssid_stats_evaluate(yaml_file, row, field, verdict):
    """getSSIDStats evaluate passes with live-shaped stats output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    results = {"steps": {}}
    for ssid, band in [("4", "5g"), ("6", "6g"), ("8", "24g")]:
        value = 0 if verdict == "Not Supported" else 42
        output = (
            f"WiFi.SSID.{ssid}.getSSIDStats() returned\n"
            f"[\n    {{\n"
            f"        {field} = {value},\n"
            f"    }}\n]"
        )
        results["steps"][f"step_{band}_stats"] = {
            "success": True, "output": output, "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True


def test_d313_getssidstats_retranscount_uses_delta_contract():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    discoverable_ids = {case["id"] for case in plugin.discover_cases()}
    assert "d313-getssidstats-retranscount" in discoverable_ids

    raw_case = yaml.safe_load((cases_dir / "D313_getssidstats_retranscount.yaml").read_text(encoding="utf-8"))
    case_data = load_case(cases_dir / "D313_getssidstats_retranscount.yaml")

    assert "aliases" not in raw_case
    assert case_data["id"] == "d313-getssidstats-retranscount"
    assert case_data["source"]["row"] == 313
    assert case_data["source"]["api"] == "getSSIDStats()"
    assert case_data["bands"] == ["5g", "6g", "2.4g"]
    assert "shared multi-band trigger phase" in case_data["test_procedure"]
    assert [step["phase"] for step in case_data["steps"]] == [
        "baseline",
        "baseline",
        "baseline",
        "trigger",
        "trigger",
        "trigger",
        "verify",
        "verify",
        "verify",
    ]
    assert [step["action"] for step in case_data["steps"]] == [
        "read",
        "read",
        "read",
        "wait",
        "wait",
        "wait",
        "read",
        "read",
        "read",
    ]
    assert [step["capture"] for step in case_data["steps"] if step.get("capture")] == [
        "stats_5g_before",
        "stats_6g_before",
        "stats_24g_before",
        "trigger_segment_5g",
        "trigger_segment_6g",
        "trigger_segment_24g",
        "stats_5g_after",
        "stats_6g_after",
        "stats_24g_after",
    ]
    assert all(step.get("duration") == 30 for step in case_data["steps"][3:6])
    assert all("shared multi-band trigger phase" in step["description"].lower() for step in case_data["steps"][3:6])
    assert all("ubus-cli" not in step.get("command", "") for step in case_data["steps"][3:6])
    assert len(case_data["pass_criteria"]) == 3
    assert case_data["pass_criteria"] == [
        {
            "delta": {
                "baseline": "stats_5g_before.RetransCount",
                "verify": "stats_5g_after.RetransCount",
            },
            "operator": "delta_nonzero",
            "description": "5G RetransCount must increase across the shared multi-band trigger phase.",
        },
        {
            "delta": {
                "baseline": "stats_6g_before.RetransCount",
                "verify": "stats_6g_after.RetransCount",
            },
            "operator": "delta_nonzero",
            "description": "6G RetransCount must increase across the shared multi-band trigger phase.",
        },
        {
            "delta": {
                "baseline": "stats_24g_before.RetransCount",
                "verify": "stats_24g_after.RetransCount",
            },
            "operator": "delta_nonzero",
            "description": "2.4G RetransCount must increase across the shared multi-band trigger phase.",
        },
    ]
    assert not any(
        criterion.get("field", "").endswith(".RetransCount")
        and criterion.get("operator") == "equals"
        and str(criterion.get("value")) == "0"
        for criterion in case_data["pass_criteria"]
    )


def test_d313_getssidstats_retranscount_setup_env(monkeypatch):
    """D313 remains DUT-only even after delta migration."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D313_getssidstats_retranscount.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d313_getssidstats_retranscount_evaluate_delta_examples():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case_data = load_case(cases_dir / "D313_getssidstats_retranscount.yaml")

    def stats_output(ssid: str, value: int) -> str:
        return (
            f"WiFi.SSID.{ssid}.getSSIDStats() returned\n"
            "[\n    {\n"
            f"        RetransCount = {value},\n"
            "    }\n]"
        )

    pass_results = {
        "steps": {
            "step_5g_baseline_stats": {
                "success": True,
                "output": stats_output("4", 10),
                "timing": 0.01,
            },
            "step_6g_baseline_stats": {
                "success": True,
                "output": stats_output("6", 20),
                "timing": 0.01,
            },
            "step_24g_baseline_stats": {
                "success": True,
                "output": stats_output("8", 30),
                "timing": 0.01,
            },
            "step_5g_trigger_segment": {
                "success": True,
                "output": "waited 30.000s",
                "timing": 30.0,
            },
            "step_6g_trigger_segment": {
                "success": True,
                "output": "waited 30.000s",
                "timing": 30.0,
            },
            "step_24g_trigger_segment": {
                "success": True,
                "output": "waited 30.000s",
                "timing": 30.0,
            },
            "step_5g_verify_stats": {
                "success": True,
                "output": stats_output("4", 11),
                "timing": 0.01,
            },
            "step_6g_verify_stats": {
                "success": True,
                "output": stats_output("6", 25),
                "timing": 0.01,
            },
            "step_24g_verify_stats": {
                "success": True,
                "output": stats_output("8", 31),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, pass_results) is True

    zero_delta_results = {
        "steps": {
            **pass_results["steps"],
            "step_6g_verify_stats": {
                "success": True,
                "output": stats_output("6", 20),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case_data, zero_delta_results) is False

# --- Batch 4d: D317 BSSID SSID property ---

def test_d317_bssid_ssid_contract():
    """D317 BSSID SSID loads as 3-band property getter."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D317_bssid_ssid.yaml")
    assert case["source"]["row"] == 317
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3
    assert case["bands"] == ["5g", "6g", "2.4g"]


def test_d317_bssid_ssid_evaluate():
    """D317 evaluate passes with valid MAC BSSID output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D317_bssid_ssid.yaml")
    results = {"steps": {}}
    macs = {"5g": "2c:59:17:00:19:95", "6g": "2c:59:17:00:19:96", "24g": "2c:59:17:00:19:a7"}
    ssids = {"5g": "4", "6g": "6", "24g": "8"}
    for band, mac in macs.items():
        s = ssids[band]
        results["steps"][f"step_{band}"] = {
            "success": True,
            "output": f'WiFi.SSID.{s}.BSSID="{mac}"',
            "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True


# --- Batch 5d: WMM Stats parametrized table ---

_WMM_STATS_CASES = [
    # (yaml_file, row, wmm_sub_object, field, live_5g, live_6g, live_24g)
    ("D481_ac_vo_stats_wmmbytesreceived_radio.yaml", 348, "AC_VO_Stats", "WmmBytesReceived", "26511", "0", "0"),
    ("D482_ac_be_stats_wmmbytessent_radio.yaml", 349, "AC_BE_Stats", "WmmBytesSent", "588206344", "393557814", "393818836"),
    ("D485_ac_vo_stats_wmmbytessent_radio.yaml", 352, "AC_VO_Stats", "WmmBytesSent", "42735", "0", "0"),
    ("D490_ac_be_stats_wmmfailedbytessent_radio.yaml", 357, "AC_BE_Stats", "WmmFailedbytesSent", "158", "0", "0"),
]

_WMM_IDS = [t[0].split(".")[0] for t in _WMM_STATS_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,wmm_sub,field,live_5g,live_6g,live_24g",
    _WMM_STATS_CASES,
    ids=_WMM_IDS,
)
def test_wmm_stats_load(yaml_file, row, wmm_sub, field, live_5g, live_6g, live_24g):
    """Each WMM stats YAML must load, have correct row and 3-band shape."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["bands"] == ["5g", "6g", "2.4g"]
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3


@pytest.mark.parametrize(
    "yaml_file,row,wmm_sub,field,live_5g,live_6g,live_24g",
    _WMM_STATS_CASES,
    ids=_WMM_IDS,
)
def test_wmm_stats_discover(yaml_file, row, wmm_sub, field, live_5g, live_6g, live_24g):
    """Every WMM stats YAML must be discoverable."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    discoverable_ids = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable_ids


@pytest.mark.parametrize(
    "yaml_file,row,wmm_sub,field,live_5g,live_6g,live_24g",
    _WMM_STATS_CASES,
    ids=_WMM_IDS,
)
def test_wmm_stats_evaluate(yaml_file, row, wmm_sub, field, live_5g, live_6g, live_24g):
    """WMM stats evaluate passes with live-shaped getRadioStats grep output."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    results = {"steps": {}}
    radio_ids = {"5g": "1", "6g": "2", "24g": "3"}
    live_vals = {"5g": live_5g, "6g": live_6g, "24g": live_24g}
    for band, rid in radio_ids.items():
        # grep filters to single AC category line
        output = (
            f'        WiFi.Radio.{rid}.Stats.{wmm_sub}.{field} = {live_vals[band]},'
        )
        results["steps"][f"step_{band}_stats"] = {
            "success": True, "output": output, "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True


def test_d478_radio_stats_wmmbytesreceived_ac_be_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D478_ac_be_stats_wmmbytesreceived_radio.yaml")
    assert case["id"] == "d478-radio-stats-wmmbytesreceived-ac_be"
    assert case["source"]["row"] == 478
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmBytesReceived."
    assert case["source"]["api"] == "AC_BE"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmBytesReceived.AC_BE?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BE"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmBytesReceived5g"


def test_d478_radio_stats_wmmbytesreceived_ac_be_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D478_ac_be_stats_wmmbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d478_radio_stats_wmmbytesreceived_ac_be_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D478_ac_be_stats_wmmbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmBytesReceived.AC_BE=26181728",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived5g=26181728",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmBytesReceived.AC_BE=37665998",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived6g=37665998",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmBytesReceived.AC_BE=26231742",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived24g=26231742",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d479_radio_stats_wmmbytesreceived_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D479_ac_bk_stats_wmmbytesreceived_radio.yaml")
    assert case["id"] == "d479-radio-stats-wmmbytesreceived-ac_bk"
    assert case["source"]["row"] == 479
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmBytesReceived."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmBytesReceived.AC_BK?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmBytesReceived5g"


def test_d479_radio_stats_wmmbytesreceived_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D479_ac_bk_stats_wmmbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d479_radio_stats_wmmbytesreceived_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D479_ac_bk_stats_wmmbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d480_radio_stats_wmmbytesreceived_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D480_ac_vi_stats_wmmbytesreceived_radio.yaml")
    assert case["id"] == "d480-radio-stats-wmmbytesreceived-ac_vi"
    assert case["source"]["row"] == 480
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmBytesReceived."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmBytesReceived.AC_VI?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmBytesReceived5g"


def test_d480_radio_stats_wmmbytesreceived_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D480_ac_vi_stats_wmmbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d480_radio_stats_wmmbytesreceived_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D480_ac_vi_stats_wmmbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmBytesReceived.AC_VI=26495350",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived5g=26495350",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmBytesReceived.AC_VI=26555510",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived6g=26555510",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmBytesReceived.AC_VI=20441610",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived24g=20441610",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d483_radio_stats_wmmbytessent_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D483_ac_bk_stats_wmmbytessent_radio.yaml")
    assert case["id"] == "d483-radio-stats-wmmbytessent-ac_bk"
    assert case["source"]["row"] == 483
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmBytesSent."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmBytesSent.AC_BK?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmBytesSent5g"


def test_d483_radio_stats_wmmbytessent_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D483_ac_bk_stats_wmmbytessent_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d483_radio_stats_wmmbytessent_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D483_ac_bk_stats_wmmbytessent_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmBytesSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmBytesSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmBytesSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d484_radio_stats_wmmbytessent_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D484_ac_vi_stats_wmmbytessent_radio.yaml")
    assert case["id"] == "d484-radio-stats-wmmbytessent-ac_vi"
    assert case["source"]["row"] == 484
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmBytesSent."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmBytesSent.AC_VI?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmBytesSent5g"


def test_d484_radio_stats_wmmbytessent_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D484_ac_vi_stats_wmmbytessent_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d484_radio_stats_wmmbytessent_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D484_ac_vi_stats_wmmbytessent_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmBytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmBytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmBytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d486_radio_stats_wmmfailedbytesreceived_ac_be_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D486_ac_be_stats_wmmfailedbytesreceived_radio.yaml")
    assert case["id"] == "d486-radio-stats-wmmfailedbytesreceived-ac_be"
    assert case["source"]["row"] == 486
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_BE"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_BE?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BE"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d486_radio_stats_wmmfailedbytesreceived_ac_be_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D486_ac_be_stats_wmmfailedbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d486_radio_stats_wmmfailedbytesreceived_ac_be_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D486_ac_be_stats_wmmfailedbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_BE=188",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=188",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedBytesReceived.AC_BE=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedBytesReceived.AC_BE=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d487_radio_stats_wmmfailedbytesreceived_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D487_ac_bk_stats_wmmfailedbytesreceived_radio.yaml")
    assert case["id"] == "d487-radio-stats-wmmfailedbytesreceived-ac_bk"
    assert case["source"]["row"] == 487
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_BK?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d487_radio_stats_wmmfailedbytesreceived_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D487_ac_bk_stats_wmmfailedbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d487_radio_stats_wmmfailedbytesreceived_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D487_ac_bk_stats_wmmfailedbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d488_radio_stats_wmmfailedbytesreceived_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D488_ac_vi_stats_wmmfailedbytesreceived_radio.yaml")
    assert case["id"] == "d488-radio-stats-wmmfailedbytesreceived-ac_vi"
    assert case["source"]["row"] == 488
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_VI?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d488_radio_stats_wmmfailedbytesreceived_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D488_ac_vi_stats_wmmfailedbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d488_radio_stats_wmmfailedbytesreceived_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D488_ac_vi_stats_wmmfailedbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedBytesReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedBytesReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d489_radio_stats_wmmfailedbytesreceived_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D489_ac_vo_stats_wmmfailedbytesreceived_radio.yaml")
    assert case["id"] == "d489-radio-stats-wmmfailedbytesreceived-ac_vo"
    assert case["source"]["row"] == 489
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_VO?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d489_radio_stats_wmmfailedbytesreceived_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D489_ac_vo_stats_wmmfailedbytesreceived_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d489_radio_stats_wmmfailedbytesreceived_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D489_ac_vo_stats_wmmfailedbytesreceived_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedBytesReceived.AC_VO=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedBytesReceived.AC_VO=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedBytesReceived.AC_VO=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d491_radio_stats_wmmfailedbytessent_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D491_ac_bk_stats_wmmfailedbytessent_radio.yaml")
    assert case["id"] == "d491-radio-stats-wmmfailedbytessent-ac_bk"
    assert case["source"]["row"] == 491
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedbytesSent."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedbytesSent.AC_BK?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedbytesSent5g"


def test_d491_radio_stats_wmmfailedbytessent_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D491_ac_bk_stats_wmmfailedbytessent_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d491_radio_stats_wmmfailedbytessent_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D491_ac_bk_stats_wmmfailedbytessent_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedbytesSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedbytesSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedbytesSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d492_radio_stats_wmmfailedbytessent_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D492_ac_vi_stats_wmmfailedbytessent_radio.yaml")
    assert case["id"] == "d492-radio-stats-wmmfailedbytessent-ac_vi"
    assert case["source"]["row"] == 492
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedbytesSent."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedbytesSent.AC_VI?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedbytesSent5g"


def test_d492_radio_stats_wmmfailedbytessent_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D492_ac_vi_stats_wmmfailedbytessent_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d492_radio_stats_wmmfailedbytessent_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D492_ac_vi_stats_wmmfailedbytessent_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedbytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedbytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedbytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d493_radio_stats_wmmfailedbytessent_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D493_ac_vo_stats_wmmfailedbytessent_radio.yaml")
    assert case["id"] == "d493-radio-stats-wmmfailedbytessent-ac_vo"
    assert case["source"]["row"] == 493
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats.WmmFailedbytesSent."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.WmmFailedbytesSent.AC_VO?' in case["steps"][0]["command"]
    assert 'wme_counters' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverWmmFailedbytesSent5g"


def test_d493_radio_stats_wmmfailedbytessent_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D493_ac_vo_stats_wmmfailedbytessent_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d493_radio_stats_wmmfailedbytessent_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D493_ac_vo_stats_wmmfailedbytessent_radio.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.WmmFailedbytesSent.AC_VO=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.WmmFailedbytesSent.AC_VO=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.WmmFailedbytesSent.AC_VO=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


# --- Batch 5e: WiFi7 Capabilities parametrized table ---

_WIFI7_CAPS_CASES = [
    # (yaml_file, row, role, property)
    ("D593_emlmrsupport_capabilities_wifi7aprole.yaml", 409, "WiFi7APRole", "EMLMRSupport"),
    ("D594_emlsrsupport_capabilities_wifi7aprole.yaml", 410, "WiFi7APRole", "EMLSRSupport"),
    ("D595_strsupport_capabilities_wifi7aprole.yaml", 411, "WiFi7APRole", "STRSupport"),
    ("D596_nstrsupport_capabilities_wifi7aprole.yaml", 412, "WiFi7APRole", "NSTRSupport"),
    ("D597_emlmrsupport_capabilities_wifi7starole.yaml", 413, "WiFi7STARole", "EMLMRSupport"),
    ("D598_emlsrsupport_capabilities_wifi7starole.yaml", 414, "WiFi7STARole", "EMLSRSupport"),
    ("D599_strsupport_capabilities_wifi7starole.yaml", 415, "WiFi7STARole", "STRSupport"),
    ("D600_nstrsupport_capabilities_wifi7starole.yaml", 600, "WiFi7STARole", "NSTRSupport"),
]

_WIFI7_IDS = [t[0].split(".")[0] for t in _WIFI7_CAPS_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,role,prop",
    _WIFI7_CAPS_CASES,
    ids=_WIFI7_IDS,
)
def test_wifi7_caps_load(yaml_file, row, role, prop):
    """Each WiFi7 capability YAML must load, have correct row and 3-band shape."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["bands"] == ["5g", "6g", "2.4g"]
    assert len(case["steps"]) == 3
    assert len(case["pass_criteria"]) == 3


@pytest.mark.parametrize(
    "yaml_file,row,role,prop",
    _WIFI7_CAPS_CASES,
    ids=_WIFI7_IDS,
)
def test_wifi7_caps_discover(yaml_file, row, role, prop):
    """Every WiFi7 capability YAML must be discoverable."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    discoverable_ids = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable_ids


@pytest.mark.parametrize(
    "yaml_file,row,role,prop",
    _WIFI7_CAPS_CASES,
    ids=_WIFI7_IDS,
)
def test_wifi7_caps_evaluate(yaml_file, row, role, prop):
    """WiFi7 capability evaluate passes with live value 1."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    results = {"steps": {}}
    radio_ids = {"5g": "1", "6g": "2", "24g": "3"}
    for band, rid in radio_ids.items():
        output = (
            f'WiFi.Radio.{rid}.Capabilities.{role}.{prop}="1"'
        )
        results["steps"][f"step_{band}_getter"] = {
            "success": True, "output": output, "timing": 0.01,
        }
    assert plugin.evaluate(case, results) is True


# --- Batch 5f: D360 MBOAssocDisallowReason Skip contract ---

def test_d360_mboassocdisallowreason_contract():
    """D360 MBOAssocDisallowReason loads as 3-band AP skip case."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D360_mboassocdisallowreason.yaml")
    assert case["source"]["row"] == 269
    assert case["bands"] == ["5g", "6g", "2.4g"]


# --- D183 TPCMode ---

def test_d183_tpcmode_contract():
    """D183 TPCMode YAML loads as fail-shaped 5G-only case."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D183_tpcmode.yaml")
    assert case["source"]["row"] == 183
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 12
    assert len(case["pass_criteria"]) == 8
    assert case["bands"] == ["5g"]


def test_d183_tpcmode_setup_env(monkeypatch):
    """D183 is DUT-only; setup_env succeeds."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D183_tpcmode.yaml")
    topo = _FakeTopology()
    recorder = _FactoryRecorder()
    _install_fake_factory(monkeypatch, recorder)
    assert plugin.setup_env(case, topology=topo) is True
    plugin.teardown(case, topo)


def test_d183_tpcmode_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D183_tpcmode.yaml")
    # Each step's output must match the pass_criteria field paths (capture-based).
    _step_outputs = {
        "step1": "TPCMode=Auto",                                # before_result
        "step2": "OffAttemptLine1=error\nOffAttemptLine2=invalid value",  # off_attempt
        "step3": "TPCMode=Auto",                                # after_off
        "step4": "ok",                                          # set_ap
        "step5": "TPCMode=Ap",                                  # after_ap
        "step6": "DriverTPCMode=0",                             # driver_after_ap
        "step7": "ok",                                          # set_sta
        "step8": "TPCMode=Sta",                                 # after_sta
        "step9": "ok",                                          # set_apsta
        "step10": "TPCMode=ApSta",                              # after_apsta
        "step11": "ok",                                         # restore_auto
        "step12": "TPCMode=Auto",                               # after_restore
    }
    results = {
        "steps": {
            sid: {"success": True, "output": out, "timing": 0.01}
            for sid, out in _step_outputs.items()
        }
    }
    assert plugin.evaluate(case, results) is True


# ---------------------------------------------------------------------------
# Batch 6 — SSID WMM Stats (D496-D527): 3-band SSID-level WMM counters
# ---------------------------------------------------------------------------
_SSID_WMM_STATS_CASES = [
    ("D497_ac_bk_stats_wmmbytesreceived_ssid.yaml", 497, "AC_BK", "WmmBytesReceived"),
    ("D498_ac_vi_stats_wmmbytesreceived_ssid.yaml", 498, "AC_VI", "WmmBytesReceived"),
    ("D500_ac_be_stats_wmmbytessent_ssid.yaml", 500, "AC_BE", "WmmBytesSent"),
    ("D501_ac_bk_stats_wmmbytessent_ssid.yaml", 501, "AC_BK", "WmmBytesSent"),
    ("D503_ac_vo_stats_wmmbytessent_ssid.yaml", 503, "AC_VO", "WmmBytesSent"),
    ("D504_ac_be_stats_wmmfailedbytesreceived_ssid.yaml", 504, "AC_BE", "WmmFailedBytesReceived"),
    ("D508_ac_be_stats_wmmfailedbytessent_ssid.yaml", 508, "AC_BE", "WmmFailedbytesSent"),
    ("D509_ac_bk_stats_wmmfailedbytessent_ssid.yaml", 509, "AC_BK", "WmmFailedbytesSent"),
    ("D511_ac_vo_stats_wmmfailedbytessent_ssid.yaml", 511, "AC_VO", "WmmFailedbytesSent"),
    ("D514_ac_vi_stats_wmmfailedreceived.yaml", 514, "AC_VI", "WmmFailedReceived"),
    ("D515_ac_vo_stats_wmmfailedreceived.yaml", 515, "AC_VO", "WmmFailedReceived"),
    ("D516_ac_be_stats_wmmfailedsent.yaml", 516, "AC_BE", "WmmFailedSent"),
    ("D524_ac_be_stats_wmmpacketssent.yaml", 524, "AC_BE", "WmmPacketsSent"),
]
_SSID_WMM_IDS = [t[0].split(".")[0] for t in _SSID_WMM_STATS_CASES]


def test_d496_ssid_stats_wmmbytesreceived_ac_be_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D496_ac_be_stats_wmmbytesreceived_ssid.yaml")
    assert case["id"] == "d496-ssid-wmm-ac_be_stats_wmmbytesreceived_ssid"
    assert case["source"]["row"] == 496
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmBytesReceived."
    assert case["source"]["api"] == "AC_BE"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmBytesReceived.AC_BE?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BE"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmBytesReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmBytesReceived5g"


def test_d496_ssid_stats_wmmbytesreceived_ac_be_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D496_ac_be_stats_wmmbytesreceived_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d496_ssid_stats_wmmbytesreceived_ac_be_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D496_ac_be_stats_wmmbytesreceived_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesReceived5g=97351163",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmBytesReceived.AC_BE=97351163",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived5g=97351163",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesReceived6g=14117865",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmBytesReceived.AC_BE=14117865",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived6g=14117865",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesReceived24g=13359133",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmBytesReceived.AC_BE=13359133",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived24g=13359133",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d499_ssid_stats_wmmbytesreceived_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D499_ac_vo_stats_wmmbytesreceived_ssid.yaml")
    assert case["id"] == "d499-ssid-wmm-ac_vo_stats_wmmbytesreceived_ssid"
    assert case["source"]["row"] == 499
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmBytesReceived."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmBytesReceived.AC_VO?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmBytesReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmBytesReceived5g"


def test_d499_ssid_stats_wmmbytesreceived_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D499_ac_vo_stats_wmmbytesreceived_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d499_ssid_stats_wmmbytesreceived_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D499_ac_vo_stats_wmmbytesreceived_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesReceived5g=60420",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmBytesReceived.AC_VO=60420",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived5g=60420",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesReceived6g=43680",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmBytesReceived.AC_VO=43680",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived6g=43680",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesReceived24g=42351",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmBytesReceived.AC_VO=42351",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesReceived24g=42351",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d502_ssid_stats_wmmbytessent_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D502_ac_vi_stats_wmmbytessent_ssid.yaml")
    assert case["id"] == "d502-ssid-wmm-ac_vi_stats_wmmbytessent_ssid"
    assert case["source"]["row"] == 502
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmBytesSent."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmBytesSent.AC_VI?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmBytesSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmBytesSent5g"


def test_d502_ssid_stats_wmmbytessent_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D502_ac_vi_stats_wmmbytessent_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d502_ssid_stats_wmmbytessent_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D502_ac_vi_stats_wmmbytessent_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmBytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmBytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmBytesSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmBytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmBytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d505_ssid_stats_wmmfailedbytesreceived_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D505_ac_bk_stats_wmmfailedbytesreceived_ssid.yaml")
    assert case["id"] == "d505-ssid-wmm-ac_bk_stats_wmmfailedbytesreceived_ssid"
    assert case["source"]["row"] == 505
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedBytesReceived.AC_BK?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedBytesReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d505_ssid_stats_wmmfailedbytesreceived_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D505_ac_bk_stats_wmmfailedbytesreceived_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d505_ssid_stats_wmmfailedbytesreceived_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D505_ac_bk_stats_wmmfailedbytesreceived_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedBytesReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d506_ssid_stats_wmmfailedbytesreceived_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D506_ac_vi_stats_wmmfailedbytesreceived_ssid.yaml")
    assert case["id"] == "d506-ssid-wmm-ac_vi_stats_wmmfailedbytesreceived_ssid"
    assert case["source"]["row"] == 506
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedBytesReceived.AC_VI?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedBytesReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d506_ssid_stats_wmmfailedbytesreceived_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D506_ac_vi_stats_wmmfailedbytesreceived_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d506_ssid_stats_wmmfailedbytesreceived_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D506_ac_vi_stats_wmmfailedbytesreceived_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedBytesReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedBytesReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedBytesReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d507_ssid_stats_wmmfailedbytesreceived_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D507_ac_vo_stats_wmmfailedbytesreceived_ssid.yaml")
    assert case["id"] == "d507-ssid-wmm-ac_vo_stats_wmmfailedbytesreceived_ssid"
    assert case["source"]["row"] == 507
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedBytesReceived."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedBytesReceived.AC_VO?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedBytesReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedBytesReceived5g"


def test_d507_ssid_stats_wmmfailedbytesreceived_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D507_ac_vo_stats_wmmfailedbytesreceived_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d507_ssid_stats_wmmfailedbytesreceived_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D507_ac_vo_stats_wmmfailedbytesreceived_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedBytesReceived.AC_VO=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedBytesReceived.AC_VO=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedBytesReceived.AC_VO=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedBytesReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d510_ssid_stats_wmmfailedbytessent_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D510_ac_vi_stats_wmmfailedbytessent_ssid.yaml")
    assert case["id"] == "d510-ssid-wmm-ac_vi_stats_wmmfailedbytessent_ssid"
    assert case["source"]["row"] == 510
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedbytesSent."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedbytesSent.AC_VI?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedbytesSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedbytesSent5g"


def test_d510_ssid_stats_wmmfailedbytessent_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D510_ac_vi_stats_wmmfailedbytessent_ssid.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d510_ssid_stats_wmmfailedbytessent_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D510_ac_vi_stats_wmmfailedbytessent_ssid.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedbytesSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedbytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedbytesSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedbytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedbytesSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedbytesSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedbytesSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d512_ssid_stats_wmmfailedreceived_ac_be_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D512_ac_be_stats_wmmfailedreceived.yaml")
    assert case["id"] == "d512-ssid-wmm-ac_be_stats_wmmfailedreceived"
    assert case["source"]["row"] == 512
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedReceived."
    assert case["source"]["api"] == "AC_BE"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedReceived.AC_BE?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BE"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedReceived5g"


def test_d512_ssid_stats_wmmfailedreceived_ac_be_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D512_ac_be_stats_wmmfailedreceived.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d512_ssid_stats_wmmfailedreceived_ac_be_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D512_ac_be_stats_wmmfailedreceived.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedReceived5g=2",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedReceived.AC_BE=2",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedReceived5g=2",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedReceived.AC_BE=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedReceived.AC_BE=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d513_ssid_stats_wmmfailedreceived_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D513_ac_bk_stats_wmmfailedreceived.yaml")
    assert case["id"] == "d513-ssid-wmm-ac_bk_stats_wmmfailedreceived"
    assert case["source"]["row"] == 513
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedReceived."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedReceived.AC_BK?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedReceived5g"


def test_d513_ssid_stats_wmmfailedreceived_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D513_ac_bk_stats_wmmfailedreceived.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d513_ssid_stats_wmmfailedreceived_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D513_ac_bk_stats_wmmfailedreceived.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedReceived5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d517_ssid_stats_wmmfailedsent_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D517_ac_bk_stats_wmmfailedsent.yaml")
    assert case["id"] == "d517-ssid-wmm-ac_bk_stats_wmmfailedsent"
    assert case["source"]["row"] == 517
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedSent."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedSent.AC_BK?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedSent5g"


def test_d517_ssid_stats_wmmfailedsent_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D517_ac_bk_stats_wmmfailedsent.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d517_ssid_stats_wmmfailedsent_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D517_ac_bk_stats_wmmfailedsent.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d518_ssid_stats_wmmfailedsent_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D518_ac_vi_stats_wmmfailedsent.yaml")
    assert case["id"] == "d518-ssid-wmm-ac_vi_stats_wmmfailedsent"
    assert case["source"]["row"] == 518
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedSent."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedSent.AC_VI?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedSent5g"


def test_d518_ssid_stats_wmmfailedsent_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D518_ac_vi_stats_wmmfailedsent.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d518_ssid_stats_wmmfailedsent_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D518_ac_vi_stats_wmmfailedsent.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d519_ssid_stats_wmmfailedsent_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D519_ac_vo_stats_wmmfailedsent.yaml")
    assert case["id"] == "d519-ssid-wmm-ac_vo_stats_wmmfailedsent"
    assert case["source"]["row"] == 519
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmFailedSent."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmFailedSent.AC_VO?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmFailedSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmFailedSent5g"


def test_d519_ssid_stats_wmmfailedsent_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D519_ac_vo_stats_wmmfailedsent.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d519_ssid_stats_wmmfailedsent_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D519_ac_vo_stats_wmmfailedsent.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmFailedSent.AC_VO=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmFailedSent.AC_VO=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmFailedSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmFailedSent.AC_VO=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmFailedSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d520_ssid_stats_wmmpacketsreceived_ac_be_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D520_ac_be_stats_wmmpacketsreceived.yaml")
    assert case["id"] == "d520-ssid-wmm-ac_be_stats_wmmpacketsreceived"
    assert case["source"]["row"] == 520
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsReceived."
    assert case["source"]["api"] == "AC_BE"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsReceived.AC_BE?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BE"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsReceived5g"


def test_d520_ssid_stats_wmmpacketsreceived_ac_be_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D520_ac_be_stats_wmmpacketsreceived.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d520_ssid_stats_wmmpacketsreceived_ac_be_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D520_ac_be_stats_wmmpacketsreceived.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived5g=301665",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsReceived.AC_BE=301665",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived5g=301665",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived6g=29727",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsReceived.AC_BE=29727",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived6g=29727",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived24g=27320",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsReceived.AC_BE=27320",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived24g=27320",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d521_ssid_stats_wmmpacketsreceived_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D521_ac_bk_stats_wmmpacketsreceived.yaml")
    assert case["id"] == "d521-ssid-wmm-ac_bk_stats_wmmpacketsreceived"
    assert case["source"]["row"] == 521
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsReceived."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsReceived.AC_BK?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsReceived5g"


def test_d521_ssid_stats_wmmpacketsreceived_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D521_ac_bk_stats_wmmpacketsreceived.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d521_ssid_stats_wmmpacketsreceived_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D521_ac_bk_stats_wmmpacketsreceived.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsReceived.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d522_ssid_stats_wmmpacketsreceived_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D522_ac_vi_stats_wmmpacketsreceived.yaml")
    assert case["id"] == "d522-ssid-wmm-ac_vi_stats_wmmpacketsreceived"
    assert case["source"]["row"] == 522
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsReceived."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsReceived.AC_VI?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsReceived5g"


def test_d522_ssid_stats_wmmpacketsreceived_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D522_ac_vi_stats_wmmpacketsreceived.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d522_ssid_stats_wmmpacketsreceived_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D522_ac_vi_stats_wmmpacketsreceived.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsReceived.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d523_ssid_stats_wmmpacketsreceived_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D523_ac_vo_stats_wmmpacketsreceived.yaml")
    assert case["id"] == "d523-ssid-wmm-ac_vo_stats_wmmpacketsreceived"
    assert case["source"]["row"] == 523
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsReceived."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsReceived.AC_VO?' in case["steps"][1]["command"]
    assert 'wme_counters' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsReceived5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsReceived5g"


def test_d523_ssid_stats_wmmpacketsreceived_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D523_ac_vo_stats_wmmpacketsreceived.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d523_ssid_stats_wmmpacketsreceived_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D523_ac_vo_stats_wmmpacketsreceived.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived5g=336",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsReceived.AC_VO=336",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived5g=336",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived6g=210",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsReceived.AC_VO=210",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived6g=210",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsReceived24g=237",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsReceived.AC_VO=237",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsReceived24g=237",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d525_ssid_stats_wmmpacketssent_ac_bk_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D525_ac_bk_stats_wmmpacketssent.yaml")
    assert case["id"] == "d525-ssid-wmm-ac_bk_stats_wmmpacketssent"
    assert case["source"]["row"] == 525
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsSent."
    assert case["source"]["api"] == "AC_BK"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsSent.AC_BK?' in case["steps"][1]["command"]
    assert 'DriverWmmPacketsSent5g' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_BK"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsSent5g"


def test_d525_ssid_stats_wmmpacketssent_ac_bk_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D525_ac_bk_stats_wmmpacketssent.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d525_ssid_stats_wmmpacketssent_ac_bk_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D525_ac_bk_stats_wmmpacketssent.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsSent.AC_BK=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d526_ssid_stats_wmmpacketssent_ac_vi_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D526_ac_vi_stats_wmmpacketssent.yaml")
    assert case["id"] == "d526-ssid-wmm-ac_vi_stats_wmmpacketssent"
    assert case["source"]["row"] == 526
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsSent."
    assert case["source"]["api"] == "AC_VI"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsSent.AC_VI?' in case["steps"][1]["command"]
    assert 'DriverWmmPacketsSent5g' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VI"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsSent5g"


def test_d526_ssid_stats_wmmpacketssent_ac_vi_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D526_ac_vi_stats_wmmpacketssent.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d526_ssid_stats_wmmpacketssent_ac_vi_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D526_ac_vi_stats_wmmpacketssent.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent5g=0",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent5g=0",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent6g=0",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent6g=0",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent24g=0",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsSent.AC_VI=0",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent24g=0",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d527_ssid_stats_wmmpacketssent_ac_vo_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D527_ac_vo_stats_wmmpacketssent.yaml")
    assert case["id"] == "d527-ssid-wmm-ac_vo_stats_wmmpacketssent"
    assert case["source"]["row"] == 527
    assert case["source"]["object"] == "WiFi.SSID.{i}.Stats.WmmPacketsSent."
    assert case["source"]["api"] == "AC_VO"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 9
    assert 'WiFi.SSID.4.getSSIDStats()' in case["steps"][0]["command"]
    assert 'WiFi.SSID.4.Stats.WmmPacketsSent.AC_VO?' in case["steps"][1]["command"]
    assert 'DriverWmmPacketsSent5g' in case["steps"][2]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.AC_VO"
    assert case["pass_criteria"][0]["reference"] == "refresh_5g.GetSSIDStatsWmmPacketsSent5g"
    assert case["pass_criteria"][1]["reference"] == "driver_5g.DriverWmmPacketsSent5g"


def test_d527_ssid_stats_wmmpacketssent_ac_vo_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D527_ac_vo_stats_wmmpacketssent.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d527_ssid_stats_wmmpacketssent_ac_vo_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D527_ac_vo_stats_wmmpacketssent.yaml")
    results = {
        "steps": {
            "step_5g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent5g=336",
                "timing": 0.01,
            },
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.SSID.4.Stats.WmmPacketsSent.AC_VO=336",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent5g=336",
                "timing": 0.01,
            },
            "step_6g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent6g=210",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.SSID.6.Stats.WmmPacketsSent.AC_VO=210",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent6g=210",
                "timing": 0.01,
            },
            "step_24g_refresh": {
                "success": True,
                "output": "GetSSIDStatsWmmPacketsSent24g=237",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.SSID.8.Stats.WmmPacketsSent.AC_VO=237",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverWmmPacketsSent24g=237",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


@pytest.mark.parametrize(
    "yaml_file,row,ac_category,wmm_metric",
    _SSID_WMM_STATS_CASES,
    ids=_SSID_WMM_IDS,
)
def test_ssid_wmm_stats_load(yaml_file, row, ac_category, wmm_metric):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize(
    "yaml_file,row,ac_category,wmm_metric",
    _SSID_WMM_STATS_CASES,
    ids=_SSID_WMM_IDS,
)
def test_ssid_wmm_stats_discover(yaml_file, row, ac_category, wmm_metric):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


@pytest.mark.parametrize(
    "yaml_file,row,ac_category,wmm_metric",
    _SSID_WMM_STATS_CASES,
    ids=_SSID_WMM_IDS,
)
def test_ssid_wmm_stats_evaluate(yaml_file, row, ac_category, wmm_metric):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    case = load_case(cases_dir / yaml_file)
    ssid_idx = {"5g": 4, "6g": 6, "2.4g": 8}
    results = {"steps": {}}
    for step in case["steps"]:
        sid = step["id"]
        band = "5g" if "5g" in sid else ("6g" if "6g" in sid else "2.4g")
        idx = ssid_idx[band]
        output = f"WiFi.SSID.{idx}.Stats.{wmm_metric}.{ac_category}=0"
        results["steps"][sid] = {"success": True, "output": output, "timing": 0.01}
    assert plugin.evaluate(case, results) is True


# ---------------------------------------------------------------------------
# Batch 6 — Spectrum (D528-D533): getSpectrumInfo method-call fields
# ---------------------------------------------------------------------------
_SPECTRUM_CASES = [
    ("D528_getspectruminfo_bandwidth.yaml", 528, "bandwidth", "20MHz"),
    ("D529_getspectruminfo_channel.yaml", 529, "channel", "36"),
    ("D530_getspectruminfo_noiselevel.yaml", 530, "noiselevel", "42"),
    ("D531_getspectruminfo_accesspoints.yaml", 531, "accesspoints", "42"),
    ("D532_getspectruminfo_ourusage.yaml", 532, "ourUsage", "42"),
    ("D533_getspectruminfo_availability.yaml", 533, "availability", "42"),
]
_SPECTRUM_IDS = [t[0].split(".")[0] for t in _SPECTRUM_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,field,sample_value",
    _SPECTRUM_CASES,
    ids=_SPECTRUM_IDS,
)
def test_spectrum_load(yaml_file, row, field, sample_value):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize(
    "yaml_file,row,field,sample_value",
    _SPECTRUM_CASES,
    ids=_SPECTRUM_IDS,
)
def test_spectrum_discover(yaml_file, row, field, sample_value):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


@pytest.mark.parametrize(
    "yaml_file,row,field,sample_value",
    _SPECTRUM_CASES,
    ids=_SPECTRUM_IDS,
)
def test_spectrum_evaluate(yaml_file, row, field, sample_value):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    case = load_case(cases_dir / yaml_file)
    if yaml_file == "D529_getspectruminfo_channel.yaml":
        results = {
            "steps": {
                "step_5g_method": {"success": True, "output": "channel=36\n", "timing": 0.01},
                "step_6g_method": {"success": True, "output": "channel=2\n", "timing": 0.01},
                "step_24g_method": {"success": True, "output": "channel=1\n", "timing": 0.01},
            }
        }
        assert plugin.evaluate(case, results) is True
        return
    radio_map = {"5g": 1, "6g": 2, "2.4g": 3}
    results = {"steps": {}}
    needs_quote = not sample_value.lstrip("-").isdigit()
    for step in case["steps"]:
        sid = step["id"]
        band = "5g" if "5g" in sid else ("6g" if "6g" in sid else "2.4g")
        rid = radio_map[band]
        value = f'"{sample_value}"' if needs_quote else sample_value
        output = f"        WiFi.Radio.{rid}.getSpectrumInfo().{field} = {value},"
        results["steps"][sid] = {"success": True, "output": output, "timing": 0.01}
    assert plugin.evaluate(case, results) is True


# ---------------------------------------------------------------------------
# Batch 6 — AssocDev getters (D014,D035,D371,D408-D415,D426): 5G-only
# ---------------------------------------------------------------------------
_ASSOCDEV_GETTER_CASES = [
    ("D014_chargeableuserid.yaml", 14, "ChargeableUserId"),
    ("D035_operatingstandard.yaml", 35, "OperatingStandard"),
    ("D371_disassociationtime.yaml", 373, "DisassociationTime"),
    ("D408_downlinkratespec.yaml", 410, "DownlinkRateSpec"),
    ("D409_maxdownlinkratesupported.yaml", 411, "MaxDownlinkRateSupported"),
    ("D410_maxrxspatialstreamssupported.yaml", 412, "MaxRxSpatialStreamsSupported"),
    ("D411_maxtxspatialstreamssupported.yaml", 413, "MaxTxSpatialStreamsSupported"),
    ("D412_maxuplinkratesupported.yaml", 414, "MaxUplinkRateSupported"),
    ("D413_rrmcapabilities.yaml", 415, "RrmCapabilities"),
    ("D414_rrmoffchannelmaxduration.yaml", 416, "RrmOffChannelMaxDuration"),
    ("D415_rrmonchannelmaxduration.yaml", 417, "RrmOnChannelMaxDuration"),
    ("D426_uplinkratespec.yaml", 428, "UplinkRateSpec"),
]
_ASSOCDEV_IDS = [t[0].split(".")[0] for t in _ASSOCDEV_GETTER_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,api_field",
    _ASSOCDEV_GETTER_CASES,
    ids=_ASSOCDEV_IDS,
)
def test_assocdev_getter_load(yaml_file, row, api_field):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row


@pytest.mark.parametrize(
    "yaml_file,row,api_field",
    _ASSOCDEV_GETTER_CASES,
    ids=_ASSOCDEV_IDS,
)
def test_assocdev_getter_discover(yaml_file, row, api_field):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d014_chargeableuserid_contract():
    """D014 getter contract keeps the single-band expectation shape."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D014_chargeableuserid.yaml")
    assert case["source"]["row"] == 14
    assert case_band_results(case, True) == _expected_case_band_results(case, True)
    assert case["pass_criteria"][1]["operator"] == "contains"
    assert case["pass_criteria"][1]["value"] == 'ChargeableUserId=""'


def test_d014_chargeableuserid_evaluate_empty_string():
    """D014 evaluates on the empty-string getter shape seen on the current lab baseline."""
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D014_chargeableuserid.yaml")
    results = {
        "steps": {
            "step_5g_assoc_check": {
                "success": True,
                "output": "assoclist 2C:59:17:00:04:85",
                "timing": 0.01,
            },
            "step_5g_getter": {
                "success": True,
                "output": 'WiFi.AccessPoint.1.AssociatedDevice.1.ChargeableUserId=""',
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d035_operatingstandard_contract():
    """D035 assocdev getter keeps the tri-band verdict projection."""
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D035_operatingstandard.yaml")
    assert case["source"]["row"] == 35
    assert case_band_results(case, True) == _expected_case_band_results(case, True)
    assert case["pass_criteria"][1]["operator"] == "regex"
    assert case["pass_criteria"][1]["value"] == "^[a-z]+$"


@pytest.mark.parametrize(
    "yaml_file,row,api_field",
    _ASSOCDEV_GETTER_CASES,
    ids=_ASSOCDEV_IDS,
)
def test_assocdev_getter_evaluate(yaml_file, row, api_field):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    case = load_case(cases_dir / yaml_file)
    # Skip evaluate for cases that use 'skip' operator
    ops = {c.get("operator") for c in case.get("pass_criteria", [])}
    if "skip" in ops:
        return
    # Build synthetic values that satisfy regex criteria
    _assocdev_synth = {
        "ChargeableUserId": '""',
        "OperatingStandard": "ax",
        "DisassociationTime": "2025-01-01T00:00:00Z",
    }
    synth_val = _assocdev_synth.get(api_field, "0")
    results = {"steps": {}}
    for step in case["steps"]:
        sid = step["id"]
        cmd = step.get("command", "")
        if "AssociatedDevice" in cmd and "?" in cmd:
            output = f"WiFi.AccessPoint.1.AssociatedDevice.1.{api_field}={synth_val}"
        elif "assoclist" in cmd:
            output = "assoclist 2C:59:17:00:04:85"
        else:
            output = "OK"
        results["steps"][sid] = {"success": True, "output": output, "timing": 0.01}
    assert plugin.evaluate(case, results) is True


# ---------------------------------------------------------------------------
# Batch 6 — AP/SSID/Security getters (D319,D320,D359,D588): 3-band
# ---------------------------------------------------------------------------
_AP_SSID_SECURITY_CASES = [
    ("D359_isolationenable.yaml", 361, "IsolationEnable", "WiFi.AccessPoint.{i}."),
    ("D319_macaddress_ssid.yaml", 319, "MACAddress", "WiFi.SSID.{i}."),
    ("D320_ssid.yaml", 320, "SSID", "WiFi.SSID.{i}."),
    ("D588_mldunit.yaml", 591, "MLDUnit", "WiFi.SSID.{i}."),
]
_AP_SSID_SECURITY_IDS = [t[0].split(".")[0] for t in _AP_SSID_SECURITY_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,api_field,path_prefix",
    _AP_SSID_SECURITY_CASES,
    ids=_AP_SSID_SECURITY_IDS,
)
def test_ap_ssid_security_load(yaml_file, row, api_field, path_prefix):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row
    assert case["bands"] == ["5g", "6g", "2.4g"]


@pytest.mark.parametrize(
    "yaml_file,row,api_field,path_prefix",
    _AP_SSID_SECURITY_CASES,
    ids=_AP_SSID_SECURITY_IDS,
)
def test_ap_ssid_security_discover(yaml_file, row, api_field, path_prefix):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


@pytest.mark.parametrize(
    "yaml_file,row,api_field,path_prefix",
    _AP_SSID_SECURITY_CASES,
    ids=_AP_SSID_SECURITY_IDS,
)
def test_ap_ssid_security_evaluate(yaml_file, row, api_field, path_prefix):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    plugin = _load_plugin()
    case = load_case(cases_dir / yaml_file)
    idx_map = {"5g": 1, "6g": 3, "2.4g": 5}
    if "SSID.{i}." in path_prefix:
        idx_map = {"5g": 4, "6g": 6, "2.4g": 8}
    # Synthetic values that satisfy each field's regex criteria
    _ap_synth = {
        "IsolationEnable": "0",
        "MACAddress": "AA:BB:CC:DD:EE:FF",
        "SSID": "testpilot5G",
        "MLDUnit": "0",
        "OWETransitionInterface": "wl0",
        "SAEPassphrase": "testpass",
        "TransitionDisable": "0",
    }
    synth_val = _ap_synth.get(api_field, "0")
    results = {"steps": {}}
    for step in case["steps"]:
        sid = step["id"]
        band = "5g" if "5g" in sid else ("6g" if "6g" in sid else "2.4g")
        idx = idx_map[band]
        path = path_prefix.replace("{i}", str(idx))
        output = f"{path}{api_field}={synth_val}"
        results["steps"][sid] = {"success": True, "output": output, "timing": 0.01}
    assert plugin.evaluate(case, results) is True


# ---------------------------------------------------------------------------
# Batch 6 — Skip / Blocked cases: load + discover only (no evaluate — skip op)
# ---------------------------------------------------------------------------
_SKIP_BLOCKED_CASES = [
    ("D352_startbgdfsclear.yaml", 354, "Skip"),
    ("D353_stopbgdfsclear.yaml", 355, "Skip"),
    ("D355_addclient.yaml", 357, "Skip"),
    ("D356_delclient.yaml", 358, "Skip"),
    ("D357_csistats.yaml", 359, "Skip"),
    ("D575_macaddress_associateddevice_affiliatedsta.yaml", 578, "Skip"),
    ("D576_bytessent_associateddevice_affiliatedsta.yaml", 579, "Skip"),
    ("D577_bytesreceived_associateddevice_affiliatedsta.yaml", 580, "Skip"),
    ("D578_packetssent_associateddevice_affiliatedsta.yaml", 581, "Skip"),
    ("D579_packetsreceived_associateddevice_affiliatedsta.yaml", 582, "Skip"),
    ("D580_errorssent_associateddevice_affiliatedsta.yaml", 583, "Skip"),
    ("D581_signalstrength_associateddevice_affiliatedsta.yaml", 584, "Skip"),
]
_SKIP_BLOCKED_IDS = [t[0].split(".")[0] for t in _SKIP_BLOCKED_CASES]


@pytest.mark.parametrize(
    "yaml_file,row,reference",
    _SKIP_BLOCKED_CASES,
    ids=_SKIP_BLOCKED_IDS,
)
def test_skip_blocked_load(yaml_file, row, reference):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    assert case["source"]["row"] == row


@pytest.mark.parametrize(
    "yaml_file,row,reference",
    _SKIP_BLOCKED_CASES,
    ids=_SKIP_BLOCKED_IDS,
)
def test_skip_blocked_discover(yaml_file, row, reference):
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / yaml_file)
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


# ---------------------------------------------------------------------------
# Batch 6 — D494 protected VHT getter with mixed band results
# ---------------------------------------------------------------------------
def test_d494_radio_vhtcapabilities_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D494_vhtcapabilities_radio.yaml")
    assert case["source"]["row"] == 494
    assert case["llapi_support"] == "Support"
    assert 'protected;WiFi.Radio.1.VHTCapabilities?' in case["steps"][0]["command"]
    assert 'VHTCapabilities=\\1' in case["steps"][0]["command"]
    assert 'WiFi.Radio.2.VHTCapabilities?' in case["steps"][1]["command"]
    assert 'error=\\1' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "getter_5g.VHTCapabilities"
    assert case["pass_criteria"][1]["field"] == "getter_6g.error"
    assert case["pass_criteria"][4]["field"] == "getter_24g.message"


def test_d494_radio_vhtcapabilities_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D494_vhtcapabilities_radio.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d494_radio_vhtcapabilities_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D494_vhtcapabilities_radio.yaml")
    results = {
        "steps": {
            "step_5g_getter": {
                "success": True,
                "output": 'VHTCapabilities=dliDDw==',
                "timing": 0.01,
            },
            "step_6g_getter": {
                "success": True,
                "output": (
                    "ERROR: get WiFi.Radio.2.VHTCapabilities failed (4 - parameter not found)\n"
                    "error=4\n"
                    "message=parameter not found"
                ),
                "timing": 0.01,
            },
            "step_24g_getter": {
                "success": True,
                "output": (
                    "ERROR: get WiFi.Radio.3.VHTCapabilities failed (4 - parameter not found)\n"
                    "error=4\n"
                    "message=parameter not found"
                ),
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True


def test_d477_radio_stats_unknownprotopacketsreceived_load():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D477_unknownprotopacketsreceived_radio_stats.yaml")
    assert case["id"] == "d477-radio-stats-unknownprotopacketsreceived"
    assert case["source"]["row"] == 477
    assert case["source"]["object"] == "WiFi.Radio.{i}.Stats."
    assert case["source"]["api"] == "UnknownProtoPacketsReceived"
    assert case["llapi_support"] == "Support"
    assert len(case["steps"]) == 6
    assert 'WiFi.Radio.1.Stats.UnknownProtoPacketsReceived?' in case["steps"][0]["command"]
    assert 'rxbadproto' in case["steps"][1]["command"]
    assert case["pass_criteria"][0]["field"] == "direct_5g.UnknownProtoPacketsReceived"
    assert case["pass_criteria"][0]["reference"] == "driver_5g.DriverUnknownProtoPacketsReceived5g"


def test_d477_radio_stats_unknownprotopacketsreceived_discover():
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D477_unknownprotopacketsreceived_radio_stats.yaml")
    plugin = _load_plugin()
    discoverable = {c["id"] for c in plugin.discover_cases()}
    assert case["id"] in discoverable, f"{case['id']} not discoverable"


def test_d477_radio_stats_unknownprotopacketsreceived_evaluate():
    plugin = _load_plugin()
    cases_dir = Path(__file__).resolve().parents[3] / "plugins" / "wifi_llapi" / "cases"
    case = load_case(cases_dir / "D477_unknownprotopacketsreceived_radio_stats.yaml")
    results = {
        "steps": {
            "step_5g_direct": {
                "success": True,
                "output": "WiFi.Radio.1.Stats.UnknownProtoPacketsReceived=21",
                "timing": 0.01,
            },
            "step_5g_driver": {
                "success": True,
                "output": "DriverUnknownProtoPacketsReceived5g=21",
                "timing": 0.01,
            },
            "step_6g_direct": {
                "success": True,
                "output": "WiFi.Radio.2.Stats.UnknownProtoPacketsReceived=2",
                "timing": 0.01,
            },
            "step_6g_driver": {
                "success": True,
                "output": "DriverUnknownProtoPacketsReceived6g=2",
                "timing": 0.01,
            },
            "step_24g_direct": {
                "success": True,
                "output": "WiFi.Radio.3.Stats.UnknownProtoPacketsReceived=12",
                "timing": 0.01,
            },
            "step_24g_driver": {
                "success": True,
                "output": "DriverUnknownProtoPacketsReceived24g=12",
                "timing": 0.01,
            },
        }
    }
    assert plugin.evaluate(case, results) is True
