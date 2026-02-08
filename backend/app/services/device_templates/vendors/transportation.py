"""Transportation / ITS device templates (Econolite, McCain, Daktronics, Wavetronix, FLIR, Q-Free, Kapsch, Axis, Hikvision, Pelco)."""

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

        oui_prefixes=["00:19:FA"],

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
                cves=["CVE-2022-25343"],
            ),
            FirmwareVariant(
                version="V6.45",
                release_date=date(2020, 9, 20),
                cves=["CVE-2022-25343", "CVE-2020-14476"],
            ),
        ],

        snmp_identity={
            "sys_descr": "ASC/3-2100 Cobalt Traffic Signal Controller",
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

        oui_prefixes=["00:19:FA"],

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

        firmware_variants=[
            FirmwareVariant(
                version="V7.16",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Econolite Cobalt ATC Traffic Signal Controller",
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

        oui_prefixes=["00:0E:2E"],

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
                cves=["CVE-2022-35586"],
            ),
        ],

        snmp_identity={
            "sys_descr": "McCain 2070 ATC Traffic Signal Controller",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
        },
    ),
    DeviceTemplate(
        id="mccain/170e/detector",
        vendor="McCain",
        vendor_family="170E",
        model="170E",
        model_name="170E Detector Rack",
        device_type="detector_rack",
        description="170E cabinet detector rack for vehicle detection",

        oui_prefixes=["00:50:C2", "00:17:61"],

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
            station_name_pattern="det-{location}-{seq}",
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
            "sys_descr": "McCain 170E Detector Rack",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.6",
        },
    ),
    DeviceTemplate(
        id="daktronics/venus/1500",
        vendor="Daktronics",
        vendor_family="Venus",
        model="Venus 1500",
        model_name="Venus 1500 DMS Controller",
        device_type="dms",
        description="Dynamic Message Sign controller for transportation",

        oui_prefixes=["00:0E:63"],

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
            serial_format="VNS15{8NUM}",
            station_name_pattern="dms-{location}-{seq}",
            vendor_short="DAK",
            model_short="V1500",
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
                cves=["CVE-2022-30619"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Daktronics Venus 1500 Dynamic Message Sign",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.3",
        },
    ),
    DeviceTemplate(
        id="daktronics/venus/7000",
        vendor="Daktronics",
        vendor_family="Venus",
        model="Venus 7000",
        model_name="Venus 7000 Large DMS Controller",
        device_type="dms",
        description="Large format dynamic message sign controller",

        oui_prefixes=["00:0E:63"],

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
            serial_format="VNS70{8NUM}",
            station_name_pattern="dms-{location}-{seq}",
            vendor_short="DAK",
            model_short="V7000",
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
                cves=["CVE-2022-30619"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Daktronics Venus 7000 Large Format DMS",
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

        oui_prefixes=["00:0F:B5"],

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
                cves=["CVE-2022-30620"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Wavetronix SmartSensor HD Radar Detector",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.5",
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

        oui_prefixes=["00:15:2D"],

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
                cves=["CVE-2022-30620"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Wavetronix SmartSensor Advance Vehicle Classifier",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.5.1",
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

        oui_prefixes=["00:40:7F"],

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
                cves=["CVE-2022-37061"],
            ),
        ],

        snmp_identity={
            "sys_descr": "FLIR TrafiOne Thermal Traffic Sensor",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.5",
        },
    ),
    DeviceTemplate(
        id="qfree/rsu/5000",
        vendor="Q-Free",
        vendor_family="RSU",
        model="RSU 5000",
        model_name="RSU 5000 Roadside Unit",
        device_type="toll_rsu",
        description="DSRC roadside unit for tolling and V2X",

        oui_prefixes=["00:1E:A5"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="RSU5{10NUM}",
            station_name_pattern="rsu-{location}-{seq}",
            vendor_short="QFR",
            model_short="RSU5",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.2.0",
                release_date=date(2024, 1, 30),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.0.0",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-36324"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Q-Free RSU 5000 Roadside Unit",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.6",
        },
    ),
    DeviceTemplate(
        id="kapsch/tcs/2000",
        vendor="Kapsch",
        vendor_family="TCS",
        model="TCS 2000",
        model_name="TCS 2000 Toll Controller",
        device_type="toll_controller",
        description="Central toll collection system controller",

        oui_prefixes=["00:1B:21"],

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
            serial_format="KAP{10NUM}",
            station_name_pattern="toll-{location}-{seq}",
            vendor_short="KAP",
            model_short="TCS2",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.4.0",
                release_date=date(2024, 2, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.2.0",
                release_date=date(2022, 9, 10),
                cves=["CVE-2022-37064"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Kapsch TCS 2000 Toll Collection System",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.6",
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

        oui_prefixes=["00:40:8C", "AC:CC:8E", "B8:A4:4F"],

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

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ACCC8E{6HEX}",
            station_name_pattern="cam-{location}-{seq}",
            vendor_short="AXI",
            model_short="P1455",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V11.6.94",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V11.3.64",
                release_date=date(2022, 7, 15),
                cves=["CVE-2022-37065"],
            ),
        ],

        snmp_identity={
            "sys_descr": "AXIS P1455-LE Network Camera",
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

        oui_prefixes=["00:40:8C", "AC:CC:8E", "B8:A4:4F"],

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

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ACCC8E{6HEX}",
            station_name_pattern="cam-{location}-{seq}",
            vendor_short="AXI",
            model_short="P1448",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V11.8.92",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V11.5.64",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-37065"],
            ),
        ],

        snmp_identity={
            "sys_descr": "AXIS P1448-LE Network Camera",
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

        oui_prefixes=["54:C4:15", "C0:56:E3", "44:19:B6", "BC:AD:28"],

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

        firmware_variants=[
            FirmwareVariant(
                version="V5.7.14",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.6.5",
                release_date=date(2022, 9, 20),
                cves=["CVE-2022-28173"],
            ),
            FirmwareVariant(
                version="V5.5.0",
                release_date=date(2021, 4, 15),
                cves=["CVE-2022-28173", "CVE-2021-36260"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Hikvision DS-2CD7A26G0/P ANPR Camera",
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

        oui_prefixes=["00:80:F4", "64:3A:EA"],  # Schneider Electric (Pelco parent)

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
                cves=["CVE-2022-36341"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Pelco Spectra Enhanced PTZ Camera",
            "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",  # Pelco enterprise OID
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
        oui_prefixes=['00:19:FA'],
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
        oui_prefixes=['00:40:7F', '00:80:F4'],
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
                "sys_object_id": "1.3.6.1.4.1.28846.1.2.1",
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
        oui_prefixes=['00:80:F4', '64:3A:EA'],
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
                "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",
                "sys_name": "PTZ-PELCO-001",
                "sys_location": "Tunnel Portal",
                "ntcip_device_type": "camera",
            },
    ),
]
