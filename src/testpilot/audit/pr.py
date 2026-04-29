"""Open audit-applied PR via git + gh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from testpilot.audit import bucket as bucket_mod


def _case_id_from_entry(entry: dict) -> str | None:
    """Support both 'case' and 'case_id' key shapes (mid-rollout compat)."""
    return entry.get("case") or entry.get("case_id") or None


def _resolve_repo_root(cwd: Path) -> Path:
    """Return the git repository root for the given working directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def _collect_staged_files(run_dir: Path, plugin: str, repo_root: Path) -> list[Path]:
    """Return the set of case YAML paths to stage for the PR.

    Only files from the 'applied' bucket are staged.  Pending entries are
    intentionally excluded: they have not been manually signed off and should
    be handled in a follow-up run.  Each entry must resolve to exactly one
    ``{case_id}_*.yaml`` inside ``plugins/<plugin>/cases/``; missing or
    ambiguous files are treated as hard errors to avoid opening a misleading PR.
    """
    cases_dir = repo_root / "plugins" / plugin / "cases"
    staged: list[Path] = []
    errors: list[str] = []

    for entry in bucket_mod.list_bucket(run_dir, "applied"):
        case_id = _case_id_from_entry(entry)
        if not case_id:
            continue
        yaml_files = sorted(cases_dir.glob(f"{case_id}_*.yaml"))
        if len(yaml_files) == 1:
            staged.append(yaml_files[0])
            continue
        if not yaml_files:
            errors.append(f"{case_id}: target yaml not found in {cases_dir}")
            continue
        errors.append(f"{case_id}: target yaml ambiguous")

    if errors:
        raise ValueError("; ".join(errors))

    return staged


def build_pr_body(run_dir: Path, *, rid: str) -> str:
    """Build a Markdown PR body from an audit run directory."""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    plugin = manifest.get("plugin", "")

    lines = [
        f"# Audit Run — `{rid}`",
        "",
        f"- Plugin: `{plugin}`",
        f"- Total cases in run: {len(manifest.get('cases', []))}",
        "",
        "## Bucket counts",
        "",
        "| Bucket | Count |",
        "| --- | ---: |",
    ]
    for b in bucket_mod.BUCKETS:
        n = len(bucket_mod.list_bucket(run_dir, b))
        lines.append(f"| {b} | {n} |")
    lines.append("")

    applied = bucket_mod.list_bucket(run_dir, "applied")
    if applied:
        lines.extend(["## Applied cases", ""])
        for e in applied:
            case_id = _case_id_from_entry(e) or "(unknown)"
            lines.append(f"- `{case_id}` — {e.get('reason', '')}")
        lines.append("")

    block = bucket_mod.list_bucket(run_dir, "block")
    if block:
        lines.extend(["## Block list (manual review needed)", ""])
        for e in block:
            case_id = _case_id_from_entry(e) or "(unknown)"
            lines.append(f"- `{case_id}` — {e.get('reason', '')}")
        lines.append("")

    lines.extend([
        "## Verification",
        "",
        f"- 全程 evidence 在 `audit/runs/{rid}/{plugin}/`（gitignored, local-only）",
        "- 主 agent doctrine: `docs/audit-guide.md`",
        "- spec: `docs/superpowers/specs/2026-04-27-audit-mode-design.md`",
        "",
    ])
    return "\n".join(lines)


def open_pr(run_dir: Path, *, rid: str, draft: bool = False) -> str:
    """Stage case files, commit, push, and open a PR.  Returns the PR URL.

    Staging strategy
    ----------------
    Only the YAML files for cases in the ``applied`` bucket are staged.
    This is surgical: we never blindly ``git add plugins/<plugin>/cases``
    which could pull in unreviewed or in-progress edits.

    If there are no applied case files to stage, return an empty string without
    creating a commit or PR.
    """
    plugin = run_dir.name
    repo_root = _resolve_repo_root(run_dir)

    staged_files = _collect_staged_files(run_dir, plugin, repo_root)
    if not staged_files:
        return ""

    body = build_pr_body(run_dir, rid=rid)

    # 1. git add — only the resolved case files
    subprocess.run(
        ["git", "add", "--"] + [str(f) for f in staged_files],
        cwd=repo_root,
        check=True,
    )

    # 2. git commit
    msg_summary = f"audit({plugin}): apply RID {rid[:15]}"
    subprocess.run(
        ["git", "commit", "-m", msg_summary, "-m", body],
        cwd=repo_root,
        check=True,
    )

    # 3. git push
    subprocess.run(
        ["git", "push", "-u", "origin", "HEAD"],
        cwd=repo_root,
        check=True,
    )

    # 4. gh pr create
    title = f"audit({plugin}): {rid[:15]}"
    pr_args = ["gh", "pr", "create", "--title", title, "--body", body]
    if draft:
        pr_args.append("--draft")
    result = subprocess.run(
        pr_args,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
