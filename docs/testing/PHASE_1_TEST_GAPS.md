# Phase 1 Testing Gaps - Action Plan

**Date**: November 2, 2025  
**Status**: Identified critical test coverage gaps  
**Priority**: Must fix before Phase 2  

---

## 🚨 Critical Gaps Identified

### **1. Missing Unhappy Path Testing**

**Problem**: Tests only cover success scenarios (happy path)

**Impact**: Production errors won't be caught

**Missing Error Scenarios:**
- [ ] Database connection failures
- [ ] Invalid API input (400 errors)
- [ ] Authentication/authorization failures (401/403)
- [ ] Resource not found (404)
- [ ] Conflict errors (409)
- [ ] Rate limiting (429)
- [ ] Internal server errors (500)
- [ ] Timeout errors (504)
- [ ] Malformed JSON
- [ ] SQL injection attempts
- [ ] XSS attempts in inputs
- [ ] Concurrent modification conflicts
- [ ] Disk full scenarios
- [ ] Memory exhaustion
- [ ] Network partitions

---

### **2. Untested Phase 1 Systems**

**Problem**: Major systems have zero test coverage

**Missing Tests:**

#### **Prompt Versioning System** (0% coverage)
- [ ] Version creation (MAJOR.MINOR.PATCH)
- [ ] Version comparison
- [ ] A/B test creation
- [ ] A/B test traffic split
- [ ] Variant performance tracking
- [ ] Rollback to previous version
- [ ] Version conflict handling

#### **Built-In Agents** (0% coverage)
- [ ] AgentFactory instantiation
- [ ] 11 agent prompt loading
- [ ] Agent configuration
- [ ] Prompt template rendering
- [ ] Agent type validation

#### **AI Assistant** (0% coverage)
- [ ] Prompt improvement suggestions
- [ ] Variant generation
- [ ] Quality scoring
- [ ] Integration with prompt editor

#### **Timeout Monitor** (0% coverage)
- [ ] Task monitoring start/stop
- [ ] Timeout detection
- [ ] Gate creation on timeout
- [ ] Stats tracking
- [ ] Concurrent task monitoring

#### **Progress Evaluator** (0% coverage)
- [ ] Baseline setting
- [ ] Progress detection (with tests)
- [ ] Progress detection (without tests)
- [ ] File change tracking
- [ ] Dependency tracking
- [ ] Metrics calculation

#### **Orchestrator** (0% coverage)
- [ ] Task delegation
- [ ] Agent selection
- [ ] Goal proximity evaluation
- [ ] State management
- [ ] LLM interaction
- [ ] Error recovery

#### **Collaboration Protocol** (10% coverage)
- [ ] Request routing
- [ ] Scenario matching
- [ ] Response handling
- [ ] Loop detection (semantic)
- [ ] Metrics tracking
- [ ] Full lifecycle workflow

#### **Qdrant Setup** (0% coverage)
- [ ] Collection creation
- [ ] Index creation
- [ ] Vector insertion
- [ ] Configuration validation

#### **Knowledge Cleanup Job** (0% coverage)
- [ ] Cleanup execution
- [ ] Retention policy (365 days)
- [ ] Qdrant deletion
- [ ] PostgreSQL deletion
- [ ] Stats reporting

---

### **3. Missing LLM/Tribunal Testing**

**Problem**: No implementation of two-stage LLM testing philosophy

**Required Implementation:**

#### **Stage 1: Rubric Validation** (100% missing)
```python
# test_llm_rubric_validation.py - NEW FILE NEEDED

class TestOrchestratorLLMRubric:
    def test_goal_proximity_response_structure(self):
        """Validate LLM response has required fields."""
        # Call orchestrator.evaluate_goal_proximity()
        # Assert response has: proximity_score, reasoning, evidence, confidence
        # Assert proximity_score is float 0-1
        # Assert confidence is float 0-1
        # Assert reasoning is non-empty string
        
    def test_goal_proximity_handles_malformed_response(self):
        """Test graceful degradation on bad LLM output."""
        # Mock LLM returning invalid JSON
        # Assert fallback to heuristic evaluation
        # Assert error logged but not raised
        
class TestPromptAssistantLLMRubric:
    def test_improvement_suggestion_structure(self):
        """Validate AI assistant output structure."""
        # Should have: suggestions[], confidence, reasoning
        
    def test_variant_generation_structure(self):
        """Validate variant generation output."""
        # Should have: variant_text, changes[], rationale
```

#### **Stage 2: AI Panel (Tribunal)** (100% missing)
```python
# test_llm_tribunal.py - NEW FILE NEEDED

class TestLLMTribunal:
    """3-judge consensus panel for semantic quality."""
    
    def test_orchestrator_goal_proximity_quality(self):
        """Tribunal evaluates goal proximity reasoning."""
        # Judge 1: Logical consistency (is reasoning sound?)
        # Judge 2: Completeness (covers all aspects?)
        # Judge 3: Accuracy (matches actual state?)
        # Requires ≥80% confidence consensus
        
    def test_prompt_improvement_quality(self):
        """Tribunal evaluates AI assistant suggestions."""
        # Judge 1: Instruction adherence
        # Judge 2: Code quality
        # Judge 3: Security awareness
        
    def test_collaboration_response_quality(self):
        """Tribunal evaluates specialist responses."""
        # Judge 1: Technical accuracy
        # Judge 2: Completeness
        # Judge 3: Actionability
```

#### **Golden Dataset** (0% exists)
- [ ] Create `backend/tests/fixtures/golden_llm_responses.json`
- [ ] 10+ successful goal proximity evaluations
- [ ] 10+ successful AI assistant interactions
- [ ] 10+ successful collaboration responses
- [ ] Store in Qdrant for regression testing

