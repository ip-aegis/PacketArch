"""Startup services for initializing the application."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.pcap_capture import PcapCapture, ProcessingStatus
from app.models.settings import DEFAULT_SETTINGS, SystemSetting
from app.models.user import User
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

    # Recover any stuck PCAP processing jobs
    stuck_count = await recover_stuck_pcap_processing(db)
    if stuck_count > 0:
        results["pcap_recovery"] = f"Reset {stuck_count} stuck PCAP processing job(s)"
    else:
        results["pcap_recovery"] = "No stuck PCAP jobs found"

    return results
