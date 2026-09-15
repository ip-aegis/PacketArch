# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Audit — and repair — Cyber Vision networks that CV 5.6 never registered.

Run inside the backend container (scripts/cv-repair-networks.sh does this):

    python -m app.cli.repair_cv_networks                          # report
    python -m app.cli.repair_cv_networks --scenario <id|name> --apply

The defect
----------
CV 5.6 moved network creation into the new UI. A network created through the
classic ``POST /api/3.0/networks/`` is not registered correctly: it lists on
both APIs and assets are attributed to it, but CV never creates the network's
**asset group** — and the communications map groups on asset groups, so the
network is invisible there. Every other check comes back clean, which is why
this is easy to misdiagnose.

A CSV *upsert* does not repair such a network: only a *create* materializes the
asset group. So repair means delete-then-create, which is destructive and
resets Organization Hierarchy membership (OH is keyed by network id, and a
recreated network gets a new id). That is why this is an operator action and
not something provisioning does implicitly.

What it does
------------
Default (no ``--apply``) is a read-only report — the four checks that together
distinguish this defect from a healthy install:

1. every expected range present (classic ``GET /networks/``);
2. **its asset group exists** (``GET /scv/4.0/asset-group``) — the only check
   that detects this defect;
3. it is assigned to the right OH level, not parked at ``Global``;
4. PacketArch's stored ids match CV.

``--scenario X --apply`` repairs ONE scenario: delete the broken ids, assert
the asset groups are actually gone, CSV-create, verify every range came back
with an asset group, then re-resolve ids and re-assign the hierarchy. It
refuses to sweep — work one scenario at a time and verify before continuing.

Exit codes: 0 all healthy / repaired, 1 something is broken or a repair
aborted, 2 misconfiguration (no center, no UI credentials).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.scenario import Scenario
from app.services import cv_centers
from app.services import cv_provisioning_service as cps
from app.services.cyber_vision_ui_service import CyberVisionUIError, build_networks_csv

# CV's root Organization Hierarchy level. A repaired network lands back here,
# because OH membership is keyed by network id and a recreated network has a
# new one.
_GLOBAL = "Global"


class Aborted(Exception):
    """A repair step failed its verification — stop before doing more damage."""


class Misconfigured(Exception):
    """The Center is not set up for this check (exit 2, not a failed check)."""


def _fmt(ok: bool | None) -> str:
    """``None`` means "not checked", which is not the same as a failure."""
    if ok is None:
        return "?"
    return "ok" if ok else "BAD"


async def _scenario_rows(db, wanted: str | None) -> list[Scenario]:
    """Scenarios carrying CV state, optionally narrowed to one id or name."""
    rows = (await db.execute(select(Scenario))).scalars().all()
    rows = [s for s in rows if (s.definition or {}).get(cps.CV_STATE_KEY)]
    if wanted is None:
        return sorted(rows, key=lambda s: s.name or "")
    picked = [s for s in rows if str(s.id) == wanted or (s.name or "") == wanted]
    if not picked:
        raise SystemExit(f"No CV-provisioned scenario matches '{wanted}'.")
    if len(picked) > 1:
        raise SystemExit(f"'{wanted}' matches {len(picked)} scenarios — use the id.")
    return picked


async def _center_state(db, center):
    """Everything the checks need from CV, fetched once per center."""
    classic = cv_centers.classic_client(center)
    v1 = cv_centers.v1_client(center)
    ui = cv_centers.ui_client(center)
    if classic is None:
        raise Misconfigured(f"Center '{center.name}' has no classic API token configured.")
    if ui is None:
        raise Misconfigured(
            f"Center '{center.name}' has no CV UI credentials configured. The asset-group "
            "check needs a UI session (/scv) — an API token cannot reach it. Add a UI "
            "username/password under Settings > Cyber Vision."
        )
    try:
        live = {n.get("ipRange"): n for n in await classic.get_networks() if n.get("ipRange")}
        groups = {(g.get("name") or "").strip() for g in await ui.list_asset_groups()}
        levels, v1_nets = {}, {}
        if v1 is not None:
            levels = {lvl["id"]: lvl for lvl in await v1.get_oh_levels()}
            v1_nets = {n["id"]: n for n in await v1.get_networks()}
    finally:
        await classic.close()
        if v1 is not None:
            await v1.close()
    return {
        "live": live,
        "groups": groups,
        "levels": levels,
        "v1_nets": v1_nets,
        # Without a new-UI token the hierarchy check is unknown, not failed.
        "oh_known": v1 is not None,
        "ui": ui,
    }


