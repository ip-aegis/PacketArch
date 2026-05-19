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

    # ==================== SEL Family-Wide CVEs ====================

    # CVE-2023-31170 - SEL family-wide DNS Resolver Stack Overflow
    # CISA ICSA-23-187-01 - affects nearly the entire SEL product line through
    # a shared lwIP-based network stack used by relays and RTACs. SEL published
    # firmware updates across the 300/400/700/2400/3500 series in mid-2023.
    {
        "cve_id": "CVE-2023-31170",
        "title": "SEL Multiple Products lwIP DNS Resolver Stack Overflow",
        "description": (
            "Multiple SEL relays and Real-Time Automation Controllers using a shared "
            "embedded lwIP network stack contain a stack-based buffer overflow in the "
            "DNS resolver. A crafted DNS response from a network attacker on the "
            "management VLAN could cause memory corruption leading to denial of "
            "service or remote code execution, disrupting protection and automation "
            "functions on the substation LAN."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "SEL",
        "product_family": "Protection Relay",
        "affected_models": [
            "SEL-451", "SEL-487E", "SEL-751", "SEL-311C",
            "SEL-411L", "SEL-787", "SEL-3530", "SEL-3555", "SEL-2411",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "R151-V2",
        "fixed_firmware_version": "Vendor-specific (see SEL security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-187-01",
        "references": [
            "https://selinc.com/support/security-notifications/",
        ],
        "mitre_techniques": ["T0814", "T0831"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2023, 7, 6),
        "vulnerable_variants": [
            {
                "firmware_version": "R159-V2",
                "display_name": "SEL-451 (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-451 Bay Controller V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-451",
                    "major_minor_revision": "R159-V2",
                    "product_name": "SEL-451 Bay Controller",
                    "model_name": "SEL-451",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-451 Bay Controller",
                    "hardware_version": "451",
                    "software_version": "R159-V2",
                    "device_serial": "451-VULN",
                },
            },
            {
                "firmware_version": "R158-V2",
                "display_name": "SEL-487E (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-487E Transformer Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-487E",
                    "major_minor_revision": "R158-V2",
                    "product_name": "SEL-487E Transformer Protection Relay",
                    "model_name": "SEL-487E",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-487E Transformer Protection Relay",
                    "hardware_version": "487E",
                    "software_version": "R158-V2",
                    "device_serial": "487E-VULN",
                },
            },
            {
                "firmware_version": "R151-V2",
                "display_name": "SEL-751 (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-751 Feeder Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-751",
                    "major_minor_revision": "R151-V2",
                    "product_name": "SEL-751 Feeder Protection Relay",
                    "model_name": "SEL-751",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-751 Feeder Protection Relay",
                    "hardware_version": "751",
                    "software_version": "R151-V2",
                    "device_serial": "751-VULN",
                },
            },
            {
                "firmware_version": "R110-V3",
                "display_name": "SEL-311C (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-311C Line Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-311C",
                    "major_minor_revision": "R110-V3",
                    "product_name": "SEL-311C Line Protection Relay",
                    "model_name": "SEL-311C",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-311C Line Protection Relay",
                    "hardware_version": "311C",
                    "software_version": "R110-V3",
                    "device_serial": "311C-VULN",
                },
            },
            {
                "firmware_version": "R123-V2",
                "display_name": "SEL-411L (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-411L Line Current Differential System V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-411L",
                    "major_minor_revision": "R123-V2",
                    "product_name": "SEL-411L Line Current Differential System",
                    "model_name": "SEL-411L",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-411L Line Current Differential System",
                    "hardware_version": "411L",
                    "software_version": "R123-V2",
                    "device_serial": "411L-VULN",
                },
            },
            {
                "firmware_version": "R206-V2",
                "display_name": "SEL-787 (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-787 Transformer Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-787",
                    "major_minor_revision": "R206-V2",
                    "product_name": "SEL-787 Transformer Protection Relay",
                    "model_name": "SEL-787",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-787 Transformer Protection Relay",
                    "hardware_version": "787",
                    "software_version": "R206-V2",
                    "device_serial": "787-VULN",
                },
            },
            {
                "firmware_version": "R148-V2",
                "display_name": "SEL-3530 RTAC (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-3530 RTAC V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-3530",
                    "major_minor_revision": "R148-V2",
                    "product_name": "SEL-3530 Real-Time Automation Controller",
                    "model_name": "SEL-3530",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-3530 Real-Time Automation Controller",
                    "hardware_version": "3530",
                    "software_version": "R148-V2",
                    "device_serial": "3530-VULN",
                },
                "iec104_identity_override": {
                    "station_name": "SEL3530-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "R150-V1",
                "display_name": "SEL-3555 RTAC (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-3555 RTAC V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-3555",
                    "major_minor_revision": "R150-V1",
                    "product_name": "SEL-3555 Real-Time Automation Controller",
                    "model_name": "SEL-3555",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-3555 Real-Time Automation Controller",
                    "hardware_version": "3555",
                    "software_version": "R150-V1",
                    "device_serial": "3555-VULN",
                },
                "iec104_identity_override": {
                    "station_name": "SEL3555-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "R131-V2",
                "display_name": "SEL-2411 PAC (CVE-2023-31170)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-2411 Programmable Automation Controller V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-2411",
                    "major_minor_revision": "R131-V2",
                    "product_name": "SEL-2411 Programmable Automation Controller",
                    "model_name": "SEL-2411",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-2411 Programmable Automation Controller",
                    "hardware_version": "2411",
                    "software_version": "R131-V2",
                    "device_serial": "2411-VULN",
                },
            },
        ],
    },

    # CVE-2021-31553 - SEL Protection Relay multi-model auth/management vuln
    # CISA ICSA-21-208-XX; ties to legacy SEL firmware shipped on 300/400/700
    # series prior to the unified R140-series remediation.
    {
        "cve_id": "CVE-2021-31553",
        "title": "SEL Protection Relays Insufficient Authentication on Management Interface",
        "description": (
            "Multiple SEL protection relays expose a legacy management interface "
            "that fails to require authentication on certain administrative commands. "
            "An attacker with logical access to the substation LAN can read or modify "
            "non-protection settings, undermining the relay's trust boundary and "
            "providing a pivot for further attack."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "SEL",
        "product_family": "Protection Relay",
        "affected_models": ["SEL-751", "SEL-451", "SEL-487E", "SEL-311C"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R150-V0",
        "fixed_firmware_version": "Vendor-specific (see SEL security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-208-XX",
        "references": [
            "https://selinc.com/support/security-notifications/",
        ],
        "mitre_techniques": ["T0859", "T0812"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2021, 7, 27),
        "vulnerable_variants": [
            {
                "firmware_version": "R150-V0",
                "display_name": "SEL-751 (CVE-2021-31553)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-751 Feeder Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-751",
                    "major_minor_revision": "R150-V0",
                    "product_name": "SEL-751 Feeder Protection Relay",
                    "model_name": "SEL-751",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-751 Feeder Protection Relay",
                    "hardware_version": "751",
                    "software_version": "R150-V0",
                    "device_serial": "751-LEGACY-VULN",
                },
            },
            {
                "firmware_version": "R157-V0",
                "display_name": "SEL-451 (CVE-2021-31553)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-451 Bay Controller V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-451",
                    "major_minor_revision": "R157-V0",
                    "product_name": "SEL-451 Bay Controller",
                    "model_name": "SEL-451",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-451 Bay Controller",
                    "hardware_version": "451",
                    "software_version": "R157-V0",
                    "device_serial": "451-LEGACY-VULN",
                },
            },
            {
                "firmware_version": "R156-V0",
                "display_name": "SEL-487E (CVE-2021-31553)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-487E Transformer Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-487E",
                    "major_minor_revision": "R156-V0",
                    "product_name": "SEL-487E Transformer Protection Relay",
                    "model_name": "SEL-487E",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-487E Transformer Protection Relay",
                    "hardware_version": "487E",
                    "software_version": "R156-V0",
                    "device_serial": "487E-LEGACY-VULN",
                },
            },
            {
                "firmware_version": "R108-V0",
                "display_name": "SEL-311C (CVE-2021-31553)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-311C Line Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-311C",
                    "major_minor_revision": "R108-V0",
                    "product_name": "SEL-311C Line Protection Relay",
                    "model_name": "SEL-311C",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-311C Line Protection Relay",
                    "hardware_version": "311C",
                    "software_version": "R108-V0",
                    "device_serial": "311C-LEGACY-VULN",
                },
            },
        ],
    },

    # CVE-2020-24650 - SEL Firmware Information Disclosure on 400/700 series
    {
        "cve_id": "CVE-2020-24650",
        "title": "SEL Protection Relays Configuration Information Disclosure",
        "description": (
            "Certain SEL protection relays disclose protection settings and engineering "
            "metadata to unauthenticated network clients via legacy ports. An attacker "
            "on the substation LAN can enumerate trip thresholds, CT/PT ratios, and "
            "logic equations, providing reconnaissance for follow-on protection-system "
            "tampering."
        ),
        "severity": "medium",
        "cvss_score": 5.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "vendor": "SEL",
        "product_family": "Protection Relay",
        "affected_models": ["SEL-411L", "SEL-787", "SEL-735"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R203-V0",
        "fixed_firmware_version": "Vendor-specific (see SEL security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-XXX-XX",
        "references": [
            "https://selinc.com/support/security-notifications/",
        ],
        "mitre_techniques": ["T0846", "T0888"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 9, 1),
        "vulnerable_variants": [
            {
                "firmware_version": "R120-V0",
                "display_name": "SEL-411L (CVE-2020-24650)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-411L Line Current Differential System V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-411L",
                    "major_minor_revision": "R120-V0",
                    "product_name": "SEL-411L Line Current Differential System",
                    "model_name": "SEL-411L",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-411L Line Current Differential System",
                    "hardware_version": "411L",
                    "software_version": "R120-V0",
                    "device_serial": "411L-INFO-DISC",
                },
            },
            {
                "firmware_version": "R203-V0",
                "display_name": "SEL-787 (CVE-2020-24650)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-787 Transformer Protection Relay V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-787",
                    "major_minor_revision": "R203-V0",
                    "product_name": "SEL-787 Transformer Protection Relay",
                    "model_name": "SEL-787",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-787 Transformer Protection Relay",
                    "hardware_version": "787",
                    "software_version": "R203-V0",
                    "device_serial": "787-INFO-DISC",
                },
            },
            {
                "firmware_version": "R108-V1",
                "display_name": "SEL-735 Meter (CVE-2020-24650)",
                "snmp_sys_descr_template": "Schweitzer Engineering Laboratories SEL-735 Power Quality and Revenue Meter V{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "product_code": "SEL-735",
                    "major_minor_revision": "R108-V1",
                    "product_name": "SEL-735 Power Quality and Revenue Meter",
                    "model_name": "SEL-735",
                },
                "dnp3_identity_override": {
                    "vendor_name": "Schweitzer Engineering Laboratories",
                    "device_name": "SEL-735 Power Quality and Revenue Meter",
                    "hardware_version": "735",
                    "software_version": "R108-V1",
                    "device_serial": "735-INFO-DISC",
                },
            },
        ],
    },

    # ==================== Siemens SIPROTEC 5 Additional CVEs ====================

    # CVE-2022-32528 - Siemens SIPROTEC 5 Multiple Vulnerabilities
    # CISA ICSA-22-167-15 / Siemens SSA-794525
    {
        "cve_id": "CVE-2022-32528",
        "title": "Siemens SIPROTEC 5 Multiple Vulnerabilities",
        "description": (
            "Multiple vulnerabilities have been identified in SIPROTEC 5 devices with "
            "CPU variants CP100, CP200, and CP300. An unauthenticated remote attacker "
            "could send specially crafted packets to a vulnerable device to cause a "
            "denial-of-service condition, requiring a manual restart of the device and "
            "potentially impacting protection availability across a substation bay."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7SD87", "7SJ85", "7SL87", "7UT87"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V9.20",
        "fixed_firmware_version": "V9.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-167-15",
        "references": [
            "https://cert-portal.siemens.com/productcert/pdf/ssa-794525.pdf",
        ],
        "mitre_techniques": ["T0814", "T0816"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 6, 16),
        "vulnerable_variants": [
            {
                "firmware_version": "V9.10",
                "display_name": "SIPROTEC 7SD87 (CVE-2022-32528)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SD87 Differential Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SD87",
                    "major_minor_revision": "V9.10",
                    "product_name": "SIPROTEC 7SD87 Differential Protection",
                },
                "iec104_identity_override": {
                    "station_name": "7SD87-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V9.20",
                "display_name": "SIPROTEC 7SJ85 (CVE-2022-32528)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SJ85 Overcurrent Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SJ85",
                    "major_minor_revision": "V9.20",
                    "product_name": "SIPROTEC 7SJ85 Overcurrent Protection",
                },
                "iec104_identity_override": {
                    "station_name": "7SJ85-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V9.20",
                "display_name": "SIPROTEC 7SL87 (CVE-2022-32528)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SL87 Line Differential {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SL87",
                    "major_minor_revision": "V9.20",
                    "product_name": "SIPROTEC 7SL87 Line Differential",
                },
                "iec104_identity_override": {
                    "station_name": "7SL87-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V9.20",
                "display_name": "SIPROTEC 7UT87 (CVE-2022-32528)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7UT87 Transformer Differential {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7UT87",
                    "major_minor_revision": "V9.20",
                    "product_name": "SIPROTEC 7UT87 Transformer Differential",
                },
                "iec104_identity_override": {
                    "station_name": "7UT87-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # CVE-2020-15795 - Siemens SIPROTEC 5 Improper Input Validation
    {
        "cve_id": "CVE-2020-15795",
        "title": "Siemens SIPROTEC 5 Improper Input Validation",
        "description": (
            "SIPROTEC 5 devices with firmware versions prior to V8.30 contain an "
            "improper input validation vulnerability in the network interface. A "
            "specially crafted packet could cause the device to enter an undefined "
            "state, requiring a manual reboot to restore protection function."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7SJ85", "7SL87", "7UT87"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V8.30",
        "fixed_firmware_version": "V8.40",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-XXX-XX",
        "references": [
            "https://cert-portal.siemens.com/productcert/",
        ],
        "mitre_techniques": ["T0814", "T0831"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 9, 8),
        "vulnerable_variants": [
            {
                "firmware_version": "V8.30",
                "display_name": "SIPROTEC 7SJ85 (CVE-2020-15795)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SJ85 Overcurrent Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SJ85",
                    "major_minor_revision": "V8.30",
                    "product_name": "SIPROTEC 7SJ85 Overcurrent Protection",
                },
                "iec104_identity_override": {
                    "station_name": "7SJ85-LEGACY-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V8.30",
                "display_name": "SIPROTEC 7SL87 (CVE-2020-15795)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SL87 Line Differential {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SL87",
                    "major_minor_revision": "V8.30",
                    "product_name": "SIPROTEC 7SL87 Line Differential",
                },
                "iec104_identity_override": {
                    "station_name": "7SL87-LEGACY-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V8.30",
                "display_name": "SIPROTEC 7UT87 (CVE-2020-15795)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7UT87 Transformer Differential {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7UT87",
                    "major_minor_revision": "V8.30",
                    "product_name": "SIPROTEC 7UT87 Transformer Differential",
                },
                "iec104_identity_override": {
                    "station_name": "7UT87-LEGACY-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # CVE-2024-31486 - Siemens SIPROTEC 5 7SS85 vulnerability (recent)
    {
        "cve_id": "CVE-2024-31486",
        "title": "Siemens SIPROTEC 5 7SS85 Network Stack Vulnerability",
        "description": (
            "SIPROTEC 5 7SS85 busbar differential protection relays contain a "
            "vulnerability in the embedded network stack that allows an "
            "unauthenticated attacker on the substation LAN to disrupt the relay's "
            "communications, potentially impacting GOOSE/SV-based busbar protection "
            "and requiring manual recovery."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7SS85"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V9.20",
        "fixed_firmware_version": "V9.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-24-XXX-XX",
        "references": [
            "https://cert-portal.siemens.com/productcert/",
        ],
        "mitre_techniques": ["T0814", "T0816"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2024, 4, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "V9.20",
                "display_name": "SIPROTEC 7SS85 (CVE-2024-31486)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SS85 Busbar Differential {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SS85",
                    "major_minor_revision": "V9.20",
                    "product_name": "SIPROTEC 7SS85 Busbar Differential",
                },
                "iec61850_identity_override": {
                    "ied_name": "SIE_7SS85_VULN_E01",
                    "vendor": "Siemens AG",
                    "software_version": "V9.20",
                },
            },
        ],
    },

    # CVE-2023-30899 - Siemens SIPROTEC 5 (7UM85, 7VK87)
    {
        "cve_id": "CVE-2023-30899",
        "title": "Siemens SIPROTEC 5 Web Interface Information Disclosure",
        "description": (
            "Certain SIPROTEC 5 firmware revisions allow an unauthenticated remote "
            "attacker to obtain sensitive configuration information from the device's "
            "web interface. The disclosed information can aid in further attacks "
            "against the substation protection system."
        ),
        "severity": "medium",
        "cvss_score": 6.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7UM85", "7VK87"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V9.20",
        "fixed_firmware_version": "V9.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-XXX-XX",
        "references": [
            "https://cert-portal.siemens.com/productcert/",
        ],
        "mitre_techniques": ["T0846", "T0888"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 6, 13),
        "vulnerable_variants": [
            {
                "firmware_version": "V8.40",
                "display_name": "SIPROTEC 7UM85 (CVE-2023-30899)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7UM85 Generator Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7UM85",
                    "major_minor_revision": "V8.40",
                    "product_name": "SIPROTEC 7UM85 Generator Protection",
                },
                "iec61850_identity_override": {
                    "ied_name": "SIE_7UM85_VULN_E01",
                    "vendor": "Siemens AG",
                    "software_version": "V8.40",
                },
            },
            {
                "firmware_version": "V9.20",
                "display_name": "SIPROTEC 7VK87 (CVE-2023-30899)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7VK87 Autoreclose / Synchrocheck {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7VK87",
                    "major_minor_revision": "V9.20",
                    "product_name": "SIPROTEC 7VK87 Autoreclose / Synchrocheck",
                },
                "iec61850_identity_override": {
                    "ied_name": "SIE_7VK87_VULN_E01",
                    "vendor": "Siemens AG",
                    "software_version": "V9.20",
                },
            },
        ],
    },

    # CVE-2023-32785 - Siemens SIPROTEC 5 7UM85 specific
    {
        "cve_id": "CVE-2023-32785",
        "title": "Siemens SIPROTEC 7UM85 Generator Protection Authentication Weakness",
        "description": (
            "SIPROTEC 7UM85 generator protection relays running affected firmware "
            "implement an authentication mechanism that can be bypassed under "
            "specific network conditions, allowing limited read access to "
            "engineering data."
        ),
        "severity": "medium",
        "cvss_score": 5.3,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7UM85"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V9.20",
        "fixed_firmware_version": "V9.30",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-XXX-XX",
        "references": [
            "https://cert-portal.siemens.com/productcert/",
        ],
        "mitre_techniques": ["T0859"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2023, 7, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V9.20",
                "display_name": "SIPROTEC 7UM85 (CVE-2023-32785)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7UM85 Generator Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7UM85",
                    "major_minor_revision": "V9.20",
                    "product_name": "SIPROTEC 7UM85 Generator Protection",
                },
                "iec61850_identity_override": {
                    "ied_name": "SIE_7UM85_AUTH_VULN",
                    "vendor": "Siemens AG",
                    "software_version": "V9.20",
                },
            },
        ],
    },

    # CVE-2015-5374 - Siemens SIPROTEC firmware DoS (historic, INDUSTROYER-relevant)
    # Originally targeted SIPROTEC 4 / EN100 module; templates apply it to legacy
    # variants of 7SS85 and 7VK87 as a representative historic DoS vulnerability.
    {
        "cve_id": "CVE-2015-5374",
        "title": "Siemens SIPROTEC EN100 Ethernet Module Denial of Service",
        "description": (
            "A vulnerability in the EN100 Ethernet module integrated with certain "
            "SIPROTEC protection relays allows a remote attacker to send a single "
            "crafted UDP packet to port 50000/UDP that causes the network stack to "
            "stop responding until the device is manually rebooted. This "
            "vulnerability was referenced in post-mortem analyses of the 2016 "
            "Ukraine power-grid attack (INDUSTROYER/CRASHOVERRIDE)."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "SIPROTEC 5",
        "affected_models": ["7SS85", "7VK87"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V8.40",
        "fixed_firmware_version": "V8.50",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-15-202-01",
        "references": [
            "https://cert-portal.siemens.com/productcert/pdf/ssa-603476.pdf",
            "https://www.welivesecurity.com/2017/06/12/industroyer-biggest-threat-industrial-control-systems-since-stuxnet/",
        ],
        "mitre_techniques": ["T0814", "T0816", "T0826"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2015, 7, 21),
        "vulnerable_variants": [
            {
                "firmware_version": "V8.40",
                "display_name": "SIPROTEC 7SS85 (CVE-2015-5374 EN100 DoS)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7SS85 Busbar Differential {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7SS85",
                    "major_minor_revision": "V8.40",
                    "product_name": "SIPROTEC 7SS85 Busbar Differential",
                },
                "iec104_identity_override": {
                    "station_name": "7SS85-EN100-VULN",
                    "common_address": 1,
                },
            },
            {
                "firmware_version": "V8.40",
                "display_name": "SIPROTEC 7VK87 (CVE-2015-5374 EN100 DoS)",
                "snmp_sys_descr_template": "Siemens SIPROTEC 7VK87 Autoreclose / Synchrocheck {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Siemens AG",
                    "product_code": "7VK87",
                    "major_minor_revision": "V8.40",
                    "product_name": "SIPROTEC 7VK87 Autoreclose / Synchrocheck",
                },
                "iec104_identity_override": {
                    "station_name": "7VK87-EN100-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # ==================== ABB Relion / Symphony Plus CVEs ====================

    # CVE-2021-22276 - ABB Relion 615/630/670 series authentication / config vuln
    {
        "cve_id": "CVE-2021-22276",
        "title": "ABB Relion Series Multiple Authentication Vulnerabilities",
        "description": (
            "Multiple ABB Relion series protection relays contain authentication "
            "weaknesses in the WHMI web management interface and engineering "
            "protocols. An attacker with network access could escalate privileges, "
            "modify protection settings, or extract configuration data, undermining "
            "the integrity of substation protection schemes."
        ),
        "severity": "high",
        "cvss_score": 8.2,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N",
        "vendor": "ABB",
        "product_family": "Relion",
        "affected_models": ["REL630", "RED615", "REL670"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V2.2.1",
        "fixed_firmware_version": "Vendor-specific (see ABB security advisory)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-XXX-XX",
        "references": [
            "https://search.abb.com/library/Download.aspx?DocumentID=2NGA001214",
        ],
        "mitre_techniques": ["T0859", "T0812", "T0846"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2021, 5, 25),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.2.1",
                "display_name": "ABB REL630 (CVE-2021-22276)",
                "snmp_sys_descr_template": "ABB Relion REL630 Line Distance Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REL630",
                    "major_minor_revision": "V2.2.1",
                    "product_name": "Relion REL630 Line Distance Protection",
                },
                "iec104_identity_override": {
                    "station_name": "REL630-VULN",
                    "common_address": 1,
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_REL630_VULN_IED",
                    "vendor": "ABB",
                    "software_version": "V2.2.1",
                },
            },
            {
                "firmware_version": "V4.0",
                "display_name": "ABB RED615 (CVE-2021-22276)",
                "snmp_sys_descr_template": "ABB Relion RED615 Line Differential Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "RED615",
                    "major_minor_revision": "V4.0",
                    "product_name": "Relion RED615 Line Differential Protection",
                },
                "iec104_identity_override": {
                    "station_name": "RED615-VULN",
                    "common_address": 1,
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_RED615_VULN_IED",
                    "vendor": "ABB",
                    "software_version": "V4.0",
                },
            },
            {
                "firmware_version": "V2.2.0",
                "display_name": "ABB REL670 (CVE-2021-22276)",
                "snmp_sys_descr_template": "ABB Relion REL670 Line Distance Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REL670",
                    "major_minor_revision": "V2.2.0",
                    "product_name": "Relion REL670 Line Distance Protection",
                },
                "iec104_identity_override": {
                    "station_name": "REL670-VULN",
                    "common_address": 1,
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_REL670_VULN_IED",
                    "vendor": "ABB",
                    "software_version": "V2.2.0",
                },
            },
        ],
    },

    # CVE-2022-26143 - ABB Relion / Symphony Plus management plane vuln
    {
        "cve_id": "CVE-2022-26143",
        "title": "ABB Relion and Symphony Plus Management Interface Vulnerability",
        "description": (
            "Affected ABB Relion protection relays and Symphony Plus HPG800 process "
            "controllers expose a management-plane vulnerability that allows an "
            "authenticated remote attacker to manipulate device configuration. In a "
            "substation or generation plant environment, exploitation could degrade "
            "protection coordination or DCS supervisory control."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:N",
        "vendor": "ABB",
        "product_family": "Relion",
        "affected_models": ["HPG800", "REL630", "REL670"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V3.1.0",
        "fixed_firmware_version": "Vendor-specific (see ABB security advisory)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-XXX-XX",
        "references": [
            "https://search.abb.com/library/Download.aspx?DocumentID=2NGA001311",
        ],
        "mitre_techniques": ["T0836", "T0855"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2022, 3, 1),
        "vulnerable_variants": [
            {
                "firmware_version": "V3.1.0",
                "display_name": "ABB Symphony Plus HPG800 (CVE-2022-26143)",
                "snmp_sys_descr_template": "ABB Symphony Plus HPG800 Harmony Process Gateway {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "HPG800",
                    "major_minor_revision": "V3.1.0",
                    "product_name": "Symphony Plus HPG800 Harmony Process Gateway",
                },
            },
            {
                "firmware_version": "V2.1.0",
                "display_name": "ABB REL630 (CVE-2022-26143)",
                "snmp_sys_descr_template": "ABB Relion REL630 Line Distance Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REL630",
                    "major_minor_revision": "V2.1.0",
                    "product_name": "Relion REL630 Line Distance Protection",
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_REL630_MGMT_VULN",
                    "vendor": "ABB",
                    "software_version": "V2.1.0",
                },
            },
            {
                "firmware_version": "V2.2.0",
                "display_name": "ABB REL670 (CVE-2022-26143)",
                "snmp_sys_descr_template": "ABB Relion REL670 Line Distance Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REL670",
                    "major_minor_revision": "V2.2.0",
                    "product_name": "Relion REL670 Line Distance Protection",
                },
                "iec104_identity_override": {
                    "station_name": "REL670-MGMT-VULN",
                    "common_address": 1,
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_REL670_MGMT_VULN",
                    "vendor": "ABB",
                    "software_version": "V2.2.0",
                },
            },
        ],
    },

    # CVE-2023-26517 - ABB Relion 615 / 670 firmware vulnerability
    {
        "cve_id": "CVE-2023-26517",
        "title": "ABB Relion 615 / 670 Series Firmware Vulnerability",
        "description": (
            "ABB Relion RED615 line-differential and REL670 transmission-distance "
            "protection IEDs running affected firmware contain a vulnerability in "
            "the engineering-protocol handler that allows a remote authenticated "
            "attacker to disrupt the device or extract sensitive engineering data."
        ),
        "severity": "high",
        "cvss_score": 7.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:H",
        "vendor": "ABB",
        "product_family": "Relion",
        "affected_models": ["RED615", "REL670"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V4.2",
        "fixed_firmware_version": "Vendor-specific (see ABB security advisory)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-XXX-XX",
        "references": [
            "https://search.abb.com/library/Download.aspx?DocumentID=2NGA001489",
        ],
        "mitre_techniques": ["T0846", "T0814"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2023, 4, 18),
        "vulnerable_variants": [
            {
                "firmware_version": "V4.2",
                "display_name": "ABB RED615 (CVE-2023-26517)",
                "snmp_sys_descr_template": "ABB Relion RED615 Line Differential Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "RED615",
                    "major_minor_revision": "V4.2",
                    "product_name": "Relion RED615 Line Differential Protection",
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_RED615_ENG_VULN",
                    "vendor": "ABB",
                    "software_version": "V4.2",
                },
            },
            {
                "firmware_version": "V2.2.3",
                "display_name": "ABB REL670 (CVE-2023-26517)",
                "snmp_sys_descr_template": "ABB Relion REL670 Line Distance Protection {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "ABB",
                    "product_code": "REL670",
                    "major_minor_revision": "V2.2.3",
                    "product_name": "Relion REL670 Line Distance Protection",
                },
                "iec104_identity_override": {
                    "station_name": "REL670-ENG-VULN",
                    "common_address": 1,
                },
                "iec61850_identity_override": {
                    "ied_name": "ABB_REL670_ENG_VULN",
                    "vendor": "ABB",
                    "software_version": "V2.2.3",
                },
            },
        ],
    },

    # ==================== Schneider MiCOM / Easergy CVEs ====================

    # CVE-2021-22772 - Schneider MiCOM authentication vulnerability
    {
        "cve_id": "CVE-2021-22772",
        "title": "Schneider Electric MiCOM Protection Relay Authentication Bypass",
        "description": (
            "Schneider Electric MiCOM P40/P540/P740 series protection relays and the "
            "C264 substation bay computer contain an authentication weakness in the "
            "legacy management interface used by EcoStruxure engineering tools. An "
            "attacker on the substation LAN could bypass authentication to read or "
            "modify non-protection settings, providing a foothold for further "
            "protection-system tampering."
        ),
        "severity": "critical",
        "cvss_score": 9.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L",
        "vendor": "Schneider",
        "product_family": "MiCOM",
        "affected_models": ["P145", "P543", "P746", "C264"],
        "affected_firmware_min": None,
        "affected_firmware_max": "D4.0",
        "fixed_firmware_version": "Vendor-specific (see Schneider security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-XXX-XX",
        "references": [
            "https://www.se.com/ww/en/download/document/SEVD-2021-073-XX/",
        ],
        "mitre_techniques": ["T0859", "T0812", "T0836"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 3, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "B2.1",
                "display_name": "MiCOM P145 (CVE-2021-22772)",
                "snmp_sys_descr_template": "Schneider Electric MiCOM P40 Agile P145 Feeder Management Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P145",
                    "major_minor_revision": "B2.1",
                    "product_name": "MiCOM P40 Agile P145 Feeder Management Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "P145MICOM_VULN_01",
                    "vendor": "Schneider Electric",
                    "software_version": "B2.1",
                },
            },
            {
                "firmware_version": "D4.0",
                "display_name": "MiCOM P543 (CVE-2021-22772)",
                "snmp_sys_descr_template": "Schneider Electric MiCOM P543 Line Differential Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P543",
                    "major_minor_revision": "D4.0",
                    "product_name": "MiCOM P543 Line Differential Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "P543MICOM_VULN_01",
                    "vendor": "Schneider Electric",
                    "software_version": "D4.0",
                },
            },
            {
                "firmware_version": "B2.4",
                "display_name": "MiCOM P746 (CVE-2021-22772)",
                "snmp_sys_descr_template": "Schneider Electric MiCOM P746 Busbar Differential Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P746",
                    "major_minor_revision": "B2.4",
                    "product_name": "MiCOM P746 Busbar Differential Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "P746MICOM_VULN_01",
                    "vendor": "Schneider Electric",
                    "software_version": "B2.4",
                },
            },
            {
                "firmware_version": "P14.A1",
                "display_name": "MiCOM C264 Bay Computer (CVE-2021-22772)",
                "snmp_sys_descr_template": "Schneider Electric MiCOM C264 Substation Bay Computer {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "C264",
                    "major_minor_revision": "P14.A1",
                    "product_name": "MiCOM C264 Substation Bay Computer",
                },
                "iec61850_identity_override": {
                    "ied_name": "C264BAY_VULN_01",
                    "vendor": "Schneider Electric",
                    "software_version": "P14.A1",
                },
            },
        ],
    },

    # CVE-2022-37300 - Schneider Easergy Path Traversal
    {
        "cve_id": "CVE-2022-37300",
        "title": "Schneider Electric Easergy Path Traversal",
        "description": (
            "Schneider Electric Easergy P1, P3, and T300 product families contain a "
            "path-traversal vulnerability in their embedded web interface. An "
            "unauthenticated remote attacker could craft a request that escapes the "
            "web root and reads arbitrary files from the device, disclosing "
            "configuration data and credentials usable for further attack."
        ),
        "severity": "high",
        "cvss_score": 8.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "Schneider",
        "product_family": "Easergy",
        "affected_models": ["P1F30", "P3U30", "T300"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V30.20",
        "fixed_firmware_version": "Vendor-specific (see Schneider security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-XXX-XX",
        "references": [
            "https://www.se.com/ww/en/download/document/SEVD-2022-221-XX/",
        ],
        "mitre_techniques": ["T0846", "T0859"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 8, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "V1.6.0",
                "display_name": "Easergy P1 (CVE-2022-37300)",
                "snmp_sys_descr_template": "Schneider Electric Easergy P1 Feeder Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P1F30",
                    "major_minor_revision": "V1.6.0",
                    "product_name": "Easergy P1 Feeder Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "EASERGY_P1_VULN_01",
                    "vendor": "Schneider Electric",
                    "software_version": "V1.6.0",
                },
            },
            {
                "firmware_version": "V30.20",
                "display_name": "Easergy P3 (CVE-2022-37300)",
                "snmp_sys_descr_template": "Schneider Electric Easergy P3 Universal Feeder Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P3U30",
                    "major_minor_revision": "V30.20",
                    "product_name": "Easergy P3 Universal Feeder Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "EASERGY_P3_VULN_01",
                    "vendor": "Schneider Electric",
                    "software_version": "V30.20",
                },
            },
            {
                "firmware_version": "V2.7.0",
                "display_name": "Easergy T300 (CVE-2022-37300)",
                "snmp_sys_descr_template": "Schneider Electric Easergy T300 Feeder RTU {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "T300",
                    "major_minor_revision": "V2.7.0",
                    "product_name": "Easergy T300 Feeder RTU",
                },
                "iec104_identity_override": {
                    "station_name": "EASERGY-T300-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # CVE-2022-37301 - Schneider Easergy Hard-coded Credentials / Auth Bypass companion
    {
        "cve_id": "CVE-2022-37301",
        "title": "Schneider Electric Easergy Hard-coded Credentials",
        "description": (
            "Schneider Electric Easergy P1, P3, and T300 family devices ship with "
            "hard-coded credentials in their embedded service account. An attacker "
            "with knowledge of the credentials can authenticate to the device and "
            "modify protection or automation settings, posing a serious risk in "
            "distribution-feeder environments."
        ),
        "severity": "high",
        "cvss_score": 7.2,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Easergy",
        "affected_models": ["P1F30", "P3U30", "T300"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V30.20",
        "fixed_firmware_version": "Vendor-specific (see Schneider security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-XXX-XX",
        "references": [
            "https://www.se.com/ww/en/download/document/SEVD-2022-221-XX/",
        ],
        "mitre_techniques": ["T0812", "T0859"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 8, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "V1.6.0",
                "display_name": "Easergy P1 (CVE-2022-37301)",
                "snmp_sys_descr_template": "Schneider Electric Easergy P1 Feeder Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P1F30",
                    "major_minor_revision": "V1.6.0",
                    "product_name": "Easergy P1 Feeder Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "EASERGY_P1_HC_VULN",
                    "vendor": "Schneider Electric",
                    "software_version": "V1.6.0",
                },
            },
            {
                "firmware_version": "V30.20",
                "display_name": "Easergy P3 (CVE-2022-37301)",
                "snmp_sys_descr_template": "Schneider Electric Easergy P3 Universal Feeder Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P3U30",
                    "major_minor_revision": "V30.20",
                    "product_name": "Easergy P3 Universal Feeder Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "EASERGY_P3_HC_VULN",
                    "vendor": "Schneider Electric",
                    "software_version": "V30.20",
                },
            },
            {
                "firmware_version": "V2.7.0",
                "display_name": "Easergy T300 (CVE-2022-37301)",
                "snmp_sys_descr_template": "Schneider Electric Easergy T300 Feeder RTU {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "T300",
                    "major_minor_revision": "V2.7.0",
                    "product_name": "Easergy T300 Feeder RTU",
                },
                "iec104_identity_override": {
                    "station_name": "EASERGY-T300-HC-VULN",
                    "common_address": 1,
                },
            },
        ],
    },

    # CVE-2023-37193 - Schneider Easergy P3 / T300 Info Disclosure
    {
        "cve_id": "CVE-2023-37193",
        "title": "Schneider Electric Easergy P3 / T300 Information Disclosure",
        "description": (
            "Easergy P3 and T300 devices running affected firmware allow an "
            "unauthenticated remote attacker to retrieve sensitive configuration "
            "information from the management interface. The disclosed data can be "
            "used to plan further attacks against the device or the surrounding "
            "distribution-automation network."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Schneider",
        "product_family": "Easergy",
        "affected_models": ["P3U30", "T300"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V30.20",
        "fixed_firmware_version": "Vendor-specific (see Schneider security notification)",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-XXX-XX",
        "references": [
            "https://www.se.com/ww/en/download/document/SEVD-2023-194-XX/",
        ],
        "mitre_techniques": ["T0846", "T0888"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 7, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V30.20",
                "display_name": "Easergy P3 (CVE-2023-37193)",
                "snmp_sys_descr_template": "Schneider Electric Easergy P3 Universal Feeder Protection Relay {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "P3U30",
                    "major_minor_revision": "V30.20",
                    "product_name": "Easergy P3 Universal Feeder Protection Relay",
                },
                "iec61850_identity_override": {
                    "ied_name": "EASERGY_P3_INFO_VULN",
                    "vendor": "Schneider Electric",
                    "software_version": "V30.20",
                },
            },
            {
                "firmware_version": "V2.7.0",
                "display_name": "Easergy T300 (CVE-2023-37193)",
                "snmp_sys_descr_template": "Schneider Electric Easergy T300 Feeder RTU {firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Schneider Electric",
                    "product_code": "T300",
                    "major_minor_revision": "V2.7.0",
                    "product_name": "Easergy T300 Feeder RTU",
                },
                "iec104_identity_override": {
                    "station_name": "EASERGY-T300-INFO-VULN",
                    "common_address": 1,
                },
            },
        ],
    },
]
