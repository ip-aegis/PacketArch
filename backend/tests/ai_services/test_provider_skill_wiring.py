# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Provider-side wiring of Claude Agent Skills.

These tests exercise the ``_build_system_blocks`` helper directly so
we do not need the live Anthropic client.
"""

from __future__ import annotations

from pathlib import Path

from app.ai_services.skills.registry import SkillRegistry
from app.mcp_server.ai_providers.anthropic_provider import AnthropicProvider


def _make_tmp_registry(tmp_path: Path, skills: dict[str, str]) -> SkillRegistry:
    for name, body in skills.items():
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {name} desc\nversion: 1.0.0\n---\n{body}\n",
            encoding="utf-8",
        )
    return SkillRegistry(skills_dir=tmp_path)


def test_build_system_blocks_prepends_skills(tmp_path: Path, monkeypatch) -> None:
    tmp_registry = _make_tmp_registry(
        tmp_path,
        {"alpha": "alpha body", "beta": "beta body"},
    )
    monkeypatch.setattr(
        "app.mcp_server.ai_providers.anthropic_provider.get_registry",
        lambda: tmp_registry,
    )

    provider = AnthropicProvider(api_key="not-used", model="claude-opus-4-7")
    blocks = provider._build_system_blocks(
        system_message="task-specific",
        skills=["alpha", "beta"],
    )

    assert blocks is not None
    assert len(blocks) == 3
    assert blocks[0]["text"] == "alpha body"
    assert blocks[1]["text"] == "beta body"
    assert blocks[2]["text"] == "task-specific"
    # Every block is cacheable so repeated calls benefit.
    for block in blocks:
        assert block["cache_control"] == {"type": "ephemeral"}


def test_build_system_blocks_skips_missing_skill(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    tmp_registry = _make_tmp_registry(tmp_path, {"alpha": "alpha body"})
    monkeypatch.setattr(
        "app.mcp_server.ai_providers.anthropic_provider.get_registry",
        lambda: tmp_registry,
    )

    provider = AnthropicProvider(api_key="not-used", model="claude-opus-4-7")
    blocks = provider._build_system_blocks(
        system_message=None,
        skills=["alpha", "nonexistent"],
    )

    assert blocks is not None
    assert len(blocks) == 1
    assert blocks[0]["text"] == "alpha body"


def test_build_system_blocks_returns_none_when_empty(tmp_path: Path, monkeypatch) -> None:
    tmp_registry = _make_tmp_registry(tmp_path, {})
    monkeypatch.setattr(
        "app.mcp_server.ai_providers.anthropic_provider.get_registry",
        lambda: tmp_registry,
    )

    provider = AnthropicProvider(api_key="not-used", model="claude-opus-4-7")
    assert provider._build_system_blocks(None, None) is None
    assert provider._build_system_blocks(None, []) is None
