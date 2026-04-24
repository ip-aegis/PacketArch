# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Skill registry: discovers, parses, and composes Claude Agent Skills.

A skill is a directory containing ``SKILL.md`` with YAML-style
frontmatter:

.. code-block:: markdown

    ---
    name: packetarch-scenario-authoring
    description: Procedural knowledge for OT scenario design
    version: 1.0.0
    ---

    # Skill body in markdown...

The registry walks the ``skills/`` directory once per process, caches
each parsed skill, and exposes a lookup + composition API used by the
Anthropic provider and other call sites.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


SKILL_FILENAME = "SKILL.md"
FRONTMATTER_DELIM = "---"

# Matches ``key: value`` lines within frontmatter. Lists are comma-separated.
_FRONTMATTER_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")


class SkillNotFoundError(KeyError):
    """Raised when a skill name is not in the registry."""


@dataclass(frozen=True)
class Skill:
    """A single Claude Agent Skill.

    Attributes:
        name: Unique skill identifier (matches directory name).
        description: Short trigger description used in telemetry +
            the skill-listing API.
        version: Semver string for the skill body.
        body: The markdown body (frontmatter stripped).
        path: Absolute path to the ``SKILL.md`` file.
        tags: Optional tags for filtering (e.g., ``["scenario", "ai"]``).
    """

    name: str
    description: str
    version: str
    body: str
    path: Path
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def tokens_estimate(self) -> int:
        """Rough token count for telemetry (1 token ≈ 4 chars)."""
        return len(self.body) // 4


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse ``---``-fenced YAML-lite frontmatter from a markdown file.

    Returns:
        (metadata dict, body string). If no frontmatter is present,
        returns an empty dict and the full text.
    """
    if not text.startswith(FRONTMATTER_DELIM):
        return {}, text

    lines = text.split("\n")
    if lines[0].strip() != FRONTMATTER_DELIM:
        return {}, text

    meta: dict[str, str] = {}
    body_start = 1
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == FRONTMATTER_DELIM:
            body_start = idx + 1
            break
        match = _FRONTMATTER_LINE.match(line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            meta[key] = value
    else:
        # No closing delimiter — treat as malformed, return everything.
        return {}, text

    body = "\n".join(lines[body_start:]).lstrip("\n")
    return meta, body


def _parse_list(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated value string into a tuple."""
    if not raw:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


class SkillRegistry:
    """In-memory cache of all skills under a skills directory.

    The registry is lazy: it scans on first access and caches indefinitely
    for the process lifetime. Call :meth:`reload` to force a rescan
    (useful in tests).
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        if skills_dir is None:
            skills_dir = Path(__file__).resolve().parent
        self._skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self._loaded = False
        self._lock = Lock()

    @property
    def skills_dir(self) -> Path:
        return self._skills_dir

    def _load(self) -> None:
        """Walk the skills directory and parse each ``SKILL.md``."""
        skills: dict[str, Skill] = {}
        if not self._skills_dir.exists():
            logger.warning("Skills directory does not exist: %s", self._skills_dir)
            self._skills = skills
            self._loaded = True
            return

        for entry in sorted(self._skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            skill_file = entry / SKILL_FILENAME
            if not skill_file.is_file():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError as e:
                logger.error("Failed to read skill %s: %s", skill_file, e)
                continue

            meta, body = _parse_frontmatter(text)
            name = meta.get("name") or entry.name
            description = meta.get("description", "").strip()
            version = meta.get("version", "0.0.0").strip()
            tags = _parse_list(meta.get("tags", ""))

            if not description:
                logger.warning("Skill %s is missing `description` frontmatter", name)

            if name in skills:
                logger.warning(
                    "Duplicate skill name '%s' at %s — ignoring second copy",
                    name,
                    skill_file,
                )
                continue

            skills[name] = Skill(
                name=name,
                description=description,
                version=version,
                body=body.strip(),
                path=skill_file,
                tags=tags,
            )

        self._skills = skills
        self._loaded = True
        logger.info(
            "Loaded %d skills from %s: %s",
            len(skills),
            self._skills_dir,
            sorted(skills.keys()),
        )

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if not self._loaded:
                self._load()

    def reload(self) -> None:
        """Force a rescan of the skills directory."""
        with self._lock:
            self._loaded = False
            self._load()

    def list_skills(self) -> list[Skill]:
        """Return every loaded skill, sorted by name."""
        self._ensure_loaded()
        return sorted(self._skills.values(), key=lambda s: s.name)

    def has(self, name: str) -> bool:
        self._ensure_loaded()
        return name in self._skills

    def get(self, name: str) -> Skill:
        """Return the skill with the given name.

        Raises:
            SkillNotFoundError: if the name is not registered.
        """
        self._ensure_loaded()
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Known skills: "
                f"{sorted(self._skills.keys())}"
            ) from exc

    def compose(
        self,
        names: list[str],
        *,
        ignore_missing: bool = False,
    ) -> list[Skill]:
        """Resolve an ordered list of skill names into Skill objects.

        Args:
            names: Skill names to load, in order.
            ignore_missing: When True, silently skip unknown names
                instead of raising. Useful when a skill has been
                removed but a call site still references it — the
                hardcoded fallback prompt will still carry the load.

        Returns:
            List of Skill objects, preserving ``names`` order.
        """
        self._ensure_loaded()
        resolved: list[Skill] = []
        for name in names:
            try:
                resolved.append(self.get(name))
            except SkillNotFoundError:
                if ignore_missing:
                    logger.warning("Skill '%s' not found; skipping", name)
                    continue
                raise
        return resolved


@lru_cache(maxsize=1)
def get_registry() -> SkillRegistry:
    """Process-wide singleton registry pointing at the bundled skills."""
    return SkillRegistry()
