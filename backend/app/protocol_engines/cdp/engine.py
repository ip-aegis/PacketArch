# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""CDP (Cisco Discovery Protocol) engine for network discovery simulation.

CDP is a Layer 2 protocol used by Cisco devices to advertise their presence
and capabilities to directly connected neighbors.

Key characteristics:
- Multicast destination: 01:00:0c:cc:cc:cc
- Default advertisement interval: 60 seconds
- Default hold time (TTL): 180 seconds
- One-way protocol (no responses, just advertisements)

Supported features:
- Device ID, Port ID, Addresses
- Capabilities bitmap
- Software version, Platform
- Native VLAN, VTP Domain
- Duplex status
- Management addresses
"""

import logging
import random
from typing import Any

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.cdp.packets import (
    CDP_DEFAULT_INTERVAL,
    CDP_DEFAULT_TTL,
    CDP_VERSION_2,
    CDPCapability,
    build_cdp_advertisement,
    build_cdp_frame,
)
from app.protocol_engines.types import (
    CDPConversationState,
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
)

logger = logging.getLogger(__name__)


# Cisco platform strings by device type
CISCO_PLATFORMS = {
    "switch": [
        "Catalyst 2960X-48TS-L",
        "Catalyst 3850-24P",
        "Catalyst 9300-48P",
        "WS-C3750X-24P",
        "Nexus 9336C-FX2",
    ],
    "router": [
        "Cisco ISR 4331",
        "Cisco ISR 4451-X",
        "Cisco ASR 1001-X",
        "Cisco C8200-1N-4T",
        "Cisco 2911",
    ],
    "firewall": [
        "Cisco ASA 5506-X",
        "Cisco ASA 5516-X",
        "Cisco Firepower 2110",
        "Cisco Firepower 4110",
    ],
    "phone": [
        "Cisco IP Phone 8845",
        "Cisco IP Phone 7945G",
        "Cisco IP Phone 8865",
    ],
    "ap": [
        "Cisco Aironet 2802I",
        "Cisco Aironet 3802I",
        "Cisco Catalyst 9120AXI",
    ],
    "default": ["Cisco Device"],
}

# Cisco IOS versions by platform type
CISCO_IOS_VERSIONS = {
    "switch": [
        "Cisco IOS Software, C2960X Software (C2960X-UNIVERSALK9-M), Version 15.2(7)E3",
        "Cisco IOS XE Software, Version 16.12.04",
        "Cisco IOS XE Software, Version 17.3.3",
    ],
    "router": [
        "Cisco IOS Software, ISR Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 15.6(3)M7",
        "Cisco IOS XE Software, Version 17.6.1a",
        "Cisco IOS Software, Version 15.2(4)M11",
    ],
    "firewall": [
        "Cisco Adaptive Security Appliance Software, Version 9.14(3)",
        "Cisco Firepower Threat Defense, Version 7.0.1",
    ],
    "phone": [
        "SCCP Phone Firmware, Version 11.0(1)",
        "SIP Phone Firmware, Version 14.0(1)",
    ],
    "ap": [
        "Cisco AP Software, Version 17.3.3",
        "Cisco AP Software, Version 8.10.142.0",
    ],
    "default": ["Cisco IOS Software, Version 15.2(4)M1"],
}


def get_capabilities_for_device_type(device_type: str) -> int:
    """Get CDP capabilities bitmask for device type.

    Args:
        device_type: Device type string

    Returns:
        Capabilities bitmask
    """
    device_type_lower = device_type.lower()

    if "router" in device_type_lower:
        return CDPCapability.ROUTER | CDPCapability.SWITCH
    elif "switch" in device_type_lower:
        return CDPCapability.SWITCH | CDPCapability.IGMP_CAPABLE
    elif "firewall" in device_type_lower or "asa" in device_type_lower:
        return CDPCapability.ROUTER
    elif "phone" in device_type_lower:
        return CDPCapability.HOST | CDPCapability.VOIP_PHONE
    elif "ap" in device_type_lower or "wireless" in device_type_lower:
        return CDPCapability.TRANSPARENT_BRIDGE | CDPCapability.SWITCH
    elif "host" in device_type_lower or "server" in device_type_lower:
        return CDPCapability.HOST
    else:
        return CDPCapability.SWITCH


def get_platform_for_device(device_type: str, model: str | None = None) -> str:
    """Get Cisco platform string for device.

    Args:
        device_type: Device type string
        model: Optional model name override

    Returns:
        Platform string
    """
    if model:
        return model

    device_type_lower = device_type.lower()

    for key in ["switch", "router", "firewall", "phone", "ap"]:
        if key in device_type_lower:
            return random.choice(CISCO_PLATFORMS[key])

    return random.choice(CISCO_PLATFORMS["default"])


def get_ios_version_for_device(device_type: str) -> str:
    """Get Cisco IOS version string for device type.

    Args:
        device_type: Device type string

    Returns:
        IOS version string
    """
    device_type_lower = device_type.lower()

    for key in ["switch", "router", "firewall", "phone", "ap"]:
        if key in device_type_lower:
            return random.choice(CISCO_IOS_VERSIONS[key])

    return random.choice(CISCO_IOS_VERSIONS["default"])


@register_engine(ProtocolType.CDP)
class CDPEngine(ProtocolEngine):
    """Protocol engine for CDP (Cisco Discovery Protocol).

    CDP is a one-way broadcast protocol - devices send advertisements
    periodically without expecting responses. This engine generates
    periodic CDP advertisement frames.
    """

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: CDPConversationState,
    ) -> list[PacketEvent]:
        """Generate initial CDP advertisement.

        CDP devices typically send an advertisement immediately upon
        link-up, then continue at regular intervals.

        Args:
            flow: Flow context with device information
            state: CDP conversation state

        Returns:
            List of PacketEvent containing initial CDP advertisement
        """
        events = []
        current_time = 0.0

        # Get source device info
        src_device = flow.source
        config = flow.config

        # Build CDP configuration from device context
        cdp_config = self._build_cdp_config(src_device, config)

        # Generate initial advertisement
        cdp_frame = build_cdp_advertisement(
            src_mac=src_device.mac_address,
            src_ip=src_device.ip_address,
            device_config=cdp_config,
        )

        events.append(
            PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=cdp_frame,
                direction="broadcast",
                metadata={
                    "protocol": "cdp",
                    "message_type": "advertisement",
                    "device_id": cdp_config.get("device_id", ""),
                    "frame_number": state.frame_count,
                },
            )
        )

        # Update state
        state.frame_count = 1
        state.last_tx_time_ms = current_time
        state.state_name = "advertising"

        logger.debug(
            f"CDP startup: device_id={cdp_config.get('device_id')}, "
            f"platform={cdp_config.get('platform')}"
        )

        return events

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: CDPConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate periodic CDP advertisement.

        CDP sends advertisements at regular intervals (default 60 seconds).
        This method is called to generate each periodic advertisement.

        Args:
            flow: Flow context with device information
            state: CDP conversation state
            current_time_ms: Current simulation time

        Returns:
            List of PacketEvent containing CDP advertisement
        """
        events = []

        # Check if it's time for another advertisement
        interval_ms = state.tx_interval * 1000
        time_since_last = current_time_ms - state.last_tx_time_ms

        if time_since_last < interval_ms:
            # Not time for another advertisement yet
            return events

        # Get source device info
        src_device = flow.source
        config = flow.config

        # Build CDP configuration
        cdp_config = self._build_cdp_config(src_device, config)

        # Add jitter to timing (±5% of interval)
        jitter_ms = random.uniform(-interval_ms * 0.05, interval_ms * 0.05)
        tx_time = current_time_ms + jitter_ms

        # Generate advertisement
        cdp_frame = build_cdp_advertisement(
            src_mac=src_device.mac_address,
            src_ip=src_device.ip_address,
            device_config=cdp_config,
        )

        events.append(
            PacketEvent(
                timestamp_ms=tx_time,
                flow_id=flow.flow_id,
                packet_bytes=cdp_frame,
                direction="broadcast",
                metadata={
                    "protocol": "cdp",
                    "message_type": "advertisement",
                    "device_id": cdp_config.get("device_id", ""),
                    "frame_number": state.frame_count,
                },
            )
        )

        # Update state
        state.frame_count += 1
        state.last_tx_time_ms = tx_time

        return events

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: CDPConversationState,
    ) -> list[PacketEvent]:
        """Generate shutdown sequence.

        CDP doesn't have a formal shutdown - devices simply stop sending
        advertisements and neighbors time out after the hold time expires.

        Args:
            flow: Flow context
            state: CDP conversation state

        Returns:
            Empty list (no shutdown packets)
        """
        # CDP has no shutdown packets - devices just stop advertising
        # and neighbors remove entries after TTL expires
        state.state_name = "stopped"
        return []

    def _build_cdp_config(
        self,
        device: DeviceContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Build CDP configuration from device context.

        Args:
            device: Device context with fingerprint info
            config: Flow configuration

        Returns:
            CDP configuration dictionary
        """
        # Extract from flow config or generate defaults
        device_type = config.get("device_type", "switch")
        device_name = device.device_name or config.get("device_name")

        # Generate device ID
        if device_name:
            device_id = device_name
        else:
            # Use hostname from fingerprint or generate from MAC
            device_id = device.vendor_fingerprint.get(
                "hostname", f"Device-{device.mac_address[-8:].replace(':', '')}"
            )

        # Get port ID
        port_id = config.get("port_id", "GigabitEthernet0/1")

        # Get capabilities
        capabilities = config.get("capabilities")
        if capabilities is None:
            capabilities = get_capabilities_for_device_type(device_type)

        # Get platform
        platform = config.get("platform")
        if platform is None:
            model = device.model or device.vendor_fingerprint.get("model")
            platform = get_platform_for_device(device_type, model)

        # Get software version
        software_version = config.get("software_version")
        if software_version is None:
            fw = device.firmware_version or device.vendor_fingerprint.get(
                "firmware_version"
            )
            if fw:
                software_version = f"Cisco IOS Software, Version {fw}"
            else:
                software_version = get_ios_version_for_device(device_type)

        # Optional fields
        native_vlan = config.get("native_vlan", 1)
        vtp_domain = config.get("vtp_domain")
        full_duplex = config.get("full_duplex", True)
        management_ip = config.get("management_ip", device.ip_address)

        return {
            "device_id": device_id,
            "port_id": port_id,
            "capabilities": capabilities,
            "platform": platform,
            "software_version": software_version,
            "native_vlan": native_vlan,
            "vtp_domain": vtp_domain,
            "full_duplex": full_duplex,
            "management_ip": management_ip,
        }

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate CDP configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate optional fields if present
        if "native_vlan" in config:
            vlan = config["native_vlan"]
            if not isinstance(vlan, int) or vlan < 1 or vlan > 4094:
                errors.append("native_vlan must be an integer between 1 and 4094")

        if "tx_interval" in config:
            interval = config["tx_interval"]
            if not isinstance(interval, (int, float)) or interval < 5 or interval > 254:
                errors.append("tx_interval must be between 5 and 254 seconds")

        if "ttl" in config:
            ttl = config["ttl"]
            if not isinstance(ttl, int) or ttl < 10 or ttl > 255:
                errors.append("ttl must be between 10 and 255 seconds")

        if "capabilities" in config:
            caps = config["capabilities"]
            if not isinstance(caps, int) or caps < 0 or caps > 0xFF:
                errors.append("capabilities must be a valid bitmask (0-255)")

        return errors

    def create_state(self, flow_id: str, config: dict[str, Any]) -> CDPConversationState:
        """Create CDP conversation state.

        Args:
            flow_id: Flow identifier
            config: Flow configuration

        Returns:
            Initialized CDPConversationState
        """
        tx_interval = config.get("tx_interval", CDP_DEFAULT_INTERVAL)
        ttl = config.get("ttl", CDP_DEFAULT_TTL)

        return CDPConversationState(
            flow_id=flow_id,
            state_name="init",
            tx_interval=tx_interval,
            ttl=ttl,
        )
