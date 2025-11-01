# Decision 70: Agent Collaboration Protocol

## Status
✅ **RESOLVED**  
**Date**: Nov 1, 2025  
**Priority**: P0 - BLOCKING

---

## Context

The system uses a hub-and-spoke architecture where all communication flows through the orchestrator (Decision 4). However, agents frequently need input from other specialists:

- Backend developers need security reviews
- Frontend developers need API clarification from backend
- QA engineers need to collaborate with developers on bug fixes
- Any agent may need Project Manager clarification
- Developers need DevOps guidance on deployment

**Current Architecture**:
- **Decision 4**: No direct agent-to-agent communication
- **Decision 36**: "Agents can request orchestrator help from other agents"
- **Decision 67**: Orchestrator-mediated context sharing

**Problem**: The protocol for how agents request help, how orchestrator routes collaboration, and how context is shared between collaborating agents is undefined.

---

## Decision

### **1. Collaboration Request Protocol**

**Architecture**: Structured help request → Orchestrator routing → Specialist response → Orchestrator delivery

**Agent Help Request Format**:
```json
{
  "request_type": "agent_consultation",
  "requesting_agent": "frontend_developer",
  "question": "How is the User model structured? I need to know what fields are available.",
  "context": {
    "current_task": "Build user profile display",
    "specific_concern": "What user fields can I display in the UI?",
    "attempted_approaches": ["Checked API docs but unclear on nested fields"]
  },
  "suggested_agent": "backend_developer",  // OPTIONAL - Orchestrator always makes final decision
  "urgency": "normal",  // low, normal, high, critical
  "collaboration_id": "uuid"  // Orchestrator-generated for tracking
}
```

**Note**: Orchestrator ALWAYS decides which agent to consult, even if requesting agent suggests one.

**Orchestrator Response Format**:
```json
{
  "collaboration_id": "uuid",
  "status": "completed",  // pending, in_progress, completed, escalated
  "consulted_agent": "backend_developer",
  "response": {
    "answer": "User model has: id, username, email, profile_image_url, created_at, last_login, preferences (JSON)",
    "additional_context": "Preferences field contains theme, notifications, language settings",
    "code_reference": "models/user.py lines 15-42"
  },
  "suggested_next_steps": ["Display basic fields (username, email, profile_image)", "Parse preferences JSON for settings UI"]
}
```

**Note**: Simple and direct - orchestrator routes question, gets answer, returns to requester.

---

### **2. Collaboration Scenarios Catalog**

**Core Pattern** (applies to all scenarios):
```
1. Agent A has question
2. Agent A sends request to Orchestrator
3. Orchestrator decides which agent can answer
4. Orchestrator provides minimal context to Agent B
5. Agent B provides answer
6. Orchestrator delivers answer to Agent A
7. Agent A continues work
```

#### **Scenario 1: Model/Data Structure Questions**
```
Example: "Frontend needs to know User model structure"
  Frontend → Orchestrator: "What fields are in User model?"
  Orchestrator → Backend Dev: [provides context about frontend task]
  Backend Dev → Orchestrator: "User has id, username, email, profile_image_url..."
  Orchestrator → Frontend: [delivers answer]
```

#### **Scenario 2: Security Review**
```
Example: "Backend implements auth, needs security validation"
  Backend → Orchestrator: "Is this auth implementation secure?"
  Orchestrator → Security Expert: [provides auth code context]
  Security Expert → Orchestrator: "Vulnerabilities found: X, Y, Z..."
  Orchestrator → Backend: [delivers recommendations]
```

#### **Scenario 3: API Contract Clarification**
```
Example: "Frontend unclear on API endpoint behavior"
  Frontend → Orchestrator: "What does POST /users return on conflict?"
  Orchestrator → Backend Dev: [provides API context]
  Backend Dev → Orchestrator: "Returns 409 with existing user ID"
  Orchestrator → Frontend: [delivers answer]
```

