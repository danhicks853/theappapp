# Decision 80: Error Handling & Classification System

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P2 - MEDIUM  
**Depends On**: All architectural decisions

---

## Context

Errors are mentioned throughout the system but no unified taxonomy or handling strategy exists. Different error types require different recovery strategies and user communication approaches.

---

## Decision Summary

### Core Approach
- **Hierarchical error taxonomy**: Categories → Types → Specific errors
- **HTTP-style error codes**: 4-digit codes (e.g., 1001, 2003)
- **Structured error logging**: JSON format with context
- **Tiered recovery**: Automatic retry → Agent retry → Gate → Human
- **User-friendly messages**: Technical details hidden, clear actions shown

---

## 1. Error Taxonomy

### Error Categories

```
1000-1999: Agent Errors
2000-2999: System Errors
3000-3999: External Service Errors
4000-4999: User Input Errors
5000-5999: Resource Errors
```

### Detailed Taxonomy

#### 1000-1999: Agent Errors
- **1001**: Agent timeout (exceeded task time limit)
- **1002**: Agent loop detected (3 identical failures)
- **1003**: Agent invalid output (malformed response)
- **1004**: Agent tool access denied (TAS permission violation)
- **1005**: Agent reasoning failure (LLM error)

#### 2000-2999: System Errors
- **2001**: Orchestrator failure (orchestrator crash/error)
- **2002**: Database connection error
- **2003**: Container creation failure
- **2004**: File system error (read/write failure)
- **2005**: Configuration error (missing/invalid config)

#### 3000-3999: External Service Errors
- **3001**: LLM API error (OpenAI/provider failure)
- **3002**: GitHub API error (authentication/rate limit)
- **3003**: Network timeout (external service unreachable)
- **3004**: RAG/Qdrant error (vector DB failure)
- **3005**: External dependency unavailable

#### 4000-4999: User Input Errors
- **4001**: Invalid project configuration
- **4002**: Missing required field
- **4003**: Invalid file format
- **4004**: Unauthorized access
- **4005**: Invalid API request

#### 5000-5999: Resource Errors
- **5001**: Disk space exhausted
- **5002**: Memory limit exceeded
- **5003**: CPU limit exceeded
- **5004**: Container limit reached
- **5005**: Database storage full

---

## 2. Error Structure

### Error Object Schema

```python
class SystemError:
    code: int              # Error code (e.g., 1001)
    category: str          # "agent", "system", "external", "user", "resource"
    message: str           # User-friendly message
    technical_detail: str  # Technical details (for logs)
    context: dict          # Additional context
    timestamp: datetime
    project_id: str        # Optional: related project
    agent_id: str          # Optional: related agent
    task_id: str           # Optional: related task
    recoverable: bool      # Can this be automatically recovered?
    recovery_strategy: str # "retry", "gate", "fail"
```

### Example Error

```json
{
    "code": 1001,
    "category": "agent",
    "message": "Agent task timed out after 10 minutes",
    "technical_detail": "Backend Dev agent exceeded timeout on task 'implement_auth'",
    "context": {
        "agent_id": "backend_dev",
        "task_id": "task_auth",
        "timeout_seconds": 600,
        "elapsed_seconds": 612
    },
    "timestamp": "2025-11-01T02:30:00Z",
    "project_id": "project_123",
    "agent_id": "backend_dev",
    "task_id": "task_auth",
    "recoverable": true,
    "recovery_strategy": "retry"
}
```

---

## 3. Error Logging

### Log Format

```python
import logging
import json
from datetime import datetime

class ErrorLogger:
    def __init__(self):
        self.logger = logging.getLogger("helix.errors")
    
    def log_error(
        self,
        code: int,
        category: str,
        message: str,
        technical_detail: str,
        context: dict = None,
        project_id: str = None,
        agent_id: str = None,
        task_id: str = None
    ):
        """Log structured error"""
        
        error_data = {
            "code": code,
            "category": category,
            "message": message,
            "technical_detail": technical_detail,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": project_id,
            "agent_id": agent_id,
            "task_id": task_id
        }
        
        # Log as JSON for easy parsing
        self.logger.error(json.dumps(error_data))
        
        # Also store in database for querying
        asyncio.create_task(self.store_error_in_db(error_data))
    
    async def store_error_in_db(self, error_data: dict):
        """Store error in database for analytics"""
        await db.execute(
            """
            INSERT INTO error_log 
                (code, category, message, technical_detail, context, 
                 project_id, agent_id, task_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            error_data['code'],
            error_data['category'],
            error_data['message'],
            error_data['technical_detail'],
            json.dumps(error_data['context']),
            error_data['project_id'],
            error_data['agent_id'],
            error_data['task_id']
        )
```

