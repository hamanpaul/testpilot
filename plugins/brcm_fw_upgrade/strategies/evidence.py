from __future__ import annotations


def slice_log_window(text: str, marker: str, *, before: int = 3, after: int = 3) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if marker in line:
            start = max(0, index - before)
            end = min(len(lines), index + after + 1)
            return "\n".join(lines[start:end])
    return ""
