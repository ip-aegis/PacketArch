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

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY
from app.protocol_engines.vendor_oui import generate_mac_address, get_oui_for_vendor
from app.services.device_templates import (
    get_fingerprint_by_vendor_model,
    get_fingerprints_by_vendor,
    get_all_templates,
    DEVICE_TEMPLATES,
)
from app.ai_services.nl_parser import extract_device_counts

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
        "protocols": ["ethernet_ip", "profinet", "modbus_tcp", "pccc", "codesys", "ethercat"],
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
        "protocols": ["iec61850", "iec_104", "dnp3", "modbus_tcp"],
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
        "protocols": ["modbus_tcp", "opc_ua", "dcs"],
        "zones": ["wellhead", "pipeline", "refinery", "control_room"],
        "poll_intervals_ms": {"fast": 500, "normal": 2000, "slow": 10000},
    },
    "transportation": {
        "name": "Transportation ITS",
        "description": "Traffic management, toll systems, tunnels, and highway operations",
        "typical_devices": {
            "traffic_controller": {
                "count_range": (2, 20),
                "vendors": ["econolite", "siemens_its", "mccain"],
                "fingerprint_models": {
                    "econolite": "Cobalt ATC",
                    "siemens_its": "M60",
                    "mccain": "2070 ATC",
                },
                "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},
            },
            "dms": {
                "count_range": (1, 10),
                "vendors": ["daktronics"],
                "fingerprint_models": {
                    "daktronics": "Venus 1500",
                },
                "error_config": {"exception_rate": 0.002, "timeout_rate": 0.003},
            },
            "rsu": {
                "count_range": (2, 20),
                "vendors": ["q-free", "kapsch"],
                "fingerprint_models": {
                    "q-free": "RSU 5000",
                    "kapsch": "TCS 2000",
                },
                "error_config": {"exception_rate": 0.001, "timeout_rate": 0.001},
            },
            "radar_sensor": {
                "count_range": (5, 50),
                "vendors": ["wavetronix"],
                "fingerprint_models": {
                    "wavetronix": "SmartSensor HD",
                },
                "error_config": {"exception_rate": 0.002, "timeout_rate": 0.003},
            },
            "weather_station": {
                "count_range": (1, 10),
                "vendors": ["vaisala"],
                "fingerprint_models": {
                    "vaisala": "RWIS500",
                },
            },
            "camera": {
                "count_range": (5, 30),
                "vendors": ["axis", "pelco", "hikvision"],
                "fingerprint_models": {
                    "axis": "P1455-LE",
                    "pelco": "Spectra Enhanced",
                    "hikvision": "DS-2CD7A26G0/P",
                },
            },
            "thermal_sensor": {
                "count_range": (2, 20),
                "vendors": ["flir"],
                "fingerprint_models": {
                    "flir": "TrafiOne",
                },
            },
            "lighting_controller": {
                "count_range": (2, 10),
                "vendors": ["siemens_its"],
                "fingerprint_models": {
                    "siemens_its": "TCS-LIGHT",
                },
            },
            "ventilation_controller": {
                "count_range": (1, 5),
                "vendors": ["siemens_its"],
                "fingerprint_models": {
                    "siemens_its": "TCS-VENT",
                },
            },
        },
        "protocols": ["snmp"],
        "zones": ["tmc", "field", "corridor", "tunnel"],
        "poll_intervals_ms": {"fast": 500, "normal": 2000, "slow": 10000},
    },
    "building_automation": {
        "name": "Building Automation",
        "description": "Commercial buildings, campus BMS, data centers with HVAC, lighting, and metering",
        "typical_devices": {
            "bms_controller": {
                "count_range": (1, 5),
                "vendors": ["honeywell", "johnson_controls", "schneider", "siemens"],
                "fingerprint_models": {
                    "honeywell": "Spyder",
                    "johnson_controls": "FEC",
                    "schneider": "SmartStruxure",
                    "siemens": "Desigo CC",
                },
                "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
            },
            "vav_controller": {
                "count_range": (5, 50),
                "vendors": ["honeywell", "johnson_controls", "tridium"],
                "fingerprint_models": {
                    "honeywell": "Spyder",
                    "johnson_controls": "VAV Controller",
                    "tridium": "JACE 8000",
                },
                "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
            },
            "chiller_controller": {
                "count_range": (1, 5),
                "vendors": ["trane", "carrier", "york"],
                "fingerprint_models": {
                    "trane": "Tracer SC+",
                    "carrier": "i-Vu",
                    "york": "YorkWorks",
                },
                "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
            },
            "lighting_controller": {
                "count_range": (2, 20),
                "vendors": ["lutron", "philips", "acuity"],
                "fingerprint_models": {
                    "lutron": "Quantum",
                    "philips": "Dynalite",
                    "acuity": "nLight",
                },
            },
            "power_meter": {
                "count_range": (5, 30),
                "vendors": ["schneider", "siemens", "eaton"],
                "fingerprint_models": {
                    "schneider": "PM8000",
                    "siemens": "SENTRON PAC",
                    "eaton": "PXM",
                },
            },
            "fire_panel": {
                "count_range": (1, 3),
                "vendors": ["notifier", "simplex", "est"],
                "fingerprint_models": {
                    "notifier": "NFS2-3030",
                    "simplex": "4100ES",
                    "est": "EST4",
                },
            },
        },
        "protocols": ["bacnet", "modbus_tcp"],
        "zones": ["bms", "hvac", "lighting", "metering", "fire_life_safety"],
        "poll_intervals_ms": {"fast": 1000, "normal": 5000, "slow": 30000},
    },
}

