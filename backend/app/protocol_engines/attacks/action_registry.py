"""Attack action registry — maps action_type keys to packet generators.

Each registered generator has the signature::

    def generate(
        params: dict[str, Any],
        targets: list[TargetInfo],
        attacker_ip: str,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]

The registry uses the same ``@register`` decorator pattern as the
protocol engine registry in ``protocol_engines/__init__.py``.

Core generators that delegate to :class:`ExternalCommEngine`:
  - ``port_scan``, ``c2_beacon``, ``dns_tunnel``, ``http_exfil``,
    ``exploit_attempt``

ICS-specific generators are registered in ``ics_actions.py`` (auto-imported
by the package ``__init__``).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from scapy.layers.l2 import Ether
from scapy.packet import Packet as ScapyPacket

from app.protocol_engines.types import PacketEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Target info passed to every generator
# ---------------------------------------------------------------------------

@dataclass
class TargetInfo:
    """Resolved target device information for attack generators."""

    device_id: str
    ip_address: str
    mac_address: str
    device_type: str  # "plc", "hmi", "rtu", "ews", etc.
    protocols: list[str]
    port: int = 0  # protocol-specific port if available


# ---------------------------------------------------------------------------
# Generator type alias and registry
# ---------------------------------------------------------------------------

ActionGenerator = Callable[
    [dict[str, Any], list[TargetInfo], str, float],
    Iterator[PacketEvent],
]

_ACTION_REGISTRY: dict[str, ActionGenerator] = {}


def register_action(action_type: str) -> Callable[[ActionGenerator], ActionGenerator]:
    """Decorator to register an attack action generator."""

    def decorator(fn: ActionGenerator) -> ActionGenerator:
        if action_type in _ACTION_REGISTRY:
            logger.warning(f"Overwriting action generator for '{action_type}'")
        _ACTION_REGISTRY[action_type] = fn
        return fn

    return decorator


def get_action_generator(action_type: str) -> ActionGenerator | None:
    """Look up a generator by action_type key."""
    return _ACTION_REGISTRY.get(action_type)


def list_action_types() -> list[str]:
    """Return all registered action type keys."""
    return sorted(_ACTION_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Synthetic flow ID prefix for attack packets
ATTACK_FLOW_PREFIX = "__attack__"


def _scapy_to_packet_event(
    timestamp_ms: float,
    pkt: ScapyPacket,
    action_type: str,
    metadata: dict[str, Any] | None = None,
) -> PacketEvent:
    """Convert a Scapy packet to the orchestrator's PacketEvent."""
    # Ensure Ethernet layer exists
    if not pkt.haslayer(Ether):
        pkt = Ether() / pkt
    return PacketEvent(
        timestamp_ms=timestamp_ms,
        flow_id=f"{ATTACK_FLOW_PREFIX}{action_type}",
        packet_bytes=bytes(pkt),
        direction="request",
        metadata={"attack_action": action_type, **(metadata or {})},
    )


def _pick_targets(
    targets: list[TargetInfo],
    count: int = 1,
) -> list[TargetInfo]:
    """Pick ``count`` random targets (or all if fewer available)."""
    if len(targets) <= count:
        return list(targets)
    return random.sample(targets, count)


# ---------------------------------------------------------------------------
# Core generators — delegate to ExternalCommEngine / exploit_patterns
# ---------------------------------------------------------------------------


