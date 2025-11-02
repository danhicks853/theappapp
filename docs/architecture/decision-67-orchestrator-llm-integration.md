# Decision 67: Orchestrator LLM Integration Architecture

## Status
✅ **RESOLVED**  
**Date**: Nov 1, 2025  
**Priority**: P0 - BLOCKING

---

## Context

The orchestrator is the central coordinator in the hub-and-spoke architecture but currently lacks LLM reasoning capabilities. The orchestrator needs to make complex decisions including:

- When to escalate to humans (gate detection)
- Which specialist to involve for consultation
- How to decompose user requests into agent tasks
- When agents are stuck vs making progress
- Task sequencing and dependency management
- Vetting project decisions from PM with other agents

Without LLM integration, the orchestrator cannot make intelligent coordination decisions.

---

## Decision

### **1. Autonomy Level: Moderate with User-Configurable Slider**

**Implementation**:
- Default: Moderate autonomy (balanced approach)
- Frontend Settings: "Orchestrator Autonomy" slider with three levels
  - **Low**: Escalates frequently (design decisions, task failures, specialist consultations)
  - **Medium** (default): Escalates on significant issues (phase transitions, security concerns, 3-cycle loops)
  - **High**: Escalates only on critical blockers (unresolvable conflicts, mandatory approval gates)

**Rationale**:
- Flexibility per user preference and project type
- Aligns with "manual control with visibility" philosophy (Decision 5, Cost Management)
- Allows users to experiment and find optimal balance
- High autonomy for trusted experimental projects, low autonomy for critical production work

**Configuration Storage**: Database (user settings table)

---

### **2. Reasoning: Full Chain-of-Thought**

**Implementation**:
- Orchestrator uses full chain-of-thought reasoning for all coordination decisions
- Chain-of-thought visible in agent communication stream (frontend monitoring)
- Reasoning logged to database for debugging and learning
- RAG system can learn from orchestrator reasoning patterns

**Rationale**:
- Consistency with Decision 2 (all agents use chain-of-thought)
- Transparency in orchestrator decision-making
- Debugging capability - understand WHY orchestrator made choices
- Trust building - users see orchestrator's reasoning process
- Learning opportunity - future projects benefit from orchestrator patterns

**Trade-off**: Higher token costs for orchestrator operations, justified by quality and transparency

---

### **3. Context Management: Orchestrator-Centric with Filtered RAG**

**Implementation**:
- **Orchestrator Context** (full visibility):
  - Complete project state and history
  - All agent conversations and deliverables
  - Current phase and milestone progress
  - Pending tasks and dependencies
  - Project decisions and architecture
  
- **Agent Context** (minimal, task-specific):
  - Current task requirements only
  - Immediate dependencies for this task
  - Relevant project context (orchestrator-filtered)
  - No visibility into other agent tasks
  - No knowledge of overall project timeline

- **RAG Integration** (orchestrator-mediated):
  - Agents DO NOT query RAG directly
  - Orchestrator queries RAG for relevant knowledge
  - Orchestrator filters and injects RAG results into agent context
  - Orchestrator determines WHICH agent needs WHICH knowledge
  - Prevents duplicate queries and irrelevant information

**Rationale**:
- **Cost Optimization**: Agents don't carry bloated context (aligns with Decision 3)
- **Security**: Orchestrator controls what knowledge agents can access
- **Focus**: Agents stay laser-focused on current task only
- **Quality Control**: Orchestrator vets RAG results before providing to agents
- **Efficiency**: Single RAG query by orchestrator vs multiple by agents
- **Awareness**: Orchestrator maintains "who knows what" understanding

**Context Flow**:
```
1. Orchestrator receives task
2. Orchestrator queries RAG: "What patterns exist for [task type]?"
3. Orchestrator evaluates RAG results for relevance
4. Orchestrator constructs agent context: task + filtered RAG knowledge
5. Agent receives minimal context package
6. Agent completes task without RAG distraction
7. Orchestrator stores agent results for future RAG
```

