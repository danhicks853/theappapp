# Phase 1 Testing Plan

**Date**: November 2, 2025  
**Objective**: Comprehensive testing of all Phase 1 systems before Phase 2  
**Coverage Goal**: High coverage (>80%) with integration focus  

---

## Testing Strategy

### 1. Unit Tests
Individual component testing in isolation with mocks

### 2. Integration Tests
Cross-system testing with real dependencies (database, etc.)

### 3. LLM Testing
Following our testing philosophy:
- Mock LLM responses for deterministic tests
- Test prompt structure and formatting
- Test error handling and fallbacks
- Validate response parsing

---

## Test Coverage by System

### ✅ Already Tested
- [x] Loop Detection (21 unit + 7 integration)
- [x] RAG System (10 integration)
- [x] Cross-Project Learning (8 integration)

### 🔨 Needs Testing

#### **Database & Migrations**
- [x] 19 migrations exist
- [ ] Migration rollback tests
- [ ] Schema validation tests

#### **API Endpoints** (34 endpoints)
- [ ] Settings endpoints (API keys, agent models)
- [ ] Gate endpoints (create, approve, deny, list)
- [ ] Prompt endpoints (CRUD, versions, A/B tests)
- [ ] Specialist endpoints (CRUD)
- [ ] Project endpoints (CRUD)
- [ ] Task endpoints (CRUD)
- [ ] Store endpoints

#### **Services**
- [ ] GateManager (creation, approval, denial)
- [ ] CollaborationOrchestrator (routing, loop detection)
- [ ] TimeoutMonitor (detection, gate creation)
- [ ] FailureSignature (extraction, classification)
- [ ] ProgressEvaluator (metrics, evaluation)
- [ ] PromptManagementService (versioning, A/B)
- [ ] KnowledgeCaptureService (4 capture types)
- [ ] CheckpointEmbeddingService (batch processing)
- [ ] AgentFactory (agent creation)
- [ ] Orchestrator (task delegation, goal proximity)

#### **Cross-System Integration**
- [ ] Gate → Collaboration flow
- [ ] Loop Detection → Gate creation
- [ ] Timeout → Gate creation
- [ ] Knowledge capture → Checkpoint embedding → RAG query
- [ ] Orchestrator → Agent → Task → Gate
- [ ] Collaboration → Knowledge capture
- [ ] Failure → Signature → Knowledge

---

## Test Files to Create

### Unit Tests
1. `test_gate_manager.py` - Gate CRUD, approval workflow
2. `test_collaboration_orchestrator.py` - Routing, scenarios
3. `test_timeout_monitor.py` - Timeout detection, stats
4. `test_failure_signature.py` - Error classification, hashing
5. `test_progress_evaluator.py` - Metrics evaluation
6. `test_prompt_management.py` - Versioning, A/B testing
7. `test_agent_factory.py` - Agent instantiation
8. `test_orchestrator.py` - Task delegation, LLM calls

### Integration Tests
1. `test_api_endpoints.py` - All 34 API endpoints
2. `test_gate_workflow_integration.py` - Full gate lifecycle
3. `test_collaboration_integration.py` - Agent-to-agent flow
4. `test_failure_recovery_integration.py` - Timeout → Loop → Gate
5. `test_knowledge_pipeline_integration.py` - Capture → Embed → Query
6. `test_orchestrator_integration.py` - Full orchestration flow
7. `test_database_migrations.py` - Migration up/down

### LLM Tests
1. `test_llm_goal_proximity.py` - LLM evaluation mocking
2. `test_llm_prompt_formatting.py` - RAG context injection
3. `test_llm_agent_prompts.py` - Built-in agent prompts
4. `test_llm_semantic_similarity.py` - Embedding mocks

---

## Prerequisites

### 1. Database Setup
```bash
# Start Docker services
docker-compose up -d postgres qdrant

# Run migrations
cd backend
alembic upgrade head
```

### 2. Test Database
```bash
# Create test database
docker exec -it theappapp-postgres psql -U postgres -c "CREATE DATABASE theappapp_test;"
```

### 3. Environment Variables
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:55432/theappapp_test
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=test_key_for_mocking
```

---

## Running Tests

### All Tests
```bash
pytest backend/tests/ -v --cov=backend --cov-report=html
```

### Unit Tests Only
```bash
pytest backend/tests/unit/ -v
```

### Integration Tests Only
```bash
pytest backend/tests/integration/ -v
```

### Specific System
```bash
pytest backend/tests/unit/test_gate_manager.py -v
pytest backend/tests/integration/test_gate_workflow_integration.py -v
```

### With Coverage Report
```bash
pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term
```

---

## Success Criteria

- ✅ All migrations run successfully
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Coverage > 80% for critical paths
- ✅ No blocking errors for Phase 2 development
- ✅ Cross-system integration verified
- ✅ LLM functionality mocked and tested

---

## Priority Order

### Priority 1 (Critical Path)
1. Database migrations test
2. API endpoints test (health, basic CRUD)
3. Gate manager tests
4. Orchestrator basic tests

### Priority 2 (Core Functionality)
1. Collaboration orchestrator tests
2. Timeout monitor tests
3. Knowledge capture tests
4. Cross-system integration tests

### Priority 3 (Enhanced Features)
1. LLM testing
2. Progress evaluator tests
3. Prompt management tests
4. Full coverage optimization

---

## Test Data

### Mock Agents
```python
MOCK_AGENTS = {
    "backend_developer": {"name": "Backend Dev", "model": "gpt-4"},
    "frontend_developer": {"name": "Frontend Dev", "model": "gpt-4"},
    "qa_engineer": {"name": "QA Engineer", "model": "gpt-4-turbo"}
}
```

### Mock Projects
```python
MOCK_PROJECTS = {
    "test_proj_1": {"name": "Test Project 1", "status": "active"},
    "test_proj_2": {"name": "Test Project 2", "status": "completed"}
}
```

### Mock Tasks
```python
MOCK_TASKS = {
    "task_1": {"description": "Implement API", "status": "pending"},
    "task_2": {"description": "Write tests", "status": "in_progress"}
}
```

---

## Notes

- Frontend testing deferred to Phase 4
- E2E project tests require Phase 2 (TAS, tools)
- Focus on backend stability and cross-system integration
- Use pytest fixtures for common setup
- Mock external APIs (OpenAI, etc.)
- Use real database for integration tests
