# TheAppApp Development Task Tracker

## Overview
This document tracks all development tasks derived from our 6-phase planning. Each task is marked as TODO, IN_PROGRESS, or COMPLETED as we work through the implementation.

---

## Phase 1: Core Architecture Implementation

### 1.1 Orchestrator Core System
**Reference**: Foundation for Decision 67 implementation

- [x] **COMPLETED**: Design orchestrator class architecture with hub-and-spoke pattern
  - **File**: `backend/services/orchestrator.py`
  - **Class**: `Orchestrator` with attributes: `active_agents: Dict[str, Agent]`, `task_queue: Queue`, `project_state: ProjectState`, `llm_client: OrchestratorLLMClient`
  - **Pattern**: Hub-and-spoke where orchestrator is hub, all agents are spokes, no direct agent-to-agent communication
  - **Methods**: `assign_task()`, `route_message()`, `consult_specialist()`, `escalate_to_human()`, `update_state()`
  - **Acceptance**: Single orchestrator instance coordinates all agents, all communication flows through hub, agents cannot contact each other directly
  - **Test**: Unit tests verify hub-and-spoke enforcement, integration tests confirm message routing
  - **Implementation Doc**: `docs/implementation/phase1/task-1-1-1-orchestrator-core.md`
  - **Test Coverage**: 39 unit tests + 10 integration tests + 2 comparison tests (51 total tests, ALL PASSING)
  - **Code Coverage**: 99% (154/154 statements, only 2 placeholder methods uncovered)
  - **Verification**: ✅ All tests passing ✅ 99% code coverage ✅ Hub-and-spoke pattern enforced ✅ All acceptance criteria met

- [ ] **TODO**: Implement synchronous task queue system
  - **File**: `backend/services/task_queue.py`
  - **Class**: `TaskQueue` with methods: `enqueue()`, `dequeue()`, `peek()`, `get_pending_count()`, `prioritize_task()`
  - **Implementation**: Python Queue (thread-safe), FIFO ordering, priority queue support for urgent tasks
  - **Task Structure**: `Task(id, type, agent_type, priority, payload, created_at, status)`
  - **Integration**: Orchestrator calls `enqueue()` when receiving work, agents pull via orchestrator `dequeue()`
  - **Acceptance**: Tasks processed in order, thread-safe operations, no race conditions, priority tasks jump queue
  - **Test**: Concurrent enqueue/dequeue tests, priority ordering tests, thread safety tests

- [ ] **TODO**: Create agent communication protocol (agent ↔ orchestrator ↔ agent)
  - **File**: `backend/models/communication.py`
  - **Classes**: `AgentMessage`, `OrchestratorMessage`, `MessageType(Enum)`, `MessageRouter`
  - **Protocol**: Structured JSON messages with: sender_id, recipient_id, message_type, payload, timestamp, correlation_id
  - **Message Types**: TASK_ASSIGNMENT, TASK_RESULT, HELP_REQUEST, SPECIALIST_RESPONSE, PROGRESS_UPDATE, ERROR_REPORT
  - **Flow**: Agent → Orchestrator (always), Orchestrator → Agent (always), Agent → Agent (NEVER - blocked)
  - **Validation**: Pydantic models enforce message structure, orchestrator validates all messages
  - **Acceptance**: All agent communication routed through orchestrator, direct agent messages rejected, message structure validated
  - **Test**: Message routing tests, validation tests, protocol enforcement tests

- [ ] **TODO**: Build project state management system
  - **File**: `backend/services/project_state_manager.py`
  - **Class**: `ProjectStateManager` with methods: `get_state()`, `update_state()`, `record_task_completion()`, `get_progress()`, `rollback_state()`
  - **State Structure**: `ProjectState(project_id, current_phase, active_task_id, active_agent_id, completed_tasks: List, pending_tasks: List, metadata: dict, last_updated)`
  - **Persistence**: Database-backed (project_state table), in-memory cache for performance, write-through caching
  - **Recovery**: State snapshots every 5 minutes, restore on crash/restart, transaction log for point-in-time recovery
  - **Acceptance**: State persists to database, survives restarts, accurate progress tracking, rollback capability
  - **Test**: State persistence tests, recovery tests, concurrent update tests, rollback tests

- [ ] **TODO**: Implement agent lifecycle management (start, pause, stop, cleanup)
  - **File**: `backend/services/agent_lifecycle_manager.py`
  - **Class**: `AgentLifecycleManager` with methods: `start_agent()`, `pause_agent()`, `resume_agent()`, `stop_agent()`, `cleanup_agent()`, `get_agent_status()`
  - **Lifecycle States**: INITIALIZING → READY → ACTIVE → PAUSED → STOPPED → CLEANED_UP
  - **Operations**: Start (initialize resources), Pause (save state, suspend), Resume (restore state), Stop (graceful shutdown), Cleanup (release resources)
  - **Resource Management**: Track agent memory usage, file handles, database connections, release on cleanup
  - **Gate Integration**: Auto-pause on human approval gate, resume on gate approval, track pause reason
  - **Acceptance**: Agents start/stop cleanly, pause/resume preserves state, resources released on cleanup, no orphaned processes
  - **Test**: Lifecycle transition tests, resource cleanup tests, pause/resume state preservation tests

### 1.1.1 Orchestrator LLM Integration (Decision 67)
**Reference**: `docs/architecture/decision-67-orchestrator-llm-integration.md`

- [ ] **TODO**: Implement OrchestratorLLMClient with full chain-of-thought reasoning
  - **File**: `backend/services/orchestrator_llm_client.py`
  - **Class**: `OrchestratorLLMClient` with methods: `reason_about_task()`, `select_agent()`, `evaluate_progress()`
  - **Acceptance**: Client returns structured reasoning with confidence scores, uses gpt-4o model
  - **Test**: Unit tests verify reasoning structure, integration tests validate agent selection logic

- [ ] **TODO**: Create orchestrator base system prompt and templates
  - **File**: `backend/prompts/orchestrator_prompts.py`
  - **Content**: Base system prompt defining orchestrator role, context injection templates, decision-making guidelines
  - **Acceptance**: Prompt includes role definition, available agents list, escalation rules, output format requirements
  - **Test**: Prompt validation tests ensure all required sections present

- [ ] **TODO**: Implement autonomy level configuration (low/medium/high slider)
  - **Database**: Add `autonomy_level` column to `user_settings` table (VARCHAR, values: 'low'/'medium'/'high')
  - **Backend**: `backend/models/user_settings.py` - add field and validation
  - **Acceptance**: Setting persists to database, defaults to 'medium', validates enum values
  - **Test**: CRUD tests for autonomy setting

- [ ] **TODO**: Build autonomy threshold logic for escalation decisions
  - **File**: `backend/services/orchestrator.py` - add `should_escalate()` method
  - **Logic**: Low=always escalate, Medium=escalate on uncertainty>0.3, High=escalate on uncertainty>0.7
  - **Acceptance**: Method returns boolean based on autonomy level and confidence score
  - **Test**: Unit tests for all 3 autonomy levels with various confidence scores

- [ ] **TODO**: Create orchestrator-mediated RAG query system
  - **File**: `backend/services/orchestrator.py` - add `query_knowledge_base()` method
  - **Integration**: Calls `RAGQueryService.search()` and formats results for agent context
  - **Acceptance**: Returns top 5 relevant patterns, includes similarity scores, formats for prompt injection
  - **Test**: Integration test with mock Qdrant, verify result formatting

- [ ] **TODO**: Implement PM vetting workflow (orchestrator reviews PM decisions with specialists)
  - **File**: `backend/services/orchestrator.py` - add `vet_pm_decision()` method
  - **Workflow**: PM proposes → Orchestrator reviews → Consults specialist if needed → Approves/rejects
  - **Acceptance**: Creates collaboration request, waits for specialist response, logs decision to database
  - **Test**: End-to-end test simulating PM decision requiring specialist input

- [ ] **TODO**: Build orchestrator decision logging to database
  - **Table**: `orchestrator_decisions` (already defined in Decision 79)
  - **File**: `backend/services/orchestrator.py` - add `log_decision()` method
  - **Fields**: decision_type, reasoning, confidence, selected_agent, outcome
  - **Acceptance**: Every major decision logged with full context, queryable for analytics
  - **Test**: Verify logging on agent selection, escalation, collaboration routing

- [ ] **TODO**: Create frontend autonomy slider in settings
  - **File**: `frontend/src/pages/Settings.tsx` - add autonomy section
  - **Component**: Slider with 3 positions (Low/Medium/High), descriptions for each level
  - **API**: PUT `/api/v1/settings/autonomy` endpoint
  - **Acceptance**: Slider updates database, shows current value on load, displays help text
  - **Test**: E2E test changing autonomy level and verifying persistence

- [ ] **TODO**: Implement orchestrator context layer templates
  - **File**: `backend/prompts/orchestrator_prompts.py` - add `build_context()` function
  - **Templates**: Project context, agent context, RAG results, collaboration history
  - **Acceptance**: Templates inject all relevant context into LLM prompts, max 8000 tokens
  - **Test**: Unit tests verify context assembly, token counting

- [ ] **TODO**: Build orchestrator agent selection logic for collaboration routing
  - **File**: `backend/services/orchestrator.py` - add `route_collaboration()` method
  - **Logic**: Analyzes help request, selects best specialist based on expertise, checks availability
  - **Acceptance**: Returns agent_id and reasoning, logs routing decision, handles no-match case
  - **Test**: Unit tests for various collaboration scenarios (security, performance, architecture)

### 1.2 Agent System Architecture (REVISED FOR LLM INTEGRATION)
- [ ] **TODO**: Create base agent class with common functionality
- [ ] **TODO**: Implement Backend Developer agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement Frontend Developer agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement QA Engineer agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement Security Expert agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement DevOps Engineer agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement Documentation Expert agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement UI/UX Designer agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement GitHub Specialist agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement Workshopper agent (TRADITIONAL - NEEDS REFACTOR)
- [ ] **TODO**: Implement Project Manager agent (TRADITIONAL - NEEDS REFACTOR)

### 1.2.1 LLM Agent Architecture (FINAL - Based on Decisions)
- [ ] **TODO**: Implement OpenAI-only LLM integration with per-agent model selection
- [ ] **TODO**: Create token usage logging system for database storage
- [ ] **TODO**: Build agent-specific chain-of-thought prompt templates
- [ ] **TODO**: Implement LLM input/output validation and sanitization
- [ ] **TODO**: Create AI-assisted testing framework for LLM components
- [ ] **TODO**: Build prompt versioning and management system
- [ ] **TODO**: Implement RAG integration for agent learning
- [ ] **TODO**: Create LLM error handling and retry logic

### 1.2.2 Agent Refactoring for LLM Integration (FINAL)
- [ ] **TODO**: Refactor Backend Developer agent with OpenAI integration and chain-of-thought (reference implementation)
- [ ] **TODO**: Refactor Frontend Developer agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor QA Engineer agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor Security Expert agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor DevOps Engineer agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor Documentation Expert agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor UI/UX Designer agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor GitHub Specialist agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor Workshopper agent with OpenAI integration and chain-of-thought
- [ ] **TODO**: Refactor Project Manager agent with OpenAI integration and chain-of-thought

### 1.2.3 Prompt Engineering and System Design (FINAL)

- [ ] **TODO**: Design agent-specific base prompts with strict role definitions
  - **File**: `backend/prompts/agents/` - separate files per agent (orchestrator.txt, backend_dev.txt, etc.)
  - **Structure**: Role definition, capabilities, constraints, output format, examples
  - **Agents**: All 10 agent types (orchestrator, backend_dev, frontend_dev, qa, devops, security, pm, data_analyst, tech_writer, github_specialist)
  - **Acceptance**: Each agent has complete base prompt, role clearly defined, constraints explicit
  - **Test**: Load all prompts, verify structure, test with LLM

- [ ] **TODO**: Create chain-of-thought reasoning templates for all agents
  - **File**: `backend/prompts/reasoning_templates.yaml`
  - **Templates**: Step-by-step reasoning format for each agent type
  - **Format**: "1. Analyze: ..., 2. Consider: ..., 3. Decide: ..., 4. Execute: ..."
  - **Acceptance**: All agents have reasoning templates, format is consistent, encourages structured thinking
  - **Test**: Test templates with sample tasks, verify reasoning quality

- [ ] **TODO**: Build prompt template system with context injection
  - **File**: `backend/services/prompt_builder.py`
  - **Class**: `PromptBuilder` with method `build_prompt(agent_type, context: dict) -> str`
  - **Injection**: Base prompt + context (task, project info, RAG results, collaboration history)
  - **Variables**: {{task}}, {{project_name}}, {{rag_context}}, {{previous_attempts}}
  - **Acceptance**: Templates support variable injection, context properly formatted, token limits respected
  - **Test**: Build prompts with various contexts, verify injection, check token counts

- [ ] **TODO**: Implement prompt versioning and rollback capabilities
  - **Note**: Already covered in 1.2.4 (Prompt Versioning System)
  - **Reference**: See Decision 69 implementation above
  - **Acceptance**: Versioning system implemented, no additional work needed
  - **Test**: Covered in 1.2.4 tests

- [ ] **TODO**: Create AI-assisted prompt optimization and A/B testing
  - **Note**: Already covered in 1.2.4 and 6.6.1 (LLM Testing Strategy)
  - **Reference**: A/B Testing Lab in Decision 69, full testing framework in Decision 72
  - **Acceptance**: A/B testing implemented, optimization framework ready
  - **Test**: Covered in 1.2.4 and 6.6.1 tests

- [ ] **TODO**: Design prompt performance metrics and monitoring dashboard
  - **File**: `frontend/src/pages/PromptMetrics.tsx`
  - **Route**: `/metrics/prompts`
  - **Metrics**: Success rate by agent, average reasoning quality score, token usage, response time, error rate
  - **Charts**: Line chart (success rate over time), bar chart (by agent), heatmap (performance by task type)
  - **Acceptance**: Shows all metrics, updates in real-time, filterable by date/agent
  - **Test**: E2E test viewing metrics, verify data accuracy

### 1.2.4 Prompt Versioning System (Decision 69)
**Reference**: `docs/architecture/decision-69-prompt-versioning-system.md`

- [ ] **TODO**: Create prompts table with semantic versioning (major.minor.patch)
  - **Migration**: Alembic migration file creating `prompts` table
  - **Schema**: id, agent_type, version, prompt_text, is_active, created_at, created_by, notes
  - **Indexes**: (agent_type, version) UNIQUE, (agent_type, is_active)
  - **Acceptance**: Table created, indexes applied, seed data for all 10 agent types at v1.0.0
  - **Test**: Database schema test verifies table structure and constraints

