# Decision 73: Frontend-Backend API Specification

**Status**: ✅ COMPLETE  
**Date Resolved**: Nov 1, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: Phase 4 frontend decisions, orchestrator architecture

---

## Context

Phase 4 defines frontend architecture but lacks concrete API contract between frontend and backend. Without this specification:
- Frontend developers don't know what endpoints to call
- WebSocket message formats are undefined
- Real-time update protocols are unclear
- No contract for testing or validation

This decision defines the complete API specification enabling Phase 4 implementation.

---

## Decision

**REST API with JWT authentication, WebSocket for real-time events, context-aware event subscriptions, and cursor-based pagination.**

### Core Architecture
- **REST API**: CRUD operations, settings, gates, reporting
- **WebSocket**: Real-time event streaming
- **Authentication**: JWT tokens for both REST and WebSocket
- **Event Delivery**: Context-aware subscriptions (dashboard vs project page)
- **Message Format**: Detailed envelope with metadata
- **Versioning**: URL-based (`/api/v1/...`)
- **Pagination**: Cursor-based for lists
- **Rate Limiting**: None for MVP
- **CORS**: Enabled for development

---

## Implementation Details

### 1. REST API Endpoints

#### Project Management

```
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{id}
PUT    /api/v1/projects/{id}
DELETE /api/v1/projects/{id}
POST   /api/v1/projects/{id}/start
POST   /api/v1/projects/{id}/pause
POST   /api/v1/projects/{id}/resume
```

**Example: Create Project**
```http
POST /api/v1/projects
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "name": "E-commerce Platform",
  "description": "Build online store with React and FastAPI",
  "requirements": "User authentication, product catalog, shopping cart",
  "tech_stack": ["react", "fastapi", "postgresql"],
  "settings": {
    "autonomy_level": 0.7,
    "cost_limit": 50.00
  }
}

Response 201:
{
  "id": "proj_abc123",
  "name": "E-commerce Platform",
  "status": "created",
  "created_at": "2025-11-01T01:45:00Z"
}
```

#### Settings & Configuration

```
GET /api/v1/settings
PUT /api/v1/settings
GET /api/v1/agents
GET /api/v1/agents/{id}/permissions
PUT /api/v1/agents/{id}/permissions
```

#### Gates & Approvals

```
GET  /api/v1/gates/pending
POST /api/v1/gates/{id}/approve
POST /api/v1/gates/{id}/reject
POST /api/v1/gates/{id}/feedback
```

#### Reporting & Metrics

```
GET /api/v1/projects/{id}/cost
GET /api/v1/projects/{id}/activity
GET /api/v1/audit/logs
GET /api/v1/metrics/dashboard
```

---

### 2. WebSocket Message Types

#### Agent Activity Events
- `agent.started` - Agent begins work
- `agent.completed` - Agent finishes task
- `agent.error` - Agent encounters error
- `agent.thinking` - Agent reasoning update (chain-of-thought)
- `agent.tool_use` - Agent uses a tool

#### Project Status Events
- `project.status_changed` - Project state transition
- `project.phase_completed` - Phase milestone reached
- `project.progress_update` - Progress percentage update

#### File System Events
- `file.created` - New file created
- `file.modified` - File changed
- `file.deleted` - File removed

#### Gate & Approval Events
- `gate.triggered` - New gate requires approval
- `gate.resolved` - Gate approved/rejected

#### Error & Notification Events
- `error.occurred` - System error
- `notification.info` - Info message
- `notification.warning` - Warning message

#### Cost Events
- `cost.updated` - Cost accumulation update

---

### 3. Message Schema

#### Message Envelope (Detailed Format)

```json
{
  "type": "agent.started",
  "id": "msg_xyz789",
  "timestamp": "2025-11-01T01:45:30Z",
  "project_id": "proj_abc123",
  "version": "1.0",
  "data": {
    "agent_id": "backend_dev_001",
    "agent_type": "backend_developer",
    "task": "Implement user authentication API"
  }
}
```

**Envelope Fields**:
- `type`: Event type (string)
- `id`: Unique message ID (string)
- `timestamp`: ISO 8601 timestamp (string)
- `project_id`: Associated project (string, nullable)
- `version`: API version (string)
- `data`: Event-specific payload (object)

#### Error Format

```json
{
  "error": {
    "code": "AGENT_FAILED",
    "message": "Backend Dev Agent encountered error during execution",
    "details": {
      "agent_id": "backend_dev_001",
      "task_id": "task_456",
      "error_type": "SyntaxError",
      "stack_trace": "..."
    },
    "project_id": "proj_abc123",
    "agent_id": "backend_dev_001",
    "timestamp": "2025-11-01T01:45:45Z"
  }
}
```

