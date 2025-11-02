"""
Test Generator Service

LLM-powered test generation and optimization.
Generates pytest tests for code, identifies missing coverage, suggests edge cases.

Reference: Phase 3.2 - Testing Framework Integration
"""
import logging
import ast
from typing import List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Generated test case."""
    name: str
    description: str
    test_code: str
    edge_case: bool = False


@dataclass
class CoverageGap:
    """Missing coverage information."""
    file_path: str
    line_numbers: List[int]
    function_name: str
    reason: str


class TestGenerator:
    """
    Service for LLM-powered test generation.
    
    Features:
    - Generate unit tests from code
    - Identify missing coverage areas
    - Suggest edge cases
    - Optimize existing tests
    
    Example:
        generator = TestGenerator(llm_client)
        tests = await generator.generate_unit_tests("backend/services/user_service.py")
        gaps = await generator.identify_missing_coverage(coverage_report)
        edge_cases = await generator.generate_edge_cases(function_signature)
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize test generator.
        
        Args:
            llm_client: Optional LLM client for intelligent generation
        """
        self.llm_client = llm_client
        logger.info("TestGenerator initialized")
    
    async def generate_unit_tests(
        self,
        code_file: str,
        function_name: Optional[str] = None
    ) -> str:
        """
        Generate pytest unit tests for code file or specific function.
        
        Args:
            code_file: Path to code file
            function_name: Optional specific function to test
        
        Returns:
            Generated test code as string
        """
        logger.info(f"Generating unit tests for: {code_file}")
        
        # Read code file
        try:
            with open(code_file, 'r') as f:
                code = f.read()
        except FileNotFoundError:
            logger.error(f"File not found: {code_file}")
            return ""
        
        # Parse code to find functions
        functions = self._extract_functions(code)
        
        if function_name:
            functions = [f for f in functions if f['name'] == function_name]
        
        if not functions:
            logger.warning(f"No functions found in {code_file}")
            return ""
        
        # Generate tests
        if self.llm_client:
            tests = await self._generate_tests_with_llm(code, functions)
        else:
            tests = self._generate_tests_template(code_file, functions)
        
        logger.info(f"Generated tests for {len(functions)} functions")
        return tests
    
    async def identify_missing_coverage(
        self,
        coverage_report: dict
    ) -> List[CoverageGap]:
        """
        Identify areas with missing test coverage.
        
        Args:
            coverage_report: Coverage data (from coverage.json)
        
        Returns:
            List of coverage gaps
        """
        logger.info("Identifying missing coverage")
        
        gaps = []
        
        files = coverage_report.get('files', {})
        for file_path, file_data in files.items():
            missing_lines = file_data.get('missing_lines', [])
            
            if missing_lines:
                # Try to identify function names for missing lines
                gap = CoverageGap(
                    file_path=file_path,
                    line_numbers=missing_lines,
                    function_name="unknown",
                    reason=f"{len(missing_lines)} uncovered lines"
                )
                gaps.append(gap)
        
        logger.info(f"Found {len(gaps)} coverage gaps")
        return gaps
    
    async def generate_edge_cases(
        self,
        function_signature: str,
        function_body: Optional[str] = None
    ) -> List[TestCase]:
        """
        Generate edge case test scenarios for a function.
        
        Args:
            function_signature: Function signature (def func(args): ...)
            function_body: Optional function implementation
        
        Returns:
            List of edge case test scenarios
        """
        logger.info(f"Generating edge cases for: {function_signature[:50]}...")
        
        if self.llm_client:
            edge_cases = await self._generate_edge_cases_with_llm(
                function_signature, function_body
            )
        else:
            edge_cases = self._generate_default_edge_cases(function_signature)
        
        logger.info(f"Generated {len(edge_cases)} edge cases")
        return edge_cases
    
    def _extract_functions(self, code: str) -> List[dict]:
        """Extract function definitions from code."""
        functions = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get function signature
                    args = [arg.arg for arg in node.args.args]
                    
                    functions.append({
                        'name': node.name,
                        'args': args,
                        'lineno': node.lineno,
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'docstring': ast.get_docstring(node)
                    })
        except SyntaxError as e:
            logger.error(f"Syntax error parsing code: {e}")
        
        return functions
    
    async def _generate_tests_with_llm(
        self,
        code: str,
        functions: List[dict]
    ) -> str:
        """Generate tests using LLM (TODO: implement)."""
        logger.info("LLM test generation not yet implemented")
        return self._generate_tests_template("file.py", functions)
    
    def _generate_tests_template(
        self,
        file_path: str,
        functions: List[dict]
    ) -> str:
        """Generate basic test template."""
        module_name = file_path.replace('/', '.').replace('.py', '')
        
        imports = f"""import pytest
