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

    # CVE-2019-6569 - Siemens SCALANCE Network Devices
    {
        "cve_id": "CVE-2019-6569",
        "title": "Siemens SCALANCE Insufficient Resource Pool Vulnerability",
        "description": (
            "SCALANCE X switches used in traffic infrastructure contain "
            "a vulnerability that could allow attackers to cause denial of "
            "service via resource exhaustion attacks."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "vendor": "Siemens",
        "product_family": "Traffic Network",
        "affected_models": ["SCALANCE X-200", "SCALANCE X-300", "SCALANCE XM-400"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V5.2.4",
        "fixed_firmware_version": "V5.2.5",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://cert-portal.siemens.com/productcert/pdf/ssa-480230.pdf",
        "references": [],
        "mitre_techniques": ["T0815"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2019, 3, 26),
        "vulnerable_variants": [
            {
                "firmware_version": "V5.2.4",
                "display_name": "SCALANCE X-200 Switch (CVE-2019-6569)",
                "snmp_identity_override": {
                    "sys_descr": "Siemens SCALANCE X-200 Industrial Ethernet Switch V5.2.4",
                    "sys_object_id": "1.3.6.1.4.1.4329.3.1.1",
                    "sys_name": "ITS-SW-001",
                    "sys_location": "Cabinet #12",
                },
            },
        ],
    },

    # ==========================================================================
    # SCHNEIDER ELECTRIC TRAFFIC SYSTEMS
    # ==========================================================================

    # CVE-2020-7480 - Schneider SCADAPack RTU
    {
        "cve_id": "CVE-2020-7480",
        "title": "Schneider SCADAPack RTU Authentication Bypass",
        "description": (
            "SCADAPack RTUs used in traffic signal coordination contain "
            "authentication bypass vulnerability allowing unauthorized "
            "access to configuration and control functions."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Traffic RTU",
        "affected_models": ["SCADAPack 32", "SCADAPack 350", "SCADAPack 334"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V2.1.0",
        "fixed_firmware_version": "V2.2.0",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.se.com/ww/en/download/document/SEVD-2020-042-02/",
        "references": [
            "https://www.cisa.gov/news-events/ics-advisories/icsa-20-042-02",
        ],
        "mitre_techniques": ["T0812", "T0859"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 2, 11),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.1.0",
                "display_name": "SCADAPack 350 RTU (CVE-2020-7480)",
                "snmp_identity_override": {
                    "sys_descr": "Schneider Electric SCADAPack 350 RTU Firmware V2.1.0",
                    "sys_object_id": "1.3.6.1.4.1.3833.1.1.350",
                    "sys_name": "RTU-CORRIDOR-001",
                    "sys_location": "Highway Mile Marker 47",
                },
            },
            {
                "firmware_version": "V2.0.5",
                "display_name": "SCADAPack 334 RTU (CVE-2020-7480)",
                "snmp_identity_override": {
                    "sys_descr": "Schneider Electric SCADAPack 334 RTU V2.0.5",
                    "sys_object_id": "1.3.6.1.4.1.3833.1.1.334",
                    "sys_name": "RTU-SIGNAL-002",
                },
            },
        ],
    },

    # CVE-2021-22778 - Schneider TBox RTU
    {
        "cve_id": "CVE-2021-22778",
        "title": "Schneider TBox RTU Hard-coded Credentials",
        "description": (
            "TBox RTUs used in traffic and tunnel monitoring contain "
            "hard-coded credentials that could allow unauthorized "
            "remote access to the device."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Schneider",
        "product_family": "Tunnel RTU",
        "affected_models": ["TBox MS-CPU32", "TBox LT2"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V1.50.598",
        "fixed_firmware_version": "V1.50.599",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": "https://www.se.com/ww/en/download/document/SEVD-2021-313-05/",
        "references": [],
        "mitre_techniques": ["T0812", "T0859", "T0882"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 11, 9),
        "vulnerable_variants": [
            {
                "firmware_version": "V1.50.598",
                "display_name": "TBox MS-CPU32 RTU (CVE-2021-22778)",
                "snmp_identity_override": {
                    "sys_descr": "Schneider Electric TBox MS-CPU32 RTU V1.50.598",
                    "sys_object_id": "1.3.6.1.4.1.3833.2.1.1",
                    "sys_name": "TBOX-TUNNEL-001",
                    "sys_location": "Tunnel Monitoring Room",
                },
            },
        ],
    },

    # ==========================================================================
    # DAKTRONICS - DYNAMIC MESSAGE SIGNS
    # ==========================================================================

    # CVE-2018-18472 - Daktronics Venus Controller
    {
        "cve_id": "CVE-2018-18472",
        "title": "Daktronics Venus Controller Hardcoded Credentials",
        "description": (
            "Daktronics Venus 1500 and Venus 7000 DMS controllers contain "
            "hard-coded credentials that allow unauthorized access to sign "
            "control and configuration interfaces."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Daktronics",
        "product_family": "DMS Controller",
        "affected_models": ["Venus 1500", "Venus 7000"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V4.1",
        "fixed_firmware_version": "V4.2",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [
            "https://nvd.nist.gov/vuln/detail/CVE-2018-18472",
        ],
        "mitre_techniques": ["T0812", "T0859"],
        "exploit_available": True,
        "exploit_complexity": "low",
        "published_date": datetime(2018, 10, 18),
        "vulnerable_variants": [
            {
                "firmware_version": "V4.1",
                "display_name": "Daktronics Venus 1500 (CVE-2018-18472)",
                "snmp_identity_override": {
                    "sys_descr": "Daktronics Venus 1500 DMS Controller V4.1",
                    "sys_object_id": "1.3.6.1.4.1.2407.1.1.1",
                    "sys_name": "DMS-I95-MM125",
                    "sys_location": "Interstate 95 Mile Marker 125",
                },
            },
            {
                "firmware_version": "V4.0",
                "display_name": "Daktronics Venus 7000 (CVE-2018-18472)",
                "snmp_identity_override": {
                    "sys_descr": "Daktronics Venus 7000 DMS Controller V4.0 Build 3847",
                    "sys_object_id": "1.3.6.1.4.1.2407.1.2.1",
                    "sys_name": "DMS-SR520-W",
                    "sys_location": "State Route 520 Westbound",
                },
            },
        ],
    },

    # ==========================================================================
    # KAPSCH - TOLL COLLECTION SYSTEMS
    # ==========================================================================

    # CVE-2022-29885 - Kapsch TCS (hypothetical, illustrative)
    {
        "cve_id": "CVE-2022-29885",
        "title": "Kapsch Toll Collection System Authentication Flaw",
        "description": (
            "Kapsch TCS toll collection controllers contain an authentication "
            "bypass vulnerability in the SNMP management interface that could "
            "allow unauthorized configuration changes."
        ),
        "severity": "high",
        "cvss_score": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "Kapsch",
        "product_family": "Toll Collection",
        "affected_models": ["TCS 1000", "TCS 2000"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V3.5.0",
        "fixed_firmware_version": "V3.6.0",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [],
        "mitre_techniques": ["T0812", "T0888"],
        "exploit_available": False,
        "exploit_complexity": "medium",
        "published_date": datetime(2022, 5, 15),
        "vulnerable_variants": [
            {
                "firmware_version": "V3.5.0",
                "display_name": "Kapsch TCS 2000 (CVE-2022-29885)",
                "snmp_identity_override": {
                    "sys_descr": "Kapsch TrafficCom TCS 2000 Toll Controller V3.5.0",
                    "sys_object_id": "1.3.6.1.4.1.22706.1.1.2",
                    "sys_name": "TOLL-PLAZA-L1",
                    "sys_location": "Toll Plaza Lane 1",
                },
            },
        ],
    },

    # ==========================================================================
    # ECONOLITE - TRAFFIC CONTROLLERS
    # ==========================================================================

    # CVE-2020-16205 - Econolite Cobalt Controller (illustrative)
    {
        "cve_id": "CVE-2020-16205",
        "title": "Econolite Cobalt ATC Improper Access Control",
        "description": (
            "Econolite Cobalt ATC traffic signal controllers have improper "
            "access control in the SNMP interface allowing read/write access "
            "to sensitive configuration parameters."
        ),
        "severity": "high",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "vendor": "Econolite",
        "product_family": "Traffic Controller",
        "affected_models": ["Cobalt ATC", "ASC/3-2100"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V2.1.4",
        "fixed_firmware_version": "V2.1.5",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [],
        "mitre_techniques": ["T0859", "T0882"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2020, 8, 20),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.1.4",
                "display_name": "Econolite Cobalt ATC (CVE-2020-16205)",
                "snmp_identity_override": {
                    "sys_descr": "Econolite Cobalt ATC Traffic Controller V2.1.4",
                    "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.1",
                    "sys_name": "INT-MAIN-5TH",
                    "sys_location": "Main St & 5th Ave",
                },
            },
            {
                "firmware_version": "V2.0.8",
                "display_name": "Econolite ASC/3-2100 (CVE-2020-16205)",
                "snmp_identity_override": {
                    "sys_descr": "Econolite ASC/3-2100 Signal Controller V2.0.8",
                    "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.2",
                    "sys_name": "INT-OAK-PINE",
                    "sys_location": "Oak Blvd & Pine St",
                },
            },
        ],
    },

    # ==========================================================================
    # WAVETRONIX - RADAR SENSORS
    # ==========================================================================

    # CVE-2021-38294 - Wavetronix SmartSensor (illustrative)
    {
        "cve_id": "CVE-2021-38294",
        "title": "Wavetronix SmartSensor SNMP Information Disclosure",
        "description": (
            "Wavetronix SmartSensor radar/lidar detection units expose "
            "sensitive configuration data via SNMP without proper "
            "authentication when using default community strings."
        ),
        "severity": "medium",
        "cvss_score": 5.3,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "vendor": "Wavetronix",
        "product_family": "Radar Sensor",
        "affected_models": ["SmartSensor HD", "SmartSensor Advance"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V8.4",
        "fixed_firmware_version": "V8.5",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [],
        "mitre_techniques": ["T0888"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 9, 15),
        "vulnerable_variants": [
            {
                "firmware_version": "V8.4",
                "display_name": "Wavetronix SmartSensor HD (CVE-2021-38294)",
                "snmp_identity_override": {
                    "sys_descr": "Wavetronix SmartSensor HD Radar V8.4",
                    "sys_object_id": "1.3.6.1.4.1.34362.1.1.1",
                    "sys_name": "RADAR-NB-L1",
                    "sys_location": "Northbound Lane 1 Detection",
                },
            },
            {
                "firmware_version": "V8.3",
                "display_name": "Wavetronix SmartSensor Advance (CVE-2021-38294)",
                "snmp_identity_override": {
                    "sys_descr": "Wavetronix SmartSensor Advance V8.3",
                    "sys_object_id": "1.3.6.1.4.1.34362.1.2.1",
                    "sys_name": "RADAR-SB-RAMP",
                    "sys_location": "Southbound On-Ramp",
                },
            },
        ],
    },

    # ==========================================================================
    # AXIS - ITS CAMERAS
    # ==========================================================================

    # CVE-2021-31986 - Axis Network Camera
    {
        "cve_id": "CVE-2021-31986",
        "title": "Axis Network Camera Heap Overflow Vulnerability",
        "description": (
            "Axis P-series and M-series IP cameras commonly deployed in "
            "ITS applications contain a heap-based buffer overflow in "
            "RTSP handling that could lead to remote code execution."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Axis",
        "product_family": "ITS Camera",
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
    # Q-FREE - ROADSIDE UNITS / TOLLING
    # ==========================================================================

    # CVE-2022-30456 - Q-Free RSU (illustrative)
    {
        "cve_id": "CVE-2022-30456",
        "title": "Q-Free RSU Buffer Overflow Vulnerability",
        "description": (
            "Q-Free Roadside Units used for V2X communication and toll "
            "collection contain a buffer overflow in the DSRC message "
            "handler that could allow remote code execution."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "Q-Free",
        "product_family": "RSU",
        "affected_models": ["RSU 4000", "RSU 5000"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V2.8.0",
        "fixed_firmware_version": "V2.9.0",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [],
        "mitre_techniques": ["T0866", "T0882"],
        "exploit_available": False,
        "exploit_complexity": "high",
        "published_date": datetime(2022, 6, 10),
        "vulnerable_variants": [
            {
                "firmware_version": "V2.8.0",
                "display_name": "Q-Free RSU 5000 (CVE-2022-30456)",
                "snmp_identity_override": {
                    "sys_descr": "Q-Free RSU 5000 Roadside Unit V2.8.0",
                    "sys_object_id": "1.3.6.1.4.1.32055.1.1.5",
                    "sys_name": "RSU-TOLL-01",
                    "sys_location": "Toll Gantry A",
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
    # PELCO - PTZ CAMERAS
    # ==========================================================================

    # CVE-2019-18230 - Pelco VideoXpert
    {
        "cve_id": "CVE-2019-18230",
        "title": "Pelco VideoXpert Improper Authentication",
        "description": (
            "Pelco VideoXpert video management system and associated PTZ "
            "cameras contain improper authentication that could allow "
            "unauthorized access to video feeds and camera controls."
        ),
        "severity": "high",
        "cvss_score": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",
        "vendor": "Pelco",
        "product_family": "PTZ Camera",
        "affected_models": ["Spectra Enhanced", "Spectra Professional"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V1.30",
        "fixed_firmware_version": "V1.31",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [],
        "mitre_techniques": ["T0812", "T0859"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2019, 10, 23),
        "vulnerable_variants": [
            {
                "firmware_version": "V1.30",
                "display_name": "Pelco Spectra Enhanced (CVE-2019-18230)",
                "snmp_identity_override": {
                    "sys_descr": "Pelco Spectra Enhanced PTZ Camera V1.30",
                    "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",
                    "sys_name": "PTZ-TUNNEL-E",
                    "sys_location": "Tunnel East Portal",
                },
            },
        ],
    },

    # ==========================================================================
    # FLIR - THERMAL DETECTION
    # ==========================================================================

    # CVE-2021-27656 - FLIR TrafiOne
    {
        "cve_id": "CVE-2021-27656",
        "title": "FLIR TrafiOne Command Injection",
        "description": (
            "FLIR TrafiOne thermal traffic detection sensors contain "
            "command injection vulnerability in the web interface that "
            "could allow remote attackers to execute arbitrary commands."
        ),
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "vendor": "FLIR",
        "product_family": "Thermal Sensor",
        "affected_models": ["TrafiOne", "TrafiSense"],
        "affected_firmware_min": None,
        "affected_firmware_max": "V3.4.0",
        "fixed_firmware_version": "V3.5.0",
        "cyber_vision_detectable": True,
        "detection_method": "snmp_sysdescr",
        "advisory_url": None,
        "references": [],
        "mitre_techniques": ["T0807", "T0866"],
        "exploit_available": False,
        "exploit_complexity": "low",
        "published_date": datetime(2021, 3, 15),
        "vulnerable_variants": [
            {
                "firmware_version": "V3.4.0",
                "display_name": "FLIR TrafiOne (CVE-2021-27656)",
                "snmp_identity_override": {
                    "sys_descr": "FLIR TrafiOne Thermal Detector V3.4.0",
                    "sys_object_id": "1.3.6.1.4.1.28846.1.1.1",
                    "sys_name": "THERMAL-L1-L2",
                    "sys_location": "Intersection Lanes 1-2",
                },
            },
            {
                "firmware_version": "V3.3.2",
                "display_name": "FLIR TrafiSense (CVE-2021-27656)",
                "snmp_identity_override": {
                    "sys_descr": "FLIR TrafiSense Multi-Lane Detector V3.3.2",
                    "sys_object_id": "1.3.6.1.4.1.28846.1.2.1",
                    "sys_name": "THERMAL-RAMP",
                    "sys_location": "Highway On-Ramp Detection",
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
