"""LDAP / Active Directory authentication service.

Mirrors the Cyber Vision integration pattern: settings live as rows in the
``system_settings`` table (the bind password is Fernet-encrypted), and a
singleton service is consumed by the auth route and admin endpoints.

Design notes:

* ``authenticate`` performs the classic bind -> search -> rebind flow. We
  never substitute the username into the search filter via string formatting;
  we escape it with :func:`ldap3.utils.conv.escape_filter_chars` to prevent
  LDAP injection.
* Empty passwords are rejected up front because some directories treat an
  empty-password bind as a successful anonymous bind.
* Every failure path is swallowed into a structured
  :class:`LdapAuthResult` so the auth route can treat "LDAP said no" and
  "LDAP is down" the same way — both simply fall back to local bcrypt.
"""

from __future__ import annotations

import logging
import ssl
from dataclasses import dataclass
from typing import Any

from ldap3 import ALL, NTLM, SIMPLE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.settings import SystemSetting

logger = logging.getLogger(__name__)


LDAP_SETTING_KEYS = [
    "ldap_enabled",
    "ldap_server_url",
    "ldap_use_ssl",
    "ldap_start_tls",
    "ldap_verify_ssl",
    "ldap_bind_dn",
    "ldap_bind_password",
    "ldap_search_base",
    "ldap_user_search_filter",
    "ldap_email_attribute",
    "ldap_display_name_attribute",
]


@dataclass
class LdapConfig:
    """Resolved LDAP configuration read from ``system_settings``."""

    enabled: bool
    server_url: str
    use_ssl: bool
    start_tls: bool
    verify_ssl: bool
    bind_dn: str
    bind_password: str
    search_base: str
    user_search_filter: str
    email_attribute: str
    display_name_attribute: str


@dataclass
class LdapUserInfo:
    """Details returned after a successful LDAP authentication."""

    dn: str
    username: str
    email: str | None
    display_name: str | None


@dataclass
class LdapAuthResult:
    """Outcome of an LDAP authentication attempt.

    ``user`` is populated only on success. ``reason`` is a short tag so the
    auth route can decide whether to fall back to local bcrypt (for
    "not_found" / any configuration problem) or not.
    """

    success: bool
    user: LdapUserInfo | None = None
    reason: str | None = None


@dataclass
class LdapTestResult:
    """Outcome of a service-account bind test."""

    success: bool
    message: str
    server_info: str | None = None


