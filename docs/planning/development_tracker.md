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

- [x] **COMPLETED**: Implement synchronous task queue system
  - **File**: `backend/services/task_queue.py`
  - **Class**: `TaskQueue` with methods: `enqueue()`, `dequeue()`, `peek()`, `get_pending_count()`, `prioritize_task()`
  - **Implementation**: Python Queue (thread-safe), FIFO ordering, priority queue support for urgent tasks
  - **Task Structure**: `Task(id, type, agent_type, priority, payload, created_at, status)`
  - **Integration**: Orchestrator calls `enqueue()` when receiving work, agents pull via orchestrator `dequeue()`
  - **Acceptance**: Tasks processed in order, thread-safe operations, no race conditions, priority tasks jump queue
  - **Test**: Concurrent enqueue/dequeue tests, priority ordering tests, thread safety tests
  - **Completed**: Nov 1, 2025
  - **Coverage**: 99% (50 tests, all passing)
  - **Documentation**: `docs/implementation/phase1/task-1-1-2-task-queue.md`

- [x] **COMPLETED**: Create agent communication protocol (agent ↔ orchestrator ↔ agent)
  - **File**: `backend/models/communication.py`
  - **Classes**: `BaseMessage`, `TaskAssignmentMessage`, `TaskResultMessage`, `HelpRequestMessage`, `SpecialistResponseMessage`, `ProgressUpdateMessage`, `ErrorReportMessage`, `MessageRouter`
  - **Protocol**: Pydantic models with: sender_id, recipient_id, message_type, payload, timestamp, correlation_id
  - **Message Types**: TASK_ASSIGNMENT, TASK_RESULT, HELP_REQUEST, SPECIALIST_RESPONSE, PROGRESS_UPDATE, ERROR_REPORT
  - **Flow**: Agent → Orchestrator (always), Orchestrator → Agent (always), Agent → Agent (NEVER - blocked)
  - **Validation**: Pydantic v2 models enforce message structure, MessageRouter validates hub-and-spoke pattern
  - **Acceptance**: ✅ All agent communication routed through orchestrator ✅ Direct agent messages rejected ✅ Message structure validated
  - **Test**: 26 tests, all passing (100% coverage)
  - **Completed**: Nov 1, 2025
  - **Coverage**: 100% (26/26 tests passing)
  - **Documentation**: `docs/implementation/phase1/task-1-1-3-agent-communication-protocol.md`

- [x] **COMPLETED**: Build project state management system
  - **File**: `backend/services/project_state_manager.py`
  - **Class**: `ProjectStateManager` with methods: `get_state()`, `update_state()`, `record_task_completion()`, `get_progress()`, `rollback_state()`
  - **State Structure**: `ProjectState(project_id, current_phase, active_task_id, active_agent_id, completed_tasks: List, pending_tasks: List, metadata: dict, last_updated)`
  - **Persistence**: Database-backed (project_state table), in-memory cache for performance, write-through caching
  - **Recovery**: State snapshots every 5 minutes, restore on crash/restart, transaction log for point-in-time recovery
  - **Acceptance**: State persists to database, survives restarts, accurate progress tracking, rollback capability
  - **Test**: State persistence tests, recovery tests, concurrent update tests, rollback tests (unit + Postgres integration)
  - **Completed**: Nov 1, 2025
  - **Coverage**: 97% branch (`pytest backend/tests/services/test_project_state_manager.py --cov=backend.services.project_state_manager --cov-report=term-missing --cov-branch` and combined unit+integration run)
  - **Documentation**: `docs/implementation/phase1/task-1-1-4-project-state-management-system.md`

- [x] **COMPLETED**: Implement agent lifecycle management (start, pause, stop, cleanup)
  - **File**: `backend/services/agent_lifecycle_manager.py`
  - **Class**: `AgentLifecycleManager` with methods: `start_agent()`, `pause_agent()`, `resume_agent()`, `stop_agent()`, `cleanup_agent()`, `get_agent_status()`
  - **Lifecycle States**: INITIALIZING → READY → ACTIVE → PAUSED → STOPPED → CLEANED_UP
  - **Operations**: Start (initialize resources), Pause (save state, suspend), Resume (restore state), Stop (graceful shutdown), Cleanup (release resources)
  - **Resource Management**: Track agent memory usage, file handles, database connections, release on cleanup
  - **Gate Integration**: Auto-pause on human approval gate, resume on gate approval, track pause reason
  - **Acceptance**: Agents start/stop cleanly, pause/resume preserves state, resources released on cleanup, no orphaned processes
  - **Test**: Lifecycle transition tests, resource cleanup tests, pause/resume state preservation tests (unit suite `backend/tests/unit/test_agent_lifecycle_manager.py`)
  - **Completed**: Nov 1, 2025
  - **Coverage**: 94% line (`pytest backend/tests --cov=backend.services.agent_lifecycle_manager --cov-report=term-missing`)
  - **Documentation**: `docs/implementation/phase1/task-1-1-5-agent-lifecycle-management.md`

### 1.2.0 Agent Execution Loop Architecture (Decision 83) - P0 BLOCKING
**Reference**: `docs/architecture/decision-83-agent-execution-loop-architecture.md`
**Priority**: P0 - BLOCKS ALL AGENT IMPLEMENTATIONS
**Dependencies**: Requires 1.1 (Orchestrator Core System) complete

⚠️ **CRITICAL**: This section MUST be completed before sections 1.1.1, 1.2+. Prevents "fake agent loops" risk and defines orchestrator methods needed by LLM integration.

- [x] **COMPLETED**: Implement BaseAgent class with iterative execution loop
  - **File**: `backend/agents/base_agent.py`
  - **Class**: `BaseAgent` with methods: `run_task()`, `_plan_next_step()`, `_execute_step_with_retry()`, `_validate_step()`, `_update_state()`, `_should_terminate()`
  - **Pattern**: Goal-based termination loop with while-not-done iteration
  - **Acceptance**: Real iterative loop (not single-shot), terminates on multiple criteria, full state tracking
  - **Test**: Unit tests cover loop execution, retries, validation hierarchy (see `backend/tests/unit/test_base_agent.py`)
  - **Completed**: Nov 1, 2025
  - **Coverage**: 100% (unit + integration)
  - **Documentation**: `docs/implementation/phase1/task-1-2-0-agent-execution-loop.md`

- [x] **COMPLETED**: Implement TaskState and Step data models
  - **File**: `backend/models/agent_state.py`
  - **Classes**: `TaskState`, `Step`, `Action`, `Result`, `ValidationResult`, `LLMCall`, `ToolExecution`
  - **State**: Full audit state with steps history, artifacts, failures, progress, resources, reasoning
  - **Acceptance**: Complete state tracking for debugging and recovery
  - **Test**: Exercised via BaseAgent unit tests ensuring serialization and metrics coverage

- [x] **COMPLETED**: Implement LoopDetector class
  - **File**: `backend/services/loop_detector.py`
  - **Class**: `LoopDetector` with methods: `is_looping()`, `record_failure()`, `record_success()`
  - **Logic**: Detect 3 consecutive identical errors (exact string match)
  - **Acceptance**: Detects loops accurately, fast (<1ms), integrates with agent execution
  - **Test**: Covered via BaseAgent retry/loop unit tests

- [x] **COMPLETED**: Add orchestrator.execute_tool() method
  - **File**: `backend/services/orchestrator.py`
  - **Method**: `async def execute_tool(tool_request: dict) -> dict`
  - **Flow**: Orchestrator → TAS → Tool → TAS Audit → Orchestrator
  - **Acceptance**: Routes to TAS, returns result with audit logging
  - **Test**: Verified via BaseAgent integration test with stub TAS client

- [x] **COMPLETED**: Add orchestrator.evaluate_confidence() method
  - **File**: `backend/services/orchestrator.py`
  - **Method**: `async def evaluate_confidence(confidence_request: dict) -> float`
  - **Logic**: LLM evaluates agent progress/approach, returns 0.0-1.0 score
  - **Triggers**: Every 5 steps, on agent uncertainty, on explicit request
  - **Threshold**: <0.5 triggers human gate
  - **Acceptance**: Returns confidence score with reasoning
  - **Test**: Exercised via integration test `test_low_confidence_triggers_gate`

- [x] **COMPLETED**: Verify orchestrator.create_gate() method exists
  - **File**: `backend/services/orchestrator.py`
  - **Method**: `async def create_gate(reason: str, context: dict, agent_id: str) -> str`
  - **Purpose**: Create human approval gate, pause agent
  - **Returns**: gate_id
  - **Note**: May already exist from Decision 67, verify and enhance if needed
  - **Enhancement**: Added async implementation with optional gate manager integration and logging

- [x] **COMPLETED**: Create agent execution database tables
  - **Migration**: Alembic migration file
  - **Tables**: `agent_execution_history`, `agent_execution_steps`
  - **Schema**: Track complete execution: steps, reasoning, actions, results, costs
  - **Acceptance**: Tables created, indexes applied, supports audit queries
  - **Test**: `pytest backend/tests/integration/test_migrations.py -v`
  - **Documentation**: `docs/implementation/phase1/task-1-2-0-agent-execution-loop.md`
  - **Completed**: Nov 1, 2025

- [x] **COMPLETED**: Implement intelligent retry with replanning
  - **File**: `backend/agents/base_agent.py` - `_execute_step_with_retry()` method
  - **Logic**: Max 3 retries, each with DIFFERENT approach (replan after failure)
  - **Backoff**: Exponential (2^attempt seconds)
  - **Acceptance**: Retries use different approaches, not identical attempts
  - **Test**: `test_retry_generates_unique_replanned_actions`

- [x] **COMPLETED**: Implement hybrid progress validation
  - **File**: `backend/agents/base_agent.py` - `_evaluate_progress()` method
  - **Priority**: Test metrics → Artifact metrics → LLM evaluation
  - **Acceptance**: Uses quantifiable metrics first, LLM as fallback
  - **Test**: `test_progress_hierarchy_prefers_tests_then_artifacts_then_llm`

- [x] **COMPLETED**: Write comprehensive unit tests for base agent
  - **File**: `backend/tests/unit/test_base_agent.py`
  - **Coverage**: Loop execution, termination criteria, retry logic, state management, loop detection
  - **Scenarios**: Success, failure, loop detection, confidence gating, timeout, cost limit
  - **Acceptance**: 100% code coverage, all scenarios tested
  - **Result**: Pytest suite passes (`pytest backend/tests/unit/test_base_agent.py backend/tests/integration/test_agent_execution_loop.py -v`)

- [x] **COMPLETED**: Write integration tests for execution loop
  - **File**: `backend/tests/integration/test_agent_execution_loop.py`
  - **Coverage**: Full task execution, TAS integration, orchestrator confidence checks, loop escalation
  - **Acceptance**: Complete end-to-end execution with real components
  - **Result**: Pytest suite passes (`pytest backend/tests/unit/test_base_agent.py backend/tests/integration/test_agent_execution_loop.py -v`)

- [x] **COMPLETED**: Create execution loop implementation guide
  - **File**: `docs/implementation/base-agent-implementation-guide.md`
  - **Content**: How to implement agents, examples, patterns, anti-patterns
  - **Acceptance**: Complete guide for developers implementing agents
  - **Status**: Documented in `docs/implementation/phase1/task-1-2-0-agent-execution-loop.md`

### 1.1.1 Orchestrator LLM Integration (Decision 67)
**Dependencies**: Requires 1.2.0 (Agent Execution Loop) complete - uses orchestrator.evaluate_confidence()
**Reference**: `docs/architecture/decision-67-orchestrator-llm-integration.md`

- [x] **COMPLETED**: Implement OrchestratorLLMClient with full chain-of-thought reasoning
  - **File**: `backend/services/orchestrator_llm_client.py`
  - **Class**: `OrchestratorLLMClient` with methods: `reason_about_task()`, `select_agent()`, `evaluate_progress()`
  - **Acceptance**: Client returns structured reasoning with confidence scores, uses gpt-4o model
  - **Test**: Unit tests verify reasoning structure, integration tests validate agent selection logic

- [x] **COMPLETED**: Create orchestrator base system prompt and templates
  - **File**: `backend/prompts/orchestrator_prompts.py`
  - **Content**: Base system prompt defining orchestrator role, context injection templates, decision-making guidelines
  - **Acceptance**: Prompt includes role definition, available agents list, escalation rules, output format requirements
  - **Test**: Prompt validation tests ensure all required sections present

- [x] **COMPLETED**: Implement autonomy level configuration (low/medium/high slider)
  - **Database**: Add `autonomy_level` column to `user_settings` table (VARCHAR, values: 'low'/'medium'/'high')
  - **Backend**: `backend/models/user_settings.py` - add field and validation
  - **Acceptance**: Setting persists to database, defaults to 'medium', validates enum values
  - **Test**: CRUD tests for autonomy setting

- [x] **COMPLETED**: Build autonomy threshold logic for escalation decisions
  - **File**: `backend/services/orchestrator.py` - add `should_escalate()` method
  - **Logic**: Low=always escalate, Medium=escalate on uncertainty>0.3, High=escalate on uncertainty>0.7
  - **Acceptance**: Method returns boolean based on autonomy level and confidence score
  - **Test**: Unit tests for all 3 autonomy levels with various confidence scores

- [x] **COMPLETED**: Create orchestrator-mediated RAG query system
  - **File**: `backend/services/orchestrator.py` - add `query_knowledge_base()` method
  - **Integration**: Calls `RAGQueryService.search()` and formats results for agent context
  - **Acceptance**: Returns top 5 relevant patterns, includes similarity scores, formats for prompt injection
  - **Test**: Integration test with mock Qdrant, verify result formatting

- [x] **COMPLETED**: Implement PM vetting workflow (orchestrator reviews PM decisions with specialists)
  - **File**: `backend/services/orchestrator.py` - add `vet_pm_decision()` method
  - **Workflow**: PM proposes → Orchestrator reviews → Consults specialist if needed → Approves/rejects
  - **Acceptance**: Creates collaboration request, waits for specialist response, logs decision to database
  - **Test**: End-to-end test simulating PM decision requiring specialist input

- [x] **COMPLETED**: Build orchestrator decision logging to database
  - **Table**: `orchestrator_decisions` (already defined in Decision 79)
  - **File**: `backend/services/orchestrator.py` - add `log_decision()` method
  - **Fields**: decision_type, reasoning, confidence, selected_agent, outcome
  - **Acceptance**: Every major decision logged with full context, queryable for analytics
  - **Test**: Verify logging on agent selection, escalation, collaboration routing

- [x] **COMPLETED**: Create frontend autonomy slider in settings
  - **File**: `frontend/src/pages/Settings.tsx` - add autonomy section
  - **Component**: Slider with 3 positions (Low/Medium/High), descriptions for each level
  - **API**: PUT `/api/v1/settings/autonomy` endpoint
  - **Acceptance**: Slider updates database, shows current value on load, displays help text
  - **Test**: E2E test changing autonomy level and verifying persistence

- [x] **COMPLETED**: Implement orchestrator context layer templates
  - **File**: `backend/prompts/orchestrator_prompts.py` - add `build_context()` function
  - **Templates**: Project context, agent context, RAG results, collaboration history
  - **Acceptance**: Templates inject all relevant context into LLM prompts, max 8000 tokens
  - **Test**: Unit tests verify context assembly, token counting

- [x] **COMPLETED**: Build orchestrator agent selection logic for collaboration routing
  - **File**: `backend/services/orchestrator.py` - add `route_collaboration()` method
  - **Logic**: Analyzes help request, selects best specialist based on expertise, checks availability
  - **Acceptance**: Returns agent_id and reasoning, logs routing decision, handles no-match case
  - **Test**: Unit tests for various collaboration scenarios (security, performance, architecture)

### 1.2.1 OpenAI Integration Foundation (BLOCKING - Must Complete First)
**Priority**: P0 - BLOCKS ALL AGENT IMPLEMENTATIONS
**Dependencies**: Requires 1.2.0 (BaseAgent) complete
**Reference**: Foundation for all LLM operations

