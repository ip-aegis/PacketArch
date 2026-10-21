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


def _definition_from_hand_template(name: str) -> dict:
    """Mirror api/routes/templates.py create-from-template for a curated
    template with explicit devices/flows: expand device specs by count,
    resolve fingerprints by vendor+model, round-robin flows by
    (type, zone) with ``timing.intervalMs``. IPs/MACs are synthetic."""
    from app.scenario_templates.transportation import TRANSPORTATION_TEMPLATES
    from app.services.device_templates import get_fingerprint_by_vendor_model

    template = TRANSPORTATION_TEMPLATES[name]
    devices = {}
    for spec in template["devices"]:
        for _ in range(spec.get("count", 1)):
            n = len(devices) + 1
            dev_id = f"device_{n:03d}"
            devices[dev_id] = {
                "id": dev_id,
                "name": spec.get("name") or f"{spec['type']}-{n:03d}",
                "type": spec["type"],
                "zoneId": spec.get("zone"),
                "group": spec.get("group"),
                "vendorFingerprint": get_fingerprint_by_vendor_model(spec.get("vendor"), spec.get("fingerprint_model")) or {},
                "network": {"ipAddress": f"10.77.{n // 250}.{n % 250 + 2}", "macAddress": f"02:00:00:00:{n // 256:02x}:{n % 256:02x}"},
            }
    from app.services.template_flows import expand_template_flows

    flows = expand_template_flows(
        template["flows"], devices, honor_config=bool(template.get("honor_flow_config"))
    )
    return {"devices": devices, "flows": flows, "zones": {}, "conduits": {}}


def _roadway_templates():
    from app.scenario_templates.transportation import TRANSPORTATION_TEMPLATES

    kinds = {"traffic_controller", "dms_sign", "dms", "weather_station"}
    return sorted(k for k, t in TRANSPORTATION_TEMPLATES.items()
                  if any(d.get("type") in kinds for d in t.get("devices", [])))


@pytest.mark.parametrize("template", _roadway_templates())
def test_hand_authored_templates_answer_ntcip(template):
    d = repair_flow_protocols(auto_repair_protocols(_definition_from_hand_template(template)))
    by_ip = {dev["network"]["ipAddress"]: dev for dev in d["devices"].values()}
    out = _Capture()
    orch = UnifiedOrchestrator(out, duration_ms=60_000)
    for fc in _build_flow_contexts(d, scenario_id="00000000-0000-0000-0000-0000000000bb", vertical="transportation"):
        orch.add_flow(fc)
    orch.run()
    answered = collections.Counter()
    for raw in out.packets:
        pkt = Ether(raw)
        if SNMP in pkt and UDP in pkt and pkt[UDP].sport == 161:
            for vb in pkt[SNMP].PDU.varbindlist:
                if vb.oid.val.startswith(NTCIP) and vb.value.val:
                    answered[by_ip[pkt[IP].src]["type"]] += 1
    expected = {t for t in ("traffic_controller", "dms_sign", "dms", "weather_station")
                if any(dev["type"] == t for dev in d["devices"].values())}
    assert expected and expected <= set(answered), (expected, dict(answered))
