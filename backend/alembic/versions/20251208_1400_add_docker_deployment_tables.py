"""Add docker hosts and remote deployments tables

Revision ID: 3f5a8b9c0d1e
Revises: 2edadfaf14a4
Create Date: 2025-12-08 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f5a8b9c0d1e"
down_revision: Union[str, None] = "2edadfaf14a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create docker_hosts table
    op.create_table(
        "docker_hosts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("docker_api_url", sa.String(length=500), nullable=False),
        sa.Column("tls_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("ca_cert", sa.Text(), nullable=True),
        sa.Column("client_cert", sa.Text(), nullable=True),
        sa.Column("client_key", sa.Text(), nullable=True),
        sa.Column("default_interface", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create remote_deployments table
    op.create_table(
        "remote_deployments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("docker_host_id", sa.UUID(), nullable=False),
        sa.Column("container_id", sa.String(length=100), nullable=True),
        sa.Column("container_name", sa.String(length=255), nullable=True),
        sa.Column("network_interface", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, default="pending"),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False, default=60000),
        sa.Column("packets_injected", sa.BigInteger(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.ForeignKeyConstraint(["docker_host_id"], ["docker_hosts.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        op.f("ix_remote_deployments_scenario_id"),
        "remote_deployments",
        ["scenario_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_remote_deployments_docker_host_id"),
        "remote_deployments",
        ["docker_host_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_remote_deployments_status"),
        "remote_deployments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes
    op.drop_index(op.f("ix_remote_deployments_status"), table_name="remote_deployments")
    op.drop_index(
        op.f("ix_remote_deployments_docker_host_id"), table_name="remote_deployments"
    )
    op.drop_index(
        op.f("ix_remote_deployments_scenario_id"), table_name="remote_deployments"
    )

    # Drop tables
    op.drop_table("remote_deployments")
    op.drop_table("docker_hosts")