async def _cv_state(db, scenario_id) -> dict:
    """The scenario's CV state, read straight from the row.

    NEVER take this off the ORM attribute. The provisioning saves go through
    raw ``jsonb_set`` SQL, so ``scenario.definition`` is stale the moment
    ``provision_networks`` has run — which is exactly when the post-repair
    report needs it. Same hazard as ``cv_provisioning_service._stored_center_id``.
    """
    definition = (
        await db.execute(select(Scenario.definition).where(Scenario.id == scenario_id))
    ).scalar_one() or {}
    return definition.get(cps.CV_STATE_KEY) or {}


def _report_scenario(cv: dict, state: dict) -> list[dict]:
    """Per-range check rows for one scenario's CV state. Pure — no I/O."""
    stored = cv.get("networks") or {}
    oh = cv.get("org_hierarchy") or {}
    expected_levels = {oh.get("scenario_level_id"), *(oh.get("zones") or {}).values()}

    rows = []
    for ip_range, meta in sorted(stored.items()):
        live = state["live"].get(ip_range)
        name = (meta.get("name") or "").strip()
        v1_net = state["v1_nets"].get(str(live.get("id"))) if live else None
        level_id = (v1_net or {}).get("groupId")
        level_name = (state["levels"].get(level_id) or {}).get("name")

        if not state["oh_known"]:
            oh_ok = None  # no new-UI token: unknown, not broken
        else:
            oh_ok = bool(level_name) and level_name != _GLOBAL and level_id in expected_levels

        rows.append(
            {
                "range": ip_range,
                "name": name,
                "present": live is not None,
                # THE detector: presence in CV's asset-group list, by name.
                # Never interfaceCount — a scenario's /16 umbrella legitimately
                # reports 0 because CV attributes assets to the per-zone /24s.
                "asset_group": name in state["groups"],
                "oh_ok": oh_ok,
                "oh_level": level_name or "-",
                "id_in_sync": bool(live) and str(live.get("id")) == str(meta.get("id")),
                "live_id": str(live.get("id")) if live else None,
            }
        )
    return rows


def _print_report(scenario: Scenario, rows: list[dict]) -> int:
    broken = [r for r in rows if not r["asset_group"]]
    print(f"\n{scenario.name}  ({scenario.id})")
    print(f"  {'range':18} {'present':8} {'assetgrp':9} {'oh':4} {'ids':4}  oh level / name")
    for r in rows:
        print(
            f"  {r['range']:18} {_fmt(r['present']):8} {_fmt(r['asset_group']):9} "
            f"{_fmt(r['oh_ok']):4} {_fmt(r['id_in_sync']):4}  "
            f"{r['oh_level']} / {r['name']}"
        )
    if broken:
        print(
            f"  => {len(broken)} of {len(rows)} networks have NO asset group and will not "
            f"appear on the communications map."
        )
    else:
        print(f"  => all {len(rows)} networks have an asset group.")
    return len(broken)


