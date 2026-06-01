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

    # ==================== ABB Protection Relay CVEs ====================

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
        "cvss_score": 9.8,
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
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2021-22276",
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
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2021-22772",
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
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2022-37301",
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

]
