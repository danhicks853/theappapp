"""DevOps Engineer Agent - Infrastructure, deployment, and CI/CD."""
from typing import Any
from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result

DEVOPS_ENGINEER_SYSTEM_PROMPT = """You are a DevOps engineer expert.

Expertise:
- Docker and containerization
- CI/CD pipelines (GitHub Actions, GitLab CI)
- Cloud platforms (AWS, GCP, Azure)
- Infrastructure as Code (Terraform, CloudFormation)
- Kubernetes and orchestration
- Monitoring and logging
- Database administration
- System reliability and scaling

Responsibilities:
1. Design deployment strategies
2. Write Dockerfiles and docker-compose
3. Create CI/CD pipeline configurations
4. Set up monitoring and alerting
5. Optimize infrastructure costs
6. Implement backup and disaster recovery

Output: Infrastructure configs, deployment scripts, monitoring setups.
"""

class DevOpsEngineerAgent(BaseAgent):
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, **kwargs):
        final_agent_type = kwargs.pop('agent_type', 'devops_engineer')
        super().__init__(agent_id=agent_id, agent_type=final_agent_type, orchestrator=orchestrator,
                         llm_client=llm_client, **kwargs)
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """Execute DevOps actions."""
        action_type = action.operation or action.tool_name or ""
        
        if action_type == "setup_deployment":
            return await self._setup_deployment(action, state)
        elif action_type == "create_cicd":
            return await self._create_cicd_pipeline(action, state)
        elif action_type == "write_dockerfile":
            return await self._write_dockerfile(action, state)
        else:
            return await self._generate_devops_config(action, state)
    
    async def _setup_deployment(self, action: Any, state: Any):
        """Create deployment configuration."""
        deploy_script = '''#!/bin/bash
# Deployment script

echo "Starting deployment..."

# Build containers
docker-compose build

# Start services
docker-compose up -d

echo "Deployment complete!"
echo "Frontend: http://localhost:8000"
echo "Backend: http://localhost:5000"
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "deploy.sh",
                "content": deploy_script
            }
        })
        
        return Result(success=True, output="Deployment configured", metadata={"files_created": ["deploy.sh"]})
    
    async def _create_cicd_pipeline(self, action: Any, state: Any):
        """Create CI/CD pipeline."""
        github_workflow = '''name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest tests/
          
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy
        run: ./deploy.sh
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": ".github/workflows/ci.yml",
                "content": github_workflow
            }
        })
        
        return Result(success=True, output="CI/CD pipeline created", metadata={"files_created": [".github/workflows/ci.yml"]})
    
    async def _write_dockerfile(self, action: Any, state: Any):
        """Create Dockerfile."""
        dockerfile = '''FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 5000

CMD ["python", "app.py"]
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "Dockerfile",
                "content": dockerfile
            }
        })
        
        return Result(success=True, output="Dockerfile created", metadata={"files_created": ["Dockerfile"]})
    
    async def _generate_devops_config(self, action: Any, state: Any):
        """Generate generic DevOps configuration."""
        docker_compose = '''version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "8000:8000"
    
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "docker-compose.yml",
                "content": docker_compose
            }
        })
        
        return Result(success=True, output="DevOps config created", metadata={"files_created": ["docker-compose.yml"]})
