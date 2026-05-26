# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Stats API routes for dashboard statistics.

The dashboard's hero KPIs and breakdown panels all hang off
``GET /api/v1/stats/overview``. The endpoint scans the current
user's scenarios once (definition is large but cheap to deserialize
locally) and synthesises every aggregate from a single pass.
"""

from collections import Counter
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.models.scenario import Scenario

router = APIRouter(prefix="/stats", tags=["Stats"])


# ─── Response models ─────────────────────────────────────────────────


class VerticalMixEntry(BaseModel):
    """One slice of the vertical-distribution panel."""

    vertical: str
    count: int


class ProtocolUsageEntry(BaseModel):
    """One row of the top-protocols panel."""

    protocol: str
    scenarios: int      # number of scenarios that include this protocol
    devices: int        # device instances declaring it across the fleet


class RecentScenarioEntry(BaseModel):
    """One row of the recent-scenarios panel."""

    id: str
    name: str
    vertical: str | None
    device_count: int
    flow_count: int
    updated_at: str | None


class OverviewStatsResponse(BaseModel):
    """Overview statistics for the dashboard."""

    scenarios: int
    device_instances: int
    protocols: int
    pcaps: int
    vertical_mix: list[VerticalMixEntry]
    top_protocols: list[ProtocolUsageEntry]
    recent_scenarios: list[RecentScenarioEntry]


# ─── Endpoint ────────────────────────────────────────────────────────


def _count_pcaps() -> int:
    """Count generated PCAP files on disk."""
    pcap_dir = Path(settings.pcap_output_dir)
    if not pcap_dir.exists():
        return 0
    return len(list(pcap_dir.glob("*.pcap"))) + len(list(pcap_dir.glob("*.pcapng")))


@router.get("/overview", response_model=OverviewStatsResponse)
async def get_overview_stats(
    db: DBSession,
    current_user: CurrentUser,
) -> OverviewStatsResponse:
    """Aggregate dashboard stats scoped to the requesting user.

    Returns:
      * `scenarios` — count of scenarios the user owns
      * `device_instances` — sum of devices across all of their scenarios
        (operator-meaningful, not the global template catalog)
      * `protocols` — distinct protocol count across their fleet
      * `pcaps` — generated PCAP files on disk
      * `vertical_mix` — `[{vertical, count}]` sorted desc
      * `top_protocols` — top 5 by device usage `[{protocol, scenarios, devices}]`
      * `recent_scenarios` — 5 most recently updated `[{id, name, vertical,
        device_count, flow_count, updated_at}]`
    """
    # 1. Count + summary breakdowns from a single scan of the user's scenarios.
    #    Pulls minimal columns; the definition JSON is big but we need it for
    #    accurate protocol & device-instance counts.
    result = await db.execute(
        select(Scenario.id, Scenario.name, Scenario.vertical,
               Scenario.definition, Scenario.updated_at)
        .where(Scenario.user_id == current_user.id)
        .order_by(desc(Scenario.updated_at))
    )
    rows = result.all()

    scenario_count = len(rows)
    device_instances = 0
    vertical_counter: Counter[str] = Counter()
    # protocol -> (scenarios using it, total device declarations)
    protocol_scenarios: Counter[str] = Counter()
    protocol_devices: Counter[str] = Counter()
    recent: list[RecentScenarioEntry] = []

    for sid, name, vertical, definition, updated_at in rows:
        definition = definition or {}
        devices = definition.get("devices") or {}
        flows = definition.get("flows") or {}
        device_iter = devices.values() if isinstance(devices, dict) else devices
        flow_iter = flows.values() if isinstance(flows, dict) else flows

        s_protos: set[str] = set()
        d_count = 0
        for d in device_iter:
            if not isinstance(d, dict):
                continue
            d_count += 1
            for p in (d.get("protocols") or []):
                if isinstance(p, str) and p:
                    protocol_devices[p] += 1
                    s_protos.add(p)
        for f in flow_iter:
            if isinstance(f, dict):
                proto = f.get("protocol")
                if isinstance(proto, str) and proto:
                    s_protos.add(proto)

        device_instances += d_count
        if vertical:
            vertical_counter[vertical] += 1
        for p in s_protos:
            protocol_scenarios[p] += 1

        if len(recent) < 5:
            recent.append(RecentScenarioEntry(
                id=str(sid),
                name=name or "(unnamed)",
                vertical=vertical,
                device_count=d_count,
                flow_count=len(flows) if isinstance(flows, dict) else len(list(flow_iter)),
                updated_at=updated_at.isoformat() if updated_at else None,
            ))

    # 2. Order the breakdowns.
    vertical_mix = [
        VerticalMixEntry(vertical=v, count=c)
        for v, c in vertical_counter.most_common()
    ]
    # OT-protocols breakdown: rank only canonical industrial protocols.
    # Management transports (SNMP/NTCIP), IT plumbing (HTTPS/SSH/etc.),
    # and link-layer discovery (LLDP/CDP/ARP/DHCP) get filtered out —
    # they dominate the raw counts but tell you nothing about the OT
    # mix. They still contribute to the headline `protocols` total.
    _OT_PROTOCOLS = {
        "modbus_tcp", "modbus", "modbus_rtu",
        "ethernet_ip", "enip", "cip_safety",
        "profinet", "profisafe",
        "s7comm", "s7comm_plus", "s7",
        "bacnet", "bacnet_ip",
        "opc_ua", "opcua",
        "dnp3",
        "iec104", "iec_104", "iec_60870_5_104",
        "iec61850", "iec_61850", "goose", "sv",
        "hart", "hart_ip",
        "fins", "slmp", "pccc", "ethercat", "codesys",
    }
    top_protocols = [
        ProtocolUsageEntry(
            protocol=p,
            scenarios=protocol_scenarios.get(p, 0),
            devices=protocol_devices[p],
        )
        for p, _ in protocol_devices.most_common()
        if p in _OT_PROTOCOLS
    ][:5]

    return OverviewStatsResponse(
        scenarios=scenario_count,
        device_instances=device_instances,
        protocols=len(protocol_devices),
        pcaps=_count_pcaps(),
        vertical_mix=vertical_mix,
        top_protocols=top_protocols,
        recent_scenarios=recent,
    )
