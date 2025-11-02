"""
Collaboration Models

Pydantic models for agent-to-agent collaboration requests, context, and outcomes.

Reference: Decision 70 - Agent Collaboration Protocol
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


class CollaborationRequestType(str, Enum):
    """Types of collaboration requests."""
    MODEL_DATA = "model_data"  # Questions about data models or schemas
    SECURITY_REVIEW = "security_review"  # Security concerns or reviews
    API_CLARIFICATION = "api_clarification"  # API design or usage questions
    BUG_DEBUGGING = "bug_debugging"  # Help debugging an issue
    REQUIREMENTS = "requirements"  # Clarifying requirements
    INFRASTRUCTURE = "infrastructure"  # Infrastructure or deployment questions


class CollaborationUrgency(str, Enum):
    """Urgency levels for collaboration requests."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CollaborationStatus(str, Enum):
    """Status of collaboration lifecycle."""
    PENDING = "pending"  # Request created, not yet routed
    ROUTED = "routed"  # Routed to specialist
    IN_PROGRESS = "in_progress"  # Specialist working on it
    RESPONDED = "responded"  # Specialist provided response
    RESOLVED = "resolved"  # Requester confirmed resolution
    FAILED = "failed"  # Could not be resolved
    TIMEOUT = "timeout"  # No response within time limit


class CollaborationRequest(BaseModel):
    """
    Structured collaboration request from one agent to another.
    
    This is the primary message format for agent-to-agent help requests.
    """
    collaboration_id: str = Field(..., description="Unique identifier for this collaboration")
    request_type: CollaborationRequestType = Field(..., description="Type of request")
    requesting_agent_id: str = Field(..., description="ID of agent requesting help")
    requesting_agent_type: str = Field(..., description="Type of requesting agent")
    question: str = Field(..., min_length=10, max_length=2000, description="The specific question or request")
    context: Dict[str, Any] = Field(default_factory=dict, description="Relevant context")
    suggested_specialist: Optional[str] = Field(None, description="Optional hint about which specialist to use")
    urgency: CollaborationUrgency = Field(default=CollaborationUrgency.NORMAL, description="How urgent is this request")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When request was created")
    
    @validator('question')
    def question_not_empty(cls, v):
        """Ensure question is not just whitespace."""
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "collaboration_id": "collab-123",
                "request_type": "security_review",
                "requesting_agent_id": "backend-dev-1",
                "requesting_agent_type": "backend_developer",
                "question": "Is this authentication flow secure against CSRF attacks?",
                "context": {
                    "code": "def authenticate(request): ...",
                    "file": "auth.py",
                    "line": 42
                },
                "urgency": "high"
            }
        }


class CollaborationContext(BaseModel):
    """
    Curated context shared with specialist.
    
    Orchestrator filters and limits context to prevent overwhelming the specialist.
    """
    requesting_agent_id: str = Field(..., description="Who needs help")
    current_task: str = Field(..., description="What the agent is trying to do")
    specific_question: str = Field(..., description="The exact question")
    relevant_code: Optional[str] = Field(None, max_length=2000, description="Relevant code snippet (limited)")
    attempted_approaches: List[str] = Field(default_factory=list, description="What's been tried already")
    error_message: Optional[str] = Field(None, max_length=500, description="Error if applicable")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Other relevant info")
    
    @validator('relevant_code')
    def truncate_code(cls, v):
        """Ensure code doesn't exceed reasonable length."""
        if v and len(v) > 2000:
            return v[:2000] + "\n... (truncated)"
        return v
    
    def estimate_tokens(self) -> int:
        """Rough estimate of token count."""
        text = f"{self.current_task} {self.specific_question} {self.relevant_code or ''}"
        return len(text) // 4  # Rough approximation


class CollaborationResponse(BaseModel):
    """
    Response from specialist to requesting agent.
    """
    collaboration_id: str = Field(..., description="Links back to request")
    responding_specialist_id: str = Field(..., description="Who provided the response")
    responding_specialist_type: str = Field(..., description="Type of specialist")
    response: str = Field(..., min_length=10, description="The answer or guidance")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Specialist's confidence (0-1)")
    reasoning: Optional[str] = Field(None, description="Why this answer was given")
    suggested_actions: List[str] = Field(default_factory=list, description="Recommended next steps")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Supporting information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When response was created")
    
    @validator('response')
    def response_not_empty(cls, v):
        """Ensure response is not just whitespace."""
        if not v.strip():
            raise ValueError('Response cannot be empty')
        return v.strip()


class CollaborationOutcome(BaseModel):
    """
    Final outcome of the collaboration.
    
    Records whether the collaboration was successful and captures learnings.
    """
    collaboration_id: str = Field(..., description="Links back to request")
    status: CollaborationStatus = Field(..., description="Final status")
    resolution: str = Field(..., description="How it was resolved")
    requester_satisfied: bool = Field(..., description="Did the answer help?")
    valuable_for_rag: bool = Field(default=False, description="Should this be saved for future reference?")
    response_time_seconds: Optional[float] = Field(None, description="How long from request to response")
    tokens_used: Optional[int] = Field(None, description="Approximate tokens for this collaboration")
    cost_usd: Optional[float] = Field(None, description="Estimated cost")
    lessons_learned: Optional[str] = Field(None, description="Key takeaways")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When outcome was recorded")


class CollaborationLoop(BaseModel):
    """
    Detected collaboration loop (agents asking each other repeatedly).
    """
    loop_id: str = Field(..., description="Unique identifier for this loop")
    agent_a_id: str = Field(..., description="First agent in loop")
    agent_b_id: str = Field(..., description="Second agent in loop")
    topic_similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score of repeated questions")
    cycle_count: int = Field(..., ge=1, description="How many times the loop has occurred")
    questions: List[str] = Field(..., description="The repeated questions")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When loop was detected")
    gate_created: bool = Field(default=False, description="Whether a gate was triggered")
    gate_id: Optional[str] = Field(None, description="ID of created gate if any")
    
    @validator('cycle_count')
    def cycle_count_positive(cls, v):
        """Ensure cycle count is positive."""
        if v < 1:
            raise ValueError('Cycle count must be at least 1')
        return v


class CollaborationMetrics(BaseModel):
    """
    Aggregated metrics for collaboration analysis.
    """
    agent_pair: str = Field(..., description="e.g., 'backend_dev->security_expert'")
    total_collaborations: int = Field(default=0, description="Total number of collaborations")
    successful_count: int = Field(default=0, description="How many were resolved")
    failed_count: int = Field(default=0, description="How many failed")
    average_response_time_seconds: Optional[float] = Field(None, description="Average time to respond")
    total_cost_usd: Optional[float] = Field(None, description="Total cost for this pair")
    most_common_request_type: Optional[CollaborationRequestType] = Field(None, description="Most frequent type")
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Percentage successful")
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_collaborations == 0:
            return 0.0
        return self.successful_count / self.total_collaborations
