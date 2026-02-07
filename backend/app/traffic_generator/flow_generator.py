"""Smart Flow Generator for OT Traffic Simulation.

This module provides intelligent flow generation that ensures all devices
participate in network traffic based on their roles in the OT hierarchy.

Instead of simple round-robin flow creation, this generator:
1. Assigns roles to devices based on their type (controller, HMI, field device)
2. Creates realistic communication patterns based on role relationships
3. Ensures no devices are orphaned (all devices have at least one flow)
4. Supports multiple flow patterns (hierarchical, mesh, star)

OT Communication Hierarchy:
- SCADA/Historian: Polls controllers, receives alarms
- HMI: Monitors controllers, issues commands
- Controller (PLC/RTU): Controls field devices, reports to SCADA
- Field Device: Responds to controller queries
"""

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DeviceRole(str, Enum):
    """Device roles in OT communication hierarchy."""

    SCADA = "scada"  # SCADA server, historian, engineering workstation
    HMI = "hmi"  # Human-machine interface, operator workstation
    CONTROLLER = "controller"  # PLC, RTU, DCS controller
    FIELD_DEVICE = "field_device"  # I/O module, drive, sensor, actuator
    GATEWAY = "gateway"  # Protocol converter, network gateway
    HISTORIAN = "historian"  # Data historian server
    ENGINEERING = "engineering"  # Engineering workstation
    SAFETY = "safety"  # Safety controller, SIS


class FlowPattern(str, Enum):
    """Flow generation patterns."""

    HIERARCHICAL = "hierarchical"  # Strict hierarchy: SCADA -> Controller -> Field
    MESH = "mesh"  # All-to-all communication
    STAR = "star"  # Central node communicates with all others
    TREE = "tree"  # Tree structure with branching
    REALISTIC = "realistic"  # Role-based realistic OT traffic


# Role relationship definitions
# Key: initiating role, Value: list of roles that can be targets
ROLE_CONNECTIONS: dict[DeviceRole, list[DeviceRole]] = {
    DeviceRole.SCADA: [
        DeviceRole.CONTROLLER,
        DeviceRole.HMI,
        DeviceRole.GATEWAY,
        DeviceRole.HISTORIAN,
        DeviceRole.FIELD_DEVICE,  # ITS/BMS: TMC/BMS server directly polls field equipment
    ],
    DeviceRole.HMI: [
        DeviceRole.CONTROLLER,
        DeviceRole.SCADA,
    ],
    DeviceRole.CONTROLLER: [
        DeviceRole.FIELD_DEVICE,
        DeviceRole.CONTROLLER,  # Controller-to-controller for interlocks
        DeviceRole.GATEWAY,
    ],
    DeviceRole.FIELD_DEVICE: [],  # Responds only, doesn't initiate
    DeviceRole.GATEWAY: [
        DeviceRole.CONTROLLER,
        DeviceRole.FIELD_DEVICE,
    ],
    DeviceRole.HISTORIAN: [
        DeviceRole.CONTROLLER,
        DeviceRole.SCADA,
    ],
    DeviceRole.ENGINEERING: [
        DeviceRole.CONTROLLER,
        DeviceRole.HMI,
        DeviceRole.SCADA,
    ],
    DeviceRole.SAFETY: [
        DeviceRole.CONTROLLER,
        DeviceRole.FIELD_DEVICE,
    ],
}

# ---------------------------------------------------------------------------
# Vendor-aware protocol selection
# ---------------------------------------------------------------------------

# Preferred protocol by vendor for real-time I/O (CONTROLLER→FIELD_DEVICE)
VENDOR_REALTIME_PROTOCOL: dict[str, str] = {
    "siemens": "profinet",
    "rockwell": "ethernet_ip",
    "allen-bradley": "ethernet_ip",
    "schneider": "modbus_tcp",
    "schneider electric": "modbus_tcp",
    "abb": "modbus_tcp",
    "ge": "modbus_tcp",
    "honeywell": "modbus_tcp",
    "johnson controls": "bacnet",
    "johnson_controls": "bacnet",
    "trane": "bacnet",
    "carrier": "bacnet",
    "automated logic": "bacnet",
    "automated_logic": "bacnet",
    "distech": "bacnet",
    "sel": "dnp3",
    "econolite": "snmp",
    "daktronics": "snmp",
    "wavetronix": "snmp",
}

