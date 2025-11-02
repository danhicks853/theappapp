# MVP/DEMO SPRINT PLAN - 24 HOURS TO WORKING DEMO

**Target Demo Date**: November 2, 2025 @ 10:00 PM
**Start Time**: November 1, 2025 @ 10:30 PM
**Total Available Time**: ~20 hours of coding

---

## 🎯 DEMO OBJECTIVES

### What We'll Show:
1. **Specialist Creation** (The Killer Feature)
   - Beautiful UI to create custom specialists
   - Upload documentation for RAG
   - Configure tool permissions (TAS)
   - Scope web search per specialist
   - AI-generated system prompts
   - Global vs Project-specific specialists

2. **Working Multi-Agent System**
   - Orchestrator routing tasks intelligently
   - 2 Built-in agents: Backend Dev, Frontend Dev
   - Custom specialist executing tasks
   - Real-time streaming output

3. **Project Management**
   - Create project with specialist assignment
   - Cannot add specialists after creation (immutable)
   - Project detail page with agent activity

4. **Cost Tracking**
   - Token usage by agent/project
   - Real-time cost dashboard

---

## 📋 TASK LIST (28 Tasks, ~24 Hours)

### BACKEND INFRASTRUCTURE (3 tasks - 2 hours)
- [ ] Qdrant RAG setup (45m)
  - Docker: `docker run -p 6333:6333 qdrant/qdrant`
  - Python client integration
  - Embed + upsert functions
  - Search function
  
- [ ] SearxNG integration (45m)
  - HTTP client wrapper
  - Result parsing
  - Per-specialist filtering
  
- [ ] Project specialists M2M migration (30m)
  - Table: `project_specialists`
  - Fields: specialist_id, project_id, created_at
  - Immutable after project creation

---

### CORE AGENTS (3 tasks - 2.5 hours)
- [ ] BaseAgent class with OpenAI integration (1.5h)
  - File: `backend/agents/base_agent.py`
  - Methods: plan(), execute(), validate()
  - OpenAI adapter integration
  - RAG integration
  - Web search integration
  - TAS tool hooks
  
- [ ] Backend Dev Agent implementation (30m)
  - File: `backend/agents/backend_dev.py`
  - Inherits BaseAgent
  - System prompt for Python/backend tasks
  - Test writing capabilities
  
- [ ] Frontend Dev Agent implementation (30m)
  - File: `backend/agents/frontend_dev.py`
  - Inherits BaseAgent
  - System prompt for React/TypeScript
  - UI component focus

---

### SPECIALISTS FEATURE (4 tasks - 3.5 hours)
- [ ] Specialist DB model + migration (30m)
  - Migration 006: `specialists` table
  - Fields:
    - id, name, description
    - system_prompt (TEXT)
    - scope (enum: 'global', 'project')
    - project_id (nullable FK)
    - web_search_enabled (bool)
    - web_search_config (JSONB)
    - tools_enabled (JSONB)
    - created_at, updated_at
  
- [ ] Specialist creation API (1.5h)
  - POST /api/v1/specialists
  - GET /api/v1/specialists
  - GET /api/v1/specialists/{id}
  - PUT /api/v1/specialists/{id}
  - Document upload endpoint
  
- [ ] AI prompt generator endpoint (30m)
  - POST /api/v1/specialists/generate-prompt
  - Input: name, description, role, capabilities
  - Output: Complete system prompt
  - Uses gpt-4o-mini
  
- [ ] Document upload + RAG indexing (1h)
  - File upload to storage
  - Extract text (PDF, TXT, MD)
  - Chunk documents
  - Generate embeddings (OpenAI)
  - Upsert to Qdrant with metadata

---

### ORCHESTRATOR (3 tasks - 3.5 hours)
- [ ] Core routing logic (2h)
  - File: `backend/services/orchestrator.py`
  - Task analysis (what specialist fits?)
  - Load available agents + specialists
  - Route to best agent
  - Execute with streaming
  
- [ ] Load specialists dynamically (30m)
  - Query DB for specialists
  - Instantiate BaseAgent with specialist config
  - Add to available agents pool
  - Filter by project if applicable
  
- [ ] WebSocket task streaming (1h)
  - WebSocket endpoint: `/ws/tasks/{task_id}`
  - Events: task_started, agent_thinking, agent_response, task_completed
  - Stream agent output in real-time

---

### TAS (1 task - 1.5 hours)
- [ ] Tool permission system hooks (1.5h)
  - Check specialist.tools_enabled before execution
  - Stub TAS calls (full impl in Phase 2)
  - Log tool usage attempts
  - Return "permission denied" if not allowed

---

