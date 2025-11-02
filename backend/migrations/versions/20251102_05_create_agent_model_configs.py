"""create agent model configs table

Revision ID: 20251102_05
Revises: 20251102_04
Create Date: 2025-11-02

Migration 005: Agent Model Configurations
Purpose: Per-agent LLM model and temperature configuration
Reference: Section 1.1.2, Migration 005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_05'
down_revision = '20251102_04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent_model_configs table with seed data."""
    op.create_table(
        'agent_model_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_type', sa.String(50), nullable=False, unique=True),
        sa.Column('model', sa.String(50), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='4096'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create index
    op.create_index('idx_agent_model_configs_agent_type', 'agent_model_configs', ['agent_type'], unique=True)
    
    # Seed default configurations for all 10 agent types
    op.execute("""
        INSERT INTO agent_model_configs (agent_type, model, temperature, max_tokens) VALUES
        ('orchestrator', 'gpt-4o-mini', 0.3, 4096),
        ('backend_dev', 'gpt-4o-mini', 0.7, 8192),
        ('frontend_dev', 'gpt-4o-mini', 0.7, 8192),
        ('qa_engineer', 'gpt-4o-mini', 0.5, 4096),
        ('security_expert', 'gpt-4o-mini', 0.3, 4096),
        ('devops_engineer', 'gpt-4o-mini', 0.5, 4096),
        ('documentation_expert', 'gpt-4o-mini', 0.7, 8192),
        ('uiux_designer', 'gpt-4o-mini', 0.8, 8192),
        ('github_specialist', 'gpt-4o-mini', 0.5, 4096),
        ('workshopper', 'gpt-4o-mini', 0.7, 8192),
        ('project_manager', 'gpt-4o-mini', 0.5, 4096)
    """)


def downgrade() -> None:
    """Drop agent_model_configs table."""
    op.drop_index('idx_agent_model_configs_agent_type', table_name='agent_model_configs')
    op.drop_table('agent_model_configs')
