"""Live attack simulation — multi-stage ICS kill-chain playbooks.

Provides :class:`AttackOrchestrator` for integration with
:class:`~app.protocol_engines.unified_orchestrator.UnifiedOrchestrator`,
pre-built playbooks modeled on real ICS campaigns, and an action registry
that maps attack types to packet generators.

Auto-imports ``ics_actions`` to populate the action registry with
ICS-protocol-specific generators.
"""

from .action_registry import (
    ATTACK_FLOW_PREFIX,
    TargetInfo,
    get_action_generator,
    list_action_types,
    register_action,
)
from .attack_orchestrator import AttackOrchestrator
from .playbooks import PLAYBOOK_REGISTRY, get_playbook, list_playbooks
from .types import (
    AttackAction,
    AttackPlaybook,
    AttackPlaybookConfig,
    AttackState,
    KillChainStage,
)

# Ensure ICS action generators are registered on import
from . import ics_actions as _ics_actions  # noqa: F401

__all__ = [
    "ATTACK_FLOW_PREFIX",
    "AttackAction",
    "AttackOrchestrator",
    "AttackPlaybook",
    "AttackPlaybookConfig",
    "AttackState",
    "KillChainStage",
    "PLAYBOOK_REGISTRY",
    "TargetInfo",
    "get_action_generator",
    "get_playbook",
    "list_action_types",
    "list_playbooks",
    "register_action",
]
