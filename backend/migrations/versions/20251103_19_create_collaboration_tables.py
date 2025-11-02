"""create collaboration tables

Revision ID: 20251103_19
Revises: 20251103_18
Create Date: 2025-11-03

Migration 019: Create Collaboration Tracking Tables
Purpose: Full lifecycle tracking for agent-to-agent collaborations
Reference: Decision 70 - Agent Collaboration Protocol

Tables Created:
1. collaboration_requests - Main collaboration request records
2. collaboration_exchanges - Message history between agents
3. collaboration_responses - Specialist response details
4. collaboration_outcomes - Final collaboration outcomes
5. collaboration_loops - Detected collaboration loops
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20251103_19'
down_revision = '20251103_18'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create collaboration tracking tables."""
    
    # 1. collaboration_requests - Main request tracking
    op.create_table(
        'collaboration_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('request_type', sa.String(50), nullable=False),  # model_data, security_review, etc.
        sa.Column('requesting_agent_id', sa.String(100), nullable=False),
        sa.Column('requesting_agent_type', sa.String(50), nullable=False),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('context', sa.Text, nullable=True),  # JSON string or text
        sa.Column('suggested_specialist', sa.String(50), nullable=True),
        sa.Column('urgency', sa.String(20), nullable=False, server_default='normal'),  # low, normal, high, critical
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, routed, responded, resolved, failed
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Indexes for collaboration_requests
    op.create_index('ix_collaboration_requests_requesting_agent', 'collaboration_requests', ['requesting_agent_id'])
    op.create_index('ix_collaboration_requests_status', 'collaboration_requests', ['status'])
    op.create_index('ix_collaboration_requests_request_type', 'collaboration_requests', ['request_type'])
    op.create_index('ix_collaboration_requests_created_at', 'collaboration_requests', ['created_at'])
    
    # 2. collaboration_exchanges - Message history
    op.create_table(
        'collaboration_exchanges',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('collaboration_id', UUID(as_uuid=True), nullable=False),
        sa.Column('from_agent_id', sa.String(100), nullable=False),
        sa.Column('to_agent_id', sa.String(100), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False),  # request, response, clarification
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['collaboration_id'], ['collaboration_requests.id'], ondelete='CASCADE')
    )
    
    # Indexes for collaboration_exchanges
    op.create_index('ix_collaboration_exchanges_collaboration_id', 'collaboration_exchanges', ['collaboration_id'])
    op.create_index('ix_collaboration_exchanges_timestamp', 'collaboration_exchanges', ['timestamp'])
    
    # 3. collaboration_responses - Specialist response details
    op.create_table(
        'collaboration_responses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('collaboration_id', UUID(as_uuid=True), nullable=False),
        sa.Column('responding_specialist_id', sa.String(100), nullable=False),
        sa.Column('responding_specialist_type', sa.String(50), nullable=False),
        sa.Column('response', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),  # 0.0 to 1.0
        sa.Column('reasoning', sa.Text, nullable=True),
        sa.Column('suggested_actions', sa.Text, nullable=True),  # JSON array as text
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['collaboration_id'], ['collaboration_requests.id'], ondelete='CASCADE')
    )
    
    # Indexes for collaboration_responses
    op.create_index('ix_collaboration_responses_collaboration_id', 'collaboration_responses', ['collaboration_id'])
    op.create_index('ix_collaboration_responses_specialist_id', 'collaboration_responses', ['responding_specialist_id'])
    
    # 4. collaboration_outcomes - Final outcomes
    op.create_table(
        'collaboration_outcomes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('collaboration_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # resolved, failed, timeout
        sa.Column('resolution', sa.Text, nullable=False),
        sa.Column('requester_satisfied', sa.Boolean, nullable=False),
        sa.Column('valuable_for_rag', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('response_time_seconds', sa.Float, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('cost_usd', sa.Float, nullable=True),
        sa.Column('lessons_learned', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['collaboration_id'], ['collaboration_requests.id'], ondelete='CASCADE')
    )
    
    # Indexes for collaboration_outcomes
    op.create_index('ix_collaboration_outcomes_collaboration_id', 'collaboration_outcomes', ['collaboration_id'])
    op.create_index('ix_collaboration_outcomes_status', 'collaboration_outcomes', ['status'])
    op.create_index('ix_collaboration_outcomes_valuable_for_rag', 'collaboration_outcomes', ['valuable_for_rag'])
    op.create_index('ix_collaboration_outcomes_timestamp', 'collaboration_outcomes', ['timestamp'])
    
    # 5. collaboration_loops - Detected loops
    op.create_table(
        'collaboration_loops',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_a_id', sa.String(100), nullable=False),
        sa.Column('agent_b_id', sa.String(100), nullable=False),
        sa.Column('topic_similarity', sa.Float, nullable=False),  # 0.0 to 1.0
        sa.Column('cycle_count', sa.Integer, nullable=False),
        sa.Column('questions', sa.Text, nullable=False),  # JSON array or text list
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('gate_created', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('gate_id', UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['gate_id'], ['gates.id'], ondelete='SET NULL')
    )
    
    # Indexes for collaboration_loops
    op.create_index('ix_collaboration_loops_agents', 'collaboration_loops', ['agent_a_id', 'agent_b_id'])
    op.create_index('ix_collaboration_loops_detected_at', 'collaboration_loops', ['detected_at'])
    op.create_index('ix_collaboration_loops_gate_created', 'collaboration_loops', ['gate_created'])
    
    print("✅ Created 5 collaboration tracking tables:")
    print("   - collaboration_requests (main)")
    print("   - collaboration_exchanges (message history)")
    print("   - collaboration_responses (specialist responses)")
    print("   - collaboration_outcomes (final outcomes)")
    print("   - collaboration_loops (detected loops)")


def downgrade() -> None:
    """Drop collaboration tracking tables."""
    op.drop_table('collaboration_loops')
    op.drop_table('collaboration_outcomes')
    op.drop_table('collaboration_responses')
    op.drop_table('collaboration_exchanges')
    op.drop_table('collaboration_requests')
    print("❌ Dropped all collaboration tracking tables")
