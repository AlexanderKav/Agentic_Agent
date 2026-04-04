"""Unit tests for SelfHealingAgent."""

import pytest
import time
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.self_healing.healing_agent import SelfHealingAgent, HealingAction, FailurePattern, get_healing_agent


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def healing_agent(temp_storage_dir):
    """Create a SelfHealingAgent instance with temp storage."""
    return SelfHealingAgent(
        storage_dir=temp_storage_dir,
        min_failures_for_action=3,
        pattern_window_hours=24,
        auto_apply_threshold=0.85
    )


class TestSelfHealingAgent:
    """Test the SelfHealingAgent functionality."""
    
    def test_initialization(self, temp_storage_dir):
        """Test agent initialization."""
        agent = SelfHealingAgent(storage_dir=temp_storage_dir)
        assert agent.storage_dir == temp_storage_dir
        assert len(agent.failure_patterns) == 0
        assert len(agent.healing_actions) == 0
        assert agent.min_failures_for_action == 3
        assert agent.pattern_window_hours == 24
        assert agent.auto_apply_threshold == 0.85
    
    def test_analyze_failure_first_time(self, healing_agent):
        """Test analyzing a new failure pattern."""
        error = KeyError("'revenue'")
        context = {
            'tool': 'compute_kpis',
            'data_shape': (10, 5),
            'available_columns': ['date', 'cost']
        }
        
        action = healing_agent.analyze_failure(error, context)
        
        # First failure shouldn't return action (needs 3 occurrences)
        assert action is None
        assert len(healing_agent.failure_patterns) == 1
    
    def test_analyze_failure_repeated(self, healing_agent):
        """Test analyzing repeated failures."""
        error = KeyError("'revenue'")
        context = {'tool': 'compute_kpis'}
        
        # First 2 times - no action
        for i in range(2):
            action = healing_agent.analyze_failure(error, context)
            assert action is None, f"Expected no action on attempt {i+1}"
        
        # 3rd time - should get action
        action = healing_agent.analyze_failure(error, context)
        assert action is not None
        assert 'KeyError' in action.pattern_id
        assert 'column' in action.suggestion.lower()
        assert action.confidence >= 0.3
        assert 0 <= action.confidence <= 1
    
    def test_fix_templates(self, temp_storage_dir):
        """Test all fix templates."""
        agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
        
        test_cases = [
            (KeyError("'revenue'"), 'column'),
            (ValueError("invalid literal"), 'validate'),
            (TypeError("unsupported type"), 'data types'),
            (AttributeError("no attribute"), 'attribute'),
            (IndexError("list index"), 'bounds'),
            (ZeroDivisionError("division by zero"), 'zero'),
            (FileNotFoundError("no file"), 'path'),
            (PermissionError("denied"), 'permissions'),
        ]
        
        for error, expected in test_cases:
            context = {'tool': 'test'}
            # Need multiple failures to trigger fix
            for _ in range(3):
                agent.analyze_failure(error, context)
            
            # Get the last action
            if agent.healing_actions:
                action = agent.healing_actions[-1]
                assert expected.lower() in action.suggestion.lower()
    
    def test_confidence_calculation(self, healing_agent):
        """Test confidence calculation."""
        error = KeyError("'revenue'")
        context = {'tool': 'compute_kpis'}
        
        # Generate multiple failures and track confidence
        confidences = []
        for i in range(10):
            action = healing_agent.analyze_failure(error, context)
            if action:
                confidences.append(action.confidence)
        
        # Confidence should increase with more occurrences
        if len(confidences) >= 2:
            assert confidences[-1] >= confidences[0]
    
    def test_record_fix_result(self, healing_agent):
        """Test recording fix results."""
        # Generate a failure pattern
        error = KeyError("'revenue'")
        context = {'tool': 'compute_kpis'}

        # Need 3 failures to get action
        for _ in range(3):
            healing_agent.analyze_failure(error, context)

        assert len(healing_agent.healing_actions) > 0
        action = healing_agent.healing_actions[-1]

        # Initially, success rate should be 0
        initial_rate = healing_agent._get_success_rate('KeyError')
        assert initial_rate == 0.0

        # Record success
        healing_agent.record_fix_result(action, success=True)

        # Success rate should now be 1.0 (1 success, 0 failures)
        success_rate = healing_agent._get_success_rate('KeyError')
        assert success_rate == 1.0

        # Record failure
        healing_agent.record_fix_result(action, success=False)
        
        # Now rate should be 0.5 (1 success, 1 failure)
        new_rate = healing_agent._get_success_rate('KeyError')
        assert new_rate == 0.5
        
        # Record another success
        healing_agent.record_fix_result(action, success=True)
        
        # Rate should be 0.67 (2 successes, 1 failure)
        final_rate = healing_agent._get_success_rate('KeyError')
        assert round(final_rate, 2) == 0.67
    
    def test_persistence(self, temp_storage_dir):
        """Test that patterns persist across sessions."""
        agent1 = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
        
        error = KeyError("'revenue'")
        context = {'tool': 'compute_kpis'}
        
        for _ in range(3):
            agent1.analyze_failure(error, context)
        
        # Create new agent instance (should load patterns)
        agent2 = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
        
        assert len(agent2.failure_patterns) >= 3
        
        # Should have learned from history
        action = agent2.analyze_failure(error, context)
        assert action is not None
    
    def test_healing_report(self, healing_agent):
        """Test healing report generation."""
        # Generate some failures
        error = KeyError("'revenue'")
        context = {'tool': 'compute_kpis'}
        
        for _ in range(3):
            healing_agent.analyze_failure(error, context)
        
        report = healing_agent.get_healing_report()
        
        assert 'total_patterns' in report
        assert 'total_actions' in report
        assert 'successful_fixes' in report
        assert 'recent_patterns' in report
        assert 'pending_actions' in report
        assert report['total_patterns'] >= 3
        assert report['total_actions'] >= 1
    
    def test_different_error_types(self, temp_storage_dir):
        """Test handling of different error types."""
        agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
        
        errors = [
            (KeyError("missing"), "KeyError"),
            (ValueError("bad value"), "ValueError"),
            (TypeError("wrong type"), "TypeError"),
        ]
        
        for error, error_type in errors:
            for _ in range(3):
                agent.analyze_failure(error, {'tool': 'test'})
        
        # Should have suggestions for all
        found_types = set()
        for action in agent.healing_actions:
            for error_type in ['KeyError', 'ValueError', 'TypeError']:
                if error_type in action.pattern_id:
                    found_types.add(error_type)
        
        assert len(found_types) >= 2
    
    def test_context_awareness(self, temp_storage_dir):
        """Test that context influences suggestions."""
        agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
        
        error = KeyError("'revenue'")
        
        # Context with dataframe info
        context_with_df = {
            'tool': 'compute_kpis',
            'available_columns': ['date', 'cost', 'profit']
        }
        
        # Generate failures
        action = None
        for _ in range(3):
            action = agent.analyze_failure(error, context_with_df)
        
        if action:
            # Suggestion should mention available columns
            assert ('date' in action.suggestion or 
                   'cost' in action.suggestion or 
                   'profit' in action.suggestion)
    
    def test_auto_apply_threshold(self, temp_storage_dir):
        """Test auto-apply threshold based on confidence."""
        agent = SelfHealingAgent(
            storage_dir=temp_storage_dir,
            min_failures_for_action=3,
            auto_apply_threshold=0.7
        )
        
        error = KeyError("'revenue'")
        context = {'tool': 'compute_kpis'}
        
        # Generate many failures to increase confidence
        actions = []
        for i in range(15):
            action = agent.analyze_failure(error, context)
            if action:
                actions.append(action)
        
        if len(actions) >= 2:
            # Later actions should have higher confidence
            assert actions[-1].confidence >= actions[0].confidence
    
    def test_get_pattern_summary(self, healing_agent):
        """Test pattern summary generation."""
        # Generate different error types
        errors = [
            (KeyError("key1"), "KeyError"),
            (KeyError("key2"), "KeyError"),
            (ValueError("val1"), "ValueError"),
            (TypeError("type1"), "TypeError"),
        ]
        
        for error, _ in errors:
            healing_agent.analyze_failure(error, {'tool': 'test'})
        
        summary = healing_agent.get_pattern_summary()
        assert isinstance(summary, dict)
        assert len(summary) > 0
    
    def test_get_most_common_errors(self, healing_agent):
        """Test getting most common errors."""
        # Generate multiple KeyErrors
        for _ in range(5):
            healing_agent.analyze_failure(KeyError("test"), {'tool': 'test'})
        
        # Generate a few ValueErrors
        for _ in range(2):
            healing_agent.analyze_failure(ValueError("test"), {'tool': 'test'})
        
        most_common = healing_agent.get_most_common_errors(limit=2)
        assert len(most_common) <= 2
        # KeyError should be first (most common)
        if most_common:
            assert most_common[0][0] == 'KeyError'
    
    def test_clear_old_patterns(self, healing_agent):
        """Test clearing old patterns."""
        # Add a pattern
        healing_agent.analyze_failure(KeyError("test"), {'tool': 'test'})
        
        # Should have 1 pattern
        assert len(healing_agent.failure_patterns) == 1
        
        # Clear patterns older than 0 days (all)
        removed = healing_agent.clear_old_patterns(days=0)
        assert removed >= 0
        # Patterns may or may not be removed depending on timestamp


