# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.api.routes import about, acknowledgments, adaptation, admin, agent_install, agents, ai, ai_usage, anomalies, architecture as architecture_routes, attacks, auth, cloud_services, cml, cve, cyber_vision, dashboard, deployments, downloads, fingerprints, generation, health, health_monitor as health_monitor_routes, ip_management, ldap, protocols, scenario_versions, scenarios, setup as setup_routes, site_config, stats, system as system_routes, templates, users
from app.api.websocket import agent_hub
from app.api.deps import RequireLiveTrafficEnabled, RequireSetupComplete
from app.mcp_server.transport import http_sse
from app.core.config import settings
from app.core.database import async_session_maker, close_db, init_db
from app.core.exceptions import PacketArchError, ValidationError as AppValidationError
from app.core.version import get_startup_banner
from app.services.health_monitor import health_monitor
from app.services.startup import run_startup_tasks

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(get_startup_banner())
    logger.info("Starting PacketArch API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Run startup tasks
    async with async_session_maker() as db:
        results = await run_startup_tasks(db)
        for task, result in results.items():
            logger.info(f"Startup task [{task}]: {result}")

    # Start health monitor
    await health_monitor.start()

    logger.info("PacketArch API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PacketArch API...")
    await health_monitor.stop()
    await close_db()
    logger.info("PacketArch API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="OT Traffic Simulation Platform - Generate hyper-realistic industrial network traffic",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS - explicit origins only (override via CORS_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers for custom exceptions
@app.exception_handler(PacketArchError)
async def packetarch_exception_handler(request: Request, exc: PacketArchError) -> JSONResponse:
    """Handle PacketArch custom exceptions with structured responses."""
    logger.warning(
        f"PacketArch error [{exc.code}]: {exc.message}",
        extra={"details": exc.details, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with structured responses."""
    errors = exc.errors()
    logger.warning(f"Validation error: {errors}", extra={"path": request.url.path})

    # Convert to our standard format
    details = {
        "validation_errors": [
            {
                "field": ".".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Unknown validation error"),
                "type": err.get("type", "unknown"),
            }
            for err in errors
        ]
    }

    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": details,
        },
    )


# Global exception handler for uncaught exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Include routers.
#
# Setup-gating contract: every authenticated/feature router gets
# RequireSetupComplete so the API surface is one big 503 until first-run
# setup finishes. Three routers stay open during the wizard window:
#   - health.router  (load balancers + container healthchecks)
#   - about.router   (login footer + setup wizard need product metadata)
#   - setup_routes.router (the wizard itself)
app.include_router(health.router)
app.include_router(about.router, prefix=settings.api_prefix)
app.include_router(setup_routes.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(acknowledgments.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(admin.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(system_routes.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(ai_usage.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(site_config.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(scenarios.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(architecture_routes.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(scenario_versions.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(protocols.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(generation.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(ai.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(templates.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(deployments.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete, RequireLiveTrafficEnabled])
app.include_router(anomalies.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(fingerprints.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(ip_management.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(stats.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(dashboard.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete, RequireLiveTrafficEnabled])
app.include_router(adaptation.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete, RequireLiveTrafficEnabled])
# attacks.router has per-route gating: read endpoints (playbooks list/get,
# compatible-playbooks) stay open so the PCAP-only build can populate the
# attack-playbook dropdown in GeneratePcapModal. Runtime-control endpoints
# (start/stop/advance/pause/inject/state/injection-status) are gated inside
# the route file. Setup-gating is uniform across all of them.
app.include_router(attacks.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(cve.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(cloud_services.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(cyber_vision.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
# CML auto-deploy is meaningless in the PCAP-only build (no agents / no
# install bundle), so gate it like the agents router.
app.include_router(cml.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete, RequireLiveTrafficEnabled])
app.include_router(ldap.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(users.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(agents.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete, RequireLiveTrafficEnabled])
app.include_router(health_monitor_routes.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(downloads.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])
app.include_router(http_sse.router, prefix=settings.api_prefix, dependencies=[RequireSetupComplete])

# WebSocket + agent install bundle: live-traffic-only. Conditionally mounted
# (WebSockets cannot return 503 cleanly; install bundle has no place in a
# PCAP-only deployment). Frontend useFeatures().liveTrafficEnabled hides any
# UI that would point at these.
if settings.live_traffic_enabled:
    # WebSocket routes (no prefix - mounted at root)
    app.include_router(agent_hub.router)
    # Agent installation resources (no prefix - served at /agent/*)
    app.include_router(agent_install.router)


# Root endpoint
@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    from app.core.version import LICENSE_ID, OWNER_COPYRIGHT, OWNER_EMAIL
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "owner": f"{OWNER_COPYRIGHT} <{OWNER_EMAIL}>",
        "license": LICENSE_ID,
        "docs": "/api/docs",
        "health": "/health",
        "about": f"{settings.api_prefix}/about",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
