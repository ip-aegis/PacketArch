#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Closed-loop realism enforcement demonstration (patent supporting evidence).

Standalone — NO database, NO server, NO network. Builds a deliberately-broken
synthetic OT scenario in memory, runs the REAL readiness checker over it to
DETECT the realism violations (BEFORE), applies the REAL auto-repair functions
to FIX them, then re-runs the readiness checker to CONFIRM the scenario is clean
(AFTER).

Every function exercised here is the same production code path the platform runs
at scenario-create / scenario-save time:

  * compute_scenario_readiness()  — app/api/routes/scenarios.py  (pure detector)
  * auto_repair_protocols()        — app/services/scenario_enrichment.py
  * narrow_protocols_by_vendor()   — app/services/scenario_enrichment.py
  * repair_flow_protocols()        — app/services/scenario_enrichment.py
  * ensure_device_flow_coverage()  — app/services/scenario_enrichment.py (async)
  * canonical_mac()                — app/protocol_engines/canonical_identity.py

The broken devices use REAL vendor/model values from the device-template catalog
so the repairs actually resolve against the canonical fingerprint cache.

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/demo_realism_enforcement.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# A SECRET_KEY is required by the settings model when the fingerprint cache
# attempts (and gracefully fails) to load optional DB enhancements. Provide an
# ephemeral one so the standalone run is quiet — no DB is ever touched.
os.environ.setdefault("SECRET_KEY", "demo-" + "0" * 60)

# Quiet the catalog build for a clean exhibit. Building the in-memory
# fingerprint cache legitimately logs (a) per-template firmware-parse warnings
# and (b) a graceful "no DB enhancements" error when no Postgres is running —
# both are benign for a standalone run with no database. Suppress them so the
# console shows only the BEFORE / REPAIRS / AFTER report.
logging.disable(logging.CRITICAL)

from app.api.routes.scenarios import compute_scenario_readiness  # noqa: E402
from app.protocol_engines.canonical_identity import canonical_mac  # noqa: E402
from app.services.fingerprint_cache import get_fingerprint_cache  # noqa: E402
from app.services.scenario_enrichment import (  # noqa: E402
    auto_repair_protocols,
    ensure_device_flow_coverage,
    narrow_protocols_by_vendor,
    repair_flow_protocols,
)

SCENARIO_ID = "demo-realism-0001"


# ----------------------------------------------------------------------
# A deliberately-broken synthetic OT scenario.
#
# Real vendor/model values, hydrated with the FULL catalog fingerprint (the
# same thing the create-time materializer attaches), so the repairs resolve
# against the canonical cache and the fingerprint-coverage check is realistic.
# Each control device is seeded with at least one realism violation:
#
#   plc_siemens   — GENERIC NAME ("device_001"); carries EtherNet/IP which a
#                   Siemens device does not speak (vendor-protocol affinity);
#                   MAC uses a Rockwell OUI (MAC-vendor mismatch).
#   plc_schneider — MAC uses a Siemens OUI (MAC-vendor mismatch); is the only
#                   endpoint of a flow whose protocol (s7comm) neither endpoint
#                   speaks (flow-protocol consistency).
#   plc_rockwell  — ORPHAN: participates in no flow at all (CV cannot
#                   fingerprint it); carries PROFINET which a Rockwell device
#                   does not speak (vendor-protocol affinity).
#
# scada_server is a correctly-formed L3 supervisory device — it gives the
# orphan a rational northbound partner so the coverage repair can heal it.
# ----------------------------------------------------------------------
def _hydrate_fingerprint(vendor: str, model: str) -> dict:
    """Pull the full catalog fingerprint for vendor/model, mirroring what the
    create-time materializer attaches to each device. Falls back to a bare
    {vendor, model} stub on a cache miss (still enough for the repairs)."""
    fp = get_fingerprint_cache().get_by_vendor_model(vendor, model)
    return dict(fp) if fp else {"vendor": vendor, "model": model}