### PROJECTS (2 tasks - 2 hours)
- [ ] Project creation API with specialist binding (1h)
  - POST /api/v1/projects
  - Input: name, description, specialist_ids[]
  - Create project + bind specialists (M2M insert)
  - Return project with specialists
  
- [ ] Project CRUD endpoints (1h)
  - GET /api/v1/projects
  - GET /api/v1/projects/{id}
  - PUT /api/v1/projects/{id}
  - DELETE /api/v1/projects/{id}
  - GET /api/v1/projects/{id}/specialists (read-only)

---

### COST TRACKING (1 task - 1 hour)
- [ ] Token usage aggregation API (1h)
  - GET /api/v1/costs/summary
  - GET /api/v1/costs/by-agent
  - GET /api/v1/costs/by-project
  - Query existing llm_token_usage table
  - Join with llm_pricing for cost calc

---

### FRONTEND SETUP (2 tasks - 1.5 hours)
- [ ] React + Vite + TypeScript + Tailwind (1h)
  - `npm create vite@latest frontend -- --template react-ts`
  - Install: tailwindcss, @headlessui/react, lucide-react
  - Configure Tailwind
  - Dark theme setup
  
- [ ] Routing + layout structure (30m)
  - React Router setup
  - Layout: Sidebar + main content
  - Routes: /, /projects/:id, /specialists, /specialists/new, /costs

---

### UI COMPONENTS (5 tasks - 10 hours)
- [ ] Dashboard with project cards (1.5h)
  - Page: `/`
  - Grid of project cards
  - Card: name, specialist count, recent activity
  - "New Project" button
  
- [ ] Specialist creation form (3h) ⭐ CRITICAL
  - Page: `/specialists/new`
  - Form fields:
    - Name (text)
    - Description (textarea)
    - Upload documentation (file upload)
    - Tool selection (checkboxes)
    - Web search config (toggle + scope input)
    - Scope: Global vs Project (radio)
    - System prompt (textarea with "Generate" button)
  - AI prompt generator integration
  - Real-time preview of specialist
  - Submit → Create specialist
  
- [ ] Project creation flow (2h) ⭐ CRITICAL
  - Page: `/projects/new`
  - Form fields:
    - Project name
    - Description
    - Select specialists (multi-select from available)
  - Show selected specialists
  - Submit → Create project
  - Navigate to project detail
  
- [ ] Project detail page with agent stream (2h)
  - Page: `/projects/:id`
  - Header: Project name, specialist list
  - Task input box
  - "Execute" button
  - Real-time agent activity stream
  - WebSocket connection
  - Stream formatting (agent name, timestamp, message)
  
- [ ] Cost tracking dashboard (1.5h)
  - Page: `/costs`
  - Overview cards: Total cost, total tokens, total calls
  - Chart: Cost over time (simple line chart)
  - Table: Cost by agent
  - Table: Cost by project

---

### INTEGRATION & DEMO PREP (3 tasks - 2.5 hours)
- [ ] End-to-end specialist creation test (1h)
  - Create specialist via UI
  - Verify DB entry
  - Create project with specialist
  - Execute task assigned to specialist
  - Verify specialist uses uploaded docs (RAG)
  - Verify output streams correctly
  
- [ ] Full demo flow rehearsal (1h)
  - Practice demo script
  - Identify rough edges
  - Polish critical paths
  - Prepare fallback if something breaks
  
- [ ] Seed data + demo script (30m)
  - Seed 1-2 sample projects
  - Pre-upload sample docs for RAG demo
  - Write demo script (what to say/do)
  - Backup plan if API fails

---

## 🗓️ TIMELINE

### TONIGHT (November 1, 10:30 PM - 2:00 AM) - 4 hours
**Focus: Backend Foundation**
- ✅ Qdrant RAG setup
- ✅ SearxNG integration
- ✅ Project specialists migration
- ✅ BaseAgent class
- ✅ Backend Dev Agent
- ✅ Frontend Dev Agent
- ✅ Specialist DB model + migration

**Checkpoint**: All backend infrastructure ready

---

### TOMORROW MORNING (November 2, 8:00 AM - 1:00 PM) - 5 hours
**Focus: Backend Logic**
- ✅ Specialist creation API
- ✅ AI prompt generator
- ✅ Document upload + RAG
- ✅ Orchestrator core routing
- ✅ Dynamic specialist loading
- ✅ WebSocket streaming
- ✅ TAS tool hooks
- ✅ Project creation API
- ✅ Project CRUD
- ✅ Cost tracking API

**Checkpoint**: All backend APIs working, testable via Postman

---

