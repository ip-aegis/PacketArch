# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario diff service for comparing two scenario version snapshots."""

from __future__ import annotations

from typing import Any


# Fields to ignore in diffs (position changes are noise from drag events)
_IGNORE_FIELDS = {"position"}

# Fields that contain large nested objects - summarize instead of deep diff
_SUMMARY_FIELDS = {
    "vendorFingerprint",
    "vendor_fingerprint",
    "vulnerabilityOverride",
}


def compute_definition_diff(
    base_def: dict[str, Any],
    compare_def: dict[str, Any],
    base_meta: dict[str, Any] | None = None,
    compare_meta: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Compute structured diff between two scenario definitions.

    Args:
        base_def: The base (older) definition JSONB.
        compare_def: The compare (newer) definition JSONB.
        base_meta: Optional base metadata (name, description, total_duration_ms).
        compare_meta: Optional compare metadata.

    Returns:
        Tuple of (changes list, summary dict with counts of added/removed/modified).
    """
    changes: list[dict[str, Any]] = []

    # Diff each Record<id, object> category
    for category in ("devices", "flows", "zones", "conduits"):
        base_items: dict[str, Any] = base_def.get(category, {})
        compare_items: dict[str, Any] = compare_def.get(category, {})

        base_ids = set(base_items.keys())
        compare_ids = set(compare_items.keys())

        # Added
        for item_id in sorted(compare_ids - base_ids):
            item = compare_items[item_id]
            changes.append(
                {
                    "category": category,
                    "change_type": "added",
                    "item_id": item_id,
                    "item_name": item.get("name", item_id),
                    "details": None,
                }
            )

        # Removed
        for item_id in sorted(base_ids - compare_ids):
            item = base_items[item_id]
            changes.append(
                {
                    "category": category,
                    "change_type": "removed",
                    "item_id": item_id,
                    "item_name": item.get("name", item_id),
                    "details": None,
                }
            )

        # Modified
        for item_id in sorted(base_ids & compare_ids):
            base_item = base_items[item_id]
            compare_item = compare_items[item_id]

            if base_item != compare_item:
                changed_fields = _diff_dict_fields(base_item, compare_item)
                if changed_fields:
                    changes.append(
                        {
                            "category": category,
                            "change_type": "modified",
                            "item_id": item_id,
                            "item_name": compare_item.get("name", item_id),
                            "details": changed_fields,
                        }
                    )

    # Diff phases (array, keyed by phase id)
    base_phases = {p.get("id", str(i)): p for i, p in enumerate(base_def.get("phases", []))}
    compare_phases = {
        p.get("id", str(i)): p for i, p in enumerate(compare_def.get("phases", []))
    }

    base_phase_ids = set(base_phases.keys())
    compare_phase_ids = set(compare_phases.keys())

    for phase_id in sorted(compare_phase_ids - base_phase_ids):
        phase = compare_phases[phase_id]
        changes.append(
            {
                "category": "phases",
                "change_type": "added",
                "item_id": phase_id,
                "item_name": phase.get("displayName", phase.get("name", phase_id)),
                "details": None,
            }
        )

    for phase_id in sorted(base_phase_ids - compare_phase_ids):
        phase = base_phases[phase_id]
        changes.append(
            {
                "category": "phases",
                "change_type": "removed",
                "item_id": phase_id,
                "item_name": phase.get("displayName", phase.get("name", phase_id)),
                "details": None,
            }
        )

    for phase_id in sorted(base_phase_ids & compare_phase_ids):
        base_phase = base_phases[phase_id]
        compare_phase = compare_phases[phase_id]
        if base_phase != compare_phase:
            changed_fields = _diff_dict_fields(base_phase, compare_phase)
            if changed_fields:
                changes.append(
                    {
                        "category": "phases",
                        "change_type": "modified",
                        "item_id": phase_id,
                        "item_name": compare_phase.get(
                            "displayName", compare_phase.get("name", phase_id)
                        ),
                        "details": changed_fields,
                    }
                )

    # Diff metadata
    if base_meta and compare_meta:
        for field in ("name", "description", "total_duration_ms"):
            old_val = base_meta.get(field)
            new_val = compare_meta.get(field)
            if old_val != new_val:
                changes.append(
                    {
                        "category": "metadata",
                        "change_type": "modified",
                        "item_id": field,
                        "item_name": field,
                        "details": {"old": old_val, "new": new_val},
                    }
                )

    # Build summary
    summary: dict[str, int] = {"added": 0, "removed": 0, "modified": 0}
    for change in changes:
        ct = change["change_type"]
        if ct in summary:
            summary[ct] += 1

    return changes, summary


def _diff_dict_fields(
    base: dict[str, Any], compare: dict[str, Any]
) -> dict[str, Any]:
    """Compare two dicts and return changed fields.

    Returns a dict of field_name -> {"old": ..., "new": ...}.
    Ignores position changes and summarizes large nested objects.
    """
    changed: dict[str, Any] = {}
    all_keys = set(base.keys()) | set(compare.keys())

    for key in sorted(all_keys):
        if key in _IGNORE_FIELDS:
            continue

        old_val = base.get(key)
        new_val = compare.get(key)

        if old_val != new_val:
            if key in _SUMMARY_FIELDS:
                # Summarize large objects
                changed[key] = {"old": "[object]", "new": "[modified]"}
            elif isinstance(old_val, dict) and isinstance(new_val, dict):
                # For nested dicts, show which sub-keys changed
                sub_changed = []
                sub_all = set(old_val.keys()) | set(new_val.keys())
                for sk in sorted(sub_all):
                    if old_val.get(sk) != new_val.get(sk):
                        sub_changed.append(sk)
                if sub_changed:
                    changed[key] = {
                        "old": "[object]",
                        "new": "[modified]",
                        "changed_subfields": sub_changed,
                    }
            elif isinstance(old_val, list) and isinstance(new_val, list):
                changed[key] = {
                    "old": f"[{len(old_val)} items]",
                    "new": f"[{len(new_val)} items]",
                }
            else:
                changed[key] = {"old": old_val, "new": new_val}

    return changed
