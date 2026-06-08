# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Transportation ITS CVE data.

CVE information for traffic controllers, DMS, toll systems, and roadside
equipment. These vulnerabilities are detectable via SNMP sysDescr strings
which Cisco Cyber Vision parses for device identification and firmware
version extraction.

Detection Method:
    Cyber Vision monitors SNMP GetResponse packets for sysDescr OID
    (1.3.6.1.2.1.1.1.0). The sysDescr string typically contains:
    - Vendor name
    - Model/product name
    - Firmware/software version
    Cyber Vision extracts this information and matches against its
    vulnerability database.
"""

from datetime import datetime

TRANSPORTATION_CVES: list[dict] = [
    # ==========================================================================
    # SIEMENS TRAFFIC MANAGEMENT
    # ==========================================================================

    # CVE-2023-28489 - Siemens CP-8000 Master Station
    {
        "cve_id": "CVE-2023-28489",
        "title": "Siemens SICAM CP-8000 Traffic Management Vulnerability",
        "description": (
            "A vulnerability in Siemens SICAM CP-8000/CP-8021/CP-8022 master "
            "stations allows remote attackers to execute arbitrary code via "
            "crafted network packets. Affects traffic management center systems."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Siemens",
        "product_family": "Traffic Management",
        "affected_models": ["CP-8000", "CP-8021", "CP-8022"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V5.20",
        "fixed_firmware_version": "V5.30",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-333517.pdf",
        "references": [
            "https://www.cisa.gov/news-events/ics-advisories/icsa-23-103-09",
        ],
        "mitre_techniques": ["T0866", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 4, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V5.20",
                "display_name": "Siemens CP-8000 Master Station (CVE-2023-28489)",
                "snmp_identity_override": {
                    "sys_descr": "Siemens SICAM CP-8000 Master Station V5.20",
                    "sys_object_id": "1.3.6.1.4.1.4329.6.1.2",
                    "sys_name": "CP8000-TMC-001",
                    "sys_location": "Traffic Management Center",
                    "sys_contact": "its-admin@example.gov",
                },
            },
            {
                "firmware_version": "V5.11",
                "display_name": "Siemens CP-8021 RTU (CVE-2023-28489)",
                "snmp_identity_override": {
                    "sys_descr": "Siemens SICAM CP-8021 RTU V5.11",
                    "sys_object_id": "1.3.6.1.4.1.4329.6.1.3",
                    "sys_name": "CP8021-FIELD-001",
                    "sys_location": "Intersection #47",
                },
            },
        ],
    },

    # CVE-2023-20198 - Cisco IOS XE Web UI Privilege Escalation
    {
        "cve_id": "CVE-2023-20198",
        "title": "Cisco IOS XE Web UI Privilege Escalation Vulnerability",
        "description": (
            "Cisco IOS XE switches used in traffic infrastructure contain "
            "a vulnerability in the web UI that could allow an unauthenticated "
            "remote attacker to create a privileged account on the device."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Cisco",
        "product_family": "Traffic Network",
        "affected_models": ["IE-3300-8T2S", "IE-4000-8GT4G-E", "IE-9320-24T4X-E"],
        "affected_firmware_min": None,
        "affected_firmware_max": "17.9.04",
        "fixed_firmware_version": "17.9.04a",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-iosxe-webui-privesc-j22SaA4z",
        "references": [],
        "mitre_techniques": ["T0815"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 10, 16),
        "vulnerable_variants": [
            {
                "firmware_version": "17.9.04",
                "display_name": "Cisco IE-3300 Switch (CVE-2023-20198)",
                "snmp_identity_override": {
                    "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3300 Software (IE3300-UNIVERSALK9-M), Version 17.9.04",
                    "sys_object_id": "1.3.6.1.4.1.9.1.2824",
                    "sys_name": "ITS-SW-001",
                    "sys_location": "Cabinet #12",
                },
            },
        ],
    },

    # ==========================================================================
    # SCHNEIDER ELECTRIC TRAFFIC SYSTEMS
    # ==========================================================================

    # CVE-2020-7480 - Schneider Electric Andover Continuum Code Injection (CWE-94)
    {
        "cve_id": "CVE-2020-7480",
        "title": "Schneider Electric Andover Continuum Code Injection",
        "description": (
            "An Improper Control of Generation of Code (CWE-94) vulnerability "
            "exists in Schneider Electric Andover Continuum building/access "
            "controllers (all versions). A remote unauthenticated attacker can "
            "inject and execute arbitrary code, leading to full compromise of "
            "the controller."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Andover Continuum",
        # NVD CPE: Andover Continuum models 5720/5740/9200/9680/9702/9900/
        # 9924/9940/9941/BCX4040/BCX9640 at all versions (CWE-94).
        "affected_models": [
            "CX9680", "9680", "9200", "9702", "9900", "9924", "9940", "9941",
            "5720", "5740", "BCX4040", "BCX9640",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2020-7480",
        "references": [
            "https://www.se.com/ww/en/download/document/SEVD-2020-042-02/",
        ],
        "mitre_techniques": ["T0812", "T0859"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 2, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.6.0",
                "display_name": "Andover Continuum CX9680 (CVE-2020-7480)",
                "snmp_identity_override": {
                    "sys_descr": "Schneider Electric Andover Continuum CX9680 V2.6.0",
                    "sys_object_id": "1.3.6.1.4.1.539.1.1.9680",
                    "sys_name": "CONTINUUM-CX9680",
                },
            },
        ],
    },

    # ==========================================================================
    # AXIS - ITS CAMERAS
    # ==========================================================================

    # CVE-2021-31986 - AXIS OS SMTP-notification heap buffer overflow.
    # Re-framed per verified_corrections.json (Axis): this is NOT an RTSP RCE.
    # It is an AXIS-OS-wide heap buffer overflow (CWE-122) in the parsing of
    # SMTP-notification parameters, causing a crash and possible data leakage.
    # NVD scores it 6.8 MEDIUM (AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:N/A:H). Keyed to
    # AXIS OS version (not model); fixed on the active track at 10.7 and on the
    # LTS branches at 6.50.5.5 / 8.40.4.3 / 9.80.3.5. The template ships real
    # pre-fix builds (P1455-LE 10.6.0 active, P1448-LE 9.80.3.1 LTS-2020), both
    # numerically below the 10.6 active-track ceiling and thus in-range.
    {
        "cve_id": "CVE-2021-31986",
        "title": "AXIS OS SMTP-Notification Heap Buffer Overflow",
        "description": (
            "AXIS OS on a wide range of Axis network cameras (e.g. P1455-LE, "
            "P1448-LE, M3106-L) contains a heap-based buffer overflow (CWE-122) "
            "in the handling of SMTP-notification parameters. A successful "
            "exploit can crash the affected service and may lead to data "
            "leakage. Fixed on the active track in AXIS OS 10.7 and on the LTS "
            "branches in 6.50.5.5, 8.40.4.3, and 9.80.3.5."
        ),
        "severity": "medium",
        "cvss_score": 6.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:N/A:H",
        "vendor": "Axis",
        "product_family": "AXIS OS Camera",
        "affected_models": ["P1455-LE", "P1448-LE", "M3106-L"],
        "affected_firmware_min": None,
        "affected_firmware_max": "10.6",
        "fixed_firmware_version": "10.7",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.axis.com/dam/public/22/48/13/cve-2021-31986-en-US-337398.pdf",
        "references": [],
        "mitre_techniques": ["T0866", "T0882"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2021, 8, 3),
        "vulnerable_variants": [
            {
                "firmware_version": "10.6",
                "display_name": "Axis P1455-LE Camera (CVE-2021-31986)",
                "snmp_identity_override": {
                    "sys_descr": "AXIS P1455-LE Network Camera; 10.6; Linux 4.14 armv7l",
                    "sys_object_id": "1.3.6.1.4.1.368.1.1.1",
                    "sys_name": "CAM-INT-001",
                    "sys_location": "Intersection Main & Oak",
                },
            },
        ],
    },

    # ==========================================================================
    # GENERIC NTCIP/TRECK STACK VULNERABILITIES
    # ==========================================================================

    # CVE-2020-11896 - Treck TCP/IP Stack (Ripple20)
    {
        "cve_id": "CVE-2020-11896",
        "title": "Treck TCP/IP Stack Remote Code Execution (Ripple20)",
        "description": (
            "Multiple ITS devices using Treck TCP/IP stack are vulnerable "
            "to remote code execution via malformed IPv4 tunneling packets. "
            "Affects many embedded traffic control and sensor devices."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Multiple",
        "product_family": "Embedded ITS",
        "affected_models": [
            "Various traffic controllers",
            "Various sensor equipment",
            "Various DMS controllers",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "6.0.1.66",
        "fixed_firmware_version": "6.0.1.67",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-20-168-01",
        "references": [
            "https://www.jsof-tech.com/ripple20/",
        ],
        "mitre_techniques": ["T0866", "T0882", "T0888"],
        "exploit_available": True,
        "exploit_complexity": "high",
        "published_date": datetime(2020, 6, 16),
        "vulnerable_variants": [
            {
                "firmware_version": "Treck 6.0.1.66",
                "display_name": "NTCIP Device with Treck Stack (CVE-2020-11896)",
                "snmp_identity_override": {
                    "sys_descr": "NTCIP Traffic Controller FW 3.2 (Treck 6.0.1.66)",
                    "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
                    "sys_name": "TC-GENERIC-001",
                    "sys_location": "Field Cabinet",
                },
            },
        ],
    },

    # ==========================================================================
    # HIKVISION - ANPR CAMERAS
    # ==========================================================================

    # CVE-2021-36260 - Hikvision IP Camera Command Injection
    {
        "cve_id": "CVE-2021-36260",
        "title": "Hikvision IP Camera Command Injection Vulnerability",
        "description": (
            "Hikvision IP cameras including ANPR models contain a command "
            "injection vulnerability in the web server that allows remote "
            "attackers to execute arbitrary commands via crafted requests."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Hikvision",
        "product_family": "ANPR Camera",
        "affected_models": ["DS-2CD7A26G0/P", "DS-2CD4A26FWD-IZHS", "DS-2CD6365G0-IVS"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V5.7.2",
        "fixed_firmware_version": "V5.7.4",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-265-02",
        "references": [
            "https://nvd.nist.gov/vuln/detail/CVE-2021-36260",
        ],
        "mitre_techniques": ["T0866", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 9, 22),
        "vulnerable_variants": [
            {
                "firmware_version": "V5.7.2",
                "display_name": "Hikvision DS-2CD7A26G0/P ANPR (CVE-2021-36260)",
                "snmp_identity_override": {
                    "sys_descr": "Hikvision DS-2CD7A26G0/P ANPR Camera V5.7.2",
                    "sys_object_id": "1.3.6.1.4.1.39165.1.1.1",
                    "sys_name": "ANPR-TOLL-001",
                    "sys_location": "Toll Plaza Lane 1",
                },
            },
            {
                "firmware_version": "V5.6.8",
                "display_name": "Hikvision DS-2CD4A26FWD ANPR (CVE-2021-36260)",
                "snmp_identity_override": {
                    "sys_descr": "Hikvision DS-2CD4A26FWD-IZHS ANPR Camera V5.6.8",
                    "sys_object_id": "1.3.6.1.4.1.39165.1.1.2",
                    "sys_name": "ANPR-TOLL-002",
                    "sys_location": "Toll Plaza Lane 2",
                },
            },
        ],
    },

    # ==========================================================================
    # SIEMENS - TRAFFIC SIGNAL CONTROLLERS
    # ==========================================================================

    # CVE-2020-25230 - Siemens Traffic Controller
    {
        "cve_id": "CVE-2020-25230",
        "title": "Siemens Mobility Traffic Controller Vulnerability",
        "description": (
            "Siemens Mobility traffic signal controllers including M60 and "
            "M50 series contain a vulnerability in the web interface that "
            "allows unauthenticated access to sensitive configuration data."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Siemens",
        "product_family": "Traffic Controller",
        "affected_models": ["M60", "M50", "M40"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V3.2.0",
        "fixed_firmware_version": "V3.3.0",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-423808.pdf",
        "references": [],
        "mitre_techniques": ["T0859", "T0888"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 11, 10),
        "vulnerable_variants": [
            {
                "firmware_version": "V3.2.0",
                "display_name": "Siemens M60 Traffic Controller (CVE-2020-25230)",
                "snmp_identity_override": {
                    "sys_descr": "Siemens Mobility M60 Traffic Controller V3.2.0",
                    "sys_object_id": "1.3.6.1.4.1.4329.6.1.4",
                    "sys_name": "M60-MASTER-001",
                    "sys_location": "Traffic Operations Center",
                },
            },
            {
                "firmware_version": "V3.1.5",
                "display_name": "Siemens M50 Traffic Controller (CVE-2020-25230)",
                "snmp_identity_override": {
                    "sys_descr": "Siemens Mobility M50 Traffic Controller V3.1.5",
                    "sys_object_id": "1.3.6.1.4.1.4329.6.1.5",
                    "sys_name": "M50-INT-001",
                    "sys_location": "Intersection Cabinet",
                },
            },
        ],
    },
]
