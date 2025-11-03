"""create collaboration supporting tables

Revision ID: 20251103_30
Revises: 20251103_29
Create Date: 2025-11-03

Migration 030: Create collaboration_exchanges, collaboration_responses, collaboration_loops tables
Purpose: Support full collaboration tracking system
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251103_30'
down_revision = '20251103_29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create collaboration supporting tables."""
    
    # 1. collaboration_exchanges - message history
    op.create_table(
        'collaboration_exchanges',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('collaboration_id', sa.String(100), nullable=False),
        sa.Column('from_agent_id', sa.String(100), nullable=False),
        sa.Column('to_agent_id', sa.String(100), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collab_exchanges_collab_id', 'collaboration_exchanges', ['collaboration_id'])
    op.create_index('idx_collab_exchanges_from_agent', 'collaboration_exchanges', ['from_agent_id'])
    op.create_index('idx_collab_exchanges_to_agent', 'collaboration_exchanges', ['to_agent_id'])
    
    # 2. collaboration_responses - specialist responses
    op.create_table(
        'collaboration_responses',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('collaboration_id', sa.String(100), nullable=False),
        sa.Column('responding_specialist_id', sa.String(100), nullable=False),
        sa.Column('responding_specialist_type', sa.String(50), nullable=False),
        sa.Column('response', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collab_responses_collab_id', 'collaboration_responses', ['collaboration_id'])
    op.create_index('idx_collab_responses_specialist_id', 'collaboration_responses', ['responding_specialist_id'])
    
    # 3. collaboration_loops - detected loops
    op.create_table(
        'collaboration_loops',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('agent_a_id', sa.String(100), nullable=False),
        sa.Column('agent_b_id', sa.String(100), nullable=False),
        sa.Column('topic_similarity', sa.Float(), nullable=True),
        sa.Column('cycle_count', sa.Integer(), nullable=False),
        sa.Column('questions', sa.Text, nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('gate_created', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collab_loops_agent_a', 'collaboration_loops', ['agent_a_id'])
    op.create_index('idx_collab_loops_agent_b', 'collaboration_loops', ['agent_b_id'])
    op.create_index('idx_collab_loops_detected_at', 'collaboration_loops', ['detected_at'])


def downgrade() -> None:
    """Drop collaboration supporting tables."""
    # Drop collaboration_loops
    op.drop_index('idx_collab_loops_detected_at', table_name='collaboration_loops')
    op.drop_index('idx_collab_loops_agent_b', table_name='collaboration_loops')
    op.drop_index('idx_collab_loops_agent_a', table_name='collaboration_loops')
    op.drop_table('collaboration_loops')
    
    # Drop collaboration_responses
    op.drop_index('idx_collab_responses_specialist_id', table_name='collaboration_responses')
    op.drop_index('idx_collab_responses_collab_id', table_name='collaboration_responses')
    op.drop_table('collaboration_responses')
    
    # Drop collaboration_exchanges
    op.drop_index('idx_collab_exchanges_to_agent', table_name='collaboration_exchanges')
    op.drop_index('idx_collab_exchanges_from_agent', table_name='collaboration_exchanges')
    op.drop_index('idx_collab_exchanges_collab_id', table_name='collaboration_exchanges')
    op.drop_table('collaboration_exchanges')
