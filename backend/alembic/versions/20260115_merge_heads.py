"""Merge migration heads.

Revision ID: merge_heads_20260115
Revises: add_external_comms, add_vendor_fingerprint_identity_columns
Create Date: 2026-01-15

Merges the external_comms branch with the identity columns branch.
"""

# revision identifiers, used by Alembic.
revision = "merge_heads_20260115"
down_revision = ("add_external_comms", "add_vendor_fingerprint_identity_columns")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge heads - no schema changes needed."""
    pass


def downgrade() -> None:
    """Reverse merge - no schema changes needed."""
    pass
