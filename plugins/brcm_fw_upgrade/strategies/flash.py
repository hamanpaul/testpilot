from __future__ import annotations

from typing import Any


def render_flash_command(template: str, *, fw_name: str) -> str:
    return template.replace("{{fw_name}}", fw_name)


def run_flash_sequence(
    shell: Any,
    *,
    commands: dict[str, str],
    fw_name: str,
    flash_marker: str,
    bootstate_marker: str = "marked to boot",
) -> list[dict[str, str]]:
    transcript: list[dict[str, str]] = []
    change_dir_command = commands.get("change_dir", "cd /tmp")
    flash_command = render_flash_command(commands["flash"], fw_name=fw_name)
    bootstate_command = commands.get("bootstate_set", "bcm_bootstate 1")
    reboot_command = commands["reboot"]
    expected_markers = {
        flash_command: flash_marker,
        bootstate_command: bootstate_marker,
    }
    for command in (
        change_dir_command,
        flash_command,
        bootstate_command,
        reboot_command,
    ):
        output = shell.run(command)
        transcript.append({"command": command, "output": output})
        expected_marker = expected_markers.get(command)
        if expected_marker and expected_marker not in output:
            raise RuntimeError(f"expected marker {expected_marker!r} not found after command: {command}")
    return transcript
