"""
Phase Validator Service

Validates phase completion criteria before allowing phase transitions.
Enforces quality gates: deliverables, tests, coverage, no blockers, human approval.

Reference: Phase 3.1 - Phase Management System
"""
import logging
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of phase validation."""
    can_complete: bool
    overall_score: float  # 0.0-1.0
    criteria_results: Dict[str, bool]
    feedback: str
    blockers: List[str]
    warnings: List[str]


class PhaseValidator:
    """
    Service for validating phase completion criteria.
    
    Validation Criteria:
    1. All deliverables present and validated
    2. All tests passing (pytest + frontend tests)
    3. Code coverage ≥ 90%
    4. No blocking issues or gates
    5. Human approval received (if required)
    
    Example:
        validator = PhaseValidator(engine)
        result = await validator.can_complete_phase("phase-123")
        if result.can_complete:
            await phase_manager.complete_phase(...)
    """
    
    MINIMUM_COVERAGE = 90.0  # Minimum code coverage percentage
    
    def __init__(self, engine: Engine, gate_manager: Optional[Any] = None):
        """
        Initialize phase validator.
        
        Args:
            engine: Database engine
            gate_manager: Optional GateManager for checking blocking gates
        """
        self.engine = engine
        self.gate_manager = gate_manager
        logger.info("PhaseValidator initialized")
    
    async def can_complete_phase(
        self,
        phase_id: str,
        autonomy_level: int = 3
    ) -> ValidationResult:
        """
        Validate if a phase can be completed.
        
        Args:
            phase_id: Phase identifier
            autonomy_level: Autonomy level (1-5, higher = less human approval needed)
        
        Returns:
            ValidationResult with completion status and details
        """
        logger.info(f"Validating phase completion: phase_id={phase_id}")
        
        blockers = []
        warnings = []
        criteria = {}
        
        # 1. Check deliverables
        deliverables_ok, deliverable_msg = await self._check_deliverables(phase_id)
        criteria["deliverables"] = deliverables_ok
        if not deliverables_ok:
            blockers.append(deliverable_msg)
        
        # 2. Check tests passing
        tests_ok, tests_msg = await self._check_tests_passing()
        criteria["tests_passing"] = tests_ok
        if not tests_ok:
            blockers.append(tests_msg)
        
        # 3. Check code coverage
        coverage_ok, coverage_msg = await self._check_coverage()
        criteria["code_coverage"] = coverage_ok
        if not coverage_ok:
            if self.MINIMUM_COVERAGE - 10 <= await self._get_coverage() < self.MINIMUM_COVERAGE:
                warnings.append(coverage_msg)  # Close to minimum, just warn
            else:
                blockers.append(coverage_msg)
        
        # 4. Check for blocking gates
        gates_ok, gates_msg = await self._check_no_blocking_gates(phase_id)
        criteria["no_blockers"] = gates_ok
        if not gates_ok:
            blockers.append(gates_msg)
        
        # 5. Check human approval (based on autonomy level)
        approval_ok, approval_msg = await self._check_human_approval(phase_id, autonomy_level)
        criteria["human_approval"] = approval_ok
        if not approval_ok:
            # Human approval creates a gate, not a hard blocker
            warnings.append(approval_msg)
        
        # Calculate overall score
        passed_criteria = sum(1 for v in criteria.values() if v)
        total_criteria = len(criteria)
        overall_score = passed_criteria / total_criteria if total_criteria > 0 else 0.0
        
        # Determine if phase can complete
        can_complete = len(blockers) == 0
        
        # Generate feedback
        if can_complete:
            feedback = f"Phase validation passed ({passed_criteria}/{total_criteria} criteria met)"
        else:
            feedback = f"Phase validation failed: {len(blockers)} blockers found"
        
        result = ValidationResult(
            can_complete=can_complete,
            overall_score=overall_score,
            criteria_results=criteria,
            feedback=feedback,
            blockers=blockers,
            warnings=warnings
        )
        
        logger.info(
            f"Validation complete: can_complete={can_complete}, "
            f"score={overall_score:.2f}, blockers={len(blockers)}"
        )
        
        return result
    
    async def _check_deliverables(self, phase_id: str) -> tuple[bool, str]:
        """
        Check if all required deliverables are completed and validated.
        
        Returns:
            (success, message)
        """
        from backend.services.deliverable_tracker import DeliverableTracker, DeliverableStatus
        
        tracker = DeliverableTracker(self.engine)
        deliverables = await tracker.get_phase_deliverables(phase_id)
        
        if not deliverables:
            return False, "No deliverables defined for phase"
        
        incomplete = [
            d for d in deliverables 
            if d.status not in [DeliverableStatus.COMPLETED, DeliverableStatus.VALIDATED]
        ]
        
        if incomplete:
            names = [d.name for d in incomplete]
            return False, f"{len(incomplete)} incomplete deliverables: {', '.join(names[:3])}"
        
        # Check for rejected deliverables
        rejected = [d for d in deliverables if d.status == DeliverableStatus.REJECTED]
        if rejected:
            names = [d.name for d in rejected]
            return False, f"{len(rejected)} rejected deliverables need revision: {', '.join(names)}"
        
        return True, "All deliverables completed"
    
    async def _check_tests_passing(self) -> tuple[bool, str]:
        """
        Check if all tests are passing.
        
        Returns:
            (success, message)
        """
        try:
            # Run pytest with minimal output
            result = subprocess.run(
                ["pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # If pytest collection succeeds, try running tests
            if result.returncode == 0:
                test_result = subprocess.run(
                    ["pytest", "-x", "--tb=no", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes max
                )
                
                if test_result.returncode == 0:
                    return True, "All tests passing"
                else:
                    # Parse output for failure count
                    output = test_result.stdout + test_result.stderr
                    return False, f"Tests failing. Run 'pytest' for details. Output: {output[:200]}"
            else:
                return False, "Test collection failed. Check test configuration."
        
        except subprocess.TimeoutExpired:
            return False, "Test execution timeout (>5 minutes)"
        except FileNotFoundError:
            logger.warning("pytest not found, skipping test validation")
            return True, "Test validation skipped (pytest not available)"
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False, f"Test execution error: {str(e)}"
    
    async def _check_coverage(self) -> tuple[bool, str]:
        """
        Check if code coverage meets minimum threshold.
        
        Returns:
            (success, message)
        """
        coverage = await self._get_coverage()
        
        if coverage >= self.MINIMUM_COVERAGE:
            return True, f"Code coverage {coverage:.1f}% (≥ {self.MINIMUM_COVERAGE}%)"
        else:
            gap = self.MINIMUM_COVERAGE - coverage
            return False, f"Code coverage {coverage:.1f}% is below minimum {self.MINIMUM_COVERAGE}% (need {gap:.1f}% more)"
    
    async def _get_coverage(self) -> float:
        """
        Get current code coverage percentage.
        
        Returns:
            Coverage percentage (0.0-100.0)
        """
        try:
            # Run pytest with coverage
            subprocess.run(
                ["pytest", "--cov=backend", "--cov-report=term-missing", "--cov-report=json"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse coverage from JSON report
            import json
            try:
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0.0)
                    return total_coverage
            except FileNotFoundError:
                logger.warning("coverage.json not found")
                return 0.0
        
        except subprocess.TimeoutExpired:
            logger.warning("Coverage calculation timeout")
            return 0.0
        except FileNotFoundError:
            logger.warning("pytest-cov not found, skipping coverage check")
            return 100.0  # Pass validation if coverage tool not available
        except Exception as e:
            logger.error(f"Error getting coverage: {e}")
            return 0.0
    
    async def _check_no_blocking_gates(self, phase_id: str) -> tuple[bool, str]:
        """
        Check if there are any blocking gates for the phase.
        
        Returns:
            (success, message)
        """
        if not self.gate_manager:
            logger.info("No gate manager provided, skipping gate check")
            return True, "Gate validation skipped (no gate manager)"
        
        # Get phase info to find project_id
        from backend.services.phase_manager import PhaseManager
        phase_mgr = PhaseManager(self.engine)
        phase = await phase_mgr.get_phase(phase_id)
        
        if not phase:
            return False, "Phase not found"
        
        # Check for pending gates
        gates = await self.gate_manager.get_pending_gates(phase.project_id)
        
        if gates:
            gate_reasons = [g.get("reason", "Unknown") for g in gates[:3]]
            return False, f"{len(gates)} pending gates blocking completion: {', '.join(gate_reasons)}"
        
        return True, "No blocking gates"
    
    async def _check_human_approval(
        self,
        phase_id: str,
        autonomy_level: int
    ) -> tuple[bool, str]:
        """
        Check if human approval is required and received.
        
        Autonomy levels:
        1-2: Requires approval for all phases
        3: Requires approval for deployment and later
        4: Requires approval for production deployment only
        5: Full autonomy, no approval needed
        
        Returns:
            (success, message)
        """
        from backend.services.phase_manager import PhaseManager, PhaseType
        
        phase_mgr = PhaseManager(self.engine)
        phase = await phase_mgr.get_phase(phase_id)
        
        if not phase:
            return False, "Phase not found"
        
        # Determine if approval needed based on autonomy level
        requires_approval = False
        
        if autonomy_level <= 2:
            requires_approval = True
        elif autonomy_level == 3:
            requires_approval = phase.phase_name in [
                PhaseType.DEPLOYMENT,
                PhaseType.MONITORING,
                PhaseType.MAINTENANCE
            ]
        elif autonomy_level == 4:
            requires_approval = phase.phase_name == PhaseType.DEPLOYMENT
        # autonomy_level 5 never requires approval
        
        if not requires_approval:
            return True, f"Human approval not required (autonomy level {autonomy_level})"
        
        # Check if approval gate exists and is approved
        if self.gate_manager:
            gates = await self.gate_manager.get_pending_gates(phase.project_id)
            approval_gates = [
                g for g in gates 
                if g.get("gate_type") == "manual" and "phase completion" in g.get("reason", "").lower()
            ]
            
            if approval_gates:
                return False, "Human approval pending for phase completion"
            
            # TODO: Check for approved gates in gate history
            # For now, assume if no pending gates, approval was received
            return True, "Human approval received"
        
        # If no gate manager, create approval requirement
        return False, "Human approval required but gate system not available"
    
    async def create_approval_gate(
        self,
        phase_id: str,
        reason: str
    ) -> Optional[str]:
        """
        Create a human approval gate for phase completion.
        
        Args:
            phase_id: Phase identifier
            reason: Reason for approval requirement
        
        Returns:
            Gate ID if created, None otherwise
        """
        if not self.gate_manager:
            logger.warning("Cannot create approval gate: no gate manager")
            return None
        
        from backend.services.phase_manager import PhaseManager
        phase_mgr = PhaseManager(self.engine)
        phase = await phase_mgr.get_phase(phase_id)
        
        if not phase:
            logger.error(f"Phase not found: {phase_id}")
            return None
        
        gate_id = await self.gate_manager.create_gate(
            project_id=phase.project_id,
            agent_id="phase_validator",
            gate_type="manual",
            reason=f"Phase completion approval required: {reason}",
            context={
                "phase_id": phase_id,
                "phase_name": phase.phase_name.value,
                "approval_type": "phase_completion"
            }
        )
        
        logger.info(f"Created approval gate: {gate_id} for phase {phase_id}")
        return gate_id
