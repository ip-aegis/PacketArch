"""Extended vendor fingerprint schemas for hyper-realistic device emulation.

These schemas define the detailed characteristics needed to fool advanced
vulnerability scanners like Cisco Cyber Vision by accurately emulating
vendor-specific network behavior, protocol responses, and timing patterns.
"""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JitterDistribution(str, Enum):
    """Distribution types for timing jitter."""

    UNIFORM = "uniform"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    GAMMA = "gamma"
    LOGNORMAL = "lognormal"


class TcpStackCharacteristics(BaseModel):
    """TCP/IP stack fingerprint characteristics.

    These values help emulate vendor-specific TCP implementations
    that vulnerability scanners use for OS/device fingerprinting.
    """

    ttl: int = Field(default=64, ge=1, le=255, description="IP Time-To-Live")
    window_size: int = Field(
        default=65535, ge=1, le=65535, description="TCP window size"
    )
    mss: int = Field(default=1460, ge=536, le=65535, description="Maximum Segment Size")
    window_scaling: int | None = Field(
        default=None, ge=0, le=14, description="Window scale factor (None = disabled)"
    )
    sack_permitted: bool = Field(default=True, description="SACK permitted option")
    timestamps_enabled: bool = Field(default=True, description="TCP timestamps option")
    nop_padding: bool = Field(default=True, description="NOP padding in options")
    df_flag: bool = Field(default=True, description="Don't Fragment flag")
    ecn_support: bool = Field(default=False, description="ECN capability")


class ModbusDeviceIdentification(BaseModel):
    """Modbus FC 43 (Read Device Identification) response data.

    This is what scanners query to identify Modbus devices.
    """

    vendor_name: str = Field(..., description="Object 0x00 - VendorName")
    product_code: str = Field(..., description="Object 0x01 - ProductCode")
    major_minor_revision: str = Field(..., description="Object 0x02 - MajorMinorRevision")
    vendor_url: str | None = Field(default=None, description="Object 0x03 - VendorUrl")
    product_name: str | None = Field(default=None, description="Object 0x04 - ProductName")
    model_name: str | None = Field(default=None, description="Object 0x05 - ModelName")
    user_application_name: str | None = Field(
        default=None, description="Object 0x06 - UserApplicationName"
    )
    # Extended objects (0x80-0xFF) for vendor-specific data
    extended_objects: dict[str, str] = Field(default_factory=dict)


class EtherNetIPIdentity(BaseModel):
    """EtherNet/IP ListIdentity response data.

    Used for CIP device identification in EtherNet/IP networks.
    """

    vendor_id: int = Field(..., ge=0, le=65535, description="ODVA Vendor ID")
    device_type: int = Field(..., ge=0, le=65535, description="CIP Device Type")
    product_code: int = Field(..., ge=0, le=65535, description="Product Code")
    revision_major: int = Field(..., ge=0, le=255, description="Major Revision")
    revision_minor: int = Field(..., ge=0, le=255, description="Minor Revision")
    serial_number: int = Field(..., ge=0, description="Serial Number")
    product_name: str = Field(..., max_length=32, description="Product Name")
    state: int = Field(default=3, ge=0, le=255, description="Device State")
    # CIP capabilities
    encap_protocol_version: int = Field(default=1, description="Encapsulation version")
    sin_family: int = Field(default=2, description="Socket family (AF_INET)")
    sin_port: int = Field(default=44818, description="TCP/UDP port")


class ProfinetIdentity(BaseModel):
    """PROFINET DCP identity block data.

    Used for PROFINET device identification via DCP protocol.
    """

    vendor_id: int = Field(..., ge=0, le=65535, description="Vendor ID (VendorIDHigh/Low)")
    device_id: int = Field(..., ge=0, le=65535, description="Device ID")
    station_name: str = Field(..., max_length=240, description="NameOfStation")
    device_role: int = Field(default=1, description="DeviceRole (1=Device, 2=Controller)")
    device_options: list[int] = Field(
        default_factory=list, description="Supported options"
    )
    alias_name: str | None = Field(default=None, description="Alias name")
    oem_vendor_id: int | None = Field(default=None, description="OEM Vendor ID")
    oem_device_id: int | None = Field(default=None, description="OEM Device ID")
    # I&M (Identification & Maintenance) data
    im0_manufacturer: str | None = Field(default=None, description="I&M0 Manufacturer")
    im0_order_id: str | None = Field(default=None, description="I&M0 Order ID")
    im0_serial_number: str | None = Field(default=None, description="I&M0 Serial Number")
    im0_hw_revision: int | None = Field(default=None, description="I&M0 HW Revision")
    im0_sw_revision: str | None = Field(default=None, description="I&M0 SW Revision")


class ResponseTiming(BaseModel):
    """Response timing characteristics with statistical distribution.

    Realistic response timing is critical for fooling scanners that
    measure timing patterns to identify device types.
    """

    min_ms: float = Field(default=1.0, ge=0, description="Minimum response time")
    max_ms: float = Field(default=50.0, ge=0, description="Maximum response time")
    mean_ms: float = Field(default=10.0, ge=0, description="Mean response time")
    std_dev_ms: float = Field(default=5.0, ge=0, description="Standard deviation")
    distribution: JitterDistribution = Field(
        default=JitterDistribution.GAUSSIAN, description="Distribution type"
    )
    # Occasional outliers (important for realism)
    outlier_probability: float = Field(
        default=0.01, ge=0, le=1, description="Probability of outlier response"
    )
    outlier_multiplier: float = Field(
        default=3.0, ge=1, description="Outlier time multiplier"
    )


