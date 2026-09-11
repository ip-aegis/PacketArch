# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Multiple Cyber Vision Centers.

Covers the center lifecycle (first-is-default, uniqueness, delete guards), the
boot-time move of the legacy global ``cyber_vision_*`` settings into a default
center, the one-center-per-scenario conflict guard, the deploy-time lock of a
local-lab agent to its lab's center, teardown following the RECORDED center
rather than the current default, and per-center vertical roll-ups.
"""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.cyber_vision_center import CyberVisionCenter
from app.models.ip_range_allocation import IPRangeAllocation
from app.models.local_lab import LocalLab
from app.models.scenario import Scenario
from app.models.settings import SystemSetting
from app.models.traffic_agent import TrafficAgent
from app.services import cv_centers
from app.services import cv_provisioning_service as cps

pytestmark = pytest.mark.asyncio


async def _scenario(db, user, name="Plant", cv_state=None, vertical="manufacturing") -> Scenario:
    definition = {"devices": {}, "flows": {}}
    if cv_state is not None:
        definition["cyber_vision"] = cv_state
    s = Scenario(
        user_id=user.id, name=name, vertical=vertical,
        total_duration_ms=60000, definition=definition,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _center(db, name, url, **kw) -> CyberVisionCenter:
    c = await cv_centers.create_center(db, name=name, url=url, api_token="tok", **kw)
    await db.commit()
    await db.refresh(c)
    return c


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
async def test_first_center_is_default_and_second_is_not(db_session: AsyncSession):
    a = await _center(db_session, "A", "10.0.0.1/")
    b = await _center(db_session, "B", "https://10.0.0.2")
    assert a.url == "https://10.0.0.1"  # scheme added, slash trimmed
    assert a.is_default and not b.is_default
    assert decrypt_value(a.api_token) == "tok"  # stored encrypted

    await cv_centers.set_default(db_session, b)
    await db_session.commit()
    await db_session.refresh(a)
    assert b.is_default and not a.is_default
    assert (await cv_centers.default_center(db_session)).id == b.id


async def test_name_and_url_are_unique(db_session: AsyncSession):
    await _center(db_session, "A", "https://10.0.0.1")
    with pytest.raises(ConflictError):
        await cv_centers.create_center(db_session, name="A", url="https://10.0.0.9", api_token="t")
    with pytest.raises(ConflictError):
        await cv_centers.create_center(db_session, name="Z", url="10.0.0.1", api_token="t")


async def test_resolve_center(db_session: AsyncSession):
    assert await cv_centers.resolve_center(db_session) is None  # nothing configured
    a = await _center(db_session, "A", "https://10.0.0.1")
    assert (await cv_centers.resolve_center(db_session)).id == a.id
    with pytest.raises(NotFoundError):
        await cv_centers.resolve_center(db_session, uuid.uuid4())
    with pytest.raises(ValidationError):
        await cv_centers.resolve_center(db_session, "not-a-uuid")


async def test_delete_refuses_in_use_and_default_with_others(db_session, test_user):
    a = await _center(db_session, "A", "https://10.0.0.1")
    b = await _center(db_session, "B", "https://10.0.0.2")
    await _scenario(db_session, test_user, cv_state={"center_id": str(b.id), "preset_id": "p"})

    with pytest.raises(ConflictError, match="provisioned scenario"):
        await cv_centers.delete_center(db_session, b)
    with pytest.raises(ConflictError, match="default"):
        await cv_centers.delete_center(db_session, a)

    c = await _center(db_session, "C", "https://10.0.0.3")
    await cv_centers.delete_center(db_session, c)
    await db_session.commit()
    assert await db_session.get(CyberVisionCenter, c.id) is None


async def test_url_change_refused_while_in_use(db_session, test_user):
    a = await _center(db_session, "A", "https://10.0.0.1")
    await _scenario(db_session, test_user, cv_state={"center_id": str(a.id)})
    with pytest.raises(ConflictError):
        await cv_centers.update_center(db_session, a, url="https://10.9.9.9")
    # Renaming and rotating tokens are fine.
    await cv_centers.update_center(db_session, a, name="Plant A", api_token="new", new_ui_token="v1")
    assert a.name == "Plant A"
    assert decrypt_value(a.api_token) == "new" and decrypt_value(a.new_ui_token) == "v1"
    await cv_centers.update_center(db_session, a, new_ui_token="")
    assert a.new_ui_token is None


# --------------------------------------------------------------------------- #
# Legacy migration
# --------------------------------------------------------------------------- #
async def test_legacy_settings_become_the_default_center(db_session, test_user):
    token_ct = encrypt_value("legacy-classic")
    ui_ct = encrypt_value("legacy-ui")
    for key, value in (
        ("cyber_vision_url", "https://10.10.20.115/"),
        ("cyber_vision_api_token", token_ct),
        ("cyber_vision_verify_ssl", "true"),
        ("cyber_vision_new_ui_token", ui_ct),
    ):
        db_session.add(SystemSetting(key=key, value=value, category="cyber_vision"))
    lab = LocalLab(
        name="Old Lab", slug="oldlab01", sensor_compose="x", gen_if="pa-gen-o", mon_if="pa-mon-o",
    )
    db_session.add(lab)
    provisioned = await _scenario(db_session, test_user, cv_state={"preset_id": "p1"})
    untouched = await _scenario(db_session, test_user, name="Never provisioned")
    await db_session.commit()

    msg = await cv_centers.migrate_legacy_settings(db_session)
    assert "migrated" in msg

    center = await cv_centers.default_center(db_session)
    assert center.url == "https://10.10.20.115" and center.name == "10.10.20.115"
    assert center.verify_ssl is True
    # Ciphertext copied verbatim — no decrypt/re-encrypt round trip.
    assert center.api_token == token_ct and center.new_ui_token == ui_ct

    await db_session.refresh(lab)
    assert lab.cv_center_id == center.id
    await db_session.refresh(provisioned)
    await db_session.refresh(untouched)
    assert provisioned.definition["cyber_vision"]["center_id"] == str(center.id)
    assert provisioned.definition["cyber_vision"]["preset_id"] == "p1"
    assert "cyber_vision" not in untouched.definition

    left = (await db_session.execute(
        select(SystemSetting).where(SystemSetting.key.in_(cv_centers.LEGACY_CV_KEYS))
    )).scalars().all()
    assert left == []
    assert await cv_centers.migrate_legacy_settings(db_session) == "no legacy settings"


async def test_empty_legacy_rows_are_just_removed(db_session):
    db_session.add(SystemSetting(key="cyber_vision_url", value="", category="cyber_vision"))
    await db_session.commit()
    await cv_centers.migrate_legacy_settings(db_session)
    assert await cv_centers.default_center(db_session) is None
    left = (await db_session.execute(
        select(SystemSetting).where(SystemSetting.key.in_(cv_centers.LEGACY_CV_KEYS))
    )).scalars().all()
    assert left == []


async def test_half_configured_legacy_rows_are_kept(db_session):
    """A URL with no token can't become a center, and must not be thrown away."""
    db_session.add(SystemSetting(
        key="cyber_vision_url", value="https://10.9.9.9", category="cyber_vision"))
    db_session.add(SystemSetting(
        key="cyber_vision_api_token", value="", category="cyber_vision", is_secret=True))
    await db_session.commit()
    message = await cv_centers.migrate_legacy_settings(db_session)
    assert "incomplete" in message
    assert await cv_centers.default_center(db_session) is None
    left = {s.key: s.value for s in (await db_session.execute(
        select(SystemSetting).where(SystemSetting.key.in_(cv_centers.LEGACY_CV_KEYS))
    )).scalars().all()}
    assert left.get("cyber_vision_url") == "https://10.9.9.9"


