#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from testpilot.reporting.wifi_llapi_compare_0401 import (
    compare_run_against_0401,
    render_compare_markdown,
)


def _default_trace_root() -> Path:
    return Path(__file__).resolve().parents[1] / "plugins" / "wifi_llapi" / "reports" / "agent_trace"


def _resolve_run_dir(value: str, trace_root: Path) -> Path:
    candidate = Path(value)
    if candidate.is_dir():
        return candidate
    run_dir = trace_root / value
    if run_dir.is_dir():
        return run_dir
    raise FileNotFoundError(f"run directory not found: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare wifi_llapi run results against 0401.xlsx answer sheet."
    )
    parser.add_argument(
        "runs",
        nargs="+",
        help=(
            "One or more run IDs under plugins/wifi_llapi/reports/agent_trace, "
            "or explicit run directories. Later runs override earlier case results."
        ),
    )
    parser.add_argument(
        "--answers",
        default="0401.xlsx",
        help="Answer workbook path (default: 0401.xlsx at repo root).",
    )
    parser.add_argument(
        "--cases-dir",
        default="plugins/wifi_llapi/cases",
        help="Case YAML directory.",
    )
    parser.add_argument(
        "--trace-root",
        default=str(_default_trace_root()),
        help="Trace root directory for resolving run IDs.",
    )
    parser.add_argument(
        "--output-md",
        default="compare-0401.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--output-json",
        default="compare-0401.json",
        help="JSON report output path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    trace_root = Path(args.trace_root)
    run_dirs = [_resolve_run_dir(value, trace_root) for value in args.runs]
    answers = Path(args.answers)
    if not answers.is_absolute():
        answers = repo_root / answers
    cases_dir = Path(args.cases_dir)
    if not cases_dir.is_absolute():
        cases_dir = repo_root / cases_dir
    output_md = Path(args.output_md)
    if not output_md.is_absolute():
        output_md = repo_root / output_md
    output_json = Path(args.output_json)
    if not output_json.is_absolute():
        output_json = repo_root / output_json

    payload = compare_run_against_0401(
        run_dirs,
        answers,
        cases_dir=cases_dir,
    )
    output_md.write_text(render_compare_markdown(payload), encoding="utf-8")
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
