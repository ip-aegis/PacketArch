"""Anomaly template model for configurable traffic anomalies.

Anomaly templates define reusable anomaly patterns that can be injected
into traffic generation to simulate network issues, attacks, or equipment
malfunctions.
"""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Enum as SQLEnum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnomalyCategory(str, Enum):
    """Categories of anomalies."""

    TIMING = "timing"  # Response delays, timeouts
    PROTOCOL = "protocol"  # Protocol violations, malformed packets
    SEQUENCE = "sequence"  # Out-of-order, missing, duplicate packets
    PAYLOAD = "payload"  # Invalid values, corruption
    NETWORK = "network"  # Packet loss, jitter spikes
    SECURITY = "security"  # Scan signatures, exploit patterns
    EXTERNAL_COMMUNICATION = "external_communication"  # C2, exfil, external recon


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    LOW = "low"  # Minor glitches, barely noticeable
    MEDIUM = "medium"  # Noticeable issues, may trigger alerts
    HIGH = "high"  # Significant problems, likely triggers alerts
    CRITICAL = "critical"  # Major failures, definite detection


class AnomalyTemplate(Base):
    """Template for traffic anomaly injection.

    Anomaly templates define configurable patterns that can be injected
    into traffic to simulate various network conditions and security events.
    """

    __tablename__ = "anomaly_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    category: Mapped[AnomalyCategory] = mapped_column(
        SQLEnum(AnomalyCategory), nullable=False
    )
    severity: Mapped[AnomalySeverity] = mapped_column(
        SQLEnum(AnomalySeverity), nullable=False, default=AnomalySeverity.MEDIUM
    )

    # Targeting
    target_protocols: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # ["modbus_tcp", "ethernet_ip"] or null for all
    target_device_types: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # ["plc", "hmi"] or null for all

    # Anomaly configuration
    anomaly_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Specific anomaly type within category

    # Parameters for the anomaly
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Example parameters by type:
    # - timeout: {"timeout_ms": 5000, "partial_response": false}
    # - delayed: {"delay_factor": 10.0, "jitter_ms": 100}
    # - duplicate: {"duplicate_count": 2, "interval_ms": 50}
    # - malformed: {"corruption_type": "crc", "byte_offset": null}
    # - value_spike: {"spike_factor": 100.0, "duration_cycles": 5}

    # Injection configuration
    injection_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="random"
    )  # "random", "scheduled", "triggered", "continuous"

    injection_probability: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.01
    )  # For random mode

    injection_schedule: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # For scheduled mode: {"start_ms": 10000, "interval_ms": 60000}

    # Duration and scope
    duration_cycles: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # How many cycles the anomaly affects

    affects_flow_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # How many flows are affected simultaneously

    # Metadata
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Attack/detection metadata (for security anomalies)
    mitre_technique: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # e.g., "T0802"
    cve_reference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detection_signature: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Expected IDS signature match

    # External communication fields (for EXTERNAL_COMMUNICATION category)
    external_target_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # "c2_server", "exfil_destination", "attacker_source"
    external_protocol: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "http", "https", "dns", "tcp_raw", "udp_raw"
    external_port: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Target port for external traffic
    ids_trigger_patterns: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # IDS/Snort signatures this anomaly should trigger
    # Example: ["alert tcp any any -> any any (content:'cmd.exe';)", ...]
    external_ip_pool: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "test_net_1", "test_net_2", "test_net_3", "realistic"

    def to_injection_config(self) -> dict[str, Any]:
        """Convert template to injection configuration.

        Returns:
            Configuration dict for AIEnhancedProtocolEngine
        """
        config = {
            "enabled": self.is_active,
            "type": self.anomaly_type,
            "category": self.category.value,
            "severity": self.severity.value,
            "mode": self.injection_mode,
            "probability": self.injection_probability,
            "schedule": self.injection_schedule,
            "parameters": self.parameters or {},
            "duration_cycles": self.duration_cycles,
            "affects_flow_count": self.affects_flow_count,
        }

        # Add external communication fields if this is an external category
        if self.category == AnomalyCategory.EXTERNAL_COMMUNICATION:
            config["external"] = {
                "target_type": self.external_target_type,
                "protocol": self.external_protocol,
                "port": self.external_port,
                "ids_patterns": self.ids_trigger_patterns,
                "ip_pool": self.external_ip_pool,
            }

        # Add MITRE/CVE metadata if present
        if self.mitre_technique:
            config["mitre_technique"] = self.mitre_technique
        if self.cve_reference:
            config["cve_reference"] = self.cve_reference
        if self.detection_signature:
            config["detection_signature"] = self.detection_signature

        return config
