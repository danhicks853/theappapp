# Architecture Decision Catalog

**Total Decisions**: 82 (Decision 1-82)  
**Status**: All Approved & Documented  
**Implementation**: 0% (All TODO)

**Decision Range**:
- **Decisions 1-66**: Early architectural decisions (extracted from phase planning)
- **Decisions 67-82**: Detailed technical specifications (comprehensive documentation)

All decisions are now individual files in this directory for easy LLM parsing.

---

## 📖 Quick Reference for LLMs

### Finding a Decision
- **By Number**: `decision-[01-82]-*.md` in this directory (all 82 decisions)
- **By Topic**: See catalog below (decisions 1-66 are brief, 67-82 are detailed)
- **By Tracker Section**: Cross-referenced in development_tracker.md
- **Early Decisions**: Decisions 1-66 provide context, decisions 67-82 provide implementation details

### Reading a Decision
Each decision includes:
- **Status**: ✅ RESOLVED (all current decisions)
- **Context**: Why this decision was needed
- **Decision**: What was chosen and why
- **Implementation**: Code examples and specifications
- **Related**: Dependencies and connected systems
- **Testing**: How to validate implementation

---

## 🗂️ Decision Catalog

### Core Orchestrator & Coordination (5 decisions)

#### Decision 67: Orchestrator LLM Integration
**File**: `decision-67-orchestrator-llm-integration.md`  
**Tracker Refs**: Section 1.1.1 (10 tasks)  
**Summary**: How orchestrator uses LLM for reasoning, agent selection, and coordination  
**Key Decisions**:
- Moderate autonomy with user-configurable slider (low/medium/high)
- Full chain-of-thought reasoning for transparency
- Orchestrator-centric context management
- PM vetting workflow through specialist consultation

**Implementation Components**:
- `OrchestratorLLMClient` class
- Autonomy level configuration
- RAG-mediated context injection
- PM vetting service

---

#### Decision 70: Agent Collaboration Protocol
**File**: `decision-70-agent-collaboration-protocol.md`  
**Tracker Refs**: Section 1.3.1 (9 tasks)  
**Summary**: How agents request help from specialists through orchestrator  
**Key Decisions**:
- Orchestrator-routed collaboration (no direct agent-to-agent)
- Structured help request format
- 6 collaboration scenarios (security, API, debugging, etc.)
- Semantic loop detection with 0.85 similarity threshold

**Implementation Components**:
- `CollaborationOrchestrator` service
- Help request message format
- Collaboration tracking database
- Loop detection algorithm

---

#### Decision 74: Loop Detection Algorithm
**File**: `decision-74-loop-detection-algorithm.md`  
**Tracker Refs**: Section 1.4.1 (12 tasks)  
**Summary**: Detecting when agents are stuck in failure loops  
**Key Decisions**:
- Exact error message matching for task loops
- 3-strike threshold triggers human gate
- Semantic similarity for collaboration loops
- Progress evaluation with test metrics

**Implementation Components**:
- `LoopDetectionService` class
- Failure signature extraction
- Progress evaluator
- In-memory loop state tracking

---

#### Decision 76: Project State Recovery
**File**: `decision-76-project-state-recovery.md`  
**Tracker Refs**: Section 1.4.2 (8 tasks)  
**Summary**: Recovering project state after crashes or restarts  
**Key Decisions**:
- Automatic recovery on orchestrator startup
- File state scanning to detect progress
- LLM-based recovery evaluation
- 4 recovery decisions (continue/restart/next/human)

**Implementation Components**:
- `project_state` database table
- `FileStateScanner` service
- LLM recovery evaluation
- Manual resume API endpoint

---

#### Decision 80: Error Handling System
**File**: `decision-80-error-handling-system.md`  
**Tracker Refs**: Section 6.5 (10 tasks)  
**Summary**: Comprehensive error taxonomy and handling strategy  
**Key Decisions**:
- 5-tier error taxonomy (Critical/High/Medium/Low/Info)
- Standardized error response format
- Agent-specific error handling
- Error recovery strategies per tier

**Implementation Components**:
- Custom exception hierarchy
- Error response models
- Recovery middleware
- Error logging and tracking

---

### Knowledge & Learning (2 decisions)

#### Decision 68: RAG System Architecture
**File**: `decision-68-rag-system-architecture.md`  
**Tracker Refs**: Section 1.5 (11 tasks)  
**Summary**: How the system learns from past projects using RAG  
**Key Decisions**:
- Qdrant vector database for embeddings
- Orchestrator-mediated knowledge queries
- 3-stage ingestion (staging, review, production)
- Agent-specific knowledge embedding

**Implementation Components**:
- Qdrant integration
- Knowledge staging tables
- RAG query service
- Knowledge ingestion pipeline

---