---

### **4. Relationship with Project Manager Agent**

**Implementation**:
- **PM as Agent**: Project Manager is a specialized agent (spoke in hub-and-spoke)
- **PM Authority**: PM makes project design and strategy decisions
- **Orchestrator Role**: Coordinates execution, vets PM decisions with specialists
- **Decision Flow**: PM designs → Orchestrator vets → Orchestrator executes

**Vetting Process**:
```
PM creates project plan
→ Orchestrator reviews plan
→ Orchestrator identifies concerns (security, performance, feasibility)
→ Orchestrator consults relevant specialists (Security Expert, DevOps, Backend Dev)
→ Specialists provide feedback
→ Orchestrator routes feedback to PM
→ PM revises plan
→ Loop until orchestrator approves (or escalates to human)
→ Orchestrator begins execution with agents
```

**Rationale**:
- **Clear Separation**: PM = project strategy, Orchestrator = execution coordination
- **Hub-and-Spoke Maintained**: PM is an agent like others, not special case
- **Quality Assurance**: Orchestrator vets PM decisions before committing
- **Aligns with Decision 11**: Hierarchical decision flow through orchestrator
- **Specialist Input**: Security/DevOps can catch issues in design phase

**Example Scenario**:
```
Human: "Build a user authentication system"

1. Orchestrator → Workshopper: Gather requirements
2. Workshopper → Orchestrator: Requirements document
3. Orchestrator → PM: Create project plan
4. PM → Orchestrator: Plan with basic auth + session cookies
5. Orchestrator: Detects security implications
6. Orchestrator → Security Expert: Review auth design
7. Security → Orchestrator: "Recommend OAuth 2.0 + JWT tokens"
8. Orchestrator → PM: Security feedback
9. PM → Orchestrator: Revised plan with OAuth 2.0
10. Orchestrator: Approves plan, begins Backend Dev execution
```

---

## Orchestrator Prompt Architecture

### **Base System Prompt**

```
You are the Orchestrator, the central coordinator for autonomous software development.

Your role:
- Coordinate all agents in the hub-and-spoke architecture
- Make strategic decisions about task routing and agent assignments
- Vet project decisions with appropriate specialists
- Detect when human intervention is needed
- Manage project state and ensure progress

Your responsibilities:
- Maintain complete project awareness (state, history, progress)
- Route tasks to appropriate agents with minimal necessary context
- Query knowledge base for relevant patterns and inject into agent context
- Detect agent loops and progress vs identical failures
- Escalate to humans based on autonomy level and situation criticality

Your constraints:
- All agent communication flows through you (hub-and-spoke)
- You must use chain-of-thought reasoning for transparency
- You defer to Project Manager for project design decisions
- You vet PM decisions with specialists before execution
- You never send tasks directly between agents

Your approach:
- Strategic: Think several steps ahead
- Collaborative: Leverage specialist expertise
- Transparent: Show your reasoning process
- Adaptive: Learn from RAG knowledge base
- Prudent: Escalate when uncertain
```

### **Context Layer Template**

```
Current Project: {project_name}
Current Phase: {phase_name} ({phase_progress}%)
Autonomy Level: {low|medium|high}

Project State:
- Active Agent: {agent_name} working on {task_name}
- Completed Tasks: {completed_count}
- Pending Tasks: {pending_count}
- Recent Decisions: {recent_decision_summary}

Recent Agent Activity:
{last_3_agent_exchanges}

Available Agents:
{agent_roster_with_status}

RAG Context:
{relevant_patterns_from_knowledge_base}
```

### **Task Layer Template**

```
Decision Required: {decision_type}
Situation: {situation_description}
Options: {available_options}
Constraints: {relevant_constraints}
Urgency: {low|medium|high|critical}
```

### **Chain-of-Thought Format**