#### **Scenario 4: Bug Debugging**
```
Example: "QA finds bug, needs developer input"
  QA → Orchestrator: "Login fails intermittently, need help debugging"
  Orchestrator → Backend Dev: [provides bug reproduction steps]
  Backend Dev → Orchestrator: "Race condition in session creation"
  Orchestrator → QA: [delivers diagnosis + fix approach]
```

#### **Scenario 5: Requirements Clarification**
```
Example: "Any agent unclear on requirements"
  Agent → Orchestrator: "Should pagination start at 0 or 1?"
  Orchestrator → PM: [provides context about pagination task]
  PM → Orchestrator: "Start at 1 for user-friendliness"
  Orchestrator → Agent: [delivers decision]
```

#### **Scenario 6: Infrastructure Questions**
```
Example: "Developer needs deployment guidance"
  Developer → Orchestrator: "How should I structure Docker volumes?"
  Orchestrator → DevOps: [provides deployment context]
  DevOps → Orchestrator: "Use named volumes for persistence..."
  Orchestrator → Developer: [delivers guidance]
```

---

### **3. Context Sharing Protocol**

**Principle**: Orchestrator curates and filters context for efficient collaboration

**Context Package Structure**:
```python
class CollaborationContext:
    """
    Context package orchestrator provides to specialist agent.
    """
    collaboration_id: str
    requesting_agent: str
    consultation_reason: str
    
    # Task-specific context
    current_task: str
    relevant_files: List[str]
    code_snippets: List[CodeSnippet]
    error_messages: List[str]
    attempted_solutions: List[str]
    
    # Filtered project context (orchestrator-curated)
    project_type: str
    tech_stack: List[str]
    relevant_architecture_decisions: List[str]
    
    # RAG knowledge (orchestrator-injected)
    similar_past_collaborations: List[RAGResult]
    best_practices: List[str]
    
    # NO FULL PROJECT HISTORY
    # NO UNRELATED AGENT TASKS
    # NO SENSITIVE INFORMATION UNLESS RELEVANT
```

**Context Flow**:
```
1. Agent A requests help with minimal context
2. Orchestrator enriches context:
   - Queries RAG for similar past collaborations
   - Adds relevant architecture decisions
   - Filters project information for relevance
   - Removes sensitive data unless necessary
3. Orchestrator builds specialist context package
4. Specialist Agent B receives curated context only
5. Specialist responds with focused answer
6. Orchestrator synthesizes response for Agent A
7. Orchestrator stores collaboration for future RAG
```

**Context Principles**:
- **Minimal by default**: Only what's needed for this specific question
- **Orchestrator decides**: Always curates context, no full project dumps
- **Task-focused**: Context relevant to the specific question only
- **RAG-enhanced**: Past collaboration patterns included when relevant

---

### **4. Collaboration Loop Management**

**Loop Detection Algorithm**:
```python
class CollaborationLoopDetector:
    """
    Detects when collaboration is stuck in unproductive loop.
    """
    
    def detect_loop(
        self,
        collaboration_history: List[CollaborationExchange]
    ) -> LoopStatus:
        """
        Analyze collaboration exchanges for loop patterns.
        """
        # Check for identical questions
        if self._has_identical_questions(collaboration_history, window=3):
            return LoopStatus.IDENTICAL_LOOP
        
        # Check for circular dependencies
        if self._has_circular_reasoning(collaboration_history):
            return LoopStatus.CIRCULAR_LOOP
        
        # Check for progress
        if self._has_progress_indicators(collaboration_history):
            return LoopStatus.MAKING_PROGRESS
        
        # Check iteration count
        if len(collaboration_history) >= self.max_iterations:
            return LoopStatus.ITERATION_LIMIT
        
        return LoopStatus.HEALTHY
```

**Loop Categories**:

