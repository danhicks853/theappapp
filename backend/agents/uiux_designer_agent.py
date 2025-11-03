"""UI/UX Designer Agent - User interface and user experience design."""
from typing import Any
from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result

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
        final_agent_type = kwargs.pop('agent_type', 'ui_ux_designer')
        super().__init__(agent_id=agent_id, agent_type=final_agent_type, orchestrator=orchestrator,
                         llm_client=llm_client, **kwargs)
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """Execute UI/UX design actions."""
        action_type = action.operation or action.tool_name or ""
        
        if action_type == "create_design_spec":
            return await self._create_design_spec(action, state)
        elif action_type == "design_components":
            return await self._design_components(action, state)
        else:
            return await self._generate_design_doc(action, state)
    
    async def _create_design_spec(self, action: Any, state: Any):
        """Create design specifications."""
        design_spec = '''# UI/UX Design Specification

## Design Goals
- Clean, modern interface
- Intuitive user experience
- Accessible to all users
- Mobile-responsive design

## Color Palette
- Primary: #667eea (Purple gradient start)
- Secondary: #764ba2 (Purple gradient end)
- Text: #333333
- Background: White
- Accent: Gradient from primary to secondary

## Typography
- Font Family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto
- Headings: 2.5rem, bold
- Body: 1rem, regular
- Buttons: 1.2rem, semi-bold

## Layout
- Centered card design
- Max width: 500px
- Padding: 3rem
- Border radius: 20px
- Box shadow for depth

## Interactive Elements
- Button with gradient background
- Hover effect: Lift with shadow
- Smooth animations (0.2-0.3s transitions)
- Modal popup with overlay

## Accessibility
- ARIA labels on interactive elements
- Keyboard navigation support
- High contrast ratios
- Focus indicators
- Screen reader friendly

## Responsive Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

## User Flow
1. User lands on page
2. Sees clear call-to-action button
3. Clicks button
4. Modal appears with message
5. User can close modal easily
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "design/design_spec.md",
                "content": design_spec
            }
        })
        
        return Result(success=True, output="Design specification created", metadata={"files_created": ["design/design_spec.md"]})
    
    async def _design_components(self, action: Any, state: Any):
        """Design component specifications."""
        components = '''# Component Design

## Button Component
**Purpose:** Primary call-to-action

**Visual Design:**
- Gradient background (purple)
- White text
- Rounded corners (50px)
- Padding: 1rem 2rem
- Font size: 1.2rem
- Shadow on hover

**States:**
- Default: Gradient background
- Hover: Lift effect + shadow
- Active: Press down effect
- Disabled: Reduced opacity

## Modal Component
**Purpose:** Display "Hello World" message

**Visual Design:**
- White card on dark overlay
- Centered on screen
- Border radius: 15px
- Animation: Pop-in effect
- Shadow: Deep shadow for elevation

**Structure:**
- Overlay (rgba(0,0,0,0.5))
- Content card (white background)
- Title (2rem, purple color)
- Body text
- Close button

## Container Component
**Purpose:** Main content wrapper

**Visual Design:**
- White background
- Centered on gradient background
- Border radius: 20px
- Max width: 500px
- Responsive width: 90% on mobile

## Accessibility Features
- All buttons have aria-labels
- Modal has role="dialog"
- Focus trap in modal
- Keyboard ESC to close
- High contrast text
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "design/components.md",
                "content": components
            }
        })
        
        return Result(success=True, output="Component designs created", metadata={"files_created": ["design/components.md"]})
    
    async def _generate_design_doc(self, action: Any, state: Any):
        """Generate design documentation."""
        ux_flow = '''# UX Flow Documentation

## User Journey
1. **Landing** - User arrives at application
2. **Discovery** - User sees welcoming interface
3. **Action** - User clicks prominent button
4. **Feedback** - Modal appears with message
5. **Completion** - User closes modal

## Usability Principles Applied
- **Clarity:** Clear button text and purpose
- **Feedback:** Visual response to user actions
- **Simplicity:** Single focused interaction
- **Accessibility:** Keyboard and screen reader support
- **Aesthetics:** Modern, professional design

## Design System
- Consistent spacing (rem units)
- Cohesive color palette
- Unified typography
- Smooth transitions
- Clear visual hierarchy

## Testing Recommendations
- Test on multiple devices
- Verify keyboard navigation
- Check screen reader compatibility
- Validate color contrast
- Test animations performance
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "design/ux_flow.md",
                "content": ux_flow
            }
        })
        
        return Result(success=True, output="UX flow documented", metadata={"files_created": ["design/ux_flow.md"]})