# Preferred protocol by vendor for supervisory/HMI polling
VENDOR_SUPERVISORY_PROTOCOL: dict[str, str] = {
    "siemens": "s7comm_plus",
    "rockwell": "ethernet_ip",
    "allen-bradley": "ethernet_ip",
    "schneider": "modbus_tcp",
    "schneider electric": "modbus_tcp",
    "abb": "modbus_tcp",
    "ge": "opc_ua",
    "honeywell": "bacnet",
    "johnson controls": "bacnet",
    "johnson_controls": "bacnet",
    "trane": "bacnet",
    "carrier": "bacnet",
}

# ---------------------------------------------------------------------------
# Protocol × role timing (interval in milliseconds)
# Derived from 200+ real template flow definitions across 6 industry verticals
# ---------------------------------------------------------------------------
PROTOCOL_TIMING: dict[tuple[str, DeviceRole | None, DeviceRole | None], int] = {
    # PROFINET real-time (Siemens manufacturing)
    ("profinet", DeviceRole.CONTROLLER, DeviceRole.FIELD_DEVICE): 4,
    ("profinet", DeviceRole.CONTROLLER, DeviceRole.CONTROLLER): 32,
    ("profinet", DeviceRole.SAFETY, DeviceRole.CONTROLLER): 4,
    ("profinet", DeviceRole.SAFETY, DeviceRole.FIELD_DEVICE): 4,
    ("profinet", None, None): 8,
    # EtherNet/IP implicit messaging (Rockwell manufacturing)
    ("ethernet_ip", DeviceRole.CONTROLLER, DeviceRole.FIELD_DEVICE): 10,
    ("ethernet_ip", DeviceRole.CONTROLLER, DeviceRole.CONTROLLER): 20,
    ("ethernet_ip", DeviceRole.SAFETY, DeviceRole.CONTROLLER): 4,
    ("ethernet_ip", DeviceRole.SAFETY, DeviceRole.FIELD_DEVICE): 20,
    ("ethernet_ip", DeviceRole.HMI, DeviceRole.CONTROLLER): 500,
    ("ethernet_ip", DeviceRole.SCADA, DeviceRole.CONTROLLER): 1000,
    ("ethernet_ip", DeviceRole.SCADA, DeviceRole.FIELD_DEVICE): 1000,
    ("ethernet_ip", DeviceRole.SCADA, DeviceRole.HMI): 5000,
    ("ethernet_ip", DeviceRole.HISTORIAN, DeviceRole.CONTROLLER): 5000,
    ("ethernet_ip", None, None): 100,
    # Modbus TCP (Schneider, ABB, general process)
    ("modbus_tcp", DeviceRole.CONTROLLER, DeviceRole.FIELD_DEVICE): 200,
    ("modbus_tcp", DeviceRole.CONTROLLER, DeviceRole.CONTROLLER): 250,
    ("modbus_tcp", DeviceRole.HMI, DeviceRole.CONTROLLER): 500,
    ("modbus_tcp", DeviceRole.SCADA, DeviceRole.CONTROLLER): 1000,
    ("modbus_tcp", DeviceRole.HISTORIAN, DeviceRole.CONTROLLER): 5000,
    ("modbus_tcp", DeviceRole.GATEWAY, DeviceRole.CONTROLLER): 5000,
    ("modbus_tcp", None, None): 1000,
    # S7comm / S7comm+ (Siemens HMI/SCADA)
    ("s7comm_plus", DeviceRole.HMI, DeviceRole.CONTROLLER): 500,
    ("s7comm_plus", DeviceRole.SCADA, DeviceRole.CONTROLLER): 1000,
    ("s7comm_plus", None, None): 1000,
    ("s7comm", DeviceRole.HMI, DeviceRole.CONTROLLER): 500,
    ("s7comm", DeviceRole.SCADA, DeviceRole.CONTROLLER): 1000,
    ("s7comm", None, None): 1000,
    # BACnet (building automation)
    ("bacnet", DeviceRole.SCADA, DeviceRole.CONTROLLER): 5000,
    ("bacnet", DeviceRole.CONTROLLER, DeviceRole.FIELD_DEVICE): 500,
    ("bacnet", DeviceRole.CONTROLLER, DeviceRole.CONTROLLER): 1000,
    ("bacnet", DeviceRole.HMI, DeviceRole.CONTROLLER): 1000,
    ("bacnet", None, None): 1000,
    # SNMP (infrastructure monitoring, ITS)
    ("snmp", DeviceRole.SCADA, DeviceRole.FIELD_DEVICE): 30000,
    ("snmp", DeviceRole.SCADA, DeviceRole.CONTROLLER): 30000,
    ("snmp", DeviceRole.SCADA, DeviceRole.GATEWAY): 30000,
    ("snmp", None, None): 30000,
    # OPC UA (supervisory)
    ("opc_ua", DeviceRole.SCADA, DeviceRole.CONTROLLER): 1000,
    ("opc_ua", DeviceRole.HISTORIAN, DeviceRole.CONTROLLER): 5000,
    ("opc_ua", None, None): 1000,
    # Safety protocols
    ("profisafe", None, None): 4,
    ("cip_safety", None, None): 4,
    # DNP3 / IEC 104 (utilities SCADA)
    ("dnp3", None, None): 5000,
    ("iec104", None, None): 5000,
}

