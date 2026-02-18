"""Scenario remediation service — deterministic execution of AI-suggested fixes.

Each handler delegates to existing MCP tool functions which handle
safe_update_scenario, validation, and db commits internally.
"""

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.scenario_review import RemediationAction, RemediationResult

logger = logging.getLogger(__name__)


async def execute_actions(
    db: AsyncSession,
    scenario_id: str,
    actions: list[RemediationAction],
) -> list[RemediationResult]:
    """Execute a list of remediation actions sequentially.

    Each action is dispatched to an existing MCP tool function.
    Partial success is supported — failed actions don't block later ones.
    """
    results: list[RemediationResult] = []
    for action in actions:
        logger.info(f"Remediation action: {action.action_type}, params={action.params}")
        handler = _ACTION_HANDLERS.get(action.action_type)
        if not handler:
            results.append(RemediationResult(
                action_type=action.action_type,
                success=False,
                message=f"Unknown action type: {action.action_type}",
            ))
            continue
        try:
            result = await handler(db, scenario_id, action.params)
            logger.info(f"Remediation result: {action.action_type} -> success={result.success}, message={result.message}")
            results.append(result)
        except Exception as e:
            logger.error(f"Remediation {action.action_type} failed: {e}")
            results.append(RemediationResult(
                action_type=action.action_type,
                success=False,
                message=str(e),
            ))
    return results


