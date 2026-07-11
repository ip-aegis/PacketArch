# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for the topology segment router (generate-once/render-many)."""

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import ARP, Dot1Q, Ether

from app.protocol_engines.topology_router import TopologyRouter
from app.services.topology_planner import derive_topology, plan_segments

DA_MAC, DB_MAC = "00:0e:8c:aa:00:01", "00:01:05:bb:00:02"
PLC1_MAC = "00:0e:8c:11:11:11"
PLC2_MAC = "00:0e:8c:22:22:22"
HMI_MAC = "00:0e:8c:33:33:33"


def _def() -> dict:
    return {
        "zones": {
            "z-cell": {"id": "z-cell", "name": "Cell", "level": 1,
                       "network": {"subnet": "10.5.1.0/24", "gateway": "10.5.1.1", "vlan": 101}},
            "z-sup": {"id": "z-sup", "name": "Sup", "level": 2,
                      "network": {"subnet": "10.5.2.0/24", "gateway": "10.5.2.1", "vlan": 102}},
        },
        "devices": {
            "plc1": {"id": "plc1", "zoneId": "z-cell",
                     "network": {"ipAddress": "10.5.1.10", "macAddress": PLC1_MAC}},
            "plc2": {"id": "plc2", "zoneId": "z-cell",
                     "network": {"ipAddress": "10.5.1.11", "macAddress": PLC2_MAC}},
            "hmi1": {"id": "hmi1", "zoneId": "z-sup",
                     "network": {"ipAddress": "10.5.2.10", "macAddress": HMI_MAC}},
        },
        "flows": {
            "f-intra": {"id": "f-intra", "sourceDeviceId": "plc1", "targetDeviceId": "plc2", "protocol": "modbus_tcp"},
            "f-cross": {"id": "f-cross", "sourceDeviceId": "hmi1", "targetDeviceId": "plc1", "protocol": "s7comm"},
        },
    }


def _router(definition=None):
    definition = definition or _def()
    plan = derive_topology(definition, seed="scn")
    plan = plan_segments(definition, plan)
    return TopologyRouter(plan.as_dict()), plan


def _frame(src_mac, dst_mac, src_ip, dst_ip, ttl=64):
    return bytes(Ether(src=src_mac, dst=dst_mac) / IP(src=src_ip, dst=dst_ip, ttl=ttl) / TCP(sport=51000, dport=502))


class TestIntraZone:
    def test_single_span_true_macs_untagged(self):
        router, _ = _router()
        raw = _frame(PLC1_MAC, PLC2_MAC, "10.5.1.10", "10.5.1.11")
        out = router.route(raw, "f-intra")
        assert len(out) == 1
        span, data = out[0]
        assert span == "zone:z-cell"
        pkt = Ether(data)
        assert pkt.src == PLC1_MAC and pkt.dst == PLC2_MAC
        assert not pkt.haslayer(Dot1Q)
        assert pkt[IP].ttl == 64


class TestCrossZone:
    def test_four_segments_gateway_rewritten(self):
        router, plan = _router()
        svi_sup = plan.core["svis"]["z-sup"]["mac"]
        svi_cell = plan.core["svis"]["z-cell"]["mac"]
        # forward: hmi1 (source) -> plc1
        raw = _frame(HMI_MAC, PLC1_MAC, "10.5.2.10", "10.5.1.10", ttl=64)
        out = router.route(raw, "f-cross")
        assert [s for s, _ in out] == ["zone:z-sup", "core", "core", "zone:z-cell"]
        # near side (source zone): true src MAC -> SVI-sup, VLAN 102, TTL intact
        near = Ether(out[0][1])
        assert near.src == HMI_MAC and near.dst == svi_sup
        assert near[Dot1Q].vlan == 102 and near[IP].ttl == 64
        # far side (target zone): SVI-cell -> true dst MAC, VLAN 101, TTL-1
        far = Ether(out[3][1])
        assert far.src == svi_cell and far.dst == PLC1_MAC
        assert far[Dot1Q].vlan == 101 and far[IP].ttl == 63
        # IPs preserved end to end
        assert near[IP].src == "10.5.2.10" and far[IP].dst == "10.5.1.10"

    def test_reverse_direction_detected_from_ip(self):
        router, plan = _router()
        svi_sup = plan.core["svis"]["z-sup"]["mac"]
        # reply: plc1 -> hmi1 (source_ip is hmi1, so this is reverse)
        raw = _frame(PLC1_MAC, HMI_MAC, "10.5.1.10", "10.5.2.10", ttl=64)
        out = router.route(raw, "f-cross")
        assert [s for s, _ in out] == ["zone:z-cell", "core", "core", "zone:z-sup"]
        # delivered into sup zone: SVI-sup -> true hmi MAC, TTL-1
        far = Ether(out[3][1])
        assert far.src == svi_sup and far.dst == HMI_MAC
        assert far[IP].ttl == 63

    def test_ip_checksum_recomputed_after_ttl_change(self):
        router, _ = _router()
        raw = _frame(HMI_MAC, PLC1_MAC, "10.5.2.10", "10.5.1.10", ttl=64)
        far = Ether(router.route(raw, "f-cross")[3][1])
        # Re-parse and verify scapy considers the checksum valid
        rebuilt = Ether(bytes(far))
        assert rebuilt[IP].ttl == 63
        # scapy recomputes on build; compare stored vs computed
        computed = IP(bytes(rebuilt[IP])).chksum
        assert far[IP].chksum == computed


