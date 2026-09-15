# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cyber Vision Centers: lookup, client construction, legacy migration.

The single place that turns "which Cyber Vision Center?" into a configured
client. Every CV consumer goes through ``cv_client`` / ``cv_v1_client`` /
``cv_ui_client`` (the historical ``cv_service_from_settings`` /
``cv_v1_service_from_settings`` factories are thin wrappers over them).

Three credential kinds, one per surface: the classic ``/api/3.0`` token, the
new-UI ``/cvapi/v1`` token, and a UI username/password for the private
``/scv`` surface — which is the only way to create a network CV 5.6 actually
registers. See ``cyber_vision_ui_service``.

Resolution rule, used everywhere:
- an explicit ``center_id`` must exist (``NotFoundError`` otherwise);
- no ``center_id`` means the default center;
- nothing configured means ``None`` (callers decide whether that is fatal).

Objects that live on a center carry its id — ``LocalLab.cv_center_id`` and
``scenario.definition['cyber_vision']['center_id']`` — and teardown/reconcile
follow those ids. Only brand-new work falls back to the default.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select, update

from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.cyber_vision_center import CyberVisionCenter
from app.models.local_lab import LocalLab
from app.models.settings import SystemSetting
from app.services.cyber_vision_service import CyberVisionService
from app.services.cyber_vision_ui_service import CyberVisionUIService
from app.services.cyber_vision_v1_service import CyberVisionV1Service

logger = logging.getLogger(__name__)

# The pre-multi-center configuration: four global system_settings rows.
LEGACY_CV_KEYS = (
    "cyber_vision_url",
    "cyber_vision_api_token",
    "cyber_vision_verify_ssl",
    "cyber_vision_new_ui_token",
)

CenterRef = uuid.UUID | str | None


def normalize_url(url: str) -> str:
    """Canonical form used for storage and the uniqueness check."""
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ValidationError("A Cyber Vision Center URL is required.")
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValidationError(f"'{url}' is not a valid Cyber Vision Center URL.")
    return url


def default_name_for_url(url: str) -> str:
    """A readable default center name: the URL's host."""
    return urlparse(normalize_url(url)).netloc or url


def _as_uuid(center_id: CenterRef) -> uuid.UUID | None:
    if center_id is None or center_id == "":
        return None
    if isinstance(center_id, uuid.UUID):
        return center_id
    try:
        return uuid.UUID(str(center_id))
    except ValueError:
        raise ValidationError(f"'{center_id}' is not a valid Cyber Vision Center id.")


# --------------------------------------------------------------------------- #
# Lookup
# --------------------------------------------------------------------------- #
async def list_centers(db) -> list[CyberVisionCenter]:
    result = await db.execute(
        select(CyberVisionCenter).order_by(
            CyberVisionCenter.is_default.desc(), CyberVisionCenter.name
        )
    )
    return list(result.scalars().all())


async def default_center(db) -> CyberVisionCenter | None:
    result = await db.execute(
        select(CyberVisionCenter).where(CyberVisionCenter.is_default.is_(True))
    )
    return result.scalar_one_or_none()


async def get_center(db, center_id: CenterRef) -> CyberVisionCenter:
    """The named center. Raises NotFoundError if it doesn't exist."""
    cid = _as_uuid(center_id)
    center = await db.get(CyberVisionCenter, cid) if cid else None
    if center is None:
        raise NotFoundError("Cyber Vision Center", str(center_id))
    return center


async def resolve_center(db, center_id: CenterRef = None) -> CyberVisionCenter | None:
    """Explicit id → that center (must exist); None → the default (or None)."""
    if _as_uuid(center_id) is not None:
        return await get_center(db, center_id)
    return await default_center(db)


async def center_names(db) -> dict[str, str]:
    """{center id (str): name} for labeling responses."""
    return {str(c.id): c.name for c in await list_centers(db)}


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
def classic_client(center: CyberVisionCenter | None) -> CyberVisionService | None:
    """Classic /api/3.0 client for a center, or None without a classic token."""
    if center is None or not center.api_token:
        return None
    token = decrypt_value(center.api_token)
    if not token:
        return None
    return CyberVisionService(center.url, token, center.verify_ssl)


