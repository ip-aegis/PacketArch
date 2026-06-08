# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Rockwell Automation/Allen-Bradley CVE data.

CVE information for ControlLogix, CompactLogix, and MicroLogix PLCs.
These vulnerabilities are detectable via firmware version strings in
EtherNet/IP ListIdentity responses and Modbus FC 43 device identification.
"""

from datetime import datetime

ROCKWELL_CVES: list[dict] = [
    # CVE-2022-1159 - Studio 5000 Logix Designer Code Execution
    {
        "cve_id": "CVE-2022-1159",
        "title": "Rockwell Studio 5000 Logix Designer Unauthorized Code Execution",
        "description": (
            "An attacker with the ability to modify a user program may change user "
            "program code on some ControlLogix, CompactLogix, and GuardLogix controllers. "
            "The attacker could potentially halt the PLC or modify the running program."
        ),
        "severity": "critical",
        "cvss_score": 7.2,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Rockwell",
        "product_family": "ControlLogix",
        "affected_models": [
            "1756-L81E", "1756-L82E", "1756-L83E", "1756-L84E", "1756-L85E",
            "1756-L81ES", "1756-L82ES", "1756-L83ES",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "32.011",
        "fixed_firmware_version": "33.011",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-090-05",
        "references": [
            "https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/1134618",
        ],
        "mitre_techniques": ["T0843", "T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 3, 31),
        # Protocol identity overrides for vulnerable firmware
        "vulnerable_variants": [
            {
                "firmware_version": "32.011",
                "display_name": "ControlLogix L85E (CVE-2022-1159)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "32.011",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,  # Rockwell ODVA vendor ID
                    "device_type": 14,  # Programmable Logic Controller
                    "product_code": 0x37,
                    "revision_major": 32,
                    "revision_minor": 11,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,  # Running
                    "status": 0x0000,  # Normal operation
                },
                "cip_identity_override": {
                    "protection_mode": 0,  # No protection - vulnerable to unauthorized code changes
                    "configuration_consistency_value": 0xDEAD0000,  # Indicates unconfigured/vulnerable
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "31.012",
                "display_name": "ControlLogix L83E (CVE-2022-1159)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L83E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L83E",
                    "major_minor_revision": "31.012",
                    "product_name": "1756-L83E/B LOGIX5583",
                    "model_name": "ControlLogix 5583E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x35,
                    "revision_major": 31,
                    "revision_minor": 12,

                    "product_name": "1756-L83E/B LOGIX5583",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,  # No protection - vulnerable
                    "configuration_consistency_value": 0xDEAD0001,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            # Additional vulnerable firmware versions
            {
                "firmware_version": "30.011",
                "display_name": "ControlLogix L85E v30 (CVE-2022-1159)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "30.011",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    "revision_major": 30,
                    "revision_minor": 11,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xDEAD0002,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "29.011",
                "display_name": "ControlLogix L85E v29 (CVE-2022-1159)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "29.011",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    "revision_major": 29,
                    "revision_minor": 11,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xDEAD0003,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "28.015",
                "display_name": "ControlLogix L84E v28 (CVE-2022-1159)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L84E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L84E",
                    "major_minor_revision": "28.015",
                    "product_name": "1756-L84E/B LOGIX5584",
                    "model_name": "ControlLogix 5584E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x36,
                    "revision_major": 28,
                    "revision_minor": 15,

                    "product_name": "1756-L84E/B LOGIX5584",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xDEAD0004,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
        ],
    },

    # CVE-2022-1161 - ControlLogix/CompactLogix Code Execution via CIP
    {
        "cve_id": "CVE-2022-1161",
        "title": "Rockwell ControlLogix/CompactLogix Remote Code Execution",
        "description": (
            "A maliciously crafted CIP packet sent to an affected device may result "
            "in arbitrary code execution. This allows an attacker to gain remote "
            "access to the running memory of the controller."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Rockwell",
        "product_family": "ControlLogix",
        "affected_models": [
            "1756-L81E", "1756-L82E", "1756-L83E", "1756-L84E", "1756-L85E",
            # ControlLogix 5570 and CompactLogix 5370 families are also in
            # scope per CISA ICSA-22-090-05 (corrected family fix is V33.013).
            "1756-L73", "1769-L24ER-QB1B",
        ],
        "affected_firmware_min": None,
        # CISA ICSA-22-090-05: corrected firmware for the 5570/5370 family is
        # V33.013, so every genuinely-vulnerable variant (incl. V33.011,
        # V32.011) sits below 33.013. Prior 32.016 ceiling was a different
        # family's fix and under-stated the range.
        "affected_firmware_max": "33.012",
        "fixed_firmware_version": "33.013",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-090-05",
        "references": [
            "https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/1134620",
        ],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 3, 31),
        "vulnerable_variants": [
            {
                "firmware_version": "32.016",
                "display_name": "ControlLogix L85E (CVE-2022-1161)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "32.016",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    "revision_major": 32,
                    "revision_minor": 16,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,  # No protection - vulnerable to CIP RCE
                    "configuration_consistency_value": 0xBAD00000,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "31.011",
                "display_name": "ControlLogix L85E v31 (CVE-2022-1161)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "31.011",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    "revision_major": 31,
                    "revision_minor": 11,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xBAD00001,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "30.016",
                "display_name": "ControlLogix L84E v30 (CVE-2022-1161)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L84E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L84E",
                    "major_minor_revision": "30.016",
                    "product_name": "1756-L84E/B LOGIX5584",
                    "model_name": "ControlLogix 5584E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x36,
                    "revision_major": 30,
                    "revision_minor": 16,

                    "product_name": "1756-L84E/B LOGIX5584",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xBAD00002,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "29.013",
                "display_name": "ControlLogix L83E v29 (CVE-2022-1161)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L83E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L83E",
                    "major_minor_revision": "29.013",
                    "product_name": "1756-L83E/B LOGIX5583",
                    "model_name": "ControlLogix 5583E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x35,
                    "revision_major": 29,
                    "revision_minor": 13,

                    "product_name": "1756-L83E/B LOGIX5583",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xBAD00003,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
        ],
    },

    # CVE-2021-22681 - CompactLogix Authentication Bypass
    {
        "cve_id": "CVE-2021-22681",
        "title": "Rockwell CompactLogix Authentication Bypass",
        "description": (
            "An authentication bypass vulnerability exists that may allow an attacker "
            "to bypass authentication to execute CIP requests on the PLC without "
            "proper authorization. This can lead to full device compromise."
        ),
        "severity": "critical",
        # CISA ICSA-21-056-03 scores this 10.0 (CISA KEV, actively exploited).
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Rockwell",
        "product_family": "CompactLogix",
        "affected_models": [
            "1769-L33ER", "1769-L33ERM", "1769-L36ERM",
            "1769-L30ER", "1769-L30ERM", "1769-L30ER-NSE",
            # CISA ICSA-21-056-03 / NVD CPE list the ControlLogix 5570 and
            # 5580 families as affected too (all firmware versions).
            "1756-L73", "1769-L24ER-QB1B", "1756-L83E",
        ],
        "affected_firmware_min": None,
        # CISA ICSA-21-056-03: NO firmware patch exists (mitigations only:
        # mode-switch RUN, CIP Security, segmentation). ALL versions are
        # vulnerable, so the ceiling covers every real Logix firmware
        # (latest line is V36.x). Prior 32.013 cap was artificial.
        "affected_firmware_max": "36.011",
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-056-03",
        "references": [],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 2, 25),
        "vulnerable_variants": [
            {
                "firmware_version": "32.013",
                "display_name": "CompactLogix L33ER (CVE-2021-22681)",
                "snmp_sys_descr_template": "Rockwell Automation 1769-L33ER/B CompactLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1769-L33ER",
                    "major_minor_revision": "32.013",
                    "product_name": "1769-L33ER/B CompactLogix 5370",
                    "model_name": "CompactLogix 5370",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x5D,
                    "revision_major": 32,
                    "revision_minor": 13,

                    "product_name": "1769-L33ER/B CompactLogix 5370",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,  # No authentication - vulnerable to bypass
                    "configuration_consistency_value": 0x0,  # Unconfigured security
                    "maximum_cip_connections": 32,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "31.011",
                "display_name": "CompactLogix L33ER v31 (CVE-2021-22681)",
                "snmp_sys_descr_template": "Rockwell Automation 1769-L33ER/B CompactLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1769-L33ER",
                    "major_minor_revision": "31.011",
                    "product_name": "1769-L33ER/B CompactLogix 5370",
                    "model_name": "CompactLogix 5370",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x5D,
                    "revision_major": 31,
                    "revision_minor": 11,

                    "product_name": "1769-L33ER/B CompactLogix 5370",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0x0,
                    "maximum_cip_connections": 32,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "30.013",
                "display_name": "CompactLogix L30ER v30 (CVE-2021-22681)",
                "snmp_sys_descr_template": "Rockwell Automation 1769-L30ER/B CompactLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1769-L30ER",
                    "major_minor_revision": "30.013",
                    "product_name": "1769-L30ER/B CompactLogix 5370",
                    "model_name": "CompactLogix 5370",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x5C,
                    "revision_major": 30,
                    "revision_minor": 13,

                    "product_name": "1769-L30ER/B CompactLogix 5370",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0x0,
                    "maximum_cip_connections": 32,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "29.011",
                "display_name": "CompactLogix L36ERM v29 (CVE-2021-22681)",
                "snmp_sys_descr_template": "Rockwell Automation 1769-L36ERM/B CompactLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1769-L36ERM",
                    "major_minor_revision": "29.011",
                    "product_name": "1769-L36ERM/B CompactLogix 5370",
                    "model_name": "CompactLogix 5370",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x5E,
                    "revision_major": 29,
                    "revision_minor": 11,

                    "product_name": "1769-L36ERM/B CompactLogix 5370",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0x0,
                    "maximum_cip_connections": 32,
                    "heartbeat_interval": 250,
                },
            },
        ],
    },

    # CVE-2019-10954 - MicroLogix 1400 Authentication Bypass (No Fix)
    {
        "cve_id": "CVE-2019-10954",
        "title": "Rockwell MicroLogix 1400 Authentication Bypass (No Fix Available)",
        "description": (
            "MicroLogix 1400 Controllers Series A and B are vulnerable to an "
            "authentication bypass vulnerability. No fix is available as the "
            "product has reached end of life."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Rockwell",
        "product_family": "MicroLogix",
        "affected_models": [
            "1766-L32BWA", "1766-L32BWAA", "1766-L32BXB",
            "1766-L32AWAA", "1766-L32BXBA",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "21.007",  # All versions affected
        "fixed_firmware_version": None,  # No fix available
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-113-01",
        "references": [],
        "mitre_techniques": ["T0859"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 4, 23),
        "vulnerable_variants": [
            {
                "firmware_version": "21.007",
                "display_name": "MicroLogix 1400 v21.007 (CVE-2019-10954)",
                "snmp_sys_descr_template": "Rockwell Automation 1766-L32BWA MicroLogix 1400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1766-L32BWA",
                    "major_minor_revision": "21.007",
                    "product_name": "1766-L32BWA MicroLogix 1400",
                    "model_name": "MicroLogix 1400",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x19,
                    "revision_major": 21,
                    "revision_minor": 7,

                    "product_name": "1766-L32BWA MicroLogix 1400",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,  # No protection - permanently vulnerable (EOL)
                    "configuration_consistency_value": 0xFFFFFFFF,  # Legacy device
                    "maximum_cip_connections": 8,  # MicroLogix has limited connections
                    "heartbeat_interval": 500,
                },
            },
            {
                "firmware_version": "21.006",
                "display_name": "MicroLogix 1400 v21.006 (CVE-2019-10954)",
                "snmp_sys_descr_template": "Rockwell Automation 1766-L32BWA MicroLogix 1400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1766-L32BWA",
                    "major_minor_revision": "21.006",
                    "product_name": "1766-L32BWA MicroLogix 1400",
                    "model_name": "MicroLogix 1400",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x19,
                    "revision_major": 21,
                    "revision_minor": 6,

                    "product_name": "1766-L32BWA MicroLogix 1400",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xFFFFFFFF,
                    "maximum_cip_connections": 8,
                    "heartbeat_interval": 500,
                },
            },
            {
                "firmware_version": "21.005",
                "display_name": "MicroLogix 1400 v21.005 (CVE-2019-10954)",
                "snmp_sys_descr_template": "Rockwell Automation 1766-L32BWAA MicroLogix 1400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1766-L32BWAA",
                    "major_minor_revision": "21.005",
                    "product_name": "1766-L32BWAA MicroLogix 1400",
                    "model_name": "MicroLogix 1400",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x19,
                    "revision_major": 21,
                    "revision_minor": 5,

                    "product_name": "1766-L32BWAA MicroLogix 1400",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xFFFFFFFF,
                    "maximum_cip_connections": 8,
                    "heartbeat_interval": 500,
                },
            },
            {
                "firmware_version": "21.004",
                "display_name": "MicroLogix 1400 v21.004 (CVE-2019-10954)",
                "snmp_sys_descr_template": "Rockwell Automation 1766-L32BXB MicroLogix 1400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1766-L32BXB",
                    "major_minor_revision": "21.004",
                    "product_name": "1766-L32BXB MicroLogix 1400",
                    "model_name": "MicroLogix 1400",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x19,
                    "revision_major": 21,
                    "revision_minor": 4,

                    "product_name": "1766-L32BXB MicroLogix 1400",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xFFFFFFFF,
                    "maximum_cip_connections": 8,
                    "heartbeat_interval": 500,
                },
            },
            {
                "firmware_version": "21.003",
                "display_name": "MicroLogix 1400 v21.003 (CVE-2019-10954)",
                "snmp_sys_descr_template": "Rockwell Automation 1766-L32AWAA MicroLogix 1400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1766-L32AWAA",
                    "major_minor_revision": "21.003",
                    "product_name": "1766-L32AWAA MicroLogix 1400",
                    "model_name": "MicroLogix 1400",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x19,
                    "revision_major": 21,
                    "revision_minor": 3,

                    "product_name": "1766-L32AWAA MicroLogix 1400",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xFFFFFFFF,
                    "maximum_cip_connections": 8,
                    "heartbeat_interval": 500,
                },
            },
        ],
    },

    # CVE-2023-3595 - ControlLogix/GuardLogix Unauthorized Access
    {
        "cve_id": "CVE-2023-3595",
        "title": "Rockwell ControlLogix/GuardLogix Unauthorized Access",
        "description": (
            "A vulnerability exists in affected Rockwell Automation products that "
            "allows a threat actor to access and modify controller memory, which "
            "could result in data manipulation, loss of view, and/or loss of control."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Rockwell",
        "product_family": "ControlLogix",
        "affected_models": [
            "1756-L81E", "1756-L82E", "1756-L83E", "1756-L84E", "1756-L85E",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "33.016",
        "fixed_firmware_version": "34.011",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-193-01",
        "references": [],
        "mitre_techniques": ["T0843", "T0831", "T0882"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2023, 7, 12),
        "vulnerable_variants": [
            {
                "firmware_version": "33.016",
                "display_name": "ControlLogix L85E v33.016 (CVE-2023-3595)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "33.016",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    "revision_major": 33,
                    "revision_minor": 16,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,  # No memory protection - vulnerable to unauthorized access
                    "configuration_consistency_value": 0xCAFE0000,  # Pre-patch firmware
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "33.011",
                "display_name": "ControlLogix L85E v33.011 (CVE-2023-3595)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L85E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    "major_minor_revision": "33.011",
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    "revision_major": 33,
                    "revision_minor": 11,

                    "product_name": "1756-L85E/B LOGIX5585",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xCAFE0001,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "32.016",
                "display_name": "ControlLogix L84E v32.016 (CVE-2023-3595)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L84E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L84E",
                    "major_minor_revision": "32.016",
                    "product_name": "1756-L84E/B LOGIX5584",
                    "model_name": "ControlLogix 5584E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x36,
                    "revision_major": 32,
                    "revision_minor": 16,

                    "product_name": "1756-L84E/B LOGIX5584",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xCAFE0002,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
            {
                "firmware_version": "32.011",
                "display_name": "ControlLogix L83E v32.011 (CVE-2023-3595)",
                "snmp_sys_descr_template": "Rockwell Automation 1756-L83E/B ControlLogix v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L83E",
                    "major_minor_revision": "32.011",
                    "product_name": "1756-L83E/B LOGIX5583",
                    "model_name": "ControlLogix 5583E",
                    "vendor_url": "www.rockwellautomation.com",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x35,
                    "revision_major": 32,
                    "revision_minor": 11,

                    "product_name": "1756-L83E/B LOGIX5583",
                    "state": 3,
                    "status": 0x0000,
                },
                "cip_identity_override": {
                    "protection_mode": 0,
                    "configuration_consistency_value": 0xCAFE0003,
                    "maximum_cip_connections": 64,
                    "heartbeat_interval": 250,
                },
            },
        ],
    },
]
