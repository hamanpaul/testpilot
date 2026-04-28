from __future__ import annotations

import hashlib
import json
import os
import subprocess
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RID_PATTERN = re.compile(r"^[0-9a-f]+-\d{4}-\d{2}-\d{2}T\d{6}Z$")


def _git_short_sha(repo_root: Path) -> str:
    """Return the short git sha for HEAD in repo_root.

    Do not swallow subprocess errors; let them propagate to callers so they can
    fail loudly instead of producing invalid placeholder values.
    """
    out = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(repo_root),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return out.stdout.strip()


def _git_full_sha(repo_root: Path) -> str:
    """Return the full git sha for HEAD in repo_root.

    Propagate subprocess failures to the caller.
    """
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return out.stdout.strip()


def generate_rid(commit_sha: str | None = None, *, repo_root: Path | None = None, now: datetime | None = None) -> str:
    """Generate RID of form <git_short_sha>-<YYYY-MM-DDTHHMMSSZ> using UTC timezone-aware now.

    If commit_sha is provided, use its short form as the prefix instead of querying git.
    repo_root is required when commit_sha is None to obtain short sha.
    now can be provided for deterministic tests.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H%M%SZ")

    if commit_sha:
        short = str(commit_sha)[:7]
    else:
        if repo_root is None:
            raise ValueError("Either commit_sha or repo_root must be provided to generate RID")
        short = _git_short_sha(Path(repo_root))

    # Validate short sha is hex
    if not re.fullmatch(r"[0-9a-f]+", short):
        raise ValueError(f"invalid git short sha: {short!r}")

    rid = f"{short}-{ts}"
    if not RID_PATTERN.match(rid):
        raise ValueError(f"generated RID does not match pattern: {rid}")
    return rid


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

    workbook_sha = ""
    wbpath = Path(workbook_path)
    if wbpath.is_file():
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

    run_root = Path(audit_root) / "runs" / rid
    run_dir = run_root / plugin
    mpath = run_dir / "manifest.json"

    # Atomically reserve the run directory to avoid race where two callers
    # generate same RID and then one overwrites the other's manifest. mkdir
    # with exist_ok=False will raise if the directory already exists.
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise FileExistsError(f"run directory already exists: {run_dir}")

    try:
        # create expected subdirectories
        (run_dir / "case").mkdir(parents=True, exist_ok=True)
        (run_dir / "buckets").mkdir(parents=True, exist_ok=True)

        # Write manifest atomically
        tmp_path = run_dir / "manifest.json.tmp"
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Atomic move into final location
        os.replace(str(tmp_path), str(mpath))
    except Exception:
        shutil.rmtree(run_dir, ignore_errors=True)
        try:
            run_root.rmdir()
        except OSError:
            pass
        raise

    return rid


def load_run(rid: str, *, plugin: str, audit_root: Path) -> dict[str, Any]:
    mpath = Path(audit_root) / "runs" / rid / plugin / "manifest.json"
    if not mpath.exists():
        raise FileNotFoundError(f"manifest not found: {mpath}")
    with mpath.open("r", encoding="utf-8") as f:
        return json.load(f)
