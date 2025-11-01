# Decision 75: Cost Tracking System Implementation

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P1 - HIGH  
**Depends On**: Decision 45 (cost tracking), Database schema, Decision 73 (API spec)

---

## Context

Decision 45 specifies "EVERY LLM call inspected and logged" for cost tracking. The system needs to track token usage and costs across projects and agents to provide visibility into LLM spending.

---

## Decision Summary

### Core Approach
- **Store token counts only** (not pre-calculated costs)
- **Calculate costs on-demand** when dashboard loads
- **Track by project and agent** (no task-level granularity)
- **Manual pricing management** via frontend settings
- **1-year rolling retention** for all data

---

## 1. Token Usage Logging Schema

### Database Table: `llm_token_usage`

```sql
CREATE TABLE llm_token_usage (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id UUID NOT NULL REFERENCES projects(id),
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
```

---

## 2. Pricing Matrix Schema

### Database Table: `llm_pricing`

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

INSERT INTO llm_pricing (model, input_cost_per_million, output_cost_per_million) VALUES
('gpt-4', 30.00, 60.00),
('gpt-4-turbo', 10.00, 30.00),
('gpt-3.5-turbo', 0.50, 1.50);
```

---

## 3. Cost Calculation Strategy

### On-Demand Calculation

**Formula**:
```
cost = (input_tokens / 1,000,000 * input_cost_per_million) + 
       (output_tokens / 1,000,000 * output_cost_per_million)
```

### Query Examples

```sql
-- Cost by project
SELECT 
    p.name,
    SUM(
        (tu.input_tokens::DECIMAL / 1000000 * lp.input_cost_per_million) +
        (tu.output_tokens::DECIMAL / 1000000 * lp.output_cost_per_million)
    ) AS total_cost
FROM llm_token_usage tu
JOIN projects p ON tu.project_id = p.id
JOIN llm_pricing lp ON tu.model = lp.model
WHERE tu.timestamp >= $1 AND tu.timestamp < $2
GROUP BY p.name;

-- Cost by agent
SELECT 
    tu.agent_id,
    SUM(
        (tu.input_tokens::DECIMAL / 1000000 * lp.input_cost_per_million) +
        (tu.output_tokens::DECIMAL / 1000000 * lp.output_cost_per_million)
    ) AS total_cost
FROM llm_token_usage tu
JOIN llm_pricing lp ON tu.model = lp.model
WHERE tu.timestamp >= $1 AND tu.timestamp < $2
GROUP BY tu.agent_id;

-- Cost by agent per project (drill-down)
SELECT 
    p.name AS project_name,
    tu.agent_id,
    SUM(
        (tu.input_tokens::DECIMAL / 1000000 * lp.input_cost_per_million) +
        (tu.output_tokens::DECIMAL / 1000000 * lp.output_cost_per_million)
    ) AS total_cost
FROM llm_token_usage tu
JOIN projects p ON tu.project_id = p.id
JOIN llm_pricing lp ON tu.model = lp.model
WHERE tu.timestamp >= $1 AND tu.timestamp < $2
GROUP BY p.name, tu.agent_id;
```

---

## 4. LLM Adapter Integration

### Token Capture Implementation

```python
class LLMAdapter:
    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
    
    async def call_llm(
        self,
        prompt: str,
        model: str,
        project_id: str,
        agent_id: str,
        **kwargs
    ) -> LLMResponse:
        # Make LLM call
        response = await self._make_api_call(prompt, model, **kwargs)
        
        # Extract token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Log to database (non-blocking)
        await self.cost_tracker.log_usage(
            project_id=project_id,
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        return response

class CostTracker:
    async def log_usage(
        self,
        project_id: str,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ):
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO llm_token_usage 
                        (project_id, agent_id, model, input_tokens, output_tokens)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    project_id, agent_id, model, input_tokens, output_tokens
                )
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")
            # Don't fail LLM call if logging fails
```

---

## 5. Pricing Matrix Management

### Frontend Settings Page: `/settings/pricing`

**Features**:
- List all models with pricing
- Edit input/output costs
- Add new models
- Manual entry only

### API Endpoints

```python
@router.get("/api/pricing")
async def get_pricing():
    pricing = await db.fetch("SELECT * FROM llm_pricing ORDER BY model")
    return {"pricing": pricing}

@router.put("/api/pricing/{model}")
async def update_pricing(model: str, pricing: PricingUpdate):
    await db.execute(
        """
        UPDATE llm_pricing 
        SET input_cost_per_million = $1,
            output_cost_per_million = $2,
            updated_at = NOW()
        WHERE model = $3
        """,
        pricing.input_cost, pricing.output_cost, model
    )
    return {"success": True}