```
[ORCHESTRATOR REASONING]

1. Situation Analysis:
   - {analyze current situation}

2. Context Evaluation:
   - {evaluate available context and constraints}

3. Options Consideration:
   - Option A: {option} - Pros: {pros} - Cons: {cons}
   - Option B: {option} - Pros: {pros} - Cons: {cons}
   - [additional options]

4. RAG Knowledge Review:
   - {relevant patterns from similar situations}
   - {lessons learned from past projects}

5. Decision:
   - Chosen: {selected_option}
   - Rationale: {detailed reasoning}
   - Next Steps: {concrete actions}

6. Risk Assessment:
   - Potential Issues: {identified risks}
   - Mitigation: {how to handle if things go wrong}

[END REASONING]

[ACTION]: {specific action to take}
```

---

## Implementation Components

### **1. Orchestrator LLM Client**

```python
class OrchestratorLLMClient:
    """
    Handles orchestrator's LLM interactions with full context and reasoning.
    """
    
    def __init__(self, model: str, autonomy_level: str, token_logger: TokenLogger):
        self.model = model  # gpt-4.1 or gpt-5 recommended
        self.autonomy_level = autonomy_level  # low, medium, high
        self.token_logger = token_logger
        self.rag_client = RAGClient()
    
    async def make_decision(
        self,
        decision_type: str,
        project_context: ProjectContext,
        situation: dict
    ) -> OrchestratorDecision:
        """
        Make coordination decision with full chain-of-thought.
        """
        # Query RAG for relevant patterns
        rag_context = await self.rag_client.query_patterns(
            decision_type=decision_type,
            project_type=project_context.type
        )
        
        # Build full context prompt
        prompt = self._build_decision_prompt(
            project_context=project_context,
            situation=situation,
            rag_context=rag_context
        )
        
        # Get LLM response with chain-of-thought
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # Log tokens
        await self.token_logger.log(
            agent="orchestrator",
            model=self.model,
            tokens_input=response.usage.prompt_tokens,
            tokens_output=response.usage.completion_tokens,
            cost=self._calculate_cost(response.usage),
            decision_type=decision_type
        )
        
        # Parse and validate decision
        decision = self._parse_decision(response.choices[0].message.content)
        
        return decision
```

### **2. Autonomy Level Configuration**

```python
class AutonomyConfig:
    """
    Defines escalation thresholds based on autonomy level.
    """
    
    THRESHOLDS = {
        "low": {
            "task_failure": 1,  # Escalate after 1 failure
            "design_decision": True,  # Always escalate design choices
            "specialist_consult": True,  # Always ask before consulting
            "phase_transition": True,  # Always confirm phase completion
            "cost_alert": 50,  # Alert every $50 spent
        },
        "medium": {
            "task_failure": 2,  # Escalate after 2 failures
            "design_decision": False,  # Vet with specialists, don't escalate
            "specialist_consult": False,  # Auto-consult when needed
            "phase_transition": True,  # Confirm phase completion
            "cost_alert": 200,  # Alert every $200 spent
        },
        "high": {
            "task_failure": 3,  # Escalate only at loop (3 failures)
            "design_decision": False,  # Fully autonomous decisions
            "specialist_consult": False,  # Auto-consult as needed
            "phase_transition": False,  # Auto-approve phase transitions
            "cost_alert": 500,  # Alert every $500 spent
        }
    }
```

### **3. Configurable LLM Parameters (Temperature & Model Selection)**

**Implementation**:
- Per-agent temperature configuration (default: 0.3 for deterministic reasoning)
- Per-agent model selection (default: gpt-4o-mini for cost efficiency)
- Stored in database alongside autonomy level in user_settings or agent_configs table
- Configurable via frontend settings UI (Phase 2 frontend work)

**Temperature Guidelines**:
- **Orchestrator**: 0.3 (deterministic coordination decisions)
- **Backend/Frontend Developers**: 0.3-0.5 (predictable code generation)
- **PM/Workshopper**: 0.5-0.7 (creative ideation and planning)
- **QA Engineer**: 0.2 (consistent test generation)
- **Security Expert**: 0.2 (rigorous security analysis)

