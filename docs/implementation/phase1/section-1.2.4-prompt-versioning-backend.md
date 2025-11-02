# Section 1.2.4: Prompt Versioning System (Backend)

**Implementation Date**: November 2, 2025  
**Status**: ✅ Backend Complete, ⏳ Frontend UI Pending

---

## What Was Built

Complete backend system for prompt versioning with semantic versioning, caching, and management capabilities.

---

## Files Created

### 1. PromptLoadingService
**File**: `backend/services/prompt_loading_service.py` (~110 lines)

**Purpose**: Load active prompts with automatic caching

**Methods**:
- `get_active_prompt(agent_type)` - Get active prompt with 5-minute cache
- `clear_cache(agent_type)` - Force reload from DB
- `get_cache_stats()` - Get cache statistics

**Features**:
- Automatic 5-minute TTL cache
- Per-agent-type caching
- Cache hit/miss logging
- Error handling for missing prompts

---

### 2. PromptManagementService
**File**: `backend/services/prompt_management_service.py` (~240 lines)

**Purpose**: Manage prompt versions with semantic versioning

**Methods**:
- `create_version()` - Create new version with validation
- `promote_to_active()` - Make version active (one per agent)
- `create_patch()` - Auto-increment patch version
- `get_versions()` - List all versions for agent
- `get_prompt_content()` - Get specific version content

**Features**:
- Semantic versioning (major.minor.patch)
- Version format validation (regex)
- Fix-forward only (no rollback)
- Independent versioning per agent type
- UNIQUE constraint enforcement
- Automatic patch incrementing

**Versioning Logic**:
```python
# Current: 1.0.0
await service.create_patch(...)  # Creates 1.0.1
await service.create_patch(...)  # Creates 1.0.2
```

---

### 3. Prompt Management API
**File**: `backend/api/routes/prompts.py` (~240 lines)

**8 Endpoints Created**:

1. **POST /api/v1/prompts/versions**
   - Create new version
   - Body: agent_type, version, prompt_text, created_by, notes
   - Validation: Semantic version format
   - Error: 400 if version exists

2. **POST /api/v1/prompts/patch**
   - Create patch (auto-increment)
   - Body: agent_type, prompt_text, created_by, notes
   - Auto-promotes to active
   - Error: 404 if no active version

3. **POST /api/v1/prompts/promote**
   - Promote version to active
   - Body: agent_type, version
   - Deactivates all others for that agent
   - Error: 404 if version not found

4. **GET /api/v1/prompts/{agent_type}/versions**
   - List all versions for agent
   - Returns: Array of version objects
   - Sorted by created_at DESC

5. **GET /api/v1/prompts/{agent_type}/active**
   - Get currently active prompt
   - Returns: Full prompt content with version
   - Error: 404 if no active

6. **GET /api/v1/prompts/{agent_type}/{version}**
   - Get specific version
   - Returns: Prompt content
   - Error: 404 if not found

7. **DELETE /api/v1/prompts/cache/{agent_type}**
   - Clear cache for agent
   - Forces reload from DB
   - Returns: Success status

**Models**:
- `CreateVersionRequest` (Pydantic)
- `CreatePatchRequest` (Pydantic)
- `PromoteRequest` (Pydantic)
- `VersionResponse` (Pydantic)
- `PromptContentResponse` (Pydantic)

---

### 4. Dependencies
**File**: `backend/api/dependencies.py` (modified)

**Added**:
- `get_prompt_loading_service()` dependency
- `get_prompt_management_service()` dependency
- Imports for both services

---

### 5. Router Registration
**File**: `backend/api/__init__.py` (modified)

**Changes**:
- Imported prompts router
- Registered prompts.router with FastAPI app

---

## Database Integration

**Table**: `prompts` (Migration 013)

**Schema**:
```sql
CREATE TABLE prompts (
    id UUID PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    notes TEXT,
    UNIQUE(agent_type, version)
);
```

**Indexes**:
- idx_prompts_agent_type (agent_type)
- idx_prompts_active (agent_type, is_active)
- idx_prompts_created (created_at)

**Constraints**:
- UNIQUE(agent_type, version) - No duplicate versions per agent
- One is_active per agent_type (enforced by promote_to_active)

---

## Example Usage

### Create New Version
```bash
POST /api/v1/prompts/versions
{
    "agent_type": "backend_dev",
    "version": "1.1.0",
    "prompt_text": "You are an expert Python backend developer...",
    "created_by": "user-1",
    "notes": "Added error handling guidelines"
}
```

### Create Patch (Auto-Increment)
```bash
POST /api/v1/prompts/patch
{
    "agent_type": "backend_dev",
    "prompt_text": "Fixed typo in instructions...",
    "created_by": "user-1",
    "notes": "Fixed documentation typo"
}
# If active was 1.1.0, creates and activates 1.1.1
```

### Promote Version
```bash
POST /api/v1/prompts/promote
{
    "agent_type": "backend_dev",
    "version": "1.2.0"
}
```

### Get Active Prompt (Python)
```python
loading_svc = PromptLoadingService(engine)
prompt = await loading_svc.get_active_prompt("backend_dev")
# Cached for 5 minutes
```

