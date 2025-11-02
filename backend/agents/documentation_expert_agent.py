"""Documentation Expert Agent - Technical writing and documentation."""
from typing import Any
from backend.agents.base_agent import BaseAgent

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
        super().__init__(agent_id=agent_id, agent_type="documentation_expert", orchestrator=orchestrator,
                         llm_client=llm_client, system_prompt=DOCUMENTATION_EXPERT_SYSTEM_PROMPT, **kwargs)
