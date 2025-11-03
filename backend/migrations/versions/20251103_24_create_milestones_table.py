"""create milestones table

Revision ID: 20251103_24
Revises: 20251103_23
Create Date: 2025-11-03

Migration 024: Create milestones table for MilestoneGenerator
Purpose: Store project milestones with tasks and deliverables
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251103_24'
down_revision = '20251103_23'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create milestones table."""
    op.create_table(
        'milestones',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('phase_name', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tasks', sa.Text, nullable=True),  # JSON as text
        sa.Column('estimated_days', sa.Integer(), nullable=True),
        sa.Column('dependencies', sa.Text, nullable=True),  # JSON as text
        sa.Column('deliverables', sa.Text, nullable=True),  # JSON as text
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_milestones_project_id', 'milestones', ['project_id'])
    op.create_index('idx_milestones_phase_name', 'milestones', ['phase_name'])


def downgrade() -> None:
    """Drop milestones table."""
    op.drop_index('idx_milestones_phase_name', table_name='milestones')
    op.drop_index('idx_milestones_project_id', table_name='milestones')
    op.drop_table('milestones')