**Model Selection Guidelines**:
- **Default**: gpt-4o-mini (cost-effective for most tasks)
- **Complex Reasoning**: gpt-4o (orchestrator decisions, architecture planning)
- **Heavy Code Generation**: gpt-4o (backend/frontend complex features)
- **Simple Tasks**: gpt-4o-mini (documentation, simple CRUD, tests)

**Rationale**:
- Different agents require different creativity levels
- Cost optimization by using smaller models where appropriate
- User control over quality vs cost trade-off per agent
- Allows experimentation to find optimal settings per project type

**Storage Schema**:
```python
# agent_llm_configs table
{
    "agent_type": "orchestrator",
    "model": "gpt-4o-mini",
    "temperature": 0.3,
    "user_id": "user-123",
    "project_id": "project-456"  # optional: per-project overrides
}
```

**Frontend Implementation** (Phase 2):
- Settings page with agent-specific LLM configuration
- Sliders for temperature per agent type
- Dropdown for model selection per agent type
- Presets: "Cost Optimized", "Quality Optimized", "Balanced"
- API endpoints: GET/PUT `/api/v1/settings/agent-llm-config`

---

### **4. RAG-Mediated Context Injection**

```python
class ContextBuilder:
    """
    Builds minimal agent context with orchestrator-filtered RAG knowledge.
    """
    
    def __init__(self, rag_client: RAGClient):
        self.rag_client = rag_client
    
    async def build_agent_context(
        self,
        task: Task,
        agent_type: str,
        project_context: ProjectContext
    ) -> AgentContext:
        """
        Build minimal context package for agent.
        """
        # Query RAG for relevant knowledge
        rag_results = await self.rag_client.query(
            query=f"Best practices for {agent_type} on {task.type}",
            filters={"agent_type": agent_type, "task_type": task.type}
        )
        
        # Filter and validate RAG results
        relevant_knowledge = self._filter_rag_results(
            results=rag_results,
            task=task,
            agent_type=agent_type
        )
        
        # Build minimal context
        return AgentContext(
            task=task,
            project_name=project_context.name,
            current_phase=project_context.phase,
            relevant_knowledge=relevant_knowledge,
            # NO full project history
            # NO other agent tasks
            # NO pending work visibility
        )
```

### **5. PM Vetting Workflow**

```python
class PMVettingService:
    """
    Orchestrator service for vetting PM decisions with specialists.
    """
    
    async def vet_project_plan(
        self,
        project_plan: ProjectPlan,
        orchestrator: Orchestrator
    ) -> VettingResult:
        """
        Vet PM's project plan with relevant specialists.
        """
        concerns = self._identify_concerns(project_plan)
        
        # Consult specialists based on concerns
        specialist_feedback = []
        
        if concerns.has_security_implications:
            security_feedback = await orchestrator.consult_agent(
                agent_type="security_expert",
                question=f"Review this architecture: {project_plan.architecture}"
            )
            specialist_feedback.append(security_feedback)
        
        if concerns.has_performance_requirements:
            devops_feedback = await orchestrator.consult_agent(
                agent_type="devops_engineer",
                question=f"Review scalability of: {project_plan.architecture}"
            )
            specialist_feedback.append(devops_feedback)
        
        if concerns.has_complex_backend:
            backend_feedback = await orchestrator.consult_agent(
                agent_type="backend_developer",
                question=f"Feasibility check: {project_plan.technical_design}"
            )
            specialist_feedback.append(backend_feedback)
        
        # Aggregate feedback and decide
        return self._evaluate_feedback(specialist_feedback)
```

---

## Database Schema Additions

### **Orchestrator Decisions Table**