---

### **4. Docker Integration Testing**

**Problem**: Tests use mocks instead of real Docker services

**Current**: PostgreSQL ✓, Qdrant ❌, Full stack ❌

**Required Implementation:**

#### **Real Qdrant Testing**
```python
# conftest.py additions needed

@pytest.fixture(scope="session")
def qdrant_client():
    """Real Qdrant client for integration tests."""
    from qdrant_client import QdrantClient
    
    client = QdrantClient(host="localhost", port=6333)
    
    # Create test collection
    from backend.services.qdrant_setup import QdrantSetup
    setup = QdrantSetup(client)
    setup.create_knowledge_collection(recreate=True)
    
    yield client
    
    # Cleanup
    try:
        client.delete_collection("helix_knowledge")
    except:
        pass
```

#### **Full Stack Testing**
```bash
# scripts/run_integration_tests.sh - NEW FILE NEEDED

#!/bin/bash

# 1. Build Docker images
docker-compose build

# 2. Start all services
docker-compose up -d

# 3. Wait for services
sleep 10

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Seed test data
docker-compose exec backend python scripts/seed_test_data.py

# 6. Run integration tests
docker-compose exec backend pytest backend/tests/integration/ -v

# 7. Cleanup
docker-compose down -v
```

#### **Seed Test Data**
```python
# scripts/seed_test_data.py - NEW FILE NEEDED

def seed_test_data():
    """Seed database with test data for integration tests."""
    
    # Specialists
    create_specialists([
        "backend_developer",
        "frontend_developer", 
        "qa_engineer",
        # ... all 11
    ])
    
    # Prompts
    create_prompts_for_all_agents()
    
    # Sample projects
    create_sample_projects(count=5)
    
    # Sample knowledge
    create_sample_knowledge(count=20)
    
    # Sample gates
    create_sample_gates(count=10)
```

---

## 📊 Coverage Targets vs Actual

| Category | Target | Actual | Gap |
|----------|--------|--------|-----|
| **Unit Tests** | ≥90% | ~60% | -30% |
| **Integration** | ≥75% | ~40% | -35% |
| **LLM Rubric** | 100% | 0% | -100% |
| **LLM Tribunal** | 100% | 0% | -100% |
| **Unhappy Path** | ≥50% | ~10% | -40% |
| **Docker Integration** | 100% | ~30% | -70% |

---

## 🎯 Action Plan

### **Priority 1: Critical (Block Phase 2)**
1. [ ] Add unhappy path tests for all API endpoints
2. [ ] Implement real Qdrant integration tests
3. [ ] Test Orchestrator LLM interactions
4. [ ] Test Timeout Monitor
5. [ ] Test Progress Evaluator

### **Priority 2: Important (Before Production)**
1. [ ] Implement LLM Rubric validation
2. [ ] Implement AI Tribunal framework
3. [ ] Create golden dataset
4. [ ] Test Collaboration Protocol fully
5. [ ] Test Prompt Versioning
6. [ ] Test Built-In Agents
7. [ ] Test AI Assistant

### **Priority 3: Nice to Have**
1. [ ] Full Docker stack testing
2. [ ] Load testing
3. [ ] Chaos engineering
4. [ ] Performance benchmarks

---

## 🔧 Files to Create

### **New Test Files** (10 files)
1. `test_unhappy_paths.py` - Error scenario testing
2. `test_timeout_monitor.py` - Timeout detection
3. `test_progress_evaluator.py` - Progress metrics
4. `test_orchestrator.py` - Core orchestration
5. `test_orchestrator_llm.py` - LLM interactions
6. `test_prompt_versioning.py` - Version management
7. `test_built_in_agents.py` - Agent factory
8. `test_ai_assistant.py` - Prompt improvements
9. `test_llm_rubric.py` - Stage 1 validation
10. `test_llm_tribunal.py` - Stage 2 evaluation

### **New Infrastructure** (4 files)
1. `seed_test_data.py` - Database seeding
2. `run_integration_tests.sh` - Full stack testing
3. `golden_llm_responses.json` - Golden dataset
4. `llm_tribunal_framework.py` - 3-judge system

---

## 🎓 Testing Philosophy Compliance

**Current**: ❌ Not Following Philosophy

**Violations:**
- ❌ LLM testing not implemented (Decision 72)
- ❌ TestContainers pattern not used
- ❌ Coverage below 90% threshold
- ❌ No tribunal pattern
- ❌ No golden dataset
- ❌ Insufficient unhappy path coverage

**To Comply:**
- [ ] Follow testing_philosophy.md strictly
- [ ] Implement two-stage LLM testing
- [ ] Use real Docker services
- [ ] Achieve 90%+ branch coverage
- [ ] Test all error scenarios
- [ ] Document test patterns

---

## 📈 Estimated Effort

- **Priority 1**: 6-8 hours
- **Priority 2**: 10-12 hours
- **Priority 3**: 4-6 hours
- **Total**: ~20-26 hours

---

## ✅ Success Criteria

- [ ] All API endpoints have unhappy path tests
- [ ] All Phase 1 systems have >90% coverage
- [ ] LLM rubric validation implemented
- [ ] AI Tribunal framework working
- [ ] Golden dataset created (30+ examples)
- [ ] Real Qdrant integration tests passing
- [ ] Full Docker stack tests passing
- [ ] No test failures
- [ ] Coverage >90% overall

---

**Status**: Gaps identified, action plan created  
**Next Step**: Implement Priority 1 items
