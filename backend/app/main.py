"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin, ai, anomalies, auth, cve, cyber_vision, deployments, devices, docker_hosts, fingerprints, generation, health, ip_management, learning, protocols, scenarios, stats, templates, users
from app.mcp_server.transport import http_sse
from app.core.config import settings
from app.core.database import async_session_maker, close_db, init_db
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
    logger.info("Starting PacketArch API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Run startup tasks
    async with async_session_maker() as db:
        results = await run_startup_tasks(db)
        for task, result in results.items():
            logger.info(f"Startup task [{task}]: {result}")

    logger.info("PacketArch API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PacketArch API...")
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

# Configure CORS - use regex to allow any origin on frontend ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://.*(:443|:3001|:5173)?$",  # HTTPS (443), dev (3001, 5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(scenarios.router, prefix=settings.api_prefix)
app.include_router(protocols.router, prefix=settings.api_prefix)
app.include_router(generation.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)
app.include_router(templates.router, prefix=settings.api_prefix)
app.include_router(docker_hosts.router, prefix=settings.api_prefix)
app.include_router(deployments.router, prefix=settings.api_prefix)
app.include_router(learning.router, prefix=settings.api_prefix)
app.include_router(anomalies.router, prefix=settings.api_prefix)
app.include_router(fingerprints.router, prefix=settings.api_prefix)
app.include_router(ip_management.router, prefix=settings.api_prefix)
app.include_router(stats.router, prefix=settings.api_prefix)
app.include_router(cve.router, prefix=settings.api_prefix)
app.include_router(cyber_vision.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(http_sse.router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
