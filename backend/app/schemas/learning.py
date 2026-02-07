"""Pydantic schemas for Learning API endpoints."""

from datetime import datetime

from pydantic import BaseModel


# ========== PCAP Schemas ==========


class PcapUploadResponse(BaseModel):
    """Response for PCAP upload."""

    id: str
    filename: str
    status: str
    message: str
    job_id: str | None = None  # For tracking Celery job progress


class PcapJobStatusResponse(BaseModel):
    """Response for PCAP processing job status."""

    job_id: str
    capture_id: str
    status: str
    progress: float
    stage: str
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    packets_analyzed: int = 0
    patterns_extracted: int = 0
    fingerprints_extracted: int = 0
    sequences_extracted: int = 0


class PcapCaptureResponse(BaseModel):
    """Response for PCAP capture details."""

    id: str
    filename: str
    original_filename: str
    file_size: int
    status: str
    error_message: str | None
    packet_count: int | None
    flow_count: int | None
    capture_duration_ms: float | None
    protocol_stats: dict | None
    devices_detected: dict | None
    description: str | None
    tags: list | None
    source_environment: str | None
    industry_vertical: str | None
    created_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True


class PcapListResponse(BaseModel):
    """Response for PCAP list."""

    captures: list[PcapCaptureResponse]
    total: int
    page: int
    page_size: int


# ========== Pattern Schemas ==========


class LearnedPatternResponse(BaseModel):
    """Response for learned pattern."""

    id: str
    name: str
    pattern_type: str
    protocol: str
    source_ip: str | None
    destination_ip: str | None
    distribution_type: str | None
    sample_count: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None
    std_dev: float | None
    fit_score: float | None
    confidence: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PatternListResponse(BaseModel):
    """Response for pattern list."""

    patterns: list[LearnedPatternResponse]
    total: int
    page: int
    page_size: int


class LearningStatsResponse(BaseModel):
    """Response for learning statistics."""

    uploaded_pcaps: int
    learned_patterns: int
    active_patterns: int
    protocols_covered: int
    protocol_patterns: int
    device_fingerprints: int
    learned_sequences: int


class PatternStatsResponse(BaseModel):
    """Response for pattern statistics."""
    protocol_patterns: dict
    device_fingerprints: dict
    sequences: dict


# ========== Protocol Pattern Schemas ==========


class ProtocolPatternResponse(BaseModel):
    """Response for learned protocol pattern."""

    id: str
    pcap_capture_id: str | None
    protocol: str
    function_codes: dict | None
    address_patterns: dict | None
    payload_structures: dict | None
    request_response_pairs: list | None
    unit_id_distribution: dict | None
    exception_patterns: dict | None
    device_identities: list | None
    protocol_metadata: dict | None
    sample_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProtocolPatternListResponse(BaseModel):
    """Response for protocol pattern list."""

    patterns: list[ProtocolPatternResponse]
    total: int
    page: int
    page_size: int


# ========== Device Fingerprint Schemas ==========


class DeviceFingerprintResponse(BaseModel):
    """Response for learned device fingerprint template.

    Fingerprints are GENERIC TEMPLATES capturing vendor characteristics,
    NOT specific device instances with IP addresses.
    """

    id: str
    pcap_capture_id: str | None
    # Vendor identification
    inferred_vendor: str | None
    device_type: str | None
    oui_patterns: list | None  # OUI prefixes associated with this fingerprint
    # TCP stack signature
    tcp_signature: dict | None
    # Response timing distributions
    response_timings: dict | None
    # Protocol-specific identity info (vendor, model, firmware)
    protocol_identities: dict | None
    # Behavioral patterns
    role: str
    active_protocols: list | None
    typical_ports: dict | None
    # Aggregation metadata
    observation_count: int
    total_packets_analyzed: int
    # Quality metrics
    confidence: float
    consistency_score: float
    # User metadata
    name: str | None
    tags: list | None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceFingerprintListResponse(BaseModel):
    """Response for device fingerprint list."""

    fingerprints: list[DeviceFingerprintResponse]
    total: int
    page: int
    page_size: int


