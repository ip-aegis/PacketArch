"""Add agent_deployments.deploy_config.

Additive: one nullable JSONB column recording the options a deployment was
started with (adaptive timing, attack playbook, cell-isolation override,
whether it is a multi-sensor topology conductor). It is what lets a
deployment that went ``disconnected`` — backend restart, agent restart, or
the whole host losing power — be replayed faithfully when its agent
reconnects (see AgentManager.resume_disconnected_deployments). Null on rows
created before this revision; those resume with the scenario's stored
definition alone. Nothing existing is modified or dropped.

Revision ID: add_deployment_deploy_config
Revises: add_agent_pending_deploy
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_deployment_deploy_config"
down_revision = "add_agent_pending_deploy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_deployments",
        sa.Column("deploy_config", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_deployments", "deploy_config")
