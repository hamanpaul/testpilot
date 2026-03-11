"""Serialwrap transport implementation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from typing import Any

from .base import TransportBase

SERIALWRAP_BIN = "/home/paul_chen/.paul_tools/serialwrap"
TERMINAL_STATUSES = {"done", "failed", "error", "timeout", "cancelled", "canceled"}
SEQ_PATTERN = re.compile(r"^\S+\s+\S+\s+(\d+)\s+")


class SerialWrapTransport(TransportBase):
    """Transport backed by serialwrap CLI."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = dict(config or {})
        self._binary = str(self._config.get("binary", SERIALWRAP_BIN))
        self._socket = self._config.get("socket")
        self._source = str(self._config.get("source", "agent:testpilot"))
        self._mode = str(self._config.get("mode", "fg"))
        self._priority = int(self._config.get("priority", 10))
        self._poll_interval = float(self._config.get("poll_interval", 0.2))
        self._log_limit = int(self._config.get("log_limit", 800))
        self._use_marker = bool(self._config.get("use_marker", True))
        self._connected = False
        self._selector: str | None = None
        self._session: dict[str, Any] | None = None
        self._mirror_path: str | None = None
        self._wal_path: str | None = None

    @property
    def transport_type(self) -> str:
        return "serialwrap"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def session(self) -> dict[str, Any] | None:
        if self._session is None:
            return None
        return dict(self._session)

    def connect(self, **kwargs: Any) -> None:
        params = {**self._config, **kwargs}
        sessions = self._list_sessions()
        selector, session = self._resolve_session(params, sessions)
        state = str(session.get("state", "")).upper()
        if state != "READY":
            raise RuntimeError(f"serialwrap session not READY: {selector} ({state})")

        self._selector = str(
            session.get("session_id") or session.get("com") or session.get("alias") or selector
        )
        self._session = session
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._selector = None
        self._session = None
        self._mirror_path = None
        self._wal_path = None

    def execute(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
        if not self._connected or not self._selector:
            raise RuntimeError("serialwrap transport is not connected")

        timeout_s = max(float(timeout), 0.1)
        start = time.monotonic()
        marker = self._new_marker() if self._use_marker else None
        wrapped_command = self._wrap_command(command, marker) if marker else command

        seq_before = self._get_latest_seq(self._selector)
        submit_payload = self._run_json(
            [
                "cmd",
                "submit",
                "--selector",
                self._selector,
                "--cmd",
                wrapped_command,
                "--source",
                self._source,
                "--mode",
                self._mode,
                "--priority",
                str(self._priority),
                "--cmd-timeout",
                f"{timeout_s:.3f}",
            ],
            timeout=timeout_s + 2.0,
        )

        cmd_id = submit_payload.get("cmd_id")
        if not isinstance(cmd_id, str) or not cmd_id:
            raise RuntimeError("serialwrap cmd submit response missing cmd_id")

        try:
            status_payload = self._poll_status(cmd_id, timeout_s)
        except TimeoutError as exc:
            return {
                "returncode": 124,
                "stdout": "",
                "stderr": str(exc),
                "elapsed": time.monotonic() - start,
            }

        command_status = status_payload.get("command", {})
        raw_stdout = self._collect_output_after_command(
            selector=self._selector,
            seq_before=seq_before,
            marker=marker,
            timeout_s=min(max(1.0, timeout_s * 0.2), 4.0),
        )

        stdout = raw_stdout
        returncode: int | None = None
        if marker is not None:
            parsed = self._extract_marker_output(raw_stdout, marker)
            stdout = parsed["stdout"] or raw_stdout
            returncode = parsed["returncode"]

        if not stdout:
            stdout = str(command_status.get("command", "")).strip()

        if returncode is None:
            returncode = self._status_to_returncode(
                str(command_status.get("status", "")),
                command_status.get("error_code"),
            )

        stderr = self._build_stderr(command_status)
        return {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed": time.monotonic() - start,
        }

    def _build_cli(self, args: list[str]) -> list[str]:
        cmd = [self._binary]
        if self._socket:
            cmd.extend(["--socket", str(self._socket)])
        cmd.extend(args)
        return cmd

    def _run_json(self, args: list[str], timeout: float | None = None) -> dict[str, Any]:
        completed = subprocess.run(
            self._build_cli(args),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise RuntimeError(f"serialwrap command failed: {' '.join(args)}: {stderr}")

        stdout = (completed.stdout or "").strip()
        if not stdout:
            raise RuntimeError(f"serialwrap command returned empty stdout: {' '.join(args)}")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"serialwrap JSON decode failed: {stdout!r}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"serialwrap response must be JSON object: {stdout!r}")
        if payload.get("ok") is False:
            raise RuntimeError(f"serialwrap command not ok: {' '.join(args)}: {stdout}")
        return payload

    def _list_sessions(self) -> list[dict[str, Any]]:
        payload = self._run_json(["session", "list"], timeout=5.0)
        sessions = payload.get("sessions", [])
        if not isinstance(sessions, list):
            raise RuntimeError("serialwrap session list response missing sessions")
        return [s for s in sessions if isinstance(s, dict)]

    def _resolve_session(
        self, params: dict[str, Any], sessions: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any]]:
        selector = params.get("selector")
        alias = params.get("alias")
        session_id = params.get("session_id")
        serial_port = params.get("serial_port")

        if selector:
            selected = self._find_by_selector(str(selector), sessions)
            if selected is None:
                raise RuntimeError(f"serialwrap session not found by selector: {selector}")
            return str(selector), selected

        if alias:
            selected = self._find_one(sessions, "alias", str(alias))
            return str(alias), selected

        if session_id:
            selected = self._find_one(sessions, "session_id", str(session_id))
            return str(session_id), selected

        if serial_port:
            serial_port_str = str(serial_port)
            candidates = [
                session
                for session in sessions
                if serial_port_str
                in {
                    str(session.get("device_by_id", "")),
                    str(session.get("vtty", "")),
                    str(session.get("com", "")),
                }
            ]
            if len(candidates) == 1:
                return serial_port_str, candidates[0]

            by_id = self._resolve_by_id_from_real_path(serial_port_str)
            if by_id:
                by_id_candidates = [
                    session
                    for session in sessions
                    if str(session.get("device_by_id", "")) == by_id
                ]
                if len(by_id_candidates) == 1:
                    return serial_port_str, by_id_candidates[0]

            com = self._resolve_com_from_serial_port(serial_port_str)
            if com:
                selected = self._find_by_selector(com, sessions)
                if selected is not None:
                    return com, selected

            raise RuntimeError(f"serialwrap serial_port lookup failed: {serial_port}")

        ready_sessions = [s for s in sessions if str(s.get("state", "")).upper() == "READY"]
        if len(ready_sessions) == 1:
            only = ready_sessions[0]
            fallback = str(only.get("session_id") or only.get("com") or only.get("alias") or "")
            if not fallback:
                raise RuntimeError("serialwrap READY session missing selector fields")
            return fallback, only

        raise RuntimeError(
            "serialwrap connect requires selector/alias/session_id/serial_port "
            "when READY sessions are not unique"
        )

    def _find_by_selector(
        self, selector: str, sessions: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        for session in sessions:
            if selector in {
                str(session.get("session_id", "")),
                str(session.get("alias", "")),
                str(session.get("com", "")),
            }:
                return session
        return None

    def _find_one(
        self, sessions: list[dict[str, Any]], field: str, expected: str
    ) -> dict[str, Any]:
        candidates = [session for session in sessions if str(session.get(field, "")) == expected]
        if len(candidates) != 1:
            raise RuntimeError(f"serialwrap {field} lookup failed: {expected}")
        return candidates[0]

    def _poll_status(self, cmd_id: str, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout + 1.0
        last_payload: dict[str, Any] = {}
        while True:
            last_payload = self._run_json(
                ["cmd", "status", "--cmd-id", cmd_id],
                timeout=min(timeout + 1.0, 5.0),
            )
            command_payload = last_payload.get("command", {})
            status = str(command_payload.get("status", "")).lower()
            if status in TERMINAL_STATUSES:
                return last_payload
            if time.monotonic() >= deadline:
                raise TimeoutError(f"serialwrap cmd status timeout: {cmd_id}")
            if self._poll_interval > 0:
                time.sleep(self._poll_interval)

    def _get_latest_seq(self, selector: str) -> int | None:
        mirror_path = self._ensure_mirror_path()
        if mirror_path:
            seq = self._read_last_seq_from_mirror(mirror_path)
            if seq is not None:
                return seq

        wal_path = self._ensure_wal_path()
        if wal_path:
            seq = self._read_last_seq_from_wal(wal_path)
            if seq is not None:
                return seq

        # Avoid dangerous fallback to `log tail-text --limit 1`.
        # serialwrap returns the oldest entries first, which can rewind
        # baseline seq and replay historical logs unexpectedly.
        return None

    def _tail_text(self, selector: str, seq_before: int | None) -> dict[str, Any]:
        args = [
            "log",
            "tail-text",
            "--selector",
            selector,
            "--limit",
            str(self._log_limit),
        ]
        if seq_before is not None:
            args.extend(["--from-seq", str(seq_before + 1)])
        return self._run_json(args, timeout=5.0)

    def _tail_text_since(
        self,
        selector: str,
        from_seq: int,
    ) -> tuple[int, list[str]]:
        payload = self._tail_text(selector, from_seq)
        lines = payload.get("lines", [])
        if not isinstance(lines, list):
            return from_seq, []
        typed_lines = [line for line in lines if isinstance(line, str)]
        new_seq = from_seq
        for line in typed_lines:
            seq = self._parse_seq(line)
            if seq is not None and seq > new_seq:
                new_seq = seq
        return new_seq, typed_lines

    def _collect_output_after_command(
        self,
        *,
        selector: str,
        seq_before: int | None,
        marker: dict[str, str] | None,
        timeout_s: float,
    ) -> str:
        last_seq = seq_before or 0
        deadline = time.monotonic() + max(timeout_s, 0.5)
        all_lines: list[str] = []
        end_marker = marker["end"] if marker else ""

        while True:
            next_seq, lines = self._tail_text_since(selector, last_seq)
            if lines:
                all_lines.extend(lines)
                last_seq = max(last_seq, next_seq)
                if end_marker and any(end_marker in line for line in lines):
                    break

            if time.monotonic() >= deadline:
                break
            if self._poll_interval > 0:
                time.sleep(self._poll_interval)
            else:
                time.sleep(0.05)

        return self._extract_text_payload(all_lines)

    def _parse_seq(self, line: str) -> int | None:
        match = SEQ_PATTERN.match(line)
        if not match:
            return None
        return int(match.group(1))

    def _extract_text_payload(self, lines: list[Any]) -> str:
        chunks: list[str] = []
        for line in lines:
            if not isinstance(line, str):
                continue
            if " RX " not in line:
                continue
            if "|" in line:
                chunks.append(line.split("|", 1)[1].lstrip())
            else:
                chunks.append(line)
        return "".join(chunks).strip()

    def _new_marker(self) -> dict[str, str]:
        token = uuid.uuid4().hex[:12]
        return {
            "begin": f"__TP_BEGIN_{token}__",
            "end": f"__TP_END_{token}__",
            "rc_prefix": f"__TP_RC_{token}__=",
        }

    def _wrap_command(self, command: str, marker: dict[str, str]) -> str:
        begin = marker["begin"]
        end = marker["end"]
        rc_prefix = marker["rc_prefix"]
        return (
            f"printf '{begin}\\n'; "
            f"{command}; "
            "__tp_rc=$?; "
            f"printf '{rc_prefix}%s\\n{end}\\n' \"$__tp_rc\""
        )

    def _extract_marker_output(self, output: str, marker: dict[str, str]) -> dict[str, Any]:
        begin = marker["begin"]
        end = marker["end"]
        rc_prefix = marker["rc_prefix"]

        start = output.rfind(begin)
        segment = output[start + len(begin) :] if start >= 0 else output

        end_pos = segment.find(end)
        if end_pos >= 0:
            segment = segment[:end_pos]

        rc_pattern = re.escape(rc_prefix) + r"(-?\d+)"
        returncode: int | None = None
        rc_match = re.search(rc_pattern, segment)
        if rc_match:
            # Use the first RC marker emitted after the matching begin marker.
            # Old transcript fragments may replay the same token later in the segment.
            returncode = int(rc_match.group(1))
            segment = re.sub(rf"(?m)^[ \t]*{re.escape(rc_prefix)}-?\d+[ \t]*\n?", "", segment)
            segment = re.sub(rc_pattern, "", segment)

        return {"stdout": segment.strip(), "returncode": returncode}

    def _status_to_returncode(self, status: str, error_code: Any) -> int:
        status_lower = status.lower()
        if status_lower == "done" and not error_code:
            return 0
        if status_lower == "timeout":
            return 124
        if status_lower in {"cancelled", "canceled"}:
            return 130
        return 1

    def _build_stderr(self, command_status: dict[str, Any]) -> str:
        details: list[str] = []
        error_code = command_status.get("error_code")
        status = str(command_status.get("status", ""))

        if error_code:
            details.append(str(error_code))
        if status and status.lower() not in {"done", "running", "accepted"}:
            details.append(f"status={status}")
        return "; ".join(details)

    def _resolve_by_id_from_real_path(self, serial_port: str) -> str | None:
        try:
            payload = self._run_json(["device", "list"], timeout=5.0)
        except Exception:
            return None
        devices = payload.get("devices", [])
        if not isinstance(devices, list):
            return None
        for item in devices:
            if not isinstance(item, dict):
                continue
            if str(item.get("real_path", "")) != serial_port:
                continue
            by_id = str(item.get("by_id", "")).strip()
            if by_id:
                return by_id
        return None

    @staticmethod
    def _resolve_com_from_serial_port(serial_port: str) -> str | None:
        match = re.search(r"ttyUSB(\d+)$", serial_port)
        if not match:
            return None
        return f"COM{match.group(1)}"

    def _ensure_mirror_path(self) -> str | None:
        if self._mirror_path and os.path.exists(self._mirror_path):
            return self._mirror_path
        payload = self._daemon_status()
        if payload is None:
            return None
        mirror_path = str(payload.get("mirror_path", "")).strip()
        if not mirror_path:
            return None
        self._mirror_path = mirror_path
        return mirror_path

    def _ensure_wal_path(self) -> str | None:
        if self._wal_path and os.path.exists(self._wal_path):
            return self._wal_path
        payload = self._daemon_status()
        if payload is None:
            return None
        wal_path = str(payload.get("wal_path", "")).strip()
        if not wal_path:
            return None
        self._wal_path = wal_path
        return wal_path

    def _daemon_status(self) -> dict[str, Any] | None:
        try:
            payload = self._run_json(["daemon", "status"], timeout=5.0)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _read_last_seq_from_mirror(self, path: str) -> int | None:
        if not os.path.exists(path):
            return None

        with open(path, "rb") as fp:
            fp.seek(0, os.SEEK_END)
            size = fp.tell()
            if size <= 0:
                return None

            chunk = bytearray()
            pos = size - 1
            while pos >= 0:
                fp.seek(pos)
                b = fp.read(1)
                if b == b"\n" and chunk:
                    break
                if b != b"\n":
                    chunk.extend(b)
                pos -= 1

        if not chunk:
            return None

        line = chunk[::-1].decode("utf-8", errors="replace")
        seq = self._parse_seq(line)
        if seq is None:
            return None
        return seq

    def _read_last_seq_from_wal(self, path: str) -> int | None:
        if not os.path.exists(path):
            return None

        with open(path, "rb") as fp:
            fp.seek(0, os.SEEK_END)
            size = fp.tell()
            if size <= 0:
                return None

            chunk = bytearray()
            pos = size - 1
            while pos >= 0:
                fp.seek(pos)
                b = fp.read(1)
                if b == b"\n" and chunk:
                    break
                if b != b"\n":
                    chunk.extend(b)
                pos -= 1

        if not chunk:
            return None

        line = chunk[::-1].decode("utf-8", errors="replace")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        seq = payload.get("seq")
        if isinstance(seq, int):
            return seq
        if isinstance(seq, str) and seq.isdigit():
            return int(seq)
        return None
