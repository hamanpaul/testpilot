from pathlib import Path
import json
from typing import Any, Dict, List

BUCKETS = (
    "confirmed",
    "applied",
    "pending",
    "block",
    "needs_pass3",
)


def _bucket_path(run_dir: Path, bucket: str) -> Path:
    if bucket not in BUCKETS:
        raise ValueError(f"Unknown bucket: {bucket!r}")
    return Path(run_dir) / "buckets" / f"{bucket}.jsonl"


def append_to_bucket(run_dir: Path, bucket: str, entry: Dict[str, Any]) -> None:
    """Append a JSON entry to the named bucket file under run_dir/buckets.

    The file is append-only; this function will create parent dirs as needed.
    """
    if not isinstance(entry, dict):
        raise TypeError("bucket entry must be a dict")

    p = _bucket_path(run_dir, bucket)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_bucket(run_dir: Path, bucket: str) -> List[Dict[str, Any]]:
    """Return list of entries from the named bucket JSONL file.

    Returns empty list if the bucket file does not exist.
    """
    p = _bucket_path(run_dir, bucket)
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    with p.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Corrupted JSONL in {bucket} bucket at line {line_number}: {exc}"
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError(
                    f"Bucket entry must be a dict in {bucket} bucket at line {line_number}"
                )
            out.append(parsed)
    return out