# ---------------------------------------------------------------------------
# Flow pattern types
# ---------------------------------------------------------------------------
PROTOCOL_PATTERN: dict[str, str] = {
    "profinet": "cyclic_io",
    "ethernet_ip": "cyclic_io",
    "modbus_tcp": "poll",
    "modbus": "poll",
    "s7comm": "poll",
    "s7comm_plus": "poll",
    "bacnet": "poll",
    "snmp": "poll",
    "opc_ua": "subscription",
    "profisafe": "safety",
    "cip_safety": "safety",
    "dnp3": "poll",
    "iec104": "poll",
}


def _get_interval_ms(
    protocol: str, source_role: DeviceRole, target_role: DeviceRole,
) -> int:
    """Look up realistic interval_ms for a protocol × role pairing.

    Falls back to protocol default, then 1000ms.
    """
    return (
        PROTOCOL_TIMING.get((protocol, source_role, target_role))
        or PROTOCOL_TIMING.get((protocol, None, None))
        or 1000
    )

# Cross-zone connection rules.
# Only supervisory/aggregating roles may initiate flows across zone boundaries.
# CONTROLLER and FIELD_DEVICE are intentionally omitted — they must stay within
# their zone (east-west prevention for Purdue cell isolation).
CROSS_ZONE_CONNECTIONS: dict[DeviceRole, list[DeviceRole]] = {
    DeviceRole.SCADA: [
        DeviceRole.CONTROLLER,
        DeviceRole.HMI,
        DeviceRole.GATEWAY,
        DeviceRole.HISTORIAN,
        DeviceRole.FIELD_DEVICE,
    ],
    DeviceRole.HISTORIAN: [
        DeviceRole.CONTROLLER,
        DeviceRole.SCADA,
    ],
    DeviceRole.GATEWAY: [
        DeviceRole.CONTROLLER,
        DeviceRole.FIELD_DEVICE,
    ],
    DeviceRole.ENGINEERING: [
        DeviceRole.CONTROLLER,
        DeviceRole.HMI,
        DeviceRole.SCADA,
    ],
    DeviceRole.SAFETY: [
        DeviceRole.CONTROLLER,
        DeviceRole.FIELD_DEVICE,
    ],
}