def build_broken_scenario() -> dict:
    return {
        "devices": {
            "plc_siemens": {
                "id": "plc_siemens",
                # VIOLATION 1: generic, non-descriptive name.
                "name": "device_001",
                "type": "plc",
                "vendor": "siemens",
                "zoneId": "zone_control",
                # VIOLATION 2: ethernet_ip is not a Siemens-native protocol.
                "protocols": ["profinet", "s7comm", "ethernet_ip"],
                "network": {
                    "ipAddress": "10.1.2.10",
                    # VIOLATION 4: Rockwell OUI (00:1D:9C) on a Siemens device.
                    "macAddress": "00:1D:9C:11:22:33",
                },
                "vendorFingerprint": _hydrate_fingerprint(
                    "siemens", "6ES7 517-3AP00-0AB0"
                ),
            },
            "plc_schneider": {
                "id": "plc_schneider",
                "name": "Stamping_Cell_Modicon_PLC_01",
                "type": "plc",
                "vendor": "schneider",
                "zoneId": "zone_control",
                "protocols": ["modbus_tcp", "ethernet_ip"],
                "network": {
                    "ipAddress": "10.1.2.11",
                    # VIOLATION 4: Siemens OUI (00:0E:8C) on a Schneider device.
                    "macAddress": "00:0E:8C:44:55:66",
                },
                "vendorFingerprint": _hydrate_fingerprint(
                    "schneider", "BMEP586040"
                ),
            },
            "plc_rockwell": {
                "id": "plc_rockwell",
                "name": "Assembly_Logix_Controller_01",
                "type": "plc",
                "vendor": "rockwell",
                "zoneId": "zone_control",
                # VIOLATION 2: profinet is not a Rockwell-native protocol.
                "protocols": ["ethernet_ip", "profinet"],
                "network": {
                    "ipAddress": "10.1.2.12",
                    # Correct Rockwell OUI — this device's only sins are the
                    # orphan status and the profinet affinity warning.
                    "macAddress": "00:00:BC:77:88:99",
                },
                "vendorFingerprint": _hydrate_fingerprint(
                    "rockwell", "1756-L85E"
                ),
            },
            # Correctly-formed supervisory device (the orphan's coverage
            # partner). Same control zone as the PLCs so the synthesised
            # coverage flow is intra-zone (no conduit needed).
            "scada_server": {
                "id": "scada_server",
                "name": "Plant_SCADA_Primary_01",
                "type": "scada_server",
                "vendor": "rockwell",
                "zoneId": "zone_control",
                "protocols": ["ethernet_ip", "snmp"],
                "network": {
                    "ipAddress": "10.1.2.20",
                    "macAddress": canonical_mac(
                        "scada_server", SCENARIO_ID, vendor="rockwell",
                        oui_prefixes=["00:00:BC", "00:1D:9C"],
                    ).upper(),
                },
                "vendorFingerprint": _hydrate_fingerprint(
                    "rockwell", "1756-L85E"
                ),
            },
        },
        "flows": {
            # VIOLATION 3 (flow protocol consistency): this flow declares
            # s7comm, but its Schneider/Siemens endpoints don't BOTH speak it
            # — and the generator would silently drop it. (plc_rockwell is left
            # out of every flow on purpose → orphan.)
            "flow_001": {
                "id": "flow_001",
                "sourceDeviceId": "plc_siemens",
                "targetDeviceId": "plc_schneider",
                "protocol": "s7comm",
                "timing_model": {"poll_interval_ms": 1000},
            },
            # A well-formed flow so the SCADA server isn't itself an orphan.
            "flow_002": {
                "id": "flow_002",
                "sourceDeviceId": "scada_server",
                "targetDeviceId": "plc_siemens",
                "protocol": "snmp",
                "timing_model": {"poll_interval_ms": 5000},
            },
        },
        "zones": {
            "zone_control": {
                "id": "zone_control",
                "name": "Control Network",
                "level": 2,
                "purdueLevel": 2,
                "network": {"subnet": "10.1.2.0/24"},
            },
        },
    }


# ----------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------
def _print_readiness(summary, label: str) -> None:
    passed = [c for c in summary.checks if c.passed]
    failed = [c for c in summary.checks if not c.passed]
    print(f"  Readiness score: {summary.score}/100   status: {summary.status}")
    print(
        f"  Checks: {len(passed)}/{len(summary.checks)} passed   "
        f"({summary.error_count} error, {summary.warning_count} warning failing)"
    )
    print()
    name_w = max(len(c.name) for c in summary.checks)
    for c in summary.checks:
        mark = "PASS" if c.passed else "FAIL"
        sev = "" if c.passed else f"[{c.severity}]"
        line = f"    {mark}  {c.name.ljust(name_w)}  {sev}"
        if not c.passed and c.message:
            line += f"\n          -> {c.message}"
        print(line)
    print()
    if failed:
        print(f"  {label}: {len(failed)} realism violation(s) detected.")
    else:
        print(f"  {label}: no violations — scenario is clean.")


