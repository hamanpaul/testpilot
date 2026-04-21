"""Test YAML case schema validation."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import yaml
from testpilot.schema.case_schema import (
    CaseValidationError,
    load_brcm_fw_upgrade_platform_profiles,
    load_brcm_fw_upgrade_topologies,
    load_wifi_band_baselines,
    validate_brcm_fw_upgrade_case,
    validate_case,
)

_PLUGIN_PATH = Path(__file__).resolve().parents[1] / "plugins" / "brcm_fw_upgrade" / "plugin.py"
_PLUGIN_SPEC = spec_from_file_location("tests_brcm_fw_upgrade_plugin", _PLUGIN_PATH)
assert _PLUGIN_SPEC and _PLUGIN_SPEC.loader
_PLUGIN_MODULE = module_from_spec(_PLUGIN_SPEC)
_PLUGIN_SPEC.loader.exec_module(_PLUGIN_MODULE)
Plugin = _PLUGIN_MODULE.Plugin


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


def _minimal_brcm_case(**overrides):
    base = {
        "id": "brcm-fw-upgrade-dut-sta-forward",
        "name": "BRCM DUT+STA forward upgrade",
        "platform_profile": "bgw720_prpl",
        "topology_ref": "dut_plus_sta",
        "artifacts": {
            "forward_image": "{{FW_FORWARD_PATH}}",
            "rollback_image": "{{FW_ROLLBACK_PATH}}",
            "active_image_role": "forward_image",
        },
        "runtime_inputs": {
            "fw_name": "{{FW_NAME}}",
            "expected_image_tag": "{{EXPECTED_IMAGE_TAG}}",
            "expected_build_time": "{{EXPECTED_BUILD_TIME}}",
        },
        "success_gates": [
            {
                "id": "image_tag_matches",
                "verifier": "image_tag",
                "operator": "equals",
                "expected": "{{EXPECTED_IMAGE_TAG}}",
            }
        ],
        "evidence": {
            "capture": ["dut_serial", "sta_serial", "command_output"],
            "required_for_pass": ["image_tag_matches"],
        },
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
    dut_pre_start_commands: [ubus-cli WiFi.AccessPoint.3.MultiAPType=None]
    dut_runtime_config_commands: ["sed -i 's/^sae_pwe=.*/sae_pwe=2/g' /tmp/wl1_hapd.conf"]
    dut_runtime_ready_commands: ["grep -q '^sae_pwe=2$' /tmp/wl1_hapd.conf"]
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
    assert profiles["6g"]["dut_pre_start_commands"] == ["ubus-cli WiFi.AccessPoint.3.MultiAPType=None"]
    assert profiles["6g"]["dut_runtime_config_commands"] == [
        "sed -i 's/^sae_pwe=.*/sae_pwe=2/g' /tmp/wl1_hapd.conf"
    ]
    assert profiles["6g"]["dut_runtime_ready_commands"] == [
        "grep -q '^sae_pwe=2$' /tmp/wl1_hapd.conf"
    ]
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


def test_validate_brcm_fw_upgrade_case_accepts_minimal_valid_case():
    validate_brcm_fw_upgrade_case(_minimal_brcm_case())


def test_validate_brcm_fw_upgrade_case_rejects_missing_success_gates():
    case = _minimal_brcm_case()
    del case["success_gates"]
    with pytest.raises(CaseValidationError, match="missing required keys"):
        validate_brcm_fw_upgrade_case(case)


def test_validate_brcm_fw_upgrade_case_rejects_missing_gate_fields():
    case = _minimal_brcm_case(success_gates=[{"id": "image_tag_matches"}])
    with pytest.raises(CaseValidationError, match="success_gates\\[0\\] missing required keys"):
        validate_brcm_fw_upgrade_case(case)


def test_validate_brcm_fw_upgrade_case_accepts_one_of_expected_list():
    case = _minimal_brcm_case(
        success_gates=[
            {
                "id": "image_tag_matches",
                "verifier": "image_tag",
                "operator": "one_of",
                "expected": ["{{EXPECTED_IMAGE_TAG}}", "{{FALLBACK_IMAGE_TAG}}"],
            }
        ]
    )
    validate_brcm_fw_upgrade_case(case)


def test_validate_brcm_fw_upgrade_case_rejects_unknown_operator():
    case = _minimal_brcm_case(
        success_gates=[
            {
                "id": "image_tag_matches",
                "verifier": "image_tag",
                "operator": "typo",
                "expected": "{{EXPECTED_IMAGE_TAG}}",
            }
        ]
    )
    with pytest.raises(CaseValidationError, match="operator must be one of"):
        validate_brcm_fw_upgrade_case(case)


def test_validate_brcm_fw_upgrade_case_rejects_invalid_active_image_role():
    case = _minimal_brcm_case(
        artifacts={
            "forward_image": "{{FW_FORWARD_PATH}}",
            "rollback_image": "{{FW_ROLLBACK_PATH}}",
            "active_image_role": "active_image_role",
        }
    )
    with pytest.raises(CaseValidationError, match="active_image_role"):
        validate_brcm_fw_upgrade_case(case)


def test_validate_brcm_fw_upgrade_case_rejects_non_string_platform_profile():
    case = _minimal_brcm_case(platform_profile=["bgw720_prpl"])
    with pytest.raises(CaseValidationError, match="platform_profile"):
        validate_brcm_fw_upgrade_case(case)


def test_load_brcm_fw_upgrade_platform_profiles_accepts_valid_file(tmp_path):
    path = tmp_path / "profiles.yaml"
    path.write_text(
        """