1. **Identical Question Loop**
   - Same agent asks same question 3+ times
   - Same specialist provides same answer
   - No observable progress
   - **Action**: Escalate to human with full history

2. **Circular Dependency Loop**
   - Agent A needs answer from Agent B
   - Agent B needs answer from Agent A
   - Neither can proceed
   - **Action**: Orchestrator identifies missing information, escalates if needed

3. **Multi-Agent Stall**
   - Multiple agents collaborating but no progress
   - Questions asked but not resolved
   - Iteration count exceeds threshold (5 exchanges)
   - **Action**: Orchestrator escalates with root cause analysis

4. **Progress vs Iteration**
   - Many exchanges but clear progress indicators
   - Different questions each iteration
   - Incremental improvements visible
   - **Action**: Allow continuation, monitor closely

**Loop Thresholds**:
```python
COLLABORATION_LIMITS = {
    "max_exchanges_per_collaboration": 5,  # Total back-and-forth
    "max_identical_questions": 2,  # Same question repeated
    "max_active_collaborations_per_agent": 3,  # Concurrent collaborations
    "escalation_after_loops": 1,  # Escalate after detecting 1 loop
}
```

---

### **5. Collaboration Tracking & Logging**

**Database Schema**:
```sql
-- Collaboration sessions
CREATE TABLE agent_collaborations (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    requesting_agent VARCHAR(50) NOT NULL,
    specialist_agent VARCHAR(50) NOT NULL,
    consultation_reason VARCHAR(100) NOT NULL,
    urgency VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- pending, active, completed, escalated
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    escalated BOOLEAN DEFAULT FALSE,
    escalation_reason TEXT
);

-- Individual exchanges within collaboration
CREATE TABLE collaboration_exchanges (
    id UUID PRIMARY KEY,
    collaboration_id UUID REFERENCES agent_collaborations(id),
    exchange_number INTEGER NOT NULL,
    from_agent VARCHAR(50) NOT NULL,
    to_agent VARCHAR(50) NOT NULL,
    message_type VARCHAR(50) NOT NULL,  -- question, response, clarification
    message_content JSONB NOT NULL,
    context_provided JSONB,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Collaboration outcomes for learning
CREATE TABLE collaboration_outcomes (
    id UUID PRIMARY KEY,
    collaboration_id UUID REFERENCES agent_collaborations(id),
    outcome_type VARCHAR(50) NOT NULL,  -- successful, escalated, loop_detected
    resolution_summary TEXT NOT NULL,
    success_rating INTEGER,  -- 1-5 from requesting agent
    lessons_learned TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Loop detection tracking
CREATE TABLE collaboration_loops (
    id UUID PRIMARY KEY,
    collaboration_id UUID REFERENCES agent_collaborations(id),
    loop_type VARCHAR(50) NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    loop_evidence JSONB NOT NULL,  -- What pattern was detected
    resolution VARCHAR(50) NOT NULL,  -- escalated, resolved, continued
    resolution_notes TEXT
);

CREATE INDEX idx_collaborations_project ON agent_collaborations(project_id);
CREATE INDEX idx_collaborations_status ON agent_collaborations(status);
CREATE INDEX idx_collaborations_agents ON agent_collaborations(requesting_agent, specialist_agent);
CREATE INDEX idx_exchanges_collaboration ON collaboration_exchanges(collaboration_id);
CREATE INDEX idx_loops_collaboration ON collaboration_loops(collaboration_id);
```

**Metrics Tracked**:
- Collaboration frequency per agent pair
- Average exchanges per collaboration
- Success rate by consultation type
- Loop detection rate
- Cost per collaboration
- Response time from specialists
- Agent satisfaction ratings

**RAG Storage**:
After successful collaboration:
```python
# Store in Qdrant for future learning
collaboration_document = {
    "type": "agent_collaboration",
    "scenario": consultation_reason,
    "agents_involved": [requesting_agent, specialist_agent],
    "question_summary": question,
    "resolution_summary": specialist_response,
    "outcome": "successful",
    "lessons_learned": lessons,
    "embedding": generate_embedding(full_collaboration)
}
qdrant_client.upsert(collaboration_document)
```

