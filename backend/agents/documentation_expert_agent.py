"""Documentation Expert Agent - Technical writing and documentation."""
from typing import Any
from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result

DOCUMENTATION_EXPERT_SYSTEM_PROMPT = """You are a technical documentation expert.

Expertise:
- API documentation (OpenAPI/Swagger)
- User guides and tutorials
- Architecture documentation
- README files
- Code comments and docstrings
- Markdown formatting
- Diagrams (Mermaid, PlantUML)
- Documentation maintenance

Responsibilities:
1. Write clear, comprehensive documentation
2. Create API reference docs
3. Write user-friendly tutorials
4. Document system architecture
5. Maintain consistency across docs
6. Generate code examples

Output: Well-structured markdown docs with examples and diagrams.
"""

class DocumentationExpertAgent(BaseAgent):
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, **kwargs):
        final_agent_type = kwargs.pop('agent_type', 'documentation_expert')
        super().__init__(agent_id=agent_id, agent_type=final_agent_type, orchestrator=orchestrator,
                         llm_client=llm_client, **kwargs)
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """Execute documentation actions."""
        action_type = action.operation or action.tool_name or ""
        
        if action_type == "write_readme":
            return await self._write_readme(action, state)
        elif action_type == "write_api_docs":
            return await self._write_api_docs(action, state)
        else:
            return await self._generate_documentation(action, state)
    
    async def _write_readme(self, action: Any, state: Any):
        """Create README file."""
        readme = '''# Hello World Web Application

A simple web application that displays a "Hello World" message with a modern UI.

## Features

- Clean, modern user interface
- Interactive button with popup
- Backend API with greeting endpoint
- Full test coverage
- Docker deployment ready

## Quick Start

### Prerequisites
- Python 3.8+
- Docker (optional)

### Running Locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Frontend:**
```bash
cd frontend
python -m http.server 8000
```

Visit: http://localhost:8000

### Running with Docker

```bash
docker-compose up
```

## API Documentation

### GET /api/greeting
Returns a greeting message.

**Parameters:**
- `name` (optional): Name to greet (default: "World")

**Response:**
```json
{
  "message": "Hello {name}!"
}
```

### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Testing

```bash
pytest tests/
```

## Project Structure

```
.
├── backend/           # Backend API
│   ├── app.py        # Flask application
│   ├── services.py   # Business logic
│   └── test_app.py   # Backend tests
├── frontend/         # Frontend UI
│   ├── index.html    # Main page
│   └── test_app.js   # Frontend tests
├── tests/            # Test suite
└── docker-compose.yml
```

## License

MIT License
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "README.md",
                "content": readme
            }
        })
        
        return Result(success=True, output="README created", metadata={"files_created": ["README.md"]})
    
    async def _write_api_docs(self, action: Any, state: Any):
        """Create API documentation."""
        api_docs = '''# API Documentation

## Base URL
```
http://localhost:5000/api
```

## Endpoints

### Greeting Endpoint

#### GET /greeting

Returns a personalized greeting message.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | Name to include in greeting (default: "World") |

**Example Request:**
```bash
curl http://localhost:5000/api/greeting?name=Alice
```

**Example Response:**
```json
{
  "message": "Hello Alice!"
}
```

**Status Codes:**
- `200 OK`: Success
- `500 Internal Server Error`: Server error

---

### Health Check

#### GET /health

Check if the API is running.

**Example Request:**
```bash
curl http://localhost:5000/api/health
```

**Example Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

## Error Handling

All errors return JSON with error details:

```json
{
  "error": "Error message",
  "status": 500
}
```

## CORS

CORS is enabled for all origins in development mode.
Configure appropriately for production.
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "docs/API.md",
                "content": api_docs
            }
        })
        
        return Result(success=True, output="API documentation created", metadata={"files_created": ["docs/API.md"]})
    
    async def _generate_documentation(self, action: Any, state: Any):
        """Generate generic documentation."""
        user_guide = '''# User Guide

## Getting Started

Welcome to the Hello World application!

### What This App Does

This is a simple web application that demonstrates:
- Modern web UI design
- Client-server communication
- RESTful API architecture

### How to Use

1. Open the application in your browser
2. Click the "Click Me!" button
3. See the "Hello World!" popup appear

### For Developers

- Backend: Flask API server
- Frontend: Vanilla HTML/CSS/JavaScript
- Tests: pytest and Jest
- Deployment: Docker-ready

## Support

For issues or questions, refer to the README.md file.
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "docs/USER_GUIDE.md",
                "content": user_guide
            }
        })
        
        return Result(success=True, output="User guide created", metadata={"files_created": ["docs/USER_GUIDE.md"]})
