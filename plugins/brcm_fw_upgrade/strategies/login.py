from __future__ import annotations

from typing import Any


def build_login_commands(profile: dict[str, Any]) -> list[str]:
    strategy = str(profile.get("login_strategy", "none")).strip()
    if strategy == "none":
        return []
    if strategy == "serialwrap_profile_login":
        return list(profile.get("pre_login_commands") or [])
    raise ValueError(f"unsupported login_strategy: {strategy}")
