"""Seed agent tool permissions from YAML

Revision ID: 20251103_21
Revises: 20251103_20
Create Date: 2025-11-03

Seeds agent_tool_permissions table with default permissions from
backend/config/default_permissions.yaml
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from pathlib import Path
import yaml

# revision identifiers, used by Alembic.
revision = '20251103_21'
down_revision = '20251103_20'
branch_labels = None
depends_on = None


def load_default_permissions():
    """Load default permissions from YAML file."""
    # Get path to YAML file
    config_path = Path(__file__).parent.parent.parent / 'config' / 'default_permissions.yaml'
    
    if not config_path.exists():
        raise FileNotFoundError(f"Default permissions file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        permissions = yaml.safe_load(f)
    
    return permissions


def upgrade() -> None:
    # Load permissions from YAML
    try:
        permissions_data = load_default_permissions()
    except Exception as e:
        print(f"Warning: Could not load default permissions: {e}")
        print("Skipping permission seeding. Run manually if needed.")
        return
    
    # Define table structure for bulk insert
    agent_tool_permissions = table(
        'agent_tool_permissions',
        column('agent_type', sa.String),
        column('tool_name', sa.String),
        column('operation', sa.String),
        column('allowed', sa.Boolean)
    )
    
    # Build permission rows
    permission_rows = []
    for agent_type, tools in permissions_data.items():
        if not isinstance(tools, dict):
            continue  # Skip if not a dict (e.g., comments)
        
        for tool_name, operations in tools.items():
            if not isinstance(operations, list):
                continue  # Skip if not a list
            
            for operation in operations:
                permission_rows.append({
                    'agent_type': agent_type,
                    'tool_name': tool_name,
                    'operation': operation,
                    'allowed': True
                })
    
    # Bulk insert
    if permission_rows:
        op.bulk_insert(agent_tool_permissions, permission_rows)
        print(f"Seeded {len(permission_rows)} permissions for {len(permissions_data)} agent types")
    else:
        print("Warning: No permissions found to seed")


def downgrade() -> None:
    # Delete all seeded permissions
    op.execute("DELETE FROM agent_tool_permissions WHERE allowed = true")
