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
    # CVE-2023-28489 (SICAM A8000 CP-8031/CP-8050) used to sit here framed as
    # "traffic management". NVD lists only the CP-8031/CP-8050 master modules,
    # which are energy RTUs, so it now lives in energy_cves.py.
    # CVE-2020-25230 was removed: NVD lists it for LOGO! 8 BM, not M60.

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
                # No model-specific sys_descr override: CVE-2023-20198 covers many
                # IOS XE switches (IE-3300/IE-4000/IE-9320/…). The device's own
                # firmware-pinned sys_descr carries the correct model + version, so
                # a hardcoded IE3300 string here would wrongly clobber e.g. an
                # IE-9320. Just declare the vulnerable firmware.
                "firmware_version": "17.9.3",
                "display_name": "Cisco IOS XE switch (CVE-2023-20198)",
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

    # CVE-2021-36260 (Hikvision web-server command injection) was removed
    # 2026-10-21: the record pinned it to three ANPR models (DS-2CD7A26G0/P,
    # DS-2CD4A26FWD-IZHS, DS-2CD6365G0-IVS) that Hikvision's advisory
    # HSRC-202109-01 does not list (it names DS-2CD4xx6FWD as non-ANPR only).
    # CVE-2025-1100 - Q-Free MAXTIME hard-coded root password (Nozomi
    # Networks, 2025-02-11; one of ~40 MAXTIME findings published together).
    # NVD CPE: q-free:maxtime versionEndIncluding 2.11.0. No fixed version
    # had been communicated by the vendor at publication.
    {
        "cve_id": "CVE-2025-1100",
        "title": "Q-Free MAXTIME Hard-coded Root Password",
        "description": (
            "A CWE-259 \"Use of Hard-coded Password\" for the root account in "
            "Q-Free MaxTime less than or equal to version 2.11.0 allows an "
            "unauthenticated remote attacker to execute arbitrary code with "
            "root privileges via SSH."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Q-Free",
        "product_family": "MAXTIME",
        "affected_models": ["Intelight 2070LX", "MAXTIME"],
        "affected_firmware_min": None,
        "affected_firmware_max": "2.11.0",
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.nozominetworks.com/labs/vulnerability-advisories-cve-2025-1100",
        "references": [],
        "mitre_techniques": ["T0859", "T0866"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2025, 2, 12),
        "vulnerable_variants": [
            {
                "display_name": "Intelight 2070LX MAXTIME 2.11.0 (CVE-2025-1100)",
                "firmware_version": "2.11.0",
            },
        ],
    },
    # SICK LMS5xx (SICK advisory SCA-2023-0007, 2023-08-24). These three
    # affect all LMS5xx firmware with no fix, so they carry no version bounds.
    # The TIC502 traffic collector is built on two LMS511 SE scanners.
    {
        "cve_id": "CVE-2023-4418",
        "title": "SICK LMS5xx TCP SYN Flood Denial of Service",
        "description": (
            'A remote unprivileged attacker can send multiple packets to the LMS5xx to disrupt its availability through a TCP SYN-based denial-of-service attack.'
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "SICK",
        "product_family": "LMS5xx",
        "affected_models": ['LMS5xx', 'TIC502 Master'],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://sick.com/.well-known/csaf/white/2023/sca-2023-0007.pdf",
        "references": [],
        "mitre_techniques": ['T0814'],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 8, 24),
        "vulnerable_variants": [
            {
                "display_name": "SICK TIC502 (LMS511 SE) TEMS 2.8.0",
                "firmware_version": "2.8.0",
            },
        ],
    },
    {
        "cve_id": "CVE-2023-4420",
        "title": "SICK LMS5xx Missing Transport Encryption",
        "description": (
            'A remote unprivileged attacker can intercept the communication, e.g. by man-in-the-middle, due to the absence of Transport Layer Security (TLS) in the SICK LMS5xx.'
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "SICK",
        "product_family": "LMS5xx",
        "affected_models": ['LMS5xx', 'TIC502 Master'],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://sick.com/.well-known/csaf/white/2023/sca-2023-0007.pdf",
        "references": [],
        "mitre_techniques": ['T0830'],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 8, 24),
        "vulnerable_variants": [
            {
                "display_name": "SICK TIC502 (LMS511 SE) TEMS 2.8.0",
                "firmware_version": "2.8.0",
            },
        ],
    },
    {
        "cve_id": "CVE-2023-31412",
        "title": "SICK LMS5xx Weak Password Hashing",
        "description": (
            'The LMS5xx uses weak hash generation methods, resulting in insecure hashes. An attacker who retrieves a hash could mount collision attacks and potentially recover the password.'
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "SICK",
        "product_family": "LMS5xx",
        "affected_models": ['LMS5xx', 'TIC502 Master'],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://sick.com/.well-known/csaf/white/2023/sca-2023-0007.pdf",
        "references": [],
        "mitre_techniques": ['T0859'],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 8, 24),
        "vulnerable_variants": [
            {
                "display_name": "SICK TIC502 (LMS511 SE) TEMS 2.8.0",
                "firmware_version": "2.8.0",
            },
        ],
    },
    # Kapsch RIS-9160 / RIS-9260 V2X RSUs (CVE records 2025-08-26). Both are
    # physical-access findings; the records list affected builds
    # 3.2.0.829.23, 3.8.0.1119.42 and 4.6.0.1211.28 and no fixed version.
    {
        "cve_id": "CVE-2025-25734",
        "title": "Kapsch RIS-9260 Unauthenticated EFI Shell",
        "description": (
            'Kapsch TrafficCom RIS-9160 and RIS-9260 roadside units v3.2.0.829.23, v3.8.0.1119.42 and v4.6.0.1211.28 contain an unauthenticated EFI shell that allows attackers to execute arbitrary code or escalate privileges during the boot process.'
        ),
        "severity": "medium",
        "cvss_score": 6.8,
        "cvss_vector": "CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Kapsch",
        "product_family": "RIS",
        "affected_models": ['RIS-9260', 'RIS-9160'],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.cve.org/CVERecord?id=CVE-2025-25734",
        "references": [],
        "mitre_techniques": ['T0839'],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2025, 8, 26),
        "vulnerable_variants": [
            {
                "display_name": "Kapsch RIS-9260 4.6.0.1211.28",
                "firmware_version": "4.6.0.1211.28",
            },
            {
                "display_name": "Kapsch RIS-9260 3.8.0.1119.42",
                "firmware_version": "3.8.0.1119.42",
            },
        ],
    },
    {
        "cve_id": "CVE-2025-25736",
        "title": "Kapsch RIS-9260 ADB Enabled by Default",
        "description": (
            'Kapsch TrafficCom RIS-9260 RSU LEO v3.2.0.829.23, v3.8.0.1119.42 and v4.6.0.1211.28 ship with Android Debug Bridge pre-installed and enabled by default, allowing an unauthenticated root shell.'
        ),
        "severity": "medium",
        "cvss_score": 6.8,
        "cvss_vector": "CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Kapsch",
        "product_family": "RIS",
        "affected_models": ['RIS-9260'],
        "affected_firmware_min": None,
        "affected_firmware_max": None,
        "fixed_firmware_version": None,
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.cve.org/CVERecord?id=CVE-2025-25736",
        "references": [],
        "mitre_techniques": ['T0886'],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2025, 8, 26),
        "vulnerable_variants": [
            {
                "display_name": "Kapsch RIS-9260 4.6.0.1211.28",
                "firmware_version": "4.6.0.1211.28",
            },
            {
                "display_name": "Kapsch RIS-9260 3.8.0.1119.42",
                "firmware_version": "3.8.0.1119.42",
            },
        ],
    },
]
