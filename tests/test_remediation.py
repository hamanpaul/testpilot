"""Tests for remediation planner module."""

from __future__ import annotations

import pytest
from testpilot.core.advisory import AdvisoryCollector, AdvisoryOutput
from testpilot.core.remediation import (
    RemediationAction,
    RemediationPlan,
    RemediationPlanner,
)


# -- RemediationAction -------------------------------------------------------

class TestRemediationAction:
    def test_creation(self):
        action = RemediationAction(
            action_id="RA-001",
            case_id="D001",
            action_type="config_change",
            description="Fix SSID configuration",
        )
        assert action.action_id == "RA-001"
        assert action.auto_applicable is False

    def test_defaults(self):
        action = RemediationAction(
            action_id="RA-001", case_id="D001",
            action_type="manual_review", description="check",
        )
        assert action.priority == 0
        assert action.prerequisites == []
        assert action.estimated_impact == ""


# -- RemediationPlan ---------------------------------------------------------

class TestRemediationPlan:
    def test_empty_plan(self):
        plan = RemediationPlan(run_id="test-run")
        assert plan.action_count == 0
        assert plan.auto_applicable_actions == []
        assert plan.by_priority() == []

    def test_actions_for_case(self):
        plan = RemediationPlan(run_id="run1", actions=[
            RemediationAction("RA-001", "D001", "config_change", "fix1"),
            RemediationAction("RA-002", "D002", "reboot", "fix2"),
            RemediationAction("RA-003", "D001", "manual_review", "fix3"),
        ])
        d001 = plan.actions_for_case("D001")
        assert len(d001) == 2
        assert all(a.case_id == "D001" for a in d001)

    def test_by_priority(self):
        plan = RemediationPlan(run_id="run1", actions=[
            RemediationAction("RA-001", "D001", "a", "low", priority=1),
            RemediationAction("RA-002", "D002", "b", "high", priority=10),
            RemediationAction("RA-003", "D003", "c", "mid", priority=5),
        ])
        sorted_actions = plan.by_priority()
        assert [a.priority for a in sorted_actions] == [10, 5, 1]

    def test_auto_applicable(self):
        plan = RemediationPlan(run_id="run1", actions=[
            RemediationAction("RA-001", "D001", "a", "fix1", auto_applicable=True),
            RemediationAction("RA-002", "D002", "b", "fix2", auto_applicable=False),
        ])
        assert len(plan.auto_applicable_actions) == 1
        assert plan.auto_applicable_actions[0].action_id == "RA-001"

    def test_summary(self):
        plan = RemediationPlan(
            run_id="run1",
            actions=[
                RemediationAction("RA-001", "D001", "config_change", "fix1", auto_applicable=True),
                RemediationAction("RA-002", "D002", "reboot", "fix2"),
                RemediationAction("RA-003", "D003", "config_change", "fix3"),
            ],
            skipped_cases=["D097"],
            notes=["note1"],
        )
        s = plan.summary()
        assert s["total_actions"] == 3
        assert s["auto_applicable"] == 1
        assert s["by_type"] == {"config_change": 2, "reboot": 1}
        assert s["skipped_cases"] == 1
        assert s["notes_count"] == 1


# -- RemediationPlanner ------------------------------------------------------

class TestRemediationPlanner:
    def _make_advisory(
        self, case_id: str, severity: str = "warning",
        category: str = "configuration", confidence: float = 0.5,
    ) -> AdvisoryOutput:
        return AdvisoryOutput(
            case_id=case_id,
            severity=severity,
            category=category,
            summary=f"issue in {case_id}",
            suggested_action=f"fix {case_id}",
            confidence=confidence,
        )

    def test_plan_from_empty_advisories(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        plan = planner.plan_from_advisories(collector)
        assert plan.action_count == 0

    def test_plan_from_single_advisory(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001"))
        plan = planner.plan_from_advisories(collector)
        assert plan.action_count == 1
        assert plan.actions[0].case_id == "D001"
        assert plan.actions[0].action_type == "config_change"

    def test_severity_ordering(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001", severity="info"))
        collector.add(self._make_advisory("D002", severity="critical"))
        collector.add(self._make_advisory("D003", severity="error"))
        plan = planner.plan_from_advisories(collector)
        # Critical should get highest priority
        sorted_plan = plan.by_priority()
        assert sorted_plan[0].case_id == "D002"

    def test_category_to_action_type_mapping(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        for category, expected_type in [
            ("configuration", "config_change"),
            ("environment", "reboot"),
            ("firmware", "firmware_update"),
            ("test_design", "test_skip"),
            ("flaky", "manual_review"),
        ]:
            collector.add(self._make_advisory(f"D-{category}", category=category))
        plan = planner.plan_from_advisories(collector)
        action_types = {a.case_id: a.action_type for a in plan.actions}
        assert action_types["D-configuration"] == "config_change"
        assert action_types["D-environment"] == "reboot"
        assert action_types["D-firmware"] == "firmware_update"
        assert action_types["D-test_design"] == "test_skip"
        assert action_types["D-flaky"] == "manual_review"

    def test_deduplication_per_case_category(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001", category="configuration"))
        collector.add(self._make_advisory("D001", category="configuration"))
        plan = planner.plan_from_advisories(collector)
        assert plan.action_count == 1  # deduplicated

    def test_failed_cases_without_advisories(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001"))
        plan = planner.plan_from_advisories(
            collector, failed_case_ids=["D001", "D002", "D003"]
        )
        # D001 has advisory, D002/D003 get manual_review
        manual = [a for a in plan.actions if a.action_type == "manual_review"]
        assert len(manual) == 2
        manual_cases = {a.case_id for a in manual}
        assert manual_cases == {"D002", "D003"}

    def test_auto_applicable_high_confidence(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001", confidence=0.95))
        plan = planner.plan_from_advisories(collector)
        assert plan.actions[0].auto_applicable is True

    def test_not_auto_applicable_low_confidence(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001", confidence=0.5))
        plan = planner.plan_from_advisories(collector)
        assert plan.actions[0].auto_applicable is False

    def test_estimated_impact_levels(self):
        planner = RemediationPlanner(run_id="run1")
        collector = AdvisoryCollector()
        collector.add(self._make_advisory("D001", confidence=0.9, category="environment"))
        collector.add(self._make_advisory("D002", confidence=0.6, category="firmware"))
        collector.add(self._make_advisory("D003", confidence=0.2, category="flaky"))
        plan = planner.plan_from_advisories(collector)
        impacts = {a.case_id: a.estimated_impact for a in plan.actions}
        assert impacts["D001"] == "high"
        assert impacts["D002"] == "medium"
        assert impacts["D003"] == "low"
