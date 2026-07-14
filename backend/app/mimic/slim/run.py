# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim persona entrypoint: ``python -m mimic_slim.run <resolved_spec.json>``.

Runs on a bare Alpine node (stdlib + pymodbus). Optionally pings a check-in URL
so the backend learns the node is up and listening.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import urllib.request
from pathlib import Path

from .persona import SlimPersona
from .spec import ResolvedPersonaSpec

logger = logging.getLogger(__name__)


def _checkin(url: str, name: str) -> None:
    # The backend serves a self-signed cert; urllib would reject it, so use an
    # unverified context (this is a liveness ping, not a trust boundary).
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        urllib.request.urlopen(f"{url}?name={name}&slim=1&up=1&listening=1", timeout=5, context=ctx)
    except Exception:  # noqa: BLE001
        pass


async def _run(spec: ResolvedPersonaSpec, checkin_url: str | None) -> None:
    persona = SlimPersona(spec)
    await persona.start()
    if checkin_url:
        _checkin(checkin_url, spec.name)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover
            pass
    try:
        await stop.wait()
    finally:
        await persona.stop()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m mimic_slim.run <resolved_spec.json> [checkin_url]", file=sys.stderr)
        return 2
    spec = ResolvedPersonaSpec.from_dict(json.loads(Path(argv[0]).read_text()))
    checkin_url = argv[1] if len(argv) > 1 else None
    asyncio.run(_run(spec, checkin_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
