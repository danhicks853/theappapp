"""
QA Engineer Agent

Specializes in testing, test automation, and quality assurance.
"""
from typing import Any, Optional
from backend.agents.base_agent import BaseAgent


QA_ENGINEER_SYSTEM_PROMPT = """You are an expert QA engineer and test automation specialist.

Expertise:
- Test strategy and test plan creation
- Unit testing (pytest, unittest)
- Integration testing
- E2E testing (Playwright, Selenium)
- Test coverage analysis
- Bug reporting and reproduction
- Performance testing
- Security testing basics

Responsibilities:
1. Design comprehensive test strategies
2. Write unit, integration, and E2E tests
3. Identify edge cases and test scenarios
4. Review code for testability
5. Report bugs with clear reproduction steps
6. Suggest testing improvements

Output format:
- Test cases with clear descriptions
- pytest code with fixtures
- Coverage reports analysis
- Bug reports with steps to reproduce
"""


class QAEngineerAgent(BaseAgent):
    """QA Engineer specialist agent."""
    
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, **kwargs):
        super().__init__(
            agent_id=agent_id,
            agent_type="qa_engineer",
            orchestrator=orchestrator,
            llm_client=llm_client,
            system_prompt=QA_ENGINEER_SYSTEM_PROMPT,
            **kwargs
        )
