"""Pydantic schemas for request/response validation."""

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    TokenPayload,
)
from app.schemas.settings import (
    SettingResponse,
    SettingUpdate,
    SettingsResponse,
)
from app.schemas.common import (
    MessageResponse,
    PaginatedResponse,
)
from app.schemas.device_profile import (
    DeviceProfileCreate,
    DeviceProfileUpdate,
    DeviceProfileResponse,
    DeviceProfileListResponse,
)
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioSummaryResponse,
    ScenarioListResponse,
    ScenarioExport,
    ScenarioImport,
)
from app.schemas.protocol_template import (
    ProtocolTemplateCreate,
    ProtocolTemplateUpdate,
    ProtocolTemplateResponse,
    ProtocolTemplateListResponse,
)
from app.schemas.docker_host import (
    DockerHostCreate,
    DockerHostUpdate,
    DockerHostResponse,
    DockerHostListResponse,
    DockerHostTestRequest,
    DockerHostTestResult,
    DockerHostInterface,
    DockerHostInterfaceList,
)
from app.schemas.deployment import (
    DeploymentRequest,
    DeploymentResponse,
    DeploymentListResponse,
    DeploymentStatusUpdate,
    DeploymentLogsResponse,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenPayload",
    # Settings schemas
    "SettingResponse",
    "SettingUpdate",
    "SettingsResponse",
    # Common schemas
    "MessageResponse",
    "PaginatedResponse",
    # Device profile schemas
    "DeviceProfileCreate",
    "DeviceProfileUpdate",
    "DeviceProfileResponse",
    "DeviceProfileListResponse",
    # Scenario schemas
    "ScenarioCreate",
    "ScenarioUpdate",
    "ScenarioResponse",
    "ScenarioSummaryResponse",
    "ScenarioListResponse",
    "ScenarioExport",
    "ScenarioImport",
    # Protocol template schemas
    "ProtocolTemplateCreate",
    "ProtocolTemplateUpdate",
    "ProtocolTemplateResponse",
    "ProtocolTemplateListResponse",
    # Docker host schemas
    "DockerHostCreate",
    "DockerHostUpdate",
    "DockerHostResponse",
    "DockerHostListResponse",
    "DockerHostTestRequest",
    "DockerHostTestResult",
    "DockerHostInterface",
    "DockerHostInterfaceList",
    # Deployment schemas
    "DeploymentRequest",
    "DeploymentResponse",
    "DeploymentListResponse",
    "DeploymentStatusUpdate",
    "DeploymentLogsResponse",
]
