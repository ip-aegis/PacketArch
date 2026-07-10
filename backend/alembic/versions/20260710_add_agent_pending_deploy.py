"""Add traffic_agents.pending_deploy_scenario_id / pending_deploy_config.

Additive: two nullable columns used by the "deploy to a new dedicated Local
Lab" flow. Set when a scenario deploy auto-creates a Local Lab (and its
agent); cleared the moment the agent's websocket first connects, at which
point the scenario is deployed to it automatically. Null for every other
agent. Nothing existing is modified or dropped.

Revision ID: add_agent_pending_deploy
Revises: add_gen_job_artifacts
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_agent_pending_deploy"
down_revision = "add_gen_job_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "traffic_agents",
        sa.Column("pending_deploy_scenario_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "traffic_agents",
        sa.Column("pending_deploy_config", postgresql.JSONB(), nullable=True),
    )
    op.create_foreign_key(
        "fk_traffic_agents_pending_deploy_scenario_id",
        "traffic_agents",
        "scenarios",
        ["pending_deploy_scenario_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_traffic_agents_pending_deploy_scenario_id", "traffic_agents", type_="foreignkey"
    )
    op.drop_column("traffic_agents", "pending_deploy_config")
    op.drop_column("traffic_agents", "pending_deploy_scenario_id")
