"""LDAP schemas for API validation."""

from pydantic import BaseModel, Field


class LdapSettingsResponse(BaseModel):
    """LDAP settings returned to the admin UI. Bind password is masked."""

    ldap_enabled: bool
    ldap_server_url: str
    ldap_use_ssl: bool
    ldap_start_tls: bool
    ldap_verify_ssl: bool
    ldap_bind_dn: str
    ldap_bind_password_set: bool = Field(description="Whether a bind password is configured")
    ldap_search_base: str
    ldap_user_search_filter: str
    ldap_email_attribute: str
    ldap_display_name_attribute: str


class LdapSettingsUpdate(BaseModel):
    """Partial update for LDAP settings. Omit fields to leave unchanged."""

    ldap_enabled: bool | None = None
    ldap_server_url: str | None = None
    ldap_use_ssl: bool | None = None
    ldap_start_tls: bool | None = None
    ldap_verify_ssl: bool | None = None
    ldap_bind_dn: str | None = None
    ldap_bind_password: str | None = Field(
        default=None,
        description="New bind password. Omit or send empty to keep the existing one.",
    )
    ldap_search_base: str | None = None
    ldap_user_search_filter: str | None = None
    ldap_email_attribute: str | None = None
    ldap_display_name_attribute: str | None = None


class LdapTestConnectionRequest(BaseModel):
    """Ad-hoc connection test payload. Uses in-memory values, does not persist."""

    ldap_server_url: str
    ldap_use_ssl: bool = True
    ldap_start_tls: bool = False
    ldap_verify_ssl: bool = True
    ldap_bind_dn: str
    ldap_bind_password: str | None = Field(
        default=None,
        description="Bind password. If omitted, the currently stored password is used.",
    )
    ldap_search_base: str = ""


class LdapTestConnectionResponse(BaseModel):
    """Result of a test-connection attempt."""

    success: bool
    message: str
    server_info: str | None = None
