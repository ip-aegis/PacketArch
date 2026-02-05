"""Startup services for initializing the application."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.cloud_service import CloudServiceEndpoint, CloudServiceProvider
from app.models.pcap_capture import PcapCapture, ProcessingStatus
from app.models.settings import DEFAULT_SETTINGS, SystemSetting
from app.models.traffic_agent import TrafficAgent, AgentDeployment
from app.models.user import User
from app.services.cloud_service_data import BUILTIN_CLOUD_SERVICES
from app.services.seed_data import run_seed_data


async def create_first_user(db: AsyncSession) -> User | None:
    """Create the first admin user if no users exist."""
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


async def recover_stuck_pcap_processing(db: AsyncSession) -> int:
    """Reset any PCAP captures stuck in 'processing' status.

    This handles the case where the server restarted while processing was in progress.
    Since background tasks are lost on restart, these captures would be stuck forever.
    We reset them to 'pending' so they can be retried.
    """
    # Find all captures stuck in processing status
    result = await db.execute(
        select(PcapCapture).where(PcapCapture.status == ProcessingStatus.PROCESSING)
    )
    stuck_captures = result.scalars().all()

    if not stuck_captures:
        return 0

    # Reset to pending
    await db.execute(
        update(PcapCapture)
        .where(PcapCapture.status == ProcessingStatus.PROCESSING)
        .values(
            status=ProcessingStatus.PENDING,
            error_message="Processing was interrupted by server restart. Click retry to reprocess.",
        )
    )
    await db.commit()

    return len(stuck_captures)


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

    # Seed device profiles and protocol templates
    seed_results = await run_seed_data(db)
    results.update(seed_results)

    # Seed cloud service endpoints
    cloud_services_created = await seed_cloud_services(db)
    results["cloud_services"] = f"Seeded {cloud_services_created} cloud service endpoints"

    # Recover any stuck PCAP processing jobs
    stuck_count = await recover_stuck_pcap_processing(db)
    if stuck_count > 0:
        results["pcap_recovery"] = f"Reset {stuck_count} stuck PCAP processing job(s)"
    else:
        results["pcap_recovery"] = "No stuck PCAP jobs found"

    # Reconcile agent statuses (reset all to offline since no agents connected at startup)
    agents_reset = await reconcile_agent_statuses(db)
    if agents_reset > 0:
        results["agent_reconcile"] = f"Reset {agents_reset} stale 'online' agent(s) to offline"
    else:
        results["agent_reconcile"] = "No stale agent statuses found"

    return results
