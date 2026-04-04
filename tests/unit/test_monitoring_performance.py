"""Unit tests for PerformanceTracker."""

import pytest
import time
import json
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.monitoring.performance import PerformanceTracker, timer, get_performance_tracker


@pytest.fixture
def temp_log_dir():
    """Create temporary directory for logs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def performance_tracker(temp_log_dir):
    """Create a PerformanceTracker instance with temp directory."""
    return PerformanceTracker(log_dir=temp_log_dir)


class TestPerformanceTracker:
    """Test the PerformanceTracker functionality."""
    
    def test_initialization(self, temp_log_dir):
        """Test tracker initialization."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        assert tracker.log_dir == temp_log_dir
        assert os.path.exists(temp_log_dir)
        assert tracker._total_operations == 0
        assert len(tracker.metrics) == 0
        assert len(tracker.error_counts) == 0
    
    def test_record_time(self, performance_tracker):
        """Test recording execution times."""
        performance_tracker.record_time('op', 0.5)
        performance_tracker.record_time('op', 0.3)
        
        stats = performance_tracker.get_stats('op')
        assert stats['count'] == 2
        assert stats['avg'] == pytest.approx(0.4)
        assert stats['min'] == 0.3
        assert stats['max'] == 0.5
        assert stats['error_rate'] == 0.0
        assert 'p50' in stats
        assert 'p95' in stats
        assert 'p99' in stats
        assert 'std_dev' in stats
    
    def test_record_error(self, performance_tracker):
        """Test recording errors."""
        # Record errors
        performance_tracker.record_error('op', 'ValueError')
        performance_tracker.record_error('op', 'ValueError')
        performance_tracker.record_error('op', 'KeyError')
        
        # Stats with only errors
        stats = performance_tracker.get_stats('op')
        assert stats['count'] == 0
        assert stats['error_rate'] == 1.0  # 3 errors / 3 total = 1.0
        
        # Add successes
        performance_tracker.record_time('op', 0.5)
        performance_tracker.record_time('op', 0.6)
        
        stats = performance_tracker.get_stats('op')
        assert stats['count'] == 2
        assert round(stats['error_rate'], 1) == 0.6  # 3 errors / 5 total = 0.6
    
    def test_get_all_stats(self, performance_tracker):
        """Test getting all statistics."""
        performance_tracker.record_time('op1', 0.1)
        performance_tracker.record_time('op1', 0.2)
        performance_tracker.record_time('op2', 0.3)
        performance_tracker.record_error('op1', 'Error')

        all_stats = performance_tracker.get_all_stats()

        assert 'op1' in all_stats
        assert 'op2' in all_stats
        assert all_stats['op1']['count'] == 2
        assert all_stats['op2']['count'] == 1
        assert all_stats['op1']['avg'] == pytest.approx(0.15)
        assert all_stats['op2']['avg'] == 0.3
        assert all_stats['op1']['error_rate'] == pytest.approx(0.33, rel=0.1)
    
    def test_get_summary(self, performance_tracker):
        """Test getting summary statistics."""
        performance_tracker.record_time('op1', 0.1)
        performance_tracker.record_time('op1', 0.2)
        performance_tracker.record_time('op2', 0.5)
        performance_tracker.record_error('op1', 'Error')
        
        summary = performance_tracker.get_summary()
        
        assert 'total_operations' in summary
        assert 'total_errors' in summary
        assert 'overall_error_rate' in summary
        assert 'active_operations' in summary
        assert 'slowest_operation' in summary
        assert 'most_error_prone' in summary
        assert 'uptime_seconds' in summary
        assert summary['total_operations'] >= 3
    
    def test_get_operation_ranking(self, performance_tracker):
        """Test operation ranking."""
        performance_tracker.record_time('fast_op', 0.1)
        performance_tracker.record_time('medium_op', 0.5)
        performance_tracker.record_time('slow_op', 1.0)
        
        ranking = performance_tracker.get_operation_ranking(sort_by='avg', limit=2)
        
        assert len(ranking) == 2
        assert ranking[0][0] == 'slow_op'  # Slowest first
        assert ranking[1][0] == 'medium_op'
    
    def test_get_slow_operations(self, performance_tracker):
        """Test getting slow operations."""
        performance_tracker.record_time('fast_op', 0.1)
        performance_tracker.record_time('slow_op', 6.0)
        performance_tracker.record_time('very_slow_op', 10.0)
        
        slow_ops = performance_tracker.get_slow_operations(threshold=5.0)
        
        assert len(slow_ops) == 2
        assert ('very_slow_op', 10.0) in slow_ops
        assert ('slow_op', 6.0) in slow_ops
    
    def test_get_high_error_operations(self, performance_tracker):
        """Test getting high-error operations."""
        # Create operation with high error rate
        performance_tracker.record_error('error_prone', 'Error')
        performance_tracker.record_error('error_prone', 'Error')
        performance_tracker.record_time('error_prone', 0.1)  # 2 errors, 1 success = 67% error rate
        
        # Create operation with low error rate
        performance_tracker.record_time('reliable', 0.1)
        performance_tracker.record_time('reliable', 0.2)
        performance_tracker.record_error('reliable', 'Error')  # 1 error, 2 successes = 33% error rate
        
        high_error_ops = performance_tracker.get_high_error_operations(threshold=0.5)
        
        assert len(high_error_ops) == 1
        assert high_error_ops[0][0] == 'error_prone'
    
    def test_export_metrics(self, performance_tracker, temp_log_dir):
        """Test exporting metrics to file."""
        performance_tracker.record_time('test_op', 0.5)
        performance_tracker.record_error('test_op', 'Error')
        
        filepath = performance_tracker.export_metrics()
        
        assert os.path.exists(filepath)
        assert filepath.endswith('.json')
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            assert 'timestamp' in data
            assert 'summary' in data
            assert 'stats' in data
            assert 'metrics' in data
            assert 'error_counts' in data
            assert 'total_operations' in data
            assert 'test_op' in data['stats']
    
    def test_export_metrics_custom_path(self, performance_tracker, temp_log_dir):
        """Test exporting metrics to custom file path."""
        custom_path = os.path.join(temp_log_dir, 'custom_metrics.json')
        performance_tracker.record_time('test_op', 0.5)
        
        filepath = performance_tracker.export_metrics(custom_path)
        
        assert filepath == custom_path
        assert os.path.exists(custom_path)
    
    def test_reset(self, performance_tracker):
        """Test resetting metrics."""
        performance_tracker.record_time('op', 0.5)
        performance_tracker.record_error('op', 'Error')
        
        assert performance_tracker.get_stats('op')['count'] == 1
        
        performance_tracker.reset()
        
        stats = performance_tracker.get_stats('op')
        assert stats['count'] == 0
        assert stats['error_rate'] == 0.0
        assert performance_tracker._total_operations == 0
    
    def test_empty_stats(self, performance_tracker):
        """Test getting stats for non-existent operation."""
        stats = performance_tracker.get_stats('non_existent')
        
        assert stats['count'] == 0
        assert stats['avg'] == 0.0
        assert stats['min'] == 0.0
        assert stats['max'] == 0.0
        assert stats['p50'] == 0.0
        assert stats['p95'] == 0.0
        assert stats['p99'] == 0.0
        assert stats['std_dev'] == 0.0
        assert stats['error_rate'] == 0.0
    
    def test_percentile_calculation(self, performance_tracker):
        """Test percentile calculations."""
        # Create a list of 100 times for accurate percentiles
        times = list(range(1, 101))  # 1 to 100
        for t in times:
            performance_tracker.record_time('op', t / 100)  # 0.01 to 1.00
        
        stats = performance_tracker.get_stats('op')
        
        assert stats['count'] == 100
        assert stats['p50'] == pytest.approx(0.50, rel=0.05)
        assert stats['p95'] == pytest.approx(0.95, rel=0.05)
        assert stats['p99'] == pytest.approx(0.99, rel=0.05)
    
    def test_std_dev_calculation(self, performance_tracker):
        """Test standard deviation calculation."""
        # Uniform values should have std_dev near 0
        for _ in range(10):
            performance_tracker.record_time('uniform_op', 0.5)
        
        uniform_stats = performance_tracker.get_stats('uniform_op')
        assert uniform_stats['std_dev'] < 0.01
        
        # Varied values should have higher std_dev
        performance_tracker.record_time('varied_op', 0.1)
        performance_tracker.record_time('varied_op', 0.2)
        performance_tracker.record_time('varied_op', 0.9)
        
        varied_stats = performance_tracker.get_stats('varied_op')
        assert varied_stats['std_dev'] > 0.3


