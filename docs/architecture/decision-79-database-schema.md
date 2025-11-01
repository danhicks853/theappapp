# Decision 79: Database Schema Comprehensive Design

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P0 - BLOCKING  
**Depends On**: All architectural decisions

---

## Context

Multiple decisions have defined individual tables, but no unified database schema exists. This decision consolidates all table definitions, relationships, indexes, and migration strategy into a comprehensive database design.

---

## Decision Summary

### Core Approach
- **PostgreSQL**: Primary database for all structured data
- **Qdrant**: Vector database for RAG embeddings (separate system)
- **Normalized schema**: Proper foreign keys and relationships
- **Indexed for performance**: Strategic indexes on common queries
- **Migration-based**: Alembic for schema versioning
- **Data retention**: Automated cleanup jobs for old data

---

## Complete Database Schema

### 1. Core Tables

#### `users` Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
```

#### `projects` Table
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(50) NOT NULL,  -- python, nodejs, java, etc.
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, paused, completed, failed
    current_stage VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created ON projects(created_at);
```

#### `project_state` Table
```sql
CREATE TABLE project_state (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE UNIQUE,
    current_task_id VARCHAR(100),
    current_agent_id VARCHAR(100),
    last_action TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    metadata JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_project_state_project ON project_state(project_id);
CREATE INDEX idx_project_state_status ON project_state(status);
```

---

### 2. LLM & Cost Tracking Tables

#### `llm_pricing` Table
```sql
CREATE TABLE llm_pricing (
    id SERIAL PRIMARY KEY,
    model VARCHAR(100) NOT NULL UNIQUE,
    input_cost_per_million DECIMAL(10, 6) NOT NULL,
    output_cost_per_million DECIMAL(10, 6) NOT NULL,
    effective_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(100),
    notes TEXT
);

-- Initial pricing data
INSERT INTO llm_pricing (model, input_cost_per_million, output_cost_per_million) VALUES
('gpt-4', 30.00, 60.00),
('gpt-4-turbo', 10.00, 30.00),
('gpt-3.5-turbo', 0.50, 1.50),
('gpt-3.5-turbo-16k', 3.00, 4.00);
```

#### `llm_token_usage` Table
```sql
CREATE TABLE llm_token_usage (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_token_usage_timestamp ON llm_token_usage(timestamp);
CREATE INDEX idx_token_usage_project ON llm_token_usage(project_id);
CREATE INDEX idx_token_usage_agent ON llm_token_usage(agent_id);
CREATE INDEX idx_token_usage_project_agent ON llm_token_usage(project_id, agent_id);
CREATE INDEX idx_token_usage_model ON llm_token_usage(model);
```

---

### 3. Prompt Management Tables

#### `prompts` Table
```sql
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(100) NOT NULL,  -- orchestrator, backend_dev, etc.
    version VARCHAR(50) NOT NULL,  -- Semantic version (e.g., 1.2.3)
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    notes TEXT,
    UNIQUE(agent_type, version)
);

CREATE INDEX idx_prompts_agent_type ON prompts(agent_type);
CREATE INDEX idx_prompts_active ON prompts(agent_type, is_active);
```

#### `prompt_test_results` Table
```sql
CREATE TABLE prompt_test_results (
    id SERIAL PRIMARY KEY,
    prompt_id INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    passed BOOLEAN NOT NULL,
    score DECIMAL(5, 2),  -- 0.00 to 100.00
    output TEXT,
    evaluator VARCHAR(100),  -- Which evaluator ran this test
    tested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_tests_prompt ON prompt_test_results(prompt_id);
CREATE INDEX idx_prompt_tests_date ON prompt_test_results(tested_at);
```

---

### 4. Tool Access Service Tables

#### `agent_permissions` Table
```sql
CREATE TABLE agent_permissions (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_type, tool_name)
);

CREATE INDEX idx_agent_permissions_agent ON agent_permissions(agent_type);
```

#### `tool_audit_log` Table
```sql
CREATE TABLE tool_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    agent_id VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    allowed BOOLEAN NOT NULL,
    parameters JSONB,
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tool_audit_timestamp ON tool_audit_log(timestamp);
CREATE INDEX idx_tool_audit_project ON tool_audit_log(project_id);
CREATE INDEX idx_tool_audit_agent ON tool_audit_log(agent_id);
CREATE INDEX idx_tool_audit_tool ON tool_audit_log(tool_name);
```

---

### 5. GitHub Integration Tables

#### `github_credentials` Table
```sql
CREATE TABLE github_credentials (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    access_token TEXT NOT NULL,  -- Encrypted
    refresh_token TEXT NOT NULL,  -- Encrypted
    token_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_github_creds_user ON github_credentials(user_id);
```

---

### 6. Error Handling Tables

