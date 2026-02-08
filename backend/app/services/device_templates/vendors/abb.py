"""ABB device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="abb/ac500/pm5630",
        vendor="ABB",
        vendor_family="AC500",
        model="PM5630-2ETH",
        model_name="AC500-eCo PM5630",
        device_type="plc",
        description="High-performance AC500 PLC with dual Ethernet",

        oui_prefixes=["00:21:99", "00:24:2B", "00:1F:ED", "C4:93:00"],

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
            "mean_ms": 7.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "profinet", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB-{8HEX}",
            station_name_pattern="{role}-ac500-{seq}",
            vendor_short="ABB",
            model_short="PM56",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.5.2",
                release_date=date(2024, 1, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.2.0",
                release_date=date(2022, 5, 15),
                cves=["CVE-2022-26007"],
            ),
            FirmwareVariant(
                version="V3.0.1",
                release_date=date(2020, 11, 20),
                cves=["CVE-2022-26007", "CVE-2020-24680"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "PM5630-2ETH",
            "vendor_url": "http://www.abb.com",
            "product_name": "AC500-eCo PLC",
            "model_name": "PM5630",
        },

        profinet_identity={
            "vendor_id": 0x0037,
            "device_id": 0x5630,
            "device_role": 1,
            "im0_manufacturer": "ABB",
            "im0_order_id": "PM5630-2ETH",
        },
    ),
    DeviceTemplate(
        id="abb/ac500/pm590-eth",
        vendor="ABB",
        vendor_family="AC500",
        model="PM590-ETH",
        model_name="AC500 PM590-ETH",
        device_type="plc",
        description="High-performance AC500 CPU with Ethernet interface",

        oui_prefixes=["00:20:99", "00:21:99", "00:24:CB"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "profinet", "ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB{8HEX}",
            station_name_pattern="{role}-pm590-{seq}",
            vendor_short="ABB",
            model_short="PM590",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.1.2",
                release_date=date(2023, 8, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.9.0",
                release_date=date(2021, 4, 15),
                cves=["CVE-2020-24680"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "PM590-ETH",
            "vendor_url": "http://www.abb.com",
            "product_name": "AC500 PM590",
            "model_name": "AC500",
        },

        ethernet_ip_identity={
            "vendor_id": 285,  # ABB
            "device_type": 14,  # Programmable Logic Controller
            "product_code": 590,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="abb/ac500/pm583-eth",
        vendor="ABB",
        vendor_family="AC500",
        model="PM583-ETH",
        model_name="AC500 PM583-ETH",
        device_type="plc",
        description="AC500 CPU with Ethernet interface for medium applications",

        oui_prefixes=["00:20:99", "00:21:99", "00:24:CB"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.5,
            "max_ms": 25.0,
            "mean_ms": 6.0,
            "std_dev_ms": 3.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB{8HEX}",
            station_name_pattern="{role}-pm583-{seq}",
            vendor_short="ABB",
            model_short="PM583",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.0.4",
                release_date=date(2023, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "PM583-ETH",
            "vendor_url": "http://www.abb.com",
            "product_name": "AC500 PM583",
            "model_name": "AC500",
        },
    ),
    DeviceTemplate(
        id="abb/ac500-eco/pm554-tp-eth",
        vendor="ABB",
        vendor_family="AC500-eCo",
        model="PM554-TP-ETH",
        model_name="AC500-eCo PM554-TP-ETH",
        device_type="rtu",
        description="Compact AC500-eCo CPU for remote applications",

        oui_prefixes=["00:20:99", "00:21:99"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 35.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB{6HEX}",
            station_name_pattern="{role}-pm554-{seq}",
            vendor_short="ABB",
            model_short="PM554",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.4.1",
                release_date=date(2023, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "PM554-TP-ETH",
            "vendor_url": "http://www.abb.com",
            "product_name": "AC500-eCo PM554",
            "model_name": "AC500-eCo",
        },
    ),
    DeviceTemplate(
        id="abb/acs880/acs880-01",
        vendor="ABB",
        vendor_family="ACS880",
        model="ACS880-01",
        model_name="ACS880-01 Industrial Drive",
        device_type="drive",
        description="High-performance industrial drive for demanding applications",

        oui_prefixes=["00:20:99", "00:21:99", "00:24:CB"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 12.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "profinet", "ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB{8HEX}",
            station_name_pattern="{role}-acs880-{seq}",
            vendor_short="ABB",
            model_short="ACS880",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.60",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.40",
                release_date=date(2021, 6, 15),
                cves=["CVE-2021-22278"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "ACS880-01",
            "vendor_url": "http://www.abb.com",
            "product_name": "ACS880 Industrial Drive",
            "model_name": "ACS880",
        },

        ethernet_ip_identity={
            "vendor_id": 285,  # ABB
            "device_type": 2,  # AC Drive
            "product_code": 880,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="abb/ac500/ci501",
        vendor="ABB",
        vendor_family="AC500",
        model="CI501",
        model_name="CI501 Remote I/O",
        device_type="io_module",
        description="CI501 communication interface for distributed I/O",

        oui_prefixes=["00:20:99", "00:21:99"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB{6HEX}",
            station_name_pattern="rio-{location}-{seq}",
            vendor_short="ABB",
            model_short="CI501",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.1.0",
                release_date=date(2023, 5, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "CI501",
            "vendor_url": "http://www.abb.com",
            "product_name": "CI501 Remote I/O",
            "model_name": "AC500",
        },
    ),
    DeviceTemplate(
        id="abb/relion/ref615",
        vendor="ABB",
        vendor_family="Relion",
        model="REF615",
        model_name="REF615 Feeder Protection Relay",
        device_type="protection_relay",
        description="Feeder protection and control relay for distribution",

        oui_prefixes=["00:21:99", "00:24:2B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB615{8NUM}",
            station_name_pattern="relay-ref615-{seq}",
            vendor_short="ABB",
            model_short="R615",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.1 FP2",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.0 FP3",
                release_date=date(2022, 8, 20),
                cves=["CVE-2022-28613"],
            ),
            FirmwareVariant(
                version="V4.1 FP2",
                release_date=date(2020, 10, 10),
                cves=["CVE-2022-28613", "CVE-2020-8481"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "REF615",
            "product_name": "Relion REF615 Feeder Protection",
        },
    ),
    DeviceTemplate(
        id="abb/relion/rex640",
        vendor="ABB",
        vendor_family="Relion",
        model="REX640",
        model_name="REX640 Protection and Control IED",
        device_type="protection_relay",
        description="Next-generation protection and control for utility applications",

        oui_prefixes=["00:21:99", "00:24:2B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 6.0,
            "mean_ms": 1.2,
            "std_dev_ms": 0.8,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850", "iec104"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB640{8NUM}",
            station_name_pattern="relay-rex640-{seq}",
            vendor_short="ABB",
            model_short="R640",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.2.1",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.1.0",
                release_date=date(2022, 10, 15),
                cves=["CVE-2023-2184"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "REX640",
            "product_name": "Relion REX640 Protection IED",
        },
    ),
    DeviceTemplate(
        id="abb/drives/acs580",
        vendor="ABB",
        vendor_family="ACS580",
        model="ACS580-01-073A-4",
        model_name="ACS580 General Purpose Drive",
        device_type="drive",
        description="General purpose variable frequency drive with built-in features",

        oui_prefixes=["00:21:99", "00:24:2B"],

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

        supported_protocols=["modbus_tcp", "profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ACS5{10NUM}",
            station_name_pattern="vfd-{location}-{seq}",
            vendor_short="ABB",
            model_short="ACS5",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.10",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.05",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-26006"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "ACS580-01-073A-4",
            "product_name": "ACS580 General Purpose Drive",
        },

        profinet_identity={
            "vendor_id": 0x0037,
            "device_id": 0x0580,
            "device_role": 1,
            "im0_manufacturer": "ABB",
            "im0_order_id": "ACS580-01-073A-4",
        },
    ),
    DeviceTemplate(
        id="abb/hmi/cp620",
        vendor="ABB",
        vendor_family="CP600",
        model="CP620",
        model_name="CP620 Control Panel",
        device_type="hmi",
        description="6-inch touch panel for PLC integration",

        oui_prefixes=["00:21:99", "00:24:2B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 4.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABB-CP{8NUM}",
            station_name_pattern="hmi-{location}-{seq}",
            vendor_short="ABB",
            model_short="CP62",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.80",
                release_date=date(2024, 1, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.65",
                release_date=date(2022, 5, 20),
                cves=["CVE-2022-26006"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "CP620",
            "product_name": "CP620 Control Panel",
        },
    ),
    DeviceTemplate(
        id="abb/rtu/rtu560",
        vendor="ABB",
        vendor_family="RTU560",
        model="RTU560",
        model_name="RTU560 Remote Terminal Unit",
        device_type="rtu",
        description="Modular RTU for power utility automation",

        oui_prefixes=["00:21:99", "00:24:2B"],

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
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec104"],

        instance_rules=InstanceGenerationRules(
            serial_format="RTU56{8NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="ABB",
            model_short="R560",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V12.4.3",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V12.2.0",
                release_date=date(2022, 6, 10),
                cves=["CVE-2022-26007"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "RTU560",
            "product_name": "RTU560 Remote Terminal Unit",
        },
    ),
    DeviceTemplate(
        id="abb/acs580/acs580",
        vendor="ABB",
        vendor_family="ACS580",
        model="ACS580",
        model_name="ACS580",
        device_type="drive",
        description="ABB ACS580",
        oui_prefixes=['00:20:99', '00:21:99', 'CC:DA:0C'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "exponential",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.00025,
            },
        supported_protocols=['modbus', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="2.76",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "ABB",
                "product_code": "ACS580-01",
                "major_minor_revision": "V2.76",
                "vendor_url": "http://www.abb.com",
                "product_name": "ACS580-01 General Purpose Drive",
                "model_name": "Variable Speed Drive",
            },
        ethernet_ip_identity={
                "vendor_id": 285,
                "device_type": 2,
                "product_code": 580,
                "revision_major": 2,
                "revision_minor": 76,
                "serial_number": 2880439680,
                "product_name": "ACS580-01 General Purpose Drive",
                "state": 3,
            },
    ),
    DeviceTemplate(
        id="abb/m2bax/m2bax-180mlb",
        vendor="ABB",
        vendor_family="M2BAX",
        model="M2BAX 180MLB",
        model_name="M2BAX 180MLB",
        device_type="motor",
        description="ABB M2BAX 180MLB",
        oui_prefixes=['00:20:99', '00:21:99', 'CC:DA:0C'],
        tcp_stack={
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
        supported_protocols=['modbus'],
        firmware_variants=[FirmwareVariant(
            version="1.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "ABB",
                "product_code": "M2BAX 180MLB",
                "major_minor_revision": "V1.0",
                "product_name": "M2BAX 180MLB Induction Motor",
                "model_name": "Electric Motor",
            },
    ),
]
