"""
Timeout Monitor Unit Tests

Tests timeout detection, gate creation, and monitoring lifecycle.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from backend.services.timeout_monitor import TimeoutMonitor


@pytest.mark.unit
class TestTimeoutMonitorInitialization:
    """Test timeout monitor initialization."""
    
    def test_timeout_monitor_creation(self):
        """Test creating timeout monitor."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        assert monitor.gate_manager == mock_gate_manager
        assert monitor.get_active_count() == 0
    
    def test_timeout_monitor_without_gate_manager(self):
        """Test monitor works without gate manager (no auto-gates)."""
        monitor = TimeoutMonitor(None)
        
        assert monitor.gate_manager is None
        assert monitor.get_active_count() == 0


@pytest.mark.unit
class TestTaskMonitoring:
    """Test task monitoring operations."""
    
    @pytest.mark.asyncio
    async def test_monitor_task_starts_tracking(self):
        """Test that monitoring a task starts tracking it."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=60
        )
        
        assert monitor.get_active_count() == 1
        assert monitor.is_monitoring("task-1")
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_monitor_multiple_tasks(self):
        """Test monitoring multiple tasks simultaneously."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        await monitor.start()
        
        for i in range(5):
            await monitor.monitor_task(
                task_id=f"task-{i}",
                agent_id=f"agent-{i}",
                agent_type="backend_developer",
                timeout_seconds=60
            )
        
        assert monitor.get_active_count() == 5
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_task(self):
        """Test stopping monitoring for a task."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=60
        )
        
        monitor.stop_monitoring("task-1")
        
        assert monitor.get_active_count() == 0
        assert not monitor.is_monitoring("task-1")
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_monitor_task_with_zero_timeout_raises(self):
        """Test that zero timeout raises error."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        await monitor.start()
        
        with pytest.raises(ValueError):
            await monitor.monitor_task(
                task_id="task-1",
                agent_id="agent-1",
                agent_type="backend_developer",
                timeout_seconds=0
            )
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_monitor_task_with_negative_timeout_raises(self):
        """Test that negative timeout raises error."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        await monitor.start()
        
        with pytest.raises(ValueError):
            await monitor.monitor_task(
                task_id="task-1",
                agent_id="agent-1",
                agent_type="backend_developer",
                timeout_seconds=-10
            )
        
        await monitor.stop()


@pytest.mark.unit
class TestTimeoutDetection:
    """Test timeout detection and gate creation."""
    
    @pytest.mark.asyncio
    async def test_timeout_creates_gate(self):
        """Test that timeout triggers gate creation."""
        mock_gate_manager = Mock()
        mock_gate_manager.create_gate = AsyncMock(return_value="gate-123")
        
        monitor = TimeoutMonitor(mock_gate_manager)
        await monitor.start()
        
        # Monitor with very short timeout
        await monitor.monitor_task(
            task_id="task-timeout",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=1  # 1 second
        )
        
        # Wait for timeout
        await asyncio.sleep(2)
        
        # Should have created gate
        assert mock_gate_manager.create_gate.called
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_no_gate_without_gate_manager(self):
        """Test that timeout without gate manager doesn't crash."""
        monitor = TimeoutMonitor(None)
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=1
        )
        
        # Wait for timeout
        await asyncio.sleep(2)
        
        # Should not crash, just log
        assert True
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_before_timeout_prevents_gate(self):
        """Test that stopping monitoring prevents gate creation."""
        mock_gate_manager = Mock()
        mock_gate_manager.create_gate = AsyncMock(return_value="gate-123")
        
        monitor = TimeoutMonitor(mock_gate_manager)
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=5
        )
        
        # Stop before timeout
        monitor.stop_monitoring("task-1")
        
        await asyncio.sleep(6)
        
        # Should NOT have created gate
        assert not mock_gate_manager.create_gate.called
        
        await monitor.stop()


@pytest.mark.unit
class TestMonitorLifecycle:
    """Test monitor start/stop lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_monitor(self):
        """Test starting the monitor."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        
        assert monitor.is_running()
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_stop_monitor(self):
        """Test stopping the monitor."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        await monitor.stop()
        
        assert not monitor.is_running()
    
    @pytest.mark.asyncio
    async def test_stop_monitor_clears_all_tasks(self):
        """Test that stopping monitor clears all monitored tasks."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=60
        )
        await monitor.monitor_task(
            task_id="task-2",
            agent_id="agent-2",
            agent_type="backend_developer",
            timeout_seconds=60
        )
        
        await monitor.stop()
        
        assert monitor.get_active_count() == 0
    
    @pytest.mark.asyncio
    async def test_restart_monitor(self):
        """Test restarting the monitor."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        await monitor.stop()
        await monitor.start()
        
        assert monitor.is_running()
        
        await monitor.stop()


@pytest.mark.unit
class TestMonitorStatistics:
    """Test monitor statistics and reporting."""
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting monitor statistics."""
        mock_gate_manager = Mock()
        monitor = TimeoutMonitor(mock_gate_manager)
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=60
        )
        
        stats = monitor.get_stats()
        
        assert stats["active_count"] == 1
        assert stats["total_monitored"] >= 1
        assert "running" in stats
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_get_monitored_tasks(self):
        """Test getting list of monitored tasks."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=60
        )
        await monitor.monitor_task(
            task_id="task-2",
            agent_id="agent-2",
            agent_type="frontend_developer",
            timeout_seconds=120
        )
        
        tasks = monitor.get_monitored_tasks()
        
        assert len(tasks) == 2
        assert "task-1" in [t["task_id"] for t in tasks]
        assert "task-2" in [t["task_id"] for t in tasks]
        
        await monitor.stop()


@pytest.mark.unit
class TestAgentTypeTimeouts:
    """Test different timeouts for different agent types."""
    
    @pytest.mark.asyncio
    async def test_backend_developer_timeout(self):
        """Test backend developer timeout (default 30 min)."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer"
            # Uses default timeout
        )
        
        tasks = monitor.get_monitored_tasks()
        assert tasks[0]["timeout_seconds"] == 1800  # 30 min
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_custom_timeout_overrides_default(self):
        """Test custom timeout overrides agent type default."""
        monitor = TimeoutMonitor(Mock())
        
        await monitor.start()
        
        await monitor.monitor_task(
            task_id="task-1",
            agent_id="agent-1",
            agent_type="backend_developer",
            timeout_seconds=300  # Custom 5 min
        )
        
        tasks = monitor.get_monitored_tasks()
        assert tasks[0]["timeout_seconds"] == 300
        
        await monitor.stop()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
