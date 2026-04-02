"""Targeted runtime regressions for D024 LastDataDownlinkRate."""

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
        '[ -n "$RATE" ] && echo DriverLastDownlinkRateRounded=$((RATE/100*100))'
    )
    transport = _ScriptTransport("DriverLastDownlinkRateRounded=541600")
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
    assert result["captured"]["DriverLastDownlinkRateRounded"] == "541600"
    assert result["command"] == command
    assert transport.executed_commands == [command]