# TCP/UDP protocols that generate IP traffic (required for Cyber Vision discovery)
# Layer 2 protocols like PROFINET don't include IP addresses in packets
TCP_UDP_PROTOCOLS = {
    # Core industrial
    "modbus_tcp", "modbus", "modbus_rtu", "ethernet_ip", "s7comm", "s7comm_plus",
    # Building automation and network management
    "bacnet", "snmp", "ntcip",
    # SCADA/utility
    "opc_ua", "dnp3", "iec104", "iec_104", "iec61850",
    # Vendor-specific
    "fins", "slmp", "codesys", "pccc",
    # Specialized
    "fanuc", "wmi", "dcs",
}

# Device type to protocol mapping
# IMPORTANT: First protocol in list should be TCP/UDP for flow generation
# Layer 2 protocols (profinet) should come after TCP/UDP protocols
DEVICE_PROTOCOL_MAP = {
    # Core industrial PLCs
    "plc": ["modbus_tcp", "ethernet_ip", "profinet"],  # TCP/UDP first
    "rtu": ["modbus_tcp", "dnp3"],
    "hmi": ["modbus_tcp", "ethernet_ip"],  # TCP/UDP first
    "drive": ["modbus_tcp", "ethernet_ip", "profinet"],  # TCP/UDP first
    "robot": ["ethernet_ip", "profinet"],  # TCP/UDP first
    # Energy/utility devices
    "ied": ["iec61850", "iec_104", "dnp3"],  # IEC 61850 for substations
    "pmu": ["iec_104"],
    "meter": ["modbus_tcp", "dnp3"],
    "sensor": ["modbus_tcp"],
    # Process industry
    "pump_controller": ["modbus_tcp", "ethernet_ip"],
    "flow_meter": ["modbus_tcp"],
    "level_sensor": ["modbus_tcp"],
    "flow_computer": ["modbus_tcp", "opc_ua"],
    "compressor_controller": ["modbus_tcp", "ethernet_ip"],
    # Transportation device types - SNMP/NTCIP based
    "traffic_controller": ["snmp"],
    "dms": ["snmp"],
    "rsu": ["snmp"],
    "radar_sensor": ["snmp"],
    "lidar_sensor": ["snmp"],
    "weather_station": ["snmp"],
    "camera": ["snmp"],
    "thermal_sensor": ["snmp"],
    "ventilation_controller": ["snmp"],
    "toll_controller": ["snmp"],
    "anpr_camera": ["snmp"],
    "video_detector": ["snmp"],
    # Building Automation devices
    "bms_controller": ["bacnet", "modbus_tcp"],
    "vav_controller": ["bacnet", "modbus_tcp"],
    "chiller_controller": ["bacnet", "modbus_tcp"],
    "lighting_controller": ["bacnet", "modbus_tcp"],
    "power_meter": ["modbus_tcp", "bacnet"],
    "fire_panel": ["bacnet"],
    # CNC and motion control
    "cnc_machine": ["fanuc", "ethernet_ip"],
    # DCS systems
    "dcs_controller": ["dcs", "opc_ua", "modbus_tcp"],
    # Safety systems
    "safety_plc": ["iec61850", "profinet", "ethernet_ip"],
    # Vendor-specific PLCs
    "omron_plc": ["fins", "ethernet_ip"],
    "mitsubishi_plc": ["slmp", "ethernet_ip"],
    "rockwell_legacy_plc": ["pccc", "ethernet_ip"],
    "codesys_plc": ["codesys", "modbus_tcp"],
    "ethercat_slave": ["ethercat"],
    # Remote access and cloud devices
    "jump_server": ["https"],
    "remote_gateway": ["https", "modbus_tcp"],
    "cloud_connector": ["https"],
    "ewon_gateway": ["https", "modbus_tcp"],
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
    # Transportation device types
    "traffic_controller": ["traffic controller", "signal controller", "atc", "traffic signal", "intersection controller"],
    "dms": ["dms", "dynamic message sign", "variable message sign", "vms", "message board", "highway sign"],
    "rsu": ["rsu", "roadside unit", "v2x", "connected vehicle", "dsrc"],
    "radar_sensor": ["radar", "vehicle detector", "smartsensor", "traffic sensor"],
    "lidar_sensor": ["lidar", "laser scanner", "3d scanner"],
    "weather_station": ["weather station", "rwis", "environmental sensor", "roadway weather"],
    "camera": ["camera", "cctv", "surveillance", "its camera", "traffic camera"],
    "thermal_sensor": ["thermal", "infrared", "flir", "thermal detector"],
    "lighting_controller": ["lighting controller", "tunnel lighting", "bridge lighting"],
    "ventilation_controller": ["ventilation", "tunnel fan", "air handling"],
    "toll_controller": ["toll", "tolling", "etc", "electronic toll"],
    "anpr_camera": ["anpr", "lpr", "license plate", "plate reader"],
    # Building Automation device types
    "bms_controller": ["bms", "building management", "building controller", "bas", "building automation"],
    "vav_controller": ["vav", "variable air volume", "air handler", "ahu"],
    "chiller_controller": ["chiller", "chiller plant", "cooling tower"],
    "power_meter": ["power meter", "energy meter", "electrical meter", "submeter"],
    "fire_panel": ["fire panel", "fire alarm", "facp", "fire control panel"],
    # CNC and motion control
    "cnc_machine": ["cnc", "machining center", "lathe", "mill", "fanuc"],
    # DCS controllers
    "dcs_controller": ["dcs", "distributed control", "deltav", "experion", "centum"],
    # Safety systems
    "safety_plc": ["safety plc", "safety controller", "sis", "triconex", "tricon"],
    # Remote access and cloud devices
    "jump_server": ["jump server", "jump box", "bastion", "bastion host", "remote desktop server"],
    "remote_gateway": ["remote gateway", "remote access gateway", "vpn gateway", "secure gateway", "industrial gateway"],
    "cloud_connector": ["cloud connector", "iot gateway", "cloud gateway", "azure iot", "aws iot", "iot hub"],
    "ewon_gateway": ["ewon", "talk2m", "hms ewon", "flexy", "cosy", "ewon flexy", "ewon cosy"],
}

