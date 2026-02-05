"""Add traffic agents tables

Revision ID: 20260122_traffic_agents
Revises:
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_traffic_agents'
down_revision: Union[str, None] = '20260122_consolidate_fingerprints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create traffic_agents table
    op.create_table(
        'traffic_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('default_interface', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='offline'),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_traffic_agents_name'), 'traffic_agents', ['name'], unique=False)
    op.create_index(op.f('ix_traffic_agents_token_hash'), 'traffic_agents', ['token_hash'], unique=False)

    # Create agent_deployments table
    op.create_table(
        'agent_deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='starting'),
        sa.Column('interface', sa.String(length=100), nullable=True),
        sa.Column('packets_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('stopped_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['traffic_agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_deployments_agent_id'), 'agent_deployments', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_deployments_scenario_id'), 'agent_deployments', ['scenario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agent_deployments_scenario_id'), table_name='agent_deployments')
    op.drop_index(op.f('ix_agent_deployments_agent_id'), table_name='agent_deployments')
    op.drop_table('agent_deployments')
    op.drop_index(op.f('ix_traffic_agents_token_hash'), table_name='traffic_agents')
    op.drop_index(op.f('ix_traffic_agents_name'), table_name='traffic_agents')
    op.drop_table('traffic_agents')
