"""
Backend Models Package

This package contains all data models used throughout the backend system.
"""

from .communication import (
    MessageType,
    AgentType,
    MessagePriority,
    BaseMessage,
    TaskAssignmentMessage,
    TaskResultMessage,
    HelpRequestMessage,
    SpecialistResponseMessage,
    ProgressUpdateMessage,
    ErrorReportMessage,
    MessageRouter,
    AnyMessage,
)

__all__ = [
    "MessageType",
    "AgentType",
    "MessagePriority",
    "BaseMessage",
    "TaskAssignmentMessage",
    "TaskResultMessage",
    "HelpRequestMessage",
    "SpecialistResponseMessage",
    "ProgressUpdateMessage",
    "ErrorReportMessage",
    "MessageRouter",
    "AnyMessage",
]
