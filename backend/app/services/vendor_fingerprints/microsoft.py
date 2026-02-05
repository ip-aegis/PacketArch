"""Microsoft Windows device fingerprints for IT/OT jump servers.

Fingerprint data for Windows-based remote access servers commonly found at
IT/OT boundaries in industrial environments. These servers provide:
- Remote desktop access (RDP) for maintenance
- TeamViewer/AnyDesk for vendor support
- Engineering workstation access to PLCs

Windows jump servers are high-value targets for attackers as they provide
lateral movement paths from IT networks into OT environments.

Detection context:
    Cisco Cyber Vision can detect Windows systems via:
    - SNMP sysDescr containing Windows version strings
    - SMB/CIFS version negotiation
    - WMI queries (authenticated)

Included fingerprints:
- Windows Server 2019 (patched) - Standard jump server
- Windows Server 2016 (BlueKeep vulnerable) - CVE-2019-0708
- Windows Server 2008 R2 (EternalBlue vulnerable) - CVE-2017-0144
"""

from typing import Any

# MAC OUI Prefixes for Microsoft (Hyper-V, Azure, etc.)
# NOTE: Jump servers may use various NIC vendors; these are Microsoft-specific
MICROSOFT_OUI_PREFIXES = [
    "00:15:5D",  # Microsoft Corporation (Hyper-V)
    "00:1D:D8",  # Microsoft Corporation
    "00:50:F2",  # Microsoft Corporation
    "00:03:FF",  # Microsoft Corporation (Azure)
    "7C:1E:52",  # Microsoft Corporation
]


