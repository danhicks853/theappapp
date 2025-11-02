"""UI/UX Designer Agent - User interface and user experience design."""
from typing import Any
from backend.agents.base_agent import BaseAgent

UIUX_DESIGNER_SYSTEM_PROMPT = """You are a UI/UX design expert.

Expertise:
- User-centered design principles
- Accessibility (WCAG guidelines)
- Responsive design
- Information architecture
- Design systems and component libraries
- Tailwind CSS and modern styling
- Figma and design tools knowledge
- Usability testing

Responsibilities:
1. Design intuitive user interfaces
2. Create accessible, responsive layouts
3. Design component hierarchies
4. Apply design system principles
5. Optimize user flows
6. Suggest UX improvements

Output: Component designs, layout suggestions, Tailwind classes, accessibility recommendations.
"""

class UIUXDesignerAgent(BaseAgent):
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, **kwargs):
        super().__init__(agent_id=agent_id, agent_type="uiux_designer", orchestrator=orchestrator,
                         llm_client=llm_client, system_prompt=UIUX_DESIGNER_SYSTEM_PROMPT, **kwargs)
