# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Startup services for initializing the application."""

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.cloud_service import CloudServiceEndpoint, CloudServiceProvider
from app.models.scenario import Scenario
from app.models.settings import DEFAULT_SETTINGS, SystemSetting
from app.models.traffic_agent import TrafficAgent, AgentDeployment
from app.models.user import User
from app.services.cloud_service_data import BUILTIN_CLOUD_SERVICES
from app.services.seed_data import run_seed_data

logger = logging.getLogger(__name__)


async def create_first_user(db: AsyncSession) -> User | None:
    """Create the first admin user if no users exist AND a password was provided.

    Empty FIRST_USER_PASSWORD means "no env-driven bootstrap" — the operator
    will create the admin via the first-run setup wizard. This is the default
    for new installs; legacy installs that still have ADMIN_PASSWORD in their
    env continue to work.
    """
    if not settings.first_user_password:
        return None

    result = await db.execute(select(User).limit(1))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        return None

    user = User(
        username=settings.first_user_username,
        password_hash=get_password_hash(settings.first_user_password),
        is_admin=True,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def auto_graduate_setup(db: AsyncSession) -> bool:
    """Mark setup.completed=true if an admin user already exists.

    Existing installs (created before the setup wizard existed) have an admin
    user but no `setup.completed` row was ever flipped to true. On first boot
    of the new code, detect that situation and graduate them automatically so
    the wizard doesn't appear after an upgrade.

    Returns True iff this run flipped the flag.
    """
    completed_row = (
        await db.execute(
            select(SystemSetting).where(SystemSetting.key == "setup.completed")
        )
    ).scalar_one_or_none()

    if completed_row is not None and completed_row.value == "true":
        return False  # already complete, nothing to do

    admin_exists = (
        await db.execute(
            select(User).where(User.is_admin == True).limit(1)  # noqa: E712
        )
    ).scalar_one_or_none() is not None

    if not admin_exists:
        return False

    if completed_row is None:
        # The seed_default_settings step normally inserts this row; defensive
        # path in case auto_graduate runs first.
        completed_row = SystemSetting(
            key="setup.completed",
            value="true",
            is_secret=False,
            category="setup",
            description="Whether first-run setup has been completed",
        )
        db.add(completed_row)
    else:
        completed_row.value = "true"

    await db.commit()
    logger.info(
        "auto_graduate_setup: marked setup.completed=true (admin user already exists)"
    )
    return True


async def seed_default_settings(db: AsyncSession) -> int:
    """Seed default settings if they don't exist."""
    created = 0

    for setting_data in DEFAULT_SETTINGS:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == setting_data["key"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            setting = SystemSetting(**setting_data)
            db.add(setting)
            created += 1

    if created > 0:
        await db.commit()

    return created


async def seed_cloud_services(db: AsyncSession) -> int:
    """Seed builtin cloud service endpoints.

    These are pre-configured cloud services like Talk2M and TeamViewer
    that OT devices commonly connect to for remote access.

    Returns:
        Number of cloud services created
    """
    created = 0

    for service_data in BUILTIN_CLOUD_SERVICES:
        # Check if service already exists by name
        result = await db.execute(
            select(CloudServiceEndpoint).where(
                CloudServiceEndpoint.name == service_data["name"],
                CloudServiceEndpoint.is_builtin.is_(True),
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            service = CloudServiceEndpoint(
                name=service_data["name"],
                provider=CloudServiceProvider(service_data["provider"]),
                ip_addresses=service_data["ip_addresses"],
                primary_ip=service_data["primary_ip"],
                port=service_data.get("port", 443),
                hostname=service_data.get("hostname"),
                tls_enabled=service_data.get("tls_enabled", True),
                heartbeat_interval_ms=service_data.get("heartbeat_interval_ms", 30000),
                region=service_data.get("region"),
                description=service_data.get("description"),
                is_builtin=True,
                is_active=True,
            )
            db.add(service)
            created += 1

    if created > 0:
        await db.commit()

    return created


async def reconcile_agent_statuses(db: AsyncSession) -> int:
    """Reset all agent statuses to offline on startup.

    When the backend restarts, all WebSocket connections are lost but the database
    may still show agents as 'online'. This creates a mismatch where the UI shows
    agents as online but they can't receive commands.

    By resetting all agents to offline on startup, we ensure the status is accurate.
    Agents will reconnect and be marked online again via the WebSocket handler.
    """
    # Reset all online agents to offline
    result = await db.execute(
        update(TrafficAgent)
        .where(TrafficAgent.status == "online")
        .values(status="offline")
    )
    agents_reset = result.rowcount

    # Also reset any running/stopping deployments to disconnected
    result = await db.execute(
        update(AgentDeployment)
        .where(AgentDeployment.state.in_(["running", "starting", "stopping"]))
        .values(state="disconnected")
    )
    deployments_reset = result.rowcount

    if agents_reset > 0 or deployments_reset > 0:
        await db.commit()

    return agents_reset


def _agent_vt(v: str | None) -> tuple:
    import re
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)


def _find_loaded_agent_image() -> tuple[str | None, str | None]:
    """Locate a loaded agent image + its org.packetarch.agent_version label.

    Prefers the canonical packetarch-agent:latest; falls back to a release-tagged
    packetarch/agent:* image. Version is None for images built before the label
    existed (older bundles) — callers then fall back to a source build.
    """
    try:
        import docker
        client = docker.from_env()
    except Exception:
        return None, None
    try:
        img = client.images.get("packetarch-agent:latest")
        return "packetarch-agent:latest", (img.labels or {}).get("org.packetarch.agent_version")
    except Exception:
        pass
    try:
        imgs = client.images.list(name="packetarch/agent")
        if imgs:
            img = imgs[0]
            ref = (img.tags or ["packetarch/agent:latest"])[0]
            return ref, (img.labels or {}).get("org.packetarch.agent_version")
    except Exception:
        pass
    return None, None


def _serve_agent_image(image_ref: str, version: str) -> None:
    """Publish a loaded agent image as the downloadable served tarball + metadata.

    The 'distribute the prebuilt image' path — no source build. Writes the
    gzipped ``docker save`` to AGENT_IMAGE_PATH and stamps version.txt +
    checksum.txt exactly like the in-app build, so /agent/image.tar.gz and
    out-of-date detection behave identically.
    """
    import gzip
    import hashlib

    import docker

    from app.api.routes.agents import (
        AGENT_CHECKSUM_PATH,
        AGENT_IMAGE_PATH,
        AGENT_VERSION_PATH,
    )

    client = docker.from_env()
    img = client.images.get(image_ref)
    # Ensure the canonical tag exists so the tarball loads as
    # packetarch-agent:latest on the agent host (its compose references it).
    try:
        img.tag("packetarch-agent", "latest")
    except Exception:
        pass

    AGENT_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_img = client.images.get("packetarch-agent:latest")
    with gzip.open(AGENT_IMAGE_PATH, "wb") as f:
        for chunk in save_img.save(named=True):
            f.write(chunk)

    checksum = hashlib.sha256()
    with open(AGENT_IMAGE_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            checksum.update(chunk)
    AGENT_CHECKSUM_PATH.write_text(checksum.hexdigest())
    AGENT_VERSION_PATH.write_text(version)


def _try_pull_agent_from_registry(ref: str) -> tuple[str | None, str | None]:
    """Best-effort pull of the agent image from a registry (e.g. GHCR).

    Returns (image_ref, org.packetarch.agent_version) on success, else
    (None, None). Never raises — an unreachable registry (air-gapped host) just
    means we fall back to a locally-loaded image.
    """
    try:
        import docker
        client = docker.from_env()
    except Exception:
        return None, None
    try:
        repo, tag = (ref.rsplit(":", 1) if ":" in ref.rsplit("/", 1)[-1] else (ref, "latest"))
        img = client.images.pull(repo, tag=tag)
        return ref, (img.labels or {}).get("org.packetarch.agent_version")
    except Exception as e:  # noqa: BLE001
        logger.info("agent registry pull skipped/failed (%s): %s", ref, e)
        return None, None


async def ensure_agent_image_current() -> str:
    """Keep the served agent tarball current with the newest available agent.

    "Build once, distribute" — no on-box build unless a developer changed the
    agent source:
      * Source mounted (dev/git) → source is authoritative: re-serve a matching
        loaded image if present, else background-build from source.
      * No source (offline bundle, or a source-less install) → take the newest
        agent image available LOCALLY (bundle-loaded / previously pulled) or, when
        AGENT_REGISTRY_PULL_ENABLED, from the configured registry (GHCR), then
        re-serve it (fast ``docker save``, no build). Air-gapped installs disable
        the pull and rely on the bundle-loaded image.
    Re-serving writes version.txt/checksum so the update banner + agent
    self-update fire automatically. Gated by the caller to live-traffic.
    """
    import asyncio
    import threading

    from fastapi import BackgroundTasks

    from app.core.config import settings
    from app.api.routes.agents import (
        AGENT_IMAGE_PATH,
        AGENT_VERSION_PATH,
        build_agent_image,
        extract_agent_version_from_source,
    )

    served_v = AGENT_VERSION_PATH.read_text().strip() if AGENT_VERSION_PATH.exists() else None
    source_v = extract_agent_version_from_source()  # None when the source isn't mounted
    image_ref, image_v = _find_loaded_agent_image()

    def _up_to_date(v: str) -> bool:
        return bool(served_v) and AGENT_IMAGE_PATH.exists() and _agent_vt(served_v) >= _agent_vt(v)

    # --- Source available (dev/git with the source mounted) -----------------
    # Source is authoritative: re-serve a matching loaded image if we have one,
    # else rebuild from source in the background.
    if source_v:
        if _up_to_date(source_v):
            return f"up to date (served v{served_v})"
        if image_ref and image_v and _agent_vt(image_v) >= _agent_vt(source_v):
            try:
                _serve_agent_image(image_ref, image_v)
                return f"served prebuilt agent image v{image_v} (was v{served_v or 'none'})"
            except Exception as e:  # noqa: BLE001
                logger.warning("re-serve of prebuilt agent image failed: %s", e)
        bt = BackgroundTasks()
        await build_agent_image(bt)  # writes status, guards concurrent builds, queues the build
        if bt.tasks:
            threading.Thread(
                target=lambda: asyncio.run(bt()), name="agent-image-autobuild", daemon=True
            ).start()
            return f"rebuilding agent image from source (v{source_v}, was v{served_v or 'none'})"
        return f"build already in progress / unavailable (was v{served_v or 'none'})"

    # --- No source: newest local image, or pull from the registry -----------
    best_ref, best_v = image_ref, image_v
    if settings.agent_registry_pull_enabled:
        pulled_ref, pulled_v = _try_pull_agent_from_registry(settings.agent_image_registry_ref)
        if pulled_v and (best_v is None or _agent_vt(pulled_v) > _agent_vt(best_v)):
            best_ref, best_v = pulled_ref, pulled_v

    if not best_v:
        return "skipped (no source, no versioned local image, no registry image)"
    if _up_to_date(best_v):
        return f"up to date (served v{served_v})"
    try:
        _serve_agent_image(best_ref, best_v)
        return f"served agent image v{best_v} (was v{served_v or 'none'})"
    except Exception as e:  # noqa: BLE001
        logger.warning("re-serve of agent image failed: %s", e)
        return f"check failed: {e}"


async def reconcile_local_labs(db: AsyncSession) -> str:
    """Re-converge app-managed local sensor labs after a full stack restart.

    The host-agent already reconciles its own persisted specs on ITS boot, but a
    full `docker compose up` restarts the backend too; this nudges the host-agent
    to re-apply every desired lab so they come back without operator action.

    We do NOT rebuild specs from the DB: the plaintext agent token isn't stored
    here (only its hash), but it IS persisted in the host-agent's spec files on
    the shared volume. So we just count non-stopped LocalLab rows and, if any,
    fire a single reconcile request the host-agent acts on. Never raises.
    """
    from app.models.local_lab import LocalLab
    from app.services import host_agent_client

    pending = (
        await db.execute(
            select(LocalLab).where(LocalLab.state != "stopped")
        )
    ).scalars().all()

    if not pending:
        return "no local labs to reconcile"

    if not host_agent_client.is_available():
        logger.warning(
            "reconcile_local_labs: %d local lab(s) in DB but host-agent volume "
            "unavailable — not reconciled (rebuild from the Agents page if needed)",
            len(pending),
        )
        return f"{len(pending)} lab(s) NOT reconciled (host-agent unavailable)"

    host_agent_client.submit_reconcile()
    logger.info("reconcile_local_labs: requested reconcile of %d local lab(s)", len(pending))
    return f"requested reconcile of {len(pending)} local lab(s)"


async def reconcile_pending_naming(db: AsyncSession) -> str:
    """Re-enqueue background device-naming for scenarios caught mid-naming.

    A full `docker compose up` (or a worker crash) loses any in-flight
    naming task, which would otherwise leave the scenario stuck in
    'pending'/'running' forever — and therefore un-deployable, since the
    deploy/generate guard blocks those states. On boot we find such
    scenarios and re-enqueue the task using the request params persisted
    in ``definition["_naming_request"]`` at create time. Never raises.
    """
    from app.models.scenario import Scenario

    stuck = (
        await db.execute(
            select(Scenario).where(
                Scenario.naming_status.in_(("pending", "running"))
            )
        )
    ).scalars().all()

    if not stuck:
        return "no scenarios awaiting naming"

    try:
        from app.traffic_generator.tasks import apply_template_naming
    except Exception as e:  # noqa: BLE001
        logger.warning("reconcile_pending_naming: cannot import task: %s", e)
        return f"{len(stuck)} scenario(s) NOT reconciled (task import failed)"

    requeued = 0
    failed = 0
    for scenario in stuck:
        req = (scenario.definition or {}).get("_naming_request")
        if not req:
            # No stored request to replay — don't leave it stuck.
            scenario.naming_status = "failed"
            failed += 1
            continue
        try:
            scenario.naming_status = "pending"
            apply_template_naming.apply_async(
                kwargs={"scenario_id": str(scenario.id), **req}
            )
            requeued += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "reconcile_pending_naming: re-enqueue failed for %s: %s",
                scenario.id, e,
            )
            scenario.naming_status = "failed"
            failed += 1
    await db.commit()
    logger.info(
        "reconcile_pending_naming: re-enqueued %d, marked %d failed", requeued, failed
    )
    return f"re-enqueued {requeued} naming task(s), {failed} marked failed"


async def run_startup_tasks(db: AsyncSession) -> dict:
    """Run all startup tasks."""
    results = {}

    # Create first user
    first_user = await create_first_user(db)
    if first_user:
        results["first_user"] = f"Created admin user: {first_user.username}"
    else:
        results["first_user"] = "Admin user already exists"

    # Seed default settings
    settings_created = await seed_default_settings(db)
    results["settings"] = f"Seeded {settings_created} default settings"

    # Auto-graduate existing installs: if an admin already exists (legacy
    # bootstrap or pre-wizard install), mark setup as complete so the wizard
    # doesn't fire on upgrade.
    graduated = await auto_graduate_setup(db)
    results["setup_state"] = (
        "auto-graduated (admin user already exists)" if graduated
        else "left unchanged"
    )

    # Seed device profiles and protocol templates
    seed_results = await run_seed_data(db)
    results.update(seed_results)

    # Seed cloud service endpoints
    cloud_services_created = await seed_cloud_services(db)
    results["cloud_services"] = f"Seeded {cloud_services_created} cloud service endpoints"

    # Pre-warm fingerprint cache (uses sync DB, safe here since no event loop contention)
    from app.services.fingerprint_cache import get_fingerprint_cache
    cache = get_fingerprint_cache()
    cache.refresh()
    fp_count = len(cache.index.all_fingerprints)
    results["fingerprint_cache"] = f"Pre-warmed fingerprint cache with {fp_count} fingerprints"

    # Reconcile agent statuses (reset all to offline since no agents connected at startup)
    # Skipped in PCAP-only deployments — no agents will ever connect.
    from app.core.config import settings
    if settings.live_traffic_enabled:
        agents_reset = await reconcile_agent_statuses(db)
        if agents_reset > 0:
            results["agent_reconcile"] = f"Reset {agents_reset} stale 'online' agent(s) to offline"
        else:
            results["agent_reconcile"] = "No stale agent statuses found"
        # Keep the served agent image current so installs/upgrades get the latest build.
        try:
            results["agent_image"] = await ensure_agent_image_current()
        except Exception as e:  # never let an image-build hiccup block startup
            logger.warning("ensure_agent_image_current failed: %s", e)
            results["agent_image"] = f"check failed: {e}"
        # Re-converge app-managed local sensor labs after a full stack restart.
        try:
            results["local_labs"] = await reconcile_local_labs(db)
        except Exception as e:  # never let lab reconcile block startup
            logger.warning("reconcile_local_labs failed: %s", e)
            results["local_labs"] = f"reconcile failed: {e}"
    else:
        results["agent_reconcile"] = "skipped (live_traffic_enabled=false)"

    # Walk every scenario and apply protocol/fingerprint consistency.
    # Idempotent — scenarios already clean are skipped.
    repaired = await batch_repair_scenario_protocols(db)
    if repaired > 0:
        results["protocol_repair"] = (
            f"Auto-repaired protocols on {repaired} scenario(s)"
        )
    else:
        results["protocol_repair"] = "All scenarios already protocol-clean"

    # One-time vendor-aware narrowing. The first auto-repair pass over-
    # broadened device.protocols by trusting fingerprint identity blocks
    # (catalog has identity for protocols devices don't natively speak,
    # e.g. Modbus on a Siemens S7). This pass uses vendor-native lookup
    # plus flow-declared protocols as the authoritative whitelist and
    # drops everything else. Gated by a SystemSetting so it only runs
    # once per install.
    narrowed = await one_shot_narrow_scenario_protocols(db)
    if narrowed is None:
        results["protocol_narrow"] = "skipped (already applied)"
    elif narrowed > 0:
        results["protocol_narrow"] = (
            f"Narrowed protocols on {narrowed} scenario(s) by vendor"
        )
    else:
        results["protocol_narrow"] = "No vendor-narrowing needed"

    # Re-enqueue any background device-naming lost to a restart/crash so
    # scenarios don't stay stuck (and therefore un-deployable) in
    # pending/running. Not gated on live_traffic — naming feeds PCAP too.
    try:
        results["pending_naming"] = await reconcile_pending_naming(db)
    except Exception as e:  # never let naming reconcile block startup
        logger.warning("reconcile_pending_naming failed: %s", e)
        results["pending_naming"] = f"reconcile failed: {e}"

    return results


_NARROW_FLAG_KEY = "scenario.protocol_narrow_v4_inline_supported_done"


async def one_shot_narrow_scenario_protocols(
    db: AsyncSession,
) -> int | None:
    """One-time vendor-aware protocol narrowing across all scenarios.

    Returns the number of scenarios narrowed, or None if the pass has
    already run (skipped). Idempotency is enforced via a system_settings
    row so the narrowing fires once per install.
    """
    from sqlalchemy.orm.attributes import flag_modified
    from app.services.scenario_enrichment import narrow_protocols_by_vendor

    # Check the gate.
    flag = await db.execute(
        select(SystemSetting).where(SystemSetting.key == _NARROW_FLAG_KEY)
    )
    if flag.scalar_one_or_none() is not None:
        return None

    result = await db.execute(select(Scenario))
    scenarios = result.scalars().all()
    narrowed = 0
    for s in scenarios:
        if not s.definition:
            continue
        original = s.definition
        narrowed_def = narrow_protocols_by_vendor(original)
        if narrowed_def is original:
            continue
        s.definition = narrowed_def
        flag_modified(s, "definition")
        narrowed += 1
        logger.info(
            "Vendor-narrowing applied to scenario %s (%s)",
            s.id, s.name,
        )

    # Mark the pass as done so it never runs again.
    db.add(SystemSetting(
        key=_NARROW_FLAG_KEY,
        value="true",
        category="internal",
        is_secret=False,
    ))
    await db.commit()
    return narrowed


async def batch_repair_scenario_protocols(db: AsyncSession) -> int:
    """Walk every scenario and apply both protocol and flow-protocol
    repairs.

    Two-pass per scenario:
      1. auto_repair_protocols → device.protocols match fingerprint truth
      2. repair_flow_protocols → flow.protocol matches both endpoints

    Order matters: flow repair depends on the protocols being clean.

    Idempotent — only commits when something changed.
    """
    from sqlalchemy.orm.attributes import flag_modified
    from app.services.scenario_enrichment import (
        auto_repair_protocols,
        repair_flow_protocols,
    )

    result = await db.execute(select(Scenario))
    scenarios = result.scalars().all()
    repaired = 0
    for s in scenarios:
        if not s.definition:
            continue
        original = s.definition
        repaired_def = auto_repair_protocols(original)
        repaired_def = repair_flow_protocols(repaired_def)
        if repaired_def is original:
            # Nothing changed in either pass.
            continue
        s.definition = repaired_def
        flag_modified(s, "definition")
        repaired += 1
        logger.info(
            "Boot-time protocol+flow repair applied to scenario %s (%s)",
            s.id, s.name,
        )
    if repaired > 0:
        await db.commit()
    return repaired
