from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from testpilot.core.orchestrator import Orchestrator
from testpilot.reporting import log_capture


def _record(seq: int, com: str, text: str) -> dict[str, Any]:
    return {
        "seq": seq,
        "com": com,
        "payload_b64": base64.b64encode(text.encode()).decode(),
    }


def test_export_serialwrap_logs_exports_complete_current_run_range(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[dict[str, int | None]] = []
    records = [
        _record(101, "COM0", "dut run start\n"),
        _record(102, "COM1", "sta run start\n"),
        _record(130, "COM0", "dut run end\n"),
    ]

    def export_records(
        *,
        from_seq: int = 1,
        to_seq: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        calls.append({"from_seq": from_seq, "to_seq": to_seq, "limit": limit})
        return records

    monkeypatch.setattr(log_capture, "export_records", export_records)
    orch = SimpleNamespace(
        config=SimpleNamespace(
            devices={
                "dut": {"com_port": "COM0"},
                "sta": {"com_port": "COM1"},
            }
        )
    )

    result = Orchestrator._export_serialwrap_logs(
        orch,  # type: ignore[arg-type]
        run_id="run-1",
        artifact_dir=tmp_path,
        case_seq_ranges={"case-1": {"seq_start": 101, "seq_end": 130}},
        case_results=[],
        run_seq_start=100,
        run_seq_end=130,
    )

    assert calls == [{"from_seq": 101, "to_seq": 130, "limit": 0}]
    assert Path(result["dut_log_path"]).read_text(encoding="utf-8") == (
        "dut run start\ndut run end\n"
    )
    assert Path(result["sta_log_path"]).read_text(encoding="utf-8") == "sta run start\n"
