"""
Pytest Configuration and Shared Fixtures

Provides common test fixtures for all Phase 1 tests.
"""
import pytest
import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from fastapi.testclient import TestClient

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:55432/theappapp_test"
)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL."""
    return os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine(test_database_url: str) -> Generator[Engine, None, None]:
    """Create database engine for tests."""
    # Convert to psycopg
    if test_database_url.startswith("postgresql://"):
        test_database_url = test_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    engine = create_engine(test_database_url)
    
    # Verify connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Generator:
    """Create a database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    
    yield connection
    
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def api_client():
    """Create FastAPI test client."""
    from backend.api import app
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for LLM tests."""
    from unittest.mock import Mock, MagicMock
    
    mock_client = Mock()
    
    # Mock chat completion
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="Mocked LLM response"))
    ]
    mock_completion.usage = MagicMock(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )
    
    mock_client.chat.completions.create.return_value = mock_completion
    
    # Mock embeddings
    mock_embedding = MagicMock()
    mock_embedding.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create.return_value = mock_embedding
    
    return mock_client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for vector tests."""
    from unittest.mock import Mock, MagicMock
    
    mock_client = Mock()
    
    # Mock search
    mock_client.search.return_value = []
    
    # Mock upsert
    mock_client.upsert.return_value = MagicMock(status="completed")
    
    # Mock delete
    mock_client.delete.return_value = MagicMock(status="completed")
    
    # Mock get_collection
    mock_collection = MagicMock()
    mock_collection.config.params.vectors.size = 1536
    mock_collection.points_count = 0
    mock_client.get_collection.return_value = mock_collection
    
    return mock_client


@pytest.fixture
def sample_project_id():
    """Sample project ID for tests."""
    return "test-project-123"


@pytest.fixture
def sample_agent_id():
    """Sample agent ID for tests."""
    return "test-agent-456"


@pytest.fixture
def sample_task_id():
    """Sample task ID for tests."""
    return "test-task-789"


@pytest.fixture
def mock_gate_data():
    """Sample gate data for tests."""
    return {
        "project_id": "test-project-123",
        "reason": "Test gate for quality check",
        "context": {"test": "data"},
        "agent_id": "test-agent-456",
        "gate_type": "quality_check"
    }


@pytest.fixture
def mock_collaboration_data():
    """Sample collaboration request data."""
    return {
        "requesting_agent_id": "backend-dev-1",
        "specialist_agent_id": "security-expert-1",
        "question": "How do I prevent SQL injection?",
        "context": {"current_approach": "String concatenation"},
        "question_type": "security_review"
    }


@pytest.fixture
def mock_failure_signature():
    """Sample failure signature for tests."""
    from backend.models.failure_signature import FailureSignature, ErrorType
    from datetime import datetime, UTC
    
    return FailureSignature(
        exact_message="TypeError: cannot read property of undefined",
        error_type=ErrorType.TYPE_ERROR,
        location="backend/api/routes.py:42",
        context_hash="abc123def456",
        timestamp=datetime.now(UTC),
        agent_id="test-agent-456",
        task_id="test-task-789",
        metadata={}
    )


@pytest.fixture
def mock_knowledge_entry():
    """Sample knowledge entry for tests."""
    return {
        "id": "knowledge-123",
        "knowledge_type": "failure_solution",
        "content": "## Problem\nDatabase slow\n## Solution\nAdded indexes",
        "metadata": {
            "agent_type": "backend_developer",
            "task_type": "performance",
            "technology": "PostgreSQL",
            "quality_score": "high",
            "success_count": 5
        },
        "embedded": False
    }


# Helper functions for tests

def create_test_gate(db_session, gate_data: dict) -> str:
    """Helper to create a test gate."""
    import uuid
    from datetime import datetime, UTC
    import json
    
    gate_id = str(uuid.uuid4())
    
    query = text("""
        INSERT INTO gates
        (id, project_id, reason, context, status, agent_id, gate_type, created_at)
        VALUES
        (:id, :project_id, :reason, :context, :status, :agent_id, :gate_type, :created_at)
    """)
    
    db_session.execute(query, {
        "id": gate_id,
        "project_id": gate_data["project_id"],
        "reason": gate_data["reason"],
        "context": json.dumps(gate_data.get("context", {})),
        "status": "pending",
        "agent_id": gate_data.get("agent_id"),
        "gate_type": gate_data.get("gate_type", "manual_intervention"),
        "created_at": datetime.now(UTC)
    })
    db_session.commit()
    
    return gate_id


def create_test_knowledge(db_session, knowledge_data: dict) -> str:
    """Helper to create test knowledge entry."""
    import uuid
    from datetime import datetime, UTC
    import json
    
    knowledge_id = str(uuid.uuid4())
    
    query = text("""
        INSERT INTO knowledge_staging
        (id, knowledge_type, content, metadata, embedded, created_at)
        VALUES
        (:id, :knowledge_type, :content, :metadata, :embedded, :created_at)
    """)
    
    db_session.execute(query, {
        "id": knowledge_id,
        "knowledge_type": knowledge_data["knowledge_type"],
        "content": knowledge_data["content"],
        "metadata": json.dumps(knowledge_data["metadata"]),
        "embedded": knowledge_data.get("embedded", False),
        "created_at": datetime.now(UTC)
    })
    db_session.commit()
    
    return knowledge_id


# Make helper functions available
pytest.create_test_gate = create_test_gate
pytest.create_test_knowledge = create_test_knowledge
