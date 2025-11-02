"""create gates table

Revision ID: 20251103_11
Revises: 20251102_10
Create Date: 2025-11-03

Migration 011: Human Approval Gates
Purpose: Store human-in-the-loop approval gates for agent escalations
Reference: Section 1.3 - Decision-Making & Escalation System
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_11'
down_revision = '20251102_10'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create gates table."""
    op.create_table(
        'gates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(100), nullable=False),
        sa.Column('gate_type', sa.String(50), nullable=False),  # 'loop_detected', 'high_risk', 'collaboration_deadlock', 'manual'
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # 'pending', 'approved', 'denied'
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(100), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True)
    )
    
    # Create indexes
    op.create_index('idx_gates_project', 'gates', ['project_id'])
    op.create_index('idx_gates_status', 'gates', ['status'])
    op.create_index('idx_gates_agent', 'gates', ['agent_id'])
    op.create_index('idx_gates_created', 'gates', ['created_at'])


def downgrade() -> None:
    """Drop gates table."""
    op.drop_index('idx_gates_created', table_name='gates')
    op.drop_index('idx_gates_agent', table_name='gates')
    op.drop_index('idx_gates_status', table_name='gates')
    op.drop_index('idx_gates_project', table_name='gates')
    op.drop_table('gates')
