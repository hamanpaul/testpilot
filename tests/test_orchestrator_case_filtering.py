"""Tests for Orchestrator case filtering — official vs underscore-prefixed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from testpilot.core.orchestrator import Orchestrator
from testpilot.schema.case_schema import CaseValidationError


def _make_orchestrator() -> Orchestrator:
    root = Path(__file__).resolve().parents[1]
    return Orchestrator(project_root=root)


def test_sanitize_case_id_normalizes():
    """_sanitize_case_id replaces non-alphanumeric with underscores."""
    assert Orchestrator._sanitize_case_id("wifi-llapi-D004-kickstation") == "wifi-llapi-D004-kickstation"
    assert Orchestrator._sanitize_case_id("  spaced  ") == "spaced"
    assert Orchestrator._sanitize_case_id("with/slashes") == "with_slashes"
    assert Orchestrator._sanitize_case_id("") == "case"


def test_case_aliases_returns_list():
    """_case_aliases extracts aliases from case dict."""
    case = {"id": "test-1", "aliases": ["alias-a", "alias-b"]}
    aliases = Orchestrator._case_aliases(case)
    assert aliases == ["alias-a", "alias-b"]


def test_case_aliases_returns_empty_for_missing():
    """_case_aliases returns empty list when no aliases."""
    assert Orchestrator._case_aliases({}) == []
    assert Orchestrator._case_aliases({"aliases": "not-a-list"}) == []


def test_case_matches_requested_ids():
    """_case_matches_requested_ids matches on id or aliases."""
    case = {"id": "wifi-llapi-D004-kickstation", "aliases": ["D004"]}
    assert Orchestrator._case_matches_requested_ids(case, {"D004"}) is True
    assert Orchestrator._case_matches_requested_ids(case, {"wifi-llapi-D004-kickstation"}) is True
    assert Orchestrator._case_matches_requested_ids(case, {"D999"}) is False
    assert Orchestrator._case_matches_requested_ids(case, set()) is False


def test_is_wifi_llapi_official_case_d_prefix():
    """Official cases start with D followed by digits."""
    assert Orchestrator._is_wifi_llapi_official_case({"id": "wifi-llapi-D004-kickstation"}) is True
    assert Orchestrator._is_wifi_llapi_official_case({"id": "D004"}) is True
    assert Orchestrator._is_wifi_llapi_official_case({"id": "d121"}) is True


def test_is_wifi_llapi_official_case_rejects_underscore():
    """Underscore-prefixed and non-D### cases are not official."""
    assert Orchestrator._is_wifi_llapi_official_case({"id": "_legacy_compat"}) is False
    assert Orchestrator._is_wifi_llapi_official_case({"id": "custom-test"}) is False
    assert Orchestrator._is_wifi_llapi_official_case({"id": ""}) is False


def test_discover_wifi_llapi_cases_excludes_underscore_prefix():
    """Discovered wifi_llapi cases should not include underscore-prefixed files."""
    orch = _make_orchestrator()
    cases = orch.list_cases("wifi_llapi")
    ids = [c.get("id", "") for c in cases]
    underscore_cases = [cid for cid in ids if cid.startswith("_")]
    assert len(underscore_cases) == 0, f"Underscore-prefixed cases leaked: {underscore_cases}"


def test_discover_wifi_llapi_has_420_official_cases():
    """wifi_llapi should have exactly 420 official discoverable cases."""
    orch = _make_orchestrator()
    cases = orch.list_cases("wifi_llapi")
    official = [c for c in cases if Orchestrator._is_wifi_llapi_official_case(c)]
    assert len(official) == 420, f"Expected 420 official cases, got {len(official)}"


def test_load_wifi_llapi_case_pairs_rejects_results_reference_on_run_path(tmp_path, monkeypatch):
    """wifi_llapi orchestrator run-path must enforce the strict validator."""
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "D001_invalid.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "wifi-llapi-D001-invalid",
                "name": "invalid",
                "source": {"row": 1, "object": "WiFi.AccessPoint.{i}.", "api": "kickStation()"},
                "topology": {"devices": {"DUT": {"role": "ap"}}},
                "steps": [{"id": "s1", "action": "exec", "target": "DUT"}],
                "pass_criteria": [{"field": "x", "operator": "==", "value": "y"}],
                "results_reference": {"v4.0.3": {"5g": "Pass"}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    orch = _make_orchestrator()

    fake_plugin = type("_FakePlugin", (), {"cases_dir": cases_dir})()

    with pytest.raises(CaseValidationError, match=r"#31 cleanup.*results_reference"):
        orch._load_wifi_llapi_case_pairs(plugin=fake_plugin, case_ids=None)
