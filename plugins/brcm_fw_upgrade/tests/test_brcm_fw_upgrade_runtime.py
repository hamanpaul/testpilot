from __future__ import annotations

from pathlib import Path

import pytest

from testpilot.core.plugin_loader import PluginLoader

from plugins.brcm_fw_upgrade.strategies.evidence import slice_log_window
from plugins.brcm_fw_upgrade.strategies.login import build_login_commands
from plugins.brcm_fw_upgrade.strategies.flash import render_flash_command
from plugins.brcm_fw_upgrade.strategies.transfer import render_md5_command, select_transfer_method
from plugins.brcm_fw_upgrade.strategies.verify import extract_named_group


def _load_plugin():
    root = Path(__file__).resolve().parents[3]
    loader = PluginLoader(root / "plugins")
    return loader.load("brcm_fw_upgrade")


def _runtime_artifact_paths() -> tuple[Path, Path]:
    return Path(__file__).resolve(), Path(__file__).resolve().parents[1] / "plugin.py"


def _runtime_overrides(*, forward_path: Path | None = None, fw_name: str | None = None) -> dict[str, str]:
    forward_artifact, rollback_artifact = _runtime_artifact_paths()
    selected_forward = forward_path or forward_artifact
    selected_fw_name = fw_name or selected_forward.name
    return {
        "FW_FORWARD_PATH": str(selected_forward),
        "FW_ROLLBACK_PATH": str(rollback_artifact),
        "FW_NAME": selected_fw_name,
        "EXPECTED_IMAGE_TAG": "631BGW720-3001101323",
        "EXPECTED_BUILD_TIME": "Apr 20 13:02:57 CST 2026",
    }


def test_transfer_prefers_network_then_relay_then_serial():
    assert select_transfer_method({"has_scp": True}, sta_present=False) == "host_to_dut_scp"
    assert select_transfer_method({"has_scp": False}, sta_present=True) == "dut_to_sta_relay"
    assert select_transfer_method({"has_scp": False}, sta_present=False) == "serial_fallback"


def test_extract_named_group_uses_production_pattern():
    text = "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026"
    # This is the exact pattern from platform_profiles.yaml proc_version_build_time
    pattern = r"Linux version .* (?P<build_time>[A-Z][a-z]{2} .+ CST 20[0-9]{2})"
    assert extract_named_group(pattern, text, "build_time") == "Apr 20 13:02:57 CST 2026"


def test_slice_log_window_returns_marker_with_context():
    log_text = "\n".join(["line-1", "line-2", "Image flash complete", "line-4", "line-5"])
    window = slice_log_window(log_text, "Image flash complete", before=1, after=1)
    assert "Image flash complete" in window
    assert "line-2" in window
    assert "line-4" in window
    assert "line-1" not in window
    assert "line-5" not in window


def test_build_login_commands_with_no_strategy():
    assert build_login_commands({"login_strategy": "none"}) == []
    assert build_login_commands({}) == []


def test_build_login_commands_with_serialwrap_profile_login():
    profile = {"login_strategy": "serialwrap_profile_login", "pre_login_commands": ["cmd1", "cmd2"]}
    assert build_login_commands(profile) == ["cmd1", "cmd2"]


def test_build_login_commands_raises_on_unknown_strategy():
    with pytest.raises(ValueError, match="unsupported login_strategy: unknown"):
        build_login_commands({"login_strategy": "unknown"})


def test_render_md5_command_substitutes_path():
    template = "md5sum {{path}}"
    assert render_md5_command(template, path="/tmp/file.bin") == "md5sum /tmp/file.bin"


def test_render_flash_command_substitutes_fw_name():
    template = "bcm_flasher {{fw_name}}"
    assert render_flash_command(template, fw_name="image.pkgtb") == "bcm_flasher image.pkgtb"


def test_plugin_loads_profile_and_topology_metadata():
    plugin = _load_plugin()
    assert "bgw720_prpl" in plugin.platform_profiles
    assert plugin.topologies["dut_plus_sta"]["phases"][0] == "precheck"


class _RecordingShell:
    def __init__(self, outputs: dict[str, str]) -> None:
        self.outputs = dict(outputs)
        self.commands: list[str] = []

    def run(self, command: str) -> str:
        self.commands.append(command)
        return self.outputs.get(command, "")