class TestTimerDecorator:
    """Test the timer decorator."""
    
    def test_timer_basic(self, temp_log_dir):
        """Test basic timer functionality."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(operation='test_func', tracker=tracker)
        def test_func():
            time.sleep(0.05)
            return "done"
        
        result = test_func()
        assert result == "done"
        
        stats = tracker.get_stats('test_func')
        assert stats['count'] == 1
        assert 0.03 <= stats['avg'] <= 0.15
        assert stats['error_rate'] == 0.0
    
    def test_timer_error(self, temp_log_dir):
        """Test timer with error."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(operation='failing_func', tracker=tracker)
        def failing_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        stats = tracker.get_stats('failing_func')
        assert stats['count'] == 0
        assert stats['error_rate'] == 1.0
    
    def test_timer_default_name(self, temp_log_dir):
        """Test timer with default operation name."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(tracker=tracker)
        def my_func():
            return "done"
        
        my_func()
        
        stats = tracker.get_stats('my_func')
        assert stats['count'] == 1
    
    def test_timer_multiple(self, temp_log_dir):
        """Test multiple timer calls."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(operation='multi', tracker=tracker)
        def fast():
            return "fast"
        
        for _ in range(5):
            fast()
        
        stats = tracker.get_stats('multi')
        assert stats['count'] == 5
    
    def test_timer_async(self, temp_log_dir):
        """Test timer with async function."""
        import asyncio
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(operation='async_func', tracker=tracker)
        async def async_func():
            await asyncio.sleep(0.01)
            return "done"
        
        result = asyncio.run(async_func())
        assert result == "done"
        
        stats = tracker.get_stats('async_func')
        assert stats['count'] == 1
    
    def test_timer_with_args(self, temp_log_dir):
        """Test timer with function arguments."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(operation='add', tracker=tracker)
        def add(a, b):
            return a + b
        
        result = add(2, 3)
        assert result == 5
        
        stats = tracker.get_stats('add')
        assert stats['count'] == 1
    
    def test_timer_no_operation_name(self, temp_log_dir):
        """Test timer without explicit operation name."""
        tracker = PerformanceTracker(log_dir=temp_log_dir)
        
        @timer(tracker=tracker)
        def unnamed_function():
            return "result"
        
        unnamed_function()
        
        stats = tracker.get_stats('unnamed_function')
        assert stats['count'] == 1


class TestSingleton:
    """Test singleton pattern."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        t1 = get_performance_tracker()
        t2 = get_performance_tracker()
        assert t1 is t2
    
    def test_singleton_reset(self):
        """Test singleton reset."""
        tracker = get_performance_tracker()
        tracker.record_time('test', 0.1)
        tracker.reset()
        
        stats = tracker.get_stats('test')
        assert stats['count'] == 0


