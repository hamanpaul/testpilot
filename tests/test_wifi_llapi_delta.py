from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from testpilot.core.orchestrator import Orchestrator
from testpilot.core.plugin_loader import PluginLoader
from testpilot.reporting.wifi_llapi_align import AlignResult

ROOT = Path(__file__).resolve().parents[1]


def _load_plugin() -> Any:
    loader = PluginLoader(ROOT / "plugins")
    return loader.load("wifi_llapi")


Plugin = _load_plugin().__class__
ZERO_DELTA_COMMENT = "fail 原因為 0，數值無變化"
DELTA_NOT_NUMERIC_COMMENT = "fail 原因為 delta 端點非數值"


def _case(*, criteria: list[dict[str, Any]], steps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": "D999",
        "name": "delta test",
        "steps": steps
        or [
            {"id": "baseline", "phase": "baseline"},
            {"id": "trigger", "phase": "trigger"},
            {"id": "verify", "phase": "verify"},
        ],
        "pass_criteria": criteria,
    }


def _results(step_values: dict[str, Any]) -> dict[str, Any]:
    steps: dict[str, Any] = {}
    for step_id, value in step_values.items():
        item = {"success": True, "output": ""}
        if value is not None:
            item["captured"] = {"value": value}
        steps[step_id] = item
    return {"steps": steps}


def _delta_nonzero_case(*, baseline_path: str = "baseline.captured.value", verify_path: str = "verify.captured.value") -> dict[str, Any]:
    return _case(
        criteria=[
            {
                "delta": {"baseline": baseline_path, "verify": verify_path},
                "operator": "delta_nonzero",
            }
        ]
    )


def _delta_match_case(*, tolerance_pct: int | None = None) -> dict[str, Any]:
    criterion: dict[str, Any] = {
        "delta": {
            "baseline": "baseline_api.captured.value",
            "verify": "verify_api.captured.value",
        },
        "reference_delta": {
            "baseline": "baseline_drv.captured.value",
            "verify": "verify_drv.captured.value",
        },
        "operator": "delta_match",
    }
    if tolerance_pct is not None:
        criterion["tolerance_pct"] = tolerance_pct
    return _case(
        criteria=[criterion],
        steps=[
            {"id": "baseline_api", "phase": "baseline"},
            {"id": "baseline_drv", "phase": "baseline"},
            {"id": "trigger", "phase": "trigger"},
            {"id": "verify_api", "phase": "verify"},
            {"id": "verify_drv", "phase": "verify"},
        ],
    )


def test_delta_nonzero_pass() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "42"})) is True
    assert "_last_failure" not in case


def test_delta_nonzero_fail_zero() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "10"})) is False
    assert case["_last_failure"]["reason_code"] == "delta_zero"
    assert case["_last_failure"]["comment"] == ZERO_DELTA_COMMENT


def test_delta_nonzero_fail_negative() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "5"})) is False
    assert case["_last_failure"]["reason_code"] == "delta_zero"
    assert case["_last_failure"]["comment"] == ZERO_DELTA_COMMENT


def test_delta_nonzero_baseline_missing() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case(baseline_path="missing.captured.value")

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "42"})) is False
    assert case["_last_failure"]["reason_code"] == "delta_value_not_numeric"
    assert case["_last_failure"]["comment"] == DELTA_NOT_NUMERIC_COMMENT


def test_delta_nonzero_non_numeric() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "N/A"})) is False
    assert case["_last_failure"]["reason_code"] == "delta_value_not_numeric"
    assert case["_last_failure"]["comment"] == DELTA_NOT_NUMERIC_COMMENT


def test_delta_match_pass_within_tolerance() -> None:
    plugin = Plugin()
    case = _delta_match_case(tolerance_pct=10)

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "0",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "100",
                    "verify_drv": "109",
                }
            ),
        )
        is True
    )


def test_delta_match_pass_exact_match() -> None:
    plugin = Plugin()
    case = _delta_match_case()

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "0",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "100",
                    "verify_drv": "100",
                }
            ),
        )
        is True
    )


def test_delta_match_fail_exceed_tolerance() -> None:
    plugin = Plugin()
    case = _delta_match_case(tolerance_pct=10)

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "0",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "100",
                    "verify_drv": "120",
                }
            ),
        )
        is False
    )
    assert case["_last_failure"]["reason_code"] == "delta_mismatch"
    assert case["_last_failure"]["comment"] == "fail 原因為 delta 不一致：api=100 drv=120 tol=10%"


