#!/usr/bin/env python3
"""One-shot wifi_llapi inventory alignment (2026-04-24).

See docs/superpowers/specs/2026-04-24-wifi-llapi-align-missing-rows-design.md
for the full design and acceptance criteria.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TypedDict

from openpyxl import load_workbook
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_XLSX = REPO_ROOT / "plugins" / "wifi_llapi" / "reports" / "templates" / "wifi_llapi_template.xlsx"
CASES_DIR = REPO_ROOT / "plugins" / "wifi_llapi" / "cases"
TEMPLATE_YAML = CASES_DIR / "_template.yaml"
THIS_DIR = Path(__file__).resolve().parent
_FN_ROW_RE = re.compile(r"^D(\d{3,4})_")

PLAN_RENAMES: list[tuple[str, str, int, str]] = [
    ("D068_discoverymethodenabled_accesspoint_fils.yaml", "D066_discoverymethodenabled_accesspoint_fils.yaml", 66, "wifi-llapi-D066-discoverymethodenabled-accesspoint-fils"),
    ("D068_discoverymethodenabled_accesspoint_upr.yaml", "D067_discoverymethodenabled_accesspoint_upr.yaml", 67, "wifi-llapi-D067-discoverymethodenabled-accesspoint-upr"),
    ("D115_getstationstats_accesspoint.yaml", "D109_getstationstats.yaml", 109, "wifi-llapi-D109-getstationstats"),
    ("D115_getstationstats_active.yaml", "D110_getstationstats_active.yaml", 110, "wifi-llapi-D110-getstationstats-active"),
    ("D115_getstationstats_associationtime.yaml", "D111_getstationstats_associationtime.yaml", 111, "wifi-llapi-D111-getstationstats-associationtime"),
    ("D115_getstationstats_authenticationstate.yaml", "D112_getstationstats_authenticationstate.yaml", 112, "wifi-llapi-D112-getstationstats-authenticationstate"),
    ("D115_getstationstats_avgsignalstrength.yaml", "D113_getstationstats_avgsignalstrength.yaml", 113, "wifi-llapi-D113-getstationstats-avgsignalstrength"),
    ("D115_getstationstats_avgsignalstrengthbychain.yaml", "D114_getstationstats_avgsignalstrengthbychain.yaml", 114, "wifi-llapi-D114-getstationstats-avgsignalstrengthbychain"),
]

PLAN_MOVE: tuple[str, str, int, str] = ("D495_retrycount_ssid_stats_basic.yaml", "D407_retrycount_ssid_stats.yaml", 407, "wifi-llapi-D407-retrycount")
PLAN_METADATA_ONLY: list[tuple[str, int, str | None]] = [("D495_retrycount_ssid_stats_verified.yaml", 495, None)]
PLAN_DELETES: list[str] = [
    "D096_uapsdenable.yaml",
    "D097_vendorie.yaml",
    "D100_wmmenable.yaml",
    "D102_configmethodssupported.yaml",
    "D106_relaycredentialsenable.yaml",
    "D474_channel_radio_37.yaml",
]
PLAN_CREATE: dict[str, object] = {
    "filename": "D428_channel_neighbour.yaml",
    "row": 428,
    "id": "wifi-llapi-D428-channel-neighbour",
    "name": "Channel — WiFi.AccessPoint.{i}.Neighbour.{i}.",
    "object": "WiFi.AccessPoint.{i}.Neighbour.{i}.",
    "api": "Channel",
    "hlapi_command": 'ubus-cli "WiFi.AccessPoint.{i}.Neighbour.{i}.Channel=36"',
    "llapi_support": "Support",
}


class SupportRow(TypedDict):
    object: str
    type: str
    param: str
    hlapi: str


class CaseInfo(TypedDict):
    source_row: int | None
    id: str | None


def load_support_rows(xlsx: Path = TEMPLATE_XLSX) -> dict[int, SupportRow]:
    wb = load_workbook(xlsx, read_only=True)
    ws = wb["Wifi_LLAPI"]
    out: dict[int, SupportRow] = {}
    for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True), start=2):
        if row[0] is None and row[3] is None:
            continue
        e = (row[4] or "").strip() if row[4] else ""
        if e == "Support":
            out[i] = {
                "object": row[0] or "",
                "type": row[1] or "",
                "param": (row[2] or "").strip() if row[2] else "",
                "hlapi": row[3] or "",
            }
    return out


def scan_cases(cases_dir: Path = CASES_DIR) -> dict[str, CaseInfo]:
    yaml_loader = YAML(typ="safe")
    out: dict[str, CaseInfo] = {}
    for f in sorted(cases_dir.glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        d = yaml_loader.load(f)
        if not isinstance(d, dict):
            continue
        sr = (d.get("source") or {}).get("row")
        out[f.name] = {
            "source_row": int(sr) if sr is not None else None,
            "id": d.get("id"),
        }
    return out


def filename_row(name: str) -> int | None:
    m = _FN_ROW_RE.match(name)
    return int(m.group(1)) if m else None


def _self_check_plan_counts() -> None:
    assert len(PLAN_RENAMES) == 8, len(PLAN_RENAMES)
    assert len(PLAN_METADATA_ONLY) == 1
    assert len(PLAN_DELETES) == 6
    # net cases delta = -6 (deletes) + 1 (create) = -5; renames/move/metadata are net 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually mutate the working tree (default: dry-run).")
    args = parser.parse_args(argv)
    _self_check_plan_counts()
    plan_summary = (
        f"plan: {len(PLAN_RENAMES)} renames + 1 move + "
        f"{len(PLAN_METADATA_ONLY)} metadata-only + {len(PLAN_DELETES)} deletes + 1 create"
    )
    if args.apply:
        print(f"mode: apply | {plan_summary}")
    else:
        print(f"mode: dry-run | {plan_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
