# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for the Claude Agent Skill registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ai_services.skills import SkillNotFoundError, SkillRegistry, get_registry
from app.ai_services.skills.registry import _parse_frontmatter


# ---------- Frontmatter parser ----------


def test_parse_frontmatter_extracts_keys_and_body() -> None:
    text = (
        "---\n"
        "name: demo\n"
        "description: a demo skill\n"
        "version: 1.2.3\n"
        "---\n"
        "\n"
        "# Body\n"
        "body text\n"
    )
    meta, body = _parse_frontmatter(text)
    assert meta == {"name": "demo", "description": "a demo skill", "version": "1.2.3"}
    assert body.startswith("# Body")


def test_parse_frontmatter_strips_quotes() -> None:
    text = '---\nname: "quoted"\ntags: \'one, two\'\n---\nbody'
    meta, _ = _parse_frontmatter(text)
    assert meta["name"] == "quoted"
    assert meta["tags"] == "one, two"


def test_parse_frontmatter_without_delimiters_returns_full_body() -> None:
    text = "no frontmatter here\n"
    meta, body = _parse_frontmatter(text)
    assert meta == {}
    assert body == text


# ---------- Registry ----------


def _write_skill(dir_: Path, name: str, description: str = "desc", body: str = "body") -> None:
    skill_dir = dir_ / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\nversion: 1.0.0\n---\n{body}\n",
        encoding="utf-8",
    )


def test_registry_discovers_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha")
    _write_skill(tmp_path, "beta", description="second skill")

    registry = SkillRegistry(skills_dir=tmp_path)
    names = [s.name for s in registry.list_skills()]

    assert names == ["alpha", "beta"]
    assert registry.get("beta").description == "second skill"


def test_registry_raises_on_missing(tmp_path: Path) -> None:
    registry = SkillRegistry(skills_dir=tmp_path)
    with pytest.raises(SkillNotFoundError):
        registry.get("does-not-exist")


def test_registry_compose_ignore_missing(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha")
    registry = SkillRegistry(skills_dir=tmp_path)

    # Strict compose raises
    with pytest.raises(SkillNotFoundError):
        registry.compose(["alpha", "missing"])

    # Lenient compose skips the unknown name
    resolved = registry.compose(["alpha", "missing"], ignore_missing=True)
    assert [s.name for s in resolved] == ["alpha"]


def test_registry_reload_picks_up_new_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha")
    registry = SkillRegistry(skills_dir=tmp_path)
    assert registry.has("alpha")
    assert not registry.has("beta")

    _write_skill(tmp_path, "beta")
    registry.reload()
    assert registry.has("beta")


def test_registry_ignores_duplicate_names(tmp_path: Path, caplog) -> None:
    # Two skill directories declaring the same frontmatter name.
    (tmp_path / "first").mkdir()
    (tmp_path / "first" / "SKILL.md").write_text(
        "---\nname: shared\ndescription: first\nversion: 1.0.0\n---\nfirst\n",
        encoding="utf-8",
    )
    (tmp_path / "second").mkdir()
    (tmp_path / "second" / "SKILL.md").write_text(
        "---\nname: shared\ndescription: second\nversion: 2.0.0\n---\nsecond\n",
        encoding="utf-8",
    )
    registry = SkillRegistry(skills_dir=tmp_path)
    skills = registry.list_skills()
    assert len(skills) == 1
    # The first directory alphabetically wins.
    assert skills[0].description == "first"


def test_registry_missing_directory_is_silent(tmp_path: Path) -> None:
    registry = SkillRegistry(skills_dir=tmp_path / "nonexistent")
    assert registry.list_skills() == []


# ---------- Bundled skills smoke test ----------


BUNDLED_SKILLS = {
    "packetarch-scenario-authoring",
    "packetarch-fingerprint-validator",
    "packetarch-ics-attack-playbooks",
    "packetarch-device-naming",
    "packetarch-scenario-review",
}


def test_all_bundled_skills_load() -> None:
    """Every shipped skill must parse with a non-empty description and body."""
    registry = get_registry()
    loaded = {s.name for s in registry.list_skills()}
    assert BUNDLED_SKILLS.issubset(loaded), (
        f"Missing bundled skills: {BUNDLED_SKILLS - loaded}"
    )

    for name in BUNDLED_SKILLS:
        skill = registry.get(name)
        assert skill.description, f"{name}: description is empty"
        assert skill.body.strip(), f"{name}: body is empty"
        assert skill.version, f"{name}: version is empty"
        assert skill.tokens_estimate > 0
