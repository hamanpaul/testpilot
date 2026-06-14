"""Golden snapshot test for wifi_llapi report output (Task 1.2 — decouple safety net).

Asserts that ``build_wifi_llapi_summary`` produces byte-for-byte identical
output to the committed snapshot in ``tests/golden/wifi_llapi_report_baseline.json``.

Intent: after the refactor moves wifi_llapi report generation out of core,
running this test proves the summary logic is behaviourally unchanged.

Snapshot limitations
--------------------
- Exercises the *pure-Python* summary layer (``build_wifi_llapi_summary``),
  which has no hardware dependency.
- The xlsx / markdown / alignment layers require an existing Excel template
  that is NOT committed to the repo (real-hardware artefact), so they are
  intentionally excluded from this snapshot.  Their deterministic helpers are
  covered by the existing ``test_wifi_llapi_excel.py`` / ``test_wifi_llapi_summary.py`` suites.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from plugins.wifi_llapi.reporting.wifi_llapi_summary import build_wifi_llapi_summary

_GOLDEN_PATH = Path(__file__).parent / "golden" / "wifi_llapi_report_baseline.json"


def _load_golden() -> dict:
    return json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))


def _row_objects_from_fixture(fixture: dict) -> dict[int, str]:
    """Convert string keys (JSON) back to int keys for row_objects."""
    return {int(k): v for k, v in fixture["row_objects"].items()}


def _approx_equal(a: object, b: object) -> bool:
    """Deep equality allowing float tolerance for pass_rate / progress fields."""
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(_approx_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_approx_equal(x, y) for x, y in zip(a, b))
    return a == b


class TestWifiLlapiReportGolden:
    """Golden snapshot assertions for the summary layer."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        golden = _load_golden()
        fixture = golden["_fixture"]
        self.expected = golden["expected_summary"]
        self.row_objects = _row_objects_from_fixture(fixture)
        self.case_results = fixture["case_results"]

    def test_policy_version_unchanged(self) -> None:
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert summary["policy_version"] == self.expected["policy_version"]

    def test_band_category_rows_unchanged(self) -> None:
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert len(summary["band_category"]) == len(self.expected["band_category"])
        for actual_row, expected_row in zip(summary["band_category"], self.expected["band_category"]):
            assert _approx_equal(actual_row, expected_row), (
                f"band_category row mismatch:\n  actual:   {actual_row}\n  expected: {expected_row}"
            )

    def test_bucket_totals_unchanged(self) -> None:
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert _approx_equal(summary["bucket_totals"], self.expected["bucket_totals"]), (
            f"bucket_totals mismatch:\n  actual:   {summary['bucket_totals']}\n  expected: {self.expected['bucket_totals']}"
        )

    def test_raw_totals_unchanged(self) -> None:
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert summary["raw_totals"] == self.expected["raw_totals"]

    def test_diagnostic_status_unchanged(self) -> None:
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert summary["diagnostic_status"] == self.expected["diagnostic_status"]

    def test_per_case_unchanged(self) -> None:
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert len(summary["per_case"]) == len(self.expected["per_case"])
        per_case_actual = {r["case_id"]: r for r in summary["per_case"]}
        per_case_expected = {r["case_id"]: r for r in self.expected["per_case"]}
        assert set(per_case_actual.keys()) == set(per_case_expected.keys())
        for case_id in per_case_expected:
            assert per_case_actual[case_id] == per_case_expected[case_id], (
                f"per_case mismatch for {case_id}:\n  actual:   {per_case_actual[case_id]}\n  expected: {per_case_expected[case_id]}"
            )

    def test_full_summary_matches_golden(self) -> None:
        """Single comprehensive assertion — the canonical guard."""
        summary = build_wifi_llapi_summary(self.case_results, self.row_objects)
        assert _approx_equal(summary, self.expected), (
            "Full summary does not match golden snapshot. "
            "If this is an intentional change, regenerate the snapshot by updating "
            "tests/golden/wifi_llapi_report_baseline.json."
        )
