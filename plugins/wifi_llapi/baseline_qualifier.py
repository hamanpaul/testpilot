"""Standalone baseline qualification workflow for wifi_llapi."""

from __future__ import annotations

import time
from typing import Any


class BaselineQualifier:
    """Qualify reusable DUT/STA connectivity before full wifi_llapi runs."""

    FACTORY_RESET_COMMAND = "firstboot -y;sync;sync;sync;reboot -f"
    REBOOT_WAIT_SECONDS = 90
    SOAK_CHECK_INTERVAL_SECONDS = 60

    def __init__(self, plugin: Any, topology: Any) -> None:
        self.plugin = plugin
        self.topology = topology

    def run(
        self,
        *,
        bands: tuple[str, ...],
        repeat_count: int,
        soak_minutes: int,
    ) -> dict[str, Any]:
        selected_bands = self._requested_bands(bands)
        band_results: list[dict[str, Any]] = []
        overall_status = "stable"

        for band in selected_bands:
            band_result = self._qualify_band(
                band=band,
                repeat_count=repeat_count,
                soak_minutes=soak_minutes,
            )
            band_results.append(band_result)
            if not band_result.get("stable"):
                overall_status = "unstable"

        return {
            "overall_status": overall_status,
            "bands": band_results,
            "repeat_count": repeat_count,
            "soak_minutes": soak_minutes,
        }

    def _requested_bands(self, bands: tuple[str, ...]) -> tuple[str, ...]:
        self.plugin._read_sta_available_bands(self.topology)
        available = tuple(self.plugin._sta_available_bands)
        raw_requested = bands or available

        selected: list[str] = []
        for item in raw_requested:
            band = self.plugin._normalize_band_name(item)
            if not band:
                raise ValueError(f"unsupported band: {item}")
            if band not in available:
                raise ValueError(f"band '{band}' is not enabled in testbed sta_available_bands")
            if band not in selected:
                selected.append(band)
        return tuple(selected)

    @staticmethod
    def _base_case() -> dict[str, Any]:
        return {
            "id": "wifi-llapi-baseline-qualify",
            "name": "wifi_llapi baseline qualification",
            "topology": {
                "devices": {
                    "DUT": {},
                    "STA": {},
                }
            },
            "steps": [],
        }

    def _band_case(self, band: str) -> dict[str, Any]:
        case = self.plugin._case_for_bands(self._base_case(), (band,))
        case["id"] = f"wifi-llapi-baseline-qualify-{band.replace('.', '')}"
        case["name"] = f"wifi_llapi baseline qualification {band}"
        return case

    def _qualify_band(
        self,
        *,
        band: str,
        repeat_count: int,
        soak_minutes: int,
    ) -> dict[str, Any]:
        case = self._band_case(band)
        rounds: list[dict[str, Any]] = []
        consecutive_successes = 0
        max_rounds = max(repeat_count * 2, repeat_count)

        for round_index in range(1, max_rounds + 1):
            case["_attempt_index"] = round_index
            round_result = self._run_round(
                case=case,
                band=band,
                round_index=round_index,
                soak_minutes=soak_minutes,
            )
            rounds.append(round_result)
            if round_result.get("success"):
                consecutive_successes += 1
                if consecutive_successes >= repeat_count:
                    break
            else:
                consecutive_successes = 0

        stable = consecutive_successes >= repeat_count
        last_failure = {}
        if rounds and not stable:
            last_failure = dict(rounds[-1].get("last_failure") or {})

        return {
            "band": band,
            "stable": stable,
            "repeat_count": repeat_count,
            "max_rounds": max_rounds,
            "completed_rounds": len(rounds),
            "consecutive_successes": consecutive_successes,
            "rounds": rounds,
            "last_failure": last_failure,
        }

    def _run_round(
        self,
        *,
        case: dict[str, Any],
        band: str,
        round_index: int,
        soak_minutes: int,
    ) -> dict[str, Any]:
        round_result: dict[str, Any] = {
            "round": round_index,
            "band": band,
            "success": False,
        }

        try:
            if not self._safe_setup_env(case):
                recovery = self._recover_and_reopen(
                    case,
                    devices=("DUT", "STA"),
                    reason="setup_env_failed",
                )
                round_result["setup_recovery"] = recovery
                if not recovery.get("success"):
                    round_result["last_failure"] = self._last_failure(case, phase="setup_env")
                    return round_result
            round_result["setup"] = {"success": True}

            preflight = self._collect_snapshot(case, band, phase="preflight")
            round_result["preflight"] = preflight
            if not preflight.get("trusted"):
                preflight_restore = self._restore_preflight(case, band)
                round_result["preflight_restore"] = preflight_restore
                if not preflight_restore.get("success"):
                    round_result["last_failure"] = dict(
                        preflight_restore.get("last_failure")
                        or self._last_failure(case, phase="preflight")
                    )
                    return round_result
                round_result["preflight"] = dict(preflight_restore.get("snapshot") or {})

            verify = self._verify_with_recovery(case)
            round_result["verify"] = verify
            if not verify.get("success"):
                round_result["last_failure"] = dict(
                    verify.get("last_failure") or self._last_failure(case, phase="verify_env")
                )
                return round_result

            post_verify = self._collect_snapshot(case, band, phase="post-verify")
            round_result["post_verify"] = post_verify
            if post_verify.get("hard_failures"):
                hard_failures = list(post_verify.get("hard_failures") or [])
                last_failure = {
                    "case_id": str(case.get("id", "")),
                    "attempt_index": round_index,
                    "phase": "post_verify",
                    "comment": "runtime drift detected after verify_env",
                    "category": "environment",
                    "reason_code": "runtime_drift_after_verify",
                    "device": "DUT",
                    "band": band,
                    "command": "",
                    "output": "\n".join(hard_failures),
                    "evidence": hard_failures,
                    "metadata": {
                        "issues": list(post_verify.get("issues") or []),
                    },
                }
                case["_last_failure"] = last_failure
                round_result["last_failure"] = last_failure
                return round_result

            soak = self._run_soak(case, band, soak_minutes)
            round_result["soak"] = soak
            if not soak.get("success"):
                round_result["last_failure"] = dict(
                    soak.get("last_failure") or self._last_failure(case, phase="soak")
                )
                return round_result

            round_result["success"] = True
            round_result["last_failure"] = {}
            return round_result
        except Exception as exc:  # pragma: no cover - defensive guardrail
            last_failure = self._exception_failure(
                case,
                phase="baseline_qualify",
                exc=exc,
            )
            case["_last_failure"] = last_failure
            round_result["last_failure"] = last_failure
            return round_result
        finally:
            if self.plugin._transports:
                self.plugin.teardown(case, self.topology)

    def _restore_preflight(self, case: dict[str, Any], band: str) -> dict[str, Any]:
        recovery = self._recover_and_reopen(
            case,
            devices=("DUT", "STA"),
            reason="preflight_untrusted",
        )
        if recovery.get("success"):
            snapshot = self._collect_snapshot(case, band, phase="preflight-recheck")
            if snapshot.get("trusted"):
                return {
                    "success": True,
                    "strategy": "session_recover",
                    "recovery": recovery,
                    "snapshot": snapshot,
                }

        reset = self._factory_reset_and_reopen(case, reason="preflight_untrusted")
        if reset.get("success"):
            snapshot = self._collect_snapshot(case, band, phase="preflight-after-reset")
            if snapshot.get("trusted"):
                return {
                    "success": True,
                    "strategy": "factory_reset",
                    "recovery": recovery,
                    "reset": reset,
                    "snapshot": snapshot,
                }

        return {
            "success": False,
            "strategy": "factory_reset",
            "recovery": recovery,
            "reset": reset,
            "last_failure": self._last_failure(case, phase="preflight"),
        }

    def _verify_with_recovery(self, case: dict[str, Any]) -> dict[str, Any]:
        if self._safe_verify_env(case):
            return {"success": True, "strategy": "direct"}

        first_failure = self._last_failure(case, phase="verify_env")
        recovery = self._recover_and_reopen(
            case,
            devices=("DUT", "STA"),
            reason="verify_env_failed",
        )
        if recovery.get("success") and self._safe_verify_env(case):
            return {
                "success": True,
                "strategy": "session_recover",
                "recovery": recovery,
            }

        reset = self._factory_reset_and_reopen(case, reason="verify_env_failed")
        if reset.get("success") and self._safe_verify_env(case):
            return {
                "success": True,
                "strategy": "factory_reset",
                "recovery": recovery,
                "reset": reset,
            }

        return {
            "success": False,
            "strategy": "factory_reset",
            "recovery": recovery,
            "reset": reset,
            "last_failure": self._last_failure(
                case,
                phase="verify_env",
                fallback=first_failure,
            ),
        }

    def _recover_devices(self, devices: tuple[str, ...]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        success = True
        for device in devices:
            outcome = dict(self.plugin._recover_serial_session(device, self.topology))
            outcome["device"] = device
            results.append(outcome)
            if not outcome.get("success"):
                success = False
        return {
            "success": success,
            "devices": results,
        }

    def _recover_and_reopen(
        self,
        case: dict[str, Any],
        *,
        devices: tuple[str, ...],
        reason: str,
    ) -> dict[str, Any]:
        recovery = self._recover_devices(devices)
        if not recovery.get("success"):
            return {
                "success": False,
                "reason": reason,
                "recovery": recovery,
            }

        opened = self._safe_setup_env(case)
        return {
            "success": opened,
            "reason": reason,
            "recovery": recovery,
        }

    def _factory_reset_and_reopen(self, case: dict[str, Any], *, reason: str) -> dict[str, Any]:
        reset_results: list[dict[str, Any]] = []
        for device_name in ("DUT", "STA"):
            transport = self.plugin._transports.get(device_name)
            if transport is None:
                return {
                    "success": False,
                    "reason": reason,
                    "devices": reset_results,
                    "comment": f"missing {device_name} transport",
                }
            try:
                result = self.plugin._execute_env_command(
                    transport,
                    self.FACTORY_RESET_COMMAND,
                    timeout=20.0,
                )
                output = self.plugin._env_output_text(result)
                returncode = int(result.get("returncode", 1))
            except Exception as exc:  # pragma: no cover - defensive transport wrapper
                output = str(exc)
                returncode = 1
            accepted = returncode in {0, 124}
            reset_results.append(
                {
                    "device": device_name,
                    "success": accepted,
                    "returncode": returncode,
                    "output": output,
                }
            )
            if not accepted:
                return {
                    "success": False,
                    "reason": reason,
                    "devices": reset_results,
                    "comment": output,
                }

        time.sleep(float(self.REBOOT_WAIT_SECONDS))
        reopened = self._recover_and_reopen(
            case,
            devices=("DUT", "STA"),
            reason=f"{reason}:post_reset",
        )
        return {
            "success": reopened.get("success", False),
            "reason": reason,
            "devices": reset_results,
            "reopen": reopened,
        }

    def _collect_snapshot(self, case: dict[str, Any], band: str, *, phase: str) -> dict[str, Any]:
        profile = dict(self.plugin.DEFAULT_BAND_BASELINES[band])
        iface = str(profile["iface"])
        ap = str(profile["ap"])
        radio = str(profile["radio"])
        ssid_index = str(profile["ssid_index"])
        commands: dict[str, dict[str, Any]] = {}
        issues: list[str] = []

        dut = self.plugin._transports.get("DUT")
        sta = self.plugin._transports.get("STA")
        if dut is None:
            issues.append("missing_dut_transport")
        if sta is None:
            issues.append("missing_sta_transport")

        if dut is not None:
            commands["dut.gate"] = self._snapshot_command(
                dut,
                'echo "__testpilot_baseline_gate__"',
            )
            commands["dut.radio_enable"] = self._snapshot_command(
                dut,
                f"ubus-cli WiFi.Radio.{radio}.Enable?",
            )
            commands["dut.ap_enable"] = self._snapshot_command(
                dut,
                f"ubus-cli WiFi.AccessPoint.{ap}.Enable?",
            )
            commands["dut.ssid"] = self._snapshot_command(
                dut,
                f"ubus-cli WiFi.SSID.{ssid_index}.SSID?",
            )
            commands["dut.security_mode"] = self._snapshot_command(
                dut,
                f"ubus-cli WiFi.AccessPoint.{ap}.Security.ModeEnabled?",
            )
            commands["dut.mfp"] = self._snapshot_command(
                dut,
                f"ubus-cli WiFi.AccessPoint.{ap}.Security.MFPConfig?",
            )
            commands["dut.bss"] = self._snapshot_command(dut, f"wl -i {iface} bss")
            commands["dut.assoclist"] = self._snapshot_command(dut, f"wl -i {iface} assoclist")
            commands["dut.hapd_primary"] = self._snapshot_command(
                dut,
                (
                    "grep -nE "
                    "'^(ssid=|wpa_key_mgmt=|sae_pwe=|ieee80211w=|ocv=|ieee80211be=|"
                    "bss=|multi_ap=|mld_unit=|mlo_aff_link_kde=)' "
                    f"/tmp/{iface}_hapd.conf 2>/dev/null || true"
                ),
            )
            commands["dut.hapd_secondary"] = self._snapshot_command(
                dut,
                (
                    "grep -nE "
                    "'^(ssid=|wpa_key_mgmt=|sae_pwe=|ieee80211w=|ocv=|ieee80211be=|"
                    "bss=|multi_ap=|mld_unit=|mlo_aff_link_kde=)' "
                    f"/tmp/{iface}.1_hapd.conf 2>/dev/null || true"
                ),
            )
            commands["dut.mlo_config"] = self._snapshot_command(
                dut,
                "nvram get wl_mlo_config 2>/dev/null || true",
            )

        if sta is not None:
            commands["sta.gate"] = self._snapshot_command(
                sta,
                'echo "__testpilot_baseline_gate__"',
            )
            commands["sta.iw_dev"] = self._snapshot_command(sta, "iw dev")
            commands["sta.link"] = self._snapshot_command(sta, f"iw dev {iface} link")
            commands["sta.status"] = self._snapshot_command(sta, f"wl -i {iface} status")
            commands["sta.wpa_status"] = self._snapshot_command(
                sta,
                f"wpa_cli -i {iface} status",
            )

        trusted = (
            commands.get("dut.gate", {}).get("success", False)
            and commands.get("sta.gate", {}).get("success", False)
        )

        iw_output = str(commands.get("sta.iw_dev", {}).get("output", "") or "")
        link_output = str(commands.get("sta.link", {}).get("output", "") or "")
        wl_status_output = str(commands.get("sta.status", {}).get("output", "") or "")
        hapd_primary = str(commands.get("dut.hapd_primary", {}).get("output", "") or "")
        hapd_secondary = str(commands.get("dut.hapd_secondary", {}).get("output", "") or "")
        combined_hapd = f"{hapd_primary}\n{hapd_secondary}".lower()

        if self._iw_iface_is_ap(iw_output, iface):
            issues.append("sta_iface_not_managed")
        if "connected to " in link_output.lower() or "ssid:" in wl_status_output.lower():
            issues.append("sta_link_already_active")
        if "bss=" in hapd_primary.lower() or hapd_secondary.strip():
            issues.append("dut_secondary_bss_present")
        if band == "6g":
            if "ocv=0" not in combined_hapd:
                issues.append("dut_ocv_not_zero")
            if "ieee80211be=1" in hapd_secondary.lower():
                issues.append("dut_secondary_eht_present")

        hard_failures: list[str] = []
        if phase == "post-verify" and band == "6g":
            for issue in issues:
                if issue in {"dut_ocv_not_zero"}:
                    hard_failures.append(issue)

        return {
            "phase": phase,
            "band": band,
            "trusted": trusted,
            "issues": issues,
            "hard_failures": hard_failures,
            "commands": commands,
        }

    def _snapshot_command(self, transport: Any, command: str, timeout: float = 10.0) -> dict[str, Any]:
        try:
            result = self.plugin._execute_env_command(transport, command, timeout=timeout)
            output = self.plugin._env_output_text(result)
            returncode = int(result.get("returncode", 1))
            status = str(result.get("status", "") or "")
        except Exception as exc:  # pragma: no cover - defensive transport wrapper
            output = str(exc)
            returncode = 1
            status = "error"
        return {
            "command": command,
            "returncode": returncode,
            "status": status,
            "success": returncode == 0,
            "output": output,
        }

    @staticmethod
    def _iw_iface_is_ap(iw_output: str, iface: str) -> bool:
        lines = [line.strip() for line in str(iw_output).splitlines()]
        for index, line in enumerate(lines):
            if line == f"Interface {iface}":
                for probe in lines[index + 1 : index + 4]:
                    if probe.startswith("type "):
                        return probe == "type AP"
        return False

    def _run_soak(self, case: dict[str, Any], band: str, soak_minutes: int) -> dict[str, Any]:
        duration_seconds = max(0, int(soak_minutes * 60))
        if duration_seconds == 0:
            return {
                "success": True,
                "band": band,
                "duration_seconds": 0,
                "checks": [],
            }

        interval = min(self.SOAK_CHECK_INTERVAL_SECONDS, duration_seconds)
        checks: list[dict[str, Any]] = []
        elapsed = 0
        while elapsed < duration_seconds:
            sleep_seconds = min(interval, duration_seconds - elapsed)
            time.sleep(float(sleep_seconds))
            elapsed += sleep_seconds
            try:
                ok = self.plugin._verify_sta_band_connectivity(case)
            except Exception as exc:  # pragma: no cover - defensive transport wrapper
                case["_last_failure"] = self._exception_failure(
                    case,
                    phase="soak",
                    exc=exc,
                )
                ok = False
            check = {
                "elapsed_seconds": elapsed,
                "success": ok,
            }
            checks.append(check)
            if not ok:
                return {
                    "success": False,
                    "band": band,
                    "duration_seconds": duration_seconds,
                    "checks": checks,
                    "last_failure": self._last_failure(case, phase="soak"),
                }

        return {
            "success": True,
            "band": band,
            "duration_seconds": duration_seconds,
            "checks": checks,
        }

    def _safe_setup_env(self, case: dict[str, Any]) -> bool:
        try:
            return bool(self.plugin.setup_env(case, self.topology))
        except Exception as exc:
            case["_last_failure"] = self._exception_failure(
                case,
                phase="setup_env",
                exc=exc,
            )
            return False

    def _safe_verify_env(self, case: dict[str, Any]) -> bool:
        try:
            return bool(self.plugin.verify_env(case, self.topology))
        except Exception as exc:
            case["_last_failure"] = self._exception_failure(
                case,
                phase="verify_env",
                exc=exc,
            )
            return False

    def _exception_failure(self, case: dict[str, Any], *, phase: str, exc: Exception) -> dict[str, Any]:
        return {
            "case_id": str(case.get("id", "") or ""),
            "attempt_index": int(case.get("_attempt_index", 1) or 1),
            "phase": phase,
            "comment": str(exc) or exc.__class__.__name__,
            "category": "environment",
            "reason_code": "runtime_exception",
            "device": "",
            "band": "",
            "command": "",
            "output": str(exc),
            "evidence": [],
            "metadata": {
                "exception_type": exc.__class__.__name__,
            },
        }

    @staticmethod
    def _normalize_failure_snapshot(snapshot: Any) -> dict[str, Any]:
        if not isinstance(snapshot, dict):
            return {}
        return {
            "case_id": str(snapshot.get("case_id", "") or ""),
            "attempt_index": int(snapshot.get("attempt_index", 1) or 1),
            "phase": str(snapshot.get("phase", "") or ""),
            "comment": str(snapshot.get("comment", "") or ""),
            "category": str(snapshot.get("category", "") or ""),
            "reason_code": str(snapshot.get("reason_code", "") or ""),
            "device": str(snapshot.get("device", "") or ""),
            "band": str(snapshot.get("band", "") or ""),
            "command": str(snapshot.get("command", "") or ""),
            "output": str(snapshot.get("output", "") or ""),
            "evidence": list(snapshot.get("evidence") or []),
            "metadata": dict(snapshot.get("metadata") or {}),
        }

    def _last_failure(
        self,
        case: dict[str, Any],
        *,
        phase: str,
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot = self._normalize_failure_snapshot(case.get("_last_failure"))
        if snapshot:
            return snapshot
        if fallback:
            normalized = self._normalize_failure_snapshot(fallback)
            if normalized:
                return normalized
        return {
            "case_id": str(case.get("id", "") or ""),
            "attempt_index": int(case.get("_attempt_index", 1) or 1),
            "phase": phase,
            "comment": "baseline qualification failed without failure snapshot",
            "category": "environment",
            "reason_code": "missing_failure_snapshot",
            "device": "",
            "band": "",
            "command": "",
            "output": "",
            "evidence": [],
            "metadata": {},
        }
