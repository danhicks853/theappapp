#!/usr/bin/env python3
"""
Testing Framework Setup Script

Installs and configures all testing frameworks for the project:
- Backend: pytest, pytest-cov, pytest-asyncio, pytest-mock
- Frontend: Vitest, Playwright
- Creates test directories and sample tests

Usage:
    python backend/scripts/setup_testing.py [--backend-only] [--frontend-only]
"""
import subprocess
import sys
from pathlib import Path


class TestingSetup:
    """Set up all testing frameworks."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        self.errors = []
    
    def run(self, backend_only=False, frontend_only=False):
        """Run the setup process."""
        print("=" * 70)
        print("TESTING FRAMEWORK SETUP")
        print("=" * 70)
        print()
        
        if not frontend_only:
            print("Setting up backend testing frameworks...")
            self.setup_backend()
            print()
        
        if not backend_only:
            print("Setting up frontend testing frameworks...")
            self.setup_frontend()
            print()
        
        if self.errors:
            print("\n⚠️  SETUP COMPLETED WITH ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
            return 1
        else:
            print("\n✅ TESTING FRAMEWORK SETUP COMPLETE")
            self.print_next_steps()
            return 0
    
    def setup_backend(self):
        """Set up backend testing with pytest."""
        print("Backend Testing Setup")
        print("-" * 70)
        
        # Check if pytest.ini exists
        pytest_ini = self.root_dir / "pytest.ini"
        if pytest_ini.exists():
            print("✅ pytest.ini already exists")
        else:
            print("⚠️  pytest.ini not found - creating default config")
            self.create_pytest_ini()
        
        # Install pytest and plugins
        print("\nInstalling pytest and plugins...")
        packages = [
            "pytest",
            "pytest-cov",
            "pytest-asyncio",
            "pytest-mock",
            "pytest-xdist",  # For parallel test execution
            "httpx",  # For API testing
            "respx",  # For mocking HTTP
        ]
        
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + packages,
                check=True,
                capture_output=True
            )
            print(f"✅ Installed: {', '.join(packages)}")
        except subprocess.CalledProcessError as e:
            error = f"Failed to install backend packages: {e}"
            self.errors.append(error)
            print(f"❌ {error}")
        
        # Create test directories
        print("\nCreating test directories...")
        test_dirs = [
            self.backend_dir / "tests",
            self.backend_dir / "tests" / "unit",
            self.backend_dir / "tests" / "integration",
            self.backend_dir / "tests" / "api",
        ]
        
        for test_dir in test_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py
            init_file = test_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()
        
        print("✅ Test directories created")
        
        # Create conftest.py if it doesn't exist
        conftest = self.backend_dir / "tests" / "conftest.py"
        if not conftest.exists():
            print("\nCreating conftest.py...")
            self.create_conftest()
            print("✅ conftest.py created")
        else:
            print("\n✅ conftest.py already exists")
        
        # Create sample test
        sample_test = self.backend_dir / "tests" / "unit" / "test_sample.py"
        if not sample_test.exists():
            print("\nCreating sample test...")
            self.create_sample_test()
            print("✅ Sample test created")
        
        print("\n✅ Backend testing setup complete")
    
    def setup_frontend(self):
        """Set up frontend testing with Vitest and Playwright."""
        print("Frontend Testing Setup")
        print("-" * 70)
        
        # Check if package.json exists
        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            error = "package.json not found in frontend directory"
            self.errors.append(error)
            print(f"❌ {error}")
            return
        
        # Install Vitest
        print("\nInstalling Vitest...")
        vitest_packages = [
            "vitest",
            "@vitest/ui",
            "@testing-library/react",
            "@testing-library/jest-dom",
            "jsdom",
        ]
        
        try:
            subprocess.run(
                ["npm", "install", "--save-dev"] + vitest_packages,
                cwd=self.frontend_dir,
                check=True,
                capture_output=True
            )
            print(f"✅ Installed Vitest: {', '.join(vitest_packages)}")
        except subprocess.CalledProcessError as e:
            error = f"Failed to install Vitest: {e}"
            self.errors.append(error)
            print(f"❌ {error}")
        
        # Install Playwright
        print("\nInstalling Playwright...")
        try:
            subprocess.run(
                ["npm", "install", "--save-dev", "@playwright/test"],
                cwd=self.frontend_dir,
                check=True,
                capture_output=True
            )
            print("✅ Installed Playwright")
            
            # Install Playwright browsers
            print("\nInstalling Playwright browsers...")
            subprocess.run(
                ["npx", "playwright", "install", "chromium"],
                cwd=self.frontend_dir,
                check=True,
                capture_output=True
            )
            print("✅ Installed Chromium browser")
        except subprocess.CalledProcessError as e:
            error = f"Failed to install Playwright: {e}"
            self.errors.append(error)
            print(f"❌ {error}")
        
        # Check configs exist
        vitest_config = self.frontend_dir / "vitest.config.ts"
        playwright_config = self.frontend_dir / "playwright.config.ts"
        
        if vitest_config.exists():
            print("\n✅ vitest.config.ts exists")
        else:
            print("\n⚠️  vitest.config.ts not found - should exist")
        
        if playwright_config.exists():
            print("✅ playwright.config.ts exists")
        else:
            print("⚠️  playwright.config.ts not found - should exist")
        
        # Create test directories
        print("\nCreating frontend test directories...")
        test_dirs = [
            self.frontend_dir / "src" / "test",
            self.frontend_dir / "e2e",
        ]
        
        for test_dir in test_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
        
        print("✅ Frontend test directories created")
        
        # Create setup file for Vitest
        setup_file = self.frontend_dir / "src" / "test" / "setup.ts"
        if not setup_file.exists():
            print("\nCreating Vitest setup file...")
            self.create_vitest_setup()
            print("✅ Vitest setup file created")
        
        # Create sample E2E test
        sample_e2e = self.frontend_dir / "e2e" / "sample.spec.ts"
        if not sample_e2e.exists():
            print("\nCreating sample E2E test...")
            self.create_sample_e2e()
            print("✅ Sample E2E test created")
        
        print("\n✅ Frontend testing setup complete")
    
    def create_pytest_ini(self):
        """Create default pytest.ini configuration."""
        content = """[pytest]
