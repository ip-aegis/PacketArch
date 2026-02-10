"""Merge device profiles into device templates.

Add vertical_hints and palette_config columns to device_templates.
Widen role column from String(20) to String(255).
Migrate user-created device_profiles into device_templates.
Drop device_profiles table.

Revision ID: merge_profiles_templates
Revises: drop_learning_pipeline
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "merge_profiles_templates"
down_revision = "drop_learning_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns to device_templates
    op.add_column(
        "device_templates",
        sa.Column(
            "vertical_hints",
            ARRAY(sa.String(50)),
            nullable=True,
            comment="Industry verticals: manufacturing, water, energy, oil_gas, building_automation, transportation",
        ),
    )
    op.add_column(
        "device_templates",
        sa.Column(
            "palette_config",
            JSONB,
            nullable=True,
            comment="Palette/canvas config: {timing_model, payload_templates, behavior_model}",
        ),
    )

    # 2. Widen role column from String(20) to String(255)
    op.alter_column(
        "device_templates",
        "role",
        type_=sa.String(255),
        existing_type=sa.String(20),
        existing_nullable=True,
    )

    # 3. Migrate user-created device_profiles into device_templates
    # Only if device_profiles table still exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "device_profiles" in inspector.get_table_names():
        conn.execute(
            sa.text("""
                INSERT INTO device_templates (
                    id, source, vendor, model, device_type, name, description,
                    role, active_protocols, vertical_hints, palette_config,
                    is_active, confidence, sample_count, consistency_score,
                    created_at, updated_at
                )
                SELECT
                    id,
                    'user_created',
                    vendor_fingerprint->>'fingerprint_vendor',
                    vendor_fingerprint->>'fingerprint_model',
                    device_type,
                    name,
                    description,
                    role,
                    CASE
                        WHEN supported_protocols IS NOT NULL
                        THEN ARRAY(SELECT jsonb_array_elements_text(supported_protocols))
                        ELSE NULL
                    END,
                    CASE
                        WHEN vertical_hints IS NOT NULL
                        THEN ARRAY(SELECT jsonb_array_elements_text(vertical_hints))
                        ELSE NULL
                    END,
                    jsonb_build_object(
                        'timing_model', timing_model,
                        'payload_templates', payload_templates,
                        'behavior_model', behavior_model
                    ),
                    true,
                    1.0,
                    1,
                    1.0,
                    created_at,
                    now()
                FROM device_profiles
                WHERE is_builtin = false
                AND id NOT IN (SELECT id FROM device_templates)
            """)
        )

        # 4. Drop device_profiles table
        op.drop_table("device_profiles")


def downgrade() -> None:
    # Recreate device_profiles table
    op.create_table(
        "device_profiles",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False, index=True),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("supported_protocols", JSONB, nullable=True),
        sa.Column("timing_model", JSONB, nullable=True),
        sa.Column("payload_templates", JSONB, nullable=True),
        sa.Column("behavior_model", JSONB, nullable=True),
        sa.Column("vendor_fingerprint", JSONB, nullable=True),
        sa.Column("vertical_hints", JSONB, nullable=True),
        sa.Column("is_builtin", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Revert role column
    op.alter_column(
        "device_templates",
        "role",
        type_=sa.String(20),
        existing_type=sa.String(255),
        existing_nullable=True,
    )

    # Drop new columns
    op.drop_column("device_templates", "palette_config")
    op.drop_column("device_templates", "vertical_hints")
