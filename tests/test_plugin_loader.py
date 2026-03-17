"""Test PluginLoader discovery and loading."""

from pathlib import Path

from testpilot.core.plugin_loader import PluginLoader
from testpilot.schema.case_schema import load_case


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
    assert "wifi-llapi-D011-associationtime" in ids
    assert "wifi-llapi-D265-getradiostats-broadcastpacketsreceived" in ids
    assert "wifi-llapi-legacy-fixture-kickstation" not in ids
    assert "wifi-llapi-legacy-fixture-getradiostats" not in ids


def test_load_legacy_fixture_cases_explicitly():
    """legacy compatibility fixtures 應可明確載入，但不應混入 discover_cases。"""
    root = Path(__file__).resolve().parents[1]
    cases_dir = root / "plugins" / "wifi_llapi" / "cases"

    kickstation_fixture = load_case(cases_dir / "_legacy_fixture_kickstation.yaml")
    getradiostats_fixture = load_case(cases_dir / "_legacy_fixture_getradiostats.yaml")

    assert kickstation_fixture["id"] == "wifi-llapi-legacy-fixture-kickstation"
    assert kickstation_fixture["name"] == "Legacy compatibility fixture — kickStation()"
    assert kickstation_fixture["source"]["row"] == 6

    assert getradiostats_fixture["id"] == "wifi-llapi-legacy-fixture-getradiostats"
    assert getradiostats_fixture["name"] == "Legacy compatibility fixture — getRadioStats()"
    assert getradiostats_fixture["source"]["row"] == 265