def v1_client(center: CyberVisionCenter | None) -> CyberVisionV1Service | None:
    """New-UI /cvapi/v1 client for a center, or None without a new-UI token."""
    if center is None or not center.new_ui_token:
        return None
    token = decrypt_value(center.new_ui_token)
    if not token:
        return None
    return CyberVisionV1Service(center.url, token, center.verify_ssl)


def ui_client(center: CyberVisionCenter | None) -> CyberVisionUIService | None:
    """CV UI session client (/scv) for a center, or None without UI credentials.

    Both halves are required: a center carrying only a username or only a
    password has no usable UI session, so it counts as unconfigured rather than
    failing later at login.
    """
    if center is None or not center.ui_username or not center.ui_password:
        return None
    password = decrypt_value(center.ui_password)
    if not password:
        return None
    return CyberVisionUIService(center.url, center.ui_username, password, center.verify_ssl)


async def cv_client(db, center_id: CenterRef = None) -> CyberVisionService | None:
    return classic_client(await resolve_center(db, center_id))


async def cv_v1_client(db, center_id: CenterRef = None) -> CyberVisionV1Service | None:
    return v1_client(await resolve_center(db, center_id))


async def cv_ui_client(db, center_id: CenterRef = None) -> CyberVisionUIService | None:
    return ui_client(await resolve_center(db, center_id))


async def require_cv_client(db, center_id: CenterRef = None) -> CyberVisionService:
    """Like ``cv_client`` but a missing configuration is a 400, not None."""
    center = await resolve_center(db, center_id)
    if center is None:
        raise ValidationError(
            "Cyber Vision is not configured. Add a Cyber Vision Center under "
            "Settings > Cyber Vision."
        )
    client = classic_client(center)
    if client is None:
        raise ValidationError(
            f"Cyber Vision Center '{center.name}' has no API token configured."
        )
    return client


# --------------------------------------------------------------------------- #
# Create / update / delete
# --------------------------------------------------------------------------- #
async def _ensure_unique(db, *, name: str, url: str, exclude_id: uuid.UUID | None = None) -> None:
    for col, value, label in (
        (CyberVisionCenter.name, name, "name"),
        (CyberVisionCenter.url, url, "URL"),
    ):
        q = select(CyberVisionCenter).where(col == value)
        if exclude_id is not None:
            q = q.where(CyberVisionCenter.id != exclude_id)
        if (await db.execute(q)).scalar_one_or_none() is not None:
            raise ConflictError(f"A Cyber Vision Center with {label} '{value}' already exists.")


async def _clear_default(db) -> None:
    await db.execute(
        update(CyberVisionCenter)
        .where(CyberVisionCenter.is_default.is_(True))
        .values(is_default=False)
    )
    await db.flush()


async def create_center(
    db,
    *,
    url: str,
    api_token: str,
    name: str | None = None,
    new_ui_token: str | None = None,
    ui_username: str | None = None,
    ui_password: str | None = None,
    verify_ssl: bool = False,
    is_default: bool = False,
) -> CyberVisionCenter:
    """Add a center. The first center always becomes the default. Flushes, does
    not commit (callers own the transaction)."""
    url = normalize_url(url)
    name = (name or "").strip() or default_name_for_url(url)
    if not api_token:
        raise ValidationError("A Cyber Vision API token is required.")
    await _ensure_unique(db, name=name, url=url)

    is_first = (await db.execute(select(func.count(CyberVisionCenter.id)))).scalar_one() == 0
    make_default = is_default or is_first
    if make_default:
        await _clear_default(db)
    center = CyberVisionCenter(
        name=name,
        url=url,
        api_token=encrypt_value(api_token),
        new_ui_token=encrypt_value(new_ui_token) if new_ui_token else None,
        ui_username=(ui_username or "").strip() or None,
        ui_password=encrypt_value(ui_password) if ui_password else None,
        verify_ssl=verify_ssl,
        is_default=make_default,
    )
    db.add(center)
    await db.flush()
    return center


