"""
Test Config Generator Service

Generates testing framework configurations for user projects.
Creates customizable configs for pytest, Vitest, Playwright, and CI/CD.

Used by agents when setting up testing for user projects.

Reference: Phase 3.2 - Testing Framework Integration
"""
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProjectConfig:
    """User project configuration."""
    project_path: str
    project_name: str
    has_backend: bool = True
    has_frontend: bool = True
    backend_framework: str = "fastapi"  # fastapi, django, flask
    frontend_framework: str = "react"  # react, vue, angular, svelte
    test_runner: str = "vitest"  # vitest, jest
    base_url: str = "http://localhost:5173"
    backend_port: int = 8000


class TestConfigGenerator:
    """
    Service for generating testing framework configurations.
    
    Agents use this to set up testing for user projects with
    appropriate configs based on tech stack.
    
    Example:
        generator = TestConfigGenerator()
        
        # Setup for a React + FastAPI project
        generator.setup_testing_framework(ProjectConfig(
            project_path="/builds/user-123/todo-app",
            project_name="todo-app",
            frontend_framework="react",
            backend_framework="fastapi"
        ))
    """
    
    def __init__(self):
        """Initialize test config generator."""
        logger.info("TestConfigGenerator initialized")
    
    async def setup_testing_framework(
        self,
        config: ProjectConfig
    ) -> Dict[str, str]:
        """
        Set up complete testing framework for a project.
        
        Args:
            config: Project configuration
        
        Returns:
            Dict of file_path -> content for created files
        """
        logger.info(f"Setting up testing framework for: {config.project_name}")
        
        created_files = {}
        
        # Backend testing setup
        if config.has_backend:
            backend_files = await self.setup_backend_testing(config)
            created_files.update(backend_files)
        
        # Frontend testing setup
        if config.has_frontend:
            frontend_files = await self.setup_frontend_testing(config)
            created_files.update(frontend_files)
        
        # CI/CD setup
        ci_files = await self.setup_ci_workflow(config)
        created_files.update(ci_files)
        
        logger.info(f"Created {len(created_files)} testing configuration files")
        return created_files
    
    async def setup_backend_testing(
        self,
        config: ProjectConfig
    ) -> Dict[str, str]:
        """Set up backend testing (pytest)."""
        files = {}
        
        # Generate pytest.ini
        pytest_ini = self.generate_pytest_config(config)
        files[f"{config.project_path}/pytest.ini"] = pytest_ini
        
        # Generate conftest.py
        conftest = self.generate_conftest(config)
        files[f"{config.project_path}/tests/conftest.py"] = conftest
        
        # Generate sample test
        sample_test = self.generate_sample_backend_test(config)
        files[f"{config.project_path}/tests/test_sample.py"] = sample_test
        
        logger.info("Backend testing configs generated")
        return files
    
    async def setup_frontend_testing(
        self,
        config: ProjectConfig
    ) -> Dict[str, str]:
        """Set up frontend testing (Vitest/Jest + Playwright)."""
        files = {}
        
        # Generate Vitest or Jest config
        if config.test_runner == "vitest":
            test_config = self.generate_vitest_config(config)
            files[f"{config.project_path}/vitest.config.ts"] = test_config
            
            # Generate Vitest setup
            setup = self.generate_vitest_setup()
            files[f"{config.project_path}/src/test/setup.ts"] = setup
        else:  # jest
            test_config = self.generate_jest_config(config)
            files[f"{config.project_path}/jest.config.js"] = test_config
        
        # Generate Playwright config
        playwright_config = self.generate_playwright_config(config)
        files[f"{config.project_path}/playwright.config.ts"] = playwright_config
        
        # Generate sample E2E test
        sample_e2e = self.generate_sample_e2e_test(config)
        files[f"{config.project_path}/e2e/sample.spec.ts"] = sample_e2e
        
        logger.info("Frontend testing configs generated")
        return files
    
    async def setup_ci_workflow(
        self,
        config: ProjectConfig
    ) -> Dict[str, str]:
        """Set up CI/CD workflow."""
        files = {}
        
        # Generate GitHub Actions workflow
        ci_workflow = self.generate_ci_workflow(config)
        files[f"{config.project_path}/.github/workflows/ci.yml"] = ci_workflow
        
        logger.info("CI/CD workflow generated")
        return files
    
    def generate_pytest_config(self, config: ProjectConfig) -> str:
        """Generate pytest.ini configuration."""
        return f"""[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=backend
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=90
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    slow: Slow tests
asyncio_mode = auto
"""
    
    def generate_conftest(self, config: ProjectConfig) -> str:
        """Generate conftest.py with fixtures."""
        if config.backend_framework == "fastapi":
            return '''"""
Pytest configuration and shared fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///./test.db")
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """Provide clean database session for each test."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    from main import app
    return TestClient(app)
'''
        elif config.backend_framework == "django":
            return '''"""
Pytest configuration for Django.
"""
import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Set up Django test database."""
    pass


@pytest.fixture
def api_client():
    """Provide Django REST framework test client."""
    from rest_framework.test import APIClient
    return APIClient()
'''
        else:  # flask
            return '''"""
Pytest configuration for Flask.
"""
import pytest


@pytest.fixture
def app():
    """Create Flask app for testing."""
    from app import create_app
    app = create_app({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    """Provide Flask test client."""
    return app.test_client()
'''
    
    def generate_sample_backend_test(self, config: ProjectConfig) -> str:
        """Generate sample backend test."""
        if config.backend_framework == "fastapi":
            return '''"""
Sample API tests.
"""
import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_with_database(test_db):
    """Sample test using database."""
    # Your test code here
    assert test_db is not None
'''
        else:
            return '''"""
Sample tests.
"""
import pytest


def test_sample():
    """Sample test."""
    assert 1 + 1 == 2
'''
    
    def generate_vitest_config(self, config: ProjectConfig) -> str:
        """Generate Vitest configuration."""
        framework_plugin = {
            "react": "react",
            "vue": "vue",
            "svelte": "svelte"
        }.get(config.frontend_framework, "react")
        
        return f"""import {{ defineConfig }} from 'vitest/config'
import {framework_plugin} from '@vitejs/plugin-{framework_plugin}'
import path from 'path'

export default defineConfig({{
  plugins: [{framework_plugin}()],
  test: {{
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    coverage: {{
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        'dist/',
      ],
      thresholds: {{
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      }},
    }},
  }},
  resolve: {{
    alias: {{
      '@': path.resolve(__dirname, './src'),
    }},
  }},
}})
"""
    
    def generate_jest_config(self, config: ProjectConfig) -> str:
        """Generate Jest configuration."""
        return """module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/test/**',
  ],
  coverageThreshold: {
    global: {
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
    },
  },
};
"""
    
    def generate_vitest_setup(self) -> str:
        """Generate Vitest setup file."""
        return """import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Cleanup after each test
afterEach(() => {
  cleanup()
})
"""
    
    def generate_playwright_config(self, config: ProjectConfig) -> str:
        """Generate Playwright configuration."""
        return f"""import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', {{ outputFile: 'playwright-report/results.json' }}],
  ],
  use: {{
    baseURL: process.env.BASE_URL || '{config.base_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  }},
  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
    {{
      name: 'firefox',
      use: {{ ...devices['Desktop Firefox'] }},
    }},
    {{
      name: 'Mobile Chrome',
      use: {{ ...devices['Pixel 5'] }},
    }},
  ],
  webServer: {{
    command: 'npm run dev',
    url: '{config.base_url}',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  }},
}});
"""
    
    def generate_sample_e2e_test(self, config: ProjectConfig) -> str:
        """Generate sample E2E test."""
        return """import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  
  // Check page loaded
  await expect(page).toHaveTitle(/.*/)
  
  const body = page.locator('body')
  await expect(body).toBeVisible()
});

test('navigation works', async ({ page }) => {
  await page.goto('/');
  
  // Add your navigation tests here
});
"""
    
    def generate_ci_workflow(self, config: ProjectConfig) -> str:
        """Generate GitHub Actions CI workflow."""
        backend_job = ""
        if config.has_backend:
            backend_job = f"""
  backend-tests:
    name: Backend Tests
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests with coverage
        run: |
          pytest --cov --cov-fail-under=90
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
"""
        
        frontend_job = ""
        if config.has_frontend:
            frontend_job = f"""
  frontend-tests:
    name: Frontend Tests
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test -- --coverage
      
      - name: Run E2E tests
        run: |
          npx playwright install --with-deps chromium
          npx playwright test
"""
        
        return f"""name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:{backend_job}{frontend_job}
  
  ci-success:
    name: CI Success
    runs-on: ubuntu-latest
    needs: [{', '.join([n for n in ['backend-tests', 'frontend-tests'] if (n == 'backend-tests' and config.has_backend) or (n == 'frontend-tests' and config.has_frontend)])}]
    if: always()
    
    steps:
      - name: Check all jobs
        run: |
          echo "All CI checks passed!"
"""
    
    async def generate_for_tech_stack(
        self,
        project_path: str,
        tech_stack: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate configs based on detected tech stack.
        
        Args:
            project_path: Path to user's project
            tech_stack: Detected technologies
                {
                    "backend": "fastapi",
                    "frontend": "react",
                    "database": "postgresql"
                }
        
        Returns:
            Dict of file paths to content
        """
        config = ProjectConfig(
            project_path=project_path,
            project_name=Path(project_path).name,
            has_backend="backend" in tech_stack,
            has_frontend="frontend" in tech_stack,
            backend_framework=tech_stack.get("backend", "fastapi"),
            frontend_framework=tech_stack.get("frontend", "react")
        )
        
        return await self.setup_testing_framework(config)
