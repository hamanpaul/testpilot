from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

from testpilot.reporting.wifi_llapi_excel import (
    COMMENT_HEADER,
    DEFAULT_CLEAR_COLUMNS,
    DEFAULT_TEMPLATE_MAX_COLUMN,
    WifiLlapiCaseResult,
    build_template_from_source,
    collect_alignment_issues,
    create_run_report_from_template,
    fill_case_results,
    generate_report_filename,
    normalize_command_block,
    sanitize_report_output,
    _truncate_comment,
)
from testpilot.schema.case_schema import load_case


def _create_source_xlsx(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Wifi_LLAPI"
    wb.create_sheet("OtherSheet")

    ws["A2"] = "Object"
    ws["C2"] = "Parameter Name"
    ws["G2"] = "Test steps"
    ws["H2"] = "Command Output"
    ws["I2"] = "ARC 4.0.3 Test Result\nWiFi 5g"
    ws["J2"] = "ARC 4.0.3 Test Result\nWiFi 6g"
    ws["K2"] = "ARC 4.0.3 Test Result\nWiFi 2.4g"
    ws["L2"] = "Tester"
    ws["M2"] = "Legacy Extra Band"
    ws["S1"] = "BCM"
    ws["S2"] = "BCM v4.0.3 Test Result WiFi 5g"
    ws["X1"] = "ARC"
    ws["X2"] = "ARC 4.0.3 Test Result WiFi 5g"
    ws.merge_cells("I1:Q1")
    ws.merge_cells("L2:M2")
    ws.column_dimensions["S"].width = 18
    ws.column_dimensions["AB"].width = 24

    ws["A4"] = "WiFi.AccessPoint.{i}."
    ws["C4"] = "kickStation()"
    ws["G4"] = "old-step"
    ws["H4"] = "old-output"
    ws["I4"] = "Pass"
    ws["J4"] = "Pass"
    ws["K4"] = "Pass"
    ws["L4"] = "old-tester"

    ws["A5"] = "WiFi.Radio.{i}."
    ws["C5"] = "scan()"
    ws["G5"] = "old-step2"
    ws["H5"] = "old-output2"
    ws["I5"] = "Fail"
    ws["J5"] = "Fail"
    ws["K5"] = "Fail"
    ws["L5"] = "old-tester2"

    wb.save(path)
    wb.close()


def test_build_template_from_source(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    template = tmp_path / "wifi_llapi_template.xlsx"
    _create_source_xlsx(source)

    result = build_template_from_source(source, template)
    assert result.total_case_rows == 2
    assert result.sheet_name == "Wifi_LLAPI"
    assert DEFAULT_TEMPLATE_MAX_COLUMN == "M"
    assert result.cleared_columns == DEFAULT_CLEAR_COLUMNS
    assert "M" in result.cleared_columns

    wb = load_workbook(template)
    assert wb.sheetnames == ["Wifi_LLAPI"]
    ws = wb["Wifi_LLAPI"]
    assert ws.max_column == 13
    assert get_column_letter(ws.max_column) == "M"
    assert all(r.max_col <= 13 for r in ws.merged_cells.ranges)
    assert ws["I2"].value == "Result"
    assert ws["L2"].value == "Tester"
    assert ws["I3"].value == "WiFi 5G"
    assert ws["J3"].value == "WiFi 6G"
    assert ws["K3"].value == "WiFi 2.4G"
    assert ws["L3"].value == "Tester"
    assert ws["M3"].value == COMMENT_HEADER
    assert "S" not in ws.column_dimensions
    assert "AB" not in ws.column_dimensions
    assert ws["C4"].value == "kickStation()"
    assert ws["C5"].value == "scan()"
    for cell in ("G4", "H4", "I4", "J4", "K4", "L4", "M4", "G5", "H5", "I5", "J5", "K5", "L5", "M5"):
        assert ws[cell].value is None
    wb.close()


def test_fill_case_results(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    template = tmp_path / "wifi_llapi_template.xlsx"
    report = tmp_path / "20260304_BGW720-B0-403_wifi_LLAPI.xlsx"
    _create_source_xlsx(source)
    build_template_from_source(source, template)
    create_run_report_from_template(template, report)

    fill_case_results(
        report,
        [
            WifiLlapiCaseResult(
                case_id="wifi-llapi-D004-kickstation",
                source_row=4,
                executed_test_command="ubus-cli ...kickStation...\n\nwl assoclist",
                command_output="root@prplOS:/# wl assoclist\nassoclist empty\n>\n",
                result_5g="Pass",
                result_6g="Pass",
                result_24g="Pass",
                comment="verified via DUT and STA logs",
            )
        ],
    )

    wb = load_workbook(report)
    ws = wb["Wifi_LLAPI"]
    assert ws["G4"].value == "ubus-cli ...kickStation...\nwl assoclist"
    assert ws["H4"].value == "wl assoclist\nassoclist empty"
    assert ws["I4"].value == "Pass"
    assert ws["J4"].value == "Pass"
    assert ws["K4"].value == "Pass"
    assert ws["L4"].value == "testpilot"
    assert ws["M4"].value == "verified via DUT and STA logs"
    wb.close()


def test_fill_case_results_comment_truncates_and_blank_stays_empty(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    template = tmp_path / "wifi_llapi_template.xlsx"
    report = tmp_path / "20260304_BGW720-B0-403_wifi_LLAPI.xlsx"
    _create_source_xlsx(source)
    build_template_from_source(source, template)
    create_run_report_from_template(template, report)

    fill_case_results(
        report,
        [
            WifiLlapiCaseResult(
                case_id="wifi-llapi-D004-kickstation",
                source_row=4,
                executed_test_command="cmd",
                command_output="out",
                result_5g="Pass",
                result_6g="Pass",
                result_24g="Pass",
                comment="x" * 201,
            ),
            WifiLlapiCaseResult(
                case_id="wifi-llapi-D005-scan",
                source_row=5,
                executed_test_command="cmd2",
                command_output="out2",
                result_5g="Fail",
                result_6g="Fail",
                result_24g="Fail",
                comment="",
            ),
        ],
    )

    wb = load_workbook(report)
    ws = wb["Wifi_LLAPI"]
    assert ws["M4"].value == ("x" * 197) + "..."
    assert len(ws["M4"].value) == 200
    assert _truncate_comment("") == ""
    assert _truncate_comment(None) == ""
    assert ws["M5"].value in (None, "")
    wb.close()


def test_fill_case_results_with_merged_row(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    template = tmp_path / "wifi_llapi_template.xlsx"
    report = tmp_path / "20260304_BGW720-B0-403_wifi_LLAPI.xlsx"
    _create_source_xlsx(source)

    wb = load_workbook(source)
    ws = wb["Wifi_LLAPI"]
    ws.merge_cells("G4:G5")
    ws.merge_cells("H4:H5")
    ws.merge_cells("I4:I5")
    ws.merge_cells("J4:J5")
    ws.merge_cells("K4:K5")
    ws.merge_cells("L4:L5")
    ws.merge_cells("M4:M5")
    wb.save(source)
    wb.close()

    build_template_from_source(source, template)
    create_run_report_from_template(template, report)

    fill_case_results(
        report,
        [
            WifiLlapiCaseResult(
                case_id="wifi-llapi-D005-merged",
                source_row=5,
                executed_test_command="cmd-from-merged-row",
                command_output="out-from-merged-row",
                result_5g="Fail",
                result_6g="N/A",
                result_24g="Pass",
            )
        ],
    )

    wb = load_workbook(report)
    ws = wb["Wifi_LLAPI"]
    assert ws["G4"].value == "cmd-from-merged-row"
    assert ws["H4"].value == "out-from-merged-row"
    assert ws["I4"].value == "Fail"
    assert ws["J4"].value == "N/A"
    assert ws["K4"].value == "Pass"
    assert ws["L4"].value == "testpilot"
    assert ws["M4"].value in (None, "")
    wb.close()


def test_generate_report_filename():
    assert (
        generate_report_filename(date(2026, 3, 4), "BGW720-B0-403")
        == "20260304_BGW720-B0-403_wifi_LLAPI.xlsx"
    )
    assert (
        generate_report_filename(date(2026, 3, 4), "BGW720 B0 403")
        == "20260304_BGW720-B0-403_wifi_LLAPI.xlsx"
    )
    assert (
        generate_report_filename(
            date(2026, 3, 4),
            "BGW720 B0 403",
            unique_suffix="20260304T101112123456",
        )
        == "20260304_BGW720-B0-403_wifi_LLAPI_20260304T101112123456.xlsx"
    )


def test_create_run_report_from_template_preserves_existing_report(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    template = tmp_path / "wifi_llapi_template.xlsx"
    report = tmp_path / "20260304_BGW720-B0-403_wifi_LLAPI.xlsx"
    _create_source_xlsx(source)
    build_template_from_source(source, template)

    first = create_run_report_from_template(template, report)
    second = create_run_report_from_template(template, report)

    assert first == report
    assert second != report
    assert second.name == "20260304_BGW720-B0-403_wifi_LLAPI_01.xlsx"
    assert first.is_file()
    assert second.is_file()


def test_report_output_and_command_helpers_clean_noise():
    assert normalize_command_block("cmd1\n\n cmd2 \n") == "cmd1\ncmd2"
    assert (
        sanitize_report_output(
            "root@prplOS:/# wl status\nstatus ok\n>\n"
        )
        == "wl status\nstatus ok"
    )


def test_collect_alignment_issues(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    _create_source_xlsx(source)
    cases = [
        {
            "id": "wifi-llapi-kickstation",
            "source": {
                "row": 4,
                "object": "WiFi.AccessPoint.{i}.",
                "api": "kickStation()",
            },
        },
        {
            "id": "wifi-llapi-mismatch",
            "source": {
                "row": 5,
                "object": "WiFi.Radio.{i}.",
                "api": "wrongApi()",
            },
        },
    ]
    issues = collect_alignment_issues(cases, source)
    assert len(issues) == 1
    assert issues[0]["case_id"] == "wifi-llapi-mismatch"
    assert issues[0]["issue"] == "object_or_api_mismatch"


def test_collect_alignment_issues_on_repo_template_case():
    repo_root = Path(__file__).resolve().parents[3]
    case = load_case(
        repo_root / "plugins/wifi_llapi/cases/D018_downlinkshortguard.yaml"
    )
    template = repo_root / "plugins/wifi_llapi/reports/templates/wifi_llapi_template.xlsx"

    issues = collect_alignment_issues([case], template)

    assert issues == []
