# Decision 71: Tool Access Service (TAS) Architecture

**Status**: ✅ COMPLETE  
**Date Resolved**: Nov 1, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: Decision 8 (tool access matrix), Decision 60 (security boundaries)

---

## Context

The Tool Access Service (TAS) is the critical security layer that enforces which tools each agent can use. Referenced throughout the architecture but never fully specified:
- Phase 2 Section 2.3 (mostly TODO)
- Decision 8 defines access matrix but not enforcement mechanism
- Decision 60 references TAS but provides no implementation plan
- Security model depends on reliable permission enforcement

Without TAS specification, we cannot implement secure agent operations or begin Phase 2 development.

---

## Decision

**TAS will be a singleton REST API service with database-backed permissions and audit logging.**

### Core Architecture
- **API Type**: REST API with JSON payloads
- **Permission Storage**: PostgreSQL database only (no config files)
- **Audit Logging**: PostgreSQL with 1-year retention policy
- **Security Scope**: Tool permission enforcement only (not container-aware)
- **Deployment**: Single instance service
- **Rate Limiting**: None (agents self-regulate)
- **Violation Handling**: Log and reject; agent handles escalation

---

## Implementation Details

### 1. REST API Design

#### Endpoint Structure
```
POST /api/v1/tools/execute
POST /api/v1/tools/validate
GET  /api/v1/tools/permissions/{agent_id}
GET  /api/v1/audit/logs
```

#### Request Format: Tool Execution
```json
{
  "request_id": "uuid",
  "agent_id": "backend_dev_001",
  "project_id": "proj_123",
  "tool_name": "file_write",
  "operation": "write",
  "parameters": {
    "path": "/project/src/main.py",
    "content": "..."
  },
  "timestamp": "2025-11-01T01:15:30Z"
}
```

#### Response Format: Success
```json
{
  "status": "allowed",
  "request_id": "uuid",
  "result": {
    "success": true,
    "data": "..."
  },
  "logged": true
}
```

#### Response Format: Rejection
```json
{
  "status": "denied",
  "request_id": "uuid",
  "reason": "Agent 'frontend_dev_001' not permitted to use tool 'database_write'",
  "violation_type": "permission_denied",
  "allowed_tools": ["file_read", "file_write", "npm_install"],
  "logged": true
}
```

#### Validation Endpoint (Pre-check)
```
POST /api/v1/tools/validate
```
Allows agents to check permissions before attempting operations.

---

### 2. Privilege Enforcement Implementation

#### Permission Storage Schema
```sql
CREATE TABLE agent_tool_permissions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),  -- user or system
    notes TEXT,
    UNIQUE(agent_id, tool_name)
);

CREATE INDEX idx_agent_permissions ON agent_tool_permissions(agent_id, tool_name);
```

#### Frontend Configuration
- Dashboard UI for permission management
- Per-agent permission matrix (checkboxes)
- Real-time updates (no service restart required)
- Audit trail of permission changes
- Bulk permission templates (e.g., "Standard Backend Dev")

#### Permission Check Logic
```python
def check_permission(agent_id: str, tool_name: str) -> bool:
    """
    Check if agent has permission to use tool.
    Returns False if no explicit permission found (deny by default).
    """
    result = db.query(
        "SELECT allowed FROM agent_tool_permissions 
         WHERE agent_id = ? AND tool_name = ?",
        agent_id, tool_name
    )
    return result.allowed if result else False
```

#### Default Permissions
- New agents start with NO permissions
- Must be explicitly granted via frontend
- System provides permission templates for common roles

---

### 3. Audit Logging System

#### Audit Log Schema
```sql
CREATE TABLE tool_audit_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(100),
    tool_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL,
    allowed BOOLEAN NOT NULL,
    denial_reason TEXT,
    execution_time_ms INTEGER,
    result_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_timestamp ON tool_audit_logs(timestamp);
CREATE INDEX idx_audit_agent ON tool_audit_logs(agent_id);
CREATE INDEX idx_audit_tool ON tool_audit_logs(tool_name);
CREATE INDEX idx_audit_allowed ON tool_audit_logs(allowed);
```

#### Logged Fields
- **request_id**: Unique identifier for correlation
- **timestamp**: When request occurred
- **agent_id**: Which agent made request
- **project_id**: Associated project (if any)
- **tool_name**: Tool requested
- **operation**: Specific operation within tool
- **parameters**: Full parameter set (JSONB for queryability)
- **allowed**: Boolean - was request permitted?
- **denial_reason**: Why request was denied (if denied)
- **execution_time_ms**: Performance tracking
- **result_summary**: Brief outcome description

#### Retention Policy
- **Active Logs**: All logs stored in database
- **Pruning**: Automated daily job deletes logs older than 1 year
- **Archive**: (Optional future) Export to cold storage before deletion
- **Exception**: Security violations may have longer retention

