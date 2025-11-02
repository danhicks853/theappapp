"""Create tool access tables

Revision ID: 20251103_20
Revises: 20251103_19
Create Date: 2025-11-03

Creates tables for Tool Access Service (TAS):
- agent_tool_permissions: Permission matrix for agent types
- tool_audit_logs: Comprehensive audit trail with 1-year retention
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251103_20'
down_revision = '20251103_19'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agent_tool_permissions table
    op.create_table(
        'agent_tool_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('allowed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_type', 'tool_name', 'operation', name='uq_agent_tool_operation')
    )
    
    # Create indexes for fast permission lookups
    op.create_index('idx_agent_tool_permissions_agent_type', 'agent_tool_permissions', ['agent_type'])
    op.create_index('idx_agent_tool_permissions_tool_name', 'agent_tool_permissions', ['tool_name'])
    op.create_index('idx_agent_tool_permissions_lookup', 'agent_tool_permissions', ['agent_type', 'tool_name', 'operation'])
    
    # Create tool_audit_logs table
    op.create_table(
        'tool_audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=True),
        sa.Column('task_id', sa.String(length=100), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_tool_audit_logs_timestamp', 'tool_audit_logs', ['timestamp'])
    op.create_index('idx_tool_audit_logs_agent_id', 'tool_audit_logs', ['agent_id'])
    op.create_index('idx_tool_audit_logs_agent_type', 'tool_audit_logs', ['agent_type'])
    op.create_index('idx_tool_audit_logs_tool_name', 'tool_audit_logs', ['tool_name'])
    op.create_index('idx_tool_audit_logs_project_id', 'tool_audit_logs', ['project_id'])
    op.create_index('idx_tool_audit_logs_allowed', 'tool_audit_logs', ['allowed'])
    op.create_index('idx_tool_audit_logs_time_range', 'tool_audit_logs', ['timestamp', 'agent_id'])


def downgrade() -> None:
    # Drop tool_audit_logs table
    op.drop_index('idx_tool_audit_logs_time_range', table_name='tool_audit_logs')
    op.drop_index('idx_tool_audit_logs_allowed', table_name='tool_audit_logs')
    op.drop_index('idx_tool_audit_logs_project_id', table_name='tool_audit_logs')
    op.drop_index('idx_tool_audit_logs_tool_name', table_name='tool_audit_logs')
    op.drop_index('idx_tool_audit_logs_agent_type', table_name='tool_audit_logs')
    op.drop_index('idx_tool_audit_logs_agent_id', table_name='tool_audit_logs')
    op.drop_index('idx_tool_audit_logs_timestamp', table_name='tool_audit_logs')
    op.drop_table('tool_audit_logs')
    
    # Drop agent_tool_permissions table
    op.drop_index('idx_agent_tool_permissions_lookup', table_name='agent_tool_permissions')
    op.drop_index('idx_agent_tool_permissions_tool_name', table_name='agent_tool_permissions')
    op.drop_index('idx_agent_tool_permissions_agent_type', table_name='agent_tool_permissions')
    op.drop_table('agent_tool_permissions')
