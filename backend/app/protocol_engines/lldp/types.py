"""LLDP (Link Layer Discovery Protocol) types and constants.

LLDP (IEEE 802.1AB) is a Layer 2 protocol used by network devices to
advertise their identity, capabilities, and neighbors on a local network.

Key characteristics:
- Layer 2 only (no IP required)
- EtherType: 0x88CC
- Multicast destination: 01:80:C2:00:00:0E
- TLV-based format
- Default 30-second transmission interval
"""

from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Any


# =============================================================================
# LLDP Frame Constants
# =============================================================================

# EtherType for LLDP
LLDP_ETHERTYPE = 0x88CC

# LLDP Multicast Destination MACs
LLDP_MULTICAST_MAC = "01:80:C2:00:00:0E"  # Nearest bridge (standard)
LLDP_MULTICAST_MAC_NON_TPMR = "01:80:C2:00:00:03"  # Nearest non-TPMR bridge
LLDP_MULTICAST_MAC_CUSTOMER = "01:80:C2:00:00:00"  # Nearest customer bridge


# =============================================================================
# Timing Parameters
# =============================================================================

DEFAULT_TX_INTERVAL = 30  # seconds
DEFAULT_TX_HOLD_MULTIPLIER = 4  # TTL = interval * multiplier
DEFAULT_REINIT_DELAY = 2  # seconds
DEFAULT_TX_DELAY = 2  # seconds

# Default TTL: 30 * 4 = 120 seconds
DEFAULT_TTL = DEFAULT_TX_INTERVAL * DEFAULT_TX_HOLD_MULTIPLIER


# =============================================================================
# TLV Types
# =============================================================================

class LLDPTLVType(IntEnum):
    """LLDP TLV type codes (IEEE 802.1AB)."""
    END_OF_LLDPDU = 0  # End of LLDPDU marker
    CHASSIS_ID = 1  # Chassis identifier
    PORT_ID = 2  # Port identifier
    TTL = 3  # Time to live
    PORT_DESCRIPTION = 4  # Port description
    SYSTEM_NAME = 5  # System name (hostname)
    SYSTEM_DESCRIPTION = 6  # System description
    SYSTEM_CAPABILITIES = 7  # System capabilities
    MANAGEMENT_ADDRESS = 8  # Management address
    # Types 9-126 are reserved
    ORG_SPECIFIC = 127  # Organizationally specific


# =============================================================================
# Chassis ID Subtypes
# =============================================================================

class ChassisIDSubtype(IntEnum):
    """Chassis ID TLV subtypes."""
    RESERVED = 0
    CHASSIS_COMPONENT = 1  # EntPhysicalAlias
    INTERFACE_ALIAS = 2  # IfAlias
    PORT_COMPONENT = 3  # EntPhysicalAlias (port)
    MAC_ADDRESS = 4  # MAC address (most common)
    NETWORK_ADDRESS = 5  # AFI + address
    INTERFACE_NAME = 6  # IfName
    LOCALLY_ASSIGNED = 7  # Local value


# =============================================================================
# Port ID Subtypes
# =============================================================================

class PortIDSubtype(IntEnum):
    """Port ID TLV subtypes."""
    RESERVED = 0
    INTERFACE_ALIAS = 1  # IfAlias
    PORT_COMPONENT = 2  # EntPhysicalAlias
    MAC_ADDRESS = 3  # MAC address
    NETWORK_ADDRESS = 4  # AFI + address
    INTERFACE_NAME = 5  # IfName (most common for switches)
    AGENT_CIRCUIT_ID = 6  # Agent circuit ID
    LOCALLY_ASSIGNED = 7  # Local value


# =============================================================================
# System Capabilities
# =============================================================================

class SystemCapability(IntEnum):
    """System capabilities bitmap values."""
    OTHER = 0x0001
    REPEATER = 0x0002
    BRIDGE = 0x0004
    WLAN_ACCESS_POINT = 0x0008
    ROUTER = 0x0010
    TELEPHONE = 0x0020
    DOCSIS_CABLE_DEVICE = 0x0040
    STATION_ONLY = 0x0080
    C_VLAN_COMPONENT = 0x0100
    S_VLAN_COMPONENT = 0x0200
    TWO_PORT_MAC_RELAY = 0x0400


# =============================================================================
# Address Family Identifiers (AFI)
# =============================================================================

