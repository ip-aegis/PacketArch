# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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

        supported_protocols=["modbus_tcp", "profinet"],

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

        snmp_identity={
            "sys_descr": "ABB AC500-eCo PM5630 V3.5.2",
            "sys_object_id": "1.3.6.1.4.1.26381.711.49",
            "sys_name": "AC500--PM5630-001",
            "sys_location": "Production Floor",
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

        # AC500 V3 hosts an OPC UA server natively (CmpOPCUAServer
        # component in CODESYS V3 runtime).
        supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

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
            "product_name": "PM590-ETH AC500 CPU",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "ABB AC500 PM590-ETH V3.1.2",
            "sys_object_id": "1.3.6.1.4.1.26381.649.92",
            "sys_name": "AC500-PM590--001",
            "sys_location": "Production Floor",
        },

        opc_ua_identity={
            "application_name": "ABB AC500 PM590 OPC UA Server",
            "application_uri": "urn:ABB:AC500:PM590-ETH",
            "product_uri": "http://www.abb.com/ac500",
            "manufacturer_name": "ABB",
            "product_name": "AC500 PM590-ETH OPC UA Server",
            "software_version": "3.1.2",
            "build_number": "V3.1.2",
            "build_date": "2023-08-01T00:00:00Z",
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

        # AC500 V3 hosts an OPC UA server via CODESYS V3 runtime.
        # PM583 also speaks EtherNet/IP via the CM579 communication
        # module — declaring it so cross-vendor (Fanuc / Rockwell)
        # robot / drive flows have a shared industrial protocol.
        supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

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

        ethernet_ip_identity={
            "vendor_id": 75,  # ABB ODVA vendor ID
            "device_type": 14,  # Programmable Logic Controller
            "product_code": 583,
            "product_name": "AC500 PM583-ETH (CM579-PNIO module)",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "ABB AC500 PM583-ETH V3.0.4",
            "sys_object_id": "1.3.6.1.4.1.26381.724.51",
            "sys_name": "AC500-PM583--001",
            "sys_location": "Production Floor",
        },

        opc_ua_identity={
            "application_name": "ABB AC500 PM583 OPC UA Server",
            "application_uri": "urn:ABB:AC500:PM583-ETH",
            "product_uri": "http://www.abb.com/ac500",
            "manufacturer_name": "ABB",
            "product_name": "AC500 PM583-ETH OPC UA Server",
            "software_version": "3.0.4",
            "build_number": "V3.0.4",
            "build_date": "2023-06-01T00:00:00Z",
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

        snmp_identity={
            "sys_descr": "ABB AC500-eCo PM554-TP-ETH V2.4.1",
            "sys_object_id": "1.3.6.1.4.1.26381.418.23",
            "sys_name": "AC500--PM554--001",
            "sys_location": "Remote Site",
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

        supported_protocols=["modbus_tcp", "ethernet_ip"],

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
            "product_name": "ACS880-01 INDUSTRIAL DRIVE",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "ABB ACS880-01 Industrial Drive V2.60",
            "sys_object_id": "1.3.6.1.4.1.26381.643.45",
            "sys_name": "ACS880-INDUST-001",
            "sys_location": "Motor Control Center",
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

        # CI501-PNIO supports both PROFINET and EtherNet/IP via the
        # AC500 V3 / AC500-eCo communication interface modules. Declaring
        # both so cross-vendor cells reach the IO over a shared protocol.
        supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

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

        ethernet_ip_identity={
            "vendor_id": 75,
            "device_type": 7,  # General Purpose Discrete I/O
            "product_code": 501,
            "product_name": "CI501-PNIO Remote I/O (EIP variant)",
            "state": 3,
        },

        profinet_identity={
            "vendor_id": 0x0037,  # ABB PROFINET vendor ID
            "device_id": 0x0501,
            "device_role": 1,
            "im0_manufacturer": "ABB",
            "im0_order_id": "CI501-PNIO",
        },

        snmp_identity={
            "sys_descr": "ABB CI501 Remote I/O V3.1.0",
            "sys_object_id": "1.3.6.1.4.1.26381.305.43",
            "sys_name": "CI501-REMOTE-001",
            "sys_location": "Industrial Network",
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

        snmp_identity={
            "sys_descr": "ABB REF615 Feeder Protection Relay V5.1 FP2",
            "sys_object_id": "1.3.6.1.4.1.26381.291.40",
            "sys_name": "REF615-FEEDER-001",
            "sys_location": "Substation",
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

        snmp_identity={
            "sys_descr": "ABB REX640 Protection and Control IED V2.2.1",
            "sys_object_id": "1.3.6.1.4.1.26381.332.59",
            "sys_name": "REX640-PROTEC-001",
            "sys_location": "Substation",
        },

        iec104_identity={
            "vendor_name": "ABB",
            "device_name": "Relion REX640 Protection and Control IED",
            "hardware_version": "REX640",
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

        snmp_identity={
            "sys_descr": "ABB ACS580 General Purpose Drive V2.10",
            "sys_object_id": "1.3.6.1.4.1.26381.813.48",
            "sys_name": "ACS580-GENERA-001",
            "sys_location": "Motor Control Center",
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

        snmp_identity={
            "sys_descr": "ABB CP620 Control Panel V1.80",
            "sys_object_id": "1.3.6.1.4.1.26381.919.0",
            "sys_name": "CP620-CONTRO-001",
            "sys_location": "Control Room",
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

        snmp_identity={
            "sys_descr": "ABB RTU560 Remote Terminal Unit V12.4.3",
            "sys_object_id": "1.3.6.1.4.1.26381.236.90",
            "sys_name": "RTU560-REMOTE-001",
            "sys_location": "Remote Site",
        },

        iec104_identity={
            "vendor_name": "ABB",
            "device_name": "RTU560 Remote Terminal Unit",
            "hardware_version": "RTU560",
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
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
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

        snmp_identity={
            "sys_descr": "ABB ACS580 V2.76",
            "sys_object_id": "1.3.6.1.4.1.26381.820.58",
            "sys_name": "ACS580-001",
            "sys_location": "Motor Control Center",
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
        supported_protocols=['modbus_tcp'],
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

        snmp_identity={
            "sys_descr": "ABB M2BAX 180MLB V1.0",
            "sys_object_id": "1.3.6.1.4.1.26381.756.21",
            "sys_name": "M2BAX-180MLB-001",
            "sys_location": "Industrial Network",
        },
    ),

    # ------------------------------------------------------------------
    # ABB REL630 — Relion 630 series line distance protection IED.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="abb/relion/rel630",
        vendor="ABB",
        vendor_family="Relion 630",
        model="REL630",
        model_name="ABB REL630 Line Distance Protection",
        device_type="protection_relay",
        description="Relion 630 series distance protection relay for sub-transmission lines",

        oui_prefixes=["00:21:99", "00:24:2B", "00:1F:ED", "00:C0:53", "C4:93:00"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABBREL{8NUM}",
            station_name_pattern="relay-rel630-{seq}",
            vendor_short="ABB",
            model_short="REL630",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.2.3",
                release_date=date(2024, 3, 2),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.2.1",
                release_date=date(2022, 9, 14),
                cves=["CVE-2021-22276"],
            ),
            FirmwareVariant(
                version="V2.1.0",
                release_date=date(2020, 6, 22),
                cves=["CVE-2021-22276", "CVE-2022-26143"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "REL630",
            "product_name": "Relion REL630 Line Distance Protection",
        },

        snmp_identity={
            "sys_descr": "ABB Relion REL630 Line Distance Protection V2.2.3",
            "sys_object_id": "1.3.6.1.4.1.26381.630.11",
            "sys_name": "RELION-REL630-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "ABB",
            "device_name": "Relion REL630 Line Distance Protection",
            "hardware_version": "REL630",
        },

        iec61850_identity={
            "ied_name": "ABB_REL630_IED",
            "vendor": "ABB",
            "software_version": "V2.2.3",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "ABB_REL630.icd",
        },
    ),

    # ------------------------------------------------------------------
    # ABB RED615 — Relion 615 series line differential protection IED.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="abb/relion/red615",
        vendor="ABB",
        vendor_family="Relion 615",
        model="RED615",
        model_name="ABB RED615 Line Differential Protection",
        device_type="protection_relay",
        description="Relion 615 series line differential protection relay (87L)",

        oui_prefixes=["00:21:99", "00:24:2B", "00:1F:ED", "00:C0:53", "C4:93:00"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABBRED{8NUM}",
            station_name_pattern="relay-red615-{seq}",
            vendor_short="ABB",
            model_short="RED615",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.0",
                release_date=date(2024, 4, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.2",
                release_date=date(2022, 8, 18),
                cves=["CVE-2023-26517"],
            ),
            FirmwareVariant(
                version="V4.0",
                release_date=date(2020, 5, 22),
                cves=["CVE-2023-26517", "CVE-2021-22276"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "RED615",
            "product_name": "Relion RED615 Line Differential Protection",
        },

        snmp_identity={
            "sys_descr": "ABB Relion RED615 Line Differential Protection V5.0",
            "sys_object_id": "1.3.6.1.4.1.26381.615.7",
            "sys_name": "RELION-RED615-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "ABB",
            "device_name": "Relion RED615 Line Differential Protection",
            "hardware_version": "RED615",
        },

        iec61850_identity={
            "ied_name": "ABB_RED615_IED",
            "vendor": "ABB",
            "software_version": "V5.0",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "ABB_RED615.icd",
        },
    ),

    # ------------------------------------------------------------------
    # ABB REL670 — Relion 670 series high-end transmission distance protection.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="abb/relion/rel670",
        vendor="ABB",
        vendor_family="Relion 670",
        model="REL670",
        model_name="ABB REL670 Line Distance Protection",
        device_type="protection_relay",
        description="Relion 670 series high-end transmission line distance protection IED",

        oui_prefixes=["00:21:99", "00:24:2B", "00:1F:ED", "00:C0:53", "C4:93:00"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.4,
            "std_dev_ms": 0.8,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850", "iec104"],

        instance_rules=InstanceGenerationRules(
            serial_format="ABBREL{8NUM}",
            station_name_pattern="relay-rel670-{seq}",
            vendor_short="ABB",
            model_short="REL670",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.2.5",
                release_date=date(2024, 4, 12),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.2.3",
                release_date=date(2022, 11, 8),
                cves=["CVE-2023-26517"],
            ),
            FirmwareVariant(
                version="V2.2.0",
                release_date=date(2020, 7, 30),
                cves=["CVE-2023-26517", "CVE-2022-26143", "CVE-2021-22276"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "REL670",
            "product_name": "Relion REL670 Line Distance Protection",
        },

        snmp_identity={
            "sys_descr": "ABB Relion REL670 Line Distance Protection V2.2.5",
            "sys_object_id": "1.3.6.1.4.1.26381.670.14",
            "sys_name": "RELION-REL670-001",
            "sys_location": "Transmission Substation",
        },

        dnp3_identity={
            "vendor_name": "ABB",
            "device_name": "Relion REL670 Line Distance Protection",
            "hardware_version": "REL670",
        },

        iec104_identity={
            "vendor_name": "ABB",
            "device_name": "Relion REL670 Line Distance Protection",
            "hardware_version": "REL670",
        },

        iec61850_identity={
            "ied_name": "ABB_REL670_IED",
            "vendor": "ABB",
            "software_version": "V2.2.5",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "ABB_REL670.icd",
        },
    ),

    # ------------------------------------------------------------------
    # ABB Symphony Plus HPG800 — DCS Harmony Process Gateway / power-plant controller.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="abb/symphony-plus/hpg800",
        vendor="ABB",
        vendor_family="Symphony Plus",
        model="HPG800",
        model_name="ABB Symphony Plus HPG800",
        device_type="controller",
        description="Symphony Plus Harmony Process Gateway DCS controller for power generation",

        oui_prefixes=["00:21:99", "00:24:2B", "00:1F:ED", "00:C0:53", "C4:93:00"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 4.5,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "opc_ua", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="HPG{10NUM}",
            station_name_pattern="hpg800-{seq}",
            vendor_short="ABB",
            model_short="HPG800",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.2.1",
                release_date=date(2024, 2, 18),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.1.0",
                release_date=date(2022, 6, 24),
                cves=["CVE-2022-26143"],
            ),
        ],

        modbus_identity={
            "vendor_name": "ABB",
            "product_code": "HPG800",
            "product_name": "Symphony Plus HPG800 Harmony Process Gateway",
        },

        snmp_identity={
            "sys_descr": "ABB Symphony Plus HPG800 Harmony Process Gateway V3.2.1",
            "sys_object_id": "1.3.6.1.4.1.26381.800.18",
            "sys_name": "HPG800-DCS-001",
            "sys_location": "Power Plant Control Room",
        },

        opc_ua_identity={
            "application_name": "ABB Symphony Plus HPG800",
            "application_uri": "urn:ABB:SymphonyPlus:HPG800",
            "product_uri": "http://www.abb.com/control-systems/symphony-plus",
            "manufacturer_name": "ABB",
            "product_name": "Symphony Plus HPG800",
            "software_version": "3.2.1",
            "build_number": "8321",
            "build_date": "2024-02-18T08:00:00Z",
        },
    ),
]
