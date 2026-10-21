# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1202 Actuated Signal Controller (1.3.6.1.4.1.1206.4.2.1).

Models a NEMA dual-ring, eight-phase intersection running coordinated
time-of-day patterns, and answers the objects a central system polls:
phase status groups, detector status, volume/occupancy, unit and
coordination status.

Phase layout (standard NEMA)::

    ring 1:  1 → 2  ‖  3 → 4
    ring 2:  5 → 6  ‖  7 → 8
               barrier A   barrier B

Phases 2/6 are the coordinated main-street throughs, 4/8 the side street,
odd phases the protected lefts (omitted at simple four-phase intersections).
Both rings cross a barrier together, so concurrent phases are always
compatible and each phase is in exactly one of red / yellow / green.

Coordinated fixed splits with calls and detector data derived from demand.
Time-of-day plan changes run a transition cycle (shortway or dwell), so the
display never jumps. Actuated gap-out / skip lands in Phase 1; see
SPEC_NEEDS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.protocol_engines.snmp.ntcip._model import (
    NtcipClock,
    NtcipDevice,
    demand_level,
    instance,
    unit,
    value,
)

PHASES = range(1, 9)
LEFTS = (1, 3, 5, 7)
PED_PHASES = (2, 4, 6, 8)
COORD_PHASES = (2, 6)
RING_ORDER = ((1, 2, 3, 4), (5, 6, 7, 8))
BARRIER_A = (1, 2, 5, 6)

FREE_PATTERN = 254          # coordPatternStatus: 254 = Free
TIMEBASE_CONTROL = 6        # unitControlStatus: timebase(6)
NOT_FLASH = 2               # unitFlashStatus: notFlash(2)
NOT_FREE, COMMAND_FREE = 2, 3   # localFreeStatus
VOLUME_PERIOD_S = 60

# (start hour, pattern, nominal cycle s); pattern 254 = free (no coordination)
TOD_PLANS = (
    (0.0, FREE_PATTERN, 90),
    (5.0, 4, 90),
    (6.5, 1, 120),
    (9.0, 2, 100),
    (15.0, 3, 130),
    (18.5, 4, 90),
    (22.0, FREE_PATTERN, 90),
)


@dataclass(frozen=True)
class Intersection:
    """Static, seeded configuration of one intersection."""

    eight_phase: bool
    main_share: float
    yellow: dict[int, float]
    red_clear: dict[int, float]
    walk: float
    ped_clear: float
    offset_frac: float


def _intersection(dev: NtcipDevice) -> Intersection:
    s = dev.seed
    return Intersection(
        eight_phase=unit(s, "eight_phase") < 0.65,
        main_share=0.55 + 0.1 * unit(s, "main_share"),
        yellow={p: (3.5 if p in LEFTS else 4.0 + 0.5 * round(unit(s, "y", p))) for p in PHASES},
        red_clear={p: 1.0 + 0.5 * int(unit(s, "r", p) * 3) for p in PHASES},
        walk=7.0,
        ped_clear=float(10 + int(unit(s, "fdw") * 9)),
        offset_frac=unit(s, "offset"),
    )


def _plan(dev: NtcipDevice, clock: NtcipClock) -> tuple[int, int]:
    """(pattern, cycle_s) for the time of day. Cycles are corridor-wide."""
    hour = clock.hour
    pattern, cycle = TOD_PLANS[0][1], TOD_PLANS[0][2]
    for start, pat, nominal in TOD_PLANS:
        if hour >= start:
            pattern, cycle = pat, nominal
    return pattern, _plan_cycle(dev, pattern, cycle)


MIN_LEFT_GREEN_S = 7.0


def _phase_min(ix: Intersection, p: int) -> float:
    """Shortest split that still times the phase's green and clearances.

    Ped phases must hold Walk + flashing Don't Walk inside their green.
    """
    green = ix.walk + ix.ped_clear if p in PED_PHASES else MIN_LEFT_GREEN_S
    return green + ix.yellow[p] + ix.red_clear[p]


