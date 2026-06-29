# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "PacketArch"
    app_version: str = "1.11.0"
    debug: bool = False
    environment: str = "development"

    # Self-upgrade (git-clone installs). Populated from the host on Docker
    # installs so the backend can launch the updater container against the
    # real install directory. Empty outside Docker.
    host_install_dir: str = ""
    compose_project_name: str = "packetarch"
    docker_gid: str = ""

    # API
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"  # Bind to all interfaces for off-box access
    api_port: int = 8001
    cors_origins: list[str] = [
        "https://localhost",
        "https://localhost:443",
        "http://localhost:3001",  # Dev server
        "http://localhost:5173",  # Vite dev
    ]

    # Database
    database_url: PostgresDsn = "postgresql+asyncpg://packetarch:packetarch_dev@localhost:5432/packetarch"  # type: ignore

    # Redis
    redis_url: RedisDsn = "redis://localhost:6379/0"  # type: ignore

    # JWT Authentication.
    #
    # Defaults tuned for an internet-exposed deployment: a 30-min access
    # token + 1-day refresh window means a stolen token is good for at
    # most ~24h, and the absolute window does NOT slide on refresh (see
    # `/auth/refresh` — the new refresh token preserves the inbound `exp`).
    # `algorithm` is retained as a soft hint for tooling but the actual
    # JWT decode whitelist is hardcoded to `["HS256"]` in
    # `core/security.py:_JWT_ALGORITHMS`; setting this to "none" via env
    # cannot disable signature checking.
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 1

    # Encryption (for storing API keys and secrets)
    encryption_key: str = ""  # Will be generated if not provided

    # Feature flags. These control what's surfaced at the product level and
    # are exposed to the frontend via /api/v1/about.features. Air-gapped or
    # otherwise-restricted deployments typically disable ai_enabled.
    ai_enabled: bool = True
    # When false, the backend ships as a PCAP-only generator: remote-agent
    # WebSocket hub, agent install bundle, deployment/adaptation/dashboard-live
    # routes, and the runtime-control half of the attacks router are gated off.
    # PCAP generation, scenario authoring, AI, fingerprints, and Cyber Vision
    # remain available. Default true preserves full-build behavior.
    live_traffic_enabled: bool = True

    # PCAP Output
    pcap_output_dir: str = "./output/pcap"
    max_simulation_duration_ms: int = 3600000  # 60 minutes default max

    # Legacy first-user bootstrap. New installs go through the first-run setup
    # wizard (POST /api/v1/setup/complete), which creates the admin from
    # operator-supplied credentials. This var is kept for backward compatibility
    # — if set, an admin is auto-created on boot when no users exist.
    # Note: ADMIN_PASSWORD env var is mapped to FIRST_USER_PASSWORD in docker-compose.yml
    first_user_username: str = "admin"
    first_user_password: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("secret_key", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be set (min 32 chars). "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    # Note: first_user_password is intentionally NOT validated as required.
    # Empty means "no env-driven bootstrap; operator runs the setup wizard."

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        return str(self.database_url)

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic migrations."""
        return str(self.database_url).replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