```python
# Daily cleanup job
def prune_old_logs():
    """Delete audit logs older than 1 year."""
    cutoff_date = datetime.now() - timedelta(days=365)
    db.execute(
        "DELETE FROM tool_audit_logs WHERE timestamp < ?",
        cutoff_date
    )
```

---

### 4. Security Boundary Enforcement

**TAS Scope**: Tool permission enforcement ONLY

#### What TAS Enforces
- ✅ Agent has permission to use requested tool
- ✅ Logging of all tool access attempts
- ✅ Rejection of unauthorized requests

#### What TAS Does NOT Enforce
- ❌ Container filesystem boundaries (handled by Docker)
- ❌ Network access policies (handled by container networking)
- ❌ Resource limits (handled by container runtime)
- ❌ File path validation (handled by tool implementation)

#### Security Model
- **TAS**: Coarse-grained "can this agent use this tool?"
- **Tool Implementation**: Fine-grained validation (path safety, parameter validation)
- **Container**: Infrastructure-level isolation

This separation of concerns keeps TAS simple and focused while maintaining defense-in-depth.

---

### 5. Deployment Architecture

#### Singleton Service Pattern
```
┌─────────────────┐
│  Orchestrator   │
└────────┬────────┘
         │
         ↓
    ┌────────┐
    │  TAS   │ ← Single instance
    └────┬───┘
         │
         ↓
   ┌──────────┐
   │PostgreSQL│
   └──────────┘
```

#### Service Characteristics
- **Single Instance**: One TAS process per deployment
- **Stateless**: All state in database (enables future scaling)
- **HTTP Server**: FastAPI or similar
- **Port**: Configurable (default 8001)
- **Startup**: Launched with orchestrator
- **Health Check**: `/health` endpoint for monitoring

#### Deployment Configuration
```yaml
# docker-compose.yml
services:
  tas:
    build: ./services/tas
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://...
      - LOG_LEVEL=INFO
    depends_on:
      - postgres
    restart: unless-stopped
```

#### Why Singleton for MVP?
- ✅ Single-user system (no high concurrency)
- ✅ Simplest deployment and debugging
- ✅ Sufficient for expected load
- ✅ Can scale to multiple instances later if needed (stateless design)

---

### 6. Violation Handling

#### When Agent Violates Permission

**TAS Response**:
1. Log violation to audit log
2. Return HTTP 403 with detailed error
3. Include allowed tools in response
4. Do NOT notify orchestrator directly

**Agent Responsibility**:
- Receive rejection
- Decide if violation is critical
- If critical: Request orchestrator assistance
- If non-critical: Adapt approach with available tools

#### Violation Response Example
```json
{
  "status": "denied",
  "request_id": "req_789",
  "reason": "Tool 'database_write' not in allowed tool set for agent 'frontend_dev_001'",
  "violation_type": "permission_denied",
  "allowed_tools": ["file_read", "file_write", "npm_install", "git_status"],
  "suggestion": "This agent is restricted to frontend operations. Consider requesting Backend Dev agent via orchestrator.",
  "logged": true
}
```

#### Design Rationale
- **Agent autonomy**: Let agents decide if rejection is blocking
- **Reduced escalation**: Many rejections can be worked around
- **Orchestrator efficiency**: Not notified of every permission check
- **Clear communication**: Agent knows what tools ARE available

---

### 7. Testing Strategy

#### Mock Testing (Unit Level)
```python
class MockTAS:
    """Mock TAS for agent unit tests."""
    def __init__(self, permissions: dict):
        self.permissions = permissions  # {agent_id: [tool_list]}
    
    def execute_tool(self, agent_id: str, tool_name: str, **params):
        if tool_name in self.permissions.get(agent_id, []):
            return {"status": "allowed", "result": mock_tool_result()}
        return {"status": "denied", "reason": "Permission denied"}
```

**Mock Test Coverage**:
- Agent handles allowed requests
- Agent handles denied requests
- Agent adapts to available tool set
- Agent escalates when necessary

#### Integration Testing
```python
@pytest.mark.integration
def test_tas_permission_enforcement():
    """Test TAS with real database and API."""
    # Setup
    tas = TASService(db_url=test_db)
    agent = BackendDevAgent(id="test_agent")
    
    # Grant specific permission
    tas.grant_permission("test_agent", "file_write")
    
    # Test allowed operation
    response = tas.execute_tool(
        agent_id="test_agent",
        tool_name="file_write",
        path="/test.py",
        content="print('test')"
    )
    assert response["status"] == "allowed"
    
    # Test denied operation
    response = tas.execute_tool(
        agent_id="test_agent",
        tool_name="database_write",
        table="users", data={}
    )
    assert response["status"] == "denied"
    
    # Verify audit logs
    logs = tas.get_audit_logs(agent_id="test_agent")
    assert len(logs) == 2
    assert logs[0]["allowed"] == True
    assert logs[1]["allowed"] == False
```

