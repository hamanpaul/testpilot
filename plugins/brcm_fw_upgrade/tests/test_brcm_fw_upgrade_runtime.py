from pathlib import Path

from testpilot.core.plugin_loader import PluginLoader


def test_brcm_fw_upgrade_smoke_load():
    root = Path(__file__).resolve().parents[3]
    plugin = PluginLoader(root / "plugins").load("brcm_fw_upgrade")
    assert plugin.name == "brcm_fw_upgrade"