class AddressFamily(IntEnum):
    """IANA Address Family Identifiers for Management Address TLV."""
    IPV4 = 1
    IPV6 = 2
    NSAP = 3
    HDLC = 4
    BBN_1822 = 5
    IEEE_802 = 6  # MAC address
    E163 = 7
    E164 = 8
    F69 = 9
    X121 = 10
    IPX = 11
    APPLETALK = 12
    DECNET_IV = 13
    BANYAN_VINES = 14
    E164_NSAP = 15


# =============================================================================
# Interface Numbering Subtypes
# =============================================================================

class InterfaceNumberingSubtype(IntEnum):
    """Interface numbering subtypes for Management Address TLV."""
    UNKNOWN = 1
    IF_INDEX = 2  # SNMP ifIndex
    SYSTEM_PORT_NUMBER = 3


# =============================================================================
# Organizationally Unique Identifiers (OUI)
# =============================================================================

# Standard OUIs for organizational TLVs
OUI_IEEE_802_1 = bytes([0x00, 0x80, 0xC2])  # IEEE 802.1
OUI_IEEE_802_3 = bytes([0x00, 0x12, 0x0F])  # IEEE 802.3
OUI_LLDP_MED = bytes([0x00, 0x12, 0xBB])  # TIA LLDP-MED
OUI_PROFINET = bytes([0x00, 0x0E, 0xCF])  # PROFIBUS/PROFINET International
OUI_CISCO = bytes([0x00, 0x01, 0x42])  # Cisco Systems


# =============================================================================
# IEEE 802.1 Subtypes
# =============================================================================

class IEEE8021Subtype(IntEnum):
    """IEEE 802.1 organizationally specific TLV subtypes."""
    PORT_VLAN_ID = 1
    PORT_PROTOCOL_VLAN_ID = 2
    VLAN_NAME = 3
    PROTOCOL_IDENTITY = 4
    VID_USAGE_DIGEST = 5
    MANAGEMENT_VID = 6
    LINK_AGGREGATION = 7
    CONGESTION_NOTIFICATION = 8


# =============================================================================
# IEEE 802.3 Subtypes
# =============================================================================

class IEEE8023Subtype(IntEnum):
    """IEEE 802.3 organizationally specific TLV subtypes."""
    MAC_PHY_CONFIG = 1
    POWER_VIA_MDI = 2
    LINK_AGGREGATION = 3
    MAX_FRAME_SIZE = 4
    ENERGY_EFFICIENT_ETHERNET = 5


# Autonegotiation capability bits
AUTONEG_SUPPORT = 0x01
AUTONEG_ENABLED = 0x02

# PMD Autonegotiation capability bits
class PMDCapability(IntEnum):
    """PHY Medium Dependent autonegotiation capabilities."""
    HD_10BASE_T = 0x0001
    FD_10BASE_T = 0x0002
    HD_100BASE_TX = 0x0004
    FD_100BASE_TX = 0x0008
    HD_100BASE_T4 = 0x0010
    HD_1000BASE_X = 0x0020
    FD_1000BASE_X = 0x0040
    HD_1000BASE_T = 0x0080
    FD_1000BASE_T = 0x0100


# Operational MAU Types
class MAUType(IntEnum):
    """Operational MAU (Media Attachment Unit) types."""
    UNKNOWN = 0
    AUI = 1
    HD_10BASE_5 = 2
    FD_10BASE_5 = 3
    FD_10BASE_FB = 4
    HD_10BASE_FP = 5
    HD_10BASE_2 = 6
    FD_10BASE_2 = 7
    HD_10BASE_T = 10
    FD_10BASE_T = 11
    HD_100BASE_T4 = 14
    HD_100BASE_TX = 15
    FD_100BASE_TX = 16
    HD_100BASE_FX = 17
    FD_100BASE_FX = 18
    HD_1000BASE_X = 21
    FD_1000BASE_X = 22
    HD_1000BASE_T = 29
    FD_1000BASE_T = 30
    FD_10GBASE_X = 31
    FD_10GBASE_R = 32
    FD_10GBASE_W = 33


# =============================================================================
# LLDP-MED Subtypes
# =============================================================================

class LLDPMEDSubtype(IntEnum):
    """LLDP-MED (Media Endpoint Discovery) TLV subtypes."""
    CAPABILITIES = 1
    NETWORK_POLICY = 2
    LOCATION_ID = 3
    EXTENDED_POWER_VIA_MDI = 4
    INVENTORY_HARDWARE_REV = 5
    INVENTORY_FIRMWARE_REV = 6
    INVENTORY_SOFTWARE_REV = 7
    INVENTORY_SERIAL_NUMBER = 8
    INVENTORY_MANUFACTURER = 9
    INVENTORY_MODEL_NAME = 10
    INVENTORY_ASSET_ID = 11


