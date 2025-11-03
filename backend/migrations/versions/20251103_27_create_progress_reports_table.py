"""create progress reports table

Revision ID: 20251103_27
Revises: 20251103_26
Create Date: 2025-11-03

Migration 027: Create progress_reports table for ProgressReporter
Purpose: Store AI-generated progress reports
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_27'
down_revision = '20251103_26'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create progress_reports table."""
    op.create_table(
        'progress_reports',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('completed_tasks', postgresql.JSONB, nullable=True),
        sa.Column('pending_tasks', postgresql.JSONB, nullable=True),
        sa.Column('blockers', postgresql.JSONB, nullable=True),
        sa.Column('test_coverage', sa.Float(), nullable=True),
        sa.Column('next_steps', postgresql.JSONB, nullable=True),
        sa.Column('timeline_status', sa.String(50), nullable=True),
        sa.Column('generated_at', sa.String(50), nullable=True),
        sa.Column('period_start', sa.String(50), nullable=True),
        sa.Column('period_end', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_progress_reports_project_id', 'progress_reports', ['project_id'])
    op.create_index('idx_progress_reports_report_type', 'progress_reports', ['report_type'])
    op.create_index('idx_progress_reports_generated_at', 'progress_reports', ['generated_at'])


def downgrade() -> None:
    """Drop progress_reports table."""
    op.drop_index('idx_progress_reports_generated_at', table_name='progress_reports')
    op.drop_index('idx_progress_reports_report_type', table_name='progress_reports')
    op.drop_index('idx_progress_reports_project_id', table_name='progress_reports')
    op.drop_table('progress_reports')
