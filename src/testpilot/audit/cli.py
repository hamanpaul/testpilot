"""Audit CLI commands."""

from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

import click
from openpyxl.utils.exceptions import InvalidFileException

import yaml as _yaml

from testpilot.audit import bucket as bucket_mod
from testpilot.audit import decision as decision_mod
from testpilot.audit import manifest
from testpilot.audit import pass12 as pass12_mod
from testpilot.audit import verify_edit as ve_mod
from testpilot.audit.workbook_index import build_index, normalize_api, normalize_object
from testpilot.schema.case_schema import CaseValidationError, validate_case


def _resolve_workbook_path(root: Path, plugin: str, workbook: str | None) -> Path:
    if workbook:
        workbook_path = Path(workbook)
        if not workbook_path.is_absolute():
            workbook_path = root / workbook_path
    else:
        workbook_path = root / "audit" / "workbooks" / f"{plugin}.xlsx"
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


def _remove_case_from_buckets(run_dir: Path, case_id: str) -> None:
    for bucket_name in bucket_mod.BUCKETS:
        # Keep cleaning both key shapes while the audit pipeline is mid-rollout.
        kept_entries = [
            entry
            for entry in bucket_mod.list_bucket(run_dir, bucket_name)
            if entry.get("case_id") != case_id and entry.get("case") != case_id
        ]
        bucket_mod.rewrite_bucket(run_dir, bucket_name, kept_entries)


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