#### Decision 69: Prompt Versioning System
**File**: `decision-69-prompt-versioning-system.md`  
**Tracker Refs**: Section 1.2.4 (11 tasks)  
**Summary**: Managing and versioning agent prompts  
**Key Decisions**:
- Semantic versioning (major.minor.patch)
- Independent versioning per agent type
- Fix-forward only (no rollbacks)
- A/B testing lab for prompt comparison

**Implementation Components**:
- `prompts` database table
- `PromptLoadingService` (auto-loading latest)
- `PromptManagementService` (versioning)
- A/B testing frontend

---

### Tool Ecosystem (3 decisions)

#### Decision 71: Tool Access Service (TAS)
**File**: `decision-71-tool-access-service.md`  
**Tracker Refs**: Section 2.3 (21 tasks)  
**Summary**: Permission system for agent tool usage  
**Key Decisions**:
- 4 privilege tiers (read-only, standard, elevated, admin)
- Role-based access control per agent type
- Request-approval flow for elevated operations
- Detailed audit logging

**Implementation Components**:
- `TASService` class
- Privilege enforcement middleware
- Tool catalog with permissions
- Approval workflow system

---

#### Decision 77: GitHub Specialist Agent
**File**: `decision-77-github-specialist-agent.md`  
**Tracker Refs**: Section 2.4 (13 tasks)  
**Summary**: Specialized agent for GitHub operations  
**Key Decisions**:
- OAuth 2.0 for user authorization
- 3 supported operations (create repo, create PR, merge PR)
- LLM-powered commit message generation
- Repository state tracking

**Implementation Components**:
- `GitHubSpecialistAgent` class
- OAuth integration
- GitHub API client
- Commit message templates

---

#### Decision 78: Docker Container Lifecycle
**File**: `decision-78-docker-container-lifecycle.md`  
**Tracker Refs**: Section 2.1 (13 tasks)  
**Summary**: Managing code execution containers  
**Key Decisions**:
- 8 language-specific golden images
- 30-minute container lifespan
- Resource limits (2GB RAM, 2 CPU cores)
- Automatic cleanup and monitoring

**Implementation Components**:
- `ContainerManager` service
- Golden image Dockerfiles
- Health check system
- Resource monitoring

---

### Database & API (2 decisions)

#### Decision 73: Frontend-Backend API
**File**: `decision-73-frontend-backend-api.md`  
**Tracker Refs**: Section 6.1 (14 tasks)  
**Summary**: REST + WebSocket API specification  
**Key Decisions**:
- FastAPI for REST endpoints
- WebSocket for real-time updates
- JWT authentication
- Standardized response format

**Implementation Components**:
- 20+ REST endpoints
- WebSocket server
- Authentication middleware
- API documentation (OpenAPI)

---

#### Decision 79: Database Schema
**File**: `decision-79-database-schema.md`  
**Tracker Refs**: Section 6.2 (20 tasks)  
**Summary**: Complete database schema with 16 migrations  
**Key Decisions**:
- PostgreSQL for relational data
- Qdrant for vector embeddings
- 16 Alembic migrations
- Comprehensive indexing strategy

**Implementation Components**:
- 16 database migrations (001-016)
- All table schemas
- Seed data scripts
- Index specifications

---

### Testing & Quality (1 decision)

#### Decision 72: LLM Testing Strategy
**File**: `decision-72-llm-testing-strategy.md`  
**Tracker Refs**: Section 6.6 (24 tasks)  
**Summary**: How to test LLM-powered components  
**Key Decisions**:
- AI-assisted testing with automated evaluation
- 3 testing levels (unit, integration, E2E)
- Test case generation from requirements
- Quality rubrics for reasoning evaluation

**Implementation Components**:
- Test case generator
- AI evaluator service
- Quality rubrics
- A/B testing framework

---

### User Features (3 decisions)

#### Decision 75: Cost Tracking System
**File**: `decision-75-cost-tracking-system.md`  
**Tracker Refs**: Section 4.1 (10 tasks)  
**Summary**: Tracking and displaying LLM costs  
**Key Decisions**:
- Real-time token logging to database
- Model-specific pricing table
- Cost dashboard with breakdowns
- Budget alerts

**Implementation Components**:
- `token_usage` table
- `model_pricing` table
- Cost calculation service
- Frontend dashboard

---

#### Decision 81: Project Cancellation Workflow
**File**: `decision-81-project-cancellation-workflow.md`  
**Tracker Refs**: Section 4.7 (8 tasks)  
**Summary**: Safely deleting projects and resources  
**Key Decisions**:
- Two-step confirmation (type project name)
- Complete resource destruction
- Orphan cleanup checks
- Audit trail retention

**Implementation Components**:
- Cancellation workflow service
- Resource cleanup logic
- Confirmation modal
- Audit logging