@dataclass
class DeviceSpec:
    """Specification for a device in flow generation.

    Attributes:
        device_id: Unique device identifier
        role: Device role in OT hierarchy
        ip_address: Device IP address
        mac_address: Device MAC address
        protocols: List of supported protocols
        vendor: Vendor name
        model: Device model
        unit_id: Modbus unit ID or similar
        metadata: Additional device metadata
    """

    device_id: str
    role: DeviceRole
    ip_address: str
    mac_address: str = ""
    protocols: list[str] = field(default_factory=list)
    vendor: str = ""
    model: str = ""
    unit_id: int = 1
    zone: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceSpec":
        """Create DeviceSpec from dictionary.

        Args:
            data: Dictionary with device data

        Returns:
            DeviceSpec instance
        """
        role_str = data.get("role")
        if role_str:
            try:
                role = DeviceRole(role_str.lower())
            except ValueError:
                role = cls._infer_role(data)
        else:
            # No explicit role - infer from device type
            role = cls._infer_role(data)

        return cls(
            device_id=data.get("device_id", data.get("id", "")),
            role=role,
            ip_address=data.get("ip_address", data.get("ip", "")),
            mac_address=data.get("mac_address", data.get("mac", "")),
            protocols=data.get("protocols", []),
            vendor=data.get("vendor", ""),
            model=data.get("model", ""),
            unit_id=data.get("unit_id", 1),
            zone=data.get("zone") or data.get("zoneId") or data.get("zone_id"),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _infer_role(data: dict[str, Any]) -> DeviceRole:
        """Infer device role from device type and characteristics.

        Args:
            data: Device data dictionary

        Returns:
            Inferred DeviceRole
        """
        # Check both 'device_type' and 'type' fields (templates use 'type')
        device_type = (data.get("device_type") or data.get("type") or "").lower()
        name = (data.get("name") or "").lower()
        model = (data.get("model") or "").lower()

        # Check for historian (dedicated check before SCADA)
        if device_type == "historian":
            return DeviceRole.HISTORIAN

        # Check for SCADA/server
        if any(x in device_type for x in ["scada", "server", "master"]):
            return DeviceRole.SCADA
        if any(x in name for x in ["scada", "historian", "server"]):
            return DeviceRole.SCADA

        # Check for HMI
        if any(x in device_type for x in ["hmi", "panel", "display", "workstation"]):
            return DeviceRole.HMI
        if any(x in name for x in ["hmi", "panel", "operator"]):
            return DeviceRole.HMI

        # Check for controller
        if any(x in device_type for x in ["plc", "rtu", "controller", "pac", "dcs"]):
            return DeviceRole.CONTROLLER
        if any(x in model for x in ["cpu", "plc", "1756", "s7-"]):
            return DeviceRole.CONTROLLER

        # Check for gateway
        if any(x in device_type for x in ["gateway", "converter", "bridge"]):
            return DeviceRole.GATEWAY

        # Check for safety (safety_io, sis, etc.)
        if any(x in device_type for x in ["safety", "sis", "guardlogix"]):
            return DeviceRole.SAFETY

        # Check for I/O modules (remote_io, io_module, etc.)
        if any(x in device_type for x in ["remote_io", "io_module", "io_rack", "distributed_io"]):
            return DeviceRole.FIELD_DEVICE

        # Check for ITS/Transportation field devices (sensors, cameras, signs)
        # These are polled directly by TMC (SCADA) without intermediate controller
        if any(x in device_type for x in [
            "dms", "sign", "sensor", "radar", "thermal", "detector",
            "camera", "weather", "rwis", "toll", "rsu", "anpr",
            "lighting", "ventilation", "ahu", "vav", "chiller",
        ]):
            return DeviceRole.FIELD_DEVICE

        # Check for switches (treated as field devices for SNMP monitoring)
        if "switch" in device_type:
            return DeviceRole.FIELD_DEVICE

        # Default to field device
        return DeviceRole.FIELD_DEVICE


@dataclass
class GeneratedFlow:
    """A generated flow between two devices.

    Attributes:
        flow_id: Unique flow identifier
        source: Source device specification
        destination: Destination device specification
        protocol: Protocol for this flow
        poll_rate: Polls per minute
        priority: Flow priority (1-10, higher = more important)
        metadata: Additional flow metadata
    """

    flow_id: str
    source: DeviceSpec
    destination: DeviceSpec
    protocol: str
    poll_rate: float = 6.0
    priority: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "flow_id": self.flow_id,
            "source_id": self.source.device_id,
            "source_ip": self.source.ip_address,
            "destination_id": self.destination.device_id,
            "destination_ip": self.destination.ip_address,
            "protocol": self.protocol,
            "poll_rate": self.poll_rate,
            "priority": self.priority,
            "metadata": self.metadata,
        }


