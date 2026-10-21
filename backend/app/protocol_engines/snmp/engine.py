# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""SNMP/NTCIP protocol engine implementation.

Supports SNMPv1/v2c for transportation systems (traffic controllers,
DMS, sensors, cameras) with NTCIP-specific OID handling.

Key features:
- UDP-based (no connection setup/teardown)
- Fingerprint-based SNMP identity (sysDescr for Cyber Vision detection)
- NTCIP OID support for traffic controller polling
- Trap generation for event notification
"""

import random
import time
import zlib
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.snmp import ntcip
from app.protocol_engines.snmp.oids import (
    DISCOVERY_OIDS,
    DMS_POLL_OIDS,
    ESS_POLL_OIDS,
    TRAFFIC_CONTROLLER_POLL_OIDS,
    SystemOIDs,
)
from app.protocol_engines.snmp.packets import (
    build_snmp_get_request_packet,
    build_snmp_get_response_packet,
    build_snmp_trap_packet,
    build_snmpv3_get_request_packet,
    build_snmpv3_get_response_packet,
    generate_engine_id,
)
from app.protocol_engines.snmp.types import (
    SNMP_AGENT_PORT,
    SNMPFlowConfig,
    SNMPState,
    SNMPVersion,
    VarBind,
    SNMPv3Credentials,
    SNMPv3SecurityLevel,
    SNMPv3AuthProtocol,
    SNMPv3PrivProtocol,
)
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.SNMP)
class SnmpEngine(ProtocolEngine):
    """SNMP/NTCIP protocol engine for transportation systems.

    Generates realistic SNMP traffic including:
    - Discovery sequences (sysDescr, sysObjectID, sysUpTime)
    - Poll cycles (GetRequest/GetResponse)
    - NTCIP-specific traffic controller OIDs
    - Trap notifications
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.SNMP

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state for SNMP flow.

        Note: SNMP is stateless (UDP), but we track request IDs
        and uptime for realistic simulation.
        """
        return ConversationState(
            flow_id=flow.flow_id,
            state_name=SNMPState.IDLE.value,
            transaction_id=random.randint(1, 2147483647),  # SNMP request ID
            sequence_number=0,  # Poll cycle counter
            custom_data={
                "start_time_ms": time.time() * 1000,
                # Fallback run clock when the flow was not added through
                # UnifiedOrchestrator (which stamps config["_epoch_anchor_s"]).
                "start_wall_s": time.time(),
                "sys_uptime_ticks": 0,  # TimeTicks (hundredths of seconds)
                "pending_request": None,
                "oid_index": 0,
            },
        )

    def _get_snmp_config(self, flow: FlowContext) -> SNMPFlowConfig:
        """Extract SNMP configuration from flow config."""
        config = flow.config

        # Handle version - accept both integer and string formats
        version_raw = config.get("snmp_version", SNMPVersion.V2C)
        if isinstance(version_raw, str):
            version_map = {"v1": SNMPVersion.V1, "v2c": SNMPVersion.V2C, "v3": SNMPVersion.V3}
            version = version_map.get(version_raw.lower(), SNMPVersion.V2C)
        else:
            version = SNMPVersion(version_raw)

        flow_config = SNMPFlowConfig(
            community=config.get("community", "public"),
            version=version,
            timeout_ms=config.get("timeout_ms", 5000),
            retries=config.get("retries", 2),
            poll_oids=config.get("poll_oids", DISCOVERY_OIDS),
            bulk_max_repetitions=config.get("bulk_max_repetitions", 10),
            trap_community=config.get("trap_community", "public"),
        )

        # Handle SNMPv3 credentials
        if version == SNMPVersion.V3:
            v3_config = config.get("v3_credentials", {})
            if v3_config:
                # Map security level
                sec_level_map = {
                    "noAuthNoPriv": SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
                    "authNoPriv": SNMPv3SecurityLevel.AUTH_NO_PRIV,
                    "authPriv": SNMPv3SecurityLevel.AUTH_PRIV,
                }
                sec_level = sec_level_map.get(
                    v3_config.get("security_level", "authNoPriv"),
                    SNMPv3SecurityLevel.AUTH_NO_PRIV
                )

                # Map auth protocol
                auth_proto_map = {
                    "md5": SNMPv3AuthProtocol.MD5,
                    "sha": SNMPv3AuthProtocol.SHA,
                    "sha256": SNMPv3AuthProtocol.SHA256,
                }
                auth_proto = auth_proto_map.get(
                    v3_config.get("auth_protocol", "sha").lower(),
                    SNMPv3AuthProtocol.SHA
                )

                # Map priv protocol
                priv_proto_map = {
                    "des": SNMPv3PrivProtocol.DES,
                    "aes": SNMPv3PrivProtocol.AES128,
                    "aes128": SNMPv3PrivProtocol.AES128,
                    "aes256": SNMPv3PrivProtocol.AES256,
                }
                priv_proto = priv_proto_map.get(
                    v3_config.get("priv_protocol", "aes").lower(),
                    SNMPv3PrivProtocol.AES128
                )

                # Generate engine ID for the destination device
                engine_id = generate_engine_id(flow.destination.ip_address)

                flow_config.v3_credentials = SNMPv3Credentials(
                    username=v3_config.get("username", "admin"),
                    security_level=sec_level,
                    auth_protocol=auth_proto,
                    auth_password=v3_config.get("auth_password"),
                    priv_protocol=priv_proto,
                    priv_password=v3_config.get("priv_password"),
                    engine_id=engine_id,
                    engine_boots=v3_config.get("engine_boots", 1),
                    engine_time=v3_config.get("engine_time", 0),
                    context_name=v3_config.get("context_name", ""),
                )

        return flow_config

    def _get_poll_oids(self, flow: FlowContext) -> list[str]:
        """Static OID list for a flow: configured poll_oids, else the NTCIP
        status block for the destination's kind, else MIB-II discovery."""
        config = flow.config
        if config.get("poll_oids"):
            return config["poll_oids"]
        kind = self._ntcip_kind(flow)
        if kind == "asc":
            return TRAFFIC_CONTROLLER_POLL_OIDS
        if kind == "dms":
            return DMS_POLL_OIDS
        if kind == "ess":
            return ESS_POLL_OIDS
        return DISCOVERY_OIDS

    # ------------------------------------------------------------------
    # NTCIP
    # ------------------------------------------------------------------

    def _ntcip_kind(self, flow: FlowContext) -> str | None:
        """NTCIP kind (asc/dms/ess) of the destination, or None."""
        applicator = flow.destination.fingerprint_applicator
        sys_oid = None
        if hasattr(applicator, "get_sys_object_id"):
            sys_oid = applicator.get_sys_object_id()
        if not isinstance(sys_oid, str):
            fp = flow.destination.vendor_fingerprint or {}
            sys_oid = (fp.get("snmp_identity") or {}).get("sys_object_id")
        return ntcip.resolve_kind(flow.config, flow.destination, sys_oid)

    def _ntcip_context(
        self, flow: FlowContext, state: ConversationState
    ) -> tuple[str, str, ntcip.NtcipDevice] | None:
        """(kind, poller profile, device) when this flow polls NTCIP objects.

        None when poll_oids are configured explicitly, the destination is not
        an NTCIP device, or the poller only reads MIB-II (jump server, NMS).
        Cached on the conversation state: it cannot change during a run.
        """
        if "ntcip_ctx" not in state.custom_data:
            ctx = None
            if not flow.config.get("poll_oids"):
                kind = self._ntcip_kind(flow)
                profile = ntcip.resolve_profile(flow.config, flow.source) if kind else None
                if kind and profile:
                    ctx = (kind, profile, ntcip.make_device(flow.destination))
            state.custom_data["ntcip_ctx"] = ctx
        return state.custom_data["ntcip_ctx"]

    def _ntcip_clock(
        self, flow: FlowContext, state: ConversationState, t_ms: float
    ) -> ntcip.NtcipClock:
        epoch = self._epoch_s(flow, state, t_ms)
        offset = flow.config.get("_ntcip_utc_offset_s")
        if offset is None:
            offset = time.localtime(epoch).tm_gmtoff
        return ntcip.NtcipClock(epoch_s=epoch, utc_offset_s=int(offset))

    @staticmethod
    def _device_seed(flow: FlowContext) -> int:
        """Stable per-device seed (same for every poller, process and run).

        ``hash()`` is salted per process, so it would give the PCAP path, the
        live agent and a restarted agent different devices; crc32 does not.
        """
        dst = flow.destination
        return zlib.crc32(f"{dst.scenario_id or ''}:{dst.device_id}".encode())

    @staticmethod
    def _epoch_s(flow: FlowContext, state: ConversationState, t_ms: float) -> float:
        """Wall-clock epoch seconds for virtual time ``t_ms`` of this run."""
        anchor = flow.config.get("_epoch_anchor_s") if isinstance(flow.config, dict) else None
        if anchor is None:
            anchor = state.custom_data.get("start_wall_s", time.time())
        return float(anchor) + t_ms / 1000.0

    def _get_uptime_ticks(
        self,
        state: ConversationState,
        flow: FlowContext | None = None,
        t_ms: float | None = None,
    ) -> int:
        """sysUpTime in TimeTicks (hundredths of seconds) at virtual time ``t_ms``.

        Field devices have been running for a while when monitoring starts,
        so each device gets a stable boot time 2 h – 60 days before the run.
        Driven by the run clock (not ``time.time()``) so PCAP mode — which
        generates far faster than real time — still shows uptime advancing
        with the packet timestamps, and every poller of a device agrees.
        """
        if flow is None or t_ms is None:
            start_time = state.custom_data.get("start_time_ms", time.time() * 1000)
            return int((time.time() * 1000 - start_time) / 10)
        boot_age_s = 7200 + (self._device_seed(flow) % (60 * 86400 - 7200))
        return int((boot_age_s + t_ms / 1000.0) * 100)

    def _generate_snmp_values(
        self,
        flow: FlowContext,
        state: ConversationState,
        oid: str,
        t_ms: float | None = None,
    ) -> VarBind:
        """Generate appropriate SNMP value for an OID.

        Uses fingerprint data for identity OIDs (sysDescr, sysObjectID)
        to enable Cyber Vision vulnerability detection.
        """
        applicator = flow.destination.fingerprint_applicator

        # Check if applicator has SNMP identity methods
        if oid == SystemOIDs.SYS_DESCR.oid:
            # Get sysDescr from fingerprint - includes vulnerable firmware
            if hasattr(applicator, "get_sys_descr"):
                value = applicator.get_sys_descr()
            else:
                # Fallback to vendor fingerprint
                fp = flow.destination.vendor_fingerprint or {}
                sys_descr = (fp.get("snmp_identity") or {}).get("sys_descr")
                if sys_descr:
                    value = sys_descr
                else:
                    vendor = fp.get("vendor", "Generic")
                    model = fp.get("model", "Device")
                    version = fp.get("firmware_version", "1.0")
                    value = f"{vendor} {model} Version {version}"
            return VarBind(oid=oid, value=value, value_type="string")

        elif oid == SystemOIDs.SYS_OBJECT_ID.oid:
            # Get sysObjectID from fingerprint
            if hasattr(applicator, "get_sys_object_id"):
                value = applicator.get_sys_object_id()
            else:
                fp = flow.destination.vendor_fingerprint or {}
                value = (fp.get("snmp_identity") or {}).get(
                    "sys_object_id", "1.3.6.1.4.1.9999.1.1"
                )
            return VarBind(oid=oid, value=value, value_type="oid")

        elif oid == SystemOIDs.SYS_UPTIME.oid:
            value = self._get_uptime_ticks(state, flow, t_ms)
            return VarBind(oid=oid, value=value, value_type="timeticks")

        elif oid == SystemOIDs.SYS_NAME.oid:
            # Use device_name for unique sysName per device
            # Fall back to fingerprint sys_name or device_id if not set
            if flow.destination.device_name:
                value = flow.destination.device_name
            else:
                fp = flow.destination.vendor_fingerprint or {}
                value = (fp.get("snmp_identity") or {}).get(
                    "sys_name", f"device-{flow.destination.device_id[:8]}"
                )
            return VarBind(oid=oid, value=value, value_type="string")

        elif oid == SystemOIDs.SYS_LOCATION.oid:
            fp = flow.destination.vendor_fingerprint or {}
            value = (fp.get("snmp_identity") or {}).get("sys_location", "Unknown")
            return VarBind(oid=oid, value=value, value_type="string")

        elif oid == SystemOIDs.SYS_CONTACT.oid:
            fp = flow.destination.vendor_fingerprint or {}
            value = (fp.get("snmp_identity") or {}).get("sys_contact", "admin@local")
            return VarBind(oid=oid, value=value, value_type="string")

        elif oid == SystemOIDs.SYS_SERVICES.oid:
            return VarBind(oid=oid, value=72, value_type="integer")

        else:
            # Generate appropriate value based on OID pattern
            return self._generate_ntcip_value(flow, state, oid)

    def _generate_ntcip_value(
        self,
        flow: FlowContext,
        state: ConversationState,
        oid: str,
        t_ms: float | None = None,
    ) -> VarBind:
        """Value for a non-MIB-II OID: exact lookup in the device's NTCIP model.

        Unmodelled NTCIP OIDs answer NULL rather than an invented INTEGER 0
        (scapy cannot emit the v2c noSuchObject exception; see SPEC_NEEDS.md).
        """
        kind = self._ntcip_kind(flow)
        if kind:
            clock = self._ntcip_clock(flow, state, t_ms if t_ms is not None else 0.0)
            snap = ntcip.snapshot(kind, ntcip.make_device(flow.destination), clock)
            if oid in snap:
                val, value_type = snap[oid]
                return VarBind(oid=oid, value=val, value_type=value_type)
        if oid.startswith(ntcip.NTCIP_ROOT + "."):
            return VarBind(oid=oid, value=None, value_type="null")
        return VarBind(oid=oid, value=0, value_type="integer")

    def _ntcip_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        config: SNMPFlowConfig,
        cycle_time_ms: float,
        kind: str,
        profile: str,
        dev: ntcip.NtcipDevice,
    ) -> Iterator[PacketEvent]:
        """One central-system poll: each due PollGroup is one multi-varbind GET.

        Values come from the device model at the response timestamp, so every
        poller of a device sees the same intersection / sign / station.
        """
        due = state.custom_data.setdefault("ntcip_due", {})
        t = cycle_time_ms
        state.state_name = SNMPState.POLLING.value
        for group in ntcip.POLL_PLANS[(kind, profile)]:
            clock = self._ntcip_clock(flow, state, t)
            if group.period_s:
                bucket = int(clock.epoch_s // group.period_s)
                if due.get(group.name) == bucket:
                    continue
                due[group.name] = bucket
            oids = group.oids(dev, clock)
            if not oids:
                continue

            src_port = random.randint(49152, 65535)
            request_packet = self._build_get_request(flow, config, state, src_port, oids)
            yield PacketEvent(
                timestamp_ms=t,
                flow_id=flow.flow_id,
                packet_bytes=request_packet,
                direction="request",
                metadata={
                    "type": "snmp_get_request",
                    "request_id": state.transaction_id,
                    "oids": oids,
                    "poll_cycle": state.sequence_number,
                    "ntcip_kind": kind,
                    "ntcip_group": group.name,
                },
            )

            applicator = flow.destination.fingerprint_applicator
            if hasattr(applicator, "should_timeout") and applicator.should_timeout():
                yield PacketEvent(
                    timestamp_ms=t + config.timeout_ms,
                    flow_id=flow.flow_id,
                    packet_bytes=b"",
                    direction="timeout",
                    metadata={"type": "snmp_timeout", "request_id": state.transaction_id, "oids": oids},
                )
                state.transaction_id = (state.transaction_id + 1) % 2147483647
                break

            response_delay = flow.destination.get_response_delay_ms()
            if response_delay == 0:
                response_delay = random.uniform(5, 50)
            # Larger PDUs take the controller a little longer to assemble.
            response_delay += 0.4 * len(oids)
            response_time = t + response_delay

            snap = ntcip.snapshot(kind, dev, self._ntcip_clock(flow, state, response_time))
            var_binds = []
            for oid in oids:
                if oid in snap:
                    val, value_type = snap[oid]
                    var_binds.append(VarBind(oid=oid, value=val, value_type=value_type))
                else:
                    var_binds.append(self._generate_snmp_values(flow, state, oid, response_time))

            response_packet = self._build_get_response(flow, config, state, src_port, var_binds)
            yield PacketEvent(
                timestamp_ms=response_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "snmp_get_response",
                    "request_id": state.transaction_id,
                    "oids": oids,
                    "values": {vb.oid: vb.value for vb in var_binds},
                    "response_delay_ms": response_delay,
                    "poll_cycle": state.sequence_number,
                    "snmp_version": config.version.name,
                    "ntcip_kind": kind,
                    "ntcip_group": group.name,
                },
            )
            state.transaction_id = (state.transaction_id + 1) % 2147483647
            # Central sends the next PDU of the cycle once this one returns.
            t = response_time + random.uniform(3, 25)

        state.sequence_number += 1
        state.state_name = SNMPState.POLLING.value

    def _build_get_request(
        self,
        flow: FlowContext,
        config: SNMPFlowConfig,
        state: ConversationState,
        src_port: int,
        oids: list[str],
    ) -> bytes:
        if config.version == SNMPVersion.V3 and config.v3_credentials:
            return build_snmpv3_get_request_packet(
                src_mac=flow.source.mac_address,
                dst_mac=flow.destination.mac_address,
                src_ip=flow.source.ip_address,
                dst_ip=flow.destination.ip_address,
                src_port=src_port,
                dst_port=SNMP_AGENT_PORT,
                credentials=config.v3_credentials,
                request_id=state.transaction_id,
                oids=oids,
            )
        return build_snmp_get_request_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=SNMP_AGENT_PORT,
            community=config.community,
            request_id=state.transaction_id,
            oids=oids,
            version=config.version,
        )

    def _build_get_response(
        self,
        flow: FlowContext,
        config: SNMPFlowConfig,
        state: ConversationState,
        dst_port: int,
        var_binds: list[VarBind],
    ) -> bytes:
        if config.version == SNMPVersion.V3 and config.v3_credentials:
            return build_snmpv3_get_response_packet(
                src_mac=flow.destination.mac_address,
                dst_mac=flow.source.mac_address,
                src_ip=flow.destination.ip_address,
                dst_ip=flow.source.ip_address,
                src_port=SNMP_AGENT_PORT,
                dst_port=dst_port,
                credentials=config.v3_credentials,
                request_id=state.transaction_id,
                var_binds=var_binds,
            )
        return build_snmp_get_response_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=SNMP_AGENT_PORT,
            dst_port=dst_port,
            community=config.community,
            request_id=state.transaction_id,
            var_binds=var_binds,
            version=config.version,
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SNMP discovery sequence.

        Polls system MIB-II OIDs for device identification:
        - sysDescr (1.3.6.1.2.1.1.1.0) - Device description with firmware
        - sysObjectID (1.3.6.1.2.1.1.2.0) - Vendor OID
        - sysUpTime (1.3.6.1.2.1.1.3.0) - Uptime in ticks
        - sysName (1.3.6.1.2.1.1.5.0) - Device hostname
        - sysLocation (1.3.6.1.2.1.1.6.0) - Physical location

        These OIDs are used by Cyber Vision for device identification
        and vulnerability detection based on sysDescr content.
        """
        config = self._get_snmp_config(flow)
        state.state_name = SNMPState.DISCOVERING.value

        current_time = start_time_ms
        discovery_oids = DISCOVERY_OIDS

        for oid in discovery_oids:
            # Build GetRequest - use v3 builder if SNMPv3
            src_port = random.randint(49152, 65535)
            if config.version == SNMPVersion.V3 and config.v3_credentials:
                request_packet = build_snmpv3_get_request_packet(
                    src_mac=flow.source.mac_address,
                    dst_mac=flow.destination.mac_address,
                    src_ip=flow.source.ip_address,
                    dst_ip=flow.destination.ip_address,
                    src_port=src_port,
                    dst_port=SNMP_AGENT_PORT,
                    credentials=config.v3_credentials,
                    request_id=state.transaction_id,
                    oids=[oid],
                )
            else:
                request_packet = build_snmp_get_request_packet(
                    src_mac=flow.source.mac_address,
                    dst_mac=flow.destination.mac_address,
                    src_ip=flow.source.ip_address,
                    dst_ip=flow.destination.ip_address,
                    src_port=src_port,
                    dst_port=SNMP_AGENT_PORT,
                    community=config.community,
                    request_id=state.transaction_id,
                    oids=[oid],
                    version=config.version,
                )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=request_packet,
                direction="request",
                metadata={
                    "type": "snmp_get_request",
                    "request_id": state.transaction_id,
                    "oids": [oid],
                    "operation": "discovery",
                },
            )

            # Generate response with fingerprint-based values
            response_delay = flow.destination.get_response_delay_ms()
            if response_delay == 0:
                response_delay = random.uniform(5, 50)

            response_time = current_time + response_delay

            # Get value for this OID from fingerprint
            var_bind = self._generate_snmp_values(flow, state, oid, response_time)

            # Build response - use v3 builder if SNMPv3
            if config.version == SNMPVersion.V3 and config.v3_credentials:
                response_packet = build_snmpv3_get_response_packet(
                    src_mac=flow.destination.mac_address,
                    dst_mac=flow.source.mac_address,
                    src_ip=flow.destination.ip_address,
                    dst_ip=flow.source.ip_address,
                    src_port=SNMP_AGENT_PORT,
                    dst_port=src_port,
                    credentials=config.v3_credentials,
                    request_id=state.transaction_id,
                    var_binds=[var_bind],
                )
            else:
                response_packet = build_snmp_get_response_packet(
                    src_mac=flow.destination.mac_address,
                    dst_mac=flow.source.mac_address,
                    src_ip=flow.destination.ip_address,
                    dst_ip=flow.source.ip_address,
                    src_port=SNMP_AGENT_PORT,
                    dst_port=src_port,
                    community=config.community,
                    request_id=state.transaction_id,
                    var_binds=[var_bind],
                    version=config.version,
                )

            yield PacketEvent(
                timestamp_ms=response_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "snmp_get_response",
                    "request_id": state.transaction_id,
                    "oid": oid,
                    "value": str(var_bind.value),
                    "operation": "discovery",
                    "snmp_version": config.version.name,
                },
            )

            # Update state
            state.transaction_id = (state.transaction_id + 1) % 2147483647
            current_time = response_time + random.uniform(50, 200)

        state.state_name = SNMPState.POLLING.value

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SNMP poll cycle (GetRequest/GetResponse pair).

        NTCIP devices (signal controller, DMS, ESS) are polled the way the
        poller would poll them — see ``ntcip.POLL_PLANS`` — with one
        multi-varbind GetRequest per status block. Everything else rotates
        one MIB-II discovery OID (or a configured ``poll_oids`` entry) per
        cycle.

        The sysDescr in responses contains fingerprinted firmware version
        for Cyber Vision vulnerability detection.
        """
        config = self._get_snmp_config(flow)
        ctx = self._ntcip_context(flow, state)
        if ctx is not None:
            yield from self._ntcip_poll_cycle(flow, state, config, cycle_time_ms, *ctx)
            return

        poll_oids = self._get_poll_oids(flow) if flow.config.get("poll_oids") else DISCOVERY_OIDS

        state.state_name = SNMPState.POLLING.value

        # Select OID(s) for this poll cycle
        oid_index = state.custom_data.get("oid_index", 0)
        oid = poll_oids[oid_index % len(poll_oids)]

        # Update OID index for next cycle
        state.custom_data["oid_index"] = (oid_index + 1) % len(poll_oids)

        # Source port for this exchange
        src_port = random.randint(49152, 65535)

        # Build GetRequest - use v3 builder if SNMPv3
        if config.version == SNMPVersion.V3 and config.v3_credentials:
            request_packet = build_snmpv3_get_request_packet(
                src_mac=flow.source.mac_address,
                dst_mac=flow.destination.mac_address,
                src_ip=flow.source.ip_address,
                dst_ip=flow.destination.ip_address,
                src_port=src_port,
                dst_port=SNMP_AGENT_PORT,
                credentials=config.v3_credentials,
                request_id=state.transaction_id,
                oids=[oid],
            )
        else:
            request_packet = build_snmp_get_request_packet(
                src_mac=flow.source.mac_address,
                dst_mac=flow.destination.mac_address,
                src_ip=flow.source.ip_address,
                dst_ip=flow.destination.ip_address,
                src_port=src_port,
                dst_port=SNMP_AGENT_PORT,
                community=config.community,
                request_id=state.transaction_id,
                oids=[oid],
                version=config.version,
            )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "snmp_get_request",
                "request_id": state.transaction_id,
                "oids": [oid],
                "poll_cycle": state.sequence_number,
            },
        )

        state.state_name = SNMPState.AWAITING_RESPONSE.value

        # Check for timeout simulation
        applicator = flow.destination.fingerprint_applicator
        if hasattr(applicator, "should_timeout") and applicator.should_timeout():
            # Simulate timeout - no response
            yield PacketEvent(
                timestamp_ms=cycle_time_ms + config.timeout_ms,
                flow_id=flow.flow_id,
                packet_bytes=b"",
                direction="timeout",
                metadata={
                    "type": "snmp_timeout",
                    "request_id": state.transaction_id,
                    "oid": oid,
                },
            )
            state.transaction_id = (state.transaction_id + 1) % 2147483647
            state.sequence_number += 1
            state.state_name = SNMPState.POLLING.value
            return

        # Generate response
        response_delay = flow.destination.get_response_delay_ms()
        if response_delay == 0:
            response_delay = random.uniform(5, 50)

        response_time = cycle_time_ms + response_delay

        # Get value for this OID
        var_bind = self._generate_snmp_values(flow, state, oid, response_time)

        # Build response - use v3 builder if SNMPv3
        if config.version == SNMPVersion.V3 and config.v3_credentials:
            response_packet = build_snmpv3_get_response_packet(
                src_mac=flow.destination.mac_address,
                dst_mac=flow.source.mac_address,
                src_ip=flow.destination.ip_address,
                dst_ip=flow.source.ip_address,
                src_port=SNMP_AGENT_PORT,
                dst_port=src_port,
                credentials=config.v3_credentials,
                request_id=state.transaction_id,
                var_binds=[var_bind],
            )
        else:
            response_packet = build_snmp_get_response_packet(
                src_mac=flow.destination.mac_address,
                dst_mac=flow.source.mac_address,
                src_ip=flow.destination.ip_address,
                dst_ip=flow.source.ip_address,
                src_port=SNMP_AGENT_PORT,
                dst_port=src_port,
                community=config.community,
                request_id=state.transaction_id,
                var_binds=[var_bind],
                version=config.version,
            )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "snmp_get_response",
                "request_id": state.transaction_id,
                "oid": oid,
                "value": str(var_bind.value),
                "response_delay_ms": response_delay,
                "poll_cycle": state.sequence_number,
                "snmp_version": config.version.name,
            },
        )

        # Update state
        state.transaction_id = (state.transaction_id + 1) % 2147483647
        state.sequence_number += 1
        state.state_name = SNMPState.POLLING.value

    def generate_trap(
        self,
        flow: FlowContext,
        state: ConversationState,
        trap_time_ms: float,
        trap_type: str = "linkUp",
        var_binds: list[VarBind] | None = None,
    ) -> Iterator[PacketEvent]:
        """Generate SNMP trap notification.

        Used for event notifications:
        - coldStart/warmStart: Device reboot
        - linkUp/linkDown: Interface status change
        - authenticationFailure: Bad community string
        - enterprise-specific: Device-specific events
        """
        config = self._get_snmp_config(flow)
        fp = flow.destination.vendor_fingerprint or {}

        # Get enterprise OID from fingerprint
        enterprise_oid = (fp.get("snmp_identity") or {}).get(
            "sys_object_id", "1.3.6.1.4.1.9999"
        )

        state.state_name = SNMPState.TRAP_SENDING.value

        trap_packet = build_snmp_trap_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            community=config.trap_community,
            trap_type=trap_type,
            enterprise_oid=enterprise_oid,
            uptime_ticks=self._get_uptime_ticks(state, flow, trap_time_ms),
            var_binds=var_binds or [],
            version=config.version,
        )

        yield PacketEvent(
            timestamp_ms=trap_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=trap_packet,
            direction="response",  # Trap goes from agent to manager
            metadata={
                "type": f"snmp_trap_{trap_type}",
                "trap_type": trap_type,
                "enterprise_oid": enterprise_oid,
            },
        )

        state.state_name = SNMPState.POLLING.value

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence.

        SNMP is UDP-based, so there's no connection teardown.
        This method yields nothing but can be extended to send
        a coldStart trap if desired.
        """
        # SNMP is stateless/UDP - no connection teardown needed
        # Optionally could send a trap here
        return
        yield  # Make this a generator

    def validate_config(self, config: dict) -> list[str]:
        """Validate SNMP flow configuration."""
        errors = []

        # Validate community string (required for v1/v2c)
        community = config.get("community")
        if community is not None and not isinstance(community, str):
            errors.append("community must be a string")

        # Validate SNMP version
        snmp_version = config.get("snmp_version")
        if snmp_version is not None:
            if isinstance(snmp_version, str):
                if snmp_version.lower() not in ["v1", "v2c", "v3"]:
                    errors.append("snmp_version must be 'v1', 'v2c', or 'v3'")
            elif isinstance(snmp_version, int):
                if snmp_version not in [0, 1, 3]:  # SNMPv1=0, SNMPv2c=1, SNMPv3=3
                    errors.append("snmp_version must be 0 (v1), 1 (v2c), or 3 (v3)")
            else:
                errors.append("snmp_version must be a string or integer")

        # Validate SNMPv3 credentials if version is v3
        version_is_v3 = (
            (isinstance(snmp_version, str) and snmp_version.lower() == "v3") or
            (isinstance(snmp_version, int) and snmp_version == 3)
        )

        if version_is_v3:
            v3_creds = config.get("v3_credentials")
            if not v3_creds:
                errors.append("v3_credentials required for SNMPv3")
            elif isinstance(v3_creds, dict):
                if not v3_creds.get("username"):
                    errors.append("v3_credentials.username is required")

                sec_level = v3_creds.get("security_level", "authNoPriv")
                valid_levels = ["noAuthNoPriv", "authNoPriv", "authPriv"]
                if sec_level not in valid_levels:
                    errors.append(f"v3_credentials.security_level must be one of {valid_levels}")

                if sec_level in ["authNoPriv", "authPriv"]:
                    if not v3_creds.get("auth_password"):
                        errors.append("v3_credentials.auth_password required for authentication")

                    auth_proto = v3_creds.get("auth_protocol", "sha").lower()
                    valid_auth = ["md5", "sha", "sha256"]
                    if auth_proto not in valid_auth:
                        errors.append(f"v3_credentials.auth_protocol must be one of {valid_auth}")

                if sec_level == "authPriv":
                    if not v3_creds.get("priv_password"):
                        errors.append("v3_credentials.priv_password required for privacy")

                    priv_proto = v3_creds.get("priv_protocol", "aes").lower()
                    valid_priv = ["des", "aes", "aes128", "aes256"]
                    if priv_proto not in valid_priv:
                        errors.append(f"v3_credentials.priv_protocol must be one of {valid_priv}")

        # Validate timeout
        timeout = config.get("timeout_ms")
        if timeout is not None:
            if not isinstance(timeout, int) or timeout < 100:
                errors.append("timeout_ms must be an integer >= 100")

        # Validate poll OIDs
        poll_oids = config.get("poll_oids")
        if poll_oids is not None:
            if not isinstance(poll_oids, list):
                errors.append("poll_oids must be a list")
            else:
                for oid in poll_oids:
                    if not isinstance(oid, str) or not oid.startswith("1."):
                        errors.append(f"Invalid OID format: {oid}")

        return errors
