"""
Tests for: backend/models/communication.py
Task: 1.1.3 - Create agent communication protocol
Coverage Target: 95%+

This test suite validates:
1. Message model creation and validation
2. Hub-and-spoke pattern enforcement
3. Message routing logic
4. Message history tracking
5. Error handling and validation
"""

import pytest
from datetime import datetime, timedelta
from backend.models.communication import (
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
)


class TestMessageType:
    """Test MessageType enum."""
    
    def test_message_type_values(self):
        """Test all message types are defined."""
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.TASK_RESULT.value == "task_result"
        assert MessageType.HELP_REQUEST.value == "help_request"
        assert MessageType.SPECIALIST_RESPONSE.value == "specialist_response"
        assert MessageType.PROGRESS_UPDATE.value == "progress_update"
        assert MessageType.ERROR_REPORT.value == "error_report"
    
    def test_message_type_count(self):
        """Test correct number of message types."""
        assert len(MessageType) == 6


class TestAgentType:
    """Test AgentType enum."""
    
    def test_agent_type_values(self):
        """Test all agent types are defined."""
        assert AgentType.ORCHESTRATOR.value == "orchestrator"
        assert AgentType.BACKEND_DEVELOPER.value == "backend_developer"
        assert AgentType.FRONTEND_DEVELOPER.value == "frontend_developer"
        assert AgentType.QA_ENGINEER.value == "qa_engineer"
        assert AgentType.SECURITY_EXPERT.value == "security_expert"


class TestBaseMessage:
    """Test BaseMessage model."""
    
    def test_base_message_creation(self):
        """Test creating a base message with required fields."""
        msg = BaseMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            message_type=MessageType.TASK_ASSIGNMENT
        )
        
        assert msg.sender_id == "agent-1"
        assert msg.sender_type == AgentType.BACKEND_DEVELOPER
        assert msg.recipient_id == "orchestrator-1"
        assert msg.message_id is not None
        assert msg.priority == MessagePriority.NORMAL
    
    def test_base_message_auto_ids(self):
        """Test that message_id and correlation_id are auto-generated."""
        msg1 = BaseMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            message_type=MessageType.TASK_ASSIGNMENT
        )
        msg2 = BaseMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            message_type=MessageType.TASK_ASSIGNMENT
        )
        
        assert msg1.message_id != msg2.message_id


class TestTaskAssignmentMessage:
    """Test TaskAssignmentMessage model."""
    
    def test_task_assignment_creation(self):
        """Test creating a task assignment message."""
        msg = TaskAssignmentMessage(
            sender_id="orchestrator-1",
            sender_type=AgentType.ORCHESTRATOR,
            recipient_id="agent-1",
            recipient_type=AgentType.BACKEND_DEVELOPER,
            task_id="task-123",
            task_type="backend_development",
            task_description="Implement user authentication",
            requirements={"framework": "FastAPI", "auth_type": "JWT"},
            context={"project_id": "proj-1", "phase": "phase-1"}
        )
        
        assert msg.message_type == MessageType.TASK_ASSIGNMENT
        assert msg.task_id == "task-123"
        assert msg.task_type == "backend_development"
        assert msg.requirements["framework"] == "FastAPI"
    
    def test_task_assignment_with_deadline(self):
        """Test task assignment with deadline."""
        deadline = datetime.now() + timedelta(hours=24)
        msg = TaskAssignmentMessage(
            sender_id="orchestrator-1",
            sender_type=AgentType.ORCHESTRATOR,
            recipient_id="agent-1",
            recipient_type=AgentType.BACKEND_DEVELOPER,
            task_id="task-123",
            task_type="backend_development",
            task_description="Implement user authentication",
            deadline=deadline
        )
        
        assert msg.deadline == deadline