def get_microsoft_fingerprints() -> list[dict[str, Any]]:
    """Get all Microsoft Windows jump server fingerprints."""
    return [
        # ============================================================
        # WINDOWS SERVER 2019 - Patched Jump Server
        # ============================================================
        {
            "vendor": "Microsoft",
            "vendor_family": "Windows Server",
            "model": "Jump Server 2019",
            "firmware_version": "10.0.17763.5458",  # Recent cumulative update
            "device_type": "jump_server",
            "description": (
                "Windows Server 2019 remote access jump server with TeamViewer. "
                "Patched against BlueKeep and PrintNightmare."
            ),
            "oui_prefixes": MICROSOFT_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": (
                    "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - "
                    "Software: Windows Version 6.3 (Build 17763 Multiprocessor Free)"
                ),
                "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",  # Microsoft Windows
                "sys_name": "{device_name}",
                "sys_contact": "admin@example.com",
                "sys_location": "Server Room - OT Access",
                "sys_services": 76,  # Application + End-to-end + Transport + Internet
            },
            "tcp_stack": {
                "ttl": 128,  # Windows default TTL
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "external_comms": {
                "enabled": True,
                "service": "teamviewer",
                "description": "TeamViewer relay heartbeat",
                "endpoints": [
                    {"host": "router1.teamviewer.com", "ip": "185.188.32.1", "port": 443},
                    {"host": "router2.teamviewer.com", "ip": "185.188.32.2", "port": 5938},
                ],
                "interval_ms": 30000,  # 30 second heartbeat
                "protocol": "https",
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "protocol_quirks": {
                "snmp": {
                    "community_string": "public",
                    "version": "2c",
                    "additional_oids": [
                        # Windows-specific OIDs
                        ("1.3.6.1.4.1.311.1.1.3.1.1", "Windows NT"),  # Microsoft OID
                        ("1.3.6.1.4.1.311.1.1.3.1.2", "Microsoft Corporation"),
                    ],
                },
            },
        },
        # ============================================================
        # WINDOWS SERVER 2016 - BlueKeep Vulnerable
        # ============================================================
        {
            "vendor": "Microsoft",
            "vendor_family": "Windows Server",
            "model": "Jump Server 2016 (Vulnerable)",
            "firmware_version": "10.0.14393",  # Windows Server 2016 RTM - BlueKeep vulnerable
            "device_type": "jump_server",
            "description": (
                "Unpatched Windows Server 2016 jump server vulnerable to "
                "BlueKeep (CVE-2019-0708). RDP enabled with network-level authentication disabled."
            ),
            "oui_prefixes": MICROSOFT_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": (
                    "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - "
                    "Software: Windows Version 6.3 (Build 14393 Multiprocessor Free)"
                ),
                "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                "sys_name": "{device_name}",
                "sys_contact": "admin@example.com",
                "sys_location": "Server Room - OT Access",
                "sys_services": 76,
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "external_comms": {
                "enabled": True,
                "service": "teamviewer",
                "description": "TeamViewer relay heartbeat",
                "endpoints": [
                    {"host": "router1.teamviewer.com", "ip": "185.188.32.1", "port": 443},
                ],
                "interval_ms": 30000,
                "protocol": "https",
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,  # Slightly slower - older unpatched system
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
            },
            "vulnerability_info": {
                "cve_id": "CVE-2019-0708",
                "display_name": "BlueKeep - RDP Remote Code Execution",
                "is_vulnerable": True,
                "severity": "critical",
                "cvss_score": 9.8,
                "attack_vector": "network",
                "requires_authentication": False,
            },
            "protocol_quirks": {
                "snmp": {
                    "community_string": "public",
                    "version": "2c",
                },
                "rdp": {
                    "nla_enabled": False,  # Network Level Auth disabled - vulnerable
                    "port": 3389,
                },
            },
        },
        # ============================================================
        # WINDOWS SERVER 2008 R2 - EternalBlue Vulnerable
        # ============================================================
        {
            "vendor": "Microsoft",
            "vendor_family": "Windows Server",
            "model": "Jump Server 2008 R2 (Vulnerable)",
            "firmware_version": "6.1.7601",  # Windows Server 2008 R2 SP1 - EternalBlue vulnerable
            "device_type": "jump_server",
            "description": (
                "Legacy Windows Server 2008 R2 jump server vulnerable to "
                "EternalBlue (CVE-2017-0144). SMBv1 enabled."
            ),
            "oui_prefixes": MICROSOFT_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": (
                    "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - "
                    "Software: Windows Version 6.1 (Build 7601 Multiprocessor Free)"
                ),
                "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                "sys_name": "{device_name}",
                "sys_contact": "admin@example.com",
                "sys_location": "Server Room - Legacy OT Access",
                "sys_services": 76,
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,  # Older system may not have timestamps
                "df_flag": True,
            },
            "external_comms": {
                "enabled": True,
                "service": "teamviewer",
                "description": "TeamViewer relay heartbeat",
                "endpoints": [
                    {"host": "router1.teamviewer.com", "ip": "185.188.32.1", "port": 443},
                ],
                "interval_ms": 30000,
                "protocol": "https",
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 18.0,  # Slower - legacy system
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
            "vulnerability_info": {
                "cve_id": "CVE-2017-0144",
                "display_name": "EternalBlue - SMBv1 Remote Code Execution",
                "is_vulnerable": True,
                "severity": "critical",
                "cvss_score": 9.8,
                "attack_vector": "network",
                "requires_authentication": False,
            },
            "protocol_quirks": {
                "snmp": {
                    "community_string": "public",
                    "version": "2c",
                },
                "smb": {
                    "v1_enabled": True,  # SMBv1 enabled - vulnerable
                    "signing_required": False,
                },
            },
        },
        # ============================================================
        # WINDOWS SERVER 2019 - PrintNightmare Vulnerable
        # ============================================================
        {
            "vendor": "Microsoft",
            "vendor_family": "Windows Server",
            "model": "Jump Server 2019 (PrintNightmare)",
            "firmware_version": "10.0.17763.1",  # Pre-patch Windows Server 2019
            "device_type": "jump_server",
            "description": (
                "Windows Server 2019 jump server with Print Spooler enabled. "
                "Vulnerable to PrintNightmare (CVE-2021-34527)."
            ),
            "oui_prefixes": MICROSOFT_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": (
                    "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - "
                    "Software: Windows Version 6.3 (Build 17763 Multiprocessor Free)"
                ),
                "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
                "sys_name": "{device_name}",
                "sys_contact": "admin@example.com",
                "sys_location": "Server Room - OT Access",
                "sys_services": 76,
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "external_comms": {
                "enabled": True,
                "service": "teamviewer",
                "description": "TeamViewer relay heartbeat",
                "endpoints": [
                    {"host": "router1.teamviewer.com", "ip": "185.188.32.1", "port": 443},
                ],
                "interval_ms": 30000,
                "protocol": "https",
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
            "vulnerability_info": {
                "cve_id": "CVE-2021-34527",
                "display_name": "PrintNightmare - Print Spooler RCE",
                "is_vulnerable": True,
                "severity": "critical",
                "cvss_score": 8.8,
                "attack_vector": "network",
                "requires_authentication": True,  # Requires authenticated user
            },
            "protocol_quirks": {
                "snmp": {
                    "community_string": "public",
                    "version": "2c",
                },
                "print_spooler": {
                    "enabled": True,  # Print Spooler service running
                    "remote_access": True,  # Accepting remote connections
                },
            },
        },
    ]
