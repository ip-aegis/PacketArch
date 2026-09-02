# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Vendor-profile → catalog-fingerprint mapping for the generator.

A vendor profile (SIEMENS_SHOP, ROCKWELL_SHOP, ...) plus a role
(cell_controller, area_hmi, ...) deterministically picks a vendor +
fingerprint_model out of the catalog. The generator uses this to
materialize devices.

Multi-vendor profiles return a *list* of candidate (vendor,
fingerprint_model) pairs; the generator round-robins among them per
cell to spread vendors across the plant.
"""

from __future__ import annotations

from app.services.architecture.archetypes._base import VendorProfile


# (vendor, fingerprint_model) tuples. Order matters: first entry is
# the preferred default. Catalog must contain the fingerprint or the
# generator falls back to a vendor-only assignment with no model.
VendorPin = tuple[str, str]


# ---------------------------------------------------------------------------
# Per (profile, role) pinning
# ---------------------------------------------------------------------------

_PINNING: dict[tuple[VendorProfile, str], tuple[VendorPin, ...]] = {

    # ====================================================================
    # SIEMENS_SHOP
    # ====================================================================
    (VendorProfile.SIEMENS_SHOP, "cell_controller"): (
        ("siemens", "6ES7 517-3AP00-0AB0"),  # S7-1500 CPU 1517-3
        ("siemens", "6ES7 516-3AN02-0AB0"),
        ("siemens", "6ES7 511-1AK02-0AB0"),
    ),
    (VendorProfile.SIEMENS_SHOP, "safety_controller"): (
        ("siemens", "6ES7 516-3FN01-0AB0"),  # F-CPU
    ),
    (VendorProfile.SIEMENS_SHOP, "area_hmi"): (
        ("siemens", "6AV2 124-0MC01-0AX0"),  # KTP1200 Comfort
    ),
    (VendorProfile.SIEMENS_SHOP, "vfd"): (
        ("siemens", "6SL3210-1KE21-7UF1"),  # Sinamics G120
        ("siemens", "6SL3210-1PE21-1UL0"),  # Sinamics G120C
        ("siemens", "6SL3130-7TE25-5AA3"),  # Sinamics S120 line module
        ("siemens", "G120"),
    ),
    (VendorProfile.SIEMENS_SHOP, "servo"): (
        ("siemens", "6SL3130-7TE25-5AA3"),  # Sinamics S120
    ),
    (VendorProfile.SIEMENS_SHOP, "distributed_io"): (
        ("siemens", "6ES7 155-6AU01-0BN0"),  # ET 200SP
        ("siemens", "6ES7 155-5AA01-0AB0"),  # ET 200SP, alternate head
        ("siemens", "ET 200MP IM155-5 PN"),
    ),
    (VendorProfile.SIEMENS_SHOP, "engineering_workstation"): (
        ("siemens", "TIA Portal"),
    ),
    (VendorProfile.SIEMENS_SHOP, "scada_primary"): (
        ("siemens", "WinCC Professional"),
    ),
    (VendorProfile.SIEMENS_SHOP, "scada_standby"): (
        ("siemens", "WinCC Professional"),
    ),
    (VendorProfile.SIEMENS_SHOP, "wcs_controller"): (
        ("siemens", "6ES7 517-3AP00-0AB0"),
    ),
    (VendorProfile.SIEMENS_SHOP, "conveyor_controller"): (
        ("siemens", "6ES7 511-1AK02-0AB0"),
    ),
    (VendorProfile.SIEMENS_SHOP, "robot_controller"): (
        ("kuka", "KR C4"),  # KUKA is the Siemens-shop default robot
    ),
    (VendorProfile.SIEMENS_SHOP, "cnc_controller"): (
        ("fanuc", "0i-TF Plus"),
    ),
    (VendorProfile.SIEMENS_SHOP, "vision_system"): (
        ("sick", "Inspector P631"),
    ),
    (VendorProfile.SIEMENS_SHOP, "barcode_scanner"): (
        ("sick", "CLV650-0120"),
    ),

    # ====================================================================
    # ROCKWELL_SHOP
    # ====================================================================
    (VendorProfile.ROCKWELL_SHOP, "cell_controller"): (
        ("rockwell", "1756-L85E"),
        ("rockwell", "1756-L73"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "safety_controller"): (
        ("rockwell", "1756-L83ES"),  # GuardLogix
    ),
    (VendorProfile.ROCKWELL_SHOP, "area_hmi"): (
        ("rockwell", "2711P-T15C22D9P"),
        ("rockwell", "2711P-T10C22D9P"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "vfd"): (
        ("rockwell", "25B-D030N104"),   # PowerFlex 525
        ("rockwell", "PowerFlex 753"),
        ("rockwell", "20F-D052N103"),   # PowerFlex 753 frame
        ("rockwell", "PowerFlex 755"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "servo"): (
        ("rockwell", "25B-D030N104"),  # use VFD model as approximation
    ),
    (VendorProfile.ROCKWELL_SHOP, "distributed_io"): (
        ("rockwell", "1734-AENT"),
        ("rockwell", "5094-AEN2TR"),
    ),
    # Studio 5000 / FactoryTalk View SE are Windows applications. The
    # catalog doesn't carry the application skin separately — pin to
    # Windows host fingerprint that DOES exist.
    (VendorProfile.ROCKWELL_SHOP, "engineering_workstation"): (
        ("rockwell", "Studio 5000 Logix Designer 36"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "scada_primary"): (
        ("rockwell", "FactoryTalk View SE Station 14"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "scada_standby"): (
        ("rockwell", "FactoryTalk View SE Station 14"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "wcs_controller"): (
        ("rockwell", "1756-L73"),
        ("rockwell", "1756-L85E"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "conveyor_controller"): (
        ("rockwell", "1756-L73"),
        ("rockwell", "1769-L33ER"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "robot_controller"): (
        # Fanuc is the dominant robot in Rockwell-shop automotive lines.
        ("fanuc", "R-30iB Plus"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "cnc_controller"): (
        ("fanuc", "0i-TF Plus"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "vision_system"): (
        ("cognex", "In-Sight 7802"),
    ),
    (VendorProfile.ROCKWELL_SHOP, "barcode_scanner"): (
        ("cognex", "DataMan 280"),
    ),

    # ====================================================================
    # SCHNEIDER_SHOP
    # ====================================================================
    (VendorProfile.SCHNEIDER_SHOP, "cell_controller"): (
        ("schneider", "BMEP586040"),
        ("schneider", "BMXP3420302"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "area_hmi"): (
        ("schneider", "HMIGTO5310"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "vfd"): (
        ("schneider", "ATV930D15N4"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "distributed_io"): (
        ("schneider", "STBNIP2311"),
    ),

    # ====================================================================
    # ABB_SHOP
    # ====================================================================
    (VendorProfile.ABB_SHOP, "cell_controller"): (
        ("abb", "PM590-ETH"),
        ("abb", "PM583-ETH"),
    ),
    (VendorProfile.ABB_SHOP, "area_hmi"): (
        ("abb", "CP620"),
    ),
    (VendorProfile.ABB_SHOP, "vfd"): (
        ("abb", "ACS880-01"),
    ),

    # ====================================================================
    # NOTE: SEL_PROTECTION pins are defined once, further below (the
    # "pin to actual catalog models" block). An earlier duplicate block
    # here was removed — it was silently overwritten by the later one.
    # ====================================================================
    # SCHNEIDER_SHOP (extended)
    # ====================================================================
    (VendorProfile.SCHNEIDER_SHOP, "safety_controller"): (
        ("schneider", "TM5CSLC100FS"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "engineering_workstation"): (
        ("schneider", "EcoStruxure Control Expert 16"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "scada_primary"): (
        ("schneider", "Geo SCADA Expert 2022"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "scada_standby"): (
        ("schneider", "Geo SCADA Expert 2022"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "servo"): (
        ("schneider", "LXM32MD18M2"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "field_instrument"): (
        ("emerson", "3051S"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "valve_actuator"): (
        ("emerson", "DVC6200"),
        ("rotork", "IQ3 Pro"),      # electric actuator, integrated Ethernet
    ),
    (VendorProfile.SCHNEIDER_SHOP, "wcs_controller"): (
        ("schneider", "BMEP586040"),
    ),
    (VendorProfile.SCHNEIDER_SHOP, "conveyor_controller"): (
        ("schneider", "BMXP3420302"),
    ),

    # ====================================================================
    # ABB_SHOP (extended)
    # ====================================================================
    (VendorProfile.ABB_SHOP, "engineering_workstation"): (
        ("abb", "800xA Operator Workplace 6.1.1"),
    ),
    (VendorProfile.ABB_SHOP, "scada_primary"): (
        ("abb", "800xA Operator Workplace 6.1.1"),
    ),
    (VendorProfile.ABB_SHOP, "scada_standby"): (
        ("abb", "800xA Operator Workplace 6.1.1"),
    ),
    (VendorProfile.ABB_SHOP, "distributed_io"): (
        ("abb", "CI501"),
    ),
    (VendorProfile.ABB_SHOP, "field_instrument"): (
        ("emerson", "3051S"),
    ),
    (VendorProfile.ABB_SHOP, "valve_actuator"): (
        ("emerson", "DVC6200"),
        ("rotork", "IQ3 Pro"),      # electric actuator, integrated Ethernet
    ),
    (VendorProfile.ABB_SHOP, "safety_controller"): (
        # ABB doesn't have a dedicated safety PLC in catalog. Use a
        # Rockwell GuardLogix — cip_safety + ethernet_ip is the cleanest
        # cross-vendor SIS-to-robot path (vs Honeywell Safety Manager
        # which is modbus-only and doesn't talk to Fanuc/KUKA robots).
        ("rockwell", "1756-L83ES"),
    ),
    (VendorProfile.ABB_SHOP, "servo"): (
        ("abb", "ACS880-01"),
    ),
    (VendorProfile.ABB_SHOP, "wcs_controller"): (
        ("abb", "PM590-ETH"),
    ),
    (VendorProfile.ABB_SHOP, "conveyor_controller"): (
        ("abb", "PM590-ETH"),
    ),

    # ====================================================================
    # DCS profiles — pinned to catalog models that actually exist.
    # ====================================================================
    (VendorProfile.DCS_EMERSON, "dcs_controller"): (
        ("emerson", "MD Plus"),  # DeltaV controller
        ("emerson", "S-series"),  # Ovation controller
    ),
    (VendorProfile.DCS_EMERSON, "scada_primary"): (
        ("emerson", "Continuous Historian"),  # closest catalog stand-in
    ),
    (VendorProfile.DCS_EMERSON, "process_historian"): (
        ("emerson", "Continuous Historian"),
    ),
    (VendorProfile.DCS_EMERSON, "engineering_workstation"): (
        ("emerson", "Continuous Historian"),  # DeltaV ProPlus on Windows
    ),
    (VendorProfile.DCS_EMERSON, "safety_controller"): (
        ("honeywell", "Safety Manager"),  # speaks modbus_tcp like MD Plus
    ),
    (VendorProfile.DCS_EMERSON, "field_instrument"): (
        ("emerson", "3051S"),
        ("emerson", "5700"),
        ("yokogawa", "EJA530A"),
        ("endress_hauser", "Promag 400"),
    ),
    (VendorProfile.DCS_EMERSON, "valve_actuator"): (
        ("emerson", "DVC6200"),
        ("rotork", "IQ3 Pro"),      # electric actuator, integrated Ethernet
    ),
    # Up to 15 drives in one scenario. Third-party drives under a DCS are
    # normal — this pin was already cross-vendor, so it is widened, not
    # re-pointed.
    (VendorProfile.DCS_EMERSON, "vfd"): (
        ("rockwell", "25B-D030N104"),
        ("abb", "ACS580"),
        ("schneider", "ATV630D15N4"),
        ("siemens", "G120"),
    ),
    (VendorProfile.DCS_EMERSON, "area_hmi"): (
        # DCS operator station — Continuous Historian is a Windows host
        # in DeltaV speaking modbus+snmp, suitable as area_hmi stand-in.
        ("emerson", "Continuous Historian"),
    ),
    (VendorProfile.DCS_EMERSON, "distributed_io"): (
        ("schneider", "STBNIP2311"),
        ("honeywell", "Series C I/O"),
    ),
    (VendorProfile.DCS_EMERSON, "cell_switch"): (
        ("cisco", "IE-4000-8GT4G-E"),
        ("cisco", "IE-3300-8T2S"),
        ("cisco", "IE-3500-8T3S-E"),
    ),

    (VendorProfile.DCS_HONEYWELL, "dcs_controller"): (
        ("honeywell", "C300"),
        ("honeywell", "C200"),
    ),
    (VendorProfile.DCS_HONEYWELL, "scada_primary"): (
        ("honeywell", "Experion Server"),
    ),
    (VendorProfile.DCS_HONEYWELL, "engineering_workstation"): (
        ("honeywell", "Experion Station"),
    ),
    (VendorProfile.DCS_HONEYWELL, "safety_controller"): (
        ("honeywell", "Safety Manager"),
    ),
    (VendorProfile.DCS_HONEYWELL, "distributed_io"): (
        ("honeywell", "Series C I/O"),
    ),
    # NOTE: the catalog contains no Honeywell transmitters, so the previous
    # single "STT850" pin resolved to no device template — the instrument got a
    # model string with no fingerprint behind it. Pinning real instrument
    # vendors fixes both that and the merge problem; a Honeywell-DCS plant with
    # Emerson and Yokogawa instruments on it is entirely ordinary.
    (VendorProfile.DCS_HONEYWELL, "field_instrument"): (
        ("emerson", "3051S"),
        ("yokogawa", "EJA530A"),
        ("emerson", "5700"),
        ("endress_hauser", "Promag 400"),
    ),
    # Was ("honeywell", "STT850") — an STT850 is a Honeywell TEMPERATURE
    # transmitter, not a valve actuator, and it is absent from the device
    # catalog, so the pin resolved to no fingerprint at all. Real actuators
    # instead.
    (VendorProfile.DCS_HONEYWELL, "valve_actuator"): (
        ("emerson", "DVC6200"),
        ("rotork", "IQ3 Pro"),
    ),
    # Up to 20 drives in one scenario. Third-party drives under a DCS are
    # normal — this pin was already cross-vendor, so it is widened, not
    # re-pointed.
    (VendorProfile.DCS_HONEYWELL, "vfd"): (
        ("rockwell", "25B-D030N104"),
        ("abb", "ACS580"),
        ("schneider", "ATV630D15N4"),
        ("siemens", "G120"),
    ),
    (VendorProfile.DCS_HONEYWELL, "cell_switch"): (
        ("cisco", "IE-4000-8GT4G-E"),
        ("cisco", "IE-3300-8T2S"),
        ("cisco", "IE-3500-8T3S-E"),
    ),
    (VendorProfile.DCS_HONEYWELL, "cell_controller"): (
        ("schneider", "BMEP586040"),  # utility-zone PLC; modbus
    ),
    (VendorProfile.DCS_HONEYWELL, "area_hmi"): (
        # Experion Station is the per-unit operator console — speaks
        # modbus_tcp natively to C300 controllers.
        ("honeywell", "Experion Station"),
    ),
    (VendorProfile.DCS_EMERSON, "cell_controller"): (  # noqa: E501 — keep grouped
        ("schneider", "BMEP586040"),
    ),
    (VendorProfile.DCS_YOKOGAWA, "cell_controller"): (
        ("schneider", "BMEP586040"),
    ),
    (VendorProfile.DCS_ABB, "cell_controller"): (
        ("abb", "PM590-ETH"),
    ),

    (VendorProfile.DCS_YOKOGAWA, "dcs_controller"): (
        ("yokogawa", "AFV10D"),  # FCS field control station
        ("yokogawa", "SSC60D"),  # safety controller capable
    ),
    (VendorProfile.DCS_YOKOGAWA, "scada_primary"): (
        ("yokogawa", "HIS"),  # Human Interface Station
    ),
    (VendorProfile.DCS_YOKOGAWA, "engineering_workstation"): (
        ("yokogawa", "EWS"),  # Engineering Work Station
    ),
    (VendorProfile.DCS_YOKOGAWA, "safety_controller"): (
        ("yokogawa", "SSC60D"),
    ),
    (VendorProfile.DCS_YOKOGAWA, "field_instrument"): (
        ("yokogawa", "EJA530A"),
        ("yokogawa", "FLXA402"),
    ),
    # Was pinned to a Yokogawa EJA530A, which is a PRESSURE TRANSMITTER, not a
    # valve actuator — the same mis-assignment class as the Honeywell STT850
    # entry. 18 of these appear in yokogawa_refinery_unit.
    (VendorProfile.DCS_YOKOGAWA, "valve_actuator"): (
        ("emerson", "DVC6200"),
        ("rotork", "IQ3 Pro"),
    ),
    # Up to 12 drives in one scenario. Third-party drives under a DCS are
    # normal — this pin was already cross-vendor, so it is widened, not
    # re-pointed.
    (VendorProfile.DCS_YOKOGAWA, "vfd"): (
        ("rockwell", "25B-D030N104"),
        ("abb", "ACS580"),
        ("schneider", "ATV630D15N4"),
        ("siemens", "G120"),
    ),
    (VendorProfile.DCS_YOKOGAWA, "distributed_io"): (
        ("schneider", "STBNIP2311"),
    ),
    (VendorProfile.DCS_YOKOGAWA, "cell_switch"): (
        ("cisco", "IE-4000-8GT4G-E"),
        ("cisco", "IE-3300-8T2S"),
        ("cisco", "IE-3500-8T3S-E"),
    ),
    (VendorProfile.DCS_YOKOGAWA, "area_hmi"): (
        # HIS is the Centum Human Interface Station — same fingerprint
        # as scada_primary; doubles as per-unit operator console.
        ("yokogawa", "HIS"),
    ),

    (VendorProfile.DCS_ABB, "dcs_controller"): (
        ("abb", "PM590-ETH"),  # AC500 stand-in for AC800M
    ),
    (VendorProfile.DCS_ABB, "scada_primary"): (
        ("abb", "800xA Operator Workplace 6.1.1"),
    ),
    (VendorProfile.DCS_ABB, "engineering_workstation"): (
        ("abb", "800xA Operator Workplace 6.1.1"),
    ),
    (VendorProfile.DCS_ABB, "field_instrument"): (
        ("emerson", "3051S"),
    ),
    (VendorProfile.DCS_ABB, "valve_actuator"): (
        ("emerson", "DVC6200"),
    ),
    (VendorProfile.DCS_ABB, "vfd"): (
        ("abb", "ACS880-01"),
    ),
    (VendorProfile.DCS_ABB, "distributed_io"): (
        ("abb", "CI501"),
    ),
    (VendorProfile.DCS_ABB, "cell_switch"): (
        ("cisco", "IE-4000-8GT4G-E"),
    ),
    (VendorProfile.DCS_ABB, "safety_controller"): (
        ("honeywell", "Safety Manager"),
    ),
    (VendorProfile.DCS_ABB, "area_hmi"): (
        # ABB operator console stand-in — modbus-speaking historian.
        ("emerson", "Continuous Historian"),
    ),

    # ====================================================================
    # MIXED_FIELD (water utility) — uses real catalog models
    # ====================================================================
    # The existing M340 pin is kept FIRST so instance 0 of every existing
    # scenario keeps its fingerprint; the appended entries are purpose-built
    # utility RTUs (T300 and SCADAPack are Schneider's water-telemetry line,
    # RTU560 is ABB's), which is both more diverse and more accurate for a
    # remote pump station.
    (VendorProfile.MIXED_FIELD, "field_rtu"): (
        ("schneider", "BMXP3420302"),
        ("schneider", "T300"),
        ("abb", "RTU560"),
        ("schneider", "SCADAPack 350"),
    ),
    (VendorProfile.MIXED_FIELD, "aggregator_rtu"): (
        ("sel", "SEL-3530"),  # RTAC, exists in catalog
    ),
    (VendorProfile.MIXED_FIELD, "scada_primary"): (
        ("schneider", "Geo SCADA Expert 2022"),
    ),
    (VendorProfile.MIXED_FIELD, "engineering_workstation"): (
        ("schneider", "EcoStruxure Control Expert 16"),
    ),
    # 10-16 drives per water/pipeline scenario; same merge problem as above.
    # ABB and Schneider are both ordinary choices in a municipal utility.
    (VendorProfile.MIXED_FIELD, "vfd"): (
        ("schneider", "ATV930D15N4"),
        ("abb", "ACS580"),
        ("schneider", "ATV630D15N4"),
        ("abb", "ACS880-01"),
    ),
    # Round-robin across several real transmitters/flow meters rather than one
    # model. A water scenario emits 15-24 field instruments; with a single pin
    # they are fingerprint-identical, and Cyber Vision MERGES
    # identically-fingerprinted devices — so the asset count in CV silently
    # disagrees with the scenario. All four match the role's own description
    # ("smart transmitter — temperature, pressure, level, flow"); analysers are
    # a different role and are deliberately not pulled in here.
    (VendorProfile.MIXED_FIELD, "field_instrument"): (
        ("emerson", "3051S"),                    # pressure / DP
        ("yokogawa", "EJA530A"),                 # pressure
        ("endress_hauser", "Promag 400"),        # electromagnetic flow
        ("emerson", "5700"),                     # coriolis flow
    ),
    (VendorProfile.MIXED_FIELD, "valve_actuator"): (
        ("emerson", "DVC6200"),
        ("rotork", "IQ3 Pro"),      # electric actuator, integrated Ethernet
    ),
    # The energy_substation archetype is reused by solar_bess_microgrid
    # under the MIXED_FIELD profile, so we need protection-class pins
    # here too — without them every protection_relay landed with no
    # fingerprint, no MAC, and the agent rejected the scenario.
    (VendorProfile.MIXED_FIELD, "protection_relay"): (
        ("sel", "SEL-751"),
        ("sel", "SEL-451"),
    ),
    (VendorProfile.MIXED_FIELD, "local_historian"): (
        ("ge", "Proficy Historian"),
    ),

    # ====================================================================
    # SCADAPACK — uses ScadaPack-class catalog entries (none exist; fall
    # back to Schneider M340 + SEL-3530 stand-ins).
    # ====================================================================
    (VendorProfile.SCADAPACK, "field_rtu"): (
        ("schneider", "BMXP3420302"),
    ),
    (VendorProfile.SCADAPACK, "aggregator_rtu"): (
        ("sel", "SEL-3530"),
    ),
    (VendorProfile.SCADAPACK, "scada_primary"): (
        ("schneider", "Geo SCADA Expert 2022"),
    ),

    # ====================================================================
    # SEL_PROTECTION — pin to actual catalog models (SEL-751, SEL-3530,
    # SEL-451).
    # ====================================================================
    (VendorProfile.SEL_PROTECTION, "protection_relay"): (
        ("sel", "SEL-751"),
        ("sel", "SEL-451"),
        ("sel", "SEL-487E"),
    ),
    (VendorProfile.SEL_PROTECTION, "aggregator_rtu"): (
        ("sel", "SEL-3530"),
    ),
    (VendorProfile.SEL_PROTECTION, "engineering_workstation"): (
        ("sel", "SEL-5030 acSELerator"),
    ),
    (VendorProfile.SEL_PROTECTION, "scada_primary"): (
        ("sel", "SEL-5030 acSELerator"),
    ),
    (VendorProfile.SEL_PROTECTION, "local_historian"): (
        ("ge", "Proficy Historian"),
    ),

    # ====================================================================
    # BAS_TRIDIUM — Tridium catalog has 0 entries; use Honeywell JACE 8000
    # (a Tridium-licensed Honeywell branding that DOES exist in catalog).
    # ====================================================================
    (VendorProfile.BAS_TRIDIUM, "bms_field_controller"): (
        ("honeywell", "JACE 8000"),
    ),
    (VendorProfile.BAS_TRIDIUM, "scada_primary"): (
        ("honeywell", "JACE 8000"),
    ),
    (VendorProfile.BAS_TRIDIUM, "engineering_workstation"): (
        ("honeywell", "JACE 8000"),
    ),
    (VendorProfile.BAS_TRIDIUM, "field_instrument"): (
        ("honeywell", "JACE 8000"),  # stand-in for BACnet sensors
    ),
    # Up to 19 HVAC drives per scenario. ABB's ACS580 and Schneider's ATV
    # range are both ordinary in a plant room.
    (VendorProfile.BAS_TRIDIUM, "vfd"): (
        ("schneider", "ATV930D15N4"),
        ("abb", "ACS580"),
        ("schneider", "ATV630D15N4"),
    ),
    # Was ("honeywell", "JACE 8000") — a JACE is a BACnet SUPERVISORY
    # CONTROLLER, not a valve. Belimo's Energy Valve is an actual BAS control
    # valve with native BACnet/IP, so this is a correctness fix as much as a
    # diversity one.
    (VendorProfile.BAS_TRIDIUM, "valve_actuator"): (
        ("belimo", "EV065F+BAC"),
        ("emerson", "DVC6200"),
    ),

    # ====================================================================
    # ATMS_NTCIP — Econolite catalog has Cobalt ATC.
    # ====================================================================
    (VendorProfile.ATMS_NTCIP, "traffic_controller"): (
        ("econolite", "Cobalt ATC"),
        ("econolite", "ASC/3-2100 Cobalt"),
    ),
    (VendorProfile.ATMS_NTCIP, "cabinet_controller"): (
        ("econolite", "Cobalt ATC"),
    ),
    (VendorProfile.ATMS_NTCIP, "scada_primary"): (
        ("schneider", "Geo SCADA Expert 2022"),
    ),
    (VendorProfile.ATMS_NTCIP, "engineering_workstation"): (
        ("schneider", "EcoStruxure Control Expert 16"),
    ),
    # ITS field equipment — all present in catalog.
    (VendorProfile.ATMS_NTCIP, "cctv_camera"): (
        ("axis", "P1455-LE"),
        ("axis", "P1448-LE"),
        ("pelco", "Spectra Enhanced"),
        ("bosch", "MIC IP 7100i"),
    ),
    (VendorProfile.ATMS_NTCIP, "ptz_camera"): (
        ("pelco", "SD436-PG-E1"),
        ("bosch", "MIC IP 7100i"),
    ),
    (VendorProfile.ATMS_NTCIP, "anpr_camera"): (
        ("hikvision", "DS-2CD7A26G0/P"),
    ),
    (VendorProfile.ATMS_NTCIP, "dms_sign"): (
        ("daktronics", "Venus 7000"),
        ("daktronics", "Venus 1500"),
    ),
    (VendorProfile.ATMS_NTCIP, "toll_rsu"): (
        ("q-free", "RSU 5000"),
    ),
    (VendorProfile.ATMS_NTCIP, "toll_lane_controller"): (
        ("kapsch", "TCS 2000"),
    ),
    (VendorProfile.ATMS_NTCIP, "rwis_station"): (
        ("vaisala", "RWIS500"),
    ),

    # ====================================================================
    # DCIM_CISCO — facility-side OT, Cisco-class network gear + Windows
    # DCIM hosts.
    # ====================================================================
    (VendorProfile.DCIM_CISCO, "scada_primary"): (
        ("rockwell", "FactoryTalk View SE Station 14"),
    ),
    (VendorProfile.DCIM_CISCO, "engineering_workstation"): (
        ("rockwell", "Studio 5000 Logix Designer 36"),
    ),
    (VendorProfile.DCIM_CISCO, "vfd"): (
        ("schneider", "ATV930D15N4"),  # stand-in for smart PDU
    ),
    (VendorProfile.DCIM_CISCO, "field_instrument"): (
        ("emerson", "3051S"),
    ),
    (VendorProfile.DCIM_CISCO, "bms_field_controller"): (
        ("honeywell", "JACE 8000"),
    ),
    (VendorProfile.DCIM_CISCO, "cell_controller"): (
        ("rockwell", "1756-L73"),
    ),

    # ====================================================================
    # MULTI_VENDOR (manufacturing) — round-robin per cell
    # ====================================================================
    (VendorProfile.MULTI_VENDOR, "cell_controller"): (
        ("siemens", "6ES7 517-3AP00-0AB0"),
        ("rockwell", "1756-L85E"),
        ("schneider", "BMEP586040"),
        ("abb", "PM590-ETH"),
    ),
    (VendorProfile.MULTI_VENDOR, "area_hmi"): (
        ("siemens", "6AV2 124-0MC01-0AX0"),
        ("rockwell", "2711P-T15C22D9P"),
        ("schneider", "HMIGTO5310"),
        ("abb", "CP620"),
    ),
    (VendorProfile.MULTI_VENDOR, "vfd"): (
        ("siemens", "6SL3210-1KE21-7UF1"),
        ("rockwell", "25B-D030N104"),
        ("schneider", "ATV930D15N4"),
        ("abb", "ACS880-01"),
    ),
    (VendorProfile.MULTI_VENDOR, "distributed_io"): (
        ("siemens", "6ES7 155-6AU01-0BN0"),
        ("rockwell", "1734-AENT"),
    ),
    (VendorProfile.MULTI_VENDOR, "engineering_workstation"): (
        ("siemens", "TIA Portal"),
        ("rockwell", "Studio 5000 Logix Designer 36"),
        ("schneider", "EcoStruxure Control Expert 16"),
    ),
    (VendorProfile.MULTI_VENDOR, "scada_primary"): (
        ("siemens", "WinCC Professional"),
        ("rockwell", "FactoryTalk View SE Station 14"),
        ("schneider", "Geo SCADA Expert 2022"),
    ),
    (VendorProfile.MULTI_VENDOR, "scada_standby"): (
        ("siemens", "WinCC Professional"),
        ("rockwell", "FactoryTalk View SE Station 14"),
        ("schneider", "Geo SCADA Expert 2022"),
    ),
    (VendorProfile.MULTI_VENDOR, "wcs_controller"): (
        ("rockwell", "1756-L73"),
        ("siemens", "6ES7 517-3AP00-0AB0"),
    ),
    (VendorProfile.MULTI_VENDOR, "conveyor_controller"): (
        ("rockwell", "1756-L73"),
        ("siemens", "6ES7 511-1AK02-0AB0"),
    ),
    (VendorProfile.MULTI_VENDOR, "safety_controller"): (
        ("rockwell", "1756-L83ES"),
        ("siemens", "6ES7 516-3FN01-0AB0"),
    ),
    (VendorProfile.MULTI_VENDOR, "servo"): (
        ("rockwell", "25B-D030N104"),
        ("siemens", "6SL3130-7TE25-5AA3"),
    ),
    (VendorProfile.MULTI_VENDOR, "robot_controller"): (
        ("fanuc", "R-30iB Plus"),
        ("kuka", "KR C4"),
    ),
    (VendorProfile.MULTI_VENDOR, "cnc_controller"): (
        ("fanuc", "0i-TF Plus"),
    ),
    (VendorProfile.MULTI_VENDOR, "vision_system"): (
        ("cognex", "In-Sight 7802"),
        ("sick", "Inspector P631"),
    ),
    (VendorProfile.MULTI_VENDOR, "barcode_scanner"): (
        ("cognex", "DataMan 280"),
        ("sick", "CLV650-0120"),
    ),
}


# ---------------------------------------------------------------------------
# Cross-profile fallbacks (independent of vendor shop)
# ---------------------------------------------------------------------------

# IDMZ + operations + network roles share fingerprints across vendor
# profiles (a jump server is a Windows server regardless of plant vendor).
_PROFILE_AGNOSTIC: dict[str, tuple[VendorPin, ...]] = {

    "jump_server": (
        ("microsoft", "Jump Server 2016 (Vulnerable)"),
        ("microsoft", "Jump Server 2019"),
    ),
    "remote_access_gateway": (
        ("hms", "Flexy 205"),
    ),
    "patch_staging_server": (
        ("microsoft", "WSUS Server 2019"),
        ("microsoft", "WSUS Server 2022"),
        ("microsoft", "MECM Server 2022"),
    ),
    "av_management_server": (
        ("microsoft", "Defender for Endpoint 2022"),
        ("broadcom", "Symantec Endpoint Protection Manager 14"),
    ),
    "historian_replica": (
        ("ge", "Proficy Historian"),
    ),
    "process_historian": (
        ("ge", "Proficy Historian"),
    ),
    "opc_ua_aggregator": (
        ("kepware", "KEPServerEX"),
    ),
    "nms_server": (
        ("paessler", "PRTG Network Monitor 24"),
    ),
    "asset_management_server": (
        ("lansweeper", "Lansweeper 11"),
    ),
    "mes_server": (
        ("siemens", "Opcenter Execution Discrete 2406"),
    ),
    "dns_ntp_relay": (
        ("microsoft", "Jump Server 2019"),
    ),
    "email_relay": (
        ("microsoft", "Jump Server 2019"),
    ),
    "reverse_proxy": (
        ("f5 networks", "BIG-IP i2800"),
    ),
    "core_switch": (
        ("cisco", "IE-4000-8GT4G-E"),
        ("cisco", "Stratix 5700"),
    ),
    # An access layer built entirely from one switch SKU is not how a plant
    # grows, and identical fingerprints merge in Cyber Vision. IE-4000 stays
    # first (existing scenarios keep instance 0) with current-generation IE
    # models appended.
    "cell_switch": (
        ("cisco", "IE-4000-8GT4G-E"),
        ("cisco", "IE-3300-8T2S"),
        ("cisco", "IE-3500-8T3S-E"),
    ),
    "bay_switch": (
        ("cisco", "IE-4000-8GT4G-E"),
        ("cisco", "IE-3300-8T2S"),
    ),
    "wan_edge_router": (
        ("cisco", "IE-4000-8GT4G-E"),
    ),

    # Safe stand-ins for roles that should "just work" regardless of
    # the active vendor profile. Without these, archetypes that include
    # these roles under a profile that lacks an explicit pin produce
    # devices with no fingerprint / no MAC — and the agent then
    # rejects the deployed scenario silently. Better to land a Windows-
    # host stand-in than to fail.
    "scada_standby": (
        ("rockwell", "FactoryTalk View SE Station 14"),
    ),
    "alarm_event_server": (
        ("aveva", "InTouch Alarm Server 2023"),
    ),
    "batch_server": (
        ("aveva", "OSIsoft PI Server 2018"),
    ),
    "batch_controller": (
        ("rockwell", "1756-L73"),
    ),
    "protection_relay": (
        ("sel", "SEL-751"),
        ("sel", "SEL-451"),
    ),
    "local_historian": (
        ("ge", "Proficy Historian"),
    ),
    "aggregator_rtu": (
        ("sel", "SEL-3530"),
    ),
    "field_rtu": (
        ("schneider", "BMXP3420302"),
    ),
    "engineering_workstation": (
        ("rockwell", "Studio 5000 Logix Designer 36"),
    ),
    "vfd": (
        ("rockwell", "25B-D030N104"),
    ),
    "servo": (
        ("rockwell", "25B-D030N104"),
    ),
    "distributed_io": (
        ("rockwell", "1734-AENT"),
    ),
    "field_instrument": (
        ("emerson", "3051S"),
    ),
    "valve_actuator": (
        ("emerson", "DVC6200"),
    ),
    "cell_controller": (
        ("rockwell", "1756-L73"),
    ),
    "dcs_controller": (
        # Profile-agnostic stand-in for any vendor profile that doesn't
        # have its own DCS pin (used by semiconductor fab + battery
        # plant under MULTI_VENDOR / SIEMENS_SHOP / ROCKWELL_SHOP).
        ("honeywell", "C300"),
        ("emerson", "MD Plus"),
    ),
    "cctv_camera": (
        ("axis", "P1455-LE"),
    ),
    "ptz_camera": (
        ("pelco", "SD436-PG-E1"),
    ),
    "anpr_camera": (
        ("hikvision", "DS-2CD7A26G0/P"),
    ),
    "dms_sign": (
        ("daktronics", "Venus 7000"),
    ),
    "toll_rsu": (
        ("q-free", "RSU 5000"),
    ),
    "toll_lane_controller": (
        ("kapsch", "TCS 2000"),
    ),
    "rwis_station": (
        ("vaisala", "RWIS500"),
    ),
    # BAS terminal-unit roles (Phase 9 vertical audit).
    "vav_controller": (
        ("honeywell", "PUB6438S"),
        ("distech controls", "ECY-VAV"),
    ),
    "ahu_controller": (
        ("delta controls", "enteliBUS Manager"),
    ),
    "chiller_controller": (
        ("carel", "pCO5+"),
        ("honeywell", "XL Web"),
    ),
    "room_controller": (
        ("siemens", "DXR2.E12"),
    ),
    # DCIM power / cooling.
    "pdu": (
        ("schneider", "Rack PDU"),
    ),
    "ups_unit": (
        ("schneider", "Galaxy VM"),
    ),
    "crac_unit": (
        ("schneider", "InRow DX"),
    ),
    # Logistics — robotics, identification, vision.
    "agv": (
        ("mir", "MiR250"),
        ("mir", "MiR500"),
        ("kuka", "KMP 600"),
    ),
    "fleet_manager": (
        ("mir", "MiR Fleet"),
        ("kuka", "KUKA.FleetManager"),
    ),
    "barcode_scanner": (
        ("cognex", "DataMan 280"),
        ("sick", "CLV650-0120"),
    ),
    "rfid_reader": (
        ("impinj", "Speedway R420"),
        ("zebra", "FX9600"),
    ),
    "vision_system": (
        ("cognex", "In-Sight 7802"),
        ("sick", "Inspector P631"),
    ),
    # Process analyzers / meters.
    "analyzer": (
        ("yokogawa", "GC8000"),
        ("yokogawa", "TDLS8000"),
        ("endress+hauser", "CM442"),
    ),
    "flow_meter": (
        ("emerson", "5700"),
        ("endress+hauser", "Promag 400"),
    ),
    # Energy revenue metering.
    "power_meter": (
        ("schneider", "PM8000"),
        ("schneider", "ION8650"),
    ),
    "robot_controller": (
        ("fanuc", "R-30iB Plus"),
        ("kuka", "KR C4"),
    ),
    "cnc_controller": (
        ("fanuc", "0i-TF Plus"),
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_pin_candidates(
    vendor_profile: VendorProfile, role_id: str,
) -> tuple[VendorPin, ...]:
    """Return the candidate (vendor, fingerprint_model) pairs for a
    given (vendor_profile, role_id).

    Resolution order:
      1. Explicit (profile, role) pin from _PINNING.
      2. Profile-agnostic pin from _PROFILE_AGNOSTIC (IDMZ, network,
         vendor-neutral operations).
      3. Empty tuple — caller must handle (e.g. by emitting a vendor-
         only device with no fingerprint_model).
    """
    explicit = _PINNING.get((vendor_profile, role_id))
    if explicit:
        return explicit
    return _PROFILE_AGNOSTIC.get(role_id, ())


def round_robin_pick(
    candidates: tuple[VendorPin, ...], index: int,
) -> VendorPin | None:
    """Pick the candidate at `index % len(candidates)`. Returns None if
    no candidates."""
    if not candidates:
        return None
    return candidates[index % len(candidates)]
