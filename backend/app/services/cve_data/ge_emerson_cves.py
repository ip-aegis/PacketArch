"""GE/Emerson CVE data.

CVE information for PACSystems, MarkVIe, and Proficy Historian products.
These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

GE_EMERSON_CVES: list[dict] = [
    # CVE-2022-23925 - PACSystems RX3i Authentication Bypass
    {
        "cve_id": "CVE-2022-23925",
        "title": "GE PACSystems RX3i Authentication Bypass",
        "description": (
            "GE PACSystems RX3i controllers are vulnerable to authentication bypass "
            "via a specially crafted request. An attacker could exploit this to gain "
            "unauthorized access to the controller and modify its configuration."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "GE",
        "product_family": "PACSystems RX3i",
        "affected_models": [
            "IC695CPE310", "IC695CPE330", "IC695CPE400",
            "IC695PSD040", "IC695PSD140",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "9.80",
        "fixed_firmware_version": "9.85",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-081-01",
        "references": [],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 3, 22),
        "vulnerable_variants": [
            {
                "firmware_version": "9.80",
                "display_name": "PACSystems RX3i CPE400 (CVE-2022-23925)",
                "snmp_sys_descr_template": "GE Automation PACSystems RX3i CPE400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Automation",
                    "product_code": "IC695CPE400",
                    "major_minor_revision": "9.80",
                    "product_name": "PACSystems RX3i CPE400",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x001D,  # GE ODVA vendor ID
                    "device_type": 14,
                    "product_code": 0x0400,
                    "revision_major": 9,
                    "revision_minor": 80,
                    "product_name": "PACSystems RX3i CPE400",
                },
            },
            {
                "firmware_version": "9.70",
                "display_name": "PACSystems RX3i CPE330 (CVE-2022-23925)",
                "snmp_sys_descr_template": "GE Automation PACSystems RX3i CPE330 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Automation",
                    "product_code": "IC695CPE330",
                    "major_minor_revision": "9.70",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x001D,
                    "device_type": 14,
                    "product_code": 0x0330,
                    "revision_major": 9,
                    "revision_minor": 70,
                    "product_name": "PACSystems RX3i CPE330",
                },
            },
        ],
    },

    # CVE-2021-27426 - MarkVIe Remote Code Execution
    {
        "cve_id": "CVE-2021-27426",
        "title": "GE MarkVIe Remote Code Execution",
        "description": (
            "GE MarkVIe Speedtronic turbine control systems contain a vulnerability "
            "that allows remote code execution. An attacker can exploit this to execute "
            "arbitrary code on the controller, potentially affecting turbine operation."
        ),
        "severity": "critical",
        "cvss_score": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "GE",
        "product_family": "MarkVIe",
        "affected_models": [
            "MarkVIe", "MarkVIeS", "MarkVIeC",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "03.04.00",
        "fixed_firmware_version": "04.01.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-040-01",
        "references": [],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": True,
        "exploit_complexity": "medium",
        "published_date": datetime(2021, 2, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "03.04.00",
                "display_name": "MarkVIe (CVE-2021-27426)",
                "snmp_sys_descr_template": "GE Energy MarkVIe Speedtronic Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Energy",
                    "product_code": "MarkVIe",
                    "major_minor_revision": "03.04.00",
                    "product_name": "MarkVIe Speedtronic Controller",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },

    # CVE-2020-12525 - PACSystems Improper Input Validation
    {
        "cve_id": "CVE-2020-12525",
        "title": "GE PACSystems Improper Input Validation",
        "description": (
            "GE PACSystems RX3i and RSTi-EP controllers are vulnerable to improper input "
            "validation. A malformed packet can cause the controller to enter a fault "
            "state, resulting in denial of service."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "GE",
        "product_family": "PACSystems",
        "affected_models": [
            "IC695CPE310", "IC695CPE330", "IC695CPE400",
            "RSTi-EP", "IC695RMX128",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "9.45",
        "fixed_firmware_version": "9.50",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-154-01",
        "references": [],
        "mitre_techniques": ["T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 6, 2),
        "vulnerable_variants": [
            {
                "firmware_version": "9.45",
                "display_name": "PACSystems RX3i (CVE-2020-12525)",
                "snmp_sys_descr_template": "GE Automation PACSystems RX3i CPE400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Automation",
                    "product_code": "IC695CPE400",
                    "major_minor_revision": "9.45",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x001D,
                    "device_type": 14,
                    "product_code": 0x0400,
                    "revision_major": 9,
                    "revision_minor": 45,
                    "product_name": "PACSystems RX3i CPE400",
                },
            },
        ],
    },

    # CVE-2022-46660 - Proficy Historian SQL Injection
    {
        "cve_id": "CVE-2022-46660",
        "title": "GE Proficy Historian SQL Injection",
        "description": (
            "GE Proficy Historian is vulnerable to SQL injection attacks through "
            "specially crafted requests. An attacker could leverage this to extract "
            "or modify historical process data in the database."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "GE",
        "product_family": "Proficy Historian",
        "affected_models": [
            "Proficy Historian",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "7.2",
        "fixed_firmware_version": "7.3",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-342-02",
        "references": [],
        "mitre_techniques": ["T0872", "T0811"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 12, 8),
        "vulnerable_variants": [
            {
                "firmware_version": "7.2",
                "display_name": "Proficy Historian (CVE-2022-46660)",
                "snmp_sys_descr_template": "GE Digital Proficy Historian v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Digital",
                    "product_code": "Proficy-Historian",
                    "major_minor_revision": "7.2",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },

    # CVE-2018-10936 - PACSystems RX3i Hardcoded Credentials
    {
        "cve_id": "CVE-2018-10936",
        "title": "GE PACSystems RX3i Hardcoded Credentials (CVSS 10.0)",
        "description": (
            "GE PACSystems RX3i controllers contain hardcoded credentials that allow "
            "an attacker to gain administrative access. This is one of the most severe "
            "vulnerabilities affecting these controllers."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "GE",
        "product_family": "PACSystems RX3i",
        "affected_models": [
            "IC695CPE310", "IC695CPE330", "IC695CPE400",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "9.30",
        "fixed_firmware_version": "9.40",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-18-331-01",
        "references": [],
        "mitre_techniques": ["T0812", "T0859"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2018, 11, 27),
        "vulnerable_variants": [
            {
                "firmware_version": "9.30",
                "display_name": "PACSystems RX3i CPE400 (CVE-2018-10936)",
                "snmp_sys_descr_template": "GE Automation PACSystems RX3i CPE400 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Automation",
                    "product_code": "IC695CPE400",
                    "major_minor_revision": "9.30",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x001D,
                    "device_type": 14,
                    "product_code": 0x0400,
                    "revision_major": 9,
                    "revision_minor": 30,
                    "product_name": "PACSystems RX3i CPE400",
                },
            },
            {
                "firmware_version": "9.21",
                "display_name": "PACSystems RX3i CPE310 (CVE-2018-10936)",
                "snmp_sys_descr_template": "GE Automation PACSystems RX3i CPE310 v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Automation",
                    "product_code": "IC695CPE310",
                    "major_minor_revision": "9.21",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x001D,
                    "device_type": 14,
                    "product_code": 0x0310,
                    "revision_major": 9,
                    "revision_minor": 21,
                    "product_name": "PACSystems RX3i CPE310",
                },
            },
        ],
    },
]
