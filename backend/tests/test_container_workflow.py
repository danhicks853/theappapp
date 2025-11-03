"""
Test Docker Container Workflow

Tests the complete container flow:
1. Create container for project
2. Write files via TAS to container volume
3. Execute commands in container
4. Verify output
"""
import pytest
import asyncio
from pathlib import Path

from backend.services.container_manager import get_container_manager
from backend.services.tool_access_service import ToolAccessService, ToolExecutionRequest


@pytest.mark.asyncio
async def test_container_workflow():
    """Test creating container and writing files to it."""
    
    print("\n" + "="*80)
    print("DOCKER CONTAINER WORKFLOW TEST")
    print("="*80)
    
    project_id = "test-container-proj"
    task_id = f"task-{project_id}"
    
    # 1. Get container manager
    print("\n1. Getting container manager...")
    container_mgr = get_container_manager()
    print("   ✓ Container manager ready")
    
    # 2. Create container for Python project
    print("\n2. Creating Docker container...")
    print(f"   Project ID: {project_id}")
    print(f"   Language: python")
    
    result = await container_mgr.create_container(
        task_id=task_id,
        project_id=project_id,
        language="python"
    )
    
    print(f"   ✓ Container created!")
    print(f"   Container ID: {result.get('container_id', 'N/A')[:12]}...")
    print(f"   Status: {result.get('status')}")
    
    try:
        # 3. Create TAS client and write file to container
        print("\n3. Writing files via TAS...")
        tas_client = ToolAccessService(db_session=None, use_db=False)
        
        # Write a Python file
        write_request = ToolExecutionRequest(
            agent_id="test-agent",
            agent_type="backend_developer",
            tool_name="file_system",
            operation="write",
            parameters={
                "project_id": project_id,
                "task_id": task_id,  # Required for container exec
                "path": "hello.py",
                "content": 'print("Hello from Docker container!")\nprint("Container workflow working!")\n'
            },
            project_id=project_id,
            task_id=task_id
        )
        write_result = await tas_client.execute_tool(write_request)
        
        print(f"   ✓ File written: hello.py")
        print(f"   Bytes: {write_result.result.get('bytes_written')}")
        
        # 4. Execute Python script in container
        print("\n4. Executing Python script in container...")
        exec_result = await container_mgr.exec_command(
            task_id=task_id,
            command="python hello.py"
        )
        
        print(f"   ✓ Command executed!")
        print(f"   Exit code: {exec_result.exit_code}")
        print(f"   STDOUT:")
        print("   " + "-"*76)
        for line in exec_result.stdout.split('\n'):
            print(f"   {line}")
        print("   " + "-"*76)
        if exec_result.stderr:
            print(f"   STDERR:")
            print("   " + "-"*76)
            for line in exec_result.stderr.split('\n'):
                print(f"   {line}")
            print("   " + "-"*76)
        
        assert exec_result.exit_code == 0, f"Command failed with exit code {exec_result.exit_code}\nStderr: {exec_result.stderr}"
        assert "Hello from Docker container!" in exec_result.stdout
        
        # 5. List files in container
        print("\n5. Listing files in container...")
        list_request = ToolExecutionRequest(
            agent_id="test-agent",
            agent_type="backend_developer",
            tool_name="file_system",
            operation="list",
            parameters={
                "project_id": project_id,
                "task_id": task_id,
                "path": "."
            },
            project_id=project_id,
            task_id=task_id
        )
        list_result = await tas_client.execute_tool(list_request)
        
        files = list_result.result.get('files', [])
        print(f"   ✓ Found {len(files)} files:")
        for f in files:
            print(f"      - {f['name']} ({f['type']})")
        
        # 6. Execute more complex command
        print("\n6. Testing pip in container...")
        pip_result = await container_mgr.exec_command(
            task_id=task_id,
            command="pip --version"
        )
        print(f"   ✓ Pip version: {pip_result.stdout.strip()}")
        
    finally:
        # 7. Cleanup
        print("\n7. Destroying container...")
        destroy_result = await container_mgr.destroy_container(task_id)
        print(f"   ✓ Container destroyed: {destroy_result.get('status')}")
    
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED - CONTAINER WORKFLOW WORKING!")
    print("="*80)
    print("\nSummary:")
    print("  - Container creation: ✓")
    print("  - File writes to volume: ✓")
    print("  - Command execution: ✓")
    print("  - Python in container: ✓")
    print("  - File listing: ✓")
    print("  - Container cleanup: ✓")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_container_workflow())