# --------------------------------------------------------------------------- #
# One center per scenario
# --------------------------------------------------------------------------- #
async def test_provisioning_center_selection_and_conflict_guard(db_session, test_user):
    a = await _center(db_session, "A", "https://10.0.0.1")
    b = await _center(db_session, "B", "https://10.0.0.2")

    fresh = await _scenario(db_session, test_user, name="Fresh")
    assert (await cps.center_for_provisioning(db_session, fresh, None)).id == a.id  # default
    assert (await cps.center_for_provisioning(db_session, fresh, b.id)).id == b.id  # explicit

    on_b = await _scenario(db_session, test_user, name="On B", cv_state={"center_id": str(b.id)})
    # No center named: stays where it is, even though A is the default.
    assert (await cps.center_for_provisioning(db_session, on_b, None)).id == b.id
    assert (await cps.center_for_provisioning(db_session, on_b, b.id)).id == b.id
    with pytest.raises(ConflictError, match="already provisioned"):
        await cps.center_for_provisioning(db_session, on_b, a.id)

    # A recorded center that has since been deleted doesn't block a move.
    gone = await _scenario(db_session, test_user, name="Gone",
                           cv_state={"center_id": str(uuid.uuid4())})
    assert (await cps.center_for_provisioning(db_session, gone, a.id)).id == a.id