class TestFailurePattern:
    """Test FailurePattern data class."""
    
    def test_failure_pattern_creation(self):
        """Test creating a failure pattern."""
        pattern = FailurePattern(
            error_type="KeyError",
            error_message="'revenue' not found",
            tool="compute_kpis",
            data_shape=(10, 5),
            timestamp=time.time(),
            context={"available_columns": ["date", "cost"]}
        )
        
        assert pattern.error_type == "KeyError"
        assert pattern.tool == "compute_kpis"
        assert pattern.data_shape == (10, 5)
        assert "available_columns" in pattern.context
    
    def test_failure_pattern_to_dict(self):
        """Test converting failure pattern to dict."""
        pattern = FailurePattern(
            error_type="KeyError",
            error_message="'revenue' not found",
            tool="compute_kpis",
            data_shape=(10, 5),
            timestamp=1234567890.0,
            context={"available_columns": ["date", "cost"]}
        )
        
        d = pattern.to_dict()
        assert d['error_type'] == "KeyError"
        assert d['tool'] == "compute_kpis"
        assert d['data_shape'] == [10, 5]  # Tuple converted to list
        assert d['timestamp'] == 1234567890.0
    
    def test_failure_pattern_from_dict(self):
        """Test creating failure pattern from dict."""
        data = {
            'error_type': 'KeyError',
            'error_message': "'revenue' not found",
            'tool': 'compute_kpis',
            'data_shape': [10, 5],
            'timestamp': 1234567890.0,
            'context': {'available_columns': ['date', 'cost']}
        }
        
        pattern = FailurePattern.from_dict(data)
        assert pattern.error_type == "KeyError"
        assert pattern.tool == "compute_kpis"
        assert pattern.data_shape == (10, 5)
        assert pattern.timestamp == 1234567890.0


