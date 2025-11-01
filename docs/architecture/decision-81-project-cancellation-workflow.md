# Decision 81: Project Cancellation Workflow

**Status**: ✅ COMPLETE  
**Date Resolved**: November 1, 2025  
**Priority**: P2 - MEDIUM  
**Depends On**: Decision 54 (archive system)

---

## Context

Decision 54 mentions archiving "completed and cancelled" projects, but the cancellation workflow was undefined. Users need a way to permanently delete projects they no longer want.

---

## Decision Summary

### Core Approach
- **User-initiated deletion**: "Delete Project" button on project page
- **Confirmation required**: Modal confirmation before deletion
- **Log to database**: Store basic project info before deletion
- **Complete resource destruction**: Delete all project files and containers
- **No resumption**: Cancelled projects cannot be resumed (permanent deletion)

---

## 1. Cancellation Trigger

### User Interface

**Location**: Project detail page (`/projects/{project_id}`)

**Button placement**:
```
┌─────────────────────────────────────────────────────────────┐
│ Project: My API                                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Status: In Progress                                          │
│ Progress: 45%                                                │
│                                                               │
│ [Pause Project]  [Resume Project]  [Delete Project]         │
│                                                  ↑            │
│                                            Red/danger button  │
└─────────────────────────────────────────────────────────────┘
```

### Confirmation Modal

**Two-step confirmation**:
```
┌─────────────────────────────────────────────────────────────┐
│ Delete Project?                                          [×] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ⚠️  Warning: This action cannot be undone!                   │
│                                                               │
│ You are about to permanently delete:                         │
│ • Project: My API                                            │
│ • All project files and code                                 │
│ • All project history and logs                               │
│                                                               │
│ This project cannot be resumed after deletion.               │
│                                                               │
│ Type "DELETE" to confirm:                                    │
│ [________________]                                            │
│                                                               │
│ [Cancel]                              [Delete Project]       │
│                                       (disabled until typed)  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Cancellation Log

### Database Schema: `cancelled_projects` Table

```sql
CREATE TABLE cancelled_projects (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    stage VARCHAR(100),  -- What stage was project in when cancelled
    cancelled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_by UUID REFERENCES users(id),
    reason TEXT,  -- Optional user-provided reason
    metadata JSONB  -- Additional project info
);

