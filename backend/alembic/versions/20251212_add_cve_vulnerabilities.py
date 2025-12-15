"""Add CVE vulnerability tracking tables.

Revision ID: add_cve_vulnerabilities
Revises: add_enhanced_learning
Create Date: 2024-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_cve_vulnerabilities'
down_revision = 'add_enhanced_learning'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create CVE vulnerability and vulnerable fingerprint variant tables."""

    # Create cve_severity enum
    cve_severity = postgresql.ENUM(
        'critical', 'high', 'medium', 'low',
        name='cveseverity',
        create_type=False,
    )
    cve_severity.create(op.get_bind(), checkfirst=True)

    # Create cve_vulnerabilities table
    op.create_table(
        'cve_vulnerabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cve_id', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'severity',
            postgresql.ENUM('critical', 'high', 'medium', 'low', name='cveseverity', create_type=False),
            nullable=False,
            server_default='medium',
        ),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('cvss_vector', sa.String(100), nullable=True),
        sa.Column('vendor', sa.String(100), nullable=False, index=True),
        sa.Column('product_family', sa.String(100), nullable=False, index=True),
        sa.Column('affected_models', postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column('affected_firmware_min', sa.String(50), nullable=True),
        sa.Column('affected_firmware_max', sa.String(50), nullable=False),
        sa.Column('fixed_firmware_version', sa.String(50), nullable=True),
        sa.Column('cyber_vision_detectable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('detection_method', sa.String(100), nullable=True),
        sa.Column('advisory_url', sa.String(500), nullable=True),
        sa.Column('references', postgresql.JSONB(), nullable=True),
        sa.Column('mitre_techniques', postgresql.ARRAY(sa.String(20)), nullable=True),
        sa.Column('exploit_available', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('exploit_complexity', sa.String(20), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('published_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for cve_vulnerabilities
    op.create_index('ix_cve_vulnerabilities_severity', 'cve_vulnerabilities', ['severity'])

    # Create vulnerable_fingerprint_variants table
    op.create_table(
        'vulnerable_fingerprint_variants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'cve_vulnerability_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('cve_vulnerabilities.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'base_fingerprint_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('vendor_fingerprints.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('firmware_version', sa.String(50), nullable=False),
        sa.Column('modbus_identity_override', postgresql.JSONB(), nullable=True),
        sa.Column('ethernet_ip_identity_override', postgresql.JSONB(), nullable=True),
        sa.Column('profinet_identity_override', postgresql.JSONB(), nullable=True),
        sa.Column('s7_identity_override', postgresql.JSONB(), nullable=True),
        sa.Column('full_modbus_mei_template', postgresql.JSONB(), nullable=True),
        sa.Column('full_enip_identity_template', postgresql.JSONB(), nullable=True),
        sa.Column('target_vendor', sa.String(100), nullable=False, index=True),
        sa.Column('target_product_family', sa.String(100), nullable=True),
        sa.Column('target_models', postgresql.JSONB(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop CVE vulnerability tables."""
    op.drop_table('vulnerable_fingerprint_variants')
    op.drop_table('cve_vulnerabilities')

    # Drop enum
    op.execute('DROP TYPE IF EXISTS cveseverity')