def test_delta_match_fail_one_side_zero() -> None:
    plugin = Plugin()
    case = _delta_match_case(tolerance_pct=10)

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "0",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "100",
                    "verify_drv": "0",
                }
            ),
        )
        is False
    )
    assert case["_last_failure"]["reason_code"] == "delta_zero_side"
    assert case["_last_failure"]["comment"] == ZERO_DELTA_COMMENT


def test_delta_match_fail_both_zero() -> None:
    plugin = Plugin()
    case = _delta_match_case(tolerance_pct=10)

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "0",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "0",
                    "verify_drv": "0",
                }
            ),
        )
        is False
    )
    assert case["_last_failure"]["reason_code"] == "delta_zero_side"
    assert case["_last_failure"]["comment"] == ZERO_DELTA_COMMENT


def test_delta_match_fail_negative_either_side() -> None:
    plugin = Plugin()
    case = _delta_match_case(tolerance_pct=10)

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "10",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "5",
                    "verify_drv": "100",
                }
            ),
        )
        is False
    )
    assert case["_last_failure"]["reason_code"] == "delta_zero_side"
    assert case["_last_failure"]["comment"] == ZERO_DELTA_COMMENT


def test_delta_match_tolerance_boundary() -> None:
    plugin = Plugin()
    case = _delta_match_case(tolerance_pct=10)

    assert (
        plugin.evaluate(
            case,
            _results(
                {
                    "baseline_api": "0",
                    "baseline_drv": "0",
                    "trigger": None,
                    "verify_api": "100",
                    "verify_drv": "110",
                }
            ),
        )
        is True
    )


def test_phase_ok_baseline_trigger_verify() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()

    assert plugin._validate_phase_ordering(case) is None


def test_phase_no_delta_skip_check() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[{"field": "verify.captured.value", "operator": "equals", "value": "ok"}],
        steps=[
            {"id": "s1", "phase": "warmup"},
            {"id": "s2", "phase": "baseline"},
        ],
    )

    assert plugin._validate_phase_ordering(case) is None


def test_phase_missing_trigger() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "verify", "phase": "verify"},
        ],
    )

    assert plugin._validate_phase_ordering(case) == "delta_* operators require at least one phase=trigger step"


def test_phase_baseline_after_trigger() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "trigger", "phase": "trigger"},
            {"id": "baseline2", "phase": "baseline"},
            {"id": "verify", "phase": "verify"},
        ],
    )

    assert "baseline step must precede trigger" in plugin._validate_phase_ordering(case)


def test_phase_verify_before_trigger() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "verify", "phase": "verify"},
            {"id": "trigger", "phase": "trigger"},
        ],
    )

    assert "verify step must follow trigger" in plugin._validate_phase_ordering(case)


def test_phase_trigger_after_verify() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "trigger", "phase": "trigger"},
            {"id": "verify", "phase": "verify"},
            {"id": "trigger2", "phase": "trigger"},
        ],
    )

    assert plugin._validate_phase_ordering(case) == "trigger step must precede verify"


def test_phase_default_unmarked_is_verify() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "trigger", "phase": "trigger"},
            {"id": "verify"},
        ],
    )

    assert plugin._validate_phase_ordering(case) is None


def test_phase_invalid_value() -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()
    case["steps"][0]["phase"] = "warmup"

    assert plugin._validate_phase_ordering(case) == "unknown phase: warmup"


@pytest.mark.parametrize(
    ("criterion", "expected"),
    [
        (
            {"delta": {}, "operator": "delta_nonzero"},
            "delta must be a mapping with non-empty baseline/verify",
        ),
        (
            {"delta": "baseline.captured.value", "operator": "delta_nonzero"},
            "delta must be a mapping with non-empty baseline/verify",
        ),
        (
            {"delta": {"baseline": "baseline.captured.value"}, "operator": "delta_nonzero"},
            "delta.verify must be a non-empty string",
        ),
        (
            {"delta": {"baseline": "", "verify": "verify.captured.value"}, "operator": "delta_nonzero"},
            "delta.baseline must be a non-empty string",
        ),
        (
            {
                "delta": {"baseline": "baseline_api.captured.value", "verify": "verify_api.captured.value"},
                "operator": "delta_match",
            },
            "reference_delta must be a mapping with non-empty baseline/verify",
        ),
        (
            {
                "delta": {"baseline": "baseline_api.captured.value", "verify": "verify_api.captured.value"},
                "reference_delta": "baseline_drv.captured.value",
                "operator": "delta_match",
            },
            "reference_delta must be a mapping with non-empty baseline/verify",
        ),
        (
            {
                "delta": {"baseline": "baseline_api.captured.value", "verify": "verify_api.captured.value"},
                "reference_delta": {"baseline": "baseline_drv.captured.value"},
                "operator": "delta_match",
            },
            "reference_delta.verify must be a non-empty string",
        ),
    ],
)
def test_validate_delta_schema_rejects_malformed_structures(
    criterion: dict[str, Any],
    expected: str,
) -> None:
    plugin = Plugin()
    case = _case(criteria=[criterion])

    assert plugin._validate_delta_schema(case) == expected


