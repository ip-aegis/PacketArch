"""Populate cip_identity_override column with data from CVE definitions.

Revision ID: populate_cip_identity_override
Revises: add_cip_identity_override
Create Date: 2025-12-15

This migration populates the cip_identity_override column for existing
Rockwell CVE vulnerable variants. The data comes from the rockwell_cves.py
seed file which was not being used during initial seeding.
"""

from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = "populate_cip_identity_override"
down_revision = "add_cip_identity_override"
branch_labels = None
depends_on = None

# CIP identity override data for Rockwell CVEs
# Extracted from app/services/cve_data/rockwell_cves.py
CIP_IDENTITY_DATA = {
    # CVE-2022-1159 variants
    "ControlLogix L85E (CVE-2022-1159)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xDEAD0000,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L83E (CVE-2022-1159)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xDEAD0001,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L85E v30 (CVE-2022-1159)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xDEAD0002,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L85E v29 (CVE-2022-1159)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xDEAD0003,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L84E v28 (CVE-2022-1159)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xDEAD0004,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    # CVE-2022-1161 variants
    "ControlLogix L85E (CVE-2022-1161)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xBAD00000,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L85E v31 (CVE-2022-1161)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xBAD00001,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L84E v30 (CVE-2022-1161)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xBAD00002,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L83E v29 (CVE-2022-1161)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xBAD00003,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    # CVE-2021-22681 variants (CompactLogix)
    "CompactLogix L33ER (CVE-2021-22681)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0x0,
        "maximum_cip_connections": 32,
        "heartbeat_interval": 250,
    },
    "CompactLogix L33ER v31 (CVE-2021-22681)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0x0,
        "maximum_cip_connections": 32,
        "heartbeat_interval": 250,
    },
    "CompactLogix L30ER v30 (CVE-2021-22681)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0x0,
        "maximum_cip_connections": 32,
        "heartbeat_interval": 250,
    },
    "CompactLogix L36ERM v29 (CVE-2021-22681)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0x0,
        "maximum_cip_connections": 32,
        "heartbeat_interval": 250,
    },
    # CVE-2019-10954 variants (MicroLogix - no fix available)
    "MicroLogix 1400 v21.007 (CVE-2019-10954)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xFFFFFFFF,
        "maximum_cip_connections": 8,
        "heartbeat_interval": 500,
    },
    "MicroLogix 1400 v21.006 (CVE-2019-10954)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xFFFFFFFF,
        "maximum_cip_connections": 8,
        "heartbeat_interval": 500,
    },
    "MicroLogix 1400 v21.005 (CVE-2019-10954)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xFFFFFFFF,
        "maximum_cip_connections": 8,
        "heartbeat_interval": 500,
    },
    "MicroLogix 1400 v21.004 (CVE-2019-10954)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xFFFFFFFF,
        "maximum_cip_connections": 8,
        "heartbeat_interval": 500,
    },
    "MicroLogix 1400 v21.003 (CVE-2019-10954)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xFFFFFFFF,
        "maximum_cip_connections": 8,
        "heartbeat_interval": 500,
    },
    # CVE-2023-3595 variants
    "ControlLogix L85E v33.016 (CVE-2023-3595)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xCAFE0000,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L85E v33.011 (CVE-2023-3595)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xCAFE0001,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L84E v32.016 (CVE-2023-3595)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xCAFE0002,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
    "ControlLogix L83E v32.011 (CVE-2023-3595)": {
        "protection_mode": 0,
        "configuration_consistency_value": 0xCAFE0003,
        "maximum_cip_connections": 64,
        "heartbeat_interval": 250,
    },
}


def upgrade() -> None:
    """Populate cip_identity_override for existing Rockwell CVE variants."""
    connection = op.get_bind()

    for display_name, cip_data in CIP_IDENTITY_DATA.items():
        # Update the record where display_name matches
        connection.execute(
            sa.text("""
                UPDATE vulnerable_fingerprint_variants
                SET cip_identity_override = :cip_data
                WHERE display_name = :display_name
                AND cip_identity_override IS NULL
            """),
            {"display_name": display_name, "cip_data": json.dumps(cip_data)}
        )


def downgrade() -> None:
    """Clear cip_identity_override data (column remains but is nulled)."""
    op.execute(
        "UPDATE vulnerable_fingerprint_variants SET cip_identity_override = NULL"
    )
