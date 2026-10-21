# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP device models and their wiring into the SNMP engine.

These guard the failure mode the 2026-10 ITS audit found — NTCIP code that
existed but never reached the wire, with every value an INTEGER 0 under the
wrong arc. Fingerprints are built inline (not loaded from vendor templates)
so identity-data changes cannot mask or break kind resolution.
"""
from unittest.mock import MagicMock

import pytest
from scapy.layers.l2 import Ether
from scapy.layers.snmp import SNMP

from app.protocol_engines.snmp import ntcip
from app.protocol_engines.snmp.engine import SnmpEngine
from app.protocol_engines.snmp.ntcip import ntcip_1202, ntcip_1203
from app.protocol_engines.snmp.ntcip._mib_table import MIB_OBJECTS
from app.protocol_engines.snmp.ntcip._model import NtcipClock, NtcipDevice
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType

# 2026-10-21 00:00 local (UTC-5); the tests sweep the whole day from here.
MIDNIGHT = 1792558800
UTC_OFFSET = -5 * 3600
KINDS = ("asc", "dms", "ess")
SEEDS = (1, 77, 4242, 90001, 3735928559)


def _clock(hour: float, plus_s: float = 0.0) -> NtcipClock:
    return NtcipClock(MIDNIGHT + hour * 3600 + plus_s, UTC_OFFSET)


def _dev(seed: int, region: int = 7) -> NtcipDevice:
    return NtcipDevice(seed=seed, region_seed=region, vendor="Econolite", model="Cobalt", firmware="3.2.25")


# --------------------------------------------------------------------------
# Object table and poll plans
# --------------------------------------------------------------------------

def test_device_arcs_match_the_mib_files():
    arcs = {name: oid for name, (oid, *_rest) in MIB_OBJECTS.items()}
    assert arcs["phaseStatusGroupGreens"].startswith("1.3.6.1.4.1.1206.4.2.1.")
    assert arcs["dmsMessageMultiString"].startswith("1.3.6.1.4.1.1206.4.2.3.")
    assert arcs["essAirTemperature"].startswith("1.3.6.1.4.1.1206.4.2.5.")
    assert arcs["globalTime"].startswith("1.3.6.1.4.1.1206.4.2.6.")
    assert arcs["phaseStatusGroupGreens"] == "1.3.6.1.4.1.1206.4.2.1.1.4.1.4"
    assert arcs["dmsMsgTableSource"] == "1.3.6.1.4.1.1206.4.2.3.6.5"


@pytest.mark.parametrize("hour", [0.5, 4.9, 7.0, 12.0, 16.0, 20.0, 23.0])
@pytest.mark.parametrize("seed", SEEDS)
def test_every_polled_oid_has_a_modelled_value(seed, hour):
    """No poll-plan OID may fall through to a placeholder value."""
    dev, clock = _dev(seed), _clock(hour)
    for (kind, _profile), groups in ntcip.POLL_PLANS.items():
        snap = ntcip.snapshot(kind, dev, clock)
        for group in groups:
            for oid in group.oids(dev, clock):
                assert oid in snap, f"{kind}/{group.name}: {oid} not modelled"


@pytest.mark.parametrize("kind", KINDS)
def test_snapshot_types_match_the_mib(kind):
    by_base = {oid: (name, vtype, columnar) for name, (oid, vtype, _a, columnar) in MIB_OBJECTS.items()}
    for hour in (2.0, 8.0, 13.0, 17.0):
        for oid, (val, vtype) in ntcip.snapshot(kind, _dev(99), _clock(hour)).items():
            base = next((b for b in by_base if oid.startswith(b + ".")), None)
            assert base is not None, oid
            name, mib_type, columnar = by_base[base]
            assert vtype == mib_type, name
            assert columnar or oid == base + ".0", f"scalar {name} must use instance .0"
            if vtype in ("integer", "counter"):
                assert isinstance(val, int), name
            elif vtype == "octets":
                assert isinstance(val, bytes), name
            else:
                assert isinstance(val, str), name


# --------------------------------------------------------------------------
# NTCIP 1202 signal controller
# --------------------------------------------------------------------------

def _phases(mask: int) -> set[int]:
    return {p for p in range(1, 9) if mask >> (p - 1) & 1}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("hour", [1.0, 7.5, 12.0, 16.5, 20.0])
def test_phase_displays_are_physically_consistent(seed, hour):
    """Across 2+ full cycles: one colour per phase, rings and barriers honoured."""
    dev = _dev(seed)
    for t in range(0, 2 * 130 + 1):
        st = ntcip_1202.phase_status(dev, _clock(hour, t))
        reds, yellows, greens = _phases(st["reds"]), _phases(st["yellows"]), _phases(st["greens"])
        assert not (reds & yellows or reds & greens or yellows & greens)
        ons = _phases(st["ons"])
        assert len(ons) == 2 and len(ons & {1, 2, 3, 4}) == 1  # one timing phase per ring
        assert ons <= set(ntcip_1202.BARRIER_A) or not ons & set(ntcip_1202.BARRIER_A)
        assert (greens | yellows) <= ons
        assert _phases(st["walks"]) <= greens and _phases(st["ped_clears"]) <= greens
        assert not _phases(st["walks"]) & _phases(st["dont_walks"])
        assert not _phases(st["veh_calls"]) & greens


def test_controller_cycles_through_every_served_phase():
    dev = _dev(4242)
    served = set()
    for t in range(0, 140):
        served |= _phases(ntcip_1202.phase_status(dev, _clock(12.0, t))["greens"])
    splits = ntcip_1202._splits(ntcip_1202._intersection(dev), ntcip_1202._plan(dev, _clock(12.0))[1])
    assert served == {p for p, s in splits.items() if s > 0}


def test_corridor_shares_cycle_lengths_and_runs_its_tod_plans():
    a, b = _dev(1, region=5), _dev(2, region=5)
    for hour in (7.0, 12.0, 16.0):
        assert ntcip_1202._plan(a, _clock(hour)) == ntcip_1202._plan(b, _clock(hour))
    assert ntcip_1202.phase_status(a, _clock(2.0))["pattern"] == ntcip_1202.FREE_PATTERN
    assert ntcip_1202.phase_status(a, _clock(7.0))["pattern"] == 1


def test_volume_occupancy_tracks_demand():
    dev = _dev(77)
    night = sum(ntcip_1202.volume_occupancy(dev, _clock(3.0), d)[0] for d in range(1, 9))
    peak = sum(ntcip_1202.volume_occupancy(dev, _clock(17.0), d)[0] for d in range(1, 9))
    assert peak > 3 * night > 0


# --------------------------------------------------------------------------
# NTCIP 1203 DMS
# --------------------------------------------------------------------------

def test_dms_crc_matches_the_x25_check_value():
    assert ntcip_1203.crc16_x25(b"123456789") == 0x906E


def test_dms_message_id_points_at_the_displayed_entry():
    dev = _dev(4242)
    day = ntcip.snapshot("dms", dev, _clock(10.0))
    msg = ntcip_1203.current_message(dev, _clock(10.0))
    source = day[ntcip_1203.STATUS_BLOCK[0]][0]
    assert source == ntcip_1203.message_id_code(msg.memory_type, msg.number, msg.crc)
    multi_oid = ntcip_1203.message_block(dev, _clock(10.0))[0]
    assert day[multi_oid][0] == msg.multi and msg.multi
    night = ntcip_1203.current_message(dev, _clock(2.0))
    assert night.memory_type == ntcip_1203.BLANK and night.crc == 0
    assert ntcip_1203.message_block(dev, _clock(2.0)) == []


# --------------------------------------------------------------------------
# Kind and profile resolution (inline fingerprints)
# --------------------------------------------------------------------------

def _ctx(device_type=None, sys_oid=None):
    return DeviceContext(
        device_id="d", mac_address="02:00:00:00:00:02", ip_address="10.0.0.2", port=161,
        device_type=device_type,
        vendor_fingerprint={"snmp_identity": {"sys_object_id": sys_oid}} if sys_oid else {},
    )


@pytest.mark.parametrize(
    "config,device_type,sys_oid,expected",
    [
        ({}, "traffic_controller", None, "asc"),
        ({}, "dms", None, "dms"),
        ({}, "dms_sign", None, "dms"),
        ({}, "wayside_signal_controller", None, None),             # rail, not NTCIP
        ({}, "weather_station", None, "ess"),
        ({}, "controller", "1.3.6.1.4.1.1206.4.2.1", "asc"),       # generic type -> arc
        ({}, None, "1.3.6.1.4.1.1206.4.2.3.2", "dms"),
        ({}, "radar_detector", "1.3.6.1.4.1.1206.4.2.5", None),      # typed, not an ESS
        ({}, "camera", None, None),
        ({}, None, "1.3.6.1.4.1.9.1.1", None),
        ({"device_type": "dms"}, "traffic_controller", None, "dms"),  # explicit wins
        ({"ntcip": False}, "traffic_controller", None, None),
    ],
)
def test_resolve_kind(config, device_type, sys_oid, expected):
    dst = _ctx(device_type, sys_oid)
    assert ntcip.resolve_kind(config, dst, sys_oid) == expected


@pytest.mark.parametrize(
    "source_type,expected",
    [("scada_server", "status"), ("historian", "data_collection"),
     ("workstation", "config"), ("jump_server", None), (None, "status")],
)
def test_resolve_profile(source_type, expected):
    assert ntcip.resolve_profile({}, _ctx(source_type)) == expected


# --------------------------------------------------------------------------
# Engine end to end
# --------------------------------------------------------------------------

def _flow(src_type, dst_type, flow_id, anchor=MIDNIGHT + 12 * 3600, **config):
    app = MagicMock()
    app.should_timeout.return_value = False
    app.get_sys_object_id.return_value = "1.3.6.1.4.1.1206.4.2.1"
    src = DeviceContext(device_id=f"src-{flow_id}", mac_address="02:00:00:00:00:01",
                        ip_address="10.0.0.1", port=0, device_type=src_type)
    dst = DeviceContext(device_id="tc-7", mac_address="02:00:00:00:00:02", ip_address="10.0.0.2",
                        port=161, scenario_id="scn", device_type=dst_type)
    dst._fingerprint_applicator = app
    return FlowContext(
        flow_id=flow_id, source=src, destination=dst, protocol=ProtocolType.SNMP,
        config={"_epoch_anchor_s": anchor, "_ntcip_utc_offset_s": UTC_OFFSET, **config},
        timing_model={},
    )


def _poll(flow, t_ms):
    engine = SnmpEngine()
    return list(engine.generate_poll_cycle(flow, engine.create_initial_state(flow), t_ms))


def test_status_poll_is_one_multi_varbind_get_with_matching_response():
    events = _poll(_flow("scada_server", "traffic_controller", "atms"), 0.0)
    req, resp = Ether(events[0].packet_bytes)[SNMP], Ether(events[1].packet_bytes)[SNMP]
    req_oids = [vb.oid.val for vb in req.PDU.varbindlist]
    resp_oids = [vb.oid.val for vb in resp.PDU.varbindlist]
    assert req_oids == resp_oids == ntcip_1202.STATUS_BLOCK
    assert req.PDU.id.val == resp.PDU.id.val
    assert all(vb.value.val is not None for vb in resp.PDU.varbindlist)


def test_every_poller_sees_the_same_controller():
    atms = _flow("scada_server", "traffic_controller", "atms")
    other = _flow("scada_server", "traffic_controller", "backup-atms")
    for t_ms in (0.0, 13_500.0, 61_000.0):
        a = _poll(atms, t_ms)[1].metadata["values"]
        b = _poll(other, t_ms)[1].metadata["values"]
        assert a == b


def test_profiles_poll_different_objects():
    groups = lambda src: {e.metadata["ntcip_group"] for e in _poll(_flow(src, "traffic_controller", src), 0.0)}
    assert groups("scada_server") == {"asc_status", "asc_volume", "clock"}
    assert groups("historian") == {"asc_volume"}
    assert groups("workstation") == {"identity", "asc_config"}
    jump = _poll(_flow("jump_server", "traffic_controller", "jump"), 0.0)
    assert len(jump) == 2 and "ntcip_kind" not in jump[0].metadata   # MIB-II rotation


def test_slow_groups_fire_once_per_period():
    engine = SnmpEngine()
    flow = _flow("scada_server", "traffic_controller", "atms")
    state = engine.create_initial_state(flow)
    volume_polls = 0
    for second in range(120):
        events = list(engine.generate_poll_cycle(flow, state, second * 1000.0))
        volume_polls += sum(1 for e in events if e.direction == "request" and e.metadata["ntcip_group"] == "asc_volume")
    assert volume_polls in (2, 3)   # one per 60 s window (anchor may straddle a boundary)


def test_explicit_poll_oids_still_win():
    oid = "1.3.6.1.2.1.1.5.0"
    events = _poll(_flow("scada_server", "traffic_controller", "x", poll_oids=[oid]), 0.0)
    assert events[0].metadata["oids"] == [oid]


def test_global_time_is_counter32_on_the_wire():
    events = _poll(_flow("workstation", "traffic_controller", "ews"), 0.0)
    resp = next(e for e in events if e.direction == "response" and e.metadata["ntcip_group"] == "identity")
    raw = bytes(Ether(resp.packet_bytes)[SNMP])
    oid = MIB_OBJECTS["globalTime"][0] + ".0"
    from scapy.asn1.asn1 import ASN1_OID
    from scapy.asn1.asn1 import ASN1_Codecs
    enc = ASN1_OID(oid).enc(ASN1_Codecs.BER)
    assert raw[raw.index(enc) + len(enc)] == 0x41
