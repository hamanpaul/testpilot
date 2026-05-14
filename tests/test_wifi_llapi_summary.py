from __future__ import annotations

import pytest

from testpilot.reporting.wifi_llapi_summary import (
    BAND_KEYS,
    BAND_LABELS,
    CATEGORIES,
    COUNTED_BUCKETS,
    SUMMARY_POLICY_VERSION,
    BandClassification,
    build_wifi_llapi_summary,
    classify_band_result,
    extract_fail_reason,
    major_category,
)


def _make_case(
    case_id: str,
    source_row: int,
    *,
    result_5g: str = "Pass",
    result_6g: str = "Pass",
    result_24g: str = "Pass",
    diagnostic_status: str = "",
    failure_snapshot: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "source_row": source_row,
        "result_5g": result_5g,
        "result_6g": result_6g,
        "result_24g": result_24g,
        "diagnostic_status": diagnostic_status,
        "failure_snapshot": failure_snapshot,
    }


def _band_row(summary: dict[str, object], band_key: str, category: str) -> dict[str, object]:
    rows = summary["band_category"]
    assert isinstance(rows, list)
    for row in rows:
        if row["band_key"] == band_key and row["category"] == category:
            return row
    raise AssertionError(f"missing summary row: {band_key} {category}")


def test_exports_match_summary_contract() -> None:
    assert SUMMARY_POLICY_VERSION == "wifi_llapi_summary_v1"
    assert BAND_KEYS == ("result_5g", "result_6g", "result_24g")
    assert BAND_LABELS == {
        "result_5g": "5G",
        "result_6g": "6G",
        "result_24g": "2.4G",
    }
    assert CATEGORIES == (
        "WiFi.AccessPoint",
        "WiFi.EndPoint",
        "WiFi.Radio",
        "WiFi.SSID",
        "WiFi.wps_DefParam",
        "WiFi.Other",
    )
    assert COUNTED_BUCKETS == ("Pass", "Fail", "To be tested", "Not Supported", "Skip")
    item = BandClassification(raw="Fail", bucket="To be tested", fail_reason="sta band not ready")
    assert item.raw == "Fail"
    assert item.bucket == "To be tested"
    assert item.fail_reason == "sta band not ready"


@pytest.mark.parametrize(
    ("object_name", "expected"),
    [
        ("WiFi.AccessPoint.1.Security.", "WiFi.AccessPoint"),
        ("WiFi.EndPoint.1.Profile.", "WiFi.EndPoint"),
        ("WiFi.Radio.1.", "WiFi.Radio"),
        ("WiFi.SSID.1.", "WiFi.SSID"),
        ("WiFi.wps_DefParam.1.", "WiFi.wps_DefParam"),
        ("Device.Foo.1.", "WiFi.Other"),
        ("", "WiFi.Other"),
    ],
)
def test_major_category_maps_known_prefixes_and_other(
    object_name: str,
    expected: str,
) -> None:
    assert major_category(object_name) == expected


def test_extract_fail_reason_prefers_reason_code_then_comment_then_phase() -> None:
    reason_first = {
        "failure_snapshot": {
            "reason_code": "pass_criteria_not_satisfied",
            "comment": "criteria mismatch",
            "phase": "evaluate",
        }
    }
    assert extract_fail_reason(reason_first) == "pass criteria not satisfied"

    comment_second = {"failure_snapshot": {"comment": "step timeout", "phase": "execute_step"}}
    assert extract_fail_reason(comment_second) == "step timeout"

    phase_last = {"failure_snapshot": {"phase": "verify_env"}}
    assert extract_fail_reason(phase_last) == "verify env"


def test_extract_fail_reason_prefers_case_comment_before_bare_phase() -> None:
    # snapshot has only phase; case-level comment should win over bare phase
    case = {
        "failure_snapshot": {"phase": "evaluate"},
        "comment": "pass criteria not satisfied",
    }
    assert extract_fail_reason(case) == "pass criteria not satisfied"

    # diagnostic_status wins over case comment (per priority order)
    case_with_diag = {
        "failure_snapshot": {"phase": "evaluate"},
        "diagnostic_status": "FailCriteria",
        "comment": "pass criteria not satisfied",
    }
    assert extract_fail_reason(case_with_diag) == "FailCriteria"

    # phase is used only when no other info available
    case_phase_only = {"failure_snapshot": {"phase": "evaluate"}}
    assert extract_fail_reason(case_phase_only) == "evaluate"


def test_classify_band_result_reprojects_env_and_config_failures_to_to_be_tested() -> None:
    env_case = _make_case(
        "D001",
        101,
        result_5g="Fail",
        diagnostic_status="FailEnv",
        failure_snapshot={"reason_code": "sta_band_not_ready", "phase": "verify_env"},
    )
    env_result = classify_band_result("Fail", env_case)
    assert env_result == BandClassification(
        raw="Fail",
        bucket="To be tested",
        fail_reason="sta band not ready",
    )

    config_case = _make_case(
        "D002",
        102,
        result_5g="Fail",
        diagnostic_status="FailConfig",
        failure_snapshot={"comment": "missing sta profile", "phase": "setup_env"},
    )
    config_result = classify_band_result("Fail", config_case)
    assert config_result == BandClassification(
        raw="Fail",
        bucket="To be tested",
        fail_reason="missing sta profile",
    )


