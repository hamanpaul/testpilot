"""Tests for CLI entry points — verifies all commands are wired and produce expected output."""

from __future__ import annotations

from typing import Any

from click.testing import CliRunner

import testpilot.cli
from testpilot.cli import main


def _clear_provider_env(monkeypatch) -> None:
    for key in (
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "COPILOT_MODEL",
        "COPILOT_PROVIDER_AZURE_API_VERSION",
    ):
        monkeypatch.delenv(key, raising=False)


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


def test_run_without_dut_fw_ver_uses_default(monkeypatch):
    """run command accepts default --dut-fw-ver without crashing on missing transport."""
    _clear_provider_env(monkeypatch)
    calls: list[dict[str, Any]] = []

    class FakeOrchestrator:
        def __init__(self, project_root):
            self.project_root = project_root

        def run(self, plugin_name, case_ids, **kwargs):
            calls.append(
                {
                    "plugin_name": plugin_name,
                    "case_ids": case_ids,
                    "kwargs": kwargs,
                }
            )
            return {"status": "ok", "plugin": plugin_name, "case_ids": case_ids}

    monkeypatch.setattr(testpilot.cli, "Orchestrator", FakeOrchestrator)

    runner = CliRunner()
    result = runner.invoke(main, ["run", "wifi_llapi", "--case", "wifi-llapi-D004-kickstation"])

    assert result.exit_code == 0
    assert calls == [
        {
            "plugin_name": "wifi_llapi",
            "case_ids": ["wifi-llapi-D004-kickstation"],
            "kwargs": {
                "dut_fw_ver": "DUT-FW-VER",
                "report_source_xlsx": None,
                "provider_config": None,
            },
        }
    ]


def test_run_without_plugin_name_shows_correct_format_guidance():
    """run without plugin_name returns a targeted message with correct syntax."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--case", "wifi-llapi-D004-kickstation"])

    assert result.exit_code != 0
    assert "Missing required argument PLUGIN_NAME." in result.output
    assert "testpilot run <plugin_name> [--case <case_id>]" in result.output
    assert "testpilot run wifi_llapi --case wifi-llapi-D004-kickstation" in result.output
    assert "testpilot list-cases wifi_llapi" in result.output


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
    assert "baseline-qualify" in result.output
    assert "build-template-report" in result.output
    assert "audit-yaml-commands" in result.output


def test_baseline_qualify_invokes_wifi_llapi_plugin(monkeypatch):
    """wifi-llapi baseline-qualify dispatches to plugin.qualify_baseline."""
    _clear_provider_env(monkeypatch)
    calls: list[dict[str, Any]] = []

    class FakePlugin:
        def qualify_baseline(self, topology, *, bands, repeat_count, soak_minutes):
            calls.append(
                {
                    "topology": topology,
                    "bands": bands,
                    "repeat_count": repeat_count,
                    "soak_minutes": soak_minutes,
                }
            )
            return {
                "overall_status": "stable",
                "bands": [{"band": "5g", "stable": True}],
                "repeat_count": repeat_count,
                "soak_minutes": soak_minutes,
            }

    class FakeLoader:
        def __init__(self) -> None:
            self.plugin = FakePlugin()

        def load(self, plugin_name: str):
            assert plugin_name == "wifi_llapi"
            return self.plugin

    class FakeOrchestrator:
        def __init__(self, project_root):
            self.project_root = project_root
            self.loader = FakeLoader()
            self.config = {"name": "fake-topology"}

    monkeypatch.setattr(testpilot.cli, "Orchestrator", FakeOrchestrator)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "wifi-llapi",
            "baseline-qualify",
            "--band",
            "5g",
            "--repeat-count",
            "1",
            "--soak-minutes",
            "0",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "topology": {"name": "fake-topology"},
            "bands": ("5g",),
            "repeat_count": 1,
            "soak_minutes": 0,
        }
    ]
    assert "overall_status" in result.output
    assert "stable" in result.output


def test_help_text_for_run():
    """run --help shows options."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "PLUGIN_NAME" in result.output
    assert "--case" in result.output
    assert "--dut-fw-ver" in result.output
    assert "Correct format:" in result.output
    assert "testpilot run wifi_llapi --case wifi-llapi-D004-kickstation" in result.output
