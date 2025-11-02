"""
Test Maintainer Service

Automated test maintenance with AI updates.
Detects code changes and suggests corresponding test updates.

Reference: Phase 3.2 - Testing Framework Integration
"""
import logging
import ast
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CodeChange:
    """Detected code change."""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    old_code: Optional[str]
    new_code: Optional[str]
    affected_functions: List[str]


@dataclass
class TestUpdate:
    """Suggested test update."""
    test_file: str
    test_function: str
    suggestion: str
    reason: str
    priority: int  # 1-5
    automated: bool  # Can be auto-applied


class TestMaintainer:
    """
    Service for automated test maintenance.
    
    Features:
    - Detect code changes
    - Analyze impact on tests
    - Suggest test updates
    - Generate PR comments
    - Auto-update tests (optional)
    
    Example:
        maintainer = TestMaintainer(llm_client)
        changes = await maintainer.detect_changes(old_commit, new_commit)
        updates = await maintainer.suggest_updates(changes)
        comment = await maintainer.generate_pr_comment(updates)
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize test maintainer.
        
        Args:
            llm_client: Optional LLM client for intelligent suggestions
        """
        self.llm_client = llm_client
        logger.info("TestMaintainer initialized")
    
    async def detect_changes(
        self,
        old_code: str,
        new_code: str,
        file_path: str
    ) -> List[CodeChange]:
        """
        Detect changes between old and new code.
        
        Args:
            old_code: Previous version of code
            new_code: New version of code
            file_path: Path to the file
        
        Returns:
            List of detected changes
        """
        logger.info(f"Detecting changes in: {file_path}")
        
        changes = []
        
        # Parse both versions
        old_functions = self._extract_functions(old_code)
        new_functions = self._extract_functions(new_code)
        
        old_names = {f['name'] for f in old_functions}
        new_names = {f['name'] for f in new_functions}
        
        # Deleted functions
        for name in old_names - new_names:
            old_func = next(f for f in old_functions if f['name'] == name)
            changes.append(CodeChange(
                file_path=file_path,
                change_type='deleted',
                old_code=old_func['code'],
                new_code=None,
                affected_functions=[name]
            ))
        
        # Added functions
        for name in new_names - old_names:
            new_func = next(f for f in new_functions if f['name'] == name)
            changes.append(CodeChange(
                file_path=file_path,
                change_type='added',
                old_code=None,
                new_code=new_func['code'],
                affected_functions=[name]
            ))
        
        # Modified functions
        for name in old_names & new_names:
            old_func = next(f for f in old_functions if f['name'] == name)
            new_func = next(f for f in new_functions if f['name'] == name)
            
            if old_func['code'] != new_func['code']:
                changes.append(CodeChange(
                    file_path=file_path,
                    change_type='modified',
                    old_code=old_func['code'],
                    new_code=new_func['code'],
                    affected_functions=[name]
                ))
        
        logger.info(f"Detected {len(changes)} changes")
        return changes
    
    async def suggest_updates(
        self,
        changes: List[CodeChange]
    ) -> List[TestUpdate]:
        """
        Suggest test updates based on code changes.
        
        Args:
            changes: List of code changes
        
        Returns:
            List of suggested test updates
        """
        logger.info(f"Suggesting updates for {len(changes)} changes")
        
        updates = []
        
        for change in changes:
            if self.llm_client:
                change_updates = await self._suggest_with_llm(change)
            else:
                change_updates = self._suggest_with_heuristics(change)
            
            updates.extend(change_updates)
        
        logger.info(f"Generated {len(updates)} update suggestions")
        return updates
    
    def _extract_functions(self, code: str) -> List[Dict]:
        """Extract function definitions from code."""
        functions = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_code = ast.get_source_segment(code, node) or ""
                    
                    functions.append({
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'code': func_code,
                        'lineno': node.lineno
                    })
        except SyntaxError:
            logger.error("Syntax error parsing code")
        
        return functions
    
    async def _suggest_with_llm(
        self,
        change: CodeChange
    ) -> List[TestUpdate]:
        """Suggest updates using LLM (TODO: implement)."""
        logger.info("LLM test update suggestions not yet implemented")
        return self._suggest_with_heuristics(change)
    
    def _suggest_with_heuristics(
        self,
        change: CodeChange
    ) -> List[TestUpdate]:
        """Suggest updates using heuristics."""
        updates = []
        
        test_file = self._get_test_file_path(change.file_path)
        
        if change.change_type == 'added':
            for func_name in change.affected_functions:
                updates.append(TestUpdate(
                    test_file=test_file,
                    test_function=f"test_{func_name}",
                    suggestion=f"Add tests for new function '{func_name}'",
                    reason=f"New function '{func_name}' added, needs test coverage",
                    priority=4,
                    automated=False
                ))
        
        elif change.change_type == 'deleted':
            for func_name in change.affected_functions:
                updates.append(TestUpdate(
                    test_file=test_file,
                    test_function=f"test_{func_name}",
                    suggestion=f"Remove or update tests for deleted function '{func_name}'",
                    reason=f"Function '{func_name}' was deleted",
                    priority=3,
                    automated=False
                ))
        
        elif change.change_type == 'modified':
            for func_name in change.affected_functions:
                # Analyze what changed
                diff = self._analyze_diff(change.old_code or "", change.new_code or "")
                
                if 'signature' in diff:
                    updates.append(TestUpdate(
                        test_file=test_file,
                        test_function=f"test_{func_name}",
                        suggestion=f"Update test calls for '{func_name}' - signature changed",
                        reason=f"Function signature modified: {diff['signature']}",
                        priority=5,
                        automated=False
                    ))
                
                if 'return' in diff:
                    updates.append(TestUpdate(
                        test_file=test_file,
                        test_function=f"test_{func_name}",
                        suggestion=f"Update assertions for '{func_name}' - return value changed",
                        reason=f"Return value behavior modified",
                        priority=4,
                        automated=False
                    ))
        
        return updates
    
    def _get_test_file_path(self, code_file: str) -> str:
        """Get corresponding test file path."""
        # backend/services/user_service.py -> backend/tests/unit/test_user_service.py
        if '/services/' in code_file:
            return code_file.replace('/services/', '/tests/unit/test_')
        elif '/api/' in code_file:
            return code_file.replace('/api/', '/tests/api/test_')
        else:
            return f"tests/test_{code_file.split('/')[-1]}"
    
    def _analyze_diff(self, old_code: str, new_code: str) -> Dict[str, str]:
        """Analyze differences between old and new code."""
        changes = {}
        
        # Check if signature changed
        old_sig = old_code.split(':')[0] if ':' in old_code else old_code.split('\n')[0]
        new_sig = new_code.split(':')[0] if ':' in new_code else new_code.split('\n')[0]
        
        if old_sig != new_sig:
            changes['signature'] = f"{old_sig} -> {new_sig}"
        
        # Check if return statements changed
        old_returns = [line for line in old_code.split('\n') if 'return' in line]
        new_returns = [line for line in new_code.split('\n') if 'return' in line]
        
        if old_returns != new_returns:
            changes['return'] = "Return behavior modified"
        
        return changes
    
    async def generate_pr_comment(
        self,
        updates: List[TestUpdate]
    ) -> str:
        """
        Generate PR comment with test update suggestions.
        
        Args:
            updates: List of suggested updates
        
        Returns:
            Formatted markdown comment
        """
        if not updates:
            return "✅ No test updates needed for this change."
        
        comment = "## 🧪 Test Update Suggestions\n\n"
        comment += f"Found {len(updates)} test updates to consider:\n\n"
        
        # Group by priority
        high_priority = [u for u in updates if u.priority >= 4]
        medium_priority = [u for u in updates if 2 <= u.priority < 4]
        low_priority = [u for u in updates if u.priority < 2]
        
        if high_priority:
            comment += "### 🔴 High Priority\n\n"
            for update in high_priority:
                comment += f"- **{update.test_file}::{update.test_function}**\n"
                comment += f"  - {update.suggestion}\n"
                comment += f"  - Reason: {update.reason}\n\n"
        
        if medium_priority:
            comment += "### 🟡 Medium Priority\n\n"
            for update in medium_priority:
                comment += f"- **{update.test_file}::{update.test_function}**\n"
                comment += f"  - {update.suggestion}\n\n"
        
        if low_priority:
            comment += "### 🟢 Low Priority\n\n"
            for update in low_priority:
                comment += f"- {update.test_file}::{update.test_function}: {update.suggestion}\n"
        
        comment += "\n---\n"
        comment += "*Generated by TestMaintainer AI*\n"
        
        return comment
    
    async def auto_update_tests(
        self,
        updates: List[TestUpdate],
        dry_run: bool = True
    ) -> Dict[str, str]:
        """
        Automatically update tests (where possible).
        
        Args:
            updates: List of updates
            dry_run: If True, don't actually write files
        
        Returns:
            Dict of file_path -> updated_content
        """
        logger.info(f"Auto-updating tests (dry_run={dry_run})")
        
        automated_updates = [u for u in updates if u.automated]
        
        if not automated_updates:
            logger.info("No automated updates available")
            return {}
        
        updated_files = {}
        
        for update in automated_updates:
            # TODO: Implement actual test file updates
            logger.info(f"Would update: {update.test_file}")
            updated_files[update.test_file] = "# Updated test code"
        
        return updated_files
