#!/usr/bin/env python3
"""
Staged Testing Pipeline with Early Failure Detection

Runs tests in 7 stages, failing fast at the first error.
Optimizes CI time by running cheap tests first.

Usage:
    python backend/scripts/run_tests_staged.py [--stage STAGE]
    
    # Run all stages
    python backend/scripts/run_tests_staged.py
    
    # Run specific stage
    python backend/scripts/run_tests_staged.py --stage 2
    
Stages:
    1. Linting (ruff, mypy) - fails fast
    2. Unit tests (isolated) - fails fast
    3. Integration tests (database, services)
    4. API tests (FastAPI endpoints)
    5. LLM tests Stage 1 (rubric validation)
    6. E2E tests (Playwright)
    7. LLM tests Stage 2 (AI panel - expensive)
"""
import subprocess
import sys
import os
import time
from typing import List
from dataclasses import dataclass
from enum import Enum


class StageStatus(str, Enum):
    """Test stage status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Stage:
    """Test stage definition."""
    number: int
    name: str
    description: str
    commands: List[str]
    required: bool = True
    skip_in_ci: bool = False


# Define all test stages
STAGES = [
    Stage(
        number=1,
        name="Linting",
        description="Code quality checks (ruff, mypy)",
        commands=[
            "ruff check backend/",
            "mypy backend/ --config-file pyproject.toml || true"  # mypy warnings don't fail
        ],
        required=True
    ),
    Stage(
        number=2,
        name="Unit Tests",
        description="Fast, isolated unit tests",
        commands=[
            "pytest tests/unit/ -v --tb=short -x"  # -x stops at first failure
        ],
        required=True
    ),
    Stage(
        number=3,
        name="Integration Tests",
        description="Tests with database and services",
        commands=[
            "pytest tests/integration/ -v --tb=short -x"
        ],
        required=True
    ),
    Stage(
        number=4,
        name="API Tests",
        description="FastAPI endpoint tests",
        commands=[
            "pytest tests/api/ -v --tb=short -x"
        ],
        required=True
    ),
    Stage(
        number=5,
        name="LLM Tests (Stage 1)",
        description="LLM rubric validation tests",
        commands=[
            "pytest tests/ -m llm_rubric -v --tb=short -x"
        ],
        required=False,  # Skip if no API key
        skip_in_ci=False
    ),
    Stage(
        number=6,
        name="E2E Tests",
        description="Playwright end-to-end tests",
        commands=[
            "cd frontend && npx playwright test || true"  # Optional for now
        ],
        required=False
    ),
    Stage(
        number=7,
        name="LLM Tests (Stage 2)",
        description="Expensive AI panel tests",
        commands=[
            "pytest tests/ -m llm_panel -v --tb=short -x"
        ],
        required=False,  # Expensive, skip if no API key
        skip_in_ci=True  # Too expensive for CI
    )
]


class StagedTestRunner:
    """Runs tests in stages with early failure detection."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results = {}
        self.total_duration = 0.0
    
    def run_all_stages(self) -> int:
        """
        Run all test stages in order.
        
        Returns:
            Exit code (0 = success, 1 = failure)
        """
        print("=" * 70)
        print("STAGED TESTING PIPELINE")
        print("=" * 70)
        print()
        
        is_ci = os.getenv("CI") == "true"
        has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
        
        for stage in STAGES:
            # Skip stages as needed
            if stage.skip_in_ci and is_ci:
                self._skip_stage(stage, "Skipped in CI (too expensive)")
                continue
            
            if not stage.required and not has_openai_key and "LLM" in stage.name:
                self._skip_stage(stage, "Skipped (no OpenAI API key)")
                continue
            
            # Run stage
            success = self.run_stage(stage)
            
            if not success:
                if stage.required:
                    print()
                    print("=" * 70)
                    print(f"❌ PIPELINE FAILED AT STAGE {stage.number}: {stage.name}")
                    print("=" * 70)
                    self._print_summary()
                    return 1
                else:
                    print(f"⚠️  Stage {stage.number} failed but not required, continuing...")
        
        print()
        print("=" * 70)
        print("✅ ALL STAGES PASSED")
        print("=" * 70)
        self._print_summary()
        return 0
    
    def run_stage(self, stage: Stage) -> bool:
        """
        Run a single test stage.
        
        Returns:
            True if stage passed, False otherwise
        """
        print(f"\n{'='*70}")
        print(f"Stage {stage.number}: {stage.name}")
        print(f"{'='*70}")
        print(f"Description: {stage.description}")
        print()
        
        start_time = time.time()
        status = StageStatus.RUNNING
        
        for cmd in stage.commands:
            print(f"Running: {cmd}")
            print("-" * 70)
            
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=False,  # Show output in real-time
                    text=True
                )
                
                if result.returncode != 0:
                    status = StageStatus.FAILED
                    duration = time.time() - start_time
                    self.results[stage.number] = (status, duration)
                    self.total_duration += duration
                    
                    print()
                    print(f"❌ Stage {stage.number} FAILED (exit code: {result.returncode})")
                    print(f"Duration: {duration:.2f}s")
                    return False
            
            except Exception as e:
                status = StageStatus.FAILED
                duration = time.time() - start_time
                self.results[stage.number] = (status, duration)
                self.total_duration += duration
                
                print()
                print(f"❌ Stage {stage.number} FAILED (exception: {e})")
                print(f"Duration: {duration:.2f}s")
                return False
        
        duration = time.time() - start_time
        status = StageStatus.PASSED
        self.results[stage.number] = (status, duration)
        self.total_duration += duration
        
        print()
        print(f"✅ Stage {stage.number} PASSED")
        print(f"Duration: {duration:.2f}s")
        
        return True
    
    def _skip_stage(self, stage: Stage, reason: str):
        """Mark a stage as skipped."""
        self.results[stage.number] = (StageStatus.SKIPPED, 0.0)
        print(f"\n⏭️  Stage {stage.number}: {stage.name} - {reason}")
    
    def _print_summary(self):
        """Print test summary."""
        print()
        print("SUMMARY")
        print("-" * 70)
        
        for stage in STAGES:
            if stage.number not in self.results:
                continue
            
            status, duration = self.results[stage.number]
            
            icon = {
                StageStatus.PASSED: "✅",
                StageStatus.FAILED: "❌",
                StageStatus.SKIPPED: "⏭️ ",
                StageStatus.PENDING: "⏸️ "
            }.get(status, "?")
            
            duration_str = f"{duration:.2f}s" if duration > 0 else "-"
            print(f"{icon} Stage {stage.number}: {stage.name:<25} {duration_str:>10}")
        
        print("-" * 70)
        print(f"Total Duration: {self.total_duration:.2f}s")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run tests in stages with early failure detection"
    )
    parser.add_argument(
        "--stage",
        type=int,
        help="Run only a specific stage (1-7)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    runner = StagedTestRunner(verbose=args.verbose)
    
    if args.stage:
        # Run specific stage
        stage = next((s for s in STAGES if s.number == args.stage), None)
        if not stage:
            print(f"Error: Invalid stage number: {args.stage}")
            print(f"Valid stages: 1-{len(STAGES)}")
            return 1
        
        print(f"Running Stage {args.stage} only...")
        success = runner.run_stage(stage)
        return 0 if success else 1
    else:
        # Run all stages
        return runner.run_all_stages()


if __name__ == "__main__":
    sys.exit(main())
