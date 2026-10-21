# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Firmware pins and the version token in sys_descr."""

from app.services.device_templates import get_fingerprint_from_template


def test_windows_sysdescr_keeps_its_os_version_under_an_application_firmware():
    # Centracs 2.0 on Windows Server must not report "Windows Version 2.0".
    fp = get_fingerprint_from_template("econolite/centracs/atms-server")
    assert "Windows Version 6.3 (Build 17763" in fp["snmp_identity"]["sys_descr"]


def test_device_sysdescr_still_follows_the_pinned_firmware():
    fp = get_fingerprint_from_template("cisco/ie9320/24p4x", firmware_version="17.9.3")
    assert "17.9.3" in fp["snmp_identity"]["sys_descr"]
