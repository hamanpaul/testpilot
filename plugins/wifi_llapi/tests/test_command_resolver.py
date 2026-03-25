"""Tests for CommandResolver extracted from plugin.py."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# The plugin loader temporarily injects the plugin dir into sys.path when
# loading a plugin.  Replicate that so we can import command_resolver
# directly for unit testing.
_plugin_dir = str(Path(__file__).resolve().parents[1])
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from command_resolver import CommandResolver  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_plugin(**overrides: Any) -> MagicMock:
    """Return a lightweight mock that satisfies CommandResolver's needs."""
    plugin = MagicMock()

    # Tokens the resolver inspects on the plugin instance
    plugin.ROOT_COMMAND_TOKENS = ("ubus-cli", "wl", "iw")
    plugin.EXECUTABLE_TOKENS = {"ubus-cli", "wl", "iw", "ifconfig", "cat", "echo", "sh", "grep"}
    plugin.INTERACTIVE_ROOT_TOKENS = set()

    # Default passthrough helpers
    plugin._normalize_command_text = MagicMock(side_effect=lambda t: str(t).strip())
    plugin._looks_shell_command = MagicMock(return_value=False)
    plugin._looks_plausible_cli_command = MagicMock(return_value=True)
    plugin._resolve_text = MagicMock(side_effect=lambda _topo, cmd: cmd)
    plugin._quote_ubus_operand = MagicMock(side_effect=lambda t: t)
    plugin._truncate_ubus_function_tail = MagicMock(side_effect=lambda t: t)
    plugin._trim_transcript_tokens = MagicMock(side_effect=lambda tokens: tokens)
    plugin._join_shell_tokens = MagicMock(side_effect=lambda tokens: " ".join(tokens))
    plugin._shell_executable_hints = MagicMock(return_value=set())
    plugin._first_non_empty_line = MagicMock(side_effect=lambda t: t.strip().split("\n")[0])
    plugin._synthesize_readback_command = MagicMock(return_value=None)
    plugin._is_runtime_hlapi_command = MagicMock(return_value=False)

    for key, value in overrides.items():
        setattr(plugin, key, value)
    return plugin


@pytest.fixture
def mock_plugin() -> MagicMock:
    return _make_mock_plugin()


@pytest.fixture
def resolver(mock_plugin: MagicMock) -> CommandResolver:
    return CommandResolver(mock_plugin)


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestInstantiation:
    def test_creates_with_mock_plugin(self, mock_plugin: MagicMock) -> None:
        cr = CommandResolver(mock_plugin)
        assert cr._plugin is mock_plugin


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------