def test_classify_band_result_treats_step_execution_failure_without_criteria_mismatch_as_retryable() -> None:
    case = _make_case(
        "D010",
        110,
        result_6g="Fail",
        failure_snapshot={
            "phase": "execute_step",
            "comment": "command timeout",
            "reason_code": "sta_command_timeout",
        },
    )
    assert classify_band_result("Fail", case) == BandClassification(
        raw="Fail",
        bucket="To be tested",
        fail_reason="sta command timeout",
    )


def test_classify_band_result_keeps_evaluate_criteria_mismatch_as_fail() -> None:
    case = _make_case(
        "D011",
        111,
        result_24g="Fail",
        failure_snapshot={
            "phase": "evaluate",
            "comment": "pass_criteria not satisfied",
            "reason_code": "pass_criteria_not_satisfied",
        },
    )
    assert classify_band_result("Fail", case) == BandClassification(
        raw="Fail",
        bucket="Fail",
        fail_reason="pass criteria not satisfied",
    )


@pytest.mark.parametrize(
    ("raw_value", "expected_bucket"),
    [
        ("Not Supported", "Not Supported"),
        ("not_supported", "Not Supported"),
        ("Skip", "Skip"),
        ("skip", "Skip"),
        ("N/A", "N/A"),
        ("n/a", "N/A"),
    ],
)
def test_classify_band_result_recognizes_non_fail_special_buckets(
    raw_value: str,
    expected_bucket: str,
) -> None:
    result = classify_band_result(raw_value, _make_case("D020", 120))
    assert result == BandClassification(raw=expected_bucket, bucket=expected_bucket, fail_reason="")


def test_build_wifi_llapi_summary_aggregates_band_and_category_counts() -> None:
    row_objects = {
        101: "WiFi.AccessPoint.1.Security.",
        102: "WiFi.Radio.1.",
        103: "Device.Unknown.1.",
    }
    case_results = [
        _make_case(
            "D001",
            101,
            result_5g="Pass",
            result_6g="Fail",
            result_24g="Not Supported",
            diagnostic_status="FailEnv",
            failure_snapshot={"reason_code": "sta_band_not_ready", "phase": "verify_env"},
        ),
        _make_case(
            "D002",
            102,
            result_5g="Fail",
            result_6g="Skip",
            result_24g="Pass",
            failure_snapshot={
                "reason_code": "pass_criteria_not_satisfied",
                "comment": "pass_criteria not satisfied",
                "phase": "evaluate",
            },
        ),
        _make_case(
            "D003",
            103,
            result_5g="N/A",
            result_6g="Pass",
            result_24g="Fail",
            diagnostic_status="FailConfig",
            failure_snapshot={"comment": "missing sta profile", "phase": "setup_env"},
        ),
    ]

    summary = build_wifi_llapi_summary(case_results, row_objects)

    assert summary["policy_version"] == SUMMARY_POLICY_VERSION
    assert len(summary["band_category"]) == len(BAND_KEYS) * len(CATEGORIES)

    access_5g = _band_row(summary, "result_5g", "WiFi.AccessPoint")
    assert access_5g == {
        "band_key": "result_5g",
        "band_label": "5G",
        "category": "WiFi.AccessPoint",
        "total_items": 1,
        "tested_items": 1,
        "pass": 1,
        "fail": 0,
        "to_be_tested": 0,
        "not_supported": 0,
        "skip": 0,
        "pass_rate": pytest.approx(1.0),
        "progress": pytest.approx(1.0),
    }

    access_6g = _band_row(summary, "result_6g", "WiFi.AccessPoint")
    assert access_6g["to_be_tested"] == 1
    assert access_6g["tested_items"] == 0
    assert access_6g["progress"] == pytest.approx(0.0)

    other_24g = _band_row(summary, "result_24g", "WiFi.Other")
    assert other_24g["to_be_tested"] == 1
    assert other_24g["tested_items"] == 0

    radio_5g = _band_row(summary, "result_5g", "WiFi.Radio")
    assert radio_5g["fail"] == 1
    assert radio_5g["pass_rate"] == pytest.approx(0.0)

    assert summary["bucket_totals"]["result_5g"] == {
        "band_key": "result_5g",
        "band_label": "5G",
        "total_items": 3,
        "tested_items": 2,
        "pass": 1,
        "fail": 1,
        "to_be_tested": 0,
        "not_supported": 0,
        "skip": 0,
        "pass_rate": pytest.approx(0.5),
        "progress": pytest.approx(2 / 3),
    }
    assert summary["bucket_totals"]["result_6g"]["to_be_tested"] == 1
    assert summary["bucket_totals"]["result_6g"]["skip"] == 1
    assert summary["bucket_totals"]["result_24g"]["not_supported"] == 1
    assert summary["bucket_totals"]["result_24g"]["to_be_tested"] == 1

    assert summary["raw_totals"]["result_5g"] == {"Pass": 1, "Fail": 1, "N/A": 1}
    assert summary["raw_totals"]["result_6g"] == {"Fail": 1, "Skip": 1, "Pass": 1}
    assert summary["raw_totals"]["result_24g"] == {"Not Supported": 1, "Pass": 1, "Fail": 1}
    assert summary["diagnostic_status"] == {"FailEnv": 1, "FailConfig": 1}

    per_case = {item["case_id"]: item for item in summary["per_case"]}
    assert per_case["D001"]["category"] == "WiFi.AccessPoint"
    assert per_case["D001"]["bands"]["result_6g"] == {
        "raw": "Fail",
        "bucket": "To be tested",
        "fail_reason": "sta band not ready",
    }
    assert per_case["D002"]["bands"]["result_5g"]["bucket"] == "Fail"
    assert per_case["D003"]["bands"]["result_5g"]["raw"] == "N/A"