async def _repair(db, scenario: Scenario, rows: list[dict], state: dict, center) -> None:
    """Delete → verify gone → CSV create → verify → re-resolve ids + hierarchy."""
    broken = [r for r in rows if not r["asset_group"]]
    if not broken:
        print("  Nothing to repair — every network already has an asset group.")
        return

    ui = state["ui"]
    ids = [r["live_id"] for r in broken if r["live_id"]]
    names = {r["name"] for r in broken}
    print(f"\n  Repairing {len(broken)} network(s): {', '.join(r['range'] for r in broken)}")
    print(
        "  NOTE: between the delete and the create, assets in these ranges fall back to "
        "CV's built-in 10/8."
    )

    if ids:
        print(f"  - deleting {len(ids)} network(s) via the CV UI API")
        await ui.delete_networks(ids)
        # A surviving asset group means the CSV create would take CV's UPDATE
        # path, which repairs nothing while reporting success. Stop instead.
        still = {(g.get("name") or "").strip() for g in await ui.list_asset_groups()} & names
        if still:
            raise Aborted(
                f"asset group(s) still present after delete: {', '.join(sorted(still))}. "
                "A create would silently become an upsert and repair nothing."
            )
        print("  - verified their asset groups are gone")

    # Reuse the provisioning payload builder so a recreated network is
    # byte-identical to a freshly provisioned one (same name normalization,
    # same classic "OT Internal" type vocabulary the CSV import expects).
    items = [cps._net_item(r["name"], r["range"]) for r in broken]
    res = await ui.import_networks_csv(build_networks_csv(items))
    created = int(res.get("created") or 0)
    print(f"  - CSV import: {res}")
    if created != len(items):
        raise Aborted(
            f"CSV import created {created} of {len(items)} — an 'updated' row does not "
            "repair a bad network. Not continuing."
        )

    groups = {(g.get("name") or "").strip() for g in await ui.list_asset_groups()}
    missing = names - groups
    if missing:
        raise Aborted(f"no asset group after create for: {', '.join(sorted(missing))}")
    print("  - verified every recreated network now has an asset group")

    # Recreating a network changes its id, so PacketArch's stored ids are stale
    # and OH membership (keyed by id) is gone. provision_networks creates
    # nothing here — everything exists — it just re-resolves the ids by range.
    nets = await cps.provision_networks(db, scenario, center_id=center.id)
    print(f"  - re-resolved stored ids ({len(nets.get('networks') or {})} networks)")
    # networks_state MUST be passed: the default path reads the ORM attribute,
    # which is stale because the save above went through raw SQL.
    await cps.provision_org_hierarchy(
        db, scenario, networks_state=nets.get("networks"), center_id=center.id
    )
    print("  - re-assigned the Organization Hierarchy")


async def _run(wanted: str | None, apply: bool) -> int:
    async with async_session_maker() as db:
        scenarios = await _scenario_rows(db, wanted)
        if not scenarios:
            print("No CV-provisioned scenarios found.")
            return 0

        exit_code = 0
        by_center: dict[str, list[Scenario]] = {}
        for s in scenarios:
            cid = ((s.definition or {}).get(cps.CV_STATE_KEY) or {}).get("center_id")
            by_center.setdefault(str(cid), []).append(s)

        for cid, group in by_center.items():
            center = await cv_centers.resolve_center(db, None if cid in ("None", "") else cid)
            if center is None:
                print("Cyber Vision is not configured.", file=sys.stderr)
                return 2
            print(f"=== Center: {center.name} ({center.url}) ===", flush=True)
            try:
                state = await _center_state(db, center)
            except Misconfigured as e:
                print(f"{e}", file=sys.stderr)
                return 2
            try:
                for s in group:
                    rows = _report_scenario(await _cv_state(db, s.id), state)
                    broken = _print_report(s, rows)
                    if not apply:
                        exit_code = exit_code or (1 if broken else 0)
                        continue
                    try:
                        await _repair(db, s, rows, state, center)
                    except (Aborted, CyberVisionUIError) as e:
                        print(f"  ABORTED: {e}", file=sys.stderr)
                        return 1
                    # Re-read BOTH sides and re-report, so the operator sees the
                    # result of the repair rather than the state that prompted
                    # it: CV has new network ids, and our stored ids were just
                    # rewritten by raw SQL behind the ORM's back.
                    fresh = await _center_state(db, center)
                    try:
                        still_broken = _print_report(
                            s, _report_scenario(await _cv_state(db, s.id), fresh)
                        )
                    finally:
                        await fresh["ui"].close()
                    exit_code = exit_code or (1 if still_broken else 0)
            finally:
                await state["ui"].close()
        return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Report — and optionally repair — Cyber Vision networks that CV 5.6 "
            "registered without an asset group (empty communications map)."
        )
    )
    parser.add_argument(
        "--scenario",
        help="Scenario id or exact name. Required with --apply (repair never sweeps).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually repair: delete and recreate the broken networks, then re-apply "
        "the hierarchy. Destructive; one scenario at a time.",
    )
    args = parser.parse_args()

    if args.apply and not args.scenario:
        print(
            "ERROR: --apply requires --scenario. Repair one scenario at a time and "
            "verify before continuing.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(asyncio.run(_run(args.scenario, args.apply)))


if __name__ == "__main__":
    main()