async def update_center(
    db,
    center: CyberVisionCenter,
    *,
    name: str | None = None,
    url: str | None = None,
    api_token: str | None = None,
    new_ui_token: str | None = None,
    ui_username: str | None = None,
    ui_password: str | None = None,
    verify_ssl: bool | None = None,
) -> CyberVisionCenter:
    """Partial update. ``None`` leaves a field alone; an empty string clears an
    optional credential (``new_ui_token``, ``ui_username``, ``ui_password``).
    Flushes, does not commit."""
    new_name = (name.strip() if name is not None else center.name) or center.name
    new_url = normalize_url(url) if url is not None else center.url
    if new_url != center.url and await center_in_use(db, center.id):
        raise ConflictError(
            f"Cyber Vision Center '{center.name}' still has local labs or provisioned "
            "scenarios. Changing its URL would strand them; tear them down first, or "
            "add the new URL as a separate center."
        )
    await _ensure_unique(db, name=new_name, url=new_url, exclude_id=center.id)
    center.name = new_name
    center.url = new_url
    if api_token:
        center.api_token = encrypt_value(api_token)
    if new_ui_token is not None:
        center.new_ui_token = encrypt_value(new_ui_token) if new_ui_token else None
    if ui_username is not None:
        center.ui_username = ui_username.strip() or None
    if ui_password is not None:
        center.ui_password = encrypt_value(ui_password) if ui_password else None
    if verify_ssl is not None:
        center.verify_ssl = verify_ssl
    await db.flush()
    return center


async def set_default(db, center: CyberVisionCenter) -> CyberVisionCenter:
    if not center.is_default:
        await _clear_default(db)
        center.is_default = True
        await db.flush()
    return center


async def usage(db, center_id: uuid.UUID) -> dict[str, int]:
    """How many objects live on a center: local labs + CV-provisioned scenarios."""
    labs = (
        await db.execute(
            select(func.count(LocalLab.id)).where(LocalLab.cv_center_id == center_id)
        )
    ).scalar_one()
    scenarios = await _scenarios_on_center_count(db, center_id)
    return {"local_labs": int(labs), "scenarios": int(scenarios)}


def scenario_center_id_column():
    """SQL expression for a scenario's recorded ``cyber_vision.center_id`` (text).

    Reads the one JSON subfield in the database instead of loading every
    scenario definition. Compiles to ``->>`` on Postgres and ``JSON_EXTRACT``
    on sqlite (tests); NULL when the scenario has no CV state or no center.
    """
    from app.models.scenario import Scenario

    return Scenario.definition["cyber_vision"]["center_id"].as_string()


async def _scenarios_on_center_count(db, center_id: uuid.UUID) -> int:
    from app.models.scenario import Scenario

    return (
        await db.execute(
            select(func.count(Scenario.id)).where(
                scenario_center_id_column() == str(center_id)
            )
        )
    ).scalar_one()


async def center_in_use(db, center_id: uuid.UUID) -> bool:
    u = await usage(db, center_id)
    return bool(u["local_labs"] or u["scenarios"])


async def delete_center(db, center: CyberVisionCenter) -> None:
    """Remove a center. Refuses while labs or provisioned scenarios live on it
    (their sensors / presets would be orphaned with no way to clean them up),
    and refuses to delete the default while other centers exist."""
    u = await usage(db, center.id)
    if u["local_labs"] or u["scenarios"]:
        raise ConflictError(
            f"Cyber Vision Center '{center.name}' still has {u['local_labs']} local lab(s) "
            f"and {u['scenarios']} provisioned scenario(s). Tear those down first."
        )
    if center.is_default:
        others = (
            await db.execute(
                select(func.count(CyberVisionCenter.id)).where(CyberVisionCenter.id != center.id)
            )
        ).scalar_one()
        if others:
            raise ConflictError(
                "This is the default Cyber Vision Center. Make another center the "
                "default before deleting it."
            )
    await db.delete(center)
    await db.flush()


