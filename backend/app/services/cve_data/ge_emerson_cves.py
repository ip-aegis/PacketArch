# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""GE/Emerson CVE data.

CVE information for PACSystems, MarkVIe, and Proficy Historian products.
These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

GE_EMERSON_CVES: list[dict] = [

    # CVE-2021-27426 - GE Multilin UR-series "Factory Mode" insecure default
    # NVD-verified: affects the GE Multilin UR family (B30/B90/C30/C60/C70/C95/
    # D30/D60/F35/F60/G30/G60/L30/L60/L90/M60/N60/T35/T60) at all firmware
    # prior to V8.10. NOT MarkVIe (the prior record was mis-scoped) and NOT
    # capped at 03.04.00. CVSS v3.1 9.8.
    {
        "cve_id": "CVE-2021-27426",
        "title": "GE Multilin UR-series Insecure Default (Factory Mode)",
        "description": (
            "GE Multilin UR-series intelligent electronic devices (IEDs) ship with "
            "an insecure-by-default 'Factory Mode' that can be reached over the "
            "network, allowing an attacker to gain privileged access to the relay. "
            "All UR firmware prior to V8.10 is affected."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "GE",
        "product_family": "UR Series",
        "affected_models": [
            "B30", "B90", "C30", "C60", "C70", "C95", "D30", "D60",
            "F35", "F60", "G30", "G60", "L30", "L60", "L90", "M60",
            "N60", "T35", "T60",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "8.10",
        "fixed_firmware_version": "8.10",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-040-01",
        "references": [],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 2, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "7.80",
                "display_name": "GE Multilin UR (CVE-2021-27426)",
                "snmp_sys_descr_template": "GE Multilin UR-series Relay v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Grid Solutions",
                    "product_code": "UR",
                    "major_minor_revision": "7.80",
                    "product_name": "GE Multilin UR-series Relay",
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
        "severity": "high",
        "cvss_score": 6.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N",
        "vendor": "GE",
        "product_family": "Proficy Historian",
        "affected_models": [
            "Proficy Historian",
        ],
        # NVD-verified affected range: "from (including) 7.0 up to (excluding)
        # 2023" — this INCLUDES 8.0 (pre-2023). Widen the ceiling so the real
        # 8.0/7.1 template variants are covered. Fixed in the 2023 release line.
        "affected_firmware_min": None,
        "affected_firmware_max": "8.0",
        "fixed_firmware_version": "8.1",
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
                "firmware_version": "8.0",
                "display_name": "Proficy Historian (CVE-2022-46660)",
                "snmp_sys_descr_template": "GE Digital Proficy Historian v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Digital",
                    "product_code": "Proficy-Historian",
                    "major_minor_revision": "8.0",
                },
                "ethernet_ip_identity_override": None,
            },
        ],
    },
]