class ErrorBehavior(BaseModel):
    """Protocol error behavior configuration.

    Real devices have specific error patterns that scanners look for.
    """

    # Modbus exception codes (01-06, 0A, 0B)
    supported_exception_codes: list[int] = Field(
        default_factory=lambda: [1, 2, 3, 4],
        description="Supported Modbus exception codes",
    )
    exception_probability: float = Field(
        default=0.001, ge=0, le=1, description="Probability of exception response"
    )
    # Timeout behavior
    timeout_probability: float = Field(
        default=0.0005, ge=0, le=1, description="Probability of timeout (no response)"
    )
    retry_behavior: bool = Field(
        default=True, description="Whether to simulate retry sequences"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retries")
    # Connection behavior
    connection_reset_probability: float = Field(
        default=0.0001, ge=0, le=1, description="Probability of connection reset"
    )


class VendorFingerprintExtended(BaseModel):
    """Extended vendor fingerprint for hyper-realistic device emulation.

    This comprehensive fingerprint includes all the characteristics
    needed to accurately emulate a specific vendor's device.
    """

    # Basic identification
    vendor: str = Field(..., description="Vendor name (e.g., 'Rockwell', 'Siemens')")
    vendor_family: str | None = Field(
        default=None, description="Product family (e.g., 'ControlLogix', 'S7-1500')"
    )
    model: str | None = Field(default=None, description="Specific model")
    firmware_version: str | None = Field(default=None, description="Firmware version")

    # MAC address OUI prefixes for this vendor
    oui_prefixes: list[str] = Field(
        default_factory=list,
        description="Valid MAC OUI prefixes (e.g., ['00:00:BC', '00:1D:9C'])",
    )

    # Protocol-specific identity responses
    modbus_identity: ModbusDeviceIdentification | None = Field(
        default=None, description="Modbus FC 43 identity data"
    )
    ethernet_ip_identity: EtherNetIPIdentity | None = Field(
        default=None, description="EtherNet/IP ListIdentity data"
    )
    profinet_identity: ProfinetIdentity | None = Field(
        default=None, description="PROFINET DCP identity data"
    )

    # Network stack characteristics
    tcp_stack: TcpStackCharacteristics = Field(
        default_factory=TcpStackCharacteristics,
        description="TCP/IP stack fingerprint",
    )

    # Timing characteristics
    response_timing: ResponseTiming = Field(
        default_factory=ResponseTiming, description="Response timing profile"
    )

    # Error behavior
    error_behavior: ErrorBehavior = Field(
        default_factory=ErrorBehavior, description="Error handling behavior"
    )

    # Protocol-specific quirks
    protocol_quirks: dict[str, Any] = Field(
        default_factory=dict,
        description="Protocol-specific behavioral quirks",
    )


# API Request/Response schemas


class VendorFingerprintCreate(BaseModel):
    """Schema for creating a vendor fingerprint."""

    vendor: str = Field(..., min_length=1, max_length=100)
    vendor_family: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=50)
    oui_prefixes: list[str] = Field(default_factory=list)
    modbus_identity: dict[str, Any] | None = None
    ethernet_ip_identity: dict[str, Any] | None = None
    profinet_identity: dict[str, Any] | None = None
    tcp_stack: dict[str, Any] = Field(default_factory=dict)
    response_timing: dict[str, Any] = Field(default_factory=dict)
    error_behavior: dict[str, Any] | None = None
    protocol_quirks: dict[str, Any] = Field(default_factory=dict)


class VendorFingerprintUpdate(BaseModel):
    """Schema for updating a vendor fingerprint."""

    vendor: str | None = Field(default=None, max_length=100)
    vendor_family: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=50)
    oui_prefixes: list[str] | None = None
    modbus_identity: dict[str, Any] | None = None
    ethernet_ip_identity: dict[str, Any] | None = None
    profinet_identity: dict[str, Any] | None = None
    tcp_stack: dict[str, Any] | None = None
    response_timing: dict[str, Any] | None = None
    error_behavior: dict[str, Any] | None = None
    protocol_quirks: dict[str, Any] | None = None


class VendorFingerprintResponse(BaseModel):
    """Schema for vendor fingerprint response."""

    id: UUID
    vendor: str
    vendor_family: str | None
    model: str | None
    firmware_version: str | None
    oui_prefixes: list[str]
    modbus_identity: dict[str, Any] | None
    ethernet_ip_identity: dict[str, Any] | None
    profinet_identity: dict[str, Any] | None
    tcp_stack: dict[str, Any]
    response_timing: dict[str, Any]
    error_behavior: dict[str, Any] | None
    protocol_quirks: dict[str, Any]
    is_builtin: bool

    class Config:
        from_attributes = True


class VendorFingerprintListResponse(BaseModel):
    """Schema for listing vendor fingerprints."""

    items: list[VendorFingerprintResponse]
    total: int
