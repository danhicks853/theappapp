# Phase 2: Tool & Integration Planning

## Decision Tracking
*This document captures our decisions and rationale for Phase 2 deliverables*

---

## 1. Tool Ecosystem Definition

### Questions to Answer:
- What specific tools does each agent need access to?
- How do we sandbox code execution safely?
- What web search capabilities are needed?
- How do we handle file system access and permissions?

### Decision Log:

**✅ DECISION 13: Tool Access Matrix**
- **Choice**: Previously defined in Phase 1 Decision 8 - no changes needed
- **Implementation**: Principle of least privilege with specialist isolation
- **Date**: Oct 31, 2025

**✅ DECISION 14: Code Execution Sandboxing**
- **Choice**: Docker-based multi-language containers
- **Implementation**: 
  - Linux containers for Python, Node.js, Java, Go, etc.
  - Windows containers for PowerShell, .NET
  - Resource limits (CPU, memory) but no artificial time limits
  - Orchestrator handles timeouts naturally via progress monitoring
  - Root user acceptable due to container isolation
- **Date**: Oct 31, 2025

**✅ DECISION 15: Web Search Implementation**
- **Choice**: Self-hosted SearXNG meta-search engine
- **Rationale**: Free, private, self-controlled, no rate limiting
- **Implementation**: SearXNG instance with domain filtering for programming/security sites
- **Date**: Oct 31, 2025

**✅ DECISION 16: Multi-Project Architecture**
- **Choice**: Project-isolated teams (complete isolation)
- **Implementation**: Each project gets its own orchestrator + full agent team
- **Benefits**: Zero cross-project contamination, parallel development, simple permissions
- **Date**: Oct 31, 2025

**✅ DECISION 17: Knowledge Sharing System**
- **Choice**: Communal RAG system (Qdrant + LLM)
- **Implementation**: Read-only knowledge base where teams can query previous project patterns
- **Benefits**: Collective intelligence while maintaining project isolation
- **Date**: Oct 31, 2025

---

## 2. GitHub Integration Architecture

### Questions to Answer:
- What GitHub API features do we need?
- How do we manage repository creation and permissions?
- What's our branching strategy per project?
- How do we handle PR workflows and reviews?

### Decision Log:

**✅ DECISION 18: GitHub Authentication**
- **Choice**: OAuth authentication (configurable in frontend)
- **Implementation**: Users connect GitHub via OAuth flow, per-installation access tokens
- **Benefits**: Professional, secure, per-user permissions, no hardcoded credentials
- **Date**: Oct 31, 2025

**✅ DECISION 19: Repository Management**
- **Choice**: Auto-create new repository per project
- **Implementation**: GitHub Specialist creates repo at project start with proper structure and permissions
- **Date**: Oct 31, 2025

**✅ DECISION 20: PR Workflow**
- **Choice**: Milestone-based PRs with human approval
- **Implementation**: 
  - PRs created only at phase/feature completion milestones
  - PRs presented to human for review and approval
  - GitHub Specialist manages PR creation and merge after approval
- **Date**: Oct 31, 2025

**✅ DECISION 21: Branching Strategy**
- **Choice**: Commit straight to main (simple workflow)
- **Implementation**: All development happens on main branch, PRs created from main for milestone reviews
- **Rationale**: Keeps things simple, matches milestone-based development, no branch management overhead
- **Date**: Oct 31, 2025

---

## 3. Human-in-the-Loop System Design

### Questions to Answer:
- What are the mandatory approval checkpoints?
- How do we present decisions to humans for approval?
- What happens when humans reject or modify plans?
- How do we handle human availability and response times?

### Decision Log:

**✅ DECISION 22: Approval Checkpoints**
- **Choice**: Streamlined gates with continuous testing
- **Mandatory Gates**:
  1. **Project Planning Complete** - Workshopper + PM requirements approved
  2. **Architecture Approval** - System design approved
  3. **Development & Testing Complete** - All tests passing 100%
  4. **Release Approval** - Final deployment decision
- **Security Gates**: Skip if resolvable, only gate for unresolvable security issues or design flaws
- **Gate Triggers**: Automatic (orchestrator detects completion) and Manual (human requested)
- **Date**: Oct 31, 2025

**✅ DECISION 23: Escalation Authority**
- **Choice**: Orchestrator-only escalation (no direct agent requests)
- **Implementation**: Only orchestrator can determine when human input is needed and trigger reviews
- **Date**: Oct 31, 2025

**✅ DECISION 24: Manual Review Format**
- **Choice**: Full project progress report for manual reviews
- **Implementation**: When human triggers review, receive comprehensive project status, progress, and current state
- **Date**: Oct 31, 2025

**✅ DECISION 25: Frontend Approval Interface**
- **Choice**: Modal-based approval system with dashboard cards
- **Implementation**:
  - Main dashboard: Project cards that turn red when approval needed
  - Project page: Modal appears with description, approve/deny buttons, feedback field
  - Real-time updates: Cards reflect current project status
- **Date**: Oct 31, 2025

**✅ DECISION 26: Rejection Handling Process**
- **Choice**: Resolution cycle with immediate documentation updates
- **Implementation**:
  - Approval denied requires mandatory reason from human
  - Orchestrator works with Project Manager + Workshopper to create resolution plan
  - Cycle continues: resolution plan → new approval → repeat until approved
  - Once approved: project planning documentation updated immediately to new plan
- **Date**: Oct 31, 2025

**✅ DECISION 27: Project Availability Policy**
- **Choice**: Indefinite pause until approval (no auto-approvals)
- **Implementation**:
  - Projects stop ALL work when waiting for approval
  - Enter sleep state to conserve resources
  - No timeouts or auto-approvals
  - Human approval required to resume work
- **Date**: Oct 31, 2025

---

## Conflict & Risk Tracking

### Identified Conflicts:
*Will track any conflicts we discover during planning...*

### Mitigation Strategies:
*Will document how we resolve conflicts...*
