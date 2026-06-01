# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for the single canonical device identity module.

These lock the core invariant behind the Cyber Vision "two components per MAC"
fix: every name-bearing protocol emits the SAME canonical hostname, the MAC is
deterministic + vendor-appropriate, and vendor IDs come from the SoT tables.
"""

from app.protocol_engines import canonical_identity as ci
from app.protocol_engines.unique_identifier_generator import UniqueIdentifierGenerator


class TestCanonicalHostname:
    def test_lowercases_and_hyphenates(self):
        assert ci.canonical_hostname("DTW_MFG_Paint_Booth_Main_PLC_01") == (
            "dtw-mfg-paint-booth-main-plc-01"
        )

    def test_strips_illegal_chars_and_collapses_dashes(self):
        assert ci.canonical_hostname("Cell #3 / Robot (KUKA)") == "cell-3-robot-kuka"

    def test_idempotent_fixpoint(self):
        once = ci.canonical_hostname("DTW_MFG_Paint_Booth_Main_PLC_01")
        assert ci.canonical_hostname(once) == once

    def test_no_leading_digit(self):
        # PROFINET DCP forbids a leading digit on a name label.
        assert ci.canonical_hostname("3M-Press-01")[0].isalpha()

    def test_empty_falls_back(self):
        assert ci.canonical_hostname("") == "device"
        assert ci.canonical_hostname(None) == "device"

    def test_clamped_to_profinet_max(self):
        long_name = "x" * 500
        assert len(ci.canonical_hostname(long_name)) <= ci.PROFINET_NAME_MAX


class TestCrossProtocolConsistency:
    """Every name-bearing protocol reduces to the SAME canonical stem."""

    NAME = "DTW_MFG_Paint_Booth_Main_PLC_01"

    def test_all_protocols_share_one_stem(self):
        host = ci.canonical_hostname(self.NAME)
        kw = dict(device_id="d1", scenario_id="s1", device_name=self.NAME)
        snmp = UniqueIdentifierGenerator.generate_snmp_sys_name(**kw)
        profinet = UniqueIdentifierGenerator.generate_profinet_station_name(**kw)
        bacnet = UniqueIdentifierGenerator.generate_bacnet_object_name(**kw)
        s7 = UniqueIdentifierGenerator.generate_s7_plc_name(**kw)

        assert snmp == host
        assert profinet == host
        assert bacnet == host
        # S7 has a short field; it must be a prefix of the canonical stem,
        # never a differently-cased / differently-mangled string.
        assert host.startswith(s7)

    def test_no_hash_suffix(self):
        # Per design: clean hostnames, no -abcd disambiguation suffix.
        name = UniqueIdentifierGenerator.generate_snmp_sys_name(
            device_id="d1", scenario_id="s1", device_name="Line-1-PLC-01"
        )
        assert name == "line-1-plc-01"

    def test_determinism(self):
        a = UniqueIdentifierGenerator.generate_profinet_station_name(
            device_id="d1", scenario_id="s1", device_name=self.NAME
        )
        b = UniqueIdentifierGenerator.generate_profinet_station_name(
            device_id="d1", scenario_id="s1", device_name=self.NAME
        )
        assert a == b


class TestProtocolFieldLimits:
    def test_s7_plc_name_clamped(self):
        host = ci.canonical_hostname("a" * 100)
        assert len(ci.s7_plc_name(host)) <= ci.S7_PLC_NAME_MAX

    def test_product_names_are_canonical_hostname(self):
        # CV labels the CIP/Modbus component by product_name, so it MUST carry
        # the canonical hostname (matching LLDP/SNMP) for CV to merge components.
        host = ci.canonical_hostname("CNC_Cell_Main_Controller")
        assert ci.ethernet_ip_product_name(host) == host
        assert ci.modbus_product_name(host) == host

    def test_product_name_clamped_to_field(self):
        assert len(ci.ethernet_ip_product_name("x" * 80)) <= ci.CIP_PRODUCT_NAME_MAX


class TestCanonicalMac:
    def test_deterministic(self):
        a = ci.canonical_mac("dev1", "scenA", vendor="siemens")
        b = ci.canonical_mac("dev1", "scenA", vendor="siemens")
        assert a == b

    def test_vendor_oui_prefix(self):
        # Siemens OUIs from the SoT table.
        mac = ci.canonical_mac("dev1", "scenA", vendor="siemens")
        oui = mac[:8].upper()
        from app.protocol_engines.vendor_oui import VENDOR_OUI_PREFIXES

        assert oui in [p.upper() for p in VENDOR_OUI_PREFIXES["siemens"]]

    def test_fingerprint_oui_prefixes_take_priority(self):
        mac = ci.canonical_mac(
            "dev1", "scenA", vendor="siemens", oui_prefixes=["00:1B:1B"]
        )
        assert mac.startswith("00:1b:1b")

    def test_distinct_devices_differ(self):
        a = ci.canonical_mac("dev1", "scenA", vendor="siemens")
        b = ci.canonical_mac("dev2", "scenA", vendor="siemens")
        assert a != b

    def test_scenario_scoped(self):
        a = ci.canonical_mac("dev1", "scenA", vendor="siemens")
        b = ci.canonical_mac("dev1", "scenB", vendor="siemens")
        assert a != b

    def test_unknown_vendor_uses_default_oui(self):
        from app.protocol_engines.vendor_oui import DEFAULT_OUI

        mac = ci.canonical_mac("dev1", "scenA", vendor="not-a-real-vendor")
        assert mac.startswith(DEFAULT_OUI.lower())


class TestVendorIdSoT:
    def test_cip_vendor_id_from_table(self):
        assert ci.cip_vendor_id("Schneider Electric") == 243
        assert ci.cip_vendor_id("siemens") == 145
        assert ci.cip_vendor_id("rockwell") == 1

    def test_cip_vendor_id_fallback_for_unknown(self):
        assert ci.cip_vendor_id("mystery-vendor", fallback=99) == 99

    def test_profinet_vendor_id_from_table(self):
        assert ci.profinet_vendor_id("siemens") == 0x002A
        assert ci.profinet_vendor_id("schneider") == 0x0095
