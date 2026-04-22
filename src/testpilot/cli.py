"""TestPilot CLI — command-line entry point."""

from __future__ import annotations

import json
import logging
import re
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


def _run_command_guidance() -> str:
    return (
        "Correct format:\n"
        "  testpilot run <plugin_name> [--case <case_id>] [--dut-fw-ver <fw_ver>]\n\n"
        "Example:\n"
        "  testpilot run wifi_llapi --case wifi-llapi-D004-kickstation --dut-fw-ver BGW720-B0-403\n\n"
        "Tip:\n"
        "  testpilot list-cases wifi_llapi"
    )


def _parse_runtime_override(raw: str) -> tuple[str, str]:
    key, sep, value = raw.partition("=")
    if not sep or not key:
        raise ValueError(f"invalid runtime override {raw!r}; expected KEY=VALUE")
    return key, value


def _extract_brcm_image_named_group(pattern: bytes, data: bytes, group: str) -> str:
    match = re.search(pattern, data)
    if not match:
        raise ValueError(f"pattern not found for group {group}: {pattern.decode('ascii', errors='ignore')}")
    value = match.group(group)
    return value.decode("ascii", errors="ignore").strip()


def _derive_brcm_image_metadata(image_path: str) -> dict[str, str]:
    data = Path(image_path).read_bytes()
    image_tag = _extract_brcm_image_named_group(
        rb"\$imageversion:\s*(?P<image_tag>[^$]+?)\s*\$",
        data,
        "image_tag",
    )
    build_time = _extract_brcm_image_named_group(
        rb"#1 SMP PREEMPT [A-Z][a-z]{2} (?P<build_time>[A-Z][a-z]{2} [ 0-9][0-9] [0-9:]{8} CST 20[0-9]{2})",
        data,
        "build_time",
    )
    return {
        "image_tag": image_tag,
        "build_time": re.sub(r"\s+", " ", build_time),
    }


class HelpfulRunCommand(click.Command):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except click.MissingParameter as exc:
            if getattr(exc.param, "name", None) == "plugin_name":
                raise click.UsageError(
                    "Missing required argument PLUGIN_NAME.\n\n"
                    f"{_run_command_guidance()}",
                    ctx=ctx,
                ) from exc
            raise


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
    ctx.obj["provider_notice"] = None

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
        ctx.obj["provider_notice"] = "azure_interactive"
    else:
        # Check if COPILOT_PROVIDER_* env vars are already set
        provider_config = resolve_provider_config()
        if provider_config:
            ctx.obj["provider_notice"] = "azure_env"
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


@main.command("run", cls=HelpfulRunCommand)
@click.argument("plugin_name")
@click.option("--case", "case_ids", multiple=True, help="Specific case IDs to run.")
@click.option(
    "--dut-fw-ver",
    default="DUT-FW-VER",
    show_default=True,
    help="DUT firmware version used in report filename.",
)
@click.pass_context
def run_tests(
    ctx: click.Context,
    plugin_name: str,
    case_ids: tuple[str, ...],
    dut_fw_ver: str,
) -> None:
    """Run tests for a plugin.

    Correct format:
      testpilot run PLUGIN_NAME [--case CASE_ID] [--dut-fw-ver FW_VER]

    Example:
      testpilot run wifi_llapi --case wifi-llapi-D004-kickstation --dut-fw-ver BGW720-B0-403
    """
    orch: Orchestrator = ctx.obj["orchestrator"]
    provider_config = ctx.obj.get("provider_config")
    provider_notice = str(ctx.obj.get("provider_notice") or "")
    if provider_config and provider_notice == "azure_interactive":
        console.print("[green]✓ Azure OpenAI authenticated.[/green]")
    elif provider_config and provider_notice == "azure_env":
        console.print("[green]✓ Azure OpenAI (from env vars).[/green]")
    result = orch.run(
        plugin_name,
        list(case_ids) if case_ids else None,
        dut_fw_ver=dut_fw_ver,
        provider_config=provider_config,
    )
    console.print(result)


@main.group("wifi-llapi")
def wifi_llapi_group() -> None:
    """wifi_llapi plugin helper commands."""


@main.group("brcm-fw-upgrade")
def brcm_fw_upgrade_group() -> None:
    """brcm_fw_upgrade plugin helper commands."""


