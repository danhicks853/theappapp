# Decision 69: Prompt Versioning & Management System

## Status
✅ **RESOLVED**  
**Date**: Nov 1, 2025  
**Priority**: P0 - BLOCKING

---

## Context

With chain-of-thought prompts for orchestrator and 10+ agents, prompt optimization is critical. Prompts will evolve over time as we discover better approaches, clearer instructions, and more effective reasoning patterns.

Need a system to version, test, and manage prompts without breaking production agents or losing optimization progress.

---

## Decision Summary

### **1. Storage: PostgreSQL Database**

**Implementation**:
- Prompts stored in PostgreSQL with versioning metadata
- Editable via frontend interface
- Integrated with user settings and agent configuration

**Rationale**:
- Frontend editing capability (no deployments needed)
- Queryable and searchable
- Integrated with existing database infrastructure
- Version history maintained in database

---

### **2. Versioning: Semantic Versioning (Independent per Agent Type)**

**Implementation**:
- Each agent type has independent prompt versioning
- Format: `MAJOR.MINOR.PATCH` (e.g., v2.1.0)
- Version increments:
  - **MAJOR**: Breaking changes in prompt structure or format
  - **MINOR**: Optimization improvements, new capabilities
  - **PATCH**: Bug fixes, clarifications, small tweaks

**Independent Versioning Examples**:
```
Orchestrator prompts: v3.2.1
Backend Developer prompts: v2.5.0
Frontend Developer prompts: v1.8.2
QA Engineer prompts: v1.4.1
Security Expert prompts: v2.0.0
```

**Rationale**:
- Each agent type evolves at its own pace
- Backend Developer optimizations don't affect Frontend Developer
- Clear versioning semantics
- Easy to understand what changed

---

### **3. Version Loading: Latest Version Always**

**Implementation**:
- Agents always load the latest version available for their type
- No manual version selection in production
- Automatic promotion when new version is created
- Simple and predictable behavior

**Production Behavior**:
```python
# When agent initializes
agent = BackendDeveloperAgent()
agent.load_prompt()  # Automatically gets latest version

# Database query
SELECT prompt_text FROM prompts 
WHERE agent_type = 'backend_developer' 
ORDER BY version DESC 
LIMIT 1
```

**Rationale**:
- Simplicity - no version configuration needed
- Always using best available prompts
- Optimization improvements immediately available
- No version drift across agents

---

### **4. A/B Testing: Specialized Frontend UI**

**Implementation**:
- Dedicated frontend page: "Prompt Testing Lab"
- Manually interact with specific agents
- Select prompt version for testing
- Compare responses between versions side-by-side
- Decide when to promote test version to latest

**Testing Workflow**:
```
1. Developer creates new prompt version (v2.6.0-beta)
2. Opens Prompt Testing Lab UI
3. Selects Backend Developer agent
4. Chooses version v2.6.0-beta vs current v2.5.0
5. Sends same task to both versions
6. Compares outputs side-by-side
7. If better, promotes v2.6.0-beta → v2.6.0 (latest)
8. All agents automatically use v2.6.0
```

**UI Features**:
- Agent selector dropdown
- Version comparison (current vs test)
- Task input field
- Side-by-side response display
- Chain-of-thought comparison
- Token usage comparison
- Quality assessment tools
- Promote button

**No Shadow Mode**:
- Shadow mode (parallel execution) too expensive
- Doubles LLM API costs
- Manual testing sufficient for optimization
- Quality over automation

**Rationale**:
- Manual control over testing
- Cost-effective (only test when actively optimizing)
- Side-by-side comparison is intuitive
- No risk to production agents
- Clear promotion path

---

### **5. Rollback Strategy: Fix Forward**

**Implementation**:
- No rollback to previous versions
- If issue discovered, create patch version
- Always move forward with fixes

**Fix Forward Workflow**:
```
Current: v2.5.0 (has issue)
↓
Create: v2.5.1 (fixes issue)
↓
Promote: v2.5.1 becomes latest
↓
All agents automatically use v2.5.1
```

