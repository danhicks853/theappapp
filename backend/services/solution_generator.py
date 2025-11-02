"""
Solution Generator Service

LLM-generated debugging strategies and solutions.
Analyzes problems and generates multiple ranked solution approaches.

Reference: Phase 3.4 - Debugging & Failure Resolution
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Solution:
    """Generated solution approach."""
    approach: str
    implementation_steps: List[str]
    confidence: float  # 0.0-1.0
    complexity: str  # low, medium, high
    estimated_time_minutes: int
    pros: List[str]
    cons: List[str]
    similar_issues: List[str]


class SolutionGenerator:
    """
    Service for generating debugging solutions.
    
    Process:
    1. Analyze problem with LLM
    2. Query knowledge base for similar issues
    3. Generate multiple solution approaches
    4. Rank by confidence and complexity
    
    Example:
        generator = SolutionGenerator(llm_client, rag_service)
        solutions = await generator.generate_solutions({
            "problem": "Database connection timeout",
            "context": "Using PostgreSQL with connection pooling",
            "constraints": ["Cannot restart database"]
        })
        
        for solution in solutions:
            print(f"{solution.approach} (confidence: {solution.confidence})")
            for step in solution.implementation_steps:
                print(f"  - {step}")
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        rag_service: Optional[Any] = None
    ):
        """Initialize solution generator."""
        self.llm_client = llm_client
        self.rag_service = rag_service
        logger.info("SolutionGenerator initialized")
    
    async def generate_solutions(
        self,
        problem: Dict[str, Any]
    ) -> List[Solution]:
        """
        Generate multiple solution approaches.
        
        Args:
            problem: Dict with problem description, context, constraints
        
        Returns:
            List of Solution approaches, ranked by confidence
        """
        problem_desc = problem.get("problem", "")
        context = problem.get("context", "")
        constraints = problem.get("constraints", [])
        
        logger.info(f"Generating solutions for: {problem_desc[:100]}...")
        
        # Search knowledge base for similar issues
        similar_issues = []
        if self.rag_service:
            similar_issues = await self._find_similar_issues(problem_desc)
        
        # Generate solutions
        if self.llm_client:
            solutions = await self._generate_with_llm(
                problem_desc, context, constraints, similar_issues
            )
        else:
            solutions = self._generate_with_heuristics(
                problem_desc, constraints, similar_issues
            )
        
        # Rank by confidence and complexity
        solutions.sort(key=lambda s: (s.confidence, -self._complexity_score(s.complexity)), reverse=True)
        
        logger.info(f"Generated {len(solutions)} solutions")
        return solutions
    
    async def _find_similar_issues(
        self,
        problem_desc: str
    ) -> List[str]:
        """Find similar issues from knowledge base."""
        if not self.rag_service:
            return []
        
        try:
            results = await self.rag_service.search(
                query=problem_desc,
                specialist_id="failure_patterns",
                top_k=3
            )
            return [r.text[:200] for r in results]
        except Exception as e:
            logger.error(f"Failed to search similar issues: {e}")
            return []
    
    async def _generate_with_llm(
        self,
        problem_desc: str,
        context: str,
        constraints: List[str],
        similar_issues: List[str]
    ) -> List[Solution]:
        """Generate solutions with LLM (TODO: implement)."""
        logger.info("LLM solution generation not yet implemented")
        return self._generate_with_heuristics(problem_desc, constraints, similar_issues)
    
    def _generate_with_heuristics(
        self,
        problem_desc: str,
        constraints: List[str],
        similar_issues: List[str]
    ) -> List[Solution]:
        """Generate solutions with heuristics."""
        solutions = []
        
        # Database connection timeout solutions
        if "connection" in problem_desc.lower() and "timeout" in problem_desc.lower():
            solutions.append(Solution(
                approach="Increase connection timeout",
                implementation_steps=[
                    "Update database connection string with longer timeout",
                    "Test with timeout=60 seconds",
                    "Monitor if timeouts still occur",
                    "If fixed, use as permanent setting"
                ],
                confidence=0.7,
                complexity="low",
                estimated_time_minutes=15,
                pros=["Quick to implement", "Non-invasive"],
                cons=["Doesn't address root cause", "May just delay the issue"],
                similar_issues=similar_issues
            ))
            
            solutions.append(Solution(
                approach="Optimize slow queries",
                implementation_steps=[
                    "Enable query logging to identify slow queries",
                    "Review queries taking >1 second",
                    "Add indexes on frequently queried columns",
                    "Rewrite N+1 queries with joins",
                    "Test performance improvements"
                ],
                confidence=0.9,
                complexity="medium",
                estimated_time_minutes=120,
                pros=["Addresses root cause", "Improves overall performance"],
                cons=["Takes longer to implement", "Requires database knowledge"],
                similar_issues=similar_issues
            ))
            
            solutions.append(Solution(
                approach="Increase connection pool size",
                implementation_steps=[
                    "Check current connection pool settings",
                    "Increase pool_size from default (5) to 20",
                    "Increase max_overflow to 10",
                    "Monitor connection usage",
                    "Adjust based on actual usage"
                ],
                confidence=0.8,
                complexity="low",
                estimated_time_minutes=30,
                pros=["Handles more concurrent requests", "Easy to configure"],
                cons=["Uses more database resources", "Doesn't solve query performance"],
                similar_issues=similar_issues
            ))
        
        # Generic error solutions
        elif "error" in problem_desc.lower():
            solutions.append(Solution(
                approach="Add comprehensive logging",
                implementation_steps=[
                    "Add debug-level logging around the error",
                    "Log all variables and state at failure point",
                    "Run application and collect logs",
                    "Analyze logs to understand failure context",
                    "Use findings to implement specific fix"
                ],
                confidence=0.6,
                complexity="low",
                estimated_time_minutes=30,
                pros=["Provides visibility", "Helps diagnose issue"],
                cons=["Doesn't directly fix the problem"],
                similar_issues=similar_issues
            ))
            
            solutions.append(Solution(
                approach="Reproduce in isolated test",
                implementation_steps=[
                    "Create minimal test case that reproduces error",
                    "Remove dependencies and simplify",
                    "Run test in debugger",
                    "Step through to find exact failure point",
                    "Fix identified issue"
                ],
                confidence=0.8,
                complexity="medium",
                estimated_time_minutes=60,
                pros=["Isolates the problem", "Creates regression test"],
                cons=["May be hard to reproduce"],
                similar_issues=similar_issues
            ))
        
        # Fallback solution
        if not solutions:
            solutions.append(Solution(
                approach="Systematic debugging approach",
                implementation_steps=[
                    "Document exact error message and steps to reproduce",
                    "Search error message in documentation and Stack Overflow",
                    "Review recent code changes",
                    "Add logging and error handling",
                    "Test hypotheses one at a time"
                ],
                confidence=0.5,
                complexity="medium",
                estimated_time_minutes=90,
                pros=["Systematic and thorough"],
                cons=["Time-consuming"],
                similar_issues=similar_issues
            ))
        
        return solutions
    
    def _complexity_score(self, complexity: str) -> int:
        """Convert complexity to numeric score."""
        mapping = {"low": 1, "medium": 2, "high": 3}
        return mapping.get(complexity, 2)
