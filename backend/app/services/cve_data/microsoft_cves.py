# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Microsoft Windows CVE data.

CVE information for Windows Server systems commonly used as jump servers
in OT/IT boundary environments. These vulnerabilities are detectable via
SNMP sysDescr responses containing Windows version strings.

Detection Methods:
    1. SNMP: Cyber Vision parses Windows version from sysDescr
    2. WMI/SMB: Version strings from authenticated discovery

Jump Server Context:
    Windows jump servers are common in OT environments for remote access:
    - TeamViewer/AnyDesk for remote support
    - RDP for internal access
    - Engineering workstations for PLC programming

Common vulnerable scenarios:
    - Unpatched Windows Server 2016 (BlueKeep)
    - Print Spooler enabled (PrintNightmare)
    - SMBv1 enabled (EternalBlue)
"""

from datetime import datetime

MICROSOFT_CVES: list[dict] = [
    # CVE-2019-0708 - BlueKeep (RDP)
    {
        "cve_id": "CVE-2019-0708",
        "title": "Windows Remote Desktop Services RCE (BlueKeep)",
        "description": (
            "Remote code execution vulnerability in Remote Desktop Services (RDS). "
            "An unauthenticated attacker can send specially crafted requests to the "
            "target system's RDP service to execute arbitrary code. This vulnerability "
            "is wormable and does not require authentication."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Microsoft",
        "product_family": "Windows Server",
        "affected_models": [
            "Windows Server 2008 R2",
            "Windows Server 2012",
            "Windows Server 2012 R2",
            "Windows Server 2016",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "10.0.14393",  # Windows Server 2016 build
        "fixed_firmware_version": "10.0.17763",  # Windows Server 2019
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2019-0708",
        "references": [
            "https://www.cisa.gov/news-events/alerts/2019/06/17/microsoft-operating-systems-bluekeep-vulnerability",
            "https://nvd.nist.gov/vuln/detail/CVE-2019-0708",
        ],
        "mitre_techniques": ["T0886", "T0866"],  # Remote Services, Exploitation of Remote Services
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 5, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "10.0.14393",
                "display_name": "Windows Server 2016 (BlueKeep Vulnerable)",
                "snmp_sys_descr_template": (
                    "Hardware: Intel64 Family 6 Model 85 - "
                    "Software: Windows Server 2016 Datacenter {firmware_version}"
                ),
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",  # Microsoft Windows
                    "sys_name": "JUMP-SVR-01",
                    "sys_contact": "admin@example.com",
                    "sys_location": "Server Room - OT Access",
                    "sys_services": 76,
                },
            },
            {
                "firmware_version": "6.3.9600",
                "display_name": "Windows Server 2012 R2 (BlueKeep Vulnerable)",
                "snmp_sys_descr_template": (
                    "Hardware: Intel64 Family 6 Model 85 - "
                    "Software: Windows Server 2012 R2 Standard {firmware_version}"
                ),
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                    "sys_name": "JUMP-SVR-02",
                    "sys_contact": "admin@example.com",
                    "sys_location": "Server Room - OT Access",
                    "sys_services": 76,
                },
            },
        ],
    },
    # CVE-2021-34527 - PrintNightmare
    {
        "cve_id": "CVE-2021-34527",
        "title": "Windows Print Spooler RCE (PrintNightmare)",
        "description": (
            "Remote code execution vulnerability exists in Windows Print Spooler. "
            "An authenticated attacker can install programs, view/change/delete data, "
            "or create new accounts with full user rights. The Print Spooler service "
            "improperly performs privileged file operations."
        ),
        "severity": "critical",
        "cvss_score": 8.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Microsoft",
        "product_family": "Windows Server",
        "affected_models": [
            "Windows Server 2012 R2",
            "Windows Server 2016",
            "Windows Server 2019",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "10.0.17763.1",  # Pre-patch builds
        "fixed_firmware_version": "10.0.17763.2029",  # KB5004945
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2021-34527",
        "references": [
            "https://www.cisa.gov/news-events/alerts/2021/06/30/printnightmare-critical-windows-print-spooler-vulnerability",
            "https://nvd.nist.gov/vuln/detail/CVE-2021-34527",
        ],
        "mitre_techniques": ["T0863", "T0890"],  # User Execution, Exploitation for Privilege Escalation
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 7, 1),
        "vulnerable_variants": [
            {
                "firmware_version": "10.0.17763.1",
                "display_name": "Windows Server 2019 (PrintNightmare Vulnerable)",
                "snmp_sys_descr_template": (
                    "Hardware: Intel64 Family 6 Model 85 - "
                    "Software: Windows Server 2019 Datacenter {firmware_version}"
                ),
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                    "sys_name": "JUMP-SVR-01",
                    "sys_contact": "admin@example.com",
                    "sys_location": "Server Room - OT Access",
                    "sys_services": 76,
                },
            },
        ],
    },
    # CVE-2017-0144 - EternalBlue (SMB)
    {
        "cve_id": "CVE-2017-0144",
        "title": "Windows SMB RCE (EternalBlue)",
        "description": (
            "Remote code execution vulnerability exists in SMBv1 server. "
            "An attacker can send specially crafted messages to an SMBv1 server "
            "to execute arbitrary code. This vulnerability was exploited by "
            "WannaCry and NotPetya ransomware attacks."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Microsoft",
        "product_family": "Windows Server",
        "affected_models": [
            "Windows Server 2008",
            "Windows Server 2008 R2",
            "Windows Server 2012",
            "Windows Server 2016",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "6.1.7601",  # Windows Server 2008 R2 SP1
        "fixed_firmware_version": "6.1.7601.24000",  # MS17-010
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2017-0144",
        "references": [
            "https://www.cisa.gov/news-events/alerts/2017/05/12/multiple-ransomware-infections-reported",
            "https://nvd.nist.gov/vuln/detail/CVE-2017-0144",
        ],
        "mitre_techniques": ["T0866", "T0886"],  # Exploitation of Remote Services, Remote Services
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2017, 3, 14),
        "vulnerable_variants": [
            {
                "firmware_version": "6.1.7601",
                "display_name": "Windows Server 2008 R2 (EternalBlue Vulnerable)",
                "snmp_sys_descr_template": (
                    "Hardware: Intel64 Family 6 Model 85 - "
                    "Software: Windows Server 2008 R2 Standard {firmware_version} SP1"
                ),
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                    "sys_name": "LEGACY-SVR-01",
                    "sys_contact": "admin@example.com",
                    "sys_location": "Server Room - OT Access",
                    "sys_services": 76,
                },
            },
        ],
    },
    # CVE-2020-1472 - Zerologon (Netlogon)
    {
        "cve_id": "CVE-2020-1472",
        "title": "Windows Netlogon Elevation of Privilege (Zerologon)",
        "description": (
            "An elevation of privilege vulnerability exists when an attacker "
            "establishes a vulnerable Netlogon secure channel connection to a "
            "domain controller. An attacker who successfully exploited this "
            "vulnerability could run a specially crafted application on a device "
            "on the network."
        ),
        "severity": "critical",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "vendor": "Microsoft",
        "product_family": "Windows Server",
        "affected_models": [
            "Windows Server 2008 R2",
            "Windows Server 2012",
            "Windows Server 2012 R2",
            "Windows Server 2016",
            "Windows Server 2019",
        ],
        "affected_firmware_min": None,
        "affected_firmware_max": "10.0.17763.1397",
        "fixed_firmware_version": "10.0.17763.1432",  # KB4565349
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",
        "advisory_url": "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2020-1472",
        "references": [
            "https://www.cisa.gov/news-events/alerts/2020/09/14/exploit-netlogon-remote-protocol-vulnerability-cve-2020-1472",
            "https://nvd.nist.gov/vuln/detail/CVE-2020-1472",
        ],
        "mitre_techniques": ["T0890"],  # Exploitation for Privilege Escalation
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 8, 17),
        "vulnerable_variants": [
            {
                "firmware_version": "10.0.17763.1",
                "display_name": "Windows Server 2019 (Zerologon Vulnerable)",
                "snmp_sys_descr_template": (
                    "Hardware: Intel64 Family 6 Model 85 - "
                    "Software: Windows Server 2019 Datacenter {firmware_version}"
                ),
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                    "sys_name": "DC-SVR-01",
                    "sys_contact": "admin@example.com",
                    "sys_location": "Server Room - OT Access",
                    "sys_services": 76,
                },
            },
        ],
    },
]
