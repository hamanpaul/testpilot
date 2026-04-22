from pathlib import Path

from openpyxl import Workbook

from testpilot.reporting.wifi_llapi_align import (
    AlignResult,
    TemplateIndex,
    align_case,
    build_template_index,
)


def _build_template(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Wifi_LLAPI"
    ws["A4"] = "WiFi.AccessPoint.{i}."
    ws["C4"] = "kickStation()"
    ws["A5"] = "WiFi.Radio.{i}."
    ws["C5"] = "getRadioStats()"
    ws["A6"] = "WiFi.AccessPoint.{i}.AssociatedDevice.{i}."
    ws["C6"] = "HeCapabilities"
    ws["A7"] = "WiFi.AccessPoint.{i}.AssociatedDevice.{i}."
    ws["C7"] = "DownlinkShortGuard"
    wb.save(path)
    wb.close()


def test_build_template_index_happy(tmp_path: Path):
    template = tmp_path / "template.xlsx"
    _build_template(template)

    index = build_template_index(template)

    assert index.forward[4] == ("WiFi.AccessPoint.{i}.", "kickStation()")
    assert index.by_object_api[("WiFi.Radio.{i}.", "getRadioStats()")] == 5
    assert index.by_api["HeCapabilities"] == [6]


def test_align_already_aligned(tmp_path: Path):
    template = tmp_path / "template.xlsx"
    _build_template(template)
    index = build_template_index(template)
    case_file = tmp_path / "D006_hecapabilities.yaml"
    case_file.write_text("stub\n", encoding="utf-8")

    result = align_case(
        {
            "id": "wifi-llapi-D006-hecapabilities",
            "name": "HeCapabilities",
            "source": {
                "row": 6,
                "object": "WiFi.AccessPoint.{i}.AssociatedDevice.{i}.",
                "api": "HeCapabilities",
            },
        },
        index,
        case_file,
    )

    assert isinstance(result, AlignResult)
    assert result.status == "already_aligned"
    assert result.source_row_after == 6
    assert result.filename_after is None


def test_align_auto_source_row_drift(tmp_path: Path):
    template = tmp_path / "template.xlsx"
    _build_template(template)
    index = build_template_index(template)
    case_file = tmp_path / "D021_hecapabilities.yaml"
    case_file.write_text("stub\n", encoding="utf-8")

    result = align_case(
        {
            "id": "wifi-llapi-D021-hecapabilities",
            "name": "HeCapabilities",
            "source": {
                "row": 7,
                "object": "WiFi.AccessPoint.{i}.AssociatedDevice.{i}.",
                "api": "HeCapabilities",
            },
        },
        index,
        case_file,
    )

    assert result.status == "auto_aligned"
    assert result.source_row_before == 7
    assert result.source_row_after == 6


def test_align_blocked_name_different_row(tmp_path: Path):
    template = tmp_path / "template.xlsx"
    _build_template(template)
    index = build_template_index(template)
    case_file = tmp_path / "D021_hecapabilities.yaml"
    case_file.write_text("stub\n", encoding="utf-8")

    result = align_case(
        {
            "id": "wifi-llapi-D021-hecapabilities",
            "name": "DownlinkShortGuard",
            "source": {
                "row": 7,
                "object": "WiFi.AccessPoint.{i}.AssociatedDevice.{i}.",
                "api": "HeCapabilities",
            },
        },
        index,
        case_file,
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "name_points_to_different_row"
    assert isinstance(index, TemplateIndex)