def _splits(ix: Intersection, cycle: int) -> dict[int, float]:
    """Phase splits (s). Ring 1 and ring 2 sum to the same time per barrier.

    Every TOD cycle (>= 90 s) fits all eight phase minimums (<= 88 s), so the
    main/side share only moves time that is above the minimums.
    """
    def barrier_min(lead_pair, lag_pair):
        lead = max(_phase_min(ix, p) for p in lead_pair) if ix.eight_phase else 0.0
        return lead + max(_phase_min(ix, p) for p in lag_pair)

    a_min = barrier_min((1, 5), (2, 6))
    b_min = barrier_min((3, 7), (4, 8))
    a = min(max(round(cycle * ix.main_share), a_min), cycle - b_min)
    b = cycle - a
    splits = {p: 0.0 for p in PHASES}
    for (lead, lag), total, share in (((1, 2), a, 0.22), ((3, 4), b, 0.28)):
        for ring_offset in (0, 4):
            lp, tp = lead + ring_offset, lag + ring_offset
            left = 0.0
            if ix.eight_phase:
                left = max(_phase_min(ix, lp), round(total * share))
                left = min(left, total - _phase_min(ix, tp))
            splits[lp], splits[tp] = left, total - left
    return splits


@dataclass(frozen=True)
class PhaseTiming:
    phase: int
    interval: str        # "G", "Y" or "R" (red clearance)
    t_in_phase: float    # seconds since this phase's green began
    green_s: float


def _ring_timing(
    ring: tuple[int, ...], splits: dict[int, float], ix: Intersection, a_s: float, pos: float,
) -> tuple[PhaseTiming, int]:
    """Active phase timing in one ring at cycle position ``pos``, plus next phase."""
    barrier = ring[:2] if pos < a_s else ring[2:]
    local = pos if pos < a_s else pos - a_s
    served = [p for p in barrier if splits[p] > 0]
    active = served[-1]
    for p in served:
        if local < splits[p]:
            active = p
            break
        local -= splits[p]
    green = splits[active] - ix.yellow[active] - ix.red_clear[active]
    if local < green:
        interval = "G"
    elif local < green + ix.yellow[active]:
        interval = "Y"
    else:
        interval = "R"
    order = [p for p in ring if splits[p] > 0]
    nxt = order[(order.index(active) + 1) % len(order)]
    return PhaseTiming(active, interval, local, green), nxt


def _bits(phases) -> int:
    mask = 0
    for p in phases:
        mask |= 1 << (p - 1)   # bit 0 = phase 1 (phaseStatusGroup 1)
    return mask


def _plan_cycle(dev: NtcipDevice, pattern: int, nominal: int) -> int:
    if pattern == FREE_PATTERN:
        return nominal
    # Every intersection of a scenario shares the pattern's cycle length.
    return nominal + 10 * int(unit(dev.region_seed, "cycle", pattern) * 2)


def _local_pos(ix: Intersection, pattern: int, cycle: int, local_s: float) -> float:
    """Steady-state local cycle position of ``pattern`` at local time ``local_s``."""
    offset = 0.0 if pattern == FREE_PATTERN else ix.offset_frac * cycle
    return ((local_s % 86400) % cycle - offset) % cycle


