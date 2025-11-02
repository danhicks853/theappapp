"""create prompts table

Revision ID: 20251103_13
Revises: 20251103_12
Create Date: 2025-11-03

Migration 013: Prompt Versioning System
Purpose: Store versioned prompts for all agent types with semantic versioning
Reference: Section 1.2.4 - Prompt Versioning System
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_13'
down_revision = '20251103_12'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create prompts table."""
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),  # Semantic versioning: major.minor.patch
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('agent_type', 'version', name='uq_prompts_agent_version')
    )
    
    # Create indexes
    op.create_index('idx_prompts_agent_type', 'prompts', ['agent_type'])
    op.create_index('idx_prompts_active', 'prompts', ['agent_type', 'is_active'])
    op.create_index('idx_prompts_created', 'prompts', ['created_at'])


def downgrade() -> None:
    """Drop prompts table."""
    op.drop_index('idx_prompts_created', table_name='prompts')
    op.drop_index('idx_prompts_active', table_name='prompts')
    op.drop_index('idx_prompts_agent_type', table_name='prompts')
    op.drop_table('prompts')
