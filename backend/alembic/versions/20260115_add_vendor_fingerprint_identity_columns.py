"""Add s7_identity, snmp_identity, bacnet_identity columns to vendor_fingerprints.

Revision ID: add_vendor_fingerprint_identity_columns
Revises: add_bacnet_identity_override
Create Date: 2026-01-15

These columns provide consistency with the VendorFingerprint model, storing
protocol-specific identity data for S7comm, SNMP, and BACnet protocols.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "add_vendor_fingerprint_identity_columns"
down_revision = "add_bacnet_identity_override"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new identity columns to vendor_fingerprints table."""
    op.add_column(
        "vendor_fingerprints",
        sa.Column(
            "s7_identity",
            JSONB,
            nullable=True,
            comment="S7comm SZL identity data (order_code, firmware_version)",
        ),
    )
    op.add_column(
        "vendor_fingerprints",
        sa.Column(
            "snmp_identity",
            JSONB,
            nullable=True,
            comment="SNMP system identity (sys_descr, sys_object_id, sys_name)",
        ),
    )
    op.add_column(
        "vendor_fingerprints",
        sa.Column(
            "bacnet_identity",
            JSONB,
            nullable=True,
            comment="BACnet I-Am identity (vendor_id, model_name, firmware_revision)",
        ),
    )


def downgrade() -> None:
    """Remove identity columns from vendor_fingerprints table."""
    op.drop_column("vendor_fingerprints", "bacnet_identity")
    op.drop_column("vendor_fingerprints", "snmp_identity")
    op.drop_column("vendor_fingerprints", "s7_identity")