def _transition(dev: NtcipDevice, ix: Intersection, clock: NtcipClock):
    """Where the controller is relative to the latest time-of-day plan change.

    A controller never jumps its cycle position. When the plan changes it
    finishes the cycle in progress, then runs ONE transition cycle whose
    length lands the new pattern exactly on its offset: "shortway" (the
    coordinated phases 2/6 are shortened) when the phase minimums still fit,
    otherwise "dwell" (2/6 are extended by up to one cycle).

    Returns ``(mode, data)``: ``("old", (pattern, cycle))`` while finishing the
    previous plan's cycle, ``("transition", (start_local_s, length_s,
    pattern, cycle))`` during the transition cycle, or ``("steady", None)``.
    """
    hour = clock.hour
    idx = max(i for i, (start, _p, _c) in enumerate(TOD_PLANS) if hour >= start)
    start_h, pattern, nominal = TOD_PLANS[idx]
    _ps, prev_pattern, prev_nominal = TOD_PLANS[idx - 1]   # idx 0 wraps to 22:00
    new_cycle = _plan_cycle(dev, pattern, nominal)
    old_cycle = _plan_cycle(dev, prev_pattern, prev_nominal)
    if (prev_pattern, old_cycle) == (pattern, new_cycle):
        return "steady", None

    t_b = clock.local_s - clock.seconds_of_day + start_h * 3600
    end_old = t_b + (old_cycle - _local_pos(ix, prev_pattern, old_cycle, t_b)) % old_cycle
    if clock.local_s < end_old:
        return "old", (prev_pattern, old_cycle)

    gap = (-_local_pos(ix, pattern, new_cycle, end_old)) % new_cycle
    if gap < 1e-6:
        return "steady", None
    splits = _splits(ix, new_cycle)
    shortfall = new_cycle - gap
    fits = all(splits[p] - shortfall >= _phase_min(ix, p) for p in COORD_PHASES)
    length = gap if fits else gap + new_cycle
    if clock.local_s < end_old + length:
        return "transition", (end_old, length, pattern, new_cycle)
    return "steady", None


