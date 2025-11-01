---
description: Instructions for running integration tests with Postgres fixtures
---

# Postgres Integration Testing Guide

## Overview
These steps describe how to run backend integration tests against the Postgres fixtures defined in `backend/tests/integration/conftest.py`. All database-backed integration suites **must** use this setup—no SQLite or in-memory replacements.

## Prerequisites
1. Docker Desktop (or equivalent) running on the host machine.
2. Test database container listening on port `55432` (matches `TEST_DATABASE_URL`).
   - You can start one via:
     ```bash
     docker run --rm -p 55432:5432 \
       -e POSTGRES_USER=appapp \
       -e POSTGRES_PASSWORD=appapp \
       -e POSTGRES_DB=appapp_test \
       postgres:15-alpine
     ```
3. `TEST_DATABASE_URL` exported (optional if using default):
   ```bash
   set TEST_DATABASE_URL=postgresql://appapp:appapp@localhost:55432/appapp_test
   ```

## Running the Tests
```bash
set PYTHONPATH=.
pytest backend/tests/integration --cov=backend.services.orchestrator \
  --cov-report=term-missing --cov-branch
```

The fixtures automatically:
- Apply Alembic migrations to the target database
- Provide a shared SQLAlchemy engine (`postgres_engine`)
- Truncate the core tables before/after each test via `clean_database`

## Adding New DB-Backed Tests
1. Import the `postgres_engine` / `clean_database` fixtures in your test module (Pytest auto-discovers fixtures from `conftest.py`).
2. Use the engine with SQLAlchemy ORM or raw SQL inside tests as needed.
3. Avoid creating new SQLite connections—use `postgres_engine` everywhere to maintain parity.

## Verification Checklist
- [ ] Postgres container running locally
- [ ] `pytest …` executed with coverage (`--cov` + `--cov-branch`)
- [ ] No warnings about missing coverage data (`Failed to generate report` indicates code wasn’t exercised)
- [ ] Tables truncated between tests (verify via logs or manual inspection if necessary)

## FAQ
**Q: What if the fixtures aren’t adequate for a new model?**
- Extend `clean_database` to include additional tables.
- If migrations need special handling, adjust the `apply_migrations` fixture.
- If you still encounter issues, escalate before committing; do **not** fall back to SQLite.
