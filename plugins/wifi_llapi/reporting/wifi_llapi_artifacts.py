"""Helpers for wifi_llapi per-run artifact layout and legacy path resolution."""

from __future__ import annotations

from pathlib import Path


def _looks_like_trace_dir(path: Path) -> bool:
    return path.is_dir() and any(path.glob("*.json"))


def resolve_trace_run_dir(value: str | Path, reports_root: Path | str) -> Path:
    """Resolve an artifact folder or legacy trace dir to the trace directory.

    Supported inputs:
    - explicit artifact directory path containing ``agent_trace/``
    - explicit trace directory path
    - artifact directory name under ``reports_root``
    - legacy run id under ``reports_root/agent_trace/``
    """

    root = Path(reports_root)

    def _resolve_candidate(path: Path) -> Path | None:
        if not path.is_dir():
            return None
        artifact_trace_dir = path / "agent_trace"
        if _looks_like_trace_dir(artifact_trace_dir):
            return artifact_trace_dir
        if _looks_like_trace_dir(path):
            return path
        return None

    candidate = Path(value)
    resolved = _resolve_candidate(candidate)
    if resolved is not None:
        return resolved

    resolved = _resolve_candidate(root / str(value))
    if resolved is not None:
        return resolved

    resolved = _resolve_candidate(root / "agent_trace" / str(value))
    if resolved is not None:
        return resolved

    raise FileNotFoundError(f"run directory not found: {value}")


__all__ = ["resolve_trace_run_dir"]
