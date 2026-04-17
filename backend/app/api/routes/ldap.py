"""LDAP / Active Directory admin routes.

Parallel to ``cyber_vision.py``: get/update settings and test the connection.
Everything here is admin-only; end-users never need to touch these endpoints.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import AdminUser, DBSession
from app.core.encryption import encrypt_value
from app.models.settings import SystemSetting
from app.schemas.ldap import (
    LdapSettingsResponse,
    LdapSettingsUpdate,
    LdapTestConnectionRequest,
    LdapTestConnectionResponse,
)
from app.services import ldap_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ldap", tags=["LDAP"])


# Settings metadata: (key, is_secret, default_category_description)
_SETTING_META: dict[str, tuple[bool, str]] = {
    "ldap_enabled": (False, "Master switch for LDAP authentication"),
    "ldap_server_url": (False, "LDAP server URL"),
    "ldap_use_ssl": (False, "Use LDAPS (implicit TLS)"),
    "ldap_start_tls": (False, "Use StartTLS"),
    "ldap_verify_ssl": (False, "Verify TLS certificates"),
    "ldap_bind_dn": (False, "Service-account DN for user search"),
    "ldap_bind_password": (True, "Service-account password"),
    "ldap_search_base": (False, "Base DN for user searches"),
    "ldap_user_search_filter": (False, "User search filter template"),
    "ldap_email_attribute": (False, "Attribute to read email from"),
    "ldap_display_name_attribute": (False, "Attribute to read display name from"),
}


def _bool_to_str(value: bool) -> str:
    return "true" if value else "false"


async def _upsert_setting(db, key: str, value: str) -> None:
    is_secret, description = _SETTING_META[key]
    stored_value = encrypt_value(value) if (is_secret and value) else value

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        db.add(
            SystemSetting(
                key=key,
                value=stored_value,
                is_secret=is_secret,
                category="ldap",
                description=description,
            )
        )
    else:
        setting.value = stored_value


@router.get("/settings", response_model=LdapSettingsResponse)
async def get_ldap_settings(
    db: DBSession,
    _admin: AdminUser,
) -> LdapSettingsResponse:
    """Return the current LDAP settings (bind password masked)."""
    config = await ldap_service.load_config(db)
    return LdapSettingsResponse(
        ldap_enabled=config.enabled,
        ldap_server_url=config.server_url,
        ldap_use_ssl=config.use_ssl,
        ldap_start_tls=config.start_tls,
        ldap_verify_ssl=config.verify_ssl,
        ldap_bind_dn=config.bind_dn,
        ldap_bind_password_set=bool(config.bind_password),
        ldap_search_base=config.search_base,
        ldap_user_search_filter=config.user_search_filter,
        ldap_email_attribute=config.email_attribute,
        ldap_display_name_attribute=config.display_name_attribute,
    )


@router.put("/settings", response_model=LdapSettingsResponse)
async def update_ldap_settings(
    update: LdapSettingsUpdate,
    db: DBSession,
    admin: AdminUser,
) -> LdapSettingsResponse:
    """Update LDAP settings. Omit fields to leave them unchanged."""
    if update.ldap_enabled is not None:
        await _upsert_setting(db, "ldap_enabled", _bool_to_str(update.ldap_enabled))
    if update.ldap_server_url is not None:
        await _upsert_setting(db, "ldap_server_url", update.ldap_server_url.strip())
    if update.ldap_use_ssl is not None:
        await _upsert_setting(db, "ldap_use_ssl", _bool_to_str(update.ldap_use_ssl))
    if update.ldap_start_tls is not None:
        await _upsert_setting(db, "ldap_start_tls", _bool_to_str(update.ldap_start_tls))
    if update.ldap_verify_ssl is not None:
        await _upsert_setting(db, "ldap_verify_ssl", _bool_to_str(update.ldap_verify_ssl))
    if update.ldap_bind_dn is not None:
        await _upsert_setting(db, "ldap_bind_dn", update.ldap_bind_dn.strip())
    # Only overwrite the password if the caller sent a non-empty value.
    if update.ldap_bind_password:
        await _upsert_setting(db, "ldap_bind_password", update.ldap_bind_password)
    if update.ldap_search_base is not None:
        await _upsert_setting(db, "ldap_search_base", update.ldap_search_base.strip())
    if update.ldap_user_search_filter is not None:
        await _upsert_setting(db, "ldap_user_search_filter", update.ldap_user_search_filter.strip())
    if update.ldap_email_attribute is not None:
        await _upsert_setting(db, "ldap_email_attribute", update.ldap_email_attribute.strip())
    if update.ldap_display_name_attribute is not None:
        await _upsert_setting(
            db, "ldap_display_name_attribute", update.ldap_display_name_attribute.strip()
        )

    await db.commit()
    return await get_ldap_settings(db, admin)


@router.post("/test-connection", response_model=LdapTestConnectionResponse)
async def test_ldap_connection(
    request: LdapTestConnectionRequest,
    db: DBSession,
    _admin: AdminUser,
) -> LdapTestConnectionResponse:
    """Bind with the given credentials to validate settings. Does not persist.

    If ``ldap_bind_password`` is omitted, the currently stored password is
    reused — mirrors the "leave empty to keep existing" UX we use for the
    Cyber Vision token.
    """
    stored = await ldap_service.load_config(db)
    bind_password = request.ldap_bind_password or stored.bind_password

    probe_config = replace(
        stored,
        enabled=True,  # test regardless of master switch
        server_url=request.ldap_server_url.strip(),
        use_ssl=request.ldap_use_ssl,
        start_tls=request.ldap_start_tls,
        verify_ssl=request.ldap_verify_ssl,
        bind_dn=request.ldap_bind_dn.strip(),
        bind_password=bind_password,
        search_base=request.ldap_search_base.strip() or stored.search_base,
    )

    result = ldap_service.test_connection(probe_config)
    return LdapTestConnectionResponse(
        success=result.success,
        message=result.message,
        server_info=result.server_info,
    )
