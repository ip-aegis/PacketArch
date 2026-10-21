"""End-to-end: archetype generator -> enrichment -> _build_flow_contexts -> UnifiedOrchestrator -> PCAP -> decode SNMP OIDs."""
import sys, asyncio, collections, json
sys.path.insert(0, "/home/rocsmith/PacketArch/backend")
from app.services.architecture.scenario_generator import generate_from_archetype
from app.services.scenario_enrichment import auto_repair_protocols, repair_flow_protocols
from app.traffic_generator.tasks import _build_flow_contexts
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.protocol_engines.output import PcapOutput
from scapy.all import rdpcap, SNMP, UDP, IP

OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/its.pcap"
aid = sys.argv[1] if len(sys.argv) > 1 else "transportation_atms_corridor"
d = generate_from_archetype(aid, scale="small")
d = auto_repair_protocols(d); d = repair_flow_protocols(d)
devs = d["devices"]; devs = devs if isinstance(devs, dict) else {x["id"]: x for x in devs}
ip2role = {}
for x in devs.values():
    ip = (x.get("network") or {}).get("ipAddress") or x.get("ip_address")
    ip2role[ip] = x.get("architectural_role") or x.get("type")
fcs = _build_flow_contexts(d, scenario_id="00000000-0000-0000-0000-000000000001", vertical="transportation")
for f in fcs:
    if f.protocol.value == "snmp" and ip2role.get(f.destination.ip_address) == "traffic_controller": f.config["device_type"] = "asc"
snmp_fcs = [f for f in fcs if f.protocol.value == "snmp"]
print(f"{aid}: devices={len(devs)} flow_contexts={len(fcs)} snmp={len(snmp_fcs)}")
print("SNMP flow config keys seen:", sorted({k for f in snmp_fcs for k in (f.config or {})}))
print("device_type in any snmp flow config:", any("device_type" in (f.config or {}) or "poll_oids" in (f.config or {}) for f in snmp_fcs))
out = PcapOutput(OUT)
orch = UnifiedOrchestrator(out, duration_ms=30_000)
for f in fcs: orch.add_flow(f)
res = orch.run()
try: out.close()
except Exception: pass
print("orchestrator:", getattr(res, "packets_sent", res))
pkts = rdpcap(OUT)
by_role = collections.defaultdict(collections.Counter)
ntcip = collections.Counter()
for p in pkts:
    if SNMP in p and IP in p and p[UDP].sport == 161:
        role = ip2role.get(p[IP].src, p[IP].src)
        for vb in p[SNMP].PDU.varbindlist:
            oid = vb.oid.val
            by_role[role][oid] += 1
            if oid.startswith("1.3.6.1.4.1.1206.4"):
                ntcip[(oid, repr(vb.value.val))] += 1
print(f"total pkts={len(pkts)}")
for role, c in sorted(by_role.items()):
    print(f"  {role}: {dict(c)}")
print("NTCIP (1.3.6.1.4.1.1206.4.*) varbinds in responses:", sum(ntcip.values()), dict(list(ntcip.items())[:10]))
