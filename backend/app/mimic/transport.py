# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Transport implementations.

P0 provides:

- ``LocalhostTransport`` — dev/self-test; binds 127.0.0.1.
- ``NamespaceKernelStack`` — on-box: the persona process runs inside a network
  namespace the host-agent created with the persona's IP and vendor-tuned
  TTL/window sysctls, so the server just binds that IP with an ordinary kernel
  socket. The stack fingerprint is owned by the netns, not this code.

The userland-stack transport (flagship OS-fingerprint accuracy) is a future
sibling; it will additionally supply the listening socket. Servers depend only on
the ``Transport`` interface, so it drops in without touching them.
"""

from __future__ import annotations

from .interfaces import Transport


class LocalhostTransport(Transport):
    """Loopback bind for dev and self-test."""

    def __init__(self, bind_ip: str = "127.0.0.1") -> None:
        self._bind_ip = bind_ip

    @property
    def bind_ip(self) -> str:
        return self._bind_ip


class NamespaceKernelStack(Transport):
    """On-box: bind the persona's real IP inside its network namespace.

    TTL/window/MSS are set by the host-agent as netns sysctls at provision time
    (from the template ``tcp_stack``); this transport only carries the address.
    """

    def __init__(self, bind_ip: str) -> None:
        self._bind_ip = bind_ip

    @property
    def bind_ip(self) -> str:
        return self._bind_ip