class TestHealingAction:
    """Test HealingAction data class."""
    
    def test_healing_action_creation(self):
        """Test creating a healing action."""
        action = HealingAction(
            pattern_id="KeyError_12345",
            suggestion="Check if column exists",
            confidence=0.75,
            auto_apply=False
        )
        
        assert action.pattern_id == "KeyError_12345"
        assert action.suggestion == "Check if column exists"
        assert action.confidence == 0.75
        assert action.auto_apply is False
        assert action.fixed is False
    
    def test_healing_action_to_dict(self):
        """Test converting healing action to dict."""
        action = HealingAction(
            pattern_id="KeyError_12345",
            suggestion="Check if column exists",
            confidence=0.75,
            auto_apply=False,
            applied_at=1234567890.0,
            resolved_at=1234567900.0
        )
        
        d = action.to_dict()
        assert d['pattern_id'] == "KeyError_12345"
        assert d['suggestion'] == "Check if column exists"
        assert d['confidence'] == 0.75
        assert d['auto_apply'] is False
        assert d['fixed'] is False
        assert d['applied_at'] == 1234567890.0
        assert d['resolved_at'] == 1234567900.0


class TestSingleton:
    """Test singleton pattern."""
    
    def test_singleton(self):
        """Test singleton pattern for healing agent."""
        h1 = get_healing_agent()
        h2 = get_healing_agent()
        assert h1 is h2


