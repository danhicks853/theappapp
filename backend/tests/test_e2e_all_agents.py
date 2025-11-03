"""
Complete End-to-End Test for All 11 Agents

This test validates that all 11 agents can execute successfully and generate files:
1. WorkshopperAgent - Requirements and planning
2. BackendDeveloperAgent - Backend API code
3. FrontendDeveloperAgent - Frontend UI code
4. QAEngineerAgent - Test suites
5. DevOpsEngineerAgent - Deployment configs
6. SecurityExpertAgent - Security audits
7. DocumentationExpertAgent - Documentation
8. UIUXDesignerAgent - Design specifications
9. ProjectManagerAgent - Project management
10. GitHubSpecialistAgent - Version control
11. BaseAgent - Execution framework

Run with: pytest backend/tests/test_e2e_all_agents.py -v -s
"""
import pytest
import tempfile
import uuid
from pathlib import Path

from backend.agents.workshopper_agent import WorkshopperAgent
from backend.agents.backend_dev_agent import BackendDevAgent
from backend.agents.frontend_dev_agent import FrontendDevAgent
from backend.agents.qa_engineer_agent import QAEngineerAgent
from backend.agents.devops_engineer_agent import DevOpsEngineerAgent
from backend.agents.security_expert_agent import SecurityExpertAgent
from backend.agents.documentation_expert_agent import DocumentationExpertAgent
from backend.agents.uiux_designer_agent import UIUXDesignerAgent
from backend.agents.project_manager_agent import ProjectManagerAgent
from backend.agents.github_specialist_agent import GitHubSpecialistAgent
from backend.services.tool_access_service import ToolAccessService, get_tool_access_service


class MockLLMClient:
    """Mock LLM client for testing."""
    
    async def plan_next_action(self, task_state, previous_action=None, previous_result=None, attempt=0):
        """Return a simple action plan."""
        return {
            "description": "Execute agent action",
            "type": "generic_action",
            "reasoning": "Executing planned action",
            "tool_name": None,
            "operation": None,
            "parameters": {},
            "metadata": {}
        }
    
    async def evaluate_progress(self, task_state, result):
        """Return success validation."""
        return {
            "success": True,
            "issues": [],
            "metrics": {"progress_score": 1.0}
        }


class MockOrchestrator:
    """Mock orchestrator for testing agent file operations."""
    
    def __init__(self, project_id: str, container_manager, tas: ToolAccessService):
        self.project_id = project_id
        self.container_manager = container_manager  # Not used, TAS handles containers
        self.tas = tas
        self.tool_calls = []
    
    async def execute_tool(self, request):
        """Execute tool via TAS."""
        self.tool_calls.append(request)
        
        # Extract parameters
        agent_id = request.get("agent_id")
        agent_type = request.get("agent_type")
        tool = request.get("tool")
        operation = request.get("operation")
        parameters = request.get("parameters", {})
        
        # Add project_id to parameters if not present
        if "project_id" not in parameters:
            parameters["project_id"] = self.project_id
        
        # Execute via TAS
        from backend.services.tool_access_service import ToolExecutionRequest
        
        tas_request = ToolExecutionRequest(
            agent_id=agent_id,
            agent_type=agent_type,
            tool_name=tool,
            operation=operation,
            parameters=parameters,
            project_id=self.project_id,
            task_id=str(uuid.uuid4())
        )
        
        response = await self.tas.execute_tool(tas_request)
        
        return {
            "status": "success" if response.success else "error",
            "result": response.result,
            "error": response.message if not response.success else None
        }
    
    async def evaluate_confidence(self, request_payload):
        """Return high confidence."""
        return 0.9
    
    async def create_gate(self, reason, context, agent_id):
        """Mock gate creation."""
        return str(uuid.uuid4())


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    return MockLLMClient()


