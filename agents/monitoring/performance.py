"""
Performance tracking and monitoring for agents.
Provides timing decorators and performance metrics collection.
"""

import functools
import json
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Track performance metrics for agent operations.
    
    Features:
    - Execution time tracking per operation
    - Error rate monitoring
    - Percentile calculations (p50, p95, p99)
    - Thread-safe metric collection
    - Metrics export to JSON
    """
    
    def __init__(self, log_dir: str = "logs/performance/"):
        """
        Initialize the Performance Tracker.
        
        Args:
            log_dir: Directory to store performance logs
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.lock = threading.RLock()
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self._total_operations = 0
        self._start_time = datetime.now()
        
        logger.info(f"PerformanceTracker initialized with log directory: {log_dir}")
    
    def record_time(self, operation: str, duration: float) -> None:
        """
        Record execution time for an operation.
        
        Args:
            operation: Name of the operation
            duration: Execution time in seconds
        """
        with self.lock:
            self.metrics[operation].append(duration)
            self._total_operations += 1
        
        # Log slow operations
        if duration > 5.0:
            logger.warning(f"Slow operation detected: {operation} took {duration:.2f}s")
    
    def record_error(self, operation: str, error_type: str) -> None:
        """
        Record an error for an operation.
        
        Args:
            operation: Name of the operation
            error_type: Type of error that occurred
        """
        with self.lock:
            self.error_counts[operation] += 1
        
        logger.debug(f"Error recorded for {operation}: {error_type}")
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """
        Get statistics for an operation.
        
        Args:
            operation: Name of the operation
            
        Returns:
            Dictionary with statistics (avg, min, max, p50, p95, p99, error_rate)
        """
        with self.lock:
            times = list(self.metrics.get(operation, []))
            error_count = self.error_counts.get(operation, 0)
            total_calls = len(times) + error_count
        
        if total_calls == 0:
            return self._empty_stats()
        
        # Calculate error rate
        error_rate = error_count / total_calls if total_calls > 0 else 0.0
        
        if not times:
            return {
                'count': 0,
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0,
                'std_dev': 0.0,
                'error_rate': error_rate
            }
        
        times.sort()
        n = len(times)
        
        # Calculate percentiles
        p50_index = min(int(n * 0.50), n - 1)
        p95_index = min(int(n * 0.95), n - 1)
        p99_index = min(int(n * 0.99), n - 1)
        
        # Calculate standard deviation
        mean = sum(times) / n
        variance = sum((t - mean) ** 2 for t in times) / n
        std_dev = variance ** 0.5
        
        return {
            'count': n,
            'avg': round(mean, 4),
            'min': round(times[0], 4),
            'max': round(times[-1], 4),
            'p50': round(times[p50_index], 4),
            'p95': round(times[p95_index], 4),
            'p99': round(times[p99_index], 4),
            'std_dev': round(std_dev, 4),
            'error_rate': round(error_rate, 4)
        }
    
    def _empty_stats(self) -> Dict[str, float]:
        """Return empty statistics."""
        return {
            'count': 0,
            'avg': 0.0,
            'min': 0.0,
            'max': 0.0,
            'p50': 0.0,
            'p95': 0.0,
            'p99': 0.0,
            'std_dev': 0.0,
            'error_rate': 0.0
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for all operations.
        
        Returns:
            Dictionary mapping operation name to statistics
        """
        with self.lock:
            operations = set()
            operations.update(self.metrics.keys())
            operations.update(self.error_counts.keys())
            operations = list(operations)
        
        result = {}
        for op in operations:
            result[op] = self.get_stats(op)
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all performance metrics.
        
        Returns:
            Dictionary with overall summary statistics
        """
        all_stats = self.get_all_stats()
        
        total_operations = sum(s['count'] for s in all_stats.values())
        total_errors = sum(s['count'] * s['error_rate'] for s in all_stats.values())
        avg_error_rate = total_errors / max(total_operations, 1)
        
        # Find slowest operation
        slowest_op = max(all_stats.items(), key=lambda x: x[1].get('avg', 0)) if all_stats else (None, {})
        
        # Find most error-prone operation
        most_error_op = max(all_stats.items(), key=lambda x: x[1].get('error_rate', 0)) if all_stats else (None, {})
        
        return {
            'total_operations': total_operations,
            'total_errors': int(total_errors),
            'overall_error_rate': round(avg_error_rate, 4),
            'active_operations': len(all_stats),
            'slowest_operation': {
                'name': slowest_op[0],
                'avg_time': slowest_op[1].get('avg', 0)
            } if slowest_op[0] else None,
            'most_error_prone': {
                'name': most_error_op[0],
                'error_rate': most_error_op[1].get('error_rate', 0)
            } if most_error_op[0] else None,
            'uptime_seconds': (datetime.now() - self._start_time).total_seconds()
        }
    
    def get_operation_ranking(self, sort_by: str = 'avg', limit: int = 10) -> List[Tuple[str, Dict]]:
        """
        Get ranking of operations by specified metric.
        
        Args:
            sort_by: Metric to sort by ('avg', 'p95', 'error_rate', 'count')
            limit: Maximum number of operations to return
            
        Returns:
            List of (operation_name, stats) tuples sorted descending
        """
        all_stats = self.get_all_stats()
        
        valid_sort_keys = ['avg', 'p95', 'error_rate', 'count']
        if sort_by not in valid_sort_keys:
            sort_by = 'avg'
        
        sorted_ops = sorted(
            all_stats.items(),
            key=lambda x: x[1].get(sort_by, 0),
            reverse=True
        )
        
        return sorted_ops[:limit]
    
    def get_time_series(self, operation: str) -> List[Dict[str, Any]]:
        """
        Get time series data for an operation.
        
        Args:
            operation: Name of the operation
            
        Returns:
            List of execution records with timestamps
        """
        # This would require storing timestamps with each measurement
        # For now, return just the list of durations
        with self.lock:
            times = list(self.metrics.get(operation, []))
        
        return [
            {'index': i, 'duration': duration}
            for i, duration in enumerate(times)
        ]
    
    def export_metrics(self, filepath: Optional[str] = None) -> str:
        """
        Export metrics to JSON file.
        
        Args:
            filepath: Optional custom filepath
            
        Returns:
            Path to the exported file
        """
        if filepath is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.log_dir, f"metrics_{timestamp}.json")
        
        # Get data under lock
        with self.lock:
            stats_data = self.get_all_stats()
            metrics_data = {k: list(v) for k, v in self.metrics.items()}
            errors_data = dict(self.error_counts)
        
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': self.get_summary(),
            'stats': stats_data,
            'metrics': metrics_data,
            'error_counts': errors_data,
            'total_operations': self._total_operations
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Metrics exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
        
        return filepath
    
    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self.lock:
            self.metrics.clear()
            self.error_counts.clear()
            self._total_operations = 0
            self._start_time = datetime.now()
        
        logger.info("Performance metrics reset")
    
    def get_slow_operations(self, threshold: float = 5.0) -> List[Tuple[str, float]]:
        """
        Get operations that exceed a time threshold.
        
        Args:
            threshold: Time threshold in seconds
            
        Returns:
            List of (operation_name, avg_time) for slow operations
        """
        all_stats = self.get_all_stats()
        slow_ops = []
        
        for op, stats in all_stats.items():
            avg_time = stats.get('avg', 0)
            if avg_time > threshold and stats.get('count', 0) > 0:
                slow_ops.append((op, avg_time))
        
        return sorted(slow_ops, key=lambda x: x[1], reverse=True)
    
    def get_high_error_operations(self, threshold: float = 0.1) -> List[Tuple[str, float]]:
        """
        Get operations with high error rates.
        
        Args:
            threshold: Error rate threshold (e.g., 0.1 = 10%)
            
        Returns:
            List of (operation_name, error_rate) for high-error operations
        """
        all_stats = self.get_all_stats()
        high_error_ops = []
        
        for op, stats in all_stats.items():
            error_rate = stats.get('error_rate', 0)
            if error_rate > threshold and stats.get('count', 0) > 0:
                high_error_ops.append((op, error_rate))
        
        return sorted(high_error_ops, key=lambda x: x[1], reverse=True)