```sql
CREATE TABLE orchestrator_decisions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    decision_type VARCHAR(50) NOT NULL,
    situation JSONB NOT NULL,
    reasoning TEXT NOT NULL,  -- Chain-of-thought
    decision JSONB NOT NULL,  -- Actual decision made
    autonomy_level VARCHAR(10) NOT NULL,  -- low, medium, high
    rag_context JSONB,  -- RAG knowledge used
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    execution_result JSONB  -- What happened after decision
);

CREATE INDEX idx_orchestrator_decisions_project ON orchestrator_decisions(project_id);
CREATE INDEX idx_orchestrator_decisions_type ON orchestrator_decisions(decision_type);
CREATE INDEX idx_orchestrator_decisions_created ON orchestrator_decisions(created_at);
```

### **User Settings Table (Autonomy Configuration)**

```sql
CREATE TABLE user_settings (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, setting_key)
);

-- Example setting:
-- setting_key: "orchestrator_autonomy"
-- setting_value: {"level": "medium"}
```

---

## Testing Strategy

### **Unit Tests**

1. **Prompt Construction**: Test prompt building with various contexts
2. **Decision Parsing**: Test parsing of LLM responses into structured decisions
3. **Context Filtering**: Test RAG result filtering for relevance
4. **Autonomy Thresholds**: Test escalation triggers at each level

### **Integration Tests**

1. **RAG Integration**: Test orchestrator querying RAG and filtering results
2. **Agent Context Building**: Test minimal context package construction
3. **PM Vetting Workflow**: Test specialist consultation flow
4. **Autonomy Level Changes**: Test behavior changes when user adjusts slider

### **End-to-End Tests**

1. **Full Project Flow**: Test orchestrator coordinating complete project
2. **PM Decision Vetting**: Test orchestrator catching design issues
3. **Escalation Scenarios**: Test escalation at each autonomy level
4. **Knowledge Injection**: Test RAG knowledge improving agent performance

### **AI-Assisted Testing**

1. **Reasoning Quality**: AI evaluation agent assesses orchestrator chain-of-thought
2. **Decision Appropriateness**: AI evaluation of decision quality
3. **Context Relevance**: AI assessment of RAG filtering accuracy

---

## Implications

### **Enables**

- All agent coordination workflows
- Intelligent task routing and sequencing
- Automated specialist consultation
- Dynamic escalation based on user preference
- Knowledge-driven decision making
- PM decision quality assurance

### **Requires**

- Database schema updates (orchestrator_decisions, user_settings)
- Orchestrator prompt templates
- RAG integration for context injection
- Frontend settings page for autonomy slider
- Token logging for orchestrator operations
- Testing framework for orchestrator decisions

### **Trade-offs**

- **Higher Cost**: Full chain-of-thought increases token usage
- **Complexity**: Orchestrator becomes sophisticated LLM system
- **Development Time**: Significant implementation effort
- **Worth It**: Transparency, quality, and flexibility justify costs

---

## Dependencies

**Depends On**:
- Decision 1: OpenAI provider (orchestrator uses OpenAI)
- Decision 3: Context management (orchestrator-centric already decided)
- Decision 5: Manual control philosophy (autonomy slider aligns)

**Enables**:
- Decision 68: RAG System (orchestrator-mediated RAG design)
- Decision 70: Agent Collaboration (orchestrator routing)
- Decision 74: Loop Detection (orchestrator analyzes failures)
- All agent refactoring tasks (agents need orchestrator coordination)

---

## Next Steps

1. ✅ Document this decision (COMPLETE)
2. ⏭️ Update development tracker with orchestrator LLM tasks
3. ⏭️ Create orchestrator prompt templates
4. ⏭️ Design database schema for orchestrator decisions
5. ⏭️ Design frontend autonomy slider interface
6. ⏭️ Move to Decision 68: RAG System Architecture

---

## Notes

- This decision establishes orchestrator as intelligent coordinator, not just message router
- Orchestrator-mediated RAG is superior to direct agent RAG access
- Autonomy slider provides flexibility without architectural changes
- PM vetting workflow ensures design quality before implementation
- Chain-of-thought transparency builds trust and enables learning

---

*Decision resolved: Nov 1, 2025*
*Implementation priority: P0 - Required before any Phase 1 agent work*