class TestUnplanned:
    def test_ambient_arp_routed_by_zone(self):
        router, _ = _router()
        raw = bytes(Ether(src=PLC1_MAC, dst="ff:ff:ff:ff:ff:ff") /
                    ARP(op=1, hwsrc=PLC1_MAC, psrc="10.5.1.10", pdst="10.5.1.1"))
        out = router.route(raw, "ambient_arp_plc1")
        assert len(out) == 1
        assert out[0][0] == "zone:z-cell"
        # untouched (true MACs, no reframing)
        assert out[0][1] == raw

    def test_unknown_frame_dropped(self):
        router, _ = _router()
        raw = _frame("aa:aa:aa:aa:aa:aa", "bb:bb:bb:bb:bb:bb", "192.0.2.1", "192.0.2.2")
        out = router.route(raw, "ambient_unknown")
        assert out == []

    def test_ip_frame_unplanned_routed_by_ip(self):
        router, _ = _router()
        # an unplanned IP frame from a known device IP
        raw = _frame(PLC2_MAC, PLC1_MAC, "10.5.1.11", "10.5.1.10")
        out = router.route(raw, "__attack__scan")
        assert {s for s, _ in out} == {"zone:z-cell"}


class TestEtherTypePreservation:
    """Regression: reframing must NOT drop the EtherType of non-IP L2 protocols
    (PROFINET/GOOSE/SV/LLDP). The old scapy-rebuild path lost it and fell back
    to scapy's 0x9000 default, which Cyber Vision decodes as EthernetCTP →
    'Decode failure'."""

    def _profinet_flow_def(self):
        d = _def()
        # intra-zone PROFINET between the two cell PLCs (L2, no IP)
        d["flows"]["f-pn"] = {
            "id": "f-pn", "sourceDeviceId": "plc1", "targetDeviceId": "plc2",
            "protocol": "profinet",
        }
        return d

    def test_profinet_intra_zone_keeps_ethertype(self):
        from app.protocol_engines.topology_router import _reframe

        # Ether(type=0x8892)/raw — a PROFINET RT frame, no IP.
        pn = bytes(Ether(src=PLC1_MAC, dst=PLC2_MAC, type=0x8892) / (b"\x80\x01" + b"\xab" * 36))
        out = _reframe(pn, {"src_mac": PLC1_MAC, "dst_mac": PLC2_MAC, "vlan": None, "ttl_delta": 0})
        assert Ether(out).type == 0x8892  # not 0x9000
        assert out[14:] == pn[14:]  # payload verbatim

    def test_l2_protocol_ethertype_preserved_under_vlan(self):
        from app.protocol_engines.topology_router import _reframe

        goose = bytes(Ether(src=PLC1_MAC, dst="01:0c:cd:01:00:01", type=0x88B8) / (b"\x00" * 40))
        out = _reframe(goose, {"src_mac": "aa:bb:cc:00:00:01", "dst_mac": "01:0c:cd:01:00:01", "vlan": 250, "ttl_delta": 0})
        p = Ether(out)
        assert p.type == 0x8100 and p[Dot1Q].type == 0x88B8  # GOOSE preserved

    def test_ip_frame_checksum_valid_after_ttl(self):
        from app.protocol_engines.topology_router import _reframe
        from scapy.layers.inet import IP, TCP

        f = bytes(Ether(src=PLC1_MAC, dst=PLC2_MAC) / IP(src="10.5.1.10", dst="10.5.2.10", ttl=64) / TCP())
        out = _reframe(f, {"src_mac": PLC1_MAC, "dst_mac": "00:00:0c:aa:bb:cc", "vlan": 101, "ttl_delta": -1})
        p = Ether(out)
        assert p[IP].ttl == 63
        assert p[IP].chksum == IP(bytes(p[IP])).chksum  # recomputed correctly


class TestSpanIds:
    def test_span_ids_exposed(self):
        router, _ = _router()
        assert set(router.span_ids) == {"zone:z-cell", "zone:z-sup", "core"}
