from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from testpilot.core.case_utils import case_band_results
from testpilot.reporting.excel_adapter import open_workbook as load_workbook


_DEFAULT_SHEET = "Wifi_LLAPI"
_ROW_SCAN_LIMIT = 2000
_EMPTY_STREAK_STOP = 50


@dataclass(slots=True)
class AnswerRow:
    row: int
    object: str
    api: str
    test_steps: str
    command_output: str
    raw_5g: str
    raw_6g: str
    raw_24g: str
    norm_5g: str
    norm_6g: str
    norm_24g: str


@dataclass(slots=True)
class CaseMeta:
    case_id: str
    case_file: str
    dnum: int
    source_row: int
    source_object: str
    source_api: str
    case: dict[str, Any]


@dataclass(slots=True)
class RunCaseResult:
    case_id: str
    case_file: str
    dnum: int
    source_row: int
    source_object: str
    source_api: str
    raw_5g: str
    raw_6g: str
    raw_24g: str
    norm_5g: str
    norm_6g: str
    norm_24g: str
    final_status: str
    evaluation_verdict: str
    attempts_used: int
    comment: str
    trace_path: str


def _extract_dnum(text: str) -> int:
    match = re.search(r"(?:^|[-_/])(?:wifi-llapi-)?[Dd](\d{3})(?:\b|[-_])", text)
    if match:
        return int(match.group(1))
    raise ValueError(f"unable to extract D-number from: {text}")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_result(value: Any) -> str:
    return "Pass" if str(value or "").strip().lower() == "pass" else "Fail"


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", "", text)
    return text.rstrip(".").lower()


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _excerpt(value: str, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def load_0401_answers(
    workbook_path: Path | str,
    *,
    sheet_name: str = _DEFAULT_SHEET,
) -> dict[int, AnswerRow]:
    path = Path(workbook_path)
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    answers: dict[int, AnswerRow] = {}
    current_object = ""
    empty_streak = 0
    for idx, values in enumerate(
        ws.iter_rows(
            min_row=2,
            max_row=min(ws.max_row, _ROW_SCAN_LIMIT),
            min_col=1,
            max_col=20,
            values_only=True,
        ),
        start=2,
    ):
        obj, _, api = values[:3]
        if obj is not None and str(obj).strip():
            current_object = str(obj).strip()
        api_text = _clean_cell(api)
        if not api_text:
            empty_streak += 1
            if empty_streak >= _EMPTY_STREAK_STOP:
                break
            continue
        empty_streak = 0
        raw_5g = _clean_cell(values[17])
        raw_6g = _clean_cell(values[18])
        raw_24g = _clean_cell(values[19])
        answers[idx] = AnswerRow(
            row=idx,
            object=current_object,
            api=api_text,
            test_steps=_clean_cell(values[6]),
            command_output=_clean_cell(values[7]),
            raw_5g=raw_5g,
            raw_6g=raw_6g,
            raw_24g=raw_24g,
            norm_5g=normalize_result(raw_5g),
            norm_6g=normalize_result(raw_6g),
            norm_24g=normalize_result(raw_24g),
        )
    wb.close()
    return answers


def load_case_index(cases_dir: Path | str) -> dict[str, CaseMeta]:
    base = Path(cases_dir)
    index: dict[str, CaseMeta] = {}
    for path in sorted(base.glob("D*.yaml")):
        if path.name.startswith("_"):
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("id", "")).strip()
        if not case_id:
            continue
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        index[case_id] = CaseMeta(
            case_id=case_id,
            case_file=path.name,
            dnum=_extract_dnum(path.name),
            source_row=_safe_int(source.get("row")),
            source_object=str(source.get("object", "") or "").strip(),
            source_api=str(source.get("api", "") or "").strip(),
            case=payload,
        )
    return index


