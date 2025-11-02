"""create knowledge staging table

Revision ID: 20251103_15
Revises: 20251103_14
Create Date: 2025-11-03

Migration 015: RAG Knowledge Staging
Purpose: Staging area for knowledge before embedding to Qdrant
Reference: Section 1.5.1 - RAG System Architecture
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_15'
down_revision = '20251103_14'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create knowledge_staging table."""
    op.create_table(
        'knowledge_staging',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('knowledge_type', sa.String(50), nullable=False),  # 'failure_solution', 'gate_rejection', 'gate_approval', 'collaboration'
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=False),  # {project_id, agent_type, task_type, technology, success_verified}
        sa.Column('embedded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('embedded_at', sa.DateTime(), nullable=True)
    )
    
    # Create indexes
    op.create_index('idx_knowledge_staging_type', 'knowledge_staging', ['knowledge_type'])
    op.create_index('idx_knowledge_staging_embedded', 'knowledge_staging', ['embedded'])
    op.create_index('idx_knowledge_staging_created', 'knowledge_staging', ['created_at'])


def downgrade() -> None:
    """Drop knowledge_staging table."""
    op.drop_index('idx_knowledge_staging_created', table_name='knowledge_staging')
    op.drop_index('idx_knowledge_staging_embedded', table_name='knowledge_staging')
    op.drop_index('idx_knowledge_staging_type', table_name='knowledge_staging')
    op.drop_table('knowledge_staging')