class _RuntimePluginHarness:
    def __init__(self, *, fw_name: str | None = None) -> None:
        active_fw_name = fw_name or Path(__file__).name
        self.shells = {
            "STA": _RecordingShell(
                {
                    "cd /tmp": "/tmp",
                    f"bcm_flasher {active_fw_name}": "Image flash complete",
                    "bcm_bootstate 1": "The booted partition is marked to boot",
                    "reboot": "rebooting",
                    "echo ready": "ready",
                    "cat /proc/version": "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026",
                    "bcm_bootstate": "$imageversion: 631BGW720-3001101323 $",
                }
            ),
            "DUT": _RecordingShell(
                {
                    "cd /tmp": "/tmp",
                    f"bcm_flasher {active_fw_name}": "Image flash complete",
                    "bcm_bootstate 1": "The booted partition is marked to boot",
                    "reboot": "rebooting",
                    "echo ready": "ready",
                    "cat /proc/version": "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026",
                    "bcm_bootstate": "$imageversion: 631BGW720-3001101323 $",
                }
            ),
        }


def test_flash_sequence_runs_one_command_at_a_time():
    from plugins.brcm_fw_upgrade.strategies.flash import run_flash_sequence

    shell = _RecordingShell(
        {
            "cd /firmware": "/firmware",
            "flash_tool bcmBGW720-300_squashfs_full_update.pkgtb": "Image flash complete",
            "set_boot 1": "The booted partition is marked to boot",
            "restart_platform": "",
        }
    )
    run_flash_sequence(
        shell,
        commands={
            "change_dir": "cd /firmware",
            "flash": "flash_tool {{fw_name}}",
            "bootstate_set": "set_boot 1",
            "reboot": "restart_platform",
        },
        fw_name="bcmBGW720-300_squashfs_full_update.pkgtb",
        flash_marker="Image flash complete",
    )
    assert shell.commands == [
        "cd /firmware",
        "flash_tool bcmBGW720-300_squashfs_full_update.pkgtb",
        "set_boot 1",
        "restart_platform",
    ]


def test_flash_sequence_raises_when_marker_missing():
    from plugins.brcm_fw_upgrade.strategies.flash import run_flash_sequence

    shell = _RecordingShell(
        {
            "cd /tmp": "/tmp",
            "bcm_flasher bcmBGW720-300_squashfs_full_update.pkgtb": "flash failed",
        }
    )
    with pytest.raises(RuntimeError, match="Image flash complete"):
        run_flash_sequence(
            shell,
            commands={
                "change_dir": "cd /tmp",
                "flash": "bcm_flasher {{fw_name}}",
                "bootstate_set": "bcm_bootstate 1",
                "reboot": "reboot",
            },
            fw_name="bcmBGW720-300_squashfs_full_update.pkgtb",
            flash_marker="Image flash complete",
        )


def test_flash_sequence_raises_when_bootstate_marker_missing():
    from plugins.brcm_fw_upgrade.strategies.flash import run_flash_sequence

    shell = _RecordingShell(
        {
            "cd /tmp": "/tmp",
            "bcm_flasher bcmBGW720-300_squashfs_full_update.pkgtb": "Image flash complete",
            "bcm_bootstate 1": "bootstate failed",
        }
    )
    with pytest.raises(RuntimeError, match="marked to boot"):
        run_flash_sequence(
            shell,
            commands={
                "change_dir": "cd /tmp",
                "flash": "bcm_flasher {{fw_name}}",
                "bootstate_set": "bcm_bootstate 1",
                "reboot": "reboot",
            },
            fw_name="bcmBGW720-300_squashfs_full_update.pkgtb",
            flash_marker="Image flash complete",
        )


