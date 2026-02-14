"""System settings model for storing configuration."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SystemSetting(Base):
    """System settings model for storing configuration values."""

    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_secret: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<SystemSetting {self.key}>"


# Default settings to be seeded
DEFAULT_SETTINGS = [
    {
        "key": "ai_provider",
        "value": "anthropic",
        "is_secret": False,
        "category": "ai",
        "description": "AI provider to use (anthropic or openai)",
    },
    {
        "key": "anthropic_model",
        "value": "claude-opus-4-6",
        "is_secret": False,
        "category": "ai",
        "description": "Anthropic model to use for AI features",
    },
    {
        "key": "openai_model",
        "value": "gpt-4.1",
        "is_secret": False,
        "category": "ai",
        "description": "OpenAI model to use for AI features",
    },
    {
        "key": "anthropic_api_key",
        "is_secret": True,
        "category": "ai",
        "description": "Anthropic API key for Claude MCP integration",
    },
    {
        "key": "openai_api_key",
        "is_secret": True,
        "category": "ai",
        "description": "OpenAI API key for GPT integration",
    },
    {
        "key": "default_subnet_plant_floor",
        "value": "192.168.1.0/24",
        "is_secret": False,
        "category": "network",
        "description": "Default subnet for plant floor zone",
    },
    {
        "key": "default_subnet_dmz",
        "value": "192.168.2.0/24",
        "is_secret": False,
        "category": "network",
        "description": "Default subnet for DMZ zone",
    },
    {
        "key": "default_subnet_corporate",
        "value": "192.168.3.0/24",
        "is_secret": False,
        "category": "network",
        "description": "Default subnet for corporate zone",
    },
    {
        "key": "default_subnet_remote",
        "value": "10.0.0.0/24",
        "is_secret": False,
        "category": "network",
        "description": "Default subnet for remote zone",
    },
    {
        "key": "default_vlan_range_start",
        "value": "100",
        "is_secret": False,
        "category": "network",
        "description": "Starting VLAN ID for auto-assignment",
    },
    {
        "key": "default_vlan_range_end",
        "value": "200",
        "is_secret": False,
        "category": "network",
        "description": "Ending VLAN ID for auto-assignment",
    },
    {
        "key": "pcap_output_directory",
        "value": "./output/pcap",
        "is_secret": False,
        "category": "system",
        "description": "Directory for PCAP file output",
    },
    {
        "key": "max_simulation_duration_ms",
        "value": "600000",
        "is_secret": False,
        "category": "system",
        "description": "Maximum allowed simulation duration (10 minutes)",
    },
    {
        "key": "default_scenario_duration_ms",
        "value": "60000",
        "is_secret": False,
        "category": "system",
        "description": "Default scenario duration (1 minute)",
    },
    {
        "key": "enable_realtime_generation",
        "value": "false",
        "is_secret": False,
        "category": "system",
        "description": "Enable real-time packet generation",
    },
    # Cyber Vision settings
    {
        "key": "cyber_vision_url",
        "value": "",
        "is_secret": False,
        "category": "cyber_vision",
        "description": "Cisco Cyber Vision center URL (e.g., https://10.10.20.115)",
    },
    {
        "key": "cyber_vision_api_token",
        "is_secret": True,
        "category": "cyber_vision",
        "description": "Cisco Cyber Vision API token for authentication",
    },
    {
        "key": "cyber_vision_verify_ssl",
        "value": "false",
        "is_secret": False,
        "category": "cyber_vision",
        "description": "Verify SSL certificates when connecting to Cyber Vision",
    },
]
