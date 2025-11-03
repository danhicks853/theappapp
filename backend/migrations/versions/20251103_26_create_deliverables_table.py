"""create deliverables table

Revision ID: 20251103_26
Revises: 20251103_25
Create Date: 2025-11-03

Migration 026: Create deliverables table for DeliverableTracker
Purpose: Track project deliverables per phase
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_26'
down_revision = '20251103_25'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create deliverables table."""
    op.create_table(
        'deliverables',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('milestone_id', sa.String(100), nullable=True),
        sa.Column('phase_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('deliverable_type', sa.String(50), nullable=False),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='not_started'),
        sa.Column('artifact_path', sa.String(500), nullable=True),
        sa.Column('validation_result', postgresql.JSONB, nullable=True),
        sa.Column('dependencies', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_deliverables_project_id', 'deliverables', ['project_id'])
    op.create_index('idx_deliverables_milestone_id', 'deliverables', ['milestone_id'])
    op.create_index('idx_deliverables_phase_id', 'deliverables', ['phase_id'])
    op.create_index('idx_deliverables_status', 'deliverables', ['status'])


def downgrade() -> None:
    """Drop deliverables table."""
    op.drop_index('idx_deliverables_status', table_name='deliverables')
    op.drop_index('idx_deliverables_phase_id', table_name='deliverables')
    op.drop_index('idx_deliverables_milestone_id', table_name='deliverables')
    op.drop_index('idx_deliverables_project_id', table_name='deliverables')
    op.drop_table('deliverables')
