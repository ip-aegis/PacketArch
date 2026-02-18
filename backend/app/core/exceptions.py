"""Custom exception hierarchy for PacketArch.

This module provides a unified exception system that:
1. Enables consistent error responses across all API endpoints
2. Includes error codes for frontend mapping
3. Carries structured context for debugging
4. Maps to appropriate HTTP status codes
"""

from typing import Any


class PacketArchError(Exception):
    """Base exception for all PacketArch errors.

    All custom exceptions should inherit from this class to enable
    consistent error handling and response formatting.

    Attributes:
        message: Human-readable error description
        code: Machine-readable error code (e.g., "VALIDATION_ERROR")
        details: Additional context for debugging
        status_code: HTTP status code to return (default 500)
    """

    status_code: int = 500

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {
            "error": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# ============================================================================
# Client Errors (4xx)
# ============================================================================


class ValidationError(PacketArchError):
    """Invalid input data or request parameters.

    Use for:
    - Pydantic validation failures
    - Invalid file types
    - Out-of-range values
    - Missing required fields
    """

    status_code = 400

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if field:
            _details["field"] = field
        if value is not None:
            _details["value"] = str(value)[:100]  # Truncate long values
        super().__init__(message, code="VALIDATION_ERROR", details=_details)


class NotFoundError(PacketArchError):
    """Requested resource does not exist.

    Use for:
    - Database lookups that return no results
    - Missing files
    - Unknown IDs
    """

    status_code = 404

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        _details["resource"] = resource
        if identifier:
            _details["identifier"] = identifier
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message, code="NOT_FOUND", details=_details)


class ConflictError(PacketArchError):
    """Resource state conflict prevents the operation.

    Use for:
    - Duplicate entries
    - Concurrent modification conflicts
    - Invalid state transitions
    """

    status_code = 409

    def __init__(
        self,
        message: str,
        resource: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if resource:
            _details["resource"] = resource
        super().__init__(message, code="CONFLICT", details=_details)


class AuthenticationError(PacketArchError):
    """Authentication failed or credentials invalid.

    Use for:
    - Invalid tokens
    - Expired sessions
    - Missing credentials
    """

    status_code = 401

    def __init__(
        self,
        message: str = "Authentication required",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(PacketArchError):
    """User lacks permission for the requested action.

    Use for:
    - Insufficient privileges
    - Resource access denied
    - Admin-only operations
    """

    status_code = 403

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if required_permission:
            _details["required_permission"] = required_permission
        super().__init__(message, code="AUTHORIZATION_ERROR", details=_details)


class RateLimitError(PacketArchError):
    """Request rate limit exceeded.

    Use for:
    - API rate limiting
    - Resource throttling
    """

    status_code = 429

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if retry_after:
            _details["retry_after_seconds"] = retry_after
        super().__init__(message, code="RATE_LIMIT_ERROR", details=_details)


# ============================================================================
# Server Errors (5xx)
# ============================================================================


class ExternalServiceError(PacketArchError):
    """External service communication failure.

    Use for:
    - Docker API errors
    - Cyber Vision API failures
    - AI provider (Anthropic) errors
    - Remote agent communication issues
    """

    status_code = 502

    def __init__(
        self,
        service: str,
        message: str | None = None,
        original_error: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        _details["service"] = service
        if original_error:
            _details["original_error"] = str(original_error)[:500]
        _message = message or f"External service '{service}' error"
        super().__init__(_message, code="EXTERNAL_SERVICE_ERROR", details=_details)


class PatternExtractionError(PacketArchError):
    """PCAP pattern extraction or analysis failure.

    Use for:
    - Malformed PCAP files
    - Protocol parsing errors
    - Fingerprint extraction failures
    - Sequence detection errors
    """

    status_code = 422

    def __init__(
        self,
        message: str,
        protocol: str | None = None,
        pcap_id: str | None = None,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if protocol:
            _details["protocol"] = protocol
        if pcap_id:
            _details["pcap_id"] = pcap_id
        if stage:
            _details["stage"] = stage
        super().__init__(message, code="PATTERN_EXTRACTION_ERROR", details=_details)


class TrafficGenerationError(PacketArchError):
    """Traffic generation or PCAP creation failure.

    Use for:
    - Protocol engine errors
    - Invalid scenario configuration
    - PCAP writing failures
    - Timing model errors
    """

    status_code = 500

    def __init__(
        self,
        message: str,
        protocol: str | None = None,
        scenario_id: str | None = None,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if protocol:
            _details["protocol"] = protocol
        if scenario_id:
            _details["scenario_id"] = scenario_id
        if stage:
            _details["stage"] = stage
        super().__init__(message, code="TRAFFIC_GENERATION_ERROR", details=_details)


class ConfigurationError(PacketArchError):
    """Application configuration error.

    Use for:
    - Missing environment variables
    - Invalid configuration values
    - Missing API keys
    """

    status_code = 500

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if config_key:
            _details["config_key"] = config_key
        super().__init__(message, code="CONFIGURATION_ERROR", details=_details)


class DatabaseError(PacketArchError):
    """Database operation failure.

    Use for:
    - Connection failures
    - Query errors (that aren't NotFound)
    - Migration issues
    """

    status_code = 500

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if operation:
            _details["operation"] = operation
        super().__init__(message, code="DATABASE_ERROR", details=_details)


# ============================================================================
# AI/MCP Specific Errors
# ============================================================================


class AIProviderError(ExternalServiceError):
    """AI provider (Anthropic) specific error.

    Use for:
    - API key issues
    - Model errors
    - Token limit exceeded
    """

    def __init__(
        self,
        message: str,
        model: str | None = None,
        original_error: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if model:
            _details["model"] = model
        super().__init__(
            service="anthropic",
            message=message,
            original_error=original_error,
            details=_details,
        )
        self.code = "AI_PROVIDER_ERROR"


class MCPToolError(PacketArchError):
    """MCP tool execution failure.

    Use for:
    - Tool not found
    - Tool parameter validation
    - Tool execution errors
    """

    status_code = 500

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if tool_name:
            _details["tool_name"] = tool_name
        super().__init__(message, code="MCP_TOOL_ERROR", details=_details)


# ============================================================================
# Deployment Errors
# ============================================================================


class DeploymentError(PacketArchError):
    """Traffic deployment failure.

    Use for:
    - Container start failures
    - Network interface issues
    - Deployment configuration errors
    """

    status_code = 500

    def __init__(
        self,
        message: str,
        deployment_id: str | None = None,
        scenario_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if deployment_id:
            _details["deployment_id"] = deployment_id
        if scenario_id:
            _details["scenario_id"] = scenario_id
        super().__init__(message, code="DEPLOYMENT_ERROR", details=_details)


# ============================================================================
# Cyber Vision Errors
# ============================================================================


class CyberVisionError(ExternalServiceError):
    """Cisco Cyber Vision API error.

    Use for:
    - API authentication failures
    - Device sync errors
    - Enrichment failures
    """

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        original_error: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        _details = details or {}
        if endpoint:
            _details["endpoint"] = endpoint
        super().__init__(
            service="cyber_vision",
            message=message,
            original_error=original_error,
            details=_details,
        )
        self.code = "CYBER_VISION_ERROR"