CREATE INDEX idx_cancelled_projects_user ON cancelled_projects(cancelled_by);
CREATE INDEX idx_cancelled_projects_date ON cancelled_projects(cancelled_at);
```

### Log Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `project_id` | Original project UUID | `550e8400-e29b-41d4-a716-446655440000` |
| `project_name` | Project name | `My API` |
| `stage` | Current stage when cancelled | `Phase 2: Implementation` |
| `cancelled_at` | Timestamp of cancellation | `2025-11-01 02:30:00Z` |
| `cancelled_by` | User who cancelled | `user_123` |
| `reason` | Optional cancellation reason | `"Project no longer needed"` |
| `metadata` | Additional context | `{"language": "python", "tasks_completed": 5}` |

### What Gets Logged

**Basic project info**:
- Project ID and name
- Current stage/phase
- Language
- Number of tasks completed
- Creation date
- Last activity date

**NOT logged**:
- Project files (deleted)
- Code content (deleted)
- Full history (deleted)

**Rationale**: Log is for analytics only (e.g., "what stage do users typically cancel?"), not for recovery.

---

## 3. Resource Destruction

### Deletion Process

**Order of operations**:
1. Log project to `cancelled_projects` table
2. Stop any active containers
3. Delete project files from persistent volume
4. Delete project database records
5. Delete project from active projects list
6. Return success to user

### Implementation

```python
class ProjectManager:
    async def cancel_project(
        self,
        project_id: str,
        user_id: str,
        reason: Optional[str] = None
    ):
        """Cancel and permanently delete a project"""
        
        # 1. Get project info before deletion
        project = await self.get_project(project_id)
        
        if not project:
            raise ValueError("Project not found")
        
        # 2. Log cancellation
        await self.log_cancellation(
            project_id=project_id,
            project_name=project['name'],
            stage=project.get('current_stage', 'Unknown'),
            cancelled_by=user_id,
            reason=reason,
            metadata={
                'language': project.get('language'),
                'tasks_completed': project.get('tasks_completed', 0),
                'created_at': project.get('created_at'),
                'last_activity': project.get('last_activity')
            }
        )
        
        logger.info(f"Logged cancellation for project {project_id}")
        
        # 3. Stop active containers
        await self.stop_project_containers(project_id)
        
        # 4. Delete project files
        await self.delete_project_files(project_id)
        
        # 5. Delete database records
        await self.delete_project_records(project_id)
        
        logger.info(f"Project {project_id} fully deleted")
        
        return {"success": True, "message": "Project deleted successfully"}
    
    async def log_cancellation(
        self,
        project_id: str,
        project_name: str,
        stage: str,
        cancelled_by: str,
        reason: Optional[str],
        metadata: dict
    ):
        """Log project cancellation"""
        await db.execute(
            """
            INSERT INTO cancelled_projects 
                (project_id, project_name, stage, cancelled_by, reason, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            project_id, project_name, stage, cancelled_by, reason, 
            json.dumps(metadata)
        )
    
    async def stop_project_containers(self, project_id: str):
        """Stop and remove all containers for project"""
        containers = await container_manager.get_project_containers(project_id)
        
        for container in containers:
            try:
                container.stop(timeout=5)
                container.remove()
                logger.info(f"Stopped container {container.id[:12]}")
            except Exception as e:
                logger.error(f"Error stopping container: {e}")
                # Continue with deletion even if container cleanup fails
    
    async def delete_project_files(self, project_id: str):
        """Delete all project files from persistent volume"""
        project_path = self.get_project_path(project_id)
        
        if os.path.exists(project_path):
            try:
                shutil.rmtree(project_path)
                logger.info(f"Deleted project files at {project_path}")
            except Exception as e:
                logger.error(f"Error deleting project files: {e}")
                raise
    
    async def delete_project_records(self, project_id: str):
        """Delete all database records for project"""
        
        # Delete in order to respect foreign key constraints
        tables = [
            'llm_token_usage',      # Token usage logs
            'project_state',        # Project state
            'task_history',         # Task history
            'project_files',        # File metadata
            'projects'              # Main project record
        ]
        
        for table in tables:
            try:
                await db.execute(
                    f"DELETE FROM {table} WHERE project_id = $1",
                    project_id
                )
                logger.info(f"Deleted records from {table}")
            except Exception as e:
                logger.error(f"Error deleting from {table}: {e}")
                # Continue with other tables
```

---

## 4. API Endpoints

### Delete Project Endpoint

```python
@router.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Delete a project permanently"""
    
    # Verify user owns project
    project = await db.fetchrow(
        "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
        project_id, current_user.id
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Cancel and delete project
    result = await project_manager.cancel_project(
        project_id=project_id,
        user_id=current_user.id,
        reason=reason
    )
    
    return result
```

### Get Cancellation History (Optional)

```python
@router.get("/api/projects/cancelled")
async def get_cancelled_projects(
    current_user: User = Depends(get_current_user),
    limit: int = 50
):
    """Get user's cancelled project history"""
    
    cancelled = await db.fetch(
        """
        SELECT project_name, stage, cancelled_at, reason
        FROM cancelled_projects
        WHERE cancelled_by = $1
        ORDER BY cancelled_at DESC
        LIMIT $2
        """,
        current_user.id, limit
    )
    
    return {"cancelled_projects": cancelled}
```

---

## 5. Frontend Implementation

### Delete Button Component

```javascript
function ProjectActions({ project }) {
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);
    
    async function handleDelete() {
        if (deleteConfirmation !== 'DELETE') {
            return;
        }
        
        setIsDeleting(true);
        
        try {
            const response = await fetch(`/api/projects/${project.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Redirect to projects list
                window.location.href = '/projects';
            } else {
                alert('Failed to delete project');
            }
        } catch (error) {
            console.error('Error deleting project:', error);
            alert('Error deleting project');
        } finally {
            setIsDeleting(false);
        }
    }
    
    return (
        <>
            <button 
                className="btn btn-danger"
                onClick={() => setShowDeleteModal(true)}
            >
                Delete Project
            </button>
            
            {showDeleteModal && (
                <DeleteConfirmationModal
                    project={project}
                    confirmation={deleteConfirmation}
                    onConfirmationChange={setDeleteConfirmation}
                    onDelete={handleDelete}
                    onCancel={() => {
                        setShowDeleteModal(false);
                        setDeleteConfirmation('');
                    }}
                    isDeleting={isDeleting}
                />
            )}
        </>
    );
}
```

### Confirmation Modal Component

```javascript
function DeleteConfirmationModal({
    project,
    confirmation,
    onConfirmationChange,
    onDelete,
    onCancel,
    isDeleting
}) {
    const isConfirmed = confirmation === 'DELETE';
    
    return (
        <div className="modal-overlay">
            <div className="modal">
                <div className="modal-header">
                    <h2>Delete Project?</h2>
                    <button onClick={onCancel}>×</button>
                </div>
                
                <div className="modal-body">
                    <div className="warning">
                        ⚠️ Warning: This action cannot be undone!
                    </div>
                    
                    <p>You are about to permanently delete:</p>
                    <ul>
                        <li>Project: <strong>{project.name}</strong></li>
                        <li>All project files and code</li>
                        <li>All project history and logs</li>
                    </ul>
                    
                    <p className="emphasis">
                        This project cannot be resumed after deletion.
                    </p>
                    
                    <div className="confirmation-input">
                        <label>Type "DELETE" to confirm:</label>
                        <input
                            type="text"
                            value={confirmation}
                            onChange={(e) => onConfirmationChange(e.target.value)}
                            placeholder="DELETE"
                            autoFocus
                        />
                    </div>
                </div>
                
                <div className="modal-footer">
                    <button 
                        className="btn btn-secondary"
                        onClick={onCancel}
                        disabled={isDeleting}
                    >
                        Cancel
                    </button>
                    <button 
                        className="btn btn-danger"
                        onClick={onDelete}
                        disabled={!isConfirmed || isDeleting}
                    >
                        {isDeleting ? 'Deleting...' : 'Delete Project'}
                    </button>
                </div>
            </div>
        </div>
    );
}
```

---

## 6. Cancellation vs Completion

### Key Differences

| Aspect | Cancelled | Completed |
|--------|-----------|-----------|
| **Files** | Deleted | Archived |
| **Database** | Deleted (except log) | Archived |
| **Resumable** | No | No |
| **Reason** | User initiated | Project finished |
| **Status** | Destroyed | Archived |

### Archive System Integration

**Completed projects** (Decision 54):
- Files moved to archive storage
- Database records marked as archived
- Can be viewed (read-only)
- Not resumable but accessible

**Cancelled projects**:
- Files completely deleted
- Database records deleted
- Only basic log remains
- Not accessible after deletion

---

## 7. Error Handling

### Deletion Failures

```python
async def cancel_project(self, project_id: str, user_id: str, reason: Optional[str]):
    """Cancel project with error handling"""
    
    try:
        # Log cancellation first (most important)
        await self.log_cancellation(...)
        
        # Try to clean up resources
        try:
            await self.stop_project_containers(project_id)
        except Exception as e:
            logger.error(f"Container cleanup failed: {e}")
            # Continue with deletion
        
        try:
            await self.delete_project_files(project_id)
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            # This is critical, re-raise
            raise
        
        try:
            await self.delete_project_records(project_id)
        except Exception as e:
            logger.error(f"Database deletion failed: {e}")
            # This is critical, re-raise
            raise
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Project cancellation failed: {e}")
        # Project may be partially deleted
        # Log should still exist for tracking
        raise HTTPException(
            status_code=500,
            detail="Failed to delete project. Please contact support."
        )
```

### Partial Deletion Recovery

**If deletion fails mid-process**:
- Cancellation log exists (good for tracking)
- Some resources may remain (orphaned)
- Admin cleanup job can detect and remove orphaned resources

```python
@scheduler.scheduled_job('cron', hour=3, minute=0)
async def cleanup_orphaned_resources():
    """Clean up resources from failed deletions"""
    
    # Find projects in cancelled_projects but still in projects table
    orphaned = await db.fetch(
        """
        SELECT cp.project_id
        FROM cancelled_projects cp
        JOIN projects p ON cp.project_id = p.id
        WHERE cp.cancelled_at < NOW() - INTERVAL '1 hour'
        """
    )
    
    for record in orphaned:
        logger.warning(f"Found orphaned project: {record['project_id']}")
        try:
            await project_manager.delete_project_records(record['project_id'])
            await project_manager.delete_project_files(record['project_id'])
        except Exception as e:
            logger.error(f"Failed to clean up orphaned project: {e}")
```

---

## 8. Analytics and Reporting

### Cancellation Metrics

**Useful analytics from cancellation log**:
- Cancellation rate (% of projects cancelled vs completed)
- Common cancellation stages (where do users give up?)
- Time to cancellation (how long before users cancel?)
- Cancellation reasons (if provided)

### Example Queries

```sql
-- Cancellation rate by stage
SELECT 
    stage,
    COUNT(*) as cancellations
FROM cancelled_projects
GROUP BY stage
ORDER BY cancellations DESC;

-- Average time to cancellation
SELECT 
    AVG(cp.cancelled_at - p.created_at) as avg_time_to_cancel
FROM cancelled_projects cp
JOIN projects p ON cp.project_id = p.id;

-- Cancellations over time
SELECT 
    DATE_TRUNC('week', cancelled_at) as week,
    COUNT(*) as cancellations
FROM cancelled_projects
GROUP BY week
ORDER BY week DESC;
```

---

## 9. User Experience Considerations

### When to Show Delete Button

**Always available**:
- User can delete project at any stage
- No restrictions on when deletion is allowed
- Even active/in-progress projects can be deleted

### Warning Messages

**Clear communication**:
- "Cannot be undone" prominently displayed
- List exactly what will be deleted
- Require typed confirmation (prevents accidental clicks)
- Show loading state during deletion

### Post-Deletion

**After successful deletion**:
- Redirect to projects list
- Show success message: "Project deleted successfully"
- Remove project from all UI lists immediately

---

## Implementation Details

### Database Constraints

```sql
-- Ensure cancelled_projects references are handled
ALTER TABLE cancelled_projects
    ADD CONSTRAINT fk_cancelled_by 
    FOREIGN KEY (cancelled_by) 
    REFERENCES users(id) 
    ON DELETE SET NULL;  -- Keep log even if user deleted
```

### Deletion Transaction

```python
async def delete_project_records(self, project_id: str):
    """Delete project records in a transaction"""
    
    async with db.transaction():
        # Delete in order to respect foreign keys
        await db.execute(
            "DELETE FROM llm_token_usage WHERE project_id = $1",
            project_id
        )
        await db.execute(
            "DELETE FROM project_state WHERE project_id = $1",
            project_id
        )
        await db.execute(
            "DELETE FROM projects WHERE id = $1",
            project_id
        )
```

---

## Rationale

### Why Permanent Deletion?
- User explicitly wants project gone
- No value in keeping cancelled project data
- Reduces storage costs
- Simpler than archival system for cancelled projects

### Why Log Basic Info?
- Analytics on cancellation patterns
- Helps improve product (why do users cancel?)
- Minimal storage cost
- No sensitive data stored

### Why Require Confirmation?
- Prevents accidental deletion
- Deletion is permanent and destructive
- Industry best practice for dangerous actions
- Typed confirmation adds extra safety layer

### Why No Resumption?
- Cancelled = user doesn't want it
- Simplifies system (no cancelled project state)
- If user wants to restart, they create new project
- Clear distinction from "paused" projects

---

## Related Decisions

- **Decision 54**: Archive system (for completed projects, not cancelled)
- **Decision 76**: State recovery (cancelled projects excluded)
- **Decision 73**: API specification (delete endpoint)

---

## Tasks Created

### Phase 4: Frontend (Week 10)
- [ ] **Task 4.7.1**: Add "Delete Project" button to project page
- [ ] **Task 4.7.2**: Create delete confirmation modal
- [ ] **Task 4.7.3**: Implement delete project API call

### Phase 5: Backend (Week 11)
- [ ] **Task 5.3.1**: Create `cancelled_projects` table
- [ ] **Task 5.3.2**: Implement project cancellation logic
- [ ] **Task 5.3.3**: Implement resource cleanup (containers, files, DB)
- [ ] **Task 5.3.4**: Add orphaned resource cleanup job

### Phase 6: Testing (Week 12)
- [ ] **Task 6.6.21**: Test project deletion flow
- [ ] **Task 6.6.22**: Test partial deletion recovery
- [ ] **Task 6.6.23**: Test orphaned resource cleanup

---

## Approval

**Approved By**: User  
**Date**: November 1, 2025

---

*Last Updated: November 1, 2025*