**Integration Test Coverage**:
- Permission grant/revoke workflow
- Tool execution with permission checks
- Audit log creation and querying
- Frontend permission UI (Playwright)
- Database retention policy
- Service startup/shutdown
- Error handling for database failures

---

## Rationale

### Why REST API?
- Widely understood, easy to debug
- Sufficient performance for expected load (not high-frequency trading)
- Simple client libraries (requests, axios)
- OpenAPI documentation support

### Why Database-Only Permissions?
- Dynamic updates via frontend without restarts
- Single source of truth
- Queryable for reporting
- Aligns with user requirement for frontend configuration

### Why Database Audit Logs?
- Structured, queryable data
- Supports dashboard and reporting
- 1-year retention is manageable in PostgreSQL
- Can add archival later if needed

### Why Tool-Permission-Only Enforcement?
- Clear separation of concerns
- TAS remains simple and focused
- Container handles infrastructure security
- Tool implementations handle parameter validation
- Each layer responsible for appropriate scope

### Why Singleton?
- Single-user MVP scope
- Simplest deployment model
- No coordination complexity
- Stateless design allows future scaling

### Why No Rate Limiting?
- Agents are cooperative, not adversarial
- Orchestrator manages agent coordination
- Simpler implementation
- Can add later if abuse patterns emerge

### Why Agent-Driven Escalation?
- Agents understand task context
- Reduces orchestrator notification spam
- Many permission denials are non-critical
- Agents can adapt or escalate as needed

---

## Implications

### Enables
- ✅ Secure tool access enforcement (blocking Phase 2)
- ✅ Agent permission management UI (Phase 4)
- ✅ Security audit trail
- ✅ Tool usage analytics
- ✅ Fine-grained agent capability control

### Constraints
- TAS is required dependency for all agent tool operations
- Database must be available for TAS to function
- Permission changes require database write
- No offline tool execution

### Trade-offs
- **Simplicity vs Performance**: REST API is slower than in-process, but sufficient
- **Database vs Config**: Database requires more infrastructure but enables frontend UI
- **No Rate Limiting**: Simpler but assumes cooperative agents
- **Agent Escalation**: More agent logic but less orchestrator overhead

---

## Related Decisions

- **Decision 8**: Tool access matrix (defines what permissions are possible)
- **Decision 60**: Security boundaries (TAS is enforcement layer)
- **Decision 67**: Orchestrator LLM (handles permission escalations)
- **Decision 70**: Agent collaboration (agents request help when blocked)

---

## Tasks Created

### Phase 2.3: Tool Access Service (Updated)
- [x] 2.3.1: Define TAS requirements → **COMPLETE** (this decision)
- [ ] 2.3.2: Implement TAS REST API service
  - [ ] FastAPI service setup
  - [ ] Tool execution endpoint
  - [ ] Validation endpoint
  - [ ] Permission query endpoint
  - [ ] Audit log query endpoint
- [ ] 2.3.3: Implement permission enforcement
  - [ ] Database schema creation
  - [ ] Permission check logic
  - [ ] Default permission templates
- [ ] 2.3.4: Implement audit logging
  - [ ] Log writing on every tool request
  - [ ] Query interface for logs
  - [ ] Retention policy job (1-year prune)
- [ ] 2.3.5: Build frontend permission UI
  - [ ] Agent permission matrix view
  - [ ] Permission editing interface
  - [ ] Permission templates (role-based)
  - [ ] Audit log viewer
- [ ] 2.3.6: Agent-TAS integration
  - [ ] Agent base class TAS client
  - [ ] Error handling for denials
  - [ ] Escalation helper methods
- [ ] 2.3.7: Testing
  - [ ] Mock TAS for unit tests
  - [ ] Integration test suite
  - [ ] Permission grant/deny scenarios
  - [ ] Audit log validation tests
- [ ] 2.3.8: Documentation
  - [ ] API specification (OpenAPI)
  - [ ] Permission configuration guide
  - [ ] Audit log query examples

---

## API Specification

### OpenAPI Schema (Summary)

