"""
Prompt Versioning Unit Tests

Tests semantic versioning, A/B testing, and version management.
"""
import pytest
from unittest.mock import Mock, MagicMock
from backend.services.prompt_management_service import PromptManagementService


@pytest.mark.unit
class TestPromptVersioning:
    """Test prompt version management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.service = PromptManagementService(self.mock_engine)
    
    def test_create_version_with_semantic_versioning(self):
        """Test creating version with MAJOR.MINOR.PATCH format."""
        version_id = self.service.create_version(
            agent_type="backend_developer",
            content="Test prompt content",
            version="1.0.0"
        )
        
        assert version_id is not None
        assert self.mock_conn.execute.called
    
    def test_create_version_increments_patch(self):
        """Test creating version increments patch number."""
        # Mock existing version
        self.mock_conn.execute.return_value.fetchone.return_value = ("1.0.0",)
        
        new_version = self.service.increment_version(
            agent_type="backend_developer",
            change_type="patch"
        )
        
        assert new_version == "1.0.1"
    
    def test_create_version_increments_minor(self):
        """Test creating version increments minor number."""
        self.mock_conn.execute.return_value.fetchone.return_value = ("1.0.5",)
        
        new_version = self.service.increment_version(
            agent_type="backend_developer",
            change_type="minor"
        )
        
        assert new_version == "1.1.0"
    
    def test_create_version_increments_major(self):
        """Test creating version increments major number."""
        self.mock_conn.execute.return_value.fetchone.return_value = ("1.2.3",)
        
        new_version = self.service.increment_version(
            agent_type="backend_developer",
            change_type="major"
        )
        
        assert new_version == "2.0.0"
    
    def test_invalid_version_format_raises_error(self):
        """Test invalid version format raises ValueError."""
        with pytest.raises(ValueError):
            self.service.create_version(
                agent_type="backend_developer",
                content="Test",
                version="1.0"  # Invalid: missing patch
            )
    
    def test_get_latest_version(self):
        """Test getting latest version for agent type."""
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "version-123", "2.1.0", "Test content"
        )
        
        version = self.service.get_latest_version("backend_developer")
        
        assert version is not None
        assert version["version"] == "2.1.0"
    
    def test_get_version_history(self):
        """Test getting version history."""
        self.mock_conn.execute.return_value.fetchall.return_value = [
            ("v1", "1.0.0", "Initial"),
            ("v2", "1.1.0", "Update"),
            ("v3", "2.0.0", "Major")
        ]
        
        history = self.service.get_version_history("backend_developer")
        
        assert len(history) == 3
        assert history[0]["version"] == "1.0.0"


@pytest.mark.unit
class TestVersionComparison:
    """Test version comparison logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.service = PromptManagementService(self.mock_engine)
    
    def test_compare_versions_equal(self):
        """Test comparing equal versions."""
        result = self.service.compare_versions("1.0.0", "1.0.0")
        
        assert result == 0
    
    def test_compare_versions_greater(self):
        """Test comparing greater version."""
        result = self.service.compare_versions("2.0.0", "1.0.0")
        
        assert result > 0
    
    def test_compare_versions_less(self):
        """Test comparing lesser version."""
        result = self.service.compare_versions("1.0.0", "2.0.0")
        
        assert result < 0
    
    def test_compare_versions_minor_difference(self):
        """Test comparing versions with minor difference."""
        result = self.service.compare_versions("1.2.0", "1.1.0")
        
        assert result > 0
    
    def test_compare_versions_patch_difference(self):
        """Test comparing versions with patch difference."""
        result = self.service.compare_versions("1.0.1", "1.0.0")
        
        assert result > 0