---

## Still Needed (Frontend UI)

### 1. PromptEditor Component
**File**: `frontend/src/pages/PromptEditor.tsx`

**Features**:
- Monaco code editor
- Syntax highlighting
- Version metadata input (notes)
- Save as new version button
- Preview mode
- Version selector to edit from

### 2. A/B Testing Lab
**File**: `frontend/src/pages/ABTestingLab.tsx`

**Features**:
- Select 2 versions to compare
- Test case input/management
- Run comparison button
- Side-by-side results
- Performance metrics
- Winner selection

### 3. PromptComparison Component
**File**: `frontend/src/components/PromptComparison.tsx`

**Features**:
- Two-column layout
- Diff highlighting (additions/deletions)
- Character/line count
- Performance comparison
- Quick promote button

### 4. PromptHistory Viewer
**File**: `frontend/src/components/PromptHistory.tsx`

**Features**:
- Table of all versions
- Sortable by date
- Filter by agent
- Active indicator
- Click to view full prompt
- Quick promote action

### 5. Agent Integration
**File**: `backend/agents/base_agent.py` (modify)

**Change**: Load prompts from DB instead of hardcoded constants

```python
# Current (hardcoded):
BACKEND_DEV_SYSTEM_PROMPT = """You are..."""

# New (from DB):
def __init__(self, ...):
    prompt_loader = PromptLoadingService(engine)
    self.system_prompt = await prompt_loader.get_active_prompt(self.agent_type)
```

---

## Semantic Versioning Rules

**Format**: `major.minor.patch`

**When to Increment**:
- **Major (X.0.0)**: Breaking changes to prompt structure/behavior
- **Minor (1.X.0)**: New capabilities/guidelines added (backwards compatible)
- **Patch (1.0.X)**: Bug fixes, typos, clarifications

**Examples**:
- `1.0.0` → Initial version
- `1.0.1` → Fixed typo in guidelines
- `1.1.0` → Added error handling section
- `2.0.0` → Complete rewrite with new structure

---

## Fix-Forward Philosophy

**No Rollback**: System does NOT support rolling back to previous versions.

**Instead**: Create a new patch version that fixes the issue.

**Reasoning**:
- Maintains complete history
- Clear audit trail
- Version numbers always increase
- No confusion about "which version 1.0.0?"

**Example**:
```
1.0.0 - Initial
1.0.1 - Bug introduced
1.0.2 - Bug fixed (NOT rollback to 1.0.0)
```

---

## Caching Strategy

**TTL**: 5 minutes per agent type

**Cache Key**: agent_type

**Storage**: In-memory dictionary

**Invalidation**:
- Automatic after 5 minutes
- Manual via DELETE /api/v1/prompts/cache/{agent_type}
- On service restart

**Why Cache**:
- Reduce DB queries
- Prompts don't change frequently
- Fast agent initialization

---

## Testing Requirements

### Backend Tests Needed

1. **PromptLoadingService Tests** (`test_prompt_loading_service.py`)
   - Cache hit/miss
   - Multiple agent types
   - Missing prompt error
   - Cache expiration
   - Clear cache

2. **PromptManagementService Tests** (`test_prompt_management_service.py`)
   - Create version (valid/invalid format)
   - Promote to active
   - Create patch (auto-increment)
   - Get versions
   - Get prompt content
   - UNIQUE constraint violations

3. **API Tests** (`test_prompts_api.py`)
   - All 8 endpoints
   - Request validation
   - Error responses (400, 404)
   - Version format validation
   - Promotion workflow

4. **Integration Tests** (`test_prompt_versioning_integration.py`)
   - Create → Promote workflow
   - Patch creation flow
   - Multiple versions for multiple agents
   - Cache behavior

---

## Metrics & Observability

**Logging**:
- Version creation with agent/version
- Promotions logged with agent/version
- Cache hits/misses
- Errors (missing prompts, invalid versions)

**Future Metrics**:
- Versions created per agent
- Most active version per agent
- Patch frequency
- Cache hit rate
- Average prompt length

---

## Summary

**Completed**:
- ✅ PromptLoadingService (caching)
- ✅ PromptManagementService (versioning)
- ✅ 8 REST API endpoints
- ✅ Dependency injection
- ✅ Router registration
- ✅ Database integration (migration 013)

**Lines Added**: ~600 lines

**Time**: ~3 hours

**Still Needed**:
- Frontend: PromptEditor
- Frontend: A/B Testing Lab
- Frontend: PromptComparison component
- Frontend: PromptHistory viewer
- Backend: Agent integration to load from DB

**Next Steps**:
1. Seed initial prompts for all 10 agents at v1.0.0
2. Build PromptEditor UI
3. Integrate agents to load from DB
4. Build A/B testing UI (optional, P2)

---

## Tracker Updated

✅ Marked 6 items complete in section 1.2.4
- Prompts table ✅
- PromptLoadingService ✅
- PromptManagementService ✅
- Independent versioning ✅
- Fix-forward patching ✅
- API endpoints ✅