# Decorator for timing functions
def timer(
    operation: Optional[str] = None,
    tracker: Optional[PerformanceTracker] = None,
    log_slow: bool = True
) -> Callable:
    """
    Decorator to time function execution.
    
    Args:
        operation: Name of the operation (defaults to function name)
        tracker: PerformanceTracker instance (uses global if None)
        log_slow: Whether to log slow operations
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal operation
            if operation is None:
                operation = func.__name__
            
            perf_tracker = tracker or get_performance_tracker()
            
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                perf_tracker.record_time(operation, duration)
                
                if log_slow and duration > 5.0:
                    logger.warning(f"Timer: {operation} took {duration:.2f}s")
                
                return result
            except Exception as e:
                perf_tracker.record_error(operation, type(e).__name__)
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            nonlocal operation
            if operation is None:
                operation = func.__name__
            
            perf_tracker = tracker or get_performance_tracker()
            
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                perf_tracker.record_time(operation, duration)
                
                if log_slow and duration > 5.0:
                    logger.warning(f"Timer: {operation} took {duration:.2f}s")
                
                return result
            except Exception as e:
                perf_tracker.record_error(operation, type(e).__name__)
                raise
        
        # Return appropriate wrapper based on whether the function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


# Singleton instance
_performance_tracker = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create the global performance tracker instance."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker


__all__ = ['PerformanceTracker', 'timer', 'get_performance_tracker']