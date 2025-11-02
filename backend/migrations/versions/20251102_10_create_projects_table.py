"""create projects table

Revision ID: 20251102_10
Revises: 20251102_09
Create Date: 2025-11-02 01:39:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_10'
down_revision = '20251102_09'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create projects table."""
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Create index on status for faster filtering
    op.create_index('ix_projects_status', 'projects', ['status'])


def downgrade() -> None:
    """Drop projects table."""
    op.drop_index('ix_projects_status')
    op.drop_table('projects')
