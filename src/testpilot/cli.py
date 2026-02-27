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
@click.pass_context
def run_tests(ctx: click.Context, plugin_name: str, case_ids: tuple[str, ...]) -> None:
    """Run tests for a plugin (skeleton)."""
    orch: Orchestrator = ctx.obj["orchestrator"]
    result = orch.run(plugin_name, list(case_ids) if case_ids else None)
    console.print(result)


if __name__ == "__main__":
    main()
