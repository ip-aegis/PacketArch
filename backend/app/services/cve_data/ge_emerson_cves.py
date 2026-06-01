# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""GE/Emerson CVE data.

CVE information for PACSystems, MarkVIe, and Proficy Historian products.
These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

GE_EMERSON_CVES: list[dict] = [

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
        "cvss_score": 6.5,
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
]