#### `error_log` Table
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

#### `error_log_summary` Table
```sql
CREATE TABLE error_log_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    code INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(date, category, code)
);

CREATE INDEX idx_error_summary_date ON error_log_summary(date);
```

---

### 7. Project Lifecycle Tables

#### `cancelled_projects` Table
```sql
CREATE TABLE cancelled_projects (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    stage VARCHAR(100),
    cancelled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reason TEXT,
    metadata JSONB
);

CREATE INDEX idx_cancelled_projects_user ON cancelled_projects(cancelled_by);
CREATE INDEX idx_cancelled_projects_date ON cancelled_projects(cancelled_at);
```

#### `archived_projects` Table
```sql
CREATE TABLE archived_projects (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(50),
    completed_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archive_path TEXT,  -- Path to archived files
    metadata JSONB
);

CREATE INDEX idx_archived_projects_user ON archived_projects(user_id);
CREATE INDEX idx_archived_projects_date ON archived_projects(archived_at);
```

---

### 8. RAG Knowledge Tables

#### `rag_knowledge` Table
```sql
CREATE TABLE rag_knowledge (
    id SERIAL PRIMARY KEY,
    knowledge_type VARCHAR(50) NOT NULL,  -- pattern, failure, solution, etc.
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding_id VARCHAR(255),  -- Reference to Qdrant vector
    source VARCHAR(100),  -- manual, checkpoint, agent_learning
    quality_score DECIMAL(3, 2),  -- 0.00 to 1.00
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- NULL = never expires
);

CREATE INDEX idx_rag_knowledge_type ON rag_knowledge(knowledge_type);
CREATE INDEX idx_rag_knowledge_created ON rag_knowledge(created_at);
CREATE INDEX idx_rag_knowledge_expires ON rag_knowledge(expires_at);
```

---

## Entity Relationship Diagram

```
users
  ├─→ projects (1:N)
  │    ├─→ project_state (1:1)
  │    ├─→ llm_token_usage (1:N)
  │    ├─→ tool_audit_log (1:N)
  │    └─→ error_log (1:N)
  ├─→ github_credentials (1:1)
  ├─→ cancelled_projects (1:N)
  └─→ archived_projects (1:N)

prompts
  └─→ prompt_test_results (1:N)

agent_permissions (standalone)
llm_pricing (standalone)
rag_knowledge (standalone, links to Qdrant)
error_log_summary (standalone)
```

---

## Index Strategy

### Performance Indexes

**High-frequency queries**:
- User lookups by email
- Project lookups by user
- Token usage by project/agent/time
- Error logs by project/time
- Tool audit by project/agent

**Composite indexes**:
- `(project_id, agent_id)` on `llm_token_usage`
- `(agent_type, is_active)` on `prompts`
- `(agent_type, tool_name)` on `agent_permissions`

**Time-series indexes**:
- All `timestamp` and `created_at` fields
- Supports efficient time-range queries
- Enables cleanup jobs

---

## Migration Strategy

### Alembic Configuration

```python
# alembic/env.py
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.database import Base

config = context.config
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

### Migration Workflow

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Review migration file
# Edit alembic/versions/xxxx_add_new_table.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Initial Migration

```python
# alembic/versions/001_initial_schema.py
def upgrade():
    # Create all tables in order
    op.create_table('users', ...)
    op.create_table('projects', ...)
    op.create_table('project_state', ...)
    # ... etc
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    # ... etc
    
    # Insert initial data
    op.execute("""
        INSERT INTO llm_pricing (model, input_cost_per_million, output_cost_per_million)
        VALUES ('gpt-4', 30.00, 60.00)
    """)

def downgrade():
    # Drop in reverse order
    op.drop_table('error_log_summary')
    op.drop_table('error_log')
    # ... etc
```

---

## Data Retention Policies

### Automated Cleanup Jobs

```python
@scheduler.scheduled_job('cron', hour=2, minute=0)
async def daily_cleanup():
    """Run all cleanup jobs daily at 2 AM"""
    
    cutoff_1_year = datetime.now() - timedelta(days=365)
    cutoff_90_days = datetime.now() - timedelta(days=90)
    
    # 1. Clean up old token usage (1 year)
    await db.execute(
        "DELETE FROM llm_token_usage WHERE timestamp < $1",
        cutoff_1_year
    )
    
    # 2. Clean up old tool audit logs (1 year)
    await db.execute(
        "DELETE FROM tool_audit_log WHERE timestamp < $1",
        cutoff_1_year
    )
    
    # 3. Archive and clean up old error logs (90 days)
    await db.execute("""
        INSERT INTO error_log_summary (date, category, code, count)
        SELECT DATE(created_at), category, code, COUNT(*)
        FROM error_log
        WHERE created_at < $1
        GROUP BY DATE(created_at), category, code
        ON CONFLICT (date, category, code) DO UPDATE
        SET count = error_log_summary.count + EXCLUDED.count
    """, cutoff_90_days)
    
    await db.execute(
        "DELETE FROM error_log WHERE created_at < $1",
        cutoff_90_days
    )
    
    # 4. Clean up expired RAG knowledge
    await db.execute(
        "DELETE FROM rag_knowledge WHERE expires_at < NOW()"
    )
    
    logger.info("Daily cleanup completed")
