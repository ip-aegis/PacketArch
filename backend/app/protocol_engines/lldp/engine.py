"""LLDP protocol engine implementation.

LLDP (IEEE 802.1AB) is a Layer 2 discovery protocol used by network devices
to advertise their identity, capabilities, and neighbors. Unlike request/response
protocols, LLDP is a one-way broadcast protocol - devices periodically send
LLDP frames to a multicast address without expecting responses.

Key characteristics:
- Layer 2 only (no IP required)
- Multicast destination: 01:80:C2:00:00:0E
- EtherType: 0x88CC
- Default 30-second transmission interval
- TTL typically 120 seconds (30 * 4)
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.lldp.packets import (
    build_lldpdu,
    build_shutdown_lldpdu,
)
from app.protocol_engines.lldp.types import (
    DEFAULT_TX_INTERVAL,
    DEFAULT_TTL,
    ChassisIDSubtype,
    PortIDSubtype,
    SystemCapability,
    AddressFamily,
    MAUType,
    LLDPDeviceType,
    LLDPIdentity,
    LLDPConfig,
    INDUSTRIAL_DEVICE_PROFILES,
)
from app.protocol_engines.types import (
    FlowContext,
    PacketEvent,
    LLDPConversationState,
    ProtocolType,
)


@register_engine(ProtocolType.LLDP)
class LLDPEngine(ProtocolEngine):
    """LLDP protocol engine.

    Generates periodic LLDP advertisement frames from devices.
    LLDP is a one-way broadcast protocol - devices send frames
    without expecting responses.
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.LLDP

    def create_initial_state(self, flow: FlowContext) -> LLDPConversationState:
        """Create initial conversation state."""
        return LLDPConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            frame_count=0,
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: LLDPConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup sequence.

        For LLDP, the startup sends the first advertisement frame immediately.
        """
        # Get device identity
        identity = self._get_device_identity(flow)
        config = self._get_config(flow)

        # Store config in state
        state.custom_data["tx_interval"] = config.tx_interval
        state.custom_data["include_ieee_802_1"] = config.include_ieee_802_1
        state.custom_data["include_ieee_802_3"] = config.include_ieee_802_3
        state.custom_data["include_lldp_med"] = config.include_lldp_med
        state.custom_data["include_profinet"] = config.include_profinet

        # Build and send first LLDP frame
        lldp_frame = build_lldpdu(
            src_mac=flow.source.mac_address,
            identity=identity,
            include_ieee_802_1=config.include_ieee_802_1,
            include_ieee_802_3=config.include_ieee_802_3,
            include_lldp_med=config.include_lldp_med,
            include_profinet=config.include_profinet,
        )

        state.frame_count += 1
        state.state_name = "advertising"
        state.last_tx_time_ms = start_time_ms

        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=lldp_frame,
            direction="request",  # LLDP is always "outgoing" from the device
            metadata={
                "type": "lldp_advertisement",
                "frame_number": state.frame_count,
                "system_name": identity.system_name,
                "ttl": identity.ttl,
            },
        )

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: LLDPConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate periodic LLDP advertisement.

        LLDP devices send advertisements at regular intervals (default 30 seconds).
        """
        # Get device identity
        identity = self._get_device_identity(flow)

        # Get config from state
        include_ieee_802_1 = state.custom_data.get("include_ieee_802_1", True)
        include_ieee_802_3 = state.custom_data.get("include_ieee_802_3", True)
        include_lldp_med = state.custom_data.get("include_lldp_med", False)
        include_profinet = state.custom_data.get("include_profinet", False)

        # Build LLDP frame
        lldp_frame = build_lldpdu(
            src_mac=flow.source.mac_address,
            identity=identity,
            include_ieee_802_1=include_ieee_802_1,
            include_ieee_802_3=include_ieee_802_3,
            include_lldp_med=include_lldp_med,
            include_profinet=include_profinet,
        )

        state.frame_count += 1
        state.last_tx_time_ms = cycle_time_ms

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=lldp_frame,
            direction="request",
            metadata={
                "type": "lldp_advertisement",
                "frame_number": state.frame_count,
                "system_name": identity.system_name,
                "ttl": identity.ttl,
            },
        )

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: LLDPConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence.

        Sends LLDP frame with TTL=0 to trigger immediate neighbor deletion.
        """
        identity = self._get_device_identity(flow)

        # Build shutdown frame (TTL=0)
        shutdown_frame = build_shutdown_lldpdu(
            src_mac=flow.source.mac_address,
            port_id=identity.port_id,
        )

        state.state_name = "shutdown"

        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=shutdown_frame,
            direction="request",
            metadata={
                "type": "lldp_shutdown",
                "ttl": 0,
            },
        )

    def _get_device_identity(self, flow: FlowContext) -> LLDPIdentity:
        """Get LLDP identity from fingerprint or config."""
        fingerprint = flow.source.vendor_fingerprint
        config = flow.config

        # Check for device profile
        profile_key = config.get("device_profile")
        if profile_key and profile_key in INDUSTRIAL_DEVICE_PROFILES:
            profile = INDUSTRIAL_DEVICE_PROFILES[profile_key]
            identity = LLDPIdentity(
                chassis_id=flow.source.mac_address,
                port_id=config.get("port_id", "eth0"),
                ttl=config.get("ttl", DEFAULT_TTL),
                port_description=config.get("port_description", f"Port {config.get('port_id', 'eth0')}"),
                system_name=config.get("system_name", profile["model"]),
                system_description=profile["description"],
                capabilities=profile["capabilities"],
                enabled_capabilities=profile["capabilities"],
                management_address=flow.source.ip_address,
                vlan_id=config.get("vlan_id"),
                manufacturer=profile["vendor"],
                model_name=profile["model"],
            )
            return identity

        # Check fingerprint for LLDP identity
        if fingerprint:
            lldp_identity = fingerprint.get("lldp_identity", {})
            if lldp_identity:
                return LLDPIdentity(
                    chassis_id_subtype=ChassisIDSubtype(
                        lldp_identity.get("chassis_id_subtype", ChassisIDSubtype.MAC_ADDRESS)
                    ),
                    chassis_id=lldp_identity.get("chassis_id", flow.source.mac_address),
                    port_id_subtype=PortIDSubtype(
                        lldp_identity.get("port_id_subtype", PortIDSubtype.INTERFACE_NAME)
                    ),
                    port_id=lldp_identity.get("port_id", "eth0"),
                    ttl=lldp_identity.get("ttl", DEFAULT_TTL),
                    port_description=lldp_identity.get("port_description", ""),
                    system_name=lldp_identity.get("system_name", ""),
                    system_description=lldp_identity.get("system_description", ""),
                    capabilities=lldp_identity.get("capabilities", 0),
                    enabled_capabilities=lldp_identity.get("enabled_capabilities", 0),
                    management_address=lldp_identity.get(
                        "management_address", flow.source.ip_address
                    ),
                    vlan_id=lldp_identity.get("vlan_id"),
                    max_frame_size=lldp_identity.get("max_frame_size", 1522),
                    mau_type=MAUType(lldp_identity.get("mau_type", MAUType.FD_1000BASE_T)),
                    hardware_revision=lldp_identity.get("hardware_revision", ""),
                    firmware_revision=lldp_identity.get("firmware_revision", ""),
                    serial_number=lldp_identity.get("serial_number", ""),
                    manufacturer=lldp_identity.get("manufacturer", ""),
                    model_name=lldp_identity.get("model_name", ""),
                )

        # Build identity from config and defaults
        device_type = config.get("device_type", LLDPDeviceType.SWITCH)

        # Determine capabilities based on device type
        capabilities = self._get_capabilities_for_device_type(device_type)

        return LLDPIdentity(
            chassis_id=config.get("chassis_id", flow.source.mac_address),
            chassis_id_subtype=ChassisIDSubtype(
                config.get("chassis_id_subtype", ChassisIDSubtype.MAC_ADDRESS)
            ),
            port_id=config.get("port_id", "eth0"),
            port_id_subtype=PortIDSubtype(
                config.get("port_id_subtype", PortIDSubtype.INTERFACE_NAME)
            ),
            ttl=config.get("ttl", DEFAULT_TTL),
            port_description=config.get("port_description", ""),
            system_name=config.get("system_name", flow.source.device_name or "Device"),
            system_description=config.get("system_description", ""),
            capabilities=config.get("capabilities", capabilities),
            enabled_capabilities=config.get("enabled_capabilities", capabilities),
            management_address=config.get("management_address", flow.source.ip_address),
            management_address_afi=AddressFamily(
                config.get("management_address_afi", AddressFamily.IPV4)
            ),
            vlan_id=config.get("vlan_id"),
            vlan_name=config.get("vlan_name", ""),
            max_frame_size=config.get("max_frame_size", 1522),
            mau_type=MAUType(config.get("mau_type", MAUType.FD_1000BASE_T)),
            hardware_revision=config.get("hardware_revision", ""),
            firmware_revision=config.get("firmware_revision", ""),
            software_revision=config.get("software_revision", ""),
            serial_number=config.get("serial_number", ""),
            manufacturer=config.get("manufacturer", ""),
            model_name=config.get("model_name", ""),
            asset_id=config.get("asset_id", ""),
            profinet_delay_values=config.get("profinet_delay_values", False),
            rx_delay_local=config.get("rx_delay_local", 0),
            tx_delay_local=config.get("tx_delay_local", 0),
        )

    def _get_config(self, flow: FlowContext) -> LLDPConfig:
        """Get LLDP configuration from flow config."""
        config = flow.config

        return LLDPConfig(
            tx_interval=config.get("tx_interval", DEFAULT_TX_INTERVAL),
            tx_hold_multiplier=config.get("tx_hold_multiplier", 4),
            include_port_description=config.get("include_port_description", True),
            include_system_name=config.get("include_system_name", True),
            include_system_description=config.get("include_system_description", True),
            include_system_capabilities=config.get("include_system_capabilities", True),
            include_management_address=config.get("include_management_address", True),
            include_ieee_802_1=config.get("include_ieee_802_1", True),
            include_ieee_802_3=config.get("include_ieee_802_3", True),
            include_lldp_med=config.get("include_lldp_med", False),
            include_profinet=config.get("include_profinet", False),
        )

    def _get_capabilities_for_device_type(self, device_type: str | LLDPDeviceType) -> int:
        """Get default capabilities for a device type."""
        if isinstance(device_type, str):
            try:
                device_type = LLDPDeviceType(device_type)
            except ValueError:
                device_type = LLDPDeviceType.SWITCH

        capability_map = {
            LLDPDeviceType.SWITCH: SystemCapability.BRIDGE,
            LLDPDeviceType.ROUTER: SystemCapability.BRIDGE | SystemCapability.ROUTER,
            LLDPDeviceType.PLC: SystemCapability.STATION_ONLY,
            LLDPDeviceType.HMI: SystemCapability.STATION_ONLY,
            LLDPDeviceType.IO_DEVICE: SystemCapability.STATION_ONLY,
            LLDPDeviceType.DRIVE: SystemCapability.STATION_ONLY,
            LLDPDeviceType.SENSOR: SystemCapability.STATION_ONLY,
            LLDPDeviceType.WORKSTATION: SystemCapability.STATION_ONLY,
            LLDPDeviceType.SERVER: SystemCapability.STATION_ONLY,
        }

        return capability_map.get(device_type, SystemCapability.STATION_ONLY)

    def validate_config(self, config: dict) -> list[str]:
        """Validate LLDP configuration."""
        errors = []

        # Validate tx_interval
        tx_interval = config.get("tx_interval")
        if tx_interval is not None:
            if not isinstance(tx_interval, int) or tx_interval < 1 or tx_interval > 32768:
                errors.append("tx_interval must be 1-32768 seconds")

        # Validate tx_hold_multiplier
        hold = config.get("tx_hold_multiplier")
        if hold is not None:
            if not isinstance(hold, int) or hold < 2 or hold > 10:
                errors.append("tx_hold_multiplier must be 2-10")

        # Validate TTL
        ttl = config.get("ttl")
        if ttl is not None:
            if not isinstance(ttl, int) or ttl < 0 or ttl > 65535:
                errors.append("ttl must be 0-65535 seconds")

        # Validate VLAN ID
        vlan_id = config.get("vlan_id")
        if vlan_id is not None:
            if not isinstance(vlan_id, int) or vlan_id < 1 or vlan_id > 4094:
                errors.append("vlan_id must be 1-4094")

        # Validate device_type
        device_type = config.get("device_type")
        if device_type is not None:
            valid_types = [t.value for t in LLDPDeviceType]
            if device_type not in valid_types:
                errors.append(f"device_type must be one of: {valid_types}")

        # Validate device_profile
        profile = config.get("device_profile")
        if profile is not None:
            if profile not in INDUSTRIAL_DEVICE_PROFILES:
                errors.append(f"Unknown device_profile: {profile}")

        return errors