def test_evaluate_field_path_unchanged() -> None:
    plugin = Plugin()
    case = _case(criteria=[{"field": "verify.captured.value", "operator": "equals", "value": "expected"}])

    assert plugin.evaluate(case, _results({"baseline": None, "trigger": None, "verify": "actual"})) is False
    assert case["_last_failure"]["reason_code"] == "pass_criteria_not_satisfied"
    assert case["_last_failure"]["comment"] == "pass_criteria not satisfied"


def test_evaluate_delta_path_picks_new_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = Plugin()
    case = _delta_nonzero_case()

    monkeypatch.setattr(plugin, "_compare", lambda *args, **kwargs: pytest.fail("_compare should not run for delta criteria"))

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "42"})) is True


def test_evaluate_mixed_criteria(monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = Plugin()
    case = _case(
        criteria=[
            {"field": "verify.captured.value", "operator": "equals", "value": "100"},
            {
                "delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"},
                "operator": "delta_nonzero",
            },
            {"field": "verify.captured.value", "operator": "equals", "value": "never"},
        ]
    )
    calls: list[str] = []
    original = plugin._evaluate_delta_criterion

    def _spy(case_data: dict[str, Any], context: dict[str, Any], criterion: dict[str, Any], idx: int) -> bool:
        calls.append(f"delta:{idx}")
        return original(case_data, context, criterion, idx)

    monkeypatch.setattr(plugin, "_evaluate_delta_criterion", _spy)

    assert plugin.evaluate(case, _results({"baseline": "100", "trigger": None, "verify": "100"})) is False
    assert calls == ["delta:1"]
    assert case["_last_failure"]["reason_code"] == "delta_zero"


def test_unknown_delta_operator_cannot_pass() -> None:
    plugin = Plugin()
    case = _case(
        criteria=[
            {
                "delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"},
                "operator": "delta_surprise",
            }
        ]
    )

    assert plugin.evaluate(case, _results({"baseline": "10", "trigger": None, "verify": "42"})) is False
    assert case["_last_failure"]["reason_code"] == "invalid_delta_operator"


def test_invalid_delta_schema_marks_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    valid = _delta_nonzero_case()
    valid["id"] = "D-valid"
    invalid = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "verify", "phase": "verify"},
        ],
    )
    invalid["id"] = "D-invalid"

    monkeypatch.setitem(Plugin.discover_cases.__globals__, "load_cases_dir", lambda *args, **kwargs: [valid, invalid])

    cases = {case["id"]: case for case in Plugin().discover_cases()}

    assert set(cases) == {"D-valid", "D-invalid"}
    assert cases["D-valid"].get("blocked_reason") is None
    assert cases["D-invalid"]["llapi_support"] == "Blocked"
    assert cases["D-invalid"]["blocked_reason"] == "invalid_delta_schema: delta_* operators require at least one phase=trigger step"


