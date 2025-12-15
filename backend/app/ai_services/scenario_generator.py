"""Natural language scenario generator for OT traffic simulation.

This module provides AI-powered scenario generation from natural language
descriptions, supporting:
- Entity extraction (devices, protocols, verticals)
- Industry template matching
- Automatic topology generation
- Protocol inference from device types
- IP/MAC address assignment
- Vendor fingerprint application for hyper-realistic traffic
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.protocol_engines.vendor_oui import generate_mac_address, get_oui_for_vendor
from app.services.vendor_fingerprint_data import (
    get_fingerprint_by_vendor_model,
    get_fingerprints_by_vendor,
    get_random_oui_for_vendor,
    VENDOR_OUI_PREFIXES,
)

logger = logging.getLogger(__name__)


# Industry vertical templates with fingerprint model hints
# Each device type includes preferred fingerprint models for hyper-realistic generation
VERTICAL_TEMPLATES = {
    "manufacturing": {
        "name": "Manufacturing",
        "description": "Discrete and process manufacturing environments",
        "typical_devices": {
            "plc": {
                "count_range": (2, 10),
                "vendors": ["rockwell", "siemens", "schneider"],
                "fingerprint_models": {
                    "rockwell": "1756-L83E",  # ControlLogix L83E
                    "siemens": "6ES7 516-3AN02-0AB0",  # S7-1500 CPU 1516-3
                    "schneider": "BMEP584040",  # Modicon M580
                },
                "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
            },
            "hmi": {
                "count_range": (1, 5),
                "vendors": ["rockwell", "siemens"],
                "fingerprint_models": {
                    "rockwell": "2711P-T15C22D9P",  # PanelView Plus 7
                    "siemens": "6AV2 123-2GB03-0AX0",  # KTP700
                },
                "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
            },
            "drive": {
                "count_range": (2, 20),
                "vendors": ["abb", "siemens", "schneider"],
                "fingerprint_models": {
                    "schneider": "ATV630D15N4",  # Altivar Process
                    "abb": "PM5630-2ETH",  # AC500 (used for drive control)
                },
                "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0003},
            },
            "robot": {"count_range": (0, 5), "vendors": ["fanuc", "kuka", "abb"]},
            "sensor": {"count_range": (10, 50), "vendors": ["generic"]},
        },
        "protocols": ["ethernet_ip", "profinet", "modbus_tcp"],
        "zones": ["process_control", "safety", "enterprise"],
        "poll_intervals_ms": {"fast": 100, "normal": 500, "slow": 2000},
    },
    "water": {
        "name": "Water/Wastewater",
        "description": "Water treatment and distribution systems",
        "typical_devices": {
            "rtu": {
                "count_range": (5, 20),
                "vendors": ["schneider", "honeywell", "ge"],
                "fingerprint_models": {
                    "schneider": "TM241CE40R",  # Modicon M241
                    "ge": "IC695CPE400",  # PACSystems RX3i
                    "honeywell": "LCNP4M",  # ControlEdge PLC
                },
                "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},  # Higher for remote
            },
            "plc": {
                "count_range": (1, 5),
                "vendors": ["schneider", "rockwell"],
                "fingerprint_models": {
                    "schneider": "BMEP584040",  # Modicon M580
                    "rockwell": "1769-L33ER",  # CompactLogix
                },
                "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
            },
            "pump_controller": {
                "count_range": (3, 15),
                "vendors": ["abb", "schneider"],
                "fingerprint_models": {
                    "abb": "PM5630-2ETH",
                    "schneider": "TM241CE40R",
                },
            },
            "flow_meter": {"count_range": (5, 30), "vendors": ["generic"]},
            "level_sensor": {"count_range": (5, 20), "vendors": ["generic"]},
        },
        "protocols": ["modbus_tcp", "dnp3"],
        "zones": ["scada", "field", "corporate"],
        "poll_intervals_ms": {"fast": 1000, "normal": 5000, "slow": 30000},
    },
    "energy": {
        "name": "Energy/Power",
        "description": "Power generation and distribution",
        "typical_devices": {
            "rtu": {
                "count_range": (10, 50),
                "vendors": ["ge", "abb", "siemens"],
                "fingerprint_models": {
                    "ge": "IC695CPE400",  # PACSystems RX3i
                    "abb": "PM5630-2ETH",  # AC500
                    "siemens": "6ES7 516-3AN02-0AB0",  # S7-1500
                },
                "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0002},  # High reliability
            },
            "ied": {
                "count_range": (5, 30),
                "vendors": ["abb", "ge", "siemens"],
                "fingerprint_models": {
                    "ge": "IC695CPE400",
                    "abb": "PM5630-2ETH",
                },
                "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},  # Critical
            },
            "pmu": {"count_range": (2, 10), "vendors": ["sel", "ge"]},
            "meter": {"count_range": (10, 100), "vendors": ["generic"]},
        },
        "protocols": ["iec_104", "dnp3", "modbus_tcp"],
        "zones": ["substation", "control_center", "corporate"],
        "poll_intervals_ms": {"fast": 100, "normal": 1000, "slow": 5000},
    },
    "oil_gas": {
        "name": "Oil & Gas",
        "description": "Pipeline, refinery, and upstream operations",
        "typical_devices": {
            "rtu": {
                "count_range": (10, 100),
                "vendors": ["emerson", "honeywell", "abb"],
                "fingerprint_models": {
                    "emerson": "ROC800L",  # ROC800 for pipeline
                    "honeywell": "LCNP4M",  # ControlEdge
                    "abb": "PM5630-2ETH",
                },
                "error_config": {"exception_rate": 0.002, "timeout_rate": 0.005},  # Satellite/cellular
            },
            "plc": {
                "count_range": (2, 10),
                "vendors": ["rockwell", "schneider", "emerson"],
                "fingerprint_models": {
                    "rockwell": "1756-L83E",  # ControlLogix
                    "schneider": "BMEP584040",  # M580
                    "emerson": "S-series Controller",  # DeltaV
                },
                "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
            },
            "flow_computer": {
                "count_range": (5, 30),
                "vendors": ["emerson", "honeywell"],
                "fingerprint_models": {
                    "emerson": "ROC800L",
                    "honeywell": "LCNP4M",
                },
            },
            "compressor_controller": {
                "count_range": (2, 10),
                "vendors": ["ge", "siemens"],
                "fingerprint_models": {
                    "ge": "IS420UCSBH1A",  # Mark VIe
                    "siemens": "6ES7 516-3AN02-0AB0",
                },
            },
        },
        "protocols": ["modbus_tcp", "opc_ua"],
        "zones": ["wellhead", "pipeline", "refinery", "control_room"],
        "poll_intervals_ms": {"fast": 500, "normal": 2000, "slow": 10000},
    },
}

# Device type to protocol mapping
DEVICE_PROTOCOL_MAP = {
    "plc": ["ethernet_ip", "profinet", "modbus_tcp"],
    "rtu": ["modbus_tcp", "dnp3"],
    "hmi": ["ethernet_ip", "modbus_tcp"],
    "drive": ["profinet", "ethernet_ip", "modbus_tcp"],
    "robot": ["profinet", "ethernet_ip"],
    "ied": ["iec_104", "dnp3"],
    "pmu": ["iec_104"],
    "meter": ["modbus_tcp", "dnp3"],
    "sensor": ["modbus_tcp"],
    "pump_controller": ["modbus_tcp", "ethernet_ip"],
    "flow_meter": ["modbus_tcp"],
    "level_sensor": ["modbus_tcp"],
    "flow_computer": ["modbus_tcp", "opc_ua"],
    "compressor_controller": ["modbus_tcp", "ethernet_ip"],
}

# Keywords for entity extraction
DEVICE_KEYWORDS = {
    "plc": ["plc", "controller", "programmable logic controller", "pac"],
    "hmi": ["hmi", "panel", "operator interface", "touch screen", "visualization"],
    "rtu": ["rtu", "remote terminal", "remote unit"],
    "drive": ["drive", "vfd", "variable frequency", "motor drive", "inverter"],
    "robot": ["robot", "robotic arm", "cobot"],
    "sensor": ["sensor", "transmitter", "probe", "detector"],
    "ied": ["ied", "intelligent electronic device", "relay"],
    "meter": ["meter", "power meter", "energy meter"],
}

VENDOR_KEYWORDS = {
    "rockwell": ["rockwell", "allen-bradley", "allen bradley", "ab", "logix", "compactlogix", "controllogix"],
    "siemens": ["siemens", "s7", "simatic", "tia portal", "profinet"],
    "schneider": ["schneider", "modicon", "m580", "m340", "unity"],
    "abb": ["abb", "ac500", "freelance"],
    "honeywell": ["honeywell", "experion", "c300"],
    "emerson": ["emerson", "deltav", "ovation", "roc"],
    "ge": ["ge", "general electric", "mark vi", "rx3i"],
}

PROTOCOL_KEYWORDS = {
    "modbus_tcp": ["modbus", "modbus tcp", "modbus/tcp"],
    "ethernet_ip": ["ethernet/ip", "ethernet-ip", "enip", "cip"],
    "profinet": ["profinet", "pn io", "profinet io"],
    "opc_ua": ["opc ua", "opc-ua", "opcua", "opc unified"],
    "dnp3": ["dnp3", "dnp 3", "distributed network protocol"],
    "iec_104": ["iec 104", "iec104", "iec 60870-5-104", "iec-104"],
}

VERTICAL_KEYWORDS = {
    "manufacturing": ["manufacturing", "factory", "assembly", "production line", "discrete", "automotive"],
    "water": ["water", "wastewater", "treatment plant", "pumping station", "utility"],
    "energy": ["power", "energy", "substation", "grid", "generation", "transmission"],
    "oil_gas": ["oil", "gas", "pipeline", "refinery", "petrochemical", "upstream", "downstream"],
}


@dataclass
class ExtractedEntity:
    """Entity extracted from natural language."""

    entity_type: str  # "device", "vendor", "protocol", "vertical", "count"
    value: str
    confidence: float
    source_text: str


@dataclass
class GeneratedDevice:
    """A generated device in a scenario."""

    device_id: str
    device_type: str
    name: str
    vendor: str | None
    model: str | None
    ip_address: str
    mac_address: str
    zone: str
    protocols: list[str]
    # Fingerprint model reference for hyper-realistic traffic generation
    fingerprint_model: str | None = None
    # Error injection configuration
    error_config: dict[str, float] | None = None
    # Full fingerprint data (optional, for advanced use)
    fingerprint_data: dict[str, Any] | None = None


@dataclass
class GeneratedFlow:
    """A generated traffic flow."""

    flow_id: str
    source_device_id: str
    destination_device_id: str
    protocol: str
    poll_interval_ms: int
    description: str


@dataclass
class GeneratedScenario:
    """A complete generated scenario."""

    scenario_id: str
    name: str
    description: str
    vertical: str
    devices: list[GeneratedDevice]
    flows: list[GeneratedFlow]
    zones: list[dict[str, Any]]
    duration_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ScenarioGenerator:
    """Service for generating scenarios from natural language descriptions.

    The generator:
    1. Extracts entities from the NL description
    2. Matches to an industry vertical template
    3. Generates device topology
    4. Infers protocols from device types
    5. Creates flows with appropriate timing
    6. Assigns IP/MAC addresses using zone scheme
    """

    def __init__(self):
        """Initialize the scenario generator."""
        self._ip_counter = 1
        self._mac_counter = 1

    def generate_from_description(
        self,
        description: str,
        name: str | None = None,
        duration_ms: int = 300000,
    ) -> GeneratedScenario:
        """Generate a scenario from natural language description.

        Args:
            description: Natural language scenario description
            name: Optional scenario name
            duration_ms: Scenario duration in milliseconds

        Returns:
            Generated scenario
        """
        # Extract entities
        entities = self._extract_entities(description)

        # Determine vertical
        vertical = self._determine_vertical(entities, description)
        template = VERTICAL_TEMPLATES.get(vertical, VERTICAL_TEMPLATES["manufacturing"])

        # Generate devices
        devices = self._generate_devices(entities, template)

        # Generate zones
        zones = self._generate_zones(template, devices)

        # Generate flows
        flows = self._generate_flows(devices, template)

        # Create scenario
        scenario = GeneratedScenario(
            scenario_id=str(uuid.uuid4()),
            name=name or f"{template['name']} Scenario",
            description=description,
            vertical=vertical,
            devices=devices,
            flows=flows,
            zones=zones,
            duration_ms=duration_ms,
            metadata={
                "extracted_entities": [
                    {"type": e.entity_type, "value": e.value, "confidence": e.confidence}
                    for e in entities
                ],
                "template_used": vertical,
            },
        )

        logger.info(
            f"Generated scenario '{scenario.name}' with "
            f"{len(devices)} devices and {len(flows)} flows"
        )
        return scenario

    def _extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities from text.

        Args:
            text: Input text

        Returns:
            List of extracted entities
        """
        entities = []
        text_lower = text.lower()

        # Extract device types
        for device_type, keywords in DEVICE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Try to extract count
                    count_match = re.search(rf"(\d+)\s*{keyword}", text_lower)
                    if count_match:
                        entities.append(ExtractedEntity(
                            entity_type="device_count",
                            value=f"{device_type}:{count_match.group(1)}",
                            confidence=0.9,
                            source_text=count_match.group(0),
                        ))
                    entities.append(ExtractedEntity(
                        entity_type="device",
                        value=device_type,
                        confidence=0.8,
                        source_text=keyword,
                    ))
                    break

        # Extract vendors
        for vendor, keywords in VENDOR_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities.append(ExtractedEntity(
                        entity_type="vendor",
                        value=vendor,
                        confidence=0.85,
                        source_text=keyword,
                    ))
                    break

        # Extract protocols
        for protocol, keywords in PROTOCOL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities.append(ExtractedEntity(
                        entity_type="protocol",
                        value=protocol,
                        confidence=0.9,
                        source_text=keyword,
                    ))
                    break

        # Extract verticals
        for vertical, keywords in VERTICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities.append(ExtractedEntity(
                        entity_type="vertical",
                        value=vertical,
                        confidence=0.85,
                        source_text=keyword,
                    ))
                    break

        return entities

    def _determine_vertical(
        self,
        entities: list[ExtractedEntity],
        text: str,
    ) -> str:
        """Determine the industry vertical.

        Args:
            entities: Extracted entities
            text: Original text

        Returns:
            Vertical name
        """
        vertical_entities = [e for e in entities if e.entity_type == "vertical"]
        if vertical_entities:
            return vertical_entities[0].value

        # Default based on devices mentioned
        device_entities = [e for e in entities if e.entity_type == "device"]
        device_types = [e.value for e in device_entities]

        if "rtu" in device_types or "ied" in device_types:
            return "energy"
        if "robot" in device_types:
            return "manufacturing"

        return "manufacturing"  # Default

    def _generate_devices(
        self,
        entities: list[ExtractedEntity],
        template: dict[str, Any],
    ) -> list[GeneratedDevice]:
        """Generate devices based on entities and template.

        Applies vendor fingerprints for hyper-realistic traffic generation:
        - Looks up fingerprint model from template config
        - Applies correct OUI prefix for MAC generation
        - Configures error rates per device type
        - Stores fingerprint data for packet generation

        Args:
            entities: Extracted entities
            template: Vertical template

        Returns:
            List of generated devices with fingerprint data
        """
        import random

        devices = []

        # Get device counts from entities
        device_counts = {}
        for e in entities:
            if e.entity_type == "device_count":
                device_type, count = e.value.split(":")
                device_counts[device_type] = int(count)

        # Get preferred vendors
        preferred_vendors = [e.value for e in entities if e.entity_type == "vendor"]

        # Generate devices for each type
        for device_type, config in template["typical_devices"].items():
            # Determine count
            if device_type in device_counts:
                count = device_counts[device_type]
            else:
                min_count, max_count = config["count_range"]
                count = random.randint(min_count, max_count)

            # Skip if count is 0
            if count == 0:
                continue

            # Determine vendor
            vendors = config["vendors"]
            if preferred_vendors:
                matching = [v for v in preferred_vendors if v in vendors]
                vendor = matching[0] if matching else random.choice(vendors)
            else:
                vendor = random.choice(vendors)

            # Get protocols for device type
            protocols = DEVICE_PROTOCOL_MAP.get(device_type, ["modbus_tcp"])
            # Filter to template protocols
            protocols = [p for p in protocols if p in template["protocols"]] or [protocols[0]]

            # Assign zone
            zones = template["zones"]
            if device_type in ["plc", "rtu"]:
                zone = zones[0]  # Control zone
            elif device_type in ["hmi"]:
                zone = zones[-1] if len(zones) > 1 else zones[0]  # Enterprise/higher zone
            else:
                zone = zones[0]  # Default to control zone

            # Get fingerprint model from template config (if available)
            fingerprint_models = config.get("fingerprint_models", {})
            fingerprint_model = fingerprint_models.get(vendor)

            # Look up full fingerprint data
            fingerprint_data = None
            if fingerprint_model and vendor != "generic":
                fingerprint_data = get_fingerprint_by_vendor_model(vendor, fingerprint_model)

            # Get error config from template or fingerprint
            error_config = config.get("error_config")
            if not error_config and fingerprint_data:
                error_behavior = fingerprint_data.get("error_behavior", {})
                if error_behavior:
                    error_config = {
                        "exception_rate": error_behavior.get("exception_probability", 0.001),
                        "timeout_rate": error_behavior.get("timeout_probability", 0.0005),
                    }

            # Generate devices
            for i in range(count):
                # Generate MAC using fingerprint OUI if available
                if fingerprint_data and fingerprint_data.get("oui_prefixes"):
                    oui = random.choice(fingerprint_data["oui_prefixes"])
                    mac_address = self._generate_mac_with_oui(oui)
                else:
                    mac_address = generate_mac_address(vendor=vendor, device_type=device_type)

                device = GeneratedDevice(
                    device_id=str(uuid.uuid4()),
                    device_type=device_type,
                    name=f"{device_type.upper()}-{i+1:03d}",
                    vendor=vendor if vendor != "generic" else None,
                    model=fingerprint_model,
                    ip_address=self._generate_ip(zone),
                    mac_address=mac_address,
                    zone=zone,
                    protocols=protocols,
                    fingerprint_model=fingerprint_model,
                    error_config=error_config,
                    fingerprint_data=fingerprint_data,
                )
                devices.append(device)

                logger.debug(
                    f"Generated device {device.name} with fingerprint "
                    f"{fingerprint_model or 'none'} (vendor={vendor})"
                )

        return devices

    def _generate_zones(
        self,
        template: dict[str, Any],
        devices: list[GeneratedDevice],
    ) -> list[dict[str, Any]]:
        """Generate zone configurations.

        Args:
            template: Vertical template
            devices: Generated devices

        Returns:
            List of zone configurations
        """
        zones = []

        for zone_name in template["zones"]:
            zone_devices = [d for d in devices if d.zone == zone_name]
            zones.append({
                "name": zone_name,
                "device_count": len(zone_devices),
                "device_ids": [d.device_id for d in zone_devices],
            })

        return zones

    def _generate_flows(
        self,
        devices: list[GeneratedDevice],
        template: dict[str, Any],
    ) -> list[GeneratedFlow]:
        """Generate traffic flows between devices.

        Args:
            devices: Generated devices
            template: Vertical template

        Returns:
            List of generated flows
        """
        flows = []

        # Find controllers (PLCs, RTUs)
        controllers = [d for d in devices if d.device_type in ["plc", "rtu"]]
        field_devices = [d for d in devices if d.device_type not in ["plc", "rtu", "hmi"]]
        hmis = [d for d in devices if d.device_type == "hmi"]

        poll_intervals = template["poll_intervals_ms"]

        # Controller to field device flows
        for controller in controllers:
            # Each controller polls several field devices
            import random
            target_count = min(len(field_devices), random.randint(3, 10))
            targets = random.sample(field_devices, target_count) if field_devices else []

            for target in targets:
                # Find common protocol
                common = set(controller.protocols) & set(target.protocols)
                protocol = list(common)[0] if common else controller.protocols[0]

                flow = GeneratedFlow(
                    flow_id=str(uuid.uuid4()),
                    source_device_id=controller.device_id,
                    destination_device_id=target.device_id,
                    protocol=protocol,
                    poll_interval_ms=poll_intervals.get("normal", 1000),
                    description=f"{controller.name} polling {target.name}",
                )
                flows.append(flow)

        # HMI to controller flows
        for hmi in hmis:
            for controller in controllers[:3]:  # HMI connects to a few controllers
                common = set(hmi.protocols) & set(controller.protocols)
                protocol = list(common)[0] if common else "modbus_tcp"

                flow = GeneratedFlow(
                    flow_id=str(uuid.uuid4()),
                    source_device_id=hmi.device_id,
                    destination_device_id=controller.device_id,
                    protocol=protocol,
                    poll_interval_ms=poll_intervals.get("slow", 2000),
                    description=f"{hmi.name} monitoring {controller.name}",
                )
                flows.append(flow)

        return flows

    def _generate_ip(self, zone: str) -> str:
        """Generate an IP address for a zone.

        Args:
            zone: Zone name

        Returns:
            IP address string
        """
        # Zone-based subnets
        zone_subnets = {
            "process_control": "10.10.1",
            "safety": "10.10.2",
            "enterprise": "10.10.100",
            "scada": "10.20.1",
            "field": "10.20.10",
            "corporate": "10.20.100",
            "substation": "10.30.1",
            "control_center": "10.30.100",
            "wellhead": "10.40.1",
            "pipeline": "10.40.10",
            "refinery": "10.40.20",
            "control_room": "10.40.100",
        }

        subnet = zone_subnets.get(zone, "192.168.1")
        ip = f"{subnet}.{self._ip_counter}"
        self._ip_counter += 1
        if self._ip_counter > 254:
            self._ip_counter = 1

        return ip

    def _generate_mac(self, vendor: str | None) -> str:
        """Generate a MAC address with vendor OUI.

        Args:
            vendor: Vendor name

        Returns:
            MAC address string
        """
        # Vendor OUI prefixes
        vendor_ouis = {
            "rockwell": "00:00:BC",
            "siemens": "00:0E:8C",
            "schneider": "00:00:54",
            "abb": "00:20:99",
            "honeywell": "00:60:35",
            "emerson": "00:A0:F8",
            "ge": "00:14:49",
        }

        oui = vendor_ouis.get(vendor, "00:00:00")

        # Generate NIC portion
        nic = [
            (self._mac_counter >> 16) & 0xFF,
            (self._mac_counter >> 8) & 0xFF,
            self._mac_counter & 0xFF,
        ]
        self._mac_counter += 1

        return f"{oui}:{nic[0]:02X}:{nic[1]:02X}:{nic[2]:02X}"

    def _generate_mac_with_oui(self, oui: str) -> str:
        """Generate a MAC address with a specific OUI prefix.

        Args:
            oui: OUI prefix (e.g., "00:0E:8C")

        Returns:
            MAC address string
        """
        # Generate NIC portion using counter for uniqueness
        nic = [
            (self._mac_counter >> 16) & 0xFF,
            (self._mac_counter >> 8) & 0xFF,
            self._mac_counter & 0xFF,
        ]
        self._mac_counter += 1

        return f"{oui}:{nic[0]:02X}:{nic[1]:02X}:{nic[2]:02X}"

    def to_scenario_dict(self, scenario: GeneratedScenario) -> dict[str, Any]:
        """Convert a generated scenario to a dictionary for API response.

        Args:
            scenario: Generated scenario

        Returns:
            Dictionary representation
        """
        return {
            "id": scenario.scenario_id,
            "name": scenario.name,
            "description": scenario.description,
            "vertical": scenario.vertical,
            "duration_ms": scenario.duration_ms,
            "devices": [
                {
                    "id": d.device_id,
                    "type": d.device_type,
                    "name": d.name,
                    "vendor": d.vendor,
                    "model": d.model,
                    "ip_address": d.ip_address,
                    "mac_address": d.mac_address,
                    "zone": d.zone,
                    "protocols": d.protocols,
                    # Fingerprint data for hyper-realistic traffic
                    "fingerprint_model": d.fingerprint_model,
                    "error_config": d.error_config,
                    # Include response timing from fingerprint (if available)
                    "response_timing": (
                        d.fingerprint_data.get("response_timing")
                        if d.fingerprint_data else None
                    ),
                    # Include TCP stack characteristics (if available)
                    "tcp_stack": (
                        d.fingerprint_data.get("tcp_stack")
                        if d.fingerprint_data else None
                    ),
                }
                for d in scenario.devices
            ],
            "flows": [
                {
                    "id": f.flow_id,
                    "source_device_id": f.source_device_id,
                    "destination_device_id": f.destination_device_id,
                    "protocol": f.protocol,
                    "poll_interval_ms": f.poll_interval_ms,
                    "description": f.description,
                }
                for f in scenario.flows
            ],
            "zones": scenario.zones,
            "metadata": scenario.metadata,
        }

    def suggest_vertical(self, description: str) -> dict[str, Any]:
        """Suggest an industry vertical based on description.

        Args:
            description: Natural language description

        Returns:
            Suggested vertical with confidence
        """
        entities = self._extract_entities(description)
        vertical = self._determine_vertical(entities, description)
        template = VERTICAL_TEMPLATES[vertical]

        return {
            "vertical": vertical,
            "name": template["name"],
            "description": template["description"],
            "typical_protocols": template["protocols"],
            "confidence": 0.8,
        }