- [ ] **TODO**: Implement PromptLoadingService (latest version auto-loading)
  - **File**: `backend/services/prompt_loading_service.py`
  - **Class**: `PromptLoadingService` with method `get_active_prompt(agent_type: str) -> str`
  - **Logic**: Query WHERE agent_type=X AND is_active=true, cache for 5 minutes
  - **Acceptance**: Returns active prompt text, raises error if none found, caches results
  - **Test**: Unit tests for cache hit/miss, multiple agent types, missing prompt error

- [ ] **TODO**: Build PromptManagementService (create, promote, patch versions)
  - **File**: `backend/services/prompt_management_service.py`
  - **Methods**: `create_version()`, `promote_to_active()`, `create_patch()`
  - **Versioning**: Major (breaking), Minor (new features), Patch (fixes)
  - **Acceptance**: Creates new versions, only one active per agent, validates semantic versioning
  - **Test**: Unit tests for version creation, promotion, patch application

- [ ] **TODO**: Create independent versioning per agent type
  - **Implementation**: Each agent_type has separate version sequence (orchestrator v1.2.3, backend_dev v2.0.1)
  - **Database**: UNIQUE constraint on (agent_type, version)
  - **Acceptance**: Agents can be on different versions independently
  - **Test**: Create versions for multiple agents, verify independence

- [ ] **TODO**: Implement fix-forward patch creation (no rollback)
  - **File**: `backend/services/prompt_management_service.py` - `create_patch()` method
  - **Logic**: Increments patch version, copies previous prompt as base, marks new as active
  - **Acceptance**: No rollback functionality, always creates new version forward
  - **Test**: Verify patch creation increments correctly (1.0.0 → 1.0.1 → 1.0.2)

- [ ] **TODO**: Build A/B Testing Lab frontend page
  - **File**: `frontend/src/pages/ABTestingLab.tsx`
  - **Route**: `/testing/prompts`
  - **Features**: Select 2 versions, run test cases, compare results side-by-side
  - **Acceptance**: Shows version selector, test case list, run button, results comparison
  - **Test**: E2E test running A/B comparison

- [ ] **TODO**: Create prompt testing API endpoints (test, compare, promote)
  - **Endpoints**: POST `/api/v1/prompts/test`, POST `/api/v1/prompts/compare`, POST `/api/v1/prompts/{id}/promote`
  - **File**: `backend/api/routes/prompts.py`
  - **Acceptance**: Test runs prompt against test cases, compare shows diff, promote activates version
  - **Test**: API integration tests for all 3 endpoints

- [ ] **TODO**: Implement side-by-side version comparison UI
  - **File**: `frontend/src/components/PromptComparison.tsx`
  - **Layout**: Two-column layout showing Version A vs Version B, diff highlighting
  - **Acceptance**: Shows prompt text diff, test results comparison, performance metrics
  - **Test**: Component test with mock data

- [ ] **TODO**: Build prompt editing interface in frontend
  - **File**: `frontend/src/pages/PromptEditor.tsx`
  - **Features**: Monaco editor, syntax highlighting, version info, save as new version
  - **Acceptance**: Edit prompt text, validate format, create new version, show preview
  - **Test**: E2E test creating new prompt version

- [ ] **TODO**: Create prompt version history viewer
  - **File**: `frontend/src/components/PromptHistory.tsx`
  - **Display**: Table showing all versions for agent, with date, author, notes, active indicator
  - **Acceptance**: Sortable by date, filterable by agent, click to view full prompt
  - **Test**: Component test with mock version data

- [ ] **TODO**: Implement agent integration with automatic latest version loading
  - **File**: `backend/agents/base_agent.py` - modify `__init__()` to load prompt
  - **Integration**: Calls `PromptLoadingService.get_active_prompt(self.agent_type)`
  - **Acceptance**: Agents always use active version, no code changes needed for prompt updates
  - **Test**: Agent initialization test verifies prompt loading

### 1.3 Decision-Making & Escalation System

- [ ] **TODO**: Build human approval gate system
  - **File**: `backend/services/gate_manager.py`
  - **Class**: `GateManager` with methods: `create_gate()`, `approve_gate()`, `deny_gate()`, `get_pending_gates()`
  - **Gate Types**: Loop detected (3 failures), high-risk operation, collaboration deadlock, manual trigger
  - **Database**: Uses gates table from migration 006
  - **Acceptance**: Creates gates with context, pauses agent, notifies user, resumes on approval
  - **Test**: Create gate, approve/deny, verify agent pause/resume

- [ ] **TODO**: Create escalation workflow (agent → orchestrator → specialist)
  - **File**: `backend/services/orchestrator.py` - add `escalate_to_specialist()` method
  - **Flow**: Agent requests help → Orchestrator analyzes → Routes to specialist → Specialist responds → Orchestrator delivers
  - **Integration**: Uses CollaborationOrchestrator from Decision 70
  - **Acceptance**: Escalation works, specialist selected correctly, response delivered
  - **Test**: Test escalation scenarios, verify routing, check response delivery

- [ ] **TODO**: Implement manual gate trigger interface
  - **File**: `frontend/src/components/ManualGateTrigger.tsx`
  - **Location**: Project detail page, agent activity section
  - **UI**: "Pause for Review" button, reason input, confirmation
  - **API**: POST /api/v1/gates/manual with project_id, agent_id, reason
  - **Acceptance**: Button visible, creates gate, pauses agent, shows in pending gates
  - **Test**: E2E test triggering manual gate

- [ ] **TODO**: Design approval/deny workflow with feedback collection
  - **File**: `frontend/src/components/GateApprovalModal.tsx`
  - **UI**: Gate details, agent context, approve/deny buttons, feedback textarea
  - **Workflow**: Show gate → User reviews → Approve (resume) or Deny (provide feedback) → Agent receives decision
  - **Feedback**: Required on deny, optional on approve, stored in gates table
  - **Acceptance**: Modal shows all context, feedback collected, decision recorded
  - **Test**: E2E test approval and denial workflows

### 1.3.1 Agent Collaboration Protocol (Decision 70)
**Reference**: `docs/architecture/decision-70-agent-collaboration-protocol.md`

- [ ] **TODO**: Implement CollaborationOrchestrator service
  - **File**: `backend/services/collaboration_orchestrator.py`
  - **Class**: `CollaborationOrchestrator` with methods: `handle_help_request()`, `route_to_specialist()`, `deliver_response()`
  - **Flow**: Receive request → Select specialist → Provide context → Get response → Deliver to requester
  - **Acceptance**: Handles collaboration requests, routes correctly, tracks lifecycle
  - **Test**: Unit tests for routing logic, integration tests for full collaboration flow

- [ ] **TODO**: Create agent help request message format (structured JSON)
  - **File**: `backend/models/collaboration.py`
  - **Class**: `CollaborationRequest` with fields: request_type, requesting_agent, question, context, suggested_agent (optional), urgency, collaboration_id
  - **Validation**: Pydantic model with field validation, required fields enforced
  - **Acceptance**: Structured format, validated, includes all necessary context
  - **Test**: Create requests, validate fields, test serialization

- [ ] **TODO**: Build orchestrator collaboration routing logic
  - **File**: `backend/services/collaboration_orchestrator.py` - `route_to_specialist()` method
  - **Logic**: Analyze question → Match to agent expertise → Check availability → Select best specialist
  - **Expertise Map**: Security questions → Security Expert, API questions → Backend Dev, UI questions → Frontend Dev, etc.
  - **Override**: Orchestrator always makes final decision, ignores suggested_agent if inappropriate
  - **Acceptance**: Routes to correct specialist, logs routing decision, handles no-match case
  - **Test**: Test all 6 collaboration scenarios, verify routing accuracy

- [ ] **TODO**: Implement context sharing protocol for agent pairs
  - **File**: `backend/models/collaboration.py` - `CollaborationContext` class
  - **Structure**: requesting_agent_id, current_task, specific_question, relevant_code, attempted_approaches
  - **Filtering**: Orchestrator curates context, removes irrelevant details, max 1000 tokens
  - **Acceptance**: Context is minimal but sufficient, specialist can answer without full project knowledge
  - **Test**: Build context packages, verify token limits, test specialist comprehension

- [ ] **TODO**: Create collaboration scenario catalog with workflows
  - **File**: `backend/config/collaboration_scenarios.yaml`
  - **Scenarios**: 6 types (Model/Data, Security Review, API Clarification, Bug Debugging, Requirements, Infrastructure)
  - **Workflow**: Each scenario defines: trigger, routing rule, context requirements, expected response format
  - **Acceptance**: All 6 scenarios documented, workflows clear, routing rules implemented
  - **Test**: Test each scenario type, verify workflow execution

- [ ] **TODO**: Build collaboration loop detection algorithm
  - **File**: `backend/services/collaboration_orchestrator.py` - `detect_collaboration_loop()` method
  - **Logic**: Track collaboration chain → Detect if Agent A asks Agent B, then B asks A about same topic → Flag as loop after 3 cycles
  - **Semantic Similarity**: Use embedding similarity (>0.85) to detect "same topic"
  - **Acceptance**: Detects collaboration loops, triggers gate after 3 cycles, logs loop events
  - **Test**: Simulate collaboration loops, verify detection, test gate triggering

- [ ] **TODO**: Implement collaboration tracking database schema (agent_collaborations, collaboration_exchanges, collaboration_outcomes, collaboration_loops tables)
  - **Migration**: Already covered in 6.2.1 (migration 013)
  - **Tables**: agent_collaborations (main), collaboration_exchanges (messages), collaboration_outcomes (results), collaboration_loops (detected loops)
  - **Relationships**: Foreign keys linking exchanges to collaborations, outcomes to collaborations
  - **Acceptance**: All 4 tables created, relationships enforced, tracks full lifecycle
  - **Test**: Create collaboration with exchanges, record outcome, detect loop

- [ ] **TODO**: Create collaboration metrics tracking (frequency, success rate, cost)
  - **File**: `backend/services/collaboration_metrics.py`
  - **Metrics**: Collaboration frequency by agent pair, success rate (outcome=resolved), average response time, token cost
  - **Storage**: Aggregate metrics in collaboration_outcomes table
  - **Dashboard**: Query endpoints for metrics visualization
  - **Acceptance**: Tracks all metrics, calculates success rates, monitors costs
  - **Test**: Generate collaborations, calculate metrics, verify accuracy

- [ ] **TODO**: Implement RAG storage for successful collaborations
  - **File**: `backend/services/knowledge_capture_service.py` - add `capture_collaboration_success()` method
  - **Trigger**: When collaboration outcome=resolved and marked as valuable
  - **Content**: Question + Answer + Context stored in knowledge_staging
  - **Metadata**: agent_pair, question_type, resolution_approach
  - **Acceptance**: Successful collaborations captured, available for future RAG queries
  - **Test**: Complete collaboration, verify RAG capture, query and retrieve

- [ ] **TODO**: Build frontend collaboration visibility dashboard
  - **File**: `frontend/src/pages/CollaborationDashboard.tsx`
  - **Features**: Active collaborations list, collaboration history, metrics charts (frequency, success rate), agent pair heatmap
  - **Real-time**: WebSocket updates for active collaborations
  - **Acceptance**: Shows all collaborations, updates in real-time, displays metrics
  - **Test**: E2E test viewing collaborations, verify real-time updates

### 1.4 Failure Handling & Recovery

- [ ] **TODO**: Implement agent timeout detection system
  - **File**: `backend/services/timeout_monitor.py`
  - **Class**: `TimeoutMonitor` with method `monitor_task(task_id, timeout_seconds)`
  - **Timeout**: 10 minutes default, configurable per agent type
  - **Action**: On timeout → Log error → Create gate → Notify user
  - **Acceptance**: Detects timeouts accurately, creates gates, doesn't false-positive on long tasks
  - **Test**: Test with various timeout scenarios, verify detection

- [ ] **TODO**: Create loop detection (3 strikes → human gate)
  - **Note**: Already covered in 1.4.1 (Loop Detection Algorithm, Decision 74)
  - **Reference**: Complete implementation in Decision 74 above
  - **Acceptance**: Loop detection implemented with 3-strike threshold
  - **Test**: Covered in 1.4.1 tests

- [ ] **TODO**: Build project recovery mechanisms
  - **Note**: Already covered in 1.4.2 (Project State Recovery, Decision 76)
  - **Reference**: Complete implementation in Decision 76 above
  - **Acceptance**: Recovery on startup, file scanning, LLM evaluation implemented
  - **Test**: Covered in 1.4.2 tests

- [ ] **TODO**: Design "nuke from orbit" project deletion system
  - **Note**: Already covered in 4.7.1 (Project Cancellation Workflow, Decision 81)
  - **Reference**: Complete deletion workflow in Decision 81 above
  - **Acceptance**: Two-step confirmation, complete resource destruction implemented
  - **Test**: Covered in 4.7.1 tests

### 1.4.1 Loop Detection Algorithm (Decision 74)
**Reference**: `docs/architecture/decision-74-loop-detection-algorithm.md`

- [ ] **TODO**: Implement LoopDetectionService with exact error message matching
  - **File**: `backend/services/loop_detection_service.py`
  - **Class**: `LoopDetectionService` with methods: `check_for_loop()`, `record_failure()`, `reset_loop_counter()`
  - **Logic**: Extract error message → Compare with recent failures → Increment counter on exact match
  - **Acceptance**: Detects identical error messages, fast string comparison (<1ms), accurate loop counting
  - **Test**: Unit tests with identical/different errors, verify counter increments

- [ ] **TODO**: Create failure signature extraction and storage (error type, location, context hash)
  - **File**: `backend/models/failure_signature.py`
  - **Class**: `FailureSignature` with fields: exact_message, error_type, location, context_hash, timestamp, agent_id, task_id
  - **Extraction**: Parse error output → Classify error type → Extract file:line → Hash stack trace
  - **Storage**: In-memory in LoopTracker, last 10 failures per task
  - **Acceptance**: Extracts all signature components, classifies error types correctly
  - **Test**: Parse various error formats, verify extraction accuracy

- [ ] **TODO**: Build progress evaluation with test metrics (coverage, failure rate)
  - **File**: `backend/services/progress_evaluator.py`
  - **Class**: `ProgressEvaluator` with method `evaluate_progress(task_id: str) -> bool`
  - **Metrics**: Test coverage % change, test failure rate change, files created, dependencies added
  - **Logic**: IF tests exist: check coverage/failure improvements, ELSE: check task completion markers
  - **Acceptance**: Accurately detects progress, handles no-test scenarios, returns boolean
  - **Test**: Test with improving/declining metrics, no-test scenarios