class LLDPMEDDeviceType(IntEnum):
    """LLDP-MED device types."""
    NOT_DEFINED = 0
    ENDPOINT_CLASS_I = 1  # Generic endpoint
    ENDPOINT_CLASS_II = 2  # Media endpoint
    ENDPOINT_CLASS_III = 3  # Communication device endpoint
    NETWORK_CONNECTIVITY = 4  # Network infrastructure


class LLDPMEDCapability(IntEnum):
    """LLDP-MED capability bits."""
    CAPABILITIES = 0x0001
    NETWORK_POLICY = 0x0002
    LOCATION_ID = 0x0004
    EXTENDED_PSE = 0x0008
    EXTENDED_PD = 0x0010
    INVENTORY = 0x0020


# =============================================================================
# PROFINET Subtypes
# =============================================================================

class ProfinetSubtype(IntEnum):
    """PROFINET organizationally specific TLV subtypes."""
    MEASURED_DELAY = 1
    PORT_STATUS = 2
    ALIAS = 3
    MRP_PORT_STATUS = 4
    CHASSIS_MAC = 5
    PTCP_STATUS = 6


# =============================================================================
# Device Types for OT Networks
# =============================================================================

class LLDPDeviceType(str, Enum):
    """Common OT device types for LLDP simulation."""
    SWITCH = "switch"
    ROUTER = "router"
    PLC = "plc"
    HMI = "hmi"
    IO_DEVICE = "io_device"
    DRIVE = "drive"
    SENSOR = "sensor"
    WORKSTATION = "workstation"
    SERVER = "server"


# =============================================================================
# Common Industrial Device Profiles
# =============================================================================

