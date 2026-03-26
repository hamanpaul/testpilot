"""Remediation planner — iterative failure analysis and fix suggestion loop.

Combines advisory outputs with agent role capabilities to build
remediation plans for persistent test failures.  The planner operates
as a post-run aggregation step, not during individual case execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

from testpilot.core.advisory import AdvisoryCollector, AdvisoryOutput

log = logging.getLogger(__name__)


@dataclass(slots=True)
class RemediationAction:
    """A single proposed remediation action."""

    action_id: str
    case_id: str
    action_type: str  # "config_change", "reboot", "firmware_update", "test_skip", "manual_review"
    description: str
    priority: int = 0  # higher = more important
    estimated_impact: str = ""  # "high", "medium", "low"
    prerequisites: list[str] = field(default_factory=list)
    auto_applicable: bool = False


@dataclass(slots=True)
class RemediationPlan:
    """Aggregated remediation plan for a test run."""

    run_id: str
    actions: list[RemediationAction] = field(default_factory=list)
    skipped_cases: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def action_count(self) -> int:
        return len(self.actions)

    @property
    def auto_applicable_actions(self) -> list[RemediationAction]:
        return [a for a in self.actions if a.auto_applicable]

    def actions_for_case(self, case_id: str) -> list[RemediationAction]:
        return [a for a in self.actions if a.case_id == case_id]

    def by_priority(self) -> list[RemediationAction]:
        return sorted(self.actions, key=lambda a: a.priority, reverse=True)

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for action in self.actions:
            by_type[action.action_type] = by_type.get(action.action_type, 0) + 1
        return {
            "run_id": self.run_id,
            "total_actions": self.action_count,
            "auto_applicable": len(self.auto_applicable_actions),
            "by_type": by_type,
            "skipped_cases": len(self.skipped_cases),
            "notes_count": len(self.notes),
        }


class RemediationPlanner:
    """Build remediation plans from advisory outputs and failure patterns."""

    def __init__(self, run_id: str = "") -> None:
        self.run_id = run_id
        self._action_counter = 0

    def _next_action_id(self) -> str:
        self._action_counter += 1
        return f"RA-{self._action_counter:03d}"

    def plan_from_advisories(
        self,
        collector: AdvisoryCollector,
        *,
        failed_case_ids: Sequence[str] = (),
    ) -> RemediationPlan:
        """Build a remediation plan from collected advisories.

        Processes advisories by severity (critical first), maps categories
        to action types, and deduplicates per-case actions.
        """
        plan = RemediationPlan(run_id=self.run_id)

        severity_order = {"critical": 4, "error": 3, "warning": 2, "info": 1}
        sorted_advisories = sorted(
            collector.all,
            key=lambda a: severity_order.get(a.severity, 0),
            reverse=True,
        )

        seen_case_categories: set[tuple[str, str]] = set()

        for advisory in sorted_advisories:
            key = (advisory.case_id, advisory.category)
            if key in seen_case_categories:
                continue
            seen_case_categories.add(key)

            action = self._advisory_to_action(advisory)
            if action is not None:
                plan.actions.append(action)

        # Mark failed cases with no advisories for manual review
        advised_cases = {a.case_id for a in collector.all}
        for case_id in failed_case_ids:
            if case_id not in advised_cases:
                plan.actions.append(RemediationAction(
                    action_id=self._next_action_id(),
                    case_id=case_id,
                    action_type="manual_review",
                    description=f"No advisory data for failed case {case_id}",
                    priority=1,
                ))

        return plan

    def _advisory_to_action(self, advisory: AdvisoryOutput) -> RemediationAction | None:
        """Map an advisory output to a remediation action."""
        category_to_type = {
            "configuration": "config_change",
            "environment": "reboot",
            "firmware": "firmware_update",
            "test_design": "test_skip",
            "flaky": "manual_review",
        }
        action_type = category_to_type.get(advisory.category, "manual_review")

        severity_to_priority = {"critical": 10, "error": 7, "warning": 4, "info": 1}
        priority = severity_to_priority.get(advisory.severity, 0)

        impact = "high" if advisory.confidence >= 0.8 else "medium" if advisory.confidence >= 0.5 else "low"

        return RemediationAction(
            action_id=self._next_action_id(),
            case_id=advisory.case_id,
            action_type=action_type,
            description=advisory.suggested_action or advisory.summary,
            priority=priority,
            estimated_impact=impact,
            auto_applicable=action_type == "config_change" and advisory.confidence >= 0.9,
        )
