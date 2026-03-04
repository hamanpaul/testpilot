"""TestPilot CLI — command-line entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from testpilot import __version__
from testpilot.core.orchestrator import Orchestrator
from testpilot.reporting.wifi_llapi_excel import ensure_template_report

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
@click.pass_context
def main(ctx: click.Context, verbose: bool, root: str | None) -> None:
    """TestPilot — plugin-based test automation for embedded devices."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["root"] = Path(root) if root else Path(__file__).resolve().parents[2]
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
    help="Override source Excel path for wifi_llapi report/template.",
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
    result = orch.run(
        plugin_name,
        list(case_ids) if case_ids else None,
        dut_fw_ver=dut_fw_ver,
        report_source_xlsx=report_source_xlsx,
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


if __name__ == "__main__":
    main()
