"""Audit thin facade over Orchestrator.run() -- single-case mode."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from testpilot.audit import runner_facade
from testpilot.audit.runner_facade import AuditCaseResult, run_one_case_for_audit


@pytest.mark.skip(reason="needs wifi_llapi full testbed; integration covered elsewhere")
def test_run_one_case_returns_verdict():
    pass


def test_audit_case_result_has_required_fields():
    result = AuditCaseResult(
        case_id="D001",
        verdict_per_band={"5g": "Pass", "6g": "Pass", "2.4g": "Pass"},
        capture={"x": "y"},
        artifacts={"json_report_path": "/tmp/r.json"},
        error=None,
    )

    assert result.case_id == "D001"
    assert result.verdict_per_band["5g"] == "Pass"
    assert result.error is None


def test_run_one_case_projects_wifi_llapi_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    json_report = tmp_path / "report.json"
    json_report.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "d001-getradiostats-noise",
                        "result_5g": "Pass",
                        "result_6g": "Fail",
                        "result_24g": "N/A",
                        "command_output": "noise=-91",
                        "diagnostic_status": "matched",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    seen: dict[str, object] = {}

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            seen["project_root"] = project_root

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            seen["plugin"] = plugin
            seen["case_ids"] = case_ids
            return {
                "report_path": str(tmp_path / "report.xlsx"),
                "json_report_path": str(json_report),
                "md_report_path": str(tmp_path / "report.md"),
                "sta_log_path": str(tmp_path / "sta.log"),
            }

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert seen == {
        "project_root": tmp_path,
        "plugin": "wifi_llapi",
        "case_ids": ["D001"],
    }
    assert result.case_id == "D001"
    assert result.verdict_per_band == {"5g": "Pass", "6g": "Fail", "2.4g": "N/A"}
    assert result.capture == {
        "command_output": "noise=-91",
        "diagnostic_status": "matched",
    }
    assert result.artifacts == {
        "report_path": str(tmp_path / "report.xlsx"),
        "json_report_path": str(json_report),
        "md_report_path": str(tmp_path / "report.md"),
        "sta_log_path": str(tmp_path / "sta.log"),
    }
    assert result.error is None


def test_run_one_case_returns_error_when_case_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    json_report = tmp_path / "report.json"
    json_report.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "d099-some-other-case",
                        "result_5g": "Pass",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(json_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.verdict_per_band == {}
    assert result.capture == {}
    assert result.artifacts == {"json_report_path": str(json_report)}
    assert result.error == "case not found in json report: D001"


def test_run_one_case_projects_runtime_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            raise RuntimeError("boom")

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.case_id == "D001"
    assert result.verdict_per_band == {}
    assert result.capture == {}
    assert result.artifacts == {}
    assert result.error == "orchestrator error: boom"


def test_run_one_case_projects_non_runtime_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            raise FileNotFoundError("missing workbook")

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.error == "orchestrator error: missing workbook"


def test_run_one_case_returns_error_when_multiple_cases_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    json_report = tmp_path / "report.json"
    json_report.write_text(
        json.dumps(
            {
                "cases": [
                    {"case_id": "d001-getradiostats-noise", "result_5g": "Pass"},
                    {"case_id": "d001-getradiostats-load", "result_5g": "Fail"},
                ]
            }
        ),
        encoding="utf-8",
    )

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(json_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.verdict_per_band == {}
    assert result.capture == {}
    assert result.error == "multiple cases matched json report: D001"


def test_run_one_case_prefers_exact_case_id_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    json_report = tmp_path / "report.json"
    json_report.write_text(
        json.dumps(
            {
                "cases": [
                    {"case_id": "d001-foo", "result_5g": "Pass", "comment": "exact"},
                    {"case_id": "d001-foo-bar", "result_5g": "Fail", "comment": "prefix"},
                ]
            }
        ),
        encoding="utf-8",
    )

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001-foo"]
            return {"json_report_path": str(json_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001-foo", repo_root=tmp_path)

    assert result.verdict_per_band == {"5g": "Pass"}
    assert result.capture == {"comment": "exact"}
    assert result.error is None


def test_run_one_case_returns_error_when_json_report_path_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"report_path": str(tmp_path / "report.xlsx")}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.artifacts == {"report_path": str(tmp_path / "report.xlsx")}
    assert result.error == "missing json_report_path from orchestrator result"


def test_run_one_case_returns_error_when_json_report_file_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    missing_report = tmp_path / "missing.json"

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(missing_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.artifacts == {"json_report_path": str(missing_report)}
    assert result.error == f"json report not found: {missing_report}"


def test_run_one_case_returns_error_when_json_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    json_report = tmp_path / "report.json"
    json_report.write_text("{not-json", encoding="utf-8")

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(json_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.error is not None
    assert result.error.startswith("json report parse error: ")


def test_run_one_case_returns_error_when_json_root_is_not_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    json_report = tmp_path / "report.json"
    json_report.write_text(json.dumps([]), encoding="utf-8")

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(json_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.error == f"json report must be an object: {json_report}"


def test_run_one_case_returns_error_when_cases_list_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    json_report = tmp_path / "report.json"
    json_report.write_text(json.dumps({"meta": {}}), encoding="utf-8")

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(json_report)}

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.error == f"json report missing cases list: {json_report}"


def test_run_one_case_returns_error_when_json_report_read_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    json_report = tmp_path / "report.json"
    json_report.write_text(json.dumps({"cases": []}), encoding="utf-8")
    original_read_text = Path.read_text

    class FakeOrchestrator:
        def __init__(self, *, project_root: Path):
            assert project_root == tmp_path

        def run(self, plugin: str, case_ids: list[str]) -> dict[str, str]:
            assert plugin == "wifi_llapi"
            assert case_ids == ["D001"]
            return {"json_report_path": str(json_report)}

    def fake_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self == json_report:
            raise OSError("report disappeared")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(runner_facade, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    result = run_one_case_for_audit("wifi_llapi", "D001", repo_root=tmp_path)

    assert result.error == "json report read error: report disappeared"
