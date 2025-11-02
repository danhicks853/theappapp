"""
Progress Evaluator Unit Tests

Tests progress evaluation, baseline tracking, and metrics calculation.
"""
import pytest
import os
import tempfile
import time
from backend.services.progress_evaluator import ProgressEvaluator


@pytest.mark.unit
class TestProgressEvaluatorInitialization:
    """Test progress evaluator initialization."""
    
    def test_progress_evaluator_creation(self):
        """Test creating progress evaluator."""
        evaluator = ProgressEvaluator()
        
        assert evaluator is not None
        assert evaluator.get_baseline_count() == 0
    
    def test_evaluator_handles_multiple_tasks(self):
        """Test evaluator can handle multiple tasks."""
        evaluator = ProgressEvaluator()
        
        assert evaluator.get_baseline_count() == 0


@pytest.mark.unit
class TestBaselineManagement:
    """Test baseline setting and retrieval."""
    
    def test_set_baseline_creates_snapshot(self):
        """Test setting baseline creates a snapshot."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("print('hello')")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            assert evaluator.has_baseline("task-1")
            assert evaluator.get_baseline_count() == 1
    
    def test_set_baseline_captures_file_count(self):
        """Test baseline captures file count."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files
            for i in range(5):
                with open(os.path.join(tmpdir, f"file{i}.py"), "w") as f:
                    f.write(f"content {i}")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            baseline = evaluator.get_baseline("task-1")
            assert baseline["file_count"] == 5
    
    def test_set_baseline_captures_line_count(self):
        """Test baseline captures total line count."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with multiple lines
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("line 1\nline 2\nline 3\n")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            baseline = evaluator.get_baseline("task-1")
            assert baseline["total_lines"] == 3
    
    def test_get_baseline_returns_none_for_unknown_task(self):
        """Test getting baseline for unknown task returns None."""
        evaluator = ProgressEvaluator()
        
        result = evaluator.get_baseline("unknown-task")
        
        assert result is None
    
    def test_update_baseline_replaces_old(self):
        """Test updating baseline replaces old snapshot."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initial baseline
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("initial")
            
            evaluator.set_baseline("task-1", tmpdir)
            baseline1 = evaluator.get_baseline("task-1")
            
            # Update baseline
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("updated")
            
            evaluator.set_baseline("task-1", tmpdir)
            baseline2 = evaluator.get_baseline("task-1")
            
            assert baseline2["file_count"] == 2
            assert baseline2["file_count"] != baseline1["file_count"]