async def test_teardown_targets_the_recorded_center(db_session, test_user):
    a = await _center(db_session, "A", "https://10.0.0.1")
    b = await _center(db_session, "B", "https://10.0.0.2")
    scn = await _scenario(db_session, test_user,
                          cv_state={"center_id": str(b.id), "preset_id": "preset-on-b"})

    class _Fake:
        def __init__(self):
            self.deleted = []

        async def delete_preset(self, pid):
            self.deleted.append(pid)

        async def close(self):
            pass

    fake = _Fake()
    seen = []

    def _client(center):
        seen.append(center.id)
        return fake

    with patch("app.services.cv_centers.classic_client", side_effect=_client), \
         patch.object(cps, "_purge_scenario_entities", return_value={}):
        summary = await cps.teardown_cv_provisioning(db_session, scn)

    assert seen == [b.id] and a.id not in seen
    assert fake.deleted == ["preset-on-b"]
    assert summary["center_id"] == str(b.id)


async def test_scenarios_by_center_and_per_center_rollups(db_session, test_user):
    a = await _center(db_session, "A", "https://10.0.0.1")
    b = await _center(db_session, "B", "https://10.0.0.2")
    on_a = await _scenario(db_session, test_user, name="On A", cv_state={"center_id": str(a.id)})
    on_b = await _scenario(db_session, test_user, name="On B", cv_state={"center_id": str(b.id)})
    legacy = await _scenario(db_session, test_user, name="Unassigned")
    for i, s in enumerate((on_a, on_b, legacy), start=1):
        db_session.add(IPRangeAllocation(scenario_id=s.id, range_index=i, cidr_range=f"10.{i}.0.0/16"))
    await db_session.commit()

    by_center = await cps._scenarios_by_center(db_session)
    assert {s.name for s in by_center[str(a.id)]} == {"On A", "Unassigned"}  # default owns unassigned
    assert {s.name for s in by_center[str(b.id)]} == {"On B"}

    assert (await cps._subnets_by_vertical(db_session, a.id))["manufacturing"] == ["10.1.0.0/16", "10.3.0.0/16"]
    assert (await cps._subnets_by_vertical(db_session, b.id))["manufacturing"] == ["10.2.0.0/16"]


# --------------------------------------------------------------------------- #
# Deploy lock
# --------------------------------------------------------------------------- #
async def test_local_lab_agent_is_locked_to_its_labs_center(db_session, test_user):
    from app.services.agent_manager import agent_manager

    a = await _center(db_session, "A", "https://10.0.0.1")
    b = await _center(db_session, "B", "https://10.0.0.2")
    lab_id = uuid.uuid4()
    db_session.add(LocalLab(
        id=lab_id, name="Lab on B", slug="labonb01", sensor_compose="x",
        gen_if="pa-gen-b", mon_if="pa-mon-b", cv_center_id=b.id,
    ))
    agent = TrafficAgent(name="lab-agent", token_hash="h" * 64, local_lab_id=str(lab_id))
    manual = TrafficAgent(name="manual-agent", token_hash="m" * 64)
    db_session.add_all([agent, manual])
    await db_session.commit()
    scn = await _scenario(db_session, test_user)

    # Nothing named: the lab's center, not the default.
    assert (await agent_manager.resolve_deploy_cv_center(db_session, agent, scn, None)).id == b.id
    assert (await agent_manager.resolve_deploy_cv_center(db_session, agent, scn, b.id)).id == b.id
    with pytest.raises(ValidationError, match="has to target that center"):
        await agent_manager.resolve_deploy_cv_center(db_session, agent, scn, a.id)

    # A manual agent takes what it is given, else the default.
    assert (await agent_manager.resolve_deploy_cv_center(db_session, manual, scn, None)).id == a.id
    assert (await agent_manager.resolve_deploy_cv_center(db_session, manual, scn, b.id)).id == b.id