**Rationale**:
- Simpler than rollback mechanism
- Maintains forward progress
- Rollback can hide issues rather than fix them
- Database stores all versions (can reference old if needed)
- Aligns with "fix it right" philosophy

---

## Implementation Architecture

### **1. Database Schema**

```sql
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    
    -- Prompt components
    system_prompt TEXT NOT NULL,
    context_template TEXT,
    task_template TEXT,
    chain_of_thought_template TEXT,
    format_template TEXT,
    
    -- Metadata
    description TEXT,
    changelog TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    is_beta BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMP,
    
    -- Validation
    UNIQUE(agent_type, version),
    CHECK (version ~ '^v?\d+\.\d+\.\d+(-beta)?$')
);

CREATE INDEX idx_prompts_agent_type ON prompts(agent_type);
CREATE INDEX idx_prompts_version ON prompts(major DESC, minor DESC, patch DESC);
CREATE INDEX idx_prompts_created ON prompts(created_at DESC);

-- View for latest versions
CREATE VIEW latest_prompts AS
SELECT DISTINCT ON (agent_type) *
FROM prompts
WHERE is_beta = FALSE
ORDER BY agent_type, major DESC, minor DESC, patch DESC;
```

### **2. Prompt Loading Service**

```python
from dataclasses import dataclass

@dataclass
class PromptVersion:
    """Represents a versioned prompt."""
    agent_type: str
    version: str
    system_prompt: str
    context_template: str
    task_template: str
    chain_of_thought_template: str
    format_template: str

class PromptLoadingService:
    """Service for loading agent prompts."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def load_latest_prompt(self, agent_type: str) -> PromptVersion:
        """
        Load the latest non-beta prompt for an agent type.
        This is used by all agents in production.
        """
        result = await self.db.fetchrow(
            """
            SELECT * FROM latest_prompts
            WHERE agent_type = $1
            """,
            agent_type
        )
        
        if not result:
            raise ValueError(f"No prompt found for agent type: {agent_type}")
        
        return PromptVersion(
            agent_type=result['agent_type'],
            version=result['version'],
            system_prompt=result['system_prompt'],
            context_template=result['context_template'],
            task_template=result['task_template'],
            chain_of_thought_template=result['chain_of_thought_template'],
            format_template=result['format_template']
        )
    
    async def load_specific_version(
        self, agent_type: str, version: str
    ) -> PromptVersion:
        """
        Load a specific prompt version.
        Used by A/B testing UI only.
        """
        result = await self.db.fetchrow(
            """
            SELECT * FROM prompts
            WHERE agent_type = $1 AND version = $2
            """,
            agent_type, version
        )
        
        if not result:
            raise ValueError(f"Version {version} not found for {agent_type}")
        
        return PromptVersion(
            agent_type=result['agent_type'],
            version=result['version'],
            system_prompt=result['system_prompt'],
            context_template=result['context_template'],
            task_template=result['task_template'],
            chain_of_thought_template=result['chain_of_thought_template'],
            format_template=result['format_template']
        )
    
    async def list_versions(self, agent_type: str) -> List[dict]:
        """List all versions for an agent type (for A/B testing UI)."""
        results = await self.db.fetch(
            """
            SELECT version, description, created_at, is_beta
            FROM prompts
            WHERE agent_type = $1
            ORDER BY major DESC, minor DESC, patch DESC
            """,
            agent_type
        )
        return [dict(r) for r in results]
```

### **3. Prompt Management Service**

