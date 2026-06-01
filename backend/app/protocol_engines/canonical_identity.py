# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Single source of truth for on-wire device identity.

Every simulated device gets ONE canonical hostname, emitted *identically* by
every traffic path that advertises a name — LLDP, PROFINET-DCP NameOfStation,
SNMP sysName, S7 PLC name — subject only to each protocol's hard charset/length
limits (applied by the per-protocol sanitizers below). This is what lets Cisco
Cyber Vision reconcile a device's L2 (LLDP) sighting with its L3 host into a
single component instead of splitting it in two.

Real OT gear presents a consistent station name across LLDP / PROFINET / SNMP;
the canonical hostname mirrors that. The descriptive ``device.name`` (canvas/UI
label) is intentionally NOT emitted on the wire — only the canonical hostname is.

Companion derivations (vendor-OUI MAC, CIP/PROFINET vendor-id) also live here so
they too come from the canonical source-of-truth tables in ``vendor_oui.py``
rather than stale per-template values.

All functions are pure and deterministic: the same inputs always yield the same
output, so the PCAP path and the live agent emit byte-identical identities for
the same ``(device_id, scenario_id)`` — preserving PCAP/live lockstep.
"""

from __future__ import annotations

import re

from app.protocol_engines.serial_number_generator import device_hash
from app.protocol_engines.vendor_oui import (
    DEFAULT_OUI,
    ODVA_VENDOR_IDS,
    PROFINET_VENDOR_IDS,
    VENDOR_OUI_PREFIXES,
    normalize_vendor,
)

# Hard protocol field limits (characters).
PROFINET_NAME_MAX = 240  # IEC 61158 DCP NameOfStation total length
SNMP_SYS_NAME_MAX = 255  # SNMPv2-MIB sysName DisplayString
S7_PLC_NAME_MAX = 24  # S7 SZL component/module name field (24-byte slot)
# CIP Identity Object Product Name is a SHORT_STRING (1-byte length -> max 255).
# 64 comfortably holds every canonical hostname while staying tidy; the field
# must hold the FULL hostname (not truncated) so it equals the LLDP/SNMP name
# and Cyber Vision merges the EtherNet/IP component with the L2/SNMP component.
CIP_PRODUCT_NAME_MAX = 64
MODBUS_PRODUCT_NAME_MAX = 64  # Modbus FC43 object value (kept aligned with CIP)

_INVALID_HOST_CHARS = re.compile(r"[^a-z0-9-]+")
_MULTI_DASH = re.compile(r"-+")


def canonical_hostname(name: str | None, *, fallback: str = "device") -> str:
    """Reduce any device name to the one canonical on-wire hostname.

    Lowercase, ``[a-z0-9-]`` only (``_``/space/illegal chars collapse to ``-``),
    no leading/trailing or consecutive hyphens, must start with a letter
    (PROFINET DCP forbids a leading digit), clamped to ``PROFINET_NAME_MAX``.

    Because the result is already a strict lowercase hostname within every
    protocol's charset, each protocol can emit it verbatim — that byte-identity
    across protocols is the whole point.

    Args:
        name: Source device name (the site-coherent ``device.name``).
        fallback: Used when ``name`` is empty/unusable.

    Returns:
        Canonical hostname, e.g. ``"dtw-mfg-1-paint-plc-01"``.
    """
    base = (name or "").strip().lower()
    base = base.replace("_", "-")
    base = _INVALID_HOST_CHARS.sub("-", base)
    base = _MULTI_DASH.sub("-", base).strip("-")
    if not base:
        base = fallback
    # PROFINET: a name label must not start with a digit.
    if base[0].isdigit():
        base = f"d-{base}"
    if len(base) > PROFINET_NAME_MAX:
        base = base[:PROFINET_NAME_MAX].rstrip("-")
    return base


def _clamp(host: str, limit: int) -> str:
    """Truncate to ``limit`` chars without leaving a trailing hyphen."""
    if len(host) <= limit:
        return host
    return host[:limit].rstrip("-")


def profinet_station_name(host: str) -> str:
    """PROFINET DCP NameOfStation — canonical hostname clamped to the field."""
    return _clamp(host, PROFINET_NAME_MAX)


def snmp_sys_name(host: str) -> str:
    """SNMP sysName — canonical hostname (DisplayString, clamped)."""
    return _clamp(host, SNMP_SYS_NAME_MAX)


def s7_plc_name(host: str) -> str:
    """S7 PLC/module name — canonical hostname clamped to the SZL slot width."""
    return _clamp(host, S7_PLC_NAME_MAX)


def bacnet_object_name(host: str) -> str:
    """BACnet object name — canonical hostname (CharacterString, unbounded)."""
    return host


def ethernet_ip_product_name(host: str) -> str:
    """CIP Identity Object Product Name = the canonical hostname.

    Cyber Vision labels the EtherNet/IP component by this field and only merges
    it with the L2/SNMP (hostname) component when the two match — so this MUST
    be the canonical hostname, not the catalog model. The hardware model stays
    identifiable via the CIP product_code / device_type / vendor_id attributes.
    """
    return _clamp(host, CIP_PRODUCT_NAME_MAX)


def modbus_product_name(host: str) -> str:
    """Modbus FC43 product name = the canonical hostname.

    Same rationale as CIP: CV labels the Modbus component by this, so it carries
    the hostname for component merging. The catalog model stays in the Modbus
    ``model_name`` field.
    """
    return _clamp(host, MODBUS_PRODUCT_NAME_MAX)


def canonical_mac(
    device_id: str,
    scenario_id: str | None = None,
    vendor: str | None = None,
    oui_prefixes: list[str] | None = None,
) -> str:
    """Deterministic, vendor-appropriate MAC for a device.

    Seeded by the same ``device_hash(device_id, scenario_id)`` used for serials
    and unique identifiers, so the MAC is stable across deployments AND across
    any fingerprint re-resolution (re-derives the identical value). The OUI is
    chosen vendor-appropriately from the fingerprint's ``oui_prefixes`` when
    available, else from the canonical ``VENDOR_OUI_PREFIXES`` table.

    Args:
        device_id: Unique device identifier.
        scenario_id: Scenario identifier (defaults to "global" in device_hash).
        vendor: Vendor name (used when ``oui_prefixes`` not supplied).
        oui_prefixes: Vendor OUI prefixes from the fingerprint (highest priority).

    Returns:
        Lowercase MAC, e.g. ``"00:1b:1b:78:a8:e8"``.
    """
    h = device_hash(device_id, scenario_id)

    ouis = oui_prefixes or []
    if not ouis and vendor:
        ouis = VENDOR_OUI_PREFIXES.get(normalize_vendor(vendor), [])
    oui = ouis[h[5] % len(ouis)] if ouis else DEFAULT_OUI

    oui = oui.lower().replace("-", ":")
    last = ":".join(f"{b:02x}" for b in h[2:5])
    return f"{oui}:{last}"


def cip_vendor_id(vendor: str | None, fallback: int | None = None) -> int | None:
    """Resolve the ODVA (EtherNet/IP) vendor id from the canonical table.

    Always prefers the source-of-truth table over any (often stale) template
    value. Returns ``fallback`` when the vendor isn't in the table.
    """
    if vendor:
        vid = ODVA_VENDOR_IDS.get(normalize_vendor(vendor))
        if vid is not None:
            return vid
    return fallback


def profinet_vendor_id(vendor: str | None, fallback: int | None = None) -> int | None:
    """Resolve the PROFINET vendor id from the canonical table.

    Prefers the source-of-truth table over any stale template value. Returns
    ``fallback`` when the vendor isn't in the table.
    """
    if vendor:
        vid = PROFINET_VENDOR_IDS.get(normalize_vendor(vendor))
        if vid is not None:
            return vid
    return fallback
