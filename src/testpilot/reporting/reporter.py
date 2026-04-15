"""Generic MD / JSON report projectors.

Provides :class:`IReporter` protocol plus concrete
:class:`MarkdownReporter` and :class:`JsonReporter` implementations.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

# ---------------------------------------------------------------------------
# Band / summary helpers
# ---------------------------------------------------------------------------

_BAND_KEYS: tuple[str, ...] = ("result_5g", "result_6g", "result_24g")
_BAND_LABELS: dict[str, str] = {
    "result_5g": "5G",
    "result_6g": "6G",
    "result_24g": "2.4G",
}


def _verdict(value: str) -> str:
    """Normalise a single band verdict to lower-case token."""
    return value.strip().lower() if value else ""


def _summarise(case_results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Aggregate pass / fail / not_supported / error counts across bands."""
    counter: Counter[str] = Counter()
    diagnostic_counter: Counter[str] = Counter()
    for case in case_results:
        for key in _BAND_KEYS:
            v = _verdict(str(case.get(key, "")))
            if v:
                counter[v] += 1
        diagnostic = str(case.get("diagnostic_status", "")).strip()
        if diagnostic:
            diagnostic_counter[diagnostic] += 1
    return {
        "total_cases": len(case_results),
        "pass": counter.get("pass", 0),
        "fail": counter.get("fail", 0),
        "not_supported": counter.get("not_supported", 0)
        + counter.get("not supported", 0),
        "error": counter.get("error", 0),
        "diagnostic_status": dict(diagnostic_counter),
    }


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class IReporter(Protocol):
    """Minimal reporter contract."""

    def generate(
        self,
        case_results: Sequence[Mapping[str, Any]],
        meta: Mapping[str, Any],
        output_path: Path,
    ) -> Path: ...


# ---------------------------------------------------------------------------
# MarkdownReporter
# ---------------------------------------------------------------------------


class MarkdownReporter:
    """Render results to a human-readable Markdown file."""

    def generate(
        self,
        case_results: Sequence[Mapping[str, Any]],
        meta: Mapping[str, Any],
        output_path: Path,
    ) -> Path:
        lines: list[str] = []
        self._write_header(lines, meta)
        self._write_summary_table(lines, case_results)
        self._write_case_details(lines, case_results)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path

    # -- private helpers ----------------------------------------------------

    @staticmethod
    def _write_header(lines: list[str], meta: Mapping[str, Any]) -> None:
        title = meta.get("title", "Test Report")
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"- **Date**: {meta.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))}")
        for key in ("tester", "testbed", "dut_model", "firmware_version", "plugin"):
            if key in meta:
                label = key.replace("_", " ").title()
                lines.append(f"- **{label}**: {meta[key]}")
        lines.append("")

    @staticmethod
    def _write_summary_table(
        lines: list[str],
        case_results: Sequence[Mapping[str, Any]],
    ) -> None:
        lines.append("## Summary")
        lines.append("")
        header = "| case_id | source_row | result_5g | result_6g | result_24g | diagnostic_status | comment |"
        sep = "|---------|------------|-----------|-----------|------------|-------------------|---------|"
        lines.append(header)
        lines.append(sep)
        for case in case_results:
            cid = case.get("case_id", "")
            row = case.get("source_row", "")
            r5 = case.get("result_5g", "")
            r6 = case.get("result_6g", "")
            r24 = case.get("result_24g", "")
            diagnostic = case.get("diagnostic_status", "")
            comment = case.get("comment", "")
            lines.append(f"| {cid} | {row} | {r5} | {r6} | {r24} | {diagnostic} | {comment} |")
        lines.append("")

    @staticmethod
    def _write_case_details(
        lines: list[str],
        case_results: Sequence[Mapping[str, Any]],
    ) -> None:
        if not case_results:
            return
        lines.append("## Case Details")
        lines.append("")
        for case in case_results:
            cid = case.get("case_id", "unknown")
            lines.append(f"<details><summary>{cid}</summary>")
            lines.append("")
            cmd = case.get("executed_test_command", "")
            if cmd:
                lines.append("**Command**")
                lines.append("")
                lines.append("```")
                lines.append(cmd)
                lines.append("```")
                lines.append("")
            output = case.get("command_output", "")
            if output:
                lines.append("**Output**")
                lines.append("")
                lines.append("```")
                lines.append(output)
                lines.append("```")
                lines.append("")
            # Log references
            dut_lines = case.get("dut_log_lines", "")
            sta_lines = case.get("sta_log_lines", "")
            if dut_lines or sta_lines:
                lines.append("**Log Reference**")
                lines.append("")
                if dut_lines:
                    lines.append(f"- DUT: `{dut_lines}`")
                if sta_lines:
                    lines.append(f"- STA: `{sta_lines}`")
                lines.append("")
            # Emit any extra keys not yet rendered
            shown = {
                "case_id",
                "source_row",
                "executed_test_command",
                "command_output",
                "result_5g",
                "result_6g",
                "result_24g",
                "comment",
                "tester",
                "dut_log_lines",
                "sta_log_lines",
            }
            extras = {k: v for k, v in case.items() if k not in shown}
            if extras:
                for k, v in extras.items():
                    lines.append(f"- **{k}**: {v}")
                lines.append("")
            lines.append("</details>")
            lines.append("")


# ---------------------------------------------------------------------------
# JsonReporter
# ---------------------------------------------------------------------------


class JsonReporter:
    """Render results to a structured JSON file."""

    def generate(
        self,
        case_results: Sequence[Mapping[str, Any]],
        meta: Mapping[str, Any],
        output_path: Path,
    ) -> Path:
        payload: dict[str, Any] = {
            "meta": dict(meta),
            "cases": [dict(c) for c in case_results],
            "summary": _summarise(case_results),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        return output_path


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------

_FORMAT_REGISTRY: dict[str, type[MarkdownReporter | JsonReporter]] = {
    "md": MarkdownReporter,
    "json": JsonReporter,
}


def generate_reports(
    case_results: Sequence[Mapping[str, Any]],
    meta: Mapping[str, Any],
    output_dir: Path,
    formats: Sequence[str] = ("md", "json"),
) -> list[Path]:
    """Generate reports in the requested formats and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = meta.get("title", "report").replace(" ", "_").lower()
    paths: list[Path] = []
    for fmt in formats:
        cls = _FORMAT_REGISTRY.get(fmt)
        if cls is None:
            raise ValueError(f"Unsupported report format: {fmt!r}")
        out = output_dir / f"{stem}.{fmt}"
        reporter = cls()
        reporter.generate(case_results, meta, out)
        paths.append(out)
    return paths