# ========== Sequence Schemas ==========


class SequenceResponse(BaseModel):
    """Response for learned sequence."""

    id: str
    pcap_capture_id: str | None
    name: str
    sequence_type: str
    protocol: str
    initiator_ip: str | None
    responder_ip: str | None
    steps: dict | None
    step_count: int
    average_duration_ms: float | None
    timing_variance: float | None
    inter_step_timings: dict | None
    repetition_interval_ms: float | None
    repetition_jitter_ms: float | None
    occurrence_count: int
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class SequenceListResponse(BaseModel):
    """Response for sequence list."""

    sequences: list[SequenceResponse]
    total: int
    page: int
    page_size: int


# ========== Pattern Service Schemas ==========


class TimingModelResponse(BaseModel):
    """Response for timing model."""
    protocol: str
    source_pattern_id: str | None
    timing: dict | None
    confidence: float


class FunctionCodeDistributionResponse(BaseModel):
    """Response for function code distribution."""
    protocol: str
    source_pattern_id: str | None
    function_codes: dict | None
    sample_count: int
    confidence: float


class AddressPatternsResponse(BaseModel):
    """Response for address patterns."""
    protocol: str
    source_pattern_id: str | None
    address_patterns: dict | None
    sample_count: int
    confidence: float


class TcpSignatureModelResponse(BaseModel):
    """Response for TCP signature model."""
    protocol: str | None
    role: str | None
    signatures: list[dict]
    count: int


class ResponseTimingModelResponse(BaseModel):
    """Response for device response timing model."""
    protocol: str
    role: str
    aggregate: dict
    individual_timings: list[dict]
    device_count: int


class StartupSequenceResponse(BaseModel):
    """Response for startup sequence."""
    protocol: str
    sequence_id: str
    name: str
    steps: dict | None
    step_count: int
    average_duration_ms: float | None
    confidence: float


class PollCyclePatternResponse(BaseModel):
    """Response for poll cycle pattern."""
    protocol: str
    sequence_id: str
    name: str
    steps: dict | None
    step_count: int
    repetition_interval_ms: float | None
    repetition_jitter_ms: float | None
    confidence: float


class PatternSuggestionResponse(BaseModel):
    """Response for pattern suggestions."""
    device_type: str
    protocol: str
    expected_role: str
    suggestions: dict


# ========== Learning Session Schemas ==========


class LearningSessionCreate(BaseModel):
    """Request to create a learning session."""

    name: str
    description: str | None = None
    source_environment: str | None = None
    industry_vertical: str | None = None
    network_description: str | None = None
    tags: list[str] | None = None


class LearningSessionUpdate(BaseModel):
    """Request to update a learning session."""

    name: str | None = None
    description: str | None = None
    source_environment: str | None = None
    industry_vertical: str | None = None
    network_description: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class LearningSessionResponse(BaseModel):
    """Response for a learning session."""

    id: str
    name: str
    description: str | None
    status: str
    source_environment: str | None
    industry_vertical: str | None
    network_description: str | None
    tags: list | None
    capture_count: int
    total_packets: int
    total_flows: int
    total_duration_ms: float | None
    protocols_detected: list | None
    protocol_stats: dict | None
    aggregate_confidence: float | None
    pattern_count: int
    fingerprint_count: int
    sequence_count: int
    created_at: datetime
    updated_at: datetime
    analyzed_at: datetime | None

    class Config:
        from_attributes = True


class LearningSessionListResponse(BaseModel):
    """Response for learning session list."""

    sessions: list[LearningSessionResponse]
    total: int
    page: int
    page_size: int


class ApplySessionPatternsRequest(BaseModel):
    """Request to apply session patterns to a scenario."""

    scenario_id: str
    apply_fingerprints: bool = True
    apply_timing: bool = True
    apply_sequences: bool = False
    min_confidence: float = 0.5


class ApplySessionPatternsResponse(BaseModel):
    """Response from applying session patterns."""

    session_id: str
    scenario_id: str
    devices_updated: int
    patterns_applied: int
    fingerprints_applied: int
    sequences_applied: int
    message: str
