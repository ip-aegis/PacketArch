"""Add cip_identity_override column to vulnerable_fingerprint_variants table.

Revision ID: add_cip_identity_override
Revises: 20251211_add_ip_range_allocations
Create Date: 2025-12-15

This column stores CIP Identity Object (Class 0x01) attribute overrides
for deep device fingerprinting, enabling Cisco Cyber Vision to detect
vulnerable Rockwell devices beyond MAC-level identification.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "add_cip_identity_override"
down_revision = "add_ip_range_allocations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cip_identity_override column."""
    op.add_column(
        "vulnerable_fingerprint_variants",
        sa.Column(
            "cip_identity_override",
            JSONB,
            nullable=True,
            comment="Overrides for CIP Identity Object (Class 0x01) deep fingerprinting",
        ),
    )


def downgrade() -> None:
    """Remove cip_identity_override column."""
    op.drop_column("vulnerable_fingerprint_variants", "cip_identity_override")