def load_run_results(
    trace_dir: Path | str | Iterable[Path | str],
    *,
    cases_dir: Path | str,
) -> list[RunCaseResult]:
    case_index = load_case_index(cases_dir)
    trace_roots = (
        [Path(trace_dir)]
        if isinstance(trace_dir, (str, Path))
        else [Path(item) for item in trace_dir]
    )
    results_by_case: dict[str, RunCaseResult] = {}
    for trace_root in trace_roots:
        for path in sorted(trace_root.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_id = str(payload.get("case_id", "")).strip()
            meta = case_index.get(case_id)
            if meta is None:
                continue
            final = payload.get("final") if isinstance(payload.get("final"), dict) else {}
            evaluation_verdict = str(final.get("evaluation_verdict", "")).strip() or "Fail"
            verdict = evaluation_verdict == "Pass"
            raw_5g, raw_6g, raw_24g = case_band_results(meta.case, verdict)
            results_by_case[case_id] = RunCaseResult(
                case_id=case_id,
                case_file=meta.case_file,
                dnum=meta.dnum,
                source_row=meta.source_row,
                source_object=meta.source_object,
                source_api=meta.source_api,
                raw_5g=raw_5g,
                raw_6g=raw_6g,
                raw_24g=raw_24g,
                norm_5g=normalize_result(raw_5g),
                norm_6g=normalize_result(raw_6g),
                norm_24g=normalize_result(raw_24g),
                final_status=str(final.get("status", "") or "").strip(),
                evaluation_verdict=evaluation_verdict,
                attempts_used=_safe_int(final.get("attempts_used")),
                comment=str(final.get("comment", "") or "").strip(),
                trace_path=str(path),
            )
    return list(results_by_case.values())


def compare_run_against_0401(
    trace_dir: Path | str | Iterable[Path | str],
    answers_xlsx: Path | str,
    *,
    cases_dir: Path | str,
) -> dict[str, Any]:
    trace_roots = (
        [Path(trace_dir)]
        if isinstance(trace_dir, (str, Path))
        else [Path(item) for item in trace_dir]
    )
    answers = load_0401_answers(answers_xlsx)
    run_results = load_run_results(trace_roots, cases_dir=cases_dir)
    compared: list[dict[str, Any]] = []
    missing_answer_rows: list[dict[str, Any]] = []
    metadata_drift_count = 0
    band_summary = {
        "5g": {"matched": 0, "mismatched": 0},
        "6g": {"matched": 0, "mismatched": 0},
        "2.4g": {"matched": 0, "mismatched": 0},
    }

    for item in run_results:
        answer = answers.get(item.dnum)
        if answer is None:
            missing_answer_rows.append(
                {
                    "case_id": item.case_id,
                    "case_file": item.case_file,
                    "dnum": item.dnum,
                    "source_row": item.source_row,
                }
            )
            continue

        object_match = _normalize_text(item.source_object) == _normalize_text(answer.object)
        api_match = _normalize_text(item.source_api) == _normalize_text(answer.api)
        mapping_status = "exact" if object_match and api_match else "drift"
        if mapping_status == "drift":
            metadata_drift_count += 1

        bands = {
            "5g": {
                "actual_raw": item.raw_5g,
                "actual_norm": item.norm_5g,
                "expected_raw": answer.raw_5g,
                "expected_norm": answer.norm_5g,
            },
            "6g": {
                "actual_raw": item.raw_6g,
                "actual_norm": item.norm_6g,
                "expected_raw": answer.raw_6g,
                "expected_norm": answer.norm_6g,
            },
            "2.4g": {
                "actual_raw": item.raw_24g,
                "actual_norm": item.norm_24g,
                "expected_raw": answer.raw_24g,
                "expected_norm": answer.norm_24g,
            },
        }
        mismatch_bands: list[str] = []
        for band, band_info in bands.items():
            if band_info["actual_norm"] == band_info["expected_norm"]:
                band_summary[band]["matched"] += 1
            else:
                band_summary[band]["mismatched"] += 1
                mismatch_bands.append(band)

        compared.append(
            {
                "case_id": item.case_id,
                "case_file": item.case_file,
                "dnum": item.dnum,
                "source_row": item.source_row,
                "source_object": item.source_object,
                "source_api": item.source_api,
                "answer_row": answer.row,
                "answer_object": answer.object,
                "answer_api": answer.api,
                "mapping_status": mapping_status,
                "mapping_object_match": object_match,
                "mapping_api_match": api_match,
                "final_status": item.final_status,
                "evaluation_verdict": item.evaluation_verdict,
                "attempts_used": item.attempts_used,
                "comment": item.comment,
                "bands": bands,
                "mismatch_bands": mismatch_bands,
                "matches_answer": not mismatch_bands,
                "workbook_test_steps_excerpt": _excerpt(answer.test_steps),
                "workbook_command_output_excerpt": _excerpt(answer.command_output),
                "trace_path": item.trace_path,
            }
        )

    compared.sort(key=lambda item: (item["dnum"], item["case_id"]))
    mismatch_items = [item for item in compared if not item["matches_answer"]]

    return {
        "trace_dir": str(trace_roots[0]),
        "trace_dirs": [str(path) for path in trace_roots],
        "answers_xlsx": str(Path(answers_xlsx)),
        "cases_dir": str(Path(cases_dir)),
        "compared_case_count": len(compared),
        "missing_answer_count": len(missing_answer_rows),
        "missing_answer_rows": missing_answer_rows,
        "metadata_drift_count": metadata_drift_count,
        "full_match_count": len(compared) - len(mismatch_items),
        "mismatch_case_count": len(mismatch_items),
        "band_summary": band_summary,
        "cases": compared,
        "mismatches": mismatch_items,
    }


def render_compare_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# compare-0401")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    trace_dirs = payload.get("trace_dirs") or [payload["trace_dir"]]
    if len(trace_dirs) == 1:
        lines.append(f"- trace dir: `{trace_dirs[0]}`")
    else:
        lines.append("- trace dirs (overlay order; later directories override earlier case results):")
        for path in trace_dirs:
            lines.append(f"  - `{path}`")
    lines.append(f"- answer sheet: `{payload['answers_xlsx']}`")
    lines.append(f"- cases dir: `{payload['cases_dir']}`")
    lines.append("- compare rule: normalize both sides so only `Pass` stays `Pass`; all other values become `Fail`.")
    lines.append("- row mapping rule: use case `D###` number to match `0401.xlsx` worksheet row `###`.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("| --- | ---: |")
    lines.append(f"| compared cases | {payload['compared_case_count']} |")
    lines.append(f"| full matches | {payload['full_match_count']} |")
    lines.append(f"| mismatch cases | {payload['mismatch_case_count']} |")
    lines.append(f"| missing answer rows | {payload['missing_answer_count']} |")
    lines.append(f"| metadata drift rows | {payload['metadata_drift_count']} |")
    lines.append("")
    lines.append("## Per-band summary")
    lines.append("")
    lines.append("| band | matched | mismatched |")
    lines.append("| --- | ---: | ---: |")
    for band in ("5g", "6g", "2.4g"):
        info = payload["band_summary"][band]
        lines.append(f"| {band} | {info['matched']} | {info['mismatched']} |")
    lines.append("")

    if payload["missing_answer_rows"]:
        lines.append("## Missing answer rows")
        lines.append("")
        lines.append("| case_id | case_file | D-row | source.row |")
        lines.append("| --- | --- | ---: | ---: |")
        for item in payload["missing_answer_rows"]:
            lines.append(
                f"| `{item['case_id']}` | `{item['case_file']}` | {item['dnum']} | {item['source_row']} |"
            )
        lines.append("")

    lines.append("## Mismatch table")
    lines.append("")
    if not payload["mismatches"]:
        lines.append("No mismatches.")
        lines.append("")
        return "\n".join(lines)

    lines.append(
        "| case_id | D-row | mapping | actual raw (5/6/2.4) | expected raw (R/S/T) | actual norm | expected norm | mismatch bands |"
    )
    lines.append("| --- | ---: | --- | --- | --- | --- | --- | --- |")
    for item in payload["mismatches"]:
        actual_raw = f"{item['bands']['5g']['actual_raw']} / {item['bands']['6g']['actual_raw']} / {item['bands']['2.4g']['actual_raw']}"
        expected_raw = f"{item['bands']['5g']['expected_raw']} / {item['bands']['6g']['expected_raw']} / {item['bands']['2.4g']['expected_raw']}"
        actual_norm = f"{item['bands']['5g']['actual_norm']} / {item['bands']['6g']['actual_norm']} / {item['bands']['2.4g']['actual_norm']}"
        expected_norm = f"{item['bands']['5g']['expected_norm']} / {item['bands']['6g']['expected_norm']} / {item['bands']['2.4g']['expected_norm']}"
        mismatch_bands = ", ".join(item["mismatch_bands"])
        lines.append(
            f"| `{item['case_id']}` | {item['dnum']} | {item['mapping_status']} | "
            f"{actual_raw} | {expected_raw} | {actual_norm} | {expected_norm} | {mismatch_bands} |"
        )
    lines.append("")

    lines.append("## Mismatch details")
    lines.append("")
    for item in payload["mismatches"]:
        lines.append(f"### {item['case_id']}")
        lines.append("")
        lines.append(f"- case file: `{item['case_file']}`")
        lines.append(f"- answer row: `{item['answer_row']}`")
        lines.append(f"- mapping status: `{item['mapping_status']}`")
        lines.append(f"- source metadata: `{item['source_object']}` / `{item['source_api']}`")
        lines.append(f"- workbook metadata: `{item['answer_object']}` / `{item['answer_api']}`")
        lines.append(f"- final status: `{item['final_status']}`")
        lines.append(f"- evaluation verdict: `{item['evaluation_verdict']}`")
        lines.append(f"- attempts used: `{item['attempts_used']}`")
        if item["comment"]:
            lines.append(f"- runtime comment: {item['comment']}")
        lines.append(
            f"- actual raw: `{item['bands']['5g']['actual_raw']}` / `{item['bands']['6g']['actual_raw']}` / `{item['bands']['2.4g']['actual_raw']}`"
        )
        lines.append(
            f"- expected raw: `{item['bands']['5g']['expected_raw']}` / `{item['bands']['6g']['expected_raw']}` / `{item['bands']['2.4g']['expected_raw']}`"
        )
        lines.append(
            f"- actual normalized: `{item['bands']['5g']['actual_norm']}` / `{item['bands']['6g']['actual_norm']}` / `{item['bands']['2.4g']['actual_norm']}`"
        )
        lines.append(
            f"- expected normalized: `{item['bands']['5g']['expected_norm']}` / `{item['bands']['6g']['expected_norm']}` / `{item['bands']['2.4g']['expected_norm']}`"
        )
        lines.append(f"- mismatch bands: `{', '.join(item['mismatch_bands'])}`")
        lines.append(f"- 0401 G excerpt: {item['workbook_test_steps_excerpt'] or '(empty)'}")
        lines.append(f"- 0401 H excerpt: {item['workbook_command_output_excerpt'] or '(empty)'}")
        lines.append(f"- trace: `{item['trace_path']}`")
        lines.append("")

    return "\n".join(lines)


def write_compare_outputs(
    payload: dict[str, Any],
    *,
    output_md: Path | str,
    output_json: Path | str | None = None,
) -> None:
    md_path = Path(output_md)
    md_path.write_text(render_compare_markdown(payload), encoding="utf-8")
    if output_json is not None:
        Path(output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


__all__ = [
    "AnswerRow",
    "CaseMeta",
    "RunCaseResult",
    "compare_run_against_0401",
    "load_0401_answers",
    "load_case_index",
    "load_run_results",
    "normalize_result",
    "render_compare_markdown",
    "write_compare_outputs",
]