@pytest.mark.unit
class TestABTesting:
    """Test A/B testing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.service = PromptManagementService(self.mock_engine)
    
    def test_create_ab_test(self):
        """Test creating A/B test."""
        test_id = self.service.create_ab_test(
            name="Test A vs B",
            agent_type="backend_developer",
            control_version="1.0.0",
            variant_version="1.1.0",
            traffic_split=0.5
        )
        
        assert test_id is not None
        assert self.mock_conn.execute.called
    
    def test_ab_test_traffic_split_validation(self):
        """Test traffic split must be between 0 and 1."""
        with pytest.raises(ValueError):
            self.service.create_ab_test(
                name="Test",
                agent_type="backend_developer",
                control_version="1.0.0",
                variant_version="1.1.0",
                traffic_split=1.5  # Invalid
            )
    
    def test_ab_test_negative_traffic_split_raises(self):
        """Test negative traffic split raises error."""
        with pytest.raises(ValueError):
            self.service.create_ab_test(
                name="Test",
                agent_type="backend_developer",
                control_version="1.0.0",
                variant_version="1.1.0",
                traffic_split=-0.1
            )
    
    def test_get_active_ab_tests(self):
        """Test getting active A/B tests."""
        self.mock_conn.execute.return_value.fetchall.return_value = [
            ("test-1", "Test A vs B", "1.0.0", "1.1.0", 0.5, "active")
        ]
        
        tests = self.service.get_active_ab_tests("backend_developer")
        
        assert len(tests) == 1
        assert tests[0]["traffic_split"] == 0.5
    
    def test_stop_ab_test(self):
        """Test stopping an A/B test."""
        result = self.service.stop_ab_test("test-123")
        
        assert self.mock_conn.execute.called
    
    def test_get_ab_test_results(self):
        """Test getting A/B test results."""
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "test-1", "Test", 100, 95, 0.85, 0.82
        )
        
        results = self.service.get_ab_test_results("test-1")
        
        assert results is not None
        assert "control_count" in results
        assert "variant_count" in results


@pytest.mark.unit
class TestVariantSelection:
    """Test variant selection for A/B tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.service = PromptManagementService(self.mock_engine)
    
    def test_select_variant_returns_control_or_variant(self):
        """Test variant selection returns either control or variant."""
        # Mock active AB test
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "test-1", "1.0.0", "1.1.0", 0.5
        )
        
        variant = self.service.select_variant("backend_developer")
        
        assert variant in ["1.0.0", "1.1.0"]
    
    def test_select_variant_respects_traffic_split(self):
        """Test variant selection respects traffic split."""
        # Mock AB test with 100% control
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "test-1", "1.0.0", "1.1.0", 0.0  # 0% variant traffic
        )
        
        # Should always return control
        for _ in range(10):
            variant = self.service.select_variant("backend_developer")
            assert variant == "1.0.0"
    
    def test_select_variant_no_active_test_returns_latest(self):
        """Test variant selection with no active test returns latest."""
        # Mock no active AB test
        self.mock_conn.execute.return_value.fetchone.return_value = None
        
        # Mock latest version
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "v-1", "2.0.0", "Latest"
        )
        
        variant = self.service.select_variant("backend_developer")
        
        # Should return latest version when no AB test
        assert variant is not None


@pytest.mark.unit
class TestVersionRollback:
    """Test version rollback functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.service = PromptManagementService(self.mock_engine)
    
    def test_rollback_to_previous_version(self):
        """Test rolling back to previous version."""
        result = self.service.rollback_to_version(
            agent_type="backend_developer",
            version="1.0.0"
        )
        
        assert result is True
        assert self.mock_conn.execute.called
    
    def test_rollback_to_nonexistent_version_fails(self):
        """Test rollback to nonexistent version fails."""
        self.mock_conn.execute.return_value.fetchone.return_value = None
        
        result = self.service.rollback_to_version(
            agent_type="backend_developer",
            version="99.99.99"
        )
        
        assert result is False
    
    def test_rollback_creates_new_version_entry(self):
        """Test rollback creates new version entry (not just updates)."""
        # This ensures rollback is traceable in history
        self.service.rollback_to_version(
            agent_type="backend_developer",
            version="1.0.0"
        )
        
        # Should insert new version entry
        assert self.mock_conn.execute.called


@pytest.mark.unit
class TestVersionMetadata:
    """Test version metadata management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.service = PromptManagementService(self.mock_engine)
    
    def test_add_version_metadata(self):
        """Test adding metadata to version."""
        self.service.update_version_metadata(
            version_id="v-123",
            metadata={
                "author": "test_user",
                "description": "Fixed bug",
                "tags": ["bugfix", "performance"]
            }
        )
        
        assert self.mock_conn.execute.called
    
    def test_get_version_with_metadata(self):
        """Test getting version includes metadata."""
        self.mock_conn.execute.return_value.fetchone.return_value = (
            "v-1", "1.0.0", "Content", '{"author": "test"}'
        )
        
        version = self.service.get_version("v-1")
        
        assert version["metadata"]["author"] == "test"


@pytest.mark.unit
class TestPromptDiff:
    """Test prompt diff functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_engine.connect.return_value.__exit__.return_value = None
        
        self.service = PromptManagementService(self.mock_engine)
    
    def test_get_diff_between_versions(self):
        """Test getting diff between two versions."""
        # Mock version contents
        self.mock_conn.execute.return_value.fetchall.return_value = [
            ("1.0.0", "Original content"),
            ("1.1.0", "Updated content")
        ]
        
        diff = self.service.get_version_diff(
            agent_type="backend_developer",
            version_a="1.0.0",
            version_b="1.1.0"
        )
        
        assert diff is not None
        assert "additions" in diff or "changes" in diff


@pytest.mark.unit
class TestVersionValidation:
    """Test version validation rules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = PromptManagementService(Mock())
    
    def test_valid_version_format(self):
        """Test valid version formats pass validation."""
        valid_versions = ["1.0.0", "2.5.3", "10.0.1", "0.0.1"]
        
        for version in valid_versions:
            assert self.service.is_valid_version(version)
    
    def test_invalid_version_format(self):
        """Test invalid version formats fail validation."""
        invalid_versions = [
            "1.0", "1", "v1.0.0", "1.0.0-beta", 
            "1.0.0.0", "abc", "1.a.0"
        ]
        
        for version in invalid_versions:
            assert not self.service.is_valid_version(version)
    
    def test_version_components_must_be_non_negative(self):
        """Test version components must be non-negative."""
        invalid = ["-1.0.0", "1.-2.0", "1.0.-3"]
        
        for version in invalid:
            assert not self.service.is_valid_version(version)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
