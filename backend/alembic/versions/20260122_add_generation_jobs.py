"""Add generation jobs table

Revision ID: 20260122_generation_jobs
Revises: 20260122_traffic_agents
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_generation_jobs'
down_revision: Union[str, None] = '20260122_traffic_agents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create generation_jobs table
    op.create_table(
        'generation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_duration_ms', sa.Integer(), nullable=False),
        sa.Column('packets_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('output_filename', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generation_jobs_scenario_id'), 'generation_jobs', ['scenario_id'], unique=False)
    op.create_index(op.f('ix_generation_jobs_user_id'), 'generation_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_generation_jobs_status'), 'generation_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_generation_jobs_status'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_user_id'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_scenario_id'), table_name='generation_jobs')
    op.drop_table('generation_jobs')
