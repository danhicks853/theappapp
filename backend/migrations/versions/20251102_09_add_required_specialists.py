"""add required flag and seed core specialists

Revision ID: 20251102_09
Revises: 20251102_08
Create Date: 2025-11-02 00:27:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_09'
down_revision = '20251102_08'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns from original table
    op.add_column('specialists', sa.Column('status', sa.String(20), nullable=False, server_default='active'))
    op.add_column('specialists', sa.Column('tags', postgresql.JSONB(), nullable=True))
    op.add_column('specialists', sa.Column('model', sa.String(50), nullable=False, server_default='gpt-4'))
    op.add_column('specialists', sa.Column('temperature', sa.Numeric(3, 2), nullable=False, server_default='0.7'))
    op.add_column('specialists', sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='4000'))
    
    # Add required column
    op.add_column('specialists', sa.Column('required', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create index for required specialists
    op.create_index('ix_specialists_required', 'specialists', ['required'])
    
    # NOTE: Built-in agents are NOT seeded here
    # Built-in agents (orchestrator, backend_dev, frontend_dev, etc.) are system-level
    # and managed via the prompts table with versioning (see migration 013)
    # 
    # This table is ONLY for user-created custom specialists
    # No seed data needed - users will create their own specialists via the App Store


def downgrade() -> None:
    # Remove seeded specialists
    op.execute("DELETE FROM specialists WHERE required = true OR name IN ('data_scientist', 'devops_engineer', 'qa_engineer', 'security_specialist', 'ux_designer')")
    
    # Drop index and column
    op.drop_index('ix_specialists_required')
    op.drop_column('specialists', 'required')
    
    # Drop other added columns
    op.drop_column('specialists', 'max_tokens')
    op.drop_column('specialists', 'temperature')
    op.drop_column('specialists', 'model')
    op.drop_column('specialists', 'tags')
    op.drop_column('specialists', 'status')
