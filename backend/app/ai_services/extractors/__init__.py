"""Protocol-specific extractors for deep PCAP analysis."""

from app.ai_services.extractors.base import (
    ProtocolExtractor,
    ExtractedPacketInfo,
    ExtractedFlowInfo,
)
from app.ai_services.extractors.fingerprint_extractor import (
    FingerprintExtractor,
    TCPSignature,
    OUIMapper,
)
from app.ai_services.extractors.snmp_vendor import (
    extract_vendor_from_snmp,
    extract_model_from_snmp,
    get_vendor_confidence,
    vendor_from_enterprise_oid,
    vendor_from_sysdescr,
    ENTERPRISE_OID_VENDORS,
)
from app.ai_services.extractors.modbus_extractor import ModbusExtractor
from app.ai_services.extractors.s7_extractor import S7Extractor
from app.ai_services.extractors.bacnet_extractor import BACnetExtractor
from app.ai_services.extractors.ethernet_ip_extractor import EtherNetIPExtractor
from app.ai_services.extractors.profinet_extractor import ProfinetExtractor
from app.ai_services.extractors.opc_ua_extractor import OpcUaExtractor
from app.ai_services.extractors.sequence_learner import SequenceLearner

__all__ = [
    "ProtocolExtractor",
    "ExtractedPacketInfo",
    "ExtractedFlowInfo",
    "FingerprintExtractor",
    "TCPSignature",
    "OUIMapper",
    # SNMP vendor detection
    "extract_vendor_from_snmp",
    "extract_model_from_snmp",
    "get_vendor_confidence",
    "vendor_from_enterprise_oid",
    "vendor_from_sysdescr",
    "ENTERPRISE_OID_VENDORS",
    # Protocol extractors
    "ModbusExtractor",
    "S7Extractor",
    "BACnetExtractor",
    "EtherNetIPExtractor",
    "ProfinetExtractor",
    "OpcUaExtractor",
    "SequenceLearner",
]
