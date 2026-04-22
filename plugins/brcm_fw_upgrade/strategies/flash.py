from __future__ import annotations

import time
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
    reboot_settle_seconds = float(commands.get("reboot_settle_seconds", 0))
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
        try:
            output = shell.run(command)
        except RuntimeError as exc:
            if command == bootstate_command and "PROMPT_TIMEOUT" in str(exc):
                transcript.append(
                    {
                        "command": command,
                        "output": str(exc),
                        "tolerated_error": "PROMPT_TIMEOUT",
                    }
                )
                continue
            raise
        transcript.append({"command": command, "output": output})
        expected_marker = expected_markers.get(command)
        if expected_marker and expected_marker not in output:
            raise RuntimeError(f"expected marker {expected_marker!r} not found after command: {command}")
        if command == reboot_command and reboot_settle_seconds > 0:
            time.sleep(reboot_settle_seconds)
            transcript.append(
                {
                    "command": "__post_reboot_settle__",
                    "output": f"slept {reboot_settle_seconds:.1f}s",
                }
            )
    return transcript
