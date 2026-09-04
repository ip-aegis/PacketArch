# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Admin routes for system settings management."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, DBSession
from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import NotFoundError, ValidationError
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
        raise NotFoundError("Setting", key)

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
        raise NotFoundError("Setting", key)

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


@router.get("/ai/routing", response_model=dict)
async def get_ai_routing(
    db: DBSession,
    _admin: AdminUser,
) -> dict:
    """Return the active provider's task → model routing table.

    Lets the Settings UI render what model PacketArch will pick for
    each AI task without duplicating the routing table on the frontend.
    """
    from app.mcp_server.ai_providers.model_router import (
        TASK_MODEL_MAP, FALLBACK_MODEL, AITask,
    )
    provider_row = (
        await db.execute(
            select(SystemSetting).where(SystemSetting.key == "ai_provider")
        )
    ).scalar_one_or_none()
    provider = provider_row.value if provider_row else "anthropic"

    # Human-friendly task labels for the Settings UI.
    task_labels: dict[str, str] = {
        AITask.CHAT.value: "AI Assistant chat",
        AITask.SCENARIO_GENERATION.value: "Scenario generation (from prompt)",
        AITask.SCENARIO_REVIEW.value: "Scenario review / realism scoring",
        AITask.DEVICE_NAMING.value: "Device naming",
        AITask.SITE_IDENTITY.value: "Site identity generation",
        AITask.DESCRIPTION_GENERATION.value: "Description generation",
        AITask.AI_HELP.value: "Inline help / explanations",
    }
    mapping = TASK_MODEL_MAP.get(provider, {})
    routing = [
        {
            "task": task.value,
            "label": task_labels.get(task.value, task.value),
            "model": model,
        }
        for task, model in mapping.items()
    ]
    return {
        "provider": provider,
        "fallback_model": FALLBACK_MODEL.get(provider),
        "routing": routing,
    }


@router.post("/settings/test-connection", response_model=dict)
async def test_api_connection(
    db: DBSession,
    _admin: AdminUser,
) -> dict:
    """Test the currently-selected AI provider's connection.

    Dispatches based on the ``ai_provider`` setting so the UI can hit
    one button to verify whichever provider is currently active. Each
    branch performs a minimal real call (token+chat for CIRCUIT, a
    1-token completion for Anthropic / OpenAI) so plumbing + auth +
    entitlements are all exercised.
    """
    provider_row = (
        await db.execute(
            select(SystemSetting).where(SystemSetting.key == "ai_provider")
        )
    ).scalar_one_or_none()
    provider = provider_row.value if provider_row else "anthropic"

    if provider == "openai":
        return await _test_openai_connection(db)
    if provider == "circuit":
        return await _test_circuit_connection(db)

    # default: anthropic (preserves pre-existing behaviour)
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "anthropic_api_key")
    )
    setting = result.scalar_one_or_none()

    if setting is None or not setting.value:
        raise ValidationError("Anthropic API key not configured")

    api_key = decrypt_value(setting.value)

    if not api_key:
        raise ValidationError("Failed to decrypt API key")

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
            model="claude-haiku-4-5",
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


async def _test_openai_connection(db: AsyncSession) -> dict:
    """Validate the OpenAI provider config with a 1-token completion."""
    key_row = (
        await db.execute(
            select(SystemSetting).where(SystemSetting.key == "openai_api_key")
        )
    ).scalar_one_or_none()
    if not key_row or not key_row.value:
        raise ValidationError("OpenAI API key not configured")
    api_key = decrypt_value(key_row.value)
    if not api_key:
        raise ValidationError("Failed to decrypt OpenAI API key")
    model_row = (
        await db.execute(
            select(SystemSetting).where(SystemSetting.key == "openai_model")
        )
    ).scalar_one_or_none()
    model = (model_row.value if model_row else "gpt-5.6-sol") or "gpt-5.6-sol"
    try:
        from openai import AsyncOpenAI, AuthenticationError, RateLimitError
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model=model, max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return {
            "success": True,
            "message": "OpenAI API key is valid and connection successful.",
            "model_used": resp.model,
        }
    except AuthenticationError:
        return {"success": False, "message": "OpenAI API key is invalid or expired."}
    except RateLimitError:
        return {"success": True, "message": "OpenAI API key is valid but rate limited."}
    except Exception as e:
        return {"success": False, "message": f"OpenAI test failed: {e}"}


