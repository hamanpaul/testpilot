"""Pass 2 mechanical command extractor.

抽 workbook G/H prose 中可執行命令；不重新組合 / 改寫；citation 必須是原文 substring。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_TOKENS: frozenset[str] = frozenset({
    "ubus-cli", "wl", "hostapd_cli", "grep", "cat", "sed", "awk",
    "ip", "iw", "hostapd", "wpa_cli",
})

_TRIPLE_FENCE_RE = re.compile(r"```(?:\w+)?[ \t]*\n(.*?)```", re.DOTALL)
_SINGLE_FENCE_RE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER_RE = re.compile(r"<[A-Z_]+>")


@dataclass(frozen=True)
class ExtractedCommand:
    command: str
    citation: str   # original substring of source text
    rule: str       # which extraction rule fired


def _starts_with_allowed_token(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return False
    first = stripped.split(None, 1)[0]
    return first in ALLOWED_TOKENS


def _candidate_is_clean(cmd: str) -> bool:
    if _PLACEHOLDER_RE.search(cmd):
        return False
    return _starts_with_allowed_token(cmd)


def _span_within_fences(start: int, end: int, fence_spans: list[tuple[int, int]]) -> bool:
    return any(fence_start <= start and end <= fence_end for fence_start, fence_end in fence_spans)


def extract_commands(text: str) -> list[ExtractedCommand]:
    """Mechanical extract — return list of candidate commands with citations.

    Order of rules (first match wins per substring of source):
    1. Triple-fenced code blocks
    2. Single-backtick inline
    3. Bare lines starting with allowed token
    """
    if not text:
        return []
    out: list[ExtractedCommand] = []
    fence_matches = list(_TRIPLE_FENCE_RE.finditer(text))
    fence_spans = [m.span() for m in fence_matches]

    # Rule 1: triple-fenced blocks
    for m in fence_matches:
        block = m.group(1)
        for line in block.splitlines():
            line = line.rstrip()
            if _candidate_is_clean(line):
                out.append(ExtractedCommand(
                    command=line.strip(),
                    citation=m.group(0),
                    rule="triple_fence",
                ))

    # Rule 2: single-backtick inline
    for m in _SINGLE_FENCE_RE.finditer(text):
        if _span_within_fences(m.start(), m.end(), fence_spans):
            continue
        cmd = m.group(1).strip()
        if _candidate_is_clean(cmd):
            out.append(ExtractedCommand(
                command=cmd,
                citation=m.group(0),
                rule="single_backtick",
            ))

    # Rule 3: bare-line allowed token
    offset = 0
    for line in text.splitlines(keepends=True):
        raw_line = line.rstrip("\r\n")
        line_end = offset + len(raw_line)
        stripped = raw_line.strip()
        if _span_within_fences(offset, line_end, fence_spans):
            offset += len(line)
            continue
        if not stripped:
            offset += len(line)
            continue
        if _candidate_is_clean(stripped):
            out.append(ExtractedCommand(
                command=stripped,
                citation=raw_line,
                rule="bare_line",
            ))
        offset += len(line)

    # deduplicate by (command, rule)
    seen: set[tuple[str, str]] = set()
    deduped: list[ExtractedCommand] = []
    for c in out:
        key = (c.command, c.rule)
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped
