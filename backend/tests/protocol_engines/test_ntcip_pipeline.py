# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""End to end: archetype → flow builder → orchestrator → decoded SNMP.

The 2026-10 audit found zero NTCIP varbinds on the wire for a generated ITS
corridor. This runs the same pipeline (tasks/audit-results/its-ntcip) and
asserts every signal controller, DMS and RWIS answers NTCIP objects with
values from its model.
"""
import collections

import pytest
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.layers.snmp import SNMP

from app.protocol_engines.output import PacketOutput
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.services.architecture.scenario_generator import generate_from_archetype
from app.services.scenario_enrichment import auto_repair_protocols, repair_flow_protocols
from app.traffic_generator.tasks import _build_flow_contexts

NTCIP = "1.3.6.1.4.1.1206.4.2."
GREENS = "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1"
REDS = "1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1"
KIND_OF = {"traffic_controller": "asc", "dms": "dms", "weather_station": "ess"}


class _Capture(PacketOutput):
    def __init__(self):
        self.packets: list[bytes] = []

    def write_packet(self, packet_bytes, timestamp_ms, is_attack=False, flow_id=None):
        self.packets.append(packet_bytes)

    def close(self):
        pass

    @property
    def packet_count(self):
        return len(self.packets)

    @property
    def bytes_sent(self):
        return sum(len(p) for p in self.packets)


@pytest.mark.parametrize("archetype", ["transportation_atms_corridor", "transportation_tunnel"])
def test_its_devices_answer_ntcip_on_the_wire(archetype):
    d = repair_flow_protocols(auto_repair_protocols(generate_from_archetype(archetype, scale="small")))
    devices = d["devices"] if isinstance(d["devices"], dict) else {x["id"]: x for x in d["devices"]}
    by_ip = {(dev.get("network") or {}).get("ipAddress"): dev for dev in devices.values()}

    out = _Capture()
    orch = UnifiedOrchestrator(out, duration_ms=90_000)
    for fc in _build_flow_contexts(d, scenario_id="00000000-0000-0000-0000-0000000000aa", vertical="transportation"):
        orch.add_flow(fc)
    orch.run()

    ntcip_by_device = collections.Counter()
    nonzero_by_device = collections.Counter()
    for raw in out.packets:
        pkt = Ether(raw)
        if SNMP not in pkt or UDP not in pkt or pkt[UDP].sport != 161:
            continue
        varbinds = {vb.oid.val: vb.value.val for vb in pkt[SNMP].PDU.varbindlist}
        dev_id = by_ip[pkt[IP].src]["id"]
        for oid, val in varbinds.items():
            if oid.startswith(NTCIP):
                ntcip_by_device[dev_id] += 1
                nonzero_by_device[dev_id] += bool(val)
        if GREENS in varbinds:
            assert not (varbinds[GREENS] & varbinds[REDS])

    ntcip_devices = [dev for dev in devices.values() if dev.get("type") in KIND_OF]
    assert ntcip_devices
    for dev in ntcip_devices:
        assert ntcip_by_device[dev["id"]] > 0, f"{dev['type']} {dev['id']} answered no NTCIP"
        assert nonzero_by_device[dev["id"]] > 0, f"{dev['type']} {dev['id']} NTCIP values all zero"
