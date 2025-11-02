"""create llm pricing table

Revision ID: 20251103_16
Revises: 20251103_15
Create Date: 2025-11-03

Migration 016: LLM Pricing Table
Purpose: Store pricing information for LLM models for cost calculation
Reference: Section 1.1.2 - Database Schema Initialization
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_16'
down_revision = '20251103_15'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create llm_pricing table."""
    op.create_table(
        'llm_pricing',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('model', sa.String(50), unique=True, nullable=False),
        sa.Column('input_cost_per_million', sa.Numeric(10, 2), nullable=False),
        sa.Column('output_cost_per_million', sa.Numeric(10, 2), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),  # 'active', 'deprecated'
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_by', sa.String(100), nullable=True)
    )
    
    # Create indexes
    op.create_index('idx_llm_pricing_model', 'llm_pricing', ['model'], unique=True)
    op.create_index('idx_llm_pricing_status', 'llm_pricing', ['status'])
    
    # Seed pricing data (as of November 2025)
    op.execute("""
        INSERT INTO llm_pricing (model, input_cost_per_million, output_cost_per_million, status, notes) VALUES
        ('gpt-4.1', 2.00, 8.00, 'active', 'GPT-4.1 base model - Standard tier'),
        ('gpt-4.1-mini', 0.40, 1.60, 'active', 'GPT-4.1 Mini - Standard tier'),
        ('gpt-4o', 2.50, 10.00, 'active', 'GPT-4o optimized - Standard tier'),
        ('gpt-4o-mini', 0.15, 0.60, 'active', 'GPT-4o Mini - Standard tier'),
        ('gpt-5', 1.25, 10.00, 'active', 'GPT-5 base model - Standard tier'),
        ('gpt-5-mini', 0.25, 2.00, 'active', 'GPT-5 Mini - Standard tier'),
        ('gpt-5-nano', 0.05, 0.40, 'active', 'GPT-5 Nano - Standard tier'),
        ('text-embedding-3-large', 0.13, 0.00, 'active', 'Text embeddings large'),
        ('text-embedding-3-small', 0.02, 0.00, 'active', 'Text embeddings small'),
        ('gpt-4-turbo', 10.00, 30.00, 'active', 'GPT-4 Turbo - Legacy pricing'),
        ('gpt-3.5-turbo', 0.50, 1.50, 'active', 'GPT-3.5 Turbo - Legacy pricing')
    """)


def downgrade() -> None:
    """Drop llm_pricing table."""
    op.drop_index('idx_llm_pricing_status', table_name='llm_pricing')
    op.drop_index('idx_llm_pricing_model', table_name='llm_pricing')
    op.drop_table('llm_pricing')
