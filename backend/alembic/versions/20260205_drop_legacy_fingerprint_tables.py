"""Drop legacy fingerprint tables.

The vendor_fingerprints and learned_device_fingerprints tables are no longer
used. All fingerprint data now lives in the device_templates table.

- vendor_fingerprints: Was seeded from Python data, replaced by device_templates
- learned_device_fingerprints: Replaced by DeviceTemplate(source="pcap_learned")

Revision ID: drop_legacy_fp_tables
Revises: add_opc_ua_identity
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'drop_legacy_fp_tables'
down_revision = 'add_opc_ua_identity'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop legacy fingerprint tables."""
    # Drop foreign key from vulnerable_fingerprint_variants first
    op.drop_constraint(
        'vulnerable_fingerprint_variants_vendor_fingerprint_id_fkey',
        'vulnerable_fingerprint_variants',
        type_='foreignkey',
    )
    op.drop_column('vulnerable_fingerprint_variants', 'vendor_fingerprint_id')

    # Drop the tables
    op.drop_table('learned_device_fingerprints')
    op.drop_table('vendor_fingerprints')


def downgrade() -> None:
    """Recreate legacy fingerprint tables for rollback."""
    # Recreate vendor_fingerprints table
    op.create_table(
        'vendor_fingerprints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vendor', sa.String(100), nullable=False),
        sa.Column('model', sa.String(200), nullable=False),
        sa.Column('device_type', sa.String(100)),
        sa.Column('firmware_version', sa.String(100)),
        sa.Column('oui_prefixes', postgresql.JSONB),
        sa.Column('tcp_stack', postgresql.JSONB),
        sa.Column('response_timing', postgresql.JSONB),
        sa.Column('error_behavior', postgresql.JSONB),
        sa.Column('protocol_quirks', postgresql.JSONB),
        sa.Column('modbus_identity', postgresql.JSONB),
        sa.Column('ethernet_ip_identity', postgresql.JSONB),
        sa.Column('profinet_identity', postgresql.JSONB),
        sa.Column('s7_identity', postgresql.JSONB),
        sa.Column('bacnet_identity', postgresql.JSONB),
        sa.Column('snmp_identity', postgresql.JSONB),
        sa.Column('is_builtin', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Recreate learned_device_fingerprints table
    op.create_table(
        'learned_device_fingerprints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pcap_capture_id', postgresql.UUID(as_uuid=True)),
        sa.Column('source_mac', sa.String(17)),
        sa.Column('source_ip', sa.String(45)),
        sa.Column('inferred_vendor', sa.String(200)),
        sa.Column('device_type', sa.String(100)),
        sa.Column('role', sa.String(20)),
        sa.Column('active_protocols', postgresql.JSONB),
        sa.Column('oui_patterns', postgresql.JSONB),
        sa.Column('tcp_signature', postgresql.JSONB),
        sa.Column('response_timings', postgresql.JSONB),
        sa.Column('observation_count', sa.Integer, default=0),
        sa.Column('confidence', sa.Float, default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Re-add the foreign key column
    op.add_column(
        'vulnerable_fingerprint_variants',
        sa.Column('vendor_fingerprint_id', postgresql.UUID(as_uuid=True)),
    )
    op.create_foreign_key(
        'vulnerable_fingerprint_variants_vendor_fingerprint_id_fkey',
        'vulnerable_fingerprint_variants',
        'vendor_fingerprints',
        ['vendor_fingerprint_id'],
        ['id'],
        ondelete='SET NULL',
    )
