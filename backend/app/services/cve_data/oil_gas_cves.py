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
        "cvss_score": 9.8,
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
        "title": "Honeywell Experion PKS Unrestricted File Upload",
        "description": (
            "Honeywell Experion PKS and Experion LX contain an unrestricted file upload "
            "vulnerability that allows remote code execution. An attacker can upload "
            "malicious files to execute arbitrary code on the system."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Experion PKS",
        "affected_models": ["Experion PKS", "Experion LX"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R520.1",
        "fixed_firmware_version": "R520.2",
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
                "firmware_version": "R520.1",
                "display_name": "Experion PKS (CVE-2021-38397)",
                "snmp_sys_descr_template": "Honeywell Experion Process Knowledge System v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Honeywell International Inc.",
                    "product_code": "Experion-PKS",
                    "major_minor_revision": "R520.1",
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
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Yokogawa",
        "product_family": "CENTUM",
        "affected_models": ["CENTUM VP", "CENTUM CS 3000"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R6.08.00",
        "fixed_firmware_version": "R6.09.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-006-03",
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

    # CVE-2019-6008 - Yokogawa CENTUM VP
    {
        "cve_id": "CVE-2019-6008",
        "title": "Yokogawa CENTUM VP Buffer Overflow",
        "description": (
            "Yokogawa CENTUM VP contains a buffer overflow vulnerability in its "
            "network communication module. A remote attacker can send specially "
            "crafted packets to cause denial of service or execute arbitrary code."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H",
        "vendor": "Yokogawa",
        "product_family": "CENTUM",
        "affected_models": ["CENTUM VP", "CENTUM VP Small"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R5.04.20",
        "fixed_firmware_version": "R5.04.B1",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-073-02",
        "references": [],
        "mitre_techniques": ["T0831", "T0883"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2019, 3, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "R5.04.20",
                "display_name": "CENTUM VP (CVE-2019-6008)",
                "snmp_sys_descr_template": "Yokogawa CENTUM VP Field Control Station v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Yokogawa Electric Corporation",
                    "product_code": "CENTUM-VP",
                    "major_minor_revision": "R5.04.20",
                    "product_name": "CENTUM VP Field Control Station",
                },
            },
        ],
    },

    # CVE-2023-26593 - Yokogawa ProSafe-RS
    {
        "cve_id": "CVE-2023-26593",
        "title": "Yokogawa ProSafe-RS Authentication Bypass",
        "description": (
            "Yokogawa ProSafe-RS Safety Instrumented System contains an authentication "
            "bypass vulnerability. An attacker can exploit this to access safety system "
            "configuration and potentially modify safety logic."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Yokogawa",
        "product_family": "ProSafe-RS",
        "affected_models": ["ProSafe-RS R4", "ProSafe-RS R3"],
        "affected_firmware_min": None,
        "affected_firmware_max": "R4.05.00",
        "fixed_firmware_version": "R4.06.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-080-03",
        "references": [],
        "mitre_techniques": ["T0859", "T0800"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 3, 21),
        "vulnerable_variants": [
            {
                "firmware_version": "R4.05.00",
                "display_name": "ProSafe-RS R4 (CVE-2023-26593)",
                "snmp_sys_descr_template": "Yokogawa ProSafe-RS Safety Instrumented System v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Yokogawa Electric Corporation",
                    "product_code": "ProSafe-RS",
                    "major_minor_revision": "R4.05.00",
                    "product_name": "ProSafe-RS Safety Instrumented System",
                },
            },
        ],
    },

    # =========================================================================
    # Emerson CVEs
    # =========================================================================
    # CVE-2022-29966 - Emerson DeltaV
    {
        "cve_id": "CVE-2022-29966",
        "title": "Emerson DeltaV Distributed Control System RCE",
        "description": (
            "Emerson DeltaV DCS contains a remote code execution vulnerability in "
            "the DeltaV Controller. An attacker can send specially crafted network "
            "packets to execute arbitrary code on the controller."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Emerson",
        "product_family": "DeltaV",
        "affected_models": ["M-Series", "S-Series", "MD Plus"],
        "affected_firmware_min": None,
        "affected_firmware_max": "v14.3",
        "fixed_firmware_version": "v14.5",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-22-179-04",
        "references": [],
        "mitre_techniques": ["T0843", "T0883"],
        "exploit_available": True,
        "exploit_complexity": "medium",
        "published_date": datetime(2022, 6, 28),
        "vulnerable_variants": [
            {
                "firmware_version": "14.3",
                "display_name": "DeltaV MD Plus (CVE-2022-29966)",
                "snmp_sys_descr_template": "Emerson DeltaV MD Plus Controller v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Emerson Process Management",
                    "product_code": "MD Plus",
                    "major_minor_revision": "V14.3",
                    "product_name": "DeltaV MD Plus Controller",
                },
                "ethernet_ip_identity_override": {
                    "vendor_id": 90,
                    "device_type": 14,
                    "product_code": 143,
                    "revision_major": 14,
                    "revision_minor": 3,
                    "product_name": "DeltaV MD Plus Controller",
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

    # =========================================================================
    # Endress+Hauser CVEs
    # =========================================================================
    # CVE-2021-41091 - Endress+Hauser FieldCare
    {
        "cve_id": "CVE-2021-41091",
        "title": "Endress+Hauser FieldCare Path Traversal",
        "description": (
            "Endress+Hauser FieldCare asset management software contains a path "
            "traversal vulnerability that allows reading arbitrary files. An attacker "
            "can access sensitive configuration and credential data."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Endress+Hauser",
        "product_family": "FieldCare",
        "affected_models": ["SFE500", "SFE600"],
        "affected_firmware_min": None,
        "affected_firmware_max": "2.13.0",
        "fixed_firmware_version": "2.14.0",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-315-06",
        "references": [],
        "mitre_techniques": ["T0808", "T0888"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 11, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "2.13.0",
                "display_name": "FieldCare SFE500 (CVE-2021-41091)",
                "snmp_sys_descr_template": "Endress+Hauser FieldCare SFE500 Asset Management v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Endress+Hauser",
                    "product_code": "SFE500",
                    "major_minor_revision": "2.13.0",
                    "product_name": "FieldCare SFE500 Asset Management",
                },
            },
        ],
    },

    # CVE-2023-1617 - Endress+Hauser Proline Flowmeters
    {
        "cve_id": "CVE-2023-1617",
        "title": "Endress+Hauser Proline Flowmeter HART Stack Overflow",
        "description": (
            "Endress+Hauser Proline flowmeters contain a stack overflow vulnerability "
            "in the HART protocol implementation. An attacker can send malformed HART "
            "commands to crash the device or potentially execute code."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Endress+Hauser",
        "product_family": "Proline",
        "affected_models": ["Promag 400", "Promag W 400", "Promass 100"],
        "affected_firmware_min": None,
        "affected_firmware_max": "01.06.00",
        "fixed_firmware_version": "01.07.00",
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-096-01",
        "references": [],
        "mitre_techniques": ["T0831"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 4, 6),
        "vulnerable_variants": [
            {
                "firmware_version": "01.06.00",
                "display_name": "Promag 400 (CVE-2023-1617)",
                "snmp_sys_descr_template": "Endress+Hauser Promag 400 Electromagnetic Flowmeter v{firmware_version}",
                "modbus_identity_override": {
                    "vendor_name": "Endress+Hauser",
                    "product_code": "50W40-UA0A1AA0AAAA",
                    "major_minor_revision": "01.06.00",
                    "product_name": "Promag 400 Electromagnetic Flowmeter",
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