**Error Fields**:
- `code`: Error code (string)
- `message`: Human-readable message (string)
- `details`: Additional context (object)
- `project_id`: Associated project (string)
- `agent_id`: Agent that errored (string)
- `timestamp`: When error occurred (string)

---

### 4. Authentication & Authorization

#### JWT Token Authentication

**Login Flow**:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}

Response 200:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**REST API Authentication**:
```http
GET /api/v1/projects
Authorization: Bearer eyJhbGc...
```

**WebSocket Authentication**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Send token after connection
ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'authenticate',
    token: 'eyJhbGc...'
  }));
};
```

**Token Refresh**:
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}

Response 200:
{
  "access_token": "eyJhbGc...",
  "expires_in": 3600
}
```

---

### 5. Real-Time Event Delivery

#### Context-Aware Subscriptions

**Dashboard Page** (viewing all projects):
```javascript
// Subscribe to summary events for all projects
ws.send(JSON.stringify({
  action: 'subscribe',
  context: 'dashboard',
  events: [
    'project.status_changed',
    'project.progress_update',
    'gate.triggered',
    'cost.updated'
  ]
}));

// Receives events for ALL projects
// Filtered to show only summary-level info
```

**Project Page** (viewing specific project):
```javascript
// Subscribe to all events for specific project
ws.send(JSON.stringify({
  action: 'subscribe',
  context: 'project',
  project_id: 'proj_abc123',
  events: 'all'  // or specific event types
}));

// Receives ALL events for proj_abc123
```

**Settings Page** (managing agent permissions):
```javascript
// Subscribe to agent-related events
ws.send(JSON.stringify({
  action: 'subscribe',
  context: 'settings',
  events: ['agent.error', 'notification.warning']
}));
```

#### Delivery Guarantees

**Best Effort Delivery**:
- Events sent to connected clients
- No guarantee if client disconnected
- No event replay on reconnect

**Resume from Current State**:
- On reconnect, client requests current state
- Backend sends snapshot of current project status
- Client updates UI to match current reality
- New events stream from that point forward

```javascript
ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    action: 'authenticate',
    token: jwt_token
  }));
  
  // Request current state
  ws.send(JSON.stringify({
    action: 'get_state',
    project_id: 'proj_abc123'
  }));
  
  // Subscribe to future events
  ws.send(JSON.stringify({
    action: 'subscribe',
    context: 'project',
    project_id: 'proj_abc123'
  }));
};

// Backend responds with current state
{
  "type": "state.snapshot",
  "data": {
    "project": { /* current project state */ },
    "active_agents": [ /* currently running agents */ ],
    "pending_gates": [ /* gates awaiting approval */ ],
    "cost": { /* current cost */ }
  }
}
```

---

### 6. API Versioning

**URL-Based Versioning**:
```
/api/v1/projects
/api/v1/settings
/api/v1/gates
```

**Benefits**:
- Clear, visible version in URL
- Easy to support multiple versions
- Simple routing

**Version Strategy**:
- v1: Initial MVP release
- Breaking changes require new version (v2)
- Non-breaking changes can be added to existing version
- Deprecation notices before removing old versions

---

### 7. Cursor-Based Pagination

**For List Endpoints**:
```http
GET /api/v1/projects?limit=20&cursor=eyJpZCI6InByb2pfMTIzIn0

Response 200:
{
  "data": [
    { "id": "proj_124", "name": "Project A" },
    { "id": "proj_125", "name": "Project B" }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6InByb2pfMTI1In0",
    "has_more": true,
    "limit": 20
  }
}
```

