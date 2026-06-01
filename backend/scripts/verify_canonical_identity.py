#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Verify the single canonical device identity invariants.

Standalone — NO database, NO server, NO PCAP. Runs the real creation-time
enrichment + the generation-time FingerprintApplicator + the ambient
DeviceContext over representative multi-protocol devices, and asserts the two
properties the platform owner asked us to verify:

  A. MAC — assigned at creation, vendor-OUI-appropriate, deterministic, and
     stable across re-resolution (regenerating yields the identical address).
  B. Single source of truth — every name-bearing protocol (LLDP / PROFINET /
     SNMP / S7) emits the SAME canonical hostname, the ambient path and the
     engine path agree, and CIP/PROFINET vendor IDs come from the SoT tables.

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/verify_canonical_identity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.protocol_engines import canonical_identity as ci
from app.protocol_engines.fingerprint_applicator import FingerprintApplicator
from app.protocol_engines.vendor_oui import (
    ODVA_VENDOR_IDS,
    PROFINET_VENDOR_IDS,
    VENDOR_OUI_PREFIXES,
)
from app.services.device_identity_enricher import (
    enrich_device_serial_numbers,
    enrich_device_unique_identifiers,
)

SCENARIO_ID = "verify-scenario-0001"

# Representative multi-protocol devices, one per affected vendor.
DEVICES = [
    {
        "id": "device_paint_plc",
        "name": "DTW_MFG_Paint_Booth_Main_PLC_01",
        "vendor": "siemens",
        "protocols": ["profinet", "s7comm", "modbus_tcp", "snmp"],
        "network": {"ipAddress": "10.1.4.10"},
        "vendorFingerprint": {
            "vendor": "siemens",
            "model": "6ES7 517-3AP00-0AB0",
            "oui_prefixes": ["00:0E:8C", "00:1B:1B", "00:1C:06"],
            "snmp_identity": {"sys_descr": "Siemens", "sys_object_id": "1.3.6.1.4.1.4329"},
            "profinet_identity": {"vendor_id": 285, "order_id": "x"},
            "s7_identity": {"order_code": "6ES7 517-3AP00-0AB0"},
            "modbus_identity": {"vendor_name": "Siemens AG"},
        },
    },
    {
        "id": "device_stamp_plc",
        "name": "DTW_MFG_Stamping_Cell_Main_PLC_01",
        "vendor": "schneider",
        "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
        "network": {"ipAddress": "10.1.2.10"},
        "vendorFingerprint": {
            "vendor": "schneider",
            "model": "BMEP586040",
            "oui_prefixes": ["00:00:54", "00:80:F4"],
            "snmp_identity": {"sys_descr": "Schneider", "sys_object_id": "1.3.6.1.4.1.3833"},
            "ethernet_ip_identity": {"vendor_id": 67, "product_code": 1},  # stale 67!
            "modbus_identity": {"vendor_name": "Schneider Electric"},
        },
    },
    {
        "id": "device_assy_plc",
        "name": "DTW_MFG_Final_Assembly_Main_PLC_01",
        "vendor": "rockwell",
        "protocols": ["ethernet_ip", "snmp"],
        "network": {"ipAddress": "10.1.5.10"},
        "vendorFingerprint": {
            "vendor": "rockwell",
            "model": "1756-L85E/B LOGIX5580",
            "oui_prefixes": ["00:00:BC", "00:1D:9C"],
            "snmp_identity": {"sys_descr": "Rockwell", "sys_object_id": "1.3.6.1.4.1.1418"},
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "product_code": 1,
                "product_name": "1756-L85E/B LOGIX5580",
            },
        },
    },
]

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((PASS if ok else FAIL, name, detail))


def hostname_bearing_fields(fa: FingerprintApplicator) -> dict[str, str]:
    """Pull every name-bearing field a protocol advertises on the wire."""
    out = {}
    if fa.snmp_identity:
        out["snmp.sys_name"] = fa.snmp_identity.get("sys_name", "")
    if fa.profinet_identity:
        out["profinet.station_name"] = fa.profinet_identity.get("station_name", "")
    if fa.s7_identity:
        out["s7.plc_name"] = fa.s7_identity.get("plc_name", "")
    return out


