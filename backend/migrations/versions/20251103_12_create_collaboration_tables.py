"""create collaboration tables

Revision ID: 20251103_12
Revises: 20251103_11
Create Date: 2025-11-03

Migration 012: Agent Collaboration Tracking
Purpose: Track agent-to-agent collaboration requests and outcomes
Reference: Section 1.3.1 - Agent Collaboration Protocol
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_12'
down_revision = '20251103_11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create collaboration tables."""
    
    # Collaboration requests table
    op.create_table(
        'collaboration_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('collaboration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),  # 'model_data', 'security_review', 'api_clarification', etc.
        sa.Column('requesting_agent', sa.String(50), nullable=False),
        sa.Column('specialist_agent', sa.String(50), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(), nullable=False),
        sa.Column('urgency', sa.String(20), nullable=False, server_default='medium'),  # 'low', 'medium', 'high'
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    
    op.create_index('idx_collab_requests_collab_id', 'collaboration_requests', ['collaboration_id'])
    op.create_index('idx_collab_requests_requesting', 'collaboration_requests', ['requesting_agent'])
    op.create_index('idx_collab_requests_specialist', 'collaboration_requests', ['specialist_agent'])
    
    # Collaboration outcomes table
    op.create_table(
        'collaboration_outcomes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('collaboration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('specialist_agent', sa.String(50), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    
    op.create_index('idx_collab_outcomes_collab_id', 'collaboration_outcomes', ['collaboration_id'])
    op.create_index('idx_collab_outcomes_specialist', 'collaboration_outcomes', ['specialist_agent'])


def downgrade() -> None:
    """Drop collaboration tables."""
    op.drop_index('idx_collab_outcomes_specialist', table_name='collaboration_outcomes')
    op.drop_index('idx_collab_outcomes_collab_id', table_name='collaboration_outcomes')
    op.drop_table('collaboration_outcomes')
    
    op.drop_index('idx_collab_requests_specialist', table_name='collaboration_requests')
    op.drop_index('idx_collab_requests_requesting', table_name='collaboration_requests')
    op.drop_index('idx_collab_requests_collab_id', table_name='collaboration_requests')
    op.drop_table('collaboration_requests')