version: "2026-04-21"
profiles:
  bgw720_prpl:
    family: brcm
    board: BGW720-300
    os_flavor: prpl
    login_strategy: none
    capabilities:
      has_scp: true
      has_md5sum: true
      has_bcm_bootstate: true
    commands:
      proc_version: cat /proc/version
      image_state: bcm_bootstate
      md5: md5sum {{path}}
      flash: bcm_flasher {{fw_name}}
      reboot: reboot
    success_parsers:
      proc_version_build_time: "Linux version .*"
      image_tag: '\\$imageversion: (?P<image_tag>[^$]+) \\$'
    log_markers:
      flash_complete: Image flash complete
""".strip(),
        encoding="utf-8",
    )
    profiles = load_brcm_fw_upgrade_platform_profiles(path)
    assert profiles["bgw720_prpl"]["capabilities"]["has_scp"] is True


def test_load_brcm_fw_upgrade_platform_profiles_rejects_missing_login_strategy(tmp_path):
    path = tmp_path / "profiles.yaml"
    path.write_text(
        """
version: "2026-04-21"
profiles:
  bgw720_prpl:
    family: brcm
    board: BGW720-300
    os_flavor: prpl
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError, match="login_strategy"):
        load_brcm_fw_upgrade_platform_profiles(path)


def test_load_brcm_fw_upgrade_platform_profiles_rejects_non_mapping_capabilities(tmp_path):
    path = tmp_path / "profiles.yaml"
    path.write_text(
        """
version: "2026-04-21"
profiles:
  bgw720_prpl:
    family: brcm
    board: BGW720-300
    os_flavor: prpl
    login_strategy: none
    capabilities:
      - has_scp
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError, match="capabilities"):
        load_brcm_fw_upgrade_platform_profiles(path)


def test_load_brcm_fw_upgrade_platform_profiles_rejects_non_mapping_commands(tmp_path):
    path = tmp_path / "profiles.yaml"
    path.write_text(
        """
version: "2026-04-21"
profiles:
  bgw720_prpl:
    family: brcm
    board: BGW720-300
    os_flavor: prpl
    login_strategy: none
    commands: ""
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError, match="commands"):
        load_brcm_fw_upgrade_platform_profiles(path)


