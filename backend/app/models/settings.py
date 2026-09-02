# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""System settings model for storing configuration."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

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
    # First-run setup state. Flipped to "true" by the setup wizard
    # (POST /api/v1/setup/complete) or by auto-graduation at startup when an
    # admin user already exists. Until true, all non-setup/non-about API
    # routes return 503.
    {
        "key": "setup.completed",
        "value": "false",
        "is_secret": False,
        "category": "setup",
        "description": "Whether first-run setup has been completed",
    },
    {
        "key": "site.name",
        "value": "",
        "is_secret": False,
        "category": "setup",
        "description": "Friendly site name (shown in title bar, briefing decks)",
    },
    {
        "key": "site.fqdn",
        "value": "",
        "is_secret": False,
        "category": "setup",
        "description": "Server FQDN or IP (baked into agent install commands)",
    },
    {
        "key": "site.timezone",
        "value": "UTC",
        "is_secret": False,
        "category": "setup",
        "description": "Site time zone (used for timestamps in scenarios and logs)",
    },
    {
        "key": "ai_provider",
        "value": "anthropic",
        "is_secret": False,
        "category": "ai",
        "description": "AI provider to use (anthropic, openai, or circuit)",
    },
    {
        "key": "anthropic_model",
        "value": "claude-opus-4-8",
        "is_secret": False,
        "category": "ai",
        "description": "Anthropic model to use for AI features",
    },
    {
        "key": "openai_model",
        "value": "gpt-5.6-sol",
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
    # ----- Cisco CIRCUIT (chat-ai.cisco.com) provider -----
    # CIRCUIT uses OAuth2 client_credentials against id.cisco.com to mint
    # a short-lived JWT for each chat call, plus a per-application appkey
    # (egai-...) that identifies the billable Cisco app. Env vars
    # CIRCUIT_CLIENT_ID / CIRCUIT_CLIENT_SECRET / CIRCUIT_APP_KEY /
    # CIRCUIT_MODEL override these system_settings rows when set, so
    # dev / containerised deploys can configure without touching the DB.
    {
        "key": "circuit_model",
        "value": "gpt-5-nano",
        "is_secret": False,
        "category": "ai",
        "description": "CIRCUIT model deployment to use (gpt-5-nano, gpt-5-mini, gpt-5, gemini-3.1-pro, gemini-3.1-flash-lite, claude-opus-4-8, etc. — subject to per-appkey entitlement)",
    },
    {
        "key": "circuit_client_id",
        "is_secret": False,
        "category": "ai",
        "description": "CIRCUIT Okta client_id (oart...). Not a password — stored unencrypted",
    },
    {
        "key": "circuit_client_secret",
        "is_secret": True,
        "category": "ai",
        "description": "CIRCUIT Okta client_secret (password-equivalent — encrypted at rest)",
    },
    {
        "key": "circuit_app_key",
        "is_secret": False,
        "category": "ai",
        "description": "CIRCUIT appkey (egai-...) identifying the Cisco application charged for usage",
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
    {
        "key": "cyber_vision_new_ui_token",
        "is_secret": True,
        "category": "cyber_vision",
        "description": (
            "Cisco Cyber Vision New UI API token (cvapi/v1 — a separate token "
            "store from the classic API token above; same URL/SSL setting)"
        ),
    },
    # Cisco Modeling Labs (CML) settings
    {
        "key": "cml_url",
        "value": "",
        "is_secret": False,
        "category": "cml",
        "description": "Cisco Modeling Labs base URL (e.g., https://10.10.20.230)",
    },
    {
        "key": "cml_username",
        "value": "",
        "is_secret": False,
        "category": "cml",
        "description": "CML username for JWT authentication",
    },
    {
        "key": "cml_password",
        "is_secret": True,
        "category": "cml",
        "description": "CML password (encrypted at rest; used to mint short-lived JWTs)",
    },
    {
        "key": "cml_verify_ssl",
        "value": "false",
        "is_secret": False,
        "category": "cml",
        "description": "Verify SSL certificates when connecting to CML",
    },
    {
        "key": "cml_packetarch_server_url",
        "value": "",
        "is_secret": False,
        "category": "cml",
        "description": (
            "URL the deployed agent phones home to (reachable from inside the CML lab; "
            "may differ from the browser-facing URL). Blank = fall back to site.fqdn."
        ),
    },
    # LDAP / Active Directory settings
    {
        "key": "ldap_enabled",
        "value": "false",
        "is_secret": False,
        "category": "ldap",
        "description": "Master switch for LDAP authentication. When false, login is local-only.",
    },
    {
        "key": "ldap_server_url",
        "value": "",
        "is_secret": False,
        "category": "ldap",
        "description": "LDAP server URL (e.g., ldaps://dc.acme.com:636 or ldap://dc.acme.com:389)",
    },
    {
        "key": "ldap_use_ssl",
        "value": "true",
        "is_secret": False,
        "category": "ldap",
        "description": "Use LDAPS (implicit TLS) when connecting",
    },
    {
        "key": "ldap_start_tls",
        "value": "false",
        "is_secret": False,
        "category": "ldap",
        "description": "Upgrade connection with StartTLS (use with plain ldap:// on port 389)",
    },
    {
        "key": "ldap_verify_ssl",
        "value": "true",
        "is_secret": False,
        "category": "ldap",
        "description": "Verify TLS certificates. Disable for lab use with self-signed certs.",
    },
    {
        "key": "ldap_bind_dn",
        "value": "",
        "is_secret": False,
        "category": "ldap",
        "description": "Service-account DN used to search for users (e.g., CN=svc_packetarch,OU=Service Accounts,DC=acme,DC=com)",
    },
    {
        "key": "ldap_bind_password",
        "is_secret": True,
        "category": "ldap",
        "description": "Password for the service-account bind DN",
    },
    {
        "key": "ldap_search_base",
        "value": "",
        "is_secret": False,
        "category": "ldap",
        "description": "Base DN for user searches (e.g., DC=acme,DC=com)",
    },
    {
        "key": "ldap_user_search_filter",
        "value": "(&(objectClass=user)(sAMAccountName={username}))",
        "is_secret": False,
        "category": "ldap",
        "description": "LDAP filter template. The literal {username} is replaced with the escaped login name.",
    },
    {
        "key": "ldap_email_attribute",
        "value": "mail",
        "is_secret": False,
        "category": "ldap",
        "description": "LDAP attribute to read the user's email from",
    },
    {
        "key": "ldap_display_name_attribute",
        "value": "displayName",
        "is_secret": False,
        "category": "ldap",
        "description": "LDAP attribute to read the user's display name from",
    },
]
