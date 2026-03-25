"""Tests for Orchestrator case filtering — official vs underscore-prefixed."""

from __future__ import annotations

import re
from pathlib import Path

from testpilot.core.orchestrator import Orchestrator


def _make_orchestrator() -> Orchestrator:
    root = Path(__file__).resolve().parents[1]
    return Orchestrator(project_root=root)


def test_sanitize_case_id_normalizes():
    """_sanitize_case_id replaces non-alphanumeric with underscores."""
    assert Orchestrator._sanitize_case_id("wifi-llapi-D006-kickstation") == "wifi-llapi-D006-kickstation"
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
    case = {"id": "wifi-llapi-D006-kickstation", "aliases": ["D006"]}
    assert Orchestrator._case_matches_requested_ids(case, {"D006"}) is True
    assert Orchestrator._case_matches_requested_ids(case, {"wifi-llapi-D006-kickstation"}) is True
    assert Orchestrator._case_matches_requested_ids(case, {"D999"}) is False
    assert Orchestrator._case_matches_requested_ids(case, set()) is False


def test_is_wifi_llapi_official_case_d_prefix():
    """Official cases start with D followed by digits."""
    assert Orchestrator._is_wifi_llapi_official_case({"id": "wifi-llapi-D006-kickstation"}) is True
    assert Orchestrator._is_wifi_llapi_official_case({"id": "D006"}) is True
    assert Orchestrator._is_wifi_llapi_official_case({"id": "d123"}) is True


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