@audit_group.command("pass12")
@click.argument("rid")
@click.pass_context
def audit_pass12(ctx: click.Context, rid: str) -> None:
    """Run Pass 1 + Pass 2 across all cases for an audit RID."""
    root = Path(ctx.obj["root"])
    audit_root = root / "audit"
    run_dir = _resolve_run_dir(audit_root, rid)
    plugin = run_dir.name

    run_manifest = manifest.load_run(rid, plugin=plugin, audit_root=audit_root)

    snapshot = run_dir / "workbook_snapshot.xlsx"
    if not snapshot.is_file():
        raise click.ClickException(f"workbook snapshot not found: {snapshot}")

    cli_args = run_manifest.get("cli_args", {})
    sheet = cli_args.get("sheet", "Wifi_LLAPI")
    column_overrides = cli_args.get("column_overrides") or None

    try:
        wb_index = build_index(snapshot, sheet_name=sheet, column_overrides=column_overrides)
    except (OSError, ValueError, BadZipFile, InvalidFileException) as exc:
        raise click.ClickException(f"failed to build workbook index: {exc}") from exc

    cases_root = root / "plugins" / plugin / "cases"
    if not cases_root.is_dir():
        for case_id in run_manifest["cases"]:
            _remove_case_from_buckets(run_dir, case_id)
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {
                    "case_id": case_id,
                    "reason": "cases_dir_not_found",
                    "cases_dir": str(cases_root),
                },
            )
            click.echo(f"[block] {case_id}: cases_dir_not_found")
        return

    for case_id in run_manifest["cases"]:
        _remove_case_from_buckets(run_dir, case_id)

        # Locate case YAML
        yaml_files = sorted(cases_root.glob(f"{case_id}_*.yaml"))
        if not yaml_files:
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {"case_id": case_id, "reason": "case_yaml_not_found"},
            )
            click.echo(f"[block] {case_id}: case_yaml_not_found")
            continue
        if len(yaml_files) > 1:
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {
                    "case_id": case_id,
                    "reason": "case_yaml_ambiguous",
                    "candidate_files": [path.name for path in yaml_files],
                },
            )
            click.echo(f"[block] {case_id}: case_yaml_ambiguous")
            continue

        try:
            case_data = _yaml.safe_load(yaml_files[0].read_text(encoding="utf-8")) or {}
        except (OSError, _yaml.YAMLError) as exc:
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {"case_id": case_id, "reason": f"case_yaml_parse_error: {exc}"},
            )
            click.echo(f"[block] {case_id}: case_yaml_parse_error")
            continue
        if not isinstance(case_data, dict):
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {"case_id": case_id, "reason": "case_yaml_invalid_root"},
            )
            click.echo(f"[block] {case_id}: case_yaml_invalid_root")
            continue

        source = case_data.get("source")
        if not isinstance(source, dict):
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {"case_id": case_id, "reason": "case_yaml_missing_source"},
            )
            click.echo(f"[block] {case_id}: case_yaml_missing_source")
            continue
        obj = source.get("object") or ""
        api = source.get("api") or ""
        key = (normalize_object(obj), normalize_api(api))

        # Workbook row resolution
        rows = wb_index.get(key, [])
        if not rows:
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {"case_id": case_id, "reason": "workbook_row_missing", "key": list(key)},
            )
            click.echo(f"[block] {case_id}: workbook_row_missing")
            continue

        if len(rows) > 1:
            bucket_mod.append_to_bucket(
                run_dir,
                "block",
                {
                    "case_id": case_id,
                    "reason": "workbook_row_ambiguous",
                    "candidate_row_indices": [r.raw_row_index for r in rows],
                },
            )
            click.echo(f"[block] {case_id}: workbook_row_ambiguous")
            continue

        wb_row = rows[0]
        case_dir = run_dir / "case" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        result = pass12_mod.run_pass12_for_case(
            plugin=plugin,
            case_id=case_id,
            workbook_row=wb_row,
            run_dir=run_dir,
            repo_root=root,
        )

        # Write pass1 artifact (always)
        pass1_payload: dict[str, Any] = {
            "case_id": case_id,
            "pass1_verdict_match": result.pass1_verdict_match,
            "pass1_artifacts": result.pass1_artifacts,
            "bucket": result.bucket,
            "reason": result.reason,
        }
        (case_dir / "pass1_baseline.json").write_text(
            json.dumps(pass1_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Write pass2 artifact when commands were extracted
        if result.extracted_commands:
            pass2_payload: dict[str, Any] = {
                "case_id": case_id,
                "pass2_verdict_match": result.pass2_verdict_match,
                "extracted_commands": [
                    {"command": c.command, "citation": c.citation, "rule": c.rule}
                    for c in result.extracted_commands
                ],
            }
            (case_dir / "pass2_workbook.json").write_text(
                json.dumps(pass2_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        bucket_mod.append_to_bucket(
            run_dir,
            result.bucket,
            {"case_id": case_id, "reason": result.reason},
        )
        click.echo(f"[{result.bucket}] {case_id}: {result.reason}")


@audit_group.command("verify-edit")
@click.argument("rid")
@click.argument("case")
@click.option("--yaml", "yaml_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--proposed", "proposed_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
def cmd_verify_edit(
    ctx: click.Context,
    rid: str,
    case: str,
    yaml_path: Path,
    proposed_path: Path,
) -> None:
    """Verify an audit YAML edit (boundary + schema + log)."""
    audit_root = Path(ctx.obj["root"]) / "audit"
    run_dir = _resolve_run_dir(audit_root, rid)

    # 1. Boundary check
    try:
        diffs = ve_mod.check_boundary(yaml_path, proposed_path)
    except ve_mod.BoundaryViolation as exc:
        raise click.ClickException(str(exc)) from exc
    except _yaml.YAMLError as exc:
        raise click.ClickException(f"YAML parse error during boundary check: {exc}") from exc
    except OSError as exc:
        raise click.ClickException(f"YAML file error during boundary check: {exc}") from exc

    # 2. Schema check on proposed.yaml
    try:
        raw = proposed_path.read_text(encoding="utf-8")
        proposed_data = _yaml.safe_load(raw)
    except OSError as exc:
        raise click.ClickException(f"proposed YAML read error: {exc}") from exc

    if not isinstance(proposed_data, dict):
        raise click.ClickException(f"proposed YAML root must be a mapping: {proposed_path}")

    try:
        validate_case(proposed_data, source=proposed_path)
    except CaseValidationError as exc:
        raise click.ClickException(f"schema invalid: {exc}") from exc

    # 3. RID active check
    if not (run_dir / "manifest.json").is_file():
        raise click.ClickException(f"RID not active or manifest missing: {rid}")

    # 4. Append verify_edit_log.jsonl
    log_path = run_dir / "verify_edit_log.jsonl"
    try:
        sha_before = ve_mod.file_sha256(yaml_path)
        sha_after = ve_mod.file_sha256(proposed_path)
        ve_mod.append_verify_edit_log(
            log_path=log_path,
            case=case,
            yaml_path=yaml_path,
            sha_before=sha_before,
            sha_after_proposed=sha_after,
            diff_paths_set=diffs,
        )
    except OSError as exc:
        raise click.ClickException(f"failed to write verify-edit log: {exc}") from exc
    click.echo(f"[OK] verify-edit pass; logged to {log_path}")


@audit_group.command("record")
@click.argument("rid")
@click.argument("case")
@click.option(
    "--evidence",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to JSON file with Pass 3 evidence.",
)
@click.pass_context
def cmd_record(ctx: click.Context, rid: str, case: str, evidence: Path) -> None:
    """Record Pass 3 evidence for a case; verify all citations mechanically."""
    root = Path(ctx.obj["root"])
    audit_root = root / "audit"
    run_dir = _resolve_run_dir(audit_root, rid)

    try:
        data: dict = json.loads(evidence.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"evidence JSON parse error: {exc}") from exc
    except OSError as exc:
        raise click.ClickException(f"evidence file read error: {exc}") from exc

    citations_raw = data.get("citations", [])
    try:
        citations = [decision_mod.Citation(**c) for c in citations_raw]
    except (TypeError, KeyError) as exc:
        raise click.ClickException(f"malformed citation entry: {exc}") from exc

    all_ok = decision_mod.verify_all(citations, repo_root=root)

    case_dir = run_dir / "case" / case
    case_dir.mkdir(parents=True, exist_ok=True)
    out_path = case_dir / "pass3_source.json"

    data["citations_verified"] = all_ok
    try:
        out_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        raise click.ClickException(f"failed to write pass3_source.json: {exc}") from exc

    if all_ok:
        click.echo(f"[OK] recorded {out_path}; all citations verified")
    else:
        click.echo(f"[WARN] recorded {out_path}; some citations did not verify")