---

## Implementation Components

### **1. CollaborationOrchestrator Service**

```python
class CollaborationOrchestrator:
    """
    Orchestrator service managing agent-to-agent collaboration.
    """
    
    def __init__(
        self,
        orchestrator: Orchestrator,
        loop_detector: CollaborationLoopDetector,
        context_builder: ContextBuilder,
        db: Database
    ):
        self.orchestrator = orchestrator
        self.loop_detector = loop_detector
        self.context_builder = context_builder
        self.db = db
    
    async def request_specialist_help(
        self,
        request: CollaborationRequest
    ) -> CollaborationResponse:
        """
        Handle specialist consultation request from agent.
        """
        # Create collaboration session
        collaboration = await self._create_collaboration(request)
        
        # Check loop conditions
        loop_status = await self._check_for_loops(request.requesting_agent)
        if loop_status.is_loop:
            return await self._escalate_collaboration(
                collaboration,
                reason=loop_status.description
            )
        
        # Orchestrator decides which agent to consult
        selected_agent = await self._select_agent(request)
        
        # Build minimal context package for selected agent
        context = await self.context_builder.build_collaboration_context(
            request=request,
            target_agent=selected_agent
        )
        
        # Route to selected agent
        agent_response = await self.orchestrator.consult_agent(
            agent_type=selected_agent,
            context=context,
            question=request.question
        )
        
        # Log exchange
        await self._log_exchange(
            collaboration=collaboration,
            from_agent=request.requesting_agent,
            to_agent=selected_agent,
            response=agent_response
        )
        
        # Deliver response to requesting agent
        final_response = CollaborationResponse(
            collaboration_id=collaboration.id,
            consulted_agent=selected_agent,
            answer=agent_response.answer,
            suggested_next_steps=agent_response.next_steps
        )
        
        # Store for RAG
        await self._store_collaboration_for_learning(
            collaboration=collaboration,
            outcome=final_response
        )
        
        return final_response
    
    async def _select_agent(
        self,
        request: CollaborationRequest
    ) -> str:
        """
        Orchestrator ALWAYS decides which agent to consult.
        Requesting agent's suggestion is considered but not binding.
        """
        # Use orchestrator LLM to decide best agent
        selected_agent = await self.orchestrator.llm_client.make_decision(
            decision_type="agent_selection",
            situation={
                "question": request.question,
                "requesting_agent": request.requesting_agent,
                "suggested_agent": request.suggested_agent,  # Optional hint
                "context": request.context
            }
        )
        
        return selected_agent.selected_agent
```

### **2. Loop Detection Service**

