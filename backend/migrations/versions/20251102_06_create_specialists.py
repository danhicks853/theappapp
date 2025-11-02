"""create specialists table

Revision ID: 20251102_06
Revises: 20251102_05
Create Date: 2025-11-02

Migration 006: Specialists (Custom Agents)
Purpose: Store user-created specialist configurations
Reference: MVP Demo Plan - Specialist creation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_06'
down_revision = '20251102_05'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create specialists table."""
    op.create_table(
        'specialists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('scope', sa.String(20), nullable=False, server_default='global'),  # 'global' or 'project'
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),  # Only if scope=project
        sa.Column('web_search_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('web_search_config', postgresql.JSONB(), nullable=True),  # {scope, engines, max_results}
        sa.Column('tools_enabled', postgresql.JSONB(), nullable=True),  # {read_files, execute_code, etc.}
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create indexes
    op.create_index('idx_specialists_scope', 'specialists', ['scope'])
    op.create_index('idx_specialists_project', 'specialists', ['project_id'])


def downgrade() -> None:
    """Drop specialists table."""
    op.drop_index('idx_specialists_project', table_name='specialists')
    op.drop_index('idx_specialists_scope', table_name='specialists')
    op.drop_table('specialists')