- [ ] **TODO**: Create OpenAI adapter service with token logging hooks
  - **File**: `backend/services/openai_adapter.py`
  - **Class**: `OpenAIAdapter` with methods:
    - `__init__(api_key: str, token_logger: TokenLogger | None)` - Initialize AsyncOpenAI client
    - `async chat_completion(model: str, messages: List[dict], temperature: float, **kwargs) -> ChatCompletion` - Call chat API
    - `async embed_text(text: str, model: str = "text-embedding-3-small") -> List[float]` - Generate embeddings
    - `_log_tokens(response: ChatCompletion, metadata: dict)` - Hook for token logging
  - **Wrapper**: Wraps AsyncOpenAI from `openai` package (already imported in OrchestratorLLMClient)
  - **Error Handling**: Retry logic (3 attempts, exponential backoff), timeout handling, API error parsing
  - **Token Logging**: Extracts `response.usage.{prompt_tokens, completion_tokens}` and calls TokenLogger
  - **Configuration**: Loads API key from `OPENAI_API_KEY` env var or database `api_keys` table
  - **Acceptance**: All OpenAI calls go through adapter, token logging works, errors handled gracefully
  - **Test**: Unit tests with mock AsyncOpenAI, integration tests with real API (skipif no key)
  - **Example Usage**:
    ```python
    adapter = OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY"))
    response = await adapter.chat_completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7
    )
    ```

- [ ] **TODO**: Create API keys configuration table
  - **Migration**: `alembic/versions/004_create_api_keys_table.py`
  - **Schema**: `api_keys` table
    - id (UUID PRIMARY KEY)
    - service (VARCHAR UNIQUE) - e.g., "openai", "anthropic" (for future)
    - api_key_encrypted (TEXT NOT NULL) - Fernet encrypted
    - is_active (BOOLEAN DEFAULT true)
    - created_at (TIMESTAMP DEFAULT NOW())
    - updated_at (TIMESTAMP DEFAULT NOW())
  - **Indexes**: idx_api_keys_service (unique), idx_api_keys_active
  - **Encryption**: Use Fernet from cryptography package, key stored in `ENCRYPTION_KEY` env var
  - **Seed Data**: None (user must configure via UI)
  - **Acceptance**: Table stores encrypted API keys, one key per service, supports rotation
  - **Test**: Insert key, retrieve and decrypt, verify encryption, test uniqueness constraint
  - **Example**:
    ```sql
    INSERT INTO api_keys (service, api_key_encrypted, is_active) 
    VALUES ('openai', 'gAAAAABf...encrypted...', true);
    ```

- [ ] **TODO**: Implement API key management service
  - **File**: `backend/services/api_key_service.py`
  - **Class**: `APIKeyService` with methods:
    - `get_key(service: str) -> str` - Get decrypted API key for service
    - `set_key(service: str, api_key: str) -> bool` - Encrypt and store API key
    - `test_key(service: str, api_key: str) -> bool` - Test key validity before storing
    - `rotate_key(service: str, new_key: str) -> bool` - Replace existing key
  - **Encryption**: Uses Fernet for symmetric encryption, generates cipher from ENCRYPTION_KEY env var
  - **Caching**: Cache decrypted keys in memory for 5 minutes (security trade-off for performance)
  - **Validation**: Test OpenAI key by calling `/v1/models` endpoint before storing
  - **Acceptance**: Keys stored encrypted, decryption works, caching improves performance, validation prevents invalid keys
  - **Test**: Store/retrieve keys, verify encryption, test caching, test validation
  - **Example**:
    ```python
    key_service = APIKeyService()
    await key_service.set_key("openai", "sk-proj-...")
    api_key = await key_service.get_key("openai")  # Returns decrypted key
    ```

- [ ] **TODO**: Create API key configuration UI in settings
  - **File**: `frontend/src/pages/Settings.tsx` - Add API Keys section
  - **Form Fields**:
    - Service selector (OpenAI for now, disabled other options)
    - API key input (password field with show/hide toggle)
    - Test connection button
    - Save button
  - **Workflow**: Enter key → Test (calls `/api/v1/keys/test`) → Save if valid → Show success
  - **Security**: Never display full key after save, only show "sk-proj-...****abc" (last 3 chars)
  - **Status Indicator**: Show "Connected" (green) or "Not Configured" (yellow) or "Invalid" (red)
  - **Help Text**: Link to OpenAI API keys page, instructions for creating key
  - **Acceptance**: Can configure OpenAI key, test before save, key encrypted in transit (HTTPS)
  - **Test**: E2E test configuring key, verify test endpoint, check encryption
  - **Backend API**: POST `/api/v1/keys` (set key), GET `/api/v1/keys/{service}/status` (check), POST `/api/v1/keys/{service}/test` (validate)

- [ ] **TODO**: Build per-agent model configuration system
  - **Migration**: `alembic/versions/005_create_agent_model_configs.py`
  - **Schema**: `agent_model_configs` table
    - id (UUID PRIMARY KEY)
    - agent_type (VARCHAR NOT NULL) - "orchestrator", "backend_dev", etc.
    - model (VARCHAR NOT NULL) - "gpt-4o-mini", "gpt-4o", "gpt-4-turbo"
    - temperature (FLOAT DEFAULT 0.7) - 0.0 to 1.0
    - max_tokens (INTEGER DEFAULT 4096) - Response length limit
    - is_active (BOOLEAN DEFAULT true)
    - updated_at (TIMESTAMP DEFAULT NOW())
  - **Indexes**: idx_agent_model_configs_agent_type (unique)
  - **Seed Data**: Default configs for all 10 agent types with gpt-4o-mini, temperature=0.7
  - **Acceptance**: Each agent type has separate model config, defaults loaded on first run
  - **Test**: Insert configs, query by agent_type, verify uniqueness
  - **Example Seed Data**:
    ```sql
    INSERT INTO agent_model_configs (agent_type, model, temperature, max_tokens) VALUES
    ('orchestrator', 'gpt-4o-mini', 0.3, 4096),
    ('backend_dev', 'gpt-4o-mini', 0.7, 8192),
    ('frontend_dev', 'gpt-4o-mini', 0.7, 8192);
    ```

- [ ] **TODO**: Implement AgentModelConfigService
  - **File**: `backend/services/agent_model_config_service.py`
  - **Class**: `AgentModelConfigService` with methods:
    - `get_config(agent_type: str) -> AgentModelConfig` - Get config for agent
    - `set_config(agent_type: str, model: str, temperature: float, max_tokens: int)` - Update config
    - `get_all_configs() -> List[AgentModelConfig]` - Get all agent configs
  - **Caching**: Cache configs in memory for 5 minutes
  - **Defaults**: If config not found, return default (gpt-4o-mini, temp=0.7, max_tokens=4096)
  - **Validation**: Validate model is in allowed list, temperature 0.0-1.0, max_tokens positive
  - **Acceptance**: Configs loaded per agent, caching works, defaults applied
  - **Test**: Get/set configs, test caching, verify defaults
  - **Example**:
    ```python
    config_service = AgentModelConfigService()
    config = await config_service.get_config("backend_dev")
    # Returns: AgentModelConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=8192)
    ```

- [ ] **TODO**: Create agent model selection UI in settings
  - **File**: `frontend/src/pages/Settings.tsx` - Add Agent Configuration section
  - **Layout**: Grid of agent cards (10 agents), each card shows:
    - Agent name and icon
    - Model selector dropdown (gpt-4o-mini, gpt-4o, gpt-4-turbo)
    - Temperature slider (0.0 to 1.0, step 0.1)
    - Max tokens input (1000-16000)
    - Recommended settings hint (e.g., "Recommended: gpt-4o-mini, temp=0.7")
  - **Presets**: "Cost Optimized" (all gpt-4o-mini), "Quality Optimized" (all gpt-4o), "Balanced" (mixed)
  - **Save**: Batch save all configs with single API call
  - **Acceptance**: Can configure all agents, presets work, settings save and persist
  - **Test**: E2E test changing configs, applying presets, verify persistence
  - **Backend API**: GET `/api/v1/agent-configs`, PUT `/api/v1/agent-configs` (bulk update)

- [ ] **TODO**: Update BaseAgent to load model config
  - **File**: `backend/agents/base_agent.py` - modify `__init__()` method
  - **Integration**:
    ```python
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        config_service = AgentModelConfigService()
        self.model_config = await config_service.get_config(agent_type)
        self.openai_adapter = OpenAIAdapter()
    ```
  - **Usage**: When agent calls LLM, use `self.model_config.model` and `self.model_config.temperature`
  - **Acceptance**: Agents automatically load correct model config, no hardcoded models
  - **Test**: Initialize agent, verify config loaded, test model/temperature values

### 1.1.2 Database Schema Initialization (Complete Migration Order)
**Priority**: Must complete before dependent features
**Purpose**: Consolidate all database migrations in correct dependency order

**Migration Execution Order** (sequential, no parallel):
```
001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 011-021
```

- [x] **COMPLETED**: Migration 001 - Agent execution tracking tables
  - **File**: `backend/migrations/versions/20251101_01_create_agent_execution_tables.py`
  - **Tables**: `agent_execution_history`, `agent_execution_steps`
  - **Purpose**: Track agent execution loops for debugging and auditing
  - **Status**: Already created and tested

- [x] **COMPLETED**: Migration 002 - Project state tables
  - **File**: `backend/migrations/versions/20251101_02_create_project_state_tables.py`
  - **Tables**: `project_state`, `project_phases`, `project_tasks`
  - **Purpose**: Persist project state for recovery and progress tracking
  - **Status**: Already created and tested

- [x] **COMPLETED**: Migration 003 - User settings and autonomy
  - **File**: `backend/migrations/versions/20251101_03_add_autonomy_and_decision_logging.py`
  - **Tables**: `user_settings`, `orchestrator_decisions`
  - **Columns**: autonomy_level (low/medium/high), decision logs
  - **Purpose**: User preferences and orchestrator decision audit trail
  - **Status**: Already created and tested

- [ ] **TODO**: Migration 004 - API keys configuration
  - **File**: `backend/migrations/versions/20251102_04_create_api_keys_table.py`
  - **Table**: `api_keys`
  - **Schema**:
    ```sql
    CREATE TABLE api_keys (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        service VARCHAR(50) UNIQUE NOT NULL,
        api_key_encrypted TEXT NOT NULL,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX idx_api_keys_service ON api_keys(service);
    CREATE INDEX idx_api_keys_active ON api_keys(is_active);
    ```
  - **Purpose**: Store encrypted OpenAI API keys
  - **Dependencies**: None (independent)
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_004 -v`

- [ ] **TODO**: Migration 005 - Agent model configurations
  - **File**: `backend/migrations/versions/20251102_05_create_agent_model_configs.py`
  - **Table**: `agent_model_configs`
  - **Schema**:
    ```sql
    CREATE TABLE agent_model_configs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_type VARCHAR(50) UNIQUE NOT NULL,
        model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini',
        temperature FLOAT NOT NULL DEFAULT 0.7,
        max_tokens INTEGER NOT NULL DEFAULT 4096,
        is_active BOOLEAN DEFAULT true,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX idx_agent_model_configs_agent_type ON agent_model_configs(agent_type);
    ```
  - **Seed Data**:
    ```sql
    INSERT INTO agent_model_configs (agent_type, model, temperature, max_tokens) VALUES
    ('orchestrator', 'gpt-4o-mini', 0.3, 4096),
    ('backend_dev', 'gpt-4o-mini', 0.7, 8192),
    ('frontend_dev', 'gpt-4o-mini', 0.7, 8192),
    ('qa_engineer', 'gpt-4o-mini', 0.5, 4096),
    ('security_expert', 'gpt-4o-mini', 0.3, 4096),
    ('devops_engineer', 'gpt-4o-mini', 0.5, 4096),
    ('documentation_expert', 'gpt-4o-mini', 0.7, 8192),
    ('uiux_designer', 'gpt-4o-mini', 0.8, 8192),
    ('github_specialist', 'gpt-4o-mini', 0.5, 4096),
    ('workshopper', 'gpt-4o-mini', 0.7, 8192),
    ('project_manager', 'gpt-4o-mini', 0.5, 4096);
    ```
  - **Purpose**: Per-agent LLM model and temperature configuration
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_005 -v`

- [ ] **TODO**: Migration 006 - Human approval gates
  - **File**: `backend/migrations/versions/20251102_06_create_gates_table.py`
  - **Table**: `gates`
  - **Schema**:
    ```sql
    CREATE TABLE gates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL,
        agent_id VARCHAR(100) NOT NULL,
        gate_type VARCHAR(50) NOT NULL,
        reason TEXT NOT NULL,
        context JSONB NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT NOW(),
        resolved_at TIMESTAMP,
        resolved_by VARCHAR(100),
        feedback TEXT
    );
    CREATE INDEX idx_gates_project ON gates(project_id);
    CREATE INDEX idx_gates_status ON gates(status);
    CREATE INDEX idx_gates_agent ON gates(agent_id);
    ```
  - **Purpose**: Human-in-the-loop approval system
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_006 -v`

- [ ] **TODO**: Migration 007 - Agent collaboration tracking
  - **File**: `backend/migrations/versions/20251102_07_create_collaboration_tables.py`
  - **Tables**: `collaboration_requests`, `collaboration_outcomes`
  - **Schema**:
    ```sql
    CREATE TABLE collaboration_requests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        collaboration_id UUID NOT NULL,
        request_type VARCHAR(50) NOT NULL,
        requesting_agent VARCHAR(50) NOT NULL,
        specialist_agent VARCHAR(50) NOT NULL,
        question TEXT NOT NULL,
        context JSONB NOT NULL,
        urgency VARCHAR(20) DEFAULT 'medium',
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX idx_collab_requests_collab_id ON collaboration_requests(collaboration_id);
    
    CREATE TABLE collaboration_outcomes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        collaboration_id UUID NOT NULL,
        specialist_agent VARCHAR(50) NOT NULL,
        response TEXT NOT NULL,
        confidence FLOAT NOT NULL,
        tokens_used INTEGER,
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX idx_collab_outcomes_collab_id ON collaboration_outcomes(collaboration_id);
    ```
  - **Purpose**: Track agent-to-agent collaboration requests
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_007 -v`

