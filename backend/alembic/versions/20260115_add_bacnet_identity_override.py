"""Add bacnet_identity_override column to vulnerable_fingerprint_variants table.

Revision ID: add_bacnet_identity_override
Revises: add_snmp_identity_override
Create Date: 2026-01-15

This column stores BACnet I-Am identity overrides for BMS/building automation
devices, enabling Cisco Cyber Vision to detect vulnerable devices via BACnet.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import json


# revision identifiers, used by Alembic.
revision = "add_bacnet_identity_override"
down_revision = "add_snmp_identity_override"
branch_labels = None
depends_on = None


# BACnet identity override data for Building Automation CVEs
# Extracted from app/services/cve_data/building_automation_cves.py
BACNET_IDENTITY_DATA = {
    # CVE-2022-30312 - Tridium Niagara
    "Tridium Niagara JACE 8000 (CVE-2022-30312)": {
        "vendor_id": 17,
        "vendor_name": "Honeywell",
        "model_name": "Niagara 4 JACE 8000",
        "firmware_revision": "4.10.1",
        "application_software_version": "4.10",
    },

    # CVE-2023-4804 - Johnson Controls Metasys
    "Metasys NAE55 (CVE-2023-4804)": {
        "vendor_id": 5,
        "vendor_name": "Johnson Controls",
        "model_name": "NAE55 Network Automation Engine",
        "firmware_revision": "12.0.3",
        "application_software_version": "12.0",
    },
    "Metasys SNC (CVE-2023-4804)": {
        "vendor_id": 5,
        "vendor_name": "Johnson Controls",
        "model_name": "SNC Supervisory Network Controller",
        "firmware_revision": "11.0.2",
    },

    # CVE-2019-9569 - Delta Controls enteliBUS
    "Delta Controls enteliBUS Manager (CVE-2019-9569)": {
        "vendor_id": 122,
        "vendor_name": "Delta Controls",
        "model_name": "enteliBUS Manager",
        "firmware_revision": "4.7.0",
        "application_software_version": "4.7",
    },

    # CVE-2015-2867 - Trane ComfortLink II
    "Trane ComfortLink II XL950 (CVE-2015-2867)": {
        "vendor_id": 97,
        "vendor_name": "Trane",
        "model_name": "ComfortLink II XL950",
        "firmware_revision": "4.0.1",
    },

    # CVE-2021-42534 - Trane Tracer SC
    "Trane Tracer SC+ (CVE-2021-42534)": {
        "vendor_id": 97,
        "vendor_name": "Trane",
        "model_name": "Tracer SC+ System Controller",
        "firmware_revision": "5.7.0",
        "application_software_version": "5.7",
    },

    # CVE-2019-6853 - Schneider Electric Andover Continuum
    "Andover Continuum CX9680 (CVE-2019-6853)": {
        "vendor_id": 67,
        "vendor_name": "Schneider Electric",
        "model_name": "Andover Continuum CX9680",
        "firmware_revision": "1.86.0",
    },

    # CVE-2021-35963 - Automated Logic WebCTRL
    "Automated Logic WebCTRL Server (CVE-2021-35963)": {
        "vendor_id": 86,
        "vendor_name": "Automated Logic",
        "model_name": "WebCTRL Building Automation Server",
        "firmware_revision": "8.4.0",
        "application_software_version": "8.4",
    },

    # CVE-2020-7002 - Carrier i-Vu
    "Carrier i-Vu Pro (CVE-2020-7002)": {
        "vendor_id": 301,
        "vendor_name": "Carrier",
        "model_name": "i-Vu Pro Open Server",
        "firmware_revision": "6.9.0",
        "application_software_version": "6.9",
    },

    # CVE-2020-9049 - Distech Controls ECLYPSE
    "Distech EC-BOS-8 (CVE-2020-9049)": {
        "vendor_id": 165,
        "vendor_name": "Distech Controls",
        "model_name": "EC-BOS-8 Building Controller",
        "firmware_revision": "4.0.1",
        "application_software_version": "4.0",
    },

    # CVE-2022-31465 - Siemens Desigo CC
    "Siemens DXR2 Controller (CVE-2022-31465)": {
        "vendor_id": 24,
        "vendor_name": "Siemens",
        "model_name": "DXR2.E12 Room Automation Station",
        "firmware_revision": "5.29.0",
        "application_software_version": "5.29",
    },
}


def upgrade() -> None:
    """Add bacnet_identity_override column and populate with BMS CVE data."""
    # Add the column
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "bacnet_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for BACnet I-Am identity (for BMS/building automation devices)",
        ),
    )

    # Populate the column for existing BMS CVE variants
    connection = op.get_bind()

    for display_name, bacnet_data in BACNET_IDENTITY_DATA.items():
        connection.execute(
            sa.text("""
                UPDATE vulnerable_fingerprint_variants
                SET bacnet_identity_override = :bacnet_data
                WHERE display_name = :display_name
                AND bacnet_identity_override IS NULL
            """),
            {"display_name": display_name, "bacnet_data": json.dumps(bacnet_data)}
        )


def downgrade() -> None:
    """Remove bacnet_identity_override column."""
    op.drop_column("vulnerable_fingerprint_variants", "bacnet_identity_override")
