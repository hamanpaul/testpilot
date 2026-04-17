from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from testpilot.reporting.wifi_llapi_excel import TemplateBuildResult, write_template_manifest


def test_write_template_manifest_prefers_repo_relative_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True)
    template_path = repo_root / "plugins" / "wifi_llapi" / "reports" / "templates" / "wifi_llapi_template.xlsx"
    source_workbook = repo_root / "0401.xlsx"
    manifest_path = template_path.with_suffix(".manifest.json")
    template_path.parent.mkdir(parents=True)

    result = TemplateBuildResult(
        template_path=template_path,
        sheet_name="Wifi_LLAPI",
        total_case_rows=741,
        cleared_columns=("G", "H"),
        source_workbook=source_workbook,
        source_sheet="Wifi_LLAPI",
    )

    write_template_manifest(manifest_path, result)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["template_path"] == "plugins/wifi_llapi/reports/templates/wifi_llapi_template.xlsx"
    assert payload["source_workbook"] == "0401.xlsx"


def test_write_template_manifest_falls_back_to_manifest_relative_paths(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "output"
    manifest_path = manifest_dir / "wifi_llapi_template.manifest.json"
    template_path = tmp_path / "shared" / "wifi_llapi_template.xlsx"
    source_workbook = tmp_path / "shared" / "0401.xlsx"
    manifest_dir.mkdir(parents=True)
    template_path.parent.mkdir(parents=True)

    result = TemplateBuildResult(
        template_path=template_path,
        sheet_name="Wifi_LLAPI",
        total_case_rows=741,
        cleared_columns=("G", "H"),
        source_workbook=source_workbook,
        source_sheet="Wifi_LLAPI",
    )

    write_template_manifest(manifest_path, result)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["template_path"] == "../shared/wifi_llapi_template.xlsx"
    assert payload["source_workbook"] == "../shared/0401.xlsx"


def test_write_template_manifest_normalizes_windows_style_relative_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_dir = tmp_path / "output"
    manifest_path = manifest_dir / "wifi_llapi_template.manifest.json"
    template_path = tmp_path / "shared" / "wifi_llapi_template.xlsx"
    source_workbook = tmp_path / "shared" / "0401.xlsx"
    manifest_dir.mkdir(parents=True)
    template_path.parent.mkdir(parents=True)

    result = TemplateBuildResult(
        template_path=template_path,
        sheet_name="Wifi_LLAPI",
        total_case_rows=741,
        cleared_columns=("G", "H"),
        source_workbook=source_workbook,
        source_sheet="Wifi_LLAPI",
    )

    def _fake_relpath(path: os.PathLike[str] | str, start: os.PathLike[str] | str = ".") -> str:
        del path, start
        return "..\\shared\\wifi_llapi_template.xlsx"

    monkeypatch.setattr(
        "testpilot.reporting.wifi_llapi_excel._find_git_root",
        lambda start: None,
    )
    monkeypatch.setattr("testpilot.reporting.wifi_llapi_excel.os.path.relpath", _fake_relpath)

    write_template_manifest(manifest_path, result)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["template_path"] == "../shared/wifi_llapi_template.xlsx"
