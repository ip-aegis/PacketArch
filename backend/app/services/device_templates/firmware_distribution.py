# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Deterministic firmware-variant selection ("template-defined mix").

When a scenario places ``total_count`` copies of a device, each copy must pick a
firmware variant. The chosen variant is the SINGLE source of both the emitted
firmware version AND the CVEs for that instance, so the on-wire firmware and the
assigned CVE always agree (the decoupling that previously let "patched" firmware
hide a curated CVE).

Selection is a pure function of ``(template, instance_index, total_count)`` — no
RNG — so materialising the same scenario twice yields the same fleet, and the
per-instance call ``select_firmware_variant(t, i, n)`` is consistent with the
whole distribution for ``i in range(n)``.

Distribution rules (see ``FirmwareVariant.population_weight``):
  * No variant sets a weight  -> every instance gets ``get_default_firmware()``
    (backward compatible with templates not yet curated).
  * Weights set -> instances are split across variants proportionally to weight
    via the largest-remainder method.
  * Coverage floor -> if any *vulnerable* variant (non-empty ``cves``) carries
    weight > 0, at least one instance is guaranteed that variant even when the
    proportional split would have rounded it to zero (e.g. a single-device role).
    This is what makes "every vendor surfaces a CVE in every scenario" hold by
    construction rather than by chance.
"""

from __future__ import annotations

from ._types import DeviceTemplate, FirmwareVariant


def _largest_remainder(weights: list[float], total: int) -> list[int]:
    """Apportion ``total`` integer slots across ``weights`` proportionally.

    Largest-remainder (Hamilton) method: floor each share, then hand the leftover
    slots to the largest fractional remainders. Deterministic; ties break by
    higher weight then lower index.
    """
    s = sum(weights)
    if s <= 0 or total <= 0:
        return [0] * len(weights)
    raw = [w / s * total for w in weights]
    counts = [int(x) for x in raw]
    leftover = total - sum(counts)
    order = sorted(
        range(len(weights)),
        key=lambda i: (raw[i] - counts[i], weights[i], -i),
        reverse=True,
    )
    for k in range(leftover):
        counts[order[k % len(order)]] += 1
    return counts


def build_distribution(
    template: DeviceTemplate, total_count: int
) -> list[FirmwareVariant]:
    """Return a length-``total_count`` list mapping each instance index to a
    firmware variant, honouring weights + the coverage floor.

    Vulnerable variants are placed on the LOW instance indices so that a
    single-device role (instance 0) always lands on a CVE-bearing build when one
    is weighted. ``select_firmware_variant`` indexes into this list.
    """
    variants = list(template.firmware_variants or [])
    if not variants:
        return []
    if total_count <= 0:
        total_count = 1

    weighted = [v for v in variants if v.population_weight > 0]
    if not weighted:
        # Uncurated template: faithful default for every instance.
        default = template.get_default_firmware()
        return [default] * total_count if default else [variants[0]] * total_count

    weights = [v.population_weight for v in weighted]
    counts = _largest_remainder(weights, total_count)

    # Coverage floor: guarantee >=1 vulnerable instance when a vulnerable variant
    # is weighted but rounding zeroed it out.
    vuln_idx = [i for i, v in enumerate(weighted) if v.cves]
    if vuln_idx and not any(counts[i] for i in vuln_idx):
        take = max(vuln_idx, key=lambda i: weights[i])  # highest-weight vulnerable
        give = max(range(len(counts)), key=lambda i: counts[i])  # biggest donor
        counts[give] -= 1
        counts[take] += 1

    # Emit vulnerable variants first (low indices), then the rest, each in
    # declaration order — stable and deterministic.
    ordered: list[FirmwareVariant] = []
    for i in sorted(range(len(weighted)), key=lambda i: (not weighted[i].cves, i)):
        ordered.extend([weighted[i]] * counts[i])
    return ordered


def select_firmware_variant(
    template: DeviceTemplate, instance_index: int, total_count: int
) -> FirmwareVariant | None:
    """Pick the firmware variant for one instance ("template-defined mix").

    Pure function of the arguments. ``instance_index`` is clamped into range so
    callers needn't guard. Returns ``None`` only when the template has no
    firmware variants at all.
    """
    dist = build_distribution(template, total_count)
    if not dist:
        return None
    return dist[instance_index % len(dist)]
