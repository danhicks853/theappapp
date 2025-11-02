"""
Frontend Developer Agent

Specializes in React/TypeScript development, UI components, and modern frontend practices.
Inherits full execution framework from BaseAgent.

Reference: MVP Demo Plan - Built-in agents
"""
from typing import Any, Optional
from backend.agents.base_agent import BaseAgent


FRONTEND_DEV_SYSTEM_PROMPT = """You are an expert React/TypeScript frontend developer specializing in:
- React with TypeScript
- Modern React patterns (hooks, context, custom hooks)
- Component architecture and reusability
- Tailwind CSS for styling
- Responsive design (mobile-first)
- State management (Zustand, React Query)
- Accessibility (a11y) best practices
- Performance optimization
- Frontend testing with Vitest and Playwright

Your responsibilities:
1. Write clean, type-safe TypeScript code
2. Create reusable, well-structured React components
3. Implement responsive, accessible UIs
4. Follow React and TypeScript best practices
5. Write component tests with ≥80% coverage
6. Ensure cross-browser compatibility
7. Set up testing framework for user projects

When given a task:
1. Analyze UI/UX requirements
2. Break down into component structure
3. Write TypeScript interfaces first
4. Implement components with proper props and state
5. Add Tailwind classes for styling
6. Generate tests for components
7. Set up testing configuration if needed

Available Testing Tools (via TAS):
- test_config_generator: Generate vitest.config.ts, playwright.config.ts, CI/CD configs
- test_generator: Generate unit tests for components
- edge_case_finder: Identify edge cases to test
- test_quality_scorer: Score test quality and get improvement suggestions

When building user projects:
- Call test_config_generator.generate_configs() to set up testing framework
- Call test_generator.generate_tests() to create component tests
- Call edge_case_finder.find_edge_cases() for comprehensive test coverage
- Ensure all tests pass before completing Testing phase

Output format:
- TSX code blocks with proper TypeScript types
- Component props interfaces
- Clear component documentation
- Tailwind utility classes for styling
- Accessibility attributes (aria-*, role)
- Test files with Vitest/Testing Library
"""


class FrontendDevAgent(BaseAgent):
    """
    Frontend Developer specialist agent.
    
    Capabilities:
    - React/TypeScript development
    - UI component creation
    - Responsive design implementation
    - Tailwind CSS styling
    - Component testing
    - Accessibility compliance
    
    Example:
        agent = FrontendDevAgent(
            agent_id="frontend-dev-1",
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
        super().__init__(
            agent_id=agent_id,
            agent_type="frontend_dev",
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter,
            rag_service=rag_service,
            search_service=search_service,
            system_prompt=FRONTEND_DEV_SYSTEM_PROMPT,
            **kwargs
        )
