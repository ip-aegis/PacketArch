"""Add vendor_fingerprints table for hyper-realistic device emulation

Revision ID: 5b7c0d3e4f5a
Revises: 4a6b9c0d2e3f
Create Date: 2025-12-09 15:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

# revision identifiers, used by Alembic.
revision: str = "5b7c0d3e4f5a"
down_revision: Union[str, None] = "4a6b9c0d2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create vendor_fingerprints table."""
    op.create_table(
        "vendor_fingerprints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("vendor", sa.String(length=100), nullable=False),
        sa.Column("vendor_family", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("firmware_version", sa.String(length=50), nullable=True),
        sa.Column("oui_prefixes", ARRAY(sa.String(17)), nullable=True),
        sa.Column(
            "modbus_identity",
            JSONB(),
            nullable=True,
            comment="Modbus FC 43 Read Device Identification response",
        ),
        sa.Column(
            "ethernet_ip_identity",
            JSONB(),
            nullable=True,
            comment="EtherNet/IP ListIdentity response data",
        ),
        sa.Column(
            "profinet_identity",
            JSONB(),
            nullable=True,
            comment="PROFINET DCP identity block data",
        ),
        sa.Column(
            "tcp_stack",
            JSONB(),
            nullable=False,
            comment="TCP stack fingerprint (TTL, window, MSS, etc.)",
        ),
        sa.Column(
            "response_timing",
            JSONB(),
            nullable=False,
            comment="Response timing profile with distribution",
        ),
        sa.Column(
            "error_behavior",
            JSONB(),
            nullable=True,
            comment="Error response behavior configuration",
        ),
        sa.Column(
            "protocol_quirks",
            JSONB(),
            nullable=True,
            comment="Protocol-specific behavioral quirks",
        ),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient lookups
    op.create_index(
        op.f("ix_vendor_fingerprints_vendor"),
        "vendor_fingerprints",
        ["vendor"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vendor_fingerprints_vendor_family"),
        "vendor_fingerprints",
        ["vendor_family"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_fingerprints_vendor_model",
        "vendor_fingerprints",
        ["vendor", "model"],
        unique=False,
    )


def downgrade() -> None:
    """Drop vendor_fingerprints table."""
    op.drop_index("ix_vendor_fingerprints_vendor_model", table_name="vendor_fingerprints")
    op.drop_index(
        op.f("ix_vendor_fingerprints_vendor_family"), table_name="vendor_fingerprints"
    )
    op.drop_index(op.f("ix_vendor_fingerprints_vendor"), table_name="vendor_fingerprints")
    op.drop_table("vendor_fingerprints")
