"""create project plans table

Revision ID: 20251103_23
Revises: 20251103_22
Create Date: 2025-11-03

Migration 023: Create project_plans table for MilestoneGenerator
Purpose: Store AI-generated project plans with milestones
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_23'
down_revision = '20251103_22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project_plans table."""
    op.create_table(
        'project_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=False, unique=True),
        sa.Column('project_description', sa.Text, nullable=False),
        sa.Column('total_estimated_days', sa.Integer(), nullable=True),
        sa.Column('complexity_score', sa.Float(), nullable=True),
        sa.Column('generated_at', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', name='uq_project_plans_project_id')
    )
    
    # Create index on project_id for faster lookups
    op.create_index('idx_project_plans_project_id', 'project_plans', ['project_id'])


def downgrade() -> None:
    """Drop project_plans table."""
    op.drop_index('idx_project_plans_project_id', table_name='project_plans')
    op.drop_table('project_plans')
