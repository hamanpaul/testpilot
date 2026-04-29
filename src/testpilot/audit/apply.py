"""Write proposed.yaml back to plugins/cases/."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from testpilot.audit import bucket as bucket_mod

_APPLY_BUCKETS = ("applied",)
_APPLY_BUCKETS_WITH_PENDING = ("applied", "pending")


@dataclass
class ApplyResult:
    applied_cases: list[str] = field(default_factory=list)
    skipped_cases: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def apply_run(
    run_dir: Path,
    *,
    cases_dir: Path,
    include_pending: bool = False,
    only_cases: list[str] | None = None,
) -> ApplyResult:
    """Apply proposed.yaml from applied (and optionally pending) buckets.

    Block entries are always skipped.
    """
    res = ApplyResult()
    target_buckets = _APPLY_BUCKETS_WITH_PENDING if include_pending else _APPLY_BUCKETS
    seen: set[str] = set()

    for bucket_name in target_buckets:
        for entry in bucket_mod.list_bucket(run_dir, bucket_name):
            # Support both legacy `case_id` and newer `case` key shapes.
            case = entry.get("case") or entry.get("case_id")
            if not case:
                continue
            if case in seen:
                continue
            seen.add(case)

            if only_cases is not None and case not in only_cases:
                res.skipped_cases.append(case)
                continue

            proposed = run_dir / "case" / case / "proposed.yaml"
            if not proposed.is_file():
                res.errors.append(f"{case}: proposed.yaml missing")
                continue

            yaml_files = list(cases_dir.glob(f"{case}_*.yaml"))
            if not yaml_files:
                res.errors.append(f"{case}: target yaml not found in {cases_dir}")
                continue
            if len(yaml_files) > 1:
                res.errors.append(f"{case}: target yaml ambiguous")
                continue

            target = yaml_files[0]
            try:
                shutil.copy2(proposed, target)
            except OSError as exc:
                res.errors.append(f"{case}: apply copy failed: {exc}")
                continue
            res.applied_cases.append(case)

    return res
