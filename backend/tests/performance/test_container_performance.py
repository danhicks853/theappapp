"""
Performance tests for Container Operations.

Tests container performance metrics:
- Container creation time (<2s target)
- First command execution time (<1s target)
- Total startup time (<3s target)
- Cleanup time
- Throughput tests

Requires Docker to be running.
"""
import pytest
import asyncio
import time
from statistics import mean, stdev
from backend.services.container_manager import get_container_manager

pytestmark = [pytest.mark.performance, pytest.mark.asyncio]


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


class TestContainerCreationPerformance:
    """Test container creation performance."""
    
    @pytest.mark.asyncio
    async def test_single_container_creation_time(self, container_manager):
        """Test single container creation is under 2s."""
        task_id = "perf-test-single"
        
        start_time = time.time()
        
        result = await container_manager.create_container(
            task_id=task_id,
            project_id="perf-project",
            language="python"
        )
        
        creation_time = time.time() - start_time
        
        assert result["success"] is True
        assert creation_time < 2.0, f"Container creation took {creation_time:.2f}s (target: <2s)"
        
        print(f"\n✓ Container creation time: {creation_time:.3f}s")
        
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_average_creation_time(self, container_manager):
        """Test average creation time over 10 containers."""
        times = []
        
        for i in range(10):
            task_id = f"perf-test-avg-{i}"
            
            start_time = time.time()
            result = await container_manager.create_container(
                task_id=task_id,
                project_id="perf-project",
                language="python"
            )
            creation_time = time.time() - start_time
            
            assert result["success"] is True
            times.append(creation_time)
            
            await container_manager.destroy_container(task_id)
            await asyncio.sleep(0.1)  # Brief pause between tests
        
        avg_time = mean(times)
        std_time = stdev(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 Creation time statistics (n=10):")
        print(f"   Average: {avg_time:.3f}s")
        print(f"   Std Dev: {std_time:.3f}s")
        print(f"   Min:     {min_time:.3f}s")
        print(f"   Max:     {max_time:.3f}s")
        
        assert avg_time < 2.0, f"Average creation time {avg_time:.2f}s exceeds 2s target"
        assert max_time < 3.0, f"Max creation time {max_time:.2f}s is too high"


class TestCommandExecutionPerformance:
    """Test command execution performance."""
    
    @pytest.mark.asyncio
    async def test_first_command_execution_time(self, container_manager):
        """Test first command execution is under 1s."""
        task_id = "perf-test-first-cmd"
        
        # Create container
        await container_manager.create_container(
            task_id=task_id,
            project_id="perf-project",
            language="python"
        )
        
        # Measure first command execution
        start_time = time.time()
        result = await container_manager.exec_command(
            task_id=task_id,
            command="echo 'test'"
        )
        exec_time = time.time() - start_time
        
        assert result.exit_code == 0
        assert exec_time < 1.0, f"First command took {exec_time:.2f}s (target: <1s)"
        
        print(f"\n✓ First command execution time: {exec_time:.3f}s")
        
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_subsequent_command_execution_time(self, container_manager):
        """Test subsequent commands are fast."""
        task_id = "perf-test-subsequent-cmd"
        
        await container_manager.create_container(
            task_id=task_id,
            project_id="perf-project",
            language="python"
        )
        
        # First command (warm up)
        await container_manager.exec_command(task_id=task_id, command="echo 'warmup'")
        
        # Measure subsequent commands
        times = []
        for i in range(5):
            start_time = time.time()
            result = await container_manager.exec_command(
                task_id=task_id,
                command=f"echo 'test {i}'"
            )
            exec_time = time.time() - start_time
            
            assert result.exit_code == 0
            times.append(exec_time)
        
        avg_time = mean(times)
        
        print(f"\n📊 Subsequent command stats (n=5):")
        print(f"   Average: {avg_time:.3f}s")
        print(f"   Min:     {min(times):.3f}s")
        print(f"   Max:     {max(times):.3f}s")
        
        assert avg_time < 0.5, f"Subsequent commands too slow: {avg_time:.2f}s"
        
        await container_manager.destroy_container(task_id)


class TestTotalStartupPerformance:
    """Test total startup time (create + first command)."""
    
    @pytest.mark.asyncio
    async def test_total_startup_time(self, container_manager):
        """Test total startup (create + execute) is under 3s."""
        task_id = "perf-test-startup"
        
        start_time = time.time()
        
        # Create container
        result = await container_manager.create_container(
            task_id=task_id,
            project_id="perf-project",
            language="python"
        )
        assert result["success"] is True
        
        # Execute first command
        exec_result = await container_manager.exec_command(
            task_id=task_id,
            command="python -c 'print(2+2)'"
        )
        assert exec_result.exit_code == 0
        
        total_time = time.time() - start_time
        
        assert total_time < 3.0, f"Total startup took {total_time:.2f}s (target: <3s)"
        
        print(f"\n✓ Total startup time: {total_time:.3f}s")
        
        await container_manager.destroy_container(task_id)
    
    @pytest.mark.asyncio
    async def test_total_startup_multiple_languages(self, container_manager):
        """Test startup time for all supported languages."""
        languages = ["python", "node", "java", "go", "ruby", "php"]
        results = {}
        
        for lang in languages:
            task_id = f"perf-test-{lang}"
            
            start_time = time.time()
            
            # Create and execute
            create_result = await container_manager.create_container(
                task_id=task_id,
                project_id="perf-project",
                language=lang
            )
            
            if create_result["success"]:
                exec_result = await container_manager.exec_command(
                    task_id=task_id,
                    command="echo 'test'"
                )
                
                total_time = time.time() - start_time
                results[lang] = total_time
                
                await container_manager.destroy_container(task_id)
            else:
                results[lang] = None
        
        print(f"\n📊 Startup time by language:")
        for lang, time_val in results.items():
            if time_val:
                status = "✓" if time_val < 3.0 else "⚠"
                print(f"   {status} {lang:12s}: {time_val:.3f}s")
        
        # All successful languages should be under 3s
        for lang, time_val in results.items():
            if time_val is not None:
                assert time_val < 3.0, f"{lang} startup took {time_val:.2f}s (target: <3s)"


class TestCleanupPerformance:
    """Test container cleanup performance."""
    
    @pytest.mark.asyncio
    async def test_container_cleanup_time(self, container_manager):
        """Test container destruction is fast."""
        task_id = "perf-test-cleanup"
        
        # Create container
        await container_manager.create_container(
            task_id=task_id,
            project_id="perf-project",
            language="python"
        )
        
        # Measure cleanup time
        start_time = time.time()
        result = await container_manager.destroy_container(task_id)
        cleanup_time = time.time() - start_time
        
        assert result["success"] is True
        assert cleanup_time < 6.0, f"Cleanup took {cleanup_time:.2f}s (should be <6s)"
        
        print(f"\n✓ Container cleanup time: {cleanup_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_batch_cleanup_time(self, container_manager):
        """Test cleaning up multiple containers."""
        num_containers = 5
        
        # Create multiple containers
        for i in range(num_containers):
            await container_manager.create_container(
                task_id=f"perf-cleanup-{i}",
                project_id="perf-project",
                language="python"
            )
        
        # Measure batch cleanup
        start_time = time.time()
        for i in range(num_containers):
            await container_manager.destroy_container(f"perf-cleanup-{i}")
        cleanup_time = time.time() - start_time
        
        avg_cleanup = cleanup_time / num_containers
        
        print(f"\n📊 Batch cleanup (n={num_containers}):")
        print(f"   Total time: {cleanup_time:.3f}s")
        print(f"   Per container: {avg_cleanup:.3f}s")
        
        assert avg_cleanup < 6.0, f"Average cleanup too slow: {avg_cleanup:.2f}s"


class TestThroughputPerformance:
    """Test container throughput and concurrency."""
    
    @pytest.mark.asyncio
    async def test_sequential_container_creation(self, container_manager):
        """Test creating multiple containers sequentially."""
        num_containers = 5
        
        start_time = time.time()
        
        for i in range(num_containers):
            task_id = f"perf-seq-{i}"
            result = await container_manager.create_container(
                task_id=task_id,
                project_id="perf-project",
                language="python"
            )
            assert result["success"] is True
        
        total_time = time.time() - start_time
        throughput = num_containers / total_time
        
        print(f"\n📊 Sequential creation (n={num_containers}):")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Throughput: {throughput:.2f} containers/s")
        
        # Cleanup
        for i in range(num_containers):
            await container_manager.destroy_container(f"perf-seq-{i}")
    
    @pytest.mark.asyncio
    async def test_concurrent_container_creation(self, container_manager):
        """Test creating multiple containers concurrently."""
        num_containers = 5
        
        async def create_and_cleanup(idx):
            task_id = f"perf-concurrent-{idx}"
            result = await container_manager.create_container(
                task_id=task_id,
                project_id="perf-project",
                language="python"
            )
            assert result["success"] is True
            await container_manager.destroy_container(task_id)
        
        start_time = time.time()
        
        # Create all concurrently
        await asyncio.gather(*[create_and_cleanup(i) for i in range(num_containers)])
        
        total_time = time.time() - start_time
        
        print(f"\n📊 Concurrent creation (n={num_containers}):")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Speedup vs sequential: ~{num_containers * 2 / total_time:.1f}x")


class TestMemoryAndResourceUsage:
    """Test resource usage patterns."""
    
    @pytest.mark.asyncio
    async def test_active_container_tracking(self, container_manager):
        """Test container tracking accuracy."""
        initial_count = container_manager.get_active_container_count()
        
        # Create containers
        for i in range(3):
            await container_manager.create_container(
                task_id=f"track-test-{i}",
                project_id="perf-project",
                language="python"
            )
        
        assert container_manager.get_active_container_count() == initial_count + 3
        
        # Destroy containers
        for i in range(3):
            await container_manager.destroy_container(f"track-test-{i}")
        
        assert container_manager.get_active_container_count() == initial_count
        
        print(f"\n✓ Container tracking accurate")


class TestPerformanceRegression:
    """Performance regression tests."""
    
    @pytest.mark.asyncio
    async def test_no_performance_degradation(self, container_manager):
        """Test that repeated operations don't degrade."""
        times_first_batch = []
        times_second_batch = []
        
        # First batch
        for i in range(5):
            task_id = f"regression-1-{i}"
            start = time.time()
            await container_manager.create_container(
                task_id=task_id,
                project_id="perf-project",
                language="python"
            )
            times_first_batch.append(time.time() - start)
            await container_manager.destroy_container(task_id)
        
        await asyncio.sleep(1)  # Brief pause
        
        # Second batch
        for i in range(5):
            task_id = f"regression-2-{i}"
            start = time.time()
            await container_manager.create_container(
                task_id=task_id,
                project_id="perf-project",
                language="python"
            )
            times_second_batch.append(time.time() - start)
            await container_manager.destroy_container(task_id)
        
        avg_first = mean(times_first_batch)
        avg_second = mean(times_second_batch)
        
        print(f"\n📊 Performance regression check:")
        print(f"   First batch avg:  {avg_first:.3f}s")
        print(f"   Second batch avg: {avg_second:.3f}s")
        print(f"   Difference:       {abs(avg_second - avg_first):.3f}s")
        
        # Second batch should not be significantly slower (allow 20% variance)
        assert avg_second < avg_first * 1.2, "Performance degradation detected"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
