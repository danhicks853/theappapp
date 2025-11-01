# Decision 8: Agent Tool Access Matrix

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Principle of least privilege with specialist isolation + Tool Access Service

**Access Distribution**:
- **Devs**: Code execution, web search, read/write, database expertise
- **QA Engineer**: Code execution (testing only), limited web search, read/write (test reports only)
- **DevOps**: Code execution (Docker/deployment), read/write (no IaaS access)
- **Security**: Web search, read/write, read-only code execution (scanning tools only)
- **Workshopper**: Read/write only
- **Documentation**: Read/write only
- **GitHub Specialist**: Full GitHub API, limited web search, private document access

**PR Workflow**: PRs only at milestones, agents request → Orchestrator → Human approval → GitHub Specialist execution

**Key Architecture**: Tool Access Service brokers all privileged operations with validation and audit logging

## Related
- Detailed in Decision 71: Tool Access Service (TAS)
