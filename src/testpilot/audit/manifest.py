from __future__ import annotations

import hashlib
import json
import subprocess
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RID_PATTERN = re.compile(r"^[0-9a-f]+-\d{4}-\d{2}-\d{2}T\d{6}Z$")


def _git_short_sha(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root))
        return out.decode().strip()
    except Exception:
        return "unknown"


def _git_full_sha(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root))
        return out.decode().strip()
    except Exception:
        return ""


def generate_rid(commit_sha: str | None = None, *, repo_root: Path | None = None, now: datetime | None = None) -> str:
    """Generate RID of form <git_short_sha>-<YYYY-MM-DDTHHMMSSZ> using UTC timezone-aware now.

    If commit_sha is provided, use its short form as the prefix instead of querying git.
    repo_root is only used when commit_sha is None to obtain short sha.
    now can be provided for deterministic tests.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H%M%SZ")
    if commit_sha:
        short = commit_sha[:7]
    else:
        root = Path(repo_root) if repo_root is not None else Path.cwd()
        short = _git_short_sha(root)
    return f"{short}-{ts}"


@dataclass
class RunManifest:
    plugin: str
    rid: str
    workbook_path: str
    workbook_sha256: str
    cli_args: dict[str, Any]
    cases: list[str]
    git_commit_sha: str
    init_timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_run(*, plugin: str, workbook_path: Path, cli_args: dict[str, Any], case_ids: list[str], audit_root: Path, repo_root: Path) -> str:
    """Create a run directory and write manifest. Returns RID.

    Fails with FileExistsError if manifest already exists for same rid/plugin.
    """
    # determine rid
    rid = generate_rid(None, repo_root=repo_root)

    run_dir = Path(audit_root) / "runs" / rid / plugin
    mpath = run_dir / "manifest.json"
    if mpath.exists():
        raise FileExistsError(f"run manifest already exists: {mpath}")

    (run_dir / "case").mkdir(parents=True, exist_ok=True)
    (run_dir / "buckets").mkdir(parents=True, exist_ok=True)

    workbook_sha = ""
    wbpath = Path(workbook_path)
    if wbpath.exists():
        workbook_sha = _sha256_of_file(wbpath)

    manifest = RunManifest(
        plugin=plugin,
        rid=rid,
        workbook_path=str(workbook_path),
        workbook_sha256=workbook_sha,
        cli_args=dict(cli_args),
        cases=list(case_ids),
        git_commit_sha=_git_full_sha(repo_root),
        init_timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ"),
    )

    with mpath.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

    return rid


def load_run(rid: str, *, plugin: str, audit_root: Path) -> dict[str, Any]:
    mpath = Path(audit_root) / "runs" / rid / plugin / "manifest.json"
    if not mpath.exists():
        raise FileNotFoundError(f"manifest not found: {mpath}")
    with mpath.open("r", encoding="utf-8") as f:
        return json.load(f)
