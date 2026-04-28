from pathlib import Path
import json
from typing import Any, Dict, List

BUCKETS = [
    "confirmed",
    "applied",
    "pending",
    "block",
    "needs_pass3",
]


def _bucket_path(run_dir: Path, bucket: str) -> Path:
    if bucket not in BUCKETS:
        raise ValueError(f"Unknown bucket: {bucket!r}")
    return Path(run_dir) / "buckets" / f"{bucket}.jsonl"


def append_to_bucket(run_dir: Path, bucket: str, entry: Dict[str, Any]) -> None:
    """Append a JSON entry to the named bucket file under run_dir/buckets.

    The file is append-only; this function will create parent dirs as needed.
    """
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
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out