def to_summary(center: CyberVisionCenter, usage_counts: dict[str, int] | None = None) -> dict[str, Any]:
    """API shape (never includes tokens)."""
    return {
        "id": str(center.id),
        "name": center.name,
        "url": center.url,
        "verify_ssl": center.verify_ssl,
        "is_default": center.is_default,
        "api_token_set": bool(center.api_token),
        "new_ui_token_set": bool(center.new_ui_token),
        # The UI username is shown (so an operator can see which account a
        # center logs in as); the password never leaves the server.
        "ui_username": center.ui_username,
        "ui_password_set": bool(center.ui_password),
        "local_labs": (usage_counts or {}).get("local_labs", 0),
        "scenarios": (usage_counts or {}).get("scenarios", 0),
        "created_at": center.created_at,
        "updated_at": center.updated_at,
    }


# --------------------------------------------------------------------------- #
# Legacy single-center migration (boot-time, idempotent)
# --------------------------------------------------------------------------- #
async def migrate_legacy_settings(db) -> str:
    """Move the old global ``cyber_vision_*`` settings into the first center.

    Runs on every boot and is a no-op once done. When no center exists yet and
    a legacy URL + token are present, it creates the default center with the
    token CIPHERTEXT copied verbatim (same Fernet key, so no decrypt/re-encrypt),
    stamps every existing local lab and every CV-provisioned scenario with it
    (so later changing the default never retargets them), and deletes the
    legacy rows so there is one source of truth. One transaction.
    """
    rows = {
        s.key: s
        for s in (
            await db.execute(select(SystemSetting).where(SystemSetting.key.in_(LEGACY_CV_KEYS)))
        ).scalars().all()
    }
    if not rows:
        return "no legacy settings"

    have_centers = (await db.execute(select(func.count(CyberVisionCenter.id)))).scalar_one() > 0
    url_row = rows.get("cyber_vision_url")
    token_row = rows.get("cyber_vision_api_token")
    legacy_url = (url_row.value if url_row else "") or ""
    legacy_token = (token_row.value if token_row else "") or ""

    message = "legacy settings were empty; removed"
    if not have_centers and legacy_url and legacy_token:
        url = normalize_url(legacy_url)
        new_ui_row = rows.get("cyber_vision_new_ui_token")
        verify_row = rows.get("cyber_vision_verify_ssl")
        center = CyberVisionCenter(
            name=default_name_for_url(url),
            url=url,
            api_token=legacy_token,  # already encrypted
            new_ui_token=(new_ui_row.value if new_ui_row and new_ui_row.value else None),
            verify_ssl=((verify_row.value if verify_row else "") or "false").lower() == "true",
            is_default=True,
        )
        db.add(center)
        await db.flush()

        labs = await db.execute(
            update(LocalLab).where(LocalLab.cv_center_id.is_(None)).values(cv_center_id=center.id)
        )
        scenarios = await _stamp_scenarios(db, center.id)
        message = (
            f"migrated legacy settings into default center '{center.name}' "
            f"({labs.rowcount or 0} lab(s), {scenarios} scenario(s) stamped)"
        )
    elif have_centers:
        message = "centers already exist; removed stale legacy settings"
    elif legacy_url or legacy_token:
        # Half-configured (a URL with no token, or the reverse). There is no
        # center to build, but deleting would throw away what the operator
        # did enter, so leave the rows for them (or a rollback) to finish.
        # Nothing was written above, so there is nothing to roll back.
        message = (
            "legacy settings are incomplete (URL and API token are both needed); "
            "left in place, add the center under Settings > Cyber Vision"
        )
        logger.warning("cv_centers: %s", message)
        return message

    for row in rows.values():
        await db.delete(row)
    await db.commit()
    logger.info("cv_centers: %s", message)
    return message


async def _stamp_scenarios(db, center_id: uuid.UUID) -> int:
    """Add ``center_id`` to every scenario's CV state that lacks one."""
    from app.models.scenario import Scenario

    stamped = 0
    for scenario in (await db.execute(select(Scenario))).scalars().all():
        definition = scenario.definition if isinstance(scenario.definition, dict) else None
        cv = (definition or {}).get("cyber_vision")
        if not isinstance(cv, dict) or cv.get("center_id"):
            continue
        # Reassign (not mutate) so SQLAlchemy sees the JSON change.
        scenario.definition = {**definition, "cyber_vision": {**cv, "center_id": str(center_id)}}
        stamped += 1
    await db.flush()
    return stamped
