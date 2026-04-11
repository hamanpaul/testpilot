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
    plugin._resolve_runtime_text = MagicMock(side_effect=lambda _case, _topo, cmd: cmd)
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

    def test_list_command_returns_resolved_lines_without_fallback(self, resolver: CommandResolver) -> None:
        case: dict[str, Any] = {"id": "D001"}
        step: dict[str, Any] = {"id": "s1", "command": ["echo one", "echo two"]}
        commands, reason = resolver.resolve(case, step, topology=None)
        assert commands == ["echo one", "echo two"]
        assert reason == ""

    def test_driver_capture_shell_step_does_not_use_synthesized_readback(
        self, mock_plugin: MagicMock
    ) -> None:
        mock_plugin._looks_shell_command.side_effect = (
            lambda command: str(command).strip().startswith(("wl ", "iw ", "cat ", "echo "))
        )
        mock_plugin._synthesize_readback_command.return_value = (
            'ubus-cli "WiFi.AccessPoint.*.?" | grep -E "AssociatedDevice\\.[0-9]+\\.AssocMac5g"'
        )
        resolver = CommandResolver(mock_plugin)

        case: dict[str, Any] = {
            "id": "wifi-llapi-D009-associationtime",
            "source": {
                "object": "WiFi.AccessPoint.{i}.AssociatedDevice.{i}.",
                "api": "AssociationTime",
            },
            "pass_criteria": [
                {
                    "field": "assoc_5g.AssocMac5g",
                    "operator": "regex",
                    "value": "(?i)^([0-9a-f]{2}:){5}[0-9a-f]{2}$",
                }
            ],
        }
        step: dict[str, Any] = {
            "id": "step2_5g_assoc",
            "capture": "assoc_5g",
            "command": (
                "wl -i wl0 assoclist | tr 'A-F' 'a-f' | "
                "sed -n 's/^assoclist \\([^ ]*\\).*$/AssocMac5g=\\1/p'"
            ),
        }

        commands, reason = resolver.resolve(case, step, topology=None)

        assert commands == [step["command"]]
        assert reason == ""


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

    def test_retries_scan_timeout_with_reduced_capture(self, resolver: CommandResolver) -> None:
        result = resolver.handle_runtime_fallback(
            case={"id": "D277"},
            step={"id": "step_5g_scan", "command": 'ubus-cli "WiFi.Radio.1.getScanResults()"'},
            topology=None,
            result={
                "returncode": 124,
                "stdout": "",
                "stderr": "serialwrap cmd status timeout: command did not finish",
            },
            current_commands=['ubus-cli "WiFi.Radio.1.getScanResults()"'],
            current_fallback_reason="",
        )
        assert result is not None
        commands, reason = result
        assert reason == "scan_first_result_capture"
        assert commands == [
            "ubus-cli WiFi.Radio.1.getScanResults() | head -60 | sed -n '/BSSID = /,/^        },/p'"
        ]

    def test_does_not_reduce_piped_scan_command_on_timeout(self, resolver: CommandResolver) -> None:
        result = resolver.handle_runtime_fallback(
            case={"id": "D277"},
            step={
                "id": "step_5g_scan",
                "command": 'ubus-cli "WiFi.Radio.1.getScanResults()" | head -40',
            },
            topology=None,
            result={
                "returncode": 124,
                "stdout": "",
                "stderr": "serialwrap cmd status timeout: command did not finish",
            },
            current_commands=['ubus-cli "WiFi.Radio.1.getScanResults()" | head -40'],
            current_fallback_reason="",
        )
        assert result is None


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


class TestSplitSafeShellCommands:
    def test_preserves_multiline_printf_literal(self, resolver: CommandResolver) -> None:
        command = (
            "printf 'ctrl_interface=/var/run/wpa_supplicant\n"
            "update_config=1\n"
            "network={\n"
            "ssid=\"TestPilot_BTM\"\n"
            "key_mgmt=SAE\n"
            "}\n"
            "' > /tmp/wpa_wl0.conf"
        )

        assert resolver.split_safe_shell_commands(command) == [command]


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


class TestIsTimeoutResult:
    def test_return_code_124(self) -> None:
        assert CommandResolver.is_timeout_result(
            {"returncode": 124, "stdout": "", "stderr": ""}
        ) is True

    def test_serialwrap_timeout_stderr(self) -> None:
        assert CommandResolver.is_timeout_result(
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "serialwrap cmd status timeout: command did not finish",
            }
        ) is True

    def test_generic_failure_not_timeout(self) -> None:
        assert CommandResolver.is_timeout_result(
            {"returncode": 1, "stdout": "", "stderr": "some other failure"}
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
