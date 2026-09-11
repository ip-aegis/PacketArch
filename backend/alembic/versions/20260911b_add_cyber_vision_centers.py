"""Add cyber_vision_centers + local_labs.cv_center_id.

Multi-center Cyber Vision support. Additive: a new table (one row per CV
Center, each with its own URL, SSL flag and both API tokens, exactly one
default) and a nullable FK column on local_labs recording which center a lab's
sensor enrolls into.

Existing single-center configuration lives in four ``cyber_vision_*``
system_settings rows. It is moved into the first (default) center — and
existing labs / provisioned scenarios are stamped with it — by an idempotent
boot step (``services/cv_centers.migrate_legacy_settings``), not here, so the
move also runs on installs whose schema was built by create_all and stamped.

Revision ID: add_cyber_vision_centers
Revises: add_deployment_deploy_config
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_cyber_vision_centers"
down_revision = "add_deployment_deploy_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cyber_vision_centers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("url", sa.String(500), nullable=False, unique=True),
        sa.Column("api_token", sa.Text(), nullable=True),
        sa.Column("new_ui_token", sa.Text(), nullable=True),
        sa.Column("verify_ssl", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "uq_cyber_vision_centers_default",
        "cyber_vision_centers",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.add_column(
        "local_labs",
        sa.Column("cv_center_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_local_labs_cv_center_id",
        "local_labs",
        "cyber_vision_centers",
        ["cv_center_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_local_labs_cv_center_id", "local_labs", ["cv_center_id"])


def downgrade() -> None:
    op.drop_index("ix_local_labs_cv_center_id", table_name="local_labs")
    op.drop_constraint("fk_local_labs_cv_center_id", "local_labs", type_="foreignkey")
    op.drop_column("local_labs", "cv_center_id")
    op.drop_index("uq_cyber_vision_centers_default", table_name="cyber_vision_centers")
    op.drop_table("cyber_vision_centers")
