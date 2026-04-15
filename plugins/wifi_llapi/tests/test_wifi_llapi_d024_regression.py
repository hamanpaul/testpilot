"""Targeted runtime regressions for D024-D026 AssociatedDevice rate steps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from testpilot.core.plugin_loader import PluginLoader


class _PassthroughTopology:
    def resolve(self, text: str) -> str:
        return text

    def get_device(self, role: str) -> dict[str, Any]:
        del role
        return {}


class _ScriptTransport:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.executed_commands: list[str] = []

    def execute(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
        del timeout
        self.executed_commands.append(command)
        return {
            "returncode": 0,
            "stdout": self.stdout,
            "stderr": "",
            "elapsed": 0.01,
        }


def _load_plugin() -> Any:
    root = Path(__file__).resolve().parents[3]
    return PluginLoader(root / "plugins").load("wifi_llapi")


def test_execute_step_accepts_d024_driver_rate_shell_pipeline() -> None:
    plugin = _load_plugin()
    command = (
        'STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" '
        '| sed -n \'s/.*MACAddress="\\([^"]*\\)".*/\\1/p\'); '
        "RATE=$(wl -i wl0 sta_info $STA_MAC | sed -n "
        '\'s/.*rate of last tx pkt: \\([0-9][0-9]*\\) kbps.*/\\1/p\' | head -n1); '
        'if [ -n "$RATE" ]; then UPPER=$((RATE/100*100)); LOWER=$UPPER; '
        '[ "$LOWER" -ge 100 ] && LOWER=$((LOWER-100)); '
        'printf "DriverLastDownlinkRateLower=%s\\nDriverLastDownlinkRateUpper=%s\\n" "$LOWER" "$UPPER"; fi'
    )
    transport = _ScriptTransport(
        "DriverLastDownlinkRateLower=541500\nDriverLastDownlinkRateUpper=541600"
    )
    plugin._transports["DUT"] = transport
    case = {
        "id": "wifi-llapi-runtime-d024-driver-rate",
        "steps": [
            {
                "id": "step4",
                "action": "exec",
                "target": "DUT",
                "capture": "driver_rate",
                "command": command,
            }
        ],
    }

    result = plugin.execute_step(case, case["steps"][0], topology=_PassthroughTopology())

    assert result["success"] is True
    assert result["returncode"] == 0
    assert result["captured"]["DriverLastDownlinkRateLower"] == "541500"
    assert result["captured"]["DriverLastDownlinkRateUpper"] == "541600"
    assert result["command"] == command
    assert transport.executed_commands == [command]


def test_execute_step_accepts_d025_driver_rate_shell_pipeline() -> None:
    plugin = _load_plugin()
    command = (
        'STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" '
        '| sed -n \'s/.*MACAddress="\\([^"]*\\)".*/\\1/p\'); '
        "RATE=$(wl -i wl0 sta_info $STA_MAC | sed -n "
        '\'s/.*rate of last rx pkt: \\([0-9][0-9]*\\) kbps.*/\\1/p\' | head -n1); '
        '[ -n "$RATE" ] && echo DriverLastUplinkRateRounded=$((RATE/100*100))'
    )
    transport = _ScriptTransport("DriverLastUplinkRateRounded=6000")
    plugin._transports["DUT"] = transport
    case = {
        "id": "wifi-llapi-runtime-d025-driver-rate",
        "steps": [
            {
                "id": "step4",
                "action": "exec",
                "target": "DUT",
                "capture": "driver_rate",
                "command": command,
            }
        ],
    }

    result = plugin.execute_step(case, case["steps"][0], topology=_PassthroughTopology())

    assert result["success"] is True
    assert result["returncode"] == 0
    assert result["captured"]["DriverLastUplinkRateRounded"] == "6000"
    assert result["command"] == command
    assert transport.executed_commands == [command]


def test_execute_step_accepts_d026_driver_bandwidth_shell_pipeline() -> None:
    plugin = _load_plugin()
    command = (
        'STA_MAC=$(ubus-cli "WiFi.AccessPoint.1.AssociatedDevice.1.MACAddress?" '
        '| sed -n \'s/.*MACAddress="\\([^"]*\\)".*/\\1/p\'); '
        '[ -n "$STA_MAC" ] && wl -i wl0 sta_info $STA_MAC | sed -n '
        '\'s/.*link bandwidth = *\\([0-9][0-9]*\\) MHZ.*/DriverLinkBandwidth=\\1MHz/p\''
    )
    transport = _ScriptTransport("DriverLinkBandwidth=20MHz")
    plugin._transports["DUT"] = transport
    case = {
        "id": "wifi-llapi-runtime-d026-driver-bandwidth",
        "steps": [
            {
                "id": "step4",
                "action": "exec",
                "target": "DUT",
                "capture": "driver_bw",
                "command": command,
            }
        ],
    }

    result = plugin.execute_step(case, case["steps"][0], topology=_PassthroughTopology())

    assert result["success"] is True
    assert result["returncode"] == 0
    assert result["captured"]["DriverLinkBandwidth"] == "20MHz"
    assert result["command"] == command
    assert transport.executed_commands == [command]
