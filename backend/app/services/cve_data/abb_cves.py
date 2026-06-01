# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ABB CVE data.

CVE information for System 800xA, AC500 V2, and other ABB ICS products.
These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

ABB_CVES: list[dict] = [
    # CVE-2020-8477 - System 800xA Remote Code Execution
    {
        "cve_id": "CVE-2020-8477",
        "title": "ABB System 800xA Remote Code Execution",
        "description": (
            "A vulnerability in the ABB System 800xA allows remote code execution. "
            "An attacker can exploit this to execute arbitrary code on the system, "
            "potentially compromising the entire DCS infrastructure."
        ),
        "severity": "critical",
        "cvss_score": 8.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "ABB",
        "product_family": "System 800xA",
        "affected_models": [
            "800xA", "800xA Batch Management", "800xA Control Builder",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "6.0.3.2",
        "fixed_firmware_version": "6.0.3.3",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-072-02",
        "references": [
            "https://search.abb.com/library/Download.aspx?DocumentID=3ADR010645",
        ],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": True,
        "exploit_complexity": "medium",
        "published_date": datetime(2020, 3, 12),
        "vulnerable_variants": [
            {
                "firmware_version": "6.0.3.2",
                "display_name": "System 800xA (CVE-2020-8477)",
                "snmp_sys_descr_template": "ABB System 800xA DCS v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "800xA",
                    "major_minor_revision": "6.0.3.2",
                    "product_name": "ABB System 800xA DCS",
                },
                "ethernet_ip_identity_override": None,
                "profinet_identity_override": {
                    "vendor_id": 0x0016,  # ABB PROFINET vendor ID
                    "device_id": 0x0DAC,
                    "device_role": 0x01,
                    "device_vendor": "ABB",
                    "station_name": "system-800xa",
                },
            },
        ],
    },

    # CVE-2021-22285 - AC500 V2 PLC Authentication Bypass
    {
        "cve_id": "CVE-2021-22285",
        "title": "ABB AC500 V2 PLC Authentication Bypass",
        "description": (
            "ABB AC500 V2 PLCs are vulnerable to an authentication bypass. An attacker "
            "can send specially crafted requests to bypass authentication and gain "
            "unauthorized access to the controller configuration."
        ),
        "severity": "critical",
        "cvss_score": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "ABB",
        "product_family": "AC500 V2",
        "affected_models": [
            "PM582", "PM583", "PM590", "PM591", "PM592",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "2.8.4",
        "fixed_firmware_version": "2.8.6",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-110-01",
        "references": [],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 4, 20),
        "vulnerable_variants": [
            {
                "firmware_version": "2.8.4",
                "display_name": "AC500 PM590 (CVE-2021-22285)",
                "snmp_sys_descr_template": "ABB AC500 PM590-ETH PLC v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "PM590-ETH",
                    "major_minor_revision": "2.8.4",
                    "product_name": "ABB AC500 PM590-ETH PLC",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0016,  # ABB ODVA vendor ID
                    "device_type": 14,
                    "product_code": 0x0590,
                    "revision_major": 2,
                    "revision_minor": 84,
                    "product_name": "ABB AC500 PM590-ETH",
                },
            },
            {
                "firmware_version": "2.7.2",
                "display_name": "AC500 PM583 (CVE-2021-22285)",
                "snmp_sys_descr_template": "ABB AC500 PM583-ETH PLC v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "PM583-ETH",
                    "major_minor_revision": "2.7.2",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0016,
                    "device_type": 14,
                    "product_code": 0x0583,
                    "revision_major": 2,
                    "revision_minor": 72,
                    "product_name": "ABB AC500 PM583-ETH",
                },
            },
        ],
    },

    # CVE-2022-26057 - SPIET800/SPICT800 Information Disclosure
    {
        "cve_id": "CVE-2022-26057",
        "title": "ABB SPIET800/SPICT800 Information Disclosure",
        "description": (
            "ABB SPIET800 and SPICT800 devices are vulnerable to information disclosure. "
            "An attacker can extract sensitive configuration data including credentials "
            "through the network interface."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N",
        "vendor": "ABB",
        "product_family": "SPI Ethernet",
        "affected_models": [
            "SPIET800", "SPICT800", "SPI600",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.4.1",
        "fixed_firmware_version": "3.4.2",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-095-01",
        "references": [],
        "mitre_techniques": ["T0811", "T0846"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 4, 5),
        "vulnerable_variants": [
            {
                "firmware_version": "3.4.1",
                "display_name": "SPIET800 (CVE-2022-26057)",
                "snmp_sys_descr_template": "ABB SPI SPIET800 Ethernet Interface v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "SPIET800",
                    "major_minor_revision": "3.4.1",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },

    # CVE-2019-18253 - PM554-TP-ETH Stack Buffer Overflow
    {
        "cve_id": "CVE-2019-18253",
        "title": "ABB PM554-TP-ETH Stack Buffer Overflow",
        "description": (
            "A stack buffer overflow vulnerability exists in ABB PM554-TP-ETH PLCs. "
            "An attacker can exploit this to crash the device or execute arbitrary code "
            "by sending a specially crafted network packet."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "ABB",
        "product_family": "AC500",
        "affected_models": [
            "PM554-TP-ETH", "PM564-TP-ETH", "PM566-TP-ETH",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "2.5.1",
        "fixed_firmware_version": "2.6.0",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-318-02",
        "references": [],
        "mitre_techniques": ["T0843", "T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 11, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "2.5.1",
                "display_name": "PM554-TP-ETH (CVE-2019-18253)",
                "snmp_sys_descr_template": "ABB AC500 PM554-TP-ETH PLC v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "PM554-TP-ETH",
                    "major_minor_revision": "2.5.1",
                    "product_name": "ABB AC500 PM554-TP-ETH PLC",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0016,
                    "device_type": 14,
                    "product_code": 0x0554,
                    "revision_major": 2,
                    "revision_minor": 51,
                    "product_name": "ABB AC500 PM554-TP-ETH",
                },
            },
        ],
    },

    # CVE-2020-8481 - Symphony Plus Denial of Service
    {
        "cve_id": "CVE-2020-8481",
        "title": "ABB Symphony Plus Denial of Service",
        "description": (
            "ABB Symphony Plus systems are vulnerable to denial of service attacks. "
            "An attacker can send malformed packets that cause the system to become "
            "unresponsive, affecting process control operations."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "ABB",
        "product_family": "Symphony Plus",
        "affected_models": [
            "Symphony Plus S+ Operations", "Symphony Plus S+ Engineering",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.0 SP2",
        "fixed_firmware_version": "3.1",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-051-02",
        "references": [],
        "mitre_techniques": ["T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 2, 20),
        "vulnerable_variants": [
            {
                "firmware_version": "3.0 SP2",
                "display_name": "Symphony Plus (CVE-2020-8481)",
                "snmp_sys_descr_template": "ABB Symphony Plus S+ Operations v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "Symphony-Plus",
                    "major_minor_revision": "3.0.2",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },
]
