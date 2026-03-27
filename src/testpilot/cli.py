"""TestPilot CLI — command-line entry point."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from testpilot import __version__
from testpilot.core.azure_auth import (
    AzureAuthError,
    resolve_provider_config,
    setup_azure_auth,
)
from testpilot.core.orchestrator import Orchestrator
from testpilot.reporting.wifi_llapi_excel import ensure_template_report
from testpilot.yaml_command_audit import (
    DEFAULT_AUDIT_FIELDS,
    build_yaml_command_audit_report,
    rewrite_yaml_chained_commands,
    write_yaml_command_audit_report,
)

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.version_option(__version__, prog_name="testpilot")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Project root directory.",
)
@click.option(
    "--azure",
    is_flag=True,
    default=False,
    help="Use Azure OpenAI API. Prompts for endpoint, key, and model interactively.",
)
@click.pass_context
def main(ctx: click.Context, verbose: bool, root: str | None, azure: bool) -> None:
    """TestPilot — plugin-based test automation for embedded devices."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["root"] = Path(root) if root else Path(__file__).resolve().parents[2]

    # --- Authentication: Azure BYOK → GitHub OAuth fallback ---
    provider_config: dict | None = None
    if azure:
        provider_config = setup_azure_auth()
        if provider_config is None:
            console.print(
                "[bold red]Azure authentication failed.[/bold red] "
                "Cannot proceed. Please check your credentials and network.",
            )
            raise SystemExit(1)
        console.print("[green]✓ Azure OpenAI authenticated.[/green]")
    else:
        # Check if COPILOT_PROVIDER_* env vars are already set
        provider_config = resolve_provider_config()
        if provider_config:
            console.print("[green]✓ Azure OpenAI (from env vars).[/green]")
        # else: fall through to GitHub OAuth (handled by Copilot SDK)

    ctx.obj["provider_config"] = provider_config
    ctx.obj["orchestrator"] = Orchestrator(project_root=ctx.obj["root"])


@main.command("list-plugins")
@click.pass_context
def list_plugins(ctx: click.Context) -> None:
    """List available test plugins."""
    orch: Orchestrator = ctx.obj["orchestrator"]
    names = orch.discover_plugins()
    if not names:
        console.print("[yellow]No plugins found.[/yellow]")
        return
    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    for name in names:
        try:
            plugin = orch.loader.load(name)
            cases = plugin.discover_cases()
            table.add_row(name, f"v{plugin.version} ({len(cases)} cases)")
        except Exception as e:
            table.add_row(name, f"[red]error: {e}[/red]")
    console.print(table)


@main.command("list-cases")
@click.argument("plugin_name")
@click.pass_context
def list_cases(ctx: click.Context, plugin_name: str) -> None:
    """List test cases for a plugin."""
    orch: Orchestrator = ctx.obj["orchestrator"]
    cases = orch.list_cases(plugin_name)
    if not cases:
        console.print(f"[yellow]No cases found for plugin '{plugin_name}'.[/yellow]")
        return
    table = Table(title=f"Cases: {plugin_name}")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Steps", justify="right")
    for case in cases:
        table.add_row(
            case.get("id", "?"),
            case.get("name", "?"),
            str(len(case.get("steps", []))),
        )
    console.print(table)


@main.command("run")
@click.argument("plugin_name")
@click.option("--case", "case_ids", multiple=True, help="Specific case IDs to run.")
@click.option(
    "--dut-fw-ver",
    default="DUT-FW-VER",
    show_default=True,
    help="DUT firmware version used in report filename.",
)
@click.option(
    "--report-source-xlsx",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Optional source Excel path used to (re)build the wifi_llapi template before running.",
)
@click.pass_context
def run_tests(
    ctx: click.Context,
    plugin_name: str,
    case_ids: tuple[str, ...],
    dut_fw_ver: str,
    report_source_xlsx: str | None,
) -> None:
    """Run tests for a plugin (skeleton)."""
    orch: Orchestrator = ctx.obj["orchestrator"]
    provider_config = ctx.obj.get("provider_config")
    result = orch.run(
        plugin_name,
        list(case_ids) if case_ids else None,
        dut_fw_ver=dut_fw_ver,
        report_source_xlsx=report_source_xlsx,
        provider_config=provider_config,
    )
    console.print(result)


@main.group("wifi-llapi")
def wifi_llapi_group() -> None:
    """wifi_llapi plugin helper commands."""


