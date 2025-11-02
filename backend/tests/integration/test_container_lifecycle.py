"""
Integration tests for Container Lifecycle.

Tests the full lifecycle of Docker containers:
- Container creation for all 8 languages
- Container destruction and cleanup
- Volume mounting and persistence
- Error handling

Requires Docker to be running.
"""
import pytest
import asyncio
from backend.services.container_manager import get_container_manager

# Mark all tests in this file as integration and requiring Docker
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(scope="session")
def container_manager():
    """Get ContainerManager instance (auto-initializes on first use)."""
    return get_container_manager()


@pytest.fixture(autouse=True)
async def cleanup_after_test(container_manager):
    """Cleanup any containers after each test."""
    yield
    # Cleanup any containers that might have been created
    await asyncio.sleep(0.5)  # Brief delay to ensure cleanup
    result = await container_manager.cleanup_orphaned_containers()
    if result["cleaned"] > 0:
        print(f"\n⚠️  Cleaned up {result['cleaned']} orphaned containers after test")


class TestContainerCreation:
    """Test container creation for all supported languages."""
    
    @pytest.mark.asyncio
    async def test_create_python_container(self, container_manager):
        """Test creating a Python container."""
        result = await container_manager.create_container(
            task_id="test-python-1",
            project_id="test-project-1",
            language="python"
        )
        
        if not result["success"]:
            print(f"\n❌ Container creation failed: {result['message']}")
        
        assert result["success"] is True, f"Failed: {result['message']}"
        assert result["container_id"] is not None
        assert "test-python-1" in container_manager.active_containers
        
        # Cleanup
        await container_manager.destroy_container("test-python-1")
    
    @pytest.mark.asyncio
    async def test_create_node_container(self, container_manager):
        """Test creating a Node.js container."""
        result = await container_manager.create_container(
            task_id="test-node-1",
            project_id="test-project-1",
            language="node"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-node-1")
    
    @pytest.mark.asyncio
    async def test_create_java_container(self, container_manager):
        """Test creating a Java container."""
        result = await container_manager.create_container(
            task_id="test-java-1",
            project_id="test-project-1",
            language="java"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-java-1")
    
    @pytest.mark.asyncio
    async def test_create_go_container(self, container_manager):
        """Test creating a Go container."""
        result = await container_manager.create_container(
            task_id="test-go-1",
            project_id="test-project-1",
            language="go"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-go-1")
    
    @pytest.mark.asyncio
    async def test_create_ruby_container(self, container_manager):
        """Test creating a Ruby container."""
        result = await container_manager.create_container(
            task_id="test-ruby-1",
            project_id="test-project-1",
            language="ruby"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-ruby-1")
    
    @pytest.mark.asyncio
    async def test_create_php_container(self, container_manager):
        """Test creating a PHP container."""
        result = await container_manager.create_container(
            task_id="test-php-1",
            project_id="test-project-1",
            language="php"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-php-1")
    
    @pytest.mark.asyncio
    async def test_create_dotnet_container(self, container_manager):
        """Test creating a .NET container."""
        result = await container_manager.create_container(
            task_id="test-dotnet-1",
            project_id="test-project-1",
            language="dotnet"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-dotnet-1")
    
    @pytest.mark.asyncio
    async def test_create_powershell_container(self, container_manager):
        """Test creating a PowerShell container."""
        result = await container_manager.create_container(
            task_id="test-powershell-1",
            project_id="test-project-1",
            language="powershell"
        )
        
        assert result["success"] is True
        assert result["container_id"] is not None
        
        await container_manager.destroy_container("test-powershell-1")
    
    @pytest.mark.asyncio
    async def test_create_container_with_alias(self, container_manager):
        """Test creating container with language alias."""
        # Test nodejs alias
        result = await container_manager.create_container(
            task_id="test-nodejs-alias",
            project_id="test-project-1",
            language="nodejs"
        )
        
        assert result["success"] is True
        await container_manager.destroy_container("test-nodejs-alias")
        
        # Test javascript alias
        result = await container_manager.create_container(
            task_id="test-javascript-alias",
            project_id="test-project-1",
            language="javascript"
        )
        
        assert result["success"] is True
        await container_manager.destroy_container("test-javascript-alias")


class TestContainerDestruction:
    """Test container cleanup and destruction."""
    
    @pytest.mark.asyncio
    async def test_destroy_container(self, container_manager):
        """Test destroying a container."""
        # Create container
        create_result = await container_manager.create_container(
            task_id="test-destroy-1",
            project_id="test-project-1",
            language="python"
        )
        assert create_result["success"] is True
        
        # Destroy container
        destroy_result = await container_manager.destroy_container("test-destroy-1")
        assert destroy_result["success"] is True
        assert "test-destroy-1" not in container_manager.active_containers
    
    @pytest.mark.asyncio
    async def test_destroy_nonexistent_container(self, container_manager):
        """Test destroying a container that doesn't exist."""
        result = await container_manager.destroy_container("nonexistent-task")
        # Should succeed (idempotent)
        assert result["success"] is True
        assert "No container" in result["message"]
    
    @pytest.mark.asyncio
    async def test_create_destroy_cycle(self, container_manager):
        """Test multiple create/destroy cycles."""
        for i in range(3):
            task_id = f"test-cycle-{i}"
            
            # Create
            create_result = await container_manager.create_container(
                task_id=task_id,
                project_id="test-project-1",
                language="python"
            )
            assert create_result["success"] is True
            
            # Destroy
            destroy_result = await container_manager.destroy_container(task_id)
            assert destroy_result["success"] is True


class TestContainerExecution:
    """Test command execution in containers."""
    
    @pytest.mark.asyncio
    async def test_execute_simple_command(self, container_manager):
        """Test executing a simple command."""
        # Create container
        await container_manager.create_container(
            task_id="test-exec-1",
            project_id="test-project-1",
            language="python"
        )
        
        # Execute command
        result = await container_manager.exec_command(
            task_id="test-exec-1",
            command="echo 'Hello World'"
        )
        
        assert result.exit_code == 0
        assert result.success is True
        assert "Hello World" in result.stdout
        
        await container_manager.destroy_container("test-exec-1")
    
    @pytest.mark.asyncio
    async def test_execute_python_code(self, container_manager):
        """Test executing Python code."""
        await container_manager.create_container(
            task_id="test-python-exec",
            project_id="test-project-1",
            language="python"
        )
        
        result = await container_manager.exec_command(
            task_id="test-python-exec",
            command='python -c "print(2 + 2)"'
        )
        
        assert result.exit_code == 0
        assert "4" in result.stdout
        
        await container_manager.destroy_container("test-python-exec")
    
    @pytest.mark.asyncio
    async def test_execute_command_with_error(self, container_manager):
        """Test executing a command that fails."""
        await container_manager.create_container(
            task_id="test-error-exec",
            project_id="test-project-1",
            language="python"
        )
        
        result = await container_manager.exec_command(
            task_id="test-error-exec",
            command="python -c 'import nonexistent_module'"
        )
        
        assert result.exit_code != 0
        assert result.success is False
        assert len(result.stderr) > 0 or "Error" in result.stdout
        
        await container_manager.destroy_container("test-error-exec")


class TestVolumeMounting:
    """Test persistent volume mounting."""
    
    @pytest.mark.asyncio
    async def test_volume_persists_across_containers(self, container_manager):
        """Test that files persist when container is recreated."""
        project_id = "test-volume-project"
        
        # Create first container and write a file
        await container_manager.create_container(
            task_id="test-volume-1",
            project_id=project_id,
            language="python"
        )
        
        # Write a file using sh -c for proper shell redirection
        write_result = await container_manager.exec_command(
            task_id="test-volume-1",
            command='sh -c "echo test_content > /workspace/test_file.txt"'
        )
        assert write_result.exit_code == 0
        
        # Destroy container
        await container_manager.destroy_container("test-volume-1")
        
        # Create new container for same project
        await container_manager.create_container(
            task_id="test-volume-2",
            project_id=project_id,
            language="python"
        )
        
        # Read the file
        read_result = await container_manager.exec_command(
            task_id="test-volume-2",
            command="cat /workspace/test_file.txt"
        )
        
        assert read_result.exit_code == 0
        assert "test_content" in read_result.stdout
        
        # Cleanup - remove test file
        await container_manager.exec_command(
            task_id="test-volume-2",
            command="rm -f /workspace/test_file.txt"
        )
        await container_manager.destroy_container("test-volume-2")


class TestErrorHandling:
    """Test error handling in container operations."""
    
    @pytest.mark.asyncio
    async def test_unsupported_language(self, container_manager):
        """Test creating container with unsupported language."""
        result = await container_manager.create_container(
            task_id="test-invalid-lang",
            project_id="test-project-1",
            language="unsupported-language"
        )
        
        assert result["success"] is False
        assert "Unsupported language" in result["message"]
    
    @pytest.mark.asyncio
    async def test_exec_without_container(self, container_manager):
        """Test executing command without creating container first."""
        with pytest.raises(ValueError, match="No container found"):
            await container_manager.exec_command(
                task_id="nonexistent-task",
                command="echo test"
            )
    
    @pytest.mark.asyncio
    async def test_duplicate_container_creation(self, container_manager):
        """Test creating container with same task_id twice."""
        # Create first container
        result1 = await container_manager.create_container(
            task_id="test-duplicate",
            project_id="test-project-1",
            language="python"
        )
        assert result1["success"] is True
        
        # Try to create again with same task_id
        result2 = await container_manager.create_container(
            task_id="test-duplicate",
            project_id="test-project-1",
            language="python"
        )
        
        # Should succeed (idempotent) and return existing container
        assert result2["success"] is True
        assert "already exists" in result2["message"]
        
        await container_manager.destroy_container("test-duplicate")


class TestContainerInfo:
    """Test container information retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_container_info(self, container_manager):
        """Test getting container information."""
        await container_manager.create_container(
            task_id="test-info",
            project_id="test-project-1",
            language="python"
        )
        
        info = container_manager.get_container_info("test-info")
        
        assert info is not None
        assert "id" in info
        assert "name" in info
        assert "status" in info
        assert "labels" in info
        
        await container_manager.destroy_container("test-info")
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_container_info(self, container_manager):
        """Test getting info for nonexistent container."""
        info = container_manager.get_container_info("nonexistent")
        assert info is None
    
    @pytest.mark.asyncio
    async def test_active_container_count(self, container_manager):
        """Test getting active container count."""
        initial_count = container_manager.get_active_container_count()
        
        # Create containers
        await container_manager.create_container(
            task_id="test-count-1",
            project_id="test-project-1",
            language="python"
        )
        await container_manager.create_container(
            task_id="test-count-2",
            project_id="test-project-1",
            language="node"
        )
        
        assert container_manager.get_active_container_count() == initial_count + 2
        
        # Cleanup
        await container_manager.destroy_container("test-count-1")
        await container_manager.destroy_container("test-count-2")
        
        assert container_manager.get_active_container_count() == initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
