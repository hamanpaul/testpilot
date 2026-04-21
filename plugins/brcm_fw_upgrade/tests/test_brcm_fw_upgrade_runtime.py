from __future__ import annotations

from pathlib import Path
from typing import cast

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
    def __init__(self, outputs: dict[str, object]) -> None:
        self.outputs = dict(outputs)
        self.commands: list[str] = []

    def run(self, command: str) -> str:
        self.commands.append(command)
        output = self.outputs.get(command, "")
        if isinstance(output, Exception):
            raise output
        if isinstance(output, list):
            if output:
                next_output = output.pop(0)
                if isinstance(next_output, Exception):
                    raise next_output
                return cast(str, next_output)
            return ""
        return cast(str, output)


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


class _RecordingTransport:
    def __init__(self, outputs: dict[str, object]) -> None:
        self.outputs = dict(outputs)
        self.commands: list[tuple[str, float]] = []
        self.connected = False
        self.disconnected = False

    def connect(self, **kwargs) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.disconnected = True
        self.connected = False

    def execute(self, command: str, timeout: float = 30.0) -> dict[str, object]:
        self.commands.append((command, timeout))
        output = self.outputs.get(command, "")
        if isinstance(output, Exception):
            return {"returncode": 1, "stdout": "", "stderr": str(output), "elapsed": 0.0}
        if isinstance(output, list):
            if output:
                next_output = output.pop(0)
                if isinstance(next_output, Exception):
                    return {"returncode": 1, "stdout": "", "stderr": str(next_output), "elapsed": 0.0}
                return {"returncode": 0, "stdout": cast(str, next_output), "stderr": "", "elapsed": 0.0}
            return {"returncode": 0, "stdout": "", "stderr": "", "elapsed": 0.0}
        return {"returncode": 0, "stdout": cast(str, output), "stderr": "", "elapsed": 0.0}


class _FakeTopology:
    def __init__(self, devices: dict[str, dict[str, object]], name: str = "fake-topology") -> None:
        self.name = name
        self.devices = devices

    def get_device(self, role: str) -> dict[str, object]:
        return dict(self.devices[role])


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


def test_dut_sta_case_verifies_sta_before_flashing_dut(monkeypatch: pytest.MonkeyPatch):
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    sleep_calls: list[float] = []
    monkeypatch.setattr("plugins.brcm_fw_upgrade.plugin.time.sleep", lambda delay: sleep_calls.append(delay))
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
        "retry_delay_seconds": 1.0,
        "attempts": [
            {"attempt": 1, "command": "echo ready", "output": "ready", "status": "ready"},
        ],
        "output": "ready",
    }
    assert sleep_calls == []
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


