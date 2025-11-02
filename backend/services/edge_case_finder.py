"""
Edge Case Finder Service

AI-assisted edge case identification for comprehensive test coverage.
Analyzes function signatures and logic to suggest non-obvious test scenarios.

Reference: Phase 3.2 - Testing Framework Integration
"""
import logging
import ast
from typing import List, Optional, Any
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class EdgeCaseType(str, Enum):
    """Types of edge cases."""
    NULL_INPUT = "null_input"
    EMPTY_COLLECTION = "empty_collection"
    BOUNDARY_VALUE = "boundary_value"
    TYPE_MISMATCH = "type_mismatch"
    CONCURRENT_ACCESS = "concurrent_access"
    UNICODE_SPECIAL_CHARS = "unicode_special_chars"
    MAX_MIN_VALUES = "max_min_values"
    ZERO_DIVISION = "zero_division"
    RECURSION_DEPTH = "recursion_depth"
    MEMORY_LIMIT = "memory_limit"


@dataclass
class EdgeCase:
    """Edge case test scenario."""
    type: EdgeCaseType
    description: str
    test_scenario: str
    expected_behavior: str
    priority: int  # 1-5, 5 is highest
    rationale: str


class EdgeCaseFinder:
    """
    Service for AI-assisted edge case identification.
    
    Features:
    - Analyze function signatures and types
    - Identify boundary conditions
    - Suggest concurrency edge cases
    - Find unicode and special character issues
    - Detect potential overflow/underflow
    
    Example:
        finder = EdgeCaseFinder(llm_client)
        edge_cases = await finder.find_edge_cases(function_def)
        for case in edge_cases:
            print(f"{case.type}: {case.description}")
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize edge case finder.
        
        Args:
            llm_client: Optional LLM client for intelligent analysis
        """
        self.llm_client = llm_client
        logger.info("EdgeCaseFinder initialized")
    
    async def find_edge_cases(
        self,
        function_def: str,
        context: Optional[str] = None
    ) -> List[EdgeCase]:
        """
        Find edge cases for a function.
        
        Args:
            function_def: Function definition code
            context: Optional surrounding code context
        
        Returns:
            List of identified edge cases
        """
        logger.info(f"Finding edge cases for function: {function_def[:50]}...")
        
        # Parse function
        function_info = self._parse_function(function_def)
        
        if not function_info:
            logger.warning("Could not parse function")
            return []
        
        # Generate edge cases
        if self.llm_client:
            edge_cases = await self._find_with_llm(function_info, context)
        else:
            edge_cases = self._find_with_heuristics(function_info)
        
        # Sort by priority
        edge_cases.sort(key=lambda x: x.priority, reverse=True)
        
        logger.info(f"Found {len(edge_cases)} edge cases")
        return edge_cases
    
    def _parse_function(self, function_def: str) -> Optional[dict]:
        """Parse function definition."""
        try:
            tree = ast.parse(function_def)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return {
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'arg_types': self._extract_types(node),
                        'return_type': self._get_return_type(node),
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'has_loops': self._has_loops(node),
                        'has_recursion': self._has_recursion(node),
                        'body': ast.unparse(node) if hasattr(ast, 'unparse') else function_def
                    }
        except SyntaxError:
            logger.error("Syntax error parsing function")
        
        return None
    
    def _extract_types(self, node: ast.FunctionDef) -> dict:
        """Extract type hints from function."""
        types = {}
        for arg in node.args.args:
            if arg.annotation:
                type_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                types[arg.arg] = type_str
        return types
    
    def _get_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Get return type annotation."""
        if node.returns:
            return ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
        return None
    
    def _has_loops(self, node: ast.FunctionDef) -> bool:
        """Check if function has loops."""
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):
                return True
        return False
    
    def _has_recursion(self, node: ast.FunctionDef) -> bool:
        """Check if function is recursive."""
        func_name = node.name
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if hasattr(child.func, 'id') and child.func.id == func_name:
                    return True
        return False
    
    async def _find_with_llm(
        self,
        function_info: dict,
        context: Optional[str]
    ) -> List[EdgeCase]:
        """Find edge cases using LLM (TODO: implement)."""
        logger.info("LLM edge case finding not yet implemented")
        return self._find_with_heuristics(function_info)
    
    def _find_with_heuristics(self, function_info: dict) -> List[EdgeCase]:
        """Find edge cases using heuristics."""
        edge_cases = []
        
        func_name = function_info['name']
        args = function_info['args']
        arg_types = function_info['arg_types']
        
        # Check for None/null inputs
        for arg in args:
            edge_cases.append(EdgeCase(
                type=EdgeCaseType.NULL_INPUT,
                description=f"Test {func_name} with None for {arg}",
                test_scenario=f"{func_name}(..., {arg}=None, ...)",
                expected_behavior="Should handle None gracefully or raise ValueError",
                priority=5,
                rationale=f"Null input is a common source of errors"
            ))
        
        # Check for collection types
        for arg, type_hint in arg_types.items():
            if any(t in type_hint.lower() for t in ['list', 'dict', 'set', 'tuple']):
                edge_cases.append(EdgeCase(
                    type=EdgeCaseType.EMPTY_COLLECTION,
                    description=f"Test {func_name} with empty {type_hint} for {arg}",
                    test_scenario=f"{func_name}(..., {arg}={{}}, ...)",
                    expected_behavior="Should handle empty collection without errors",
                    priority=4,
                    rationale="Empty collections can cause iteration errors"
                ))
        
        # Check for string types
        for arg, type_hint in arg_types.items():
            if 'str' in type_hint.lower():
                edge_cases.append(EdgeCase(
                    type=EdgeCaseType.UNICODE_SPECIAL_CHARS,
                    description=f"Test {func_name} with unicode/special chars for {arg}",
                    test_scenario=f"{func_name}(..., {arg}='🔥test™', ...)",
                    expected_behavior="Should handle unicode correctly",
                    priority=3,
                    rationale="Unicode can cause encoding/decoding errors"
                ))
                
                edge_cases.append(EdgeCase(
                    type=EdgeCaseType.EMPTY_COLLECTION,
                    description=f"Test {func_name} with empty string for {arg}",
                    test_scenario=f"{func_name}(..., {arg}='', ...)",
                    expected_behavior="Should handle empty string",
                    priority=4,
                    rationale="Empty strings are often edge cases"
                ))
        
        # Check for integer/float types
        for arg, type_hint in arg_types.items():
            if any(t in type_hint.lower() for t in ['int', 'float']):
                edge_cases.append(EdgeCase(
                    type=EdgeCaseType.MAX_MIN_VALUES,
                    description=f"Test {func_name} with max/min values for {arg}",
                    test_scenario=f"{func_name}(..., {arg}=sys.maxsize, ...)",
                    expected_behavior="Should handle extreme values",
                    priority=3,
                    rationale="Integer overflow/underflow possible"
                ))
                
                edge_cases.append(EdgeCase(
                    type=EdgeCaseType.BOUNDARY_VALUE,
                    description=f"Test {func_name} with zero for {arg}",
                    test_scenario=f"{func_name}(..., {arg}=0, ...)",
                    expected_behavior="Should handle zero correctly",
                    priority=4,
                    rationale="Zero is a common boundary value"
                ))
                
                edge_cases.append(EdgeCase(
                    type=EdgeCaseType.BOUNDARY_VALUE,
                    description=f"Test {func_name} with negative value for {arg}",
                    test_scenario=f"{func_name}(..., {arg}=-1, ...)",
                    expected_behavior="Should validate negative values",
                    priority=3,
                    rationale="Negative values may be invalid"
                ))
        
        # Check for division operations
        if any(op in function_info['body'] for op in ['/', '//', '%']):
            edge_cases.append(EdgeCase(
                type=EdgeCaseType.ZERO_DIVISION,
                description=f"Test {func_name} with denominator zero",
                test_scenario="Test division by zero scenario",
                expected_behavior="Should raise ZeroDivisionError or handle gracefully",
                priority=5,
                rationale="Division by zero will crash"
            ))
        
        # Check for recursion
        if function_info['has_recursion']:
            edge_cases.append(EdgeCase(
                type=EdgeCaseType.RECURSION_DEPTH,
                description=f"Test {func_name} with deep recursion",
                test_scenario="Test with input causing deep recursion",
                expected_behavior="Should handle or limit recursion depth",
                priority=4,
                rationale="Stack overflow from deep recursion"
            ))
        
        # Check for async functions (concurrency)
        if function_info['is_async']:
            edge_cases.append(EdgeCase(
                type=EdgeCaseType.CONCURRENT_ACCESS,
                description=f"Test {func_name} with concurrent calls",
                test_scenario="Call function multiple times concurrently",
                expected_behavior="Should be thread-safe or document concurrency limits",
                priority=3,
                rationale="Async functions may have race conditions"
            ))
        
        # Check for loops (large inputs)
        if function_info['has_loops']:
            edge_cases.append(EdgeCase(
                type=EdgeCaseType.MEMORY_LIMIT,
                description=f"Test {func_name} with large input",
                test_scenario="Test with very large collection/number",
                expected_behavior="Should handle large inputs or enforce limits",
                priority=3,
                rationale="Large inputs can cause memory issues"
            ))
        
        return edge_cases
    
    async def prioritize_edge_cases(
        self,
        edge_cases: List[EdgeCase],
        coverage_data: Optional[dict] = None
    ) -> List[EdgeCase]:
        """
        Prioritize edge cases based on coverage and risk.
        
        Args:
            edge_cases: List of edge cases
            coverage_data: Optional coverage report
        
        Returns:
            Prioritized list of edge cases
        """
        # If we have coverage data, prioritize uncovered areas
        if coverage_data:
            # TODO: Adjust priorities based on coverage
            pass
        
        # Sort by priority
        return sorted(edge_cases, key=lambda x: x.priority, reverse=True)
    
    def generate_test_code(
        self,
        edge_case: EdgeCase,
        function_name: str
    ) -> str:
        """
        Generate pytest code for an edge case.
        
        Args:
            edge_case: Edge case to test
            function_name: Function being tested
        
        Returns:
            Generated test code
        """
        test_name = f"test_{function_name}_{edge_case.type.value}"
        
        test_code = f'''def {test_name}():
    """
    {edge_case.description}
    
    Expected: {edge_case.expected_behavior}
    Rationale: {edge_case.rationale}
    """
    # TODO: Implement test for: {edge_case.test_scenario}
    pass
'''
        
        return test_code
