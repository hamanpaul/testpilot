"""Tests for CLI entry points — verifies all commands are wired and produce expected output."""

from __future__ import annotations

from click.testing import CliRunner

from testpilot.cli import main


def test_version_flag():
    """--version prints version string."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "testpilot" in result.output.lower()


def test_list_plugins_shows_wifi_llapi():
    """list-plugins discovers wifi_llapi."""
    runner = CliRunner()
    result = runner.invoke(main, ["list-plugins"])
    assert result.exit_code == 0
    assert "wifi_llapi" in result.output


def test_list_cases_for_wifi_llapi():
    """list-cases wifi_llapi returns non-empty list."""
    runner = CliRunner()
    result = runner.invoke(main, ["list-cases", "wifi_llapi"])
    assert result.exit_code == 0
    # Should contain at least one D### case ID
    assert "D0" in result.output or "D1" in result.output


def test_list_cases_unknown_plugin():
    """list-cases with unknown plugin name raises error."""
    runner = CliRunner()
    result = runner.invoke(main, ["list-cases", "nonexistent_plugin"])
    assert result.exit_code != 0


def test_run_without_dut_fw_ver_uses_default():
    """run command accepts default --dut-fw-ver without crashing on missing transport."""
    runner = CliRunner()
    # This will fail because no transport is available, but should not crash on CLI parsing
    result = runner.invoke(main, ["run", "wifi_llapi", "--case", "wifi-llapi-D004-kickstation"])
    # Either exits 0 (completed) or non-zero (transport error), but should not have UsageError
    assert "Usage:" not in result.output or result.exit_code != 2


def test_help_text_for_main():
    """Main --help shows all subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "list-plugins" in result.output
    assert "list-cases" in result.output
    assert "run" in result.output
    assert "wifi-llapi" in result.output


def test_help_text_for_wifi_llapi_group():
    """wifi-llapi --help shows subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["wifi-llapi", "--help"])
    assert result.exit_code == 0
    assert "build-template-report" in result.output
    assert "audit-yaml-commands" in result.output


def test_help_text_for_run():
    """run --help shows options."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "--case" in result.output
    assert "--dut-fw-ver" in result.output