@router.post("/api/pricing")
async def add_pricing(pricing: NewPricing):
    await db.execute(
        """
        INSERT INTO llm_pricing 
            (model, input_cost_per_million, output_cost_per_million)
        VALUES ($1, $2, $3)
        """,
        pricing.model, pricing.input_cost, pricing.output_cost
    )
    return {"success": True}
```

---

## 6. Cost Dashboard

### Frontend Dashboard: `/dashboard/costs`

**Time Ranges**:
- Last Hour
- Last Day
- Last Week
- Last Month
- Last Quarter
- Last Year

**Visualizations**:
1. **Overview Cards**: Total cost, tokens, calls
2. **Line Chart**: Cost over time
3. **Bar Chart**: Cost by project
4. **Pie Chart**: Cost by agent
5. **Bar Chart**: Cost by model
6. **Table**: Cost by agent per project (drill-down)

### API Endpoints

```python
@router.get("/api/costs/summary")
async def get_cost_summary(start_time: datetime, end_time: datetime):
    result = await db.fetchrow(
        """
        SELECT 
            SUM(
                (tu.input_tokens::DECIMAL / 1000000 * lp.input_cost_per_million) +
                (tu.output_tokens::DECIMAL / 1000000 * lp.output_cost_per_million)
            ) AS total_cost,
            SUM(tu.input_tokens + tu.output_tokens) AS total_tokens,
            COUNT(*) AS total_calls
        FROM llm_token_usage tu
        JOIN llm_pricing lp ON tu.model = lp.model
        WHERE tu.timestamp >= $1 AND tu.timestamp < $2
        """,
        start_time, end_time
    )
    return result

@router.get("/api/costs/by-project")
async def get_costs_by_project(start_time: datetime, end_time: datetime):
    # Returns cost grouped by project

@router.get("/api/costs/by-agent")
async def get_costs_by_agent(start_time: datetime, end_time: datetime):
    # Returns cost grouped by agent

@router.get("/api/costs/by-agent-per-project")
async def get_costs_by_agent_per_project(start_time: datetime, end_time: datetime):
    # Returns cost grouped by agent per project (drill-down)

@router.get("/api/costs/over-time")
async def get_cost_over_time(start_time: datetime, end_time: datetime, bucket: str):
    # Returns time series data for line chart
```

---

## 7. Data Retention Policy

### Rolling 1-Year Retention

```python
async def cleanup_old_token_usage():
    cutoff_date = datetime.now() - timedelta(days=365)
    result = await db.execute(
        "DELETE FROM llm_token_usage WHERE timestamp < $1",
        cutoff_date
    )
    logger.info(f"Deleted {result} old token usage records")

# Run daily at 2 AM
@scheduler.scheduled_job('cron', hour=2, minute=0)
async def daily_cleanup():
    await cleanup_old_token_usage()
```

---

## Rationale

### Why Store Token Counts Only?
- Pricing updates automatically apply to all historical data
- No need to recalculate stored costs when pricing changes
- Simpler schema

### Why On-Demand Calculation?
- Dashboard loads are infrequent (admin-only)
- Query performance is acceptable with proper indexes
- Always accurate with current pricing

### Why Manual Pricing Only?
- Pricing changes are infrequent
- Simple to implement and maintain
- No external API dependencies

### Why 1-Year Retention?
- Consistent with other retention policies (Decision 68, 71)
- Sufficient for cost analysis and trends
- Keeps database size manageable

---

## Tasks Created

### Phase 4: Frontend (Week 9)
- [ ] **Task 4.6.1**: Create pricing management settings page
- [ ] **Task 4.6.2**: Create cost dashboard with visualizations
- [ ] **Task 4.6.3**: Implement time range selector and data loading

### Phase 6: Backend (Week 12)
- [ ] **Task 6.2.1**: Create `llm_token_usage` and `llm_pricing` tables
- [ ] **Task 6.2.2**: Implement `CostTracker` service
- [ ] **Task 6.2.3**: Integrate token logging into LLM adapters
- [ ] **Task 6.2.4**: Implement cost calculation API endpoints
- [ ] **Task 6.2.5**: Implement pricing management API endpoints
- [ ] **Task 6.2.6**: Create daily cleanup job for old data

### Phase 6: Testing (Week 12)
- [ ] **Task 6.6.9**: Test token usage logging
- [ ] **Task 6.6.10**: Test cost calculation accuracy
- [ ] **Task 6.6.11**: Test dashboard performance with large datasets

---

## Related Decisions

- **Decision 45**: Cost tracking requirement
- **Decision 73**: API specification for cost endpoints
- **Decision 68**: 1-year retention policy pattern

---

## Approval

**Approved By**: User  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