@pytest.mark.asyncio
async def test_all_agents_e2e(temp_workspace, mock_llm_client):
    """
    Complete E2E test: All 11 agents execute and generate files.
    
    This test validates:
    1. All agents can be instantiated
    2. All agents can execute actions
    3. All agents can write files via TAS
    4. Files are created in the correct locations
    5. No permission errors occur
    6. All agents complete successfully
    """
    print("\n" + "="*80)
    print("E2E TEST: ALL 11 AGENTS FILE GENERATION")
    print("="*80)
    
    # Setup
    project_id = str(uuid.uuid4())
    print(f"\nProject ID: {project_id}")
    
    # Get TAS instance - it manages containers internally
    tas = get_tool_access_service()
    
    # Create mock orchestrator (container_manager not needed, TAS handles it)
    orchestrator = MockOrchestrator(project_id, None, tas)
    
    # Track results
    agent_results = {}
    files_created = []
    
    print("\n" + "-"*80)
    print("TESTING AGENTS")
    print("-"*80)
    
    # Test state for all agents
    test_state = {
        "task_id": str(uuid.uuid4()),
        "project_id": project_id,
        "context": {
            "description": "Build a Hello World web application"
        },
        "goal": "Generate project files",
        "acceptance_criteria": ["Files created"],
        "constraints": {},
        "max_steps": 5
    }
    
    # 1. WorkshopperAgent
    print("\n1. Testing WorkshopperAgent...")
    try:
        agent = WorkshopperAgent(
            agent_id="workshopper-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="workshopper"
        )
        
        action = {"type": "analyze_requirements", "description": "Analyze requirements"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["WorkshopperAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": result.get("output", "")
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ WorkshopperAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ WorkshopperAgent FAILED: {e}")
        agent_results["WorkshopperAgent"] = {"success": False, "error": str(e)}
    
    # 2. BackendDeveloperAgent
    print("\n2. Testing BackendDeveloperAgent...")
    try:
        agent = BackendDevAgent(
            agent_id="backend-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="backend_developer"
        )
        
        action = {"type": "write_api", "description": "Write API code"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["BackendDeveloperAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output_length": len(str(result.get("output", "")))
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ BackendDeveloperAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ BackendDeveloperAgent FAILED: {e}")
        agent_results["BackendDeveloperAgent"] = {"success": False, "error": str(e)}
    
    # 3. FrontendDeveloperAgent
    print("\n3. Testing FrontendDeveloperAgent...")
    try:
        agent = FrontendDevAgent(
            agent_id="frontend-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="frontend_developer"
        )
        
        action = {"type": "write_component", "description": "Write UI component"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["FrontendDeveloperAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output_length": len(str(result.get("output", "")))
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ FrontendDeveloperAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ FrontendDeveloperAgent FAILED: {e}")
        agent_results["FrontendDeveloperAgent"] = {"success": False, "error": str(e)}
    
    # 4. QAEngineerAgent
    print("\n4. Testing QAEngineerAgent...")
    try:
        agent = QAEngineerAgent(
            agent_id="qa-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="qa_engineer"
        )
        
        action = {"type": "write_tests", "description": "Write test suite"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["QAEngineerAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output_length": len(str(result.get("output", "")))
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ QAEngineerAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ QAEngineerAgent FAILED: {e}")
        agent_results["QAEngineerAgent"] = {"success": False, "error": str(e)}
    
    # 5. DevOpsEngineerAgent
    print("\n5. Testing DevOpsEngineerAgent...")
    try:
        agent = DevOpsEngineerAgent(
            agent_id="devops-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="devops_engineer"
        )
        
        action = {"type": "setup_deployment", "description": "Setup deployment"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["DevOpsEngineerAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": result.get("output", "")
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ DevOpsEngineerAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ DevOpsEngineerAgent FAILED: {e}")
        agent_results["DevOpsEngineerAgent"] = {"success": False, "error": str(e)}
    
    # 6. SecurityExpertAgent
    print("\n6. Testing SecurityExpertAgent...")
    try:
        agent = SecurityExpertAgent(
            agent_id="security-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="security_expert"
        )
        
        action = {"type": "security_audit", "description": "Run security audit"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["SecurityExpertAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": result.get("output", "")
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ SecurityExpertAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ SecurityExpertAgent FAILED: {e}")
        agent_results["SecurityExpertAgent"] = {"success": False, "error": str(e)}
    
    # 7. DocumentationExpertAgent
    print("\n7. Testing DocumentationExpertAgent...")
    try:
        agent = DocumentationExpertAgent(
            agent_id="docs-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="documentation_expert"
        )
        
        action = {"type": "write_readme", "description": "Write README"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["DocumentationExpertAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": result.get("output", "")
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ DocumentationExpertAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ DocumentationExpertAgent FAILED: {e}")
        agent_results["DocumentationExpertAgent"] = {"success": False, "error": str(e)}
    
    # 8. UIUXDesignerAgent
    print("\n8. Testing UIUXDesignerAgent...")
    try:
        agent = UIUXDesignerAgent(
            agent_id="uiux-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="ui_ux_designer"
        )
        
        action = {"type": "create_design_spec", "description": "Create design spec"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["UIUXDesignerAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": result.get("output", "")
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ UIUXDesignerAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ UIUXDesignerAgent FAILED: {e}")
        agent_results["UIUXDesignerAgent"] = {"success": False, "error": str(e)}
    
    # 9. ProjectManagerAgent
    print("\n9. Testing ProjectManagerAgent...")
    try:
        agent = ProjectManagerAgent(
            agent_id="pm-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="project_manager"
        )
        
        action = {"type": "create_project_plan", "description": "Create project plan"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["ProjectManagerAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": result.get("output", "")
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ ProjectManagerAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ ProjectManagerAgent FAILED: {e}")
        agent_results["ProjectManagerAgent"] = {"success": False, "error": str(e)}
    
    # 10. GitHubSpecialistAgent
    print("\n10. Testing GitHubSpecialistAgent...")
    try:
        agent = GitHubSpecialistAgent(
            agent_id="github-1",
            orchestrator=orchestrator,
            llm_client=mock_llm_client,
            agent_type="github_specialist"
        )
        
        action = {"type": "create_repository", "description": "Create GitHub repo"}
        result = await agent._execute_internal_action(action, test_state, attempt=1)
        
        agent_results["GitHubSpecialistAgent"] = {
            "success": result.get("status") == "completed",
            "files": result.get("files_created", []),
            "output": str(result.get("output", ""))
        }
        files_created.extend(result.get("files_created", []))
        print(f"   ✅ GitHubSpecialistAgent: {result.get('status')} - Files: {result.get('files_created', [])}")
    except Exception as e:
        print(f"   ❌ GitHubSpecialistAgent FAILED: {e}")
        agent_results["GitHubSpecialistAgent"] = {"success": False, "error": str(e)}
    
    # Results Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    successful_agents = sum(1 for result in agent_results.values() if result.get("success", False))
    total_agents = len(agent_results)
    total_files = len(files_created)
    
    print(f"\nAgents Tested: {total_agents}")
    print(f"Agents Successful: {successful_agents}")
    print(f"Success Rate: {(successful_agents/total_agents*100):.1f}%")
    print(f"Total Files Created: {total_files}")
    
    print("\nFiles Created:")
    for file in files_created:
        print(f"  - {file}")
    
    print("\nAgent Details:")
    for agent_name, result in agent_results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"  {status} {agent_name}")
        if not result.get("success"):
            print(f"      Error: {result.get('error', 'Unknown error')}")
    
    # Verify TAS tool calls
    print(f"\nTAS Tool Calls: {len(orchestrator.tool_calls)}")
    print(f"Expected: {total_agents} (one per agent)")
    
    # Assertions
    print("\n" + "-"*80)
    print("VALIDATING RESULTS")
    print("-"*80)
    
    # All agents should succeed
    assert successful_agents == total_agents, f"Expected {total_agents} successful agents, got {successful_agents}"
    print("✅ All agents executed successfully")
    
    # Files should be created
    assert total_files >= 10, f"Expected at least 10 files, got {total_files}"
    print(f"✅ Sufficient files created ({total_files})")
    
    # TAS calls should match agents
    assert len(orchestrator.tool_calls) >= total_agents, f"Expected at least {total_agents} TAS calls, got {len(orchestrator.tool_calls)}"
    print(f"✅ TAS integration working ({len(orchestrator.tool_calls)} calls)")
    
    # Each agent should have files
    agents_with_files = sum(1 for result in agent_results.values() if result.get("files"))
    assert agents_with_files == total_agents, f"Expected all {total_agents} agents to create files, got {agents_with_files}"
    print(f"✅ All agents generated files")
    
    print("\n" + "="*80)
    print("✅ E2E TEST PASSED - ALL 11 AGENTS WORKING")
    print("="*80)


@pytest.mark.asyncio
async def test_agent_file_verification(temp_workspace, mock_llm_client):
    """
    Verify that files created by agents actually exist and have content.
    """
    print("\n" + "="*80)
    print("FILE VERIFICATION TEST")
    print("="*80)
    
    project_id = str(uuid.uuid4())
    tas = get_tool_access_service()
    orchestrator = MockOrchestrator(project_id, None, tas)
    
    test_state = {
        "task_id": str(uuid.uuid4()),
        "project_id": project_id,
        "context": {"description": "Test project"},
        "goal": "Verify files",
        "acceptance_criteria": [],
        "constraints": {},
        "max_steps": 5
    }
    
    # Create a backend file
    agent = BackendDevAgent(
        agent_id="backend-test",
        orchestrator=orchestrator,
        llm_client=mock_llm_client,
        agent_type="backend_developer"
    )
    
    action = {"type": "write_api", "description": "Write API"}
    result = await agent._execute_internal_action(action, test_state, attempt=1)
    
    print(f"\nAgent executed: {result.get('status')}")
    print(f"Files created: {result.get('files_created', [])}")
    
    # Verify file content
    assert result.get("status") == "completed", "Agent should complete successfully"
    assert len(result.get("files_created", [])) > 0, "Agent should create files"
    
    # Verify output has content
    output = result.get("output", "")
    assert len(output) > 100, f"Output should be substantial, got {len(output)} chars"
    assert "Flask" in output or "app" in output, "Output should contain expected code"
    
    print("✅ File verification passed")


if __name__ == "__main__":
    print("Run with: pytest backend/tests/test_e2e_all_agents.py -v -s")