- [ ] **TODO**: Migration 008 - Prompt versioning system
  - **File**: `backend/migrations/versions/20251102_08_create_prompts_table.py`
  - **Table**: `prompts`
  - **Schema**:
    ```sql
    CREATE TABLE prompts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_type VARCHAR(50) NOT NULL,
        version VARCHAR(20) NOT NULL,
        prompt_text TEXT NOT NULL,
        is_active BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT NOW(),
        created_by VARCHAR(100),
        notes TEXT,
        UNIQUE(agent_type, version)
    );
    CREATE INDEX idx_prompts_agent_type ON prompts(agent_type);
    CREATE INDEX idx_prompts_active ON prompts(agent_type, is_active);
    ```
  - **Seed Data**: Load default v1.0.0 prompts for all 10 agent types
  - **Purpose**: Semantic versioning for agent prompts
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_008 -v`
  - **Note**: Seed prompts will be added in section 1.2.3

- [ ] **TODO**: Migration 009 - LLM token usage tracking
  - **File**: `backend/migrations/versions/20251102_09_create_llm_token_usage_table.py`
  - **Table**: `llm_token_usage`
  - **Schema**:
    ```sql
    CREATE TABLE llm_token_usage (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
        project_id UUID,
        agent_id VARCHAR(100),
        model VARCHAR(50) NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX idx_token_usage_timestamp ON llm_token_usage(timestamp);
    CREATE INDEX idx_token_usage_project ON llm_token_usage(project_id);
    CREATE INDEX idx_token_usage_agent ON llm_token_usage(agent_id);
    CREATE INDEX idx_token_usage_project_agent ON llm_token_usage(project_id, agent_id);
    ```
  - **Purpose**: Track token usage for cost calculation
  - **Dependencies**: None
  - **Retention**: Delete records older than 1 year (cleanup job)
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_009 -v`

- [ ] **TODO**: Migration 010 - LLM pricing table
  - **File**: `backend/migrations/versions/20251102_10_create_llm_pricing_table.py`
  - **Table**: `llm_pricing`
  - **Schema**:
    ```sql
    CREATE TABLE llm_pricing (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        model VARCHAR(50) UNIQUE NOT NULL,
        input_cost_per_million DECIMAL(10, 2) NOT NULL,
        output_cost_per_million DECIMAL(10, 2) NOT NULL,
        effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
        updated_at TIMESTAMP DEFAULT NOW(),
        updated_by VARCHAR(100),
        notes TEXT
    );
    ```
  - **Seed Data**:
    ```sql
    INSERT INTO llm_pricing (model, input_cost_per_million, output_cost_per_million, notes) VALUES
    ('gpt-4o-mini', 0.15, 0.60, 'OpenAI pricing as of Nov 2024'),
    ('gpt-4o', 2.50, 10.00, 'OpenAI pricing as of Nov 2024'),
    ('gpt-4-turbo', 10.00, 30.00, 'OpenAI pricing as of Nov 2024'),
    ('gpt-3.5-turbo', 0.50, 1.50, 'OpenAI pricing as of Nov 2024');
    ```
  - **Purpose**: Manual pricing management for cost calculation
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_010 -v`

- [ ] **TODO**: Migration 011 - RAG knowledge staging
  - **File**: `backend/migrations/versions/20251102_11_create_knowledge_staging_table.py`
  - **Table**: `knowledge_staging`
  - **Schema**:
    ```sql
    CREATE TABLE knowledge_staging (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        knowledge_type VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB NOT NULL,
        embedded BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX idx_knowledge_staging_type ON knowledge_staging(knowledge_type);
    CREATE INDEX idx_knowledge_staging_embedded ON knowledge_staging(embedded);
    ```
  - **Purpose**: Stage knowledge before embedding to Qdrant
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_011 -v`

- [ ] **TODO**: Migration 012-018 - Additional feature tables
  - **Note**: Reserved for Docker containers, GitHub credentials, email settings, etc.
  - **Will be defined as features are implemented**

- [ ] **TODO**: Migration 019 - User authentication (users, sessions, invites)
  - **File**: `backend/migrations/versions/20251102_19_create_auth_tables.py`
  - **Tables**: `users`, `user_sessions`, `user_invites`
  - **Schema**: See Section 4.7 (User Authentication with 2FA)
  - **Purpose**: User management, JWT sessions, invite-only signup
  - **Dependencies**: None (bootstrap with initial admin via script)
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_019 -v`

- [ ] **TODO**: Migration 020 - Two-factor authentication
  - **File**: `backend/migrations/versions/20251102_20_create_2fa_table.py`
  - **Table**: `two_factor_auth`
  - **Schema**: See Section 4.7 (User Authentication with 2FA)
  - **Purpose**: TOTP secrets and backup codes
  - **Dependencies**: Migration 019 (FK to users)
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_020 -v`

- [ ] **TODO**: Migration 021 - Email service configuration
  - **File**: `backend/migrations/versions/20251102_21_create_email_settings_table.py`
  - **Table**: `email_settings`
  - **Schema**: See Section 4.7 SMTP Email Service Integration
  - **Purpose**: SMTP configuration for automated emails
  - **Dependencies**: None
  - **Test**: `pytest backend/tests/integration/test_migrations.py::test_migration_021 -v`

- [ ] **TODO**: Create migration dependency validation script
  - **File**: `backend/scripts/validate_migrations.py`
  - **Purpose**: Verify migrations can be applied in order, all FK references valid
  - **Checks**: Sequential ordering, table dependencies, index names unique
  - **Usage**: `python -m backend.scripts.validate_migrations`
  - **Acceptance**: Script passes on all migrations, catches dependency issues
  - **Test**: Run script, verify output, test with intentionally broken migration

### 1.2 Agent System Architecture (REVISED FOR LLM INTEGRATION)
**Dependencies**: Requires 1.2.1 (OpenAI Integration) complete
**NOTE**: All agents use BaseAgent from 1.2.0, load prompts from 1.2.4 versioning system

- [ ] **TODO**: Implement Backend Developer agent
  - **File**: `backend/agents/backend_developer_agent.py`
  - **Class**: `BackendDeveloperAgent(BaseAgent)`
  - **Agent Type**: "backend_dev"
  - **Methods to Override**:
    - `_plan_next_step(state: TaskState) -> Step` - Plan next code/test/debug step using LLM
    - `_execute_step(step: Step) -> Result` - Execute via TAS (write_file, run_tests, etc.)
    - `_validate_step(step: Step, result: Result) -> ValidationResult` - Check tests pass, code quality
  - **Tools Required**: write_file, read_file, run_command, search_files, run_tests
  - **Prompt Loading**: Loads from prompts table WHERE agent_type='backend_dev' AND is_active=true
  - **Example Workflow**: Given "Implement user login API" → Plan endpoint → Write code → Write tests → Run tests → Iterate
  - **Acceptance**: Executes backend tasks, uses correct tools, follows TDD approach
  - **Test**: 
    - **Unit**: `backend/tests/unit/test_backend_developer_agent.py` - Test planning/validation
    - **Integration**: `backend/tests/integration/test_backend_developer_full_task.py` - Complete API implementation

- [ ] **TODO**: Implement Frontend Developer agent
  - **File**: `backend/agents/frontend_developer_agent.py`
  - **Class**: `FrontendDeveloperAgent(BaseAgent)`
  - **Agent Type**: "frontend_dev"
  - **Methods to Override**: Same pattern as Backend Dev
  - **Tools Required**: write_file, read_file, run_command (npm), search_files, run_tests (vitest)
  - **Prompt Loading**: WHERE agent_type='frontend_dev'
  - **Example Workflow**: Given "Create login form component" → Design component → Write JSX/TSX → Write tests → Run tests → Iterate
  - **Acceptance**: Builds React components, follows UI/UX best practices, writes component tests
  - **Test**: 
    - **Unit**: `backend/tests/unit/test_frontend_developer_agent.py`
    - **Integration**: `backend/tests/integration/test_frontend_developer_full_task.py`

- [ ] **TODO**: Implement QA Engineer agent
  - **File**: `backend/agents/qa_engineer_agent.py`
  - **Class**: `QAEngineerAgent(BaseAgent)`
  - **Agent Type**: "qa_engineer"
  - **Tools Required**: read_file, run_command (pytest, vitest), write_file (test files), analyze_coverage
  - **Example Workflow**: Given "Test user authentication" → Review code → Write test cases → Execute tests → Report results
  - **Acceptance**: Writes comprehensive tests, achieves >90% coverage, finds edge cases
  - **Test**:
    - **Unit**: `backend/tests/unit/test_qa_engineer_agent.py`
    - **Integration**: `backend/tests/integration/test_qa_engineer_full_task.py`

- [ ] **TODO**: Implement Security Expert agent
  - **File**: `backend/agents/security_expert_agent.py`
  - **Class**: `SecurityExpertAgent(BaseAgent)`
  - **Agent Type**: "security_expert"
  - **Tools Required**: read_file, search_files, run_security_scan, analyze_dependencies
  - **Example Workflow**: Given "Review authentication code" → Scan for vulnerabilities → Check OWASP Top 10 → Provide recommendations
  - **Acceptance**: Identifies security issues, provides remediation steps, follows OWASP guidelines
  - **Test**:
    - **Unit**: `backend/tests/unit/test_security_expert_agent.py`
    - **Integration**: `backend/tests/integration/test_security_expert_full_task.py`

- [ ] **TODO**: Implement DevOps Engineer agent
  - **File**: `backend/agents/devops_engineer_agent.py`
  - **Class**: `DevOpsEngineerAgent(BaseAgent)`
  - **Agent Type**: "devops_engineer"
  - **Tools Required**: write_file (Dockerfile, docker-compose, CI/CD), run_command (docker), manage_containers
  - **Example Workflow**: Given "Containerize application" → Write Dockerfile → Create docker-compose → Test build → Document
  - **Acceptance**: Creates working Docker configs, follows 12-factor app principles
  - **Test**:
    - **Unit**: `backend/tests/unit/test_devops_engineer_agent.py`
    - **Integration**: `backend/tests/integration/test_devops_engineer_full_task.py`

- [ ] **TODO**: Implement Documentation Expert agent
  - **File**: `backend/agents/documentation_expert_agent.py`
  - **Class**: `DocumentationExpertAgent(BaseAgent)`
  - **Agent Type**: "documentation_expert"
  - **Tools Required**: read_file, write_file, search_files, analyze_code_structure
  - **Example Workflow**: Given "Document API endpoints" → Analyze code → Generate API docs → Write README → Create examples
  - **Acceptance**: Produces clear, comprehensive documentation with examples
  - **Test**:
    - **Unit**: `backend/tests/unit/test_documentation_expert_agent.py`
    - **Integration**: `backend/tests/integration/test_documentation_expert_full_task.py`

- [ ] **TODO**: Implement UI/UX Designer agent
  - **File**: `backend/agents/uiux_designer_agent.py`
  - **Class**: `UIUXDesignerAgent(BaseAgent)`
  - **Agent Type**: "uiux_designer"
  - **Tools Required**: read_file, write_file (design docs), generate_mockups, analyze_user_flow
  - **Example Workflow**: Given "Design dashboard layout" → Analyze requirements → Create wireframes → Define component structure → Document design system
  - **Acceptance**: Produces usable design specs, follows accessibility guidelines
  - **Test**:
    - **Unit**: `backend/tests/unit/test_uiux_designer_agent.py`
    - **Integration**: `backend/tests/integration/test_uiux_designer_full_task.py`

- [ ] **TODO**: Implement GitHub Specialist agent
  - **File**: `backend/agents/github_specialist_agent.py`
  - **Class**: `GitHubSpecialistAgent(BaseAgent)`
  - **Agent Type**: "github_specialist"
  - **Reference**: Decision 77 - GitHub Specialist Agent
  - **Tools Required**: git_operations, create_pr, manage_issues, review_code
  - **Example Workflow**: Given "Create PR for feature" → Review changes → Generate commit messages → Create PR → Link issues
  - **Acceptance**: Creates proper PRs, writes semantic commits, follows Git workflow
  - **Test**:
    - **Unit**: `backend/tests/unit/test_github_specialist_agent.py`
    - **Integration**: `backend/tests/integration/test_github_specialist_full_task.py`

- [ ] **TODO**: Implement Workshopper agent
  - **File**: `backend/agents/workshopper_agent.py`
  - **Class**: `WorkshopperAgent(BaseAgent)`
  - **Agent Type**: "workshopper"
  - **Tools Required**: read_file, write_file, analyze_requirements, create_tasks
  - **Example Workflow**: Given "Plan new feature" → Interview user → Analyze requirements → Create design decisions → Generate task breakdown
  - **Acceptance**: Produces comprehensive plans with detailed tasks, follows decision-making process
  - **Test**:
    - **Unit**: `backend/tests/unit/test_workshopper_agent.py`
    - **Integration**: `backend/tests/integration/test_workshopper_full_task.py`

- [ ] **TODO**: Implement Project Manager agent
  - **File**: `backend/agents/project_manager_agent.py`
  - **Class**: `ProjectManagerAgent(BaseAgent)`
  - **Agent Type**: "project_manager"
  - **Tools Required**: read_project_state, update_tasks, manage_timeline, coordinate_agents
  - **Example Workflow**: Given "Coordinate feature development" → Assess progress → Assign tasks → Monitor blockers → Report status
  - **Acceptance**: Manages project lifecycle, coordinates agents effectively, tracks progress
  - **Test**:
    - **Unit**: `backend/tests/unit/test_project_manager_agent.py`
    - **Integration**: `backend/tests/integration/test_project_manager_full_task.py`

### 1.2.3 Prompt Engineering and System Design (FINAL)

- [ ] **TODO**: Design agent-specific base prompts with strict role definitions
  - **File**: `backend/prompts/agents/` - separate files per agent (orchestrator.txt, backend_dev.txt, etc.)
  - **Structure**: Role definition, capabilities, constraints, output format, examples
  - **Agents**: All 10 agent types (orchestrator, backend_dev, frontend_dev, qa, devops, security, pm, data_analyst, tech_writer, github_specialist)
  - **Acceptance**: Each agent has complete base prompt, role clearly defined, constraints explicit
  - **Test**: Load all prompts, verify structure, test with LLM
  - **Example Prompt (backend_dev.txt)**:
    ```
    # ROLE
    You are a Backend Developer AI agent specializing in Python, FastAPI, and PostgreSQL development. 
    Your role is to implement backend services, APIs, and database operations with a test-driven approach.

    # CAPABILITIES
    - Write clean, maintainable Python code following PEP 8 standards
    - Implement RESTful APIs using FastAPI with proper validation
    - Design and implement PostgreSQL database schemas with Alembic migrations
    - Write comprehensive unit and integration tests using pytest
    - Debug code issues and implement fixes
    - Review and refactor existing code for quality improvements

    # CONSTRAINTS
    - ALWAYS write tests BEFORE implementing features (TDD)
    - NEVER hardcode credentials or sensitive data
    - ALWAYS use type hints in Python code
    - MUST achieve minimum 90% code coverage
    - MUST follow repository code style and patterns
    - CANNOT access tools outside your permission set
    - MUST escalate to orchestrator if uncertain or blocked

    # TOOLS AVAILABLE
    - write_file: Create or modify code files
    - read_file: Read existing code
    - run_command: Execute pytest, linters, formatters
    - search_files: Find code patterns
    - run_tests: Execute test suite

    # OUTPUT FORMAT
    All responses must be valid JSON with this structure:
    {
      "reasoning": "Step-by-step thought process",
      "action": "tool_name",
      "parameters": {...},
      "confidence": 0.0-1.0
    }

    # EXAMPLE WORKFLOW
    Task: "Implement user login endpoint"
    1. Analyze requirements → Identify needs (endpoint, validation, auth)
    2. Write test first → test_user_login_success(), test_invalid_credentials()
    3. Implement endpoint → POST /api/v1/auth/login with validation
    4. Run tests → Verify all pass
    5. Refactor if needed → Clean up code, add error handling

    # QUALITY STANDARDS
    - Code must pass: mypy (type checking), black (formatting), ruff (linting)
    - Tests must cover: happy path, error cases, edge cases, input validation
    - Documentation: Docstrings for all public functions/classes
    - Error handling: Proper exception handling with meaningful messages
    ```
  - **Example Prompt (orchestrator.txt)**:
    ```
    # ROLE
    You are the Orchestrator AI - the central coordinator for all agent activities.
    You assign tasks, route messages, evaluate progress, and escalate to humans when needed.

    # CAPABILITIES
    - Analyze tasks and select appropriate agents
    - Coordinate collaboration between agents
    - Evaluate agent confidence and progress
    - Decide when to escalate to human review
    - Query knowledge base for relevant patterns
    - Make strategic decisions about project direction

    # DECISION-MAKING
    - Consider: Task complexity, agent expertise, project phase, autonomy level
    - Escalate when: Confidence < threshold, security concerns, conflicting approaches
    - Collaborate when: Agent requests help, multiple perspectives needed

    # OUTPUT FORMAT
    {
      "reasoning": "Analysis of situation and options",
      "decision": {"action": "...", "agent": "...", "parameters": {...}},
      "confidence": 0.0-1.0,
      "escalation_needed": bool
    }
    ```

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
  - **File**: `backend/services/phase_manager.py`
  - **Class**: `PhaseManager` with methods:
    - `start_phase(project_id, phase_name) -> Phase` - Initialize phase with agents
    - `get_current_phase(project_id) -> Phase` - Get active phase
    - `complete_phase(project_id, phase_name) -> bool` - Validate and complete phase
    - `transition_phase(project_id, from_phase, to_phase) -> bool` - Handle phase transitions
  - **Phases**: Workshopping, Implementation, Testing, Deployment, Monitoring, Maintenance
  - **Agent Assignment**: Each phase has designated agents (PM coordinates all)
  - **Acceptance**: Phases execute in order, cannot skip, all deliverables required
  - **Test**: 
    - **Unit**: `backend/tests/unit/test_phase_manager.py`
    - **Integration**: `backend/tests/integration/test_full_phase_lifecycle.py`

- [ ] **TODO**: Implement phase deliverable tracking with AI validation
  - **File**: `backend/services/deliverable_tracker.py`
  - **Class**: `DeliverableTracker` with methods:
    - `define_deliverables(phase_name) -> List[Deliverable]` - Get required deliverables per phase
    - `validate_deliverable(deliverable_id, artifact) -> ValidationResult` - Check quality
    - `get_phase_completeness(phase_name) -> float` - Calculate % complete (0.0-1.0)
  - **Deliverables by Phase**:
    - Workshopping: Design docs, task breakdown, architecture decisions
    - Implementation: Code files, unit tests, integration tests
    - Testing: Test coverage >90%, all tests passing, E2E tests
    - Deployment: Dockerfile, CI/CD config, deployment docs
  - **AI Validation**: LLM reviews artifact quality, completeness, adherence to requirements
  - **Acceptance**: Tracks all deliverables, validates with AI, blocks phase completion if missing
  - **Test**: Unit tests for validation logic, integration tests with real artifacts

- [ ] **TODO**: Build phase completion validation (checklist + 100% tests + human approval)
  - **File**: `backend/services/phase_validator.py`
  - **Class**: `PhaseValidator` with method `can_complete_phase(phase_id) -> ValidationResult`
  - **Validation Criteria**:
    1. All deliverables present and validated
    2. All tests passing (pytest + frontend tests)
    3. Code coverage ≥ 90%
    4. No blocking issues or gates
    5. Human approval received (if required by autonomy level)
  - **Human Approval**: Creates gate if autonomy level requires review
  - **Acceptance**: Phase cannot complete without all criteria met
  - **Test**: Test each validation criterion, test approval flow

- [ ] **TODO**: Design phase transition system with LLM agent handoffs
  - **File**: `backend/services/phase_transition_service.py`
  - **Class**: `PhaseTransitionService` with method `transition(from_phase, to_phase, project_id)`
  - **Transition Logic**:
    1. Validate current phase complete
    2. Archive current phase artifacts
    3. Notify agents of phase change
    4. Assign new agents for next phase
    5. Generate transition report (what was done, what's next)
    6. Update project state
  - **Agent Handoff**: PM agent briefs new phase agents on project context
  - **Acceptance**: Smooth transitions, no data loss, agents properly briefed
  - **Test**: Test all 5 phase transitions, test rollback on failure

- [ ] **TODO**: Add LLM-generated progress reports and status updates
  - **File**: `backend/services/progress_reporter.py`
  - **Class**: `ProgressReporter` with methods:
    - `generate_daily_report(project_id) -> Report` - Daily progress summary
    - `generate_phase_summary(phase_id) -> Summary` - Phase completion summary
    - `generate_blockers_report(project_id) -> Report` - Current issues
  - **Report Contents**: Completed tasks, test coverage, blockers, next steps, timeline
  - **LLM Generation**: Uses orchestrator LLM to analyze progress and generate natural language report
  - **Delivery**: Store in database, email to user (if SMTP enabled), show in UI
  - **Acceptance**: Reports accurate, actionable, generated automatically
  - **Test**: Generate reports, verify content accuracy, test scheduling

- [ ] **TODO**: Create AI-assisted phase planning and milestone generation
  - **File**: `backend/services/milestone_generator.py`
  - **Class**: `MilestoneGenerator` with method `generate_milestones(project_description) -> List[Milestone]`
  - **Planning Process**:
    1. Analyze project description with LLM
    2. Break into 6 phases
    3. Generate milestones per phase (3-5 milestones each)
    4. Estimate timeline based on complexity
    5. Define deliverables per milestone
  - **Example Output**:
    ```json
    {
      "phase": "Implementation",
      "milestones": [
        {"name": "Backend API Complete", "tasks": 12, "estimate": "5 days"},
        {"name": "Frontend Components", "tasks": 8, "estimate": "3 days"}
      ]
    }
    ```
  - **Acceptance**: Generates reasonable milestones, estimates within 50% of actual
  - **Test**: Test with various project types, validate output structure

### 3.2 Testing Framework Integration

- [ ] **TODO**: Set up testing frameworks (pytest, Jest, Playwright)
  - **Backend**: pytest with pytest-cov, pytest-asyncio, pytest-mock
  - **Frontend**: Vitest for unit/component tests, Playwright for E2E
  - **Configuration Files**:
    - `pytest.ini` - pytest config (already exists)
    - `vitest.config.ts` - Vitest configuration
    - `playwright.config.ts` - E2E test configuration
  - **Script**: `backend/scripts/setup_testing.py` - Install and configure all test frameworks
  - **Acceptance**: All frameworks installed, configs in place, sample test runs successfully
  - **Test**: Run `pytest --version`, `vitest --version`, `playwright test --help`

- [ ] **TODO**: Implement "test reality" philosophy (minimal mocking)
  - **Documentation**: `docs/testing/test_reality_guide.md`
  - **Principles**:
    - Use real database (PostgreSQL) in tests, not mocks
    - Use real OpenAI calls in LLM tests (with skip if no API key)
    - Use real file system operations, not mocks
    - Mock only external services (GitHub API, SMTP in CI)
  - **Infrastructure**: Docker Compose for test database, Qdrant test instance
  - **Acceptance**: Tests use real components, mocks only for external services
  - **Example**:
    ```python
    # ❌ BAD: Mock database
    @patch('database.query')
    def test_get_user(mock_query):
        mock_query.return_value = {"id": 1}
    
    # ✅ GOOD: Real database
    def test_get_user(test_db):
        user = create_user(test_db, email="test@example.com")
        result = get_user(test_db, user.id)
        assert result.email == "test@example.com"
    ```

- [ ] **TODO**: Create staged testing pipeline with early failure detection
  - **File**: `backend/scripts/run_tests_staged.py`
  - **7-Stage Pipeline**:
    1. Linting (ruff, mypy) - fails fast
    2. Unit tests (isolated) - fails fast
    3. Integration tests (database, services)
    4. API tests (FastAPI endpoints)
    5. LLM tests (Stage 1: rubric validation)
    6. E2E tests (Playwright)
    7. LLM tests (Stage 2: AI panel - expensive, runs last)
  - **Early Failure**: Stop on first failure, don't waste time
  - **CI Integration**: GitHub Actions runs this pipeline
  - **Acceptance**: Stages run in order, fail fast, clear error messages
  - **Test**: Run pipeline with intentional failures at each stage

- [ ] **TODO**: Build 100% coverage enforcement system
  - **File**: `.github/workflows/ci.yml` - CI pipeline with coverage check
  - **Enforcement**: pytest --cov --cov-fail-under=90 (90% minimum)
  - **Reporting**: Coverage report artifact in CI, displayed in PR
  - **Exceptions**: Only allow <90% with explicit comment explaining why
  - **Acceptance**: CI fails if coverage < 90%, developers notified
  - **Test**: Test with <90% coverage, verify CI fails

- [ ] **TODO**: Add LLM-powered test generation and optimization
  - **File**: `backend/services/test_generator.py`
  - **Class**: `TestGenerator` with methods:
    - `generate_unit_tests(code_file) -> str` - Generate pytest tests for code
    - `identify_missing_coverage(coverage_report) -> List[str]` - Find uncovered lines
    - `generate_edge_cases(function_signature) -> List[TestCase]` - Suggest edge cases
  - **LLM Integration**: Analyzes code, generates test cases with assertions
  - **Acceptance**: Generated tests are valid, runnable, find bugs
  - **Test**: Generate tests for sample code, verify they run and pass

- [ ] **TODO**: Implement AI-assisted test case design and edge case identification
  - **File**: `backend/services/edge_case_finder.py`
  - **Class**: `EdgeCaseFinder` with method `find_edge_cases(function_def) -> List[EdgeCase]`
  - **Analysis**: LLM analyzes function signature, types, logic to identify edge cases
  - **Edge Cases**: Null inputs, boundary values, empty lists, max/min integers, unicode, concurrent access
  - **Output**: List of test scenarios with expected behavior
  - **Acceptance**: Finds non-obvious edge cases, improves test coverage
  - **Test**: Test with various functions, verify edge case quality

- [ ] **TODO**: Create automated test maintenance with AI updates
  - **File**: `backend/services/test_maintainer.py`
  - **Purpose**: Update tests when code changes
  - **Process**:
    1. Detect code changes in PR/commit
    2. Analyze impact on existing tests
    3. Suggest test updates with LLM
    4. Generate PR comment with suggested changes
  - **Example**: Function signature changes → Update test mocks and assertions
  - **Acceptance**: Suggests accurate test updates, reduces test maintenance burden
  - **Test**: Change code, verify test update suggestions

### 3.3 Quality Assurance System

- [ ] **TODO**: Implement test quality scoring with AI analysis
  - **File**: `backend/services/test_quality_scorer.py`
  - **Class**: `TestQualityScorer` with method `score_test(test_code) -> Score`
  - **Scoring Criteria** (0-100):
    - Coverage: Does it test all code paths? (30 points)
    - Assertions: Meaningful assertions vs. just "runs without error"? (25 points)
    - Edge cases: Tests boundary conditions? (20 points)
    - Clarity: Clear test names and structure? (15 points)
    - Independence: No dependencies on other tests? (10 points)
  - **LLM Analysis**: Evaluates test quality, provides improvement suggestions
  - **Acceptance**: Scores correlate with actual test effectiveness
  - **Test**: Score known good/bad tests, verify accuracy

- [ ] **TODO**: Create continuous learning from test failures using LLM analysis
  - **File**: `backend/services/failure_learner.py`
  - **Purpose**: Learn patterns from test failures to prevent future issues
  - **Process**:
    1. Capture test failure (error message, stack trace, code context)
    2. Analyze with LLM to identify root cause pattern
    3. Store pattern in RAG knowledge base
    4. Use pattern for future test generation
  - **Knowledge Base**: Stores "common failure patterns" as embeddings
  - **Acceptance**: Similar failures detected earlier over time
  - **Test**: Introduce known failure patterns, verify learning

- [ ] **TODO**: Build security testing integration with AI vulnerability detection
  - **File**: `backend/services/security_test_runner.py`
  - **Tools**: bandit (Python), npm audit (Node), OWASP ZAP
  - **AI Enhancement**: LLM analyzes code for security patterns (SQL injection, XSS, etc.)
  - **Checks**:
    - Dependency vulnerabilities (CVE scanning)
    - Code vulnerabilities (static analysis)
    - Runtime vulnerabilities (DAST with ZAP)
    - AI-detected patterns (hardcoded secrets, weak crypto)
  - **Acceptance**: Finds known vulnerabilities, generates security test cases
  - **Test**: Test with intentionally vulnerable code

- [ ] **TODO**: Design performance testing framework with AI optimization
  - **File**: `backend/services/performance_tester.py`
  - **Metrics**: Response time, throughput, memory usage, database query count
  - **Benchmarks**: Define performance targets per endpoint
  - **AI Optimization**: LLM analyzes slow queries/endpoints and suggests improvements
  - **Tools**: locust for load testing, pytest-benchmark for micro-benchmarks
  - **Acceptance**: Detects performance regressions, suggests optimizations
  - **Test**: Run load tests, verify metrics collected

- [ ] **TODO**: Add LLM-powered code review and quality assessment
  - **File**: `backend/services/code_reviewer.py`
  - **Class**: `CodeReviewer` with method `review_code(code_diff) -> ReviewResult`
  - **Review Aspects**: Code style, potential bugs, security issues, performance, maintainability
  - **Output**: List of issues with severity (critical/major/minor), suggested fixes
  - **Integration**: Runs on PR creation, posts review as PR comment
  - **Acceptance**: Finds real issues, minimal false positives, actionable feedback
  - **Test**: Review known good/bad code, verify accuracy

- [ ] **TODO**: Create AI-driven quality metrics and improvement recommendations
  - **File**: `backend/services/quality_metrics_analyzer.py`
  - **Metrics**: Code coverage, test quality scores, security scan results, performance benchmarks
  - **Dashboard**: Aggregate metrics over time, show trends
  - **AI Recommendations**: Analyze metrics and suggest improvements ("Focus on testing module X", "Optimize query Y")
  - **Acceptance**: Recommendations are actionable and improve quality
  - **Test**: Generate metrics, verify recommendations

### 3.4 Debugging & Failure Resolution

- [ ] **TODO**: Create structured debugging process with LLM assistance
  - **File**: `backend/services/debug_assistant.py`
  - **Class**: `DebugAssistant` with method `analyze_failure(error, context) -> DebugPlan`
  - **Process**:
    1. Capture: Error message, stack trace, code context, recent changes
    2. Analyze: LLM identifies likely root cause
    3. Plan: Generate debugging steps (add logging, reproduce, test fix)
    4. Execute: Agent follows debug plan
    5. Verify: Confirm fix resolves issue
  - **Example Output**:
    ```json
    {
      "likely_cause": "Database connection timeout",
      "debug_steps": [
        "Check database connection pool settings",
        "Add logging to connection attempts",
        "Test with increased timeout"
      ],
      "confidence": 0.8
    }
    ```
  - **Acceptance**: Debugging plans are helpful, reduce time to resolution
  - **Test**: Test with various failure types

- [ ] **TODO**: Implement agent collaboration for problem solving
  - **Note**: Already covered in Section 1.3.1 (Agent Collaboration Protocol)
  - **Reference**: Decision 70 - Agent Collaboration Protocol
  - **No additional work needed**

- [ ] **TODO**: Build escalation paths for specialist help
  - **Note**: Already covered in Section 1.3 (Decision-Making & Escalation System)
  - **Reference**: Uses CollaborationOrchestrator to route to specialists
  - **No additional work needed**

- [ ] **TODO**: Design progress recognition vs. identical failure detection
  - **Note**: Already implemented in Section 1.2.0 and 1.4.1
  - **Reference**: LoopDetector (3 identical failures triggers gate)
  - **No additional work needed**

- [ ] **TODO**: Add AI-powered root cause analysis and failure prediction
  - **File**: `backend/services/root_cause_analyzer.py`
  - **Class**: `RootCauseAnalyzer` with methods:
    - `analyze_failure(failure_data) -> RootCause` - Identify root cause
    - `predict_failures(project_metrics) -> List[PredictedFailure]` - Predict issues
  - **Root Cause Analysis**: Analyzes error, code changes, dependencies, system state
  - **Failure Prediction**: Uses project metrics (test failures, code churn, complexity) to predict likely failures
  - **Acceptance**: Root cause analysis accurate >70%, predictions useful
  - **Test**: Test with historical failures, verify accuracy

- [ ] **TODO**: Create LLM-generated debugging strategies and solutions
  - **File**: `backend/services/solution_generator.py`
  - **Class**: `SolutionGenerator` with method `generate_solutions(problem) -> List[Solution]`
  - **Process**:
    1. Analyze problem with LLM
    2. Query knowledge base for similar issues
    3. Generate multiple solution approaches
    4. Rank by confidence and complexity
  - **Output**: Ranked list of solutions with implementation steps
  - **Acceptance**: Solutions are valid, at least one works >80% of time
  - **Test**: Test with known problems, verify solution quality

---

## Phase 4: Frontend & Monitoring Implementation

### 4.1 Frontend Architecture

- [ ] **TODO**: Set up React + TypeScript project structure
  - **Directory**: `frontend/` (new React app)
  - **Tool**: Create React App with TypeScript template OR Vite + React + TypeScript
  - **Structure**:
    ```
    frontend/
    ├── src/
    │   ├── components/     # Reusable UI components
    │   ├── pages/          # Page components (Dashboard, Settings, etc.)
    │   ├── hooks/          # Custom React hooks
    │   ├── store/          # Zustand state management
    │   ├── services/       # API client services
    │   ├── types/          # TypeScript type definitions
    │   ├── utils/          # Utility functions
    │   ├── App.tsx         # Root component
    │   └── main.tsx        # Entry point
    ├── public/             # Static assets
    ├── tests/              # Test files
    ├── package.json
    ├── tsconfig.json       # TypeScript config
    └── vite.config.ts      # Vite config (if using Vite)
    ```
  - **Dependencies**: react, react-dom, typescript, react-router-dom
  - **Dev Dependencies**: @types/react, @types/react-dom, vite, vitest
  - **Acceptance**: Clean project structure, TypeScript compiles, dev server runs
  - **Test**: Run `npm run dev`, verify app loads in browser

- [ ] **TODO**: Implement Tailwind CSS + Headless UI + Lucide React
  - **Tailwind CSS**: Utility-first CSS framework
  - **Installation**: `npm install -D tailwindcss postcss autoprefixer`
  - **Config**: `tailwind.config.js` with dark mode, custom colors
  - **Theme**: Dark blue dark mode as primary theme
  - **Headless UI**: Unstyled, accessible UI components
  - **Installation**: `npm install @headlessui/react`
  - **Components**: Dialog, Menu, Listbox, Disclosure, Tab, Transition
  - **Lucide React**: Icon library (modern, lightweight)
  - **Installation**: `npm install lucide-react`
  - **Icons**: Use for all UI icons (menu, settings, status, etc.)
  - **Acceptance**: Tailwind classes work, Headless UI components render, icons display
  - **Test**: Create sample component with Tailwind + Headless UI + Lucide icon
  - **Example**:
    ```tsx
    import { Menu } from '@headlessui/react'
    import { Settings } from 'lucide-react'
    
    export function SettingsMenu() {
      return (
        <Menu as="div" className="relative">
          <Menu.Button className="flex items-center space-x-2 p-2 rounded-lg hover:bg-slate-700">
            <Settings className="w-5 h-5" />
            <span>Settings</span>
          </Menu.Button>
          <Menu.Items className="absolute right-0 mt-2 w-48 bg-slate-800 rounded-lg shadow-lg">
            {/* Menu items */}
          </Menu.Items>
        </Menu>
      )
    }
    ```

- [ ] **TODO**: Create Zustand state management setup
  - **Library**: Zustand (lightweight state management)
  - **Installation**: `npm install zustand`
  - **Stores to Create**:
    - `useProjectStore` - Current project, project list, filters
    - `useAgentStore` - Agent statuses, current activity
    - `useSettingsStore` - User settings, autonomy level, preferences
    - `useGateStore` - Active gates, gate history
    - `useWebSocketStore` - WebSocket connection state, messages
  - **File**: `frontend/src/store/projectStore.ts`
  - **Example**:
    ```typescript
    import { create } from 'zustand'
    
    interface ProjectState {
      projects: Project[]
      currentProject: Project | null
      setProjects: (projects: Project[]) => void
      setCurrentProject: (project: Project) => void
    }
    
    export const useProjectStore = create<ProjectState>((set) => ({
      projects: [],
      currentProject: null,
      setProjects: (projects) => set({ projects }),
      setCurrentProject: (project) => set({ currentProject: project })
    }))
    ```
  - **Acceptance**: Stores created, state updates work, components can access state
  - **Test**: Component tests verify state updates

- [ ] **TODO**: Build React Query for server state management
  - **Library**: @tanstack/react-query (formerly React Query)
  - **Installation**: `npm install @tanstack/react-query`
  - **Purpose**: Cache server data, handle loading/error states, automatic refetch
  - **Setup**: QueryClient and QueryClientProvider in App.tsx
  - **Queries to Create**:
    - `useProjects()` - Fetch all projects
    - `useProject(id)` - Fetch single project
    - `useAgents()` - Fetch agent statuses
    - `useGates()` - Fetch active gates
    - `useSettings()` - Fetch user settings
    - `useCostData(projectId)` - Fetch cost metrics
  - **Mutations to Create**:
    - `useCreateProject()` - Create new project
    - `useUpdateSettings()` - Update settings
    - `useResolveGate()` - Resolve/reject gate
  - **Config**: Stale time, cache time, retry logic
  - **Acceptance**: Queries cache data, loading states work, mutations trigger refetch
  - **Test**: Component tests with mock QueryClient
  - **Example**:
    ```typescript
    import { useQuery } from '@tanstack/react-query'
    
    export function useProjects() {
      return useQuery({
        queryKey: ['projects'],
        queryFn: async () => {
          const res = await fetch('/api/v1/projects')
          return res.json()
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
      })
    }
    ```

- [ ] **TODO**: Implement WebSocket integration for real-time updates
  - **Backend WebSocket**: FastAPI WebSocket endpoint `/ws/{project_id}`
  - **Frontend Client**: Native WebSocket or use library like `socket.io-client`
  - **Hook**: `useWebSocket(projectId)` custom hook
  - **Events to Handle**:
    - `agent_status_update` - Agent started/stopped/error
    - `task_progress` - Task completion percentage
    - `gate_created` - New gate requires attention
    - `test_result` - Test pass/fail notification
    - `cost_update` - Token usage update
    - `llm_response_chunk` - Streaming LLM response
  - **Reconnection**: Auto-reconnect with exponential backoff
  - **Store Integration**: Update Zustand stores on WebSocket events
  - **Acceptance**: Real-time updates work, reconnection handles disconnects
  - **Test**: Integration test with mock WebSocket server
  - **Example**:
    ```typescript
    import { useEffect } from 'react'
    import { useWebSocketStore } from '@/store/websocketStore'
    
    export function useWebSocket(projectId: string) {
      const { setConnected, addMessage } = useWebSocketStore()
      
      useEffect(() => {
        const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}`)
        
        ws.onopen = () => setConnected(true)
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          addMessage(data)
        }
        ws.onclose = () => setConnected(false)
        
        return () => ws.close()
      }, [projectId])
    }
    ```

- [ ] **TODO**: Add LLM response streaming and real-time display
  - **Component**: `StreamingResponse` component
  - **File**: `frontend/src/components/StreamingResponse.tsx`
  - **Purpose**: Display LLM responses as they stream in (word-by-word or chunk)
  - **Implementation**:
    - Listen for `llm_response_chunk` WebSocket events
    - Append chunks to text buffer
    - Render with typewriter effect
    - Show loading indicator while streaming
  - **Features**:
    - Markdown rendering (code blocks, lists, etc.)
    - Syntax highlighting for code
    - Copy button for code blocks
    - Stop generation button
  - **Libraries**: `react-markdown`, `react-syntax-highlighter`
  - **Acceptance**: Streaming text displays smoothly, markdown renders correctly
  - **Test**: Component test with mock streaming data
  - **Example**:
    ```tsx
    import ReactMarkdown from 'react-markdown'
    
    export function StreamingResponse({ chunks, isStreaming }: Props) {
      const fullText = chunks.join('')
      
      return (
        <div className="streaming-response">
          <ReactMarkdown>{fullText}</ReactMarkdown>
          {isStreaming && <Spinner />}
        </div>
      )
    }
    ```

- [ ] **TODO**: Create frontend LLM prompt editing interface
  - **Page**: `/settings/prompts` or `/prompts`
  - **Component**: `PromptEditor.tsx`
  - **Features**:
    - List all agent types with current active prompt version
    - Select agent type → Show current prompt text
    - Edit prompt in textarea with syntax highlighting
    - Version number input (semantic versioning)
    - Save creates new version (doesn't modify existing)
    - Activate/deactivate prompt versions
    - Show prompt performance metrics (if available)
  - **Layout**: Split view - Agent list (left) | Prompt editor (right)
  - **Validation**: Prevent empty prompts, enforce version format (x.y.z)
  - **Acceptance**: Can view/edit/save prompts, version management works
  - **Test**: E2E test full prompt editing workflow
  - **Backend APIs**:
    - GET `/api/v1/prompts` - List all prompts
    - GET `/api/v1/prompts/{agent_type}` - Get active prompt for agent
    - POST `/api/v1/prompts` - Create new prompt version
    - PUT `/api/v1/prompts/{id}/activate` - Activate prompt version

### 4.2 Dashboard System

- [ ] **TODO**: Create main dashboard with project cards
  - **Page**: `/dashboard` (home page after login)
  - **Component**: `Dashboard.tsx`
  - **Layout**: Header + Project grid + "New Project" button
  - **Data**: Fetch projects with `useProjects()` React Query hook
  - **Real-time**: Subscribe to WebSocket for project status updates
  - **Empty State**: Show welcome message + "Create Your First Project" CTA when no projects
  - **Loading State**: Skeleton cards while loading
  - **Error State**: Error message with retry button
  - **Acceptance**: Dashboard loads projects, shows cards, real-time updates work
  - **Test**: Component test with mock data, E2E test full dashboard
  - **Backend API**: GET `/api/v1/projects` returns list of projects

- [ ] **TODO**: Build responsive grid layout (1/2/4+ columns)
  - **Grid**: CSS Grid or Tailwind grid classes
  - **Breakpoints**:
    - Mobile (< 640px): 1 column
    - Tablet (640px - 1024px): 2 columns
    - Desktop (1024px - 1536px): 3 columns
    - Large Desktop (> 1536px): 4 columns
  - **Gap**: Consistent spacing between cards (e.g., 6 or 8 in Tailwind scale)
  - **Auto-layout**: Cards flow naturally, no fixed heights
  - **Acceptance**: Grid adapts to screen size, no horizontal scroll on mobile
  - **Test**: Visual regression tests at different breakpoints
  - **Example**:
    ```tsx
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {projects.map(project => <ProjectCard key={project.id} project={project} />)}
    </div>
    ```

- [ ] **TODO**: Implement rich project card information display
  - **Component**: `ProjectCard.tsx`
  - **Information to Display**:
    - Project name (truncate if too long)
    - Status badge (color-coded: green=active, yellow=waiting, red=error, gray=complete)
    - Current phase (Workshopping, Implementation, Testing, etc.)
    - Progress bar (0-100%)
    - Last activity timestamp ("2 hours ago")
    - Active agents count ("3 agents working")
    - Cost summary ("$2.34 spent")
    - Test status ("45/50 tests passing")
  - **Hover State**: Elevate card, show more details
  - **Click**: Navigate to project detail page (`/projects/{id}`)
  - **Actions Menu**: Three-dot menu with Archive, Delete, Settings
  - **Acceptance**: All info displays correctly, click navigation works, menu actions work
  - **Test**: Component test with various project states
  - **Example**:
    ```tsx
    export function ProjectCard({ project }: Props) {
      return (
        <div className="bg-slate-800 rounded-lg p-6 hover:shadow-xl transition-shadow cursor-pointer"
             onClick={() => navigate(`/projects/${project.id}`)}>
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-xl font-semibold">{project.name}</h3>
            <StatusBadge status={project.status} />
          </div>
          <p className="text-sm text-slate-400 mb-4">{project.current_phase}</p>
          <ProgressBar value={project.progress} />
          <div className="flex justify-between text-xs text-slate-500 mt-4">
            <span>{formatDistanceToNow(project.last_activity)}</span>
            <span>${project.cost_spent.toFixed(2)}</span>
          </div>
        </div>
      )
    }
    ```

- [ ] **TODO**: Create real-time color-coded status system
  - **Statuses**:
    - `active` - Green (agents working, tasks executing)
    - `waiting` - Yellow (waiting for human approval/gate)
    - `error` - Red (agent failed, test failed, blocked)
    - `completed` - Blue (phase or project complete)
    - `archived` - Gray (project archived)
  - **Component**: `StatusBadge.tsx`
  - **Real-time Updates**: WebSocket `project_status_update` event updates badge
  - **Visual Indicators**:
    - Pulse animation for active status
    - Alert icon for error status
    - Clock icon for waiting status
  - **Tooltip**: Hover shows detailed status message
  - **Acceptance**: Colors accurate, real-time updates instant, tooltip helpful
  - **Test**: Component test all statuses, E2E test status changes
  - **Example**:
    ```tsx
    const statusConfig = {
      active: { color: 'bg-green-500', label: 'Active', icon: Activity },
      waiting: { color: 'bg-yellow-500', label: 'Waiting', icon: Clock },
      error: { color: 'bg-red-500', label: 'Error', icon: AlertCircle },
      completed: { color: 'bg-blue-500', label: 'Complete', icon: CheckCircle },
      archived: { color: 'bg-gray-500', label: 'Archived', icon: Archive },
    }
    ```

- [ ] **TODO**: Build "New Project" button functionality
  - **Button**: Prominent CTA in dashboard header
  - **Click**: Open modal/dialog for project creation
  - **Modal Component**: `NewProjectModal.tsx`
  - **Form Fields**:
    - Project name (required, max 100 chars)
    - Description (optional, max 500 chars)
    - Initial phase selection (default: Workshopping)
  - **Validation**: Name required, no duplicate names
  - **Submit**: POST to `/api/v1/projects` with mutation
  - **Success**: Close modal, navigate to new project detail page, show toast
  - **Error**: Show error message in modal
  - **Acceptance**: Can create project, validation works, navigation works
  - **Test**: E2E test full project creation flow
  - **Backend API**: POST `/api/v1/projects` with `{name, description, initial_phase}`

- [ ] **TODO**: Add LLM agent status and activity monitoring
  - **Component**: `AgentActivityPanel.tsx` (sidebar or separate section)
  - **Display**:
    - List of 10 agent types
    - Current status per agent (idle, working, error)
    - Current task (if working)
    - Last activity timestamp
    - Agent icon + name
  - **Real-time**: WebSocket `agent_status_update` event
  - **Click Agent**: Show agent detail panel with:
    - Recent tasks history
    - Token usage
    - Current LLM config (model, temperature)
    - Performance metrics (avg task time, success rate)
  - **Filter**: Show all / Show active only
  - **Acceptance**: Agent statuses accurate, real-time updates work, detail panel informative
  - **Test**: Component test with mock data, E2E test agent activity updates
  - **Backend API**: GET `/api/v1/agents/status` returns all agent statuses

- [ ] **TODO**: Create AI-powered project insights and recommendations
  - **Component**: `InsightsPanel.tsx`
  - **Location**: Dashboard sidebar or top of page
  - **Insights Generated by LLM**:
    - "Project X is blocked - consider reviewing gate #42"
    - "Test coverage dropped to 85% in Project Y"
    - "Agent Backend Dev has high error rate - check logs"
    - "Cost trending 20% higher than last week"
    - "Orchestrator recommends: Run tests before deployment"
  - **Frequency**: Regenerate insights every 15 minutes or on major events
  - **Backend**: LLM analyzes project metrics, generates recommendations
  - **UI**: Card-based, dismissible, priority-ordered
  - **Actions**: Click insight → Navigate to relevant page/data
  - **Acceptance**: Insights relevant, actionable, update automatically
  - **Test**: Mock insights, verify navigation, test auto-refresh
  - **Backend API**: GET `/api/v1/insights` returns list of insights

### 4.3 Navigation & Layout

- [ ] **TODO**: Implement sidebar navigation system
  - **Component**: `Sidebar.tsx`
  - **Layout**: Fixed left sidebar, collapsible on mobile
  - **Width**: 240px on desktop, slide-in drawer on mobile
  - **Navigation Items**:
    - Dashboard (home icon)
    - Projects (folder icon)
    - AI Costs (dollar-sign icon)
    - Agents (users icon)
    - Reporting (bar-chart icon)
    - Archive (archive icon)
    - Settings (settings icon)
  - **Active State**: Highlight current page, show indicator bar
  - **Collapse**: Hamburger menu toggle on mobile
  - **User Menu**: At bottom - user avatar, name, logout
  - **Acceptance**: Navigation works, active state accurate, mobile drawer works
  - **Test**: E2E test navigation to all pages, test mobile drawer
  - **Example**:
    ```tsx
    import { LayoutDashboard, FolderKanban, DollarSign, Users, BarChart3, Archive, Settings } from 'lucide-react'
    
    const navItems = [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Projects', href: '/projects', icon: FolderKanban },
      { name: 'AI Costs', href: '/costs', icon: DollarSign },
      // ... etc
    ]
    ```

- [ ] **TODO**: Create Dashboard, Reporting, AI Costs, Team, Archive, Settings pages
  - **Dashboard**: `/dashboard` - Already covered in 4.2
  - **Projects List**: `/projects` - Alternative view to dashboard (table instead of cards)
  - **AI Costs**: `/costs` - Cost tracking dashboard (covered in 4.6)
  - **Agents**: `/agents` - Agent status monitoring page
  - **Reporting**: `/reports` - Generate and view project reports
  - **Archive**: `/archive` - View archived projects
  - **Settings**: `/settings` - User and system settings
  - **Each Page Structure**:
    - Header with page title and actions
    - Main content area
    - Optional sidebar for filters/details
  - **Routing**: Use react-router-dom with protected routes
  - **Acceptance**: All pages accessible, routing works, 404 page for invalid routes
  - **Test**: E2E test navigation to each page
  - **Detailed Specs**:
    - **Reporting Page**: Generate PDF/HTML reports, select date range, filter by project
    - **Archive Page**: List archived projects, restore/delete permanently
    - **Agents Page**: Detailed agent monitoring (expanded version of AgentActivityPanel)

- [ ] **TODO**: Build dark blue dark mode theme
  - **Tool**: Tailwind CSS with custom color palette
  - **Color Scheme**:
    - Background: slate-900 (#0f172a)
    - Surface: slate-800 (#1e293b)
    - Primary: blue-600 (#2563eb) to blue-500 (#3b82f6)
    - Text: slate-50 (white) to slate-400 (muted)
    - Success: green-500, Warning: yellow-500, Error: red-500
  - **Tailwind Config**: `tailwind.config.js`
  - **Example**:
    ```javascript
    module.exports = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            primary: { 500: '#3b82f6', 600: '#2563eb' },
            background: '#0f172a',
            surface: '#1e293b',
          }
        }
      }
    }
    ```
  - **Global Styles**: Apply dark theme by default with `<html class="dark">`
  - **Accessibility**: Ensure sufficient contrast ratios (WCAG AA compliance)
  - **Acceptance**: Theme looks professional, consistent colors, readable text
  - **Test**: Visual regression tests, accessibility audit

- [ ] **TODO**: Design responsive mobile layout
  - **Breakpoints**: Follow Tailwind defaults (sm: 640px, md: 768px, lg: 1024px, xl: 1280px)
  - **Mobile (< 768px)**:
    - Collapsible hamburger sidebar
    - Single column layouts
    - Larger touch targets (min 44x44px)
    - Bottom navigation bar (alternative to sidebar)
  - **Tablet (768px - 1024px)**:
    - Persistent sidebar (can collapse)
    - 2-column layouts where appropriate
  - **Desktop (> 1024px)**:
    - Full sidebar always visible
    - Multi-column layouts
  - **Touch Optimization**: Larger buttons, swipe gestures for drawers
  - **Acceptance**: App usable on mobile, no horizontal scroll, touch targets adequate
  - **Test**: Manual testing on actual devices, responsive design tests

- [ ] **TODO**: Add LLM cost tracking dashboard and visualizations (manual control)
  - **Note**: Covered more comprehensively in Section 4.6.1
  - **Page**: `/costs` - Dedicated cost dashboard
  - **See Section 4.6.1 for full details**

- [ ] **TODO**: Create AI agent performance monitoring interface
  - **Page**: `/agents` - Full-page agent monitoring
  - **Layout**: Split view or tabs
  - **Agent List** (left or top):
    - All 10 agent types
    - Status indicators (active, idle, error)
    - Click to view details
  - **Agent Detail** (right or bottom):
    - Current task and progress
    - Recent task history (last 20 tasks)
    - Performance metrics:
      - Average task completion time
      - Success rate (completed vs failed)
      - Token usage (total, average per task)
      - Cost (total, average per task)
      - Error rate
    - Configuration: Current model, temperature
    - Activity timeline (visual representation)
  - **Charts**:
    - Task completion over time (line chart)
    - Success/failure pie chart
    - Token usage bar chart
  - **Filters**: Date range, agent type, status
  - **Real-time**: WebSocket updates for active agents
  - **Acceptance**: Shows accurate metrics, real-time updates work, charts render correctly
  - **Test**: Component tests with mock data, E2E test full page
  - **Backend APIs**:
    - GET `/api/v1/agents/{agent_type}/metrics` - Performance metrics
    - GET `/api/v1/agents/{agent_type}/tasks` - Task history
    - GET `/api/v1/agents/{agent_type}/activity` - Activity timeline

### 4.4 Project Detail Pages

- [ ] **TODO**: Create comprehensive project command center
  - **Page**: `/projects/{id}` - Main project detail page
  - **Layout**: Multi-panel dashboard
  - **Panels**:
    - **Header**: Project name, status, phase, progress bar, actions (Archive, Delete, Trigger Gate)
    - **Activity Stream** (center-left): Real-time feed of agent actions, test results, git commits
    - **File Browser** (left sidebar): Foldable directory tree
    - **Code Editor** (center): Monaco Editor for viewing/editing files
    - **Agent Chat** (right sidebar): Agent conversation stream
    - **Gates Panel** (bottom or modal): Active gates requiring human attention
  - **Tabs**: Overview | Code | Tests | Costs | Settings
  - **Real-time**: WebSocket for all updates (agent activity, test results, etc.)
  - **Acceptance**: All panels load, real-time updates work, navigation smooth
  - **Test**: E2E test full project page, test WebSocket updates
  - **Backend APIs**:
    - GET `/api/v1/projects/{id}` - Project details
    - GET `/api/v1/projects/{id}/activity` - Activity stream
    - GET `/api/v1/projects/{id}/files` - File tree
    - GET `/api/v1/projects/{id}/gates` - Active gates

- [ ] **TODO**: Build foldable file directory browser
  - **Component**: `FileTree.tsx`
  - **Features**:
    - Hierarchical tree structure (folders collapse/expand)
    - File icons by type (.py, .ts, .json, etc.)
    - Click file → Load in editor
    - Right-click menu: Open, Rename, Delete, New File/Folder
    - Search/filter files
    - Show file status icons (modified, new, deleted)
  - **State Management**: Track expanded folders, selected file
  - **Virtual Scrolling**: Handle large file trees (1000+ files)
  - **Library**: Consider `react-arborist` or custom recursive component
  - **Acceptance**: Tree navigable, click opens file, collapse/expand works, search works
  - **Test**: Component test with mock file tree, test search
  - **Example Structure**:
    ```typescript
    interface FileNode {
      name: string
      type: 'file' | 'folder'
      path: string
      children?: FileNode[]
    }
    ```

- [ ] **TODO**: Implement Monaco Editor integration
  - **Component**: `CodeEditor.tsx`
  - **Library**: `@monaco-editor/react` (Monaco Editor for React)
  - **Installation**: `npm install @monaco-editor/react`
  - **Features**:
    - Syntax highlighting (auto-detect from file extension)
    - Read-only mode (default) with "Edit" button to enable editing
    - Line numbers, minimap
    - Find/replace
    - Code folding
    - IntelliSense/autocomplete (if possible)
    - Diff view for comparing versions
  - **Theme**: Dark theme matching app colors
  - **Save**: "Save" button → PUT to backend
  - **Acceptance**: Editor loads files, syntax highlighting works, can edit and save
  - **Test**: Component test loading different file types, test save functionality
  - **Example**:
    ```tsx
    import Editor from '@monaco-editor/react'
    
    export function CodeEditor({ file, onSave }: Props) {
      const [value, setValue] = useState(file.content)
      
      return (
        <Editor
          height="90vh"
          language={getLanguageFromExtension(file.extension)}
          value={value}
          onChange={setValue}
          theme="vs-dark"
          options={{ readOnly: !editMode }}
        />
      )
    }
    ```

- [ ] **TODO**: Create agent chat stream viewer (read-only)
  - **Component**: `AgentChatStream.tsx`
  - **Location**: Right sidebar on project detail page
  - **Purpose**: Show real-time stream of agent "thoughts" and actions
  - **Message Types**:
    - Agent started task
    - Agent reasoning/planning
    - Agent tool call (write_file, run_command, etc.)
    - Agent result/completion
    - Agent error
    - Agent collaboration request
  - **UI**: Chat-like interface, scrollable, auto-scroll to bottom
  - **Formatting**: Markdown support, code blocks, syntax highlighting
  - **Filter**: Filter by agent type, message type
  - **Export**: Button to export chat history to file
  - **Acceptance**: Messages stream in real-time, formatting works, auto-scroll works
  - **Test**: Component test with mock messages, test auto-scroll
  - **Backend**: WebSocket `agent_chat_message` event

- [ ] **TODO**: Build manual gate trigger interface
  - **Component**: `GatePanel.tsx` and `TriggerGateButton.tsx`
  - **Location**: Project header ("Trigger Gate" button) + Gates panel at bottom
  - **Trigger Gate Button**:
    - Click → Open modal
    - Select gate type (manual_review, security_check, custom)
    - Enter reason/description
    - Submit → Create gate, pause all agents
  - **Gates Panel**:
    - List of active gates (pending approval)
    - Each gate shows: Type, reason, created time, requesting agent
    - Actions: Approve (green), Reject (red), Add Feedback
    - Approve → Resume agents, close gate
    - Reject → Stop project, close gate, agents notified
  - **Real-time**: New gates appear instantly via WebSocket
  - **Acceptance**: Can trigger gate, gates appear in panel, can approve/reject, agents respond
  - **Test**: E2E test full gate lifecycle (trigger → approve/reject → agents resume/stop)
  - **Backend APIs**:
    - POST `/api/v1/gates` - Create gate
    - PUT `/api/v1/gates/{id}/resolve` - Approve/reject gate

- [ ] **TODO**: Add LLM conversation history and context viewer
  - **Component**: `ConversationHistory.tsx`
  - **Location**: Separate tab or expandable panel on project page
  - **Display**:
    - List of all LLM conversations for this project
    - Each conversation: Agent, timestamp, prompt (truncated), response (truncated)
    - Click to expand → Show full prompt + response
    - Token count, cost, model used
  - **Filters**: By agent, date range, model
  - **Search**: Search prompt/response text
  - **Export**: Export conversations to JSON/CSV
  - **Context Viewer**: Show what context was included (files, RAG results, collaboration history)
  - **Acceptance**: Shows all conversations, expand works, filters work, export works
  - **Test**: Component test with mock conversations, test filters
  - **Backend API**: GET `/api/v1/projects/{id}/conversations`

- [ ] **TODO**: Create AI decision explanation and justification display
  - **Component**: `DecisionExplainer.tsx`
  - **Purpose**: Show why orchestrator/agents made specific decisions
  - **Display**:
    - Decision description ("Selected Backend Dev agent for API implementation")
    - Reasoning: Chain-of-thought explanation
    - Alternatives considered: Other options with scores
    - Confidence score
    - Timestamp, agent responsible
  - **Location**: Activity stream + dedicated Decisions tab
  - **Interaction**: Click decision → Expand to show full details
  - **Visual**: Tree or flowchart showing decision process
  - **Acceptance**: Decisions clear, reasoning understandable, helps user understand agent behavior
  - **Test**: Component test with mock decisions, verify formatting
  - **Backend**: Orchestrator logs decisions to `orchestrator_decisions` table
  - **Backend API**: GET `/api/v1/projects/{id}/decisions`

### 4.5 Settings & Configuration

- [ ] **TODO**: Implement database-stored settings system
  - **Note**: Already partially covered in Phase 1 and Section 1.2.1 (agent configs, API keys)
  - **Additional Settings Needed**:
    - User preferences (theme, notifications, default view)
    - System settings (session timeout, rate limits)
    - Project defaults (initial phase, default agents)
  - **Backend**: Settings stored in `user_settings` table (already created in migration 003)
  - **Frontend**: Load settings on app startup, update via mutations
  - **Acceptance**: Settings persist across sessions, changes take effect immediately
  - **Backend API**: GET/PUT `/api/v1/settings`

- [ ] **TODO**: Create GitHub Integration settings page
  - **Page**: `/settings/github`
  - **Component**: `GitHubSettings.tsx`
  - **Fields**:
    - GitHub Personal Access Token (PAT) input
    - Token scope requirements display (repo, workflow, read:org)
    - Test connection button
    - Repository selection (if connected)
    - Enable/disable auto-commit checkbox
    - Enable/disable auto-PR creation checkbox
  - **Workflow**:
    1. Enter PAT
    2. Click "Test Connection" → Verify token has correct scopes
    3. If valid, show repository list for selection
    4. Save settings
  - **Security**: Token stored encrypted in database (via backend API)
  - **Status Indicator**: Connected (green) / Not configured (yellow) / Invalid token (red)
  - **Help Section**: Link to GitHub PAT creation guide, scope explanation
  - **Acceptance**: Can configure GitHub, test connection works, token encrypted
  - **Test**: E2E test full configuration flow
  - **Backend APIs**:
    - POST `/api/v1/integrations/github/token` - Store encrypted token
    - POST `/api/v1/integrations/github/test` - Test token validity
    - GET `/api/v1/integrations/github/repos` - List accessible repos
    - PUT `/api/v1/integrations/github/settings` - Update GitHub settings

- [ ] **TODO**: Build OpenAI Integration settings page (API key config)
  - **Note**: Already covered in Section 1.2.1 - API key configuration UI
  - **See Section 1.2.1 for complete specification**
  - **No additional work needed**

- [ ] **TODO**: Design Agents and Specialists configuration pages (model selection)
  - **Note**: Already covered in Section 1.2.1 - Agent model selection UI
  - **See Section 1.2.1 for complete specification**
  - **Additional Features** (optional enhancements):
    - View agent performance metrics alongside config
    - Suggest model based on historical performance
    - Cost estimation per agent based on model selection

- [ ] **TODO**: Implement encrypted credential storage
  - **Note**: Already covered in Section 1.2.1 and authentication sections
  - **Encryption Method**: Fernet (symmetric encryption)
  - **Key Storage**: `ENCRYPTION_KEY` environment variable
  - **Encrypted Items**:
    - OpenAI API keys (Migration 004)
    - GitHub PAT tokens
    - SMTP passwords (Migration 021)
    - 2FA TOTP secrets (Migration 020)
  - **No additional implementation needed** - already specified in respective sections

- [ ] **TODO**: Add LLM provider configuration and API key management (single key)
  - **Note**: Already covered in Section 1.2.1
  - **Single provider**: OpenAI only (for now)
  - **No additional work needed**

- [ ] **TODO**: Create prompt template editing and versioning interface
  - **Note**: Already covered in Section 4.1 - "Create frontend LLM prompt editing interface"
  - **See Section 4.1 for complete specification**
  - **No additional work needed**
- [ ] **TODO**: Review and finalize Settings page autonomy slider implementation from Phase 1
  - **File**: `frontend/src/pages/Settings.tsx`
  - **Review**: Verify descriptions match backend thresholds, test E2E with backend API
  - **Acceptance**: Slider works correctly, persists to database, descriptions are accurate
  - **Test**: Manual testing of autonomy level changes with real backend
- [ ] **TODO**: Build per-agent LLM configuration UI (temperature & model selection)
  - **File**: `frontend/src/pages/Settings.tsx` or new `AgentConfiguration.tsx`
  - **Component**: Grid of agent cards, each with temperature slider and model dropdown
  - **Models**: gpt-4o-mini (default), gpt-4o, gpt-4-turbo, gpt-3.5-turbo
  - **Temperature**: Slider 0.0-1.0 with recommended defaults per agent type
  - **Presets**: "Cost Optimized", "Quality Optimized", "Balanced" buttons
  - **Acceptance**: All 11 agent types configurable, saves to database, loads current values
  - **Test**: E2E test changing agent configs and verifying persistence
- [ ] **TODO**: Create backend API endpoints for agent LLM configuration
  - **File**: `backend/api/routes/agent_config.py`
  - **Endpoints**: GET/PUT `/api/v1/settings/agent-llm-config/{agent_type}`
  - **Payload**: `{"model": "gpt-4o-mini", "temperature": 0.3, "agent_type": "orchestrator"}`
  - **Database**: Create `agent_llm_configs` table with user_id, agent_type, model, temperature
  - **Acceptance**: CRUD operations work, validates model/temperature ranges, defaults applied
  - **Test**: Unit tests for config service, integration tests for API endpoints

### 4.6 Monitoring & Cost Tracking

- [ ] **TODO**: Build comprehensive metrics collection system
  - **Backend Service**: `MetricsCollector` (already partially exists)
  - **File**: `backend/services/metrics_collector.py`
  - **Metrics to Collect**:
    - LLM token usage (input/output tokens per call) - logs to `llm_token_usage` table
    - Agent task execution times (start, end, duration)
    - Test results (pass/fail, coverage percentage)
    - Gate events (created, resolved, time to resolution)
    - Error rates (per agent, per project)
    - Cost accumulation (calculated from tokens + pricing)
  - **Collection Points**: Hook into OpenAIAdapter, agent execution loop, test runner
  - **Aggregation**: Real-time for dashboard, batch aggregation for reports
  - **Acceptance**: All metrics collected accurately, minimal performance impact
  - **Test**: Verify metrics logged, test aggregation queries

- [ ] **TODO**: Implement per-LLM-call cost tracking (token usage logging)
  - **Note**: Already specified in Section 1.2.1 and Migration 009
  - **Table**: `llm_token_usage` (Migration 009)
  - **Logging**: OpenAIAdapter._log_tokens() method hooks into this
  - **Cost Calculation**: tokens × pricing (from `llm_pricing` table)
  - **Real-time**: Calculate cost immediately after each call
  - **Retention**: 1-year rolling deletion
  - **No additional work needed** - already specified

- [ ] **TODO**: Create cost breakdown by project, agent, and action
  - **Backend Service**: `CostAnalyzer`
  - **File**: `backend/services/cost_analyzer.py`
  - **Methods**:
    - `get_cost_by_project(project_id, date_range) -> Dict` - Total cost per project
    - `get_cost_by_agent(project_id, date_range) -> Dict` - Cost breakdown by agent type
    - `get_cost_by_action(project_id, date_range) -> Dict` - Cost per action (plan, code, test, etc.)
    - `get_cost_trend(date_range) -> List` - Cost over time for charting
  - **Queries**: Aggregate from `llm_token_usage` joined with `llm_pricing`
  - **Caching**: Cache aggregated results for 5 minutes (trade-off for performance)
  - **Acceptance**: Breakdowns accurate, queries performant (<1s), caching works
  - **Test**: Unit tests with sample data, integration tests with real queries
  - **Backend API**: GET `/api/v1/costs/breakdown?project_id=X&date_range=7d&group_by=agent`

- [ ] **TODO**: Build pricing matrix management system
  - **Note**: Already covered in Migration 010 - LLM pricing table
  - **Additional UI**: Pricing management page (see Section 4.6.1)
  - **No additional backend work needed**

- [ ] **TODO**: Design cost reporting dashboard (manual oversight)
  - **Note**: Covered in Section 4.6.1 - Cost dashboard with visualizations
  - **See Section 4.6.1 for full specification**

- [ ] **TODO**: Add real-time LLM usage monitoring and alerts
  - **Component**: `CostMonitor.tsx` (widget on dashboard)
  - **Display**:
    - Current hourly/daily spend
    - Spend rate (tokens/hour)
    - Projected monthly cost
    - Budget utilization (if budget set)
  - **Alerts**:
    - Warning at 80% of daily budget
    - Critical at 100% of daily budget
    - Notification when single call exceeds threshold (e.g., $1)
  - **Budget Settings**: User-configurable daily/monthly budgets
  - **Real-time**: WebSocket `cost_update` event updates display
  - **Acceptance**: Monitors show accurate current spend, alerts trigger correctly
  - **Test**: Simulate high usage, verify alerts trigger
  - **Backend**: CostMonitor service checks budgets after each LLM call

- [ ] **TODO**: Create AI performance metrics and optimization insights
  - **Service**: `PerformanceAnalyzer`
  - **File**: `backend/services/performance_analyzer.py`
  - **Metrics**:
    - Agent efficiency (tasks completed / time spent)
    - Token efficiency (output quality / tokens used)
    - Cost efficiency (value delivered / cost)
    - Model performance comparison (gpt-4o vs gpt-4o-mini success rates)
  - **Insights Generated**:
    - "Backend Dev agent could use gpt-4o-mini for 80% of tasks, saving $X/month"
    - "Test coverage improved 10% but cost increased 5% - good ROI"
    - "Orchestrator temperature too high - consider lowering to 0.3 for cost savings"
  - **Recommendations**: LLM analyzes metrics and suggests optimizations
  - **Display**: Insights panel on costs dashboard
  - **Acceptance**: Insights actionable, recommendations improve cost efficiency
  - **Test**: Test with historical data, verify insight quality
  - **Backend API**: GET `/api/v1/insights/performance`

### 4.6.1 Cost Tracking System (Decision 75)

- [ ] **TODO**: Create pricing management settings page (/settings/pricing)
  - **Page**: `/settings/pricing`
  - **Component**: `PricingSettings.tsx`
  - **Display**: Table of all LLM models with current pricing
  - **Columns**: Model name, Input cost per 1M tokens, Output cost per 1M tokens, Effective date, Last updated
  - **Edit**: Click row → Edit modal with input fields
  - **Validation**: Positive numbers only, confirm before saving
  - **History**: Show pricing history (past 12 months)
  - **Import**: Button to import latest OpenAI pricing via API (if available) or manual CSV upload
  - **Acceptance**: Can update pricing, history tracked, changes reflect in cost calculations
  - **Test**: E2E test updating pricing, verify cost recalculation
  - **Backend API**: GET/PUT `/api/v1/pricing`, GET `/api/v1/pricing/history`

- [ ] **TODO**: Build cost dashboard with visualizations (/dashboard/costs or /costs)
  - **Page**: `/costs`
  - **Component**: `CostDashboard.tsx`
  - **Layout**: Overview cards (top) + Charts (middle) + Drill-down table (bottom)
  - **Real-time Updates**: WebSocket for current spend
  - **Export**: Button to export data to CSV/Excel
  - **Acceptance**: Dashboard loads quickly, charts interactive, data accurate
  - **Test**: Component test with mock data, E2E test full dashboard

- [ ] **TODO**: Implement time range selector (hour/day/week/month/quarter/year)
  - **Component**: `TimeRangeSelector.tsx`
  - **Options**: Last hour, Today, Last 7 days, Last 30 days, Last quarter, Last year, Custom range
  - **Custom Range**: Date picker for start/end dates
  - **State**: Selected range updates all charts/tables
  - **URL Sync**: Range in URL query params for sharing
  - **Acceptance**: Selector updates all visualizations, custom range works
  - **Test**: Component test all options, verify state updates

- [ ] **TODO**: Create overview cards (total cost, tokens, calls)
  - **Component**: `CostOverviewCards.tsx`
  - **Cards**:
    1. **Total Cost**: $X.XX with trend indicator (↑5% vs previous period)
    2. **Total Tokens**: X.XM tokens (input + output)
    3. **Total Calls**: X,XXX API calls
    4. **Average Cost per Call**: $X.XX
  - **Styling**: Card layout with large number, trend icon, comparison text
  - **Acceptance**: Cards show accurate totals, trends calculated correctly
  - **Test**: Component test with mock data

- [ ] **TODO**: Build line chart for cost over time
  - **Component**: `CostTrendChart.tsx`
  - **Library**: recharts or chart.js
  - **Installation**: `npm install recharts`
  - **X-axis**: Time (hours, days, weeks depending on range)
  - **Y-axis**: Cost ($)
  - **Lines**: Total cost, with optional split by project (toggle)
  - **Interaction**: Hover for exact values, click to drill down
  - **Acceptance**: Chart renders smoothly, interactive tooltips work
  - **Test**: Component test with sample time series data
  - **Example**:
    ```tsx
    import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts'
    
    <LineChart data={costData}>
      <XAxis dataKey="date" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Line type="monotone" dataKey="cost" stroke="#3b82f6" />
    </LineChart>
    ```

- [ ] **TODO**: Implement bar chart for cost by project
  - **Component**: `CostByProjectChart.tsx`
  - **X-axis**: Project names
  - **Y-axis**: Cost ($)
  - **Bars**: Color-coded by cost level (green=low, yellow=medium, red=high)
  - **Sorting**: Sort by cost (descending) or alphabetically
  - **Limit**: Show top 10 projects, "View All" button for full list
  - **Interaction**: Click bar → Navigate to project cost detail page
  - **Acceptance**: Chart accurate, sorting works, click navigation works
  - **Test**: Component test with mock projects

- [ ] **TODO**: Create pie chart for cost by agent
  - **Component**: `CostByAgentChart.tsx`
  - **Slices**: One per agent type (10 agents)
  - **Labels**: Agent name + percentage
  - **Colors**: Distinct color per agent
  - **Legend**: List of agents with colors
  - **Interaction**: Click slice → Show agent detail panel
  - **Acceptance**: Pie chart adds to 100%, colors distinguishable, interactive
  - **Test**: Component test with mock agent costs

- [ ] **TODO**: Build drill-down table (cost by agent per project)
  - **Component**: `CostDrillDownTable.tsx`
  - **Layout**: Expandable rows
  - **Top Level**: Project name, total cost
  - **Expanded**: Breakdown by agent (agent name, calls, tokens, cost)
  - **Columns**: Project, Agent, Calls, Input Tokens, Output Tokens, Total Cost
  - **Sorting**: Sort by any column
  - **Filtering**: Filter by project or agent
  - **Pagination**: 20 rows per page
  - **Export**: CSV export button
  - **Acceptance**: Table shows accurate data, expand/collapse works, sort/filter works
  - **Test**: Component test with mock data, test sorting

- [ ] **TODO**: Implement pricing matrix editing UI
  - **Note**: Covered in first task of this section (pricing management settings page)
  - **No additional work needed**

- [ ] **TODO**: Create manual pricing update interface
  - **Note**: Covered in first task of this section (pricing management settings page)
  - **No additional work needed**

### 4.7 User Authentication with 2FA
**Priority**: P1 - BLOCKING (Required before any multi-user features)  
**Reference**: `docs/architecture/decision-84-user-authentication-2fa.md`

#### Backend Authentication System

- [ ] **TODO**: Create users table with secure password storage
  - **Migration**: `alembic/versions/019_create_users_table.py`
  - **Schema**: id (UUID), email (UNIQUE), password_hash (bcrypt), is_active, is_verified, created_at, updated_at
  - **Indexes**: idx_users_email (unique), idx_users_active
  - **Security**: Use bcrypt for password hashing, min 12 rounds
  - **Acceptance**: Table stores user credentials securely, email uniqueness enforced
  - **Test**: Create users, verify password hashing, test uniqueness constraint

- [ ] **TODO**: Create user_sessions table for JWT token management
  - **Migration**: Same as users table migration
  - **Schema**: id (UUID), user_id (FK users), refresh_token_hash, expires_at, created_at, ip_address, user_agent
  - **Indexes**: idx_sessions_user, idx_sessions_token, idx_sessions_expiry
  - **Purpose**: Track active sessions, support token revocation, detect suspicious activity
  - **Acceptance**: Sessions tracked, tokens revocable, expired sessions cleanable
  - **Test**: Create session, verify token tracking, test expiry cleanup

- [ ] **TODO**: Create two_factor_auth table for 2FA secrets
  - **Migration**: `alembic/versions/020_create_2fa_table.py`
  - **Schema**: id (UUID), user_id (FK users, UNIQUE), secret_encrypted (Fernet), backup_codes_encrypted (JSONB), email_fallback_enabled (default true), enabled_at, last_used_at
  - **Encryption**: Use Fernet encryption for TOTP secrets, separate encryption key from password key
  - **Backup Codes**: Generate 10 single-use backup codes during setup
  - **Acceptance**: 2FA secrets stored encrypted, backup codes supported, email fallback configurable
  - **Test**: Store/retrieve secrets, verify encryption, test backup codes

- [ ] **TODO**: Create user_invites table for invite-only signup
  - **Migration**: Same as users table migration (019)
  - **Schema**: id (UUID), email (VARCHAR), invite_token (UUID UNIQUE), invited_by (FK users), expires_at (48 hours), consumed_at, created_at
  - **Indexes**: idx_invites_token (unique), idx_invites_email, idx_invites_expiry
  - **Purpose**: Track invite tokens, prevent duplicate invites, audit who invited whom
  - **Acceptance**: Invites tracked, single-use tokens, expired invites cleanable
  - **Test**: Create invite, redeem invite, test expiry, verify uniqueness

- [ ] **TODO**: Create bootstrap admin user script (solves chicken-and-egg problem)
  - **File**: `backend/scripts/create_admin_user.py`
  - **Purpose**: Create first admin user WITHOUT invite (bypasses invite-only system)
  - **Usage**: `python -m backend.scripts.create_admin_user --email admin@example.com --password <secure-password>`
  - **Security**: 
    - Only works when users table is empty (SELECT COUNT(*) FROM users = 0)
    - Requires strong password (12+ chars, complexity rules)
    - Logs admin creation with timestamp
    - Cannot run twice (raises error if users exist)
  - **Process**: 
    1. Check users table is empty
    2. Validate email format and password strength
    3. Hash password with bcrypt (12 rounds)
    4. Insert admin user with is_verified=true
    5. Log creation to console
  - **Acceptance**: First admin created, can login and create invites for other users
  - **Test**: Run script, verify admin created, test cannot run again with existing users
  - **Example**:
    ```bash
    # Create first admin
    python -m backend.scripts.create_admin_user \
      --email admin@example.com \
      --password "SecureP@ssw0rd123"
    
    # Output:
    # Admin user created successfully
    # Email: admin@example.com
    # User ID: 550e8400-e29b-41d4-a716-446655440000
    # You can now login and invite other users
    ```

- [ ] **TODO**: Implement AuthService with registration, login, and token management
  - **File**: `backend/services/auth_service.py`
  - **Class**: `AuthService` with methods:
    - `register(email, password) -> User` - Create user with hashed password
    - `login(email, password) -> TokenPair` - Authenticate and issue JWT tokens
    - `refresh_token(refresh_token) -> TokenPair` - Issue new access token
    - `logout(user_id, session_id)` - Revoke session
    - `verify_email(token)` - Email verification flow
  - **JWT Tokens**: Access token (15min), refresh token (7 days), signed with HS256
  - **Validation**: Email format, password strength (min 12 chars, uppercase, lowercase, number, special)
  - **Acceptance**: Full auth flow works, tokens secure, sessions tracked
  - **Test**: Unit tests for all methods, integration tests for auth flow

- [ ] **TODO**: Implement TwoFactorService for TOTP-based 2FA with email fallback
  - **File**: `backend/services/two_factor_service.py`
  - **Class**: `TwoFactorService` with methods:
    - `setup_2fa(user_id) -> (secret, qr_code_url)` - Generate TOTP secret and QR code
    - `verify_2fa_setup(user_id, token) -> bool` - Verify token and enable 2FA
    - `verify_2fa(user_id, token) -> bool` - Verify TOTP token during login
    - `send_email_otp(user_id) -> str` - Generate and send 6-digit OTP via email (10min expiry)
    - `verify_email_otp(user_id, code) -> bool` - Verify emailed OTP code
    - `generate_backup_codes(user_id) -> List[str]` - Generate 10 backup codes
    - `use_backup_code(user_id, code) -> bool` - Consume backup code
    - `disable_2fa(user_id, password)` - Disable 2FA after password verification
  - **Library**: Use `pyotp` for TOTP generation/verification
  - **QR Code**: Generate QR code data URI for authenticator app scanning
  - **Email OTP**: Store in Redis/memory with 10min TTL, rate limit 3 per hour
  - **Acceptance**: Full 2FA lifecycle works, backup codes functional, email OTP fallback works
  - **Test**: Setup 2FA, verify TOTP tokens, test email OTP, test backup codes, disable 2FA

- [ ] **TODO**: Create authentication API endpoints
  - **File**: `backend/api/routes/auth.py`
  - **Endpoints**:
    - POST `/api/v1/auth/register` - User registration via invite token
    - POST `/api/v1/auth/login` - Login (returns tokens + 2FA status)
    - POST `/api/v1/auth/login/2fa` - Complete login with 2FA token
    - POST `/api/v1/auth/refresh` - Refresh access token
    - POST `/api/v1/auth/logout` - Logout and revoke session
    - GET `/api/v1/auth/me` - Get current user info (requires auth)
    - GET `/api/v1/auth/sessions` - Get user's active sessions
    - DELETE `/api/v1/auth/sessions/{session_id}` - Revoke specific session
  - **Rate Limiting**: Max 5 login attempts per 15min per account, 10 per IP
  - **Acceptance**: All endpoints work, proper error handling, rate limiting enforced
  - **Test**: Integration tests for all endpoints, test rate limiting

- [ ] **TODO**: Create invite management API endpoints
  - **File**: `backend/api/routes/invites.py`
  - **Endpoints**:
    - POST `/api/v1/invites` - Create new invite (admin only)
    - GET `/api/v1/invites` - List pending invites (admin only)
    - DELETE `/api/v1/invites/{invite_id}` - Cancel invite (admin only)
    - GET `/api/v1/invites/validate/{token}` - Validate invite token (public)
  - **Payload**: `{"email": "user@example.com"}` for invite creation
  - **Response**: Returns invite token and copyable signup link
  - **Acceptance**: Invite management works, tokens validated, admin-only enforcement
  - **Test**: Create invite, validate token, redeem invite, cancel invite

- [ ] **TODO**: Create 2FA setup/management API endpoints
  - **File**: `backend/api/routes/two_factor.py`
  - **Endpoints**:
    - POST `/api/v1/2fa/setup` - Initialize 2FA setup (returns secret + QR)
    - POST `/api/v1/2fa/verify-setup` - Verify token and enable 2FA
    - POST `/api/v1/2fa/send-email-otp` - Send OTP code via email (fallback)
    - POST `/api/v1/2fa/verify-email-otp` - Verify email OTP code
    - GET `/api/v1/2fa/backup-codes` - Get backup codes (requires password)
    - POST `/api/v1/2fa/regenerate-backup-codes` - Generate new backup codes
    - PUT `/api/v1/2fa/toggle-email-fallback` - Enable/disable email OTP fallback
    - DELETE `/api/v1/2fa` - Disable 2FA (requires password)
  - **Authentication**: All endpoints require valid JWT access token
  - **Rate Limiting**: Email OTP max 3 sends per hour per account
  - **Acceptance**: Full 2FA management works, email OTP fallback functional, secure
  - **Test**: Integration tests for 2FA lifecycle including email OTP

- [ ] **TODO**: Implement JWT authentication middleware
  - **File**: `backend/api/middleware/auth_middleware.py`
  - **Middleware**: FastAPI dependency `get_current_user(token: str)` 
  - **Validation**: Verify JWT signature, check expiry, validate session exists
  - **Error Handling**: Return 401 for invalid/expired tokens, 403 for inactive users
  - **Usage**: Add `user: User = Depends(get_current_user)` to protected endpoints
  - **Acceptance**: Middleware protects endpoints, rejects invalid tokens
  - **Test**: Test valid tokens, expired tokens, tampered tokens, revoked sessions

- [ ] **TODO**: Implement rate limiting middleware for auth endpoints
  - **File**: `backend/api/middleware/rate_limit.py`
  - **Strategy**: Token bucket algorithm, keyed by IP address
  - **Limits**: 5 login attempts per 15min, 10 registration attempts per hour
  - **Storage**: In-memory dict for now (replace with Redis in production)
  - **Response**: 429 Too Many Requests with Retry-After header
  - **Acceptance**: Rate limits enforced, prevents brute force attacks
  - **Test**: Trigger rate limits, verify 429 responses, test reset timing

#### Frontend Authentication UI

- [ ] **TODO**: Create login page (/login)
  - **File**: `frontend/src/pages/Login.tsx`
  - **Form**: Email input, password input (with show/hide toggle), remember me checkbox
  - **Validation**: Client-side email/password format validation
  - **Flow**: Submit → If 2FA enabled → redirect to 2FA page, else → redirect to dashboard
  - **Error Handling**: Display auth errors (invalid credentials, account locked, etc.)
  - **Design**: Clean, modern, dark mode support, Headless UI components
  - **Acceptance**: Login works, validates input, handles errors gracefully
  - **Test**: Component tests, E2E test login flow

- [ ] **TODO**: Create registration page (/register?token=xxx)
  - **File**: `frontend/src/pages/Register.tsx`
  - **Flow**: Extract invite token from URL → Validate token → Display pre-filled email (readonly)
  - **Form**: Email (readonly), password, confirm password, terms acceptance checkbox
  - **Validation**: Real-time password strength indicator, match confirmation
  - **Password Rules**: Display requirements (12+ chars, uppercase, lowercase, number, special)
  - **Submit**: Create account → Auto-login → Redirect to dashboard
  - **Error Handling**: Invalid/expired invite token, email already registered
  - **Acceptance**: Invite-based registration works, validates input, displays clear feedback
  - **Test**: Component tests, E2E test invite redemption flow

- [ ] **TODO**: Create 2FA verification page (/login/2fa)
  - **File**: `frontend/src/pages/TwoFactorVerify.tsx`
  - **Form**: 6-digit TOTP code input (auto-focus, auto-submit on 6 digits)
  - **Alternatives**: 
    - "Use backup code" link → Switch to backup code input
    - "Send code to email" button → Request email OTP (rate limited: 3/hour)
  - **Countdown**: Display time remaining for current TOTP code (30s window)
  - **Email OTP**: Show "Code sent!" confirmation, switch to email OTP input mode
  - **Error Handling**: Invalid code, expired code, rate limiting, email send failures
  - **Flow**: Verify code → Redirect to dashboard with auth tokens
  - **Acceptance**: 2FA verification works, backup codes and email OTP supported
  - **Test**: Component tests, E2E test 2FA flow with TOTP/backup/email OTP

- [ ] **TODO**: Create 2FA setup page (/settings/2fa)
  - **File**: `frontend/src/pages/TwoFactorSetup.tsx`
  - **Display**: Show QR code for scanning with authenticator app
  - **Manual Entry**: Display secret key for manual entry in app
  - **Verification**: Input field for test TOTP code to confirm setup
  - **Backup Codes**: Display 10 backup codes after successful setup, download/print options
  - **Warning**: Emphasize importance of saving backup codes
  - **Acceptance**: Setup flow works, QR scannable, backup codes displayed
  - **Test**: Component tests, E2E test setup flow

- [ ] **TODO**: Create 2FA management section in settings
  - **File**: `frontend/src/pages/Settings.tsx` - Add 2FA section
  - **Status Display**: Show whether 2FA is enabled/disabled
  - **Actions**: Enable 2FA, disable 2FA (requires password), regenerate backup codes
  - **Email Fallback Toggle**: Enable/disable email OTP fallback option
  - **View Backup Codes**: Modal requiring password re-entry to view codes
  - **Acceptance**: Full 2FA management available, email fallback configurable, secure password re-entry
  - **Test**: Component tests, E2E test management actions

- [ ] **TODO**: Create user invite management UI in settings
  - **File**: `frontend/src/pages/Settings.tsx` - Add User Management section (admin only)
  - **Invite Form**: Email input field, "Send Invite" button
  - **Pending Invites**: Table showing email, invited by, created date, expires date, status
  - **Actions**: Copy invite link (modal with copyable URL), cancel invite (confirmation dialog)
  - **Display**: Show invite link in modal after creation (no auto-email initially)
  - **Note**: Admin manually shares invite link with user until SMTP configured
  - **Acceptance**: Invite creation works, link copyable, pending list displays, cancellation works
  - **Test**: Component tests, E2E test invite workflow

- [ ] **TODO**: Implement auth state management with Zustand
  - **File**: `frontend/src/stores/authStore.ts`
  - **State**: `{ user: User | null, accessToken: string | null, isAuthenticated: bool }`
  - **Actions**: `login(tokens)`, `logout()`, `setUser(user)`, `refreshToken()`
  - **Persistence**: Store refresh token in httpOnly cookie (via API), access token in memory only
  - **Auto-Refresh**: Refresh access token 2min before expiry using refresh token
  - **Acceptance**: Auth state persists across page reloads, tokens managed securely
  - **Test**: Test state updates, token refresh, logout clears state

- [ ] **TODO**: Create ProtectedRoute component for authenticated pages
  - **File**: `frontend/src/components/ProtectedRoute.tsx`
  - **Logic**: Check auth state → If authenticated, render children, else redirect to /login
  - **Loading State**: Show loading spinner while checking auth
  - **Usage**: Wrap all protected pages (dashboard, settings, etc.)
  - **Acceptance**: Protects pages from unauthenticated access
  - **Test**: Test authenticated/unauthenticated access, redirect behavior

- [ ] **TODO**: Implement automatic token refresh mechanism
  - **File**: `frontend/src/utils/tokenRefresh.ts`
  - **Strategy**: Set interval to check token expiry every 60s
  - **Refresh Trigger**: When access token expires in <2min, call refresh endpoint
  - **Error Handling**: If refresh fails, logout user and redirect to login
  - **Acceptance**: Tokens refresh transparently, sessions stay active
  - **Test**: Test refresh timing, error handling, logout on refresh failure

- [ ] **TODO**: Create email verification page (/verify-email)
  - **File**: `frontend/src/pages/VerifyEmail.tsx`
  - **Flow**: Extract token from URL → Call verify endpoint → Show success/error
  - **Success**: Display success message, redirect to login after 3s
  - **Error**: Display error message, offer resend verification email
  - **Acceptance**: Email verification works, clear feedback
  - **Test**: E2E test verification flow

- [ ] **TODO**: Add logout functionality to navigation
  - **File**: `frontend/src/components/Navigation.tsx`
  - **Button**: User menu dropdown with "Logout" option
  - **Action**: Call logout endpoint → Clear auth state → Redirect to login
  - **Confirmation**: Optional "Are you sure?" modal for accidental clicks
  - **Acceptance**: Logout works, clears tokens, redirects properly
  - **Test**: Test logout action, verify state cleared

#### Security & Testing

- [ ] **TODO**: Implement comprehensive auth security tests
  - **File**: `backend/tests/security/test_auth_security.py`
  - **Tests**:
    - Password hashing security (bcrypt rounds, no plaintext storage)
    - JWT token tampering detection
    - Session hijacking prevention
    - Rate limiting effectiveness
    - 2FA secret encryption
    - SQL injection prevention in auth queries
  - **Acceptance**: All security tests pass, no vulnerabilities
  - **Test**: Run security test suite, verify all attack vectors blocked

- [ ] **TODO**: Create E2E authentication flow tests
  - **File**: `frontend/tests/e2e/auth.spec.ts`
  - **Tests**:
    - Full registration → email verification → login flow
    - Login → dashboard navigation
    - 2FA setup → verify TOTP → login with 2FA
    - Backup code usage
    - Logout → verify protected page access denied
    - Token refresh during active session
  - **Acceptance**: All E2E flows work end-to-end
  - **Test**: Run E2E test suite, verify coverage

- [ ] **TODO**: Document authentication architecture and security measures
  - **File**: `docs/architecture/decision-84-user-authentication-2fa.md` (COMPLETED)
  - **Content**: Architecture overview, security considerations, token lifecycle, 2FA flow, threat model
  - **Diagrams**: Authentication flow diagram, 2FA setup flow, session management
  - **Acceptance**: Complete documentation for developers and security review
  - **Review**: Security audit by team lead

#### SMTP Email Service Integration (Phase 2)

- [ ] **TODO**: Create email_settings table for SMTP configuration
  - **Migration**: `alembic/versions/021_create_email_settings.py`
  - **Schema**: id (UUID), smtp_host, smtp_port, smtp_username, smtp_password_encrypted (Fernet), from_email, from_name, use_tls (default true), is_enabled (default false), updated_at
  - **Encryption**: Use Fernet encryption for SMTP password, separate key from other secrets
  - **Purpose**: Store configurable SMTP settings for email sending
  - **Acceptance**: Settings stored encrypted, single row enforced (config singleton)
  - **Test**: Store/retrieve settings, verify password encryption

- [ ] **TODO**: Create email template system (MUST COMPLETE BEFORE EmailService)
  - **Directory**: `backend/templates/emails/`
  - **Templates**:
    - `invite.html` / `invite.txt` - User invitation email
    - `otp.html` / `otp.txt` - 2FA OTP code email
    - `security_alert.html` / `security_alert.txt` - Security notifications
    - `welcome.html` / `welcome.txt` - Welcome email after signup (optional)
  - **Variables**: Jinja2 templating with {{user_name}}, {{invite_link}}, {{otp_code}}, etc.
  - **Styling**: Inline CSS for email client compatibility, responsive design
  - **Acceptance**: Templates render correctly, variables inject properly, mobile-friendly
  - **Test**: Render templates with test data, verify output HTML/text
  - **Example Template (invite.html)**:
    ```html
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>You're invited to TheAppApp!</h1>
        <p>Hi there,</p>
        <p>{{inviter_name}} has invited you to join TheAppApp. Click the button below to create your account:</p>
        <p><a href="{{invite_link}}" class="button">Accept Invitation</a></p>
        <p>Or copy this link: {{invite_link}}</p>
        <p>This invitation expires in 48 hours.</p>
      </div>
    </body>
    </html>
    ```
  - **Example Template (invite.txt)**:
    ```
    You're invited to TheAppApp!
    
    Hi there,
    
    {{inviter_name}} has invited you to join TheAppApp.
    
    Click this link to create your account:
    {{invite_link}}
    
    This invitation expires in 48 hours.
    
    ---
    TheAppApp Team
    ```

- [ ] **TODO**: Implement EmailService for SMTP email sending (DEPENDS ON: email templates)
  - **File**: `backend/services/email_service.py`
  - **Class**: `EmailService` with methods:
    - `send_invite_email(to: str, invite_link: str, inviter_name: str) -> bool` - Send invite email
    - `send_otp_email(to: str, otp_code: str) -> bool` - Send 2FA OTP code
    - `send_security_alert(to: str, alert_type: str, details: dict) -> bool` - Send security notification
    - `test_connection() -> bool` - Test SMTP connection
  - **Library**: Use Python `smtplib` with TLS support
  - **Templates**: Load from `backend/templates/emails/` using Jinja2
  - **Queue**: Background thread for async email sending (don't block requests)
  - **Error Handling**: Log failures, return success/failure, retry logic (max 3 attempts)
  - **Acceptance**: Emails send successfully, templates render correctly, queue works
  - **Test**: Unit tests with mock SMTP, integration tests with real SMTP test server
  - **Example Usage**:
    ```python
    email_service = EmailService()
    success = await email_service.send_invite_email(
        to="user@example.com",
        invite_link="https://app.example.com/register?token=abc123",
        inviter_name="John Doe"
    )
    ```

- [ ] **TODO**: Create SMTP settings API endpoints
  - **File**: `backend/api/routes/email_settings.py`
  - **Endpoints**:
    - GET `/api/v1/email/settings` - Get current SMTP config (admin only)
    - PUT `/api/v1/email/settings` - Update SMTP config (admin only)
    - POST `/api/v1/email/test` - Test SMTP connection (admin only)
    - POST `/api/v1/email/test-send` - Send test email (admin only)
  - **Payload**: `{"smtp_host": "smtp.gmail.com", "smtp_port": 587, ...}`
  - **Security**: Encrypt password before storing, mask password in responses
  - **Acceptance**: Config CRUD works, test connection works, secure
  - **Test**: Integration tests for all endpoints

- [ ] **TODO**: Create SMTP configuration UI in frontend settings
  - **File**: `frontend/src/pages/Settings.tsx` - Add Email Configuration section (admin only)
  - **Form Fields**:
    - SMTP Host (text input)
    - SMTP Port (number input, default 587)
    - Username (text input)
    - Password (password input, show/hide toggle)
    - From Email (text input, with validation)
    - From Name (text input)
    - Use TLS (toggle, default on)
    - Enable Email Service (toggle, default off)
  - **Actions**:
    - "Test Connection" button - Test SMTP settings without saving
    - "Send Test Email" button - Send test email to admin's address
    - "Save Settings" button - Save and enable email service
  - **Status Indicator**: Show connection status (connected, disconnected, error)
  - **Help Text**: Instructions for Gmail, Outlook, custom SMTP setup
  - **Acceptance**: Config UI works, test buttons functional, settings save correctly
  - **Test**: Component tests, E2E test SMTP configuration flow

- [ ] **TODO**: Add email queue monitoring and logs
  - **File**: `backend/services/email_queue.py`
  - **Functionality**:
    - Queue emails for background sending (asyncio queue or thread pool)
    - Track send status (pending, sent, failed)
    - Retry failed emails (max 3 attempts with exponential backoff)
    - Store send logs in database (email_logs table)
  - **Table**: `email_logs` - id, to_email, subject, template, status, sent_at, error_message
  - **Acceptance**: Queue processes emails, retries work, logs persisted
  - **Test**: Test queue processing, retry logic, error handling

- [ ] **TODO**: Create email logs viewer UI in settings
  - **File**: `frontend/src/pages/Settings.tsx` - Add Email Logs section (admin only)
  - **Display**: Table showing recent emails (last 100), filterable by status/recipient
  - **Columns**: Recipient, Subject, Template, Status, Sent At, Error (if failed)
  - **Actions**: Refresh logs, filter by status, search by recipient
  - **Real-time Updates**: Auto-refresh every 30s when page open
  - **Acceptance**: Logs display correctly, filters work, updates automatically
  - **Test**: Component tests, E2E test log viewing

- [ ] **TODO**: Update invite system to auto-send emails when SMTP enabled
  - **File**: `backend/services/auth_service.py` - Update invite creation
  - **Logic**: When admin creates invite AND email service enabled → Auto-send invite email
  - **Fallback**: If email disabled or send fails → Show copyable link in UI
  - **Status**: Track whether invite email was sent successfully
  - **Acceptance**: Auto-send works when enabled, fallback to manual link works
  - **Test**: Test with email enabled/disabled, test send failures

- [ ] **TODO**: Add email OTP automatic sending
  - **File**: `backend/services/two_factor_service.py` - Update `send_email_otp()`
  - **Logic**: Generate OTP → Send via EmailService → Store OTP with expiry
  - **Rate Limiting**: Max 3 email OTPs per hour per account
  - **Error Handling**: If email fails, return error to user (don't silently fail)
  - **Acceptance**: Email OTP sends automatically, rate limiting enforced
  - **Test**: Test email OTP flow, verify rate limiting

- [ ] **TODO**: Document email service setup and configuration
  - **File**: `docs/operations/email-service-setup.md`
  - **Content**:
    - Gmail SMTP setup instructions (App Passwords required)
    - Outlook/Office365 SMTP setup
    - Custom SMTP server setup
    - TLS/SSL configuration
    - Troubleshooting common issues
    - Rate limit considerations (Gmail: 500/day, etc.)
  - **Acceptance**: Complete setup guide for admins
  - **Review**: Test instructions with real Gmail/Outlook accounts

### 4.8 Archive System
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