@register_action("port_scan")
def _generate_port_scan(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """SYN scan of common OT ports on target devices."""
    from app.protocol_engines.external.exploit_patterns import (
        generate_ot_port_scan,
        generate_port_scan_sequence,
    )

    scan_ot = params.get("scan_ot_ports", True)
    scan_type = params.get("scan_type", "syn")
    custom_ports = params.get("ports")

    for target in targets:
        if scan_ot and not custom_ports:
            gen = generate_ot_port_scan(
                src_ip=attacker_ip,
                dst_ip=target.ip_address,
                start_time_ms=int(start_time_ms),
            )
        else:
            ports = custom_ports or [21, 22, 23, 80, 102, 443, 502, 44818, 47808]
            gen = generate_port_scan_sequence(
                src_ip=attacker_ip,
                dst_ip=target.ip_address,
                ports=ports,
                scan_type=scan_type,
                start_time_ms=int(start_time_ms),
            )

        for ts, pkt in gen:
            yield _scapy_to_packet_event(ts, pkt, "port_scan", {
                "target_ip": target.ip_address,
                "mitre_technique": "T0846",
            })


@register_action("c2_beacon")
def _generate_c2_beacon(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """C2 beaconing from a compromised device."""
    from app.protocol_engines.external.engine import (
        ExternalCommEngine,
        ExternalTrafficConfig,
    )

    # Pick one "compromised" device
    compromised = _pick_targets(targets, 1)
    if not compromised:
        return

    device_ip = compromised[0].ip_address
    pattern = params.get("pattern", "jittered_1m")
    protocol = params.get("protocol", "http")
    count = params.get("count", 10)
    duration_ms = params.get("duration_ms", 300_000)

    config = ExternalTrafficConfig(
        c2_pattern=pattern,
        c2_protocol=protocol,
        c2_count=count,
    )
    engine = ExternalCommEngine(config)

    for evt in engine.generate_c2_beaconing(
        internal_device_ip=device_ip,
        start_time_ms=int(start_time_ms),
        duration_ms=duration_ms,
        pattern_name=pattern,
    ):
        yield _scapy_to_packet_event(evt.timestamp_ms, evt.packet, "c2_beacon", {
            "compromised_ip": device_ip,
            "pattern": pattern,
            "mitre_technique": "T0885",
        })


@register_action("dns_tunnel")
def _generate_dns_tunnel(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """DNS tunneling data exfiltration."""
    from app.protocol_engines.external.engine import (
        ExternalCommEngine,
        ExternalTrafficConfig,
    )

    compromised = _pick_targets(targets, 1)
    if not compromised:
        return

    device_ip = compromised[0].ip_address
    data_size = params.get("data_size", 4096)
    fake_data = bytes(random.getrandbits(8) for _ in range(data_size))

    engine = ExternalCommEngine(ExternalTrafficConfig())

    for evt in engine.generate_dns_tunnel(
        internal_device_ip=device_ip,
        data=fake_data,
        start_time_ms=int(start_time_ms),
    ):
        yield _scapy_to_packet_event(evt.timestamp_ms, evt.packet, "dns_tunnel", {
            "compromised_ip": device_ip,
            "data_size": data_size,
            "mitre_technique": "T0884",
        })


@register_action("http_exfil")
def _generate_http_exfil(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """HTTP data exfiltration."""
    from app.protocol_engines.external.engine import (
        ExternalCommEngine,
        ExternalTrafficConfig,
    )

    compromised = _pick_targets(targets, 1)
    if not compromised:
        return

    device_ip = compromised[0].ip_address
    data_size = params.get("data_size", 4096)
    fake_data = bytes(random.getrandbits(8) for _ in range(data_size))

    engine = ExternalCommEngine(ExternalTrafficConfig())

    for evt in engine.generate_http_exfil(
        internal_device_ip=device_ip,
        data=fake_data,
        start_time_ms=int(start_time_ms),
    ):
        yield _scapy_to_packet_event(evt.timestamp_ms, evt.packet, "http_exfil", {
            "compromised_ip": device_ip,
            "data_size": data_size,
            "mitre_technique": "T0882",
        })


@register_action("exploit_attempt")
def _generate_exploit_attempt(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Exploit attempt using a named exploit pattern."""
    from app.protocol_engines.external.engine import (
        ExternalCommEngine,
        ExternalTrafficConfig,
    )

    pattern_name = params.get("exploit_pattern", "buffer_overflow_generic")
    repeat = params.get("repeat_count", 3)

    config = ExternalTrafficConfig(
        enable_exploits=True,
        exploit_patterns=[pattern_name],
    )
    engine = ExternalCommEngine(config)

    for target in targets:
        for evt in engine.generate_exploit_attempt(
            target_device_ip=target.ip_address,
            exploit_name=pattern_name,
            start_time_ms=int(start_time_ms),
        ):
            yield _scapy_to_packet_event(evt.timestamp_ms, evt.packet, "exploit_attempt", {
                "target_ip": target.ip_address,
                "exploit": pattern_name,
                "mitre_technique": evt.metadata.get("mitre_technique", "T0869"),
            })
