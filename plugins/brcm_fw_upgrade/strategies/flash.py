from __future__ import annotations

from typing import Any


def run_flash_sequence(shell: Any, *, fw_name: str, flash_marker: str) -> list[dict[str, str]]:
    transcript: list[dict[str, str]] = []
    expected_markers = {
        f"bcm_flasher {fw_name}": flash_marker,
        "bcm_bootstate 1": "marked to boot",
        "reboot": "reboot",
    }
    for command in (
        "cd /tmp",
        f"bcm_flasher {fw_name}",
        "bcm_bootstate 1",
        "reboot",
    ):
        output = shell.run(command)
        transcript.append({"command": command, "output": output})
        expected_marker = expected_markers.get(command)
        if expected_marker and expected_marker not in output:
            raise RuntimeError(f"expected marker {expected_marker!r} not found after command: {command}")
    return transcript
