"""MCP tools for attack simulation playbooks."""

import json
import logging

from app.protocol_engines.attacks.playbooks import (
    list_playbooks,
    get_playbook,
    PLAYBOOK_REGISTRY,
)

logger = logging.getLogger(__name__)


async def list_attack_playbooks() -> str:
    """List all available attack simulation playbooks with summaries."""
    playbooks = list_playbooks()
    result = []
    for pb in playbooks:
        result.append({
            "playbook_id": pb.playbook_id,
            "name": pb.name,
            "description": pb.description,
            "kill_chain_stages": len(pb.stages),
            "mitre_techniques": list({
                a.mitre_technique
                for s in pb.stages
                for a in s.actions
                if a.mitre_technique
            }),
            "required_protocols": list({
                a.protocol
                for s in pb.stages
                for a in s.actions
                if a.protocol
            }),
        })
    return json.dumps({"playbooks": result, "total": len(result)}, indent=2)


async def get_playbook_details(playbook_id: str) -> str:
    """Get full details of an attack playbook including kill chain stages and actions."""
    pb = get_playbook(playbook_id)
    if not pb:
        available = list(PLAYBOOK_REGISTRY.keys())
        return json.dumps({
            "error": f"Playbook '{playbook_id}' not found",
            "available_playbooks": available,
        })

    stages = []
    for stage in pb.stages:
        actions = []
        for action in stage.actions:
            actions.append({
                "name": action.name,
                "action_type": action.action_type,
                "protocol": action.protocol,
                "mitre_technique": action.mitre_technique,
                "description": action.description,
                "repeat_count": action.repeat_count,
                "delay_ms": action.delay_ms,
            })
        stages.append({
            "name": stage.name,
            "description": stage.description,
            "duration_seconds": stage.duration_seconds,
            "actions": actions,
        })

    return json.dumps({
        "playbook_id": pb.playbook_id,
        "name": pb.name,
        "description": pb.description,
        "stages": stages,
    }, indent=2)


async def suggest_attack_for_scenario(
    scenario_id: str,
    protocols: list[str] | None = None,
    vertical: str | None = None,
) -> str:
    """Recommend attack playbooks based on scenario protocols and vertical.

    Args:
        scenario_id: The scenario to analyze
        protocols: Protocols used in the scenario (e.g., modbus_tcp, s7comm)
        vertical: Industry vertical (e.g., manufacturing, energy)
    """
    playbooks = list_playbooks()
    proto_set = set(protocols or [])

    scored = []
    for pb in playbooks:
        # Score based on protocol overlap
        pb_protocols = {
            a.protocol
            for s in pb.stages
            for a in s.actions
            if a.protocol
        }
        overlap = len(proto_set & pb_protocols) if proto_set else 0
        total_pb_protos = len(pb_protocols) if pb_protocols else 1

        score = (overlap / total_pb_protos) * 100 if proto_set else 50

        # Boost for vertical relevance
        desc_lower = (pb.description or "").lower()
        if vertical:
            v_lower = vertical.lower()
            if v_lower in desc_lower or v_lower.replace("_", " ") in desc_lower:
                score += 20

        scored.append({
            "playbook_id": pb.playbook_id,
            "name": pb.name,
            "description": pb.description,
            "relevance_score": round(score, 1),
            "matching_protocols": sorted(proto_set & pb_protocols) if proto_set else [],
        })

    # Sort by relevance score
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    return json.dumps({
        "scenario_id": scenario_id,
        "recommendations": scored[:3],
        "all_available": len(playbooks),
    }, indent=2)