def test_runtime_prep_blocks_invalid_delta_schema_before_alignment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plugin = _load_plugin()
    orch = object.__new__(Orchestrator)
    valid_path = tmp_path / "D001_valid.yaml"
    invalid_path = tmp_path / "D002_invalid.yaml"
    valid = _delta_nonzero_case()
    valid["id"] = "D-valid"
    valid["source"] = {"row": 1, "object": "Device.WiFi.", "api": "Valid()"}
    invalid = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value", "verify": "verify.captured.value"}, "operator": "delta_nonzero"}],
        steps=[
            {"id": "baseline", "phase": "baseline"},
            {"id": "verify", "phase": "verify"},
        ],
    )
    invalid["id"] = "D-invalid"
    invalid["source"] = {"row": 2, "object": "Device.WiFi.", "api": "Invalid()"}
    seen_align_ids: list[str] = []
    loaded_cases = {valid_path: {"id": "D-valid-loaded"}}

    monkeypatch.setattr(
        orch,
        "_load_wifi_llapi_case_pairs",
        lambda **kwargs: [(valid_path, valid), (invalid_path, invalid)],
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "build_template_index",
        lambda template_path: object(),
    )

    def fake_align_case(case: dict[str, Any], index: object, path: Path) -> AlignResult:
        seen_align_ids.append(case["id"])
        return AlignResult(
            case_file=path,
            status="already_aligned",
            source_row_before=int(case["source"]["row"]),
            source_row_after=int(case["source"]["row"]),
            source_object=str(case["source"]["object"]),
            source_api=str(case["source"]["api"]),
            filename_before=path.name,
            filename_after=None,
            id_before=str(case["id"]),
            id_after=None,
        )

    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "align_case",
        fake_align_case,
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "_resolve_collisions",
        lambda results: None,
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "apply_alignment_mutations",
        lambda results: None,
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "load_case",
        lambda path, validator=None: loaded_cases[path],
    )

    prep = orch._prepare_wifi_llapi_alignment(
        plugin=plugin,
        case_ids=None,
        template_path=tmp_path / "wifi_llapi_template.xlsx",
    )

    assert seen_align_ids == ["D-valid"]
    assert prep.runnable_cases == [{"id": "D-valid-loaded"}]
    assert len(prep.blocked_results) == 1
    assert prep.blocked_results[0].id_before == "D-invalid"
    assert (
        prep.blocked_results[0].blocked_reason
        == "invalid_delta_schema: delta_* operators require at least one phase=trigger step"
    )
    assert prep.alignment_summary["blocked"] == 1
    assert prep.alignment_summary["blocked_details"] == [
        {
            "case_id": "D-invalid",
            "reason": "invalid_delta_schema: delta_* operators require at least one phase=trigger step",
            "candidate_template_rows": [],
        }
    ]


def test_runtime_prep_blocks_malformed_delta_schema_before_alignment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plugin = _load_plugin()
    orch = object.__new__(Orchestrator)
    valid_path = tmp_path / "D001_valid.yaml"
    invalid_path = tmp_path / "D002_invalid.yaml"
    valid = _delta_nonzero_case()
    valid["id"] = "D-valid"
    valid["source"] = {"row": 1, "object": "Device.WiFi.", "api": "Valid()"}
    invalid = _case(
        criteria=[{"delta": {"baseline": "baseline.captured.value"}, "operator": "delta_nonzero"}],
    )
    invalid["id"] = "D-invalid"
    invalid["source"] = {"row": 2, "object": "Device.WiFi.", "api": "Invalid()"}
    seen_align_ids: list[str] = []
    loaded_cases = {valid_path: {"id": "D-valid-loaded"}}

    monkeypatch.setattr(
        orch,
        "_load_wifi_llapi_case_pairs",
        lambda **kwargs: [(valid_path, valid), (invalid_path, invalid)],
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "build_template_index",
        lambda template_path: object(),
    )

    def fake_align_case(case: dict[str, Any], index: object, path: Path) -> AlignResult:
        seen_align_ids.append(case["id"])
        return AlignResult(
            case_file=path,
            status="already_aligned",
            source_row_before=int(case["source"]["row"]),
            source_row_after=int(case["source"]["row"]),
            source_object=str(case["source"]["object"]),
            source_api=str(case["source"]["api"]),
            filename_before=path.name,
            filename_after=None,
            id_before=str(case["id"]),
            id_after=None,
        )

    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "align_case",
        fake_align_case,
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "_resolve_collisions",
        lambda results: None,
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "apply_alignment_mutations",
        lambda results: None,
    )
    monkeypatch.setitem(
        Orchestrator._prepare_wifi_llapi_alignment.__globals__,
        "load_case",
        lambda path, validator=None: loaded_cases[path],
    )

    prep = orch._prepare_wifi_llapi_alignment(
        plugin=plugin,
        case_ids=None,
        template_path=tmp_path / "wifi_llapi_template.xlsx",
    )

    assert seen_align_ids == ["D-valid"]
    assert prep.runnable_cases == [{"id": "D-valid-loaded"}]
    assert len(prep.blocked_results) == 1
    assert prep.blocked_results[0].id_before == "D-invalid"
    assert (
        prep.blocked_results[0].blocked_reason
        == "invalid_delta_schema: delta.verify must be a non-empty string"
    )
