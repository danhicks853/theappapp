# Decision 77: GitHub Specialist Agent Specification

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P1 - HIGH  
**Depends On**: Phase 2 GitHub decisions, Decision 71 (Tool Access Service)

---

## Context

The GitHub Specialist agent handles all GitHub operations for projects. The agent must support repository management and PR workflows while maintaining security through OAuth authentication.

---

## Decision Summary

### Core Approach
- **Orchestrator-directed operations**: Agent executes specific commands from orchestrator
- **Limited operation set**: Create repo, delete repo, merge PR only
- **OAuth authentication**: User provides credentials, stored encrypted in database
- **No webhooks**: System replicates user workflow, no event-driven architecture
- **Simple workflow**: Push to main branch only, private repos, PM-reviewed PRs

---

## 1. GitHub API Operations

### Supported Operations

The GitHub Specialist supports **three core operations**:

#### 1. Create Repository
```python
{
    "action": "create_repo",
    "name": "project-name",
    "description": "Project description from user",
    "private": true
}
```

#### 2. Delete Repository
```python
{
    "action": "delete_repo",
    "repo": "username/repo-name"
}
```

#### 3. Merge Pull Request
```python
{
    "action": "merge_pr",
    "repo": "username/repo-name",
    "pr_number": 23
}
```

### Operations NOT Supported

- ❌ Create branches (only main branch)
- ❌ Create PRs (agents request PRs, PM creates them)
- ❌ Add collaborators (private repos, single user)
- ❌ Update repo settings (set once at creation)
- ❌ Manage issues, projects, wikis, etc.

**Rationale**: Keep agent simple and focused. Complex operations handled by orchestrator coordination.

---

## 2. GitHub Workflow

### Repository Setup

**When**: Project initialization

**Process**:
1. User creates project in UI, provides project name and description
2. Orchestrator requests GitHub Specialist to create repo
3. GitHub Specialist creates private repo with user's description
4. Repo initialized with main branch only

### Pull Request Workflow

**Standard Flow**:
```
1. Agent (e.g., Backend Dev) completes work
2. Agent requests PR creation from orchestrator
3. Orchestrator forwards request to Project Manager agent
4. PM reviews code changes
5. PM approves and requests merge from orchestrator
6. Orchestrator directs GitHub Specialist to merge PR
7. GitHub Specialist executes merge
```

**No Direct PR Creation**: Agents don't create PRs themselves. They request orchestrator to coordinate PM review, then PM approves merge.

### Branch Strategy

