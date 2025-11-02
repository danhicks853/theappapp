"""create token usage table

Revision ID: 20251103_14
Revises: 20251103_13
Create Date: 2025-11-03

Migration 014: LLM Token Usage Tracking
Purpose: Track token usage for cost calculation and monitoring
Reference: Section 1.5.1 - RAG System Architecture (token tracking)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_14'
down_revision = '20251103_13'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create llm_token_usage table."""
    op.create_table(
        'llm_token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', sa.String(100), nullable=True),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # Create indexes
    op.create_index('idx_token_usage_timestamp', 'llm_token_usage', ['timestamp'])
    op.create_index('idx_token_usage_project', 'llm_token_usage', ['project_id'])
    op.create_index('idx_token_usage_agent', 'llm_token_usage', ['agent_id'])
    op.create_index('idx_token_usage_project_agent', 'llm_token_usage', ['project_id', 'agent_id'])
    op.create_index('idx_token_usage_model', 'llm_token_usage', ['model'])


def downgrade() -> None:
    """Drop llm_token_usage table."""
    op.drop_index('idx_token_usage_model', table_name='llm_token_usage')
    op.drop_index('idx_token_usage_project_agent', table_name='llm_token_usage')
    op.drop_index('idx_token_usage_agent', table_name='llm_token_usage')
    op.drop_index('idx_token_usage_project', table_name='llm_token_usage')
    op.drop_index('idx_token_usage_timestamp', table_name='llm_token_usage')
    op.drop_table('llm_token_usage')