- [ ] **TODO**: Implement orchestrator LLM goal proximity evaluation
  - **File**: `backend/services/orchestrator.py` - add `evaluate_goal_proximity()` method
  - **Purpose**: Fallback when no quantifiable metrics available
  - **Logic**: LLM analyzes current state vs. goal → Returns proximity score 0-1 and reasoning
  - **Prompt**: "Given task goal: X, current state: Y, rate progress 0-1 and explain"
  - **Acceptance**: LLM provides proximity score, reasoning is clear, used only as fallback
  - **Test**: Test with various task states, verify LLM reasoning quality

- [ ] **TODO**: Create collaboration loop detection (semantic similarity)
  - **File**: `backend/services/collaboration_orchestrator.py` - add `detect_semantic_loop()` method
  - **Logic**: Track collaboration chain → Generate embeddings for questions → Calculate similarity → Flag if >0.85 similarity
  - **Threshold**: 0.85 cosine similarity indicates "same topic"
  - **Acceptance**: Detects when agents ask each other similar questions repeatedly
  - **Test**: Simulate collaboration loops with similar/different questions

- [ ] **TODO**: Build loop counter logic with 3-loop threshold
  - **File**: `backend/services/loop_detection_service.py` - `check_for_loop()` method
  - **Logic**: IF exact_match: increment counter, IF counter >= 3: trigger gate, ELSE: continue
  - **Gate Trigger**: Create human approval gate with loop context, pause agent
  - **Acceptance**: Triggers gate after exactly 3 loops, provides context to user
  - **Test**: Simulate 3 identical failures, verify gate creation

- [ ] **TODO**: Implement loop counter reset on success/human intervention
  - **File**: `backend/services/loop_detection_service.py` - `reset_loop_counter()` method
  - **Triggers**: Task completion success, human gate approval, different error encountered
  - **Logic**: Clear failure history, reset counter to 0, log reset event
  - **Acceptance**: Counter resets correctly, doesn't carry over to new tasks
  - **Test**: Trigger resets, verify counter cleared, test new task isolation

- [ ] **TODO**: Create in-memory loop state tracking
  - **File**: `backend/services/loop_detection_service.py` - `LoopTracker` class
  - **Structure**: Dict[task_id, LoopState] with LoopState containing: failure_history (last 10), loop_count, last_failure_time, progress_metrics
  - **Memory Management**: Garbage collect states >24 hours inactive, clear on task completion
  - **Acceptance**: Fast in-memory access, automatic cleanup, no database overhead
  - **Test**: Create states, verify GC, test memory usage