testpaths = backend/tests
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
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    llm: LLM-powered tests (require API key)
    llm_rubric: LLM rubric validation tests
    llm_panel: Expensive LLM panel tests
    slow: Slow tests
asyncio_mode = auto
"""
        pytest_ini = self.root_dir / "pytest.ini"
        pytest_ini.write_text(content)
    
    def create_conftest(self):
        """Create conftest.py with common fixtures."""
        content = '''"""
Pytest configuration and shared fixtures.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine("postgresql://test_user:test_pass@localhost:5433/test_db")
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
def llm_client():
    """Provide LLM client for tests."""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not set")
    
    from backend.llm_client import LLMClient
    return LLMClient(api_key=os.getenv("OPENAI_API_KEY"))
'''
        conftest = self.backend_dir / "tests" / "conftest.py"
        conftest.write_text(content)
    
    def create_sample_test(self):
        """Create a sample test file."""
        content = '''"""
Sample unit test.
"""
import pytest


def test_sample():
    """Sample test that always passes."""
    assert 1 + 1 == 2


def test_with_fixture(test_db):
    """Sample test using database fixture."""
    # test_db is a database session
    assert test_db is not None


@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_parametrized(input, expected):
    """Sample parametrized test."""
    assert input * 2 == expected
'''
        sample_test = self.backend_dir / "tests" / "unit" / "test_sample.py"
        sample_test.write_text(content)
    
    def create_vitest_setup(self):
        """Create Vitest setup file."""
        content = '''import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Cleanup after each test
afterEach(() => {
  cleanup()
})
'''
        setup_file = self.frontend_dir / "src" / "test" / "setup.ts"
        setup_file.write_text(content)
    
    def create_sample_e2e(self):
        """Create sample Playwright E2E test."""
        content = '''import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  
  // Check page loaded
  await expect(page).toHaveTitle(/.*/)
  
  // Check for basic elements
  const body = page.locator('body')
  await expect(body).toBeVisible()
});

test('navigation works', async ({ page }) => {
  await page.goto('/');
  
  // Example: Click a link and verify navigation
  // await page.click('text=About')
  // await expect(page).toHaveURL('/about')
});
'''
        sample_e2e = self.frontend_dir / "e2e" / "sample.spec.ts"
        sample_e2e.write_text(content)
    
    def print_next_steps(self):
        """Print next steps for the user."""
        print("\nNEXT STEPS:")
        print("-" * 70)
        print("\nBackend Testing:")
        print("  1. Run tests:")
        print("     pytest")
        print("  2. Run with coverage:")
        print("     pytest --cov")
        print("  3. Run specific test file:")
        print("     pytest backend/tests/unit/test_sample.py")
        print("  4. Run in parallel:")
        print("     pytest -n auto")
        print("\nFrontend Testing:")
        print("  1. Run Vitest:")
        print("     cd frontend && npm test")
        print("  2. Run Vitest with UI:")
        print("     cd frontend && npm run test:ui")
        print("  3. Run Playwright tests:")
        print("     cd frontend && npx playwright test")
        print("  4. Open Playwright report:")
        print("     cd frontend && npx playwright show-report")
        print("\nStaged Pipeline:")
        print("  python backend/scripts/run_tests_staged.py")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Set up testing frameworks for the project"
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Only set up backend testing"
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="Only set up frontend testing"
    )
    
    args = parser.parse_args()
    
    setup = TestingSetup()
    return setup.run(
        backend_only=args.backend_only,
        frontend_only=args.frontend_only
    )


if __name__ == "__main__":
    sys.exit(main())