INDUSTRIAL_DEVICE_PROFILES = {
    # Cisco Industrial Ethernet
    "CISCO_IE_4010": {
        "vendor": "Cisco",
        "model": "IE-4010-16S12P",
        "description": "Cisco IOS Software, IE4010 Software, Version 15.2(7)E",
        "capabilities": SystemCapability.BRIDGE | SystemCapability.ROUTER,
        "device_type": LLDPDeviceType.SWITCH,
    },
    "CISCO_IE_3400": {
        "vendor": "Cisco",
        "model": "IE-3400-8T2S",
        "description": "Cisco IOS XE Software, Catalyst IE3400 Series, Version 17.3.3",
        "capabilities": SystemCapability.BRIDGE | SystemCapability.ROUTER,
        "device_type": LLDPDeviceType.SWITCH,
    },

    # Siemens SCALANCE
    "SIEMENS_SCALANCE_X208": {
        "vendor": "Siemens",
        "model": "SCALANCE X208",
        "description": "SIEMENS SCALANCE X-200 Switch; HW:V1.0; FW:V5.4.5",
        "capabilities": SystemCapability.BRIDGE,
        "device_type": LLDPDeviceType.SWITCH,
    },
    "SIEMENS_SCALANCE_XC216": {
        "vendor": "Siemens",
        "model": "SCALANCE XC216-4C",
        "description": "SIEMENS SCALANCE XC-200 Switch; HW:V2.0; FW:V5.5.2",
        "capabilities": SystemCapability.BRIDGE,
        "device_type": LLDPDeviceType.SWITCH,
    },

    # Siemens PLCs
    "SIEMENS_S7_1500": {
        "vendor": "Siemens",
        "model": "CPU 1516-3 PN/DP",
        "description": "SIEMENS SIMATIC S7-1500, CPU 1516-3 PN/DP, 6ES7516-3AN01-0AB0, HW:1, FW:V2.8.3",
        "capabilities": SystemCapability.STATION_ONLY,
        "device_type": LLDPDeviceType.PLC,
    },
    "SIEMENS_S7_1200": {
        "vendor": "Siemens",
        "model": "CPU 1214C DC/DC/DC",
        "description": "SIEMENS SIMATIC S7-1200, CPU 1214C, 6ES7214-1AG40-0XB0, FW:V4.5",
        "capabilities": SystemCapability.STATION_ONLY,
        "device_type": LLDPDeviceType.PLC,
    },

    # Rockwell Automation
    "ROCKWELL_STRATIX_5700": {
        "vendor": "Rockwell Automation",
        "model": "Stratix 5700",
        "description": "Stratix 5700 Industrial Ethernet Switch, Rev. 15.2(6)E",
        "capabilities": SystemCapability.BRIDGE,
        "device_type": LLDPDeviceType.SWITCH,
    },
    "ROCKWELL_EN2T": {
        "vendor": "Rockwell Automation",
        "model": "1756-EN2T",
        "description": "1756-EN2T/C EtherNet/IP Module, Rev. 11.001",
        "capabilities": SystemCapability.STATION_ONLY,
        "device_type": LLDPDeviceType.PLC,
    },

    # Hirschmann
    "HIRSCHMANN_RSP35": {
        "vendor": "Hirschmann",
        "model": "RSP35",
        "description": "Hirschmann RSP35 Industrial Ethernet Switch, HiOS-3S-09.0.00",
        "capabilities": SystemCapability.BRIDGE,
        "device_type": LLDPDeviceType.SWITCH,
    },

    # Phoenix Contact
    "PHOENIX_FL_SWITCH": {
        "vendor": "Phoenix Contact",
        "model": "FL SWITCH 2008",
        "description": "Phoenix Contact FL SWITCH 2008 Ethernet Switch, FW:V1.90",
        "capabilities": SystemCapability.BRIDGE,
        "device_type": LLDPDeviceType.SWITCH,
    },

    # Schneider Electric
    "SCHNEIDER_M580": {
        "vendor": "Schneider Electric",
        "model": "M580",
        "description": "Modicon M580 ePAC, BME P58 4040, FW:V3.20",
        "capabilities": SystemCapability.STATION_ONLY,
        "device_type": LLDPDeviceType.PLC,
    },

    # Generic HMI
    "SIEMENS_HMI_TP1500": {
        "vendor": "Siemens",
        "model": "SIMATIC HMI TP1500 Comfort",
        "description": "SIEMENS SIMATIC HMI TP1500 Comfort Panel, FW:V16.0.0.0",
        "capabilities": SystemCapability.STATION_ONLY,
        "device_type": LLDPDeviceType.HMI,
    },
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class LLDPIdentity:
    """LLDP device identity information."""
    chassis_id_subtype: ChassisIDSubtype = ChassisIDSubtype.MAC_ADDRESS
    chassis_id: str = ""  # MAC, hostname, or other ID
    port_id_subtype: PortIDSubtype = PortIDSubtype.INTERFACE_NAME
    port_id: str = "eth0"  # Interface name or other ID
    ttl: int = DEFAULT_TTL

    # Optional basic TLVs
    port_description: str = ""
    system_name: str = ""
    system_description: str = ""
    capabilities: int = 0
    enabled_capabilities: int = 0
    management_address: str = ""
    management_address_afi: AddressFamily = AddressFamily.IPV4

    # IEEE 802.1 TLVs
    vlan_id: int | None = None
    vlan_name: str = ""

    # IEEE 802.3 TLVs
    max_frame_size: int = 1522
    mau_type: MAUType = MAUType.FD_1000BASE_T

    # LLDP-MED inventory
    hardware_revision: str = ""
    firmware_revision: str = ""
    software_revision: str = ""
    serial_number: str = ""
    manufacturer: str = ""
    model_name: str = ""
    asset_id: str = ""

    # PROFINET-specific
    profinet_delay_values: bool = False
    rx_delay_local: int = 0
    tx_delay_local: int = 0


@dataclass
class LLDPConfig:
    """Configuration for LLDP communication."""
    tx_interval: int = DEFAULT_TX_INTERVAL  # Transmission interval (seconds)
    tx_hold_multiplier: int = DEFAULT_TX_HOLD_MULTIPLIER  # TTL multiplier
    reinit_delay: int = DEFAULT_REINIT_DELAY  # Reinit delay (seconds)

    # TLV options
    include_port_description: bool = True
    include_system_name: bool = True
    include_system_description: bool = True
    include_system_capabilities: bool = True
    include_management_address: bool = True

    # Organizational TLVs
    include_ieee_802_1: bool = True  # VLAN info
    include_ieee_802_3: bool = True  # PHY info
    include_lldp_med: bool = False  # LLDP-MED inventory
    include_profinet: bool = False  # PROFINET extensions

    def calculate_ttl(self) -> int:
        """Calculate TTL from interval and multiplier."""
        return min(self.tx_interval * self.tx_hold_multiplier, 65535)


# Note: LLDPConversationState is defined in app.protocol_engines.types
# to be consistent with other protocol conversation states
