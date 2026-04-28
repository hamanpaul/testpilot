"""Audit CLI commands."""

from __future__ import annotations
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

import click
from openpyxl.utils.exceptions import InvalidFileException

from testpilot.audit import bucket as bucket_mod
from testpilot.audit import manifest
from testpilot.audit.workbook_index import build_index


def _resolve_workbook_path(root: Path, plugin: str, workbook: str | None) -> Path:
    workbook_path = Path(workbook) if workbook else root / "audit" / "workbooks" / f"{plugin}.xlsx"
    if not workbook_path.is_file():
        raise click.ClickException(f"workbook not found: {workbook_path}")
    return workbook_path


def _parse_cases(values: tuple[str, ...]) -> list[str]:
    case_ids: list[str] = []
    for raw in values:
        for item in raw.split(","):
            case_id = item.strip()
            if case_id:
                case_ids.append(case_id)
    return case_ids


def _discover_case_ids(root: Path, plugin: str) -> list[str]:
    cases_dir = root / "plugins" / plugin / "cases"
    if not cases_dir.is_dir():
        raise click.ClickException(f"cases directory not found: {cases_dir}")

    case_ids = sorted(
        {
            path.stem.split("_", 1)[0]
            for path in cases_dir.glob("D*.yaml")
            if path.is_file() and path.stem
        }
    )
    if not case_ids:
        raise click.ClickException(f"no discoverable D*.yaml cases found under {cases_dir}")
    return case_ids


def _collect_column_overrides(**options: str | None) -> dict[str, str] | None:
    overrides = {key: value for key, value in options.items() if value}
    return overrides or None


def _cleanup_failed_run(audit_root: Path, rid: str, plugin: str) -> None:
    run_root = audit_root / "runs" / rid
    run_dir = run_root / plugin
    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)
    try:
        run_root.rmdir()
    except OSError:
        pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_run_dir(audit_root: Path, rid: str, plugin: str | None = None) -> Path:
    run_root = audit_root / "runs" / rid
    if not run_root.is_dir():
        raise click.ClickException(f"RID not found: {rid}")
    if plugin is not None:
        run_dir = run_root / plugin
        if not run_dir.is_dir():
            raise click.ClickException(f"run directory not found: {run_dir}")
        return run_dir

    children = sorted(path for path in run_root.iterdir() if path.is_dir())
    if len(children) != 1:
        names = ", ".join(child.name for child in children) or "<none>"
        raise click.ClickException(f"expected exactly one plugin run directory under {run_root}, found: {names}")
    return children[0]


@click.group("audit")
def audit_group() -> None:
    """Audit mode commands."""


@audit_group.command("init")
@click.argument("plugin")
@click.option("--workbook", type=click.Path(dir_okay=False))
@click.option("--cases", "cases_values", multiple=True, help="Comma-separated case IDs.")
@click.option("--sheet", default="Wifi_LLAPI", show_default=True)
@click.option("--col-object")
@click.option("--col-api")
@click.option("--col-steps")
@click.option("--col-output")
@click.option("--col-result-5g")
@click.option("--col-result-6g")
@click.option("--col-result-24g")
@click.pass_context
def audit_init(
    ctx: click.Context,
    plugin: str,
    workbook: str | None,
    cases_values: tuple[str, ...],
    sheet: str,
    col_object: str | None,
    col_api: str | None,
    col_steps: str | None,
    col_output: str | None,
    col_result_5g: str | None,
    col_result_6g: str | None,
    col_result_24g: str | None,
) -> None:
    """Initialize an audit run and print its RID."""

    root = Path(ctx.obj["root"])
    audit_root = root / "audit"
    workbook_path = _resolve_workbook_path(root, plugin, workbook)
    case_ids = _parse_cases(cases_values) or _discover_case_ids(root, plugin)
    column_overrides = _collect_column_overrides(
        object=col_object,
        api=col_api,
        test_steps=col_steps,
        command_output=col_output,
        result_5g=col_result_5g,
        result_6g=col_result_6g,
        result_24g=col_result_24g,
    )

    rid: str | None = None
    try:
        build_index(
            workbook_path,
            sheet_name=sheet,
            column_overrides=column_overrides,
        )
        rid = manifest.create_run(
            plugin=plugin,
            workbook_path=workbook_path,
            cli_args=_build_cli_args(sheet=sheet, case_ids=case_ids, column_overrides=column_overrides),
            case_ids=case_ids,
            audit_root=audit_root,
            repo_root=root,
        )
        snapshot_path = audit_root / "runs" / rid / plugin / "workbook_snapshot.xlsx"
        shutil.copy2(workbook_path, snapshot_path)
        run_manifest = manifest.load_run(rid, plugin=plugin, audit_root=audit_root)
        if _file_sha256(snapshot_path) != run_manifest.get("workbook_sha256", ""):
            raise ValueError("workbook snapshot SHA mismatch")
    except (
        OSError,
        ValueError,
        BadZipFile,
        InvalidFileException,
        subprocess.CalledProcessError,
    ) as exc:
        if rid is not None:
            _cleanup_failed_run(audit_root, rid, plugin)
        raise click.ClickException(str(exc)) from exc

    click.echo(rid)


def _build_cli_args(
    *,
    sheet: str,
    case_ids: list[str],
    column_overrides: dict[str, str] | None,
) -> dict[str, Any]:
    cli_args: dict[str, Any] = {
        "sheet": sheet,
        "cases": list(case_ids),
    }
    if column_overrides:
        cli_args["column_overrides"] = dict(column_overrides)
    return cli_args


@audit_group.command("status")
@click.argument("rid")
@click.pass_context
def audit_status(ctx: click.Context, rid: str) -> None:
    """Print manifest and bucket counts for an audit run."""

    audit_root = Path(ctx.obj["root"]) / "audit"
    run_dir = _resolve_run_dir(audit_root, rid)
    plugin = run_dir.name
    run_manifest = manifest.load_run(rid, plugin=plugin, audit_root=audit_root)

    click.echo(f"RID: {rid}")
    click.echo(f"plugin: {plugin}")
    click.echo(f"cases: {len(run_manifest['cases'])}")
    click.echo("buckets:")
    for bucket_name in bucket_mod.BUCKETS:
        click.echo(f"  {bucket_name}: {len(bucket_mod.list_bucket(run_dir, bucket_name))}")


@audit_group.command("summary")
@click.argument("rid")
@click.pass_context
def audit_summary(ctx: click.Context, rid: str) -> None:
    """Write a Markdown summary for an audit run."""

    audit_root = Path(ctx.obj["root"]) / "audit"
    run_dir = _resolve_run_dir(audit_root, rid)
    plugin = run_dir.name
    run_manifest = manifest.load_run(rid, plugin=plugin, audit_root=audit_root)

    lines = [
        "# Audit Run Summary",
        "",
        f"- **RID**: `{rid}`",
        f"- **Plugin**: `{plugin}`",
        f"- **Workbook**: `{run_manifest['workbook_path']}`",
        f"- **Total cases**: {len(run_manifest['cases'])}",
        f"- **Init**: {run_manifest['init_timestamp']}",
        "",
        "## Bucket counts",
        "",
        "| Bucket | Count |",
        "| --- | ---: |",
    ]
    for bucket_name in bucket_mod.BUCKETS:
        lines.append(f"| {bucket_name} | {len(bucket_mod.list_bucket(run_dir, bucket_name))} |")
    lines.append("")

    summary_path = run_dir / "summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    click.echo(str(summary_path))
