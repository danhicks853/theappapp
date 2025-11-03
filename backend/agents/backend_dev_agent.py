"""
Backend Developer Agent

Specializes in Python backend development, API creation, and database operations.
Inherits full execution framework from BaseAgent.

Reference: MVP Demo Plan - Built-in agents
"""
from typing import Any, Optional
from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result


BACKEND_DEV_SYSTEM_PROMPT = """You are an expert Python backend developer specializing in:
- FastAPI and Flask application development
- RESTful API design and implementation  
- SQL database schema design and queries (PostgreSQL)
- Async Python programming
- Error handling and logging best practices
- Unit testing with pytest
- Code quality and PEP 8 compliance

Your responsibilities:
1. Write clean, efficient, production-ready Python code
2. Create comprehensive unit tests for all code
3. Follow best practices for API design
4. Optimize database queries
5. Handle errors gracefully with proper logging
6. Document code with clear docstrings

When given a task:
1. Analyze requirements carefully
2. Break down into logical steps
3. Write code with tests
4. Validate implementation against requirements
5. Provide clear explanations of your approach

Output format:
- Code blocks with language tags
- Inline comments for complex logic
- Docstrings for all functions/classes
- Test cases covering edge cases
"""


class BackendDevAgent(BaseAgent):
    """
    Backend Developer specialist agent.
    
    Capabilities:
    - Python/FastAPI development
    - Database design and queries
    - API endpoint creation
    - Unit test writing
    - Code review and optimization
    
    Example:
        agent = BackendDevAgent(
            agent_id="backend-dev-1",
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter
        )
        result = await agent.run_task(task)
    """
    
    def __init__(
        self,
        agent_id: str,
        orchestrator: Any,
        llm_client: Any,
        *,
        openai_adapter: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        search_service: Optional[Any] = None,
        **kwargs
    ):
        # Accept agent_type from kwargs or use passed value
        final_agent_type = kwargs.pop('agent_type', 'backend_developer')
        # system_prompt comes from kwargs (set by factory)
        super().__init__(
            agent_id=agent_id,
            agent_type=final_agent_type,
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter,
            rag_service=rag_service,
            search_service=search_service,
            **kwargs
        )
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """
        Execute backend development actions.
        
        Actions:
        - write_api: Create API endpoints
        - write_models: Create database models
        - write_services: Create business logic
        - write_tests: Create unit tests
        - setup_backend: Initialize backend structure
        """
        action_type = action.operation or action.tool_name or ""
        
        if action_type == "write_api":
            return await self._write_api_code(action, state)
        elif action_type == "write_models":
            return await self._write_models(action, state)
        elif action_type == "write_services":
            return await self._write_services(action, state)
        elif action_type == "write_tests":
            return await self._write_tests(action, state)
        elif action_type == "setup_backend":
            return await self._setup_backend_structure(action, state)
        else:
            # Generic code generation
            return await self._generate_backend_code(action, state)
    
    async def _write_api_code(self, action: Any, state: Any):
        """Generate API endpoint code."""
        requirements = state.get("context", {}).get("description", "API endpoints")
        
        # Generate Flask/FastAPI code
        api_code = f'''"""Backend API endpoints."""
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/greeting', methods=['GET'])
def get_greeting():
    """Return a greeting message."""
    name = request.args.get('name', 'World')
    return jsonify({{"message": f"Hello {{name}}!"}})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({{"status": "healthy"}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "backend/app.py",
                "content": api_code
            }
        })
        
        return Result(success=True, output=api_code, metadata={"files_created": ["backend/app.py"]})
    
    async def _write_models(self, action: Any, state: Any):
        """Generate database models."""
        models_code = '''"""Database models."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "backend/models.py",
                "content": models_code
            }
        })
        
        return Result(success=True, output=models_code, metadata={"files_created": ["backend/models.py"]})
    
    async def _write_services(self, action: Any, state: Any):
        """Generate service layer code."""
        services_code = '''"""Business logic services."""

class GreetingService:
    """Service for handling greetings."""
    
    def get_greeting(self, name: str = "World") -> str:
        """Generate personalized greeting."""
        return f"Hello {name}!"
    
    def get_formal_greeting(self, name: str) -> str:
        """Generate formal greeting."""
        return f"Good day, {name}."
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "backend/services.py",
                "content": services_code
            }
        })
        
        return Result(success=True, output=services_code, metadata={"files_created": ["backend/services.py"]})
    
    async def _write_tests(self, action: Any, state: Any):
        """Generate unit tests."""
        test_code = '''"""Unit tests for backend."""
import pytest
from app import app

@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test health endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_greeting_default(client):
    """Test greeting with default name."""
    response = client.get('/api/greeting')
    assert response.status_code == 200
    assert 'Hello World' in response.json['message']

def test_greeting_custom(client):
    """Test greeting with custom name."""
    response = client.get('/api/greeting?name=Alice')
    assert response.status_code == 200
    assert 'Hello Alice' in response.json['message']
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "backend/test_app.py",
                "content": test_code
            }
        })
        
        return Result(success=True, output=test_code, metadata={"files_created": ["backend/test_app.py"]})
    
    async def _setup_backend_structure(self, action: Any, state: Any):
        """Initialize backend project structure."""
        requirements_txt = '''Flask==2.3.0
Flask-CORS==4.0.0
pytest==7.4.0
python-dotenv==1.0.0
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "backend/requirements.txt",
                "content": requirements_txt
            }
        })
        
        return Result(success=True, output="Backend structure initialized", metadata={"files_created": ["backend/requirements.txt"]})
    
    async def _generate_backend_code(self, action: Any, state: Any):
        """Generic backend code generation."""
        description = action.description or "Backend code"
        
        code = f'''"""Generated backend code."""
# {description}

def main():
    """Main function."""
    print("Backend code generated")
    return True

if __name__ == '__main__':
    main()
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "backend/generated.py",
                "content": code
            }
        })
        
        return Result(success=True, output=code, metadata={"files_created": ["backend/generated.py"]})