```python
class PromptManagementService:
    """Service for creating and managing prompt versions."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def create_version(
        self,
        agent_type: str,
        version: str,
        system_prompt: str,
        context_template: str,
        task_template: str,
        chain_of_thought_template: str,
        format_template: str,
        description: str,
        is_beta: bool = True
    ) -> UUID:
        """
        Create a new prompt version.
        Defaults to beta until explicitly promoted.
        """
        # Parse semantic version
        major, minor, patch = self._parse_version(version)
        
        # Insert new version
        result = await self.db.fetchrow(
            """
            INSERT INTO prompts (
                agent_type, version, major, minor, patch,
                system_prompt, context_template, task_template,
                chain_of_thought_template, format_template,
                description, is_beta
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
            """,
            agent_type, version, major, minor, patch,
            system_prompt, context_template, task_template,
            chain_of_thought_template, format_template,
            description, is_beta
        )
        
        return result['id']
    
    async def promote_version(self, agent_type: str, version: str) -> None:
        """
        Promote a beta version to production (latest).
        Removes beta flag, making it the latest version.
        """
        await self.db.execute(
            """
            UPDATE prompts
            SET is_beta = FALSE, promoted_at = NOW()
            WHERE agent_type = $1 AND version = $2
            """,
            agent_type, version
        )
    
    async def create_patch_version(
        self,
        agent_type: str,
        base_version: str,
        changes: dict,
        description: str
    ) -> str:
        """
        Create a patch version based on current latest.
        Used for fix-forward approach.
        """
        # Get current latest
        latest = await self.db.fetchrow(
            """
            SELECT * FROM latest_prompts
            WHERE agent_type = $1
            """,
            agent_type
        )
        
        # Increment patch version
        new_version = f"v{latest['major']}.{latest['minor']}.{latest['patch'] + 1}"
        
        # Create new version with changes
        await self.create_version(
            agent_type=agent_type,
            version=new_version,
            system_prompt=changes.get('system_prompt', latest['system_prompt']),
            context_template=changes.get('context_template', latest['context_template']),
            task_template=changes.get('task_template', latest['task_template']),
            chain_of_thought_template=changes.get('chain_of_thought_template', latest['chain_of_thought_template']),
            format_template=changes.get('format_template', latest['format_template']),
            description=description,
            is_beta=False  # Patches go straight to production
        )
        
        return new_version
    
    def _parse_version(self, version: str) -> tuple:
        """Parse semantic version string."""
        version = version.lstrip('v').replace('-beta', '')
        parts = version.split('.')
        return int(parts[0]), int(parts[1]), int(parts[2])
```

### **4. Agent Integration**

```python
class BaseAgent:
    """Base class for all agents with prompt loading."""
    
    def __init__(self, agent_type: str, prompt_service: PromptLoadingService):
        self.agent_type = agent_type
        self.prompt_service = prompt_service
        self.prompt: Optional[PromptVersion] = None
    
    async def initialize(self):
        """Load latest prompt version on agent initialization."""
        self.prompt = await self.prompt_service.load_latest_prompt(self.agent_type)
        print(f"{self.agent_type} loaded prompt {self.prompt.version}")
    
    def build_prompt(self, context: dict, task: dict) -> str:
        """Build complete prompt from templates."""
        prompt = self.prompt.system_prompt + "\n\n"
        
        if self.prompt.context_template:
            prompt += self.prompt.context_template.format(**context) + "\n\n"
        
        if self.prompt.task_template:
            prompt += self.prompt.task_template.format(**task) + "\n\n"
        
        if self.prompt.chain_of_thought_template:
            prompt += self.prompt.chain_of_thought_template + "\n\n"
        
        if self.prompt.format_template:
            prompt += self.prompt.format_template
        
        return prompt
```

### **5. A/B Testing UI - API Endpoints**

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

@router.get("/agent-types")
async def list_agent_types():
    """List all available agent types."""
    return {
        "agent_types": [
            "orchestrator",
            "backend_developer",
            "frontend_developer",
            "qa_engineer",
            "security_expert",
            "devops_engineer",
            "documentation_expert",
            "ui_ux_designer",
            "github_specialist",
            "workshopper",
            "project_manager"
        ]
    }

@router.get("/{agent_type}/versions")
async def list_versions(agent_type: str, prompt_service: PromptLoadingService):
    """List all versions for an agent type."""
    versions = await prompt_service.list_versions(agent_type)
    return {"agent_type": agent_type, "versions": versions}

@router.get("/{agent_type}/latest")
async def get_latest(agent_type: str, prompt_service: PromptLoadingService):
    """Get latest prompt version."""
    prompt = await prompt_service.load_latest_prompt(agent_type)
    return {"prompt": prompt}

