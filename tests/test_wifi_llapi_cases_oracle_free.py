"""Repo-scale guards for oracle-free wifi_llapi shipped cases."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

from testpilot.core.plugin_loader import PluginLoader
from testpilot.schema.case_schema import (
    CaseValidationError,
    load_case,
    validate_wifi_llapi_case,
)

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "plugins" / "wifi_llapi" / "cases"
FORBIDDEN_TOP_KEYS = {"results_reference"}
FORBIDDEN_SOURCE_KEYS = {"baseline", "report", "sheet"}
PLACEHOLDER_MARKERS = (
    "replace with actual test command",
    "replace with verification command",
    "expected output",
)


def _discoverable_case_paths() -> list[Path]:
    return sorted(path for path in CASES_DIR.glob("*.y*ml") if not path.stem.startswith("_"))


def _load_case_text_and_data(path: Path) -> tuple[str, dict]:
    text = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(text)
    assert isinstance(payload, dict), f"{path} must stay a YAML mapping"
    return text, payload


def test_all_wifi_llapi_cases_pass_schema() -> None:
    for path in _discoverable_case_paths():
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), f"{path} must stay a YAML mapping"
        validate_wifi_llapi_case(payload, path)


def test_no_shipped_case_contains_forbidden_fields() -> None:
    forbidden_top_pattern = re.compile(r"^results_reference\s*:", re.MULTILINE)

    for path in _discoverable_case_paths():
        text, payload = _load_case_text_and_data(path)
        assert not forbidden_top_pattern.search(text), f"{path} still contains results_reference"
        assert not (FORBIDDEN_TOP_KEYS & set(payload)), f"{path} still has forbidden top keys"

        source = payload.get("source")
        if isinstance(source, dict):
            forbidden_source = FORBIDDEN_SOURCE_KEYS & set(source)
            assert not forbidden_source, f"{path} still has forbidden source keys: {sorted(forbidden_source)}"


def test_no_discoverable_case_contains_template_placeholders() -> None:
    for path in _discoverable_case_paths():
        text = path.read_text(encoding="utf-8")
        for marker in PLACEHOLDER_MARKERS:
            assert marker not in text, f"{path} still contains placeholder marker: {marker!r}"


def test_discovery_matches_discoverable_case_files() -> None:
    loader = PluginLoader(ROOT / "plugins")
    plugin = loader.load("wifi_llapi")

    file_cases = [load_case(path) for path in _discoverable_case_paths()]
    file_ids = {str(case["id"]) for case in file_cases}
    discovered_cases = plugin.discover_cases()
    discovered_ids = {str(case["id"]) for case in discovered_cases}

    assert len(discovered_cases) == len(file_cases)
    assert discovered_ids == file_ids


def test_validate_wifi_llapi_case_rejects_injected_results_reference() -> None:
    clean_case = load_case(_discoverable_case_paths()[0])
    clean_case["results_reference"] = {"v4.0.3": {"5g": "Pass"}}

    with pytest.raises(CaseValidationError, match=r"#31 cleanup.*results_reference"):
        validate_wifi_llapi_case(clean_case, "<injected>")
