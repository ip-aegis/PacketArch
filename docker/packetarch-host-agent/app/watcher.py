# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PacketArch host-agent watcher.

Long-lived loop that (a) drains the backend's file-queue (build/teardown/
reconcile requests) and (b) periodically RECONCILES: makes host reality match
the desired lab specs on disk. Reconcile-on-boot is what makes local sensor labs
survive a host reboot — the veth + daemon.json registry trust don't persist
across reboot, so the host-agent re-creates them; containers carry
`restart: unless-stopped` so Docker restarts those, and reconcile recreates any
that were removed.

Idles cheaply when no specs exist (always-on is harmless on a no-lab host).
"""

from __future__ import annotations

import logging
import os
import time

from app import hostops, state

log = logging.getLogger("hostagent.watcher")

POLL_INTERVAL = float(os.environ.get("HOST_AGENT_POLL_INTERVAL", "2"))
RECONCILE_INTERVAL = float(os.environ.get("HOST_AGENT_RECONCILE_INTERVAL", "30"))


# --- provisioning ----------------------------------------------------------

def _provision(spec: dict, *, fast: bool = False) -> None:
    """Make the host match one lab spec. Idempotent. `fast` skips the cosmetic
    progress writes used during reconcile (we still set terminal state)."""
    slug = spec["slug"]
    name = spec.get("name", slug)

    def status(state_, stage, pct, msg, **res):
        state.write_status(slug, name=name, state=state_, stage=stage,
                           percent=pct, message=msg, resources=res)

    try:
        if not fast:
            status("provisioning", "veth", 10, "creating virtual SPAN segment")
        hostops.ensure_veth(spec["gen_if"], spec["mon_if"], int(spec.get("mtu", 1500)))

        if not fast:
            status("provisioning", "registry", 25, "trusting CV Center registry")
        hostops.ensure_registry_trusted(spec.get("registry", ""))

        if not fast:
            status("provisioning", "compose", 35, "generating per-lab compose")
        work = state.work_dir(slug)
        sensor_yaml = hostops.rewrite_sensor_compose(
            spec["sensor_compose"], slug=slug, mon_if=spec["mon_if"],
            sensor_container=spec["sensor_container"],
        )
        hostops.sensor_compose_path(work).write_text(sensor_yaml)
        agent_compose = hostops.write_agent_compose(work, spec)

        if not fast:
            status("provisioning", "image", 45, "ensuring agent image")
        hostops.ensure_agent_image(spec)

        if not fast:
            status("provisioning", "sensor", 70, "starting CV sensor")
        hostops.compose_up(hostops.sensor_compose_path(work),
                           hostops._project(slug, "sensor"))

        if not fast:
            status("provisioning", "agent", 90, "starting traffic agent")
        hostops.compose_up(agent_compose, hostops._project(slug, "agent"))

        sensor_ok = hostops.container_running(spec["sensor_container"])
        agent_ok = hostops.container_running(spec["agent_container"])
        veth_ok = hostops.veth_ok(spec["gen_if"], spec["mon_if"])
        all_ok = sensor_ok and agent_ok and veth_ok
        status(
            "running" if all_ok else "degraded",
            "done", 100 if all_ok else 95,
            "lab running" if all_ok else "lab partially up — see resources",
            veth=veth_ok, sensor_running=sensor_ok, agent_running=agent_ok,
        )
        log.info("provisioned %s: state=%s", slug, "running" if all_ok else "degraded")
    except Exception as e:  # noqa: BLE001 — surface any failure as lab error state
        log.exception("provision failed for %s", slug)
        state.write_status(slug, name=name, state="error", stage="error",
                           percent=0, message=str(e))
        raise


def _deprovision(spec: dict, all_specs_after: list[dict]) -> None:
    """Tear a lab fully down (full delete = UX↔backend in sync): stop both
    compose projects, delete the veth, drop the registry trust if now unused,
    and remove spec/status/work for the slug."""
    slug = spec["slug"]
    name = spec.get("name", slug)
    state.write_status(slug, name=name, state="stopped", stage="teardown",
                       percent=0, message="tearing down")
    work = state.work_dir(slug)
    sp = hostops.sensor_compose_path(work)
    if sp.exists():
        hostops.compose_down(sp, hostops._project(slug, "sensor"))
    ac = work / "agent-compose.yml"
    if ac.exists():
        hostops.compose_down(ac, hostops._project(slug, "agent"))
    # Remove any macvlan net still bound to this lab's mon_if BEFORE the veth —
    # otherwise the held parent blocks the veth delete + a same-slug recreate.
    hostops.remove_macvlan_networks_on(spec["mon_if"])
    hostops.delete_veth(spec["gen_if"])
    hostops.untrust_registry_if_unused(spec.get("registry", ""), all_specs_after)
    state.delete_spec(slug)
    state.delete_status(slug)
    log.info("deprovisioned %s", slug)


# --- request handling -------------------------------------------------------

def _handle_request(req: dict) -> None:
    rid = req.get("id", "?")
    action = req.get("action")
    lab = req.get("lab") or {}
    try:
        if action == "build":
            state.write_spec(lab)            # persist desired state FIRST
            _provision(lab)
            state.write_result(rid, True, "lab provisioned", extra={"slug": lab.get("slug")})
        elif action == "teardown":
            spec = state.read_spec(lab.get("slug", "")) or lab
            # specs remaining AFTER this slug is removed (for registry-unused check)
            remaining = [s for s in state.list_specs() if s.get("slug") != spec.get("slug")]
            _deprovision(spec, remaining)
            state.write_result(rid, True, "lab torn down", extra={"slug": spec.get("slug")})
        elif action == "reconcile":
            _reconcile_all()
            state.write_result(rid, True, "reconciled")
        else:
            state.write_result(rid, False, f"unknown action: {action!r}")
    except Exception as e:  # noqa: BLE001
        log.exception("request %s (%s) failed", rid, action)
        state.write_result(rid, False, str(e), extra={"slug": lab.get("slug")})


def _reconcile_all() -> None:
    specs = state.list_specs()
    if not specs:
        return
    log.info("reconciling %d lab(s)", len(specs))
    for spec in specs:
        try:
            _provision(spec, fast=True)
        except Exception:  # noqa: BLE001 — one bad lab shouldn't stop the rest
            continue


# --- main loop --------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    state.ensure_dirs()
    log.info("PacketArch host-agent started; state=%s", state.STATE_ROOT)

    _reconcile_all()  # reboot survival: converge desired specs on boot
    last_reconcile = time.monotonic()

    while True:
        for path in state.list_requests():
            req = state.read_request(path)
            state.consume_request(path)
            if req:
                _handle_request(req)

        if time.monotonic() - last_reconcile >= RECONCILE_INTERVAL:
            _reconcile_all()
            last_reconcile = time.monotonic()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
