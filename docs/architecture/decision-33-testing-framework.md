# Decision 33: Testing Framework Selection

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: Comprehensive framework matrix with "test reality" philosophy

**Implementation**:
- **Backend**: pytest (Python), Jest (Node.js), JUnit (Java) + integration tools
- **Frontend**: Jest + React Testing Library + Playwright for E2E
- **Security**: OWASP tools + language-specific static analysis
- **Performance**: Locust, k6 for load testing

**Core Philosophy**: Mock as little as possible

**Real Interactions**: Always test public/external/third-party integrations

**Exception**: Only mock when it would interfere with production systems (Freshdesk tickets, Slack posts to populated channels)

## Related
- Decision 72: LLM Testing Strategy