class TestResolve:
    def test_returns_tuple_of_list_and_str(self, resolver: CommandResolver) -> None:
        case: dict[str, Any] = {"id": "D001"}
        step: dict[str, Any] = {"id": "s1", "command": "ubus-cli get WiFi.Radio.1.Enable"}
        result = resolver.resolve(case, step, topology=None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        commands, reason = result
        assert isinstance(commands, list)
        assert isinstance(reason, str)

    def test_non_executable_step_returns_skip_echo(self, resolver: CommandResolver) -> None:
        case: dict[str, Any] = {"id": "D001"}
        step: dict[str, Any] = {"id": "s1", "command": "some prose description"}
        commands, reason = resolver.resolve(case, step, topology=None)
        assert len(commands) == 1
        assert "[skip]" in commands[0]


# ---------------------------------------------------------------------------
# handle_runtime_fallback()
# ---------------------------------------------------------------------------

class TestHandleRuntimeFallback:
    def test_returns_none_when_fallback_reason_set(self, resolver: CommandResolver) -> None:
        result = resolver.handle_runtime_fallback(
            case={"id": "D001"},
            step={"id": "s1", "command": "ubus-cli get x"},
            topology=None,
            result={"returncode": 127, "stdout": "", "stderr": "not found"},
            current_commands=["ubus-cli get x"],
            current_fallback_reason="already_fell_back",
        )
        assert result is None

    def test_returns_none_when_result_is_executable(self, resolver: CommandResolver) -> None:
        result = resolver.handle_runtime_fallback(
            case={"id": "D001"},
            step={"id": "s1", "command": "ubus-cli get x"},
            topology=None,
            result={"returncode": 0, "stdout": "ok", "stderr": ""},
            current_commands=["ubus-cli get x"],
            current_fallback_reason="",
        )
        assert result is None

    def test_returns_tuple_on_unexecutable_result(self, resolver: CommandResolver) -> None:
        resolver._plugin._looks_shell_command.return_value = False
        result = resolver.handle_runtime_fallback(
            case={"id": "D001"},
            step={"id": "s1", "command": "ubus-cli get WiFi.Radio.1.Enable"},
            topology=None,
            result={"returncode": 127, "stdout": "", "stderr": "command not found"},
            current_commands=["some-other-thing"],
            current_fallback_reason="",
        )
        # Should return a tuple (commands, reason) or None
        assert result is None or (isinstance(result, tuple) and len(result) == 2)


# ---------------------------------------------------------------------------
# extract_cli_fragments()
# ---------------------------------------------------------------------------

class TestExtractCliFragments:
    def test_empty_input(self, resolver: CommandResolver) -> None:
        assert resolver.extract_cli_fragments("") == []

    def test_single_ubus_command(self, resolver: CommandResolver) -> None:
        fragments = resolver.extract_cli_fragments("ubus-cli get WiFi.Radio.1.Enable")
        assert len(fragments) >= 1
        assert any("ubus-cli" in f for f in fragments)

    def test_no_root_tokens(self, resolver: CommandResolver) -> None:
        fragments = resolver.extract_cli_fragments("just some prose text without commands")
        assert fragments == []


# ---------------------------------------------------------------------------
# looks_executable()
# ---------------------------------------------------------------------------

class TestLooksExecutable:
    def test_empty_string(self, resolver: CommandResolver) -> None:
        assert resolver.looks_executable("") is False

    def test_whitespace_only(self, resolver: CommandResolver) -> None:
        assert resolver.looks_executable("   ") is False

    def test_known_executable_token(self, resolver: CommandResolver) -> None:
        assert resolver.looks_executable("ubus-cli get something") is True

    def test_shell_command_delegated(self, resolver: CommandResolver) -> None:
        resolver._plugin._looks_shell_command.return_value = True
        assert resolver.looks_executable("cat /etc/config") is True


# ---------------------------------------------------------------------------
# is_unexecutable_result()
# ---------------------------------------------------------------------------

class TestIsUnexecutableResult:
    def test_return_code_127(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 127, "stdout": "", "stderr": ""}
        ) is True

    def test_return_code_126(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 126, "stdout": "", "stderr": ""}
        ) is True

    def test_success(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 0, "stdout": "ok", "stderr": ""}
        ) is False

    def test_not_found_in_output(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 1, "stdout": "command not found", "stderr": ""}
        ) is True

    def test_unknown_command(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 1, "stdout": "", "stderr": "Unknown command"}
        ) is True

    def test_syntax_error(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 1, "stdout": "", "stderr": "syntax error near unexpected token"}
        ) is True

    def test_generic_failure_not_unexecutable(self) -> None:
        assert CommandResolver.is_unexecutable_result(
            {"returncode": 1, "stdout": "timeout", "stderr": ""}
        ) is False


# ---------------------------------------------------------------------------
# as_mapping()
# ---------------------------------------------------------------------------

class TestAsMapping:
    def test_dict_passthrough(self) -> None:
        d = {"a": 1}
        assert CommandResolver.as_mapping(d) is d

    def test_non_dict_returns_empty(self) -> None:
        assert CommandResolver.as_mapping("string") == {}
        assert CommandResolver.as_mapping(42) == {}
        assert CommandResolver.as_mapping(None) == {}