class TestTaskResultMessage:
    """Test TaskResultMessage model."""
    
    def test_task_result_success(self):
        """Test task result message for successful completion."""
        msg = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            status="completed",
            result={"endpoint": "/api/auth/login", "method": "POST"},
            execution_time_seconds=45.5,
            tokens_used=1250
        )
        
        assert msg.message_type == MessageType.TASK_RESULT
        assert msg.task_id == "task-123"
        assert msg.status == "completed"
    
    def test_task_result_failed(self):
        """Test task result message for failed task."""
        msg = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            status="failed",
            errors=["Database connection timeout"]
        )
        
        assert msg.status == "failed"
        assert len(msg.errors) == 1
    
    def test_task_result_invalid_status(self):
        """Test that invalid status raises validation error."""
        with pytest.raises(ValueError):
            TaskResultMessage(
                sender_id="agent-1",
                sender_type=AgentType.BACKEND_DEVELOPER,
                recipient_id="orchestrator-1",
                recipient_type=AgentType.ORCHESTRATOR,
                task_id="task-123",
                status="invalid_status"
            )


class TestHelpRequestMessage:
    """Test HelpRequestMessage model."""
    
    def test_help_request_creation(self):
        """Test creating a help request message."""
        msg = HelpRequestMessage(
            sender_id="agent-1",
            sender_type=AgentType.FRONTEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            question="What is the User model structure?",
            current_task_id="task-123",
            specific_concern="Need to know available fields"
        )
        
        assert msg.message_type == MessageType.HELP_REQUEST
        assert msg.question == "What is the User model structure?"
    
    def test_help_request_urgency_levels(self):
        """Test help request with different urgency levels."""
        for urgency in ["low", "normal", "high", "critical"]:
            msg = HelpRequestMessage(
                sender_id="agent-1",
                sender_type=AgentType.FRONTEND_DEVELOPER,
                recipient_id="orchestrator-1",
                recipient_type=AgentType.ORCHESTRATOR,
                question="Help needed",
                current_task_id="task-123",
                urgency=urgency
            )
            assert msg.urgency == urgency
    
    def test_help_request_invalid_urgency(self):
        """Test that invalid urgency raises validation error."""
        with pytest.raises(ValueError):
            HelpRequestMessage(
                sender_id="agent-1",
                sender_type=AgentType.FRONTEND_DEVELOPER,
                recipient_id="orchestrator-1",
                recipient_type=AgentType.ORCHESTRATOR,
                question="Help needed",
                current_task_id="task-123",
                urgency="invalid_urgency"
            )


class TestSpecialistResponseMessage:
    """Test SpecialistResponseMessage model."""
    
    def test_specialist_response_creation(self):
        """Test creating a specialist response message."""
        msg = SpecialistResponseMessage(
            sender_id="orchestrator-1",
            sender_type=AgentType.ORCHESTRATOR,
            recipient_id="agent-1",
            recipient_type=AgentType.FRONTEND_DEVELOPER,
            collaboration_id="collab-456",
            consulted_agent_type=AgentType.BACKEND_DEVELOPER,
            answer="User model has: id, username, email",
            confidence=0.95
        )
        
        assert msg.message_type == MessageType.SPECIALIST_RESPONSE
        assert msg.collaboration_id == "collab-456"
        assert msg.confidence == 0.95
    
    def test_specialist_response_confidence_validation(self):
        """Test confidence validation (0-1 range)."""
        # Valid confidence
        msg = SpecialistResponseMessage(
            sender_id="orchestrator-1",
            sender_type=AgentType.ORCHESTRATOR,
            recipient_id="agent-1",
            recipient_type=AgentType.FRONTEND_DEVELOPER,
            collaboration_id="collab-456",
            consulted_agent_type=AgentType.BACKEND_DEVELOPER,
            answer="Answer",
            confidence=0.5
        )
        assert msg.confidence == 0.5
        
        # Invalid confidence (too high)
        with pytest.raises(ValueError):
            SpecialistResponseMessage(
                sender_id="orchestrator-1",
                sender_type=AgentType.ORCHESTRATOR,
                recipient_id="agent-1",
                recipient_type=AgentType.FRONTEND_DEVELOPER,
                collaboration_id="collab-456",
                consulted_agent_type=AgentType.BACKEND_DEVELOPER,
                answer="Answer",
                confidence=1.5
            )