```python
class CollaborationLoopDetector:
    """
    Detects unproductive collaboration loops.
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    async def check_for_loops(
        self,
        agent_id: str,
        project_id: str
    ) -> LoopStatus:
        """
        Check if agent is currently in collaboration loop.
        """
        # Get recent collaboration history
        recent_collaborations = await self.db.query(
            """
            SELECT c.*, array_agg(e.*) as exchanges
            FROM agent_collaborations c
            LEFT JOIN collaboration_exchanges e ON e.collaboration_id = c.id
            WHERE c.requesting_agent = $1
              AND c.project_id = $2
              AND c.created_at > NOW() - INTERVAL '1 hour'
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT 10
            """,
            agent_id, project_id
        )
        
        # Check for identical question patterns
        identical_count = self._count_identical_questions(recent_collaborations)
        if identical_count >= 3:
            return LoopStatus(
                is_loop=True,
                loop_type="identical_questions",
                description=f"Agent asked same question {identical_count} times"
            )
        
        # Check for circular dependencies
        if self._detect_circular_dependency(recent_collaborations):
            return LoopStatus(
                is_loop=True,
                loop_type="circular_dependency",
                description="Agents waiting on each other"
            )
        
        # Check active collaboration count
        active_count = len([c for c in recent_collaborations if c['status'] == 'active'])
        if active_count > COLLABORATION_LIMITS['max_active_collaborations_per_agent']:
            return LoopStatus(
                is_loop=True,
                loop_type="too_many_concurrent",
                description=f"Agent has {active_count} active collaborations"
            )
        
        return LoopStatus(is_loop=False)
    
    def _count_identical_questions(
        self,
        collaborations: List[dict]
    ) -> int:
        """
        Count how many times similar questions were asked.
        """
        questions = [c['question'] for c in collaborations]
        
        # Use semantic similarity
        from sklearn.metrics.pairwise import cosine_similarity
        embeddings = [generate_embedding(q) for q in questions]
        
        max_identical = 0
        for i, emb1 in enumerate(embeddings):
            identical_count = 1
            for j, emb2 in enumerate(embeddings[i+1:]):
                similarity = cosine_similarity([emb1], [emb2])[0][0]
                if similarity > 0.95:  # Threshold for "identical"
                    identical_count += 1
            max_identical = max(max_identical, identical_count)
        
        return max_identical
```

### **3. Context Builder for Collaboration**

```python
class CollaborationContextBuilder:
    """
    Builds curated context packages for specialist consultations.
    """
    
    async def build_collaboration_context(
        self,
        request: CollaborationRequest,
        specialist_type: str,
        project: Project
    ) -> CollaborationContext:
        """
        Build minimal context package for specialist.
        """
        # Query RAG for similar past collaborations
        similar_collaborations = await self.rag_client.query(
            query=f"{specialist_type} consultation for {request.consultation_reason}",
            filters={
                "type": "agent_collaboration",
                "specialist_agent": specialist_type,
                "consultation_reason": request.consultation_reason
            },
            limit=3
        )
        
        # Get relevant architecture decisions
        relevant_decisions = await self._get_relevant_decisions(
            specialist_type=specialist_type,
            project=project
        )
        
        # Build context package
        return CollaborationContext(
            collaboration_id=request.collaboration_id,
            requesting_agent=request.requesting_agent,
            consultation_reason=request.consultation_reason,
            
            # Request-specific
            current_task=request.context.get('current_task'),
            relevant_files=request.context.get('relevant_files', []),
            specific_concern=request.context.get('specific_concern'),
            attempted_approaches=request.context.get('attempted_approaches', []),
            
            # Orchestrator-curated
            project_type=project.type,
            tech_stack=project.tech_stack,
            relevant_architecture_decisions=relevant_decisions,
            
            # RAG-enhanced
            similar_past_collaborations=similar_collaborations,
            best_practices=await self._get_best_practices(specialist_type)
        )
```

---

## Orchestrator Prompt Additions

### **Orchestrator Agent Selection Prompt**

```
You are routing an agent consultation request.

Requesting Agent: {requesting_agent}
Question: {question}
Suggested Agent (optional): {suggested_agent}

Available Agents:
- Security Expert: Security reviews, vulnerability assessment, auth/auth
- Backend Developer: API design, database schema, business logic, models
- Frontend Developer: UI/UX, client-side logic, API integration
- DevOps Engineer: Infrastructure, deployment, CI/CD, monitoring
- QA Engineer: Test strategy, bug analysis, quality assurance
- Project Manager: Requirements clarification, priority decisions

[REASONING]
1. Analyze the question - what information is needed?
2. Determine which agent has this knowledge
3. Consider suggested agent but make independent decision
4. Choose single best agent (no multi-agent unless absolutely necessary)

[DECISION]
Selected Agent: {agent_name}
Rationale: {why this agent can answer the question}
[END]
```

---

## Testing Strategy

### **Unit Tests**

