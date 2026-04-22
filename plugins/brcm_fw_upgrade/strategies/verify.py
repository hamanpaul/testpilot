from __future__ import annotations

import re


def extract_named_group(pattern: str, text: str, group: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        normalized = " ".join(text.split())
        match = re.search(pattern, normalized, re.MULTILINE)
    if not match:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"pattern not found for group {group}: {pattern}")
    return str(match.group(group))


def extract_booted_image_tag(text: str, *, fallback_pattern: str | None = None) -> str:
    booted_match = re.search(
        r"^B>.*image tag\s*:\s*\$imageversion:\s*(?P<image_tag>[^$]+?)\s*\$",
        text,
        re.MULTILINE,
    )
    if booted_match:
        return str(booted_match.group("image_tag")).strip()
    if fallback_pattern:
        return extract_named_group(fallback_pattern, text, "image_tag").strip()
    raise ValueError("booted image tag not found")
