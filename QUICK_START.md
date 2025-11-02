# Quick Start Guide 🚀

Get TheAppApp running in 5 minutes!

---

## ✅ Prerequisites Check

```bash
# Check Python
python --version  # Should be 3.11+

# Check Node
node --version    # Should be 18+

# Check Docker
docker --version
```

---

## 🐳 Step 1: Start Docker Containers

```powershell
# PostgreSQL (already running from earlier)
docker ps | Select-String theappapp-postgres

# If not running:
docker run -d -p 55432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=theappapp --name theappapp-postgres postgres:15-alpine

# Qdrant (already running from earlier)
docker ps | Select-String qdrant

# Both should show as "Up"
```

---

## 🔧 Step 2: Backend Setup

```powershell
cd backend

# Activate venv (if not already)
.\.venv\Scripts\Activate.ps1

# Create .env if not exists
if (!(Test-Path .env)) {
    @"
OPENAI_API_KEY=$env:OPENAI_API_KEY
DATABASE_URL=postgresql://postgres:postgres@localhost:55432/theappapp
QDRANT_URL=http://localhost:6333
"@ | Out-File -Encoding utf8 .env
}

# Run migrations
alembic upgrade head

# Start backend
uvicorn backend.api:app --reload --port 8000
```

**Backend running at:** http://localhost:8000
**API Docs:** http://localhost:8000/docs

---

## 🎨 Step 3: Frontend Setup (New Terminal)

```powershell
cd frontend

# Install dependencies (first time only)
npm install

# Create .env if not exists
if (!(Test-Path .env)) {
    "VITE_API_URL=http://localhost:8000" | Out-File -Encoding utf8 .env
}

# Start frontend
npm run dev
```

**Frontend running at:** http://localhost:5173

---

## 🎉 Step 4: Open & Explore!

Open your browser to: **http://localhost:5173**

### Try These Actions:

1. **Browse Store** 🏪
   - Click "Browse Store" on dashboard
   - See 8 pre-built specialists
   - Click any specialist to see details

2. **Install a Specialist**
   - Click "Install TheAppApp App" button
   - Specialist gets added to your team

3. **Meet the Team** 👥
   - Click "Installed Specialists" in sidebar
   - See Employee of the Month 🏆
   - View all installed specialists

4. **Create a Project** 📁
   - Click "Projects" in sidebar
   - Click "+ New Project"
   - Select specialists for the team
   - Create!

---

## 🔍 Verification

### Check Backend is Working:

```powershell
# Health check
Invoke-WebRequest http://localhost:8000/health

# List store specialists
Invoke-WebRequest http://localhost:8000/api/v1/store/specialists | ConvertFrom-Json
```

### Check Frontend is Working:

- Navigate to http://localhost:5173
- Should see TheAppApp dashboard
- Sidebar should show all navigation links

---

## 🐛 Troubleshooting

### Backend won't start?

```powershell
# Check if port 8000 is in use
netstat -ano | Select-String ":8000"

# Check Docker containers
docker ps

# Check migrations
cd backend
alembic current
```

### Frontend won't start?

```powershell
# Clear node_modules and reinstall
Remove-Item -Recurse -Force node_modules
npm install

# Check if port 5173 is in use
netstat -ano | Select-String ":5173"
```

### Database issues?

```powershell
# Check PostgreSQL is running
docker logs theappapp-postgres

# Re-run migrations
cd backend
alembic downgrade base
alembic upgrade head
```

---

## 📊 Quick Test

Run the E2E test to verify everything works:

```powershell
cd backend
$env:PYTHONIOENCODING = 'utf-8'
D:\Github\helixChat\.venv\Scripts\python.exe -m backend.tests.integration.test_backend_e2e
```

Should show:
- ✅ OpenAI integration working
- ✅ RAG service (if Qdrant running)
- ✅ Specialist service
- ✅ Agent execution

---

## 🎯 What's Next?

1. **Explore the Store** - Install all 8 specialists
2. **Create a Project** - Assign specialists to a project
3. **Check the Docs** - http://localhost:8000/docs
4. **Read the Code** - `backend/data/store/catalog.json`

---

**You're all set!** 🎉

Need help? Check `README.md` for full documentation.