def test_dut_sta_case_verifies_sta_before_flashing_dut():
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    result = plugin.run_case(
        case_id="brcm-fw-upgrade-dut-sta-forward",
        shells=harness.shells,
        runtime_overrides=overrides,
    )
    forward_artifact, rollback_artifact = _runtime_artifact_paths()
    assert result["verdict"] is True
    assert [phase["id"] for phase in result["evidence"]["phases"]] == [
        "precheck",
        "transfer_dut",
        "transfer_sta",
        "flash_sta",
        "verify_sta",
        "flash_dut",
        "verify_dut",
    ]
    assert result["evidence"]["phases"][0] == {
        "id": "precheck",
        "required_devices": ["DUT", "STA"],
        "available_devices": ["DUT", "STA"],
        "runtime_inputs": {
            "fw_name": forward_artifact.name,
            "expected_image_tag": "631BGW720-3001101323",
            "expected_build_time": "Apr 20 13:02:57 CST 2026",
        },
        "artifacts": {
            "forward_image": str(forward_artifact),
            "rollback_image": str(rollback_artifact),
        },
        "active_image_role": "forward_image",
        "active_artifact_path": str(forward_artifact),
        "active_artifact_filename": forward_artifact.name,
        "fw_name_binding": {
            "declared_fw_name": forward_artifact.name,
            "artifact_filename": forward_artifact.name,
        },
    }
    assert result["evidence"]["phases"][1] == {
        "id": "transfer_dut",
        "target": "DUT",
        "artifact_path": str(forward_artifact),
        "artifact_filename": forward_artifact.name,
        "transfer_method": "host_to_dut_scp",
        "shell_ready": True,
        "md5_command": f"md5sum {forward_artifact}",
    }
    assert result["evidence"]["phases"][2] == {
        "id": "transfer_sta",
        "target": "STA",
        "artifact_path": str(forward_artifact),
        "artifact_filename": forward_artifact.name,
        "transfer_method": "host_to_dut_scp",
        "shell_ready": True,
        "md5_command": f"md5sum {forward_artifact}",
    }
    assert result["evidence"]["phases"][3]["artifact_path"] == str(forward_artifact)
    assert result["evidence"]["phases"][3]["artifact_filename"] == forward_artifact.name
    assert result["evidence"]["phases"][4]["checks"]["ready_probe"] == {
        "command": "echo ready",
        "output": "ready",
    }
    assert harness.shells["STA"].commands[:5] == [
        "cd /tmp",
        f"bcm_flasher {forward_artifact.name}",
        "bcm_bootstate 1",
        "reboot",
        "echo ready",
    ]
    assert harness.shells["DUT"].commands[:5] == [
        "cd /tmp",
        f"bcm_flasher {forward_artifact.name}",
        "bcm_bootstate 1",
        "reboot",
        "echo ready",
    ]


def test_dut_sta_case_fails_precheck_when_runtime_override_missing():
    plugin = _load_plugin()
    harness = _RuntimePluginHarness()

    with pytest.raises(RuntimeError, match="missing runtime override: FW_FORWARD_PATH"):
        plugin.run_case(
            case_id="brcm-fw-upgrade-dut-sta-forward",
            shells=harness.shells,
            runtime_overrides={
                key: value
                for key, value in _runtime_overrides().items()
                if key != "FW_FORWARD_PATH"
            },
        )

    assert harness.shells["STA"].commands == []
    assert harness.shells["DUT"].commands == []


def test_dut_sta_case_fails_precheck_when_active_artifact_missing():
    plugin = _load_plugin()
    harness = _RuntimePluginHarness(fw_name="missing-artifact.pkgtb")
    missing_artifact = Path(__file__).resolve().parent / "missing-artifact.pkgtb"

    with pytest.raises(RuntimeError, match="active artifact path does not exist"):
        plugin.run_case(
            case_id="brcm-fw-upgrade-dut-sta-forward",
            shells=harness.shells,
            runtime_overrides=_runtime_overrides(
                forward_path=missing_artifact,
                fw_name=missing_artifact.name,
            ),
        )

    assert harness.shells["STA"].commands == []
    assert harness.shells["DUT"].commands == []


def test_dut_sta_case_stops_when_sta_verification_fails():
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    harness.shells["STA"].outputs["bcm_bootstate"] = "$imageversion: unexpected $"

    with pytest.raises(RuntimeError, match="image tag mismatch"):
        plugin.run_case(
            case_id="brcm-fw-upgrade-dut-sta-forward",
            shells=harness.shells,
            runtime_overrides=overrides,
        )

    assert harness.shells["DUT"].commands == []


def test_dut_sta_case_fails_when_ready_probe_is_empty():
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    harness.shells["STA"].outputs["echo ready"] = ""

    with pytest.raises(RuntimeError, match="ready probe returned empty output"):
        plugin.run_case(
            case_id="brcm-fw-upgrade-dut-sta-forward",
            shells=harness.shells,
            runtime_overrides=overrides,
        )

    forward_artifact, _ = _runtime_artifact_paths()
    assert harness.shells["STA"].commands == [
        "cd /tmp",
        f"bcm_flasher {forward_artifact.name}",
        "bcm_bootstate 1",
        "reboot",
        "echo ready",
    ]
    assert harness.shells["DUT"].commands == []
