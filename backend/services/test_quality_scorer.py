"""
Test Quality Scorer Service

AI-powered test quality analysis and scoring.
Evaluates test coverage, assertions, edge cases, and clarity.

Reference: Phase 3.2 - Testing Framework Integration
"""
import logging
import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TestScore:
    """Test quality score breakdown."""
    total_score: int  # 0-100
    coverage_score: int  # 0-30
    assertion_score: int  # 0-25
    edge_case_score: int  # 0-20
    clarity_score: int  # 0-15
    independence_score: int  # 0-10
    feedback: List[str]
    improvements: List[str]


class TestQualityScorer:
    """
    Service for scoring test quality with AI analysis.
    
    Scoring Criteria (0-100):
    - Coverage: Does it test all code paths? (30 points)
    - Assertions: Meaningful assertions vs just "runs without error"? (25 points)
    - Edge cases: Tests boundary conditions? (20 points)
    - Clarity: Clear test names and structure? (15 points)
    - Independence: Tests don't depend on each other? (10 points)
    
    Example:
        scorer = TestQualityScorer(llm_client)
        score = await scorer.score_test(test_code)
        print(f"Quality: {score.total_score}/100")
        for improvement in score.improvements:
            print(f"- {improvement}")
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize test quality scorer.
        
        Args:
            llm_client: Optional LLM client for intelligent analysis
        """
        self.llm_client = llm_client
        logger.info("TestQualityScorer initialized")
    
    async def score_test(
        self,
        test_code: str,
        source_code: Optional[str] = None
    ) -> TestScore:
        """
        Score test quality.
        
        Args:
            test_code: Test code to analyze
            source_code: Optional source code being tested
        
        Returns:
            TestScore with breakdown and feedback
        """
        logger.info("Scoring test quality")
        
        if self.llm_client:
            score = await self._score_with_llm(test_code, source_code)
        else:
            score = self._score_with_heuristics(test_code, source_code)
        
        logger.info(f"Test score: {score.total_score}/100")
        return score
    
    async def _score_with_llm(
        self,
        test_code: str,
        source_code: Optional[str]
    ) -> TestScore:
        """Score using LLM (TODO: implement)."""
        logger.info("LLM test scoring not yet implemented")
        return self._score_with_heuristics(test_code, source_code)
    
    def _score_with_heuristics(
        self,
        test_code: str,
        source_code: Optional[str]
    ) -> TestScore:
        """Score using heuristics."""
        
        # Parse test code
        test_info = self._analyze_test_code(test_code)
        
        # Score each criterion
        coverage_score = self._score_coverage(test_info, source_code)
        assertion_score = self._score_assertions(test_info)
        edge_case_score = self._score_edge_cases(test_info)
        clarity_score = self._score_clarity(test_info)
        independence_score = self._score_independence(test_info)
        
        total_score = (
            coverage_score +
            assertion_score +
            edge_case_score +
            clarity_score +
            independence_score
        )
        
        # Generate feedback
        feedback = []
        improvements = []
        
        if coverage_score < 20:
            feedback.append("⚠️ Low coverage - not testing all code paths")
            improvements.append("Add tests for uncovered branches and error paths")
        
        if assertion_score < 15:
            feedback.append("⚠️ Weak assertions - tests may pass without verifying behavior")
            improvements.append("Add more specific assertions about expected behavior")
        
        if edge_case_score < 10:
            feedback.append("⚠️ Missing edge cases - boundary conditions not tested")
            improvements.append("Add tests for None, empty, max/min, and invalid inputs")
        
        if clarity_score < 10:
            feedback.append("⚠️ Poor clarity - test names or structure unclear")
            improvements.append("Improve test names to describe behavior being tested")
        
        if independence_score < 5:
            feedback.append("⚠️ Tests may have dependencies - could cause flaky failures")
            improvements.append("Ensure tests can run in any order independently")
        
        if not feedback:
            feedback.append("✅ Good test quality overall")
        
        return TestScore(
            total_score=total_score,
            coverage_score=coverage_score,
            assertion_score=assertion_score,
            edge_case_score=edge_case_score,
            clarity_score=clarity_score,
            independence_score=independence_score,
            feedback=feedback,
            improvements=improvements
        )
    
    def _analyze_test_code(self, test_code: str) -> Dict[str, Any]:
        """Analyze test code structure."""
        info = {
            'test_functions': [],
            'assertions': [],
            'fixtures': [],
            'parametrize': [],
            'has_docstrings': False,
            'has_setup_teardown': False
        }
        
        try:
            tree = ast.parse(test_code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        # Extract test function info
                        func_info = {
                            'name': node.name,
                            'docstring': ast.get_docstring(node),
                            'assertions': self._count_assertions(node),
                            'branches': self._count_branches(node)
                        }
                        info['test_functions'].append(func_info)
                        
                        if func_info['docstring']:
                            info['has_docstrings'] = True
                    
                    if node.name in ['setUp', 'tearDown', 'setup', 'teardown']:
                        info['has_setup_teardown'] = True
                
                # Count decorators
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            if decorator.id == 'fixture':
                                info['fixtures'].append(node.name)
                        elif isinstance(decorator, ast.Attribute):
                            if decorator.attr == 'parametrize':
                                info['parametrize'].append(node.name)
        
        except SyntaxError:
            logger.error("Syntax error parsing test code")
        
        return info
    
    def _count_assertions(self, node: ast.FunctionDef) -> int:
        """Count assertions in a function."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                count += 1
            elif isinstance(child, ast.Expr):
                # Check for assert_* calls
                if isinstance(child.value, ast.Call):
                    if hasattr(child.value.func, 'attr'):
                        if 'assert' in child.value.func.attr:
                            count += 1
        return count
    
    def _count_branches(self, node: ast.FunctionDef) -> int:
        """Count conditional branches in a function."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                count += 1
        return count
    
    def _score_coverage(
        self,
        test_info: Dict,
        source_code: Optional[str]
    ) -> int:
        """Score coverage (0-30 points)."""
        score = 0
        
        # Base points for having tests
        if test_info['test_functions']:
            score += 10
        
        # Points for multiple test cases
        test_count = len(test_info['test_functions'])
        if test_count >= 3:
            score += 10
        elif test_count >= 2:
            score += 5
        
        # Points for testing branches
        total_branches = sum(t['branches'] for t in test_info['test_functions'])
        if total_branches > 0:
            score += min(10, total_branches * 2)
        
        return min(score, 30)
    
    def _score_assertions(self, test_info: Dict) -> int:
        """Score assertions (0-25 points)."""
        score = 0
        
        total_assertions = sum(t['assertions'] for t in test_info['test_functions'])
        test_count = len(test_info['test_functions'])
        
        if test_count > 0:
            avg_assertions = total_assertions / test_count
            
            # Points for having assertions
            if avg_assertions >= 3:
                score += 15
            elif avg_assertions >= 2:
                score += 10
            elif avg_assertions >= 1:
                score += 5
            
            # Points for multiple assertions per test
            if total_assertions >= test_count * 2:
                score += 10
        
        return min(score, 25)
    
    def _score_edge_cases(self, test_info: Dict) -> int:
        """Score edge case coverage (0-20 points)."""
        score = 0
        
        # Check for edge case indicators in test names
        edge_case_keywords = [
            'none', 'null', 'empty', 'zero', 'negative',
            'max', 'min', 'boundary', 'invalid', 'error',
            'edge', 'special', 'unicode'
        ]
        
        edge_case_tests = []
        for test in test_info['test_functions']:
            name_lower = test['name'].lower()
            if any(keyword in name_lower for keyword in edge_case_keywords):
                edge_case_tests.append(test)
        
        # Points for edge case tests
        if len(edge_case_tests) >= 3:
            score += 15
        elif len(edge_case_tests) >= 2:
            score += 10
        elif len(edge_case_tests) >= 1:
            score += 5
        
        # Points for parametrize (good for testing multiple cases)
        if test_info['parametrize']:
            score += 5
        
        return min(score, 20)
    
    def _score_clarity(self, test_info: Dict) -> int:
        """Score test clarity (0-15 points)."""
        score = 0
        
        # Points for docstrings
        if test_info['has_docstrings']:
            score += 5
        
        # Points for descriptive test names
        descriptive_count = 0
        for test in test_info['test_functions']:
            # Good names have at least 3 parts: test_function_condition
            parts = test['name'].split('_')
            if len(parts) >= 3:
                descriptive_count += 1
        
        if descriptive_count == len(test_info['test_functions']):
            score += 5
        elif descriptive_count >= len(test_info['test_functions']) / 2:
            score += 3
        
        # Points for setup/teardown (shows organization)
        if test_info['has_setup_teardown']:
            score += 3
        
        # Points for using fixtures
        if test_info['fixtures']:
            score += 2
        
        return min(score, 15)
    
    def _score_independence(self, test_info: Dict) -> int:
        """Score test independence (0-10 points)."""
        score = 10  # Start with full points
        
        # Deduct points for potential dependencies
        # This is hard to detect statically, so we use heuristics
        
        # Check for shared state (class variables, globals)
        # TODO: Implement more sophisticated checks
        
        return score
    
    async def score_test_file(
        self,
        test_file_path: str,
        source_file_path: Optional[str] = None
    ) -> TestScore:
        """
        Score an entire test file.
        
        Args:
            test_file_path: Path to test file
            source_file_path: Optional path to source code
        
        Returns:
            Aggregated TestScore
        """
        try:
            with open(test_file_path, 'r') as f:
                test_code = f.read()
            
            source_code = None
            if source_file_path:
                with open(source_file_path, 'r') as f:
                    source_code = f.read()
            
            return await self.score_test(test_code, source_code)
        
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return TestScore(
                total_score=0,
                coverage_score=0,
                assertion_score=0,
                edge_case_score=0,
                clarity_score=0,
                independence_score=0,
                feedback=["Error: File not found"],
                improvements=[]
            )
    
    def generate_report(self, score: TestScore) -> str:
        """Generate human-readable quality report."""
        report = f"""
Test Quality Report
===================
Total Score: {score.total_score}/100

Breakdown:
- Coverage:      {score.coverage_score}/30
- Assertions:    {score.assertion_score}/25
- Edge Cases:    {score.edge_case_score}/20
- Clarity:       {score.clarity_score}/15
- Independence:  {score.independence_score}/10

Feedback:
"""
        for item in score.feedback:
            report += f"  {item}\n"
        
        if score.improvements:
            report += "\nSuggested Improvements:\n"
            for improvement in score.improvements:
                report += f"  - {improvement}\n"
        
        return report