async def _test_circuit_connection(db: AsyncSession) -> dict:
    """Validate the CIRCUIT provider config end-to-end.

    Performs the full OAuth2 client_credentials handshake AND a minimal
    chat completion. This catches three distinct failure modes:

    * 401 from id.cisco.com → client_id / client_secret wrong.
    * 401 from chat-ai.cisco.com → token good but appkey lacks API
      entitlement (most common — operator must add chat-completions
      access to the appkey in the CIRCUIT portal).
    * Network / VPN failure → host unreachable (CIRCUIT requires
      Cisco VPN from outside the corp network).

    Env vars override system_settings the same way the factory does.
    """
    import os
    from app.mcp_server.ai_providers.circuit_provider import CircuitProvider

    async def _setting(key: str) -> str | None:
        r = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        s = r.scalar_one_or_none()
        if not s or not s.value:
            return None
        return decrypt_value(s.value) if key == "circuit_client_secret" else s.value

    client_id = os.getenv("CIRCUIT_CLIENT_ID") or await _setting("circuit_client_id")
    client_secret = os.getenv("CIRCUIT_CLIENT_SECRET") or await _setting("circuit_client_secret")
    app_key = os.getenv("CIRCUIT_APP_KEY") or await _setting("circuit_app_key")
    if not (client_id and client_secret and app_key):
        missing = [n for n, v in (
            ("client_id", client_id),
            ("client_secret", client_secret),
            ("app_key", app_key),
        ) if not v]
        return {
            "success": False,
            "message": f"CIRCUIT credentials missing: {', '.join(missing)}",
        }
    model = (
        os.getenv("CIRCUIT_MODEL")
        or (await _setting("circuit_model"))
        or "gpt-5-nano"
    )
    provider = CircuitProvider(
        client_id=client_id, client_secret=client_secret,
        app_key=app_key, model=model, timeout_s=30,
    )
    try:
        from app.ai_services.usage_recorder import AIUsageContext
        resp = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a chatbot."},
                {"role": "user", "content": "Reply with OK."},
            ],
            max_tokens=10,
            tracking=AIUsageContext(feature="connection_test"),
        )
        reply = next(
            (c.get("text", "") for c in resp.get("content", []) if c.get("type") == "text"),
            "",
        )
        return {
            "success": True,
            "message": "CIRCUIT credentials valid and chat completion succeeded.",
            "model_used": resp.get("model"),
            "reply": reply[:80],
        }
    except RuntimeError as e:
        # CircuitProvider raises RuntimeError with the upstream HTTP
        # status + body baked into the message. Surface that verbatim
        # so the operator sees Cisco's exact rejection reason.
        return {"success": False, "message": f"CIRCUIT test failed: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Unexpected CIRCUIT error: {e}"}
    finally:
        await provider.close()


@router.get("/scenarios/{scenario_id}/irrational-flows")
async def get_scenario_irrational_flows(
    scenario_id: str,
    db: DBSession,
    _admin: AdminUser,
) -> dict:
    """Detailed irrational-flow analysis for a single scenario.

    The readiness check surfaces the count; this endpoint returns the full
    per-flow breakdown with reasons and device context so admins can act.
    """
    from uuid import UUID
    from app.models.scenario import Scenario
    from app.services.template_audit import (
        audit_irrational_flows,
        irrational_flow_to_dict,
    )

    result = await db.execute(
        select(Scenario).where(Scenario.id == UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)
    findings = audit_irrational_flows(scenario.definition or {})
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario.name,
        "total_findings": len(findings),
        "findings": [irrational_flow_to_dict(f) for f in findings],
    }


