# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""LLDP packet builders.

Builds LLDP (IEEE 802.1AB) frames with TLV (Type-Length-Value) encoding.
LLDP is a Layer 2 protocol - no IP headers required.
"""

import struct

from app.protocol_engines.lldp.types import (
    LLDP_ETHERTYPE,
    LLDP_MULTICAST_MAC,
    LLDPTLVType,
    ChassisIDSubtype,
    PortIDSubtype,
    AddressFamily,
    InterfaceNumberingSubtype,
    OUI_IEEE_802_1,
    OUI_IEEE_802_3,
    OUI_LLDP_MED,
    OUI_PROFINET,
    IEEE8021Subtype,
    IEEE8023Subtype,
    LLDPMEDSubtype,
    LLDPMEDDeviceType,
    LLDPMEDCapability,
    ProfinetSubtype,
    MAUType,
    PMDCapability,
    AUTONEG_SUPPORT,
    AUTONEG_ENABLED,
    LLDPIdentity,
)


# =============================================================================
# Utility Functions
# =============================================================================

def mac_to_bytes(mac: str) -> bytes:
    """Convert MAC address string to bytes."""
    return bytes.fromhex(mac.replace(":", "").replace("-", ""))


def ip_to_bytes(ip: str) -> bytes:
    """Convert IPv4 address string to bytes."""
    return bytes(int(x) for x in ip.split("."))


# =============================================================================
# Ethernet Frame Building
# =============================================================================

def build_ethernet_header(
    src_mac: str,
    dst_mac: str = LLDP_MULTICAST_MAC,
) -> bytes:
    """Build Ethernet header for LLDP frame.

    Args:
        src_mac: Source MAC address (device sending LLDP)
        dst_mac: Destination MAC (default: LLDP multicast)

    Returns:
        14-byte Ethernet header
    """
    dst = mac_to_bytes(dst_mac)
    src = mac_to_bytes(src_mac)
    return dst + src + struct.pack(">H", LLDP_ETHERTYPE)


# =============================================================================
# TLV Building
# =============================================================================

def build_tlv(tlv_type: int, value: bytes) -> bytes:
    """Build a single LLDP TLV.

    TLV format:
    - Type: 7 bits (0-127)
    - Length: 9 bits (0-511)
    - Value: 0-511 bytes

    Args:
        tlv_type: TLV type code (0-127)
        value: TLV value (max 511 bytes)

    Returns:
        Complete TLV bytes
    """
    length = len(value)
    if length > 511:
        raise ValueError(f"TLV value too long: {length} > 511 bytes")

    # Pack type (7 bits) and length (9 bits) into 2 bytes
    # Type is in upper 7 bits, length in lower 9 bits
    type_length = (tlv_type << 9) | length
    return struct.pack(">H", type_length) + value


# =============================================================================
# Mandatory TLVs
# =============================================================================

def build_chassis_id_tlv(subtype: ChassisIDSubtype, value: bytes) -> bytes:
    """Build Chassis ID TLV (Type 1).

    Args:
        subtype: Chassis ID subtype
        value: Chassis ID value (depends on subtype)

    Returns:
        Complete Chassis ID TLV
    """
    return build_tlv(LLDPTLVType.CHASSIS_ID, bytes([subtype]) + value)


def build_chassis_id_mac(mac_address: str) -> bytes:
    """Build Chassis ID TLV with MAC address subtype.

    Args:
        mac_address: MAC address string (e.g., "00:1B:1B:01:02:03")

    Returns:
        Complete Chassis ID TLV
    """
    return build_chassis_id_tlv(
        ChassisIDSubtype.MAC_ADDRESS,
        mac_to_bytes(mac_address)
    )


def build_chassis_id_locally_assigned(name: str) -> bytes:
    """Build Chassis ID TLV with locally assigned subtype.

    Args:
        name: Locally assigned chassis name

    Returns:
        Complete Chassis ID TLV
    """
    return build_chassis_id_tlv(
        ChassisIDSubtype.LOCALLY_ASSIGNED,
        name.encode("utf-8")[:255]
    )


def build_port_id_tlv(subtype: PortIDSubtype, value: bytes) -> bytes:
    """Build Port ID TLV (Type 2).

    Args:
        subtype: Port ID subtype
        value: Port ID value (depends on subtype)

    Returns:
        Complete Port ID TLV
    """
    return build_tlv(LLDPTLVType.PORT_ID, bytes([subtype]) + value)


def build_port_id_interface_name(name: str) -> bytes:
    """Build Port ID TLV with interface name.

    Args:
        name: Interface name (e.g., "GigabitEthernet0/1", "eth0")

    Returns:
        Complete Port ID TLV
    """
    return build_port_id_tlv(
        PortIDSubtype.INTERFACE_NAME,
        name.encode("utf-8")[:255]
    )


def build_port_id_mac(mac_address: str) -> bytes:
    """Build Port ID TLV with MAC address.

    Args:
        mac_address: MAC address string

    Returns:
        Complete Port ID TLV
    """
    return build_port_id_tlv(
        PortIDSubtype.MAC_ADDRESS,
        mac_to_bytes(mac_address)
    )


def build_port_id_locally_assigned(port_id: str) -> bytes:
    """Build Port ID TLV with locally assigned value.

    Args:
        port_id: Port identifier string

    Returns:
        Complete Port ID TLV
    """
    return build_port_id_tlv(
        PortIDSubtype.LOCALLY_ASSIGNED,
        port_id.encode("utf-8")[:255]
    )


def build_ttl_tlv(ttl_seconds: int) -> bytes:
    """Build Time To Live TLV (Type 3).

    Args:
        ttl_seconds: TTL in seconds (0-65535)

    Returns:
        Complete TTL TLV
    """
    return build_tlv(LLDPTLVType.TTL, struct.pack(">H", ttl_seconds & 0xFFFF))


def build_end_tlv() -> bytes:
    """Build End of LLDPDU TLV (Type 0).

    Returns:
        2-byte End TLV (type=0, length=0)
    """
    return struct.pack(">H", 0x0000)


# =============================================================================
# Optional Basic Management TLVs
# =============================================================================

def build_port_description_tlv(description: str) -> bytes:
    """Build Port Description TLV (Type 4).

    Args:
        description: Port description string

    Returns:
        Complete Port Description TLV
    """
    return build_tlv(
        LLDPTLVType.PORT_DESCRIPTION,
        description.encode("utf-8")[:255]
    )


def build_system_name_tlv(name: str) -> bytes:
    """Build System Name TLV (Type 5).

    Args:
        name: System name (hostname)

    Returns:
        Complete System Name TLV
    """
    return build_tlv(
        LLDPTLVType.SYSTEM_NAME,
        name.encode("utf-8")[:255]
    )


def build_system_description_tlv(description: str) -> bytes:
    """Build System Description TLV (Type 6).

    Args:
        description: System description (vendor, model, version info)

    Returns:
        Complete System Description TLV
    """
    return build_tlv(
        LLDPTLVType.SYSTEM_DESCRIPTION,
        description.encode("utf-8")[:255]
    )


def build_system_capabilities_tlv(
    capabilities: int,
    enabled: int | None = None,
) -> bytes:
    """Build System Capabilities TLV (Type 7).

    Args:
        capabilities: Bitmap of supported capabilities
        enabled: Bitmap of enabled capabilities (defaults to same as supported)

    Returns:
        Complete System Capabilities TLV
    """
    if enabled is None:
        enabled = capabilities

    return build_tlv(
        LLDPTLVType.SYSTEM_CAPABILITIES,
        struct.pack(">HH", capabilities & 0xFFFF, enabled & 0xFFFF)
    )


def build_management_address_tlv(
    address: str,
    afi: AddressFamily = AddressFamily.IPV4,
    interface_subtype: InterfaceNumberingSubtype = InterfaceNumberingSubtype.IF_INDEX,
    interface_number: int = 0,
    oid: bytes = b"",
) -> bytes:
    """Build Management Address TLV (Type 8).

    Args:
        address: Management address (IP or other)
        afi: Address family identifier
        interface_subtype: Interface numbering subtype
        interface_number: Interface number (e.g., SNMP ifIndex)
        oid: Object identifier (optional)

    Returns:
        Complete Management Address TLV
    """
    # Encode address based on AFI
    if afi == AddressFamily.IPV4:
        addr_bytes = ip_to_bytes(address)
    elif afi == AddressFamily.IPV6:
        import ipaddress
        addr_bytes = ipaddress.IPv6Address(address).packed
    elif afi == AddressFamily.IEEE_802:
        addr_bytes = mac_to_bytes(address)
    else:
        addr_bytes = address.encode("utf-8")

    # Management address string length includes AFI byte
    addr_string_len = 1 + len(addr_bytes)

    # Build TLV value
    value = struct.pack("BB", addr_string_len, afi)
    value += addr_bytes
    value += struct.pack(">BI", interface_subtype, interface_number)
    value += struct.pack("B", len(oid))
    value += oid

    return build_tlv(LLDPTLVType.MANAGEMENT_ADDRESS, value)


# =============================================================================
# Organizationally Specific TLVs (Type 127)
# =============================================================================

def build_org_specific_tlv(oui: bytes, subtype: int, data: bytes) -> bytes:
    """Build Organizationally Specific TLV (Type 127).

    Args:
        oui: 3-byte Organizationally Unique Identifier
        subtype: 1-byte organizationally defined subtype
        data: TLV data

    Returns:
        Complete Org Specific TLV
    """
    value = oui[:3] + bytes([subtype]) + data
    return build_tlv(LLDPTLVType.ORG_SPECIFIC, value)


# =============================================================================
# IEEE 802.1 TLVs
# =============================================================================

def build_port_vlan_id_tlv(vlan_id: int) -> bytes:
    """Build IEEE 802.1 Port VLAN ID TLV.

    Args:
        vlan_id: VLAN ID (1-4094)

    Returns:
        Complete Port VLAN ID TLV
    """
    return build_org_specific_tlv(
        OUI_IEEE_802_1,
        IEEE8021Subtype.PORT_VLAN_ID,
        struct.pack(">H", vlan_id & 0x0FFF)
    )


def build_vlan_name_tlv(vlan_id: int, vlan_name: str) -> bytes:
    """Build IEEE 802.1 VLAN Name TLV.

    Args:
        vlan_id: VLAN ID
        vlan_name: VLAN name (max 32 chars)

    Returns:
        Complete VLAN Name TLV
    """
    name_bytes = vlan_name.encode("utf-8")[:32]
    data = struct.pack(">HB", vlan_id & 0x0FFF, len(name_bytes)) + name_bytes
    return build_org_specific_tlv(OUI_IEEE_802_1, IEEE8021Subtype.VLAN_NAME, data)


# =============================================================================
# IEEE 802.3 TLVs
# =============================================================================

def build_mac_phy_config_tlv(
    autoneg_support: bool = True,
    autoneg_enabled: bool = True,
    pmd_autoneg_cap: int = (
        PMDCapability.FD_1000BASE_T |
        PMDCapability.FD_100BASE_TX |
        PMDCapability.FD_10BASE_T
    ),
    mau_type: MAUType = MAUType.FD_1000BASE_T,
) -> bytes:
    """Build IEEE 802.3 MAC/PHY Configuration/Status TLV.

    Args:
        autoneg_support: Auto-negotiation supported
        autoneg_enabled: Auto-negotiation enabled
        pmd_autoneg_cap: PMD auto-negotiation capabilities
        mau_type: Operational MAU type

    Returns:
        Complete MAC/PHY Config TLV
    """
    autoneg = 0
    if autoneg_support:
        autoneg |= AUTONEG_SUPPORT
    if autoneg_enabled:
        autoneg |= AUTONEG_ENABLED

    data = struct.pack(">BHH", autoneg, pmd_autoneg_cap, mau_type)
    return build_org_specific_tlv(OUI_IEEE_802_3, IEEE8023Subtype.MAC_PHY_CONFIG, data)


def build_max_frame_size_tlv(max_frame_size: int = 1522) -> bytes:
    """Build IEEE 802.3 Maximum Frame Size TLV.

    Args:
        max_frame_size: Maximum frame size in bytes

    Returns:
        Complete Max Frame Size TLV
    """
    return build_org_specific_tlv(
        OUI_IEEE_802_3,
        IEEE8023Subtype.MAX_FRAME_SIZE,
        struct.pack(">H", max_frame_size)
    )


def build_link_aggregation_tlv(
    aggregation_capability: int = 0x01,
    aggregation_status: int = 0x00,
    aggregated_port_id: int = 0,
) -> bytes:
    """Build IEEE 802.3 Link Aggregation TLV.

    Args:
        aggregation_capability: Aggregation capability (bit 0 = capable)
        aggregation_status: Aggregation status (bit 0 = aggregated)
        aggregated_port_id: Port ID of aggregated port

    Returns:
        Complete Link Aggregation TLV
    """
    data = struct.pack(">BBI", aggregation_capability, aggregation_status, aggregated_port_id)
    return build_org_specific_tlv(OUI_IEEE_802_3, IEEE8023Subtype.LINK_AGGREGATION, data)


# =============================================================================
# LLDP-MED TLVs
# =============================================================================

def build_lldp_med_capabilities_tlv(
    capabilities: int = (
        LLDPMEDCapability.CAPABILITIES |
        LLDPMEDCapability.INVENTORY
    ),
    device_type: LLDPMEDDeviceType = LLDPMEDDeviceType.NETWORK_CONNECTIVITY,
) -> bytes:
    """Build LLDP-MED Capabilities TLV.

    Args:
        capabilities: LLDP-MED capability bitmap
        device_type: LLDP-MED device type

    Returns:
        Complete LLDP-MED Capabilities TLV
    """
    data = struct.pack(">HB", capabilities, device_type)
    return build_org_specific_tlv(OUI_LLDP_MED, LLDPMEDSubtype.CAPABILITIES, data)


def build_lldp_med_inventory_tlv(subtype: LLDPMEDSubtype, value: str) -> bytes:
    """Build LLDP-MED Inventory TLV.

    Args:
        subtype: Inventory subtype (5-11)
        value: Inventory value (max 32 chars)

    Returns:
        Complete LLDP-MED Inventory TLV
    """
    return build_org_specific_tlv(
        OUI_LLDP_MED,
        subtype,
        value.encode("utf-8")[:32]
    )


def build_med_hardware_revision_tlv(revision: str) -> bytes:
    """Build LLDP-MED Hardware Revision TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_HARDWARE_REV, revision)


