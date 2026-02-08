"""Schneider Electric device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="schneider/modicon-m580/bmep584040",
        vendor="Schneider",
        vendor_family="Modicon M580",
        model="BMEP584040",
        model_name="M580 ePAC CPU",
        device_type="plc",
        description="High-performance Ethernet programmable automation controller",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,  # VxWorks
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": None,
            "sack_permitted": True,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 20.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
            "outlier_probability": 0.008,
            "outlier_multiplier": 3.5,
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6, 10, 11],
            "exception_probability": 0.0006,
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="BMEP{8NUM}",
            station_name_pattern="{role}-m580-{seq}",
            vendor_short="SCH",
            model_short="M580",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.10",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.60",
                release_date=date(2023, 5, 20),
                cves=[],
            ),
            FirmwareVariant(
                version="V3.20",
                release_date=date(2022, 4, 10),
                cves=["CVE-2022-45788"],
                notes="Vulnerable to authentication bypass",
            ),
            FirmwareVariant(
                version="V2.80",
                release_date=date(2020, 11, 5),
                cves=["CVE-2022-45788", "CVE-2021-22779", "CVE-2020-7561"],
                notes="Multiple critical vulnerabilities",
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMEP584040",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Modicon M580 ePAC",
            "model_name": "BMEP584040",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 14,
            "product_code": 584,
            "state": 3,
        },

        protocol_quirks={
            "modbus_max_registers": 125,
            "modbus_max_coils": 2000,
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m241/tm241ce40r",
        vendor="Schneider",
        vendor_family="Modicon M241",
        model="TM241CE40R",
        model_name="M241 Logic Controller",
        device_type="plc",
        description="Compact logic controller with Ethernet and CANopen",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 1.5,
            "max_ms": 35.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TM24{8NUM}",
            station_name_pattern="{role}-m241-{seq}",
            vendor_short="SCH",
            model_short="M241",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.2.6",
                release_date=date(2024, 1, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.1.0",
                release_date=date(2022, 9, 15),
                cves=["CVE-2022-45788"],
            ),
            FirmwareVariant(
                version="V4.0.5",
                release_date=date(2020, 6, 20),
                cves=["CVE-2022-45788", "CVE-2020-7559"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TM241CE40R",
            "product_name": "Modicon M241 Logic Controller",
            "model_name": "TM241CE40R",
        },
    ),
    DeviceTemplate(
        id="schneider/altivar/atv630",
        vendor="Schneider",
        vendor_family="Altivar Process",
        model="ATV630D15N4",
        model_name="Altivar Process ATV630",
        device_type="drive",
        description="Variable frequency drive for process applications with advanced connectivity",

        oui_prefixes=["00:00:54", "00:80:F4", "EC:FA:AA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.001,
            "timeout_probability": 0.0005,
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ATV{10NUM}",
            station_name_pattern="{role}-atv630-{seq}",
            vendor_short="SCH",
            model_short="ATV6",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.7IE61",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
                notes="Latest firmware with security patches",
            ),
            FirmwareVariant(
                version="V1.6IE42",
                release_date=date(2022, 7, 15),
                cves=["CVE-2022-22804"],
                notes="Vulnerable to improper input validation",
            ),
            FirmwareVariant(
                version="V1.5IE35",
                release_date=date(2021, 3, 10),
                cves=["CVE-2022-22804", "CVE-2020-7571"],
                notes="Multiple vulnerabilities - upgrade recommended",
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "ATV630D15N4",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Altivar Process ATV630",
            "model_name": "ATV630D15N4",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 2,  # AC Drive
            "product_code": 630,
            "state": 3,
        },

        profinet_identity={
            "vendor_id": 0x0095,
            "device_id": 0x0630,
            "device_role": 1,  # Device
            "im0_manufacturer": "Schneider Electric",
            "im0_order_id": "ATV630D15N4",
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m580/bmep582040",
        vendor="Schneider",
        vendor_family="Modicon M580",
        model="BMEP582040",
        model_name="M580 ePAC CPU",
        device_type="plc",
        description="Entry-level M580 ePAC with 2MB program memory",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": None,
            "sack_permitted": True,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 25.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="BMEP{8NUM}",
            station_name_pattern="{role}-m580-{seq}",
            vendor_short="SCH",
            model_short="M580",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.10",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.20",
                release_date=date(2022, 4, 10),
                cves=["CVE-2022-45788"],
            ),
            FirmwareVariant(
                version="V2.80",
                release_date=date(2020, 11, 5),
                cves=["CVE-2022-45788", "CVE-2021-22779"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMEP582040",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Modicon M580 ePAC",
            "model_name": "BMEP582040",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 14,
            "product_code": 582,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m340/bmxp3420302",
        vendor="Schneider",
        vendor_family="Modicon M340",
        model="BMXP3420302",
        model_name="M340 Processor",
        device_type="plc",
        description="Mid-range Modicon M340 processor with Ethernet",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="BMX{8NUM}",
            station_name_pattern="{role}-m340-{seq}",
            vendor_short="SCH",
            model_short="M340",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.40",
                release_date=date(2024, 1, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.10",
                release_date=date(2022, 5, 15),
                cves=["CVE-2022-45788"],
            ),
            FirmwareVariant(
                version="V2.90",
                release_date=date(2020, 8, 20),
                cves=["CVE-2022-45788", "CVE-2020-7537"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMXP3420302",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Modicon M340 Processor",
            "model_name": "BMXP3420302",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 14,
            "product_code": 342,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m251/tm251mese",
        vendor="Schneider",
        vendor_family="Modicon M251",
        model="TM251MESE",
        model_name="M251 Logic Controller",
        device_type="plc",
        description="Compact logic controller with Ethernet and serial ports",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 1.5,
            "max_ms": 30.0,
            "mean_ms": 7.0,
            "std_dev_ms": 4.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TM25{8NUM}",
            station_name_pattern="{role}-m251-{seq}",
            vendor_short="SCH",
            model_short="M251",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.2.6",
                release_date=date(2024, 1, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.0.0",
                release_date=date(2022, 6, 20),
                cves=["CVE-2022-45788"],
            ),
            FirmwareVariant(
                version="V4.0.7",
                release_date=date(2020, 4, 15),
                cves=["CVE-2022-45788", "CVE-2020-7559"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TM251MESE",
            "product_name": "Modicon M251 Logic Controller",
            "model_name": "TM251MESE",
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m262/tm262l20mese8t",
        vendor="Schneider",
        vendor_family="Modicon M262",
        model="TM262L20MESE8T",
        model_name="M262 Motion Controller",
        device_type="motion_controller",
        description="Motion controller with 8 axis support and EtherNet/IP",

        oui_prefixes=["00:00:54", "00:80:F4", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="TM26{8NUM}",
            station_name_pattern="{role}-m262-{seq}",
            vendor_short="SCH",
            model_short="M262",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.5.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.3.0",
                release_date=date(2022, 9, 15),
                cves=["CVE-2022-45788"],
            ),
            FirmwareVariant(
                version="V1.1.0",
                release_date=date(2021, 5, 10),
                cves=["CVE-2022-45788", "CVE-2021-22779"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TM262L20MESE8T",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Modicon M262 Motion Controller",
            "model_name": "TM262L20MESE8T",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 43,  # Motion Controller
            "product_code": 262,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="schneider/altivar/atv930",
        vendor="Schneider",
        vendor_family="Altivar Process",
        model="ATV930D15N4",
        model_name="Altivar Process ATV930",
        device_type="drive",
        description="High-performance variable frequency drive with advanced process functions",

        oui_prefixes=["00:00:54", "00:80:F4", "EC:FA:AA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 1.5,
            "max_ms": 40.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ATV9{10NUM}",
            station_name_pattern="{role}-atv930-{seq}",
            vendor_short="SCH",
            model_short="ATV9",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.6IE50",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.3IE30",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-22804"],
            ),
            FirmwareVariant(
                version="V3.1IE20",
                release_date=date(2021, 4, 10),
                cves=["CVE-2022-22804", "CVE-2020-7571"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "ATV930D15N4",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Altivar Process ATV930",
            "model_name": "ATV930D15N4",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 2,  # AC Drive
            "product_code": 930,
            "state": 3,
        },

        profinet_identity={
            "vendor_id": 0x0095,
            "device_id": 0x0930,
            "device_role": 1,
            "im0_manufacturer": "Schneider Electric",
            "im0_order_id": "ATV930D15N4",
        },
    ),
    DeviceTemplate(
        id="schneider/altivar/atv320",
        vendor="Schneider",
        vendor_family="Altivar Machine",
        model="ATV320U22N4C",
        model_name="Altivar Machine ATV320",
        device_type="drive",
        description="Compact variable frequency drive for OEM machine builders",

        oui_prefixes=["00:00:54", "00:80:F4", "EC:FA:AA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ATV3{10NUM}",
            station_name_pattern="{role}-atv320-{seq}",
            vendor_short="SCH",
            model_short="ATV3",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.8IE22",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.6IE18",
                release_date=date(2022, 5, 20),
                cves=["CVE-2022-22804"],
            ),
            FirmwareVariant(
                version="V1.4IE12",
                release_date=date(2020, 10, 10),
                cves=["CVE-2022-22804", "CVE-2020-7571"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "ATV320U22N4C",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Altivar Machine ATV320",
            "model_name": "ATV320U22N4C",
        },
    ),
    DeviceTemplate(
        id="schneider/advantys/stbnip2311",
        vendor="Schneider",
        vendor_family="Advantys STB",
        model="STBNIP2311",
        model_name="STB EtherNet/IP Adapter",
        device_type="remote_io",
        description="Advantys STB distributed I/O network interface module",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 20.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="STB{8NUM}",
            station_name_pattern="io-stb-{seq}",
            vendor_short="SCH",
            model_short="STB",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.20",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.80",
                release_date=date(2022, 3, 10),
                cves=["CVE-2021-22787"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "STBNIP2311",
            "product_name": "Advantys STB EtherNet/IP Adapter",
            "model_name": "STBNIP2311",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 7,  # General Purpose I/O
            "product_code": 231,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="schneider/tm3/tm3di32k",
        vendor="Schneider",
        vendor_family="TM3 I/O",
        model="TM3DI32K",
        model_name="TM3 32-Input Module",
        device_type="io_module",
        description="32-point digital input expansion module",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TM3{8NUM}",
            station_name_pattern="io-tm3-{seq}",
            vendor_short="SCH",
            model_short="TM3",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.1",
                release_date=date(2023, 6, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.8",
                release_date=date(2021, 9, 10),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TM3DI32K",
            "product_name": "TM3 32-Input Module",
            "model_name": "TM3DI32K",
        },
    ),
    DeviceTemplate(
        id="schneider/connexium/tcsesm083f2cu0",
        vendor="Schneider",
        vendor_family="ConneXium",
        model="TCSESM083F2CU0",
        model_name="ConneXium Managed Switch",
        device_type="network_switch",
        description="8-port managed Ethernet switch for industrial applications",

        oui_prefixes=["00:00:54", "00:80:F4", "00:60:5C"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TCE{10ALPHANUM}",
            station_name_pattern="sw-cnx-{seq}",
            vendor_short="SCH",
            model_short="CNX",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.5",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V8.1",
                release_date=date(2022, 6, 20),
                cves=["CVE-2022-30234"],
            ),
            FirmwareVariant(
                version="V7.8",
                release_date=date(2021, 1, 15),
                cves=["CVE-2022-30234", "CVE-2020-28212"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Schneider Electric ConneXium Managed Switch",
            "sys_object_id": "1.3.6.1.4.1.3833.1.100.1",
        },

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TCSESM083F2CU0",
            "product_name": "ConneXium Managed Switch",
            "model_name": "TCSESM083F2CU0",
        },
    ),
    DeviceTemplate(
        id="schneider/magelis/hmistm6",
        vendor="Schneider",
        vendor_family="Magelis STM",
        model="HMISTM6",
        model_name="Magelis STM6 HMI",
        device_type="hmi",
        description="Compact 3.4-inch color touchscreen HMI panel",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="HMI{8NUM}",
            station_name_pattern="hmi-stm-{seq}",
            vendor_short="SCH",
            model_short="STM6",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.5.2",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.3.0",
                release_date=date(2022, 5, 10),
                cves=["CVE-2022-0221"],
            ),
            FirmwareVariant(
                version="V3.1.0",
                release_date=date(2020, 11, 15),
                cves=["CVE-2022-0221", "CVE-2020-7570"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "HMISTM6",
            "product_name": "Magelis STM6 HMI",
            "model_name": "HMISTM6",
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-premium/tsxp57204m",
        vendor="Schneider",
        vendor_family="Modicon Premium",
        model="TSXP57204M",
        model_name="Premium CPU",
        device_type="plc",
        description="Legacy Modicon Premium processor - still widely deployed",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TSX{8NUM}",
            station_name_pattern="{role}-premium-{seq}",
            vendor_short="SCH",
            model_short="P57",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.3",
                release_date=date(2020, 6, 15),
                is_latest=True,
                is_default=True,
                cves=[],
                notes="Final firmware release for legacy platform",
            ),
            FirmwareVariant(
                version="V5.0",
                release_date=date(2018, 3, 10),
                cves=["CVE-2019-6857"],
            ),
            FirmwareVariant(
                version="V4.6",
                release_date=date(2015, 11, 20),
                cves=["CVE-2019-6857", "CVE-2017-7579"],
                notes="Legacy firmware - upgrade strongly recommended",
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TSXP57204M",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Modicon Premium CPU",
            "model_name": "TSXP57204M",
        },
    ),
    DeviceTemplate(
        id="schneider/tm5-safety/tm5cslc100fs",
        vendor="Schneider",
        vendor_family="TM5 Safety",
        model="TM5CSLC100FS",
        model_name="TM5 Safety Logic Controller",
        device_type="safety_plc",
        description="Safety logic controller for machine safety applications (SIL 3/PLe)",

        oui_prefixes=["00:00:54", "00:80:F4", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="TM5S{8NUM}",
            station_name_pattern="safety-tm5-{seq}",
            vendor_short="SCH",
            model_short="TM5S",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.4.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.2.0",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-45788"],
            ),
            FirmwareVariant(
                version="V1.0.0",
                release_date=date(2021, 3, 10),
                cves=["CVE-2022-45788", "CVE-2021-22779"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TM5CSLC100FS",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "TM5 Safety Logic Controller",
            "model_name": "TM5CSLC100FS",
        },
    ),
    DeviceTemplate(
        id="schneider/power/pm8000",
        vendor="Schneider",
        vendor_family="PowerLogic",
        model="PM8000",
        model_name="PowerLogic PM8000",
        device_type="power_meter",
        description="Advanced power quality and energy meter with communications",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "bacnet", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PM8{8NUM}",
            station_name_pattern="meter-pm8000-{seq}",
            vendor_short="SCH",
            model_short="PM8000",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.0.0",
                release_date=date(2023, 8, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "PM8000",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "PowerLogic PM8000 Power Meter",
            "model_name": "PM8000",
        },

        snmp_identity={
            "sys_descr": "Schneider Electric PowerLogic PM8000 Power Quality Meter",
            "sys_object_id": "1.3.6.1.4.1.3833.1.100.8000",
        },

        bacnet_identity={
            "vendor_id": 67,
            "model_name": "PM8000",
            "device_instance": 0,
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m580/bmeh586040",
        vendor="Schneider",
        vendor_family="Modicon M580",
        model="BMEH586040",
        model_name="M580 High-Performance ePAC",
        device_type="plc",
        description="High-performance Ethernet programmable automation controller with redundancy",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.4,
            "max_ms": 15.0,
            "mean_ms": 3.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="BMEH{8NUM}",
            station_name_pattern="{role}-m580h-{seq}",
            vendor_short="SCH",
            model_short="M580H",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.10",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMEH586040",
            "product_name": "Modicon M580 ePAC",
            "model_name": "BMEH586040",
        },

        ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 14,
            "product_code": 586,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m340/bmxp342020",
        vendor="Schneider",
        vendor_family="Modicon M340",
        model="BMXP342020",
        model_name="M340 Processor",
        device_type="plc",
        description="Mid-range automation processor with embedded Ethernet",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 30.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="BMX{8NUM}",
            station_name_pattern="{role}-m340-{seq}",
            vendor_short="SCH",
            model_short="M340",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.60",
                release_date=date(2023, 5, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMXP342020",
            "product_name": "Modicon M340 Processor",
            "model_name": "M340",
        },
    ),
    DeviceTemplate(
        id="schneider/modicon-m580/bmep586040s",
        vendor="Schneider",
        vendor_family="Modicon M580",
        model="BMEP586040S",
        model_name="M580 Safety ePAC",
        device_type="safety_plc",
        description="Safety-rated Ethernet programmable automation controller for SIL3 applications",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 18.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "profisafe"],

        instance_rules=InstanceGenerationRules(
            serial_format="BMEPS{8NUM}",
            station_name_pattern="{role}-m580s-{seq}",
            vendor_short="SCH",
            model_short="M580S",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.10",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMEP586040S",
            "product_name": "Modicon M580 Safety ePAC",
            "model_name": "M580S",
        },
    ),
    DeviceTemplate(
        id="schneider/lexium32/lxm32md18n4",
        vendor="Schneider",
        vendor_family="Lexium 32",
        model="LXM32MD18N4",
        model_name="Lexium 32 Servo Drive",
        device_type="servo",
        description="Motion servo drive for automation applications",

        oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="LXM{8NUM}",
            station_name_pattern="{role}-lxm32-{seq}",
            vendor_short="SCH",
            model_short="LXM32",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.60",
                release_date=date(2023, 4, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "LXM32MD18N4",
            "product_name": "Lexium 32 Servo Drive",
            "model_name": "Lexium 32",
        },
    ),
    DeviceTemplate(
        id="schneider/premium/tsxp57154m",
        vendor="Schneider",
        vendor_family="Premium",
        model="TSXP57154M",
        model_name="Premium TSXP57154M",
        device_type="plc",
        description="Legacy Premium PLC with Ethernet communication",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TSX{8NUM}",
            station_name_pattern="{role}-premium-{seq}",
            vendor_short="SCH",
            model_short="TSXP",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.0",
                release_date=date(2018, 6, 1),
                is_latest=True,
                is_default=True,
                cves=["CVE-2019-6857", "CVE-2018-7821"],
                notes="Legacy product with limited security updates",
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TSXP57154M",
            "product_name": "Premium PLC",
            "model_name": "Premium",
        },
    ),
    DeviceTemplate(
        id="schneider/advantys/stb-nip-2311",
        vendor="Schneider",
        vendor_family="Advantys STB",
        model="STB NIP 2311",
        model_name="Advantys STB Network Interface",
        device_type="io_module",
        description="Advantys STB distributed I/O network interface module",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 30.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="STB{6NUM}",
            station_name_pattern="rio-stb-{seq}",
            vendor_short="SCH",
            model_short="STB",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.50",
                release_date=date(2020, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "STB NIP 2311",
            "product_name": "Advantys STB Network Interface",
            "model_name": "Advantys STB",
        },
    ),
    DeviceTemplate(
        id="schneider/inrow/dx",
        vendor="Schneider",
        vendor_family="InRow",
        model="InRow DX",
        model_name="InRow DX Precision Cooling",
        device_type="crac_unit",
        description="InRow precision cooling for data centers",

        oui_prefixes=["00:00:54", "00:C0:B7", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 30.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="INROW{8ALPHANUM}",
            station_name_pattern="crac-{location}-{seq}",
            vendor_short="SCH",
            model_short="INROW",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.0.2",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Schneider Electric InRow DX Precision Cooling",
            "sys_object_id": "1.3.6.1.4.1.318.1.3.14.5",
        },

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "InRow DX",
            "product_name": "InRow DX Precision Cooling",
            "model_name": "InRow",
        },
    ),
    DeviceTemplate(
        id="schneider/galaxy/vm",
        vendor="Schneider",
        vendor_family="Galaxy",
        model="Galaxy VM",
        model_name="Galaxy VM UPS",
        device_type="ups",
        description="Three-phase modular UPS for data centers",

        oui_prefixes=["00:00:54", "00:C0:B7", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="UPS{8ALPHANUM}",
            station_name_pattern="ups-{location}-{seq}",
            vendor_short="SCH",
            model_short="GVM",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.5.0",
                release_date=date(2023, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.3.0",
                release_date=date(2022, 3, 15),
                cves=["CVE-2022-22805"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Schneider Electric Galaxy VM UPS",
            "sys_object_id": "1.3.6.1.4.1.318.1.3.27",
        },

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "Galaxy VM",
            "product_name": "Galaxy VM UPS",
            "model_name": "Galaxy",
        },
    ),
    DeviceTemplate(
        id="schneider/rack-pdu/switched",
        vendor="Schneider",
        vendor_family="Rack PDU",
        model="Rack PDU",
        model_name="Switched Rack PDU",
        device_type="pdu",
        description="Switched metered rack power distribution unit",

        oui_prefixes=["00:00:54", "00:C0:B7", "64:3A:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 150.0,
            "mean_ms": 40.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PDU{6ALPHANUM}",
            station_name_pattern="pdu-{location}-{seq}",
            vendor_short="SCH",
            model_short="PDU",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.9.6",
                release_date=date(2023, 8, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V6.8.4",
                release_date=date(2022, 5, 15),
                cves=["CVE-2022-0715"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Schneider Electric Switched Rack PDU",
            "sys_object_id": "1.3.6.1.4.1.318.1.3.4.5",
        },

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "Rack PDU",
            "product_name": "Switched Rack PDU",
            "model_name": "Rack PDU",
        },
    ),
    DeviceTemplate(
        id="schneider/andover/cx9680",
        vendor="Schneider",
        vendor_family="Andover Continuum",
        model="CX9680",
        model_name="Andover Continuum CX9680",
        device_type="bms_controller",
        description="Advanced BMS controller for building automation",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="CX96{8NUM}",
            station_name_pattern="continuum-{location}-{seq}",
            vendor_short="SCH",
            model_short="CX96",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.8.5",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.6.0",
                release_date=date(2022, 7, 15),
                cves=["CVE-2022-22810"],
            ),
            FirmwareVariant(
                version="V2.4.0",
                release_date=date(2020, 11, 10),
                cves=["CVE-2022-22810", "CVE-2020-7477"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 67,
            "device_type": "Building Controller",
            "model_name": "Continuum CX9680",
        },

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "CX9680",
            "product_name": "Andover Continuum CX9680",
        },
    ),
    DeviceTemplate(
        id="schneider/hmi/hmist6700",
        vendor="Schneider",
        vendor_family="Harmony",
        model="HMIST6700",
        model_name="Harmony STU 6700 HMI",
        device_type="hmi",
        description="15-inch touchscreen HMI for demanding applications",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="HMIST{8NUM}",
            station_name_pattern="hmi-{location}-{seq}",
            vendor_short="SCH",
            model_short="ST67",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.0.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.2.0",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-42972"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "HMIST6700",
            "product_name": "Harmony STU 6700 HMI",
        },
    ),
    DeviceTemplate(
        id="schneider/tbox/ms-cpu32",
        vendor="Schneider",
        vendor_family="TBox",
        model="TBox MS-CPU32",
        model_name="TBox MS RTU",
        device_type="rtu",
        description="High-performance RTU for SCADA applications",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="TBOX{10NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="SCH",
            model_short="TBOX",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.3.0",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.1.0",
                release_date=date(2022, 8, 20),
                cves=["CVE-2022-45788"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TBox MS-CPU32",
            "product_name": "TBox MS RTU",
        },
    ),
    DeviceTemplate(
        id="schneider/ion/8650",
        vendor="Schneider",
        vendor_family="ION",
        model="ION8650",
        model_name="ION8650 Power Quality Meter",
        device_type="power_meter",
        description="High-accuracy power quality meter for utility revenue metering",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 7.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="ION86{8NUM}",
            station_name_pattern="meter-{location}-{seq}",
            vendor_short="SCH",
            model_short="ION86",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.005",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.100",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-22810"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "ION8650",
            "product_name": "ION8650 Power Quality Meter",
        },
    ),
    DeviceTemplate(
        id="schneider/scadapack/350",
        vendor="Schneider",
        vendor_family="SCADAPack",
        model="SCADAPack 350",
        model_name="SCADAPack 350 RTU",
        device_type="rtu",
        description="Compact RTU for remote monitoring and control",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="SP350{8NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="SCH",
            model_short="SP350",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.5.0",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V8.2.0",
                release_date=date(2022, 7, 20),
                cves=["CVE-2022-45788"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "SCADAPack-350",
            "product_name": "SCADAPack 350 RTU",
        },
    ),
    DeviceTemplate(
        id="schneider/tbox/lt2",
        vendor="Schneider",
        vendor_family="TBox",
        model="TBox LT2",
        model_name="TBox LT2 Lite RTU",
        device_type="rtu",
        description="Compact RTU for small-scale remote monitoring",

        oui_prefixes=["00:00:54", "00:80:F4"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="TBLT2{8NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="SCH",
            model_short="TBLT2",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.8.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.5.0",
                release_date=date(2022, 5, 20),
                cves=["CVE-2022-45788"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TBox-LT2",
            "product_name": "TBox LT2 Lite RTU",
        },
    ),
    DeviceTemplate(
        id="schneider/altivar/atv320",
        vendor="Schneider",
        vendor_family="Altivar",
        model="ATV320",
        model_name="ATV320",
        device_type="drive",
        description="Schneider ATV320",
        oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
        tcp_stack={
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0003,
            },
        supported_protocols=['modbus'],
        firmware_variants=[FirmwareVariant(
            version="V1.7IE18",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "ATV320",
                "major_minor_revision": "V1.7IE18",
                "product_name": "Altivar Machine ATV320",
                "model_name": "ATV320",
            },
    ),
    DeviceTemplate(
        id="schneider/altivar/atv930-generic",
        vendor="Schneider",
        vendor_family="Altivar",
        model="ATV930",
        model_name="ATV930",
        device_type="drive",
        description="Schneider ATV930",
        oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0002,
            },
        supported_protocols=['modbus', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="V2.1IE26",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "ATV930",
                "major_minor_revision": "V2.1IE26",
                "product_name": "Altivar Process ATV930",
                "model_name": "ATV930",
            },
        ethernet_ip_identity={
                "vendor_id": 67,
                "device_type": 22,
                "product_code": 930,
                "revision_major": 2,
                "revision_minor": 1,
                "product_name": "Altivar Process ATV930",
            },
    ),
    DeviceTemplate(
        id="schneider/modicon-m580/bmep586040",
        vendor="Schneider",
        vendor_family="Modicon M580",
        model="BMEP586040",
        model_name="BMEP586040",
        device_type="plc",
        description="Schneider BMEP586040",
        oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "window_scaling": None,
                "sack_permitted": True,
                "timestamps_enabled": False,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 20.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 5, 6, 10, 11],
                "exception_probability": 0.0006,
            },
        supported_protocols=['modbus', 'ethernet_ip', 'snmp'],
        protocol_quirks={
                "modbus_max_registers": 125,
                "modbus_max_coils": 2000,
                "unity_pro_compatible": True,
            },
        firmware_variants=[FirmwareVariant(
            version="3.30",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "BMEP586040",
                "major_minor_revision": "3.30",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon M580 ePAC",
                "model_name": "BMEP586040",
            },
        ethernet_ip_identity={
                "vendor_id": 67,
                "device_type": 14,
                "product_code": 586,
                "revision_major": 3,
                "revision_minor": 30,
                "serial_number": 313210061,
                "product_name": "BMEP586040",
                "state": 3,
            },
        snmp_identity={
                "sys_descr": "Schneider Electric Modicon M580 BMEP586040 Firmware V3.30",
                "sys_name": "M580-BMEP586040",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.580",
                "sys_location": "Control Room",
            },
    ),
    DeviceTemplate(
        id="schneider/magelis/hmigto5310",
        vendor="Schneider",
        vendor_family="Magelis",
        model="HMIGTO5310",
        model_name="HMIGTO5310",
        device_type="hmi",
        description="Schneider HMIGTO5310",
        oui_prefixes=['00:80:F4', '00:60:E5'],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
            },
        supported_protocols=['modbus'],
        firmware_variants=[FirmwareVariant(
            version="5.1",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "HMIGTO5310",
                "major_minor_revision": "5.1",
                "product_name": "Magelis GTO Advanced HMI",
                "model_name": "HMIGTO5310",
            },
    ),
    DeviceTemplate(
        id="schneider/tbox/lt2",
        vendor="Schneider",
        vendor_family="TBox",
        model="LT2",
        model_name="LT2",
        device_type="controller",
        description="Schneider LT2",
        oui_prefixes=['00:00:54', '00:80:F4'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.025,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "timeout_probability": 0.003,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['modbus', 'snmp'],
        firmware_variants=[FirmwareVariant(
            version="V1.48.520",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "TBox LT2",
                "major_minor_revision": "V1.48.520",
            },
        snmp_identity={
                "sys_descr": "Schneider Electric TBox LT2 RTU V1.48.520",
                "sys_object_id": "1.3.6.1.4.1.3833.2.1.2",
                "sys_name": "TBOX-LT2-001",
                "sys_location": "Field Cabinet",
            },
    ),
    DeviceTemplate(
        id="schneider/lexium-32/lxm32md18m2",
        vendor="Schneider",
        vendor_family="Lexium 32",
        model="LXM32MD18M2",
        model_name="LXM32MD18M2",
        device_type="drive",
        description="Schneider LXM32MD18M2",
        oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
        supported_protocols=['modbus', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="V2.62",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "LXM32MD18M2",
                "major_minor_revision": "V2.62",
                "product_name": "Lexium 32 Servo Drive",
                "model_name": "LXM32",
            },
        ethernet_ip_identity={
                "vendor_id": 67,
                "device_type": 3,
                "product_code": 32,
                "revision_major": 2,
                "revision_minor": 62,
                "serial_number": 1743816978,
                "product_name": "LXM32MD18M2",
                "state": 3,
            },
    ),
    DeviceTemplate(
        id="schneider/tbox/ms-cpu32",
        vendor="Schneider",
        vendor_family="TBox",
        model="MS-CPU32",
        model_name="MS-CPU32",
        device_type="traffic_controller",
        description="Schneider MS-CPU32",
        oui_prefixes=['00:00:54', '00:80:F4'],
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
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['modbus', 'snmp'],
        firmware_variants=[FirmwareVariant(
            version="V1.50.598",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Schneider Electric",
                "product_code": "TBox MS-CPU32",
                "major_minor_revision": "V1.50.598",
            },
        snmp_identity={
                "sys_descr": "Schneider Electric TBox MS-CPU32 RTU V1.50.598",
                "sys_object_id": "1.3.6.1.4.1.3833.2.1.1",
                "sys_name": "TBOX-001",
                "sys_location": "Tunnel Monitoring",
                "ntcip_device_type": "rtu",
            },
    ),
]
