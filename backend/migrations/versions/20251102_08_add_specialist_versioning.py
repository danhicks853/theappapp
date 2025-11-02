"""add specialist versioning and personality fields

Revision ID: 20251102_08
Revises: 20251102_07
Create Date: 2025-11-02 23:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251102_08'
down_revision = '20251102_07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add versioning and personality fields
    op.add_column('specialists', sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'))
    op.add_column('specialists', sa.Column('template_id', sa.String(100), nullable=True))
    op.add_column('specialists', sa.Column('installed_from_store', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('specialists', sa.Column('store_latest_version', sa.String(20), nullable=True))
    op.add_column('specialists', sa.Column('update_available', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add personality fields
    op.add_column('specialists', sa.Column('display_name', sa.String(100), nullable=True))
    op.add_column('specialists', sa.Column('avatar', sa.String(200), nullable=True))
    op.add_column('specialists', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('specialists', sa.Column('interests', postgresql.JSONB(), nullable=True))
    op.add_column('specialists', sa.Column('favorite_tool', sa.String(100), nullable=True))
    op.add_column('specialists', sa.Column('quote', sa.Text(), nullable=True))
    
    # Add index on template_id for faster lookups
    op.create_index('ix_specialists_template_id', 'specialists', ['template_id'])


def downgrade() -> None:
    op.drop_index('ix_specialists_template_id')
    
    op.drop_column('specialists', 'quote')
    op.drop_column('specialists', 'favorite_tool')
    op.drop_column('specialists', 'interests')
    op.drop_column('specialists', 'bio')
    op.drop_column('specialists', 'avatar')
    op.drop_column('specialists', 'display_name')
    
    op.drop_column('specialists', 'update_available')
    op.drop_column('specialists', 'store_latest_version')
    op.drop_column('specialists', 'installed_from_store')
    op.drop_column('specialists', 'template_id')
    op.drop_column('specialists', 'version')
