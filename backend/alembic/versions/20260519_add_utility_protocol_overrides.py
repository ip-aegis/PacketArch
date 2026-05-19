"""Add DNP3 / IEC-104 / IEC-61850 / C37.118 override columns to vulnerable_fingerprint_variants.

Revision ID: add_utility_overrides
Revises: add_ai_call_audit
Create Date: 2026-05-19

The four utility/substation protocols had override fields declared in CVE
data dicts but no DB columns, so the seeder silently dropped them and the
runtime applicator could not emit vulnerable-flavored DNP3 / IEC-104 / 61850
identity bytes. This migration adds the missing JSONB columns so the wire
matches the declared vulnerability for power-vertical relays, RTUs, and PMUs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "add_utility_overrides"
down_revision = "add_ai_call_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "dnp3_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for DNP3 Device Attributes Group 0 (utility SCADA RTUs/IEDs)",
        ),
    )
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "iec104_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for IEC 60870-5-104 station identity (transmission SCADA)",
        ),
    )
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "iec61850_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for IEC 61850 MMS/GOOSE/SV identity (substation IEDs)",
        ),
    )
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "c37118_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for IEEE C37.118 synchrophasor PMU identity",
        ),
    )


def downgrade() -> None:
    op.drop_column("vulnerable_fingerprint_variants", "c37118_identity_override")
    op.drop_column("vulnerable_fingerprint_variants", "iec61850_identity_override")
    op.drop_column("vulnerable_fingerprint_variants", "iec104_identity_override")
    op.drop_column("vulnerable_fingerprint_variants", "dnp3_identity_override")