VENDOR_KEYWORDS = {
    "rockwell": ["rockwell", "allen-bradley", "allen bradley", "ab", "logix", "compactlogix", "controllogix"],
    "siemens": ["siemens", "s7", "simatic", "tia portal", "profinet"],
    "schneider": ["schneider", "modicon", "m580", "m340", "unity"],
    "abb": ["abb", "ac500", "freelance"],
    "honeywell": ["honeywell", "experion", "c300"],
    "emerson": ["emerson", "deltav", "ovation", "roc"],
    "ge": ["ge", "general electric", "mark vi", "rx3i"],
    # Transportation vendors
    "econolite": ["econolite", "cobalt", "asc/3", "autoscope"],
    "siemens_its": ["siemens its", "m60", "atc-940", "siemens traffic"],
    "mccain": ["mccain", "170e", "2070", "atms"],
    "wavetronix": ["wavetronix", "smartsensor", "advance"],
    "flir": ["flir", "trafione", "trafisense", "thermal"],
    "vaisala": ["vaisala", "rwis", "weather sensor"],
    "daktronics": ["daktronics", "venus", "vanguard"],
    "axis": ["axis", "axis communications"],
    "pelco": ["pelco", "spectra"],
    "hikvision": ["hikvision", "ds-"],
    "bosch": ["bosch", "mic ip"],
    "kapsch": ["kapsch", "traffics", "tcs"],
    "q-free": ["q-free", "qfree", "tolling"],
    # Building Automation vendors
    "johnson_controls": ["johnson controls", "jci", "metasys"],
    "tridium": ["tridium", "niagara", "jace"],
    "trane": ["trane", "tracer"],
    "carrier": ["carrier", "i-vu"],
    "york": ["york", "yorkworks"],
    "lutron": ["lutron", "quantum", "homeworks"],
    "acuity": ["acuity", "nlight"],
    "notifier": ["notifier", "nfs"],
    "simplex": ["simplex", "simplex 4100"],
    "est": ["edwards", "est", "est4"],
    "eaton": ["eaton", "powerware"],
    # Japanese/Asian PLC vendors
    "omron": ["omron", "cj2", "nj", "nx", "sysmac"],
    "mitsubishi": ["mitsubishi", "melsec", "iq-r", "iq-f", "fx5"],
    # Motion control vendors
    "beckhoff": ["beckhoff", "twincat", "ethercat"],
    "fanuc": ["fanuc", "focas", "cnc"],
    # DCS vendors
    "yokogawa": ["yokogawa", "centum", "prosafe"],
    # Remote access vendors
    "hms": ["hms", "ewon", "talk2m", "anybus", "flexy", "cosy"],
    "microsoft": ["microsoft", "windows server", "rdp", "remote desktop"],
    "teamviewer": ["teamviewer", "team viewer"],
}

PROTOCOL_KEYWORDS = {
    # Core industrial
    "modbus_tcp": ["modbus", "modbus tcp", "modbus/tcp"],
    "modbus_rtu": ["modbus rtu", "serial modbus", "rs485 modbus"],
    "ethernet_ip": ["ethernet/ip", "ethernet-ip", "enip", "cip"],
    "profinet": ["profinet", "pn io", "profinet io"],
    "s7comm": ["s7", "s7comm", "step 7", "simatic"],
    # SCADA/utility
    "opc_ua": ["opc ua", "opc-ua", "opcua", "opc unified"],
    "dnp3": ["dnp3", "dnp 3", "distributed network protocol"],
    "iec_104": ["iec 104", "iec104", "iec 60870-5-104", "iec-104"],
    "iec61850": ["iec 61850", "iec61850", "goose", "mms", "sampled values", "sv"],
    # Building automation and network
    "bacnet": ["bacnet", "bacnet/ip", "bacnet ip", "bac net"],
    "snmp": ["snmp", "ntcip", "mib", "simple network management"],
    "lldp": ["lldp", "link layer discovery"],
    "cdp": ["cdp", "cisco discovery"],
    # Vendor-specific
    "pccc": ["pccc", "df1", "allen-bradley legacy", "plc-5", "slc-500", "slc 500"],
    "codesys": ["codesys", "codesys v3", "wago plc", "festo plc", "3s software"],
    "fins": ["fins", "omron", "cj2", "nj", "nx", "sysmac"],
    "slmp": ["slmp", "melsec", "mitsubishi plc", "iq-r", "iq-f", "melsoft"],
    "ethercat": ["ethercat", "beckhoff", "motion control", "twincat"],
    # DCS and specialized
    "dcs": ["dcs", "deltav", "experion", "centum", "triconex", "distributed control system"],
    "fanuc": ["fanuc", "focas", "cnc", "machining center"],
    "wmi": ["wmi", "windows management", "wmic"],
}

