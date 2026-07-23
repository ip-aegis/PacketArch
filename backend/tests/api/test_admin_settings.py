# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Guards on GET /admin/settings.

The route grouped settings into the response with a hardcoded if/elif chain
naming three categories. Two of those three (``api_tokens``, ``network``) had
since left ``DEFAULT_SETTINGS`` entirely, and every category added afterwards —
``ai``, ``cml``, ``cyber_vision``, ``ldap``, ``setup`` — fell through to
nothing. The endpoint returned 4 of the 37 settings the app ships, which is
why the AI provider settings never appeared in the settings UI.

Nothing failed: the response was well-formed, just missing 33 rows. So these
guards assert the *relationship* between DEFAULT_SETTINGS and
SettingsResponse rather than any single category, because the next category
added would otherwise vanish exactly the same way.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import DEFAULT_SETTINGS, SystemSetting
from app.schemas.settings import SettingsResponse


def _default_categories() -> set[str]:
    return {
        (s.get("category") or "") for s in DEFAULT_SETTINGS
    } - {""}


def test_every_shipped_category_has_a_response_field():
    """The guard that would have caught this the day `ai` was introduced."""
    missing = sorted(_default_categories() - set(SettingsResponse.model_fields))
    assert not missing, (
        "categories in DEFAULT_SETTINGS with no SettingsResponse field — "
        f"settings in them are silently dropped by GET /admin/settings: {missing}"
    )


def test_the_category_survey_is_not_vacuous():
    """Silence must not look like success."""
    categories = _default_categories()
    assert len(categories) >= 5, (
        f"only {len(categories)} categories found in DEFAULT_SETTINGS; there "
        f"were 6 when this was written, so the survey is probably not running"
    )
    assert "ai" in categories, "the category this bug was reported against"


@pytest.mark.asyncio
async def test_get_all_settings_returns_every_category(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_auth_headers: dict[str, str],
):
    """End to end: a setting in each shipped category comes back out.

    Asserting the count alone would pass while a category was misfiled, so
    check each key lands in the group it declared.
    """
    categories = sorted(_default_categories())
    for category in categories:
        db_session.add(
            SystemSetting(
                key=f"test_{category}_key",
                value="v",
                category=category,
                is_secret=False,
                description=f"probe for {category}",
            )
        )
    await db_session.commit()

    resp = await client.get("/api/v1/admin/settings", headers=admin_auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    for category in categories:
        assert category in body, f"response has no '{category}' group"
        keys = {row["key"] for row in body[category]}
        assert f"test_{category}_key" in keys, (
            f"the {category} setting did not come back in the {category} group; "
            f"got {sorted(keys)}"
        )


@pytest.mark.asyncio
async def test_secret_settings_are_masked(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_auth_headers: dict[str, str],
):
    """Widening the response must not start handing out credentials.

    Surfacing ldap/ai/cyber_vision means groups that hold bind passwords, API
    keys and tokens now reach the client, so the masking that was always there
    is now load-bearing and gets asserted rather than assumed.
    """
    from app.core.encryption import encrypt_value

    secret = "super-secret-token-value-1234"
    db_session.add(
        SystemSetting(
            key="test_ai_secret",
            value=encrypt_value(secret),
            category="ai",
            is_secret=True,
            description="probe",
        )
    )
    await db_session.commit()

    resp = await client.get("/api/v1/admin/settings", headers=admin_auth_headers)
    assert resp.status_code == 200, resp.text
    row = next(
        r for r in resp.json()["ai"] if r["key"] == "test_ai_secret"
    )
    assert row["value"] != secret, "secret returned in the clear"
    assert "*" in row["value"], f"secret not masked: {row['value']}"
    assert secret not in resp.text
