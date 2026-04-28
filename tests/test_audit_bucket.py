import json
from pathlib import Path
import pytest

import importlib
bucket_mod = importlib.import_module('testpilot.audit.bucket')

EXPECTED_BUCKETS = [
    "confirmed",
    "applied",
    "pending",
    "block",
    "needs_pass3",
]


def test_buckets_constant():
    assert bucket_mod.BUCKETS == EXPECTED_BUCKETS


def test_empty_bucket_reads_empty(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    assert bucket_mod.list_bucket(run_dir, "pending") == []


def test_append_and_list(tmp_path):
    run_dir = tmp_path / "run2"
    run_dir.mkdir()
    entry1 = {"a": 1}
    entry2 = {"b": "x"}
    bucket_mod.append_to_bucket(run_dir, "pending", entry1)
    bucket_mod.append_to_bucket(run_dir, "pending", entry2)
    res = bucket_mod.list_bucket(run_dir, "pending")
    assert res == [entry1, entry2]


def test_unknown_bucket_rejected(tmp_path):
    run_dir = tmp_path / "r3"
    run_dir.mkdir()
    with pytest.raises(ValueError):
        bucket_mod.append_to_bucket(run_dir, "unknown", {})


def test_file_is_jsonl(tmp_path):
    run_dir = tmp_path / "r4"
    run_dir.mkdir()
    e = {"z": 1}
    bucket_mod.append_to_bucket(run_dir, "pending", e)
    path = run_dir / "buckets" / "pending.jsonl"
    assert path.exists()
    with path.open() as f:
        line = f.readline().strip()
    assert json.loads(line) == e


def test_corrupted_jsonl_raises_descriptive_error(tmp_path):
    run_dir = tmp_path / "r5"
    bucket_dir = run_dir / "buckets"
    bucket_dir.mkdir(parents=True)
    (bucket_dir / "pending.jsonl").write_text('{"case": "D1"}\n{"broken": \n')

    with pytest.raises(ValueError, match="Corrupted JSONL.*pending.*line 2"):
        bucket_mod.list_bucket(run_dir, "pending")


def test_append_rejects_non_dict_entries(tmp_path):
    run_dir = tmp_path / "r6"
    run_dir.mkdir()

    with pytest.raises(TypeError, match="bucket entry must be a dict"):
        bucket_mod.append_to_bucket(run_dir, "pending", "not-a-dict")
