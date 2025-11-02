"""create api keys table

Revision ID: 20251102_04
Revises: 20251101_03
Create Date: 2025-11-02

Migration 004: API Keys Configuration Table
Purpose: Store encrypted API keys for external services (OpenAI, etc.)
Reference: Section 1.1.2, Migration 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_04'
down_revision = '20251101_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create api_keys table for storing encrypted API keys."""
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('service', sa.String(50), nullable=False, unique=True),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create indexes
    op.create_index('idx_api_keys_service', 'api_keys', ['service'], unique=True)
    op.create_index('idx_api_keys_active', 'api_keys', ['is_active'])


def downgrade() -> None:
    """Drop api_keys table."""
    op.drop_index('idx_api_keys_active', table_name='api_keys')
    op.drop_index('idx_api_keys_service', table_name='api_keys')
    op.drop_table('api_keys')
