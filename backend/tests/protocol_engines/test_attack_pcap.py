# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Attack traffic in the PCAP (timed / virtual-clock) generation path.

Regression coverage for two bugs that made baked-attack PCAPs degenerate:

1. Stage timing used wall-clock ``time.monotonic()``. PCAP generation drains
   the event heap in a fraction of a second of wall time, so stages never
   advanced and only stage 0's first action rendered. Timed mode now advances
   the kill chain on the VIRTUAL clock and time-compresses it to fit the window.
2. ``_resolve_targets`` only understood the frontend device shape
   (``id``/``network.ipAddress``), so the flat shape the PCAP path builds
   yielded zero targets → zero attack packets.
"""

from __future__ import annotations

from app.protocol_engines.attacks import AttackOrchestrator, get_playbook
from app.protocol_engines.attacks.types import AttackPlaybookConfig
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator


class _CountingOutput:
    """Minimal PacketOutput that counts attack vs non-attack packets."""

    def __init__(self) -> None:
        self.packet_count = 0
        self.bytes_sent = 0
        self.attack_packets = 0

    def write_packet(self, packet_bytes: bytes, timestamp_ms: float,
                     is_attack: bool = False, flow_id: str | None = None) -> None:
        self.packet_count += 1
        self.bytes_sent += len(packet_bytes)
        if is_attack:
            self.attack_packets += 1

    def close(self) -> None:  # noqa: D401
        pass


# Flat device shape, exactly as traffic_generator/orchestrator.py builds it.
_DEVICES = [
    {"device_id": "plc_01", "ip_address": "10.7.0.10",
     "mac_address": "00:11:22:00:00:01", "device_type": "plc",
     "protocols": ["modbus_tcp", "s7comm"]},
    {"device_id": "hmi_01", "ip_address": "10.7.0.20",
     "mac_address": "00:11:22:00:00:02", "device_type": "hmi",
     "protocols": ["modbus_tcp"]},
    {"device_id": "eng_ws_01", "ip_address": "10.7.0.30",
     "mac_address": "00:11:22:00:00:03", "device_type": "workstation",
     "protocols": ["s7comm"]},
]


def _run(playbook_id: str, duration_ms: int) -> tuple[dict, _CountingOutput]:
    playbook = get_playbook(playbook_id)
    assert playbook is not None, f"unknown playbook {playbook_id}"
    output = _CountingOutput()
    orch = UnifiedOrchestrator(output=output, duration_ms=duration_ms)
    atk = AttackOrchestrator(
        playbook=playbook,
        devices=_DEVICES,
        config=AttackPlaybookConfig(
            playbook_id=playbook_id,
            start_mode="with_deployment",
            auto_advance=True,
        ),
    )
    orch.register_attack_orchestrator(atk, warmup_ms=1000.0)
    orch.run()
    return atk.get_report(), output


def test_full_killchain_renders_in_pcap():
    """Every stage completes and multiple distinct actions fire + emit packets."""
    report, output = _run("network_recon", duration_ms=120_000)

    assert report["total_stages"] >= 3
    assert report["stages_completed"] == report["total_stages"], (
        "not all kill-chain stages advanced in virtual/PCAP mode"
    )
    assert report["total_packets"] > 0, "no attack packets rendered"
    assert output.attack_packets > 0, "attack packets not tagged is_attack at output"
    # More than just stage 0's first action must have fired.
    assert report["total_actions"] >= 3


def test_time_compression_fits_long_playbook_into_short_pcap():
    """A 6-stage / ~1800s playbook still renders every stage in a 90s PCAP."""
    report, output = _run("triton_like", duration_ms=90_000)

    assert report["total_stages"] == 6
    assert report["stages_completed"] == 6, (
        "long kill chain was not time-compressed to fit the capture window"
    )
    assert report["total_packets"] > 0
    assert output.attack_packets > 0
