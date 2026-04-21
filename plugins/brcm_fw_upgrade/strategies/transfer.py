from __future__ import annotations

from typing import Any


def select_transfer_method(capabilities: dict[str, Any], *, sta_present: bool) -> str:
    if capabilities.get("has_scp"):
        return "host_to_dut_scp"
    if sta_present:
        return "dut_to_sta_relay"
    return "serial_fallback"


def render_md5_command(template: str, *, path: str) -> str:
    return template.replace("{{path}}", path)
