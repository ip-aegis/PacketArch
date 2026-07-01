"""Add generation_jobs.artifacts JSON column.

Additive: a nullable JSON column listing every PCAP file a generation run
produced ({kind, filename, packets, size_bytes}). Populated for attack-export
runs (combined + baseline + attack); NULL for single-file runs and all rows
written before attack export existed. Nothing existing is modified or dropped.

Revision ID: add_gen_job_artifacts
Revises: add_local_labs
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa

revision = "add_gen_job_artifacts"
down_revision = "add_local_labs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("artifacts", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "artifacts")
