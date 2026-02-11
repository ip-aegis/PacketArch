"""Server-side attack simulation management service.

Routes attack commands to agents running scenarios and provides
playbook information from the registry.
"""

import logging
from typing import Any

from app.protocol_engines.attacks import get_playbook, list_playbooks
from app.protocol_engines.attacks.types import AttackPlaybook

logger = logging.getLogger(__name__)


class AttackService:
    """Manages attack playbook commands for running deployments.

    Follows the same singleton pattern as AdaptationService.
    """

    async def _send_attack_command(
        self,
        scenario_id: str,
        command_type: str,
        **extra: Any,
    ) -> bool:
        """Send an attack command to the agent running a scenario.

        Args:
            scenario_id: Target scenario UUID
            command_type: WebSocket command type (START_ATTACK, etc.)
            **extra: Additional command payload fields

        Returns:
            True if command was sent successfully
        """
        from app.services.agent_manager import agent_manager

        command: dict[str, Any] = {
            "type": command_type,
            "scenario_id": scenario_id,
            **extra,
        }

        deployment = agent_manager.get_deployment(scenario_id)
        if not deployment:
            logger.warning(f"No active deployment for scenario {scenario_id}")
            return False

        success = await agent_manager.send_command(deployment.agent_id, command)
        if success:
            logger.info(f"Sent {command_type} to scenario {scenario_id}")
        return success

    async def start_attack(self, scenario_id: str) -> bool:
        """Start the attack playbook on a deployed scenario."""
        return await self._send_attack_command(scenario_id, "START_ATTACK")

    async def stop_attack(self, scenario_id: str) -> bool:
        """Stop the running attack playbook."""
        return await self._send_attack_command(scenario_id, "STOP_ATTACK")

    async def advance_stage(self, scenario_id: str) -> bool:
        """Advance to the next kill-chain stage."""
        return await self._send_attack_command(scenario_id, "ADVANCE_STAGE")

    async def pause_attack(self, scenario_id: str, paused: bool) -> bool:
        """Pause or resume the attack playbook."""
        return await self._send_attack_command(
            scenario_id, "PAUSE_ATTACK", paused=paused,
        )

    async def inject_attack(
        self,
        scenario_id: str,
        playbook_id: str,
        config: dict[str, Any] | None = None,
    ) -> bool:
        """Inject an attack playbook into an already-running deployment.

        Args:
            scenario_id: Target scenario UUID string
            playbook_id: Playbook to inject
            config: Optional config overrides (auto_advance, intensity, etc.)

        Returns:
            True if the injection command was sent
        """
        from app.services.agent_manager import agent_manager

        # Clear any previous injection result (allows retries)
        agent_manager.clear_injection_result(scenario_id)

        playbook = get_playbook(playbook_id)
        if not playbook:
            logger.warning(f"inject_attack: playbook '{playbook_id}' not found")
            return False

        attack_playbook = {
            "playbook_id": playbook_id,
            "start_mode": "manual",
            **(config or {}),
        }

        return await self._send_attack_command(
            scenario_id,
            "INJECT_ATTACK",
            attack_playbook=attack_playbook,
        )

    def get_attack_state(self, scenario_id: str) -> dict[str, Any] | None:
        """Get attack state from the traffic dashboard.

        Returns:
            Attack state dict or None
        """
        from app.services.traffic_dashboard import traffic_dashboard

        deployment = traffic_dashboard.get_deployment(scenario_id)
        if not deployment:
            return None
        return deployment.get("attack")

    def get_injection_status(self, scenario_id: str) -> dict[str, Any]:
        """Poll injection outcome after POST /inject.

        Checks two sources:
        1. agent_manager._injection_results for explicit agent rejection
        2. traffic_dashboard for attack state appearance (confirms success)

        Returns:
            {"status": "pending"} — no result yet
            {"status": "confirmed", "attack": {...}} — attack state appeared
            {"status": "failed", "message": "..."} — agent rejected
        """
        from app.services.agent_manager import agent_manager
        from app.services.traffic_dashboard import traffic_dashboard

        # Check for explicit failure from agent
        result = agent_manager.get_injection_result(scenario_id)
        if result and result.get("status") == "failed":
            return {
                "status": "failed",
                "message": result.get("message", "Agent rejected injection"),
            }

        # Check if attack state appeared in traffic dashboard
        deployment = traffic_dashboard.get_deployment(scenario_id)
        if deployment:
            attack = deployment.get("attack")
            if attack and (attack.get("playbook_name") or attack.get("playbook_id")):
                return {"status": "confirmed", "attack": attack}

        return {"status": "pending"}

    def get_all_playbooks(self) -> list[dict[str, Any]]:
        """Return all available playbooks as dicts."""
        return [p.to_dict() for p in list_playbooks()]

    def get_playbook_by_id(self, playbook_id: str) -> dict[str, Any] | None:
        """Return a specific playbook by ID."""
        playbook = get_playbook(playbook_id)
        return playbook.to_dict() if playbook else None

    def get_compatible_playbooks(
        self,
        scenario_protocols: list[str],
    ) -> list[dict[str, Any]]:
        """Return playbooks compatible with a scenario's protocols.

        A playbook is compatible if the scenario has all required protocols,
        or if the playbook has no required protocols (universal).

        Args:
            scenario_protocols: List of protocol strings in the scenario

        Returns:
            List of compatible playbook dicts
        """
        proto_set = set(scenario_protocols)
        compatible = []
        for playbook in list_playbooks():
            if not playbook.required_protocols:
                compatible.append(playbook.to_dict())
            elif set(playbook.required_protocols) & proto_set:
                compatible.append(playbook.to_dict())
        return compatible


# Singleton
attack_service = AttackService()
