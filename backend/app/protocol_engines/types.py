"""Protocol engine types and data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import FingerprintApplicator


class ProtocolType(str, Enum):
    """Supported protocol types."""

    MODBUS_TCP = "modbus_tcp"
    ETHERNET_IP = "ethernet_ip"
    PROFINET = "profinet"
    S7COMM = "s7comm"
    OPC_UA = "opc_ua"
    DNP3 = "dnp3"
    IEC_104 = "iec_104"


@dataclass
class DeviceContext:
    """Context information for a device in a flow.

    Extended to include comprehensive fingerprint data for
    hyper-realistic device emulation.
    """

    device_id: str
    mac_address: str
    ip_address: str
    port: int
    unit_id: int | None = None

    # Legacy fingerprint dict (for backwards compatibility)
    vendor_fingerprint: dict[str, Any] = field(default_factory=dict)

    # CVE vulnerability override - contains protocol identity overrides
    # for emitting vulnerable firmware versions in identity responses
    vulnerability_override: dict[str, Any] | None = None

    # Extended fingerprint fields
    vendor: str | None = None
    vendor_family: str | None = None
    model: str | None = None
    firmware_version: str | None = None

    # Fingerprint applicator (lazy-loaded)
    _fingerprint_applicator: "FingerprintApplicator | None" = field(
        default=None, repr=False, compare=False
    )

    @property
    def fingerprint_applicator(self) -> "FingerprintApplicator":
        """Get or create fingerprint applicator for this device.

        Returns:
            FingerprintApplicator instance with vulnerability overrides applied
        """
        if self._fingerprint_applicator is None:
            from app.protocol_engines.fingerprint_applicator import (
                FingerprintApplicator,
                create_default_applicator,
            )

            if self.vendor_fingerprint:
                # Pass vulnerability_override to apply CVE-specific identity overrides
                self._fingerprint_applicator = FingerprintApplicator(
                    self.vendor_fingerprint,
                    vulnerability_override=self.vulnerability_override,
                )
            else:
                self._fingerprint_applicator = create_default_applicator()

        return self._fingerprint_applicator

    def get_tcp_ttl(self) -> int:
        """Get TCP TTL for this device."""
        return self.fingerprint_applicator.get_tcp_options().ttl

    def get_tcp_window_size(self) -> int:
        """Get TCP window size for this device."""
        return self.fingerprint_applicator.get_tcp_options().window_size

    def get_response_delay_ms(self) -> float:
        """Get a sampled response delay for this device.

        Returns:
            Delay in milliseconds
        """
        sample = self.fingerprint_applicator.get_response_delay()
        return sample.delay_ms if not sample.is_timeout else 0

    def should_inject_error(self) -> bool:
        """Check if an error should be injected."""
        return self.fingerprint_applicator.should_inject_error()

    def get_exception_code(self) -> int:
        """Get a random exception code for error injection."""
        return self.fingerprint_applicator.get_random_exception_code()


@dataclass
class FlowContext:
    """Context for a communication flow between devices."""

    flow_id: str
    source: DeviceContext
    destination: DeviceContext
    protocol: ProtocolType
    config: dict[str, Any]
    timing_model: dict[str, Any]
    payload_template: dict[str, Any] | None = None


@dataclass
class PacketEvent:
    """Represents a packet generation event."""

    timestamp_ms: float
    flow_id: str
    packet_bytes: bytes
    direction: str  # "request" or "response"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """State for a protocol conversation."""

    flow_id: str
    state_name: str
    transaction_id: int = 0
    sequence_number: int = 0
    custom_data: dict[str, Any] = field(default_factory=dict)
