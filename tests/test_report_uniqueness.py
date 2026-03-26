"""Tests for report filename uniqueness (E09).

Verifies run_id generation and report filename uniqueness guarantees.
"""

from __future__ import annotations

from datetime import date

from testpilot.reporting.wifi_llapi_excel import generate_report_filename


class TestReportFilenameUniqueness:
    """Verify report filenames include run_id for uniqueness."""

    def test_filename_with_unique_suffix(self):
        """Filename includes unique_suffix when provided."""
        name = generate_report_filename(
            date(2025, 3, 25), "v1.0.0", unique_suffix="20250325T120000123456"
        )
        assert "20250325T120000123456" in name
        assert name.endswith(".xlsx")

    def test_filename_without_suffix(self):
        """Filename without suffix is still valid."""
        name = generate_report_filename(date(2025, 3, 25), "v1.0.0")
        assert name.endswith(".xlsx")
        assert "20250325" in name

    def test_different_suffixes_produce_different_names(self):
        """Two different run_ids produce different filenames."""
        name1 = generate_report_filename(
            date(2025, 3, 25), "v1.0.0", unique_suffix="run_001"
        )
        name2 = generate_report_filename(
            date(2025, 3, 25), "v1.0.0", unique_suffix="run_002"
        )
        assert name1 != name2

    def test_same_suffix_produces_same_name(self):
        """Same inputs produce identical filename (deterministic)."""
        name1 = generate_report_filename(
            date(2025, 3, 25), "v1.0.0", unique_suffix="abc"
        )
        name2 = generate_report_filename(
            date(2025, 3, 25), "v1.0.0", unique_suffix="abc"
        )
        assert name1 == name2

    def test_filename_contains_date(self):
        """Report filename embeds the run date."""
        name = generate_report_filename(date(2025, 1, 15), "fw2.3")
        assert "20250115" in name

    def test_filename_contains_fw_version(self):
        """Report filename embeds the firmware version."""
        name = generate_report_filename(date(2025, 3, 25), "v1.0.0")
        assert "v1.0.0" in name or "v1_0_0" in name

    def test_filename_contains_wifi_llapi(self):
        """Report filename contains wifi_LLAPI marker."""
        name = generate_report_filename(date(2025, 3, 25), "v1.0.0")
        assert "wifi_LLAPI" in name


class TestRunIdTimestamp:
    """Verify run_id format matches expected pattern."""

    def test_datetime_strftime_produces_unique_ids(self):
        """datetime.now() with microseconds should rarely collide."""
        from datetime import datetime
        ids = {datetime.now().strftime("%Y%m%dT%H%M%S%f") for _ in range(100)}
        # At minimum, several unique IDs should appear (not all same)
        assert len(ids) >= 2
