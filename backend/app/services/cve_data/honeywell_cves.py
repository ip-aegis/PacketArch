# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Honeywell CVE data.

CVE information for Experion PKS, Saia Burgess PCD, and other Honeywell ICS products.
These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

HONEYWELL_CVES: list[dict] = [

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
]
