# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Static template linter — catches scenario protocol-consistency bugs.

This linter runs static checks on a scenario template *before* any PCAP is
generated. It catches the class of bugs where a template's flows reference a
protocol that the source/target devices don't actually declare, or that the
runtime can't resolve to a known engine. Those bugs are silent at runtime —
flows get dropped or generate wire traffic that doesn't match the device
fingerprint, and CV DPI then can't identify the device.

Severities
----------
- ``error``  : will cause flows to be dropped or fingerprint inconsistencies
               that break CV identification. Templates must be error-free.
- ``warning``: cosmetic / non-blocking issues (orphaned protocols on devices,
               etc.). Reported but does not fail the build.

Use from CLI via ``scripts/validate_scenario.py --lint-only`` or as a
parametrized pytest in ``tests/integration/test_scenario_fingerprints.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.protocol_engines.protocols import resolve_protocol
from app.protocol_engines.types import ProtocolType


# Protocols that are intentionally not handled by any runtime engine.
# Flows using these are silently dropped today; the linter must flag them
# so the template author can either remove the flow or move it to
# `cloud_services` (which has its own runtime path).
_NON_ENGINE_PROTOCOLS = {"https", "rdp", "http", "ssh", "ftp"}

_VALID_RUNTIME_PROTOCOLS: set[str] = {p.value for p in ProtocolType}


@dataclass(frozen=True)
class LintIssue:
    """A single static-analysis finding for a template."""

    template_key: str
    severity: str  # "error" | "warning"
    code: str  # short stable identifier, e.g. "flow_proto_unresolvable"
    message: str
    flow_index: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def format(self) -> str:
        loc = f"flow#{self.flow_index}" if self.flow_index is not None else "template"
        return f"  [{self.severity}] {self.code} ({loc}): {self.message}"


