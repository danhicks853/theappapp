
### 4.9 Existing Codebase Import & Analysis
**Priority**: P2 - HIGH (Major feature for onboarding existing projects)  
**User Story**: Import existing codebases (zip/GitHub) for AI analysis and project planning

**Design Decisions**:
- No size limit (trust users, handle large codebases)
- All file types allowed (require zip/tar.gz format)
- Flexible mono-repo support (detect and handle automatically)
- Deep LLM-powered analysis with UI progress tracking
- GitHub URL import (clone directly from repo)

---

#### 4.9.1 Frontend - Import UI

- [ ] **TODO**: Add "Import Existing" option to project creation
  - **Component**: `ProjectCreateModal.tsx` - update to include import tab
  - **UI**: Toggle between "New Project" and "Import Existing"
  - **Tabs**: "Upload Zip" and "GitHub URL"
  - **Acceptance**: Modal shows both options, smooth transition between tabs
  - **Test**: Open modal, switch tabs, verify UI

- [ ] **TODO**: Build file upload component for codebase import
  - **Component**: `CodebaseUploadZone.tsx`
  - **Features**: Drag-and-drop, file browser, progress bar
  - **Accepted Formats**: .zip, .tar.gz, .tgz
  - **UI**: Show file name, size, upload progress percentage
  - **Validation**: Client-side file type check (must be archive)
  - **Chunked Upload**: Split large files into chunks (5MB each) for reliability
  - **Acceptance**: Upload works for files of any size, shows progress, handles errors
  - **Test**: Upload small zip (1MB), large zip (500MB), invalid file type

- [ ] **TODO**: Create GitHub repository import form
  - **Component**: `GitHubImportForm.tsx`
  - **Fields**: Repository URL, branch (default: main), private repo checkbox
  - **Private Repos**: If checked, require GitHub OAuth or personal access token
  - **Validation**: Validate URL format, check repo accessibility
  - **Preview**: Show repo info (name, stars, last commit) before import
  - **Acceptance**: Validates URL, shows preview, handles public/private repos
  - **Test**: Import public repo, import private repo with auth, invalid URL

- [ ] **TODO**: Build analysis progress tracker UI
  - **Component**: `CodebaseAnalysisProgress.tsx`
  - **Display**: Full-screen modal with progress steps
  - **Steps**: 
    1. Extracting files (10%)
    2. Indexing codebase (20%)
    3. Detecting technology stack (30%)
    4. Agent analysis in progress (40-90%, updates in real-time)
    5. Generating recommendations (95%)
    6. Complete (100%)
  - **Real-time Updates**: WebSocket connection for agent progress
  - **Agent Activity**: Show which agent is analyzing what
  - **Time Estimate**: "Analyzing 1,234 files, ~5 minutes remaining"
  - **Cancellable**: Allow user to cancel analysis
  - **Acceptance**: Progress accurate, updates in real-time, shows agent activity
  - **Test**: Mock analysis workflow, verify progress updates, test cancellation

#### 4.9.2 Backend - Import Processing

- [ ] **TODO**: Create codebase import API endpoint
  - **Endpoint**: POST `/api/v1/projects/import/upload`
  - **Request**: Multipart form with file chunks
  - **Chunking**: Support resumable uploads for large files
  - **Flow**: 
    1. Receive chunks → Store in temp directory
    2. Validate archive integrity (not corrupted)
    3. Create project record with status="importing"
    4. Extract to project volume (`/workspace`)
    5. Trigger orchestrator analysis workflow
  - **Response**: `{"project_id": "...", "analysis_id": "...", "status": "analyzing"}`
  - **Acceptance**: Handles chunked uploads, validates file, extracts successfully
  - **Test**: Upload multi-chunk file, verify extraction, check project created