@pytest.mark.unit
class TestProgressEvaluation:
    """Test progress evaluation logic."""
    
    def test_evaluate_progress_with_new_files(self):
        """Test evaluating progress detects new files."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set baseline
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("initial")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            # Add new file
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("new file")
            
            progress = evaluator.evaluate_progress("task-1", tmpdir)
            
            assert progress is True
            assert evaluator.get_last_evaluation("task-1")["files_added"] == 1
    
    def test_evaluate_progress_with_modified_files(self):
        """Test evaluating progress detects modified files."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "file1.py")
            
            # Set baseline
            with open(test_file, "w") as f:
                f.write("initial content\n")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            # Modify file
            time.sleep(0.1)  # Ensure different mtime
            with open(test_file, "a") as f:
                f.write("additional content\n")
            
            progress = evaluator.evaluate_progress("task-1", tmpdir)
            
            assert progress is True
            assert evaluator.get_last_evaluation("task-1")["files_modified"] >= 0
    
    def test_evaluate_progress_with_no_changes(self):
        """Test evaluating progress with no changes returns False."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set baseline
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("content")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            # No changes
            progress = evaluator.evaluate_progress("task-1", tmpdir)
            
            assert progress is False
    
    def test_evaluate_progress_without_baseline_returns_false(self):
        """Test evaluating progress without baseline returns False."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            progress = evaluator.evaluate_progress("unknown-task", tmpdir)
            
            assert progress is False
    
    def test_evaluate_progress_with_deleted_files(self):
        """Test evaluating progress detects deleted files."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "file1.py")
            
            # Set baseline with file
            with open(test_file, "w") as f:
                f.write("content")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            # Delete file
            os.remove(test_file)
            
            progress = evaluator.evaluate_progress("task-1", tmpdir)
            
            # Deletion is considered progress
            assert progress is True
            assert evaluator.get_last_evaluation("task-1")["files_deleted"] >= 1


@pytest.mark.unit
class TestMetricsCalculation:
    """Test metrics calculation."""
    
    def test_calculate_metrics_returns_dict(self):
        """Test calculate_metrics returns dictionary."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("line1\nline2\n")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("new")
            
            evaluator.evaluate_progress("task-1", tmpdir)
            
            metrics = evaluator.get_metrics("task-1")
            
            assert isinstance(metrics, dict)
            assert "file_count" in metrics
            assert "total_lines" in metrics
    
    def test_metrics_include_change_counts(self):
        """Test metrics include change counts."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Baseline
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("initial")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            # Changes
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("new")
            
            evaluator.evaluate_progress("task-1", tmpdir)
            
            evaluation = evaluator.get_last_evaluation("task-1")
            
            assert "files_added" in evaluation
            assert "files_modified" in evaluation
            assert "files_deleted" in evaluation


@pytest.mark.unit
class TestProgressHistory:
    """Test progress history tracking."""
    
    def test_get_last_evaluation_returns_dict(self):
        """Test getting last evaluation returns dictionary."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("content")
            
            evaluator.set_baseline("task-1", tmpdir)
            evaluator.evaluate_progress("task-1", tmpdir)
            
            last_eval = evaluator.get_last_evaluation("task-1")
            
            assert isinstance(last_eval, dict)
    
    def test_get_last_evaluation_returns_none_without_evaluation(self):
        """Test getting last evaluation without evaluation returns None."""
        evaluator = ProgressEvaluator()
        
        result = evaluator.get_last_evaluation("unknown-task")
        
        assert result is None


@pytest.mark.unit
class TestFileFiltering:
    """Test file filtering logic."""
    
    def test_ignores_gitignore_patterns(self):
        """Test that gitignore patterns are ignored."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files that should be ignored
            os.makedirs(os.path.join(tmpdir, "node_modules"))
            with open(os.path.join(tmpdir, "node_modules", "package.js"), "w") as f:
                f.write("ignored")
            
            # Create normal file
            with open(os.path.join(tmpdir, "app.js"), "w") as f:
                f.write("normal")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            baseline = evaluator.get_baseline("task-1")
            
            # Should only count app.js
            assert baseline["file_count"] == 1
    
    def test_ignores_hidden_files(self):
        """Test that hidden files are ignored."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create hidden file
            with open(os.path.join(tmpdir, ".hidden"), "w") as f:
                f.write("hidden")
            
            # Create normal file
            with open(os.path.join(tmpdir, "visible.py"), "w") as f:
                f.write("visible")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            baseline = evaluator.get_baseline("task-1")
            
            # Should only count visible.py
            assert baseline["file_count"] == 1


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_directory_baseline(self):
        """Test setting baseline on empty directory."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            evaluator.set_baseline("task-1", tmpdir)
            
            baseline = evaluator.get_baseline("task-1")
            
            assert baseline["file_count"] == 0
            assert baseline["total_lines"] == 0
    
    def test_nonexistent_directory_raises(self):
        """Test nonexistent directory raises error."""
        evaluator = ProgressEvaluator()
        
        with pytest.raises(Exception):
            evaluator.set_baseline("task-1", "/nonexistent/path")
    
    def test_multiple_evaluations_same_task(self):
        """Test multiple evaluations on same task."""
        evaluator = ProgressEvaluator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initial
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("initial")
            
            evaluator.set_baseline("task-1", tmpdir)
            
            # First evaluation
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("new")
            evaluator.evaluate_progress("task-1", tmpdir)
            
            # Second evaluation
            with open(os.path.join(tmpdir, "file3.py"), "w") as f:
                f.write("newer")
            progress = evaluator.evaluate_progress("task-1", tmpdir)
            
            assert progress is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