**Cursor Format**:
- Base64-encoded JSON: `{"id": "proj_125", "created_at": "2025-11-01T..."}`
- Opaque to client (don't parse it)
- Stable across data changes

**Benefits**:
- Handles real-time data changes
- No "page drift" issues
- Efficient database queries

---

### 8. CORS Configuration

**Enable CORS for Development**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production**:
- Restrict to actual frontend domain
- Or serve frontend from same origin (no CORS needed)

---

## Complete API Specification

### REST Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/refresh` | Refresh JWT token |
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{id}` | Get project details |
| PUT | `/api/v1/projects/{id}` | Update project |
| DELETE | `/api/v1/projects/{id}` | Delete/cancel project |
| POST | `/api/v1/projects/{id}/start` | Start project execution |
| POST | `/api/v1/projects/{id}/pause` | Pause project |
| POST | `/api/v1/projects/{id}/resume` | Resume project |
| GET | `/api/v1/projects/{id}/cost` | Get cost breakdown |
| GET | `/api/v1/projects/{id}/activity` | Get activity log |
| GET | `/api/v1/settings` | Get user settings |
| PUT | `/api/v1/settings` | Update settings |
| GET | `/api/v1/agents` | List agents |
| GET | `/api/v1/agents/{id}/permissions` | Get agent permissions |
| PUT | `/api/v1/agents/{id}/permissions` | Update permissions |
| GET | `/api/v1/gates/pending` | Get pending gates |
| POST | `/api/v1/gates/{id}/approve` | Approve gate |
| POST | `/api/v1/gates/{id}/reject` | Reject gate |
| POST | `/api/v1/gates/{id}/feedback` | Provide feedback |
| GET | `/api/v1/audit/logs` | Get audit logs |
| GET | `/api/v1/metrics/dashboard` | Dashboard metrics |

### WebSocket Events Summary

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `agent.started` | Agent begins task | agent_id, task |
| `agent.completed` | Agent finishes | agent_id, result |
| `agent.error` | Agent fails | agent_id, error |
| `agent.thinking` | Reasoning update | agent_id, thought |
| `agent.tool_use` | Tool execution | agent_id, tool, params |
| `project.status_changed` | State transition | old_status, new_status |
| `project.phase_completed` | Phase done | phase_name |
| `project.progress_update` | Progress change | percentage |
| `file.created` | File added | path, content_preview |
| `file.modified` | File changed | path, diff |
| `file.deleted` | File removed | path |
| `gate.triggered` | Gate activated | gate_type, reason |
| `gate.resolved` | Gate closed | decision, feedback |
| `error.occurred` | System error | code, message |
| `notification.info` | Info message | message |
| `notification.warning` | Warning | message |
| `cost.updated` | Cost change | total, delta |

---

## Rationale

### Why JWT Authentication?
- Stateless (scales well)
- Standard, well-supported
- Works for both REST and WebSocket
- Token refresh prevents frequent re-login

### Why Context-Aware Subscriptions?
- Reduces unnecessary traffic
- Dashboard doesn't need detailed agent thinking
- Project page gets full detail
- Efficient use of WebSocket bandwidth

### Why Best Effort + State Snapshot?
- Simpler than guaranteed delivery
- State snapshot ensures accuracy after reconnect
- Acceptable for UI updates (not critical transactions)
- Reduces complexity significantly

### Why URL Versioning?
- Most visible and explicit
- Easy to route and maintain
- Industry standard
- Simple for API consumers

### Why Cursor-Based Pagination?
- Handles real-time data changes gracefully
- No "page drift" when data inserted/deleted
- More efficient than offset pagination
- Better UX for infinite scroll

### Why Enable CORS?
- Frontend and backend on different ports during dev
- Simple to configure in FastAPI
- Can restrict in production

---

## Related Decisions

- **Decision 67**: Orchestrator LLM (backend logic)
- **Decision 70**: Agent Collaboration (events to surface)
- **Decision 71**: Tool Access Service (audit log API)
- **Phase 4**: Frontend architecture (API consumer)

---

## Tasks Created

### Phase 4: Frontend Implementation (Updated)
- [ ] 4.1: Implement REST API client
  - [ ] API client library with JWT handling
  - [ ] Endpoint wrappers for all REST calls
  - [ ] Error handling and retries
  - [ ] Token refresh logic
- [ ] 4.2: Implement WebSocket client
  - [ ] WebSocket connection management
  - [ ] Authentication on connect
  - [ ] Context-aware subscription logic
  - [ ] Reconnection with state snapshot
  - [ ] Event routing to UI components
- [ ] 4.3: Build API integration tests
  - [ ] REST endpoint tests
  - [ ] WebSocket event tests
  - [ ] Authentication flow tests
  - [ ] Error handling tests

### Phase 6.1: Backend API Implementation
- [ ] 6.1.1: Implement REST API endpoints
  - [ ] FastAPI route definitions
  - [ ] Request/response models (Pydantic)
  - [ ] JWT authentication middleware
  - [ ] CORS configuration
- [ ] 6.1.2: Implement WebSocket server
  - [ ] WebSocket connection handler
  - [ ] Authentication verification
  - [ ] Subscription management
  - [ ] Event broadcasting
  - [ ] State snapshot generation
- [ ] 6.1.3: Create OpenAPI documentation
  - [ ] Auto-generated from FastAPI
  - [ ] Example requests/responses
  - [ ] Authentication documentation
- [ ] 6.1.4: API testing
  - [ ] Unit tests for endpoints
  - [ ] Integration tests
  - [ ] WebSocket event tests
  - [ ] Load testing

---

## Documentation

**Decision Document**: `docs/architecture/decision-73-frontend-backend-api.md` (this file)  
**OpenAPI Spec**: To be auto-generated by FastAPI at `/docs`  
**WebSocket Protocol**: To be documented in `docs/api/websocket-protocol.md`  
**Frontend Integration Guide**: To be created in `docs/guides/frontend-api-integration.md`

---

*Decision finalized: Nov 1, 2025*  
*Implementation priority: P0 - Unblocks Phase 4 frontend development*