---

#### Decision 82: Meet the Team Page
**File**: `decision-82-meet-the-team-page.md`  
**Tracker Refs**: Section 4.8 (6 tasks)  
**Summary**: Easter egg page introducing all agents  
**Key Decisions**:
- Agent profile cards with personalities
- Interactive Q&A feature
- Hidden access method
- Humorous agent bios

**Implementation Components**:
- Frontend page component
- Agent profile data
- Q&A interaction system
- Easter egg trigger

---

## 📊 Decision Statistics

### Total Count
- **All Decisions**: 82 (decisions 1-82)
- **Early Decisions**: 66 (decisions 1-66, from phase planning)
- **Detailed Decisions**: 16 (decisions 67-82, comprehensive specs)

### By Phase Origin
- **Phase 1**: Decisions 1-12 (Foundation & Architecture)
- **Phase 2**: Decisions 13-27 (Tools & Integration)
- **Phase 3**: Decisions 28-36 (Development Workflow)
- **Phase 4**: Decisions 37-46 (Frontend & Monitoring)
- **Phase 5**: Decisions 47-55 (Deployment & Release)
- **Phase 6**: Decisions 56-66 (Technical Implementation)
- **Detailed Specs**: Decisions 67-82 (LLM-era comprehensive documentation)

### By Implementation Status
- **Documented**: 82/82 (100%)
- **Implemented**: 0/82 (0%)
- **Tested**: 0/82 (0%)

---

## 🔗 Cross-References

### Decisions with Heavy Dependencies

**Decision 67** (Orchestrator LLM) depends on:
- Decision 68 (RAG) - For knowledge queries
- Decision 69 (Prompts) - For prompt loading
- Decision 70 (Collaboration) - For agent routing
- Decision 74 (Loop Detection) - For failure handling

**Decision 71** (TAS) depends on:
- Decision 73 (API) - For approval endpoints
- Decision 79 (Database) - For permission storage

**Decision 79** (Database) is dependency for:
- All other decisions (provides data persistence)

### Decisions by Implementation Order

**Foundation (Build First)**:
1. Decision 79 - Database Schema
2. Decision 73 - Frontend-Backend API
3. Decision 67 - Orchestrator Core

**Core Systems**:
4. Decision 69 - Prompt Versioning
5. Decision 68 - RAG System
6. Decision 70 - Agent Collaboration
7. Decision 74 - Loop Detection
8. Decision 76 - State Recovery
9. Decision 80 - Error Handling

**Tool Ecosystem**:
10. Decision 71 - TAS
11. Decision 78 - Docker Containers
12. Decision 77 - GitHub Agent

**Testing & Features**:
13. Decision 72 - LLM Testing
14. Decision 75 - Cost Tracking
15. Decision 81 - Project Cancellation
16. Decision 82 - Meet the Team

---

## 🎯 How to Use This Catalog

### For LLMs Implementing Tasks

1. **Find your task** in `../planning/development_tracker.md`
2. **Note the decision reference** (e.g., "Decision 67")
3. **Open the decision file** from this directory
4. **Read complete context** before implementing
5. **Cross-check dependencies** in "Related" sections

### For Understanding System Design

1. **Start with Decision 67** (Orchestrator) - the core
2. **Read Decision 79** (Database) - the foundation
3. **Branch into your area** (Tools, Frontend, etc.)
4. **Check cross-references** for complete picture

### For Debugging Issues

1. **Identify the system** having issues
2. **Find its decision** in this catalog
3. **Review implementation specs** in decision doc
4. **Check related decisions** for interactions
5. **Verify against test strategy** in decision

---

## 📝 Decision Document Template

All decisions follow this structure:

```markdown
# Decision XX: Title

## Status
✅ RESOLVED
Date: [date]
Priority: [P0/P1/P2]

## Context
[Why this decision was needed]

## Decision
[What was chosen, with rationale]

## Implementation
[Code examples, specs, components]

## Related Decisions
[Dependencies and connections]

## Testing Strategy
[How to validate]

## Open Questions
[Future considerations]
```

---

## ⚠️ Important Notes

### All Decisions Are Current
Every decision in this catalog is:
- ✅ Approved and finalized
- ✅ Ready for implementation
- ✅ Cross-referenced in tracker
- ✅ Complete with specifications

### No Code Exists Yet
- All decisions documented
- All tasks specified
- Zero implementation complete
- Ready to build from scratch

### Reference Pattern
Tasks reference decisions like:
```markdown
**Reference**: `docs/architecture/decision-67-orchestrator-llm-integration.md`
```

Always check the referenced decision before implementing.

---

**Last Updated**: November 1, 2025  
**Status**: Complete - All 16 Decisions Documented  
**Ready for**: Immediate Implementation