```yaml
openapi: 3.0.0
info:
  title: Tool Access Service (TAS) API
  version: 1.0.0

paths:
  /api/v1/tools/execute:
    post:
      summary: Execute a tool with permission check
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolRequest'
      responses:
        200:
          description: Tool executed or denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ToolResponse'
  
  /api/v1/tools/validate:
    post:
      summary: Validate permission without executing
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidationRequest'
      responses:
        200:
          description: Permission check result
  
  /api/v1/tools/permissions/{agent_id}:
    get:
      summary: Get all permissions for an agent
      parameters:
        - name: agent_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: List of allowed tools
          content:
            application/json:
              schema:
                type: array
                items:
                  type: string
  
  /api/v1/audit/logs:
    get:
      summary: Query audit logs
      parameters:
        - name: agent_id
          in: query
          schema:
            type: string
        - name: start_date
          in: query
          schema:
            type: string
            format: date-time
        - name: end_date
          in: query
          schema:
            type: string
            format: date-time
        - name: allowed
          in: query
          schema:
            type: boolean
      responses:
        200:
          description: Audit log entries
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/AuditLog'

components:
  schemas:
    ToolRequest:
      type: object
      required: [request_id, agent_id, tool_name, operation, parameters]
      properties:
        request_id:
          type: string
          format: uuid
        agent_id:
          type: string
        project_id:
          type: string
        tool_name:
          type: string
        operation:
          type: string
        parameters:
          type: object
        timestamp:
          type: string
          format: date-time
    
    ToolResponse:
      type: object
      properties:
        status:
          type: string
          enum: [allowed, denied]
        request_id:
          type: string
        result:
          type: object
        reason:
          type: string
        violation_type:
          type: string
        allowed_tools:
          type: array
          items:
            type: string
        suggestion:
          type: string
        logged:
          type: boolean
    
    AuditLog:
      type: object
      properties:
        id:
          type: integer
        request_id:
          type: string
        timestamp:
          type: string
          format: date-time
        agent_id:
          type: string
        project_id:
          type: string
        tool_name:
          type: string
        operation:
          type: string
        parameters:
          type: object
        allowed:
          type: boolean
        denial_reason:
          type: string
        execution_time_ms:
          type: integer
        result_summary:
          type: string
```

---

## Database Schema Details

### Complete Schema with Indexes

```sql
-- Agent tool permissions
CREATE TABLE agent_tool_permissions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    notes TEXT,
    UNIQUE(agent_id, tool_name)
);

CREATE INDEX idx_agent_permissions ON agent_tool_permissions(agent_id, tool_name);
CREATE INDEX idx_tool_permissions ON agent_tool_permissions(tool_name);

-- Audit logs
CREATE TABLE tool_audit_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(100),
    tool_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL,
    allowed BOOLEAN NOT NULL,
    denial_reason TEXT,
    execution_time_ms INTEGER,
    result_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_timestamp ON tool_audit_logs(timestamp);
CREATE INDEX idx_audit_agent ON tool_audit_logs(agent_id);
CREATE INDEX idx_audit_project ON tool_audit_logs(project_id);
CREATE INDEX idx_audit_tool ON tool_audit_logs(tool_name);
CREATE INDEX idx_audit_allowed ON tool_audit_logs(allowed);
CREATE INDEX idx_audit_request ON tool_audit_logs(request_id);

-- Permission change history (for audit trail)
CREATE TABLE permission_change_log (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    previous_state BOOLEAN,
    new_state BOOLEAN NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);

CREATE INDEX idx_permission_changes ON permission_change_log(agent_id, tool_name, changed_at);
```

---

## Security Considerations

### Authentication
- TAS API requires authentication (JWT or session token)
- Only orchestrator should call TAS (agents call via orchestrator)
- Frontend permission UI requires user authentication

### Authorization
- User can modify any agent permissions (single-user system)
- Audit logs are read-only via UI
- Permission templates are system-defined

### Data Protection
- Tool parameters logged (may contain sensitive data)
- Consider PII filtering in audit logs
- JSONB allows flexible parameter storage but review for secrets

### Threat Model
- **Malicious Agent**: TAS enforces permissions regardless
- **Compromised TAS**: All security fails (requires infrastructure hardening)
- **Database Compromise**: All permissions and logs exposed
- **Mitigation**: TAS is trusted component, focus on infrastructure security

---

## Future Enhancements (Post-MVP)

### Potential Additions
- **Rate Limiting**: If agent abuse patterns emerge
- **Cost Tracking**: Track tool operation costs per agent
- **Advanced Audit**: Export to SIEM, long-term cold storage
- **Permission Groups**: Reusable permission sets
- **Conditional Permissions**: Time-based, project-based rules
- **Multi-tenancy**: Per-user permission isolation
- **Horizontal Scaling**: Multiple TAS instances with load balancer

### NOT Planned
- Direct agent-to-TAS communication (always via orchestrator)
- Container-level enforcement (separate concern)
- Real-time permission updates (database query sufficient)

---

## Documentation

**Decision Document**: `docs/architecture/decision-71-tool-access-service.md` (this file)  
**API Specification**: To be created in `docs/api/tas-api-spec.yaml`  
**Database Schema**: To be added to `docs/database/schema.sql`  
**User Guide**: To be created in `docs/guides/managing-agent-permissions.md`

---

*Decision finalized: Nov 1, 2025*
*Implementation priority: P0 - Must complete before Phase 2 development*
