"""Japanese PLC device templates (Omron, Mitsubishi)."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="omron/nj/nj501-1300",
        vendor="Omron",
        vendor_family="NJ Series",
        model="NJ501-1300",
        model_name="NJ501 Machine Controller",
        device_type="plc",
        description="Machine automation controller with EtherCAT and EtherNet/IP",

        oui_prefixes=["00:00:74", "00:04:C7", "00:0C:DB"],

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

        supported_protocols=["ethernet_ip", "fins", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="NJ{2ALPHA}{8NUM}",
            station_name_pattern="{role}-nj501-{seq}",
            vendor_short="OMR",
            model_short="NJ501",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.64",
                release_date=date(2024, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.49",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-34151"],
                notes="Vulnerable to authentication bypass via FINS",
            ),
            FirmwareVariant(
                version="V1.40",
                release_date=date(2021, 5, 10),
                cves=["CVE-2022-34151", "CVE-2022-33971"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 47,
            "device_type": 14,
            "product_code": 501,
            "state": 3,
        },
    ),
    DeviceTemplate(
        id="omron/cj2m/cj2m-cpu35",
        vendor="Omron",
        vendor_family="CJ2M Series",
        model="CJ2M-CPU35",
        model_name="CJ2M CPU Unit",
        device_type="plc",
        description="High-speed compact PLC for machine control",

        oui_prefixes=["00:00:74", "00:04:C7"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 25.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["fins", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="CJ{10NUM}",
            station_name_pattern="{role}-cj2m-{seq}",
            vendor_short="OMR",
            model_short="CJ2M",
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
                version="V2.0",
                release_date=date(2021, 11, 20),
                cves=["CVE-2022-34151"],
            ),
        ],
    ),
    DeviceTemplate(
        id="mitsubishi/iq-r/r08cpu",
        vendor="Mitsubishi",
        vendor_family="iQ-R Series",
        model="R08CPU",
        model_name="MELSEC iQ-R CPU",
        device_type="plc",
        description="High-speed universal CPU module for iQ-R platform",

        oui_prefixes=["00:00:7E", "00:04:0F", "00:50:13"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["slmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="{3ALPHA}{9NUM}",
            station_name_pattern="{role}-iqr-{seq}",
            vendor_short="MIT",
            model_short="R08",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V53",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V49",
                release_date=date(2022, 12, 15),
                cves=["CVE-2022-40265"],
                notes="Remote code execution via malformed packets",
            ),
            FirmwareVariant(
                version="V42",
                release_date=date(2021, 4, 20),
                cves=["CVE-2022-40265", "CVE-2021-20609"],
            ),
        ],
    ),
    DeviceTemplate(
        id="mitsubishi/fx5/fx5u-32mt",
        vendor="Mitsubishi",
        vendor_family="FX5 Series",
        model="FX5U-32MT/ES",
        model_name="MELSEC FX5U Compact PLC",
        device_type="plc",
        description="Compact PLC with built-in Ethernet",

        oui_prefixes=["00:00:7E", "00:04:0F"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 30.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["slmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="FX5{8NUM}",
            station_name_pattern="{role}-fx5-{seq}",
            vendor_short="MIT",
            model_short="FX5U",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.280",
                release_date=date(2024, 1, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.220",
                release_date=date(2022, 6, 20),
                cves=["CVE-2022-25164"],
            ),
        ],
    ),
]