```

### Retention Summary

| Table | Retention | Cleanup Strategy |
|-------|-----------|------------------|
| `llm_token_usage` | 1 year | Delete old records |
| `tool_audit_log` | 1 year | Delete old records |
| `error_log` | 90 days | Archive to summary, then delete |
| `error_log_summary` | 1 year | Delete old summaries |
| `rag_knowledge` | Variable | Delete expired (per `expires_at`) |
| `prompt_test_results` | Indefinite | Keep all (small volume) |
| `cancelled_projects` | Indefinite | Keep all (analytics) |
| `archived_projects` | Indefinite | Keep metadata (files archived separately) |

---

## Database Configuration

### Connection Pool Settings

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,  # Connection pool size
    max_overflow=10,  # Additional connections if pool exhausted
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600  # Recycle connections after 1 hour
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

### Environment Variables

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/helix
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

---

## Backup Strategy

### Automated Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/helix"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/helix_backup_$DATE.sql"

# Create backup
pg_dump -h localhost -U helix_user helix > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### Backup Schedule

- **Daily**: Full database backup
- **Retention**: 30 days of daily backups
- **Storage**: Encrypted backup storage
- **Testing**: Monthly restore test

---

## Performance Optimization

### Query Optimization Tips

```sql
-- Use EXPLAIN ANALYZE to check query performance
EXPLAIN ANALYZE
SELECT * FROM llm_token_usage
WHERE project_id = 'xxx' AND timestamp >= NOW() - INTERVAL '7 days';

-- Use covering indexes for common queries
CREATE INDEX idx_token_usage_project_time_covering 
ON llm_token_usage(project_id, timestamp) 
INCLUDE (agent_id, model, input_tokens, output_tokens);

-- Partition large tables by time (if needed in future)
CREATE TABLE llm_token_usage_2025_11 PARTITION OF llm_token_usage
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### Monitoring Queries

```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY idx_tup_read DESC;

-- Check table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Security Considerations

### Encryption

```python
# Encrypt sensitive fields (GitHub tokens)
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

### Access Control

```sql
-- Create read-only user for analytics
CREATE USER helix_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE helix TO helix_readonly;
GRANT USAGE ON SCHEMA public TO helix_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO helix_readonly;

-- Create application user with limited permissions
CREATE USER helix_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE helix TO helix_app;
GRANT USAGE, CREATE ON SCHEMA public TO helix_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO helix_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO helix_app;
```

---

## Rationale

### Why PostgreSQL?
- Robust ACID compliance
- Excellent JSON support (JSONB)
- Strong indexing capabilities
- Mature ecosystem and tooling
- Supports all our data types

### Why Normalized Schema?
- Data integrity through foreign keys
- Reduces redundancy
- Easier to maintain and update
- Standard relational design

### Why Alembic?
- Industry-standard migration tool
- Version control for schema
- Supports rollbacks
- Integrates with SQLAlchemy

### Why Automated Cleanup?
- Prevents database bloat
- Manages storage costs
- Maintains query performance
- Complies with retention policies

---

## Related Decisions

- **Decision 69**: Prompt versioning (prompts tables)
- **Decision 71**: Tool Access Service (permissions and audit tables)
- **Decision 75**: Cost tracking (pricing and token usage tables)
- **Decision 76**: State recovery (project_state table)
- **Decision 77**: GitHub integration (github_credentials table)
- **Decision 80**: Error handling (error_log tables)
- **Decision 81**: Cancellation (cancelled_projects table)

---

## Tasks Created

### Phase 6: Database Setup (Week 12)
- [ ] **Task 6.2.1**: Set up PostgreSQL database and users
- [ ] **Task 6.2.2**: Configure Alembic for migrations
- [ ] **Task 6.2.3**: Create initial migration with all tables
- [ ] **Task 6.2.4**: Create all indexes
- [ ] **Task 6.2.5**: Insert initial data (pricing, permissions)
- [ ] **Task 6.2.6**: Set up automated backup script
- [ ] **Task 6.2.7**: Implement cleanup jobs
- [ ] **Task 6.2.8**: Configure connection pooling
- [ ] **Task 6.2.9**: Set up database monitoring

---

## Approval

**Approved By**: User (via best judgment delegation)  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