- [ ] **TODO**: Implement GitHub clone endpoint
  - **Endpoint**: POST `/api/v1/projects/import/github`
  - **Request**: `{"repo_url": "...", "branch": "main", "access_token": "..." (optional)}`
  - **Authentication**: Use provided token for private repos
  - **Clone**: Clone repo into project volume using git
  - **Shallow Clone**: `git clone --depth 1` for speed (optional: allow full clone)
  - **Size Check**: Warn if repo >1GB (but don't block)
  - **Acceptance**: Clones public repos, authenticates for private, handles errors
  - **Test**: Clone public repo, clone private with token, invalid repo URL

- [ ] **TODO**: Build codebase extraction service
  - **Service**: `CodebaseExtractionService`
  - **Methods**: `extract_zip()`, `extract_tar()`
  - **Security**: Prevent zip bomb attacks (check compressed vs uncompressed ratio)
  - **Path Traversal**: Block `../` paths in archive (security)
  - **Destination**: Extract to `/workspace` in project volume
  - **Logging**: Log file count, total size, extraction time
  - **Acceptance**: Extracts safely, prevents security issues, logs metrics
  - **Test**: Extract normal zip, attempt zip bomb (should block), path traversal attempt

- [ ] **TODO**: Create technology stack detection service
  - **Service**: `TechStackDetector`
  - **Detection**: Analyze files to identify:
    - Languages (count .py, .js, .java, etc.)
    - Frameworks (package.json → React, requirements.txt → FastAPI)
    - Build tools (Makefile, Dockerfile, docker-compose.yml)
    - Databases (detect migrations, connection strings)
    - Testing (pytest, jest, junit configs)
  - **Output**: `TechStack` object with languages, frameworks, tools, versions
  - **Heuristics**: File patterns + content analysis
  - **Acceptance**: Accurately detects common stacks, handles multi-language projects
  - **Test**: Test with Python/FastAPI project, Node/React project, Java/Spring project

#### 4.9.3 Orchestrator - Analysis Workflow

- [ ] **TODO**: Create codebase analysis orchestrator workflow
  - **Workflow**: `CodebaseAnalysisWorkflow`
  - **Trigger**: Called after codebase extraction completes
  - **Phases**:
    1. **Discovery** (Workshopper): Analyze structure, create file inventory
    2. **Backend Analysis** (Backend Dev): Review backend code, patterns, quality
    3. **Frontend Analysis** (Frontend Dev): Review UI code, components, styling
    4. **Security Audit** (Security Expert): Scan for vulnerabilities, secrets, issues
    5. **DevOps Review** (DevOps): Check build/deploy configs, container setup
    6. **Test Analysis** (QA Engineer): Identify tests, coverage, gaps
    7. **Synthesis** (Orchestrator): Combine findings into comprehensive report
  - **Parallel Execution**: Run analyses concurrently where possible
  - **Progress Tracking**: Publish progress updates via WebSocket
  - **Acceptance**: Coordinates all agents, produces complete analysis
  - **Test**: Run workflow on sample codebase, verify all phases complete

- [ ] **TODO**: Implement agent prompts for codebase analysis
  - **Prompts**: Create specialized prompts for each agent role
  - **Workshopper Prompt**: 
    - "Analyze this codebase structure. Identify: project type, folder organization, entry points, key modules"
    - Output: Structured summary with folder tree, tech stack, architecture type
  - **Backend Dev Prompt**:
    - "Review backend code quality. Check: code patterns, error handling, database usage, API design, dependencies"
    - Output: Code quality score, patterns found, recommendations
  - **Frontend Dev Prompt**:
    - "Analyze frontend code. Identify: UI framework, component structure, state management, styling approach"
  - **Security Expert Prompt**:
    - "Security audit: Find hardcoded secrets, SQL injection risks, XSS vulnerabilities, outdated dependencies"
  - **Acceptance**: Prompts guide agents to thorough analysis, output is structured
  - **Test**: Run prompts on sample code, verify output quality

- [ ] **TODO**: Build analysis report aggregation service
  - **Service**: `AnalysisReportAggregator`
  - **Input**: Individual agent analysis results
  - **Processing**: 
    - Combine findings from all agents
    - Identify priority issues (security > quality > style)
    - Generate executive summary with LLM
    - Create actionable recommendation list
  - **Output**: `CodebaseAnalysisReport` with:
    - Executive summary (2-3 paragraphs)
    - Tech stack inventory
    - Code quality metrics (estimated)
    - Security findings (high/medium/low priority)
    - Recommendations (ordered by impact)
    - Suggested next steps
  - **Acceptance**: Report is comprehensive, actionable, well-structured
  - **Test**: Aggregate mock agent outputs, verify report quality

#### 4.9.4 Analysis Report UI

- [ ] **TODO**: Create analysis report viewer page
  - **Page**: `/projects/{id}/analysis` - Redirected here after import
  - **Layout**: Multi-tab report with sidebar navigation
  - **Tabs**:
    - Overview (executive summary, key metrics)
    - Technology Stack (languages, frameworks, versions)
    - Code Quality (patterns, issues, recommendations)
    - Security Findings (vulnerabilities, risks, fixes)
    - Architecture (structure, dependencies, diagrams)
    - Recommendations (prioritized action items)
  - **Interactive**: Click finding → View code location (if available)
  - **Actions**: "Start Work" button → Create tasks from recommendations
  - **Acceptance**: Report is readable, navigable, actionable
  - **Test**: Load analysis report, navigate tabs, verify data display

- [ ] **TODO**: Add analysis report export
  - **Formats**: PDF, Markdown, JSON
  - **Button**: "Export Report" dropdown
  - **PDF**: Well-formatted, includes all sections, charts/graphs
  - **Markdown**: GitHub-compatible, can be added to repo as ANALYSIS.md
  - **JSON**: Structured data for external tools
  - **Acceptance**: All formats export correctly, PDFs are professional
  - **Test**: Export in all formats, verify content completeness

#### 4.9.5 RAG Integration

- [ ] **TODO**: Index imported codebase in RAG system
  - **Trigger**: After successful extraction
  - **Process**: 
    - Chunk source files (by function/class/module)
    - Generate embeddings for each chunk
    - Store in Qdrant with metadata (file path, language, project_id)
  - **Metadata**: file_path, language, project_id, chunk_type (function/class/module)
  - **Benefits**: Agents can query codebase context during work
  - **Acceptance**: Codebase searchable via RAG, agents can find relevant code
  - **Test**: Index sample codebase, query for specific function, verify results

- [ ] **TODO**: Enable agents to query imported code context
  - **Integration**: RAG query in agent prompts
  - **Usage**: "Find examples of authentication in this codebase"
  - **Response**: Relevant code snippets with file paths
  - **Acceptance**: Agents successfully find and reference existing code
  - **Test**: Agent task that requires existing code reference, verify RAG query

#### 4.9.6 Project Volume Management

- [ ] **TODO**: Implement project volume cleanup policies
  - **Policy**: Keep imported code in volume unless explicitly deleted
  - **UI**: Settings page with "Delete Imported Code" button
  - **Warning**: Confirm before deletion (destructive action)
  - **Acceptance**: Code persists by default, can be manually deleted
  - **Test**: Import code, verify persistence, delete code, verify removal

#### 4.9.7 Testing

- [ ] **TODO**: Create integration tests for import flow
  - **File**: `backend/tests/integration/test_codebase_import.py`
  - **Tests**:
    - Upload zip → Extract → Analyze → Report
    - GitHub clone → Analyze → Report
    - Large file handling (500MB+)
    - Invalid archives (corrupted, wrong format)
    - Security: zip bomb detection, path traversal prevention
  - **Acceptance**: All tests pass, import flow robust
  - **Test**: Run integration test suite

- [ ] **TODO**: Create E2E tests for import UI
  - **File**: `frontend/tests/e2e/codebase-import.spec.ts`
  - **Tests**:
    - Select "Import Existing" → Upload zip → Track progress → View report
    - Import via GitHub URL → View report
    - Cancel analysis mid-progress
  - **Acceptance**: E2E tests cover happy path and error cases
  - **Test**: Run E2E test suite

---