- [ ] **TODO**: Build edge case handling (external failures, progressive degradation)
  - **File**: `backend/services/loop_detection_service.py` - add edge case logic
  - **Cases**: External API failures (don't count as loops), intermittent failures (require consistency), progressive degradation (different errors each time)
  - **Logic**: External failures flagged separately, intermittent requires 3 consecutive matches, degradation resets counter
  - **Acceptance**: Handles all edge cases correctly, doesn't false-positive on external issues
  - **Test**: Test each edge case, verify correct handling

- [ ] **TODO**: Implement loop detection monitoring and metrics
  - **File**: `backend/services/loop_detection_service.py` - add metrics tracking
  - **Metrics**: Total loops detected, loops by agent type, loops by error type, average loops before resolution
  - **Storage**: Log to database for analytics, expose via API
  - **Acceptance**: Tracks all loop events, metrics queryable, dashboard-ready
  - **Test**: Generate loops, verify metrics accuracy

- [ ] **TODO**: Create loop detection unit test suite
  - **File**: `backend/tests/unit/test_loop_detection.py`
  - **Coverage**: Exact match detection, counter logic, reset conditions, edge cases
  - **Scenarios**: 3 identical errors, 2 identical + 1 different, external failures, progress detection
  - **Acceptance**: 100% code coverage, all scenarios tested, tests pass consistently
  - **Test**: Run test suite, verify coverage report

- [ ] **TODO**: Build loop detection integration tests
  - **File**: `backend/tests/integration/test_loop_detection_integration.py`
  - **Scenarios**: Full agent workflow with loops, gate triggering, human intervention, loop reset
  - **Flow**: Agent fails 3 times → Loop detected → Gate created → Human approves → Counter resets
  - **Acceptance**: End-to-end loop detection works, integrates with gates, resets correctly
  - **Test**: Full integration test with real agent and orchestrator

### 1.4.2 Project State Recovery (Decision 76)
**Reference**: `docs/architecture/decision-76-project-state-recovery.md`

- [ ] **TODO**: Create project_state table for state tracking
  - **Migration**: Already covered in 6.2.1 (migration 003)
  - **Schema**: id, project_id (UNIQUE), current_task_id, current_agent_id, last_action, status, metadata (JSONB), updated_at
  - **Purpose**: Track project state for recovery after crashes/restarts
  - **Acceptance**: One state per project, tracks current position, JSONB for flexible metadata
  - **Test**: Create state, update state, verify uniqueness

- [ ] **TODO**: Implement automatic recovery on orchestrator startup
  - **File**: `backend/services/orchestrator.py` - add `recover_projects()` method in `__init__()`
  - **Trigger**: Orchestrator startup
  - **Logic**: Query project_state WHERE status='active' → For each: scan files → Evaluate recovery → Resume or escalate
  - **Acceptance**: Automatically attempts recovery on startup, logs recovery attempts
  - **Test**: Crash orchestrator mid-project, restart, verify recovery attempt

- [ ] **TODO**: Build file state scanning service
  - **File**: `backend/services/file_state_scanner.py`
  - **Class**: `FileStateScanner` with method `scan_project_files(project_id: str) -> FileState`
  - **Scan**: Check project directory → List files created → Detect partial work → Identify last completed task
  - **Output**: FileState with: files_present, last_modified, partial_work_detected, completion_indicators
  - **Acceptance**: Accurately scans project state, detects partial work, fast (<1s)
  - **Test**: Create partial project, scan, verify detection accuracy

- [ ] **TODO**: Implement orchestrator LLM recovery evaluation
  - **File**: `backend/services/orchestrator.py` - add `evaluate_recovery()` method
  - **Input**: project_state, file_state, last_action
  - **LLM Prompt**: "Project was interrupted at: X. Files present: Y. Should we: continue, restart task, move to next, or ask human?"
  - **Output**: Recovery decision (continue/restart/next/human) with reasoning
  - **Acceptance**: LLM provides clear decision, reasoning is sound, handles all scenarios
  - **Test**: Test with various interruption scenarios, verify decision quality

- [ ] **TODO**: Create recovery decision logic (continue/restart/next/human review)
  - **File**: `backend/services/orchestrator.py` - add `execute_recovery_decision()` method
  - **Decisions**: CONTINUE (resume from last action), RESTART (redo current task), NEXT (skip to next task), HUMAN (create gate)
  - **Logic**: Based on LLM evaluation → Execute appropriate action → Update project_state
  - **Acceptance**: Executes all 4 decision types correctly, updates state, logs decision
  - **Test**: Test each decision type, verify execution

- [ ] **TODO**: Build manual resume project API endpoint
  - **Endpoint**: POST `/api/v1/projects/{project_id}/resume`
  - **File**: `backend/api/routes/projects.py`
  - **Logic**: User manually triggers resume → Orchestrator evaluates recovery → Executes decision
  - **Response**: {"status": "resumed", "decision": "continue", "reasoning": "..."}
  - **Acceptance**: Endpoint works, triggers recovery, returns decision
  - **Test**: API test resuming paused project

- [ ] **TODO**: Implement state update after each significant action
  - **File**: `backend/services/orchestrator.py` - add `update_project_state()` method
  - **Triggers**: Task start, task completion, agent change, phase change, error occurrence
  - **Update**: current_task_id, current_agent_id, last_action, metadata, updated_at
  - **Frequency**: After every significant action (not every LLM call)
  - **Acceptance**: State always current, updates are atomic, no race conditions
  - **Test**: Perform actions, verify state updates, test concurrency

- [ ] **TODO**: Create recovery test suite (crash, restart, pause/resume scenarios)
  - **File**: `backend/tests/integration/test_project_recovery.py`
  - **Scenarios**: Mid-task crash, between-task crash, mid-phase crash, manual pause/resume
  - **Tests**: Crash orchestrator → Restart → Verify recovery decision → Check project continues correctly
  - **Acceptance**: All scenarios tested, recovery works correctly, no data loss
  - **Test**: Full integration tests with simulated crashes

### 1.5 Knowledge Base Integration

- [ ] **TODO**: Set up Qdrant vector database
  - **File**: `docker-compose.yml` - add Qdrant service
  - **Service**: qdrant/qdrant:latest, port 6333, persistent volume
  - **Config**: `backend/config/qdrant_config.py` - connection settings
  - **Acceptance**: Qdrant running, accessible from backend, persistent storage configured
  - **Test**: Connection test, verify persistence across restarts

- [ ] **TODO**: Implement RAG system for agent learning
  - **Note**: Already covered in 1.5.1 (RAG System Architecture, Decision 68)
  - **Reference**: Complete RAG implementation in Decision 68 above (11 tasks)
  - **Acceptance**: Knowledge capture, embedding, query, retrieval all implemented
  - **Test**: Covered in 1.5.1 tests

- [ ] **TODO**: Create failure pattern storage and retrieval
  - **Note**: Already covered in 1.5.1 (RAG System Architecture, Decision 68)
  - **Reference**: KnowledgeCaptureService.capture_failure_solution() in Decision 68
  - **Acceptance**: Failure patterns captured and retrievable via RAG
  - **Test**: Covered in 1.5.1 tests

- [ ] **TODO**: Build cross-project knowledge sharing system
  - **Note**: Already covered in 1.5.1 (RAG System Architecture, Decision 68)
  - **Reference**: Cross-project learning validation tests in Decision 68
  - **Acceptance**: Knowledge is project-agnostic, shared across projects
  - **Test**: Covered in 1.5.1 tests

### 1.5.1 RAG System Architecture (Decision 68)
**Reference**: `docs/architecture/decision-68-rag-system-architecture.md`

- [ ] **TODO**: Create knowledge_staging table in PostgreSQL
  - **Migration**: Already covered in 6.2.1 (migration 012)
  - **Schema**: id, content (TEXT), metadata (JSONB), captured_at, embedded (BOOLEAN), embedded_at
  - **Purpose**: Staging area for knowledge before Qdrant embedding
  - **Acceptance**: Table stores captured knowledge, tracks embedding status
  - **Test**: Insert knowledge, mark as embedded, query pending items

- [ ] **TODO**: Implement KnowledgeCaptureService (failures, gate rejections, approvals)
  - **File**: `backend/services/knowledge_capture_service.py`
  - **Class**: `KnowledgeCaptureService` with methods: `capture_failure_solution()`, `capture_gate_rejection()`, `capture_gate_approval()`
  - **Triggers**: Failed test/task with solution, human gate rejection with feedback, first-attempt gate approval
  - **Storage**: Writes to knowledge_staging table with metadata (project_id, agent_type, task_type, technology)
  - **Acceptance**: Captures 3 knowledge types, stores in staging, includes full context
  - **Test**: Unit tests for each capture type, verify metadata completeness

- [ ] **TODO**: Build checkpoint embedding service (phase/project completion triggers)
  - **File**: `backend/services/checkpoint_embedding_service.py`
  - **Class**: `CheckpointEmbeddingService` with method `process_checkpoint(checkpoint_type: str)`
  - **Triggers**: Phase completion, project completion, project cancellation, manual trigger
  - **Process**: Query knowledge_staging WHERE embedded=false → Generate embeddings via OpenAI → Store in Qdrant → Mark as embedded
  - **Batch Size**: Process 50 items per batch to manage API costs
  - **Acceptance**: Embeddings generated at checkpoints, no real-time embedding, batch processing works
  - **Test**: Trigger checkpoint, verify embedding generation, check Qdrant storage

- [ ] **TODO**: Set up Qdrant collection with text-embedding-3-small (1536 dimensions)
  - **File**: `backend/services/qdrant_setup.py`
  - **Collection**: `helix_knowledge` with vector size 1536
  - **Config**: Distance metric: Cosine, Quantization: Scalar (for performance)
  - **Indexes**: Payload indexes on agent_type, task_type, technology, success_verified
  - **Acceptance**: Collection created, indexes applied, ready for embeddings
  - **Test**: Create collection, verify configuration, test vector insertion

- [ ] **TODO**: Implement RAGQueryService (orchestrator-only access)
  - **File**: `backend/services/rag_query_service.py`
  - **Class**: `RAGQueryService` with method `search(query: str, filters: dict, limit: int = 5)`
  - **Access Control**: Only callable by orchestrator, not exposed to agents
  - **Query Logic**: Generate query embedding → Search Qdrant → Filter by metadata → Return top 5 results
  - **Filters**: agent_type, task_type, technology, success_verified=true
  - **Acceptance**: Returns relevant patterns, respects filters, orchestrator-only access
  - **Test**: Query with various filters, verify access control, test relevance

- [ ] **TODO**: Create orchestrator context builder with RAG injection
  - **File**: `backend/services/orchestrator.py` - add `build_context_with_rag()` method
  - **Integration**: Calls RAGQueryService.search() → Formats results → Injects into agent prompt
  - **Format**: Structured presentation with pattern ranking, success rates, decision criteria
  - **Token Limit**: Max 2000 tokens for RAG context (within 8000 total context budget)
  - **Acceptance**: RAG results formatted clearly, injected into prompts, token limits respected
  - **Test**: Build context with RAG, verify formatting, check token count

- [ ] **TODO**: Build structured pattern presentation format for agents
  - **File**: `backend/prompts/rag_formatting.py`
  - **Function**: `format_patterns(patterns: List[Pattern]) -> str`
  - **Format**: "[ORCHESTRATOR CONTEXT: Historical Knowledge]\n\nPattern 1 (Most Common - X successes):\n- Problem: ...\n- Solution: ...\n- When to try: ...\n\n[END CONTEXT]"
  - **Ranking**: Order by success count, include decision criteria
  - **Acceptance**: Clear structure, agent-friendly format, prevents confusion
  - **Test**: Format various pattern sets, verify structure, test with LLM

- [ ] **TODO**: Implement 1-year knowledge retention with automatic pruning
  - **File**: `backend/jobs/knowledge_cleanup.py`
  - **Schedule**: Daily at 3 AM via cron
  - **Logic**: Delete from Qdrant WHERE embedded_at < NOW() - 365 days, delete from knowledge_staging WHERE embedded=true AND embedded_at < NOW() - 365 days
  - **Acceptance**: Automatic cleanup runs daily, 1-year retention enforced, logs deletion count
  - **Test**: Insert old knowledge, run cleanup, verify deletion from both Qdrant and PostgreSQL

- [ ] **TODO**: Create knowledge quality indicators and success tracking
  - **File**: `backend/services/knowledge_capture_service.py` - add quality scoring
  - **Quality Levels**: HIGH (verified solution), HIGHEST (human wisdom or gold standard)
  - **Metadata**: Add quality_score, success_count, last_used_at to knowledge entries
  - **Tracking**: Increment success_count when pattern is used and task succeeds
  - **Acceptance**: Quality indicators stored, success tracking works, influences ranking
  - **Test**: Capture knowledge with quality scores, track usage, verify ranking

- [ ] **TODO**: Build RAG integration tests (capture → embed → query → retrieve)
  - **File**: `backend/tests/integration/test_rag_system.py`
  - **Flow**: Capture knowledge → Trigger checkpoint → Generate embeddings → Query → Verify retrieval
  - **Coverage**: All 3 knowledge types, various filters, relevance scoring
  - **Acceptance**: End-to-end flow works, embeddings searchable, results relevant
  - **Test**: Full pipeline test with mock OpenAI and real Qdrant

- [ ] **TODO**: Implement cross-project learning validation tests
  - **File**: `backend/tests/integration/test_cross_project_learning.py`
  - **Scenario**: Project A captures knowledge → Project B queries and retrieves it
  - **Validation**: Verify knowledge from one project helps another, filters work correctly
  - **Acceptance**: Cross-project learning works, knowledge is project-agnostic
  - **Test**: Multi-project scenario with knowledge sharing

---

## Phase 2: Tool Ecosystem Implementation

### 2.1 Code Execution Sandbox

- [ ] **TODO**: Design Docker-based sandbox system for LLM-generated code (existing safeguards)
  - **Note**: Already covered in 2.1.1 (Docker Container Lifecycle, Decision 78)
  - **Reference**: Complete 13-task implementation in Decision 78 above
  - **Acceptance**: Docker-based sandbox with 8 language support fully specified
  - **Test**: Covered in 2.1.1 tests

- [ ] **TODO**: Implement multi-language support (Python, Node.js, PowerShell, etc.)
  - **Note**: Already covered in 2.1.1 (Docker Container Lifecycle, Decision 78)
  - **Reference**: 8 golden images specified in Decision 78
  - **Acceptance**: Python, Node.js, Java, Go, Ruby, PHP, .NET, PowerShell all supported
  - **Test**: Covered in 2.1.1 tests

- [ ] **TODO**: Create container lifecycle management with LLM agent integration
  - **Note**: Already covered in 2.1.1 (Docker Container Lifecycle, Decision 78)
  - **Reference**: ContainerManager service in Decision 78
  - **Acceptance**: Full lifecycle management implemented
  - **Test**: Covered in 2.1.1 tests

- [ ] **TODO**: Build resource isolation and security boundaries for AI-generated code
  - **File**: `docker/images/base/security_config.sh`
  - **Isolation**: Network isolation (bridge), no host access, read-only system files
  - **Limits**: No CPU/memory limits (trust agents), orchestrator timeout provides safety
  - **Acceptance**: Containers isolated from host, can't access other containers
  - **Test**: Security audit, test isolation boundaries

- [ ] **TODO**: Implement file system isolation with project directories
  - **Note**: Already covered in 2.1.1 (persistent volume mounting)
  - **Reference**: Docker named volumes per project in Decision 78
  - **Acceptance**: Each project has isolated volume, no cross-project access
  - **Test**: Covered in 2.1.1 tests

- [ ] **TODO**: Add LLM code validation and security scanning before execution (minimal additions)
  - **File**: `backend/services/code_validator.py`
  - **Class**: `CodeValidator` with method `validate_code(code: str, language: str) -> ValidationResult`
  - **Checks**: Syntax validation, dangerous pattern detection (eval, exec, system calls), size limits
  - **Action**: Warn on dangerous patterns, block on syntax errors
  - **Acceptance**: Validates code before execution, catches obvious issues, doesn't block legitimate code
  - **Test**: Test with safe/unsafe code samples, verify detection

- [ ] **TODO**: Create sandbox monitoring and logging for AI operations
  - **File**: `backend/services/sandbox_monitor.py`
  - **Monitoring**: Container resource usage, command execution logs, error tracking
  - **Logging**: All commands logged with timestamp, agent_id, project_id, exit_code
  - **Acceptance**: All sandbox activity logged, resources monitored, alerts on anomalies
  - **Test**: Execute commands, verify logging, test monitoring

### 2.1.1 Docker Container Lifecycle (Decision 78)
**Reference**: `docs/architecture/decision-78-docker-container-lifecycle.md`

- [ ] **TODO**: Implement ContainerManager service
  - **File**: `backend/services/container_manager.py`
  - **Class**: `ContainerManager` with methods: `create_container()`, `destroy_container()`, `exec_command()`, `startup()`
  - **State**: Dict tracking active_containers by task_id
  - **Docker Client**: Uses docker-py library for container operations
  - **Acceptance**: Manages container lifecycle, tracks active containers, handles errors gracefully
  - **Test**: Unit tests for all methods, mock Docker client

- [ ] **TODO**: Build golden images for 8 languages (Python, Node.js, Java, Go, Ruby, PHP, .NET, PowerShell)
  - **Dockerfiles**: `docker/images/{language}/Dockerfile` for each language
  - **Base Images**: python:3.11-slim, node:20-slim, openjdk:17-slim, golang:1.21-alpine, ruby:3.2-slim, php:8.2-cli, mcr.microsoft.com/dotnet/sdk:8.0, mcr.microsoft.com/powershell:lts-alpine
  - **Common Tools**: git, curl, basic build tools pre-installed
  - **Working Dir**: /workspace (mounted from persistent volume)
  - **Acceptance**: All 8 images build successfully, optimized for size (<500MB each), include necessary tools
  - **Test**: Build all images, verify tools installed, test basic commands

- [ ] **TODO**: Create on-demand container creation (one per task)
  - **File**: `backend/services/container_manager.py` - `create_container()` method
  - **Trigger**: Agent starts new task
  - **Logic**: Select image by language → Create container with volume mount → Track in active_containers dict → Return container handle
  - **Naming**: Container name format: `helix-{project_id}-{task_id}`
  - **Acceptance**: Creates container in <2s, mounts project volume, returns ready container
  - **Test**: Create containers for all 8 languages, verify volume mounts

- [ ] **TODO**: Implement task-scoped container lifetime
  - **Scope**: One container per task, destroyed when task completes
  - **Lifecycle**: Task start → Container created → Multiple commands executed → Task end → Container destroyed
  - **No Reuse**: Fresh container for each task, no pooling
  - **Acceptance**: Container exists only during task execution, destroyed immediately after
  - **Test**: Start task, verify container exists, complete task, verify container destroyed

- [ ] **TODO**: Build immediate container cleanup on task completion
  - **File**: `backend/services/container_manager.py` - `destroy_container()` method
  - **Trigger**: Task completion (success or failure)
  - **Logic**: Stop container (5s timeout) → Remove container → Remove from tracking dict
  - **Guarantee**: Cleanup in finally block to ensure execution even on errors
  - **Acceptance**: Container destroyed within 6s of task completion, no orphaned containers
  - **Test**: Complete task, verify cleanup, test cleanup on failure

- [ ] **TODO**: Create command execution in containers
  - **File**: `backend/services/container_manager.py` - `exec_command()` method
  - **Parameters**: task_id, command (string)
  - **Execution**: container.exec_run(cmd=command, workdir='/workspace', demux=True)
  - **Return**: {exit_code, stdout, stderr}
  - **Acceptance**: Executes commands, captures output, handles errors, returns structured result
  - **Test**: Execute various commands (success/failure), verify output capture

- [ ] **TODO**: Implement persistent volume mounting for project files
  - **Volume Type**: Docker named volumes per project
  - **Volume Name**: `helix-project-{project_id}`
  - **Mount Point**: /workspace in container
  - **Persistence**: Files persist across container destruction/creation
  - **Acceptance**: Files written in one container visible in next container, survives restarts
  - **Test**: Write file in container, destroy container, create new container, verify file exists

- [ ] **TODO**: Build image pre-pulling during system startup
  - **File**: `backend/services/container_manager.py` - `startup()` method
  - **Trigger**: System startup, before accepting requests
  - **Logic**: For each language: docker_client.images.pull(image) → Log progress → Handle failures
  - **Timing**: Runs once at startup, blocks until complete
  - **Acceptance**: All images pulled before system ready, logs progress, handles missing images
  - **Test**: Start system with no cached images, verify all images pulled

- [ ] **TODO**: Create orphaned container cleanup job (hourly)
  - **File**: `backend/jobs/container_cleanup.py`
  - **Schedule**: Hourly via cron
  - **Logic**: List all containers with label helix-managed → Check if task_id in active_containers → Destroy if orphaned
  - **Orphan Detection**: Container exists but not in active tracking dict
  - **Acceptance**: Cleans up orphaned containers, logs cleanup, doesn't affect active containers
  - **Test**: Create orphaned container, run cleanup, verify removal

- [ ] **TODO**: Implement error handling for container operations
  - **File**: `backend/services/container_manager.py` - add error handling to all methods
  - **Errors**: Image not found, container creation failure, command execution timeout, cleanup failure
  - **Handling**: Log error → Return structured error response → Don't crash service
  - **Retry**: No automatic retry (agent decides whether to retry)
  - **Acceptance**: All errors caught and logged, service remains stable, clear error messages
  - **Test**: Simulate various errors, verify handling

- [ ] **TODO**: Build container creation/destruction tests
  - **File**: `backend/tests/integration/test_container_lifecycle.py`
  - **Tests**: Create container, destroy container, create+destroy cycle, error handling
  - **Coverage**: All 8 languages, volume mounting, cleanup
  - **Acceptance**: All tests pass, containers properly cleaned up after tests
  - **Test**: Run test suite, verify no orphaned containers

- [ ] **TODO**: Create multi-operation task tests (same container)
  - **File**: `backend/tests/integration/test_multi_operation_task.py`
  - **Scenario**: Create container → Execute command 1 → Execute command 2 → Execute command 3 → Destroy container
  - **Validation**: All commands execute in same container, state persists between commands, files persist
  - **Acceptance**: Multiple operations work correctly, container reused within task
  - **Test**: Full task simulation with multiple operations

- [ ] **TODO**: Implement performance tests (container startup time <3s target)
  - **File**: `backend/tests/performance/test_container_performance.py`
  - **Metrics**: Container creation time, first command execution time, total startup time
  - **Target**: <2s creation, <1s first command, <3s total
  - **Test**: Create 10 containers, measure times, calculate average, assert <3s
  - **Acceptance**: Meets performance targets, consistent timing, no outliers
  - **Test**: Run performance test suite, verify targets met

### 2.2 Web Search Integration

- [ ] **TODO**: Set up self-hosted SearXNG instance
  - **File**: `docker-compose.yml` - add SearXNG service
  - **Service**: searxng/searxng:latest, port 8080, custom config volume
  - **Config**: `config/searxng/settings.yml` - search engines, rate limits, privacy settings
  - **Acceptance**: SearXNG running, accessible from backend, configured search engines
  - **Test**: Search query test, verify results, check privacy settings

- [ ] **TODO**: Create search API integration for LLM agents
  - **File**: `backend/services/web_search_service.py`
  - **Class**: `WebSearchService` with method `search(query: str, num_results: int = 10) -> List[SearchResult]`
  - **Integration**: Calls SearXNG API, parses results, returns structured data
  - **Rate Limiting**: Max 10 searches per minute per agent
  - **Acceptance**: Search works, returns structured results, rate limiting enforced
  - **Test**: Test search queries, verify rate limiting, check result structure

- [ ] **TODO**: Implement search result processing and filtering
  - **File**: `backend/services/web_search_service.py` - `process_results()` method
  - **Processing**: Remove duplicates, filter by relevance score, extract snippets
  - **Filtering**: Block adult content, remove low-quality results, prioritize technical sites
  - **Acceptance**: Results are clean, relevant, deduplicated
  - **Test**: Test with various queries, verify filtering, check quality

- [ ] **TODO**: Build search access controls and logging
  - **File**: `backend/services/web_search_service.py` - add access control
  - **Control**: Only specific agents can search (Backend Dev, Frontend Dev, Research agents)
  - **Logging**: Log all searches with agent_id, query, result_count, timestamp
  - **Acceptance**: Access control enforced, all searches logged
  - **Test**: Test access control, verify logging, test unauthorized access

- [ ] **TODO**: Design LLM prompt integration for web search queries
  - **File**: `backend/prompts/search_query_generator.txt`
  - **Purpose**: Help agents formulate effective search queries
  - **Template**: "To find information about {{topic}}, search for: {{optimized_query}}"
  - **Acceptance**: Agents generate better search queries, results more relevant
  - **Test**: Test query generation, verify search result quality

- [ ] **TODO**: Create search result summarization for agent context
  - **File**: `backend/services/web_search_service.py` - `summarize_results()` method
  - **Summarization**: Extract key points from top 5 results, combine into concise summary
  - **Format**: Bullet points, max 500 tokens, includes source URLs
  - **Acceptance**: Summaries are accurate, concise, include sources
  - **Test**: Test summarization with various search results, verify quality

### 2.3 Tool Access Service (TAS)
- [ ] **TODO**: Design centralized tool access broker for LLM agents (existing architecture)
- [ ] **TODO**: Implement privilege enforcement per agent type
- [ ] **TODO**: Create audit logging for all LLM tool access
- [ ] **TODO**: Build security boundary enforcement system
- [ ] **TODO**: Add LLM request validation and sanitization (minimal additions)
- [ ] **TODO**: Implement tool usage tracking for cost optimization

### 2.3.1 TAS Implementation (Decision 71)
**Reference**: `docs/architecture/decision-71-tool-access-service.md` (contains complete API specs and schemas)

- [ ] **TODO**: Implement TAS REST API service with FastAPI
  - **File**: `backend/services/tool_access_service.py`
  - **Class**: `ToolAccessService` - singleton FastAPI app
  - **Port**: 8001 (separate from main API on 8000)
  - **Acceptance**: Service starts independently, health check endpoint, proper logging
  - **Test**: Service startup test, health check returns 200

- [ ] **TODO**: Create tool execution endpoint (POST /api/v1/tools/execute)
  - **Endpoint**: POST `/api/v1/tools/execute`
  - **Request**: {"agent_id": str, "tool_name": str, "operation": str, "parameters": dict, "project_id": str}
  - **Response**: {"allowed": bool, "result": dict, "audit_id": int} or 403 if denied
  - **Logic**: Check permission → Execute if allowed → Log audit → Return result
  - **Acceptance**: Returns 403 for denied, 200 for allowed, logs all attempts
  - **Test**: Test allowed/denied scenarios, verify audit logging

- [ ] **TODO**: Build validation endpoint (POST /api/v1/tools/validate)
  - **Endpoint**: POST `/api/v1/tools/validate`
  - **Request**: {"agent_id": str, "tool_name": str, "operation": str}
  - **Response**: {"allowed": bool, "reason": str}
  - **Purpose**: Check permission without executing (dry-run)
  - **Acceptance**: Returns permission status, doesn't log to audit, fast response (<10ms)
  - **Test**: Validate various agent-tool combinations

- [ ] **TODO**: Implement permission query endpoint (GET /api/v1/tools/permissions/{agent_id})
  - **Endpoint**: GET `/api/v1/tools/permissions/{agent_id}`
  - **Response**: {"agent_id": str, "permissions": [{"tool_name": str, "allowed": bool}]}
  - **Purpose**: Get all permissions for an agent
  - **Acceptance**: Returns complete permission list, cached for 5 minutes
  - **Test**: Query permissions for all agent types

- [ ] **TODO**: Create audit log query endpoint (GET /api/v1/audit/logs)
  - **Endpoint**: GET `/api/v1/audit/logs?project_id=X&agent_id=Y&start_date=Z&limit=100`
  - **Response**: {"logs": [{audit_log_object}], "total": int, "page": int}
  - **Filters**: project_id, agent_id, tool_name, allowed, date range
  - **Acceptance**: Paginated results, efficient queries with indexes, max 1000 results
  - **Test**: Query with various filters, test pagination

- [ ] **TODO**: Build agent_tool_permissions table in PostgreSQL
  - **Migration**: Already covered in 6.2.1 (migration 008)
  - **Seed Data**: Load default permissions from `backend/config/default_permissions.yaml`
  - **Acceptance**: Table populated with defaults, ready for queries
  - **Test**: Verify seed data loaded correctly

- [ ] **TODO**: Implement permission check logic (deny by default)
  - **File**: `backend/services/tool_access_service.py` - `check_permission()` method
  - **Logic**: Query agent_tool_permissions WHERE agent_type=X AND tool_name=Y, return allowed (default false if not found)
  - **Caching**: Cache results for 5 minutes to reduce DB load
  - **Acceptance**: Denies by default, respects DB permissions, cache invalidation works
  - **Test**: Test default deny, explicit allow, explicit deny, cache behavior

- [ ] **TODO**: Create default permission templates for agent roles
  - **File**: `backend/config/default_permissions.yaml`
  - **Templates**: Define permissions for each agent type (orchestrator: all, backend_dev: file_write + docker, etc.)
  - **Format**: YAML with agent_type, tool_name, allowed fields
  - **Acceptance**: Comprehensive permissions for all 10 agent types, documented rationale
  - **Test**: Load templates, verify completeness, test application

- [ ] **TODO**: Build tool_audit_logs table with 1-year retention
  - **Migration**: Already covered in 6.2.1 (migration 009)
  - **Retention**: Daily cleanup job deletes records >365 days old
  - **Acceptance**: High-volume inserts supported, efficient time-range queries
  - **Test**: Insert audit logs, verify retention cleanup

- [ ] **TODO**: Implement audit log writing on every tool request
  - **File**: `backend/services/tool_access_service.py` - `log_audit()` method
  - **Timing**: Log before execution (request) and after (result)
  - **Fields**: timestamp, project_id, agent_id, tool_name, operation, allowed, parameters, result
  - **Acceptance**: Logs all requests (allowed and denied), async write to avoid blocking, handles failures gracefully
  - **Test**: Verify logging on success/failure, test async behavior

- [ ] **TODO**: Create daily cleanup job for old audit logs
  - **File**: `backend/jobs/audit_cleanup.py`
  - **Schedule**: Daily at 2 AM via cron
  - **Logic**: DELETE FROM tool_audit_log WHERE created_at < NOW() - INTERVAL '365 days'
  - **Acceptance**: Runs daily, logs deletion count, doesn't block operations
  - **Test**: Insert old records, run cleanup, verify deletion

- [ ] **TODO**: Build frontend permission matrix UI
  - **File**: `frontend/src/pages/ToolPermissions.tsx`
  - **Layout**: Table with agents as rows, tools as columns, checkboxes for permissions
  - **Features**: Bulk edit, save changes, reset to defaults
  - **Acceptance**: Visual matrix, real-time updates, shows current state
  - **Test**: E2E test toggling permissions, verify persistence

- [ ] **TODO**: Implement permission editing interface
  - **File**: `frontend/src/pages/ToolPermissions.tsx` - edit mode
  - **API**: PUT `/api/v1/tools/permissions` with bulk update
  - **Validation**: Confirm dangerous changes (e.g., removing orchestrator permissions)
  - **Acceptance**: Edits save to database, cache invalidation, audit trail
  - **Test**: Edit permissions, verify API call, check database

- [ ] **TODO**: Create permission templates (role-based)
  - **File**: `frontend/src/pages/ToolPermissions.tsx` - template dropdown
  - **Templates**: "Restrictive", "Balanced", "Permissive", "Custom"
  - **Action**: Apply template button loads predefined permission set
  - **Acceptance**: Templates apply correctly, user can customize after applying
  - **Test**: Apply each template, verify permissions set

- [ ] **TODO**: Build audit log viewer in frontend
  - **File**: `frontend/src/pages/AuditLogs.tsx`
  - **Features**: Filterable table (project, agent, tool, date range), export to CSV
  - **Display**: Timestamp, agent, tool, operation, allowed/denied, parameters (collapsed)
  - **Acceptance**: Paginated, fast queries, expandable details
  - **Test**: Load logs, apply filters, test pagination

- [ ] **TODO**: Implement agent-TAS integration (base class TAS client)
  - **File**: `backend/agents/base_agent.py` - add `TASClient` mixin
  - **Methods**: `request_tool_access()`, `validate_permission()`, `handle_denial()`
  - **Integration**: All tool calls go through TAS client
  - **Acceptance**: Agents use TAS for all tool access, handle denials gracefully
  - **Test**: Agent tool access test with TAS, verify permission checks

- [ ] **TODO**: Create error handling for permission denials
  - **File**: `backend/agents/base_agent.py` - `handle_denial()` method
  - **Logic**: Log denial, create human gate if needed, provide clear error message
  - **Acceptance**: Denials don't crash agent, user notified, escalation path clear
  - **Test**: Trigger denial, verify gate creation, check error message

- [ ] **TODO**: Build escalation helper methods for agents
  - **File**: `backend/agents/base_agent.py` - `request_permission_escalation()` method
  - **Logic**: Create gate with permission request, wait for human approval, retry on approval
  - **Acceptance**: Agent can request permission elevation, gate shows context, approval grants temporary access
  - **Test**: Request escalation, approve gate, verify tool access granted

- [ ] **TODO**: Create Mock TAS for unit tests
  - **File**: `backend/tests/mocks/mock_tas.py`
  - **Class**: `MockToolAccessService` - in-memory permission store
  - **Features**: Configurable permissions, audit log capture, no DB required
  - **Acceptance**: Drop-in replacement for tests, fast, deterministic
  - **Test**: Use mock in agent tests, verify behavior

- [ ] **TODO**: Implement TAS integration test suite
  - **File**: `backend/tests/integration/test_tool_access_service.py`
  - **Tests**: Permission check, tool execution, audit logging, API endpoints
  - **Coverage**: All endpoints, permission scenarios, error cases
  - **Acceptance**: 100% endpoint coverage, tests pass consistently
  - **Test**: Run integration tests against real TAS instance

- [ ] **TODO**: Create OpenAPI specification for TAS
  - **File**: Auto-generated by FastAPI at `/api/v1/docs`
  - **Export**: `backend/api/openapi_tas.json`
  - **Documentation**: Request/response schemas, authentication, error codes
  - **Acceptance**: Complete API documentation, examples for all endpoints
  - **Test**: Verify OpenAPI spec validates, test with Swagger UI

### 2.4 GitHub Integration
- [ ] **TODO**: Implement GitHub OAuth authentication
- [ ] **TODO**: Create repository management system
- [ ] **TODO**: Build milestone-based PR workflow (existing gates)
- [ ] **TODO**: Implement straight-to-main branch strategy
- [ ] **TODO**: Create GitHub Specialist agent integration with LLM capabilities
- [ ] **TODO**: Add LLM-generated commit message and PR description optimization
- [ ] **TODO**: Build automated code review integration with AI analysis

### 2.4.1 GitHub Specialist Agent (Decision 77)
**Reference**: `docs/architecture/decision-77-github-specialist-agent.md`

- [ ] **TODO**: Create github_credentials table with encryption
  - **Migration**: Already covered in 6.2.1 (migration 014)
  - **Schema**: id, user_id (UNIQUE), access_token_encrypted, refresh_token_encrypted, token_expiry, created_at, updated_at
  - **Encryption**: Fernet symmetric encryption for tokens
  - **Acceptance**: Table stores encrypted tokens, one credential per user
  - **Test**: Store credentials, verify encryption, test retrieval

- [ ] **TODO**: Implement OAuth flow (frontend + backend)
  - **Frontend**: `frontend/src/pages/GitHubConnect.tsx` - OAuth initiation
  - **Backend**: `backend/api/routes/github_oauth.py` - OAuth callback handler
  - **Flow**: User clicks Connect → Redirect to GitHub → GitHub redirects back → Exchange code for tokens → Store encrypted
  - **Endpoints**: GET `/api/v1/github/connect` (initiate), GET `/api/v1/github/callback` (handle callback)
  - **Acceptance**: Full OAuth flow works, tokens stored securely, user redirected back to app
  - **Test**: E2E OAuth flow test with mock GitHub

- [ ] **TODO**: Build GitHubCredentialManager with token encryption (Fernet)
  - **File**: `backend/services/github_credential_manager.py`
  - **Class**: `GitHubCredentialManager` with methods: `store_tokens()`, `get_access_token()`, `refresh_access_token()`
  - **Encryption**: Use cryptography.fernet.Fernet with key from environment variable
  - **Key Management**: GITHUB_ENCRYPTION_KEY in environment, generated once and stored securely
  - **Acceptance**: Tokens encrypted at rest, decrypted on retrieval, key never logged
  - **Test**: Store/retrieve tokens, verify encryption, test key rotation

- [ ] **TODO**: Implement automatic token refresh logic
  - **File**: `backend/services/github_credential_manager.py` - `refresh_access_token()` method
  - **Trigger**: When access token expired (checked in get_access_token())
  - **Logic**: Decrypt refresh token → Call GitHub OAuth refresh endpoint → Store new tokens
  - **Endpoint**: POST https://github.com/login/oauth/access_token with refresh_token grant
  - **Acceptance**: Tokens refresh automatically, transparent to agent, updates database
  - **Test**: Expire token, trigger refresh, verify new tokens stored

- [ ] **TODO**: Create GitHubSpecialistAgent with 3 operations (create repo, delete repo, merge PR)
  - **File**: `backend/agents/github_specialist_agent.py`
  - **Class**: `GitHubSpecialistAgent` with methods: `create_repo()`, `delete_repo()`, `merge_pr()`
  - **Operations**: POST /user/repos (create), DELETE /repos/{owner}/{repo} (delete), PUT /repos/{owner}/{repo}/pulls/{number}/merge (merge)
  - **Authentication**: Uses Bearer token from GitHubCredentialManager
  - **Acceptance**: All 3 operations work, uses GitHub API v3, handles responses correctly
  - **Test**: Test each operation with mock GitHub API

- [ ] **TODO**: Build retry logic with exponential backoff (3 attempts)
  - **File**: `backend/agents/github_specialist_agent.py` - `_execute_with_retry()` method
  - **Logic**: Try operation → On failure: wait 2^attempt seconds → Retry → Max 3 attempts
  - **Backoff**: 1s, 2s, 4s between retries
  - **Failure**: After 3 attempts, return error with trigger_gate=True
  - **Acceptance**: Retries on transient failures, exponential backoff works, gives up after 3 attempts
  - **Test**: Simulate failures, verify retry timing, test max attempts

- [ ] **TODO**: Implement error handling and gate triggering
  - **File**: `backend/agents/github_specialist_agent.py` - error handling in all methods
  - **Errors**: API errors, network errors, authentication errors, rate limiting
  - **Gate Trigger**: Return {success: false, trigger_gate: true, reason: "..."} on max retries
  - **Orchestrator**: Checks trigger_gate flag, creates human approval gate if true
  - **Acceptance**: All errors handled, gates triggered appropriately, clear error messages
  - **Test**: Simulate various errors, verify gate triggering

- [ ] **TODO**: Create GitHub settings page in frontend
  - **File**: `frontend/src/pages/GitHubSettings.tsx`
  - **Route**: `/settings/github`
  - **Features**: Connection status, Connect/Disconnect buttons, connected account info, last sync time
  - **Acceptance**: Shows connection status, OAuth flow works, disconnect removes credentials
  - **Test**: E2E test connecting/disconnecting GitHub

- [ ] **TODO**: Build OAuth connection UI (connect/disconnect/status)
  - **File**: `frontend/src/components/GitHubConnection.tsx`
  - **States**: Not connected (show Connect button), Connected (show account info + Disconnect button), Connecting (loading state)
  - **Connect**: Opens OAuth popup, handles callback, updates UI
  - **Disconnect**: Calls DELETE `/api/v1/github/credentials`, updates UI
  - **Acceptance**: Clear UI states, OAuth popup works, status updates in real-time
  - **Test**: Component tests for all states, E2E connection flow

- [ ] **TODO**: Implement orchestrator integration for GitHub operations
  - **File**: `backend/services/orchestrator.py` - add `request_github_operation()` method
  - **Integration**: Orchestrator calls GitHubSpecialistAgent.execute_action()
  - **Gate Handling**: If trigger_gate in response, create human approval gate
  - **Context**: Provide operation context to user in gate (what failed, why, retry options)
  - **Acceptance**: Orchestrator can request GitHub operations, handles gates, logs operations
  - **Test**: Integration test with orchestrator and GitHub agent

- [ ] **TODO**: Create GitHub operation tests (create, delete, merge)
  - **File**: `backend/tests/integration/test_github_operations.py`
  - **Tests**: Test each operation (create repo, delete repo, merge PR) with mock GitHub API
  - **Validation**: Verify API calls, check request format, validate responses
  - **Acceptance**: All operations tested, mocks realistic GitHub responses
  - **Test**: Run test suite, verify all operations work

- [ ] **TODO**: Build OAuth flow and token refresh tests
  - **File**: `backend/tests/integration/test_github_oauth.py`
  - **Tests**: OAuth initiation, callback handling, token storage, token refresh, expiry handling
  - **Mock**: Mock GitHub OAuth endpoints
  - **Acceptance**: Full OAuth flow tested, token refresh works, encryption verified
  - **Test**: Run OAuth test suite

- [ ] **TODO**: Implement retry logic and error handling tests
  - **File**: `backend/tests/unit/test_github_retry_logic.py`
  - **Tests**: Retry on failure, exponential backoff timing, max retries, gate triggering
  - **Scenarios**: Transient failure (succeeds on retry), permanent failure (triggers gate), rate limiting
  - **Acceptance**: All retry scenarios tested, timing verified, gate triggering works
  - **Test**: Unit tests for retry logic

### 2.5 Human-in-the-Loop System

- [ ] **TODO**: Build approval checkpoint system for LLM-generated decisions (existing gates)
  - **Note**: Already covered in 1.3 (Decision-Making & Escalation System)
  - **Reference**: GateManager service in section 1.3 above
  - **Acceptance**: Gate system implemented with multiple trigger types
  - **Test**: Covered in 1.3 tests

- [ ] **TODO**: Create frontend approval modal interface
  - **Note**: Already covered in 1.3 (GateApprovalModal component)
  - **Reference**: GateApprovalModal.tsx in section 1.3 above
  - **Acceptance**: Modal shows gate details, approve/deny workflow implemented
  - **Test**: Covered in 1.3 tests

- [ ] **TODO**: Implement project pause/resume functionality (manual cost control)
  - **File**: `backend/api/routes/projects.py` - add pause/resume endpoints
  - **Endpoints**: POST /api/v1/projects/{id}/pause, POST /api/v1/projects/{id}/resume
  - **Logic**: Pause stops active agents, saves state, Resume restarts from saved state
  - **UI**: Pause/Resume buttons on project detail page
  - **Acceptance**: Can pause/resume projects, state preserved, agents stop/restart correctly
  - **Test**: E2E test pause and resume workflow

- [ ] **TODO**: Design rejection handling with resolution cycles
  - **File**: `backend/services/gate_manager.py` - `handle_rejection()` method
  - **Flow**: User denies gate with feedback → Agent receives feedback → Agent revises approach → Resubmits for approval
  - **Cycles**: Track revision attempts, escalate after 3 rejections
  - **Acceptance**: Rejection feedback delivered to agent, revision cycle works, escalation triggers
  - **Test**: Test rejection cycles, verify feedback delivery, test escalation

- [ ] **TODO**: Add LLM decision explanation and justification display
  - **File**: `frontend/src/components/DecisionExplanation.tsx`
  - **Display**: Shows agent's reasoning, decision rationale, alternatives considered
  - **Format**: Structured display with reasoning steps, confidence scores, trade-offs
  - **Acceptance**: Explanations clear, reasoning visible, helps user make informed decisions
  - **Test**: Component test with mock decision data

- [ ] **TODO**: Create human feedback integration for prompt optimization
  - **File**: `backend/services/feedback_collector.py`
  - **Class**: `FeedbackCollector` with method `collect_feedback(gate_id, feedback_type, feedback_text)`
  - **Integration**: Feedback stored, analyzed for patterns, used to improve prompts
  - **Analysis**: Identify common rejection reasons, suggest prompt improvements
  - **Acceptance**: Feedback collected, patterns identified, actionable insights generated
  - **Test**: Collect feedback, verify storage, test pattern analysis

---

## Phase 3: Development Workflow Implementation

### 3.1 Phase Management System
- [ ] **TODO**: Create 6-phase workflow engine with LLM agent coordination
- [ ] **TODO**: Implement phase deliverable tracking with AI validation
- [ ] **TODO**: Build phase completion validation (checklist + 100% tests + human approval - existing)
- [ ] **TODO**: Design phase transition system with LLM agent handoffs
- [ ] **TODO**: Add LLM-generated progress reports and status updates
- [ ] **TODO**: Create AI-assisted phase planning and milestone generation

### 3.2 Testing Framework Integration
- [ ] **TODO**: Set up testing frameworks (pytest, Jest, Playwright, etc.)
- [ ] **TODO**: Implement "test reality" philosophy (minimal mocking - existing)
- [ ] **TODO**: Create staged testing pipeline with early failure detection (existing 7-stage)
- [ ] **TODO**: Build 100% coverage enforcement system (existing)
- [ ] **TODO**: Add LLM-powered test generation and optimization (AI-assisted testing)
- [ ] **TODO**: Implement AI-assisted test case design and edge case identification
- [ ] **TODO**: Create automated test maintenance with AI updates

### 3.3 Quality Assurance System
- [ ] **TODO**: Implement test quality scoring with AI analysis (AI-assisted testing)
- [ ] **TODO**: Create continuous learning from test failures using LLM analysis
- [ ] **TODO**: Build security testing integration with AI vulnerability detection (existing + AI)
- [ ] **TODO**: Design performance testing framework with AI optimization
- [ ] **TODO**: Add LLM-powered code review and quality assessment
- [ ] **TODO**: Create AI-driven quality metrics and improvement recommendations

### 3.4 Debugging & Failure Resolution
- [ ] **TODO**: Create structured debugging process with LLM assistance
- [ ] **TODO**: Implement agent collaboration for problem solving (existing)
- [ ] **TODO**: Build escalation paths for specialist help (existing)
- [ ] **TODO**: Design progress recognition vs. identical failure detection (existing 3-cycle gate)
- [ ] **TODO**: Add AI-powered root cause analysis and failure prediction
- [ ] **TODO**: Create LLM-generated debugging strategies and solutions

---

## Phase 4: Frontend & Monitoring Implementation

### 4.1 Frontend Architecture
- [ ] **TODO**: Set up React + TypeScript project structure
- [ ] **TODO**: Implement Tailwind CSS + Headless UI + Lucide React
- [ ] **TODO**: Create Zustand state management setup
- [ ] **TODO**: Build React Query for server state management
- [ ] **TODO**: Implement WebSocket integration for real-time updates
- [ ] **TODO**: Add LLM response streaming and real-time display
- [ ] **TODO**: Create frontend LLM prompt editing interface

### 4.2 Dashboard System
- [ ] **TODO**: Create main dashboard with project cards
- [ ] **TODO**: Build responsive grid layout (1/2/4+ columns)
- [ ] **TODO**: Implement rich project card information display
- [ ] **TODO**: Create real-time color-coded status system
- [ ] **TODO**: Build "New Project" button functionality
- [ ] **TODO**: Add LLM agent status and activity monitoring
- [ ] **TODO**: Create AI-powered project insights and recommendations

### 4.3 Navigation & Layout
- [ ] **TODO**: Implement sidebar navigation system
- [ ] **TODO**: Create Dashboard, Reporting, AI Costs, Team, Archive, Settings pages
- [ ] **TODO**: Build dark blue dark mode theme
- [ ] **TODO**: Design responsive mobile layout
- [ ] **TODO**: Add LLM cost tracking dashboard and visualizations (manual control)
- [ ] **TODO**: Create AI agent performance monitoring interface

### 4.4 Project Detail Pages
- [ ] **TODO**: Create comprehensive project command center
- [ ] **TODO**: Build foldable file directory browser
- [ ] **TODO**: Implement Monaco Editor integration
- [ ] **TODO**: Create agent chat stream viewer (read-only)
- [ ] **TODO**: Build manual gate trigger interface
- [ ] **TODO**: Add LLM conversation history and context viewer
- [ ] **TODO**: Create AI decision explanation and justification display

### 4.5 Settings & Configuration
- [ ] **TODO**: Implement database-stored settings system
- [ ] **TODO**: Create GitHub Integration settings page
- [ ] **TODO**: Build OpenAI Integration settings page (API key config)
- [ ] **TODO**: Design Agents and Specialists configuration pages (model selection)
- [ ] **TODO**: Implement encrypted credential storage
- [ ] **TODO**: Add LLM provider configuration and API key management (single key)
- [ ] **TODO**: Create prompt template editing and versioning interface

### 4.6 Monitoring & Cost Tracking
- [ ] **TODO**: Build comprehensive metrics collection system
- [ ] **TODO**: Implement per-LLM-call cost tracking (token usage logging)
- [ ] **TODO**: Create cost breakdown by project, agent, and action
- [ ] **TODO**: Build pricing matrix management system
- [ ] **TODO**: Design cost reporting dashboard (manual oversight)
- [ ] **TODO**: Add real-time LLM usage monitoring and alerts
- [ ] **TODO**: Create AI performance metrics and optimization insights

### 4.6.1 Cost Tracking System (Decision 75)
- [ ] **TODO**: Create pricing management settings page (/settings/pricing)
- [ ] **TODO**: Build cost dashboard with visualizations (/dashboard/costs)
- [ ] **TODO**: Implement time range selector (hour/day/week/month/quarter/year)
- [ ] **TODO**: Create overview cards (total cost, tokens, calls)
- [ ] **TODO**: Build line chart for cost over time
- [ ] **TODO**: Implement bar chart for cost by project
- [ ] **TODO**: Create pie chart for cost by agent
- [ ] **TODO**: Build drill-down table (cost by agent per project)
- [ ] **TODO**: Implement pricing matrix editing UI
- [ ] **TODO**: Create manual pricing update interface

### 4.7 Archive System
- [ ] **TODO**: Create project archive page
- [ ] **TODO**: Build completed/cancelled project listing
- [ ] **TODO**: Implement GitHub repository management (view/delete)
- [ ] **TODO**: Design historical project tracking interface
- [ ] **TODO**: Add LLM conversation history and decision archive
- [ ] **TODO**: Create AI-generated project summaries and lessons learned

### 4.7.1 Project Cancellation Workflow (Decision 81)
**Reference**: `docs/architecture/decision-81-project-cancellation-workflow.md`

- [ ] **TODO**: Create cancelled_projects table
  - **Migration**: `alembic/versions/018_create_cancelled_projects.py`
  - **Schema**: id, project_id, project_name, stage, cancelled_at, cancelled_by (FK users), reason, metadata (JSONB)
  - **Indexes**: idx_cancelled_projects_user, idx_cancelled_projects_date
  - **Purpose**: Log cancellations for analytics (what stage do users cancel?)
  - **Acceptance**: Table stores cancellation records, supports analytics queries
  - **Test**: Insert cancellation, query by user/date, verify indexes

- [ ] **TODO**: Implement ProjectManager.cancel_project() method
  - **File**: `backend/services/project_manager.py` - add `cancel_project()` method
  - **Parameters**: project_id, user_id, reason (optional)
  - **Flow**: Get project info → Log cancellation → Stop containers → Delete files → Delete DB records → Return success
  - **Acceptance**: Full deletion process works, all resources cleaned up, logged correctly
  - **Test**: Cancel project, verify all resources deleted, check cancellation log

- [ ] **TODO**: Build cancellation logging (project info, stage, reason)
  - **File**: `backend/services/project_manager.py` - `log_cancellation()` method
  - **Data Logged**: project_id, project_name, current_stage, cancelled_by, reason, metadata (language, tasks_completed, created_at, last_activity)
  - **Purpose**: Analytics only, not for recovery
  - **Acceptance**: All relevant info logged, metadata includes useful context
  - **Test**: Cancel project, verify log entry, check metadata completeness

- [ ] **TODO**: Create resource destruction logic (containers, files, database)
  - **File**: `backend/services/project_manager.py` - helper methods
  - **Methods**: `stop_project_containers()`, `delete_project_files()`, `delete_project_records()`
  - **Order**: Stop containers → Delete files from volume → Delete database records
  - **Safety**: Each step has error handling, logs failures, continues to next step
  - **Acceptance**: All resources deleted, handles partial failures, logs all steps
  - **Test**: Test each deletion step, verify cleanup, test error handling

- [ ] **TODO**: Build frontend Delete Project button with confirmation modal
  - **File**: `frontend/src/pages/ProjectDetail.tsx` - add Delete button
  - **Button**: Red/danger styled, placed in project actions area
  - **Modal**: Opens on click, shows warning and confirmation form
  - **Acceptance**: Button visible, modal opens, styled appropriately
  - **Test**: Component test for button and modal

- [ ] **TODO**: Implement two-step confirmation (type "DELETE")
  - **File**: `frontend/src/components/DeleteProjectModal.tsx`
  - **UI**: Warning message, list of what will be deleted, text input requiring "DELETE", Cancel/Delete buttons
  - **Validation**: Delete button disabled until "DELETE" typed exactly
  - **API Call**: On confirm, calls DELETE /api/v1/projects/{id}, shows loading state, redirects on success
  - **Acceptance**: Two-step confirmation works, prevents accidental deletion, API call succeeds
  - **Test**: E2E test deletion flow, verify confirmation requirement

- [ ] **TODO**: Create cancellation analytics dashboard
  - **File**: `frontend/src/pages/CancellationAnalytics.tsx`
  - **Route**: `/analytics/cancellations` (admin only)
  - **Metrics**: Cancellations by stage, cancellations over time, common reasons, cancellation rate
  - **Charts**: Bar chart (by stage), line chart (over time), pie chart (reasons)
  - **Acceptance**: Shows all metrics, charts render correctly, data accurate
  - **Test**: E2E test analytics page, verify data display

- [ ] **TODO**: Build cancellation workflow tests
  - **File**: `backend/tests/integration/test_project_cancellation.py`
  - **Scenarios**: Full cancellation flow, partial failures, already deleted project, unauthorized cancellation
  - **Validation**: Verify logging, resource cleanup, database deletion, error handling
  - **Acceptance**: All scenarios tested, cancellation works correctly, handles errors
  - **Test**: Run cancellation test suite

### 4.7.2 Meet the Team Page (Decision 82)
**Reference**: `docs/architecture/decision-82-meet-the-team-page.md`

- [ ] **TODO**: Create MeetTheTeam page component
  - **File**: `frontend/src/pages/MeetTheTeam.tsx`
  - **Route**: `/team`
  - **Purpose**: Fun easter egg page, not functional, pure entertainment
  - **Layout**: Corporate "About Us" style with agent profile cards
  - **Acceptance**: Page renders, looks professional but humorous, responsive
  - **Test**: Component test, verify rendering

- [ ] **TODO**: Design agent profile cards (name, role, photo, bio, interests, quote)
  - **File**: `frontend/src/components/AgentProfileCard.tsx`
  - **Structure**: Card with avatar, name, role, bio, interests, favorite tool, quote
  - **Style**: Professional card design with subtle humor, consistent spacing
  - **Props**: {name, role, photo, bio, interests, favoriteTool, quote}
  - **Acceptance**: Cards look professional, readable, consistent design
  - **Test**: Component test with sample data

- [ ] **TODO**: Write humorous agent bios (10 agents)
  - **File**: `frontend/src/data/agentProfiles.ts`
  - **Agents**: Orchestrator, Backend Dev, Frontend Dev, QA Engineer, DevOps, Security, PM, Data Analyst, Tech Writer, GitHub Specialist
  - **Tone**: Light humor, relatable tech jokes, personality-driven
  - **Content**: Each has name, role, bio (2-3 sentences), interests (3 items), favorite tool, quote
  - **Acceptance**: All 10 agents have complete profiles, humor is appropriate, relatable
  - **Test**: Review content for quality and appropriateness

- [ ] **TODO**: Create or source agent avatars
  - **Files**: `frontend/public/images/agents/` - 10 avatar images
  - **Options**: AI-generated avatars, icon-based avatars, or illustrated characters
  - **Style**: Consistent style across all avatars, professional but friendly
  - **Format**: PNG or SVG, optimized for web, 200x200px minimum
  - **Acceptance**: All 10 avatars created, consistent style, appropriate quality
  - **Test**: Visual review of all avatars

- [ ] **TODO**: Implement responsive grid layout
  - **File**: `frontend/src/pages/MeetTheTeam.tsx` - grid layout
  - **Layout**: 3 columns on desktop, 2 on tablet, 1 on mobile
  - **Spacing**: Consistent gaps between cards, proper padding
  - **Responsive**: Uses CSS Grid or Flexbox, breakpoints at 768px and 1024px
  - **Acceptance**: Layout responsive, looks good on all screen sizes, no overflow
  - **Test**: Test on various screen sizes, verify responsiveness

- [ ] **TODO**: Add to sidebar navigation
  - **File**: `frontend/src/components/Sidebar.tsx` - add "Meet the Team" link
  - **Position**: Bottom of sidebar, after other main links
  - **Icon**: Team or people icon
  - **Route**: Links to `/team`
  - **Acceptance**: Link visible in sidebar, navigates correctly, icon appropriate
  - **Test**: Click link, verify navigations and quotes for each agent

### 4.6.1 Cost Tracking System (Decision 75)
**Reference**: `docs/architecture/decision-75-cost-tracking-system.md`

- [ ] **TODO**: Create llm_token_usage table
  - **Migration**: Already covered in 6.2.1 (migration 009)
  - **Schema**: id, timestamp, project_id, agent_id, model, input_tokens, output_tokens, created_at
  - **Indexes**: idx_token_usage_timestamp, idx_token_usage_project, idx_token_usage_agent, idx_token_usage_project_agent
  - **Acceptance**: Table stores all token usage, supports fast queries by project/agent/time
  - **Test**: Insert usage records, query by various filters, verify indexes

- [ ] **TODO**: Create llm_pricing table with manual pricing management
  - **Migration**: Already covered in 6.2.1 (migration 010)
  - **Schema**: id, model (UNIQUE), input_cost_per_million, output_cost_per_million, effective_date, updated_at, updated_by, notes
  - **Seed Data**: gpt-4 ($30/$60), gpt-4-turbo ($10/$30), gpt-3.5-turbo ($0.50/$1.50)
  - **Acceptance**: Table stores pricing for all models, supports manual updates, tracks who changed pricing
  - **Test**: Insert pricing, update pricing, verify uniqueness constraint

- [ ] **TODO**: Implement CostTracker service with token logging
  - **File**: `backend/services/cost_tracker.py`
  - **Class**: `CostTracker` with method `log_usage(project_id, agent_id, model, input_tokens, output_tokens)`
  - **Async**: Non-blocking database writes, doesn't slow down LLM calls
  - **Error Handling**: Log failures but don't fail LLM calls
  - **Acceptance**: Logs all token usage, async writes work, handles errors gracefully
  - **Test**: Log usage, verify database writes, test error handling

- [ ] **TODO**: Integrate token capture in LLMAdapter (all LLM calls)
  - **File**: `backend/services/llm_adapter.py` - add token logging to `call_llm()` method
  - **Integration**: After LLM response → Extract token counts from response.usage → Call cost_tracker.log_usage()
  - **Coverage**: EVERY LLM call must log tokens (orchestrator, agents, evaluators)
  - **Acceptance**: All LLM calls log tokens, no calls missed, logging doesn't block
  - **Test**: Make LLM calls, verify token logging, check all agent types

- [ ] **TODO**: Build on-demand cost calculation queries
  - **File**: `backend/services/cost_calculator.py`
  - **Class**: `CostCalculator` with methods: `calculate_project_cost()`, `calculate_agent_cost()`, `calculate_total_cost()`
  - **Formula**: cost = (input_tokens / 1M * input_cost_per_million) + (output_tokens / 1M * output_cost_per_million)
  - **Queries**: Join llm_token_usage with llm_pricing, aggregate by project/agent, calculate costs
  - **Acceptance**: Accurate cost calculations, fast queries (<100ms), handles missing pricing gracefully
  - **Test**: Test calculations with known token counts, verify accuracy

- [ ] **TODO**: Create cost dashboard API endpoints (by project, by agent, drill-down)
  - **File**: `backend/api/routes/costs.py`
  - **Endpoints**: GET /api/v1/costs/projects (all projects), GET /api/v1/costs/projects/{id} (single project), GET /api/v1/costs/agents (by agent)
  - **Filters**: Date range, project, agent
  - **Response**: {total_cost, breakdown_by_agent, breakdown_by_model, token_counts}
  - **Acceptance**: All endpoints work, filters apply correctly, returns accurate costs
  - **Test**: API tests for all endpoints, verify calculations

- [ ] **TODO**: Build pricing management UI (settings page)
  - **File**: `frontend/src/pages/PricingSettings.tsx`
  - **Route**: `/settings/pricing`
  - **Features**: List all models with pricing, edit input/output costs, add new models, save changes
  - **Validation**: Positive numbers only, required fields, confirmation before save
  - **Acceptance**: Can view/edit pricing, changes save to database, validation works
  - **Test**: E2E test editing pricing, verify database updates

- [ ] **TODO**: Implement 1-year rolling retention cleanup job
  - **File**: `backend/jobs/token_usage_cleanup.py`
  - **Schedule**: Daily at 3 AM via cron
  - **Logic**: DELETE FROM llm_token_usage WHERE timestamp < NOW() - INTERVAL '1 year'
  - **Logging**: Log number of records deleted
  - **Acceptance**: Cleanup runs daily, old data deleted, logs deletion count
  - **Test**: Insert old records, run cleanup, verify deletion

- [ ] **TODO**: Create cost tracking tests
  - **File**: `backend/tests/unit/test_cost_tracking.py`
  - **Coverage**: Token logging, cost calculation, API endpoints, pricing management
  - **Scenarios**: Various token counts, multiple models, date ranges
  - **Acceptance**: All cost tracking code tested, edge cases covered
  - **Test**: Run cost tracking test suite

- [ ] **TODO**: Build cost calculation accuracy tests
  - **File**: `backend/tests/unit/test_cost_calculations.py`
  - **Tests**: Known token counts with known pricing, verify exact cost calculations
  - **Examples**: 1M input tokens at $10/M = $10.00, 500K output tokens at $30/M = $15.00
  - **Acceptance**: Calculations accurate to 2 decimal places, handles edge cases (0 tokens, missing pricing)
  - **Test**: Run calculation tests, verify accuracy

- [ ] **TODO**: Build dashboard performance tests with large datasets
- [ ] **TODO**: Create API key management (single key, frontend config)
- [ ] **TODO**: Implement per-agent model selection (gpt-4o-mini, gpt-4.1, gpt-5)
- [ ] **TODO**: Add LLM usage monitoring and metrics collection
- [ ] **TODO**: Build LLM error handling and retry logic
- [ ] **TODO**: Create cost tracking integration with frontend dashboard

### 6.4 Security Implementation
- [ ] **TODO**: Build container isolation security system (existing sandbox)
- [ ] **TODO**: Implement Tool Access Service security boundaries (existing)
- [ ] **TODO**: Create encrypted credential management
- [ ] **TODO**: Build holistic logging system with frontend access (existing)
- [ ] **TODO**: Add LLM prompt injection protection
- [ ] **TODO**: Implement AI-generated code security scanning (minimal additions)
- [ ] **TODO**: Create LLM data privacy and compliance controls

### 6.5 Performance & Scalability
- [ ] **TODO**: Implement unlimited concurrency architecture (existing)
- [ ] **TODO**: Create unlimited resource allocation system (existing)
- [ ] **TODO**: Build no-load-balancing simple architecture (direct integration)
- [ ] **TODO**: Design comprehensive monitoring dashboard
- [ ] **TODO**: Add LLM performance optimization and caching
- [ ] **TODO**: Implement AI-powered performance tuning
- [ ] **TODO**: Create LLM cost optimization algorithms (manual control)

### 6.6 Testing & Quality Assurance (AI-Assisted)
- [ ] **TODO**: Build AI-assisted LLM integration testing framework
- [ ] **TODO**: Implement prompt testing and validation with AI
- [ ] **TODO**: Create LLM response quality assessment with AI
- [ ] **TODO**: Build AI-powered test generation system
- [ ] **TODO**: Add LLM performance benchmarking with AI
- [ ] **TODO**: Create automated prompt optimization testing
- [ ] **TODO**: Implement LLM regression testing and monitoring

### 6.6.1 LLM Testing Strategy (Decision 72)
**Reference**: `docs/architecture/decision-72-llm-testing-strategy.md`

- [ ] **TODO**: Implement rubric validation framework (format, protocol, security)
  - **File**: `backend/services/llm_testing/rubric_validator.py`
  - **Class**: `RubricValidator` with methods: `validate_format()`, `validate_protocol()`, `validate_security()`
  - **Checks**: JSON format compliance, required fields present, protocol adherence, no security violations
  - **Acceptance**: Fast validation (<10ms), catches format errors, returns detailed failure reasons
  - **Test**: Test with valid/invalid outputs, verify all rubric rules

- [ ] **TODO**: Define rubrics per agent type
  - **File**: `backend/config/llm_testing/rubrics.yaml`
  - **Rubrics**: One per agent type (orchestrator, backend_dev, frontend_dev, etc.) with specific rules
  - **Format**: YAML defining required fields, allowed values, format patterns, security rules
  - **Acceptance**: All 10 agent types have rubrics, rules are comprehensive, documented
  - **Test**: Load rubrics, validate structure, test against sample outputs

- [ ] **TODO**: Create AI evaluator system (3-evaluator panel with GPT-4o)
  - **File**: `backend/services/llm_testing/ai_evaluator.py`
  - **Class**: `AIEvaluatorPanel` with method `evaluate(output: str, expected: str) -> EvaluationResult`
  - **Panel**: 3 independent GPT-4o evaluators, each scores 0-100
  - **Criteria**: Task completion, reasoning quality, code quality, protocol adherence
  - **Acceptance**: Returns 3 scores + consensus, handles LLM failures, logs evaluations
  - **Test**: Test with sample outputs, verify consensus calculation

- [ ] **TODO**: Build evaluator prompt templates
  - **File**: `backend/prompts/evaluators/` - separate files per evaluation type
  - **Templates**: task_completion_evaluator.txt, reasoning_evaluator.txt, code_quality_evaluator.txt
  - **Format**: Clear instructions, scoring criteria, examples, output format requirements
  - **Acceptance**: Evaluators produce consistent scores, prompts are clear, examples provided
  - **Test**: Test evaluator prompts with known good/bad outputs

- [ ] **TODO**: Implement consensus calculation (median score, majority agreement)
  - **File**: `backend/services/llm_testing/ai_evaluator.py` - `calculate_consensus()` method
  - **Logic**: Median of 3 scores, flag if scores differ by >20 points, majority agreement on pass/fail
  - **Output**: {median_score, agreement_level, flagged_for_review}
  - **Acceptance**: Consensus calculated correctly, flags disagreements, handles edge cases
  - **Test**: Test with various score combinations, verify flagging logic

- [ ] **TODO**: Create production data collection (10% sampling)
  - **File**: `backend/services/llm_testing/production_sampler.py`
  - **Class**: `ProductionSampler` - samples 10% of successful agent outputs
  - **Trigger**: After successful task completion, random 10% chance
  - **Storage**: Writes to golden_test_cases table with metadata
  - **Acceptance**: Samples at correct rate, only captures successes, includes full context
  - **Test**: Run tasks, verify sampling rate, check data quality

- [ ] **TODO**: Build golden_test_cases table
  - **Migration**: `alembic/versions/017_create_golden_test_cases.py`
  - **Schema**: id, agent_type, input, expected_output, actual_output, metadata (JSONB), sampled_at, human_reviewed, approved
  - **Indexes**: idx_golden_agent_type, idx_golden_approved
  - **Acceptance**: Table stores test cases, supports queries by agent type, tracks review status
  - **Test**: Insert test cases, query by filters, verify indexes

- [ ] **TODO**: Implement human review interface for test cases
  - **File**: `frontend/src/pages/TestCaseReview.tsx`
  - **Features**: List sampled cases, view input/output, approve/reject, add notes, filter by agent type
  - **Workflow**: Review case → Approve (add to golden set) or Reject (discard)
  - **Acceptance**: Easy to review cases, approve/reject works, notes saved
  - **Test**: E2E test reviewing and approving test cases

- [ ] **TODO**: Create dataset management tools
  - **File**: `backend/api/routes/test_datasets.py`
  - **Endpoints**: GET /api/v1/test-datasets, POST /api/v1/test-datasets/{id}/approve, DELETE /api/v1/test-datasets/{id}
  - **Features**: List datasets, approve cases, delete cases, export dataset
  - **Acceptance**: CRUD operations work, export generates valid test file
  - **Test**: API tests for all operations

- [ ] **TODO**: Build A/B regression testing (old vs new prompt versions)
  - **File**: `backend/services/llm_testing/ab_tester.py`
  - **Class**: `ABTester` with method `compare_versions(old_version: str, new_version: str, test_cases: List) -> ComparisonResult`
  - **Process**: Run both versions on same test cases → Evaluate both → Compare scores → Generate recommendation
  - **Acceptance**: Runs A/B tests, compares results statistically, provides clear recommendation
  - **Test**: Test with known better/worse versions, verify recommendation accuracy

- [ ] **TODO**: Implement comparison algorithms and recommendation engine
  - **File**: `backend/services/llm_testing/ab_tester.py` - `generate_recommendation()` method
  - **Metrics**: Average score difference, pass rate difference, statistical significance (t-test)
  - **Recommendation**: "Deploy" (new better), "Reject" (old better), "Review" (mixed results)
  - **Acceptance**: Statistical analysis correct, recommendations sound, explains reasoning
  - **Test**: Test with various result sets, verify statistical calculations

- [ ] **TODO**: Create cost optimization (quick check vs full validation)
  - **File**: `backend/services/llm_testing/test_runner.py`
  - **Modes**: quick_check (10 cases, rubric only), full_validation (all cases, rubric + AI eval)
  - **Logic**: Run quick check first → If passes, optionally run full → If fails, stop
  - **Acceptance**: Quick check is fast (<30s), full validation thorough, cost-effective
  - **Test**: Test both modes, verify cost savings, check accuracy

- [ ] **TODO**: Build test alert system (dashboard, notifications)
  - **File**: `backend/services/llm_testing/alert_system.py`
  - **Triggers**: Test failure, low score, evaluator disagreement, regression detected
  - **Channels**: Dashboard notification, email (optional), webhook (optional)
  - **Content**: Summary, failed cases, recommendation, link to review UI
  - **Acceptance**: Alerts sent on failures, content is actionable, links work
  - **Test**: Trigger alerts, verify delivery, check content

- [ ] **TODO**: Implement review workflow UI
  - **File**: `frontend/src/pages/TestReview.tsx`
  - **Features**: View test results, see A/B comparison, review failed cases, approve/reject changes
  - **Layout**: Side-by-side comparison, score charts, failed case details
  - **Acceptance**: Clear UI, easy to review, decision buttons work
  - **Test**: E2E test review workflow

- [ ] **TODO**: Create approval/rejection actions
  - **File**: `backend/api/routes/llm_testing.py`
  - **Endpoints**: POST /api/v1/tests/{id}/approve, POST /api/v1/tests/{id}/reject
  - **Actions**: Approve (promote new version), Reject (keep old version), both log decision
  - **Acceptance**: Actions execute correctly, version changes applied, logged
  - **Test**: Test approve/reject, verify version changes

- [ ] **TODO**: Build evaluator validation (spot-check sampling)
  - **File**: `backend/services/llm_testing/evaluator_validator.py`
  - **Schedule**: Weekly, sample 20 random evaluations from past week
  - **Process**: Human reviews evaluator scores → Agrees/disagrees → Logs to evaluator_validation_log
  - **Acceptance**: Sampling works, human review tracked, accuracy calculated
  - **Test**: Run validation, verify sampling, check accuracy calculation

- [ ] **TODO**: Implement human review UI for evaluator accuracy
  - **File**: `frontend/src/pages/EvaluatorValidation.tsx`
  - **Features**: View sampled evaluations, see evaluator score, provide human score, agree/disagree
  - **Workflow**: Review evaluation → Provide human judgment → Submit → Update accuracy metrics
  - **Acceptance**: Easy to review, human scores saved, accuracy updated
  - **Test**: E2E test evaluator validation workflow

- [ ] **TODO**: Create accuracy tracking and feedback loop
  - **File**: `backend/services/llm_testing/evaluator_validator.py` - `track_accuracy()` method
  - **Metrics**: Agreement rate (human vs evaluator), average score difference, accuracy by evaluation type
  - **Threshold**: If accuracy <80%, flag for evaluator prompt update
  - **Feedback**: Use disagreement cases to improve evaluator prompts
  - **Acceptance**: Accuracy tracked over time, flags low accuracy, provides improvement suggestions
  - **Test**: Simulate disagreements, verify flagging, test feedback loop

- [ ] **TODO**: Build integration with development workflow (task completion hooks)
  - **File**: `backend/services/orchestrator.py` - add `check_for_llm_testing()` hook
  - **Trigger**: Before marking AI-related task as complete
  - **Detection**: Check if task modified prompts, agent logic, or LLM integration
  - **Action**: If AI functionality changed, trigger LLM tests, block completion until tests pass
  - **Acceptance**: Detects AI changes, triggers tests automatically, enforces testing
  - **Test**: Complete AI task, verify test triggering, test blocking

- [ ] **TODO**: Implement AI functionality detection
  - **File**: `backend/services/llm_testing/ai_change_detector.py`
  - **Logic**: Check git diff for changes in prompts/, agents/, services/orchestrator.py
  - **Keywords**: Detect changes to LLM calls, prompt templates, agent logic
  - **Acceptance**: Accurately detects AI changes, minimal false positives
  - **Test**: Test with AI/non-AI changes, verify detection accuracy

- [ ] **TODO**: Create test triggering logic
  - **File**: `backend/services/llm_testing/test_runner.py` - `trigger_tests()` method
  - **Logic**: Detect changes → Identify affected agents → Load test cases → Run A/B test → Alert on results
  - **Modes**: Auto-trigger on task completion, manual trigger via UI
  - **Acceptance**: Tests trigger correctly, run appropriate test cases, results delivered
  - **Test**: Test auto and manual triggering, verify test execution

- [ ] **TODO**: Build meta-testing (test the testing framework)
  - **File**: `backend/tests/integration/test_llm_testing_framework.py`
  - **Tests**: Test rubric validation, AI evaluator, A/B comparison, alert system, full workflow
  - **Coverage**: All testing components, edge cases, error handling
  - **Acceptance**: Testing framework itself is tested, high confidence in test results
  - **Test**: Run meta-test suite, verify framework reliability

- [ ] **TODO**: Create golden dataset seed
  - **File**: `backend/tests/fixtures/golden_dataset_seed.json`
  - **Content**: 10-20 hand-crafted test cases per agent type, covering common scenarios and edge cases
  - **Quality**: High-quality inputs and expected outputs, diverse scenarios
  - **Acceptance**: Seed dataset covers key scenarios, can bootstrap testing immediately
  - **Test**: Load seed data, run tests, verify quality

- [ ] **TODO**: Write developer guide and evaluator maintenance guide
  - **Files**: `docs/guides/llm-testing-guide.md`, `docs/guides/evaluator-maintenance.md`
  - **Content**: How to run tests, interpret results, update prompts, maintain evaluators, add test cases
  - **Examples**: Step-by-step workflows, common scenarios, troubleshooting
  - **Acceptance**: Guides are comprehensive, easy to follow, cover all workflows
  - **Test**: Have team member follow guides, verify completeness

### 6.6.2 Error Handling System (Decision 80)
**Reference**: `docs/architecture/decision-80-error-handling-system.md`

- [ ] **TODO**: Create error_log table with hierarchical taxonomy
  - **Migration**: Already covered in 6.2.1 (migration 015)
  - **Schema**: id, code (INTEGER), category, message, technical_detail, context (JSONB), project_id, agent_id, task_id, created_at
  - **Indexes**: idx_error_log_code, idx_error_log_project, idx_error_log_timestamp
  - **Acceptance**: Table stores all errors, supports queries by code/project/time, JSONB for flexible context
  - **Test**: Log errors, query by various filters, verify indexes

- [ ] **TODO**: Implement ErrorLogger with structured JSON logging
  - **File**: `backend/services/error_logger.py`
  - **Class**: `ErrorLogger` with method `log_error(code, category, message, technical_detail, context, project_id, agent_id, task_id)`
  - **Dual Logging**: Writes to application log (JSON format) AND database (error_log table)
  - **Async**: Database writes are async to avoid blocking
  - **Acceptance**: All errors logged consistently, JSON format parseable, database writes succeed
  - **Test**: Log various errors, verify log format, check database storage

- [ ] **TODO**: Build error code system (4-digit codes: 1000-5999)
  - **File**: `backend/models/error_codes.py`
  - **Enum**: `ErrorCode` with all defined codes (1001-5999)
  - **Ranges**: 1000-1999 Agent, 2000-2999 System, 3000-3999 External, 4000-4999 User, 5000-5999 Resource
  - **Documentation**: Each code has description, category, recovery strategy
  - **Acceptance**: All codes defined, organized by category, documented
  - **Test**: Verify all codes in valid ranges, check documentation completeness

- [ ] **TODO**: Create error taxonomy (Agent, System, External, User, Resource)
  - **File**: `backend/models/error_codes.py` - define categories and specific errors
  - **Categories**: 5 top-level categories, each with 10-20 specific error types
  - **Mapping**: Each error code maps to category, has user message, technical message, recovery strategy
  - **Acceptance**: Complete taxonomy, all common errors covered, clear categorization
  - **Test**: Verify taxonomy completeness, test categorization logic

- [ ] **TODO**: Implement tiered recovery strategies (retry → agent retry → gate → human)
  - **File**: `backend/services/error_recovery.py`
  - **Class**: `ErrorRecoveryService` with method `attempt_recovery(error: SystemError) -> RecoveryResult`
  - **Tiers**: Tier 1 (automatic retry), Tier 2 (agent retry with different approach), Tier 3 (create gate), Tier 4 (human intervention)
  - **Logic**: Based on error code and context, select appropriate tier, execute recovery, log outcome
  - **Acceptance**: Recovery strategies execute correctly, escalates appropriately, logs all attempts
  - **Test**: Test each tier, verify escalation, test recovery success/failure

- [ ] **TODO**: Build user-friendly error messages (hide technical details)
  - **File**: `backend/models/error_codes.py` - add user_message field to each error
  - **Format**: Clear, actionable messages without technical jargon
  - **Examples**: "Agent timeout" → "The task took longer than expected. We're retrying with more time."
  - **Technical Details**: Stored separately, available in logs and error dashboard for debugging
  - **Acceptance**: All errors have user-friendly messages, technical details hidden from UI, messages are helpful
  - **Test**: Review all error messages, verify clarity, test UI display

- [ ] **TODO**: Create error dashboard in frontend
  - **File**: `frontend/src/pages/ErrorDashboard.tsx`
  - **Features**: Error list (filterable by project, category, time), error details modal, error trends chart, recovery status
  - **Filters**: By project, category, date range, recovery status
  - **Acceptance**: Shows all errors, filters work, charts display trends, details accessible
  - **Test**: E2E test error dashboard, verify filters, check charts

- [ ] **TODO**: Implement error analytics and reporting
  - **File**: `backend/services/error_analytics.py`
  - **Metrics**: Error rate by category, most common errors, recovery success rate, error trends over time
  - **Endpoints**: GET /api/v1/analytics/errors (summary, by-category, trends)
  - **Acceptance**: Analytics calculated correctly, trends identified, actionable insights
  - **Test**: Generate errors, verify analytics, test trend detection

- [ ] **TODO**: Build error handling tests
  - **File**: `backend/tests/unit/test_error_handling.py`
  - **Coverage**: Error logging, code categorization, message formatting, recovery strategy selection
  - **Scenarios**: All error categories, various contexts, edge cases
  - **Acceptance**: All error handling code tested, edge cases covered
  - **Test**: Run error handling test suite

- [ ] **TODO**: Create error recovery tests
  - **File**: `backend/tests/integration/test_error_recovery.py`
  - **Scenarios**: Each recovery tier, escalation between tiers, recovery success/failure, gate creation
  - **Validation**: Verify recovery attempts, check escalation logic, validate gate creation
  - **Acceptance**: All recovery scenarios tested, escalation works correctly
  - **Test**: Run recovery test suite, verify all tiers

---

## Progress Summary

### Overall Progress
- **Total Tasks**: 300+ (FINAL including all Decision 67-82 tasks)
- **Completed**: 6 (Phase 1.1 Orchestrator Core System + Base Agent Class + Backend Developer)
- **In Progress**: 0
- **TODO**: 294+

### Phase Progress (FINAL)
- **Phase 1**: 6/85 completed (Core Architecture + Orchestrator LLM + RAG + Prompts + Collaboration + Loop Detection + Recovery)
- **Phase 2**: 0/60 completed (Tool Ecosystem + TAS + Docker + GitHub Specialist)
- **Phase 3**: 0/22 completed (Development Workflow with AI capabilities)
- **Phase 4**: 0/50 completed (Frontend + API + Cost Tracking + Cancellation + Meet the Team)
- **Phase 5**: 0/22 completed (Deployment & Release with AI automation)
- **Phase 6**: 0/85 completed (Backend API + Database Schema + LLM Testing + Error Handling + Cost System)

### LLM Architecture Implementation Progress
- **✅ Architecture Decisions**: 7/7 completed (Provider, Prompts, Context, Validation, Cost, Service, Testing)
- **🔄 LLM Service Design**: 1/8 completed (OpenAI service created, token logging implemented)
- **🔄 Agent Refactoring**: 1/10 completed (Backend Developer with full LLM integration)
- **🔄 Prompt Engineering**: 0/6 completed (Chain-of-thought templates, versioning, etc.)
- **🔄 LLM Infrastructure**: 0/30 completed (Database, security, testing, etc.)

### Critical Path Items (Based on Final Decisions)
1. **OpenAI Integration & Token Logging** - Foundation for all LLM operations
2. **Backend Developer Agent Refactor** - Reference implementation for chain-of-thought
3. **Database Schema for LLM Operations** - Token usage, prompt versioning, conversation storage
4. **Frontend Model Selection Interface** - Per-agent gpt-4o-mini/gpt-4.1/gpt-5 configuration
5. **AI-Assisted Testing Framework** - Comprehensive LLM testing with AI evaluation

### Immediate Next Steps (Priority Order - FINAL)
1. **Week 1**: Implement OpenAI integration and token usage logging system
2. **Week 1-2**: Create database schema for LLM operations (prompts, usage, conversations)
3. **Week 2**: Refactor Backend Developer agent with chain-of-thought (reference)
4. **Week 2-3**: Build frontend model selection and cost tracking interface
5. **Week 3**: Implement AI-assisted testing framework for LLM components
6. **Week 3-4**: Refactor remaining 9 agents using Backend Developer reference

### Architecture Summary (Based on Decisions)
- **Provider**: OpenAI only with per-agent model selection
- **Prompts**: Full chain-of-thought with agent-specific base prompts
- **Context**: Orchestrator-centric with RAG integration
- **Validation**: Leverage existing safeguards + minimal LLM additions
- **Cost**: Manual control with full visibility dashboard
- **Service**: Direct agent integration with centralized logging
- **Testing**: AI-assisted comprehensive testing framework

---

## Notes
- Each task should be marked as IN_PROGRESS when started
- Tasks should be marked TODO initially, IN_PROGRESS when started, and COMPLETED only when fully implemented and tested
- Update progress summary after completing tasks in each phase
- Add sub-tasks as needed during development process
