# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Persona entrypoint: ``python -m app.mimic.run <persona_spec.json>``.

The single launch path for a device persona. On-box the host-agent runs this
inside the persona's network namespace (so the bound IP and TTL are the netns's);
for dev it runs anywhere and binds ``127.0.0.1``. Runs until SIGINT/SIGTERM.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

from .interfaces import PersonaSpec
from .persona import DevicePersona

logger = logging.getLogger(__name__)


async def _run(spec: PersonaSpec) -> None:
    persona = DevicePersona(spec)
    await persona.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover - non-unix
            pass
    try:
        await stop.wait()
    finally:
        await persona.stop()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("usage: python -m app.mimic.run <persona_spec.json>", file=sys.stderr)
        return 2
    spec_dict = json.loads(Path(argv[0]).read_text())
    spec = PersonaSpec.from_dict(spec_dict)
    asyncio.run(_run(spec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
