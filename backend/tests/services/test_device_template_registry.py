# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Device template registry guards.

The registry used to keep the LAST template registered under an id, so a
duplicate silently replaced the earlier one. Six ids were duplicated; one of
them let a traffic_controller-typed stub replace the real Schneider TBox
MS-CPU32 RTU. These tests keep that from coming back.
"""

import collections

import pytest

from app.services.device_templates import DEVICE_TEMPLATES
from app.services.device_templates._registry import _register_all
from app.services.device_templates._types import DeviceTemplate


def _all_vendor_templates() -> list[tuple[str, DeviceTemplate]]:
    import importlib
    import pkgutil

    import app.services.device_templates.vendors as vendors_pkg

    out = []
    for info in pkgutil.iter_modules(vendors_pkg.__path__):
        mod = importlib.import_module(f"{vendors_pkg.__name__}.{info.name}")
        for t in getattr(mod, "TEMPLATES", []):
            out.append((info.name, t))
    return out


def test_no_duplicate_template_ids_across_vendor_modules():
    by_id = collections.defaultdict(list)
    for mod, t in _all_vendor_templates():
        by_id[t.id].append(mod)
    dupes = {k: v for k, v in by_id.items() if len(v) > 1}
    assert not dupes, f"duplicate template ids: {dupes}"


def test_every_vendor_template_is_registered():
    ids = {t.id for _, t in _all_vendor_templates()}
    assert ids == set(DEVICE_TEMPLATES)


def test_register_all_raises_on_duplicate(monkeypatch):
    import app.services.device_templates.vendors.transportation as transportation

    dup = transportation.TEMPLATES[0]
    monkeypatch.setattr(transportation, "TEMPLATES", [*transportation.TEMPLATES, dup])
    with pytest.raises(RuntimeError, match="Duplicate device template id"):
        _register_all()
