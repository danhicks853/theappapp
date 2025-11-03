"""create phases table

Revision ID: 20251103_25
Revises: 20251103_24
Create Date: 2025-11-03

Migration 025: Create phases table for PhaseManager
Purpose: Track project phases (workshopping, implementation, testing, etc.)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_25'
down_revision = '20251103_24'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create phases table."""
    op.create_table(
        'phases',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('phase_name', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('assigned_agents', postgresql.JSONB, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_phases_project_id', 'phases', ['project_id'])
    op.create_index('idx_phases_status', 'phases', ['status'])
    op.create_index('idx_phases_phase_name', 'phases', ['phase_name'])


def downgrade() -> None:
    """Drop phases table."""
    op.drop_index('idx_phases_phase_name', table_name='phases')
    op.drop_index('idx_phases_status', table_name='phases')
    op.drop_index('idx_phases_project_id', table_name='phases')
    op.drop_table('phases')
