"""create project specialists M2M table

Revision ID: 20251102_07
Revises: 20251102_06
Create Date: 2025-11-02

Migration 007: Project Specialists (Many-to-Many)
Purpose: Link specialists to projects (immutable after project creation)
Reference: MVP Demo Plan - Project specialist binding
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_07'
down_revision = '20251102_06'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project_specialists M2M table."""
    op.create_table(
        'project_specialists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('specialist_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create indexes
    op.create_index('idx_project_specialists_project', 'project_specialists', ['project_id'])
    op.create_index('idx_project_specialists_specialist', 'project_specialists', ['specialist_id'])
    
    # Unique constraint: Same specialist can't be added to project twice
    op.create_unique_constraint(
        'uq_project_specialist',
        'project_specialists',
        ['project_id', 'specialist_id']
    )


def downgrade() -> None:
    """Drop project_specialists table."""
    op.drop_constraint('uq_project_specialist', 'project_specialists')
    op.drop_index('idx_project_specialists_specialist', table_name='project_specialists')
    op.drop_index('idx_project_specialists_project', table_name='project_specialists')
    op.drop_table('project_specialists')
