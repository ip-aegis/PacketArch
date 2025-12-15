"""Admin routes for system settings management."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, DBSession
from app.core.encryption import decrypt_value, encrypt_value
from app.models.settings import DEFAULT_SETTINGS, SystemSetting
from app.schemas.settings import SettingResponse, SettingsResponse, SettingUpdate

router = APIRouter(prefix="/admin", tags=["Admin"])


def mask_secret_value(value: str | None) -> str | None:
    """Mask a secret value for display."""
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def setting_to_response(setting: SystemSetting, reveal_secret: bool = False) -> SettingResponse:
    """Convert a SystemSetting to a SettingResponse, handling secrets."""
    value = setting.value

    if setting.is_secret and value:
        # Decrypt the value
        decrypted = decrypt_value(value)
        if reveal_secret:
            value = decrypted
        else:
            value = mask_secret_value(decrypted)

    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=value,
        is_secret=setting.is_secret,
        category=setting.category,
        description=setting.description,
        updated_at=setting.updated_at,
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_all_settings(
    db: DBSession,
    _admin: AdminUser,
) -> SettingsResponse:
    """Get all system settings grouped by category."""
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    settings = result.scalars().all()

    response = SettingsResponse()

    for setting in settings:
        setting_response = setting_to_response(setting)

        if setting.category == "api_tokens":
            response.api_tokens.append(setting_response)
        elif setting.category == "network":
            response.network.append(setting_response)
        elif setting.category == "system":
            response.system.append(setting_response)

    return response


@router.get("/settings/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: DBSession,
    _admin: AdminUser,
) -> SettingResponse:
    """Get a specific setting by key."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    return setting_to_response(setting)


@router.put("/settings/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: DBSession,
    admin: AdminUser,
) -> SettingResponse:
    """Update a specific setting."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    # Encrypt value if this is a secret
    if setting.is_secret and update.value:
        setting.value = encrypt_value(update.value)
    else:
        setting.value = update.value

    setting.updated_by_id = admin.id

    await db.commit()
    await db.refresh(setting)

    return setting_to_response(setting)


@router.post("/settings/seed", response_model=dict)
async def seed_default_settings(
    db: DBSession,
    _admin: AdminUser,
) -> dict:
    """Seed default settings if they don't exist."""
    created = 0
    skipped = 0

    for setting_data in DEFAULT_SETTINGS:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == setting_data["key"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            setting = SystemSetting(**setting_data)
            db.add(setting)
            created += 1
        else:
            skipped += 1

    await db.commit()

    return {
        "message": f"Seeded {created} settings, skipped {skipped} existing",
        "created": created,
        "skipped": skipped,
    }


@router.post("/settings/test-connection", response_model=dict)
async def test_api_connection(
    db: DBSession,
    _admin: AdminUser,
) -> dict:
    """Test the Anthropic API connection using the stored API key."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "anthropic_api_key")
    )
    setting = result.scalar_one_or_none()

    if setting is None or not setting.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anthropic API key not configured",
        )

    api_key = decrypt_value(setting.value)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt API key",
        )

    # Verify key format first
    if not api_key.startswith("sk-ant-"):
        return {
            "success": False,
            "message": "API key format appears invalid (should start with 'sk-ant-')",
        }

    # Actually test the connection to Anthropic API
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Make a minimal API call to verify the key works
        # Using a simple messages request with minimal tokens
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )

        return {
            "success": True,
            "message": "API key is valid and connection successful.",
            "model_used": response.model,
        }

    except anthropic.AuthenticationError:
        return {
            "success": False,
            "message": "API key is invalid or expired.",
        }
    except anthropic.RateLimitError:
        return {
            "success": True,
            "message": "API key is valid but rate limited. Try again later.",
        }
    except anthropic.APIConnectionError as e:
        return {
            "success": False,
            "message": f"Failed to connect to Anthropic API: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error testing API key: {str(e)}",
        }
