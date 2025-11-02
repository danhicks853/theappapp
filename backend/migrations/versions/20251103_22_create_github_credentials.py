"""Create github_credentials table

Revision ID: 20251103_22
Revises: 20251103_21
Create Date: 2025-11-03

Creates table for storing encrypted GitHub OAuth credentials.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251103_22'
down_revision = '20251103_21'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create github_credentials table
    op.create_table(
        'github_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('github_username', sa.String(length=255), nullable=True),
        sa.Column('github_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_github_credentials_user_id')
    )
    
    # Create indexes
    op.create_index('idx_github_credentials_user_id', 'github_credentials', ['user_id'])
    op.create_index('idx_github_credentials_github_user_id', 'github_credentials', ['github_user_id'])


def downgrade() -> None:
    # Drop github_credentials table
    op.drop_index('idx_github_credentials_github_user_id', table_name='github_credentials')
    op.drop_index('idx_github_credentials_user_id', table_name='github_credentials')
    op.drop_table('github_credentials')
