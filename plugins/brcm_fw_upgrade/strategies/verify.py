from __future__ import annotations

import re


def extract_named_group(pattern: str, text: str, group: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"pattern not found for group {group}: {pattern}")
    return str(match.group(group))
