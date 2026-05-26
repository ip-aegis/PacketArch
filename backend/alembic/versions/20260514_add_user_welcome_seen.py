"""Add welcome_seen flag to users table.

Revision ID: add_user_welcome_seen
Revises: add_user_acknowledgments
Create Date: 2026-05-14

Tracks whether the user has dismissed the first-login Welcome Tour. Replaces
the prior browser-scoped localStorage gate so the tour stays dismissed across
devices and browsers for a given account.
"""

import sqlalchemy as sa

from alembic import op

revision = "add_user_welcome_seen"
down_revision = "add_user_acknowledgments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "welcome_seen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Existing users who have already logged in shouldn't see the tour again
    # after this migration — they almost certainly dismissed the prior
    # localStorage gate on whichever browser they used.
    op.execute(
        "UPDATE users SET welcome_seen = TRUE WHERE last_login IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("users", "welcome_seen")