### Database Schema: `error_log` Table

```sql
CREATE TABLE error_log (
    id BIGSERIAL PRIMARY KEY,
    code INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    technical_detail TEXT,
    context JSONB,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    agent_id VARCHAR(100),
    task_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_error_log_code ON error_log(code);
CREATE INDEX idx_error_log_category ON error_log(category);
CREATE INDEX idx_error_log_project ON error_log(project_id);
CREATE INDEX idx_error_log_timestamp ON error_log(created_at);
```

---

## 4. Recovery Strategies

### Recovery Decision Tree

```
Error Occurs
    ↓
Is it recoverable?
    ↓
YES → What type?
    ↓
    ├─ Transient (network, API rate limit)
    │   → Automatic retry with backoff (3x)
    │   → If still fails → Gate
    │
    ├─ Agent failure (timeout, loop)
    │   → Agent retry (orchestrator assigns different approach)
    │   → If still fails → Gate
    │
    ├─ Resource constraint (disk, memory)
    │   → Clean up resources
    │   → Retry once
    │   → If still fails → Gate
    │
    └─ Configuration error
        → Gate immediately (needs human fix)

NO → Gate immediately
```

### Recovery Implementation

```python
class ErrorRecoveryManager:
    async def handle_error(self, error: SystemError):
        """Handle error with appropriate recovery strategy"""
        
        if not error.recoverable:
            # Non-recoverable, gate immediately
            await self.trigger_gate(error)
            return
        
        if error.category == "external":
            # External service errors: retry with backoff
            await self.retry_with_backoff(error, max_retries=3)
        
        elif error.category == "agent":
            if error.code == 1001:  # Timeout
                # Try with different agent or approach
                await self.retry_with_different_approach(error)
            elif error.code == 1002:  # Loop detected
                # Already retried 3 times, gate
                await self.trigger_gate(error)
            else:
                # Other agent errors: retry once
                await self.retry_once(error)
        
        elif error.category == "resource":
            # Clean up and retry
            await self.cleanup_resources()
            await self.retry_once(error)
        
        elif error.category == "system":
            # System errors usually need human intervention
            await self.trigger_gate(error)
        
        else:
            # Unknown, gate for safety
            await self.trigger_gate(error)
    
    async def retry_with_backoff(self, error: SystemError, max_retries: int = 3):
        """Retry with exponential backoff"""
        for attempt in range(max_retries):
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
            
            try:
                # Retry the operation
                await self.retry_operation(error)
                return  # Success
            except Exception as e:
                if attempt == max_retries - 1:
                    # Max retries exceeded, gate
                    await self.trigger_gate(error)
```

---

## 5. User-Facing Error Messages

### Message Guidelines

**Principles**:
- Clear and actionable
- No technical jargon
- Suggest next steps
- Don't blame the user

### Error Message Templates

```python
ERROR_MESSAGES = {
    1001: {
        "title": "Task Timeout",
        "message": "The agent took longer than expected to complete this task.",
        "action": "We'll try a different approach. You can also review the progress so far."
    },
    1002: {
        "title": "Agent Stuck",
        "message": "The agent encountered the same issue multiple times.",
        "action": "We need your input to continue. Please review the error and provide guidance."
    },
    2001: {
        "title": "System Error",
        "message": "Something went wrong with the system.",
        "action": "We're working on it. Your project progress has been saved."
    },
    3001: {
        "title": "AI Service Unavailable",
        "message": "We're having trouble connecting to the AI service.",
        "action": "We'll retry automatically. This usually resolves quickly."
    },
    4001: {
        "title": "Invalid Configuration",
        "message": "There's an issue with your project settings.",
        "action": "Please check your project configuration and try again."
    },
    5001: {
        "title": "Storage Full",
        "message": "We've run out of storage space for this project.",
        "action": "Please free up some space or contact support."
    }
}
```

### Frontend Error Display

```javascript
function ErrorNotification({ error }) {
    const template = ERROR_MESSAGES[error.code] || {
        title: "Error",
        message: error.message,
        action: "Please try again or contact support."
    };
    
    return (
        <div className="error-notification">
            <div className="error-icon">⚠️</div>
            <div className="error-content">
                <h3>{template.title}</h3>
                <p>{template.message}</p>
                <p className="error-action">{template.action}</p>
                {error.code && (
                    <p className="error-code">Error Code: {error.code}</p>
                )}
            </div>
            <button onClick={() => dismissError(error.id)}>×</button>
        </div>
    );
}
```

---

## 6. Error Reporting

### API Endpoints

