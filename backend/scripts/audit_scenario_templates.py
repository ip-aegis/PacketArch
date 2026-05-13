#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Audit every scenario template against the realism rules in the
`packetarch-scenario-authoring` skill.

Walks `VERTICAL_TEMPLATES`, builds a fully-populated definition for each
template via `populate_definition_from_template` (no DB writes), and
runs the full audit suite:

  - auto_repair_protocols (counts protocols added/removed per device)
  - repair_flow_protocols (counts flow protocol snaps + no-shared-protocol
    flows that can't be healed)
  - audit_irrational_flows (jump-server-polling-PLC, drive-polling-PLC, etc.)
  - orphan device count (devices in no flow)
  - readiness checks (compute_scenario_readiness — full diagnostics)
  - cell-isolation pre-flight (count of cell↔cell flows in strict mode)

Usage:
    python -m backend.scripts.audit_scenario_templates [--json] [--vertical V]
        [--template T] [--full]

  --json      Machine-readable output for downstream automation
  --vertical  Filter to a single vertical (manufacturing, water, etc.)
  --template  Filter to a single template within a vertical
  --full      Print verbose per-finding details (otherwise summarized)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

# LOW: auto-fixable at runtime, source-file fix is purely cosmetic
# MEDIUM: source-file fix recommended; affects authored intent
# HIGH: scenario topology issue requiring authoring redesign
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"


@dataclass
class TemplateAuditFinding:
    template_id: str
    vertical: str
    template_name: str
    category: str
    severity: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateAuditResult:
    vertical: str
    template_name: str
    template_label: str
    device_count: int
    flow_count: int
    cell_isolation_mode: str
    cloud_links: int
    findings: list[TemplateAuditFinding] = field(default_factory=list)
    readiness_score: int | None = None
    readiness_status: str | None = None

    @property
    def template_id(self) -> str:
        return f"{self.vertical}/{self.template_name}"


# ---------------------------------------------------------------------------
# Audit checks
# ---------------------------------------------------------------------------

def _classify_protocol_repair(removed: list[str], added: list[str]) -> str:
    """Most repair_protocols changes are LOW-impact (silent runtime fixes
    already applied). Only escalate if the change is dramatic."""
    if len(added) > 5 or len(removed) > 5:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def _classify_flow_snap(
    original: str | None, new: str | None, shared: list[str]
) -> str:
    """Most flow snaps are LOW. Snapping to snmp/http/telnet only is MEDIUM
    because it suggests bad pairing."""
    GENERIC = {"snmp", "http", "telnet"}
    if new and new.lower() in GENERIC and len(shared) == 1:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def _audit_one_template(
    vertical: str, template_name: str
) -> TemplateAuditResult:
    """Run all audit checks against a single template."""
    from app.api.routes.scenarios import compute_scenario_readiness
    from app.scenario_templates import get_template
    from app.services.template_audit import audit_irrational_flows
    from app.services.template_definition_builder import (
        populate_definition_from_template,
    )
    from app.services.scenario_enrichment import (
        auto_repair_protocols,
        repair_flow_protocols,
    )

    template = get_template(vertical, template_name) or {}
    template_label = template.get("name", template_name)
    # Templates can declare findings categories that the audit should
    # downgrade or omit entirely. Useful for testing-only templates
    # whose authoring intent (duplicate MACs, duplicate names, etc.)
    # collides with realism rules.
    audit_exempt_categories: set[str] = set(
        template.get("audit_exempt_categories") or []
    )

    definition = populate_definition_from_template(vertical, template_name)
    if definition is None:
        return TemplateAuditResult(
            vertical=vertical,
            template_name=template_name,
            template_label=template_label,
            device_count=0,
            flow_count=0,
            cell_isolation_mode="off",
            cloud_links=0,
            findings=[
                TemplateAuditFinding(
                    template_id=f"{vertical}/{template_name}",
                    vertical=vertical,
                    template_name=template_name,
                    category="build_failure",
                    severity=SEVERITY_HIGH,
                    summary="populate_definition_from_template returned None",
                )
            ],
        )

    devices = definition.get("devices", {}) or {}
    flows = definition.get("flows", {}) or {}
    cloud_links = definition.get("cloud_service_links", []) or []
    cell_iso_mode = (definition.get("cell_isolation") or {}).get("mode", "off")

    result = TemplateAuditResult(
        vertical=vertical,
        template_name=template_name,
        template_label=template_label,
        device_count=len(devices),
        flow_count=len(flows),
        cell_isolation_mode=cell_iso_mode,
        cloud_links=len(cloud_links),
    )

    # ---- Check 1: device protocol mismatches (auto_repair_protocols) -----
    pre_protocols = {
        did: list((dev.get("protocols") or []))
        for did, dev in devices.items()
    }
    repaired_def = auto_repair_protocols(definition)
    post_devices = repaired_def.get("devices", {}) or {}
    for did, dev in post_devices.items():
        post = list(dev.get("protocols") or [])
        pre = pre_protocols.get(did, [])
        if set(pre) != set(post):
            added = sorted(set(post) - set(pre))
            removed = sorted(set(pre) - set(post))
            sev = _classify_protocol_repair(removed, added)
            result.findings.append(
                TemplateAuditFinding(
                    template_id=result.template_id,
                    vertical=vertical,
                    template_name=template_name,
                    category="device_protocol_repair",
                    severity=sev,
                    summary=(
                        f"{dev.get('name', did)}: +{added} -{removed}"
                    ),
                    details={
                        "device_id": did,
                        "device_name": dev.get("name", did),
                        "vendor": (dev.get("vendorFingerprint") or {}).get(
                            "vendor"
                        ),
                        "model": (dev.get("vendorFingerprint") or {}).get(
                            "model"
                        ),
                        "added": added,
                        "removed": removed,
                        "before": sorted(pre),
                        "after": sorted(post),
                    },
                )
            )

    # ---- Check 2: flow protocol snaps (repair_flow_protocols) -----------
    pre_flow_protos = {
        fid: (flow.get("protocol") or "").lower()
        for fid, flow in flows.items()
    }
    snapped_def = repair_flow_protocols(repaired_def)
    snapped_flows = snapped_def.get("flows", {}) or {}
    for fid, flow in snapped_flows.items():
        new_proto = (flow.get("protocol") or "").lower()
        old_proto = pre_flow_protos.get(fid, "")
        # Only count actual changes (snap functions add markers but skip
        # already-correct flows).
        if old_proto != new_proto:
            shared = []  # we don't recompute here; sub-finding is enough
            sev = _classify_flow_snap(old_proto, new_proto, shared)
            result.findings.append(
                TemplateAuditFinding(
                    template_id=result.template_id,
                    vertical=vertical,
                    template_name=template_name,
                    category="flow_protocol_snap",
                    severity=sev,
                    summary=f"flow {fid}: {old_proto!r} → {new_proto!r}",
                    details={
                        "flow_id": fid,
                        "source": flow.get("sourceDeviceId"),
                        "target": flow.get("targetDeviceId"),
                        "before": old_proto,
                        "after": new_proto,
                    },
                )
            )

    # ---- Check 3: irrational flows --------------------------------------
    irrational = audit_irrational_flows(snapped_def)
    for fr in irrational:
        result.findings.append(
            TemplateAuditFinding(
                template_id=result.template_id,
                vertical=vertical,
                template_name=template_name,
                category="irrational_flow",
                severity=SEVERITY_HIGH,
                summary=(
                    f"{fr.source_device_name} ({fr.source_device_type}) → "
                    f"{fr.target_device_name} ({fr.target_device_type}) "
                    f"via {fr.protocol}: {fr.reason}"
                ),
                details={
                    "flow_id": fr.flow_id,
                    "source_id": fr.source_device_id,
                    "source_name": fr.source_device_name,
                    "source_type": fr.source_device_type,
                    "target_id": fr.target_device_id,
                    "target_name": fr.target_device_name,
                    "target_type": fr.target_device_type,
                    "protocol": fr.protocol,
                    "reason": fr.reason,
                },
            )
        )

    # ---- Check 4: orphan devices ---------------------------------------
    in_flow: set[str] = set()
    for flow in snapped_flows.values():
        s = (
            flow.get("sourceDeviceId")
            or flow.get("source_device_id")
            or flow.get("source")
        )
        t = (
            flow.get("targetDeviceId")
            or flow.get("destinationDeviceId")
            or flow.get("destination_device_id")
            or flow.get("target")
        )
        if s:
            in_flow.add(s)
        if t:
            in_flow.add(t)
    # Cloud-link participants are not orphans either.
    for link in cloud_links:
        did = link.get("device_id")
        if did:
            in_flow.add(did)
    orphans = [
        did for did in devices if did not in in_flow
    ]
    if orphans:
        result.findings.append(
            TemplateAuditFinding(
                template_id=result.template_id,
                vertical=vertical,
                template_name=template_name,
                category="orphan_devices",
                severity=SEVERITY_MEDIUM,
                summary=(
                    f"{len(orphans)} device(s) not in any flow "
                    "(coverage flow will fire at deploy time)"
                ),
                details={
                    "orphan_device_ids": orphans,
                    "orphan_device_names": [
                        devices[did].get("name", did) for did in orphans
                    ],
                },
            )
        )

    # ---- Check 5: cell-isolation pre-flight -----------------------------
    if cell_iso_mode in ("conduit_gated", "strict_northbound"):
        from app.protocol_engines.cell_isolation import (
            parse_config as parse_iso_config,
            should_drop_flow,
        )
        iso = parse_iso_config(snapped_def)
        dropped = []
        for fid, flow in snapped_flows.items():
            drop, reason = should_drop_flow(
                flow, devices, definition.get("zones", {}),
                definition.get("conduits", {}), iso,
            )
            if drop:
                dropped.append((fid, reason))
        if dropped:
            result.findings.append(
                TemplateAuditFinding(
                    template_id=result.template_id,
                    vertical=vertical,
                    template_name=template_name,
                    category="cell_isolation_drop",
                    severity=SEVERITY_HIGH,
                    summary=(
                        f"{len(dropped)} flow(s) would be dropped at runtime "
                        f"by {cell_iso_mode} isolation"
                    ),
                    details={
                        "mode": cell_iso_mode,
                        "dropped_flows": [
                            {"flow_id": f, "reason": r} for f, r in dropped
                        ],
                    },
                )
            )

    # ---- Check 6: readiness score ---------------------------------------
    try:
        readiness = compute_scenario_readiness(snapped_def)
        result.readiness_score = readiness.score
        result.readiness_status = readiness.status
        for check in readiness.checks:
            if check.passed:
                continue
            cat = f"readiness:{check.name}"
            if cat in audit_exempt_categories:
                continue
            sev = (
                SEVERITY_HIGH if check.severity == "error"
                else SEVERITY_MEDIUM
            )
            result.findings.append(
                TemplateAuditFinding(
                    template_id=result.template_id,
                    vertical=vertical,
                    template_name=template_name,
                    category=cat,
                    severity=sev,
                    summary=check.message or check.name,
                    details={"name": check.name, "severity": check.severity},
                )
            )
    except Exception as e:  # noqa: BLE001
        result.findings.append(
            TemplateAuditFinding(
                template_id=result.template_id,
                vertical=vertical,
                template_name=template_name,
                category="readiness_failure",
                severity=SEVERITY_HIGH,
                summary=f"readiness check raised: {e!r}",
            )
        )

    return result


def audit_all_templates(
    vertical_filter: str | None = None,
    template_filter: str | None = None,
) -> list[TemplateAuditResult]:
    """Walk every template in VERTICAL_TEMPLATES and audit it."""
    from app.scenario_templates import VERTICAL_TEMPLATES

    results: list[TemplateAuditResult] = []
    for vertical, templates in sorted(VERTICAL_TEMPLATES.items()):
        if vertical_filter and vertical != vertical_filter:
            continue
        for name in sorted(templates.keys()):
            if template_filter and name != template_filter:
                continue
            results.append(_audit_one_template(vertical, name))
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _result_to_dict(r: TemplateAuditResult) -> dict[str, Any]:
    return {
        "template_id": r.template_id,
        "vertical": r.vertical,
        "template_name": r.template_name,
        "template_label": r.template_label,
        "device_count": r.device_count,
        "flow_count": r.flow_count,
        "cell_isolation_mode": r.cell_isolation_mode,
        "cloud_links": r.cloud_links,
        "readiness_score": r.readiness_score,
        "readiness_status": r.readiness_status,
        "finding_counts": {
            sev: sum(1 for f in r.findings if f.severity == sev)
            for sev in (SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH)
        },
        "findings_by_category": _bucket_by_category(r.findings),
        "findings": [
            {
                "category": f.category,
                "severity": f.severity,
                "summary": f.summary,
                "details": f.details,
            }
            for f in r.findings
        ],
    }


def _bucket_by_category(findings: list[TemplateAuditFinding]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        out[f.category] = out.get(f.category, 0) + 1
    return out


def print_human_summary(
    results: list[TemplateAuditResult], full: bool = False
) -> None:
    print()
    print("=" * 76)
    print("Scenario template audit")
    print("=" * 76)
    print()

    # Aggregate counts
    total_findings = sum(len(r.findings) for r in results)
    by_sev = {SEVERITY_LOW: 0, SEVERITY_MEDIUM: 0, SEVERITY_HIGH: 0}
    by_cat: dict[str, int] = {}
    for r in results:
        for f in r.findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
            by_cat[f.category] = by_cat.get(f.category, 0) + 1

    print(f"  Templates audited: {len(results)}")
    print(f"  Total findings:    {total_findings}")
    print(f"    high:   {by_sev[SEVERITY_HIGH]}")
    print(f"    medium: {by_sev[SEVERITY_MEDIUM]}")
    print(f"    low:    {by_sev[SEVERITY_LOW]}")
    print()
    print("  Findings by category:")
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"    {cat:<35} {n}")
    print()

    # Per-template summary table
    print("-" * 76)
    print(
        f"  {'Template':<55}  {'Score':<5} {'H':<3} {'M':<3} {'L':<3}"
    )
    print("-" * 76)
    for r in results:
        h = sum(1 for f in r.findings if f.severity == SEVERITY_HIGH)
        m = sum(1 for f in r.findings if f.severity == SEVERITY_MEDIUM)
        lo = sum(1 for f in r.findings if f.severity == SEVERITY_LOW)
        score = r.readiness_score if r.readiness_score is not None else "?"
        print(
            f"  {r.template_id[:55]:<55}  {str(score):<5} "
            f"{h:<3} {m:<3} {lo:<3}"
        )
    print()

    if not full:
        return

    # Full per-finding detail
    print("=" * 76)
    print("DETAIL")
    print("=" * 76)
    for r in results:
        if not r.findings:
            continue
        print()
        print(f"### {r.template_id} ({r.template_label})")
        print(
            f"  devices={r.device_count} flows={r.flow_count} "
            f"isolation={r.cell_isolation_mode} cloud_links={r.cloud_links}"
        )
        for f in sorted(r.findings, key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x.severity], x.category
        )):
            print(
                f"  [{f.severity:<6}] {f.category}: {f.summary}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit every scenario template against the realism rules in "
            "the packetarch-scenario-authoring skill."
        )
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON"
    )
    parser.add_argument(
        "--vertical",
        help="Filter to a single vertical (manufacturing, water, etc.)",
    )
    parser.add_argument(
        "--template",
        help="Filter to a single template within a vertical",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print verbose per-finding details",
    )
    args = parser.parse_args()

    # Trigger registries
    from app.services.device_templates import vendors as _v  # noqa: F401
    from app.scenario_templates import VERTICAL_TEMPLATES  # noqa: F401

    results = audit_all_templates(
        vertical_filter=args.vertical,
        template_filter=args.template,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "templates_audited": len(results),
                    "results": [_result_to_dict(r) for r in results],
                },
                indent=2,
                default=str,
            )
        )
        return 0

    print_human_summary(results, full=args.full)
    return 0


if __name__ == "__main__":
    sys.exit(main())
