"""Serialwrap transport implementation."""

from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

from .base import TransportBase

SERIALWRAP_BIN = "/home/paul_chen/.paul_tools/serialwrap"
TERMINAL_STATUSES = {"done", "failed", "error", "timeout", "cancelled", "canceled"}
MODE_ALIASES = {"fg": "line", "bg": "background"}


class SerialWrapTransport(TransportBase):
    """Transport backed by serialwrap CLI."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = dict(config or {})
        self._binary = str(self._config.get("binary", SERIALWRAP_BIN))
        self._socket = self._config.get("socket")
        self._source = str(self._config.get("source", "agent:testpilot"))
        self._mode = self._normalize_mode(str(self._config.get("mode", "line")))
        self._priority = int(self._config.get("priority", 10))
        self._poll_interval = float(self._config.get("poll_interval", 0.2))
        connect_timeout = float(self._config.get("connect_timeout", 10.0))
        self._connect_attempts = max(1, int(self._config.get("connect_attempts", 2)))
        self._connect_retry_delay = max(
            0.0, float(self._config.get("connect_retry_delay", 0.5))
        )
        self._session_list_timeout = float(
            self._config.get("session_list_timeout", connect_timeout)
        )
        self._session_attach_timeout = float(
            self._config.get("session_attach_timeout", connect_timeout)
        )
        self._connected = False
        self._selector: str | None = None
        self._session: dict[str, Any] | None = None

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
        last_error: Exception | None = None
        for attempt in range(1, self._connect_attempts + 1):
            try:
                sessions = self._list_sessions()
                selector, session = self._resolve_session(params, sessions)
                session = self._ensure_ready_session(selector, session)
            except Exception as exc:
                last_error = exc
                if attempt >= self._connect_attempts:
                    raise
                if self._connect_retry_delay > 0.0:
                    time.sleep(self._connect_retry_delay)
                continue

            self._selector = str(
                session.get("session_id") or session.get("com") or session.get("alias") or selector
            )
            self._session = session
            self._connected = True
            return

        if last_error is not None:
            raise last_error

    def disconnect(self) -> None:
        self._connected = False
        self._selector = None
        self._session = None

    def execute(self, command: str, timeout: float = 30.0) -> dict[str, Any]:
        if not self._connected or not self._selector:
            raise RuntimeError("serialwrap transport is not connected")

        timeout_s = max(float(timeout), 0.1)
        start = time.monotonic()
        submit_payload = self._run_json(
            [
                "cmd",
                "submit",
                "--selector",
                self._selector,
                "--cmd",
                command,
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
            recovery_action = None
            try:
                self._attach_session()
            except Exception:
                recovery_action = None
            else:
                recovery_action = "ATTACH"
            return {
                "returncode": 124,
                "stdout": "",
                "stderr": str(exc),
                "elapsed": time.monotonic() - start,
                "cmd_id": cmd_id,
                "status": "timeout",
                "partial": False,
                "execution_mode": self._mode,
                "background_capture_id": None,
                "interactive_session_id": None,
                "recovery_action": recovery_action,
            }

        command_status = status_payload.get("command", {})
        stdout = str(command_status.get("stdout", "") or "").strip()
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
            "cmd_id": cmd_id,
            "status": command_status.get("status"),
            "partial": bool(command_status.get("partial", False)),
            "execution_mode": command_status.get("execution_mode"),
            "background_capture_id": command_status.get("background_capture_id"),
            "interactive_session_id": command_status.get("interactive_session_id"),
            "recovery_action": command_status.get("recovery_action"),
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
            if self._should_retry_with_attach(args, payload):
                self._attach_session()
                return self._run_json(args, timeout=timeout)
            raise RuntimeError(f"serialwrap command not ok: {' '.join(args)}: {stdout}")
        return payload

    def _ensure_ready_session(self, selector: str, session: dict[str, Any]) -> dict[str, Any]:
        state = str(session.get("state", "")).upper()
        if state == "READY":
            return session

        self._selector = str(
            session.get("session_id") or session.get("com") or session.get("alias") or selector
        )
        payload = self._attach_session()
        attached = payload.get("session")
        if not isinstance(attached, dict):
            raise RuntimeError(f"serialwrap attach returned no session payload: {selector}")
        attached_state = str(attached.get("state", "")).upper()
        if attached_state != "READY":
            raise RuntimeError(f"serialwrap session not READY: {selector} ({attached_state})")
        return attached

    def _attach_session(self) -> dict[str, Any]:
        selector = self._selector
        if not selector:
            raise RuntimeError("serialwrap attach requires resolved selector")
        payload = self._run_json(
            ["session", "attach", "--selector", selector],
            timeout=self._session_attach_timeout,
        )
        session = payload.get("session")
        if isinstance(session, dict):
            self._session = session
        return payload

    def _should_retry_with_attach(self, args: list[str], payload: dict[str, Any]) -> bool:
        if len(args) >= 2 and args[:2] == ["session", "attach"]:
            return False
        if not self._selector:
            return False
        if payload.get("error_code") != "SESSION_NOT_READY":
            return False
        if len(args) < 2 or args[:2] == ["session", "list"]:
            return False
        return True

    def _list_sessions(self) -> list[dict[str, Any]]:
        payload = self._run_json(["session", "list"], timeout=self._session_list_timeout)
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

    def _status_to_returncode(self, status: str, error_code: Any) -> int:
        status_lower = status.lower()
        if status_lower in {"done", "interactive"} and not error_code:
            return 0
        if status_lower == "timeout":
            return 124
        if status_lower in {"cancelled", "canceled"}:
            return 130
        return 1

    def _build_stderr(self, command_status: dict[str, Any]) -> str:
        details: list[str] = []
        stderr = str(command_status.get("stderr", "") or "").strip()
        error_code = command_status.get("error_code")
        status = str(command_status.get("status", ""))

        if stderr:
            details.append(stderr)
        if error_code:
            details.append(str(error_code))
        if status and status.lower() not in {"done", "running", "accepted", "interactive"}:
            details.append(f"status={status}")
        return "; ".join(details)

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        normalized = MODE_ALIASES.get(mode.strip().lower(), mode.strip().lower())
        if normalized not in {"line", "background", "interactive"}:
            return "line"
        return normalized

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