class TestProgressUpdateMessage:
    """Test ProgressUpdateMessage model."""
    
    def test_progress_update_creation(self):
        """Test creating a progress update message."""
        msg = ProgressUpdateMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            progress_percentage=50,
            current_step="Implementing endpoints"
        )
        
        assert msg.message_type == MessageType.PROGRESS_UPDATE
        assert msg.progress_percentage == 50
    
    def test_progress_update_progress_validation(self):
        """Test progress percentage validation (0-100)."""
        # Valid progress
        msg = ProgressUpdateMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            progress_percentage=100
        )
        assert msg.progress_percentage == 100
        
        # Invalid progress (too high)
        with pytest.raises(ValueError):
            ProgressUpdateMessage(
                sender_id="agent-1",
                sender_type=AgentType.BACKEND_DEVELOPER,
                recipient_id="orchestrator-1",
                recipient_type=AgentType.ORCHESTRATOR,
                task_id="task-123",
                progress_percentage=150
            )


class TestErrorReportMessage:
    """Test ErrorReportMessage model."""
    
    def test_error_report_creation(self):
        """Test creating an error report message."""
        msg = ErrorReportMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            error_type="database_error",
            error_message="Connection timeout after 30 seconds"
        )
        
        assert msg.message_type == MessageType.ERROR_REPORT
        assert msg.error_type == "database_error"
    
    def test_error_report_escalation_flag(self):
        """Test error report with escalation flag."""
        msg = ErrorReportMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            error_type="critical_error",
            error_message="Critical system failure",
            needs_escalation=True
        )
        
        assert msg.needs_escalation is True


class TestMessageRouter:
    """Test MessageRouter hub-and-spoke enforcement."""
    
    def test_router_initialization(self):
        """Test router initialization."""
        router = MessageRouter()
        assert router.message_log == []
        assert router.orchestrator_id is None
    
    def test_agent_to_orchestrator_valid(self):
        """Test valid agent-to-orchestrator message."""
        router = MessageRouter()
        msg = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            status="completed"
        )
        
        assert router.validate_message(msg) is True
    
    def test_orchestrator_to_agent_valid(self):
        """Test valid orchestrator-to-agent message."""
        router = MessageRouter()
        msg = TaskAssignmentMessage(
            sender_id="orchestrator-1",
            sender_type=AgentType.ORCHESTRATOR,
            recipient_id="agent-1",
            recipient_type=AgentType.BACKEND_DEVELOPER,
            task_id="task-123",
            task_type="backend_development",
            task_description="Implement feature"
        )
        
        assert router.validate_message(msg) is True
    
    def test_agent_to_agent_blocked(self):
        """Test that direct agent-to-agent communication is blocked."""
        router = MessageRouter()
        msg = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="agent-2",
            recipient_type=AgentType.FRONTEND_DEVELOPER,
            task_id="task-123",
            status="completed"
        )
        
        with pytest.raises(ValueError) as exc_info:
            router.validate_message(msg)
        
        assert "Hub-and-spoke violation" in str(exc_info.value)
    
    def test_route_message_success(self):
        """Test successful message routing."""
        router = MessageRouter()
        msg = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            status="completed"
        )
        
        assert router.route_message(msg) is True
        assert len(router.message_log) == 1
    
    def test_message_history_all(self):
        """Test retrieving all message history."""
        router = MessageRouter()
        
        msg1 = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            status="completed"
        )
        msg2 = ProgressUpdateMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            progress_percentage=50
        )
        
        router.route_message(msg1)
        router.route_message(msg2)
        
        history = router.get_message_history()
        assert len(history) == 2
    
    def test_message_history_filter_by_sender(self):
        """Test filtering message history by sender ID."""
        router = MessageRouter()
        
        msg1 = TaskResultMessage(
            sender_id="agent-1",
            sender_type=AgentType.BACKEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-123",
            status="completed"
        )
        msg2 = TaskResultMessage(
            sender_id="agent-2",
            sender_type=AgentType.FRONTEND_DEVELOPER,
            recipient_id="orchestrator-1",
            recipient_type=AgentType.ORCHESTRATOR,
            task_id="task-124",
            status="completed"
        )
        
        router.route_message(msg1)
        router.route_message(msg2)
        
        history = router.get_message_history(sender_id="agent-1")
        assert len(history) == 1
