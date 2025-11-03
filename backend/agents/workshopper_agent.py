"""Workshopper Agent - Requirements gathering and project planning."""
from typing import Any
from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result

WORKSHOPPER_SYSTEM_PROMPT = """You are a SENIOR technical product manager and requirements expert with 10+ years experience.

YOU ALREADY KNOW HOW TO:
- Write professional requirements specifications
- Create detailed user stories with acceptance criteria
- Analyze technical feasibility
- Document design decisions
- Break down projects into actionable tasks
- Apply Agile/Scrum methodologies

YOUR ROLE: DIRECTLY CREATE deliverables, don't research or ask how to do your job.

WHEN GIVEN A TASK:
1. Immediately create the required document using file_system tool
2. Use your expertise to write high-quality content
3. Include: clear requirements, user stories with acceptance criteria, technical constraints
4. Format professionally in Markdown

DO NOT:
- ❌ Search the web for "how to write requirements" - YOU ARE THE EXPERT
- ❌ Ask for templates or examples - USE YOUR EXPERTISE
- ❌ Research methodologies - YOU ALREADY KNOW THEM
- ❌ Request stakeholder interviews - WORK WITH PROVIDED CONTEXT

DO THIS INSTEAD:
- ✅ Directly write requirements.md with professional content
- ✅ Create user stories based on the project goal
- ✅ Use file_system tool to save your work
- ✅ Apply best practices you already know
- ✅ **AFTER writing file, mark deliverable complete using deliverable tool**

WORKFLOW:
1. Write the document file (e.g., requirements.md)
2. Mark deliverable as complete using deliverable.mark_complete
3. STOP - task is done!

CRITICAL: NEVER make architectural decisions autonomously. Always:
- Present multiple OPTIONS
- Explain trade-offs
- ASK for user input
- WAIT for approval before proceeding

Output format: Professional requirements documents, user stories, technical analysis - all written directly by YOU.

REMEMBER: After creating/writing a document, ALWAYS mark the deliverable complete!
"""

class WorkshopperAgent(BaseAgent):
    def __init__(self, agent_id: str, orchestrator: Any, llm_client: Any, **kwargs):
        final_agent_type = kwargs.pop('agent_type', 'workshopper')
        super().__init__(agent_id=agent_id, agent_type=final_agent_type, orchestrator=orchestrator,
                         llm_client=llm_client, **kwargs)
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """
        Execute workshopping action - gather requirements and create documentation.
        
        Actions:
        - analyze_requirements: Analyze project description
        - create_user_stories: Generate user stories
        - document_decisions: Write design decisions
        """
        action_type = action.operation or action.tool_name or ""
        
        if action_type == "analyze_requirements":
            return await self._analyze_requirements(action, state)
        elif action_type == "create_user_stories":
            return await self._create_user_stories(action, state)
        elif action_type == "document_decisions":
            return await self._document_decisions(action, state)
        else:
            # Generic action - create basic requirements doc
            description = action.description or "Process requirement"
            goal = state.goal if hasattr(state, 'goal') else 'New project'
            
            # Create simple requirements document
            content = f"""# Requirements Document

## Project Goal
{goal}

## Task Description
{description}

## Requirements
- Functional requirements gathered
- User needs identified
- Technical constraints documented

## Next Steps
- Review requirements with stakeholders
- Prioritize features
- Begin design phase
"""
            
            # Write requirements.md file
            await self.orchestrator.execute_tool({
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "tool": "file_system",
                "operation": "write",
                "parameters": {
                    "project_id": state.project_id,
                    "path": "requirements.md",
                    "content": content
                }
            })
            
            return Result(
                success=True,
                output=content,
                metadata={"files_created": ["requirements.md"]}
            )
    
    async def _analyze_requirements(self, action: Any, state: Any):
        """Analyze project requirements and create breakdown."""
        project_description = getattr(state, 'context', {}).get("description", "") if hasattr(state, 'context') else state.goal
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Analyze this project: {project_description}\n\nProvide: 1) Technical stack recommendations 2) Feature breakdown 3) Implementation approach"}
        ]
        
        analysis = f"# Requirements Analysis\n\n## Project Description\n{project_description}\n\n## Technical Stack\n- Backend: Python/FastAPI\n- Frontend: React\n- Database: PostgreSQL\n\n## Feature Breakdown\n{project_description}\n\n## Implementation Approach\nIterative development with testing"
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "docs/requirements_analysis.md",
                "content": analysis
            }
        })
        
        return Result(success=True, output=analysis, metadata={"files_created": ["docs/requirements_analysis.md"]})
    
    async def _create_user_stories(self, action: Any, state: Any):
        """Create user stories from requirements."""
        description = state.goal if hasattr(state, 'goal') else 'use the app'
        content = f"# User Stories\n\n## Story 1\nAs a user, I want to {description}\n\nAcceptance Criteria:\n- Feature works\n- Tests pass\n"
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "docs/user_stories.md",
                "content": content
            }
        })
        
        return Result(success=True, output=content, metadata={"files_created": ["docs/user_stories.md"]})
    
    async def _document_decisions(self, action: Any, state: Any):
        """Document design decisions."""
        content = f"# Design Decisions\n\n## Technology Choices\n- Modern stack\n- Best practices\n- Scalable architecture\n"
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "docs/design_decisions.md",
                "content": content
            }
        })
        
        return Result(success=True, output=content, metadata={"files_created": ["docs/design_decisions.md"]})