def build_med_firmware_revision_tlv(revision: str) -> bytes:
    """Build LLDP-MED Firmware Revision TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_FIRMWARE_REV, revision)


def build_med_software_revision_tlv(revision: str) -> bytes:
    """Build LLDP-MED Software Revision TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_SOFTWARE_REV, revision)


def build_med_serial_number_tlv(serial: str) -> bytes:
    """Build LLDP-MED Serial Number TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_SERIAL_NUMBER, serial)


def build_med_manufacturer_name_tlv(name: str) -> bytes:
    """Build LLDP-MED Manufacturer Name TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_MANUFACTURER, name)


def build_med_model_name_tlv(model: str) -> bytes:
    """Build LLDP-MED Model Name TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_MODEL_NAME, model)


def build_med_asset_id_tlv(asset_id: str) -> bytes:
    """Build LLDP-MED Asset ID TLV."""
    return build_lldp_med_inventory_tlv(LLDPMEDSubtype.INVENTORY_ASSET_ID, asset_id)


# =============================================================================
# PROFINET TLVs
# =============================================================================

def build_profinet_delay_tlv(
    rx_delay_local: int = 0,
    rx_delay_remote: int = 0,
    tx_delay_local: int = 0,
    tx_delay_remote: int = 0,
    cable_delay_local: int = 0,
) -> bytes:
    """Build PROFINET Measured Delay Values TLV.

    All values in nanoseconds. Used for IRT timing calculations.

    Args:
        rx_delay_local: Local RX delay (ns)
        rx_delay_remote: Remote RX delay (ns)
        tx_delay_local: Local TX delay (ns)
        tx_delay_remote: Remote TX delay (ns)
        cable_delay_local: Cable delay (ns)

    Returns:
        Complete PROFINET Delay TLV
    """
    data = struct.pack(
        ">IIIII",
        rx_delay_local,
        rx_delay_remote,
        tx_delay_local,
        tx_delay_remote,
        cable_delay_local
    )
    return build_org_specific_tlv(OUI_PROFINET, ProfinetSubtype.MEASURED_DELAY, data)


def build_profinet_port_status_tlv(
    rt_class2_status: int = 0,
    rt_class3_status: int = 0,
) -> bytes:
    """Build PROFINET Port Status TLV.

    Args:
        rt_class2_status: RT Class 2 port status
        rt_class3_status: RT Class 3 (IRT) port status

    Returns:
        Complete PROFINET Port Status TLV
    """
    data = struct.pack(">HH", rt_class2_status, rt_class3_status)
    return build_org_specific_tlv(OUI_PROFINET, ProfinetSubtype.PORT_STATUS, data)


def build_profinet_chassis_mac_tlv(mac_address: str) -> bytes:
    """Build PROFINET Chassis MAC TLV.

    Args:
        mac_address: Chassis MAC address

    Returns:
        Complete PROFINET Chassis MAC TLV
    """
    return build_org_specific_tlv(
        OUI_PROFINET,
        ProfinetSubtype.CHASSIS_MAC,
        mac_to_bytes(mac_address)
    )


# =============================================================================
# Complete LLDPDU Building
# =============================================================================

def build_lldpdu(
    src_mac: str,
    identity: LLDPIdentity,
    include_ieee_802_1: bool = True,
    include_ieee_802_3: bool = True,
    include_lldp_med: bool = False,
    include_profinet: bool = False,
) -> bytes:
    """Build a complete LLDP Data Unit (LLDPDU).

    Args:
        src_mac: Source MAC address
        identity: LLDP identity data
        include_ieee_802_1: Include IEEE 802.1 TLVs
        include_ieee_802_3: Include IEEE 802.3 TLVs
        include_lldp_med: Include LLDP-MED TLVs
        include_profinet: Include PROFINET TLVs

    Returns:
        Complete Ethernet frame bytes
    """
    tlvs = b""

    # === Mandatory TLVs ===

    # Chassis ID
    if identity.chassis_id_subtype == ChassisIDSubtype.MAC_ADDRESS:
        chassis_id = identity.chassis_id or src_mac
        tlvs += build_chassis_id_mac(chassis_id)
    else:
        tlvs += build_chassis_id_tlv(
            identity.chassis_id_subtype,
            identity.chassis_id.encode("utf-8")
        )

    # Port ID
    if identity.port_id_subtype == PortIDSubtype.INTERFACE_NAME:
        tlvs += build_port_id_interface_name(identity.port_id)
    elif identity.port_id_subtype == PortIDSubtype.MAC_ADDRESS:
        tlvs += build_port_id_mac(identity.port_id)
    else:
        tlvs += build_port_id_tlv(
            identity.port_id_subtype,
            identity.port_id.encode("utf-8")
        )

    # TTL
    tlvs += build_ttl_tlv(identity.ttl)

    # === Optional Basic Management TLVs ===

    if identity.port_description:
        tlvs += build_port_description_tlv(identity.port_description)

    if identity.system_name:
        tlvs += build_system_name_tlv(identity.system_name)

    if identity.system_description:
        tlvs += build_system_description_tlv(identity.system_description)

    if identity.capabilities:
        tlvs += build_system_capabilities_tlv(
            identity.capabilities,
            identity.enabled_capabilities or identity.capabilities
        )

    if identity.management_address:
        tlvs += build_management_address_tlv(
            identity.management_address,
            identity.management_address_afi
        )

    # === IEEE 802.1 TLVs ===

    if include_ieee_802_1:
        if identity.vlan_id is not None:
            tlvs += build_port_vlan_id_tlv(identity.vlan_id)
        if identity.vlan_name:
            tlvs += build_vlan_name_tlv(identity.vlan_id or 1, identity.vlan_name)

    # === IEEE 802.3 TLVs ===

    if include_ieee_802_3:
        tlvs += build_mac_phy_config_tlv(mau_type=identity.mau_type)
        tlvs += build_max_frame_size_tlv(identity.max_frame_size)

    # === LLDP-MED TLVs ===

    if include_lldp_med:
        caps = LLDPMEDCapability.CAPABILITIES
        if any([identity.hardware_revision, identity.firmware_revision,
                identity.serial_number, identity.manufacturer, identity.model_name]):
            caps |= LLDPMEDCapability.INVENTORY

        tlvs += build_lldp_med_capabilities_tlv(caps)

        if identity.hardware_revision:
            tlvs += build_med_hardware_revision_tlv(identity.hardware_revision)
        if identity.firmware_revision:
            tlvs += build_med_firmware_revision_tlv(identity.firmware_revision)
        if identity.software_revision:
            tlvs += build_med_software_revision_tlv(identity.software_revision)
        if identity.serial_number:
            tlvs += build_med_serial_number_tlv(identity.serial_number)
        if identity.manufacturer:
            tlvs += build_med_manufacturer_name_tlv(identity.manufacturer)
        if identity.model_name:
            tlvs += build_med_model_name_tlv(identity.model_name)
        if identity.asset_id:
            tlvs += build_med_asset_id_tlv(identity.asset_id)

    # === PROFINET TLVs ===

    if include_profinet:
        if identity.profinet_delay_values:
            tlvs += build_profinet_delay_tlv(
                rx_delay_local=identity.rx_delay_local,
                tx_delay_local=identity.tx_delay_local,
            )
        tlvs += build_profinet_port_status_tlv()

    # === End of LLDPDU ===
    tlvs += build_end_tlv()

    # Build complete frame
    return build_ethernet_header(src_mac) + tlvs


def build_shutdown_lldpdu(src_mac: str, port_id: str = "eth0") -> bytes:
    """Build LLDP shutdown frame (TTL=0).

    Sent when disabling LLDP or shutting down a port to trigger
    immediate deletion of neighbor entry.

    Args:
        src_mac: Source MAC address
        port_id: Port identifier

    Returns:
        Complete shutdown LLDPDU frame
    """
    identity = LLDPIdentity(
        chassis_id=src_mac,
        port_id=port_id,
        ttl=0,  # TTL=0 triggers immediate deletion
    )
    return build_lldpdu(
        src_mac,
        identity,
        include_ieee_802_1=False,
        include_ieee_802_3=False,
    )
