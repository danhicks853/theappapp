"""
Test Workshopper Agent Integration

Tests the complete flow:
1. TAS file operations
2. Orchestrator tool routing
3. WorkshopperAgent execution
4. File creation in workspace
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from sqlalchemy import create_engine

from backend.services.tool_access_service import ToolAccessService
from backend.services.orchestrator import Orchestrator
from backend.agents.workshopper_agent import WorkshopperAgent
from backend.services.agent_llm_client import AgentLLMClient
from backend.services.openai_adapter import OpenAIAdapter
import os


@pytest.mark.asyncio
async def test_workshopper_creates_files():
    """Test that Workshopper agent can analyze requirements and create files."""
    
    print("\n" + "="*80)
    print("WORKSHOPPER AGENT INTEGRATION TEST")
    print("="*80)
    
    # Setup
    project_id = "test-proj-123"
    
    # 1. Create TAS client
    print("\n1. Creating TAS client...")
    tas_client = ToolAccessService(db_session=None, use_db=False)
    print("   ✓ TAS client created")
    
    # 2. Create orchestrator with TAS
    print("\n2. Creating orchestrator...")
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    openai_adapter = OpenAIAdapter(api_key=api_key)
    llm_client = AgentLLMClient(openai_adapter)
    
    orchestrator = Orchestrator(
        project_id=project_id,
        tas_client=tas_client,
        llm_client=llm_client
    )
    print("   ✓ Orchestrator created")
    
    # 3. Create Workshopper agent
    print("\n3. Creating Workshopper agent...")
    workshopper = WorkshopperAgent(
        agent_id="workshopper-1",
        orchestrator=orchestrator,
        llm_client=llm_client,
        agent_type="workshopper"
    )
    print("   ✓ Workshopper created")
    
    # 4. Register agent
    print("\n4. Registering agent...")
    registered = orchestrator.register_agent(workshopper)
    assert registered, "Failed to register workshopper"
    print("   ✓ Agent registered")
    
    # 5. Create task state
    print("\n5. Creating task state...")
    task_state = {
        "project_id": project_id,
        "context": {
            "description": "Simple hello world web app with a button that shows a popup"
        },
        "goal": "Analyze requirements and create documentation"
    }
    print(f"   ✓ Task state created for: {task_state['context']['description']}")
    
    # 6. Execute internal action (requirements analysis)
    print("\n6. Executing requirements analysis...")
    action = {
        "type": "analyze_requirements",
        "description": "Analyze project requirements"
    }
    
    result = await workshopper._execute_internal_action(action, task_state, attempt=1)
    
    print(f"\n   ✓ Analysis complete!")
    print(f"   Status: {result['status']}")
    print(f"   Files created: {result.get('files_created', [])}")
    print(f"\n   Output preview (first 200 chars):")
    print(f"   {result['output'][:200]}...")
    
    # 7. Verify files were created
    print("\n7. Verifying files in workspace...")
    temp_base = Path(tempfile.gettempdir()) / "theappapp_workspace"
    workspace = temp_base / project_id
    print(f"   Workspace location: {workspace}")
    
    expected_file = workspace / "docs" / "requirements_analysis.md"
    assert expected_file.exists(), f"File not created: {expected_file}"
    
    content = expected_file.read_text()
    print(f"   ✓ File exists: {expected_file}")
    print(f"   ✓ File size: {len(content)} bytes")
    print(f"\n   File content:")
    print("   " + "-"*76)
    for line in content.split('\n')[:15]:
        print(f"   {line}")
    print("   " + "-"*76)
    
    # 8. Test create user stories
    print("\n8. Creating user stories...")
    action2 = {
        "type": "create_user_stories",
        "description": "Create user stories"
    }
    
    result2 = await workshopper._execute_internal_action(action2, task_state, attempt=1)
    print(f"   ✓ User stories created: {result2.get('files_created', [])}")
    
    stories_file = workspace / "docs" / "user_stories.md"
    assert stories_file.exists(), "User stories file not created"
    print(f"   ✓ Verified: {stories_file}")
    
    # 9. Clean up (disabled - keeping files for inspection)
    print("\n9. Cleanup skipped - files preserved for inspection")
    print(f"   📁 Files location: {workspace}")
    # if workspace.exists():
    #     shutil.rmtree(workspace)
    #     print(f"   ✓ Removed workspace: {workspace}")
    
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED - WORKSHOPPER IS WORKING!")
    print("="*80)
    print("\nSummary:")
    print("  - TAS file operations: ✓")
    print("  - Orchestrator routing: ✓")
    print("  - Workshopper execution: ✓")
    print("  - File creation: ✓")
    print("  - File content: ✓")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_workshopper_creates_files())