def _hr(char: str = "=") -> str:
    return char * 74


def _regenerate_macs(definition: dict) -> int:
    """Realign each device's MAC OUI to its declared vendor using the
    deterministic, vendor-appropriate canonical_mac() generator (the same
    derivation the platform persists at create-time). Returns the count of
    devices whose MAC was rewritten.
    """
    fixed = 0
    for did, device in definition.get("devices", {}).items():
        fp = device.get("vendorFingerprint") or {}
        vendor = fp.get("vendor") or device.get("vendor")
        new_mac = canonical_mac(
            did,
            SCENARIO_ID,
            vendor=vendor,
            oui_prefixes=fp.get("oui_prefixes"),
        )
        old_mac = device.get("network", {}).get("macAddress", "")
        if new_mac.upper() != old_mac.upper():
            device.setdefault("network", {})["macAddress"] = new_mac.upper()
            fixed += 1
    return fixed


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    definition = build_broken_scenario()

    print(_hr())
    print("  PacketArch — Closed-Loop Realism Enforcement Demonstration")
    print("  (standalone; no database, no server, no network)")
    print(_hr())
    print(
        "\n  A deliberately-broken 3-device OT scenario is fed through the\n"
        "  REAL production readiness detector and the REAL auto-repair\n"
        "  functions. The same code runs at scenario create/save time.\n"
    )

    # --- BEFORE ---------------------------------------------------------
    print(_hr("-"))
    print("  BEFORE  —  readiness detection on the broken scenario")
    print(_hr("-"))
    before = compute_scenario_readiness(definition)
    _print_readiness(before, "BEFORE")

    # --- REPAIRS --------------------------------------------------------
    print()
    print(_hr("-"))
    print("  REPAIRS  —  applying closed-loop auto-repair functions in order")
    print(_hr("-"))

    d1 = auto_repair_protocols(definition)
    print(
        "  1. auto_repair_protocols()       — sync each device.protocols to its\n"
        "                                     fingerprint's supported_protocols"
    )

    d2 = narrow_protocols_by_vendor(d1)
    print(
        "  2. narrow_protocols_by_vendor()  — trim non-vendor-native protocols\n"
        "                                     (drops Siemens EtherNet/IP, etc.)"
    )

    d3 = repair_flow_protocols(d2)
    print(
        "  3. repair_flow_protocols()       — snap each flow.protocol to one\n"
        "                                     both endpoints actually support"
    )

    d4 = asyncio.run(ensure_device_flow_coverage(d3))
    print(
        "  4. ensure_device_flow_coverage() — synthesise a coverage flow for\n"
        "                                     every orphan device"
    )

    macs_fixed = _regenerate_macs(d4)
    print(
        "  5. canonical_mac() regeneration  — realign each MAC OUI to its\n"
        f"                                     declared vendor ({macs_fixed} MAC(s) rewritten)"
    )

    repaired = d4

    # --- AFTER ----------------------------------------------------------
    print()
    print(_hr("-"))
    print("  AFTER  —  readiness re-check on the repaired scenario")
    print(_hr("-"))
    after = compute_scenario_readiness(repaired)
    _print_readiness(after, "AFTER")

    # --- SUMMARY --------------------------------------------------------
    before_fail = sum(1 for c in before.checks if not c.passed)
    after_fail = sum(1 for c in after.checks if not c.passed)
    print(_hr())
    print(
        f"  RESULT: {before_fail} violation(s) BEFORE  ->  "
        f"{after_fail} violation(s) AFTER   "
        f"(score {before.score} -> {after.score})"
    )
    if after_fail < before_fail:
        print("  Closed-loop enforcement measurably improved scenario realism.")
    print(_hr())

    # Honest accounting of any residual violations the standalone repairs
    # cannot resolve (e.g. device naming, whose production repair path is the
    # LLM / site-identity renamer that needs a model or DB, not callable here).
    residual = [c.name for c in after.checks if not c.passed]
    if residual:
        print(
            "\n  NOTE: residual violation(s) not auto-repairable standalone: "
            + ", ".join(residual) + "."
        )
        print(
            "        'Device naming quality' is remediated in production by the\n"
            "        AI / site-identity renamer (needs an LLM or DB), which is\n"
            "        intentionally out of scope for this offline exhibit."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