def test_dut_sta_case_fails_precheck_when_active_artifact_is_not_a_file():
    plugin = _load_plugin()
    harness = _RuntimePluginHarness(fw_name=Path(__file__).resolve().parent.name)
    not_a_file = Path(__file__).resolve().parent

    with pytest.raises(RuntimeError, match="active artifact path is not a file"):
        plugin.run_case(
            case_id="brcm-fw-upgrade-dut-sta-forward",
            shells=harness.shells,
            runtime_overrides=_runtime_overrides(
                forward_path=not_a_file,
                fw_name=not_a_file.name,
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


def test_dut_sta_case_fails_when_ready_probe_is_empty(monkeypatch: pytest.MonkeyPatch):
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    harness.shells["STA"].outputs["echo ready"] = ""
    sleep_calls: list[float] = []
    monkeypatch.setattr("plugins.brcm_fw_upgrade.plugin.time.sleep", lambda delay: sleep_calls.append(delay))

    with pytest.raises(RuntimeError, match="ready probe failed after 3 attempts"):
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
        "echo ready",
        "echo ready",
    ]
    assert sleep_calls == [1.0, 1.0]
    assert harness.shells["DUT"].commands == []


def test_dut_sta_case_ready_probe_retries_until_success(monkeypatch: pytest.MonkeyPatch):
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    harness.shells["STA"].outputs["echo ready"] = ["", "ready"]
    sleep_calls: list[float] = []
    monkeypatch.setattr("plugins.brcm_fw_upgrade.plugin.time.sleep", lambda delay: sleep_calls.append(delay))

    result = plugin.run_case(
        case_id="brcm-fw-upgrade-dut-sta-forward",
        shells=harness.shells,
        runtime_overrides=overrides,
    )

    assert result["verdict"] is True
    assert result["evidence"]["phases"][4]["checks"]["ready_probe"] == {
        "command": "echo ready",
        "retry_delay_seconds": 1.0,
        "attempts": [
            {
                "attempt": 1,
                "command": "echo ready",
                "output": "",
                "status": "empty",
                "slept_seconds": 1.0,
            },
            {"attempt": 2, "command": "echo ready", "output": "ready", "status": "ready"},
        ],
        "output": "ready",
    }
    assert sleep_calls == [1.0]


def test_dut_sta_case_ready_probe_retries_after_transient_exception(
    monkeypatch: pytest.MonkeyPatch,
):
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    harness = _RuntimePluginHarness(fw_name=overrides["FW_NAME"])
    harness.shells["STA"].outputs["echo ready"] = [RuntimeError("transport not ready"), "ready"]
    sleep_calls: list[float] = []
    monkeypatch.setattr("plugins.brcm_fw_upgrade.plugin.time.sleep", lambda delay: sleep_calls.append(delay))

    result = plugin.run_case(
        case_id="brcm-fw-upgrade-dut-sta-forward",
        shells=harness.shells,
        runtime_overrides=overrides,
    )

    assert result["verdict"] is True
    assert result["evidence"]["phases"][4]["checks"]["ready_probe"] == {
        "command": "echo ready",
        "retry_delay_seconds": 1.0,
        "attempts": [
            {
                "attempt": 1,
                "command": "echo ready",
                "error": "transport not ready",
                "status": "error",
                "slept_seconds": 1.0,
            },
            {"attempt": 2, "command": "echo ready", "output": "ready", "status": "ready"},
        ],
        "output": "ready",
    }
    assert sleep_calls == [1.0]


def test_run_cases_executes_live_case_via_transports(monkeypatch: pytest.MonkeyPatch):
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    overrides.update({"PLATFORM_PROFILE": "bgw720_prpl", "TOPOLOGY": "dut_plus_sta"})
    forward_artifact, _ = _runtime_artifact_paths()
    dut_transport = _RecordingTransport(
        {
            "cd /tmp": "/tmp",
            f"bcm_flasher {forward_artifact.name}": "Image flash complete",
            "bcm_bootstate 1": "The booted partition is marked to boot",
            "reboot": "rebooting",
            "echo ready": "ready",
            "cat /proc/version": "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026",
            "bcm_bootstate": "$imageversion: 631BGW720-3001101323 $",
        }
    )
    sta_transport = _RecordingTransport(
        {
            "cd /tmp": "/tmp",
            f"bcm_flasher {forward_artifact.name}": "Image flash complete",
            "bcm_bootstate 1": "The booted partition is marked to boot",
            "reboot": "rebooting",
            "echo ready": "ready",
            "cat /proc/version": "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026",
            "bcm_bootstate": "$imageversion: 631BGW720-3001101323 $",
        }
    )

    def _fake_create_transport(kind: str, config: dict[str, object]):
        selector = config.get("selector")
        if selector == "COM0":
            return dut_transport
        if selector == "COM1":
            return sta_transport
        raise AssertionError(f"unexpected transport request: {kind} {config}")

    monkeypatch.setattr(f"{plugin.__class__.__module__}.create_transport", _fake_create_transport)
    topology = _FakeTopology(
        {
            "DUT": {"transport": "serial", "selector": "COM0"},
            "STA": {"transport": "serial", "selector": "COM1"},
        }
    )

    result = plugin.run_cases(
        topology,
        case_ids=["brcm-fw-upgrade-dut-sta-forward"],
        runtime_overrides=overrides,
    )

    assert result["status"] == "ok"
    case_result = result["results"][0]
    assert case_result["verdict"] is True
    assert case_result["topology_name"] == "fake-topology"
    assert dut_transport.connected is False
    assert dut_transport.disconnected is True
    assert sta_transport.connected is False
    assert sta_transport.disconnected is True
    assert [command for command, _timeout in sta_transport.commands[:5]] == [
        "cd /tmp",
        f"bcm_flasher {forward_artifact.name}",
        "bcm_bootstate 1",
        "reboot",
        "echo ready",
    ]
    assert [command for command, _timeout in dut_transport.commands[:5]] == [
        "cd /tmp",
        f"bcm_flasher {forward_artifact.name}",
        "bcm_bootstate 1",
        "reboot",
        "echo ready",
    ]
    assert any(timeout == 900.0 for command, timeout in sta_transport.commands if command.startswith("bcm_flasher "))


def test_run_cases_returns_failed_status_on_runtime_error(monkeypatch: pytest.MonkeyPatch):
    plugin = _load_plugin()
    overrides = _runtime_overrides()
    overrides.update({"PLATFORM_PROFILE": "bgw720_prpl", "TOPOLOGY": "dut_plus_sta"})
    forward_artifact, _ = _runtime_artifact_paths()
    dut_transport = _RecordingTransport(
        {
            "cd /tmp": "/tmp",
            f"bcm_flasher {forward_artifact.name}": "Image flash complete",
            "bcm_bootstate 1": "The booted partition is marked to boot",
            "reboot": "rebooting",
            "echo ready": "ready",
            "cat /proc/version": "Linux version 5.15.176 #1 SMP PREEMPT Mon Apr 20 13:02:57 CST 2026",
            "bcm_bootstate": "$imageversion: 631BGW720-3001101323 $",
        }
    )
    sta_transport = _RecordingTransport(
        {
            "cd /tmp": "/tmp",
            f"bcm_flasher {forward_artifact.name}": "Image flash complete",
            "bcm_bootstate 1": "The booted partition is marked to boot",
            "reboot": "rebooting",
            "echo ready": "",
        }
    )

    def _fake_create_transport(kind: str, config: dict[str, object]):
        selector = config.get("selector")
        if selector == "COM0":
            return dut_transport
        if selector == "COM1":
            return sta_transport
        raise AssertionError(f"unexpected transport request: {kind} {config}")

    monkeypatch.setattr(f"{plugin.__class__.__module__}.create_transport", _fake_create_transport)
    monkeypatch.setattr(f"{plugin.__class__.__module__}.time.sleep", lambda delay: None)
    topology = _FakeTopology(
        {
            "DUT": {"transport": "serial", "selector": "COM0"},
            "STA": {"transport": "serial", "selector": "COM1"},
        }
    )

    result = plugin.run_cases(
        topology,
        case_ids=["brcm-fw-upgrade-dut-sta-forward"],
        runtime_overrides=overrides,
    )

    assert result["status"] == "failed"
    case_result = result["results"][0]
    assert case_result["verdict"] is False
    assert "ready probe failed after 3 attempts" in case_result["comment"]


def test_open_live_shells_disconnects_partial_transports_on_failure(monkeypatch: pytest.MonkeyPatch):
    plugin = _load_plugin()
    profile = plugin.platform_profiles["bgw720_prpl"]
    forward_artifact, _ = _runtime_artifact_paths()
    dut_transport = _RecordingTransport({})

    class _FailingTransport(_RecordingTransport):
        def connect(self, **kwargs) -> None:
            raise RuntimeError("serialwrap session not READY")

    sta_transport = _FailingTransport({})

    def _fake_create_transport(kind: str, config: dict[str, object]):
        selector = config.get("selector")
        if selector == "COM0":
            return dut_transport
        if selector == "COM1":
            return sta_transport
        raise AssertionError(f"unexpected transport request: {kind} {config}")

    monkeypatch.setattr(f"{plugin.__class__.__module__}.create_transport", _fake_create_transport)
    with pytest.raises(RuntimeError, match="failed to connect transport: serialwrap session not READY"):
        plugin._open_live_shells(
            topology=_FakeTopology(
                {
                    "DUT": {"transport": "serial", "selector": "COM0"},
                    "STA": {"transport": "serial", "selector": "COM1"},
                }
            ),
            case_topology=plugin.topologies["dut_plus_sta"],
            profile=profile,
            fw_name=forward_artifact.name,
        )

    assert dut_transport.disconnected is True


def test_run_cases_returns_failed_status_when_artifact_missing():
    plugin = _load_plugin()
    missing_artifact = Path(__file__).resolve().parent / "missing-live-artifact.pkgtb"
    result = plugin.run_cases(
        _FakeTopology(
            {
                "DUT": {"transport": "serial", "selector": "COM0"},
                "STA": {"transport": "serial", "selector": "COM1"},
            }
        ),
        case_ids=["brcm-fw-upgrade-dut-sta-forward"],
        runtime_overrides={
            "FW_FORWARD_PATH": str(missing_artifact),
            "FW_ROLLBACK_PATH": str(Path(__file__).resolve().parents[1] / "plugin.py"),
            "FW_NAME": missing_artifact.name,
            "EXPECTED_IMAGE_TAG": "631BGW720-3001101323",
            "EXPECTED_BUILD_TIME": "Apr 20 13:02:57 CST 2026",
            "PLATFORM_PROFILE": "bgw720_prpl",
            "TOPOLOGY": "dut_plus_sta",
        },
    )

    assert result["status"] == "failed"
    case_result = result["results"][0]
    assert case_result["verdict"] is False
    assert "active artifact path does not exist" in case_result["comment"]
