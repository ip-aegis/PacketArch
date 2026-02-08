"""Emerson device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="emerson/deltav/s-series",
        vendor="Emerson",
        vendor_family="DeltaV",
        model="S-series",
        model_name="DeltaV S-series Controller",
        device_type="dcs_controller",
        description="Process automation controller for DeltaV DCS",

        oui_prefixes=["00:A0:F8", "00:50:43", "00:60:35"],

        tcp_stack={
            "ttl": 128,  # Windows-based
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="DV{2ALPHA}{8NUM}",
            station_name_pattern="dcs-{location}-{seq}",
            vendor_short="EMR",
            model_short="DVS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V15.3",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V14.3",
                release_date=date(2022, 7, 15),
                cves=["CVE-2022-29966"],
            ),
            FirmwareVariant(
                version="V13.3",
                release_date=date(2020, 12, 10),
                cves=["CVE-2022-29966", "CVE-2020-16233"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "DeltaV-S",
            "product_name": "DeltaV S-series Controller",
        },
    ),
    DeviceTemplate(
        id="emerson/roc/800l",
        vendor="Emerson",
        vendor_family="ROC",
        model="ROC800L",
        model_name="ROC800L Remote Operations Controller",
        device_type="rtu",
        description="Flow computer and RTU for oil & gas",

        oui_prefixes=["00:A0:F8", "00:90:E8"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="ROC{10NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="EMR",
            model_short="ROC8",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.91",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.80",
                release_date=date(2022, 4, 20),
                cves=["CVE-2022-30264"],
            ),
            FirmwareVariant(
                version="V3.50",
                release_date=date(2019, 8, 15),
                cves=["CVE-2022-30264", "CVE-2019-10971"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "ROC800L",
            "product_name": "ROC800L Remote Operations Controller",
        },
    ),
    DeviceTemplate(
        id="emerson/deltav/md-plus",
        vendor="Emerson",
        vendor_family="DeltaV",
        model="MD Plus",
        model_name="DeltaV MD Plus Controller",
        device_type="dcs_controller",
        description="Mid-range DeltaV controller for small to medium applications",

        oui_prefixes=["00:A0:F8", "00:50:43", "00:60:35"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 25.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="DVMD{8NUM}",
            station_name_pattern="dcs-md-{seq}",
            vendor_short="EMR",
            model_short="DVMD",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V15.3",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V14.3",
                release_date=date(2022, 7, 15),
                cves=["CVE-2022-29966"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "DeltaV-MD-Plus",
            "product_name": "DeltaV MD Plus Controller",
        },
    ),
    DeviceTemplate(
        id="emerson/roc/800",
        vendor="Emerson",
        vendor_family="ROC",
        model="ROC800",
        model_name="ROC800 Remote Operations Controller",
        device_type="rtu",
        description="Standard ROC800 flow computer and RTU",

        oui_prefixes=["00:A0:F8", "00:90:E8"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
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
            serial_format="ROC8{10NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="EMR",
            model_short="ROC8",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.91",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.80",
                release_date=date(2022, 4, 20),
                cves=["CVE-2022-30264"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "ROC800",
            "product_name": "ROC800 Remote Operations Controller",
        },
    ),
    DeviceTemplate(
        id="emerson/rosemount/3051s",
        vendor="Emerson",
        vendor_family="Rosemount",
        model="3051S",
        model_name="Rosemount 3051S Pressure Transmitter",
        device_type="transmitter",
        description="SuperModule pressure transmitter with advanced diagnostics",

        oui_prefixes=["00:A0:F8", "00:50:43"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="RM3051{8NUM}",
            station_name_pattern="pt-{location}-{seq}",
            vendor_short="EMR",
            model_short="3051",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V11.3",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V11.0",
                release_date=date(2022, 5, 15),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "3051S",
            "product_name": "Rosemount 3051S Pressure Transmitter",
        },
    ),
    DeviceTemplate(
        id="emerson/micromotion/5700",
        vendor="Emerson",
        vendor_family="Micro Motion",
        model="5700",
        model_name="Micro Motion 5700 Transmitter",
        device_type="flow_meter",
        description="Coriolis flow transmitter for custody transfer",

        oui_prefixes=["00:A0:F8", "00:50:43"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 7.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="MM57{10NUM}",
            station_name_pattern="flow-{location}-{seq}",
            vendor_short="EMR",
            model_short="MM57",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.2",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V8.0",
                release_date=date(2022, 6, 20),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "5700",
            "product_name": "Micro Motion 5700 Transmitter",
        },
    ),
    DeviceTemplate(
        id="emerson/fisher/dvc6200",
        vendor="Emerson",
        vendor_family="Fisher FIELDVUE",
        model="DVC6200",
        model_name="DVC6200 Digital Valve Controller",
        device_type="valve_positioner",
        description="Digital valve controller with advanced diagnostics",

        oui_prefixes=["00:A0:F8", "00:50:43"],

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

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="DVC{10NUM}",
            station_name_pattern="valve-{location}-{seq}",
            vendor_short="EMR",
            model_short="DVC6",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.4",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V6.2",
                release_date=date(2022, 4, 20),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Emerson Process Management",
            "product_code": "DVC6200",
            "product_name": "DVC6200 Digital Valve Controller",
        },
    ),
    DeviceTemplate(
        id="emerson/deltav/historian",
        vendor="Emerson",
        vendor_family="DeltaV",
        model="Continuous Historian",
        model_name="DeltaV Continuous Historian",
        device_type="historian",
        description="Process historian for DeltaV DCS",

        oui_prefixes=["00:A0:F8", "00:50:43", "00:12:A9"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 150.0,
            "mean_ms": 40.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },

        supported_protocols=["opc_ua", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="DVHIST{8HEX}",
            station_name_pattern="historian-{seq}",
            vendor_short="EMR",
            model_short="DVHIST",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V14.3",
                release_date=date(2023, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],
    ),
    DeviceTemplate(
        id="emerson/deltav/ows",
        vendor="Emerson",
        vendor_family="DeltaV",
        model="OWS",
        model_name="DeltaV Operator Workstation",
        device_type="hmi",
        description="DeltaV operator workstation for process monitoring",

        oui_prefixes=["00:A0:F8", "00:50:43", "00:12:A9"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },

        supported_protocols=["opc_ua", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="DVOWS{8HEX}",
            station_name_pattern="ows-{seq}",
            vendor_short="EMR",
            model_short="OWS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V14.3",
                release_date=date(2023, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],
    ),
]
