"""Consolidate VendorFingerprint and LearnedDeviceFingerprint into unified DeviceTemplate.

This migration:
1. Creates the new device_templates table
2. Migrates data from vendor_fingerprints (source=vendor_builtin)
3. Migrates data from learned_device_fingerprints (source=pcap_learned)
4. Preserves foreign key relationships

Note: Original tables are kept for backward compatibility but may be deprecated in future.

Revision ID: 20260122_consolidate_fingerprints
Revises: 20260122_refactor_fingerprints
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_consolidate_fingerprints'
down_revision: Union[str, None] = '20260122_refactor_fingerprints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the unified device_templates table
    op.create_table(
        'device_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Source/Provenance
        sa.Column('source', sa.String(20), nullable=False, index=True,
                  comment='Template source: vendor_builtin, pcap_learned, user_created'),
        sa.Column('source_pcap_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pcap_captures.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='Source PCAP for learned templates'),

        # Vendor identification
        sa.Column('vendor', sa.String(100), nullable=True, index=True,
                  comment='Vendor name'),
        sa.Column('vendor_family', sa.String(100), nullable=True, index=True,
                  comment='Vendor product family'),
        sa.Column('model', sa.String(100), nullable=True,
                  comment='Specific model number'),
        sa.Column('firmware_version', sa.String(50), nullable=True,
                  comment='Firmware version string'),
        sa.Column('device_type', sa.String(100), nullable=True, index=True,
                  comment='Device type/category'),

        # Network signatures
        sa.Column('oui_patterns', postgresql.ARRAY(sa.String(17)), nullable=True,
                  comment='MAC OUI prefixes'),
        sa.Column('tcp_signature', postgresql.JSONB, nullable=True,
                  comment='TCP stack fingerprint'),

        # Protocol identities (unified)
        sa.Column('protocol_identities', postgresql.JSONB, nullable=True,
                  comment='Protocol-specific identities'),

        # Legacy per-protocol columns (backward compatibility)
        sa.Column('modbus_identity', postgresql.JSONB, nullable=True),
        sa.Column('ethernet_ip_identity', postgresql.JSONB, nullable=True),
        sa.Column('profinet_identity', postgresql.JSONB, nullable=True),
        sa.Column('s7_identity', postgresql.JSONB, nullable=True),
        sa.Column('snmp_identity', postgresql.JSONB, nullable=True),
        sa.Column('bacnet_identity', postgresql.JSONB, nullable=True),

        # Timing
        sa.Column('response_timings', postgresql.JSONB, nullable=True,
                  comment='Response timing distributions'),

        # Behavioral patterns
        sa.Column('role', sa.String(20), nullable=True,
                  comment='Device role: master, slave, both, unknown'),
        sa.Column('active_protocols', postgresql.ARRAY(sa.String(50)), nullable=True,
                  comment='Supported protocols'),
        sa.Column('typical_ports', postgresql.JSONB, nullable=True,
                  comment='Typical ports'),
        sa.Column('protocol_quirks', postgresql.JSONB, nullable=True,
                  comment='Protocol-specific quirks'),
        sa.Column('error_behavior', postgresql.JSONB, nullable=True,
                  comment='Error response behavior'),

        # Quality metrics
        sa.Column('confidence', sa.Float, nullable=False, server_default='1.0',
                  comment='Confidence score 0-1'),
        sa.Column('sample_count', sa.Integer, nullable=False, server_default='1',
                  comment='Number of observations'),
        sa.Column('consistency_score', sa.Float, nullable=False, server_default='1.0',
                  comment='Observation consistency'),

        # Metadata
        sa.Column('name', sa.String(200), nullable=True,
                  comment='Human-readable name'),
        sa.Column('description', sa.String(1000), nullable=True,
                  comment='Description'),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=True,
                  comment='User-defined tags'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true',
                  comment='Whether template is active'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Create additional indexes
    op.create_index(
        'ix_device_templates_vendor_model',
        'device_templates',
        ['vendor', 'model'],
    )
    op.create_index(
        'ix_device_templates_source_vendor',
        'device_templates',
        ['source', 'vendor'],
    )

    # Migrate data from vendor_fingerprints
    op.execute("""
        INSERT INTO device_templates (
            id, source, vendor, vendor_family, model, firmware_version,
            oui_patterns, tcp_signature,
            modbus_identity, ethernet_ip_identity, profinet_identity,
            s7_identity, snmp_identity, bacnet_identity,
            response_timings, protocol_quirks, error_behavior,
            confidence, sample_count, is_active,
            created_at, updated_at
        )
        SELECT
            id, 'vendor_builtin', vendor, vendor_family, model, firmware_version,
            oui_prefixes, tcp_stack,
            modbus_identity, ethernet_ip_identity, profinet_identity,
            s7_identity, snmp_identity, bacnet_identity,
            CASE WHEN response_timing IS NOT NULL
                 THEN jsonb_build_object('default', response_timing)
                 ELSE NULL END,
            protocol_quirks, error_behavior,
            1.0, 1, true,
            created_at, updated_at
        FROM vendor_fingerprints
    """)

    # Migrate data from learned_device_fingerprints
    op.execute("""
        INSERT INTO device_templates (
            id, source, source_pcap_id, vendor, device_type,
            oui_patterns, tcp_signature, protocol_identities,
            response_timings, role, active_protocols, typical_ports,
            confidence, sample_count, consistency_score,
            name, tags, is_active,
            created_at, updated_at
        )
        SELECT
            id, 'pcap_learned', pcap_capture_id, inferred_vendor, device_type,
            oui_patterns, tcp_signature, protocol_identities,
            response_timings, role, active_protocols, typical_ports,
            confidence, observation_count, consistency_score,
            name, tags, true,
            created_at, updated_at
        FROM learned_device_fingerprints
    """)


def downgrade() -> None:
    # Drop the unified table
    op.drop_index('ix_device_templates_source_vendor', table_name='device_templates')
    op.drop_index('ix_device_templates_vendor_model', table_name='device_templates')
    op.drop_table('device_templates')