def _setting_to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def load_config(db: AsyncSession) -> LdapConfig:
    """Load the LDAP configuration from ``system_settings``."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.in_(LDAP_SETTING_KEYS))
    )
    raw: dict[str, str | None] = {s.key: s.value for s in result.scalars().all()}

    encrypted_pw = raw.get("ldap_bind_password") or ""
    bind_password = decrypt_value(encrypted_pw) if encrypted_pw else ""

    return LdapConfig(
        enabled=_setting_to_bool(raw.get("ldap_enabled")),
        server_url=(raw.get("ldap_server_url") or "").strip(),
        use_ssl=_setting_to_bool(raw.get("ldap_use_ssl"), default=True),
        start_tls=_setting_to_bool(raw.get("ldap_start_tls")),
        verify_ssl=_setting_to_bool(raw.get("ldap_verify_ssl"), default=True),
        bind_dn=(raw.get("ldap_bind_dn") or "").strip(),
        bind_password=bind_password,
        search_base=(raw.get("ldap_search_base") or "").strip(),
        user_search_filter=(
            raw.get("ldap_user_search_filter")
            or "(&(objectClass=user)(sAMAccountName={username}))"
        ),
        email_attribute=(raw.get("ldap_email_attribute") or "mail").strip(),
        display_name_attribute=(
            raw.get("ldap_display_name_attribute") or "displayName"
        ).strip(),
    )


def _build_server(config: LdapConfig) -> Server:
    """Build an ``ldap3.Server`` honouring the TLS / verify settings."""
    tls: Tls | None = None
    if config.use_ssl or config.start_tls:
        validate = ssl.CERT_REQUIRED if config.verify_ssl else ssl.CERT_NONE
        tls = Tls(validate=validate, version=ssl.PROTOCOL_TLS_CLIENT)
    return Server(config.server_url, use_ssl=config.use_ssl, tls=tls, get_info=ALL)


def _format_filter(template: str, username: str) -> str:
    """Safely substitute the username into a filter template.

    ``ldap3`` escapes ``* ( ) \\ NUL`` so a hostile username cannot alter the
    search filter.
    """
    safe = escape_filter_chars(username)
    return template.replace("{username}", safe)


def is_enabled(config: LdapConfig) -> bool:
    """Return True iff LDAP is enabled and has the minimum required config."""
    return bool(
        config.enabled
        and config.server_url
        and config.bind_dn
        and config.bind_password
        and config.search_base
        and config.user_search_filter
    )


def authenticate(config: LdapConfig, username: str, password: str) -> LdapAuthResult:
    """Authenticate a user against LDAP.

    Returns an :class:`LdapAuthResult`. ``success=True`` implies ``user`` is
    populated; otherwise ``reason`` describes why the attempt failed.
    """
    # Empty-password protection: some servers interpret this as an anonymous
    # bind and report success. Reject it before we ever hit the wire.
    if not password:
        return LdapAuthResult(success=False, reason="empty_password")

    if not is_enabled(config):
        return LdapAuthResult(success=False, reason="disabled")

    # Guard: the username must produce a sensible filter. If the template was
    # misconfigured and lacks the placeholder we'd otherwise bind every user.
    if "{username}" not in config.user_search_filter:
        logger.error("LDAP user search filter is missing the {username} placeholder")
        return LdapAuthResult(success=False, reason="bad_filter")

    server = _build_server(config)
    search_filter = _format_filter(config.user_search_filter, username)

    # Step 1: bind as the service account and locate the user DN.
    try:
        svc_conn = Connection(
            server,
            user=config.bind_dn,
            password=config.bind_password,
            authentication=SIMPLE,
            auto_bind=False,
            raise_exceptions=False,
        )
        if config.start_tls:
            svc_conn.start_tls()
        if not svc_conn.bind():
            logger.warning(
                "LDAP service-account bind failed: %s", svc_conn.result.get("description")
            )
            return LdapAuthResult(success=False, reason="service_bind_failed")

        svc_conn.search(
            search_base=config.search_base,
            search_filter=search_filter,
            attributes=[config.email_attribute, config.display_name_attribute],
            size_limit=2,
        )
        entries = svc_conn.entries
        svc_conn.unbind()
    except LDAPException:
        logger.exception("LDAP search failed")
        return LdapAuthResult(success=False, reason="server_error")

    if not entries:
        return LdapAuthResult(success=False, reason="not_found")
    if len(entries) > 1:
        # Ambiguous — refuse rather than pick the first match.
        logger.warning(
            "LDAP user search returned %d entries for %s", len(entries), username
        )
        return LdapAuthResult(success=False, reason="ambiguous")

    entry = entries[0]
    user_dn = entry.entry_dn
    email = _read_single_attribute(entry, config.email_attribute)
    display_name = _read_single_attribute(entry, config.display_name_attribute)

    # Step 2: rebind as the user to verify their password.
    try:
        user_conn = Connection(
            server,
            user=user_dn,
            password=password,
            authentication=SIMPLE,
            auto_bind=False,
            raise_exceptions=False,
        )
        if config.start_tls:
            user_conn.start_tls()
        if not user_conn.bind():
            return LdapAuthResult(success=False, reason="invalid_credentials")
        user_conn.unbind()
    except LDAPException:
        logger.exception("LDAP user bind failed")
        return LdapAuthResult(success=False, reason="server_error")

    return LdapAuthResult(
        success=True,
        user=LdapUserInfo(
            dn=user_dn,
            username=username,
            email=email,
            display_name=display_name,
        ),
    )


def test_connection(config: LdapConfig) -> LdapTestResult:
    """Bind with the service account only, to validate settings in the UI."""
    if not config.server_url:
        return LdapTestResult(success=False, message="LDAP server URL is not set")
    if not config.bind_dn:
        return LdapTestResult(success=False, message="Bind DN is not set")
    if not config.bind_password:
        return LdapTestResult(
            success=False,
            message="Bind password is not set (enter a password to test with, or save one first)",
        )

    server = _build_server(config)
    try:
        conn = Connection(
            server,
            user=config.bind_dn,
            password=config.bind_password,
            authentication=SIMPLE,
            auto_bind=False,
            raise_exceptions=False,
        )
        if config.start_tls:
            conn.start_tls()
        if not conn.bind():
            description = conn.result.get("description") or "bind failed"
            return LdapTestResult(success=False, message=f"Service-account bind failed: {description}")

        server_info = None
        try:
            info = server.info
            if info and getattr(info, "vendor_name", None):
                vendor = " ".join(info.vendor_name) if isinstance(info.vendor_name, list) else str(info.vendor_name)
                server_info = f"Connected to {vendor}"
        except Exception:  # noqa: BLE001 — informational only
            pass
        conn.unbind()
        return LdapTestResult(success=True, message="Connection successful", server_info=server_info)
    except LDAPException as exc:
        logger.exception("LDAP test connection failed")
        return LdapTestResult(success=False, message=f"Connection error: {exc}")


def _read_single_attribute(entry: Any, attr: str) -> str | None:
    """Return a single string value for an LDAP attribute, or ``None``."""
    if not attr:
        return None
    try:
        value = entry[attr].value
    except (KeyError, LDAPException):
        return None
    if value is None:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value)


# Re-export so the ldap3 NTLM constant is available if a caller wants to
# switch the auth mechanism in the future without importing ldap3 directly.
__all__ = [
    "LDAP_SETTING_KEYS",
    "LdapAuthResult",
    "LdapConfig",
    "LdapTestResult",
    "LdapUserInfo",
    "NTLM",
    "authenticate",
    "is_enabled",
    "load_config",
    "test_connection",
]
