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
    
    # Seed core required specialists
    specialists_table = sa.table('specialists',
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('system_prompt', sa.Text),
        sa.column('status', sa.String),
        sa.column('tags', postgresql.JSONB),
        sa.column('model', sa.String),
        sa.column('temperature', sa.Numeric),
        sa.column('max_tokens', sa.Integer),
        sa.column('required', sa.Boolean),
        sa.column('version', sa.String),
        sa.column('template_id', sa.String),
        sa.column('installed_from_store', sa.Boolean),
        sa.column('display_name', sa.String),
        sa.column('avatar', sa.String),
        sa.column('bio', sa.Text),
        sa.column('interests', postgresql.JSONB),
        sa.column('favorite_tool', sa.String),
        sa.column('quote', sa.Text),
    )
    
    # Seed data for required specialists (only the 3 core required ones)
    core_specialists = [
        {
            'name': 'frontend_developer',
            'display_name': 'Alex Frontend',
            'description': 'React/TypeScript specialist who builds beautiful, accessible UIs',
            'system_prompt': 'You are Alex, an expert frontend developer specializing in React, TypeScript, and modern UI/UX. You write clean, accessible code and love creating delightful user experiences.',
            'status': 'active',
            'tags': ['frontend', 'react', 'typescript', 'ui', 'ux'],
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 4000,
            'required': True,
            'version': '1.0.0',
            'template_id': 'frontend-developer',
            'installed_from_store': True,
            'avatar': 'frontend-alex',
            'bio': 'I turn designs into pixel-perfect, accessible experiences',
            'interests': ['React', 'TypeScript', 'Design Systems', 'Web Accessibility'],
            'favorite_tool': 'React Developer Tools',
            'quote': 'Every pixel matters, every interaction delights',
        },
        {
            'name': 'backend_developer',
            'display_name': 'Sam Backend',
            'description': 'Python/FastAPI expert who architects scalable backend systems',
            'status': 'active',
            'tags': ['backend', 'python', 'fastapi', 'database', 'api'],
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 4000,
            'system_prompt': 'You are Sam, a backend developer expert in Python, FastAPI, and database design. You build robust, scalable APIs and love optimizing performance.',
            'required': True,
            'version': '1.0.0',
            'template_id': 'backend-developer',
            'installed_from_store': True,
            'avatar': 'backend-sam',
            'bio': 'Building the engine that powers great products',
            'interests': ['Python', 'FastAPI', 'PostgreSQL', 'System Architecture'],
            'favorite_tool': 'FastAPI',
            'quote': 'Great APIs are invisible until you need them',
            },
        {
            'name': 'orchestrator',
            'display_name': 'Morgan Orchestrator',
            'description': 'Project coordinator who manages tasks and team collaboration',
            'status': 'active',
            'tags': ['orchestrator', 'coordination', 'planning', 'management'],
            'model': 'gpt-4',
            'temperature': 0.6,
            'max_tokens': 4000,
            'system_prompt': 'You are Morgan, the orchestrator who coordinates between specialists, breaks down complex tasks, and ensures smooth project execution. You are organized, strategic, and excel at delegation.',
            'required': True,
            'version': '1.0.0',
            'template_id': 'orchestrator',
            'installed_from_store': True,
            'avatar': 'orchestrator-morgan',
            'bio': 'Turning chaos into coordinated execution',
            'interests': ['Project Management', 'Team Coordination', 'Agile', 'Strategy'],
            'favorite_tool': 'Gantt Charts',
            'quote': 'Every great product needs a conductor',
            },
    ]
    
    op.bulk_insert(specialists_table, core_specialists)


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
