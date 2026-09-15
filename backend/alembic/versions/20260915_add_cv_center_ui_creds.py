"""Add CV UI login credentials to cyber_vision_centers.

A third credential kind alongside the two API tokens. CV 5.6 only registers a
network correctly when it is created through the new UI's CSV import, and that
requires a real UI session (/scv/*) rather than an API token.

Revision ID: add_cv_center_ui_creds
Revises: add_cyber_vision_centers
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "add_cv_center_ui_creds"
down_revision = "add_cyber_vision_centers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cyber_vision_centers", sa.Column("ui_username", sa.String(100), nullable=True))
    # Fernet ciphertext, like api_token / new_ui_token.
    op.add_column("cyber_vision_centers", sa.Column("ui_password", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cyber_vision_centers", "ui_password")
    op.drop_column("cyber_vision_centers", "ui_username")
