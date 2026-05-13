#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Generate a small, PROFINET-only PCAP for Cyber Vision testing.

Produces a focused multi-talker PROFINET capture: one IO-Controller
(S7-1500) plus a handful of IO-Devices (drives + I/O modules), with all
non-PROFINET ambient noise disabled. RT cycle is set to a realistic
8ms (vs the 1000ms default driven by `poll_interval_ms`).

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/generate_profinet_only_pcap.py [--duration-ms 30000] [--out PATH]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from app.protocol_engines.ambient.noise_generator import (
    AmbientConfig,
    AmbientDevice,
    BackgroundNoiseGenerator,
)
from app.protocol_engines.output import PcapOutput
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.services.device_templates import get_fingerprint_by_vendor_model


SCENARIO_ID = "profinet-cv-test"
RT_CYCLE_MS = 8  # Realistic PROFINET RT cycle


def _device(
    device_id: str,
    name: str,
    mac: str,
    ip: str,
    vendor: str,
    model: str,
    device_type: str,
) -> tuple[DeviceContext, dict]:
    fp = get_fingerprint_by_vendor_model(vendor, model) or {}
    if not fp:
        print(f"  [WARN] no fingerprint for {vendor}/{model}", file=sys.stderr)
    ctx = DeviceContext(
        device_id=device_id,
        mac_address=mac,
        ip_address=ip,
        port=0,
        vendor_fingerprint=fp,
        scenario_id=SCENARIO_ID,
        device_name=name,
    )
    meta = {
        "vendor": vendor,
        "model": model,
        "device_type": device_type,
        "fingerprint": fp,
    }
    return ctx, meta


def build_topology() -> tuple[list[tuple[DeviceContext, dict]], list[FlowContext]]:
    # 1 controller + 5 IO devices, all PROFINET, all in one zone.
    # MACs use Siemens OUI (00:1B:1B / 00:0E:8C); the ambient generator
    # will validate against the fingerprint OUI list and override if
    # needed, so these are just plausible defaults.
    controller, c_meta = _device(
        "ctrl-01", "CNC_Cell_Main_PLC",
        "00:1B:1B:11:22:01", "10.99.0.10",
        "Siemens", "6ES7 516-3AN02-0AB0",
        "plc",
    )
    devices: list[tuple[DeviceContext, dict]] = [(controller, c_meta)]

    targets = [
        ("io-01", "X_Axis_Servo_Drive",  "00:1B:1B:11:22:11", "10.99.0.21",
         "Siemens", "6SL3210-1PE21-1UL0", "drive"),
        ("io-02", "Y_Axis_Servo_Drive",  "00:1B:1B:11:22:12", "10.99.0.22",
         "Siemens", "6SL3210-1PE21-1UL0", "drive"),
        ("io-03", "Spindle_Motor_VFD",   "00:1B:1B:11:22:13", "10.99.0.23",
         "Siemens", "G120", "drive"),
        ("io-04", "Cell_IO_Module",      "00:1B:1B:11:22:14", "10.99.0.24",
         "Siemens", "6ES7155-6AU01-0BN0", "io_module"),
        ("io-05", "Safety_IO_Module",    "00:1B:1B:11:22:15", "10.99.0.25",
         "Siemens", "6ES7155-6AU01-0BN0", "io_module"),
    ]
    for did, name, mac, ip, vendor, model, dtype in targets:
        devices.append(_device(did, name, mac, ip, vendor, model, dtype))

    # One PROFINET flow controller -> each IO device.
    flows: list[FlowContext] = []
    for i, (target_ctx, _) in enumerate(devices[1:], start=1):
        flows.append(FlowContext(
            flow_id=f"pn_flow_{i:02d}",
            source=controller,
            destination=target_ctx,
            protocol=ProtocolType.PROFINET,
            config={
                "jitter_ms": 0,
            },
            # NOTE: orchestrator reads poll_interval_ms from timing_model
            # (unified_orchestrator.py:112), not config. The scenario
            # template path puts it in config — that's a separate bug
            # noted in REVIEW_PROFINET_REALISM.md (F-2 / S-3).
            timing_model={"poll_interval_ms": RT_CYCLE_MS},
        ))

    return devices, flows


def build_ambient_devices(devices: list[tuple[DeviceContext, dict]]) -> list[AmbientDevice]:
    out: list[AmbientDevice] = []
    for ctx, meta in devices:
        out.append(AmbientDevice(
            device_id=ctx.device_id,
            mac_address=ctx.mac_address,
            ip_address=ctx.ip_address,
            protocols=["profinet"],
            device_type=meta["device_type"],
            vendor=meta["vendor"],
            device_name=ctx.device_name or ctx.device_id,
            zone_id="cell",
            vendor_fingerprint=meta["fingerprint"],
        ))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-ms", type=int, default=30000,
                        help="Capture duration (default 30000 = 30s)")
    parser.add_argument("--out", type=Path,
                        default=Path.home() / "profinet-cv-test" / "profinet-only.pcap",
                        help="Output PCAP path")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    devices, flows = build_topology()
    print(f"Topology: {len(devices)} devices, {len(flows)} PROFINET flows, "
          f"RT cycle {RT_CYCLE_MS}ms, duration {args.duration_ms/1000:.0f}s")

    # Ambient: PROFINET DCP only. Everything else off so the PCAP stays
    # focused on PROFINET frames.
    ambient_cfg = AmbientConfig(
        enabled=True,
        lldp_enabled=False,
        stp_enabled=False,
        dhcp_enabled=False,
        bacnet_whois_enabled=False,
        snmp_trap_enabled=False,
        snmp_discovery_enabled=False,
        modbus_discovery_enabled=False,
        enip_discovery_enabled=False,
        s7_discovery_enabled=False,
        igmp_enabled=False,
        cdp_enabled=False,
        # Skip gratuitous ARP and NTP too — pure PROFINET wire output.
        arp_gratuitous_interval_s=10_000_000.0,
        ntp_server_ip=None,
        # PROFINET DCP only
        profinet_dcp_enabled=True,
    )
    noise = BackgroundNoiseGenerator(
        build_ambient_devices(devices),
        config=ambient_cfg,
    )
    # Suppress the gratuitous ARP boot phase by clearing the device list
    # for ARP — but easier: AmbientConfig doesn't have an ARP enabled
    # flag, so we accept a few ARP packets. They're tiny and CV is fine
    # with them.

    output = PcapOutput(str(args.out))
    orch = UnifiedOrchestrator(output=output, duration_ms=args.duration_ms)
    for flow in flows:
        orch.add_flow(flow)
    orch.register_ambient_generator(noise)

    t0 = time.monotonic()
    result = orch.run()
    output.close()
    gen_ms = (time.monotonic() - t0) * 1000

    size_kb = args.out.stat().st_size / 1024
    print(f"Generated {result.packets_generated} packets "
          f"({size_kb:.1f} KB) in {gen_ms:.0f}ms")
    print(f"Output: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