def test_load_brcm_fw_upgrade_platform_profiles_rejects_non_string_log_marker(tmp_path):
    path = tmp_path / "profiles.yaml"
    path.write_text(
        """
version: "2026-04-21"
profiles:
  bgw720_prpl:
    family: brcm
    board: BGW720-300
    os_flavor: prpl
    login_strategy: none
    log_markers:
      flash_complete: true
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError, match="log_markers.flash_complete"):
        load_brcm_fw_upgrade_platform_profiles(path)


def test_load_brcm_fw_upgrade_topologies_rejects_missing_phases(tmp_path):
    path = tmp_path / "topologies.yaml"
    path.write_text(
        """
version: "2026-04-21"
topologies:
  single_dut:
    devices:
      DUT:
        required: true
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError, match="phases"):
        load_brcm_fw_upgrade_topologies(path)


def test_load_brcm_fw_upgrade_topologies_rejects_non_mapping_device_entry(tmp_path):
    path = tmp_path / "topologies.yaml"
    path.write_text(
        """
version: "2026-04-21"
topologies:
  single_dut:
    devices:
      DUT: required
    phases:
      - precheck
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(CaseValidationError, match="devices.DUT"):
        load_brcm_fw_upgrade_topologies(path)


def test_brcm_plugin_discovery_rejects_unknown_topology_ref(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "invalid.yaml").write_text(
        yaml.safe_dump(_minimal_brcm_case(topology_ref="missing-topology"), sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(Plugin, "cases_dir", property(lambda self: cases_dir))

    with pytest.raises(CaseValidationError, match="unknown topology_ref"):
        Plugin().discover_cases()


def test_brcm_plugin_discovery_rejects_unknown_platform_profile(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "invalid.yaml").write_text(
        yaml.safe_dump(_minimal_brcm_case(platform_profile="missing-profile"), sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(Plugin, "cases_dir", property(lambda self: cases_dir))

    with pytest.raises(CaseValidationError, match="unknown platform_profile"):
        Plugin().discover_cases()


def test_brcm_plugin_discovery_rejects_unknown_verifier(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    invalid_case = _minimal_brcm_case(
        success_gates=[
            {
                "id": "image_tag_matches",
                "verifier": "missing_parser",
                "operator": "equals",
                "expected": "{{EXPECTED_IMAGE_TAG}}",
            }
        ]
    )
    (cases_dir / "invalid.yaml").write_text(
        yaml.safe_dump(invalid_case, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(Plugin, "cases_dir", property(lambda self: cases_dir))

    with pytest.raises(CaseValidationError, match="unknown verifier"):
        Plugin().discover_cases()


def test_brcm_plugin_discovery_rejects_unknown_required_for_pass_reference(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    invalid_case = _minimal_brcm_case(
        evidence={
            "capture": ["dut_serial", "sta_serial", "command_output"],
            "required_for_pass": ["missing-requirement"],
        }
    )
    (cases_dir / "invalid.yaml").write_text(
        yaml.safe_dump(invalid_case, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(Plugin, "cases_dir", property(lambda self: cases_dir))

    with pytest.raises(CaseValidationError, match="unknown evidence requirement"):
        Plugin().discover_cases()


def test_brcm_plugin_discovery_accepts_log_marker_required_for_pass(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    valid_case = _minimal_brcm_case(
        evidence={
            "capture": ["dut_serial", "sta_serial", "command_output"],
            "required_for_pass": ["flash_complete"],
        }
    )
    (cases_dir / "valid.yaml").write_text(
        yaml.safe_dump(valid_case, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(Plugin, "cases_dir", property(lambda self: cases_dir))

    cases = Plugin().discover_cases()
    assert len(cases) == 1


def test_brcm_plugin_discovery_rejects_non_mapping_case_yaml(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "invalid.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    monkeypatch.setattr(Plugin, "cases_dir", property(lambda self: cases_dir))

    with pytest.raises(CaseValidationError, match="case must be a YAML mapping"):
        Plugin().discover_cases()
