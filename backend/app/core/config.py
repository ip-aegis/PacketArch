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
        "https://*:443",
        "http://localhost:3001",  # Dev server
        "http://localhost:5173",  # Vite dev
        "http://*:3001",
        "http://*:5173",
    ]

    # Database
    database_url: PostgresDsn = "postgresql+asyncpg://packetarch:packetarch_dev@localhost:5432/packetarch"  # type: ignore

    # Redis
    redis_url: RedisDsn = "redis://localhost:6379/0"  # type: ignore

    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production-minimum-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption (for storing API keys and secrets)
    encryption_key: str = ""  # Will be generated if not provided

    # PCAP Output
    pcap_output_dir: str = "./output/pcap"
    max_simulation_duration_ms: int = 600000  # 10 minutes default max

    # First user (created on startup if no users exist)
    first_user_username: str = "admin"
    first_user_password: str = "changeme123"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
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
