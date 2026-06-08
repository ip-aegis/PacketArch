# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Oil & Gas industry CVE data.

CVE information for process industry vendors commonly found in Oil & Gas:
- Honeywell (Experion, Enraf, Leak Detection)
- Yokogawa (CENTUM VP, ProSafe-RS, GC analyzers)
- Emerson (DeltaV, Fisher valves, Rosemount)
- Endress+Hauser (flow meters, level transmitters)

These vulnerabilities are detectable via firmware version strings in protocol responses.
"""

from datetime import datetime

OIL_GAS_CVES: list[dict] = [
    # =========================================================================
    # Honeywell CVEs
    # =========================================================================
    # CVE-2020-10628 - Honeywell Experion PKS
    {
        "cve_id": "CVE-2020-10628",
        "title": "Honeywell Experion PKS C200/C300 Authentication Bypass",
        "description": (
            "Honeywell Experion PKS C200 and C300 controllers contain an authentication "
            "bypass vulnerability. An attacker can exploit this to gain unauthorized access "
            "to the controller and modify process control logic."
        ),
        "severity": "critical",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Experion PKS",
        "affected_models": ["C200", "C300", "C300E"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R510.1",
        "fixed_firmware_version": "R510.2",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-098-01",
        "references": [],
        "mitre_techniques": ["T0859", "T0843"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 4, 7),
        "vulnerable_variants": [
            {
                "firmware_version": "R510.1",
                "display_name": "Experion PKS C300 (CVE-2020-10628)",
                "snmp_sys_descr_template": "Honeywell Experion PKS C300 Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell International Inc.",
                    "product_code": "C300",
                    "major_minor_revision": "R510.1",
                    "product_name": "Experion PKS C300 Controller",
                },
            },
        ],
    },

    # CVE-2021-38397 - Honeywell Experion PKS/LX
    {
        "cve_id": "CVE-2021-38397",
        "title": "Honeywell Experion PKS C200/C200E Unrestricted File Upload",
        "description": (
            "Honeywell Experion PKS controllers (C200, C200E, C300 and ACE) "
            "contain an unrestricted file upload vulnerability that allows "
            "remote code execution. Per CISA ICSA-21-278-04, ALL VERSIONS of "
            "the affected controllers are vulnerable. An attacker can upload "
            "malicious files to execute arbitrary code on the system."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Experion PKS",
        # CISA ICSA-21-278-04: C200/C200E/C300/ACE all versions affected.
        "affected_models": [
            "C200", "C200E", "Experion PKS C200 Controller",
            "Experion PKS", "Experion LX",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-278-04",
        "references": [],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 10, 5),
        "vulnerable_variants": [
            {
                "firmware_version": "R520.2",
                "display_name": "Experion PKS C200 (CVE-2021-38397)",
                "snmp_sys_descr_template": "Honeywell Experion Process Knowledge System v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell International Inc.",
                    "product_code": "Experion-PKS",
                    "major_minor_revision": "R520.2",
                    "product_name": "Experion Process Knowledge System",
                },
            },
            {
                "firmware_version": "R501.1",
                "display_name": "Experion PKS C200 (CVE-2021-38397)",
                "snmp_sys_descr_template": "Honeywell Experion Process Knowledge System v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell International Inc.",
                    "product_code": "Experion-PKS",
                    "major_minor_revision": "R501.1",
                    "product_name": "Experion Process Knowledge System",
                },
            },
        ],
    },

    # CVE-2022-30315 - Honeywell Safety Manager
    {
        "cve_id": "CVE-2022-30315",
        "title": "Honeywell Safety Manager Authentication Bypass",
        "description": (
            "Honeywell Safety Manager contains an authentication bypass vulnerability "
            "in its web interface. An attacker can bypass authentication to access "
            "safety-critical configuration without credentials."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Safety Manager",
        "affected_models": ["FSC", "SC"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R160.1",
        "fixed_firmware_version": "R160.2",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-179-02",
        "references": [],
        "mitre_techniques": ["T0859", "T0800"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 6, 28),
        "vulnerable_variants": [
            {
                "firmware_version": "R160.1",
                "display_name": "Safety Manager FSC (CVE-2022-30315)",
                "snmp_sys_descr_template": "Honeywell Safety Manager FSC Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell International Inc.",
                    "product_code": "SM-FSC",
                    "major_minor_revision": "R160.1",
                    "product_name": "Safety Manager FSC Controller",
                },
            },
        ],
    },

    # =========================================================================
    # Yokogawa CVEs
    # =========================================================================
    # CVE-2022-21177 - Yokogawa CENTUM VP
    {
        "cve_id": "CVE-2022-21177",
        "title": "Yokogawa CENTUM VP/CS Authentication Bypass",
        "description": (
            "Yokogawa CENTUM VP and CS 3000 DCS systems contain an authentication "
            "bypass vulnerability. An attacker can exploit this to gain unauthorized "
            "access to the engineering workstation and modify control logic."
        ),
        "severity": "critical",
        "cvss_score": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H",
        "vendor": "Yokogawa",
        "product_family": "CENTUM",
        "affected_models": ["CENTUM VP", "CENTUM CS 3000", "HIS", "EWS"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R6.08.00",
        "fixed_firmware_version": "R6.09.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-083-01",
        "references": [],
        "mitre_techniques": ["T0859", "T0821"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 1, 6),
        "vulnerable_variants": [
            {
                "firmware_version": "R6.08.00",
                "display_name": "CENTUM VP (CVE-2022-21177)",
                "snmp_sys_descr_template": "Yokogawa CENTUM VP Distributed Control System v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Yokogawa Electric Corporation",
                    "product_code": "CENTUM-VP",
                    "major_minor_revision": "R6.08.00",
                    "product_name": "CENTUM VP Distributed Control System",
                },
            },
        ],
    },

    # CVE-2019-6008 - Yokogawa Exaopc / Windows software packages (NOT CENTUM VP controller)
    {
        "cve_id": "CVE-2019-6008",
        "title": "Yokogawa Exaopc Uncontrolled Search Path Element",
        "description": (
            "An uncontrolled search path element vulnerability affects multiple "
            "Yokogawa Windows software packages (Exaopc, Exaplog, Exaquantum, "
            "Exaquantum/Batch, Exasmoc, Exarqe, GA10, InsightSuiteAE). A local "
            "attacker can place a malicious DLL/executable on the search path to "
            "execute arbitrary code. The CENTUM VP controller line is NOT affected."
        ),
        "severity": "high",
        "cvss_score": 7.8,
        "cvss_vector": "CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H",
        "vendor": "Yokogawa",
        "product_family": "Exaopc",
        # NVD CPE enumerates the Windows software packages only (Exaopc
        # R1.01.00-R3.77.00, Exaplog, Exaquantum, Exaquantum/Batch, Exasmoc,
        # Exarqe, GA10, InsightSuiteAE). The CENTUM VP / HIS / EWS controller
        # line is explicitly NOT affected, and the only modeled Exaopc build
        # (R3.80) is post-fix (fixed in R3.78.00), so no in-range template
        # exists. Listed by full NVD product identifiers (none modeled).
        "affected_models": [
            "Yokogawa Exaopc", "Yokogawa Exaplog", "Yokogawa Exaquantum",
            "Yokogawa Exaquantum/Batch", "Yokogawa Exasmoc", "Yokogawa Exarqe",
            "Yokogawa GA10", "Yokogawa InsightSuiteAE",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "R3.77.00",
        "fixed_firmware_version": "R3.78.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-274-02",
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2019-6008"],
        "mitre_techniques": ["T0831", "T0883"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2019, 3, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "R3.77.00",
                "display_name": "Exaopc (CVE-2019-6008)",
                "snmp_sys_descr_template": "Yokogawa Exaopc OPC Server v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Yokogawa Electric Corporation",
                    "product_code": "Exaopc",
                    "major_minor_revision": "R3.77.00",
                    "product_name": "Exaopc OPC Server",
                },
            },
        ],
    },

    # CVE-2023-26593 - Yokogawa CENTUM VP (CENTUM Authentication Mode cleartext credential storage)
    {
        "cve_id": "CVE-2023-26593",
        "title": "Yokogawa CENTUM Cleartext Storage of Credentials",
        "description": (
            "Yokogawa CENTUM (CENTUM VP, CENTUM CS 1000/CS 3000, B/M9000, EXAOPC) "
            "stores credentials in cleartext when running in CENTUM Authentication "
            "Mode. A local attacker with access to the system can read stored "
            "credentials and gain unauthorized access to the control system."
        ),
        "severity": "high",
        "cvss_score": 7.8,
        "cvss_vector": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Yokogawa",
        "product_family": "CENTUM",
        "affected_models": ["CENTUM VP", "CENTUM CS 3000", "B/M9000", "EXAOPC"],
        "affected_firmware_min": "R6.01.00",
        "affected_firmware_max": "R6.11.99",
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://jvn.jp/en/vu/JVNVU98775218/",
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2023-26593"],
        "mitre_techniques": ["T0859", "T0800"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 3, 21),
        "vulnerable_variants": [
            {
                "firmware_version": "R6.08.00",
                "display_name": "CENTUM VP (CVE-2023-26593)",
                "snmp_sys_descr_template": "Yokogawa CENTUM VP Distributed Control System v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Yokogawa Electric Corporation",
                    "product_code": "CENTUM-VP",
                    "major_minor_revision": "R6.08.00",
                    "product_name": "CENTUM VP Distributed Control System",
                },
            },
        ],
    },

    # CVE-2022-30262 - Emerson DeltaV
    {
        "cve_id": "CVE-2022-30262",
        "title": "Emerson DeltaV Missing Authentication",
        "description": (
            "Emerson DeltaV DCS contains a missing authentication vulnerability "
            "that allows unauthorized access to controller configuration. An attacker "
            "can modify control logic without proper authentication."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Emerson",
        "product_family": "DeltaV",
        "affected_models": ["M-Series", "S-Series"],
        "affected_firmware_min": None,
        "affected_firmware_max": "v13.3",
        "fixed_firmware_version": "v14.3",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-181-03",
        "references": [],
        "mitre_techniques": ["T0859", "T0821"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 6, 30),
        "vulnerable_variants": [
            {
                "firmware_version": "13.3",
                "display_name": "DeltaV S-Series (CVE-2022-30262)",
                "snmp_sys_descr_template": "Emerson DeltaV S-Series Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Emerson Process Management",
                    "product_code": "S-Series",
                    "major_minor_revision": "V13.3",
                    "product_name": "DeltaV S-Series Controller",
                },
            },
        ],
    },

    # CVE-2023-46687 - Emerson ROC800-Series RTU
    {
        "cve_id": "CVE-2023-46687",
        "title": "Emerson ROC800 Command Injection",
        "description": (
            "Emerson ROC800-series RTUs contain a command injection vulnerability "
            "in the web interface. An authenticated attacker can execute arbitrary "
            "system commands on the device."
        ),
        "severity": "high",
        "cvss_score": 8.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Emerson",
        "product_family": "ROC800",
        "affected_models": ["ROC800", "ROC800L"],
        "affected_firmware_min": None,
        "affected_firmware_max": "3.75",
        "fixed_firmware_version": "3.76",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-318-01",
        "references": [],
        "mitre_techniques": ["T0807", "T0853"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 11, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "3.75",
                "display_name": "ROC800 RTU (CVE-2023-46687)",
                "snmp_sys_descr_template": "Emerson ROC800 Remote Operations Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Emerson Process Management",
                    "product_code": "ROC800",
                    "major_minor_revision": "V3.75",
                    "product_name": "ROC800 Remote Operations Controller",
                },
            },
        ],
    },

    # CVE-2020-12495 - Endress+Hauser Web Server
    {
        "cve_id": "CVE-2020-12495",
        "title": "Endress+Hauser Device Web Server XSS",
        "description": (
            "Multiple Endress+Hauser devices with embedded web servers contain "
            "cross-site scripting vulnerabilities. An attacker can inject malicious "
            "scripts to steal credentials or manipulate device configuration."
        ),
        "severity": "medium",
        "cvss_score": 6.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "vendor": "Endress+Hauser",
        "product_family": "Liquiline",
        "affected_models": ["CM442", "CM444", "CM448"],
        "affected_firmware_min": None,
        "affected_firmware_max": "01.08.00",
        "fixed_firmware_version": "01.09.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-191-01",
        "references": [],
        "mitre_techniques": ["T0866"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 7, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "01.08.00",
                "display_name": "Liquiline CM442 (CVE-2020-12495)",
                "snmp_sys_descr_template": "Endress+Hauser Liquiline CM442 Multiparameter Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Endress+Hauser",
                    "product_code": "CM442-AAM1A1A001",
                    "major_minor_revision": "01.08.00",
                    "product_name": "Liquiline CM442 Multiparameter Controller",
                },
            },
        ],
    },
]
