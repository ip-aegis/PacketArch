"""Drop PCAP learning pipeline tables.

Merges two migration branches and removes all tables/types related to
the PCAP learning feature:
- pcap_captures
- learned_patterns
- learned_protocol_patterns
- learned_sequences
- learning_sessions
- source_pcap_id FK from device_templates
- processingstatus and sessionstatus enum types

Revision ID: drop_learning_pipeline
Revises: 20260127_cloud_services, add_scenario_versions
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "drop_learning_pipeline"
down_revision = ("20260127_cloud_services", "add_scenario_versions")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Drop source_pcap_id FK and column from device_templates
    op.drop_index("ix_device_templates_source_pcap_id", table_name="device_templates")
    op.drop_constraint(
        "device_templates_source_pcap_id_fkey",
        "device_templates",
        type_="foreignkey",
    )
    op.drop_column("device_templates", "source_pcap_id")

    # Step 2: Drop legacy learned_device_fingerprints FK to pcap_captures
    # (this table was supposed to be dropped in drop_legacy_fp_tables but
    # that migration may not have run; handle gracefully)
    op.execute("""
        ALTER TABLE IF EXISTS learned_device_fingerprints
        DROP CONSTRAINT IF EXISTS learned_device_fingerprints_pcap_capture_id_fkey
    """)

    # Step 3: Drop tables in FK-safe order (children first)
    # learned_protocol_patterns -> pcap_captures
    op.drop_table("learned_protocol_patterns")
    # learned_sequences -> pcap_captures
    op.drop_table("learned_sequences")
    # learned_patterns -> pcap_captures
    op.drop_table("learned_patterns")
    # pcap_captures -> learning_sessions
    op.drop_table("pcap_captures")
    # learning_sessions (no FK dependencies)
    op.drop_table("learning_sessions")

    # Step 4: Drop legacy tables that were already replaced by device_templates
    op.execute("DROP TABLE IF EXISTS learned_device_fingerprints CASCADE")
    op.execute("DROP TABLE IF EXISTS vendor_fingerprints CASCADE")
    op.execute("DROP TABLE IF EXISTS vulnerable_fingerprint_variants CASCADE")

    # Step 3: Drop enum types
    op.execute("DROP TYPE IF EXISTS processingstatus")
    op.execute("DROP TYPE IF EXISTS sessionstatus")


def downgrade() -> None:
    # Recreate enum types
    op.execute(
        "CREATE TYPE processingstatus AS ENUM "
        "('pending', 'processing', 'completed', 'failed')"
    )
    op.execute(
        "CREATE TYPE sessionstatus AS ENUM "
        "('active', 'completed', 'archived')"
    )

    # Recreate learning_sessions
    op.create_table(
        "learning_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "status",
            sa.Enum(
                "active", "completed", "archived",
                name="sessionstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_learning_sessions_status", "learning_sessions", ["status"])

    # Recreate pcap_captures
    op.create_table(
        "pcap_captures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500)),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("file_size", sa.BigInteger()),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("packet_count", sa.Integer()),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("protocols_detected", JSONB, server_default="[]"),
        sa.Column("device_count", sa.Integer()),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="processingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text()),
        sa.Column("analysis_result", JSONB),
        sa.Column(
            "learning_session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_pcap_captures_status", "pcap_captures", ["status"])
    op.create_index(
        "ix_pcap_captures_learning_session_id",
        "pcap_captures",
        ["learning_session_id"],
    )

    # Recreate learned_patterns
    op.create_table(
        "learned_patterns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pcap_capture_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pcap_captures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pattern_type", sa.String(50), nullable=False),
        sa.Column("protocol", sa.String(50)),
        sa.Column("source_ip", sa.String(50)),
        sa.Column("destination_ip", sa.String(50)),
        sa.Column("source_port", sa.Integer()),
        sa.Column("destination_port", sa.Integer()),
        sa.Column("pattern_data", JSONB, nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("sample_count", sa.Integer()),
        sa.Column("is_promoted", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_learned_patterns_pattern_type", "learned_patterns", ["pattern_type"])

    # Recreate learned_protocol_patterns
    op.create_table(
        "learned_protocol_patterns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pcap_capture_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pcap_captures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("protocol", sa.String(50), nullable=False),
        sa.Column("pattern_name", sa.String(200), nullable=False),
        sa.Column("pattern_data", JSONB, nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("sample_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Recreate learned_sequences
    op.create_table(
        "learned_sequences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pcap_capture_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pcap_captures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_type", sa.String(50), nullable=False),
        sa.Column("protocol", sa.String(50)),
        sa.Column("sequence_data", JSONB, nullable=False),
        sa.Column("step_count", sa.Integer()),
        sa.Column("confidence", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Restore source_pcap_id on device_templates
    op.add_column(
        "device_templates",
        sa.Column(
            "source_pcap_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pcap_captures.id", ondelete="SET NULL"),
        ),
    )
    op.create_index(
        "ix_device_templates_source_pcap_id",
        "device_templates",
        ["source_pcap_id"],
    )
