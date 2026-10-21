# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""The live agent keeps its own PROTOCOL_PORTS map (fallback 44818). A
protocol missing there lands on 44818 on live while PCAP uses the shared
default (the EMP 3001 bug, agent 3.0.1). Guard the IT protocols."""

import ast
from pathlib import Path

import pytest

from app.protocol_engines.protocols import PROTOCOL_DEFAULT_PORTS

_ROOT = Path(__file__).resolve().parents[3]
_POOL = _ROOT / "docker" / "packetarch-agent" / "app" / "orchestrator_pool.py"
# Only compare inside a repo checkout. In the container test recipe the
# path resolves to /docker, the DEPLOYED agent mount, which can lag a branch.
_IN_CHECKOUT = (_ROOT / "backend").is_dir() and _POOL.exists()


def _agent_ports() -> dict[str, int]:
    tree = ast.parse(_POOL.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if getattr(target, "id", None) == "PROTOCOL_PORTS":
                return ast.literal_eval(node.value)
    raise AssertionError("PROTOCOL_PORTS not found")


@pytest.mark.skipif(not _IN_CHECKOUT, reason="agent source not beside this backend checkout")
@pytest.mark.parametrize("protocol", ["ssh", "telnet", "rdp", "https", "syslog"])
def test_agent_and_pcap_agree_on_it_protocol_ports(protocol):
    assert _agent_ports()[protocol] == PROTOCOL_DEFAULT_PORTS[protocol]