@wifi_llapi_group.command("build-template-report")
@click.option(
    "--source-xlsx",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Source xlsx file containing Wifi_LLAPI sheet.",
)
@click.option(
    "--sheet",
    default="Wifi_LLAPI",
    show_default=True,
    help="Sheet name to extract as report template.",
)
@click.option(
    "--out",
    "out_template",
    default=None,
    type=click.Path(dir_okay=False),
    help="Output template path. Defaults to plugins/wifi_llapi/reports/templates/wifi_llapi_template.xlsx",
)
@click.pass_context
def build_template_report(
    ctx: click.Context,
    source_xlsx: str,
    sheet: str,
    out_template: str | None,
) -> None:
    """Extract Wifi_LLAPI sheet and clear result/test command columns for template."""
    root: Path = ctx.obj["root"]
    default_out = root / "plugins" / "wifi_llapi" / "reports" / "templates" / "wifi_llapi_template.xlsx"
    out_path = Path(out_template) if out_template else default_out
    manifest_path = out_path.with_suffix(".manifest.json")

    result = ensure_template_report(
        source_xlsx=source_xlsx,
        template_path=out_path,
        manifest_path=manifest_path,
        sheet_name=sheet,
    )
    console.print(
        {
            "status": "ok",
            "template_path": str(result.template_path),
            "sheet": result.sheet_name,
            "total_case_rows": result.total_case_rows,
            "manifest": str(manifest_path),
        }
    )


@wifi_llapi_group.command("audit-yaml-commands")
@click.option(
    "--cases-dir",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Cases directory to scan. Defaults to plugins/wifi_llapi/cases under --root.",
)
@click.option(
    "--field",
    "fields",
    multiple=True,
    help="Field name to audit. Repeatable. Defaults to command/verification_command/hlapi_command/setup_steps/sta_env_setup.",
)
@click.option(
    "--limit",
    default=50,
    show_default=True,
    type=click.IntRange(min=1),
    help="Maximum matches printed to stdout. Full report can be written with --out.",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(dir_okay=False),
    help="Optional JSON output path for the full dry-run report.",
)
@click.pass_context
def audit_yaml_commands(
    ctx: click.Context,
    cases_dir: str | None,
    fields: tuple[str, ...],
    limit: int,
    out: str | None,
) -> None:
    """Scan wifi_llapi YAML for chained shell commands and suggest split commands."""
    root: Path = ctx.obj["root"]
    target_dir = Path(cases_dir) if cases_dir else root / "plugins" / "wifi_llapi" / "cases"
    target_fields = tuple(fields) if fields else DEFAULT_AUDIT_FIELDS

    report = build_yaml_command_audit_report(
        target_dir,
        target_fields=target_fields,
    )
    if out:
        write_yaml_command_audit_report(out, report)

    matches = list(report.get("matches", []))
    preview = dict(report)
    preview["matches_returned"] = min(limit, len(matches))
    preview["truncated"] = len(matches) > limit
    preview["matches"] = matches[:limit]
    if out:
        preview["report_path"] = str(Path(out))

    click.echo(json.dumps(preview, indent=2, ensure_ascii=False))


@wifi_llapi_group.command("rewrite-yaml-commands")
@click.option(
    "--cases-dir",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Cases directory to rewrite. Defaults to plugins/wifi_llapi/cases under --root.",
)
@click.option(
    "--field",
    "fields",
    multiple=True,
    help="Field name to rewrite. Repeatable. Defaults to command/verification_command/hlapi_command/setup_steps/sta_env_setup.",
)
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    help="Write rewritable chained commands back to YAML files. Without this flag, command runs in dry-run mode.",
)
@click.option(
    "--limit",
    default=20,
    show_default=True,
    type=click.IntRange(min=1),
    help="Maximum rewritten/blocked file records printed to stdout.",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(dir_okay=False),
    help="Optional JSON output path for the full rewrite report.",
)
@click.pass_context
def rewrite_yaml_commands(
    ctx: click.Context,
    cases_dir: str | None,
    fields: tuple[str, ...],
    apply_changes: bool,
    limit: int,
    out: str | None,
) -> None:
    """Rewrite safe chained shell commands into single-command YAML lines."""
    root: Path = ctx.obj["root"]
    target_dir = Path(cases_dir) if cases_dir else root / "plugins" / "wifi_llapi" / "cases"
    target_fields = tuple(fields) if fields else DEFAULT_AUDIT_FIELDS

    report = rewrite_yaml_chained_commands(
        target_dir,
        target_fields=target_fields,
        apply_changes=apply_changes,
    )
    if out:
        write_yaml_command_audit_report(out, report)

    preview = dict(report)
    rewritten_files = list(report.get("rewritten_files", []))
    blocked_matches = list(report.get("blocked_matches", []))
    preview["rewritten_files_returned"] = min(limit, len(rewritten_files))
    preview["blocked_matches_returned"] = min(limit, len(blocked_matches))
    preview["rewritten_files"] = rewritten_files[:limit]
    preview["blocked_matches"] = blocked_matches[:limit]
    preview["truncated"] = len(rewritten_files) > limit or len(blocked_matches) > limit
    if out:
        preview["report_path"] = str(Path(out))

    click.echo(json.dumps(preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