def lint_template(template_key: str, template: dict[str, Any]) -> list[LintIssue]:
    """Run static checks on a single scenario template.

    Returns a list of LintIssue, possibly empty. Order is stable so output
    diffs are reviewable.

    Checks performed:

    1. ``flow_proto_unresolvable`` (error) — a flow's `protocol` field cannot
       be resolved to a runtime ``ProtocolType`` even after alias resolution.
       Such flows are silently dropped at ``traffic_generator/tasks.py:547``.
    2. ``flow_proto_not_on_source`` (error) — a flow uses a protocol that no
       device of the listed `source_types` declares (after alias resolution).
       The flow gets created but the source device's fingerprint has no
       identity for that protocol, so CV won't fingerprint it.
    3. ``flow_proto_not_on_target`` (error) — same as #2 for `target_types`.
    4. ``device_proto_orphaned`` (warning) — a device declares a protocol
       that no flow ever uses. Cosmetic; useful for cleanup.
    """
    issues: list[LintIssue] = []
    flows: list[dict[str, Any]] = template.get("flows", []) or []
    devices: list[dict[str, Any]] = template.get("devices", []) or []

    # Build {device_type: set(protocols declared on any device of that type)}
    type_to_protos: dict[str, set[str]] = {}
    for d in devices:
        dtype = d.get("type", "?")
        protos = d.get("protocols") or []
        type_to_protos.setdefault(dtype, set()).update(protos)

    # Track which device-declared protocols are referenced by some flow,
    # for the orphaned-protocol warning at the end.
    referenced_device_protos: set[tuple[str, str]] = set()  # (type, protocol)

    # Dedupe (code, protocol, type) so a single offending pattern repeated
    # across many flows produces one issue, not N copies.
    seen_keys: set[tuple[str, str, str]] = set()

    for idx, flow in enumerate(flows):
        proto = flow.get("protocol")
        if not proto:
            continue

        resolved = resolve_protocol(proto)

        # 1. Unresolvable protocols (silently dropped at runtime)
        if resolved not in _VALID_RUNTIME_PROTOCOLS:
            note = ""
            if proto in _NON_ENGINE_PROTOCOLS:
                note = (
                    f" — '{proto}' has no runtime engine; remove this flow "
                    f"or migrate it to the template's cloud_services config"
                )
            issues.append(
                LintIssue(
                    template_key=template_key,
                    severity="error",
                    code="flow_proto_unresolvable",
                    message=(
                        f"flow protocol {proto!r} resolves to {resolved!r}, "
                        f"which is not a valid ProtocolType — flow will be "
                        f"silently dropped at traffic_generator/tasks.py{note}"
                    ),
                    flow_index=idx,
                    detail={"protocol": proto, "resolved": resolved},
                )
            )
            continue  # don't run further checks on a dropped flow

        # 2 & 3. Source/target device-protocol declaration consistency
        for st in flow.get("source_types", []) or []:
            src_protos = type_to_protos.get(st, set())
            src_resolved = {resolve_protocol(p) for p in src_protos}
            if proto in src_protos or resolved in src_resolved:
                # Track which declared protocol satisfied this match
                for sp in src_protos:
                    if sp == proto or resolve_protocol(sp) == resolved:
                        referenced_device_protos.add((st, sp))
                continue

            key = ("flow_proto_not_on_source", proto, st)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            issues.append(
                LintIssue(
                    template_key=template_key,
                    severity="error",
                    code="flow_proto_not_on_source",
                    message=(
                        f"flow protocol {proto!r} not declared on any "
                        f"{st!r} device (declared: {sorted(src_protos)}). "
                        f"Add {proto!r} to that device's `protocols` list, "
                        f"or change the flow."
                    ),
                    flow_index=idx,
                    detail={"protocol": proto, "device_type": st,
                            "declared": sorted(src_protos)},
                )
            )

        for tt in flow.get("target_types", []) or []:
            tgt_protos = type_to_protos.get(tt, set())
            tgt_resolved = {resolve_protocol(p) for p in tgt_protos}
            if proto in tgt_protos or resolved in tgt_resolved:
                for tp in tgt_protos:
                    if tp == proto or resolve_protocol(tp) == resolved:
                        referenced_device_protos.add((tt, tp))
                continue

            key = ("flow_proto_not_on_target", proto, tt)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            issues.append(
                LintIssue(
                    template_key=template_key,
                    severity="error",
                    code="flow_proto_not_on_target",
                    message=(
                        f"flow protocol {proto!r} not declared on any "
                        f"{tt!r} device (declared: {sorted(tgt_protos)}). "
                        f"Add {proto!r} to that device's `protocols` list, "
                        f"or change the flow."
                    ),
                    flow_index=idx,
                    detail={"protocol": proto, "device_type": tt,
                            "declared": sorted(tgt_protos)},
                )
            )

    # 4. Orphaned device-protocol declarations (warning only)
    # Skip 'snmp' from this check — it is legitimately added to many devices
    # solely so the universal SNMP discovery guardrail (background noise
    # generator) can probe them. It does not need to participate in any flow.
    for dtype, protos in type_to_protos.items():
        for p in sorted(protos):
            if p == "snmp":
                continue
            if (dtype, p) not in referenced_device_protos:
                issues.append(
                    LintIssue(
                        template_key=template_key,
                        severity="warning",
                        code="device_proto_orphaned",
                        message=(
                            f"{dtype!r} declares protocol {p!r} but no flow "
                            f"uses it"
                        ),
                        detail={"device_type": dtype, "protocol": p},
                    )
                )

    return issues


def lint_all_templates() -> dict[str, list[LintIssue]]:
    """Run lint_template against every registered scenario template.

    Returns a dict of {f"{vertical}/{template_key}": [LintIssue, ...]} so the
    caller can produce a per-template report or roll up totals.
    """
    from app.scenario_templates import VERTICAL_TEMPLATES

    report: dict[str, list[LintIssue]] = {}
    for vertical, templates in VERTICAL_TEMPLATES.items():
        for tkey, tpl in templates.items():
            issues = lint_template(tkey, tpl)
            if issues:
                report[f"{vertical}/{tkey}"] = issues
    return report


def errors_only(issues: list[LintIssue]) -> list[LintIssue]:
    """Filter a list of LintIssue down to errors only."""
    return [i for i in issues if i.severity == "error"]
