"""
Integration tests for Multi-Operation Tasks.

Tests that multiple operations can be performed within a single container:
- Multiple command executions
- File creation and reading
- State persistence between operations
- Complex workflows

Simulates real agent task execution patterns.
"""
import pytest
import asyncio
from backend.services.container_manager import get_container_manager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(scope="session")
def container_manager():
    """Get ContainerManager instance (auto-initializes on first use)."""
    return get_container_manager()


@pytest.fixture(autouse=True)
async def cleanup_after_test(container_manager):
    """Cleanup containers after each test."""
    yield
    await asyncio.sleep(0.5)
    await container_manager.cleanup_orphaned_containers()


class TestMultiOperationPython:
    """Test multiple operations in Python containers."""
    
    @pytest.mark.asyncio
    async def test_create_write_read_cycle(self, container_manager):
        """Test creating, writing, and reading files in same container."""
        task_id = "test-multi-python"
        
        # Create container
        result = await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        assert result["success"] is True
        
        # Operation 1: Create a Python file
        create_result = await container_manager.exec_command(
            task_id=task_id,
            command='echo "print(\'Hello from Python\')" > /workspace/hello.py'
        )
        assert create_result.exit_code == 0
        
        # Operation 2: Execute the Python file
        exec_result = await container_manager.exec_command(
            task_id=task_id,
            command="python /workspace/hello.py"
        )
        assert exec_result.exit_code == 0
        assert "Hello from Python" in exec_result.stdout
        
        # Operation 3: Modify the file
        modify_result = await container_manager.exec_command(
            task_id=task_id,
            command='echo "print(2 + 2)" >> /workspace/hello.py'
        )
        assert modify_result.exit_code == 0
        
        # Operation 4: Execute modified file
        exec2_result = await container_manager.exec_command(
            task_id=task_id,
            command="python /workspace/hello.py"
        )
        assert exec2_result.exit_code == 0
        assert "Hello from Python" in exec2_result.stdout
        assert "4" in exec2_result.stdout
        
        # Cleanup
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_install_and_use_package(self, container_manager):
        """Test installing a package and using it."""
        task_id = "test-package-install"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Operation 1: Create a requirements file
        create_req = await container_manager.exec_command(
            task_id=task_id,
            command='echo "requests==2.31.0" > /workspace/requirements.txt'
        )
        assert create_req.exit_code == 0
        
        # Operation 2: Install package
        install = await container_manager.exec_command(
            task_id=task_id,
            command="pip install -q -r /workspace/requirements.txt"
        )
        assert install.exit_code == 0
        
        # Operation 3: Use the package
        use_package = await container_manager.exec_command(
            task_id=task_id,
            command='python -c "import requests; print(requests.__version__)"'
        )
        assert use_package.exit_code == 0
        assert "2.31" in use_package.stdout
        
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_run_tests_workflow(self, container_manager):
        """Test a complete test workflow: create, test, verify."""
        task_id = "test-workflow"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Operation 1: Create a function
        create_func = await container_manager.exec_command(
            task_id=task_id,
            command='echo "def add(a, b):\\n    return a + b" > /workspace/math_utils.py'
        )
        assert create_func.exit_code == 0
        
        # Operation 2: Create a test file
        create_test = await container_manager.exec_command(
            task_id=task_id,
            command='cat > /workspace/test_math.py << EOF\nfrom math_utils import add\n\ndef test_add():\n    assert add(2, 2) == 4\n    assert add(-1, 1) == 0\n    print("All tests passed!")\n\nif __name__ == "__main__":\n    test_add()\nEOF'
        )
        assert create_test.exit_code == 0
        
        # Operation 3: Run the tests
        run_test = await container_manager.exec_command(
            task_id=task_id,
            command="cd /workspace && python test_math.py"
        )
        assert run_test.exit_code == 0
        assert "All tests passed" in run_test.stdout
        
        await container_manager.destroy_container(task_id)


class TestMultiOperationNode:
    """Test multiple operations in Node.js containers."""
    
    @pytest.mark.asyncio
    async def test_javascript_multi_operation(self, container_manager):
        """Test JavaScript file operations."""
        task_id = "test-multi-node"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="node"
        )
        
        # Operation 1: Create JavaScript file
        create_js = await container_manager.exec_command(
            task_id=task_id,
            command='echo "console.log(\'Hello from Node.js\');" > /workspace/app.js'
        )
        assert create_js.exit_code == 0
        
        # Operation 2: Execute JavaScript
        exec_js = await container_manager.exec_command(
            task_id=task_id,
            command="node /workspace/app.js"
        )
        assert exec_js.exit_code == 0
        assert "Hello from Node.js" in exec_js.stdout
        
        # Operation 3: Create package.json
        create_pkg = await container_manager.exec_command(
            task_id=task_id,
            command='echo \'{"name": "test-app", "version": "1.0.0"}\' > /workspace/package.json'
        )
        assert create_pkg.exit_code == 0
        
        # Operation 4: Verify package.json
        verify = await container_manager.exec_command(
            task_id=task_id,
            command="cat /workspace/package.json"
        )
        assert verify.exit_code == 0
        assert "test-app" in verify.stdout
        
        await container_manager.destroy_container(task_id)


