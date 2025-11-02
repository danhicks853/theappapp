# Testing Quick Reference

## 🚀 Quick Start

```powershell
# Run all Phase 1 tests
.\scripts\run_phase1_tests.ps1
```

That's it! The script handles:
1. Docker service check
2. Database setup
3. Migration execution
4. Test execution with coverage

---

## 📋 Manual Testing

### Setup
```bash
# 1. Start services
docker-compose up -d postgres qdrant

# 2. Prepare test database
python scripts/prepare_test_database.py

# 3. Verify services
docker ps
```

### Run Tests
```bash
# All tests with coverage
pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term

# Unit tests only
pytest backend/tests/unit/ -v

# Integration tests only
pytest backend/tests/integration/ -v

# Specific test file
pytest backend/tests/integration/test_api_endpoints.py -v

# Specific test
pytest backend/tests/unit/test_gate_manager.py::TestGateManager::test_create_gate -v

# With verbose output
pytest backend/tests/ -v -s

# Stop on first failure
pytest backend/tests/ -x

# Run last failed tests
pytest backend/tests/ --lf
```

---

## 📊 Coverage Reports

### Generate Report
```bash
pytest backend/tests/ --cov=backend --cov-report=html
```

### View Report
```bash
# Open in browser
start backend/htmlcov/index.html  # Windows
open backend/htmlcov/index.html   # Mac
```

### Terminal Report
```bash
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

---

## 🧪 Test Organization

```
backend/tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (isolated, mocked)
│   ├── test_loop_detection.py
│   └── test_gate_manager.py
└── integration/             # Integration tests (real DB)
    ├── test_database_migrations.py
    ├── test_api_endpoints.py
    ├── test_loop_detection_integration.py
    ├── test_rag_system.py
    ├── test_cross_project_learning.py
    └── test_cross_system_integration.py
```

---

## 🎯 Test Markers

### Run by marker
```bash
# Unit tests only
pytest backend/tests/ -m unit

# Integration tests only
pytest backend/tests/ -m integration

# Async tests
pytest backend/tests/ -m asyncio
```

### Skip slow tests
```bash
pytest backend/tests/ -m "not slow"
```

---

## 🔧 Environment Variables

```bash
# Test database
export DATABASE_URL="postgresql://postgres:postgres@localhost:55432/theappapp_test"

# Testing mode
export TESTING="true"

# Mock API keys
export OPENAI_API_KEY="test_key_for_mocking"
export QDRANT_URL="http://localhost:6333"
```

---

## 📈 Test Statistics

**Total Test Cases**: 99

**By Type:**
- Unit: 29 tests
- Integration: 70 tests

**By System:**
- Database/Migrations: 5 tests
- API Endpoints: 34 tests
- Loop Detection: 28 tests
- RAG System: 18 tests
- Cross-System: 6 tests
- Services: 8 tests

---

## 🐛 Debugging Tests

### Verbose output
```bash
pytest backend/tests/ -vv -s
```

### Show print statements
```bash
pytest backend/tests/ -s
```

### Drop into debugger on failure
```bash
pytest backend/tests/ --pdb
```

### Show local variables on failure
```bash
pytest backend/tests/ -l
```

---

## 🔄 Continuous Testing

### Watch mode (requires pytest-watch)
```bash
pip install pytest-watch
ptw backend/tests/ -- -v
```

### Run on file change (requires pytest-xdist)
```bash
pip install pytest-xdist
pytest backend/tests/ -f
```

---

## 📚 Documentation

- **Test Plan**: `docs/testing/PHASE_1_TEST_PLAN.md`
- **Test Complete**: `docs/testing/PHASE_1_TESTING_COMPLETE.md`
- **Development Guardrails**: `docs/testing/development_guardrails.md`

---

## ✅ Pre-Commit Checklist

Before committing code:

```bash
# 1. Run tests
pytest backend/tests/ -v

# 2. Check coverage
pytest backend/tests/ --cov=backend --cov-report=term

# 3. Verify migrations
python scripts/prepare_test_database.py

# 4. Check linting
ruff check backend/

# 5. Type checking (if using mypy)
mypy backend/
```

---

## 🚦 CI/CD Integration

### GitHub Actions (example)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: docker-compose up -d postgres qdrant
      - run: pip install -r requirements.txt
      - run: python scripts/prepare_test_database.py
      - run: pytest backend/tests/ --cov=backend
```

---

## 💡 Tips

1. **Use fixtures** - Don't repeat setup code
2. **Mock external APIs** - Keep tests fast and deterministic
3. **Test one thing** - Each test should verify one behavior
4. **Clear test names** - `test_gate_approval_creates_approval_record`
5. **Arrange-Act-Assert** - Follow AAA pattern
6. **Clean up** - Use fixtures with teardown or transactions

---

## 🎉 Success!

If you see all tests passing:
```
======================== 99 passed in 45.2s =========================
```

You're ready for Phase 2! 🚀