from {module_name} import {', '.join(f['name'] for f in functions)}


"""
        
        tests = []
        for func in functions:
            func_name = func['name']
            args = func['args']
            
            # Generate basic test
            test = f"""def test_{func_name}_basic():
    \"\"\"Test {func_name} with basic inputs.\"\"\"
    # TODO: Add test implementation
    result = {func_name}({', '.join('None' for _ in args)})
    assert result is not None


def test_{func_name}_edge_cases():
    \"\"\"Test {func_name} with edge cases.\"\"\"
    # TODO: Test with None, empty values, boundaries
    pass


"""
            tests.append(test)
        
        return imports + '\n'.join(tests)
    
    async def _generate_edge_cases_with_llm(
        self,
        signature: str,
        body: Optional[str]
    ) -> List[TestCase]:
        """Generate edge cases using LLM (TODO: implement)."""
        logger.info("LLM edge case generation not yet implemented")
        return self._generate_default_edge_cases(signature)
    
    def _generate_default_edge_cases(
        self,
        signature: str
    ) -> List[TestCase]:
        """Generate default edge cases based on signature."""
        edge_cases = []
        
        # Extract function name
        func_name = signature.split('(')[0].replace('def ', '').replace('async def ', '').strip()
        
        # Common edge cases
        edge_cases.append(TestCase(
            name=f"test_{func_name}_with_none",
            description="Test with None input",
            test_code=f"def test_{func_name}_with_none():\n    # Test None handling\n    pass",
            edge_case=True
        ))
        
        edge_cases.append(TestCase(
            name=f"test_{func_name}_with_empty",
            description="Test with empty input",
            test_code=f"def test_{func_name}_with_empty():\n    # Test empty values\n    pass",
            edge_case=True
        ))
        
        edge_cases.append(TestCase(
            name=f"test_{func_name}_with_large_input",
            description="Test with large/boundary values",
            test_code=f"def test_{func_name}_with_large_input():\n    # Test boundaries\n    pass",
            edge_case=True
        ))
        
        edge_cases.append(TestCase(
            name=f"test_{func_name}_with_invalid_type",
            description="Test with invalid type",
            test_code=f"def test_{func_name}_with_invalid_type():\n    # Test type errors\n    pass",
            edge_case=True
        ))
        
        return edge_cases
    
    async def optimize_test(
        self,
        test_code: str
    ) -> str:
        """
        Optimize existing test code.
        
        Improvements:
        - Add more assertions
        - Add edge cases
        - Improve test names
        - Add documentation
        
        Args:
            test_code: Existing test code
        
        Returns:
            Optimized test code
        """
        logger.info("Optimizing test code")
        
        if self.llm_client:
            # TODO: Use LLM to optimize
            pass
        
        # Basic optimization: ensure docstrings
        if '"""' not in test_code and "'''" not in test_code:
            # Add docstring
            lines = test_code.split('\n')
            if lines and lines[0].startswith('def test_'):
                lines.insert(1, '    """Test description."""')
                test_code = '\n'.join(lines)
        
        return test_code
    
    async def generate_test_data(
        self,
        data_type: str,
        count: int = 10
    ) -> List[Any]:
        """
        Generate test data of specific type.
        
        Args:
            data_type: Type of data (user, product, order, etc.)
            count: Number of items to generate
        
        Returns:
            List of generated test data
        """
        logger.info(f"Generating {count} {data_type} test data items")
        
        # TODO: Implement with LLM or faker library
        return []
    
    def analyze_test_quality(
        self,
        test_code: str
    ) -> dict:
        """
        Analyze test code quality.
        
        Returns:
            Quality metrics
        """
        metrics = {
            'has_docstring': '"""' in test_code or "'''" in test_code,
            'has_assertions': 'assert' in test_code,
            'line_count': len(test_code.split('\n')),
            'test_count': test_code.count('def test_'),
            'has_fixtures': '@pytest.fixture' in test_code or 'def test_' in test_code and '(' in test_code,
            'has_parametrize': '@pytest.mark.parametrize' in test_code
        }
        
        # Calculate quality score
        score = 0
        if metrics['has_docstring']:
            score += 20
        if metrics['has_assertions']:
            score += 30
        if metrics['has_fixtures']:
            score += 20
        if metrics['has_parametrize']:
            score += 15
        if metrics['test_count'] > 0:
            score += 15
        
        metrics['quality_score'] = min(score, 100)
        
        return metrics