1. **Request Format Validation**: Test collaboration request parsing
2. **Context Building**: Test context package construction with various inputs
3. **Loop Detection**: Test identical question detection algorithm
4. **Specialist Selection**: Test auto-selection logic with various scenarios
5. **Response Synthesis**: Test orchestrator response formatting

### **Integration Tests**

1. **Full Collaboration Flow**: Test request → routing → response → delivery
2. **Multi-Agent Collaboration**: Test complex debugging scenarios
3. **Loop Detection Integration**: Test loop detection triggering escalation
4. **RAG Integration**: Test past collaboration retrieval
5. **Database Persistence**: Test collaboration logging and retrieval

### **End-to-End Tests**

1. **Security Review Scenario**: Backend requests security expert help
2. **API Clarification Scenario**: Frontend clarifies backend API
3. **Bug Debugging Scenario**: QA collaborates with developer
4. **Loop Detection Scenario**: Trigger loop and verify escalation
5. **Multi-Specialist Scenario**: Complex issue requiring multiple consultations

### **AI-Assisted Testing**

1. **Context Relevance**: AI evaluates if context packages are appropriate
2. **Response Quality**: AI assesses specialist response helpfulness
3. **Loop Pattern Recognition**: AI validates loop detection accuracy

---

## Implications

### **Enables**

- Effective agent specialization without information silos
- Security reviews for all authentication/authorization code
- Cross-domain debugging and problem solving
- Quality assurance through specialist consultation
- Knowledge sharing without direct agent communication
- Loop detection prevents infinite collaboration cycles

### **Requires**

- Database schema for collaboration tracking
- Orchestrator routing logic implementation
- Context builder service for curated packages
- Loop detection algorithm
- RAG integration for past collaboration learning
- Frontend visibility into active collaborations
- Cost tracking for collaboration overhead

### **Trade-offs**

- **Added Latency**: Consultation adds time to task completion
- **Token Overhead**: Routing and context building increase token usage
- **Simplicity**: Keep it simple - question → route → answer → deliver
- **Worth It**: Quality improvements justify overhead, prevents rework and bugs

---

## Token Tracking

**Every collaboration logs**:
- Tokens used in request
- Tokens used in orchestrator routing decision
- Tokens used in agent response
- Tokens used in final delivery

**Cost calculation**: Handled by cost matrix system (Decision 75)

**Note**: Token usage tracked per call, cost calculated based on model pricing matrix.

---

## Dependencies

**Depends On**:
- Decision 4: Coordinator-only communication (architecture foundation)
- Decision 36: Agent collaboration enabled (requirement statement)
- Decision 67: Orchestrator LLM integration (routing intelligence)
- Decision 68: RAG system (past collaboration learning)

**Enables**:
- All Phase 2 specialist agents (need collaboration capability)
- Phase 3 debugging workflows (multi-agent debugging)
- Quality assurance processes (security reviews, code reviews)
- Agent learning system (collaboration outcomes stored in RAG)

---

## Next Steps

1. ✅ Document this decision (COMPLETE)
2. ⏭️ Update development tracker with collaboration protocol tasks
3. ⏭️ Design collaboration request UI in frontend
4. ⏭️ Implement CollaborationOrchestrator service
5. ⏭️ Implement loop detection algorithm
6. ⏭️ Create collaboration tracking database schema
7. ⏭️ Move to Decision 71: Tool Access Service Architecture

---

## Notes

- Hub-and-spoke architecture maintained - no direct agent communication
- Orchestrator provides intelligent routing and context curation
- Loop detection prevents infinite consultation cycles
- Cost is justified by quality improvements and bug prevention
- Past collaborations become learning material in RAG
- Collaboration is asynchronous - specialists don't block other work
- Frontend dashboard shows active collaborations for transparency

---

*Decision resolved: Nov 1, 2025*  
*Implementation priority: P0 - Required for all agent collaboration workflows*
