from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

RID_PATTERN = r"^[0-9a-f]+-\d{4}-\d{2}-\d{2}T\d{6}Z$"


def _git_short_sha(cwd: Optional[Path] = None) -> str:
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(cwd))
        return out.decode().strip()
    except Exception:
        return "unknown"


def _git_full_sha(cwd: Optional[Path] = None) -> str:
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(cwd))
        return out.decode().strip()
    except Exception:
        return ""


def generate_rid(cwd: Optional[Path] = None) -> str:
    """Generate RID of form <git_short_sha>-<YYYY-MM-DDTHHMMSSZ> using UTC now."""
    short = _git_short_sha(cwd)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    return f"{short}-{ts}"


@dataclass
class RunManifest:
    plugin: str
    rid: str
    workbook_path: str
    workbook_sha256: str
    cli_args: List[str]
    cases: List[str]
    git_commit_sha: str
    init_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_run(
    plugin: str,
    workbook_path: Optional[str] = "",
    cli_args: Optional[List[str]] = None,
    cases: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    rid = generate_rid(cwd)
    run_dir = cwd / "audit" / "runs" / rid / plugin
    (run_dir / "case").mkdir(parents=True, exist_ok=True)
    (run_dir / "buckets").mkdir(parents=True, exist_ok=True)

    workbook_sha = ""
    wbpath_str = workbook_path or ""
    if wbpath_str:
        wbpath = cwd / wbpath_str
        if wbpath.exists():
            workbook_sha = _sha256_of_file(wbpath)

    cli_args = list(cli_args or [])
    cases = list(cases or [])

    manifest = RunManifest(
        plugin=plugin,
        rid=rid,
        workbook_path=wbpath_str,
        workbook_sha256=workbook_sha,
        cli_args=cli_args,
        cases=cases,
        git_commit_sha=_git_full_sha(cwd),
        init_timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ"),
    )

    mpath = run_dir / "manifest.json"
    with mpath.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

    return manifest.to_dict()


def load_run(rid: str, plugin: str, cwd: Optional[Path] = None) -> Dict[str, Any]:
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    mpath = cwd / "audit" / "runs" / rid / plugin / "manifest.json"
    if not mpath.exists():
        raise FileNotFoundError(f"manifest not found: {mpath}")
    with mpath.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data
