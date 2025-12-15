"""Schneider Electric CVE data.

CVE information for Modicon M340, M580, and M251/M241 series PLCs.
These vulnerabilities are detectable via firmware version strings in
Modbus FC 43 device identification responses.
"""

from datetime import datetime

SCHNEIDER_CVES: list[dict] = [
    # CVE-2022-45789 - Modicon M580 Authentication Bypass
    {
        "cve_id": "CVE-2022-45789",
        "title": "Schneider Modicon M580 Authentication Bypass",
        "description": (
            "A vulnerability exists in Modicon M580 PLCs that could allow an "
            "attacker to bypass authentication and execute arbitrary Modbus "
            "commands on the device without proper authorization."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Modicon M580",
        "affected_models": [
            "BMEP581020", "BMEP582020", "BMEP582040",
            "BMEP583020", "BMEP583040", "BMEP584020",
            "BMEP584040", "BMEP585040", "BMEP586040",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.10",
        "fixed_firmware_version": "3.20",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-047-01",
        "references": [
            "https://download.schneider-electric.com/files?p_Doc_Ref=SEVD-2023-010-03",
        ],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 2, 16),
        "vulnerable_variants": [
            {
                "firmware_version": "3.10",
                "display_name": "Modicon M580 BMEP582040 (CVE-2022-45789)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "BMEP582040",
                    "major_minor_revision": "3.10",
                    "product_name": "Modicon M580 Safety PLC",
                    "model_name": "BMEP582040",
                    "user_application_name": "M580_Safety_Controller",
                },
            },
            {
                "firmware_version": "3.05",
                "display_name": "Modicon M580 BMEP584040 (CVE-2022-45789)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "BMEP584040",
                    "major_minor_revision": "3.05",
                    "product_name": "Modicon M580 Safety PLC",
                    "model_name": "BMEP584040",
                },
            },
        ],
    },

    # CVE-2021-22779 - Modicon M340 Unauthenticated Write
    {
        "cve_id": "CVE-2021-22779",
        "title": "Schneider Modicon M340 Unauthenticated Write Access",
        "description": (
            "A vulnerability exists in Modicon M340 PLCs that allows unauthenticated "
            "write access to the device. An attacker could overwrite memory areas "
            "and execute arbitrary code or modify the PLC program."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Modicon M340",
        "affected_models": [
            "BMXP341000", "BMXP342000", "BMXP3420102",
            "BMXP342020", "BMXP3420302",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.40",
        "fixed_firmware_version": "3.51",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-180-02",
        "references": [
            "https://download.schneider-electric.com/files?p_Doc_Ref=SEVD-2021-159-01",
        ],
        "mitre_techniques": ["T0843", "T0831", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 6, 29),
        "vulnerable_variants": [
            {
                "firmware_version": "3.40",
                "display_name": "Modicon M340 BMXP342020 (CVE-2021-22779)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "BMXP342020",
                    "major_minor_revision": "3.40",
                    "product_name": "Modicon M340 Processor",
                    "model_name": "BMXP342020",
                },
            },
            {
                "firmware_version": "3.30",
                "display_name": "Modicon M340 BMXP3420302 (CVE-2021-22779)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "BMXP3420302",
                    "major_minor_revision": "3.30",
                    "product_name": "Modicon M340 Processor",
                    "model_name": "BMXP3420302",
                },
            },
        ],
    },

    # CVE-2020-7540 - Modicon M251/M241 Authentication Bypass
    {
        "cve_id": "CVE-2020-7540",
        "title": "Schneider Modicon M251/M241 Authentication Bypass",
        "description": (
            "A vulnerability exists in Modicon M251 and M241 controllers that "
            "could allow an unauthenticated remote attacker to bypass authentication "
            "and gain full access to the device."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Modicon M251",
        "affected_models": [
            "TM251MESE", "TM251MESC", "TM251MESC24T",
            "TM241CE24R", "TM241CE24T", "TM241CE40R",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "5.1.3",
        "fixed_firmware_version": "5.1.4",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-315-02",
        "references": [
            "https://download.schneider-electric.com/files?p_Doc_Ref=SEVD-2020-315-05",
        ],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 11, 10),
        "vulnerable_variants": [
            {
                "firmware_version": "5.1.3",
                "display_name": "Modicon M251 TM251MESE (CVE-2020-7540)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "TM251MESE",
                    "major_minor_revision": "5.1.3",
                    "product_name": "Modicon M251 Logic Controller",
                    "model_name": "TM251MESE",
                },
            },
            {
                "firmware_version": "5.0.2",
                "display_name": "Modicon M241 TM241CE40R (CVE-2020-7540)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "TM241CE40R",
                    "major_minor_revision": "5.0.2",
                    "product_name": "Modicon M241 Logic Controller",
                    "model_name": "TM241CE40R",
                },
            },
        ],
    },

    # CVE-2018-7760 - Modicon Premium Hardcoded Credentials
    {
        "cve_id": "CVE-2018-7760",
        "title": "Schneider Modicon Premium/Quantum Hardcoded FTP Credentials",
        "description": (
            "Modicon Premium and Quantum PLCs contain hardcoded FTP credentials "
            "that allow attackers to access the device's file system and modify "
            "PLC programs or configuration."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Modicon Premium",
        "affected_models": [
            "TSXP57104M", "TSXP57154M", "TSXP57204M",
            "TSXP57254M", "TSXP573634M", "TSXP574634M",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.60",  # All versions affected
        "fixed_firmware_version": None,  # No fix - use Unity instead
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-18-107-01",
        "references": [],
        "mitre_techniques": ["T0859", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2018, 4, 17),
        "vulnerable_variants": [
            {
                "firmware_version": "3.60",
                "display_name": "Modicon Premium TSXP57204M (CVE-2018-7760)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "TSXP57204M",
                    "major_minor_revision": "3.60",
                    "product_name": "Modicon Premium PLC",
                    "model_name": "TSXP57204M",
                },
            },
        ],
    },

    # CVE-2019-6829 - Modicon M340 Buffer Overflow
    {
        "cve_id": "CVE-2019-6829",
        "title": "Schneider Modicon M340 Buffer Overflow",
        "description": (
            "A buffer overflow vulnerability exists in Modicon M340 PLCs. "
            "Sending a specially crafted Modbus request to the affected device "
            "could cause a denial of service or potentially remote code execution."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:H",
        "vendor": "Schneider",
        "product_family": "Modicon M340",
        "affected_models": [
            "BMXP341000", "BMXP342000", "BMXP3420102",
            "BMXP342020", "BMXP3420302",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.20",
        "fixed_firmware_version": "3.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-330-01",
        "references": [],
        "mitre_techniques": ["T0815", "T0869"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2019, 11, 26),
        "vulnerable_variants": [
            {
                "firmware_version": "3.20",
                "display_name": "Modicon M340 BMXP342020 (CVE-2019-6829)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "BMXP342020",
                    "major_minor_revision": "3.20",
                    "product_name": "Modicon M340 Processor",
                    "model_name": "BMXP342020",
                },
            },
        ],
    },

    # CVE-2022-37300 - Modicon M580 Information Disclosure
    {
        "cve_id": "CVE-2022-37300",
        "title": "Schneider Modicon M580 Information Disclosure",
        "description": (
            "An information exposure vulnerability exists in Modicon M580 PLCs "
            "that could allow an attacker to retrieve sensitive data from the "
            "device's memory using crafted Modbus requests."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Schneider",
        "product_family": "Modicon M580",
        "affected_models": [
            "BMEP581020", "BMEP582020", "BMEP582040",
            "BMEP583020", "BMEP584040",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.30",
        "fixed_firmware_version": "3.40",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://download.schneider-electric.com/files?p_Doc_Ref=SEVD-2022-227-02",
        "references": [],
        "mitre_techniques": ["T0882"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 8, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "3.30",
                "display_name": "Modicon M580 BMEP584040 (CVE-2022-37300)",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "BMEP584040",
                    "major_minor_revision": "3.30",
                    "product_name": "Modicon M580 Safety PLC",
                    "model_name": "BMEP584040",
                },
            },
        ],
    },
]
