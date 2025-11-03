"""create phase transitions table

Revision ID: 20251103_29
Revises: 20251103_28
Create Date: 2025-11-03

Migration 029: Create phase_transitions table for PhaseTransitionService
Purpose: Track phase transitions with handoff reports
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_29'
down_revision = '20251103_28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create phase_transitions table."""
    op.create_table(
        'phase_transitions',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('from_phase', sa.String(50), nullable=False),
        sa.Column('to_phase', sa.String(50), nullable=False),
        sa.Column('completed_deliverables', postgresql.JSONB, nullable=True),
        sa.Column('achievements', postgresql.JSONB, nullable=True),
        sa.Column('next_steps', postgresql.JSONB, nullable=True),
        sa.Column('new_agents', sa.Text, nullable=True),
        sa.Column('archived_artifacts', sa.Text, nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('transition_time', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_phase_transitions_project_id', 'phase_transitions', ['project_id'])
    op.create_index('idx_phase_transitions_from_phase', 'phase_transitions', ['from_phase'])
    op.create_index('idx_phase_transitions_to_phase', 'phase_transitions', ['to_phase'])


def downgrade() -> None:
    """Drop phase_transitions table."""
    op.drop_index('idx_phase_transitions_to_phase', table_name='phase_transitions')
    op.drop_index('idx_phase_transitions_from_phase', table_name='phase_transitions')
    op.drop_index('idx_phase_transitions_project_id', table_name='phase_transitions')
    op.drop_table('phase_transitions')