# Standalone test functions
def test_no_hanging(temp_log_dir):
    """Test that operations don't hang."""
    tracker = PerformanceTracker(log_dir=temp_log_dir)
    
    # These should all be fast
    tracker.record_time('test', 0.1)
    tracker.record_error('test', 'Error')
    
    stats = tracker.get_stats('test')
    assert stats['count'] == 1
    
    all_stats = tracker.get_all_stats()
    assert 'test' in all_stats
    
    filepath = tracker.export_metrics()
    assert os.path.exists(filepath)


def test_multiple_operations(temp_log_dir):
    """Test multiple operations."""
    tracker = PerformanceTracker(log_dir=temp_log_dir)
    
    # Record various operations
    tracker.record_time('op1', 0.1)
    tracker.record_time('op1', 0.2)
    tracker.record_time('op2', 0.3)
    tracker.record_error('op1', 'Error')
    tracker.record_error('op3', 'Error')
    
    stats = tracker.get_all_stats()
    assert len(stats) == 3
    assert 'op1' in stats
    assert 'op2' in stats
    assert 'op3' in stats


def test_large_number_of_records(temp_log_dir):
    """Test handling large number of records."""
    tracker = PerformanceTracker(log_dir=temp_log_dir)
    
    # Record 1000 operations
    for i in range(1000):
        tracker.record_time('large_op', i / 1000)
    
    stats = tracker.get_stats('large_op')
    assert stats['count'] == 1000
    assert 0.4 <= stats['avg'] <= 0.6


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])