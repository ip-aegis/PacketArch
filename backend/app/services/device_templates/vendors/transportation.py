# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Transportation / ITS device templates (Econolite, McCain, Daktronics, Wavetronix, FLIR, Q-Free, Kapsch, Axis, Hikvision, Pelco, Genetec, Cradlepoint, Sierra Wireless, SICK)."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="econolite/asc3/cobalt",
        vendor="Econolite",
        vendor_family="ASC/3",
        model="ASC/3-2100 Cobalt",
        model_name="ASC/3 Cobalt Traffic Controller",
        device_type="traffic_controller",
        description="Advanced traffic signal controller with NTCIP support",

        oui_prefixes=["00:04:81"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ECO{10NUM}",
            station_name_pattern="tsc-{location}-{seq}",
            vendor_short="ECO",
            model_short="ASC3",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.16",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V7.10",
                release_date=date(2022, 6, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V6.45",
                release_date=date(2020, 9, 20),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "ASC/3-2100 Cobalt Traffic Signal Controller V7.16",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",  # NTCIP
            "sys_contact": "traffic-ops@city.gov",
        },
    ),
    DeviceTemplate(
        id="econolite/cobalt/atc",
        vendor="Econolite",
        vendor_family="Cobalt",
        model="Cobalt ATC",
        model_name="Cobalt ATC Traffic Controller",
        device_type="traffic_controller",
        description="Advanced traffic signal controller with NTCIP support",

        oui_prefixes=["00:04:81"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ECO{10NUM}",
            station_name_pattern="tsc-{location}-{seq}",
            vendor_short="ECO",
            model_short="COBT",
        ),

        # Cobalt runs Econolite EOS (3.x). 3.2.23 is the fixed build named in
        # CISA ICSA-23-026-02 for CVE-2023-0451/0452 ("EOS versions prior to
        # 3.2.23"). 3.2.20 is an illustrative pre-fix 3.2.x build; its exact
        # build number is not published.
        firmware_variants=[
            FirmwareVariant(
                version="3.2.23",
                release_date=date(2023, 1, 26),
                is_latest=True,
                is_default=True,
                cves=[],
                population_weight=0.6,
            ),
            FirmwareVariant(
                version="3.2.20",
                release_date=date(2022, 6, 1),
                cves=["CVE-2023-0451", "CVE-2023-0452"],
                notes="Pre-3.2.23 EOS: unauthenticated READONLY file access and MD5 credential hashes (ICSA-23-026-02)",
                population_weight=0.4,
            ),
        ],

        snmp_identity={
            "sys_descr": "Econolite Cobalt ATC EOS 3.2.23",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
        },
    ),
    DeviceTemplate(
        id="mccain/2070/atc",
        vendor="McCain",
        vendor_family="2070",
        model="2070 ATC",
        model_name="2070 ATC Traffic Controller",
        device_type="traffic_controller",
        description="Type 2070 Advanced Transportation Controller",

        oui_prefixes=["10:10:B6"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 7.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="MC2070{8NUM}",
            station_name_pattern="tsc-{location}-{seq}",
            vendor_short="MCC",
            model_short="2070",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.2.0",
                release_date=date(2024, 2, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.0.0",
                release_date=date(2022, 7, 20),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "McCain 2070 ATC Traffic Signal Controller V3.2.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
        },
    ),
    DeviceTemplate(
        id="mccain/170e/controller",
        vendor="McCain",
        vendor_family="170E",
        model="170E",
        model_name="170E Traffic Controller",
        device_type="traffic_controller",
        description="Type 170E traffic signal controller",

        oui_prefixes=["10:10:B6"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 30.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="170E{6NUM}",
            station_name_pattern="tsc-{location}-{seq}",
            vendor_short="MCC",
            model_short="170E",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.5",
                release_date=date(2023, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "McCain 170E Traffic Signal Controller V2.5",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
        },
    ),
    DeviceTemplate(
        id="daktronics/vanguard/vx-2420",
        vendor="Daktronics",
        vendor_family="Vanguard",
        model="VX-2420",
        model_name="Vanguard VX-2420 Front-Access DMS",
        device_type="dms",
        description="Vanguard front-access dynamic message sign for lane control and compact messaging (NTCIP 1203)",

        oui_prefixes=["00:09:EC"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="VX24{8NUM}",
            station_name_pattern="dms-{location}-{seq}",
            vendor_short="DAK",
            model_short="VX2420",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.3.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V8.1.0",
                release_date=date(2022, 5, 20),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Daktronics Vanguard VX-2420 Dynamic Message Sign V8.3.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.3",
        },
    ),
    DeviceTemplate(
        id="daktronics/vanguard/vf-2020",
        vendor="Daktronics",
        vendor_family="Vanguard",
        model="VF-2020",
        model_name="Vanguard VF-2020 Walk-In DMS",
        device_type="dms",
        description="Vanguard walk-in full-matrix dynamic message sign (NTCIP 1203)",

        oui_prefixes=["00:09:EC"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="VF20{8NUM}",
            station_name_pattern="dms-{location}-{seq}",
            vendor_short="DAK",
            model_short="VF2020",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V12.1.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V11.5.0",
                release_date=date(2022, 8, 10),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Daktronics Vanguard VF-2020 Dynamic Message Sign V12.1.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.3",
        },
    ),
    DeviceTemplate(
        id="wavetronix/smartsensor/hd",
        vendor="Wavetronix",
        vendor_family="SmartSensor",
        model="SmartSensor HD",
        model_name="SmartSensor HD Radar Detector",
        device_type="radar_detector",
        description="High-definition radar vehicle detection sensor",

        oui_prefixes=["1C:C1:1A"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SSHD{10NUM}",
            station_name_pattern="det-{location}-{seq}",
            vendor_short="WVT",
            model_short="SSHD",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.5.0",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V7.2.0",
                release_date=date(2022, 6, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Wavetronix SmartSensor HD Radar Detector V7.5.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.4",  # NTCIP 1209 TSS (no vendor PEN)
        },
    ),
    DeviceTemplate(
        id="wavetronix/smartsensor/advance",
        vendor="Wavetronix",
        vendor_family="SmartSensor",
        model="SmartSensor Advance",
        model_name="SmartSensor Advance Vehicle Classifier",
        device_type="radar_detector",
        description="Advanced radar sensor with vehicle classification capability",

        oui_prefixes=["1C:C1:1A"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.5,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SSA{10NUM}",
            station_name_pattern="radar-adv-{location}-{seq}",
            vendor_short="WAV",
            model_short="SSA",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.5.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.2.0",
                release_date=date(2022, 7, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Wavetronix SmartSensor Advance Vehicle Classifier V4.5.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.4",  # NTCIP 1209 TSS (no vendor PEN)
        },
    ),
    DeviceTemplate(
        id="flir/trafione/sensor",
        vendor="FLIR",
        vendor_family="TrafiOne",
        model="TrafiOne",
        model_name="TrafiOne Thermal Sensor",
        device_type="thermal_sensor",
        description="Thermal imaging sensor for traffic detection",

        oui_prefixes=["00:13:56", "00:1B:D8", "00:40:7F"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 30.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TF1{10NUM}",
            station_name_pattern="therm-{location}-{seq}",
            vendor_short="FLR",
            model_short="TF1",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.8.0",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.5.0",
                release_date=date(2022, 7, 20),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "FLIR TrafiOne Thermal Traffic Sensor V2.8.0",
            "sys_object_id": "1.3.6.1.4.1.34674",  # IANA PEN 34674 = FLIR Systems
        },
    ),
    # ------------------------------------------------------------------
    # Tolling and V2X (2026-10-21). These replace "Kapsch TCS 2000" and
    # "Q-Free RSU 5000", which match no real product, and whose firmware
    # was invented. Sources: Kapsch's LSIORB technical proposal (Indiana
    # Finance Authority, 2014), Kapsch JANUS and RIS-9260 datasheets, NVD /
    # CVE records. Unpublished release dates are left empty.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="kapsch/tzc/toll-zone-controller",
        vendor="Kapsch",
        vendor_family="Toll Zone Controller",
        model="Toll Zone Controller",
        model_name="Kapsch TrafficCom Toll Zone Controller",
        device_type="toll_controller",
        description="AET toll zone (lane) controller: builds transactions from reader, camera and classifier events",
        oui_prefixes=["00:E0:6A"],  # IEEE: KAPSCH AG (the group registrant; Kapsch TrafficCom holds no block)
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 1.0,
            "max_ms": 60.0,
            "mean_ms": 8.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp"],
        instance_rules=InstanceGenerationRules(
            serial_format="KTZ{8NUM}",
            station_name_pattern="tzc-{location}-{seq}",
            vendor_short="KTC",
            model_short="TZC",
        ),
        firmware_variants=[
            # "Current release is version 1.2.0.3", released 26-Feb-2014 (LBJ /
            # NTE managed lanes). Later versions are not public.
            FirmwareVariant(version="1.2.0.3", release_date=date(2014, 2, 26), is_latest=True,
                            is_default=True, cves=[]),
        ],
        snmp_identity={
            "sys_descr": "Kapsch Toll Zone Controller 1.2.0.3",
            "sys_object_id": "1.3.6.1.4.1.13182",  # IANA PEN 13182 = kapsch TrafficCom AG
        },
    ),
    DeviceTemplate(
        id="kapsch/janus/mpr2.4",
        vendor="Kapsch",
        vendor_family="JANUS",
        model="JANUS MPR2.4",
        model_name="Kapsch JANUS Multi-Protocol Reader MPR2.4",
        device_type="toll_rsu",
        description="Multi-protocol toll tag reader (TDM/E-ZPass, 6C, 6B, SeGo, ATA); health to MOMS over SNMP",
        oui_prefixes=["00:E0:6A"],  # IEEE: KAPSCH AG (the group registrant; Kapsch TrafficCom holds no block)
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 1.0,
            "max_ms": 60.0,
            "mean_ms": 8.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp"],
        instance_rules=InstanceGenerationRules(
            serial_format="MPR{8NUM}",
            station_name_pattern="mpr-{location}-{seq}",
            vendor_short="KTC",
            model_short="MPR24",
        ),
        firmware_variants=[
            # The only public build string ("2014mar06a-MPR2", 27-Mar-2014).
            FirmwareVariant(version="2014mar06a-MPR2", release_date=date(2014, 3, 27), is_latest=True,
                            is_default=True, cves=[]),
        ],
        snmp_identity={
            "sys_descr": "Kapsch JANUS MPR2.4 2014mar06a-MPR2",
            "sys_object_id": "1.3.6.1.4.1.13182",
        },
    ),
    DeviceTemplate(
        id="kapsch/ris/9260",
        vendor="Kapsch",
        vendor_family="RIS",
        model="RIS-9260",
        model_name="Kapsch TrafficCom RIS-9260 V2X Roadside Unit",
        device_type="rsu",
        description="Connected-vehicle (V2X) roadside unit",
        oui_prefixes=["00:E0:6A"],  # IEEE: KAPSCH AG (the group registrant; Kapsch TrafficCom holds no block)
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 1.0,
            "max_ms": 60.0,
            "mean_ms": 8.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp"],
        instance_rules=InstanceGenerationRules(
            serial_format="RIS{8NUM}",
            station_name_pattern="rsu-{location}-{seq}",
            vendor_short="KTC",
            model_short="RIS9260",
        ),
        firmware_variants=[
            # The versions named in the 2025-08-26 CVE records; no fixed
            # version has been published.
            FirmwareVariant(version="4.6.0.1211.28", release_date=None, is_latest=True, is_default=True,
                            cves=["CVE-2025-25734", "CVE-2025-25736"], population_weight=0.6),
            FirmwareVariant(version="3.8.0.1119.42", release_date=None,
                            cves=["CVE-2025-25734", "CVE-2025-25736"], population_weight=0.4),
        ],
        snmp_identity={
            "sys_descr": "Kapsch RIS-9260 RSU 4.6.0.1211.28",
            "sys_object_id": "1.3.6.1.4.1.13182",
        },
    ),
    DeviceTemplate(
        # Back office on VMware (HP blades) per the 2014 proposal.
        id="kapsch/facility-host/moms",
        vendor="Kapsch",
        vendor_family="Facility Host",
        model="Facility Host / MOMS",
        model_name="Kapsch Facility Host with MOMS",
        device_type="server",
        description="Toll facility host: transactions, toll rates to pricing signs, maintenance online monitoring (MOMS)",
        oui_prefixes=["00:50:56", "00:0C:29", "00:15:5D"],  # IEEE: VMware; VMware; Microsoft (Hyper-V) — software on a virtual host
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 4.0,
            "std_dev_ms": 3.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https"],
        instance_rules=InstanceGenerationRules(
            serial_format="VMware-{8HEX}",
            station_name_pattern="tollhost-{location}-{seq}",
            vendor_short="KTC",
            model_short="FHOST",
        ),
        firmware_variants=[
            # MOMS "version 4.0.9", released 5-Feb-2014.
            FirmwareVariant(version="4.0.9", release_date=date(2014, 2, 5), is_latest=True,
                            is_default=True, cves=[]),
        ],
        snmp_identity={
            "sys_descr": "Kapsch Facility Host MOMS 4.0.9",
            "sys_object_id": "1.3.6.1.4.1.13182",
        },
    ),
    DeviceTemplate(
        # Ports per the SharpV administrator guide: HTTPS 443 among others.
        # SNMP is not documented, so none is claimed.
        id="genetec/autovu/sharpv",
        vendor="Genetec",
        vendor_family="AutoVu",
        model="AutoVu SharpV",
        model_name="Genetec AutoVu SharpV ALPR Camera",
        device_type="anpr_camera",
        description="Fixed ALPR camera with on-board plate reading",
        oui_prefixes=["0C:BF:15", "00:BF:15"],  # IEEE: Genetec Inc.
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 1.0,
            "max_ms": 60.0,
            "mean_ms": 8.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },
        supported_protocols=["https"],
        instance_rules=InstanceGenerationRules(
            serial_format="SV{8NUM}",
            station_name_pattern="alpr-{location}-{seq}",
            vendor_short="GEN",
            model_short="SHARPV",
        ),
        firmware_variants=[
            FirmwareVariant(version="14.5.3", release_date=None, is_latest=True, is_default=True, cves=[]),
        ],
        # The platform answers SNMP for every vendor device (fingerprint
        # SNMP carve-out); this makes that answer carry Genetec's real PEN.
        # SharpV's own SNMP support is not documented.
        snmp_identity={
            "sys_descr": "Genetec AutoVu SharpV 14.5.3",
            "sys_object_id": "1.3.6.1.4.1.17475",  # IANA PEN 17475 = Genetec Information Systems
        },
    ),
    DeviceTemplate(
        # Traffic Information Collector: Traffic Controller + 2x LMS511 SE.
        # Web configuration (TEMS Manager) over HTTP/HTTPS; TEMS Info
        # Interface on TCP 54345 (not modelled).
        id="sick/tic502/master",
        vendor="SICK",
        vendor_family="TIC",
        model="TIC502 Master",
        model_name="SICK TIC502 Traffic Information Collector",
        device_type="classification_sensor",
        description="Laser vehicle detection and classification at toll gantries (2x LMS511 SE)",
        oui_prefixes=["00:06:77"],  # IEEE: SICK AG
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 1.0,
            "max_ms": 60.0,
            "mean_ms": 8.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },
        supported_protocols=["https"],
        instance_rules=InstanceGenerationRules(
            serial_format="{8NUM}",
            station_name_pattern="tic-{location}-{seq}",
            vendor_short="SCK",
            model_short="TIC502",
        ),
        firmware_variants=[
            # TEMS platform >= V2.8.0 per the TIC operating instructions. The
            # LMS5xx findings below affect all LMS5xx firmware (SCA-2023-0007).
            FirmwareVariant(version="2.8.0", release_date=None, is_latest=True, is_default=True,
                            cves=["CVE-2023-4418", "CVE-2023-4420", "CVE-2023-31412"],
                            notes="LMS511 SE sensors: CVE-2023-4418/4420/31412 affect all LMS5xx versions"),
        ],
        # As for SharpV: the platform's SNMP answer, under SICK's real PEN.
        snmp_identity={
            "sys_descr": "SICK TIC502 Master TEMS 2.8.0",
            "sys_object_id": "1.3.6.1.4.1.52203",  # IANA PEN 52203 = SICK AG
        },
    ),
    DeviceTemplate(
        id="axis/camera/p1455-le",
        vendor="Axis",
        vendor_family="P-Series",
        model="P1455-LE",
        model_name="AXIS P1455-LE Network Camera",
        device_type="camera",
        description="Outdoor bullet camera for traffic monitoring",

        oui_prefixes=["00:40:8C", "AC:CC:8E", "B8:A4:4F", "E8:27:25"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 20.0,
            "mean_ms": 4.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="ACCC8E{6HEX}",
            station_name_pattern="cam-{location}-{seq}",
            vendor_short="AXI",
            model_short="P1455",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="11.6.94",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
                population_weight=0.66,
            ),
            FirmwareVariant(
                # AXIS OS 11.3.64 is a patched build (>= 10.7). CVE-2023-21412
                # was an AXIS License Plate Verifier ACAP application flaw
                # (LPV <= 2.8.3), NOT a camera-firmware vulnerability, so it is
                # removed from this firmware variant. See verified_corrections.
                version="11.3.64",
                release_date=date(2022, 7, 15),
                cves=[],
            ),
            FirmwareVariant(
                # Pre-fix AXIS OS active-track build (< 10.7). CVE-2021-31986 is
                # an AXIS-OS-wide SMTP-notification heap buffer overflow
                # (CWE-122, 6.8 MEDIUM) fixed on active track 10.7; this real
                # shipped build for the P1455-LE is genuinely vulnerable.
                version="10.6.0",
                release_date=date(2021, 4, 13),
                cves=["CVE-2021-31986"],
                population_weight=0.34,
            ),
        ],

        snmp_identity={
            "sys_descr": "AXIS P1455-LE Network Camera 11.6.94",
            "sys_object_id": "1.3.6.1.4.1.368.1.1",
        },
    ),
    DeviceTemplate(
        id="axis/camera/p1448-le",
        vendor="Axis",
        vendor_family="P Series",
        model="P1448-LE",
        model_name="AXIS P1448-LE Network Camera",
        device_type="ip_camera",
        description="4K outdoor network camera with IR illumination",

        oui_prefixes=["00:40:8C", "AC:CC:8E", "B8:A4:4F", "E8:27:25"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 25.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.5,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="ACCC8E{6HEX}",
            station_name_pattern="cam-{location}-{seq}",
            vendor_short="AXI",
            model_short="P1448",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="11.8.92",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
                population_weight=0.66,
            ),
            FirmwareVariant(
                version="11.5.64",
                release_date=date(2022, 8, 15),
                cves=[],
            ),
            FirmwareVariant(
                # Pre-fix AXIS OS 2020-LTS build (9.80.3.1, released 2021-03-02,
                # below the LTS-2020 fix 9.80.3.5). CVE-2021-31986 is an
                # AXIS-OS-wide SMTP-notification heap buffer overflow (CWE-122,
                # 6.8 MEDIUM); this real shipped build is genuinely vulnerable.
                version="9.80.3.1",
                release_date=date(2021, 3, 2),
                cves=["CVE-2021-31986"],
                population_weight=0.34,
            ),
        ],

        snmp_identity={
            "sys_descr": "AXIS P1448-LE Network Camera 11.8.92",
            "sys_object_id": "1.3.6.1.4.1.368.1.1",
        },
    ),
    DeviceTemplate(
        id="hikvision/camera/anpr",
        vendor="Hikvision",
        vendor_family="DeepinView",
        model="DS-2CD7A26G0/P",
        model_name="DS-2CD7A26G0/P ANPR Camera",
        device_type="anpr_camera",
        description="2MP ANPR camera with deep learning license plate recognition",

        oui_prefixes=["00:BC:99", "04:03:12", "04:EE:CD", "08:3B:C1"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="HIK{10ALPHANUM}",
            station_name_pattern="anpr-{location}-{seq}",
            vendor_short="HIK",
            model_short="ANPR",
        ),

        # V5.6.11 build 200609 is the only build seen in public integration
        # notes. The earlier V5.7.14 / V5.6.5 / V5.5.0 set was unsourced, and
        # CVE-2021-36260 was attached although Hikvision's advisory
        # (HSRC-202109-01) lists no DS-2CD7xxx model.
        firmware_variants=[
            FirmwareVariant(version="V5.6.11", release_date=date(2020, 6, 9), is_latest=True,
                            is_default=True, cves=[]),
        ],

        snmp_identity={
            "sys_descr": "Hikvision DS-2CD7A26G0/P ANPR Camera V5.6.11",
            "sys_object_id": "1.3.6.1.4.1.39165.1.1",
        },
    ),
    DeviceTemplate(
        id="pelco/spectra/enhanced",
        vendor="Pelco",
        vendor_family="Spectra",
        model="SD436-PG-E1",
        model_name="Spectra Enhanced PTZ Camera",
        device_type="ptz_camera",
        description="High-speed PTZ dome camera for surveillance",

        oui_prefixes=["00:00:54", "00:00:6C", "00:01:23", "00:03:74"],  # TODO(0b): Schneider OUIs; real Pelco OUI is 00:04:7D — needs adding to vendor_oui "pelco" first

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PEL{10NUM}",
            station_name_pattern="ptz-{location}-{seq}",
            vendor_short="PEL",
            model_short="SD43",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.8.3",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.6.0",
                release_date=date(2022, 6, 20),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Pelco Spectra Enhanced PTZ Camera V2.8.3",
            "sys_object_id": "1.3.6.1.4.1.25066",  # IANA PEN 25066 = PELCO
        },
    ),
    DeviceTemplate(
        id="econolite/traffic-controller/asc-3-2100",
        vendor="Econolite",
        vendor_family="Traffic Controller",
        model="ASC/3-2100",
        model_name="ASC/3-2100",
        device_type="traffic_controller",
        description="Econolite ASC/3-2100",
        oui_prefixes=["00:04:81"],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 8.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V2.0.8",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Econolite ASC/3-2100 Signal Controller V2.0.8",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.2",
                "sys_name": "ASC3-2100-001",
                "ntcip_device_type": "asc",
                "max_phases": 8,
                "max_detectors": 32,
            },
    ),
    DeviceTemplate(
        id="flir/thermal-sensor/trafisense",
        vendor="FLIR",
        vendor_family="Thermal Sensor",
        model="TrafiSense",
        model_name="TrafiSense",
        device_type="thermal_sensor",
        description="FLIR TrafiSense",
        oui_prefixes=["00:13:56", "00:1B:D8", "00:40:7F"],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V3.5.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "FLIR TrafiSense Multi-Lane Detector V3.5.0",
                "sys_object_id": "1.3.6.1.4.1.34674",  # IANA PEN 34674 = FLIR Systems
                "sys_name": "THERMAL-ML-001",
                "ntcip_device_type": "sensor",
            },
    ),
    DeviceTemplate(
        id="pelco/ptz-camera/spectra-enhanced",
        vendor="Pelco",
        vendor_family="PTZ Camera",
        model="Spectra Enhanced",
        model_name="Spectra Enhanced",
        device_type="camera",
        description="Pelco Spectra Enhanced",
        oui_prefixes=["00:00:54", "00:00:6C", "00:01:23", "00:03:74"],  # TODO(0b): Schneider OUIs; real Pelco OUI is 00:04:7D — needs adding to vendor_oui "pelco" first
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V1.32",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Pelco Spectra Enhanced PTZ Camera V1.32",
                "sys_object_id": "1.3.6.1.4.1.25066",  # IANA PEN 25066 = PELCO
                "sys_name": "PTZ-PELCO-001",
                "sys_location": "Tunnel Portal",
                "ntcip_device_type": "camera",
            },
    ),
    # ------------------------------------------------------------------
    # Roadway flagship additions (2026-10-21). OUIs and PENs checked
    # against the IEEE and IANA registries on that date; versions and CVEs
    # from vendor release notes, NVD and CISA (see the plan in
    # tasks/transportation-flagships-plan.md). Where a vendor publishes
    # only its enterprise root, sys_object_id is that root: the product
    # suffix is not public.
    # ------------------------------------------------------------------
    DeviceTemplate(
        # Centracs is ATMS software (application + communication servers);
        # Econolite does not publish a host OS spec. The host here is a
        # Windows Server VM, as for the other central software templates.
        id="econolite/centracs/atms-server",
        vendor="Econolite",
        vendor_family="Centracs",
        model="Centracs ATMS",
        model_name="Econolite Centracs Advanced Traffic Management System Server",
        device_type="server",
        description="Central traffic management system: signal timing, NTCIP polling, alarms",
        oui_prefixes=["00:50:56", "00:0C:29", "00:15:5D"],  # IEEE: VMware; VMware; Microsoft (Hyper-V) — software on a virtual host
        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "window_scaling": 8,
        },
        response_timing={
            "min_ms": 0.5,
            "max_ms": 30.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https", "rdp"],
        instance_rules=InstanceGenerationRules(
            serial_format="VMware-{8HEX}",
            station_name_pattern="atms-{location}-{seq}",
            vendor_short="ECO",
            model_short="CTRX",
        ),
        firmware_variants=[
            # Centracs 2.x (Econolite Centracs 2.0 datasheet; 2.x not EOL per
            # Econolite's Centracs FAQ). Finer build numbers are not public.
            FirmwareVariant(version="2.0", release_date=None, is_latest=True,
                            is_default=True, cves=[]),
        ],
        snmp_identity={
            "sys_descr": "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - Software: Windows Version 6.3 (Build 17763 Multiprocessor Free)",
            "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.2",
            "sys_name": "{device_name}",
        },
    ),
    DeviceTemplate(
        id="genetec/security-center/vms-server",
        vendor="Genetec",
        vendor_family="Security Center",
        model="Security Center 5",
        model_name="Genetec Security Center Video Management Server",
        device_type="server",
        description="Video management system (Directory + Archiver) for traffic CCTV",
        oui_prefixes=["00:50:56", "00:0C:29", "00:15:5D"],  # IEEE: VMware; VMware; Microsoft (Hyper-V) — software on a virtual host
        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "window_scaling": 8,
        },
        response_timing={
            "min_ms": 0.5,
            "max_ms": 40.0,
            "mean_ms": 3.0,
            "std_dev_ms": 1.5,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https", "rdp"],
        instance_rules=InstanceGenerationRules(
            serial_format="VMware-{8HEX}",
            station_name_pattern="vms-{location}-{seq}",
            vendor_short="GEN",
            model_short="SC5",
        ),
        firmware_variants=[
            # 5.14.1.2 is the fix level for CVE-2026-65422 on the 5.14 line;
            # 5.12.2.22 is its 5.12 fix and is past every other published
            # 5.12 Security Center fix (CVE-2024-7059, CVE-2025-43027,
            # CVE-2026-40619). Genetec product-release and advisory pages.
            FirmwareVariant(version="5.14.1.2", release_date=None, is_latest=True,
                            is_default=True, cves=[], population_weight=0.5),
            FirmwareVariant(version="5.12.2.22", release_date=None, cves=[],
                            population_weight=0.5),
        ],
        snmp_identity={
            # Security Center 5.12 lists Windows Server 2022 as supported.
            "sys_descr": "Hardware: Intel64 Family 6 Model 106 Stepping 6 AT/AT COMPATIBLE - Software: Windows Version 6.3 (Build 20348 Multiprocessor Free)",
            "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.2",
            "sys_name": "{device_name}",
        },
    ),
    DeviceTemplate(
        # MAXTIME is Intelight's (Q-Free since 2016) Linux controller
        # software; the 2070LX is one of the controllers it ships on.
        id="qfree/intelight-2070lx/maxtime",
        vendor="Q-Free",
        vendor_family="Intelight MAXTIME",
        model="Intelight 2070LX",
        model_name="Q-Free Intelight 2070LX ATC with MAXTIME",
        device_type="traffic_controller",
        description="Type 2070 ATC running MAXTIME intersection control software (NTCIP 1202 v03A)",
        oui_prefixes=["00:12:8E", "64:55:63"],  # IEEE: Q-Free America, Inc.; Q-Free ASA
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 0.5,
            "max_ms": 50.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https", "ssh"],
        instance_rules=InstanceGenerationRules(
            serial_format="QF{10NUM}",
            station_name_pattern="atc-{location}-{seq}",
            vendor_short="QFR",
            model_short="2070LX",
        ),
        firmware_variants=[
            # Every MAXTIME release through 2.11.0 carries the February 2025
            # Nozomi findings (CVE-2025-1100 and others); no fixed version had
            # been announced (NVD CPE versionEndIncluding 2.11.0).
            FirmwareVariant(version="2.11.0", release_date=None, is_latest=True,
                            is_default=True, cves=["CVE-2025-1100"]),
        ],
        snmp_identity={
            "sys_descr": "Q-Free Intelight 2070LX MAXTIME 2.11.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",  # NTCIP ASC node
        },
    ),
    DeviceTemplate(
        # McCain controller hardware now sold under SWARCO; the software is
        # Omni eX Intersection Control Software (manual v3.3.0).
        id="mccain/atc-ex2/omni-ex",
        vendor="McCain",
        vendor_family="ATC eX",
        model="ATC eX2 NEMA",
        model_name="McCain ATC eX2 NEMA Controller with Omni eX",
        device_type="traffic_controller",
        description="NEMA TS2 ATC running Omni eX; NTCIP over SNMP 161, HTTPS web UI",
        oui_prefixes=["10:10:B6"],  # IEEE: McCain Inc
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 0.5,
            "max_ms": 50.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https"],
        instance_rules=InstanceGenerationRules(
            serial_format="MCC{9NUM}",
            station_name_pattern="atc-{location}-{seq}",
            vendor_short="MCC",
            model_short="EX2",
        ),
        firmware_variants=[
            FirmwareVariant(version="3.3.0", release_date=date(2021, 4, 1), is_latest=True,
                            is_default=True, cves=[], population_weight=0.7),
            FirmwareVariant(version="2.00.00.0005", release_date=date(2020, 4, 1), cves=[],
                            population_weight=0.3),
        ],
        snmp_identity={
            "sys_descr": "McCain ATC eX2 NEMA Omni eX 3.3.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",  # NTCIP ASC node (McCain holds no PEN)
        },
    ),
    DeviceTemplate(
        id="cradlepoint/ibr900/router",
        vendor="Cradlepoint",
        vendor_family="IBR900",
        model="IBR900-600M",
        model_name="Cradlepoint IBR900-600M Ruggedized LTE Router",
        device_type="router",
        description="Cellular backhaul for cabinets beyond the fiber plant (NetCloud OS)",
        oui_prefixes=["00:30:44", "00:E0:1C"],  # IEEE: CradlePoint, Inc
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 0.5,
            "max_ms": 200.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.5,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https", "ssh"],
        instance_rules=InstanceGenerationRules(
            serial_format="WA{9NUM}",
            station_name_pattern="cell-{location}-{seq}",
            vendor_short="CPT",
            model_short="IBR900",
        ),
        firmware_variants=[
            # NCOS 7.MM.NN monthly releases; both are past the CVE-2021-37471
            # fix (7.21.10).
            FirmwareVariant(version="7.23.40", release_date=date(2023, 4, 1), is_latest=True,
                            is_default=True, cves=[], population_weight=0.6),
            FirmwareVariant(version="7.22.101", release_date=date(2022, 10, 1), cves=[],
                            population_weight=0.4),
        ],
        snmp_identity={
            "sys_descr": "Cradlepoint IBR900-600M NCOS 7.23.40",
            "sys_object_id": "1.3.6.1.4.1.20992",  # IANA PEN: CradlePoint, Inc.
        },
    ),
    DeviceTemplate(
        id="sierra/airlink-rv55/router",
        vendor="Sierra Wireless",
        vendor_family="AirLink",
        model="RV55",
        model_name="Sierra Wireless AirLink RV55 LTE-A Pro Router",
        device_type="router",
        description="Industrial cellular router (ALEOS) for remote cabinets",
        oui_prefixes=["00:A0:D5", "28:A3:31", "50:13:9D"],  # IEEE: Sierra Wireless
        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "window_scaling": 7,
        },
        response_timing={
            "min_ms": 0.5,
            "max_ms": 200.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.5,
            "distribution": "lognormal",
        },
        supported_protocols=["snmp", "https", "ssh"],
        instance_rules=InstanceGenerationRules(
            serial_format="{14NUM}",
            station_name_pattern="cell-{location}-{seq}",
            vendor_short="SWI",
            model_short="RV55",
        ),
        firmware_variants=[
            # 4.17.0.12 fixed the 2023 ALEOS set (CVE-2023-40458..40465,
            # ICSA-23-341-06); 4.18.0.012 (4.18.0.011 was recalled).
            FirmwareVariant(version="4.18.0.012", release_date=date(2025, 3, 1), is_latest=True,
                            is_default=True, cves=[], population_weight=0.5),
            FirmwareVariant(version="4.17.0.12", release_date=date(2023, 10, 1), cves=[],
                            population_weight=0.5),
        ],
        snmp_identity={
            "sys_descr": "Sierra Wireless AirLink RV55 ALEOS 4.18.0.012",
            "sys_object_id": "1.3.6.1.4.1.31322",  # IANA PEN: Sierra Wireless, Inc.
        },
    ),
]
