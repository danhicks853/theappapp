"""
Container Manager Service - Docker-based code execution sandbox.

Manages Docker containers for safe code execution by AI agents.
- One container per task (task-scoped lifetime)
- Supports 8 languages: Python, Node.js, Java, Go, Ruby, PHP, .NET, PowerShell
- Persistent volume mounting for project files
- Automatic cleanup and resource management
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import docker
from docker.models.containers import Container
from docker.errors import DockerException, NotFound, APIError

logger = logging.getLogger(__name__)


# Language to Docker image mapping
# Custom images with Python included for TAS file operations
# Build with: cd docker && ./build-all.sh
LANGUAGE_IMAGES = {
    "python": "theappapp-python:latest",
    "node": "theappapp-node:latest",
    "javascript": "theappapp-node:latest",
    "typescript": "theappapp-node:latest",
    "java": "theappapp-java:latest",
    "go": "theappapp-go:latest",
    "golang": "theappapp-go:latest",
    "ruby": "theappapp-ruby:latest",
    "php": "theappapp-php:latest",
    "dotnet": "theappapp-dotnet:latest",
    "csharp": "theappapp-dotnet:latest",
    "powershell": "theappapp-powershell:latest",
}


class ContainerExecutionResult:
    """Result of a container command execution."""
    
    def __init__(self, exit_code: int, stdout: str, stderr: str):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.success = exit_code == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "success": self.success
        }


class ContainerManager:
    """
    Manages Docker containers for code execution.
    
    Features:
    - Task-scoped container lifetime (one per task)
    - Multi-language support (8 languages)
    - Persistent volume mounting per project
    - Automatic cleanup on task completion
    - Image pre-pulling during startup
    """
    
    def __init__(self):
        """Initialize the ContainerManager."""
        self.active_containers: Dict[str, Container] = {}  # task_id -> Container
        self._initialized = False
        
        # Initialize Docker client immediately
        try:
            self.client = docker.from_env()
            self.client.ping()  # Test connection
            logger.info("ContainerManager initialized - Docker client connected")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            logger.warning("ContainerManager will operate in degraded mode")
            self.client = None
    
    async def startup(self):
        """
        Startup initialization - pre-pull all language images.
        
        Called during system startup before accepting requests.
        Blocks until all images are pulled or fails gracefully.
        """
        logger.info("ContainerManager startup: Initializing Docker client")
        
        try:
            # Initialize Docker client
            self.client = docker.from_env()
            
            # Test Docker connection
            self.client.ping()
            logger.info("Docker connection successful")
            
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            logger.warning("ContainerManager will operate in degraded mode")
            return
        
        # Pre-pull all language images
        logger.info(f"Pre-pulling {len(LANGUAGE_IMAGES)} language images...")
        
        unique_images = set(LANGUAGE_IMAGES.values())
        for image_name in unique_images:
            try:
                logger.info(f"Pulling image: {image_name}")
                self.client.images.pull(image_name)
                logger.info(f"✓ Successfully pulled: {image_name}")
            except DockerException as e:
                logger.warning(f"✗ Failed to pull {image_name}: {e}")
                logger.warning(f"Container creation may fail for this image")
        
        self._initialized = True
        logger.info("ContainerManager startup complete")
    
    def _get_image_for_language(self, language: str) -> str:
        """
        Get Docker image name for a language.
        
        Args:
            language: Language name (e.g., "python", "node", "java")
        
        Returns:
            Docker image name
        
        Raises:
            ValueError: If language is not supported
        """
        language_lower = language.lower()
        
        if language_lower not in LANGUAGE_IMAGES:
            supported = ", ".join(sorted(set(LANGUAGE_IMAGES.keys())))
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported languages: {supported}"
            )
        
        return LANGUAGE_IMAGES[language_lower]
    
    def _get_volume_name(self, project_id: str) -> str:
        """
        Get volume name for a project.
        
        Args:
            project_id: Project ID
        
        Returns:
            Docker volume name
        """
        return f"theappapp-project-{project_id}"
    
    def _get_container_name(self, project_id: str, task_id: str) -> str:
        """
        Get container name for a task.
        
        Args:
            project_id: Project ID
            task_id: Task ID
        
        Returns:
            Container name
        """
        return f"theappapp-{project_id}-{task_id}"
    
    async def create_container(
        self,
        task_id: str,
        project_id: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Create a new container for a task.
        
        Args:
            task_id: Unique task identifier
            project_id: Project identifier
            language: Programming language (python, node, java, etc.)
        
        Returns:
            dict: {"success": bool, "container_id": str, "message": str}
        
        Raises:
            ValueError: If language is not supported
            DockerException: If Docker operation fails
        """
        # Auto-initialize if not done yet
        if not self.client:
            await self.startup()
        
        if not self.client:
            return {
                "success": False,
                "message": "Docker client not initialized - Docker may not be running",
                "container_id": None
            }
        
        # Check if container already exists for this task
        if task_id in self.active_containers:
            logger.warning(f"Container already exists for task {task_id}")
            return {
                "success": True,
                "container_id": self.active_containers[task_id].id,
                "message": "Container already exists"
            }
        
        try:
            # Get image name
            image_name = self._get_image_for_language(language)
            
            # Get volume and container names
            volume_name = self._get_volume_name(project_id)
            container_name = self._get_container_name(project_id, task_id)
            
            logger.info(f"Creating container for task {task_id} (language: {language})")
            
            # Create container
            # Note: Container runs in detached mode, stays alive until explicitly stopped
            container = self.client.containers.run(
                image=image_name,
                name=container_name,
                detach=True,
                remove=False,  # Don't auto-remove, we manage cleanup
                working_dir="/workspace",
                volumes={
                    volume_name: {
                        "bind": "/workspace",
                        "mode": "rw"
                    }
                },
                network_mode="bridge",  # Network isolation
                labels={
                    "theappapp-managed": "true",
                    "project_id": project_id,
                    "task_id": task_id,
                    "language": language,
                    "created_at": datetime.utcnow().isoformat()
                },
                # Keep container alive
                command="tail -f /dev/null",
                # Security: no privileged mode
                privileged=False,
                # Optional: Add resource limits if needed
                # mem_limit="512m",
                # cpu_quota=50000,  # 50% of one CPU
            )
            
            # Track active container
            self.active_containers[task_id] = container
            
            logger.info(
                f"✓ Container created: {container.id[:12]} "
                f"(task: {task_id}, language: {language})"
            )
            
            return {
                "success": True,
                "container_id": container.id,
                "message": f"Container created successfully for {language}"
            }
        
        except ValueError as e:
            logger.error(f"Invalid language for task {task_id}: {e}")
            return {
                "success": False,
                "message": str(e),
                "container_id": None
            }
        
        except DockerException as e:
            logger.error(f"Failed to create container for task {task_id}: {e}")
            return {
                "success": False,
                "message": f"Docker error: {str(e)}",
                "container_id": None
            }
    
    async def destroy_container(self, task_id: str) -> Dict[str, Any]:
        """
        Destroy container for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            dict: {"success": bool, "message": str}
        """
        if not self.client:
            return {
                "success": False,
                "message": "Docker client not initialized"
            }
        
        # Check if container exists
        if task_id not in self.active_containers:
            logger.warning(f"No container found for task {task_id}")
            return {
                "success": True,
                "message": "No container to destroy"
            }
        
        container = self.active_containers[task_id]
        
        try:
            logger.info(f"Destroying container for task {task_id}")
            
            # Stop container (5 second timeout)
            container.stop(timeout=5)
            
            # Remove container
            container.remove(force=True)
            
            # Remove from tracking
            del self.active_containers[task_id]
            
            logger.info(f"✓ Container destroyed for task {task_id}")
            
            return {
                "success": True,
                "message": "Container destroyed successfully"
            }
        
        except DockerException as e:
            logger.error(f"Failed to destroy container for task {task_id}: {e}")
            
            # Still remove from tracking to avoid leaks
            if task_id in self.active_containers:
                del self.active_containers[task_id]
            
            return {
                "success": False,
                "message": f"Docker error: {str(e)}"
            }
    
    async def exec_command(
        self,
        task_id: str,
        command: str
    ) -> ContainerExecutionResult:
        """
        Execute command in a container.
        
        Args:
            task_id: Task identifier
            command: Command to execute (string or list)
        
        Returns:
            ContainerExecutionResult with exit_code, stdout, stderr
        
        Raises:
            ValueError: If container doesn't exist for task
            DockerException: If execution fails
        """
        if not self.client:
            return ContainerExecutionResult(
                exit_code=1,
                stdout="",
                stderr="Docker client not initialized"
            )
        
        # Check if container exists
        if task_id not in self.active_containers:
            raise ValueError(f"No container found for task {task_id}")
        
        container = self.active_containers[task_id]
        
        try:
            logger.info(f"Executing command in task {task_id}: {command[:100]}")
            
            # Execute command
            result = container.exec_run(
                cmd=command,
                workdir="/workspace",
                demux=True,  # Separate stdout and stderr
                tty=False
            )
            
            exit_code = result.exit_code
            stdout_bytes, stderr_bytes = result.output
            
            # Decode output
            stdout = stdout_bytes.decode("utf-8") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8") if stderr_bytes else ""
            
            logger.info(
                f"Command completed with exit code {exit_code} "
                f"(stdout: {len(stdout)} bytes, stderr: {len(stderr)} bytes)"
            )
            
            return ContainerExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr
            )
        
        except DockerException as e:
            logger.error(f"Failed to execute command in task {task_id}: {e}")
            return ContainerExecutionResult(
                exit_code=1,
                stdout="",
                stderr=f"Docker execution error: {str(e)}"
            )
    
    async def cleanup_orphaned_containers(self) -> Dict[str, Any]:
        """
        Cleanup orphaned containers (not in active tracking).
        
        Called by hourly cleanup job.
        
        Returns:
            dict: {"cleaned": int, "errors": List[str]}
        """
        if not self.client:
            return {"cleaned": 0, "errors": ["Docker client not initialized"]}
        
        cleaned = 0
        errors = []
        
        try:
            # Find all containers with theappapp-managed label
            containers = self.client.containers.list(
                all=True,
                filters={"label": "theappapp-managed=true"}
            )
            
            logger.info(f"Found {len(containers)} managed containers")
            
            for container in containers:
                # Get task_id from labels
                task_id = container.labels.get("task_id")
                
                if not task_id:
                    continue
                
                # Check if in active tracking
                if task_id not in self.active_containers:
                    logger.warning(f"Found orphaned container: {container.id[:12]} (task: {task_id})")
                    
                    try:
                        container.stop(timeout=5)
                        container.remove(force=True)
                        cleaned += 1
                        logger.info(f"✓ Cleaned orphaned container: {container.id[:12]}")
                    except DockerException as e:
                        error_msg = f"Failed to clean {container.id[:12]}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
            
            logger.info(f"Cleanup complete: {cleaned} containers cleaned, {len(errors)} errors")
            
            return {
                "cleaned": cleaned,
                "errors": errors
            }
        
        except DockerException as e:
            error_msg = f"Cleanup failed: {e}"
            logger.error(error_msg)
            return {
                "cleaned": 0,
                "errors": [error_msg]
            }
    
    def get_active_container_count(self) -> int:
        """Get number of active containers."""
        return len(self.active_containers)
    
    def get_container_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a container.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Container info dict or None if not found
        """
        if task_id not in self.active_containers:
            return None
        
        container = self.active_containers[task_id]
        
        try:
            container.reload()  # Refresh container state
            
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "labels": container.labels,
                "created": container.attrs.get("Created")
            }
        except DockerException as e:
            logger.error(f"Failed to get container info for task {task_id}: {e}")
            return None


# Singleton instance
_container_manager: Optional[ContainerManager] = None


def get_container_manager() -> ContainerManager:
    """Get singleton ContainerManager instance."""
    global _container_manager
    
    if _container_manager is None:
        _container_manager = ContainerManager()
    
    return _container_manager