async def test_deploy_without_any_center_proceeds_without_cv(db_session, test_user):
    from app.services.agent_manager import agent_manager

    manual = TrafficAgent(name="manual-agent", token_hash="m" * 64)
    db_session.add(manual)
    await db_session.commit()
    scn = await _scenario(db_session, test_user)
    assert await agent_manager.resolve_deploy_cv_center(db_session, manual, scn, None) is None


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
async def test_center_routes_round_trip(client: AsyncClient, admin_auth_headers, auth_headers):
    created = await client.post(
        "/api/v1/cyber-vision/centers",
        headers=admin_auth_headers,
        json={"url": "https://10.0.0.1", "api_token": "secret-classic", "new_ui_token": "secret-ui"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "10.0.0.1" and body["is_default"] is True
    assert body["api_token_set"] and body["new_ui_token_set"]
    assert "secret" not in created.text

    second = await client.post(
        "/api/v1/cyber-vision/centers",
        headers=admin_auth_headers,
        json={"name": "Lab B", "url": "https://10.0.0.2", "api_token": "t"},
    )
    b_id = second.json()["id"]
    assert second.json()["is_default"] is False

    # Non-admins can list (for pickers) but not change.
    listed = await client.get("/api/v1/cyber-vision/centers", headers=auth_headers)
    assert listed.status_code == 200
    assert [c["name"] for c in listed.json()["centers"]] == ["10.0.0.1", "Lab B"]
    denied = await client.post(f"/api/v1/cyber-vision/centers/{b_id}/default", headers=auth_headers)
    assert denied.status_code == 403

    made = await client.post(f"/api/v1/cyber-vision/centers/{b_id}/default", headers=admin_auth_headers)
    assert made.json()["is_default"] is True
    renamed = await client.put(
        f"/api/v1/cyber-vision/centers/{b_id}", headers=admin_auth_headers, json={"name": "Plant B"}
    )
    assert renamed.json()["name"] == "Plant B"

    # Legacy single-center shape reports the default center.
    legacy = await client.get("/api/v1/cyber-vision/settings", headers=admin_auth_headers)
    assert legacy.json()["cyber_vision_url"] == "https://10.0.0.2"

    refused = await client.delete(f"/api/v1/cyber-vision/centers/{b_id}", headers=admin_auth_headers)
    assert refused.status_code == 409  # default while another exists
    first_id = body["id"]
    gone = await client.delete(f"/api/v1/cyber-vision/centers/{first_id}", headers=admin_auth_headers)
    assert gone.status_code == 204


async def test_legacy_settings_put_creates_the_first_center(client: AsyncClient, admin_auth_headers):
    resp = await client.put(
        "/api/v1/cyber-vision/settings",
        headers=admin_auth_headers,
        json={"cyber_vision_url": "https://10.0.0.7", "cyber_vision_api_token": "t"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["cyber_vision_url"] == "https://10.0.0.7"
    centers = (await client.get("/api/v1/cyber-vision/centers", headers=admin_auth_headers)).json()
    assert len(centers["centers"]) == 1 and centers["default_center_id"]


async def test_unknown_center_is_404_and_unconfigured_is_400(client: AsyncClient, auth_headers):
    none = await client.get("/api/v1/cyber-vision/presets", headers=auth_headers)
    assert none.status_code == 400
    missing = await client.get(
        f"/api/v1/cyber-vision/presets?center_id={uuid.uuid4()}", headers=auth_headers
    )
    assert missing.status_code == 404
