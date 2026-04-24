# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Energy/Power vertical CVE data.

CVE information for protection relays, power meters, and substation equipment.
These vulnerabilities are detectable via firmware version strings in protocol responses
including IEC 104, DNP3, and Modbus device identification.
"""

from datetime import datetime

ENERGY_CVES: list[dict] = [
    # ==================== SEL Protection Relay CVEs ====================

    # CVE-2023-2745 - SEL-751 Firmware Vulnerability
    {
        "cve_id": "CVE-2023-2745",
        "title": "SEL-751 Feeder Protection Relay Authentication Bypass",
        "description": (
            "SEL-751 Feeder Protection Relays with firmware prior to R144-V0 contain "
            "an authentication bypass vulnerability. An attacker with network access "
            "could bypass authentication and modify relay settings, potentially causing "
            "protection system failures."
        ),
        "severity": "high",
        "cvss_score": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N",
        "vendor": "SEL",
        "product_family": "SEL-751",
        "affected_models": ["SEL-751", "SEL-751A"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R143-V0",
        "fixed_firmware_version": "R144-V0",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-136-02",
        "references": [
            "https://selinc.com/support/security-notifications/",
        ],
        "mitre_techniques": ["T0859", "T0831"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2023, 5, 16),
        "vulnerable_variants": [
            {
                "firmware_version": "R143-V0",
                "display_name": "SEL-751 (CVE-2023-2745)",
                "snmp_sys_descr_template": "SEL-751 Feeder Protection Relay v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "0751",
                    "major_minor_revision": "R143-V0",
                    "product_name": "SEL-751 Feeder Protection Relay",
                    "model_name": "SEL-751",
                },
                "dnp3_identity_override": {
                    "vendor_name": "SEL",
                    "device_serial": "751-VULN",
                    "software_version": "R143-V0",
                },
            },
        ],
    },

    # CVE-2022-0778 - OpenSSL Vulnerability affecting SEL Relays
    {
        "cve_id": "CVE-2022-0778",
        "title": "SEL Protection Relays OpenSSL Infinite Loop DoS",
        "description": (
            "Multiple SEL protection relays are affected by an OpenSSL vulnerability "
            "that allows denial of service via crafted certificates. An attacker could "
            "cause the relay's web interface or secure communications to become unresponsive."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "SEL",
        "product_family": "Protection Relay",
        "affected_models": ["SEL-451", "SEL-751", "SEL-311C", "SEL-487E", "SEL-2411"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R319-V0",
        "fixed_firmware_version": "R320-V0",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-111-01",
        "references": [
            "https://selinc.com/support/security-notifications/",
        ],
        "mitre_techniques": ["T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 3, 15),
        "vulnerable_variants": [
            {
                "firmware_version": "R319-V0",
                "display_name": "SEL-451 (CVE-2022-0778)",
                "snmp_sys_descr_template": "SEL-451 Bay Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "0451",
                    "major_minor_revision": "R319-V0",
                    "product_name": "SEL-451 Bay Controller",
                },
                "dnp3_identity_override": {
                    "vendor_name": "SEL",
                    "device_serial": "451-VULN",
                    "software_version": "R319-V0",
                },
            },
        ],
    },

    # ==================== Siemens SIPROTEC CVEs ====================

    # CVE-2019-18285 - SIPROTEC 5 DoS
    {
        "cve_id": "CVE-2019-18285",
        "title": "Siemens SIPROTEC 5 Denial of Service via Malformed Packets",
        "description": (
            "Siemens SIPROTEC 5 protection relays with firmware prior to V8.30 are "
            "vulnerable to denial of service attacks. Specially crafted network packets "
            "can cause the relay to restart, potentially causing protection failures."
        ),
        "severity": "critical",
        "cvss_score": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7SJ85", "7SL87", "7UT87", "7SD87", "7SA87"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V08.20",
        "fixed_firmware_version": "V08.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-344-04",
        "references": [
            "https://cert-portal.siemens.com/productcert/pdf/ssa-817401.pdf",
        ],
        "mitre_techniques": ["T0831", "T0813"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 12, 10),
        "vulnerable_variants": [
            {
                "firmware_version": "V08.20",
                "display_name": "SIPROTEC 7SJ85 (CVE-2019-18285)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SJ85 Overcurrent Protection v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SJ85",
                    "major_minor_revision": "V08.20",
                    "product_name": "SIPROTEC 7SJ85 Overcurrent Protection",
                },
                "iec104_identity_override": {
                    "station_name": "7SJ85-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V08.20",
                "display_name": "SIPROTEC 7UT87 (CVE-2019-18285)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7UT87 Transformer Differential v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7UT87",
                    "major_minor_revision": "V08.20",
                    "product_name": "SIPROTEC 7UT87 Transformer Differential",
                },
                "iec104_identity_override": {
                    "station_name": "7UT87-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # CVE-2020-8568 - SIPROTEC 5 Information Disclosure
    {
        "cve_id": "CVE-2020-8568",
        "title": "Siemens SIPROTEC 5 Information Disclosure",
        "description": (
            "Siemens SIPROTEC 5 devices are vulnerable to information disclosure. "
            "An attacker can retrieve configuration data and credentials via the "
            "engineering interface, enabling further attacks."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7SJ85", "7SL87", "7UT87", "7SD87"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V08.11",
        "fixed_firmware_version": "V08.20",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-042-09",
        "references": [],
        "mitre_techniques": ["T0811", "T0846"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 2, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V08.11",
                "display_name": "SIPROTEC 7SL87 (CVE-2020-8568)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SL87 Line Differential v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SL87",
                    "major_minor_revision": "V08.11",
                    "product_name": "SIPROTEC 7SL87 Line Differential",
                },
            },
        ],
    },

    # ==================== GE Multilin CVEs ====================

    # CVE-2019-10935 - GE Multilin Hardcoded Credentials
    {
        "cve_id": "CVE-2019-10935",
        "title": "GE Multilin 850 Hardcoded Credentials",
        "description": (
            "GE Multilin 850 Feeder Protection System contains hardcoded credentials "
            "that could allow an attacker to gain unauthorized access to the device "
            "and modify protection settings."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N",
        "vendor": "GE",
        "product_family": "Multilin",
        "affected_models": ["850", "F650", "T60"],
        "affected_firmware_min": None,
        "affected_firmware_max": "7.20",
        "fixed_firmware_version": "7.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-192-06",
        "references": [],
        "mitre_techniques": ["T0859", "T0812"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 7, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "7.20",
                "display_name": "GE Multilin 850 (CVE-2019-10935)",
                "snmp_sys_descr_template": "GE Digital Energy Multilin 850 Feeder Protection v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Digital Energy",
                    "product_code": "850",
                    "major_minor_revision": "7.20",
                    "product_name": "Multilin 850 Feeder Protection System",
                },
                "dnp3_identity_override": {
                    "vendor_name": "GE",
                    "device_serial": "850-VULN",
                    "software_version": "7.20",
                },
            },
            {
                "firmware_version": "5.80",
                "display_name": "GE Multilin F650 (CVE-2019-10935)",
                "snmp_sys_descr_template": "GE Digital Energy Multilin F650 Bay Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Digital Energy",
                    "product_code": "F650",
                    "major_minor_revision": "5.80",
                    "product_name": "Multilin F650 Digital Bay Controller",
                },
                "dnp3_identity_override": {
                    "vendor_name": "GE",
                    "device_serial": "F650-VULN",
                    "software_version": "5.80",
                },
            },
        ],
    },

    # CVE-2018-10936 - GE Multilin Stack Buffer Overflow
    {
        "cve_id": "CVE-2018-10936",
        "title": "GE Multilin Relays Stack Buffer Overflow",
        "description": (
            "GE Multilin protection relays are vulnerable to a stack buffer overflow "
            "via malformed network packets. Exploitation could allow remote code "
            "execution or denial of service."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "GE",
        "product_family": "Multilin",
        "affected_models": ["T60", "C60", "D60", "L60"],
        "affected_firmware_min": None,
        "affected_firmware_max": "7.4",
        "fixed_firmware_version": "7.5",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-18-340-01",
        "references": [],
        "mitre_techniques": ["T0843", "T0831"],
        "exploit_available": True,
        "exploit_complexity": "medium",
        "published_date": datetime(2018, 12, 6),
        "vulnerable_variants": [
            {
                "firmware_version": "7.4",
                "display_name": "GE Multilin T60 (CVE-2018-10936)",
                "snmp_sys_descr_template": "GE Digital Energy Multilin T60 Transformer Protection v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "GE Digital Energy",
                    "product_code": "T60",
                    "major_minor_revision": "7.4",
                    "product_name": "Multilin T60 Transformer Protection",
                },
                "dnp3_identity_override": {
                    "vendor_name": "GE",
                    "device_serial": "T60-VULN",
                    "software_version": "7.4",
                },
            },
        ],
    },

    # ==================== ABB Protection Relay CVEs ====================

    # CVE-2021-22287 - ABB REF615 Authentication Bypass
    {
        "cve_id": "CVE-2021-22287",
        "title": "ABB REF615 Feeder Protection Authentication Bypass",
        "description": (
            "ABB REF615 feeder protection relays contain an authentication bypass "
            "vulnerability that allows unauthorized access to configuration interfaces. "
            "An attacker could modify protection settings leading to equipment damage."
        ),
        "severity": "critical",
        "cvss_score": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "ABB",
        "product_family": "Relion",
        "affected_models": ["REF615", "REX640", "REM615"],
        "affected_firmware_min": None,
        "affected_firmware_max": "9.2",
        "fixed_firmware_version": "9.3",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-110-02",
        "references": [
            "https://search.abb.com/library/Download.aspx?DocumentID=9AKK107991A5688",
        ],
        "mitre_techniques": ["T0859", "T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 4, 20),
        "vulnerable_variants": [
            {
                "firmware_version": "9.2",
                "display_name": "ABB REF615 (CVE-2021-22287)",
                "snmp_sys_descr_template": "ABB REF615 Feeder Protection Relay v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REF615",
                    "major_minor_revision": "9.2",
                    "product_name": "REF615 Feeder Protection Relay",
                },
                "iec104_identity_override": {
                    "station_name": "REF615-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "2.1",
                "display_name": "ABB REX640 (CVE-2021-22287)",
                "snmp_sys_descr_template": "ABB REX640 IEC 61850 Protection Relay v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REX640",
                    "major_minor_revision": "2.1",
                    "product_name": "REX640 IEC 61850 Protection Relay",
                },
                "iec104_identity_override": {
                    "station_name": "REX640-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # ==================== Schneider ION Meter CVEs ====================

    # CVE-2021-22714 - Schneider ION Meters DoS
    {
        "cve_id": "CVE-2021-22714",
        "title": "Schneider Electric ION Meters Denial of Service",
        "description": (
            "Schneider Electric ION series power meters are vulnerable to denial of "
            "service via malformed Modbus requests. This could disrupt power monitoring "
            "and metering functions in critical facilities."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Schneider",
        "product_family": "ION",
        "affected_models": ["ION8650", "ION7650", "ION7550"],
        "affected_firmware_min": None,
        "affected_firmware_max": "4.03.00",
        "fixed_firmware_version": "4.03.10",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-068-02",
        "references": [],
        "mitre_techniques": ["T0831"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 3, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "4.03.00",
                "display_name": "Schneider ION8650 (CVE-2021-22714)",
                "snmp_sys_descr_template": "Schneider Electric ION8650 Power Quality Meter v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "ION8650",
                    "major_minor_revision": "4.03.00",
                    "product_name": "ION8650 Power Quality Meter",
                },
            },
        ],
    },
]
