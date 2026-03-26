"""ExecutionEngine — case execution with retry, timeout escalation, and trace writing."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from testpilot.core.case_utils import safe_float, safe_int
from testpilot.core.hook_policy import HookContext, HookDispatcher, HookResult
from testpilot.core.runner_selector import RunnerSelector

log = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryResult:
    """Structured result of a case execution with full retry history."""

    verdict: bool
    comment: str
    commands: list[str]
    outputs: list[str]
    attempts: list[dict[str, Any]]
    attempts_used: int
    max_attempts: int


class ExecutionEngine:
    """Execute a single case through plugin hooks with retry and timeout escalation."""

    def __init__(
        self,
        config: Any,
        hook_dispatcher: HookDispatcher | None = None,
    ) -> None:
        self.config = config
        self.hooks = hook_dispatcher or HookDispatcher()

    @staticmethod
    def attempt_timeout_seconds(
        *,
        steps_count: int,
        attempt_index: int,
        execution_policy: dict[str, Any],
    ) -> float:
        timeout = execution_policy.get("timeout", {})
        if not isinstance(timeout, dict):
            timeout = {}
        base_seconds = max(1.0, safe_float(timeout.get("base_seconds"), 120.0))
        per_step_seconds = max(0.0, safe_float(timeout.get("per_step_seconds"), 45.0))
        retry_multiplier = max(1.0, safe_float(timeout.get("retry_multiplier"), 1.25))
        max_seconds = max(1.0, safe_float(timeout.get("max_seconds"), 900.0))

        raw_timeout = (base_seconds + max(0, steps_count) * per_step_seconds) * (
            retry_multiplier ** max(0, attempt_index - 1)
        )
        return min(max_seconds, raw_timeout)

    def _hook_ctx(
        self,
        hook_name: str,
        case: dict[str, Any],
        runner: dict[str, Any],
        attempt_index: int = 1,
        step_id: str | None = None,
    ) -> HookContext:
        return HookContext(
            hook_name=hook_name,
            case_id=str(case.get("id", "?")),
            plugin_name=str(case.get("_plugin", "")),
            attempt_index=attempt_index,
            step_id=step_id,
            runner=dict(runner),
        )

    def execute_case_once(
        self,
        plugin: Any,
        case: dict[str, Any],
        *,
        attempt_index: int,
        attempt_timeout_seconds: float,
        runner: dict[str, Any],
    ) -> dict[str, Any]:
        """Run setup → verify → steps → evaluate → teardown for one attempt."""
        commands: list[str] = []
        outputs: list[str] = []
        verdict = False
        comment = ""

        runtime_case = dict(case)
        runtime_case["_agent_runner"] = RunnerSelector.runner_summary(runner)
        runtime_case["_attempt_index"] = attempt_index
        runtime_case["_attempt_timeout_seconds"] = attempt_timeout_seconds

        try:
            setup_ok = bool(plugin.setup_env(runtime_case, topology=self.config))
            if not setup_ok:
                comment = "setup_env failed"
            env_ok = setup_ok and bool(plugin.verify_env(runtime_case, topology=self.config))
            if setup_ok and not env_ok:
                comment = "env_verify gate failed"

            step_results: dict[str, Any] = {}
            raw_steps = runtime_case.get("steps", [])
            steps = raw_steps if isinstance(raw_steps, list) else []
            if env_ok:
                for step in steps:
                    step_data = dict(step) if isinstance(step, dict) else {"id": "step", "command": str(step)}
                    step_id = str(step_data.get("id", "step"))
                    command = str(step_data.get("command", "")).strip()
                    if command:
                        commands.append(command)

                    step_payload = dict(step_data)
                    step_payload.setdefault("timeout", attempt_timeout_seconds)
                    step_payload["_attempt_index"] = attempt_index
                    step_payload["_attempt_timeout_seconds"] = attempt_timeout_seconds

                    # pre_step hook
                    pre = self.hooks.dispatch(
                        self._hook_ctx("pre_step", runtime_case, runner, attempt_index, step_id),
                        {"step": step_payload},
                    )
                    if not pre.proceed:
                        comment = f"pre_step hook halted: {pre.advice}"
                        break

                    result = plugin.execute_step(runtime_case, step_payload, topology=self.config)
                    step_results[step_id] = result
                    out = str(result.get("output", "")).strip()
                    if out:
                        outputs.append(out)

                    # post_step hook
                    self.hooks.dispatch(
                        self._hook_ctx("post_step", runtime_case, runner, attempt_index, step_id),
                        {"step": step_payload, "result": result},
                    )

                    if not bool(result.get("success", False)):
                        comment = f"step failed: {step_id}"
                        # on_failure hook
                        self.hooks.dispatch(
                            self._hook_ctx("on_failure", runtime_case, runner, attempt_index, step_id),
                            {"step": step_payload, "result": result, "comment": comment},
                        )
                        break

                if not comment:
                    verdict = bool(plugin.evaluate(runtime_case, {"steps": step_results}))
                    if not verdict:
                        comment = "pass_criteria not satisfied"

        except Exception as exc:  # pragma: no cover - defensive catch for runtime errors
            comment = f"exception: {exc}"
        finally:
            try:
                plugin.teardown(runtime_case, topology=self.config)
            except Exception:
                log.exception("teardown failed: %s", runtime_case.get("id", "?"))

        return {
            "verdict": verdict,
            "comment": comment,
            "commands": commands,
            "outputs": outputs,
        }

    def execute_with_retry(
        self,
        plugin: Any,
        case: dict[str, Any],
        *,
        runner: dict[str, Any],
        execution_policy: dict[str, Any],
    ) -> RetryResult:
        """Execute a case with retry logic and return full attempt history."""
        retry_cfg = execution_policy.get("retry", {})
        if not isinstance(retry_cfg, dict):
            retry_cfg = {}
        max_attempts = max(1, safe_int(retry_cfg.get("max_attempts"), 1))
        failure_policy = str(
            execution_policy.get("failure_policy", "retry_then_fail_and_continue")
        )

        raw_steps = case.get("steps", [])
        steps_count = len(raw_steps) if isinstance(raw_steps, list) else 0

        attempts: list[dict[str, Any]] = []
        final_verdict = False
        final_commands: list[str] = []
        final_outputs: list[str] = []
        final_comment = ""

        # pre_case hook
        self.hooks.dispatch(
            self._hook_ctx("pre_case", case, runner),
            {"execution_policy": execution_policy, "max_attempts": max_attempts},
        )

        for attempt_index in range(1, max_attempts + 1):
            # on_retry hook (for attempts after the first)
            if attempt_index > 1:
                self.hooks.dispatch(
                    self._hook_ctx("on_retry", case, runner, attempt_index),
                    {"previous_attempts": attempts, "attempt_index": attempt_index},
                )

            timeout = self.attempt_timeout_seconds(
                steps_count=steps_count,
                attempt_index=attempt_index,
                execution_policy=execution_policy,
            )
            result = self.execute_case_once(
                plugin=plugin,
                case=case,
                attempt_index=attempt_index,
                attempt_timeout_seconds=timeout,
                runner=runner,
            )

            final_verdict = bool(result.get("verdict", False))
            final_commands = [str(x) for x in result.get("commands", [])]
            final_outputs = [str(x) for x in result.get("outputs", [])]
            final_comment = str(result.get("comment", ""))

            attempts.append({
                "attempt": attempt_index,
                "timeout_seconds": timeout,
                "runner": RunnerSelector.runner_summary(runner),
                "verdict": final_verdict,
                "evaluation_verdict": "Pass" if final_verdict else "Fail",
                "comment": final_comment,
                "commands": final_commands,
                "outputs": final_outputs,
            })

            if final_verdict:
                break
            should_retry = (
                failure_policy == "retry_then_fail_and_continue"
                and attempt_index < max_attempts
            )
            if not should_retry:
                break

        attempts_used = len(attempts)
        if final_verdict and attempts_used > 1 and not final_comment:
            final_comment = f"pass after retry ({attempts_used}/{max_attempts})"
        if not final_verdict and attempts_used > 1:
            if final_comment:
                final_comment = f"{final_comment} (failed after {attempts_used}/{max_attempts} attempts)"
            else:
                final_comment = f"failed after {attempts_used}/{max_attempts} attempts"

        # post_case hook
        self.hooks.dispatch(
            self._hook_ctx("post_case", case, runner),
            {"verdict": final_verdict, "attempts_used": attempts_used, "comment": final_comment},
        )

        return RetryResult(
            verdict=final_verdict,
            comment=final_comment,
            commands=final_commands,
            outputs=final_outputs,
            attempts=attempts,
            attempts_used=attempts_used,
            max_attempts=max_attempts,
        )

    @staticmethod
    def write_case_trace(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