```python
@router.get("/api/errors")
async def get_errors(
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[datetime] = None,
    limit: int = 50
):
    """Get error history"""
    
    query = "SELECT * FROM error_log WHERE 1=1"
    params = []
    
    if project_id:
        query += " AND project_id = $1"
        params.append(project_id)
    
    if category:
        query += f" AND category = ${len(params) + 1}"
        params.append(category)
    
    if start_date:
        query += f" AND created_at >= ${len(params) + 1}"
        params.append(start_date)
    
    query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
    params.append(limit)
    
    errors = await db.fetch(query, *params)
    return {"errors": errors}

@router.get("/api/errors/stats")
async def get_error_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get error statistics"""
    
    stats = await db.fetch(
        """
        SELECT 
            category,
            code,
            COUNT(*) as count
        FROM error_log
        WHERE created_at >= $1 AND created_at < $2
        GROUP BY category, code
        ORDER BY count DESC
        """,
        start_date or datetime.now() - timedelta(days=7),
        end_date or datetime.now()
    )
    
    return {"stats": stats}
```

---

## 7. Error Monitoring

### Key Metrics

- **Error rate**: Errors per hour/day
- **Error distribution**: By category and code
- **Recovery success rate**: % of errors auto-recovered
- **Gate trigger rate**: % of errors requiring human intervention
- **Mean time to recovery**: Average time to resolve errors

### Alerting Thresholds

```python
ALERT_THRESHOLDS = {
    "error_rate": 100,  # Errors per hour
    "gate_rate": 0.3,   # 30% of errors trigger gates
    "recovery_failure_rate": 0.5,  # 50% of retries fail
    "critical_errors": 1  # Any critical system error
}

@scheduler.scheduled_job('interval', minutes=5)
async def check_error_thresholds():
    """Monitor error rates and alert if thresholds exceeded"""
    
    # Get error rate for last hour
    error_count = await db.fetchval(
        """
        SELECT COUNT(*) FROM error_log
        WHERE created_at >= NOW() - INTERVAL '1 hour'
        """
    )
    
    if error_count > ALERT_THRESHOLDS['error_rate']:
        await send_alert(
            f"High error rate: {error_count} errors in last hour"
        )
```

---

## 8. Data Retention

### Error Log Retention

**Policy**: Rolling 90-day retention
- Keep detailed error logs for 90 days
- After 90 days, aggregate to daily summaries
- Keep summaries for 1 year

```python
@scheduler.scheduled_job('cron', hour=2, minute=0)
async def cleanup_old_errors():
    """Archive and clean up old error logs"""
    
    cutoff_date = datetime.now() - timedelta(days=90)
    
    # Aggregate old errors to daily summaries
    await db.execute(
        """
        INSERT INTO error_log_summary (date, category, code, count)
        SELECT 
            DATE(created_at),
            category,
            code,
            COUNT(*)
        FROM error_log
        WHERE created_at < $1
        GROUP BY DATE(created_at), category, code
        ON CONFLICT (date, category, code) DO UPDATE
        SET count = error_log_summary.count + EXCLUDED.count
        """,
        cutoff_date
    )
    
    # Delete old detailed logs
    result = await db.execute(
        "DELETE FROM error_log WHERE created_at < $1",
        cutoff_date
    )
    
    logger.info(f"Archived {result} old error logs")
```

---

## Rationale

### Why Hierarchical Taxonomy?
- Easy to understand and maintain
- Allows grouping by category
- Supports detailed error codes
- Extensible for new error types

### Why Automatic Recovery?
- Reduces human intervention
- Improves user experience
- Handles transient failures gracefully
- Falls back to gate when needed

### Why User-Friendly Messages?
- Technical details confuse users
- Clear actions reduce support burden
- Builds trust in the system
- Industry best practice

### Why 90-Day Retention?
- Sufficient for debugging and analysis
- Balances storage cost and utility
- Aggregated summaries for long-term trends
- Complies with typical data retention policies

---

## Related Decisions

- **All decisions**: Error handling applies system-wide
- **Decision 74**: Loop detection (error code 1002)
- **Decision 77**: GitHub Specialist (error code 3002)
- **Decision 78**: Container management (error code 2003)

---

## Tasks Created

### Phase 6: Error Handling (Week 12)
- [ ] **Task 6.3.1**: Create `error_log` table and summary table
- [ ] **Task 6.3.2**: Implement `ErrorLogger` service
- [ ] **Task 6.3.3**: Implement `ErrorRecoveryManager`
- [ ] **Task 6.3.4**: Create error message templates
- [ ] **Task 6.3.5**: Implement error monitoring and alerting
- [ ] **Task 6.3.6**: Create error dashboard in frontend
- [ ] **Task 6.3.7**: Implement error log cleanup job

---

## Approval

**Approved By**: User (via best judgment delegation)  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
