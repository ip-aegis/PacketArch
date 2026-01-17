"""Honeywell CVE data.

CVE information for Experion PKS, Saia Burgess PCD, and other Honeywell ICS products.
These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

HONEYWELL_CVES: list[dict] = [
    # CVE-2020-10628 - Experion PKS Authentication Bypass
    {
        "cve_id": "CVE-2020-10628",
        "title": "Honeywell Experion PKS C200/C300 Authentication Bypass",
        "description": (
            "The affected controllers accept remote unauthenticated commands that can "
            "change configuration settings and modify the control logic. An attacker "
            "can exploit this to gain unauthorized control of the process."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Experion PKS",
        "affected_models": [
            "C200", "C200E", "C300", "ACE",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "R510.2",
        "fixed_firmware_version": "R511.5",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-196-01",
        "references": [
            "https://www.honeywell.com/us/en/product-security",
        ],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 7, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "R510.2",
                "display_name": "Experion C300 (CVE-2020-10628)",
                "snmp_sys_descr_template": "Honeywell Experion PKS C300 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell",
                    "product_code": "C300",
                    "major_minor_revision": "R510.2",
                    "product_name": "Experion PKS C300 Controller",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0039,  # Honeywell ODVA vendor ID
                    "device_type": 14,
                    "product_code": 0xC300,
                    "revision_major": 510,
                    "revision_minor": 2,
                    "product_name": "Experion PKS C300 Controller",
                },
            },
            {
                "firmware_version": "R500.1",
                "display_name": "Experion C200 (CVE-2020-10628)",
                "snmp_sys_descr_template": "Honeywell Experion PKS C200 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell",
                    "product_code": "C200",
                    "major_minor_revision": "R500.1",
                    "product_name": "Experion PKS C200 Controller",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0039,
                    "device_type": 14,
                    "product_code": 0xC200,
                    "revision_major": 500,
                    "revision_minor": 1,
                    "product_name": "Experion PKS C200 Controller",
                },
            },
        ],
    },

    # CVE-2021-38397 - Experion PKS Unrestricted File Upload
    {
        "cve_id": "CVE-2021-38397",
        "title": "Honeywell Experion PKS Unrestricted File Upload (CVSS 10.0)",
        "description": (
            "The affected product is vulnerable to unrestricted file upload, which may "
            "allow an attacker to remotely execute arbitrary code and cause a denial-of-service "
            "condition. This is one of the most severe ICS vulnerabilities discovered."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Experion PKS",
        "affected_models": [
            "C200", "C200E", "C300", "ControlEdge", "Safety Manager",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "R520.1",
        "fixed_firmware_version": "R520.2",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-278-04",
        "references": [],
        "mitre_techniques": ["T0843", "T0883", "T0880"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 10, 5),
        "vulnerable_variants": [
            {
                "firmware_version": "R520.1",
                "display_name": "Experion PKS C300 (CVE-2021-38397)",
                "snmp_sys_descr_template": "Honeywell Experion PKS C300 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell",
                    "product_code": "C300",
                    "major_minor_revision": "R520.1",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0039,
                    "device_type": 14,
                    "product_code": 0xC300,
                    "revision_major": 520,
                    "revision_minor": 1,
                    "product_name": "Experion PKS C300 Controller",
                },
            },
        ],
    },

    # CVE-2022-30312 - Saia Burgess PCD Hardcoded Credentials
    {
        "cve_id": "CVE-2022-30312",
        "title": "Honeywell Saia Burgess PCD Hardcoded Credentials",
        "description": (
            "The firmware of affected Saia Burgess PCD controllers contains hardcoded "
            "credentials which may allow an attacker to gain unauthorized access to the "
            "device management interface and execute arbitrary commands."
        ),
        "severity": "critical",
        "cvss_score": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "Honeywell",
        "product_family": "Saia Burgess PCD",
        "affected_models": [
            "PCD1.M2", "PCD2.M5", "PCD3.M3", "PCD3.M5",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "1.28.16",
        "fixed_firmware_version": "1.29.18",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-207-03",
        "references": [],
        "mitre_techniques": ["T0859", "T0812"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 7, 26),
        "vulnerable_variants": [
            {
                "firmware_version": "1.28.16",
                "display_name": "Saia PCD3.M5 (CVE-2022-30312)",
                "snmp_sys_descr_template": "Honeywell Saia Burgess PCD3.M5 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell/Saia-Burgess",
                    "product_code": "PCD3.M5",
                    "major_minor_revision": "1.28.16",
                },
                "ethernet_ip_identity_override": None,
            },
            {
                "firmware_version": "1.24.10",
                "display_name": "Saia PCD2.M5 (CVE-2022-30312)",
                "snmp_sys_descr_template": "Honeywell Saia Burgess PCD2.M5 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell/Saia-Burgess",
                    "product_code": "PCD2.M5",
                    "major_minor_revision": "1.24.10",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },

    # CVE-2023-25078 - Experion Server Remote Code Execution
    {
        "cve_id": "CVE-2023-25078",
        "title": "Honeywell Experion Server Remote Code Execution",
        "description": (
            "A vulnerability in the Experion Server allows remote code execution through "
            "a crafted network request. An attacker can leverage this to execute arbitrary "
            "code with system privileges on the server."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Experion Server",
        "affected_models": [
            "Experion Server", "Experion Station",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "520.2 HF6",
        "fixed_firmware_version": "520.2 HF7",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-054-01",
        "references": [],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2023, 2, 23),
        "vulnerable_variants": [
            {
                "firmware_version": "520.2 HF6",
                "display_name": "Experion Server (CVE-2023-25078)",
                "snmp_sys_descr_template": "Honeywell Experion Server v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell",
                    "product_code": "EXPERION-SVR",
                    "major_minor_revision": "520.2",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },

    # CVE-2020-6959 - Experion PKS Improper Authentication
    {
        "cve_id": "CVE-2020-6959",
        "title": "Honeywell Experion PKS Improper Authentication",
        "description": (
            "The Experion PKS C200, C200E, C300, and ACE controllers are vulnerable to "
            "improper authentication. An attacker may be able to access restricted "
            "functionality without proper credentials."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N",
        "vendor": "Honeywell",
        "product_family": "Experion PKS",
        "affected_models": [
            "C200", "C200E", "C300", "ACE",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "R501.6",
        "fixed_firmware_version": "R510.1",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-049-02",
        "references": [],
        "mitre_techniques": ["T0859"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 2, 18),
        "vulnerable_variants": [
            {
                "firmware_version": "R501.6",
                "display_name": "Experion C200 (CVE-2020-6959)",
                "snmp_sys_descr_template": "Honeywell Experion PKS C200 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell",
                    "product_code": "C200",
                    "major_minor_revision": "R501.6",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 0x0039,
                    "device_type": 14,
                    "product_code": 0xC200,
                    "revision_major": 501,
                    "revision_minor": 6,
                    "product_name": "Experion PKS C200 Controller",
                },
            },
        ],
    },
]
