# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cisco / Cisco Industrial device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="cisco/ie3300/8t2s",
        vendor="Cisco",
        vendor_family="IE3300",
        model="IE-3300-8T2S",
        model_name="Catalyst IE3300 Rugged Switch",
        device_type="network_switch",
        description="8-port rugged industrial Ethernet switch with 2 SFP",

        oui_prefixes=["00:26:98", "00:1A:A1", "00:17:0E", "F8:C2:88", "3C:08:F6"],

        tcp_stack={
            "ttl": 64,  # IOS XE
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FCW{8ALPHANUM}",
            station_name_pattern="ie3300-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE33",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.12.02",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.9.04",
                release_date=date(2023, 6, 15),
                cves=["CVE-2023-20198", "CVE-2022-20919"],
            ),
            FirmwareVariant(
                version="17.6.05",
                release_date=date(2022, 3, 20),
                cves=["CVE-2023-20198", "CVE-2022-20919"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3300 Software (IE3300-UNIVERSALK9-M), Version 17.12.02, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.2824",
        },

        lldp_identity={
            "system_name": "IE-3300-8T2S",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3300 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-3300-8T2S.local",
            "platform": "cisco IE-3300-8T2S",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3300 Software (IE3300-UNIVERSALK9-M), Version 17.12.02",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },
    ),
    DeviceTemplate(
        id="cisco/ie4000/8gt4g",
        vendor="Cisco",
        vendor_family="IE4000",
        model="IE-4000-8GT4G-E",
        model_name="Catalyst IE4000 Industrial Ethernet Switch",
        device_type="network_switch",
        description="8x 10/100/1000 + 4x combo GE industrial managed switch",

        oui_prefixes=["00:26:98", "00:1A:A1", "00:17:0E", "F8:C2:88"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": 5,
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

        supported_protocols=["snmp", "lldp", "cdp", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FCW{8ALPHANUM}",
            station_name_pattern="ie4000-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE40",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="15.2(8)E",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="15.2(7)E6",
                release_date=date(2022, 9, 10),
                cves=["CVE-2022-20919"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software, IE4000 Software (IE4000-UNIVERSAL-M) V15.2(8)E",
            "sys_object_id": "1.3.6.1.4.1.9.1.2238",
        },

        lldp_identity={
            "system_name": "IE-4000-8GT4G",
            "system_description": "Cisco IOS Software, Catalyst IE4000 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-4000-8GT4G.local",
            "platform": "cisco IE-4000-8GT4G-E",
            "software_version": "Cisco IOS Software, IE4000 Software (IE4000-UNIVERSAL-M) V15.2(8)E",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },
    ),
    DeviceTemplate(
        id="cisco/ie9320/24p4x",
        vendor="Cisco",
        vendor_family="IE9300",
        model="IE-9320-24P4X-E",
        model_name="Catalyst IE9320 Rugged Switch 24-Port PoE+ 10G",
        device_type="network_switch",
        description="24x GE PoE+ RJ45 + 4x 10G SFP+ industrial switch with Network Essentials",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,  # IOS XE
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.6,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FJC{8ALPHANUM}",
            station_name_pattern="ie9320-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE93",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="17.9.05",
                release_date=date(2023, 9, 1),
                cves=["CVE-2023-20198"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.3054",
        },

        lldp_identity={
            "system_name": "IE-9320-24P4X",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
            "chassis_id_subtype": 4,  # MAC address
            "port_id_subtype": 5,  # Interface name
            "capabilities": 0x0028,  # Switch + Bridge
        },

        cdp_identity={
            "device_id": "IE-9320-24P4X.local",
            "platform": "cisco IE-9320-24P4X-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,  # Switch + IGMP + Router
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,  # Full duplex
        },

        profinet_identity={
            "vendor_id": 0x0145,  # Cisco PI-registered vendor ID
            "device_id": 0x9320,
            "device_role": 1,  # Switch/infrastructure
            "station_type": "IE-9320-24P4X",
            "station_name": "cisco-ie9320-24p4x",
        },

        ethernet_ip_identity={
            "vendor_id": 680,  # Cisco ODVA vendor ID
            "device_type": 12,  # Communications Adapter (Switch)
            "product_code": 9320,
            "product_name": "Catalyst IE-9320-24P4X-E",
            "serial_number": "FJC2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/ie9320/26s2c",
        vendor="Cisco",
        vendor_family="IE9300",
        model="IE-9320-26S2C-E",
        model_name="Catalyst IE9320 Rugged Switch 26-Port SFP",
        device_type="network_switch",
        description="22x GE SFP + 2x dual-media + 4x GE SFP industrial switch",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.6,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FJC{8ALPHANUM}",
            station_name_pattern="ie9320-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE93",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.3052",
        },

        lldp_identity={
            "system_name": "IE-9320-26S2C",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-9320-26S2C.local",
            "platform": "cisco IE-9320-26S2C-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },

        profinet_identity={
            "vendor_id": 0x0145,
            "device_id": 0x9321,
            "device_role": 1,
            "station_type": "IE-9320-26S2C",
            "station_name": "cisco-ie9320-26s2c",
        },

        ethernet_ip_identity={
            "vendor_id": 680,
            "device_type": 12,
            "product_code": 9321,
            "product_name": "Catalyst IE-9320-26S2C-E",
            "serial_number": "FJC2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/ie9310/26s2c",
        vendor="Cisco",
        vendor_family="IE9300",
        model="IE-9310-26S2C-E",
        model_name="Catalyst IE9310 Rugged Switch 26-Port SFP",
        device_type="network_switch",
        description="22x GE SFP + 2x dual-media + 4x GE SFP base model industrial switch",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.6,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FJC{8ALPHANUM}",
            station_name_pattern="ie9310-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE93",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.3050",
        },

        lldp_identity={
            "system_name": "IE-9310-26S2C",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-9310-26S2C.local",
            "platform": "cisco IE-9310-26S2C-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },
    ),
    DeviceTemplate(
        id="cisco/ie9320/24t4x",
        vendor="Cisco",
        vendor_family="IE9300",
        model="IE-9320-24T4X-E",
        model_name="Catalyst IE9320 Rugged Switch 24-Port Copper 10G",
        device_type="network_switch",
        description="24x GE copper RJ45 + 4x 10G SFP+ industrial switch",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.6,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FJC{8ALPHANUM}",
            station_name_pattern="ie9320-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE93",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.3055",
        },

        lldp_identity={
            "system_name": "IE-9320-24T4X",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-9320-24T4X.local",
            "platform": "cisco IE-9320-24T4X-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },

        profinet_identity={
            "vendor_id": 0x0145,
            "device_id": 0x9322,
            "device_role": 1,
            "station_type": "IE-9320-24T4X",
            "station_name": "cisco-ie9320-24t4x",
        },

        ethernet_ip_identity={
            "vendor_id": 680,
            "device_type": 12,
            "product_code": 9322,
            "product_name": "Catalyst IE-9320-24T4X-E",
            "serial_number": "FJC2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/ie3500/8p3s",
        vendor="Cisco",
        vendor_family="IE3500",
        model="IE-3500-8P3S-E",
        model_name="Catalyst IE3500 Rugged Switch 8-Port PoE+",
        device_type="network_switch",
        description="8x GE PoE/PoE+ + 3x GE SFP compact industrial switch with 240W PoE budget",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,  # IOS XE
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FDO{8ALPHANUM}",
            station_name_pattern="ie3500-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE35",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="17.9.05",
                release_date=date(2023, 9, 1),
                cves=["CVE-2023-20198"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.2960",
        },

        lldp_identity={
            "system_name": "IE-3500-8P3S",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-3500-8P3S.local",
            "platform": "cisco IE-3500-8P3S-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },

        profinet_identity={
            "vendor_id": 0x0145,
            "device_id": 0x3500,
            "device_role": 1,
            "station_type": "IE-3500-8P3S",
            "station_name": "cisco-ie3500-8p3s",
        },

        ethernet_ip_identity={
            "vendor_id": 680,
            "device_type": 12,
            "product_code": 3500,
            "product_name": "Catalyst IE-3500-8P3S-E",
            "serial_number": "FDO2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/ie3500/8t3s",
        vendor="Cisco",
        vendor_family="IE3500",
        model="IE-3500-8T3S-E",
        model_name="Catalyst IE3500 Rugged Switch 8-Port Copper",
        device_type="network_switch",
        description="8x GE copper + 3x GE SFP compact industrial switch (non-PoE)",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FDO{8ALPHANUM}",
            station_name_pattern="ie3500-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE35",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.2958",
        },

        lldp_identity={
            "system_name": "IE-3500-8T3S",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-3500-8T3S.local",
            "platform": "cisco IE-3500-8T3S-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },

        profinet_identity={
            "vendor_id": 0x0145,
            "device_id": 0x3501,
            "device_role": 1,
            "station_type": "IE-3500-8T3S",
            "station_name": "cisco-ie3500-8t3s",
        },

        ethernet_ip_identity={
            "vendor_id": 680,
            "device_type": 12,
            "product_code": 3501,
            "product_name": "Catalyst IE-3500-8T3S-E",
            "serial_number": "FDO2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/ie3500/8u3x",
        vendor="Cisco",
        vendor_family="IE3500",
        model="IE-3500-8U3X-E",
        model_name="Catalyst IE3500 Rugged Switch 8-Port 4PPoE 10G",
        device_type="network_switch",
        description="8x GE PoE/PoE+/4PPoE + 3x 10G SFP+ high-power industrial switch with 480W PoE budget",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 7,
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

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FDO{8ALPHANUM}",
            station_name_pattern="ie3500-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE35",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.2964",
        },

        lldp_identity={
            "system_name": "IE-3500-8U3X",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-3500-8U3X.local",
            "platform": "cisco IE-3500-8U3X-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "TenGigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },

        profinet_identity={
            "vendor_id": 0x0145,
            "device_id": 0x3502,
            "device_role": 1,
            "station_type": "IE-3500-8U3X",
            "station_name": "cisco-ie3500-8u3x",
        },

        ethernet_ip_identity={
            "vendor_id": 680,
            "device_type": 12,
            "product_code": 3502,
            "product_name": "Catalyst IE-3500-8U3X-E",
            "serial_number": "FDO2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/ie3505/8p3s",
        vendor="Cisco",
        vendor_family="IE3500",
        model="IE-3505-8P3S-E",
        model_name="Catalyst IE3505 Rugged Switch with HSR/PRP",
        device_type="network_switch",
        description="8x GE PoE+ + 3x GE SFP industrial switch with HSR/PRP/DLR redundancy",

        oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip", "ssh", "telnet", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="FDO{8ALPHANUM}",
            station_name_pattern="ie3505-{location}-{seq}",
            vendor_short="CIS",
            model_short="IE35",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="17.15.01",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="17.12.03",
                release_date=date(2024, 3, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
            "sys_object_id": "1.3.6.1.4.1.9.1.2966",
        },

        lldp_identity={
            "system_name": "IE-3505-8P3S",
            "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
            "chassis_id_subtype": 4,
            "port_id_subtype": 5,
            "capabilities": 0x0028,
        },

        cdp_identity={
            "device_id": "IE-3505-8P3S.local",
            "platform": "cisco IE-3505-8P3S-E",
            "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
            "capabilities": 0x29,
            "port_id": "GigabitEthernet1/0/1",
            "native_vlan": 1,
            "duplex": 1,
        },

        profinet_identity={
            "vendor_id": 0x0145,
            "device_id": 0x3505,
            "device_role": 1,
            "station_type": "IE-3505-8P3S",
            "station_name": "cisco-ie3505-8p3s",
        },

        ethernet_ip_identity={
            "vendor_id": 680,
            "device_type": 12,
            "product_code": 3505,
            "product_name": "Catalyst IE-3505-8P3S-E",
            "serial_number": "FDO2XXXXXXX",
        },
    ),
    DeviceTemplate(
        id="cisco/stratix/stratix-5700",
        vendor="Cisco",
        vendor_family="Stratix",
        model="Stratix 5700",
        model_name="Stratix 5700",
        device_type="network_switch",
        description="Cisco Stratix 5700",
        oui_prefixes=['00:1B:0D', '00:1E:BD'],
        tcp_stack={
                "ttl": 255,
                "window_size": 16384,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 1.0,
                "max_ms": 10.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="15.2(7)E3",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Cisco IOS Software, Stratix 5700 Software, Version 15.2(7)E3",
                "sys_object_id": "1.3.6.1.4.1.9.1.1858",
                "sys_name": "Stratix-5700-001",
                "sys_location": "Plant Floor",
                "sys_contact": "ot-network@facility.local",
            },
    ),
]