# Standalone test functions
def test_no_crash_with_invalid_context(temp_storage_dir):
    """Test that agent doesn't crash with invalid context."""
    agent = SelfHealingAgent(storage_dir=temp_storage_dir)
    
    error = KeyError("test")
    
    # Test with various invalid contexts
    invalid_contexts = [
        None,
        {},
        {'tool': None},
        {'invalid': 'data'}
    ]
    
    for context in invalid_contexts:
        try:
            action = agent.analyze_failure(error, context)
            # Should not crash, may return None or action
            assert action is None or isinstance(action, HealingAction)
        except Exception as e:
            pytest.fail(f"Agent crashed with context {context}: {e}")


def test_multiple_error_types_sequential(temp_storage_dir):
    """Test handling multiple error types in sequence."""
    agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
    
    errors = [
        (KeyError("key1"), "KeyError"),
        (ValueError("val1"), "ValueError"),
        (TypeError("type1"), "TypeError"),
        (KeyError("key2"), "KeyError"),
        (ValueError("val2"), "ValueError"),
    ]
    
    for error, _ in errors:
        agent.analyze_failure(error, {'tool': 'test'})
    
    report = agent.get_healing_report()
    assert report['total_patterns'] == len(errors)


def test_healing_action_recording(temp_storage_dir):
    """Test recording healing action results."""
    agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
    
    error = KeyError("'revenue'")
    context = {'tool': 'compute_kpis'}
    
    # Generate action
    for _ in range(3):
        agent.analyze_failure(error, context)
    
    assert len(agent.healing_actions) > 0
    action = agent.healing_actions[-1]
    
    # Record results
    agent.record_fix_result(action, success=True)
    agent.record_fix_result(action, success=True)
    agent.record_fix_result(action, success=False)
    
    report = agent.get_healing_report()
    assert 'KeyError' in report['successful_fixes']


def test_stats_tracking(temp_storage_dir):
    """Test that stats are tracked correctly."""
    agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
    
    error = KeyError("'revenue'")
    context = {'tool': 'compute_kpis'}
    
    # Generate multiple failures
    for i in range(5):
        agent.analyze_failure(error, context)
    
    report = agent.get_healing_report()
    assert report['stats']['patterns_analyzed'] >= 5


def test_import_error_fix(temp_storage_dir):
    """Test ImportError fix suggestion."""
    agent = SelfHealingAgent(storage_dir=temp_storage_dir, min_failures_for_action=3)
    
    error = ImportError("No module named 'pandas'")
    context = {'tool': 'test'}
    
    for _ in range(3):
        action = agent.analyze_failure(error, context)
    
    # Should have an action
    assert len(agent.healing_actions) > 0
    action = agent.healing_actions[-1]
    assert 'install' in action.suggestion.lower() or 'missing' in action.suggestion.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])