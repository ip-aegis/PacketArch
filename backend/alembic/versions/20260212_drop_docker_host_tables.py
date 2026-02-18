"""Drop legacy docker_hosts and remote_deployments tables.

Revision ID: drop_docker_hosts
Revises: merge_profiles_templates
Create Date: 2026-02-12

The legacy Docker Host deployment system has been retired in favor of
the WebSocket-based traffic agent model. These tables are no longer used.
"""

from alembic import op

revision = "drop_docker_hosts"
down_revision = "merge_profiles_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop remote_deployments first (has FK to docker_hosts)
    op.drop_table("remote_deployments")
    op.drop_table("docker_hosts")


def downgrade() -> None:
    # Not recreating legacy tables - data is not recoverable
    raise NotImplementedError(
        "Cannot recreate dropped docker_hosts/remote_deployments tables. "
        "The legacy Docker Host system has been retired."
    )
