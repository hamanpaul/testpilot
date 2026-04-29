"""YAML edit boundary check + verify_edit_log writer."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml as _yaml

ALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "steps[*].command",
    "steps[*].capture",
    "verification_command",
    "verification_command[*]",
    "pass_criteria[",
)
_MISSING = object()
_STEP_EDIT_RE = re.compile(r"^steps\[\d+\]\.(command|capture)$")


class BoundaryViolation(Exception):
    """Raised when YAML diff touches a path outside the audit edit allowlist."""


def is_path_allowed(path: str) -> bool:
    """Return True if json-path-like key is within the audit edit allowlist.

    ALLOWED_PATH_PREFIXES is a human-readable summary for diagnostics and docs;
    this function is the canonical enforcement gate.
    """
    if path == "verification_command":
        return True
    if path.startswith("verification_command["):
        return True
    if _STEP_EDIT_RE.fullmatch(path):
        return True
    if path.startswith("pass_criteria["):
        return True
    return False


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict/list into json-path-like keys."""
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            out.update(_flatten(v, key))
    else:
        out[prefix] = obj
    return out


def diff_paths(before_yaml: str, after_yaml: str) -> set[str]:
    """Return set of json-path-like keys whose value differs (incl add/remove)."""
    a = _yaml.safe_load(before_yaml) or {}
    b = _yaml.safe_load(after_yaml) or {}
    fa = _flatten(a)
    fb = _flatten(b)
    keys = set(fa) | set(fb)
    return {k for k in keys if fa.get(k, _MISSING) != fb.get(k, _MISSING)}


def _top_level_list_length(doc: Any, key: str) -> int:
    if not isinstance(doc, dict):
        return 0
    value = doc.get(key)
    if value is None:
        return 0
    if isinstance(value, list):
        return len(value)
    return -1


def check_boundary(before_path: Path, after_path: Path) -> set[str]:
    """Check that YAML diff is within allowed paths. Raise BoundaryViolation if not."""
    bef = before_path.read_text()
    aft = after_path.read_text()
    before_doc = _yaml.safe_load(bef) or {}
    after_doc = _yaml.safe_load(aft) or {}
    diffs = diff_paths(bef, aft)
    structural_violations: list[str] = []
    for key in ("steps", "pass_criteria"):
        if _top_level_list_length(before_doc, key) != _top_level_list_length(after_doc, key):
            structural_violations.append(key)
    violations = sorted(d for d in diffs if not is_path_allowed(d))
    violations.extend(structural_violations)
    if violations:
        raise BoundaryViolation(
            f"YAML diff touched non-allowed paths: {sorted(set(violations))}; "
            "only steps[N].(command|capture), verification_command[*], and "
            "pass_criteria[*] edits are allowed"
        )
    return diffs


def file_sha256(path: Path) -> str:
    """Return hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def append_verify_edit_log(
    *,
    log_path: Path,
    case: str,
    yaml_path: Path,
    sha_before: str,
    sha_after_proposed: str,
    diff_paths_set: set[str],
) -> None:
    """Append a JSONL entry to verify_edit_log.jsonl."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "case": case,
        "yaml_path": str(yaml_path),
        "yaml_sha256_before": sha_before,
        "yaml_sha256_after_proposed": sha_after_proposed,
        "diff_paths": sorted(diff_paths_set),
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
