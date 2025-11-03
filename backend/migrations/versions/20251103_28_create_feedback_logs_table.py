"""create feedback logs table

Revision ID: 20251103_28
Revises: 20251103_27
Create Date: 2025-11-03

Migration 028: Create feedback_logs table for FeedbackCollector
Purpose: Store user/agent feedback on gates and decisions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_28'
down_revision = '20251103_27'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create feedback_logs table."""
    op.create_table(
        'feedback_logs',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('gate_id', sa.String(100), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False),
        sa.Column('feedback_text', sa.Text, nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_feedback_logs_gate_id', 'feedback_logs', ['gate_id'])
    op.create_index('idx_feedback_logs_feedback_type', 'feedback_logs', ['feedback_type'])
    op.create_index('idx_feedback_logs_agent_type', 'feedback_logs', ['agent_type'])


def downgrade() -> None:
    """Drop feedback_logs table."""
    op.drop_index('idx_feedback_logs_agent_type', table_name='feedback_logs')
    op.drop_index('idx_feedback_logs_feedback_type', table_name='feedback_logs')
    op.drop_index('idx_feedback_logs_gate_id', table_name='feedback_logs')
    op.drop_table('feedback_logs')
