"""
Track LLM API costs across agents.
Provides real-time cost tracking and reporting for all LLM calls.
"""

import json
import logging
import os
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Track LLM API usage and costs across all agents.
    
    Features:
    - Real-time cost tracking per model
    - Daily log file rotation
    - Agent and user cost aggregation
    - Cost reports by day, agent, user
    - Thread-safe operations
    - Support for multiple pricing models
    """
    
    # Model pricing (per 1K tokens in USD)
    DEFAULT_MODEL_COSTS: Dict[str, Dict[str, float]] = {
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
        'gpt-4o': {'input': 0.005, 'output': 0.015},
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'o1-mini': {'input': 0.003, 'output': 0.012},
        'o1-preview': {'input': 0.015, 'output': 0.06},
        'claude-3-opus': {'input': 0.015, 'output': 0.075},
        'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
        'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
        'gemini-pro': {'input': 0.0005, 'output': 0.0015},
    }
    
    def __init__(self, log_dir: str = "logs/costs/"):
        """
        Initialize the Cost Tracker.
        
        Args:
            log_dir: Directory to store cost logs
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.model_costs = self.DEFAULT_MODEL_COSTS.copy()
        
        # Thread-safe storage
        self.lock = threading.Lock()
        self.session_costs: List[Dict] = []
        self.agent_costs = defaultdict(float)
        self.user_costs = defaultdict(float)
        self.model_usage = defaultdict(lambda: {'calls': 0, 'tokens': 0, 'cost': 0.0})
        
        # Statistics
        self._total_calls = 0
        self._start_time = datetime.now()
        
        logger.info(f"CostTracker initialized with log directory: {log_dir}")
    
    def track_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent: str,
        user: str = "system",
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> float:
        """
        Track an LLM API call and calculate cost.
        
        Args:
            model: Model name (e.g., 'gpt-4o-mini')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            agent: Agent making the call
            user: User identifier
            session_id: Optional session ID
            metadata: Optional additional metadata
            
        Returns:
            Total cost in USD
        """
        # Get model pricing (fallback to default)
        model_key = model
        if model not in self.model_costs:
            logger.warning(f"Unknown model: {model}, using gpt-4o-mini pricing")
            model_key = 'gpt-4o-mini'
        
        pricing = self.model_costs[model_key]
        input_cost = (input_tokens * pricing['input'] / 1000)
        output_cost = (output_tokens * pricing['output'] / 1000)
        total_cost = input_cost + output_cost
        
        call_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'agent': agent,
            'user': user,
            'session_id': session_id,
            'metadata': metadata or {}
        }
        
        with self.lock:
            self.session_costs.append(call_record)
            self.agent_costs[agent] += total_cost
            self.user_costs[user] += total_cost
            self._total_calls += 1
            
            # Track model usage
            usage = self.model_usage[model]
            usage['calls'] += 1
            usage['tokens'] += input_tokens + output_tokens
            usage['cost'] += total_cost
        
        # Append to daily log file
        self._append_to_log(call_record)
        
        # Log for debugging
        logger.debug(f"Cost tracked: {agent} | {model} | ${total_cost:.6f} | {input_tokens}/{output_tokens} tokens")
        
        return total_cost
    
    def track_call_with_estimation(
        self,
        model: str,
        input_text: str,
        output_text: str,
        agent: str,
        user: str = "system",
        session_id: Optional[str] = None
    ) -> float:
        """
        Track an LLM call using text content to estimate tokens.
        
        Args:
            model: Model name
            input_text: Input text content
            output_text: Output text content
            agent: Agent making the call
            user: User identifier
            session_id: Optional session ID
            
        Returns:
            Estimated total cost in USD
        """
        # Rough token estimation (4 chars per token)
        input_tokens = len(input_text) // 4
        output_tokens = len(output_text) // 4
        
        return self.track_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            agent=agent,
            user=user,
            session_id=session_id,
            metadata={'estimation_method': 'character_based'}
        )
    
    def _append_to_log(self, record: Dict) -> None:
        """Append cost record to daily log file."""
        today = date.today().isoformat()
        log_file = os.path.join(self.log_dir, f"costs_{today}.jsonl")
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(record, default=str) + '\n')
        except Exception as e:
            logger.error(f"Failed to write cost record: {e}")
    
    def get_session_cost(self) -> float:
        """Get total cost for current session."""
        with self.lock:
            return round(sum(c['total_cost'] for c in self.session_costs), 4)
    
    def get_session_call_count(self) -> int:
        """Get number of API calls in current session."""
        with self.lock:
            return len(self.session_costs)
    
    def get_agent_cost(self, agent: str) -> float:
        """Get total cost for a specific agent."""
        with self.lock:
            return round(self.agent_costs.get(agent, 0.0), 4)
    
    def get_user_cost(self, user: str) -> float:
        """Get total cost for a specific user."""
        with self.lock:
            return round(self.user_costs.get(user, 0.0), 4)
    
    def get_model_usage(self, model: Optional[str] = None) -> Dict:
        """
        Get usage statistics for models.
        
        Args:
            model: Specific model name (None for all)
            
        Returns:
            Dictionary with usage statistics
        """
        with self.lock:
            if model:
                usage = self.model_usage.get(model, {'calls': 0, 'tokens': 0, 'cost': 0.0})
                return dict(usage)
            return {m: dict(usage) for m, usage in self.model_usage.items()}
    
    def get_daily_cost(self, target_date: Optional[str] = None) -> float:
        """
        Get total cost for a specific date.
        
        Args:
            target_date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Total cost in USD
        """
        if target_date is None:
            target_date = date.today().isoformat()
        
        log_file = os.path.join(self.log_dir, f"costs_{target_date}.jsonl")
        
        if not os.path.exists(log_file):
            return 0.0
        
        total = 0.0
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        total += record.get('total_cost', 0.0)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading cost log: {e}")
        
        return round(total, 4)
    
    def get_daily_call_count(self, target_date: Optional[str] = None) -> int:
        """Get number of API calls for a specific date."""
        if target_date is None:
            target_date = date.today().isoformat()
        
        log_file = os.path.join(self.log_dir, f"costs_{target_date}.jsonl")
        
        if not os.path.exists(log_file):
            return 0
        
        count = 0
        try:
            with open(log_file, 'r') as f:
                count = sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error reading cost log: {e}")
        
        return count
    
    def get_cost_report(self, days: int = 7) -> Dict:
        """Generate cost report for last N days."""
        # Cap days to prevent excessive loops
        days = min(days, 30)
        
        report = {
            'period_days': days,
            'start_date': (date.today() - timedelta(days=days)).isoformat(),
            'end_date': date.today().isoformat(),
            'total': 0.0,
            'total_calls': 0,
            'by_agent': {},
            'by_user': {},
            'by_model': {},
            'daily': {},
            'session': {}
        }
        
        # Collect daily costs with timeout protection
        for i in range(days):
            day = (date.today() - timedelta(days=i)).isoformat()
            try:
                daily_total = self.get_daily_cost(day)
                daily_calls = self.get_daily_call_count(day)
                report['daily'][day] = {
                    'cost': daily_total,
                    'calls': daily_calls
                }
                report['total'] += daily_total
                report['total_calls'] += daily_calls
            except Exception as e:
                logger.warning(f"Error getting cost for {day}: {e}")
                continue
        
        report['total'] = round(report['total'], 4)
        
        # Add session data (copy to avoid modification during iteration)
        with self.lock:
            report['by_agent'] = {agent: round(cost, 4) for agent, cost in dict(self.agent_costs).items()}
            report['by_user'] = {user: round(cost, 4) for user, cost in dict(self.user_costs).items()}
            report['by_model'] = {model: round(data.get('cost', 0), 4) for model, data in dict(self.model_usage).items()}
            report['session'] = {
                'cost': self.get_session_cost(),
                'calls': self.get_session_call_count(),
                'start_time': self._start_time.isoformat(),
                'duration_seconds': round((datetime.now() - self._start_time).total_seconds(), 2)
            }
        
        return report
        
    def get_agent_ranking(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Get top N agents by cost.
        
        Args:
            top_n: Number of agents to return
            
        Returns:
            List of (agent_name, cost) tuples sorted by cost descending
        """
        with self.lock:
            sorted_agents = sorted(self.agent_costs.items(), key=lambda x: x[1], reverse=True)
            return [(agent, round(cost, 4)) for agent, cost in sorted_agents[:top_n]]
    
    def get_user_ranking(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Get top N users by cost.
        
        Args:
            top_n: Number of users to return
            
        Returns:
            List of (user_name, cost) tuples sorted by cost descending
        """
        with self.lock:
            sorted_users = sorted(self.user_costs.items(), key=lambda x: x[1], reverse=True)
            return [(user, round(cost, 4)) for user, cost in sorted_users[:top_n]]
    
    def reset_session(self) -> None:
        """Reset session costs (for testing)."""
        with self.lock:
            self.session_costs = []
            self.agent_costs.clear()
            self.user_costs.clear()
            self.model_usage.clear()
            self._total_calls = 0
            self._start_time = datetime.now()
        
        logger.info("Session costs reset")
    
    def get_stats(self) -> Dict:
        """Get overall statistics."""
        with self.lock:
            return {
                'total_calls': self._total_calls,
                'session_calls': len(self.session_costs),
                'session_cost': self.get_session_cost(),
                'active_agents': len(self.agent_costs),
                'active_users': len(self.user_costs),
                'models_used': list(self.model_usage.keys()),
                'start_time': self._start_time.isoformat(),
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds()
            }
    
    def add_custom_model(self, model_name: str, input_cost: float, output_cost: float) -> None:
        """
        Add a custom model pricing.
        
        Args:
            model_name: Name of the model
            input_cost: Cost per 1K input tokens
            output_cost: Cost per 1K output tokens
        """
        self.model_costs[model_name] = {'input': input_cost, 'output': output_cost}
        logger.info(f"Added custom model: {model_name} (${input_cost}/1K in, ${output_cost}/1K out)")


# Singleton instance for global use
_cost_tracker = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


__all__ = ['CostTracker', 'get_cost_tracker']