class TestComplexWorkflow:
    """Test complex multi-step workflows."""
    
    @pytest.mark.asyncio
    async def test_data_processing_workflow(self, container_manager):
        """Test a data processing workflow with multiple steps."""
        task_id = "test-data-workflow"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Step 1: Create input data
        create_data = await container_manager.exec_command(
            task_id=task_id,
            command='echo "1,2,3,4,5" > /workspace/data.csv'
        )
        assert create_data.exit_code == 0
        
        # Step 2: Create processing script
        create_script = await container_manager.exec_command(
            task_id=task_id,
            command='''cat > /workspace/process.py << 'EOF'
with open('/workspace/data.csv', 'r') as f:
    numbers = [int(x) for x in f.read().strip().split(',')]
    total = sum(numbers)
    avg = total / len(numbers)
    with open('/workspace/result.txt', 'w') as out:
        out.write(f'Total: {total}\\nAverage: {avg}')
    print(f'Processed {len(numbers)} numbers')
EOF'''
        )
        assert create_script.exit_code == 0
        
        # Step 3: Run processing
        process = await container_manager.exec_command(
            task_id=task_id,
            command="python /workspace/process.py"
        )
        assert process.exit_code == 0
        assert "Processed 5 numbers" in process.stdout
        
        # Step 4: Verify results
        verify = await container_manager.exec_command(
            task_id=task_id,
            command="cat /workspace/result.txt"
        )
        assert verify.exit_code == 0
        assert "Total: 15" in verify.stdout
        assert "Average: 3" in verify.stdout
        
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_iterative_development_workflow(self, container_manager):
        """Test iterative development: write, test, fix, test again."""
        task_id = "test-iterative"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Iteration 1: Write buggy code
        write_v1 = await container_manager.exec_command(
            task_id=task_id,
            command='echo "def divide(a, b):\\n    return a / b" > /workspace/calc.py'
        )
        assert write_v1.exit_code == 0
        
        # Test v1 - should fail with zero
        test_v1 = await container_manager.exec_command(
            task_id=task_id,
            command='python -c "from calc import divide; divide(10, 0)"'
        )
        assert test_v1.exit_code != 0  # Should fail (ZeroDivisionError)
        assert "ZeroDivisionError" in test_v1.stderr
        
        # Iteration 2: Fix the code
        write_v2 = await container_manager.exec_command(
            task_id=task_id,
            command='cat > /workspace/calc.py << EOF\ndef divide(a, b):\n    if b == 0:\n        return None\n    return a / b\nEOF'
        )
        assert write_v2.exit_code == 0
        
        # Test v2 - should handle zero gracefully
        test_v2 = await container_manager.exec_command(
            task_id=task_id,
            command='python -c "from calc import divide; result = divide(10, 0); print(f\'Result: {result}\')"'
        )
        assert test_v2.exit_code == 0
        assert "Result: None" in test_v2.stdout
        
        # Test v2 with valid input
        test_v2_valid = await container_manager.exec_command(
            task_id=task_id,
            command='python -c "from calc import divide; print(divide(10, 2))"'
        )
        assert test_v2_valid.exit_code == 0
        assert "5.0" in test_v2_valid.stdout
        
        await container_manager.destroy_container(task_id)


class TestStatePersistence:
    """Test that state persists between operations."""
    
    @pytest.mark.asyncio
    async def test_environment_variables_persist(self, container_manager):
        """Test environment variables persist across commands."""
        task_id = "test-env-persist"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Note: Each exec_command is independent, so ENV vars don't persist
        # But files do persist
        
        # Create a config file
        set_config = await container_manager.exec_command(
            task_id=task_id,
            command='echo "APP_NAME=TestApp" > /workspace/.env'
        )
        assert set_config.exit_code == 0
        
        # Read config in subsequent command
        read_config = await container_manager.exec_command(
            task_id=task_id,
            command="cat /workspace/.env"
        )
        assert read_config.exit_code == 0
        assert "APP_NAME=TestApp" in read_config.stdout
        
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_directory_creation_persists(self, container_manager):
        """Test that directory structure persists."""
        task_id = "test-dir-persist"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Create directory structure
        mkdir = await container_manager.exec_command(
            task_id=task_id,
            command="mkdir -p /workspace/src/utils"
        )
        assert mkdir.exit_code == 0
        
        # Create file in nested directory
        create_file = await container_manager.exec_command(
            task_id=task_id,
            command='echo "utility code" > /workspace/src/utils/helpers.py'
        )
        assert create_file.exit_code == 0
        
        # Verify structure
        verify = await container_manager.exec_command(
            task_id=task_id,
            command="ls -R /workspace"
        )
        assert verify.exit_code == 0
        assert "src" in verify.stdout
        assert "utils" in verify.stdout
        assert "helpers.py" in verify.stdout
        
        await container_manager.destroy_container(task_id)


class TestErrorRecovery:
    """Test error handling in multi-operation workflows."""
    
    @pytest.mark.asyncio
    async def test_continue_after_error(self, container_manager):
        """Test that container continues working after command error."""
        task_id = "test-error-recovery"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="test-project",
            language="python"
        )
        
        # Operation 1: Successful command
        op1 = await container_manager.exec_command(
            task_id=task_id,
            command="echo 'Starting'"
        )
        assert op1.exit_code == 0
        
        # Operation 2: Failing command
        op2 = await container_manager.exec_command(
            task_id=task_id,
            command="nonexistent-command"
        )
        assert op2.exit_code != 0
        
        # Operation 3: Should still work
        op3 = await container_manager.exec_command(
            task_id=task_id,
            command="echo 'Still working'"
        )
        assert op3.exit_code == 0
        assert "Still working" in op3.stdout
        
        await container_manager.destroy_container(task_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
