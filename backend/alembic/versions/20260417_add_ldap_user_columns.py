"""Add LDAP auth columns to users table.

Revision ID: add_ldap_user_columns
Revises: drop_docker_hosts
Create Date: 2026-04-17

- Adds `auth_source` ("local" | "ldap") with default "local" so existing rows backfill correctly.
- Adds `ldap_dn` for storing the bound DN of LDAP-authenticated users.
- Relaxes `password_hash` to nullable; LDAP users have no local password.
"""

import sqlalchemy as sa

from alembic import op

revision = "add_ldap_user_columns"
down_revision = "drop_docker_hosts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auth_source",
            sa.String(length=16),
            nullable=False,
            server_default="local",
        ),
    )
    op.add_column(
        "users",
        sa.Column("ldap_dn", sa.String(length=512), nullable=True),
    )
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("users", "ldap_dn")
    op.drop_column("users", "auth_source")
