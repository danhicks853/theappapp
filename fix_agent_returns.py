#!/usr/bin/env python3
"""
Script to fix all agent return statements:
1. Change dict returns to Result objects
2. Add deliverable marking before return
"""
import re
from pathlib import Path

AGENTS = [
    'backend_dev_agent',
    'frontend_dev_agent',
    'qa_engineer_agent',
    'devops_engineer_agent',
    'security_expert_agent',
    'documentation_expert_agent',
    'uiux_designer_agent',
    'project_manager_agent',
    'github_specialist_agent'
]

def fix_agent_file(filepath: Path):
    """Fix return statements in an agent file."""
    print(f"Fixing {filepath.name}...")
    
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    # Pattern 1: return {"status": "completed", ...}
    pattern1 = r'return\s+\{\s*"status":\s*"completed",\s*"output":\s*([^,]+),\s*"files_created":\s*\[([^\]]*)\]\s*\}'
    
    def replace_return(match):
        output = match.group(1)
        files = match.group(2)
        return f'return Result(success=True, output={output}, metadata={{"files_created": [{files}]}})'
    
    content = re.sub(pattern1, replace_return, content)
    
    # Pattern 2: Simpler returns
    pattern2 = r'return\s+\{\s*"status":\s*"([^"]+)",\s*"output":\s*([^}]+)\}'
    
    def replace_simple(match):
        status = match.group(1)
        output = match.group(2)
        success = 'True' if status == 'completed' else 'False'
        return f'return Result(success={success}, output={output})'
    
    content = re.sub(pattern2, replace_simple, content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print(f"  ✓ Fixed returns in {filepath.name}")
        return True
    else:
        print(f"  - No changes needed in {filepath.name}")
        return False

def main():
    """Fix all agent files."""
    backend_agents = Path('backend/agents')
    
    fixed_count = 0
    for agent_name in AGENTS:
        filepath = backend_agents / f'{agent_name}.py'
        if filepath.exists():
            if fix_agent_file(filepath):
                fixed_count += 1
        else:
            print(f"  ✗ File not found: {filepath}")
    
    print(f"\n✓ Fixed {fixed_count}/{len(AGENTS)} agent files")

if __name__ == '__main__':
    main()