@brcm_fw_upgrade_group.command("run")
@click.option("--case", "case_ids", multiple=True, help="Specific brcm_fw_upgrade case IDs to run.")
@click.option("--forward-image", required=True, type=click.Path(dir_okay=False))
@click.option(
    "--rollback-image",
    required=False,
    default=None,
    type=click.Path(dir_okay=False),
    help="Optional rollback image path. Defaults to the forward image when omitted.",
)
@click.option(
    "--fw-name",
    required=False,
    default=None,
    help="Firmware filename passed to the device flasher. Defaults to the forward image basename.",
)
@click.option(
    "--expected-image-tag",
    required=False,
    default=None,
    help="Expected post-flash image tag. Defaults to the tag extracted from the forward image.",
)
@click.option(
    "--expected-build-time",
    required=False,
    default=None,
    help="Expected post-flash build time. Defaults to the build time extracted from the forward image.",
)
@click.option("--platform-profile", required=False, default=None)
@click.option("--topology", "topology_name", required=False, default=None)
@click.option("--set", "extra_vars", multiple=True, help="Extra KEY=VALUE runtime overrides.")
@click.pass_context
def brcm_fw_upgrade_run(
    ctx: click.Context,
    case_ids: tuple[str, ...],
    forward_image: str,
    rollback_image: str | None,
    fw_name: str | None,
    expected_image_tag: str | None,
    expected_build_time: str | None,
    platform_profile: str | None,
    topology_name: str | None,
    extra_vars: tuple[str, ...],
) -> None:
    """Run brcm_fw_upgrade cases with explicit runtime overrides."""
    orch: Orchestrator = ctx.obj["orchestrator"]
    plugin = orch.loader.load("brcm_fw_upgrade")
    derived_metadata: dict[str, str] | None = None
    if expected_image_tag is None or expected_build_time is None:
        try:
            derived_metadata = _derive_brcm_image_metadata(forward_image)
        except (OSError, ValueError) as exc:
            raise click.ClickException(
                f"failed to derive forward image metadata from {forward_image!r}: {exc}"
            ) from exc
    runtime_overrides = {
        "FW_FORWARD_PATH": forward_image,
        "FW_ROLLBACK_PATH": rollback_image or forward_image,
        "FW_NAME": fw_name or Path(forward_image).name,
        "EXPECTED_IMAGE_TAG": expected_image_tag or derived_metadata["image_tag"],
        "EXPECTED_BUILD_TIME": expected_build_time or derived_metadata["build_time"],
    }
    if platform_profile:
        runtime_overrides["PLATFORM_PROFILE"] = platform_profile
    if topology_name:
        runtime_overrides["TOPOLOGY"] = topology_name
    try:
        for item in extra_vars:
            key, value = _parse_runtime_override(item)
            runtime_overrides[key] = value
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    try:
        result = plugin.run_cases(
            orch.config,
            case_ids=list(case_ids) if case_ids else None,
            runtime_overrides=runtime_overrides,
        )
    except (KeyError, ValueError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    console.print_json(data=result)
    if str(result.get("status", "")).lower() != "ok":
        raise SystemExit(1)


@wifi_llapi_group.command("baseline-qualify")
@click.option(
    "--band",
    "bands",
    multiple=True,
    type=click.Choice(["5g", "6g", "2.4g"], case_sensitive=False),
    help="Band to qualify. Repeatable. Defaults to all enabled sta_available_bands.",
)
@click.option(
    "--repeat-count",
    default=5,
    show_default=True,
    type=click.IntRange(min=1),
    help="Consecutive successful rounds required per band.",
)
@click.option(
    "--soak-minutes",
    default=15,
    show_default=True,
    type=click.IntRange(min=0),
    help="Soak time after each successful round.",
)
@click.pass_context
def baseline_qualify(
    ctx: click.Context,
    bands: tuple[str, ...],
    repeat_count: int,
    soak_minutes: int,
) -> None:
    """Qualify reusable DUT/STA baseline connectivity before full wifi_llapi runs."""
    orch: Orchestrator = ctx.obj["orchestrator"]
    plugin = orch.loader.load("wifi_llapi")
    qualify = getattr(plugin, "qualify_baseline", None)
    if not callable(qualify):
        raise click.ClickException("wifi_llapi plugin does not support baseline qualification")
    try:
        result = qualify(
            orch.config,
            bands=tuple(str(band).lower() for band in bands),
            repeat_count=repeat_count,
            soak_minutes=soak_minutes,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    console.print(result)
    if str(result.get("overall_status", "")).lower() != "stable":
        raise SystemExit(1)


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


@wifi_llapi_group.command("json-to-html")
@click.argument("json_report", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--out",
    default=None,
    type=click.Path(dir_okay=False),
    help="Output HTML path. Defaults to same stem as JSON report with .html extension.",
)
def json_to_html(json_report: str, out: str | None) -> None:
    """Generate an HTML report from an existing JSON report file."""
    from testpilot.reporting.html_reporter import HtmlReporter

    src = Path(json_report)
    payload = json.loads(src.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    meta = payload.get("meta", {})
    out_path = Path(out) if out else src.with_suffix(".html")
    reporter = HtmlReporter()
    result = reporter.generate(cases, meta, out_path)
    console.print(f"[green]✓[/green] HTML report: {result}")


if __name__ == "__main__":
    main()
