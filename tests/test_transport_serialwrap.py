"""Tests for serialwrap transport."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

import pytest

from testpilot.transport.serialwrap import SerialWrapTransport


def _cp(args: list[str], payload: dict[str, Any], returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=json.dumps(payload),
        stderr="",
    )


def test_connect_resolves_by_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float | None,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
        assert timeout is not None
        assert args[0] == "/tmp/serialwrap"
        assert args[1:3] == ["session", "list"]
        return _cp(
            args,
            {
                "ok": True,
                "sessions": [
                    {
                        "alias": "dut-main",
                        "com": "COM7",
                        "session_id": "lab:COM7",
                        "state": "READY",
                    }
                ],
            },
        )

    monkeypatch.setattr("testpilot.transport.serialwrap.subprocess.run", fake_run)
    transport = SerialWrapTransport({"binary": "/tmp/serialwrap", "alias": "dut-main"})
    transport.connect()

    assert transport.is_connected is True
    assert transport.session is not None
    assert transport.session["session_id"] == "lab:COM7"


def test_connect_resolves_by_serial_port(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float | None,
    ) -> subprocess.CompletedProcess[str]:
        assert args[1:3] == ["session", "list"]
        return _cp(
            args,
            {
                "ok": True,
                "sessions": [
                    {
                        "alias": "dut-main",
                        "com": "COM2",
                        "session_id": "lab:COM2",
                        "device_by_id": "/dev/serial/by-id/usb-target-2",
                        "state": "READY",
                    }
                ],
            },
        )

    monkeypatch.setattr("testpilot.transport.serialwrap.subprocess.run", fake_run)
    transport = SerialWrapTransport(
        {
            "binary": "/tmp/serialwrap",
            "serial_port": "/dev/serial/by-id/usb-target-2",
        }
    )
    transport.connect()

    assert transport.is_connected is True
    assert transport.session is not None
    assert transport.session["com"] == "COM2"


def test_execute_submit_poll_and_tail_text(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {
        "status_calls": 0,
        "marker_token": None,
        "from_seq": None,
    }

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float | None,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, timeout
        op = tuple(args[1:3])

        if op == ("session", "list"):
            return _cp(
                args,
                {
                    "ok": True,
                    "sessions": [
                        {
                            "alias": "dut-main",
                            "com": "COM0",
                            "session_id": "lab:COM0",
                            "state": "READY",
                        }
                    ],
                },
            )

        if op == ("log", "tail-text") and "--from-seq" not in args:
            return _cp(
                args,
                {
                    "ok": True,
                    "lines": [
                        "2026-03-04T00:00:00+00:00 1000 41 COM0 RX device - 1 abc | root@dev:/# "
                    ],
                },
            )

        if op == ("cmd", "submit"):
            command_text = args[args.index("--cmd") + 1]
            match = re.search(r"__TP_BEGIN_([0-9a-f]+)__", command_text)
            assert match is not None
            state["marker_token"] = match.group(1)
            return _cp(
                args,
                {
                    "ok": True,
                    "cmd_id": "cmd-001",
                    "status": "accepted",
                },
            )

        if op == ("cmd", "status"):
            state["status_calls"] += 1
            if state["status_calls"] == 1:
                return _cp(
                    args,
                    {
                        "ok": True,
                        "command": {
                            "cmd_id": "cmd-001",
                            "status": "running",
                        },
                    },
                )
            return _cp(
                args,
                {
                    "ok": True,
                    "command": {
                        "cmd_id": "cmd-001",
                        "status": "done",
                        "error_code": None,
                        "command": "echo hello",
                    },
                },
            )

        if op == ("log", "tail-text") and "--from-seq" in args:
            state["from_seq"] = args[args.index("--from-seq") + 1]
            token = state["marker_token"]
            assert token is not None
            return _cp(
                args,
                {
                    "ok": True,
                    "lines": [
                        (
                            "2026-03-04T00:00:01+00:00 1000 42 COM0 RX device - 1 abc | "
                            f"__TP_BEGIN_{token}__\n"
                        ),
                        "2026-03-04T00:00:01+00:00 1000 43 COM0 RX device - 1 abc | hello world\n",
                        (
                            "2026-03-04T00:00:01+00:00 1000 44 COM0 RX device - 1 abc | "
                            f"__TP_RC_{token}__=7\n"
                        ),
                        (
                            "2026-03-04T00:00:01+00:00 1000 45 COM0 RX device - 1 abc | "
                            f"__TP_END_{token}__\n"
                        ),
                    ],
                },
            )

        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr("testpilot.transport.serialwrap.subprocess.run", fake_run)
    monkeypatch.setattr(
        SerialWrapTransport,
        "_ensure_mirror_path",
        lambda self: "/tmp/serialwrap-test-mirror.log",
    )
    monkeypatch.setattr(
        SerialWrapTransport,
        "_read_last_seq_from_mirror",
        lambda self, path: 41,
    )
    transport = SerialWrapTransport(
        {
            "binary": "/tmp/serialwrap",
            "selector": "COM0",
            "poll_interval": 0.0,
        }
    )
    transport.connect()
    result = transport.execute("echo hello", timeout=5.0)

    assert result["returncode"] == 7
    assert "hello world" in result["stdout"]
    assert result["stderr"] == ""
    assert result["elapsed"] >= 0.0
    assert state["status_calls"] >= 2
    assert state["from_seq"] == "42"


def test_execute_stdout_fallback_when_tail_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"status_calls": 0}

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: float | None,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, timeout
        op = tuple(args[1:3])

        if op == ("session", "list"):
            return _cp(
                args,
                {
                    "ok": True,
                    "sessions": [
                        {
                            "alias": "dut-main",
                            "com": "COM0",
                            "session_id": "lab:COM0",
                            "state": "READY",
                        }
                    ],
                },
            )

        if op == ("log", "tail-text"):
            return _cp(args, {"ok": True, "lines": []})

        if op == ("cmd", "submit"):
            return _cp(args, {"ok": True, "cmd_id": "cmd-002", "status": "accepted"})

        if op == ("cmd", "status"):
            state["status_calls"] += 1
            return _cp(
                args,
                {
                    "ok": True,
                    "command": {
                        "cmd_id": "cmd-002",
                        "status": "done",
                        "error_code": None,
                        "command": "uname -a",
                    },
                },
            )

        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr("testpilot.transport.serialwrap.subprocess.run", fake_run)
    monkeypatch.setattr(
        SerialWrapTransport,
        "_ensure_mirror_path",
        lambda self: "/tmp/serialwrap-test-mirror.log",
    )
    monkeypatch.setattr(
        SerialWrapTransport,
        "_read_last_seq_from_mirror",
        lambda self, path: 999,
    )
    transport = SerialWrapTransport(
        {
            "binary": "/tmp/serialwrap",
            "selector": "COM0",
            "poll_interval": 0.0,
            "use_marker": False,
        }
    )
    transport.connect()
    result = transport.execute("uname -a", timeout=5.0)

    assert result["returncode"] == 0
    assert result["stdout"] == "uname -a"
    assert result["stderr"] == ""
    assert state["status_calls"] == 1


def test_read_last_seq_from_mirror_parses_tail_line(tmp_path: Path) -> None:
    mirror = tmp_path / "raw.mirror.log"
    mirror.write_text(
        (
            "2026-03-04T08:29:02.417028+00:00 198725531924298 15273 COM0 TX "
            "agent:testpilot abc | cmd1\n"
            "2026-03-04T08:29:02.450118+00:00 198725565012981 15274 COM0 RX "
            "device - 192 def | cmd2\n"
        ),
        encoding="utf-8",
    )

    transport = SerialWrapTransport({"binary": "/tmp/serialwrap", "selector": "COM0"})
    assert transport._read_last_seq_from_mirror(str(mirror)) == 15274


def test_read_last_seq_from_wal_parses_seq(tmp_path: Path) -> None:
    wal = tmp_path / "raw.wal.ndjson"
    wal.write_text(
        (
            '{"seq": 101, "dir": "TX"}\n'
            '{"seq": 102, "dir": "RX"}\n'
        ),
        encoding="utf-8",
    )

    transport = SerialWrapTransport({"binary": "/tmp/serialwrap", "selector": "COM0"})
    assert transport._read_last_seq_from_wal(str(wal)) == 102
