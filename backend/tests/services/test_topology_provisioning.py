# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for topology provisioning service + live conductor output."""

import pytest

from app.services import local_sensor_service, topology_provisioning_service as tps


def _def() -> dict:
    return {
        "zones": {
            "z-cell": {"id": "z-cell", "name": "Cell", "level": 1,
                       "network": {"subnet": "10.5.1.0/24", "gateway": "10.5.1.1", "vlan": 101}},
            "z-ops": {"id": "z-ops", "name": "Ops", "level": 3,
                      "network": {"subnet": "10.5.3.0/24", "gateway": "10.5.3.1", "vlan": 103}},
        },
        "devices": {
            "plc1": {"id": "plc1", "zoneId": "z-cell",
                     "network": {"ipAddress": "10.5.1.10", "macAddress": "00:0e:8c:11:11:11"}},
            "hmi1": {"id": "hmi1", "zoneId": "z-ops",
                     "network": {"ipAddress": "10.5.3.10", "macAddress": "00:0e:8c:33:33:33"}},
        },
        "flows": {"f1": {"id": "f1", "sourceDeviceId": "hmi1", "targetDeviceId": "plc1", "protocol": "s7comm"}},
    }


class _FakeScn:
    def __init__(self, sid, definition):
        self.id = sid
        self.definition = definition


@pytest.fixture
def patched(monkeypatch):
    sid = "abcdef12-0000-0000-0000-000000000000"
    scn = _FakeScn(sid, _def())

    async def fake_load(db, scenario_id):
        return scn

    built = []
    labs_store = []

    async def fake_build_lab(db, *, name, agent_name, created_by_id):
        slug = f"slug{len(built)}"
        rec = {
            "lab_id": f"lab-{len(built)}", "slug": slug,
            "agent_id": f"agent-{len(built)}", "agent_token": "tok",
            "sensor_serial": f"ser-{len(built)}", "state": "provisioning",
        }
        built.append((name, rec))
        labs_store.append({"lab_id": rec["lab_id"], "name": name, "slug": slug,
                           "gen_if": f"pa-gen-{slug}", "state": "running"})
        return rec

    async def fake_list_labs(db):
        return list(labs_store)

    torn = []

    async def fake_teardown_lab(db, lab_id):
        torn.append(lab_id)
        return {"success": True}

    monkeypatch.setattr(tps, "_load_scenario", fake_load)
    monkeypatch.setattr(local_sensor_service, "build_lab", fake_build_lab)
    monkeypatch.setattr(local_sensor_service, "list_labs", fake_list_labs)
    monkeypatch.setattr(local_sensor_service, "teardown_lab", fake_teardown_lab)
    return sid, built, torn


class TestProvisioning:
    async def test_preflight_counts(self, patched):
        sid, _, _ = patched
        pf = await tps.preflight(None, sid)
        assert pf["sensor_count"] == 3  # 2 zones + core
        assert pf["ram_estimate_gb"] == round(3 * 1.26, 2)
        assert set(pf["spans"]) == {"zone:z-cell", "zone:z-ops", "core"}
        assert pf["has_core"] is True

    async def test_provision_builds_one_lab_per_span(self, patched):
        sid, built, _ = patched
        res = await tps.provision(None, sid)
        assert res["sensor_count"] == 3
        assert len(built) == 3
        # every span mapped to an injection interface
        assert set(res["span_interface_map"]) == {"zone:z-cell", "zone:z-ops", "core"}
        for span, iface in res["span_interface_map"].items():
            assert iface.startswith("pa-gen-")
        # core member flagged
        roles = {m["span_id"]: m["role"] for m in res["members"]}
        assert roles["core"] == "core"
        assert roles["zone:z-cell"] == "zone"
        # names grouped by prefix
        prefix = tps.group_prefix(sid)
        assert all(name.startswith(prefix) for name, _ in built)

    async def test_provision_refuses_duplicate(self, patched):
        sid, _, _ = patched
        await tps.provision(None, sid)
        with pytest.raises(Exception) as ei:
            await tps.provision(None, sid)
        assert "already exists" in str(ei.value)

    async def test_status_filters_by_prefix(self, patched):
        sid, _, _ = patched
        await tps.provision(None, sid)
        st = await tps.status(None, sid)
        assert st["sensor_count"] == 3

    async def test_teardown_tears_down_all_members(self, patched):
        sid, _, torn = patched
        await tps.provision(None, sid)
        res = await tps.teardown(None, sid)
        assert len(res["torn_down"]) == 3
        assert all(r["ok"] for r in res["torn_down"])
        assert len(torn) == 3


class TestLiveTopologyOutput:
    def test_injects_reframed_copies_per_span_socket(self, monkeypatch):
        from app.protocol_engines import output as out_mod
        from app.services.topology_planner import derive_topology, plan_segments
        from scapy.layers.inet import IP, TCP
        from scapy.layers.l2 import Ether

        plan = derive_topology(_def(), seed="s")
        plan = plan_segments(_def(), plan).as_dict()

        sent: dict[str, list[bytes]] = {}

        class FakeSock:
            def __init__(self, iface):
                self.iface = iface
                sent.setdefault(iface, [])
            def send(self, data):
                sent[self.iface].append(bytes(data))
            def close(self):
                pass

        monkeypatch.setattr("scapy.arch.L2Socket", FakeSock, raising=False)

        ifmap = {"zone:z-cell": "pa-gen-a", "zone:z-ops": "pa-gen-b", "core": "pa-gen-c"}
        sink = out_mod.LiveTopologyOutput(plan, ifmap)

        # a cross-zone frame (hmi1 -> plc1) should hit all three sockets
        frame = bytes(Ether(src="00:0e:8c:33:33:33", dst="00:0e:8c:11:11:11")
                      / IP(src="10.5.3.10", dst="10.5.1.10", ttl=64) / TCP(sport=5000, dport=102))
        sink.write_packet(frame, 0.0, flow_id="f1")
        sink.close()

        assert len(sent["pa-gen-b"]) == 1  # source zone (near side)
        assert len(sent["pa-gen-a"]) == 1  # target zone (far side)
        assert len(sent["pa-gen-c"]) == 2  # core carries both framings
        assert sink.packet_count == 4
