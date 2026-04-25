#!/usr/bin/env python3
"""One-shot wifi_llapi inventory alignment (2026-04-24).

See docs/superpowers/specs/2026-04-24-wifi-llapi-align-missing-rows-design.md
for the full design and acceptance criteria.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_XLSX = REPO_ROOT / "plugins" / "wifi_llapi" / "reports" / "templates" / "wifi_llapi_template.xlsx"
CASES_DIR = REPO_ROOT / "plugins" / "wifi_llapi" / "cases"
TEMPLATE_YAML = CASES_DIR / "_template.yaml"
THIS_DIR = Path(__file__).resolve().parent

PLAN_RENAMES = [
    ("D068_discoverymethodenabled_accesspoint_fils.yaml", "D066_discoverymethodenabled_accesspoint_fils.yaml", 66, "wifi-llapi-D066-discoverymethodenabled-accesspoint-fils"),
    ("D068_discoverymethodenabled_accesspoint_upr.yaml", "D067_discoverymethodenabled_accesspoint_upr.yaml", 67, "wifi-llapi-D067-discoverymethodenabled-accesspoint-upr"),
    ("D115_getstationstats_accesspoint.yaml", "D109_getstationstats.yaml", 109, "wifi-llapi-D109-getstationstats"),
    ("D115_getstationstats_active.yaml", "D110_getstationstats_active.yaml", 110, "wifi-llapi-D110-getstationstats-active"),
    ("D115_getstationstats_associationtime.yaml", "D111_getstationstats_associationtime.yaml", 111, "wifi-llapi-D111-getstationstats-associationtime"),
    ("D115_getstationstats_authenticationstate.yaml", "D112_getstationstats_authenticationstate.yaml", 112, "wifi-llapi-D112-getstationstats-authenticationstate"),
    ("D115_getstationstats_avgsignalstrength.yaml", "D113_getstationstats_avgsignalstrength.yaml", 113, "wifi-llapi-D113-getstationstats-avgsignalstrength"),
    ("D115_getstationstats_avgsignalstrengthbychain.yaml", "D114_getstationstats_avgsignalstrengthbychain.yaml", 114, "wifi-llapi-D114-getstationstats-avgsignalstrengthbychain"),
]

PLAN_MOVE = ("D495_retrycount_ssid_stats_basic.yaml", "D407_retrycount_ssid_stats.yaml", 407, "wifi-llapi-D407-retrycount")
PLAN_METADATA_ONLY = [("D495_retrycount_ssid_stats_verified.yaml", 495, None)]
PLAN_DELETES = [
    "D096_uapsdenable.yaml",
    "D097_vendorie.yaml",
    "D100_wmmenable.yaml",
    "D102_configmethodssupported.yaml",
    "D106_relaycredentialsenable.yaml",
    "D474_channel_radio_37.yaml",
]
PLAN_CREATE = {
    "filename": "D428_channel_neighbour.yaml",
    "row": 428,
    "id": "wifi-llapi-D428-channel-neighbour",
    "name": "Channel — WiFi.AccessPoint.{i}.Neighbour.{i}.",
    "object": "WiFi.AccessPoint.{i}.Neighbour.{i}.",
    "api": "Channel",
    "hlapi_command": 'ubus-cli "WiFi.AccessPoint.{i}.Neighbour.{i}.Channel=36"',
    "llapi_support": "Support",
}


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
    if args.apply:
        print("mode: apply")
    else:
        print("mode: dry-run | plan: 8 renames + 1 move + 1 metadata-only + 6 deletes + 1 create")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
