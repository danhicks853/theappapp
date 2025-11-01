# Phase 1: Foundation & Architecture Decisions

## Decision Tracking
*This document captures our decisions and rationale for Phase 1 deliverables*

---

## 1. Core System Architecture

### Questions to Answer:
- What is the overall system architecture? (Monolithic vs Microservices)
- How does the orchestrator engine work technically?
- What communication patterns between agents? (Message queue, shared state, direct calls)
- How do we handle agent state management and persistence?

### Decision Log:

**✅ DECISION 1: Overall System Architecture**
- **Choice**: Microservices architecture
- **Rationale**: Modular design isolates issues to individual services, better fault tolerance, independent scaling and deployment of agents
- **Trade-offs**: Higher complexity in communication and deployment, but worth it for isolation and modularity
- **Date**: Oct 31, 2025

**✅ DECISION 2: Orchestrator Engine Approach**
- **Choice**: Custom-built orchestrator (no Temporal/Cadence)
- **Rationale**: Must avoid copyleft licenses for commercialization potential, need full control over IP
- **Implementation**: Custom orchestrator service with message queue + database state management
- **Date**: Oct 31, 2025

**✅ DECISION 3: Orchestrator Architecture Pattern**
- **Choice**: Central Coordinator with intelligent gate detection
- **Rationale**: Clear decision authority for human approvals, easier debugging, centralized state management
- **Key Features**: Detect approval gates, monitor agent health, auto-recovery when agents go off-rails
- **Date**: Oct 31, 2025

**✅ DECISION 4: Communication Pattern**
- **Choice**: Coordinator-Agent Only (no direct agent-to-agent communication)
- **Rationale**: Safety and control - coordinator has full visibility, can pause any interaction, simpler security model
- **Implementation**: All agent communication flows through central coordinator
- **Date**: Oct 31, 2025

**✅ DECISION 5: Agent State Management**
- **Choice**: Centralized state with stateless agents
- **Rationale**: Complete recovery capability, prevents previous project failures, full audit trails
- **Implementation**: PostgreSQL for persistent state, Redis for caching, agents get state snapshots from orchestrator
- **Date**: Oct 31, 2025

---

## 2. Agent Role Definition

### Questions to Answer:
- What specific agent roles do we need?
- What are the responsibilities of each agent type?
- Which agents have access to which tools/functions?
- How do agents specialize vs generalize?

### Decision Log:

**✅ DECISION 6: Agent Roles**
- **Choice**: 9 specialized agents + extensible Specialist category
- **Agent List**:
  - Project Manager / Product Owner
  - Backend Developer
  - Frontend Developer
  - QA & Testing Engineer
  - DevOps Engineer
  - Workshopper (project planning specialist)
  - UI/UX Designer
  - Security Expert
  - Documentation Expert
  - **Specialists** (extensible category - GitHub Specialist first)
- **Rationale**: Core team + extensible specialists for vendor/domain-specific expertise
- **Date**: Oct 31, 2025

**✅ DECISION 7: Agent Responsibilities**
- **Choice**: Specialized domain responsibilities with Workshopper as human liaison
- **Key Insight**: Workshopper interacts directly with user during project creation, then hands off to other agents
- **Implementation**: Each agent has clear domain expertise and defined deliverables
- **Date**: Oct 31, 2025

**✅ DECISION 8: Agent Tool Access Matrix**
- **Choice**: Principle of least privilege with specialist isolation + Tool Access Service
- **Access Distribution**:
  - **Devs**: Code execution, web search, read/write, database expertise (Backend Dev as DB specialist)
  - **QA Engineer**: Code execution (testing only), limited web search (testing research), read/write (test reports only)
  - **DevOps**: Code execution (Docker/deployment), read/write (no IaaS access)
  - **Security**: Web search, read/write, read-only code execution (security scanning tools only)
  - **Workshopper**: Read/write only
  - **Documentation**: Read/write only
  - **GitHub Specialist**: Full GitHub API (repos, PR creation/approval/merge), limited web search, private document access
- **PR Workflow**: PRs only at specific milestones (phase completion, feature completion), agents request PRs through GitHub Specialist → Orchestrator → Human approval → GitHub Specialist execution
- **Key Architecture**: Tool Access Service brokers all privileged operations with validation and audit logging
- **Specialist Focus**: Third-party tool management only (GitHub, future: AWS, Azure, etc.)
- **Date**: Oct 31, 2025

---

## 3. Team Structure Design

### Questions to Answer:
- What organizational structure? (Hierarchical, flat, hybrid)
- How do agents coordinate and avoid conflicts?
- What is the decision-making process between agents?
- How do we handle agent failures or timeouts?

### Decision Log:

**✅ DECISION 9: Team Organizational Structure**
- **Choice**: Hub-and-spoke (no additional hierarchy)
- **Structure**: Human → Project Manager → Orchestrator (Hub) → Agents (Spokes)
- **Rationale**: Orchestrator architecture already creates natural hub-and-spoke, prevents role confusion, clear communication paths
- **Date**: Oct 31, 2025

**✅ DECISION 10: Agent Coordination & Conflict Prevention**
- **Choice**: Synchronous task queue (no conflicts possible)
- **Implementation**: One task at a time, one agent at a time, orchestrator controls all sequencing
- **Escalation**: Agents report issues to orchestrator, who decides to involve specialists/PM/human
- **Rationale**: Sequential execution eliminates race conditions, resource conflicts, and priority battles
- **Date**: Oct 31, 2025

**✅ DECISION 11: Decision-Making Process**
- **Choice**: Hierarchical decision flow through orchestrator
- **Process**: Agent question → Orchestrator → Specialist/human input → Orchestrator decision → Agent execution
- **Example**: Backend Dev asks "PostgreSQL vs MongoDB?" → Orchestrator checks requirements → Security Expert recommends → Orchestrator decides → Agent implements
- **Rationale**: Clear decision authority, specialist input when needed, human oversight on critical choices
- **Date**: Oct 31, 2025

**✅ DECISION 12: Agent Failure Handling**
- **Choice**: Simple timeout + progress checkpoint monitoring with explicit completion protocol
- **Implementation**: 
  - Task-specific timeouts with progress reporting requirements
  - Explicit "TASK_COMPLETE" messages only (progress messages separate)
  - Orchestrator validates completion before advancing
  - Agent replacement on timeout/failure
- **Safety Features**: Message type separation, artifact verification, rollback capability
- **Date**: Oct 31, 2025

---

## Conflict & Risk Tracking

### Identified Conflicts:
*Will track any conflicts we discover during planning...*

### Mitigation Strategies:
*Will document how we resolve conflicts...*
