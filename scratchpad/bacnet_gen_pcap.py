"""Generate a real BACnet/IP PCAP via the product's UnifiedOrchestrator +
PcapOutput (the exact code path used for PCAP-mode generation), using real
building-automation device-template fingerprints. Writes /tmp/bacnet_demo.pcap.
"""
import random
random.seed(1337)

from app.protocol_engines.output import PcapOutput
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.services.device_templates import get_all_templates
from app.protocol_engines.vendor_oui import VENDOR_OUI_PREFIXES, generate_mac_address

# Pick a few distinct BACnet building-automation controllers
wanted = ["NAE55", "Tracer SC+", "ECLYPSE", "Desigo DXR2", "FEC26"]
templates = get_all_templates()
chosen = []
for w in wanted:
    for t in templates:
        if w.lower() in (t.model_name or "").lower() and t.bacnet_identity:
            chosen.append(t)
            break
print("Chosen controllers:")
for t in chosen:
    print(f"  {t.vendor:18} {t.model_name:34} vid={t.bacnet_identity.get('vendor_id')}")


def mac_for(t):
    ouis = t.oui_prefixes or VENDOR_OUI_PREFIXES.get((t.vendor or '').lower())
    try:
        return generate_mac_address(oui_prefixes=ouis)
    except Exception:
        return "02:%02x:%02x:%02x:%02x:%02x" % tuple(random.randint(0, 255) for _ in range(5))


def fp_for(t):
    return {
        "bacnet_identity": dict(t.bacnet_identity or {}),
        "response_timing": t.response_timing or {"mean_ms": 30, "std_dev_ms": 12, "min_ms": 6, "max_ms": 250},
        "tcp_stack": t.tcp_stack or {"ttl": 64},
        "vendor": t.vendor,
    }


# BMS supervisor (the polling manager)
mgr = DeviceContext(
    device_id="bms-supervisor",
    mac_address="00:50:56:ab:cd:01",
    ip_address="10.7.10.10",
    port=47808,
    vendor_fingerprint={"tcp_stack": {"ttl": 64}},
    vendor="Generic",
)

out = PcapOutput("/tmp/bacnet_demo.pcap")
orch = UnifiedOrchestrator(output=out, duration_ms=30000)

for i, t in enumerate(chosen):
    dev = DeviceContext(
        device_id=f"bacnet-ctrl-{i+1}",
        mac_address=mac_for(t),
        ip_address=f"10.7.10.{20+i}",
        port=47808,
        vendor_fingerprint=fp_for(t),
        scenario_id="bacnet-audit-demo",
        vendor=t.vendor,
    )
    flow = FlowContext(
        flow_id=f"bacnet-flow-{i+1}",
        source=mgr,
        destination=dev,
        protocol=ProtocolType.BACNET,
        config={"generate_who_is": True, "poll_interval_ms": 2000},
        timing_model={"poll_interval_ms": 2000, "response_delay_ms": 30},
    )
    orch.add_flow(flow)

result = orch.run()
out.close()
print(f"\nGenerated: packets={out.packet_count} bytes={out.file_size} duration={result.duration_ms:.0f}ms")
print("PCAP written to /tmp/bacnet_demo.pcap")
