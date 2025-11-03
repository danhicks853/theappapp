"""
Agent LLM Client

Wraps OpenAI Adapter to provide the interface agents expect.
Translates agent requests into OpenAI completion calls.

Reference: MVP Demo Plan - Agent coordination
"""
import json
import logging
from typing import Any, Dict, Optional

from backend.services.openai_adapter import OpenAIAdapter
from backend.models.agent_state import LLMCall

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
    
    def _get_available_tools(self, task_state: Any) -> str:
        """
        Get list of available tools with parameter schemas.
        
        Returns formatted string of tools, operations, and required parameters.
        """
        # Get project_id and task_id from state
        project_id = getattr(task_state, 'project_id', 'PROJECT_ID')
        task_id = getattr(task_state, 'task_id', 'TASK_ID')
        
        tools_help = f"""
file_system:
  - write: Create or update a file
    Parameters: {{"project_id": "{project_id}", "task_id": "{task_id}", "path": "filename.ext", "content": "file content"}}
  - read: Read a file
    Parameters: {{"project_id": "{project_id}", "task_id": "{task_id}", "path": "filename.ext"}}
  - list: List files in directory
    Parameters: {{"project_id": "{project_id}", "task_id": "{task_id}", "path": "directory/"}}
  - delete: Delete a file
    Parameters: {{"project_id": "{project_id}", "task_id": "{task_id}", "path": "filename.ext"}}

web_search:
  - search: Search the web
    Parameters: {{"query": "search terms", "num_results": 10}}

deliverable:
  - mark_complete: Mark current deliverable as complete
    Parameters: {{"deliverable_id": "{task_id}", "status": "completed"}}
  - get_status: Get deliverable status
    Parameters: {{"deliverable_id": "{task_id}"}}

IMPORTANT: Always include project_id and task_id for file_system operations!
"""
        return tools_help.strip()
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """
        Calculate cost in USD based on tokens and model.
        
        Pricing (as of 2024):
        - gpt-4o: $0.0025 / 1K prompt, $0.010 / 1K completion
        - gpt-4o-mini: $0.00015 / 1K prompt, $0.0006 / 1K completion
        - gpt-4: $0.03 / 1K prompt, $0.06 / 1K completion
        
        Using average for simplicity (prompt + completion / 2)
        """
        pricing = {
            "gpt-4o": 0.00625,  # Average of prompt + completion
            "gpt-4o-mini": 0.000375,  # Average
            "gpt-4": 0.045,  # Average
            "gpt-3.5-turbo": 0.0015,  # Average
        }
        
        # Get rate or use gpt-4o-mini as default
        rate_per_1k = pricing.get(model, pricing["gpt-4o-mini"])
        
        # Calculate cost
        return (tokens / 1000.0) * rate_per_1k
    
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
        
        # Get available tools for this agent
        available_tools = self._get_available_tools(task_state)
        
        messages.append({
            "role": "user",
            "content": f"""Plan the next action for this task.

Goal: {task_state.goal}

Current Progress:
- Step: {task_state.current_step}/{task_state.max_steps}
- Progress Score: {task_state.progress_score:.2f}

{context}

AVAILABLE TOOLS (use ONLY these):
{available_tools}

IMPORTANT: Only use tool_name from the list above, or set to null for actions without tools.

Respond with a JSON object:
{{
    "description": "Brief description of action",
    "tool_name": "tool to use from AVAILABLE TOOLS (or null)",
    "operation": "specific operation (or null)", 
    "parameters": {{}},
    "reasoning": "Why this action will progress toward the goal"
}}"""
        })
        
        # Get agent info from task_state for logging
        agent_name = "Unknown Agent"
        if hasattr(task_state, 'agent_id'):
            agent_name = task_state.agent_id.split('-')[0].title() if task_state.agent_id else "Unknown Agent"
        
        # Log only USER prompts (skip system - we know those from config)
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        if user_messages:
            prompt_output = "=" * 80 + "\n"
            prompt_output += f"🔵 ORCHESTRATOR → {agent_name.upper()}\n"
            prompt_output += "=" * 80 + "\n"
            for msg in user_messages:
                prompt_output += msg.get("content", "") + "\n"
            prompt_output += "=" * 80 + "\n"
            
            logger.info(prompt_output)
            print(prompt_output)  # Also print to console
        
        # Call OpenAI
        response = await self.openai.chat_completion(
            model=self.default_model,
            messages=messages,
            temperature=0.7
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        # Collect metadata for cost tracking
        tokens_used = getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
        cost_usd = self._calculate_cost(tokens_used, self.default_model)
        
        # Create LLMCall record for tracking
        llm_call = LLMCall(
            prompt=str([msg for msg in messages if msg.get("role") == "user"]),
            response=content,
            tokens_used=tokens_used,
            cost_usd=cost_usd
        )
        
        # Add to task state if available
        if hasattr(task_state, 'llm_calls'):
            task_state.llm_calls.append(llm_call)
        
        # Log the actual response (to logger AND console)
        response_output = "=" * 80 + "\n"
        response_output += f"🤖 {agent_name.upper()} → ORCHESTRATOR\n"
        response_output += "=" * 80 + "\n"
        response_output += content + "\n"
        response_output += "-" * 80 + "\n"
        response_output += f"💰 Tokens: {tokens_used} | Cost: ${cost_usd:.6f}\n"
        response_output += "=" * 80 + "\n"
        
        logger.info(response_output)
        print(response_output)  # Also print to console
        
        try:
            action = json.loads(content)
            logger.info(f"✅ Parsed action: {action.get('description', 'Unknown')}")
            return action
        except json.JSONDecodeError:
            # Fallback if not valid JSON
            logger.warning("⚠️ LLM returned non-JSON response, creating default action")
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
