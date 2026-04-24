# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Claude Agent Skills for PacketArch.

Skills are reusable bundles of procedural OT/ICS domain knowledge that
Claude loads on demand. Each skill lives in its own directory with a
``SKILL.md`` file containing frontmatter (name, description, version) and
a markdown body.

The ``SkillRegistry`` discovers skills at import time, caches parsed
bodies in memory, and composes them into the ``system`` field of
Anthropic Messages API calls.
"""

from app.ai_services.skills.registry import (
    Skill,
    SkillNotFoundError,
    SkillRegistry,
    get_registry,
)

__all__ = [
    "Skill",
    "SkillNotFoundError",
    "SkillRegistry",
    "get_registry",
]
