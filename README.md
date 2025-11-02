# TheAppApp 🚀

**An AI Agent Orchestration Platform with Custom Specialists**

Browse, install, and manage AI specialists for your projects. Create teams of specialized agents to tackle complex development tasks.

---

## ✨ Features

### 🏪 TheAppApp App Store
- Browse 8 pre-built specialist agents
- Install with one click
- Filter by tags (backend, frontend, security, etc.)
- Beautiful UI with personality profiles

### 👥 Meet the Team (Specialist Management)
- Manage installed specialists
- Employee of the Month widget 🏆
- Update specialists from store
- Create custom specialists
- Built-in agents available to install

### 📁 Projects
- Create projects with specialist teams
- Assign multiple specialists per project
- Visual team management
- Status tracking

### 🤖 Specialists Available

**Pre-Built Specialists:**
- **Sarah Kim** - Backend Developer (Python/FastAPI)
- **Marcus Webb** - Frontend Developer (React/TypeScript)
- **Jordan Lee** - QA Engineer
- **Taylor Diaz** - DevOps Engineer
- **Casey Park** - Security Expert
- **Riley Morgan** - GitHub Specialist
- **Sam Patel** - Project Manager
- **Alex Chen** - Orchestrator

Each specialist has:
- Full personality and bio
- System prompt optimized for their role
- Tool permissions
- Web search capabilities
- Version tracking

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Qdrant and PostgreSQL)
- OpenAI API key

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/theappapp.git
cd theappapp
```

### 2. Start Docker Containers

```bash
# PostgreSQL
docker run -d -p 55432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=theappapp --name theappapp-postgres postgres:15-alpine

# Qdrant (Vector DB for RAG)
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENAI_API_KEY=your-key-here" > .env
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:55432/theappapp" >> .env
echo "QDRANT_URL=http://localhost:6333" >> .env

# Run migrations
alembic upgrade head

# Start backend
uvicorn backend.api:app --reload --port 8000
```

Backend will be running at http://localhost:8000

### 4. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Start frontend
npm run dev
```

Frontend will be running at http://localhost:5173

---

## 📚 Usage

### Installing a Specialist

1. Navigate to **TheAppApp App Store** (🏪)
2. Browse available specialists
3. Click a specialist card to see full details
4. Click **[Install TheAppApp App]**
5. Specialist is now available in **Installed Specialists**

### Creating a Project

1. Navigate to **Projects** (📁)
2. Click **+ New Project**
3. Enter project name and description
4. Select specialists for your team (multi-select)
5. Click **Create Project**

### Managing Your Team

1. Navigate to **Installed Specialists** (👥)
2. View all installed specialists
3. See Employee of the Month 🏆
4. Update specialists from store (if updates available)
5. Remove specialists
6. Install built-in specialists

---

## 🏗️ Architecture

### Backend (Python/FastAPI)
- **API Routes**: Store, Specialists, Projects, Tasks
- **Services**: RAG (Qdrant), Search (SearxNG), OpenAI
- **Agents**: 11 specialized agents with full execution loop
- **Database**: PostgreSQL with Alembic migrations

### Frontend (React/TypeScript)
- **Pages**: Store, Team, Projects, Dashboard, Settings
- **Routing**: React Router v6
- **Styling**: Tailwind CSS
- **State**: React hooks

### Key Technologies
- FastAPI (backend)
- React + TypeScript (frontend)
- PostgreSQL (database)
- Qdrant (vector database)
- OpenAI (LLM)
- DiceBear (avatars)

---

## 🔧 Configuration

### Backend Environment Variables

```bash
OPENAI_API_KEY=sk-...          # Required
DATABASE_URL=postgresql://...   # Required
QDRANT_URL=http://localhost:6333  # Required
SEARXNG_URL=http://localhost:8080  # Optional
```

### Frontend Environment Variables

```bash
VITE_API_URL=http://localhost:8000  # Required
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# E2E integration test
python -m backend.tests.integration.test_backend_e2e
```

### Test the Store

```bash
# Quick API test (requires backend running)
python -m backend.scripts.test_api_endpoints
```

---

## 📖 API Documentation

Once the backend is running, visit:

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Main Endpoints

**Store:**
- `GET /api/v1/store/specialists` - Browse store
- `POST /api/v1/store/specialists/{id}/install` - Install specialist

**Specialists:**
- `GET /api/v1/specialists` - List installed
- `POST /api/v1/specialists` - Create custom
- `DELETE /api/v1/specialists/{id}` - Remove

**Projects:**
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project

---

## 🎯 Development

### Project Structure

```
theappapp/
├── backend/
│   ├── api/          # FastAPI routes
│   ├── agents/       # 11 specialist agents
│   ├── services/     # Business logic
│   ├── models/       # Database models
│   ├── migrations/   # Alembic migrations
│   ├── data/store/   # Specialist templates
│   └── tests/        # Tests
├── frontend/
│   ├── src/
│   │   ├── pages/    # React pages
│   │   └── services/ # API client
│   └── public/
└── docs/             # Documentation
```

### Key Files

- `backend/data/store/catalog.json` - Specialist catalog
- `backend/services/store_service.py` - Store logic
- `frontend/src/App.tsx` - Main app + routing
- `docs/BRANDING.md` - Branding guidelines

---

## 🤝 Contributing

See [`docs/`](docs/) for development documentation.

---

## 📄 License

TBD

---

## 🙏 Acknowledgments

- OpenAI for GPT models
- DiceBear for avatar generation
- The open-source community

---

**Built with ❤️ using AI assistance**
