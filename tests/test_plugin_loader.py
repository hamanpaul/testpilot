"""Test PluginLoader discovery and loading."""

from pathlib import Path

from testpilot.core.plugin_loader import PluginLoader


def test_discover_plugins():
    """plugins/ 下應發現 wifi_llapi。"""
    root = Path(__file__).resolve().parents[1]
    loader = PluginLoader(root / "plugins")
    names = loader.discover()
    assert "wifi_llapi" in names


def test_load_wifi_llapi():
    """wifi_llapi plugin 應可正常載入。"""
    root = Path(__file__).resolve().parents[1]
    loader = PluginLoader(root / "plugins")
    plugin = loader.load("wifi_llapi")
    assert plugin.name == "wifi_llapi"
    assert plugin.version == "0.1.0"


def test_discover_cases():
    """wifi_llapi 應有至少 2 條 test cases。"""
    root = Path(__file__).resolve().parents[1]
    loader = PluginLoader(root / "plugins")
    plugin = loader.load("wifi_llapi")
    cases = plugin.discover_cases()
    assert len(cases) >= 2
    ids = [c["id"] for c in cases]
    assert "wifi-llapi-getRadioStats" in ids
    assert "wifi-llapi-kickStation" in ids
