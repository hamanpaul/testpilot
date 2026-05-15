"""Shared WiFi LLAPI summary classification helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

SUMMARY_POLICY_VERSION = "wifi_llapi_summary_v1"

BAND_KEYS: tuple[str, ...] = ("result_5g", "result_6g", "result_24g")
BAND_LABELS: dict[str, str] = {
    "result_5g": "5G",
    "result_6g": "6G",
    "result_24g": "2.4G",
}
CATEGORIES: tuple[str, ...] = (
    "WiFi.AccessPoint",
    "WiFi.EndPoint",
    "WiFi.Radio",
    "WiFi.SSID",
    "WiFi.wps_DefParam",
    "WiFi.Other",
)
COUNTED_BUCKETS: tuple[str, ...] = (
    "Pass",
    "Fail",
    "To be confirmed",
    "Not Supported",
    "Skip",
)

_CRITERIA_HINTS = (
    "criteria",
    "pass criteria",
    "pass_criteria",
    "not satisfied",
    "mismatch",
)


@dataclass(frozen=True, slots=True)
class BandClassification:
    raw: str
    bucket: str
    fail_reason: str = ""


def _normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_text(value: Any) -> str:
    text = _normalize_text(value).replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def _canonical_raw_bucket(value: Any) -> str:
    token = _display_text(value).lower()
    if token in {"", "n/a", "na", "n a"}:
        return "N/A"
    if token in {"pass", "passed"}:
        return "Pass"
    if token in {"fail", "failed", "error"}:
        return "Fail"
    if token in {"skip", "skipped"}:
        return "Skip"
    if token in {"not supported", "not support", "not_supported", "unsupported"}:
        return "Not Supported"
    if token in {"to be confirmed", "to be tested", "to be test"}:
        return "To be confirmed"
    return _display_text(value) or "N/A"


def major_category(object_name: Any) -> str:
    text = _normalize_text(object_name)
    for category in CATEGORIES[:-1]:
        if text.startswith(category):
            return category
    return "WiFi.Other"


def extract_fail_reason(case: Mapping[str, Any]) -> str:
    snapshot = case.get("failure_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    for key in ("reason_code", "comment"):
        value = _display_text(snapshot.get(key))
        if value:
            return value
    for key in ("diagnostic_status", "comment"):
        value = _display_text(case.get(key))
        if value:
            return value
    phase = _display_text(snapshot.get("phase"))
    if phase:
        return phase
    return ""


def _is_criteria_mismatch(case: Mapping[str, Any]) -> bool:
    snapshot = case.get("failure_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    phase = _display_text(snapshot.get("phase")).lower()
    if phase != "evaluate":
        return False
    haystacks = (
        _display_text(snapshot.get("reason_code")).lower(),
        _display_text(snapshot.get("comment")).lower(),
        _display_text(case.get("comment")).lower(),
    )
    return any(hint in haystack for hint in _CRITERIA_HINTS for haystack in haystacks)


def classify_band_result(raw_value: Any, case: Mapping[str, Any]) -> BandClassification:
    raw_bucket = _canonical_raw_bucket(raw_value)
    if raw_bucket != "Fail":
        return BandClassification(raw=raw_bucket, bucket=raw_bucket)

    diagnostic = _display_text(case.get("diagnostic_status")).lower()
    snapshot = case.get("failure_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    phase = _display_text(snapshot.get("phase")).lower()
    reason = extract_fail_reason(case)

    if diagnostic in {"failenv", "failconfig"}:
        return BandClassification(raw="Fail", bucket="To be confirmed", fail_reason=reason)
    if _is_criteria_mismatch(case):
        return BandClassification(raw="Fail", bucket="Fail", fail_reason=reason)
    if phase in {"execute step", "execute_step", "setup env", "setup_env", "verify env", "verify_env"}:
        return BandClassification(raw="Fail", bucket="To be confirmed", fail_reason=reason)
    return BandClassification(raw="Fail", bucket="To be confirmed", fail_reason=reason)


def _empty_summary_row(band_key: str, category: str | None) -> dict[str, Any]:
    row = {
        "band_key": band_key,
        "band_label": BAND_LABELS[band_key],
        "total_items": 0,
        "tested_items": 0,
        "pass": 0,
        "fail": 0,
        "to_be_tested": 0,
        "not_supported": 0,
        "skip": 0,
        "pass_rate": None,
        "progress": None,
    }
    if category is not None:
        row["category"] = category
    return row


def _finalize_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    total_items = int(row["total_items"])
    tested_items = int(row["pass"]) + int(row["fail"])
    row["tested_items"] = tested_items
    row["progress"] = (tested_items / total_items) if total_items else None
    row["pass_rate"] = (int(row["pass"]) / tested_items) if tested_items else None
    return row


def build_wifi_llapi_summary(
    case_results: Sequence[Mapping[str, Any]],
    row_objects: Mapping[int, str],
) -> dict[str, Any]:
    band_category_index: dict[tuple[str, str], dict[str, Any]] = {}
    bucket_totals: dict[str, dict[str, Any]] = {}
    raw_totals: dict[str, Counter[str]] = {band_key: Counter() for band_key in BAND_KEYS}
    diagnostic_totals: Counter[str] = Counter()
    per_case: list[dict[str, Any]] = []

    for band_key in BAND_KEYS:
        bucket_totals[band_key] = _empty_summary_row(band_key, None)
        for category in CATEGORIES:
            band_category_index[(band_key, category)] = _empty_summary_row(band_key, category)

    for case in case_results:
        source_row = int(case.get("source_row") or 0)
        category = major_category(row_objects.get(source_row, ""))
        diagnostic = _display_text(case.get("diagnostic_status"))
        if diagnostic:
            diagnostic_totals[diagnostic] += 1

        case_bands: dict[str, dict[str, str]] = {}
        for band_key in BAND_KEYS:
            raw_bucket = _canonical_raw_bucket(case.get(band_key))
            raw_totals[band_key][raw_bucket] += 1
            classified = classify_band_result(case.get(band_key), case)
            case_bands[band_key] = {
                "raw": classified.raw,
                "bucket": classified.bucket,
                "fail_reason": classified.fail_reason,
            }

            for row in (
                band_category_index[(band_key, category)],
                bucket_totals[band_key],
            ):
                row["total_items"] += 1
                if classified.bucket == "Pass":
                    row["pass"] += 1
                elif classified.bucket == "Fail":
                    row["fail"] += 1
                elif classified.bucket == "To be confirmed":
                    row["to_be_tested"] += 1
                elif classified.bucket == "Not Supported":
                    row["not_supported"] += 1
                elif classified.bucket == "Skip":
                    row["skip"] += 1

        per_case.append(
            {
                "case_id": _normalize_text(case.get("case_id")),
                "source_row": source_row,
                "category": category,
                "bands": case_bands,
            }
        )

    band_category = [
        _finalize_summary_row(band_category_index[(band_key, category)])
        for band_key in BAND_KEYS
        for category in CATEGORIES
    ]
    bucket_totals = {
        band_key: _finalize_summary_row(bucket_totals[band_key])
        for band_key in BAND_KEYS
    }
    raw_totals_out = {
        band_key: dict(counter)
        for band_key, counter in raw_totals.items()
        if counter
    }

    return {
        "policy_version": SUMMARY_POLICY_VERSION,
        "band_category": band_category,
        "bucket_totals": bucket_totals,
        "raw_totals": raw_totals_out,
        "diagnostic_status": dict(diagnostic_totals),
        "per_case": per_case,
    }