class SmartFlowGenerator:
    """Intelligent flow generator for OT traffic patterns.

    Generates flows based on device roles and OT communication patterns,
    ensuring all devices participate in network traffic.

    Usage:
        generator = SmartFlowGenerator()
        devices = [DeviceSpec(...), DeviceSpec(...)]
        flows = generator.generate_flows(devices, FlowPattern.REALISTIC)
    """

    def __init__(
        self,
        min_flows_per_device: int = 1,
        max_flows_per_device: int = 20,
        default_protocol: str = "modbus_tcp",
    ):
        """Initialize the flow generator.

        Args:
            min_flows_per_device: Minimum flows for each device
            max_flows_per_device: Maximum flows from each initiator (20 for ITS/BMS scenarios)
            default_protocol: Default protocol when not specified
        """
        self.min_flows_per_device = min_flows_per_device
        self.max_flows_per_device = max_flows_per_device
        self.default_protocol = default_protocol
        self._flow_counter = 0

    def generate_flows(
        self,
        devices: list[DeviceSpec],
        pattern: FlowPattern = FlowPattern.REALISTIC,
        protocols: list[str] | None = None,
    ) -> list[GeneratedFlow]:
        """Generate flows ensuring all devices participate.

        Args:
            devices: List of device specifications
            pattern: Flow generation pattern
            protocols: Allowed protocols (None = use device protocols)

        Returns:
            List of generated flows
        """
        if not devices:
            return []

        if pattern == FlowPattern.HIERARCHICAL:
            flows = self._generate_hierarchical(devices, protocols)
        elif pattern == FlowPattern.MESH:
            flows = self._generate_mesh(devices, protocols)
        elif pattern == FlowPattern.STAR:
            flows = self._generate_star(devices, protocols)
        elif pattern == FlowPattern.TREE:
            flows = self._generate_tree(devices, protocols)
        else:  # REALISTIC
            flows = self._generate_realistic(devices, protocols)

        # Ensure minimum flows per device
        flows = self._ensure_minimum_participation(devices, flows, protocols)

        logger.info(
            f"Generated {len(flows)} flows for {len(devices)} devices "
            f"using {pattern.value} pattern"
        )

        return flows

    def _generate_realistic(
        self,
        devices: list[DeviceSpec],
        protocols: list[str] | None,
    ) -> list[GeneratedFlow]:
        """Generate flows based on realistic OT communication patterns.

        Args:
            devices: Device specifications
            protocols: Allowed protocols

        Returns:
            List of flows
        """
        flows = []

        # Group devices by role
        by_role: dict[DeviceRole, list[DeviceSpec]] = {}
        for device in devices:
            if device.role not in by_role:
                by_role[device.role] = []
            by_role[device.role].append(device)

        # Generate flows based on role relationships
        for source_role, target_roles in ROLE_CONNECTIONS.items():
            sources = by_role.get(source_role, [])
            for source in sources:
                targets_added = 0
                for target_role in target_roles:
                    targets = by_role.get(target_role, [])
                    for target in targets:
                        if source.device_id == target.device_id:
                            continue

                        if not self._is_zone_allowed(source, target):
                            continue

                        if targets_added >= self.max_flows_per_device:
                            break

                        protocol = self._select_protocol(source, target, protocols)
                        flow = self._create_flow(source, target, protocol)
                        flows.append(flow)
                        targets_added += 1

        return flows

    def _generate_hierarchical(
        self,
        devices: list[DeviceSpec],
        protocols: list[str] | None,
    ) -> list[GeneratedFlow]:
        """Generate flows in strict hierarchy.

        Args:
            devices: Device specifications
            protocols: Allowed protocols

        Returns:
            List of flows
        """
        flows = []
        hierarchy = [
            DeviceRole.SCADA,
            DeviceRole.HMI,
            DeviceRole.CONTROLLER,
            DeviceRole.FIELD_DEVICE,
        ]

        # Group by role
        by_role: dict[DeviceRole, list[DeviceSpec]] = {}
        for device in devices:
            if device.role not in by_role:
                by_role[device.role] = []
            by_role[device.role].append(device)

        # Connect each level to the next
        for i, role in enumerate(hierarchy[:-1]):
            next_role = hierarchy[i + 1]
            sources = by_role.get(role, [])
            targets = by_role.get(next_role, [])

            for source in sources:
                # Distribute targets among sources
                for target in targets:
                    if not self._is_zone_allowed(source, target):
                        continue
                    protocol = self._select_protocol(source, target, protocols)
                    flow = self._create_flow(source, target, protocol)
                    flows.append(flow)

        return flows

    def _generate_mesh(
        self,
        devices: list[DeviceSpec],
        protocols: list[str] | None,
    ) -> list[GeneratedFlow]:
        """Generate all-to-all mesh flows.

        Args:
            devices: Device specifications
            protocols: Allowed protocols

        Returns:
            List of flows
        """
        flows = []

        for source in devices:
            for target in devices:
                if source.device_id == target.device_id:
                    continue

                if not self._is_zone_allowed(source, target):
                    continue

                protocol = self._select_protocol(source, target, protocols)
                flow = self._create_flow(source, target, protocol)
                flows.append(flow)

        return flows

    def _generate_star(
        self,
        devices: list[DeviceSpec],
        protocols: list[str] | None,
    ) -> list[GeneratedFlow]:
        """Generate star topology with central node.

        Args:
            devices: Device specifications
            protocols: Allowed protocols

        Returns:
            List of flows
        """
        flows = []

        if len(devices) < 2:
            return flows

        # Find central node (prefer SCADA, then controller, then first device)
        central = None
        for role in [DeviceRole.SCADA, DeviceRole.CONTROLLER, DeviceRole.HMI]:
            for device in devices:
                if device.role == role:
                    central = device
                    break
            if central:
                break

        if not central:
            central = devices[0]

        # Create flows from central to all others
        for device in devices:
            if device.device_id == central.device_id:
                continue

            if not self._is_zone_allowed(central, device):
                continue

            protocol = self._select_protocol(central, device, protocols)
            flow = self._create_flow(central, device, protocol)
            flows.append(flow)

        return flows

    def _generate_tree(
        self,
        devices: list[DeviceSpec],
        protocols: list[str] | None,
    ) -> list[GeneratedFlow]:
        """Generate tree topology with branching.

        Args:
            devices: Device specifications
            protocols: Allowed protocols

        Returns:
            List of flows
        """
        flows = []

        if len(devices) < 2:
            return flows

        # Sort by role hierarchy
        role_order = {
            DeviceRole.SCADA: 0,
            DeviceRole.HISTORIAN: 1,
            DeviceRole.HMI: 2,
            DeviceRole.ENGINEERING: 3,
            DeviceRole.CONTROLLER: 4,
            DeviceRole.GATEWAY: 5,
            DeviceRole.SAFETY: 6,
            DeviceRole.FIELD_DEVICE: 7,
        }
        sorted_devices = sorted(
            devices, key=lambda d: role_order.get(d.role, 99)
        )

        # Build tree: each device connects to ~2 devices at next level
        branching_factor = 2
        for i, device in enumerate(sorted_devices[:-1]):
            start = min((i + 1) * branching_factor, len(sorted_devices) - 1)
            end = min(start + branching_factor, len(sorted_devices))

            for j in range(start, end):
                target = sorted_devices[j]
                if not self._is_zone_allowed(device, target):
                    continue
                protocol = self._select_protocol(device, target, protocols)
                flow = self._create_flow(device, target, protocol)
                flows.append(flow)

        return flows

    def _ensure_minimum_participation(
        self,
        devices: list[DeviceSpec],
        flows: list[GeneratedFlow],
        protocols: list[str] | None,
    ) -> list[GeneratedFlow]:
        """Ensure all devices have minimum number of flows.

        Args:
            devices: All devices
            flows: Current flows
            protocols: Allowed protocols

        Returns:
            Updated flow list
        """
        # Count participation
        participation: dict[str, int] = {d.device_id: 0 for d in devices}
        for flow in flows:
            participation[flow.source.device_id] = (
                participation.get(flow.source.device_id, 0) + 1
            )
            participation[flow.destination.device_id] = (
                participation.get(flow.destination.device_id, 0) + 1
            )

        # Find devices needing more flows
        device_map = {d.device_id: d for d in devices}
        orphans = [
            device_map[did]
            for did, count in participation.items()
            if count < self.min_flows_per_device
        ]

        if not orphans:
            return flows

        logger.debug(f"Adding flows for {len(orphans)} under-connected devices")

        # Connect orphans to appropriate devices
        for orphan in orphans:
            # Find a suitable partner based on role
            target_roles = ROLE_CONNECTIONS.get(orphan.role, [])

            # For field devices, they should be targets, not sources
            if orphan.role == DeviceRole.FIELD_DEVICE:
                # Find a controller or SCADA to poll this device
                # SCADA is included for ITS/BMS scenarios where TMC directly polls field equipment
                pollers = [
                    d for d in devices
                    if d.role in (DeviceRole.CONTROLLER, DeviceRole.SCADA)
                    and d.device_id != orphan.device_id
                    and self._is_zone_allowed(d, orphan)
                ]
                # Prefer same-zone pollers
                same_zone = [d for d in pollers if d.zone and d.zone == orphan.zone]
                if same_zone:
                    source = random.choice(same_zone)
                elif pollers:
                    source = random.choice(pollers)
                else:
                    continue
                protocol = self._select_protocol(source, orphan, protocols)
                flow = self._create_flow(source, orphan, protocol)
                flows.append(flow)
                continue

            # For initiators, find targets
            for target_role in target_roles:
                targets = [
                    d for d in devices
                    if d.role == target_role
                    and d.device_id != orphan.device_id
                    and self._is_zone_allowed(orphan, d)
                ]
                # Prefer same-zone targets
                same_zone = [d for d in targets if d.zone and d.zone == orphan.zone]
                if same_zone:
                    target = random.choice(same_zone)
                elif targets:
                    target = random.choice(targets)
                else:
                    continue
                protocol = self._select_protocol(orphan, target, protocols)
                flow = self._create_flow(orphan, target, protocol)
                flows.append(flow)
                break

        return flows

    @staticmethod
    def _is_zone_allowed(source: DeviceSpec, target: DeviceSpec) -> bool:
        """Check if a flow between source and target respects zone boundaries.

        Rules:
        - If either device has no zone info, allow (backward compat).
        - Same zone: always allowed.
        - Cross zone: only if source role is in CROSS_ZONE_CONNECTIONS
          AND target role is in its allowed list.
        """
        if not source.zone or not target.zone:
            return True
        if source.zone == target.zone:
            return True
        allowed_targets = CROSS_ZONE_CONNECTIONS.get(source.role)
        if allowed_targets is None:
            return False
        return target.role in allowed_targets

    # TCP/UDP protocols that generate IP traffic
    # Layer 2 protocols like PROFINET don't include IP addresses in packets
    TCP_UDP_PROTOCOLS = {
        "modbus_tcp", "modbus", "ethernet_ip", "s7comm", "s7comm_plus",
        "bacnet", "bacnet_ip", "snmp", "opc_ua", "dnp3", "iec104", "iec_104",
    }

    @staticmethod
    def _get_vendor_preferred_protocol(
        source: DeviceSpec, target: DeviceSpec,
    ) -> str | None:
        """Get vendor-preferred protocol for a source→target pairing.

        Uses the more specific device's vendor (target for field devices,
        source for supervisory roles) to pick the native protocol.
        """
        # Try target vendor first (field device knows its own protocol),
        # then source vendor
        vendor = (target.vendor or source.vendor or "").lower().strip()
        if not vendor:
            return None

        # Supervisory roles → supervisory protocol table
        if source.role in (DeviceRole.HMI, DeviceRole.SCADA, DeviceRole.HISTORIAN):
            return VENDOR_SUPERVISORY_PROTOCOL.get(vendor)

        # Real-time I/O roles → realtime protocol table
        if source.role in (DeviceRole.CONTROLLER, DeviceRole.SAFETY):
            return VENDOR_REALTIME_PROTOCOL.get(vendor)

        return None

    def _select_protocol(
        self,
        source: DeviceSpec,
        target: DeviceSpec,
        allowed: list[str] | None,
    ) -> str:
        """Select appropriate protocol for a flow.

        Selection order:
        1. Vendor-preferred protocol (if in common or either device's set)
        2. Common TCP/UDP protocols
        3. Source TCP/UDP, target TCP/UDP, any common, target any
        4. Allowed list or default_protocol fallback

        TCP/UDP protocols are always preferred over Layer 2 to ensure
        flows generate IP traffic (visible to Cyber Vision).

        Args:
            source: Source device
            target: Target device
            allowed: Allowed protocols

        Returns:
            Protocol name
        """
        # Determine vendor-preferred protocol based on role pairing
        vendor_pref = self._get_vendor_preferred_protocol(source, target)

        source_protocols = set(source.protocols) if source.protocols else set()
        target_protocols = set(target.protocols) if target.protocols else set()
        common = source_protocols & target_protocols

        # Apply allowed filter
        if allowed:
            allowed_set = set(allowed)
            common = common & allowed_set
            source_protocols = source_protocols & allowed_set
            target_protocols = target_protocols & allowed_set

        # 1. Vendor-preferred in common set → best choice
        if vendor_pref and vendor_pref in common:
            return vendor_pref

        # 2. Vendor-preferred in either device's protocols
        if vendor_pref:
            if vendor_pref in source_protocols:
                return vendor_pref
            if vendor_pref in target_protocols:
                return vendor_pref

        # 3. Common TCP/UDP protocols
        tcp_udp_common = common & self.TCP_UDP_PROTOCOLS
        if tcp_udp_common:
            return random.choice(list(tcp_udp_common))

        # 4. Source TCP/UDP protocols
        source_tcp = source_protocols & self.TCP_UDP_PROTOCOLS
        if source_tcp:
            return random.choice(list(source_tcp))

        # 5. Target TCP/UDP protocols
        target_tcp = target_protocols & self.TCP_UDP_PROTOCOLS
        if target_tcp:
            return random.choice(list(target_tcp))

        # 6. Any common protocol (may be Layer 2)
        if common:
            return random.choice(list(common))

        # 7. Any target protocol
        if target_protocols:
            return random.choice(list(target_protocols))

        # 8. Allowed list or default
        if allowed:
            return allowed[0]

        return self.default_protocol

    def _create_flow(
        self,
        source: DeviceSpec,
        target: DeviceSpec,
        protocol: str,
        interval_ms: int | None = None,
    ) -> GeneratedFlow:
        """Create a flow between two devices.

        Args:
            source: Source device
            target: Target device
            protocol: Protocol name
            interval_ms: Override interval in ms (auto-derived if None)

        Returns:
            GeneratedFlow instance
        """
        self._flow_counter += 1
        flow_id = f"flow_{self._flow_counter:04d}"

        # Auto-derive interval from protocol × role if not provided
        if interval_ms is None:
            interval_ms = _get_interval_ms(protocol, source.role, target.role)

        # Convert to polls_per_minute for backward compat
        poll_rate = 60000.0 / interval_ms if interval_ms > 0 else 6.0

        # Determine pattern type
        pattern = PROTOCOL_PATTERN.get(protocol, "poll")
        # Supervisory roles use explicit messaging, not cyclic I/O
        if source.role in (DeviceRole.SCADA, DeviceRole.HMI, DeviceRole.HISTORIAN):
            if pattern == "cyclic_io":
                pattern = "poll"

        # Determine priority based on roles
        priority = self._calculate_priority(source.role, target.role)

        return GeneratedFlow(
            flow_id=flow_id,
            source=source,
            destination=target,
            protocol=protocol,
            poll_rate=poll_rate,
            priority=priority,
            metadata={
                "source_role": source.role.value,
                "destination_role": target.role.value,
                "source_zone": source.zone,
                "destination_zone": target.zone,
                "cross_zone": source.zone != target.zone if (source.zone and target.zone) else None,
                "pattern": pattern,
                "interval_ms": interval_ms,
            },
        )

    def _calculate_priority(
        self,
        source_role: DeviceRole,
        target_role: DeviceRole,
    ) -> int:
        """Calculate flow priority based on roles.

        Args:
            source_role: Source device role
            target_role: Target device role

        Returns:
            Priority value (1-10)
        """
        # Safety-related flows are highest priority
        if source_role == DeviceRole.SAFETY or target_role == DeviceRole.SAFETY:
            return 10

        # Controller-to-field is high priority (real-time I/O)
        if source_role == DeviceRole.CONTROLLER and target_role == DeviceRole.FIELD_DEVICE:
            return 8

        # HMI updates are medium-high
        if source_role == DeviceRole.HMI:
            return 7

        # SCADA polling is medium
        if source_role == DeviceRole.SCADA:
            return 5

        # Historian is lower priority
        if source_role == DeviceRole.HISTORIAN:
            return 3

        return 5


def generate_flows_for_scenario(
    devices: list[dict[str, Any]],
    pattern: str = "realistic",
    protocols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convenience function to generate flows from device dictionaries.

    Args:
        devices: List of device dictionaries
        pattern: Flow pattern name
        protocols: Allowed protocols

    Returns:
        List of flow dictionaries
    """
    # Convert dicts to DeviceSpecs
    device_specs = [DeviceSpec.from_dict(d) for d in devices]

    # Parse pattern
    try:
        flow_pattern = FlowPattern((pattern or "realistic").lower())
    except ValueError:
        flow_pattern = FlowPattern.REALISTIC

    # Generate flows
    generator = SmartFlowGenerator()
    flows = generator.generate_flows(device_specs, flow_pattern, protocols)

    # Convert to dicts
    return [f.to_dict() for f in flows]