**Single Branch**: Main branch only
- All work committed directly to main (in agent's local workspace)
- PRs created from agent's workspace to main
- No feature branches, no branch management

**Rationale**: Simplifies workflow. Agents work in isolated containers, PRs provide review gate before main branch update.

---

## 3. OAuth Implementation

### OAuth Flow

**User Setup** (one-time per user):
1. User navigates to Settings → GitHub Integration
2. User enters GitHub OAuth credentials:
   - Client ID
   - Client Secret
3. User clicks "Connect GitHub"
4. OAuth flow redirects to GitHub for authorization
5. GitHub returns access token + refresh token
6. Tokens stored encrypted in database

### Token Storage

#### Database Schema: `github_credentials` Table

```sql
CREATE TABLE github_credentials (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) UNIQUE,
    access_token TEXT NOT NULL,  -- Encrypted
    refresh_token TEXT NOT NULL,  -- Encrypted
    token_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_github_creds_user ON github_credentials(user_id);
```

### Token Encryption

```python
from cryptography.fernet import Fernet

class GitHubCredentialManager:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())
    
    async def store_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int
    ):
        """Store encrypted GitHub tokens"""
        encrypted_access = self.cipher.encrypt(access_token.encode()).decode()
        encrypted_refresh = self.cipher.encrypt(refresh_token.encode()).decode()
        
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        await db.execute(
            """
            INSERT INTO github_credentials 
                (user_id, access_token, refresh_token, token_expires_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE SET
                access_token = $2,
                refresh_token = $3,
                token_expires_at = $4,
                updated_at = NOW()
            """,
            user_id, encrypted_access, encrypted_refresh, expires_at
        )
    
    async def get_access_token(self, user_id: str) -> str:
        """Retrieve and decrypt access token"""
        row = await db.fetchrow(
            "SELECT access_token, token_expires_at FROM github_credentials WHERE user_id = $1",
            user_id
        )
        
        if not row:
            raise ValueError("No GitHub credentials found")
        
        # Check if token expired
        if datetime.now() >= row['token_expires_at']:
            # Refresh token
            await self.refresh_access_token(user_id)
            return await self.get_access_token(user_id)
        
        # Decrypt and return
        encrypted_token = row['access_token'].encode()
        return self.cipher.decrypt(encrypted_token).decode()
```

### Token Refresh

**Automatic Refresh**:
- When access token expires, automatically use refresh token to get new access token
- Update database with new tokens
- Transparent to agent (agent always gets valid token)

```python
async def refresh_access_token(self, user_id: str):
    """Refresh expired access token"""
    row = await db.fetchrow(
        "SELECT refresh_token FROM github_credentials WHERE user_id = $1",
        user_id
    )
    
    # Decrypt refresh token
    encrypted_refresh = row['refresh_token'].encode()
    refresh_token = self.cipher.decrypt(encrypted_refresh).decode()
    
    # Call GitHub OAuth token refresh endpoint
    response = await httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        },
        headers={"Accept": "application/json"}
    )
    
    data = response.json()
    
    # Store new tokens
    await self.store_tokens(
        user_id=user_id,
        access_token=data['access_token'],
        refresh_token=data['refresh_token'],
        expires_in=data['expires_in']
    )
```

---

## 4. Agent Implementation

### GitHub Specialist Agent

```python
class GitHubSpecialistAgent:
    """Agent for GitHub operations"""
    
    def __init__(self, credential_manager: GitHubCredentialManager):
        self.credential_manager = credential_manager
    
    async def execute_action(
        self,
        user_id: str,
        action: dict
    ) -> dict:
        """Execute GitHub action"""
        
        # Get valid access token
        access_token = await self.credential_manager.get_access_token(user_id)
        
        # Execute action with retry logic
        return await self._execute_with_retry(action, access_token)
    
    async def _execute_with_retry(
        self,
        action: dict,
        access_token: str,
        max_retries: int = 3
    ) -> dict:
        """Execute action with exponential backoff retry"""
        
        for attempt in range(max_retries):
            try:
                if action['action'] == 'create_repo':
                    return await self.create_repo(action, access_token)
                elif action['action'] == 'delete_repo':
                    return await self.delete_repo(action, access_token)
                elif action['action'] == 'merge_pr':
                    return await self.merge_pr(action, access_token)
                else:
                    return {"success": False, "error": "Unknown action"}
            
            except GitHubAPIError as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.warning(f"GitHub API error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    # Max retries exceeded, trigger gate
                    logger.error(f"GitHub API error after {max_retries} attempts: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "trigger_gate": True,
                        "reason": f"GitHub operation failed after {max_retries} retries"
                    }
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def create_repo(self, action: dict, access_token: str) -> dict:
        """Create GitHub repository"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "name": action['name'],
                    "description": action['description'],
                    "private": True,
                    "auto_init": True  # Initialize with README
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                return {
                    "success": True,
                    "repo_url": data['html_url'],
                    "clone_url": data['clone_url']
                }
            else:
                raise GitHubAPIError(f"Failed to create repo: {response.text}")
    
    async def delete_repo(self, action: dict, access_token: str) -> dict:
        """Delete GitHub repository"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.github.com/repos/{action['repo']}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code == 204:
                return {"success": True}
            else:
                raise GitHubAPIError(f"Failed to delete repo: {response.text}")
    
    async def merge_pr(self, action: dict, access_token: str) -> dict:
        """Merge pull request"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://api.github.com/repos/{action['repo']}/pulls/{action['pr_number']}/merge",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "merge_method": "squash"  # Squash commits for clean history
                }
            )
            
            if response.status_code == 200:
                return {"success": True, "merged": True}
            else:
                raise GitHubAPIError(f"Failed to merge PR: {response.text}")
```

---

## 5. Orchestrator Integration

### Request Format

**Orchestrator → GitHub Specialist**:
```python
await github_specialist.execute_action(
    user_id=project.user_id,
    action={
        "action": "merge_pr",
        "repo": "username/project-name",
        "pr_number": 23
    }
)
```

### Response Handling

```python
class Orchestrator:
    async def request_github_operation(
        self,
        project_id: str,
        action: dict
    ):
        """Request GitHub operation"""
        
        project = await self.get_project(project_id)
        
        result = await self.github_specialist.execute_action(
            user_id=project.user_id,
            action=action
        )
        
        if result.get('trigger_gate'):
            # Operation failed after retries, trigger gate
            await self.trigger_gate(
                project_id=project_id,
                reason=result['reason'],
                details=result['error']
            )
        elif result['success']:
            # Operation succeeded
            logger.info(f"GitHub operation succeeded: {action['action']}")
        else:
            # Operation failed but no gate (shouldn't happen)
            logger.error(f"GitHub operation failed: {result['error']}")
```

---

## 6. Error Handling

### Retry Strategy

**3 Attempts with Exponential Backoff**:
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- After 3 failures: Trigger gate for human intervention

### Common Errors

| Error | Cause | Handling |
|-------|-------|----------|
| 401 Unauthorized | Token expired/invalid | Attempt token refresh, retry |
| 403 Forbidden | Insufficient permissions | Trigger gate (user needs to reauthorize) |
| 404 Not Found | Repo/PR doesn't exist | Trigger gate (orchestrator error) |
| 422 Unprocessable | Invalid request data | Trigger gate (orchestrator error) |
| 500 Server Error | GitHub outage | Retry with backoff, then gate |
| Network timeout | Connection issue | Retry with backoff, then gate |

### Gate Trigger

```python
if result.get('trigger_gate'):
    await orchestrator.trigger_gate(
        project_id=project_id,
        reason="GitHub operation failed",
        details=f"Action: {action['action']}, Error: {result['error']}"
    )
```

---

## 7. Agent Prompt Structure

### System Prompt

```
You are the GitHub Specialist agent. You execute specific GitHub operations as directed by the orchestrator.

Your capabilities:
1. Create repositories (private, with description)
2. Delete repositories
3. Merge pull requests

You do NOT:
- Create pull requests (PM agent handles this)
- Manage branches (only main branch exists)
- Add collaborators or change settings

When you receive a request, execute it precisely as specified. Report success or failure clearly.
```

### Request Validation

The agent validates requests before execution:

```python
def validate_request(self, action: dict) -> bool:
    """Validate GitHub action request"""
    
    if action['action'] == 'create_repo':
        return 'name' in action and 'description' in action
    elif action['action'] == 'delete_repo':
        return 'repo' in action
    elif action['action'] == 'merge_pr':
        return 'repo' in action and 'pr_number' in action
    else:
        return False
```

---

## 8. Frontend Integration

### Settings Page: `/settings/github`

**Features**:
- Connect GitHub account (OAuth flow)
- View connection status
- Disconnect GitHub account
- Test connection

### API Endpoints

```python
@router.post("/api/github/connect")
async def connect_github(user_id: str, code: str):
    """Complete OAuth flow and store tokens"""
    # Exchange code for tokens
    tokens = await github_oauth.exchange_code(code)
    
    # Store encrypted tokens
    await credential_manager.store_tokens(
        user_id=user_id,
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        expires_in=tokens['expires_in']
    )
    
    return {"success": True}

@router.get("/api/github/status")
async def get_github_status(user_id: str):
    """Check if GitHub is connected"""
    has_credentials = await db.fetchval(
        "SELECT EXISTS(SELECT 1 FROM github_credentials WHERE user_id = $1)",
        user_id
    )
    return {"connected": has_credentials}

@router.delete("/api/github/disconnect")
async def disconnect_github(user_id: str):
    """Remove GitHub credentials"""
    await db.execute(
        "DELETE FROM github_credentials WHERE user_id = $1",
        user_id
    )
    return {"success": True}
```

---

## Rationale

### Why Limited Operations?
- Simplifies agent implementation
- Reduces security surface area
- Sufficient for core workflow
- Can expand later if needed

### Why OAuth (Not Personal Access Token)?
- More secure (scoped permissions)
- Token refresh capability
- Standard authentication flow
- Better user experience

### Why No Webhooks?
- System replicates user workflow (pull-based)
- No need for event-driven architecture
- Simpler implementation
- Fewer moving parts

### Why Retry with Gate?
- Handles transient GitHub API issues
- Doesn't waste agent time on persistent failures
- Human can resolve authentication/permission issues
- Clear escalation path

---

## Related Decisions

- **Decision 71**: Tool Access Service (GitHub Specialist uses TAS for permissions)
- **Decision 70**: Agent Collaboration (PM reviews before GitHub merge)
- **Decision 73**: API specification (GitHub settings endpoints)

---

## Tasks Created

### Phase 2: GitHub Integration (Week 6)
- [ ] **Task 2.4.1**: Create `github_credentials` table with encryption
- [ ] **Task 2.4.2**: Implement OAuth flow (frontend + backend)
- [ ] **Task 2.4.3**: Implement `GitHubCredentialManager` with token refresh
- [ ] **Task 2.4.4**: Implement `GitHubSpecialistAgent` with retry logic
- [ ] **Task 2.4.5**: Create GitHub settings page in frontend
- [ ] **Task 2.4.6**: Integrate GitHub Specialist with orchestrator

### Phase 6: Testing (Week 12)
- [ ] **Task 6.6.14**: Test GitHub operations (create, delete, merge)
- [ ] **Task 6.6.15**: Test OAuth flow and token refresh
- [ ] **Task 6.6.16**: Test retry logic and error handling

---

## Approval

**Approved By**: User  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
