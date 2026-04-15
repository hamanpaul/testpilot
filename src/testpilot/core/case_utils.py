"""Case utility functions — pure helpers for case filtering, band mapping, and ID handling."""

from __future__ import annotations

import re
from typing import Any


def safe_int(value: Any, default: int) -> int:
    """Convert *value* to int, falling back to *default*."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float) -> float:
    """Convert *value* to float, falling back to *default*."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def sanitize_case_id(case_id: str) -> str:
    """Return a filesystem-safe variant of *case_id*."""
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", case_id.strip())
    return normalized or "case"


def normalize_step_command(value: Any) -> str | list[str]:
    """Normalize a step command while preserving `str | list[str]` semantics."""
    if isinstance(value, list):
        commands: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                commands.append(text)
        return commands
    return str(value or "").strip()


def step_command_lines(value: Any) -> list[str]:
    """Return the step command as a list of executable command strings."""
    normalized = normalize_step_command(value)
    if isinstance(normalized, list):
        return normalized
    return [normalized] if normalized else []


def stringify_step_command(value: Any) -> str:
    """Return a display string for `str | list[str]` step commands."""
    normalized = normalize_step_command(value)
    if isinstance(normalized, list):
        return "\n".join(normalized).strip()
    return normalized


def case_aliases(case: dict[str, Any]) -> list[str]:
    """Extract the list of alias strings from *case*."""
    raw_aliases = case.get("aliases")
    if not isinstance(raw_aliases, list):
        return []
    aliases: list[str] = []
    for item in raw_aliases:
        alias = str(item).strip()
        if alias:
            aliases.append(alias)
    return aliases


def case_matches_requested_ids(
    case: dict[str, Any],
    requested_ids: set[str],
) -> bool:
    """Return True if *case* id or any alias is in *requested_ids*."""
    if not requested_ids:
        return False
    case_ids = {str(case.get("id", "")).strip(), *case_aliases(case)}
    case_ids.discard("")
    return bool(case_ids & requested_ids)


def is_wifi_llapi_official_case(case: dict[str, Any]) -> bool:
    """Return True if the case id matches the ``D###`` official naming."""
    return re.match(r"^(?:wifi-llapi-)?[Dd]\d+", str(case.get("id", "")).strip()) is not None


def band_results(status: str, bands: list[str] | None) -> tuple[str, str, str]:
    """Map a *status* string to per-band (5g, 6g, 2.4g) results."""
    if not bands:
        return status, status, status
    normalized = {b.strip().lower() for b in bands}
    r5 = status if "5g" in normalized else "N/A"
    r6 = status if "6g" in normalized else "N/A"
    r24 = status if "2.4g" in normalized else "N/A"
    return r5, r6, r24


def baseline_results_reference(case: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the results_reference dict matching the case baseline version."""
    source = case.get("source")
    if not isinstance(source, dict):
        return None
    results_reference = case.get("results_reference")
    if not isinstance(results_reference, dict):
        return None

    baseline = str(source.get("baseline", "")).strip()
    candidates: list[str] = []
    if baseline:
        candidates.append(baseline)
        version_match = re.search(r"\bv\d+(?:\.\d+)+\b", baseline, re.IGNORECASE)
        if version_match:
            candidates.append(version_match.group(0))
        numeric_match = re.search(r"\b\d+(?:\.\d+)+\b", baseline)
        if numeric_match:
            candidates.append(f"v{numeric_match.group(0)}")

    seen: set[str] = set()
    for candidate in candidates:
        norm = candidate.strip()
        if not norm or norm.lower() in seen:
            continue
        seen.add(norm.lower())
        value = results_reference.get(norm)
        if isinstance(value, dict):
            return value
        for key, entry in results_reference.items():
            if isinstance(key, str) and key.strip().lower() == norm.lower() and isinstance(entry, dict):
                return entry
    for fallback in ("v4.0.3", "4.0.3", "v4.0.1", "4.0.1"):
        value = results_reference.get(fallback)
        if isinstance(value, dict):
            return value
        for key, entry in results_reference.items():
            if isinstance(key, str) and key.strip().lower() == fallback.lower() and isinstance(entry, dict):
                return entry
    return None


def case_band_results(case: dict[str, Any], verdict: bool) -> tuple[str, str, str]:
    """Compute per-band results for *case* given an evaluation *verdict*."""
    default_status = "Pass" if verdict else "Fail"
    result_5g, result_6g, result_24g = band_results(default_status, case.get("bands"))
    reference = baseline_results_reference(case)
    if not reference:
        return result_5g, result_6g, result_24g

    by_band = {
        "5g": result_5g,
        "6g": result_6g,
        "2.4g": result_24g,
    }
    for b in ("5g", "6g", "2.4g"):
        value = reference.get(b)
        if not isinstance(value, str):
            continue
        norm = value.strip()
        if not norm:
            continue
        if verdict:
            by_band[b] = norm
        elif norm in {"Skip", "N/A"}:
            by_band[b] = norm

    return by_band["5g"], by_band["6g"], by_band["2.4g"]


def overall_case_status(result_5g: str, result_6g: str, result_24g: str) -> str:
    """Return ``'Fail'`` if any band failed, otherwise ``'Pass'``."""
    return "Fail" if "Fail" in {result_5g, result_6g, result_24g} else "Pass"
