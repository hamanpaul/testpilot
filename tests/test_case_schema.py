"""Test YAML case schema validation."""

import pytest
from testpilot.schema.case_schema import (
    CaseValidationError,
    load_wifi_band_baselines,
    validate_case,
)


def _minimal_case(**overrides):
    base = {
        "id": "test-1",
        "name": "test case",
        "topology": {"devices": {"DUT": {"role": "ap"}}},
        "steps": [{"id": "s1", "action": "exec", "target": "DUT"}],
        "pass_criteria": [{"field": "x", "operator": "==", "value": "y"}],
    }
    base.update(overrides)
    return base


def test_valid_case():
    validate_case(_minimal_case())


def test_missing_top_key():
    case = _minimal_case()
    del case["steps"]
    with pytest.raises(CaseValidationError, match="missing required keys"):
        validate_case(case)


def test_empty_devices():
    case = _minimal_case(topology={"devices": {}})
    with pytest.raises(CaseValidationError, match="non-empty mapping"):
        validate_case(case)


def test_duplicate_step_id():
    case = _minimal_case(steps=[
        {"id": "s1", "action": "exec", "target": "DUT"},
        {"id": "s1", "action": "exec", "target": "DUT"},
    ])
    with pytest.raises(CaseValidationError, match="duplicate step id"):
        validate_case(case)


def test_depends_on_ordering():
    case = _minimal_case(steps=[
        {"id": "s1", "action": "exec", "target": "DUT", "depends_on": "s2"},
        {"id": "s2", "action": "exec", "target": "DUT"},
    ])
    with pytest.raises(CaseValidationError, match="not found before"):
        validate_case(case)


def test_step_command_accepts_non_empty_string_list():
    case = _minimal_case(steps=[
        {"id": "s1", "action": "exec", "target": "DUT", "command": ["echo one", "echo two"]},
    ])
    validate_case(case)


def test_step_command_rejects_non_string_list_items():
    case = _minimal_case(steps=[
        {"id": "s1", "action": "exec", "target": "DUT", "command": ["echo one", 2]},
    ])
    with pytest.raises(CaseValidationError, match="command must be a string or non-empty list of strings"):
        validate_case(case)


def test_step_command_rejects_empty_string_list_items():
    case = _minimal_case(steps=[
        {"id": "s1", "action": "exec", "target": "DUT", "command": ["echo one", "   "]},
    ])
    with pytest.raises(CaseValidationError, match="command must be a string or non-empty list of strings"):
        validate_case(case)


def test_load_wifi_band_baselines_accepts_valid_profiles(tmp_path):
    baseline_file = tmp_path / "wifi-band-baselines.yaml"
    baseline_file.write_text(
        """
profiles:
  5g:
    iface: wl0
    radio: "1"
    ap: "1"
    secondary_ap: "2"
    ssid_index: "4"
    ssid: testpilot5G
    mode: WPA2-Personal
    key: "00000000"
    mfp: Disabled
    dut_secret_fields: [KeyPassPhrase]
    sta_global_config: [ctrl_interface=/var/run/wpa_supplicant, update_config=1]
    sta_network_config: ['ssid="{{ssid}}"', key_mgmt=WPA-PSK, 'psk="{{key}}"', scan_ssid=1]
    sta_post_start_commands: ['wpa_cli -i {{iface}} select_network 0']
    sta_ctrl_command: wpa_cli -i {{iface}} ping
    sta_connect_command: wpa_cli -i {{iface}} select_network 0
    sta_status_command: wpa_cli -i {{iface}} status
    sta_driver_join_command: wl -i {{iface}} join {{ssid}} imode bss
  6g:
    iface: wl1
    radio: "2"
    ap: "3"
    secondary_ap: "4"
    ssid_index: "6"
    ssid: testpilot6G
    mode: WPA3-Personal
    key: "00000000"
    mfp: Required
    dut_secret_fields: [SAEPassphrase, KeyPassPhrase]
    sta_global_config: [ctrl_interface=/var/run/wpa_supplicant, update_config=1, sae_pwe=2]
    sta_network_config: ['ssid="{{ssid}}"', key_mgmt=SAE, 'sae_password="{{key}}"', ieee80211w=2, scan_ssid=1]
    sta_post_start_commands: []
    sta_ctrl_command: wpa_cli -i {{iface}} ping
    sta_connect_command: wpa_cli -i {{iface}} reconnect
    sta_status_command: wpa_cli -i {{iface}} status
  2.4g:
    iface: wl2
    radio: "3"
    ap: "5"
    secondary_ap: "6"
    ssid_index: "8"
    ssid: testpilot2G
    mode: WPA2-Personal
    key: "00000000"
    mfp: Disabled
    dut_secret_fields: [KeyPassPhrase]
    sta_global_config: [ctrl_interface=/var/run/wpa_supplicant, update_config=1]
    sta_network_config: ['ssid="{{ssid}}"', key_mgmt=WPA-PSK, 'psk="{{key}}"', scan_ssid=1]
    sta_post_start_commands: ['wpa_cli -i {{iface}} enable_network 0', 'wpa_cli -i {{iface}} select_network 0']
    sta_ctrl_command: wpa_cli -i {{iface}} ping
    sta_connect_command: wpa_cli -i {{iface}} select_network 0
    sta_status_command: wpa_cli -i {{iface}} status
""".strip(),
        encoding="utf-8",
    )

    profiles = load_wifi_band_baselines(baseline_file)

    assert profiles["5g"]["ssid"] == "testpilot5G"
    assert profiles["6g"]["dut_secret_fields"] == ["SAEPassphrase", "KeyPassPhrase"]
    assert profiles["2.4g"]["sta_post_start_commands"] == [
        "wpa_cli -i {{iface}} enable_network 0",
        "wpa_cli -i {{iface}} select_network 0",
    ]


def test_load_wifi_band_baselines_rejects_missing_band(tmp_path):
    baseline_file = tmp_path / "wifi-band-baselines.yaml"
    baseline_file.write_text(
        """
profiles:
  5g:
    iface: wl0
    radio: "1"
    ap: "1"
    secondary_ap: "2"
    ssid_index: "4"
    ssid: testpilot5G
    mode: WPA2-Personal
    key: "00000000"
    mfp: Disabled
    dut_secret_fields: [KeyPassPhrase]
    sta_global_config: [ctrl_interface=/var/run/wpa_supplicant]
    sta_network_config: ['ssid="{{ssid}}"']
    sta_post_start_commands: []
    sta_ctrl_command: wpa_cli -i {{iface}} ping
    sta_connect_command: wpa_cli -i {{iface}} select_network 0
    sta_status_command: wpa_cli -i {{iface}} status
  2.4g:
    iface: wl2
    radio: "3"
    ap: "5"
    secondary_ap: "6"
    ssid_index: "8"
    ssid: testpilot2G
    mode: WPA2-Personal
    key: "00000000"
    mfp: Disabled
    dut_secret_fields: [KeyPassPhrase]
    sta_global_config: [ctrl_interface=/var/run/wpa_supplicant]
    sta_network_config: ['ssid="{{ssid}}"']
    sta_post_start_commands: []
    sta_ctrl_command: wpa_cli -i {{iface}} ping
    sta_connect_command: wpa_cli -i {{iface}} select_network 0
    sta_status_command: wpa_cli -i {{iface}} status
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(CaseValidationError, match="missing wifi baseline profiles"):
        load_wifi_band_baselines(baseline_file)
