"""Serialwrap RAW log capture and decoding for test run reports.

Manages serialwrap daemon lifecycle per run and provides utilities
to capture, decode, and map UART log records to line numbers.
"""

from __future__ import annotations

import base64
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SERIALWRAP_BIN = "/home/paul_chen/.paul_tools/serialwrap"
DEFAULT_WAL_DIR = Path("/tmp/serialwrap/wal")


def _run_sw(args: list[str], timeout: float = 10.0) -> dict[str, Any]:
    """Run a serialwrap CLI command and return parsed JSON response."""
    cmd = [SERIALWRAP_BIN, *args]
    completed = subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=timeout,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(f"serialwrap failed: {' '.join(args)}: {stderr}")
    stdout = (completed.stdout or "").strip()
    if not stdout:
        raise RuntimeError(f"serialwrap empty response: {' '.join(args)}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"serialwrap JSON decode error: {stdout[:200]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"serialwrap unexpected response type: {type(payload)}")
    return payload


# ---------------------------------------------------------------------------
# Daemon lifecycle
# ---------------------------------------------------------------------------

def start_daemon(profile_dir: str | Path | None = None) -> dict[str, Any]:
    """Start serialwrap daemon and return status (contains wal_path)."""
    args = ["daemon", "start"]
    if profile_dir:
        args.extend(["--profile-dir", str(profile_dir)])
    payload = _run_sw(args, timeout=15.0)
    logger.info("serialwrap daemon started: pid=%s", payload.get("pid"))
    return payload


def stop_daemon() -> None:
    """Stop serialwrap daemon. Silently ignores if not running."""
    try:
        _run_sw(["daemon", "stop"], timeout=10.0)
        logger.info("serialwrap daemon stopped")
    except Exception:
        logger.debug("serialwrap daemon stop ignored (may not be running)")


def daemon_status() -> dict[str, Any] | None:
    """Return daemon status dict, or None if daemon is not running."""
    try:
        return _run_sw(["daemon", "status"], timeout=5.0)
    except Exception:
        return None


def clean_wal(wal_dir: Path | None = None) -> None:
    """Remove old WAL files so next daemon start has a clean slate."""
    target = wal_dir or DEFAULT_WAL_DIR
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
        logger.info("cleaned WAL directory: %s", target)


def setup_sessions(
    devices: list[dict[str, Any]],
    *,
    timeout: float = 15.0,
) -> None:
    """Attach sessions and set aliases for DUT/STA devices.

    Each device dict should have:
      - profile: str (e.g. "prpl-template")
      - com: str (e.g. "COM0")
      - alias: str (e.g. "dut")
    """
    for dev in devices:
        profile = dev.get("profile", "prpl-template")
        com = dev.get("com", "")
        alias = dev.get("alias", "")
        session_id = f"{profile}:{com}"

        payload = _run_sw(
            ["session", "attach", "--selector", session_id],
            timeout=timeout,
        )
        session = payload.get("session", {})
        state = str(session.get("state", "")).upper()
        logger.info(
            "attached session %s → %s (state=%s)",
            session_id, session.get("device_by_id", "?"), state,
        )

        if alias:
            _run_sw(
                ["alias", "set", "--session-id", session_id, "--alias", alias],
                timeout=5.0,
            )
            logger.info("alias %s → %s", alias, session_id)


# ---------------------------------------------------------------------------
# Seq tracking
# ---------------------------------------------------------------------------

def get_wal_path() -> Path:
    """Return the WAL ndjson file path from daemon status."""
    status = daemon_status()
    if status and status.get("wal_path"):
        return Path(status["wal_path"])
    return DEFAULT_WAL_DIR / "raw.wal.ndjson"


def get_current_seq(wal_path: Path | None = None) -> int | None:
    """Read the latest seq number from the WAL ndjson tail line.

    Returns None if WAL file doesn't exist or is empty.
    """
    path = wal_path or get_wal_path()
    if not path.is_file():
        return None
    try:
        completed = subprocess.run(
            ["tail", "-1", str(path)],
            capture_output=True, text=True, check=False, timeout=3.0,
        )
        line = (completed.stdout or "").strip()
        if not line:
            return None
        record = json.loads(line)
        return int(record["seq"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Log export & decode
# ---------------------------------------------------------------------------

def export_records(
    from_seq: int = 1,
    to_seq: int | None = None,
) -> list[dict[str, Any]]:
    """Export WAL records in a seq range.

    If to_seq is None, exports from from_seq to end of WAL.
    """
    args = ["wal", "export", "--from-seq", str(from_seq)]
    if to_seq is not None:
        args.extend(["--to-seq", str(to_seq)])
    payload = _run_sw(args, timeout=60.0)
    records = payload.get("records", [])
    if not isinstance(records, list):
        return []
    return records


def decode_log(
    records: list[dict[str, Any]],
    com_filter: str | None = None,
) -> str:
    """Decode base64 payloads from records into plain text.

    Args:
        records: WAL records from export_records().
        com_filter: If set, only include records from this COM port (e.g. "COM0").

    Returns:
        Decoded text with each record's payload joined by newlines.
    """
    lines: list[str] = []
    for rec in records:
        if com_filter and rec.get("com") != com_filter:
            continue
        payload_b64 = rec.get("payload_b64", "")
        if not payload_b64:
            continue
        try:
            text = base64.b64decode(payload_b64).decode("utf-8", errors="replace")
        except Exception:
            continue
        lines.append(text)
    return "".join(lines)


def save_decoded_log(text: str, path: Path) -> Path:
    """Write decoded log text to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    logger.info("saved decoded log: %s (%d bytes)", path, len(text))
    return path


def build_seq_to_line_map(
    records: list[dict[str, Any]],
    com_filter: str | None = None,
) -> dict[int, int]:
    """Build a mapping from seq number to the first line number in decoded output.

    Line numbers are 1-based. A record with multi-line payload maps to its
    first line. Records from other COM ports are skipped.

    Returns:
        {seq: first_line_number, ...}
    """
    mapping: dict[int, int] = {}
    current_line = 1
    for rec in records:
        if com_filter and rec.get("com") != com_filter:
            continue
        seq = rec.get("seq")
        payload_b64 = rec.get("payload_b64", "")
        if not payload_b64:
            continue
        try:
            text = base64.b64decode(payload_b64).decode("utf-8", errors="replace")
        except Exception:
            continue
        if seq is not None:
            mapping[int(seq)] = current_line
        line_count = text.count("\n")
        if not text.endswith("\n") and text:
            line_count += 1
        current_line += line_count
    return mapping


def seq_range_to_line_range(
    seq_start: int | None,
    seq_end: int | None,
    seq_to_line: dict[int, int],
) -> str:
    """Convert a seq range to line range string (e.g. 'L123-L456').

    Returns empty string if mapping is insufficient.
    """
    if seq_start is None or seq_end is None:
        return ""
    if not seq_to_line:
        return ""

    start_line = seq_to_line.get(seq_start)
    end_line = seq_to_line.get(seq_end)

    if start_line is None:
        seqs_at_or_after = [s for s in seq_to_line if s >= seq_start]
        if seqs_at_or_after:
            start_line = seq_to_line[min(seqs_at_or_after)]
    if end_line is None:
        seqs_at_or_before = [s for s in seq_to_line if s <= seq_end]
        if seqs_at_or_before:
            end_line = seq_to_line[max(seqs_at_or_before)]

    if start_line is None or end_line is None:
        return ""
    if start_line > end_line:
        start_line, end_line = end_line, start_line
    return f"L{start_line}-L{end_line}"
