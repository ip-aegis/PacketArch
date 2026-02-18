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
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

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

    # JWT Authentication
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption (for storing API keys and secrets)
    encryption_key: str = ""  # Will be generated if not provided

    # PCAP Output
    pcap_output_dir: str = "./output/pcap"
    max_simulation_duration_ms: int = 600000  # 10 minutes default max

    # First user (created on startup if no users exist)
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

    @field_validator("first_user_password", mode="after")
    @classmethod
    def validate_first_user_password(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "FIRST_USER_PASSWORD (or ADMIN_PASSWORD) must be set in environment"
            )
        return v

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
