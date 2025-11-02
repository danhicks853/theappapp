# Test Reality Philosophy

## Overview

This project follows a "test reality" philosophy: **use real components in tests, minimize mocking.**

The goal is to test the actual behavior of the system as it will run in production, not test mocks of the system.

## Core Principles

### 1. Use Real Databases

**❌ BAD: Mocked Database**
```python
from unittest.mock import patch

@patch('backend.database.query')
def test_get_user(mock_query):
    mock_query.return_value = {"id": 1, "email": "test@example.com"}
    user = get_user(1)
    assert user["email"] == "test@example.com"
```

**Why bad:** You're testing the mock, not your actual database queries.

**✅ GOOD: Real Database**
```python
def test_get_user(test_db):
    # test_db is a real PostgreSQL database
    user_id = create_user(test_db, email="test@example.com")
    user = get_user(test_db, user_id)
    assert user.email == "test@example.com"
```

**Setup:** Use Docker Compose to spin up a test PostgreSQL instance.

```yaml
# docker-compose.test.yml
services:
  test_db:
    image: postgres:15
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"
```

### 2. Use Real LLM Calls

**❌ BAD: Mocked LLM**
```python
@patch('backend.llm_client.complete')
def test_generate_code(mock_llm):
    mock_llm.return_value = "def hello(): return 'world'"
    result = generate_code("write hello function")
    assert "hello" in result
```

**✅ GOOD: Real LLM (with skip option)**
```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not set"
)
def test_generate_code(llm_client):
    # Uses real OpenAI API
    result = generate_code("write a hello function")
    assert "def" in result
    assert "hello" in result.lower()
```

**Benefits:**
- Catches real API changes
- Tests actual LLM behavior
- Finds prompt engineering issues
- Can skip in CI if no API key

### 3. Use Real File System

**❌ BAD: Mocked Files**
```python
@patch('builtins.open', mock_open(read_data="test content"))
def test_read_file():
    content = read_file("file.txt")
    assert content == "test content"
```

**✅ GOOD: Real Temporary Files**
```python
import tempfile
import os

def test_read_file():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_path = f.name
    
    try:
        content = read_file(temp_path)
        assert content == "test content"
    finally:
        os.unlink(temp_path)
```

### 4. Use Real HTTP Requests (Internal APIs)

**❌ BAD: Mocked FastAPI**
```python
@patch('httpx.get')
def test_api_endpoint(mock_get):
    mock_get.return_value.json.return_value = {"status": "ok"}
    response = call_api()
    assert response["status"] == "ok"
```

**✅ GOOD: Real FastAPI TestClient**
```python
from fastapi.testclient import TestClient
from backend.main import app

def test_api_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## When to Mock

Mock **only** external services you don't control:

### External Services to Mock

1. **Third-party APIs**
   - GitHub API (use `responses` or `httpx_mock`)
   - Stripe payment API
   - SendGrid email API

2. **External Infrastructure**
   - AWS S3 (use moto)
   - External webhooks
   - SMS providers

3. **In CI/CD Only**
   - SMTP servers (use `aiosmtpd` locally, mock in CI)
   - Browser automation (Playwright works everywhere)

### Example: Mocking GitHub API

```python
import httpx
import respx

@respx.mock
def test_create_github_repo():
    # Mock GitHub API
    respx.post("https://api.github.com/user/repos").mock(
        return_value=httpx.Response(
            201,
            json={"id": 123, "name": "test-repo"}
        )
    )
    
    # Real code execution
    result = create_github_repo("test-repo")
    assert result["name"] == "test-repo"
```

## Test Fixtures

### Database Fixture

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def test_db():
    """Provide a clean database for each test."""
    engine = create_engine("postgresql://test_user:test_pass@localhost:5433/test_db")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(engine)
```

### LLM Client Fixture

```python
@pytest.fixture(scope="session")
def llm_client():
    """Provide real LLM client."""
    from backend.llm_client import LLMClient
    return LLMClient(api_key=os.getenv("OPENAI_API_KEY"))
```

### Temporary Directory Fixture

```python
@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

## Benefits of Test Reality

### 1. Catch Real Bugs

Mocks hide bugs:
```python
# Mock says query works, but real DB would fail
@patch('db.execute')
def test_complex_query(mock_db):
    mock_db.return_value = [...]
    # Real query has SQL syntax error - not caught!
```

Real tests catch real issues:
```python
def test_complex_query(test_db):
    # If SQL is wrong, test fails immediately
    results = test_db.execute("SELECT * FROM users WHERE...")
```

### 2. Refactoring Confidence

With real tests, you can refactor internals freely:
- Change database schema → tests still work (or break correctly)
- Swap database library → tests validate behavior
- Optimize queries → tests confirm results unchanged

With mocks, internal changes break tests even when behavior is correct.

### 3. Integration Issues

Real tests catch integration bugs:
- Type mismatches between services
- Serialization issues
- Transaction boundaries
- Race conditions
- Connection pooling problems

Mocks can't catch these.

### 4. Production Parity

Tests run like production:
- Same database engine
- Same query planner
- Same connection pooling
- Same error modes

This means fewer "works in tests, fails in production" surprises.

## Performance Considerations

### Speed Optimization

**Use Transactions for Cleanup**
```python
@pytest.fixture
def test_db_fast():
    engine = create_engine(...)
    connection = engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    # Rollback instead of drop/recreate
    session.close()
    transaction.rollback()
    connection.close()
```

**Parallel Test Execution**
```bash
# Run tests in parallel with pytest-xdist
pytest -n auto  # Use all CPU cores
```

**Separate Test Database Per Worker**
```python
# Each worker gets its own database
DB_NAME = f"test_db_{os.getenv('PYTEST_XDIST_WORKER', 'master')}"
```

### Test Data Factories

Use factories to quickly create test data:

```python
# factories.py
from factory import Factory, Faker
from factory.alchemy import SQLAlchemyModelFactory

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = db_session
    
    email = Faker('email')
    username = Faker('user_name')
    created_at = Faker('date_time')

# Usage
def test_user_creation(test_db):
    user = UserFactory.create()
    assert user.id is not None
```

## Test Organization

### Structure

```
tests/
├── unit/           # Fast, isolated tests (real DB, no network)
├── integration/    # Tests with multiple components
├── e2e/            # Full system tests (Playwright)
└── conftest.py     # Shared fixtures
```

### Naming Convention

```python
# Good test names describe behavior
def test_user_creation_stores_hashed_password():
    ...

def test_login_fails_with_wrong_password():
    ...

def test_api_returns_404_for_missing_resource():
    ...
```

## CI/CD Integration

### Docker Compose for CI

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test_pass@localhost:5432/test_db
        run: pytest
```

### Conditional LLM Tests

```yaml
- name: Run LLM tests
  if: ${{ secrets.OPENAI_API_KEY != '' }}
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: pytest -m llm
```

## Summary

**Do's:**
- ✅ Use real PostgreSQL in tests
- ✅ Use real file system operations
- ✅ Use real HTTP with TestClient
- ✅ Use real LLM calls (skip if no key)
- ✅ Mock external services only

**Don'ts:**
- ❌ Don't mock your own code
- ❌ Don't mock the database
- ❌ Don't mock the file system
- ❌ Don't mock internal APIs

**Result:** Tests that actually test your system, catch real bugs, and give you confidence to ship.