def verify_device(dev: dict) -> None:
    did = dev["id"]
    name = dev["name"]
    vendor = dev["vendor"]
    expected_host = ci.canonical_hostname(name)

    # --- creation-time enrichment (what gets persisted) ---
    enrich_device_serial_numbers(dev, did, SCENARIO_ID)
    enrich_device_unique_identifiers(dev, did, SCENARIO_ID)
    fp = dev["vendorFingerprint"]

    # A. MAC checks ----------------------------------------------------
    mac = dev["network"].get("macAddress", "")
    check(f"[{did}] MAC assigned at creation", bool(mac), mac)

    oui = mac[:8].upper()
    expected_ouis = [p.upper() for p in (fp.get("oui_prefixes") or VENDOR_OUI_PREFIXES.get(vendor, []))]
    check(f"[{did}] MAC OUI matches vendor", oui in expected_ouis, f"{oui} in {expected_ouis}")

    mac_again = ci.canonical_mac(did, SCENARIO_ID, vendor=vendor, oui_prefixes=fp.get("oui_prefixes"))
    check(f"[{did}] MAC deterministic / stable across re-resolution", mac == mac_again, f"{mac} vs {mac_again}")

    # B. generation-time resolution (what the engines emit) ------------
    fa = FingerprintApplicator(fp, device_id=did, scenario_id=SCENARIO_ID, device_name=name)
    fields = hostname_bearing_fields(fa)

    # SNMP/PROFINET emit the exact canonical hostname; S7 is clamped to its
    # 24-char field so it must be a prefix of the canonical stem.
    for key, value in fields.items():
        if key == "s7.plc_name":
            ok = expected_host.startswith(value) and bool(value)
        else:
            ok = value == expected_host
        check(f"[{did}] {key} == canonical hostname", ok, f"{value!r} vs {expected_host!r}")

    # creation-time persisted values must equal generation-time values
    if fp.get("snmp_identity"):
        check(
            f"[{did}] persisted sys_name == resolved sys_name",
            fp["snmp_identity"].get("sys_name") == fa.snmp_identity.get("sys_name"),
            f"{fp['snmp_identity'].get('sys_name')!r}",
        )

    # vendor_id from SoT
    if fa.ethernet_ip_identity:
        expected = ODVA_VENDOR_IDS.get(vendor)
        check(
            f"[{did}] CIP vendor_id from SoT",
            fa.ethernet_ip_identity.get("vendor_id") == expected,
            f"{fa.ethernet_ip_identity.get('vendor_id')} expect {expected}",
        )
    if fa.profinet_identity:
        expected = PROFINET_VENDOR_IDS.get(vendor)
        check(
            f"[{did}] PROFINET vendor_id from SoT",
            fa.profinet_identity.get("vendor_id") == expected,
            f"{fa.profinet_identity.get('vendor_id')} expect {expected}",
        )

    # CIP/Modbus product_name must be the canonical hostname (CV labels the
    # EtherNet/IP & Modbus components by it, so it must match LLDP/SNMP for CV
    # to merge components). The catalog model stays in Modbus model_name.
    if fa.ethernet_ip_identity:
        pn = fa.ethernet_ip_identity.get("product_name", "")
        check(f"[{did}] CIP product_name == canonical hostname", pn == expected_host, f"{pn!r}")
    if fa.modbus_identity:
        pn = fa.modbus_identity.get("product_name", "")
        check(f"[{did}] Modbus product_name == canonical hostname", pn == expected_host, f"{pn!r}")
        mn = fa.modbus_identity.get("model_name", "")
        check(f"[{did}] Modbus model_name preserves catalog model", mn == dev["vendorFingerprint"]["model"], f"{mn!r}")

    # B. ambient-vs-engine parity --------------------------------------
    # The ambient path advertises LLDP/SNMP names via canonical_hostname(name);
    # assert it equals what the engine path resolves.
    ambient_lldp = ci.canonical_hostname(name)
    check(f"[{did}] ambient LLDP/SNMP name == engine canonical hostname",
          ambient_lldp == expected_host and ambient_lldp == fields.get("snmp.sys_name", expected_host),
          f"{ambient_lldp!r}")


def main() -> int:
    for dev in DEVICES:
        verify_device(dev)

    width = max(len(n) for _, n, _ in _results)
    print("\nCanonical Identity Verification\n" + "=" * (width + 12))
    for status, name, detail in _results:
        line = f"  {status}  {name.ljust(width)}"
        if status == FAIL and detail:
            line += f"   <- {detail}"
        print(line)

    failed = [r for r in _results if r[0] == FAIL]
    total = len(_results)
    print("=" * (width + 12))
    print(f"  {total - len(failed)}/{total} checks passed"
          + (f", {len(failed)} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