def _parse_tool_result(raw: str) -> dict[str, Any]:
    """Parse a JSON string returned by an MCP tool."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": raw}


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

async def _assign_fingerprint(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.fingerprint_tools import apply_fingerprint_to_device

    device_id = params.get("device_id", "")
    vendor = params.get("vendor", "")
    model = params.get("model", "")
    if not all([device_id, vendor, model]):
        return RemediationResult(
            action_type="assign_fingerprint", success=False,
            message="Missing required params: device_id, vendor, model",
        )
    raw = await apply_fingerprint_to_device(db, scenario_id, device_id, vendor, model)
    data = _parse_tool_result(raw)
    if "error" in data:
        return RemediationResult(
            action_type="assign_fingerprint", success=False, message=data["error"],
        )
    return RemediationResult(
        action_type="assign_fingerprint", success=True,
        message=f"Applied {vendor}/{model} fingerprint",
    )


async def _repair_protocols(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    """Remove unsupported protocols from devices using existing repair logic."""
    from app.mcp_server.tools.scenario_lock import safe_update_scenario
    from app.services.fingerprint_cache import get_fingerprint_cache
    from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY

    target_ids = set(params.get("device_ids", []))
    cache = get_fingerprint_cache()
    fixed_count = 0

    def do_repair(definition: dict) -> dict:
        nonlocal fixed_count
        devices = definition.get("devices", {})
        for did, device in devices.items():
            if target_ids and did not in target_ids:
                continue
            fp = device.get("vendorFingerprint") or {}
            vendor = fp.get("vendor", "")
            model = fp.get("model", "")
            if not vendor or not model:
                continue
            full_fp = cache.get_by_vendor_model(vendor, model)
            if not full_fp:
                continue
            protocols = device.get("protocols") or []
            kept = []
            for proto in protocols:
                identity_key = PROTOCOL_TO_IDENTITY_KEY.get(proto)
                if identity_key and full_fp.get(identity_key):
                    kept.append(proto)
                elif not identity_key:
                    kept.append(proto)
            if len(kept) < len(protocols):
                fixed_count += 1
                device["protocols"] = kept
        return {"success": True}

    if not target_ids:
        return RemediationResult(
            action_type="repair_protocols", success=False,
            message="Missing required param: device_ids",
        )

    scenario, result = await safe_update_scenario(db, scenario_id, do_repair)
    if scenario is None:
        return RemediationResult(
            action_type="repair_protocols", success=False, message="Scenario not found",
        )
    if fixed_count == 0:
        return RemediationResult(
            action_type="repair_protocols", success=False,
            message=f"No protocol changes needed (device IDs: {list(target_ids)[:3]})",
        )
    return RemediationResult(
        action_type="repair_protocols", success=True,
        message=f"Repaired protocols on {fixed_count} device(s)",
    )


async def _update_flow_timing(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.flow_tools import update_flow

    flow_id = params.get("flow_id", "")
    interval_ms = params.get("interval_ms")
    if not flow_id or interval_ms is None:
        return RemediationResult(
            action_type="update_flow_timing", success=False,
            message="Missing required params: flow_id, interval_ms",
        )
    raw = await update_flow(
        db, scenario_id, flow_id,
        {"config": {"pollIntervalMs": int(interval_ms)}},
    )
    data = _parse_tool_result(raw)
    if "error" in data:
        return RemediationResult(
            action_type="update_flow_timing", success=False, message=data["error"],
        )
    return RemediationResult(
        action_type="update_flow_timing", success=True,
        message=f"Updated poll interval to {interval_ms}ms",
    )


async def _add_flow(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.flow_tools import add_flow

    src = params.get("source_device_id", "")
    tgt = params.get("target_device_id", "")
    protocol = params.get("protocol", "")
    interval_ms = params.get("interval_ms", 1000)
    if not all([src, tgt, protocol]):
        return RemediationResult(
            action_type="add_flow", success=False,
            message="Missing required params: source_device_id, target_device_id, protocol",
        )
    flow_data: dict[str, Any] = {
        "sourceDeviceId": src,
        "targetDeviceId": tgt,
        "protocol": protocol,
        "config": {"pollIntervalMs": int(interval_ms)},
    }
    raw = await add_flow(db, scenario_id, flow_data)
    data = _parse_tool_result(raw)
    if "error" in data:
        return RemediationResult(
            action_type="add_flow", success=False, message=data["error"],
        )
    return RemediationResult(
        action_type="add_flow", success=True,
        message=f"Added {protocol} flow",
    )


async def _assign_ips(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.addressing_tools import auto_assign_addresses

    raw = await auto_assign_addresses(db, scenario_id, "zone_based")
    data = _parse_tool_result(raw)
    if "error" in data:
        return RemediationResult(
            action_type="assign_ips", success=False, message=data["error"],
        )
    return RemediationResult(
        action_type="assign_ips", success=True,
        message="Auto-assigned IP addresses",
    )


async def _regenerate_macs(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.scenario_lock import safe_update_scenario
    from app.protocol_engines.identity import generate_mac

    target_ids = set(params.get("device_ids", []))
    regen_count = 0

    def do_regen(definition: dict) -> dict:
        nonlocal regen_count
        devices = definition.get("devices", {})
        for did, device in devices.items():
            if target_ids and did not in target_ids:
                continue
            vendor = device.get("vendor", "")
            device_type = device.get("type", "")
            network = device.setdefault("network", {})
            network["macAddress"] = generate_mac(vendor=vendor, device_type=device_type)
            regen_count += 1
        return {"success": True}

    if not target_ids:
        return RemediationResult(
            action_type="regenerate_macs", success=False,
            message="Missing required param: device_ids",
        )

    scenario, _ = await safe_update_scenario(db, scenario_id, do_regen)
    if scenario is None:
        return RemediationResult(
            action_type="regenerate_macs", success=False, message="Scenario not found",
        )
    if regen_count == 0:
        return RemediationResult(
            action_type="regenerate_macs", success=False,
            message=f"No matching devices found (IDs: {list(target_ids)[:3]})",
        )
    return RemediationResult(
        action_type="regenerate_macs", success=True,
        message=f"Regenerated MAC addresses for {regen_count} device(s)",
    )


async def _apply_cve(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.fingerprint_tools import apply_cve_to_device

    device_id = params.get("device_id", "")
    cve_id = params.get("cve_id", "")
    if not all([device_id, cve_id]):
        return RemediationResult(
            action_type="apply_cve", success=False,
            message="Missing required params: device_id, cve_id",
        )
    raw = await apply_cve_to_device(db, scenario_id, device_id, cve_id)
    data = _parse_tool_result(raw)
    if "error" in data:
        return RemediationResult(
            action_type="apply_cve", success=False, message=data["error"],
        )
    return RemediationResult(
        action_type="apply_cve", success=True,
        message=f"Applied {cve_id}",
    )


async def _remove_device(
    db: AsyncSession, scenario_id: str, params: dict,
) -> RemediationResult:
    from app.mcp_server.tools.device_tools import remove_device

    device_id = params.get("device_id", "")
    if not device_id:
        return RemediationResult(
            action_type="remove_device", success=False,
            message="Missing required param: device_id",
        )
    raw = await remove_device(db, scenario_id, device_id)
    data = _parse_tool_result(raw)
    if "error" in data:
        return RemediationResult(
            action_type="remove_device", success=False, message=data["error"],
        )
    return RemediationResult(
        action_type="remove_device", success=True,
        message="Removed device",
    )


_ACTION_HANDLERS = {
    "assign_fingerprint": _assign_fingerprint,
    "repair_protocols": _repair_protocols,
    "update_flow_timing": _update_flow_timing,
    "add_flow": _add_flow,
    "assign_ips": _assign_ips,
    "regenerate_macs": _regenerate_macs,
    "apply_cve": _apply_cve,
    "remove_device": _remove_device,
}
