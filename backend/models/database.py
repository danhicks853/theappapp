"""
Database Models for Tool Access Service

SQLAlchemy models for TAS tables.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class AgentToolPermission(Base):
    """Agent tool permission matrix.
    
    Stores which agent types can access which tools and operations.
    """
    __tablename__ = 'agent_tool_permissions'
    
    id = Column(Integer, primary_key=True)
    agent_type = Column(String(50), nullable=False)
    tool_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    allowed = Column(Boolean, nullable=False, default=False, server_default='false')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('agent_type', 'tool_name', 'operation', name='uq_agent_tool_operation'),
        Index('idx_agent_tool_permissions_agent_type', 'agent_type'),
        Index('idx_agent_tool_permissions_tool_name', 'tool_name'),
        Index('idx_agent_tool_permissions_lookup', 'agent_type', 'tool_name', 'operation'),
    )
    
    def __repr__(self):
        return f"<AgentToolPermission(agent_type={self.agent_type}, tool={self.tool_name}, operation={self.operation}, allowed={self.allowed})>"


class ToolAuditLog(Base):
    """Tool access audit log.
    
    Comprehensive audit trail of all tool access attempts.
    Retention: 1 year (cleaned up by daily job).
    """
    __tablename__ = 'tool_audit_logs'
    
    id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    agent_id = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)
    tool_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    project_id = Column(String(100), nullable=True)
    task_id = Column(String(100), nullable=True)
    parameters = Column(JSONB, nullable=True)
    allowed = Column(Boolean, nullable=False)
    success = Column(Boolean, nullable=True)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_tool_audit_logs_timestamp', 'timestamp'),
        Index('idx_tool_audit_logs_agent_id', 'agent_id'),
        Index('idx_tool_audit_logs_agent_type', 'agent_type'),
        Index('idx_tool_audit_logs_tool_name', 'tool_name'),
        Index('idx_tool_audit_logs_project_id', 'project_id'),
        Index('idx_tool_audit_logs_allowed', 'allowed'),
        Index('idx_tool_audit_logs_time_range', 'timestamp', 'agent_id'),
    )
    
    def __repr__(self):
        return f"<ToolAuditLog(timestamp={self.timestamp}, agent={self.agent_id}, tool={self.tool_name}, operation={self.operation}, allowed={self.allowed})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool_name": self.tool_name,
            "operation": self.operation,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "parameters": self.parameters,
            "allowed": self.allowed,
            "success": self.success,
            "result": self.result,
            "error_message": self.error_message
        }
