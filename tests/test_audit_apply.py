"""Tests for testpilot.audit.apply."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from testpilot.audit.apply import apply_run, ApplyResult


def _make_run_dir(base: Path, cases: dict[str, str]) -> tuple[Path, Path]:
    """Helper: create run_dir with bucket entries and case dirs for given bucket→case mapping."""
    run_dir = base / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    for bucket_name, case_id in cases.items():
        (run_dir / "buckets" / f"{bucket_name}.jsonl").write_text(
            json.dumps({"case": case_id}) + "\n"
        )
        (run_dir / "case" / case_id).mkdir(parents=True)
        (run_dir / "case" / case_id / "proposed.yaml").write_text(
            f"id: {case_id}\nname: proposed\n"
        )
    cases_dir = base / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    for case_id in cases.values():
        (cases_dir / f"{case_id}_test.yaml").write_text(f"id: {case_id}\nname: original\n")
    return run_dir, cases_dir


# ---------------------------------------------------------------------------
# Core plan tests
# ---------------------------------------------------------------------------


def test_apply_writes_proposed_yaml_for_applied_bucket_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    (run_dir / "buckets" / "applied.jsonl").write_text(
        json.dumps({"case": "D366"}) + "\n"
    )
    (run_dir / "buckets" / "pending.jsonl").write_text(
        json.dumps({"case": "D369"}) + "\n"
    )
    (run_dir / "case" / "D366").mkdir(parents=True)
    (run_dir / "case" / "D369").mkdir(parents=True)
    (run_dir / "case" / "D366" / "proposed.yaml").write_text("id: D366\nname: x\n")
    (run_dir / "case" / "D369" / "proposed.yaml").write_text("id: D369\nname: x\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D366_x.yaml").write_text("id: D366\nname: old\n")
    (cases_dir / "D369_x.yaml").write_text("id: D369\nname: old\n")

    res = apply_run(run_dir, cases_dir=cases_dir, include_pending=False)
    assert "D366" in res.applied_cases
    assert "D369" not in res.applied_cases
    assert "name: x" in (cases_dir / "D366_x.yaml").read_text()
    assert "name: old" in (cases_dir / "D369_x.yaml").read_text()


def test_apply_with_include_pending(tmp_path: Path) -> None:
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    (run_dir / "buckets" / "pending.jsonl").write_text(
        json.dumps({"case": "D369"}) + "\n"
    )
    (run_dir / "case" / "D369").mkdir(parents=True)
    (run_dir / "case" / "D369" / "proposed.yaml").write_text("id: D369\nname: new\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D369_x.yaml").write_text("id: D369\nname: old\n")

    res = apply_run(run_dir, cases_dir=cases_dir, include_pending=True)
    assert "D369" in res.applied_cases
    assert "name: new" in (cases_dir / "D369_x.yaml").read_text()


def test_apply_skips_block_bucket(tmp_path: Path) -> None:
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    (run_dir / "buckets" / "block.jsonl").write_text(
        json.dumps({"case": "D047"}) + "\n"
    )
    (run_dir / "case" / "D047").mkdir(parents=True)
    (run_dir / "case" / "D047" / "proposed.yaml").write_text("id: D047\nname: should_not_apply\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D047_x.yaml").write_text("id: D047\nname: original\n")

    res = apply_run(run_dir, cases_dir=cases_dir, include_pending=True)
    assert "D047" not in res.applied_cases
    assert "name: original" in (cases_dir / "D047_x.yaml").read_text()


# ---------------------------------------------------------------------------
# Compatibility / error-path tests
# ---------------------------------------------------------------------------


def test_apply_handles_case_id_key_in_bucket_entry(tmp_path: Path) -> None:
    """Legacy `case_id` entries in bucket should be handled the same as `case`."""
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    # Use old `case_id` key shape
    (run_dir / "buckets" / "applied.jsonl").write_text(
        json.dumps({"case_id": "D100"}) + "\n"
    )
    (run_dir / "case" / "D100").mkdir(parents=True)
    (run_dir / "case" / "D100" / "proposed.yaml").write_text("id: D100\nname: new\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D100_test.yaml").write_text("id: D100\nname: old\n")

    res = apply_run(run_dir, cases_dir=cases_dir)
    assert "D100" in res.applied_cases
    assert "name: new" in (cases_dir / "D100_test.yaml").read_text()
    assert not res.errors


def test_apply_errors_on_ambiguous_target_yaml(tmp_path: Path) -> None:
    """Multiple matching YAML files should surface an explicit error."""
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    (run_dir / "buckets" / "applied.jsonl").write_text(
        json.dumps({"case": "D200"}) + "\n"
    )
    (run_dir / "case" / "D200").mkdir(parents=True)
    (run_dir / "case" / "D200" / "proposed.yaml").write_text("id: D200\nname: new\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    # Two files matching D200_*.yaml → ambiguous
    (cases_dir / "D200_alpha.yaml").write_text("id: D200\nname: alpha\n")
    (cases_dir / "D200_beta.yaml").write_text("id: D200\nname: beta\n")

    res = apply_run(run_dir, cases_dir=cases_dir)
    assert "D200" not in res.applied_cases
    assert any("ambiguous" in e for e in res.errors)
    # Neither target file should be modified
    assert "name: alpha" in (cases_dir / "D200_alpha.yaml").read_text()
    assert "name: beta" in (cases_dir / "D200_beta.yaml").read_text()


def test_apply_collects_copy_errors_without_raising(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    (run_dir / "buckets" / "applied.jsonl").write_text(
        json.dumps({"case": "D201"}) + "\n"
    )
    (run_dir / "case" / "D201").mkdir(parents=True)
    (run_dir / "case" / "D201" / "proposed.yaml").write_text("id: D201\nname: new\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D201_test.yaml").write_text("id: D201\nname: old\n")

    def _boom(src: Path, dst: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr("testpilot.audit.apply.shutil.copy2", _boom)

    res = apply_run(run_dir, cases_dir=cases_dir)
    assert "D201" not in res.applied_cases
    assert any("copy failed" in e for e in res.errors)


def test_apply_deduplicates_case_present_in_applied_and_pending(tmp_path: Path) -> None:
    run_dir = tmp_path / "audit" / "runs" / "rid" / "wifi_llapi"
    (run_dir / "buckets").mkdir(parents=True)
    (run_dir / "buckets" / "applied.jsonl").write_text(
        json.dumps({"case": "D202"}) + "\n"
    )
    (run_dir / "buckets" / "pending.jsonl").write_text(
        json.dumps({"case": "D202"}) + "\n"
    )
    (run_dir / "case" / "D202").mkdir(parents=True)
    (run_dir / "case" / "D202" / "proposed.yaml").write_text("id: D202\nname: new\n")

    cases_dir = tmp_path / "plugins" / "wifi_llapi" / "cases"
    cases_dir.mkdir(parents=True)
    (cases_dir / "D202_test.yaml").write_text("id: D202\nname: old\n")

    res = apply_run(run_dir, cases_dir=cases_dir, include_pending=True)
    assert res.applied_cases == ["D202"]
    assert not res.errors
