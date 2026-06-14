from __future__ import annotations

from pathlib import Path

import pytest

from plugins.wifi_llapi.reporting.wifi_llapi_artifacts import resolve_trace_run_dir


def test_resolve_trace_run_dir_accepts_artifact_directory(tmp_path: Path) -> None:
    reports_root = tmp_path / "reports"
    trace_dir = reports_root / "20260407_FW_wifi_LLAPI_20260407T113432267653" / "agent_trace"
    trace_dir.mkdir(parents=True)
    (trace_dir / "D001.json").write_text("{}", encoding="utf-8")

    resolved = resolve_trace_run_dir(
        "20260407_FW_wifi_LLAPI_20260407T113432267653",
        reports_root,
    )

    assert resolved == trace_dir


def test_resolve_trace_run_dir_accepts_legacy_run_id(tmp_path: Path) -> None:
    reports_root = tmp_path / "reports"
    trace_dir = reports_root / "agent_trace" / "20260407T113432267653"
    trace_dir.mkdir(parents=True)
    (trace_dir / "D001.json").write_text("{}", encoding="utf-8")

    resolved = resolve_trace_run_dir("20260407T113432267653", reports_root)

    assert resolved == trace_dir


def test_resolve_trace_run_dir_accepts_explicit_trace_dir(tmp_path: Path) -> None:
    reports_root = tmp_path / "reports"
    trace_dir = reports_root / "explicit"
    trace_dir.mkdir(parents=True)
    (trace_dir / "D001.json").write_text("{}", encoding="utf-8")

    resolved = resolve_trace_run_dir(trace_dir, reports_root)

    assert resolved == trace_dir


def test_resolve_trace_run_dir_raises_for_unknown_run(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_trace_run_dir("missing-run", tmp_path / "reports")
