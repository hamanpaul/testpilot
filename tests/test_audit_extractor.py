"""Pass 2 mechanical command extractor tests."""

from __future__ import annotations

import pytest

from testpilot.audit.extractor import (
    ALLOWED_TOKENS,
    ExtractedCommand,
    extract_commands,
)


def test_allowed_tokens_set():
    assert "ubus-cli" in ALLOWED_TOKENS
    assert "wl" in ALLOWED_TOKENS
    assert "grep" in ALLOWED_TOKENS
    assert "rm" not in ALLOWED_TOKENS


def test_line_start_token_capture():
    text = """Read radio noise:
ubus-cli "WiFi.Radio.1.Noise?"
expected: numeric"""
    cmds = extract_commands(text)
    assert any(c.command.startswith("ubus-cli") for c in cmds)
    for c in cmds:
        assert c.citation in text


def test_fenced_triple_backtick():
    text = """Procedure:
```bash
wl -i wl0 sr_config srg_obsscolorbmp
```
end"""
    cmds = extract_commands(text)
    assert any("wl -i wl0 sr_config srg_obsscolorbmp" in c.command for c in cmds)


def test_fenced_triple_backtick_allows_trailing_whitespace_in_opener():
    text = """Procedure:
```bash \t
wl -i wl0 status
```
end"""
    cmds = extract_commands(text)
    assert any(c.command == "wl -i wl0 status" for c in cmds)


def test_inline_single_backtick():
    text = "Run `grep -c he_spr_srg /tmp/wl0_hapd.conf` and check output"
    cmds = extract_commands(text)
    assert any("grep -c he_spr_srg" in c.command for c in cmds)


def test_chinese_prose_yields_nothing():
    text = "設定 SRG bitmap 並驗證 driver 是否拉起。"
    cmds = extract_commands(text)
    assert cmds == []


def test_placeholder_command_rejected():
    text = "ubus-cli <YOUR_OBJECT>.Foo?"
    cmds = extract_commands(text)
    assert cmds == []


def test_disallowed_token_rejected():
    text = """Try this:
rm -rf /tmp/foo
nc -l 80
"""
    cmds = extract_commands(text)
    assert cmds == []


def test_empty_text_yields_nothing():
    assert extract_commands("") == []


def test_citation_is_original_substring_triple_fence():
    text = "```\nwl -i wl0 status\n```"
    cmds = extract_commands(text)
    assert cmds
    for c in cmds:
        assert c.citation in text


def test_citation_is_original_substring_single_backtick():
    text = "Check `wl -i wl1 status` and report"
    cmds = extract_commands(text)
    assert cmds
    for c in cmds:
        assert c.citation in text


def test_deduplication():
    text = """```bash
grep foo /etc/config
grep foo /etc/config
```"""
    cmds = extract_commands(text)
    assert len(cmds) == 1
    assert cmds[0].command == "grep foo /etc/config"
    assert cmds[0].rule == "triple_fence"


def test_rule_priority_triple_fence_over_bare_line():
    """A command inside a fence block must not also appear as bare_line."""
    text = "```bash\nwl status\n```"
    cmds = extract_commands(text)
    fence_cmds = [c for c in cmds if c.rule == "triple_fence"]
    bare_cmds = [c for c in cmds if c.rule == "bare_line"]
    assert len(fence_cmds) == 1
    assert len(bare_cmds) == 0


def test_bare_line_outside_fence_is_kept_even_if_command_matches():
    text = "```bash\nwl status\n```\nwl status"
    cmds = extract_commands(text)

    assert [c.rule for c in cmds] == ["triple_fence", "bare_line"]


def test_fence_block_with_multiple_commands():
    text = "```bash\nwl status\nwl scan\n```"
    cmds = extract_commands(text)

    assert len(cmds) == 2
    assert {c.command for c in cmds} == {"wl status", "wl scan"}
    assert all(c.rule == "triple_fence" for c in cmds)
    assert all(c.citation == text for c in cmds)


def test_single_backtick_inside_triple_fence_is_not_extracted():
    text = "```bash\n`grep foo /etc/config`\n```"
    cmds = extract_commands(text)

    assert cmds == []


def test_single_backtick_and_separate_bare_line_are_both_kept():
    text = "Run `wl status` to inspect\nwl status"
    cmds = extract_commands(text)

    assert [c.rule for c in cmds] == ["single_backtick", "bare_line"]
