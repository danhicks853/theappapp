"""
Agent LLM Client

Wraps OpenAI Adapter to provide the interface agents expect.
Translates agent requests into OpenAI completion calls.

Reference: MVP Demo - Agent integration
"""
import json
import logging
from typing import Any, Dict, Optional

from backend.services.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)


class AgentLLMClient:
    """
    LLM client for agent interactions.
    
    Provides methods agents expect:
    - plan_next_action: Generate next step plan
    - evaluate_progress: Validate step completion
    
    Uses OpenAI Adapter for actual LLM calls.
    """
    
    def __init__(self, openai_adapter: OpenAIAdapter, default_model: str = "gpt-4o-mini"):
        """
        Initialize agent LLM client.
        
        Args:
            openai_adapter: OpenAI adapter instance
            default_model: Default model for completions
        """
        self.openai = openai_adapter
        self.default_model = default_model
        logger.info("Agent LLM client initialized")
    
    async def plan_next_action(
        self,
        task_state: Any,
        previous_action: Optional[Any] = None,
        previous_result: Optional[Any] = None,
        attempt: int = 0,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plan the next action for an agent.
        
        Args:
            task_state: Current task state
            previous_action: Previous action taken (if retry)
            previous_result: Result of previous action (if retry)
            attempt: Retry attempt number
            system_prompt: Agent's system prompt
        
        Returns:
            Dict with action plan including:
            - description: What to do
            - tool_name: Tool to use (if any)
            - operation: Specific operation
            - parameters: Operation parameters
            - reasoning: Why this action
        """
        # Build context
        context = self._build_planning_context(task_state, previous_action, previous_result, attempt)
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": f"""Plan the next action for this task.

Goal: {task_state.goal}

Current Progress:
- Step: {task_state.current_step}/{task_state.max_steps}
- Progress Score: {task_state.progress_score:.2f}

{context}

Respond with a JSON object:
{{
    "description": "Brief description of action",
    "tool_name": "tool to use (or null)",
    "operation": "specific operation (or null)", 
    "parameters": {{}},
    "reasoning": "Why this action will progress toward the goal"
}}"""
        })
        
        # Call OpenAI
        response = await self.openai.chat_completion(
            model=self.default_model,
            messages=messages,
            temperature=0.7
        )
        
        # Parse response
        content = response.choices[0].message.content
        try:
            action = json.loads(content)
            logger.debug(f"Planned action: {action.get('description', 'Unknown')}")
            return action
        except json.JSONDecodeError:
            # Fallback if not valid JSON
            logger.warning("LLM returned non-JSON response, creating default action")
            return {
                "description": content[:200],
                "tool_name": None,
                "operation": None,
                "parameters": {},
                "reasoning": content
            }
    
    async def evaluate_progress(
        self,
        task_state: Any,
        result: Any,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate if progress was made.
        
        Args:
            task_state: Current task state
            result: Result to evaluate
            system_prompt: Agent's system prompt
        
        Returns:
            Dict with validation result:
            - success: bool
            - issues: List[str]
            - metrics: Dict[str, Any]
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": f"""Evaluate if this action made progress toward the goal.

Goal: {task_state.goal}

Result:
Success: {result.success}
Output: {result.output}
Error: {result.error}

Respond with JSON:
{{
    "success": true/false,
    "issues": ["list", "of", "issues"],
    "metrics": {{"progress_score": 0.0 to 1.0}}
}}"""
        })
        
        response = await self.openai.chat_completion(
            model=self.default_model,
            messages=messages,
            temperature=0.3  # Lower temp for evaluation
        )
        
        content = response.choices[0].message.content
        try:
            validation = json.loads(content)
            return validation
        except json.JSONDecodeError:
            # Conservative fallback
            return {
                "success": result.success,
                "issues": [] if result.success else [result.error or "Unknown error"],
                "metrics": {"progress_score": 0.5 if result.success else 0.0}
            }
    
    def _build_planning_context(
        self,
        task_state: Any,
        previous_action: Optional[Any],
        previous_result: Optional[Any],
        attempt: int
    ) -> str:
        """Build context string for planning prompt."""
        context_parts = []
        
        if previous_action and previous_result:
            context_parts.append(f"Previous attempt #{attempt}:")
            context_parts.append(f"  Action: {previous_action.description}")
            context_parts.append(f"  Result: {'Success' if previous_result.success else 'Failed'}")
            if previous_result.error:
                context_parts.append(f"  Error: {previous_result.error}")
        
        if task_state.acceptance_criteria:
            context_parts.append("\nAcceptance Criteria:")
            for i, criterion in enumerate(task_state.acceptance_criteria, 1):
                context_parts.append(f"  {i}. {criterion}")
        
        if task_state.steps_history:
            context_parts.append(f"\nCompleted steps: {len(task_state.steps_history)}")
            if task_state.steps_history:
                last_step = task_state.steps_history[-1]
                context_parts.append(f"Last step: {last_step.reasoning}")
        
        return "\n".join(context_parts) if context_parts else "No prior context"
