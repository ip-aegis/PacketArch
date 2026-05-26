# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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

    def get_attack_report(self, scenario_id: str) -> dict[str, Any] | None:
        """Pull the after-action report from the cached attack state.

        The orchestrator embeds the report inside its state snapshot
        (see ``AttackOrchestrator.get_state_snapshot``), so it rides
        the same agent→traffic_dashboard pipeline as the live state.

        Returns:
            Report dict or None if no attack is associated with the
            scenario yet.
        """
        state = self.get_attack_state(scenario_id)
        if not state:
            return None
        return state.get("report")

    async def persist_completed_report(
        self,
        scenario_id: str,
        db: Any,
    ) -> dict[str, Any] | None:
        """If the current attack has completed, snapshot the report into
        ``scenario.definition['attack_history'][]`` so it survives
        deployment teardown.

        Idempotent — already-persisted reports (matched by ``started_at``)
        are not duplicated.

        Returns the persisted report (or the existing duplicate), or
        None if nothing has completed yet.
        """
        from sqlalchemy import select
        from uuid import UUID

        from app.models.scenario import Scenario

        report = self.get_attack_report(scenario_id)
        if not report or report.get("status") not in ("completed", "stopped"):
            return None

        try:
            scenario_uuid = UUID(scenario_id)
        except ValueError:
            return None

        result = await db.execute(
            select(Scenario).where(Scenario.id == scenario_uuid),
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            return None

        definition = dict(scenario.definition or {})
        history = list(definition.get("attack_history", []))
        # Dedupe by (playbook_id, started_at) — same run won't be saved twice.
        started_at = report.get("started_at")
        if any(
            entry.get("playbook_id") == report.get("playbook_id")
            and entry.get("started_at") == started_at
            for entry in history
        ):
            return report

        history.append(report)
        # Cap history at 50 runs to keep definitions bounded.
        if len(history) > 50:
            history = history[-50:]
        definition["attack_history"] = history
        scenario.definition = definition
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(scenario, "definition")
        await db.commit()
        logger.info(
            "Persisted attack report for scenario %s "
            "(playbook=%s, status=%s, total_packets=%s)",
            scenario_id,
            report.get("playbook_id"),
            report.get("status"),
            report.get("total_packets"),
        )
        return report

    async def get_attack_history(
        self,
        scenario_id: str,
        db: Any,
    ) -> list[dict[str, Any]]:
        """Return all persisted attack reports for a scenario.

        Includes runs from previous deployments — survives teardown.
        """
        from sqlalchemy import select
        from uuid import UUID

        from app.models.scenario import Scenario

        try:
            scenario_uuid = UUID(scenario_id)
        except ValueError:
            return []

        result = await db.execute(
            select(Scenario).where(Scenario.id == scenario_uuid),
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            return []
        return list((scenario.definition or {}).get("attack_history", []))

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