VERTICAL_KEYWORDS = {
    "manufacturing": ["manufacturing", "factory", "assembly", "production line", "discrete", "automotive"],
    "water": ["water", "wastewater", "treatment plant", "pumping station", "utility"],
    "energy": ["power", "energy", "substation", "grid", "generation", "transmission"],
    "oil_gas": ["oil", "gas", "pipeline", "refinery", "petrochemical", "upstream", "downstream"],
    "transportation": [
        "transportation", "traffic", "highway", "freeway", "interstate", "toll", "tunnel", "bridge",
        "its", "intelligent transportation", "tmc", "traffic management", "intersection", "corridor",
        "roadway", "arterial", "signal", "dms", "ramp meter", "connected vehicle", "v2x",
    ],
    "building_automation": [
        "building", "building automation", "bms", "bas", "hvac", "commercial building", "campus",
        "data center", "facility", "smart building", "bacs", "bacnet", "chiller", "ahu", "vav",
        "lighting control", "metering", "energy management",
    ],
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
    6. Assigns IP/MAC addresses using zone scheme with proper /16 allocation
    """

    def __init__(self, range_index: int = 1):
        """Initialize the scenario generator.

        Args:
            range_index: The scenario's /16 IP range index (1-254)
        """
        self.range_index = range_index
        self._ip_counter = 10  # Start at .10 like templates do
        self._mac_counter = 1
        self._zone_subnet_map: dict[str, int] = {}  # zone_name -> subnet_offset

    def _filter_protocols_by_fingerprint(
        self,
        protocols: list[str],
        fingerprint_data: dict | None,
        device_name: str,
    ) -> list[str]:
        """Filter protocols to only those supported by the fingerprint identity data.

        This prevents protocol_identity_mismatch validation errors at deploy time.

        Args:
            protocols: List of requested protocols
            fingerprint_data: Device fingerprint data with identity fields
            device_name: Device name for logging

        Returns:
            List of protocols that have valid identity support in the fingerprint
        """
        if not protocols:
            return []

        # If no fingerprint data at all, we cannot assign protocols that require identities
        if not fingerprint_data:
            logger.warning(
                f"Device '{device_name}': No fingerprint data - device will have no protocols"
            )
            return []

        validated = []
        removed = []

        for protocol in protocols:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)

            if identity_key:
                # Protocol requires identity - check if fingerprint has it
                identity = fingerprint_data.get(identity_key)
                if identity and isinstance(identity, dict) and len(identity) > 0:
                    validated.append(protocol)
                else:
                    removed.append(protocol)
            else:
                # Protocol doesn't require identity (e.g., http, ssh) - allow it
                validated.append(protocol)

        # Always log the filtering result for debugging
        if removed:
            logger.info(
                f"Device '{device_name}': Removed protocols {removed} (no identity in fingerprint). "
                f"Kept: {validated}"
            )
        else:
            logger.debug(
                f"Device '{device_name}': All protocols validated: {validated}"
            )

        return validated

    def generate_from_description(
        self,
        description: str,
        name: str | None = None,
        duration_ms: int = 300000,
        preferred_vendors: list[str] | None = None,
        preferred_protocols: list[str] | None = None,
        vertical: str | None = None,
        total_device_count: int | None = None,
        device_counts: dict[str, int] | None = None,
    ) -> GeneratedScenario:
        """Generate a scenario from natural language description.

        Args:
            description: Natural language scenario description
            name: Optional scenario name
            duration_ms: Scenario duration in milliseconds
            preferred_vendors: Optional list of preferred vendors (e.g., ["rockwell", "siemens"])
            preferred_protocols: Optional list of preferred protocols (e.g., ["modbus_tcp", "ethernet_ip"])
            vertical: Optional vertical override (e.g., "manufacturing", "water")
            total_device_count: Optional target total device count (AI decides the mix)
            device_counts: Optional specific counts per device type (e.g., {"plc": 5, "hmi": 2})

        Returns:
            Generated scenario
        """
        # Reset counters for new scenario
        self._ip_counter = 10
        self._zone_subnet_map = {}

        # Extract entities
        entities = self._extract_entities(description)

        # Determine device count constraints
        # Priority: explicit params > NL parsing
        max_devices = None
        explicit_device_counts: dict[str, int] | None = None

        if device_counts:
            # Manual mode: user specified exact counts per device type
            explicit_device_counts = device_counts
            max_devices = sum(device_counts.values())
            logger.info(f"Using explicit device counts: {device_counts} (total: {max_devices})")
        elif total_device_count:
            # AI decides mix mode: user specified total, AI decides distribution
            max_devices = total_device_count
            logger.info(f"User requested total {max_devices} devices (AI decides mix)")
        else:
            # Fallback: parse device counts from natural language
            parsed_counts = extract_device_counts(description)
            if parsed_counts["has_explicit_total"]:
                max_devices = parsed_counts["total_requested"]
                logger.info(f"NL parser: max {max_devices} devices")
            elif parsed_counts["total_requested"] > 0:
                max_devices = parsed_counts["total_requested"]
                explicit_device_counts = parsed_counts.get("device_counts", {})
                logger.info(f"NL parser: implied max {max_devices} devices")

        # Determine vertical (use override if provided)
        if vertical and vertical in VERTICAL_TEMPLATES:
            determined_vertical = vertical
        else:
            determined_vertical = self._determine_vertical(entities, description)
        template = VERTICAL_TEMPLATES.get(determined_vertical, VERTICAL_TEMPLATES["manufacturing"])

        # Apply vendor constraints if provided
        if preferred_vendors:
            logger.info(f"Applying vendor constraints: {preferred_vendors}")
            template = self._apply_vendor_constraints(template, preferred_vendors)

        # Apply protocol constraints if provided
        if preferred_protocols:
            logger.info(f"Applying protocol constraints: {preferred_protocols}")
            template = self._apply_protocol_constraints(template, preferred_protocols)

        # Generate devices with limit enforcement
        devices = self._generate_devices(
            entities,
            template,
            max_devices=max_devices,
            parsed_device_counts=explicit_device_counts or {},
        )

        # Generate zones
        zones = self._generate_zones(template, devices)

        # Generate flows
        flows = self._generate_flows(devices, template)

        # Create scenario
        scenario = GeneratedScenario(
            scenario_id=str(uuid.uuid4()),
            name=name or f"{template['name']} Scenario",
            description=description,
            vertical=determined_vertical,
            devices=devices,
            flows=flows,
            zones=zones,
            duration_ms=duration_ms,
            metadata={
                "extracted_entities": [
                    {"type": e.entity_type, "value": e.value, "confidence": e.confidence}
                    for e in entities
                ],
                "template_used": determined_vertical,
                "range_index": self.range_index,
                "ip_range": f"10.{self.range_index}.0.0/16",
            },
        )

        logger.info(
            f"Generated scenario '{scenario.name}' with "
            f"{len(devices)} devices and {len(flows)} flows"
        )
        return scenario

    def _apply_vendor_constraints(
        self,
        template: dict[str, Any],
        preferred_vendors: list[str],
    ) -> dict[str, Any]:
        """Apply vendor constraints to a template.

        Filters the template's device vendor lists to only include
        vendors from the preferred list.

        Args:
            template: Original template dictionary
            preferred_vendors: List of preferred vendor names (lowercase)

        Returns:
            Modified template with filtered vendors
        """
        import copy
        modified = copy.deepcopy(template)
        preferred_lower = [v.lower() for v in preferred_vendors]

        for device_type, config in modified.get("typical_devices", {}).items():
            if "vendors" in config:
                # Filter to only preferred vendors
                filtered = [v for v in config["vendors"] if v.lower() in preferred_lower]
                if filtered:
                    config["vendors"] = filtered
                # If no overlap, keep original to avoid empty list

        return modified

    def _apply_protocol_constraints(
        self,
        template: dict[str, Any],
        preferred_protocols: list[str],
    ) -> dict[str, Any]:
        """Apply protocol constraints to a template.

        Filters the template's protocol list to only include
        protocols from the preferred list.

        Args:
            template: Original template dictionary
            preferred_protocols: List of preferred protocol names

        Returns:
            Modified template with filtered protocols
        """
        import copy
        modified = copy.deepcopy(template)

        # Normalize protocol names (handle variations like "modbus_tcp" vs "modbus tcp")
        preferred_normalized = []
        for p in preferred_protocols:
            normalized = p.lower().replace(" ", "_").replace("-", "_")
            preferred_normalized.append(normalized)

        if "protocols" in modified:
            # Filter to only preferred protocols
            filtered = [
                p for p in modified["protocols"]
                if p.lower().replace(" ", "_").replace("-", "_") in preferred_normalized
            ]
            if filtered:
                modified["protocols"] = filtered
            # If no overlap, keep original to avoid empty list

        return modified

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
        max_devices: int | None = None,
        parsed_device_counts: dict[str, int] | None = None,
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
            max_devices: Maximum total devices to generate (user-specified limit)
            parsed_device_counts: Device counts parsed from natural language (e.g., {"plc": 5, "sensor": 10})

        Returns:
            List of generated devices with fingerprint data
        """
        import random

        devices = []

        # Use parsed device counts if provided, otherwise extract from entities
        device_counts = parsed_device_counts.copy() if parsed_device_counts else {}
        if not device_counts:
            for e in entities:
                if e.entity_type == "device_count":
                    device_type, count = e.value.split(":")
                    device_counts[device_type] = int(count)

        # Get preferred vendors
        preferred_vendors = [e.value for e in entities if e.entity_type == "vendor"]

        # Calculate planned device counts per type
        planned_counts = {}
        template_ranges = {}  # Store min/max for scaling

        for device_type, config in template["typical_devices"].items():
            min_count, max_count = config["count_range"]
            template_ranges[device_type] = (min_count, max_count)

            if device_type in device_counts:
                # User specified exact count for this type
                planned_counts[device_type] = device_counts[device_type]
            elif max_devices is not None:
                # Start with minimum, will scale up/down later
                planned_counts[device_type] = min_count
            else:
                # No target, use random within range
                planned_counts[device_type] = random.randint(min_count, max_count)

        # Scale to meet max_devices target
        total_planned = sum(planned_counts.values())

        if max_devices is not None and total_planned != max_devices:
            critical_types = {"plc", "rtu", "hmi"}

            if total_planned < max_devices:
                # Scale UP to meet target
                logger.info(f"Scaling up from {total_planned} to {max_devices} devices")
                devices_to_add = max_devices - total_planned

                # Calculate how much room each type has to grow (up to its max)
                growth_room = {}
                for dtype, count in planned_counts.items():
                    _, max_count = template_ranges.get(dtype, (0, count))
                    growth_room[dtype] = max(0, max_count - count)

                total_growth_room = sum(growth_room.values())

                if total_growth_room > 0:
                    # Distribute additional devices proportionally based on growth room
                    for dtype in planned_counts.keys():
                        if growth_room[dtype] > 0:
                            # Proportion of growth this type should get
                            proportion = growth_room[dtype] / total_growth_room
                            additional = int(devices_to_add * proportion)
                            # Don't exceed max for this type
                            _, max_count = template_ranges.get(dtype, (0, 100))
                            planned_counts[dtype] = min(planned_counts[dtype] + additional, max_count)

                    # If still under target, add to types with remaining room
                    remaining = max_devices - sum(planned_counts.values())
                    while remaining > 0:
                        added_any = False
                        for dtype in planned_counts.keys():
                            if remaining <= 0:
                                break
                            _, max_count = template_ranges.get(dtype, (0, 100))
                            if planned_counts[dtype] < max_count:
                                planned_counts[dtype] += 1
                                remaining -= 1
                                added_any = True
                        if not added_any:
                            # All types at max, can't add more
                            break

                logger.info(f"After scaling up: {planned_counts} (total: {sum(planned_counts.values())})")

            elif total_planned > max_devices:
                # Scale DOWN (existing logic)
                logger.info(f"Scaling down from {total_planned} to {max_devices} devices")
                scale_factor = max_devices / total_planned

                scaled_counts = {}
                for dtype, count in planned_counts.items():
                    scaled = max(1 if dtype in critical_types else 0, int(count * scale_factor))
                    scaled_counts[dtype] = scaled

                # If still over limit, reduce non-critical types further
                while sum(scaled_counts.values()) > max_devices:
                    non_critical = [(k, v) for k, v in scaled_counts.items() if k not in critical_types and v > 0]
                    if not non_critical:
                        critical = [(k, v) for k, v in scaled_counts.items() if v > 1]
                        if critical:
                            largest = max(critical, key=lambda x: x[1])
                            scaled_counts[largest[0]] -= 1
                        else:
                            break
                    else:
                        largest = max(non_critical, key=lambda x: x[1])
                        scaled_counts[largest[0]] -= 1

                planned_counts = scaled_counts
                logger.info(f"After scaling down: {planned_counts} (total: {sum(planned_counts.values())})")

        # Generate devices for each type
        for device_type, config in template["typical_devices"].items():
            # Use pre-calculated count
            count = planned_counts.get(device_type, 0)

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

            # Ensure at least one TCP/UDP protocol (for IP traffic generation)
            has_tcp_udp = any(p in TCP_UDP_PROTOCOLS for p in protocols)
            if not has_tcp_udp:
                # Add modbus_tcp as universal fallback for IP traffic
                protocols = protocols + ["modbus_tcp"]
                logger.info(f"Added modbus_tcp to {device_type} devices (had only Layer 2 protocols)")

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

            # Fallback: if no specific model, try to find ANY fingerprint for this vendor
            # This ensures devices have protocol identity data for traffic generation
            if not fingerprint_data and vendor and vendor != "generic":
                vendor_fps = get_fingerprints_by_vendor(vendor)
                if vendor_fps:
                    # Pick first available fingerprint for this vendor
                    fingerprint_data = vendor_fps[0]
                    fingerprint_model = fingerprint_data.get("model")
                    logger.debug(
                        f"Using fallback fingerprint {fingerprint_model} for {vendor} {device_type}"
                    )

            # Final fallback for generic/unknown vendors: use a common modbus-capable device
            # This ensures sensors and other generic devices can still generate traffic
            if not fingerprint_data:
                # Try Schneider for sensors/meters (good modbus support)
                fallback_vendors = ["schneider", "siemens", "honeywell"]
                for fallback_vendor in fallback_vendors:
                    vendor_fps = get_fingerprints_by_vendor(fallback_vendor)
                    if vendor_fps:
                        # Find one with modbus_identity
                        for fp in vendor_fps:
                            if fp.get("modbus_identity"):
                                fingerprint_data = fp
                                fingerprint_model = fp.get("model")
                                # Update vendor to match fingerprint
                                vendor = fallback_vendor
                                logger.info(
                                    f"Using generic fallback fingerprint {fingerprint_model} ({fallback_vendor}) for {device_type}"
                                )
                                break
                    if fingerprint_data:
                        break

            # Get error config from template or fingerprint
            error_config = config.get("error_config")
            if not error_config and fingerprint_data:
                error_behavior = fingerprint_data.get("error_behavior", {})
                if error_behavior:
                    error_config = {
                        "exception_rate": error_behavior.get("exception_probability", 0.001),
                        "timeout_rate": error_behavior.get("timeout_probability", 0.0005),
                    }

            # Filter protocols to only those supported by the fingerprint
            # This prevents protocol_identity_mismatch validation errors
            filtered_protocols = self._filter_protocols_by_fingerprint(
                protocols, fingerprint_data, f"{device_type.upper()}"
            )

            # If no fingerprint data, clear the fingerprint_model to avoid validation errors
            if not fingerprint_data:
                fingerprint_model = None

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
                    protocols=filtered_protocols,
                    fingerprint_model=fingerprint_model,
                    error_config=error_config,
                    fingerprint_data=fingerprint_data,
                )
                devices.append(device)

                logger.info(
                    f"Generated device {device.name}: vendor={vendor}, "
                    f"fingerprint_model={fingerprint_model or 'NONE'}, "
                    f"protocols={filtered_protocols}"
                )

        # Ensure at least 1 controller (PLC/RTU) exists for flow generation
        has_controller = any(d.device_type in ["plc", "rtu"] for d in devices)
        has_field_devices = any(d.device_type not in ["plc", "rtu", "hmi"] for d in devices)

        if not has_controller and has_field_devices and len(devices) > 0:
            logger.info("No controller devices found. Adding a PLC for flow generation.")
            # Add a PLC to enable proper flow generation
            plc_config = template["typical_devices"].get("plc", {})
            vendors = plc_config.get("vendors", ["rockwell", "siemens"])
            vendor = random.choice(vendors)
            protocols = template.get("protocols", ["modbus_tcp"])

            # Look up fingerprint for the fallback PLC
            fingerprint_models = plc_config.get("fingerprint_models", {})
            fallback_fingerprint_model = fingerprint_models.get(vendor)
            fallback_fingerprint_data = None

            if fallback_fingerprint_model:
                fallback_fingerprint_data = get_fingerprint_by_vendor_model(
                    vendor, fallback_fingerprint_model
                )

            # Try to find any fingerprint for the vendor if specific one not found
            if not fallback_fingerprint_data:
                vendor_fps = get_fingerprints_by_vendor(vendor)
                if vendor_fps:
                    fallback_fingerprint_data = vendor_fps[0]
                    fallback_fingerprint_model = fallback_fingerprint_data.get("model")

            # Filter protocols for the fallback PLC
            filtered_fallback_protocols = self._filter_protocols_by_fingerprint(
                protocols, fallback_fingerprint_data, "PLC-MAIN-001"
            )

            device = GeneratedDevice(
                device_id=str(uuid.uuid4()),
                device_type="plc",
                name="PLC-MAIN-001",
                vendor=vendor,
                model=fallback_fingerprint_model,
                ip_address=self._generate_ip(template["zones"][0]),
                mac_address=generate_mac_address(vendor=vendor, device_type="plc"),
                zone=template["zones"][0],
                protocols=filtered_fallback_protocols,
                fingerprint_model=fallback_fingerprint_model,
                error_config=plc_config.get("error_config"),
                fingerprint_data=fallback_fingerprint_data,
            )
            devices.insert(0, device)  # Add at beginning

        return devices

    def _generate_zones(
        self,
        template: dict[str, Any],
        devices: list[GeneratedDevice],
    ) -> list[dict[str, Any]]:
        """Generate zone configurations with proper subnet allocation.

        Each zone gets a /24 subnet within the scenario's /16 range.

        Args:
            template: Vertical template
            devices: Generated devices

        Returns:
            List of zone configurations with subnet info
        """
        zones = []

        for i, zone_name in enumerate(template["zones"]):
            zone_devices = [d for d in devices if d.zone == zone_name]
            subnet_offset = self._zone_subnet_map.get(zone_name, i)
            zones.append({
                "id": zone_name.lower().replace(" ", "_"),
                "name": zone_name,
                "subnet_offset": subnet_offset,
                "vlan": 100 + i * 10,
                "network": {
                    "subnet": f"10.{self.range_index}.{subnet_offset}.0/24",
                    "gateway": f"10.{self.range_index}.{subnet_offset}.1",
                    "subnet_offset": subnet_offset,
                },
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
        import random

        flows = []

        # Find controllers (PLCs, RTUs)
        controllers = [d for d in devices if d.device_type in ["plc", "rtu"]]
        field_devices = [d for d in devices if d.device_type not in ["plc", "rtu", "hmi"]]
        hmis = [d for d in devices if d.device_type == "hmi"]

        poll_intervals = template["poll_intervals_ms"]

        # Controller to field device flows
        for controller in controllers:
            # Each controller polls several field devices
            target_count = min(len(field_devices), random.randint(3, 10))
            targets = random.sample(field_devices, target_count) if field_devices else []

            for target in targets:
                # Find common TCP/UDP protocol (exclude Layer 2 like PROFINET)
                common = set(controller.protocols) & set(target.protocols)
                tcp_udp_common = common & TCP_UDP_PROTOCOLS
                if tcp_udp_common:
                    protocol = list(tcp_udp_common)[0]
                else:
                    # Fallback to any TCP/UDP protocol from either device
                    controller_tcp = set(controller.protocols) & TCP_UDP_PROTOCOLS
                    target_tcp = set(target.protocols) & TCP_UDP_PROTOCOLS
                    if controller_tcp:
                        protocol = list(controller_tcp)[0]
                    elif target_tcp:
                        protocol = list(target_tcp)[0]
                    else:
                        protocol = "modbus_tcp"  # Universal fallback

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
                # Find common TCP/UDP protocol
                common = set(hmi.protocols) & set(controller.protocols)
                tcp_udp_common = common & TCP_UDP_PROTOCOLS
                if tcp_udp_common:
                    protocol = list(tcp_udp_common)[0]
                else:
                    hmi_tcp = set(hmi.protocols) & TCP_UDP_PROTOCOLS
                    controller_tcp = set(controller.protocols) & TCP_UDP_PROTOCOLS
                    if hmi_tcp:
                        protocol = list(hmi_tcp)[0]
                    elif controller_tcp:
                        protocol = list(controller_tcp)[0]
                    else:
                        protocol = "modbus_tcp"

                flow = GeneratedFlow(
                    flow_id=str(uuid.uuid4()),
                    source_device_id=hmi.device_id,
                    destination_device_id=controller.device_id,
                    protocol=protocol,
                    poll_interval_ms=poll_intervals.get("slow", 2000),
                    description=f"{hmi.name} monitoring {controller.name}",
                )
                flows.append(flow)

        # FALLBACK: If no flows generated but we have 2+ devices, create peer flows
        if not flows and len(devices) >= 2:
            logger.warning(
                f"No controller devices found for flow generation. "
                f"Creating fallback peer-to-peer flows for {len(devices)} devices."
            )
            # Create flows between adjacent devices
            for i in range(len(devices) - 1):
                source = devices[i]
                target = devices[i + 1]

                # Find common TCP/UDP protocol (exclude Layer 2)
                common = set(source.protocols) & set(target.protocols)
                tcp_udp_common = common & TCP_UDP_PROTOCOLS
                if tcp_udp_common:
                    protocol = list(tcp_udp_common)[0]
                else:
                    source_tcp = set(source.protocols) & TCP_UDP_PROTOCOLS
                    target_tcp = set(target.protocols) & TCP_UDP_PROTOCOLS
                    if source_tcp:
                        protocol = list(source_tcp)[0]
                    elif target_tcp:
                        protocol = list(target_tcp)[0]
                    else:
                        protocol = "modbus_tcp"

                flow = GeneratedFlow(
                    flow_id=str(uuid.uuid4()),
                    source_device_id=source.device_id,
                    destination_device_id=target.device_id,
                    protocol=protocol,
                    poll_interval_ms=poll_intervals.get("normal", 1000),
                    description=f"{source.name} to {target.name}",
                )
                flows.append(flow)

            # Also create some reverse flows for bidirectional communication
            for i in range(0, len(devices) - 1, 2):  # Every other pair
                source = devices[i + 1]
                target = devices[i]

                common = set(source.protocols) & set(target.protocols)
                tcp_udp_common = common & TCP_UDP_PROTOCOLS
                if tcp_udp_common:
                    protocol = list(tcp_udp_common)[0]
                else:
                    source_tcp = set(source.protocols) & TCP_UDP_PROTOCOLS
                    target_tcp = set(target.protocols) & TCP_UDP_PROTOCOLS
                    if source_tcp:
                        protocol = list(source_tcp)[0]
                    elif target_tcp:
                        protocol = list(target_tcp)[0]
                    else:
                        protocol = "modbus_tcp"

                flow = GeneratedFlow(
                    flow_id=str(uuid.uuid4()),
                    source_device_id=source.device_id,
                    destination_device_id=target.device_id,
                    protocol=protocol,
                    poll_interval_ms=poll_intervals.get("slow", 2000),
                    description=f"{source.name} to {target.name} (response)",
                )
                flows.append(flow)

            logger.info(f"Created {len(flows)} fallback flows")

        return flows

    def _generate_ip(self, zone: str) -> str:
        """Generate an IP address within a zone's /24 subnet.

        Uses the scenario's allocated /16 range and the zone's subnet_offset
        to generate IPs in the format: 10.{range_index}.{subnet_offset}.{host}

        Args:
            zone: Zone name

        Returns:
            IP address string
        """
        # Get or assign subnet_offset for this zone
        if zone not in self._zone_subnet_map:
            self._zone_subnet_map[zone] = len(self._zone_subnet_map)

        subnet_offset = self._zone_subnet_map[zone]
        ip = f"10.{self.range_index}.{subnet_offset}.{self._ip_counter}"
        self._ip_counter += 1
        if self._ip_counter > 254:
            self._ip_counter = 10

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
            "abb": "00:21:99",
            "honeywell": "00:40:84",  # Honeywell Inc (verified IEEE)
            "emerson": "00:0D:3A",  # Emerson Network Power (verified IEEE)
            "ge": "00:09:45",  # GE Fanuc (verified IEEE)
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
