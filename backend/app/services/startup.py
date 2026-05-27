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
                CloudServiceEndpoint.is_builtin == True,
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


async def ensure_agent_image_current() -> str:
    """Rebuild the served agent image if it's missing or older than the source.

    Keeps installs/upgrades automatically current: after an agent version bump,
    the next backend boot rebuilds the served tarball so `install.sh` hands out
    the latest agent. The heavy build runs in a background thread (so startup is
    not blocked) and reuses the build-image route's logic, including its
    concurrent-build guard. Gated by the caller to live-traffic deployments.
    """
    import asyncio
    import re
    import threading

    from fastapi import BackgroundTasks

    from app.api.routes.agents import (
        AGENT_IMAGE_PATH,
        AGENT_VERSION_PATH,
        build_agent_image,
        extract_agent_version_from_source,
    )

    def _vt(v: str | None) -> tuple:
        return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)

    source_v = extract_agent_version_from_source()
    if not source_v:
        return "skipped (no agent source version)"
    served_v = AGENT_VERSION_PATH.read_text().strip() if AGENT_VERSION_PATH.exists() else None
    if served_v and AGENT_IMAGE_PATH.exists() and _vt(served_v) >= _vt(source_v):
        return f"up to date (served v{served_v})"

    # Stale or missing — trigger a background rebuild via the route's own logic.
    bt = BackgroundTasks()
    await build_agent_image(bt)  # writes build status, guards concurrent builds, queues the build
    if bt.tasks:
        threading.Thread(
            target=lambda: asyncio.run(bt()), name="agent-image-autobuild", daemon=True
        ).start()
        return f"rebuilding agent image (served v{served_v or 'none'} -> source v{source_v})"
    return f"build already in progress / unavailable (served v{served_v or 'none'})"


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