@router.get("/catalog/protocol-audit")
async def get_template_protocol_audit(
    _admin: AdminUser,
    vendor: str | None = None,
) -> dict:
    """Audit the device-template catalog for protocol declaration issues.

    Read-only. Returns a structured report of:
      - Templates that declare a protocol the vendor doesn't natively
        serve (off-vendor declarations).
      - Templates that declare a protocol with no identity block populated
        on the template (missing-identity declarations).

    Use to triage catalog hygiene without modifying any source files.

    Args:
        vendor: Optional case-insensitive substring to filter findings to
            a single vendor brand.

    Returns:
        ``{"summary": {...}, "findings": [...]}`` mirroring the CLI tool
        ``backend/scripts/audit_template_protocols.py --json``.
    """
    from app.services.device_templates import vendors as _vendors  # noqa: F401  side-effect: register
    from app.services.template_audit import (
        audit_templates,
        finding_to_dict,
        summarize,
    )

    findings = audit_templates()
    if vendor:
        needle = vendor.lower()
        findings = [f for f in findings if needle in f.vendor.lower()]

    return {
        "summary": summarize(findings),
        "findings": [finding_to_dict(f) for f in findings],
    }


@router.post("/scenarios/{scenario_id}/regenerate-names")
async def regenerate_scenario_names(
    scenario_id: str,
    db: DBSession,
    _admin: AdminUser,
    use_llm: bool = True,
) -> dict:
    """Re-pick a SiteIdentity for an existing scenario and rename every
    device under it. Snapshots a ScenarioVersion before mutating so the
    operation is reversible.

    Args:
        scenario_id: Target scenario UUID.
        use_llm: If True (default) and AI is configured, use Claude to
            generate a fresh site identity. If False, use the
            deterministic fallback only.

    Returns:
        Summary including the picked site_identity and a count of
        renames.
    """
    from app.models.scenario import Scenario
    from app.services.architecture.site_naming_pipeline import (
        apply_site_naming_pipeline,
    )
    from app.api.routes.scenario_versions import create_version_snapshot

    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    definition = scenario.definition or {}
    if not definition.get("devices"):
        raise ValidationError("Scenario has no devices to rename")

    # Snapshot current state as a version before mutating.
    await create_version_snapshot(
        db, scenario,
        source="manual",
        user_id=_admin.id,
        label="before-rename",
    )

    # Apply the pipeline in-place
    template_meta = (definition.get("_template_meta") or {})
    template_name = template_meta.get("name", "manual")
    template_description = template_meta.get("description", "")

    identity = await apply_site_naming_pipeline(
        db=db,
        definition=definition,
        scenario_id=str(scenario.id),
        vertical=scenario.vertical or "manufacturing",
        template_name=template_name,
        template_description=template_description,
        archetype_id=None,
        use_llm=use_llm,
        exclude_scenario_id=str(scenario.id),
    )

    from sqlalchemy.orm.attributes import flag_modified

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version = (scenario.version or 1) + 1
    await db.commit()
    await db.refresh(scenario)

    return {
        "scenario_id": str(scenario.id),
        "scenario_name": scenario.name,
        "renamed_devices": len(definition.get("devices") or {}),
        "site_identity": identity.to_dict(),
    }


@router.post("/scenarios/regenerate-names")
async def regenerate_all_scenario_names(
    db: DBSession,
    _admin: AdminUser,
    use_llm: bool = True,
) -> dict:
    """Run the rename pipeline on EVERY scenario in this install.

    Useful after upgrading to the site-identity naming rail. Each
    scenario gets its own snapshot version before being renamed.

    Returns a per-scenario summary list.
    """
    from app.models.scenario import Scenario

    result = await db.execute(select(Scenario))
    scenarios = list(result.scalars().all())
    summary: list[dict] = []
    for sc in scenarios:
        try:
            sub = await regenerate_scenario_names(
                str(sc.id), db, _admin, use_llm=use_llm
            )
            summary.append({
                "scenario_id": sub["scenario_id"],
                "scenario_name": sub["scenario_name"],
                "site_code": sub["site_identity"]["site_code"],
                "renamed_devices": sub["renamed_devices"],
                "status": "ok",
            })
        except Exception as e:  # noqa: BLE001
            summary.append({
                "scenario_id": str(sc.id),
                "scenario_name": sc.name,
                "status": "error",
                "error": str(e),
            })
    return {
        "total": len(scenarios),
        "results": summary,
    }
