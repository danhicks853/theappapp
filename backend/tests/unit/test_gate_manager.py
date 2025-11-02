"""
Gate Manager Unit Tests

Tests gate creation, approval, denial, and querying.
"""
import pytest
from unittest.mock import Mock
from backend.services.gate_manager import GateManager


@pytest.mark.unit
class TestGateManager:
    """Test GateManager service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from unittest.mock import MagicMock
        
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.gate_manager = GateManager(self.mock_engine)
    
    def test_create_gate(self):
        """Test gate creation."""
        gate_id = self.gate_manager.create_gate(
            project_id="proj-123",
            reason="Quality check needed",
            context={"test": "data"},
            agent_id="agent-456",
            gate_type="quality_check"
        )
        
        assert gate_id is not None
        assert self.mock_conn.execute.called
        assert self.mock_conn.commit.called
    
    def test_create_gate_with_minimal_params(self):
        """Test gate creation with minimal parameters."""
        gate_id = self.gate_manager.create_gate(
            project_id="proj-123",
            reason="Test gate"
        )
        
        assert gate_id is not None
        assert self.mock_conn.execute.called
    
    def test_approve_gate(self):
        """Test gate approval."""
        gate_id = "gate-123"
        
        result = self.gate_manager.approve_gate(
            gate_id=gate_id,
            approver="user-1",
            notes="Looks good"
        )
        
        assert result is True
        assert self.mock_conn.execute.called
        assert self.mock_conn.commit.called
    
    def test_deny_gate(self):
        """Test gate denial."""
        gate_id = "gate-123"
        
        result = self.gate_manager.deny_gate(
            gate_id=gate_id,
            denier="user-1",
            reason="Needs more work"
        )
        
        assert result is True
        assert self.mock_conn.execute.called
        assert self.mock_conn.commit.called
    
    def test_get_pending_gates(self):
        """Test querying pending gates."""
        # Mock database response
        self.mock_conn.execute.return_value.fetchall.return_value = []
        
        gates = self.gate_manager.get_pending_gates(project_id="proj-123")
        
        assert isinstance(gates, list)
        assert self.mock_conn.execute.called
    
    def test_get_gate_by_id(self):
        """Test getting specific gate."""
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "gate-123", "proj-123", "Test reason", "{}", "pending",
            None, None, None, "agent-456", "quality_check"
        )
        
        gate = self.gate_manager.get_gate("gate-123")
        
        assert gate is not None
        assert gate["id"] == "gate-123"
        assert gate["status"] == "pending"
    
    def test_create_gate_error_handling(self):
        """Test gate creation with database error."""
        self.mock_conn.execute.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            self.gate_manager.create_gate(
                project_id="proj-123",
                reason="Test"
            )


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