### TOMORROW AFTERNOON (November 2, 1:00 PM - 7:00 PM) - 6 hours
**Focus: Frontend**
- ✅ React + Vite setup
- ✅ Routing + layout
- ✅ Dashboard
- ✅ Specialist creation form (PRIORITY)
- ✅ Project creation flow (PRIORITY)
- ✅ Project detail page
- ✅ Cost tracking dashboard

**Checkpoint**: All UI pages working, connected to backend

---

### TOMORROW EVENING (November 2, 7:00 PM - 10:00 PM) - 3 hours
**Focus: Integration & Polish**
- ✅ E2E specialist creation test
- ✅ Demo rehearsal
- ✅ Seed data preparation
- ✅ Final bug fixes

**Checkpoint**: Demo-ready system

---

### DEMO TIME: November 2, 10:00 PM 🎬

---

## 🎬 DEMO SCRIPT

### Introduction (2 minutes)
"This is an AI agent orchestration system with a unique feature: **dynamic specialist creation**. Unlike other frameworks, users can create custom AI specialists with their own knowledge bases, tools, and constraints."

### Part 1: Show Existing System (3 minutes)
1. Open dashboard
2. Show existing projects
3. Click into project
4. Show built-in agents: Backend Dev, Frontend Dev
5. Execute simple task: "Write a function to reverse a string"
6. Watch agent work in real-time

### Part 2: Create Custom Specialist (5 minutes) ⭐ THE MONEY SHOT
1. Click "Create Specialist"
2. Fill form:
   - Name: "Database Expert"
   - Description: "PostgreSQL optimization and schema design"
   - Upload: PostgreSQL documentation PDF
   - Tools: Check "Read files", "Execute SQL"
   - Web search: Enable, scope to "PostgreSQL documentation"
3. Click "Generate Prompt" → AI writes perfect system prompt
4. Review and tweak prompt
5. Click "Create"
6. **Specialist appears instantly in list**

### Part 3: Use Custom Specialist (4 minutes)
1. Click "New Project"
2. Name: "Database Optimization"
3. Select specialists: Database Expert, Backend Dev
4. Create project
5. Enter task: "Optimize this slow query: SELECT * FROM users WHERE..."
6. Watch Database Expert:
   - References uploaded PostgreSQL docs
   - Suggests optimized query
   - Explains reasoning
7. Show cost tracking updating in real-time

### Part 4: Show Flexibility (2 minutes)
1. Navigate to Specialists page
2. Show Database Expert is now available globally
3. Show it can be assigned to any new project
4. Demonstrate the power of extensibility

### Closing (1 minute)
"That's the system. Custom specialists, created in minutes, with their own knowledge and tools. Ready for any project."

**Total Demo Time: ~15 minutes**

---

## 🚨 RISK MITIGATION

### Highest Risks:
1. **UI takes longer than expected**
   - Mitigation: Use component library (Headless UI), minimal custom CSS
   - Fallback: Simplify UI, focus on functionality over beauty

2. **Integration issues between frontend/backend**
   - Mitigation: Test API endpoints early with Postman
   - Fallback: Mock API responses in frontend if backend breaks

3. **Qdrant/SearxNG setup problems**
   - Mitigation: Docker compose for easy setup
   - Fallback: Stub RAG/search, show UI working

4. **WebSocket complexity**
   - Mitigation: Use simple Socket.IO library
   - Fallback: Polling instead of WebSocket

### Backup Plans:
- If specialist creation breaks: Use pre-created specialists
- If RAG breaks: Fake document references in responses
- If orchestrator breaks: Hardcode agent assignment
- If frontend breaks: Demo via Postman + terminal output

---

## ✅ SUCCESS CRITERIA

### Must Have (Demo Fails Without):
- ✅ Specialist creation UI works
- ✅ Specialist appears and can execute tasks
- ✅ Real-time task streaming
- ✅ Project creation with specialist binding

### Should Have (Demo Less Impressive Without):
- ✅ AI prompt generator
- ✅ Document upload (RAG)
- ✅ Cost tracking visible

### Nice to Have (Won't Break Demo):
- ✅ Beautiful UI animations
- ✅ Perfect error handling
- ✅ Full test coverage

---

## 📊 PROGRESS TRACKING

**Current Status**: 
- ✅ OpenAI Integration Foundation (COMPLETE)
- 📋 MVP Sprint (NOT STARTED)

**Tasks Completed**: 0 / 28
**Hours Spent**: 0 / 24
**Hours Remaining**: 20

**Updated**: November 1, 2025 @ 10:25 PM

---

## 🎯 NEXT ACTION

**Immediate next step**: Start Qdrant RAG setup

**Command to run**: 
```bash
docker run -d -p 6333:6333 qdrant/qdrant
pip install qdrant-client
```

**File to create**: `backend/services/rag_service.py`

---

**LET'S BUILD THIS! 🚀**