def _cycle_state(dev: NtcipDevice, clock: NtcipClock):
    ix = _intersection(dev)
    mode, data = _transition(dev, ix, clock)
    if mode == "transition":
        start, length, pattern, cycle = data
        splits = _splits(ix, cycle)
        extra = length - cycle
        splits[2] += extra
        splits[6] += extra
        pos = clock.local_s - start
        return ix, pattern, length, splits, splits[1] + splits[2], clock.seconds_of_day % cycle, pos, int(start)
    if mode == "old":
        pattern, cycle = data
    else:
        pattern, cycle = _plan(dev, clock)
    splits = _splits(ix, cycle)
    a_s = splits[1] + splits[2]
    sync = clock.seconds_of_day % cycle                      # since system reference
    offset = 0.0 if pattern == FREE_PATTERN else ix.offset_frac * cycle
    pos = (sync - offset) % cycle                            # local cycle position
    cycle_no = int((clock.local_s - offset) // cycle)
    return ix, pattern, cycle, splits, a_s, sync, pos, cycle_no


def _has_vehicle_call(dev: NtcipDevice, phase: int, cycle_no: int, demand: float) -> bool:
    if phase in COORD_PHASES:
        return True                                          # coordinated recall
    p = demand * (0.85 if phase in LEFTS else 0.95)
    return unit(dev.seed, "vc", phase, cycle_no) < p


def _has_ped_call(dev: NtcipDevice, phase: int, cycle_no: int, demand: float) -> bool:
    return unit(dev.seed, "pc", phase, cycle_no) < 0.1 + 0.3 * demand


def phase_status(dev: NtcipDevice, clock: NtcipClock) -> dict[str, int]:
    """Phase status group 1 bitmasks plus coordination counters."""
    ix, pattern, cycle, splits, a_s, sync, pos, cycle_no = _cycle_state(dev, clock)
    demand = demand_level(clock.hour)
    used = [p for p in PHASES if splits[p] > 0]

    timings, nexts = [], []
    for ring in RING_ORDER:
        timing, nxt = _ring_timing(ring, splits, ix, a_s, pos)
        timings.append(timing)
        if timing.interval in ("Y", "R"):
            nexts.append(nxt)   # decided at end of the terminating phase's green

    greens = [t.phase for t in timings if t.interval == "G"]
    yellows = [t.phase for t in timings if t.interval == "Y"]
    ons = [t.phase for t in timings]
    reds = [p for p in used if p not in greens and p not in yellows]

    walks, ped_clears = [], []
    for t in timings:
        if t.phase in PED_PHASES and t.interval == "G" and _has_ped_call(dev, t.phase, cycle_no, demand):
            if t.t_in_phase < ix.walk:
                walks.append(t.phase)
            elif t.t_in_phase < ix.walk + ix.ped_clear:
                ped_clears.append(t.phase)
    dont_walks = [p for p in PED_PHASES if p in used and p not in walks and p not in ped_clears]

    veh_calls, ped_calls = [], []
    for p in used:
        if p in greens:
            continue
        # A call that will be served next appears some time after the phase
        # went red (arrivals are random), so calls build up over the red.
        if _has_vehicle_call(dev, p, cycle_no, demand) and unit(dev.seed, "arr", p, cycle_no) < 0.5 + 0.5 * demand:
            veh_calls.append(p)
        if p in PED_PHASES and p not in walks and _has_ped_call(dev, p, cycle_no + 1, demand):
            ped_calls.append(p)

    return {
        "reds": _bits(reds),
        "yellows": _bits(yellows),
        "greens": _bits(greens),
        "dont_walks": _bits(dont_walks),
        "ped_clears": _bits(ped_clears),
        "walks": _bits(walks),
        "veh_calls": _bits(veh_calls),
        "ped_calls": _bits(ped_calls),
        "ons": _bits(ons),
        "nexts": _bits(nexts),
        "pattern": pattern,
        "cycle": cycle,
        "cycle_status": 0 if pattern == FREE_PATTERN else max(1, int(round(cycle - pos))),
        "sync_status": 0 if pattern == FREE_PATTERN else int(sync),
        "free_status": COMMAND_FREE if pattern == FREE_PATTERN else NOT_FREE,
    }


def _detector_rate_per_min(phase: int, demand: float) -> float:
    if phase in COORD_PHASES:
        base = 28.0            # two through lanes on the main street
    elif phase in (4, 8):
        base = 9.0
    else:
        base = 4.0             # protected lefts
    return base * demand


def detector_status(dev: NtcipDevice, clock: NtcipClock, status: dict[str, int]) -> int:
    """vehicleDetectorStatusGroupActive.1 — detectors 1..8 are the phase stop bars."""
    demand = demand_level(clock.hour)
    tick = int(clock.epoch_s * 2)
    active = 0
    for p in PHASES:
        bit = 1 << (p - 1)
        if status["veh_calls"] & bit:
            active |= bit                                    # queued on red
        elif status["greens"] & bit:
            occupancy = min(0.6, _detector_rate_per_min(p, demand) / 60.0 * 0.9)
            if unit(dev.seed, "det", p, tick) < occupancy:
                active |= bit                                # vehicle crossing
    return active


def volume_occupancy(dev: NtcipDevice, clock: NtcipClock, detector: int) -> tuple[int, int]:
    """(detectorVolume, detectorOccupancy) for the last completed 60 s period."""
    period = int(clock.epoch_s // VOLUME_PERIOD_S) - 1
    period_clock = NtcipClock(period * VOLUME_PERIOD_S, clock.utc_offset_s)
    demand = demand_level(period_clock.hour)
    rate = _detector_rate_per_min(detector, demand)
    noise = 0.75 + 0.5 * unit(dev.seed, "vol", detector, period)
    volume = min(254, int(round(rate * noise)))
    # ~0.45 s on a 6 ft loop per vehicle at speed, more as queues form.
    occupied_s = volume * (0.45 + 1.2 * demand * demand)
    occupancy_half_pct = min(200, int(round(occupied_s / VOLUME_PERIOD_S * 200)))
    return volume, occupancy_half_pct


def snapshot(dev: NtcipDevice, clock: NtcipClock) -> dict[str, tuple[Any, str]]:
    """All modelled 1202 instances for this controller at ``clock``."""
    st = phase_status(dev, clock)
    ix = _intersection(dev)
    out = dict([
        value("maxPhases", 16),
        value("maxPhaseGroups", 2),
        value("maxRings", 4),
        value("maxVehicleDetectors", 64),
        value("maxVehicleDetectorStatusGroups", 8),
        value("maxPatterns", 48),
        value("phaseStatusGroupNumber", 1, 1),
        value("phaseStatusGroupReds", st["reds"], 1),
        value("phaseStatusGroupYellows", st["yellows"], 1),
        value("phaseStatusGroupGreens", st["greens"], 1),
        value("phaseStatusGroupDontWalks", st["dont_walks"], 1),
        value("phaseStatusGroupPedClears", st["ped_clears"], 1),
        value("phaseStatusGroupWalks", st["walks"], 1),
        value("phaseStatusGroupVehCalls", st["veh_calls"], 1),
        value("phaseStatusGroupPedCalls", st["ped_calls"], 1),
        value("phaseStatusGroupPhaseOns", st["ons"], 1),
        value("phaseStatusGroupPhaseNexts", st["nexts"], 1),
        value("vehicleDetectorStatusGroupActive", detector_status(dev, clock, st), 1),
        value("vehicleDetectorStatusGroupAlarms", 0, 1),
        value("volumeOccupancySequence", int(clock.epoch_s // VOLUME_PERIOD_S) % 256),
        value("volumeOccupancyPeriod", VOLUME_PERIOD_S),
        value("activeVolumeOccupancyDetectors", 8),
        value("unitControlStatus", TIMEBASE_CONTROL),
        value("unitFlashStatus", NOT_FLASH),
        value("unitAlarmStatus1", 0),
        value("unitAlarmStatus2", 0),
        value("shortAlarmStatus", 0),
        value("coordPatternStatus", st["pattern"]),
        value("localFreeStatus", st["free_status"]),
        value("coordCycleStatus", st["cycle_status"]),
        value("coordSyncStatus", st["sync_status"]),
        value("systemPatternControl", 255 if st["pattern"] == FREE_PATTERN else st["pattern"]),
    ])
    for d in PHASES:
        vol, occ = volume_occupancy(dev, clock, d)
        out.update([value("detectorVolume", vol, d), value("detectorOccupancy", occ, d)])
    for _start, pat, nominal in TOD_PLANS:
        if pat == FREE_PATTERN:
            continue
        cycle = nominal + 10 * int(unit(dev.region_seed, "cycle", pat) * 2)
        out.update([
            value("patternCycleTime", cycle, pat),
            value("patternOffsetTime", int(ix.offset_frac * cycle), pat),
        ])
    return out


STATUS_BLOCK = [
    instance("phaseStatusGroupReds", 1),
    instance("phaseStatusGroupYellows", 1),
    instance("phaseStatusGroupGreens", 1),
    instance("phaseStatusGroupDontWalks", 1),
    instance("phaseStatusGroupPedClears", 1),
    instance("phaseStatusGroupWalks", 1),
    instance("phaseStatusGroupVehCalls", 1),
    instance("phaseStatusGroupPedCalls", 1),
    instance("phaseStatusGroupPhaseOns", 1),
    instance("phaseStatusGroupPhaseNexts", 1),
    instance("vehicleDetectorStatusGroupActive", 1),
    instance("unitControlStatus"),
    instance("unitFlashStatus"),
    instance("unitAlarmStatus1"),
    instance("shortAlarmStatus"),
    instance("coordPatternStatus"),
    instance("localFreeStatus"),
    instance("coordCycleStatus"),
    instance("coordSyncStatus"),
]

VOLUME_BLOCK = [
    instance("volumeOccupancySequence"),
    instance("volumeOccupancyPeriod"),
    instance("activeVolumeOccupancyDetectors"),
    *[instance("detectorVolume", d) for d in PHASES],
    *[instance("detectorOccupancy", d) for d in PHASES],
]

CONFIG_BLOCK = [
    instance("maxPhases"),
    instance("maxPhaseGroups"),
    instance("maxRings"),
    instance("maxVehicleDetectors"),
    instance("maxPatterns"),
    *[instance("patternCycleTime", p) for p in (1, 2, 3, 4)],
    *[instance("patternOffsetTime", p) for p in (1, 2, 3, 4)],
]
