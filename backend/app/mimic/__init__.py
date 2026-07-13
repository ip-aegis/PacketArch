# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PacketArch Mimic — interactive device emulation.

A separate canvas → deploy → agent path from the traffic generator. A *mimic
agent* hosts one or more *device personas*: each binds real protocol sockets and
answers as a specific industrial device (identity from the shared fingerprint
substrate), with register values that move because a real process model runs
behind them. Personas can poll each other and answer real scanners / Cyber Vision.

This package is the persona RUNTIME. It imports — never copies — the shared
device-knowledge substrate (`device_templates`, `fingerprint_applicator`,
`process_sim`, `vendor_oui`, `canonical_identity`). See
`tasks/emulator-agent-design.md` for the full design and `tasks/mimic-build-plan.md`
for the phased build.

P0 scope: one Modbus-TCP persona, headless (spec-driven), self-verifiable on
localhost; netns/off-box deployment and the Mimic Studio canvas come later. The
public seams (`Transport`, `Projection`, `ProtocolServer`, `DevicePersona`,
`PersonaSpec`) are frozen here so breadth slots in without re-architecture.
"""

from __future__ import annotations
