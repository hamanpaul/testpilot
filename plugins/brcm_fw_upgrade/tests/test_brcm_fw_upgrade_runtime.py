from __future__ import annotations

from pathlib import Path

from testpilot.core.plugin_loader import PluginLoader

from plugins.brcm_fw_upgrade.strategies.evidence import slice_log_window
from plugins.brcm_fw_upgrade.strategies.transfer import select_transfer_method
from plugins.brcm_fw_upgrade.strategies.verify import extract_named_group


def _load_plugin():
    root = Path(__file__).resolve().parents[3]
    loader = PluginLoader(root / "plugins")
    return loader.load("brcm_fw_upgrade")


def test_transfer_prefers_network_then_relay_then_serial():
    assert select_transfer_method({"has_scp": True}, sta_present=False) == "host_to_dut_scp"
    assert select_transfer_method({"has_scp": False}, sta_present=True) == "dut_to_sta_relay"
    assert select_transfer_method({"has_scp": False}, sta_present=False) == "serial_fallback"


def test_extract_named_group_returns_expected_value():
    text = "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026"
    pattern = r"Linux version .* (?P<build_time>[A-Z][a-z]{2} [A-Z][a-z]{2} .+ CST 20[0-9]{2})"
    assert extract_named_group(pattern, text, "build_time") == "Mon Apr 20 13:02:57 CST 2026"


def test_slice_log_window_returns_marker_context():
    log_text = "\\n".join(["line-1", "line-2", "Image flash complete", "line-4", "line-5"])
    assert "Image flash complete" in slice_log_window(log_text, "Image flash complete", before=1, after=1)


def test_plugin_loads_profile_and_topology_metadata():
    plugin = _load_plugin()
    assert "bgw720_prpl" in plugin.platform_profiles
    assert plugin.topologies["dut_plus_sta"]["phases"][0] == "precheck"
