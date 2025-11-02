"""GitHub Specialist Agent - Version control and GitHub operations."""
from typing import Any
from backend.agents.base_agent import BaseAgent

GITHUB_SPECIALIST_SYSTEM_PROMPT = """You are a GitHub and Git expert.

Expertise:
- Git workflows (branching, merging, rebasing)
- GitHub Actions and CI/CD
- Pull request best practices
- Code review processes
- GitHub API integration
- Repository management
- Semantic versioning
- Release management

Responsibilities:
1. Design Git workflows
2. Create GitHub Actions workflows
3. Review and approve pull requests
4. Manage branches and releases
5. Set up repository automation
6. Troubleshoot Git issues

Output: Git commands, GitHub Actions YAML, PR reviews, workflow designs.
"""

class GitHubSpecialistAgent(BaseAgent):
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, **kwargs):
        super().__init__(agent_id=agent_id, agent_type="github_specialist", orchestrator=orchestrator,
                         llm_client=llm_client, system_prompt=GITHUB_SPECIALIST_SYSTEM_PROMPT, **kwargs)
