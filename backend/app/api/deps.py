# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""API dependencies for authentication and database access."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.features import get_features
from app.core.security import verify_token
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if payload is None:
        raise credentials_exception

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def require_ai_enabled() -> None:
    """Guard that 503s when AI features are disabled by deployment config.

    Applied at the router level on AI / MCP endpoints so the routes stay in
    the OpenAPI spec and return a clean, predictable error instead of 404.
    """
    if not get_features().ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI features are disabled in this deployment. "
                "Contact your administrator if you need AI-assisted workflows."
            ),
        )


async def require_live_traffic_enabled() -> None:
    """Guard that 503s when live-traffic features are disabled.

    Applied to remote-agent, deployment, live-dashboard, adaptation, and the
    runtime-control half of the attacks router. PCAP-only deployments disable
    this flag — gated routes stay in the OpenAPI spec and return a clean 503
    so the frontend can render an informative state instead of a 404.
    """
    if not get_features().live_traffic_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Live traffic features are disabled in this deployment. "
                "This installation is configured as a PCAP-only generator."
            ),
        )


async def require_multi_sensor_topology() -> None:
    """Guard that 503s when the multi-sensor topology workflow is disabled.

    Applied to the /scenarios/*/topology router. The feature is experimental
    ("Advanced Deployment") and ships default-off; enabling it requires
    MULTI_SENSOR_TOPOLOGY_ENABLED=true.
    """
    if not get_features().multi_sensor_topology_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Multi-sensor topology deployment is disabled in this "
                "deployment. Set MULTI_SENSOR_TOPOLOGY_ENABLED=true to enable "
                "this experimental workflow."
            ),
        )


async def require_mimic_enabled() -> None:
    """Guard that 503s when the Mimic device-emulation path is disabled.

    Applied to the /mimic router. Mimic (interactive device personas that bind
    real sockets and answer as industrial devices) ships default-off; enabling it
    requires MIMIC_ENABLED=true. Gated route stays in the OpenAPI spec and returns
    a clean 503 so the frontend can render an informative state.
    """
    if not get_features().mimic_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PacketArch Mimic (device emulation) is disabled in this "
                "deployment. Set MIMIC_ENABLED=true to enable this experimental "
                "workflow."
            ),
        )


async def require_setup_complete(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Guard that 503s while first-run setup is incomplete.

    Applied to every authenticated router so the frontend gets a clean,
    diagnostic error during the wizard window instead of a 401-cascade.
    /api/v1/setup/*, /about, and /health remain open without this dep.
    """
    # Lazy import to avoid circular at module-load time.
    from app.models.settings import SystemSetting

    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == "setup.completed")
    )
    value = result.scalar_one_or_none()
    if value != "true":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "First-time setup not complete. Open this server's URL in a "
                "browser and finish the setup wizard."
            ),
        )


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
RequireAIEnabled = Depends(require_ai_enabled)
RequireLiveTrafficEnabled = Depends(require_live_traffic_enabled)
RequireMultiSensorTopology = Depends(require_multi_sensor_topology)
RequireMimicEnabled = Depends(require_mimic_enabled)
RequireSetupComplete = Depends(require_setup_complete)
