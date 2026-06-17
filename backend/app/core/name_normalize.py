# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Display-name normalization helpers.

LLM-generated zone/device names get title-cased, which mangles OT acronyms
(``OT DMZ`` -> ``Ot Dmz``). ``normalize_acronyms`` restores the correct casing
without touching anything else — it only upper-cases a token that is *currently*
title-case AND whose upper form is a known acronym, so model numbers, normal
words, and already-correct text are left exactly as-is.
"""
from __future__ import annotations

import re

# OT/ICS/IT acronyms that should always render upper-case in display names.
ACRONYMS: frozenset[str] = frozenset({
    "OT", "IT", "DMZ", "IDMZ", "ICS", "SCADA", "DCS", "PLC", "HMI", "RTU",
    "IED", "VFD", "MCC", "UPS", "HVAC", "SIS", "ESD", "BMS", "MES", "ERP",
    "CNC", "AGV", "RFID", "CCTV", "ANPR", "ETC", "DMS", "TMC", "LAN", "WAN",
    "VLAN", "WLAN", "UV", "WFI", "TFF", "SIL", "GC", "CIP", "ITS", "HV", "MV",
    "LV", "PV", "VPN", "DNP3", "MQTT", "OPC", "SNMP", "GPS", "ESS", "BESS",
    "PMU", "PDC", "RTAC", "AVR", "GIS", "AIS", "FACTS",
})

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _fix(match: re.Match[str]) -> str:
    tok = match.group(0)
    # Only repair title-case tokens (Ot, Dmz) whose upper form is an acronym.
    # Leave ALL-CAPS, all-lower, and mixed model strings (BMEP586040) untouched.
    if tok.upper() in ACRONYMS and tok != tok.upper() and tok[:1].isupper():
        return tok.upper()
    return tok


def normalize_acronyms(name: str | None) -> str:
    """Upper-case mangled OT acronyms in a display name; otherwise return as-is."""
    if not name:
        return name or ""
    return _TOKEN.sub(_fix, name)
