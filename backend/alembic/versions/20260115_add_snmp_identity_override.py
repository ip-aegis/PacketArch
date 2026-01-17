"""Add snmp_identity_override column to vulnerable_fingerprint_variants table.

Revision ID: add_snmp_identity_override
Revises: populate_cip_identity_override
Create Date: 2026-01-15

This column stores SNMP sysDescr/sysName identity overrides for ITS/transportation
devices, enabling Cisco Cyber Vision to detect vulnerable devices via SNMP.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import json


# revision identifiers, used by Alembic.
revision = "add_snmp_identity_override"
down_revision = "populate_cip_identity_override"
branch_labels = None
depends_on = None


# SNMP identity override data for Transportation CVEs
# Extracted from app/services/cve_data/transportation_cves.py
SNMP_IDENTITY_DATA = {
    # CVE-2023-28489 - Siemens CP-8000 variants
    "Siemens CP-8000 Master Station (CVE-2023-28489)": {
        "sys_descr": "Siemens SICAM CP-8000 Master Station V5.20",
        "sys_object_id": "1.3.6.1.4.1.4329.6.1.2",
        "sys_name": "CP8000-TMC-001",
        "sys_location": "Traffic Management Center",
        "sys_contact": "its-admin@example.gov",
    },
    "Siemens CP-8021 RTU (CVE-2023-28489)": {
        "sys_descr": "Siemens SICAM CP-8021 RTU V5.11",
        "sys_object_id": "1.3.6.1.4.1.4329.6.1.3",
        "sys_name": "CP8021-FIELD-001",
        "sys_location": "Intersection #47",
    },

    # CVE-2019-6569 - Siemens SCALANCE
    "SCALANCE X-200 Switch (CVE-2019-6569)": {
        "sys_descr": "Siemens SCALANCE X-200 Industrial Ethernet Switch V5.2.4",
        "sys_object_id": "1.3.6.1.4.1.4329.3.1.1",
        "sys_name": "ITS-SW-001",
        "sys_location": "Cabinet #12",
    },

    # CVE-2020-7480 - Schneider SCADAPack
    "SCADAPack 350 RTU (CVE-2020-7480)": {
        "sys_descr": "Schneider Electric SCADAPack 350 RTU Firmware V2.1.0",
        "sys_object_id": "1.3.6.1.4.1.3833.1.1.350",
        "sys_name": "RTU-CORRIDOR-001",
        "sys_location": "Highway Mile Marker 47",
    },
    "SCADAPack 334 RTU (CVE-2020-7480)": {
        "sys_descr": "Schneider Electric SCADAPack 334 RTU V2.0.5",
        "sys_object_id": "1.3.6.1.4.1.3833.1.1.334",
        "sys_name": "RTU-SIGNAL-002",
    },

    # CVE-2021-22778 - Schneider TBox
    "TBox MS-CPU32 RTU (CVE-2021-22778)": {
        "sys_descr": "Schneider Electric TBox MS-CPU32 RTU V1.50.598",
        "sys_object_id": "1.3.6.1.4.1.3833.2.1.1",
        "sys_name": "TBOX-TUNNEL-001",
        "sys_location": "Tunnel Monitoring Room",
    },

    # CVE-2018-18472 - Daktronics DMS
    "Daktronics Venus 1500 (CVE-2018-18472)": {
        "sys_descr": "Daktronics Venus 1500 DMS Controller V4.1",
        "sys_object_id": "1.3.6.1.4.1.2407.1.1.1",
        "sys_name": "DMS-I95-MM125",
        "sys_location": "Interstate 95 Mile Marker 125",
    },
    "Daktronics Venus 7000 (CVE-2018-18472)": {
        "sys_descr": "Daktronics Venus 7000 DMS Controller V4.0 Build 3847",
        "sys_object_id": "1.3.6.1.4.1.2407.1.2.1",
        "sys_name": "DMS-SR520-W",
        "sys_location": "State Route 520 Westbound",
    },

    # CVE-2022-29885 - Kapsch Toll
    "Kapsch TCS 2000 (CVE-2022-29885)": {
        "sys_descr": "Kapsch TrafficCom TCS 2000 Toll Controller V3.5.0",
        "sys_object_id": "1.3.6.1.4.1.22706.1.1.2",
        "sys_name": "TOLL-PLAZA-L1",
        "sys_location": "Toll Plaza Lane 1",
    },

    # CVE-2020-16205 - Econolite
    "Econolite Cobalt ATC (CVE-2020-16205)": {
        "sys_descr": "Econolite Cobalt ATC Traffic Controller V2.1.4",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.1",
        "sys_name": "INT-MAIN-5TH",
        "sys_location": "Main St & 5th Ave",
    },
    "Econolite ASC/3-2100 (CVE-2020-16205)": {
        "sys_descr": "Econolite ASC/3-2100 Signal Controller V2.0.8",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.2",
        "sys_name": "INT-OAK-PINE",
        "sys_location": "Oak Blvd & Pine St",
    },

    # CVE-2021-38294 - Wavetronix
    "Wavetronix SmartSensor HD (CVE-2021-38294)": {
        "sys_descr": "Wavetronix SmartSensor HD Radar V8.4",
        "sys_object_id": "1.3.6.1.4.1.34362.1.1.1",
        "sys_name": "RADAR-NB-L1",
        "sys_location": "Northbound Lane 1 Detection",
    },
    "Wavetronix SmartSensor Advance (CVE-2021-38294)": {
        "sys_descr": "Wavetronix SmartSensor Advance V8.3",
        "sys_object_id": "1.3.6.1.4.1.34362.1.2.1",
        "sys_name": "RADAR-SB-RAMP",
        "sys_location": "Southbound On-Ramp",
    },

    # CVE-2021-31986 - Axis Cameras
    "Axis P1455-LE Camera (CVE-2021-31986)": {
        "sys_descr": "AXIS P1455-LE Network Camera; 10.6; Linux 4.14 armv7l",
        "sys_object_id": "1.3.6.1.4.1.368.1.1.1",
        "sys_name": "CAM-INT-001",
        "sys_location": "Intersection Main & Oak",
    },

    # CVE-2022-30456 - Q-Free RSU
    "Q-Free RSU 5000 (CVE-2022-30456)": {
        "sys_descr": "Q-Free RSU 5000 Roadside Unit V2.8.0",
        "sys_object_id": "1.3.6.1.4.1.32055.1.1.5",
        "sys_name": "RSU-TOLL-01",
        "sys_location": "Toll Gantry A",
    },

    # CVE-2020-11896 - Treck/Ripple20
    "NTCIP Device with Treck Stack (CVE-2020-11896)": {
        "sys_descr": "NTCIP Traffic Controller FW 3.2 (Treck 6.0.1.66)",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
        "sys_name": "TC-GENERIC-001",
        "sys_location": "Field Cabinet",
    },

    # CVE-2019-18230 - Pelco
    "Pelco Spectra Enhanced (CVE-2019-18230)": {
        "sys_descr": "Pelco Spectra Enhanced PTZ Camera V1.30",
        "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",
        "sys_name": "PTZ-TUNNEL-E",
        "sys_location": "Tunnel East Portal",
    },

    # CVE-2021-27656 - FLIR
    "FLIR TrafiOne (CVE-2021-27656)": {
        "sys_descr": "FLIR TrafiOne Thermal Detector V3.4.0",
        "sys_object_id": "1.3.6.1.4.1.28846.1.1.1",
        "sys_name": "THERMAL-L1-L2",
        "sys_location": "Intersection Lanes 1-2",
    },
    "FLIR TrafiSense (CVE-2021-27656)": {
        "sys_descr": "FLIR TrafiSense Multi-Lane Detector V3.3.2",
        "sys_object_id": "1.3.6.1.4.1.28846.1.2.1",
        "sys_name": "THERMAL-RAMP",
        "sys_location": "Highway On-Ramp Detection",
    },
}


def upgrade() -> None:
    """Add snmp_identity_override column and populate with transportation CVE data."""
    # Add the column
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "snmp_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for SNMP sysDescr/sysName identity (for ITS/transportation devices)",
        ),
    )

    # Populate the column for existing transportation CVE variants
    connection = op.get_bind()

    for display_name, snmp_data in SNMP_IDENTITY_DATA.items():
        connection.execute(
            sa.text("""
                UPDATE vulnerable_fingerprint_variants
                SET snmp_identity_override = :snmp_data
                WHERE display_name = :display_name
                AND snmp_identity_override IS NULL
            """),
            {"display_name": display_name, "snmp_data": json.dumps(snmp_data)}
        )


def downgrade() -> None:
    """Remove snmp_identity_override column."""
    op.drop_column("vulnerable_fingerprint_variants", "snmp_identity_override")
