"""Siemens CVE data.

CVE information for S7-1200, S7-1500, and S7-300/400 series PLCs.
These vulnerabilities are detectable via firmware version strings in
S7comm SZL responses and PROFINET DCP identify responses.
"""

from datetime import datetime

SIEMENS_CVES: list[dict] = [
    # CVE-2019-13945 - S7-1500 CPU Cryptographic Vulnerability
    {
        "cve_id": "CVE-2019-13945",
        "title": "Siemens S7-1500 CPU Cryptographic Vulnerability",
        "description": (
            "A vulnerability has been identified in SIMATIC S7-1500 CPU family. "
            "An attacker with network access to an affected device could use the "
            "vulnerability to decrypt the S7 communication and spoof user data."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Siemens",
        "product_family": "S7-1500",
        "affected_models": [
            "6ES7 510-1DJ01-0AB0", "6ES7 511-1AK02-0AB0",
            "6ES7 512-1CK01-0AB0", "6ES7 513-1AL02-0AB0",
            "6ES7 515-2AM02-0AB0", "6ES7 516-3AN01-0AB0",
            "6ES7 517-3AP00-0AB0", "6ES7 518-4AP00-0AB0",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "V2.8.0",
        "fixed_firmware_version": "V2.8.1",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-232418.pdf",
        "references": [
            "https://www.cisa.gov/news-events/ics-advisories/icsa-19-344-04",
        ],
        "mitre_techniques": ["T0882", "T0888"],
        "exploit_available": True,
        "exploit_complexity": "medium",
        "published_date": datetime(2019, 12, 10),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.8.0",
                "display_name": "S7-1516 CPU (CVE-2019-13945)",
                "s7_identity_override": {
                    "order_code": "6ES7 516-3AN01-0AB0",
                    "module_type": "CPU 1516-3 PN/DP",
                    "firmware_version": "V2.8.0",
                    "serial_number": "S V-P92001234",
                    "hardware_version": "1",
                },
                "profinet_identity_override": {
                    "vendor_id": 0x002A,  # Siemens PROFINET vendor ID
                    "device_id": 0x0500,
                    "device_type": "CPU 1516-3 PN/DP",
                    "device_role": "controller",
                    "sw_release": "V2.8.0",
                    "order_id": "6ES7 516-3AN01-0AB0",
                },
            },
            {
                "firmware_version": "V2.6.1",
                "display_name": "S7-1515 CPU (CVE-2019-13945)",
                "s7_identity_override": {
                    "order_code": "6ES7 515-2AM02-0AB0",
                    "module_type": "CPU 1515-2 PN",
                    "firmware_version": "V2.6.1",
                    "serial_number": "S V-P91001234",
                },
                "profinet_identity_override": {
                    "vendor_id": 0x002A,
                    "device_id": 0x0400,
                    "device_type": "CPU 1515-2 PN",
                    "sw_release": "V2.6.1",
                    "order_id": "6ES7 515-2AM02-0AB0",
                },
            },
        ],
    },

    # CVE-2020-15782 - S7-1200/1500 Memory Protection Bypass (CRITICAL)
    {
        "cve_id": "CVE-2020-15782",
        "title": "Siemens S7-1200/1500 Memory Protection Bypass",
        "description": (
            "A vulnerability exists in SIMATIC S7-1200 and S7-1500 CPU families "
            "that could allow an attacker to gain native code execution on the "
            "devices. This vulnerability enables bypassing memory protection "
            "mechanisms to read and write to any memory area."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Siemens",
        "product_family": "S7-1500",
        "affected_models": [
            "6ES7 510-1DJ01-0AB0", "6ES7 511-1AK02-0AB0",
            "6ES7 512-1CK01-0AB0", "6ES7 513-1AL02-0AB0",
            "6ES7 515-2AM02-0AB0", "6ES7 516-3AN01-0AB0",
            "6ES7 517-3AP00-0AB0", "6ES7 518-4AP00-0AB0",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "V2.9.1",
        "fixed_firmware_version": "V2.9.2",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-434534.pdf",
        "references": [
            "https://www.cisa.gov/news-events/ics-advisories/icsa-21-131-05",
        ],
        "mitre_techniques": ["T0843", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 5, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.9.1",
                "display_name": "S7-1516 CPU (CVE-2020-15782)",
                "s7_identity_override": {
                    "order_code": "6ES7 516-3AN01-0AB0",
                    "module_type": "CPU 1516-3 PN/DP",
                    "firmware_version": "V2.9.1",
                },
                "profinet_identity_override": {
                    "vendor_id": 0x002A,
                    "device_id": 0x0500,
                    "device_type": "CPU 1516-3 PN/DP",
                    "sw_release": "V2.9.1",
                    "order_id": "6ES7 516-3AN01-0AB0",
                },
            },
        ],
    },

    # CVE-2019-10929 - S7-1200 Web Server Vulnerability
    {
        "cve_id": "CVE-2019-10929",
        "title": "Siemens S7-1200 Web Server Vulnerability",
        "description": (
            "Affected devices contain a vulnerability that could allow an attacker "
            "to cause a denial-of-service condition on the web server of an affected "
            "device. This could result in the web server going into a defect mode."
        ),
        "severity": "high",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Siemens",
        "product_family": "S7-1200",
        "affected_models": [
            "6ES7 211-1AE40-0XB0", "6ES7 211-1BE40-0XB0",
            "6ES7 212-1AE40-0XB0", "6ES7 212-1BE40-0XB0",
            "6ES7 214-1AG40-0XB0", "6ES7 214-1BG40-0XB0",
            "6ES7 215-1AG40-0XB0", "6ES7 215-1BG40-0XB0",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "V4.3",
        "fixed_firmware_version": "V4.4",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-121293.pdf",
        "references": [],
        "mitre_techniques": ["T0815", "T0808"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 8, 13),
        "vulnerable_variants": [
            {
                "firmware_version": "V4.3",
                "display_name": "S7-1215C CPU (CVE-2019-10929)",
                "s7_identity_override": {
                    "order_code": "6ES7 215-1AG40-0XB0",
                    "module_type": "CPU 1215C DC/DC/DC",
                    "firmware_version": "V4.3",
                },
                "profinet_identity_override": {
                    "vendor_id": 0x002A,
                    "device_id": 0x0200,
                    "device_type": "CPU 1215C DC/DC/DC",
                    "sw_release": "V4.3",
                    "order_id": "6ES7 215-1AG40-0XB0",
                },
            },
        ],
    },

    # CVE-2022-38465 - S7-1500 TM MFP Vulnerability
    {
        "cve_id": "CVE-2022-38465",
        "title": "Siemens S7-1500 TM MFP Hardcoded Key Vulnerability",
        "description": (
            "Affected devices use a hardcoded key to obfuscate the PROFINET system "
            "redundancy state. An attacker with physical access could extract the "
            "key and decrypt the data."
        ),
        "severity": "medium",
        "cvss_score": 6.8,
        "cvss_vector": "CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Siemens",
        "product_family": "S7-1500",
        "affected_models": [
            "6ES7 516-3AN01-0AB0", "6ES7 517-3AP00-0AB0",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "V3.0.0",
        "fixed_firmware_version": "V3.0.1",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-568427.pdf",
        "references": [],
        "mitre_techniques": ["T0882"],
        "exploit_available": False,
        "exploit_complexity": "high",
        "published_date": datetime(2022, 10, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V3.0.0",
                "display_name": "S7-1516 CPU (CVE-2022-38465)",
                "s7_identity_override": {
                    "order_code": "6ES7 516-3AN01-0AB0",
                    "module_type": "CPU 1516-3 PN/DP",
                    "firmware_version": "V3.0.0",
                },
                "profinet_identity_override": {
                    "vendor_id": 0x002A,
                    "device_id": 0x0500,
                    "device_type": "CPU 1516-3 PN/DP",
                    "sw_release": "V3.0.0",
                    "order_id": "6ES7 516-3AN01-0AB0",
                },
            },
        ],
    },

    # CVE-2019-13103 - S7-300/400 DoS
    {
        "cve_id": "CVE-2019-13103",
        "title": "Siemens S7-300/400 Denial of Service",
        "description": (
            "SIMATIC S7-300 and S7-400 CPU families contain a vulnerability "
            "that could allow remote attackers to cause a denial of service "
            "condition by sending specially crafted packets to port 102/tcp."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "S7-300",
        "affected_models": [
            "6ES7 315-2EH14-0AB0", "6ES7 317-2EK14-0AB0",
            "6ES7 318-3EL01-0AB0",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "V3.2.17",
        "fixed_firmware_version": "V3.2.18",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-232418.pdf",
        "references": [],
        "mitre_techniques": ["T0815"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 9, 10),
        "vulnerable_variants": [
            {
                "firmware_version": "V3.2.17",
                "display_name": "S7-315-2 PN/DP (CVE-2019-13103)",
                "s7_identity_override": {
                    "order_code": "6ES7 315-2EH14-0AB0",
                    "module_type": "CPU 315-2 PN/DP",
                    "firmware_version": "V3.2.17",
                },
                "profinet_identity_override": {
                    "vendor_id": 0x002A,
                    "device_id": 0x0103,
                    "device_type": "CPU 315-2 PN/DP",
                    "sw_release": "V3.2.17",
                    "order_id": "6ES7 315-2EH14-0AB0",
                },
            },
        ],
    },
]
