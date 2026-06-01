# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Building Automation / BMS CVE data.

CVE information for Building Management Systems, HVAC controllers, and
building automation equipment. These vulnerabilities are detectable via
BACnet I-Am responses and/or SNMP sysDescr strings which Cisco Cyber Vision
parses for device identification and firmware version extraction.

Detection Methods:
    1. BACnet I-Am: Cyber Vision monitors BACnet/IP broadcasts for I-Am
       responses containing vendor_id, model_name, and firmware_revision.
    2. SNMP sysDescr: Cyber Vision monitors SNMP GetResponse packets for
       sysDescr OID (1.3.6.1.2.1.1.1.0).

Auto-Derivation:
    With FirmwareVersionDeriver, only the top-level `firmware_version` field
    is required. The following are auto-derived:
    - bacnet_identity.firmware_revision
    - snmp_identity.sys_descr (from snmp_sys_descr_template)

    Non-firmware fields remain explicit (vendor_id, vendor_name, model_name,
    sys_object_id, sys_name).

BACnet Vendor IDs:
    5: Johnson Controls
    17: Honeywell
    24: Siemens
    67: Schneider Electric
    86: Automated Logic
    97: Trane
    122: Delta Controls
    165: Distech Controls
    301: Carrier
"""

from datetime import datetime

BUILDING_AUTOMATION_CVES: list[dict] = [
    # ==========================================================================
    # HONEYWELL / TRIDIUM - Niagara Framework
    # ==========================================================================

    # CVE-2022-30312 - Tridium Niagara
    {
        "cve_id": "CVE-2022-30312",
        "title": "Tridium Niagara Framework Credential Exposure",
        "description": (
            "Tridium Niagara Framework through 4.10 allows attackers to "
            "extract credential information from backup files. This affects "
            "JACE and Supervisor installations used in building automation."
        ),
        "severity": "critical",
        "cvss_score": 6.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Honeywell",
        "product_family": "Niagara",
        "affected_models": ["JACE 8000", "Niagara 4 Supervisor", "JACE 3E"],
        "affected_firmware_min": None,
        "affected_firmware_max": "4.10.1",
        "fixed_firmware_version": "4.11.0",
        "cyber_vision_detectable": True,
        "detection_method": "bacnet_i_am",
        "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2022-30312",
        "references": [
            "https://nvd.nist.gov/vuln/detail/CVE-2022-30312",
        ],
        "mitre_techniques": ["T0859", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2022, 6, 28),
        "vulnerable_variants": [
            {
                # firmware_version is the single source of truth
                # Auto-derived to: bacnet_identity.firmware_revision = "4.10.1"
                #                  snmp_identity.sys_descr (from template)
                "firmware_version": "4.10.1",
                "display_name": "Tridium Niagara JACE 8000 (CVE-2022-30312)",
                # SNMP sys_descr template - firmware auto-interpolated
                "snmp_sys_descr_template": "Tridium Niagara 4 JACE 8000 v{firmware_version}",
                # Non-firmware BACnet fields - must be explicit
                "bacnet_identity_override": {
                    "vendor_id": 17,
                    "vendor_name": "Honeywell",
                    "model_name": "Niagara 4 JACE 8000",
                    "application_software_version": "4.10",
                },
                # Non-firmware SNMP fields - must be explicit
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.4131.1.1.1",
                    "sys_name": "JACE8000-BLD-001",
                },
            },
        ],
    },

    # ==========================================================================
    # JOHNSON CONTROLS - Metasys
    # ==========================================================================

    # CVE-2023-4804 - Johnson Controls Metasys
    {
        "cve_id": "CVE-2023-4804",
        "title": "Johnson Controls Metasys NAE Authentication Bypass",
        "description": (
            "Johnson Controls Metasys NAE and SNE controllers versions prior "
            "to 12.0.4 contain an authentication bypass vulnerability that "
            "allows remote attackers to access sensitive configuration data."
        ),
        "severity": "high",
        "cvss_score": 8.6,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:L",
        "vendor": "Johnson Controls",
        "product_family": "Metasys",
        "affected_models": ["NAE55", "NAE45", "SNE", "SNC"],
        "affected_firmware_min": None,
        "affected_firmware_max": "12.0.3",
        "fixed_firmware_version": "12.0.4",
        "cyber_vision_detectable": True,
        "detection_method": "bacnet_i_am",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-23-341-03",
        "references": [
            "https://www.johnsoncontrols.com/cyber-solutions/security-advisories",
        ],
        "mitre_techniques": ["T0859", "T0800"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2023, 12, 7),
        "vulnerable_variants": [
            {
                "firmware_version": "12.0.3",
                "display_name": "Metasys NAE55 (CVE-2023-4804)",
                "snmp_sys_descr_template": "Johnson Controls Metasys NAE55 v{firmware_version}",
                "bacnet_identity_override": {
                    "vendor_id": 5,
                    "vendor_name": "Johnson Controls",
                    "model_name": "NAE55 Network Automation Engine",
                    "application_software_version": "12.0",
                },
                "snmp_identity_override": {
                    "sys_object_id": "1.3.6.1.4.1.4399.2.1.1",
                    "sys_name": "NAE55-VULNERABLE",
                },
            },
            {
                "firmware_version": "11.0.2",
                "display_name": "Metasys SNC (CVE-2023-4804)",
                "bacnet_identity_override": {
                    "vendor_id": 5,
                    "vendor_name": "Johnson Controls",
                    "model_name": "SNC Supervisory Network Controller",
                },
            },
        ],
    },

    # ==========================================================================
    # DELTA CONTROLS - enteliBUS
    # ==========================================================================

    # CVE-2019-9569 - Delta Controls enteliBUS Manager
    {
        "cve_id": "CVE-2019-9569",
        "title": "Delta Controls enteliBUS Manager Remote Code Execution",
        "description": (
            "Delta Controls enteliBUS Manager contains multiple buffer "
            "overflow vulnerabilities that allow remote code execution via "
            "specially crafted BACnet packets."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Delta Controls",
        "product_family": "enteliBUS",
        "affected_models": ["enteliBUS Manager", "eBMGR"],
        "affected_firmware_min": None,
        "affected_firmware_max": "4.7.0",
        "fixed_firmware_version": "4.8.0",
        "cyber_vision_detectable": True,
        "detection_method": "bacnet_i_am",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-19-311-01",
        "references": [
            "https://nvd.nist.gov/vuln/detail/CVE-2019-9569",
        ],
        "mitre_techniques": ["T0866", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 11, 7),
        "vulnerable_variants": [
            {
                "firmware_version": "4.7.0",
                "display_name": "Delta Controls enteliBUS Manager (CVE-2019-9569)",
                "snmp_sys_descr_template": "Delta Controls enteliBUS Manager v{firmware_version}",
                "bacnet_identity_override": {
                    "vendor_id": 122,
                    "vendor_name": "Delta Controls",
                    "model_name": "enteliBUS Manager",
                    "application_software_version": "4.7",
                },
            },
        ],
    },

    # ==========================================================================
    # TRANE - Building Controllers
    # ==========================================================================

    # CVE-2015-2867 - Trane ComfortLink II
    {
        "cve_id": "CVE-2015-2867",
        "title": "Trane ComfortLink II Hardcoded Credentials",
        "description": (
            "Trane ComfortLink II thermostats contain hardcoded credentials "
            "that allow remote attackers to access the device configuration "
            "and control HVAC systems."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Trane",
        "product_family": "ComfortLink",
        "affected_models": ["ComfortLink II XL950", "ComfortLink II XL850"],
        "affected_firmware_min": None,
        "affected_firmware_max": "4.0.1",
        "fixed_firmware_version": "4.2.0",
        "cyber_vision_detectable": True,
        "detection_method": "bacnet_i_am",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-15-153-01",
        "references": [
            "https://nvd.nist.gov/vuln/detail/CVE-2015-2867",
        ],
        "mitre_techniques": ["T0859", "T0831"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2015, 6, 2),
        "vulnerable_variants": [
            {
                "firmware_version": "4.0.1",
                "display_name": "Trane ComfortLink II XL950 (CVE-2015-2867)",
                "snmp_sys_descr_template": "Trane ComfortLink II XL950 v{firmware_version}",
                "bacnet_identity_override": {
                    "vendor_id": 97,
                    "vendor_name": "Trane",
                    "model_name": "ComfortLink II XL950",
                },
            },
        ],
    },

    # CVE-2021-42534 - Trane Tracer SC
    {
        "cve_id": "CVE-2021-42534",
        "title": "Trane Tracer SC Cross-Site Scripting",
        "description": (
            "Trane Tracer SC/SC+ building controllers contain stored XSS "
            "vulnerabilities that allow attackers to inject malicious "
            "scripts via the web interface."
        ),
        "severity": "medium",
        "cvss_score": 6.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "vendor": "Trane",
        "product_family": "Tracer",
        "affected_models": ["Tracer SC", "Tracer SC+"],
        "affected_firmware_min": None,
        "affected_firmware_max": "5.7.0",
        "fixed_firmware_version": "5.8.0",
        "cyber_vision_detectable": True,
        "detection_method": "bacnet_i_am",
        "advisory_url": "https://www.cisa.gov/news-events/ics-advisories/icsa-21-301-01",
        "references": [],
        "mitre_techniques": ["T0866"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2021, 10, 28),
        "vulnerable_variants": [
            {
                "firmware_version": "5.7.0",
                "display_name": "Trane Tracer SC+ (CVE-2021-42534)",
                "snmp_sys_descr_template": "Trane Tracer SC+ Controller v{firmware_version}",
                "bacnet_identity_override": {
                    "vendor_id": 97,
                    "vendor_name": "Trane",
                    "model_name": "Tracer SC+ System Controller",
                    "application_software_version": "5.7",
                },
            },
        ],
    },

    # ==========================================================================
    # SCHNEIDER ELECTRIC - Andover Continuum
    # ==========================================================================

    # CVE-2019-6853 - Schneider Electric Andover Continuum
    {
        "cve_id": "CVE-2019-6853",
        "title": "Schneider Electric Andover Continuum Information Disclosure",
        "description": (
            "Schneider Electric Andover Continuum controllers contain an "
            "information disclosure vulnerability allowing unauthorized "
            "access to sensitive configuration data via unauthenticated API."
        ),
        "severity": "medium",
        "cvss_score": 6.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N",
        "vendor": "Schneider Electric",
        "product_family": "Andover Continuum",
        "affected_models": ["CX9680", "CX9640", "CX9600"],
        "affected_firmware_min": None,
        "affected_firmware_max": "1.86.0",
        "fixed_firmware_version": "1.87.0",
        "cyber_vision_detectable": True,
        "detection_method": "bacnet_i_am",
        "advisory_url": "https://www.se.com/ww/en/download/document/SEVD-2019-225-02/",
        "references": [],
        "mitre_techniques": ["T0859"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 8, 13),
        "vulnerable_variants": [
            {
                "firmware_version": "1.86.0",
                "display_name": "Andover Continuum CX9680 (CVE-2019-6853)",
                "snmp_sys_descr_template": "Schneider Electric Andover Continuum CX9680 v{firmware_version}",
                "bacnet_identity_override": {
                    "vendor_id": 67,
                    "vendor_name": "Schneider Electric",
                    "model_name": "Andover Continuum CX9680",
                },
                # Non-firmware Modbus fields - must be explicit
                "modbus_identity_override": {
                    "vendor_id": 0x000B,
                    "product_code": "CX9680",
                    "vendor_name": "Schneider Electric",
                    "product_name": "Andover Continuum CX9680",
                },
            },
        ],
    },
]


def get_building_automation_cves_by_vendor(vendor: str) -> list[dict]:
    """Get CVEs for a specific vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        List of CVEs for the vendor
    """
    vendor_lower = vendor.lower()
    return [
        cve for cve in BUILDING_AUTOMATION_CVES
        if cve["vendor"].lower() == vendor_lower
    ]


def get_building_automation_cve_by_id(cve_id: str) -> dict | None:
    """Get a specific CVE by ID.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2022-30312")

    Returns:
        CVE dictionary or None if not found
    """
    for cve in BUILDING_AUTOMATION_CVES:
        if cve["cve_id"] == cve_id:
            return cve
    return None