@router.post("/test")
async def test_prompt_version(
    agent_type: str,
    version: str,
    task_description: str,
    orchestrator: Orchestrator
):
    """
    Test a specific prompt version with a task.
    Used by A/B Testing UI.
    """
    # Create temporary agent with specific version
    prompt = await prompt_service.load_specific_version(agent_type, version)
    
    # Execute task with this prompt
    result = await orchestrator.execute_task_with_prompt(
        agent_type=agent_type,
        prompt=prompt,
        task_description=task_description
    )
    
    return {
        "agent_type": agent_type,
        "version": version,
        "response": result.response,
        "chain_of_thought": result.reasoning,
        "tokens_used": result.tokens,
        "cost": result.cost
    }

@router.post("/{agent_type}/versions/{version}/promote")
async def promote_version(
    agent_type: str,
    version: str,
    prompt_mgmt: PromptManagementService
):
    """Promote a beta version to latest."""
    await prompt_mgmt.promote_version(agent_type, version)
    return {"message": f"Promoted {agent_type} {version} to latest"}

@router.post("/{agent_type}/patch")
async def create_patch(
    agent_type: str,
    changes: dict,
    description: str,
    prompt_mgmt: PromptManagementService
):
    """Create a patch version (fix forward)."""
    new_version = await prompt_mgmt.create_patch_version(
        agent_type, changes, description
    )
    return {"message": f"Created patch version {new_version}"}
```

---

## Frontend: Prompt Testing Lab UI

### **Page Structure**

```typescript
interface PromptTestingLabState {
  selectedAgentType: string;
  availableVersions: PromptVersion[];
  testVersion: string;
  currentVersion: string;
  taskInput: string;
  testResult: TestResult | null;
  currentResult: TestResult | null;
  loading: boolean;
}

interface TestResult {
  version: string;
  response: string;
  chainOfThought: string;
  tokensUsed: number;
  cost: number;
}
```

### **UI Components**

1. **Agent Selector**
   - Dropdown with all agent types
   - Shows current latest version

2. **Version Comparison Panel**
   - Left: Current latest version
   - Right: Selected test version
   - Version dropdown for test selection

3. **Task Input**
   - Text area for task description
   - "Run Test" button (executes both versions)

4. **Results Display**
   - Side-by-side response comparison
   - Chain-of-thought comparison
   - Token/cost metrics
   - Quality indicators

5. **Promotion Panel**
   - "Promote to Latest" button
   - Confirmation modal
   - Success notification

---

## Testing Strategy

### **Unit Tests**
- Version parsing (semver format)
- Latest version query logic
- Patch version increment
- Template rendering

### **Integration Tests**
- Prompt loading by agents
- Version promotion workflow
- Patch creation workflow
- A/B testing API endpoints

### **End-to-End Tests**
- Create beta version → Test → Promote → Agents use new version
- Issue discovered → Create patch → Automatically becomes latest
- A/B testing UI workflow

### **Quality Validation**
- Prompt template variable validation
- Semantic version format enforcement
- Duplicate version prevention

---

## Implications

### **Enables**
- Continuous prompt optimization
- Safe testing of improvements
- Independent agent evolution
- Frontend-driven prompt management
- Quality improvements without deployments

### **Requires**
- Prompts database table and schema
- Prompt loading service integration
- A/B Testing Lab frontend page
- API endpoints for prompt management
- Initial prompt seeding (v1.0.0 for each agent)

### **Trade-offs**
- **No Shadow Mode**: Manual testing only (cost savings)
- **Fix Forward**: No rollback capability (simpler)
- **Latest Always**: No version pinning (predictability)
- **Worth It**: Continuous optimization with minimal complexity

---

## Dependencies

**Depends On**:
- Decision 67: Orchestrator LLM Integration (orchestrator has prompts)
- PostgreSQL database (storage)

**Enables**:
- All prompt optimization work
- Agent quality improvements over time
- Experimentation and A/B testing

---

## Next Steps

1. ✅ Document this decision (COMPLETE)
2. ⏭️ Update development tracker
3. ⏭️ Move to Decision 70: Agent Collaboration Protocol

---

*Decision resolved: Nov 1, 2025*  
*Implementation priority: P0 - Required for prompt management*  
*Nice: 69 ✅*
