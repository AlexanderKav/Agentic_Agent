"""
Self-healing agent that learns from failures and suggests fixes.
Provides automated error pattern recognition and healing suggestions.
"""

import json
import logging
import os
import threading
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """Represents a detected failure pattern."""
    error_type: str
    error_message: str
    tool: Optional[str]
    data_shape: Optional[Tuple[int, int]]
    timestamp: float
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if self.data_shape:
            data['data_shape'] = list(self.data_shape)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailurePattern':
        """Create from dictionary."""
        if 'data_shape' in data and isinstance(data['data_shape'], list):
            data['data_shape'] = tuple(data['data_shape'])
        return cls(**data)


@dataclass
class HealingAction:
    """Represents a suggested healing action."""
    pattern_id: str
    suggestion: str
    confidence: float
    auto_apply: bool
    fixed: bool = False
    applied_at: Optional[float] = None
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class SelfHealingAgent:
    """
    Agent that learns from failures and suggests/prevents fixes.
    
    Features:
    - Pattern recognition for recurring failures
    - Template-based fix suggestions
    - Confidence scoring based on frequency and history
    - Auto-apply for high-confidence fixes
    - Persistence of failure patterns
    """
    
    def __init__(
        self,
        storage_dir: str = "data/healing/",
        min_failures_for_action: int = 3,
        pattern_window_hours: int = 24,
        auto_apply_threshold: float = 0.85
    ):
        """
        Initialize the Self-Healing Agent.
        
        Args:
            storage_dir: Directory to store failure patterns
            min_failures_for_action: Minimum failures before generating action
            pattern_window_hours: Time window for pattern detection
            auto_apply_threshold: Confidence threshold for auto-apply
        """
        self.storage_dir = storage_dir
        self.min_failures_for_action = min_failures_for_action
        self.pattern_window_hours = pattern_window_hours
        self.auto_apply_threshold = auto_apply_threshold
        
        os.makedirs(storage_dir, exist_ok=True)
        
        self.lock = threading.RLock()
        self.failure_patterns: List[FailurePattern] = []
        self.healing_actions: List[HealingAction] = []
        self.successful_fixes: Dict[str, int] = defaultdict(int)
        self.failed_fixes: Dict[str, int] = defaultdict(int)
        
        # Known fix templates
        self.fix_templates: Dict[str, callable] = {
            'KeyError': self._fix_key_error,
            'ValueError': self._fix_value_error,
            'TypeError': self._fix_type_error,
            'AttributeError': self._fix_attribute_error,
            'IndexError': self._fix_index_error,
            'ZeroDivisionError': self._fix_zero_division,
            'FileNotFoundError': self._fix_file_not_found,
            'PermissionError': self._fix_permission_error,
            'ImportError': self._fix_import_error,
            'MemoryError': self._fix_memory_error,
            'TimeoutError': self._fix_timeout_error,
            'ConnectionError': self._fix_connection_error,
        }
        
        # Track statistics
        self._stats = {
            'patterns_analyzed': 0,
            'actions_generated': 0,
            'auto_applied': 0,
            'manual_applied': 0,
            'start_time': datetime.now()
        }
        
        # Load historical patterns
        self._load_patterns()
        
        logger.info(f"SelfHealingAgent initialized with {len(self.failure_patterns)} historical patterns")
    
    def analyze_failure(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[HealingAction]:
        """
        Analyze a failure and suggest a fix.
        
        Args:
            error: The exception that occurred
            context: Additional context about the failure
            
        Returns:
            HealingAction if a fix is suggested, None otherwise
        """
        if context is None:
            context = {}
        
        # Create failure pattern
        pattern = FailurePattern(
            error_type=type(error).__name__,
            error_message=str(error),
            tool=context.get('tool'),
            data_shape=context.get('data_shape'),
            timestamp=time.time(),
            context=context
        )
        
        with self.lock:
            self.failure_patterns.append(pattern)
            self._stats['patterns_analyzed'] += 1
        
        # Save pattern for persistence
        self._save_pattern(pattern)
        
        # Find similar patterns
        similar = self._find_similar_patterns(pattern)
        similar_count = len(similar)
        
        logger.debug(f"Analyzed failure: {pattern.error_type} | Similar patterns: {similar_count}")
        
        # Only generate fix after minimum failures
        if similar_count >= self.min_failures_for_action:
            healing_action = self._generate_fix(pattern, similar_count)
            if healing_action:
                logger.info(f"Generated healing action for {pattern.error_type} with confidence {healing_action.confidence}")
                return healing_action
        
        return None
    
    def _find_similar_patterns(
        self,
        pattern: FailurePattern,
        hours: Optional[int] = None
    ) -> List[FailurePattern]:
        """Find similar patterns from last N hours."""
        if hours is None:
            hours = self.pattern_window_hours
        
        cutoff = time.time() - (hours * 3600)
        
        similar = []
        for p in self.failure_patterns:
            if p.timestamp < cutoff:
                continue
            
            # Match on error type, tool, and error message similarity
            if p.error_type == pattern.error_type and p.tool == pattern.tool:
                # Check if error messages are similar (first 100 chars)
                if p.error_message[:100] == pattern.error_message[:100]:
                    similar.append(p)
        
        return similar
    
    def _generate_fix(
        self,
        pattern: FailurePattern,
        similar_count: int
    ) -> Optional[HealingAction]:
        """Generate a healing action for a pattern."""
        
        # Check if we have a template fix
        if pattern.error_type in self.fix_templates:
            suggestion = self.fix_templates[pattern.error_type](pattern)
            
            # Calculate confidence based on frequency and historical success
            base_confidence = min(
                0.3 + (similar_count - self.min_failures_for_action) * 0.1,
                0.9
            )
            
            # Adjust based on historical success rate
            success_rate = self._get_success_rate(pattern.error_type)
            confidence = min(base_confidence + (success_rate * 0.15), 0.95)
            confidence = round(confidence, 2)
            
            # Determine if auto-apply
            auto_apply = confidence >= self.auto_apply_threshold and similar_count > 5
            
            pattern_id = f"{pattern.error_type}_{int(time.time())}_{pattern.tool or 'unknown'}"
            
            healing_action = HealingAction(
                pattern_id=pattern_id,
                suggestion=suggestion,
                confidence=confidence,
                auto_apply=auto_apply,
                applied_at=time.time() if auto_apply else None
            )
            
            with self.lock:
                self.healing_actions.append(healing_action)
                self._stats['actions_generated'] += 1
                if auto_apply:
                    self._stats['auto_applied'] += 1
            
            return healing_action
        
        return None
    
    def _get_success_rate(self, error_type: str) -> float:
        """Get historical success rate for fixing this error type."""
        successful = self.successful_fixes.get(error_type, 0)
        failed = self.failed_fixes.get(error_type, 0)
        total = successful + failed
        
        if total == 0:
            return 0.0
        
        return successful / total
    
    def record_fix_result(self, healing_action: HealingAction, success: bool) -> None:
        """
        Record whether a healing action was successful.
        
        Args:
            healing_action: The healing action that was applied
            success: Whether the fix was successful
        """
        error_type = healing_action.pattern_id.split('_')[0]
        
        with self.lock:
            if success:
                self.successful_fixes[error_type] += 1
                healing_action.fixed = True
                healing_action.resolved_at = time.time()
                logger.info(f"Fix successful for {error_type}")
            else:
                self.failed_fixes[error_type] += 1
                logger.warning(f"Fix failed for {error_type}: {healing_action.suggestion[:100]}")
    
    # ==================== Fix Templates ====================
    
    def _fix_key_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for KeyError."""
        missing_key = pattern.error_message.split("'")[1] if "'" in pattern.error_message else "unknown"
        
        # Check if we have dataframe columns in context
        if pattern.context and 'available_columns' in pattern.context:
            available = pattern.context['available_columns']
            if available and len(available) <= 10:
                return f"Column '{missing_key}' not found. Available columns: {', '.join(available)}. Check column name spelling."
            elif available:
                return f"Column '{missing_key}' not found. Available columns (first 10): {', '.join(available[:10])}..."
        
        return f"Check if column '{missing_key}' exists. Use df.columns to list available columns."
    
    def _fix_value_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for ValueError."""
        msg = pattern.error_message.lower()
        
        if "date" in msg or "datetime" in msg:
            return "Invalid date format. Use pd.to_datetime() with errors='coerce' to handle invalid dates."
        elif "numeric" in msg or "float" in msg or "int" in msg:
            return "Invalid numeric value. Use pd.to_numeric() with errors='coerce' to convert or handle non-numeric values."
        
        return "Validate input data types and formats. Use try/except to handle expected edge cases."
    
    def _fix_type_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for TypeError."""
        msg = pattern.error_message.lower()
        
        if "NoneType" in msg:
            return "Encountered None value. Add null checks before processing. Use .fillna() or handle None cases."
        
        return "Check data types. Use pd.to_numeric() for numbers, astype() for type conversion, or verify input types."
    
    def _fix_attribute_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for AttributeError."""
        missing_attr = pattern.error_message.split("'")[1] if "'" in pattern.error_message else "unknown"
        
        if pattern.context and 'object_type' in pattern.context:
            return f"'{missing_attr}' not found on {pattern.context['object_type']}. Check available attributes with dir(object)."
        
        return f"Check if object has '{missing_attr}' attribute. Verify data structure and object type."
    
    def _fix_index_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for IndexError."""
        return "List/array index out of range. Check length before accessing by index, or use slicing with bounds checking."
    
    def _fix_zero_division(self, pattern: FailurePattern) -> str:
        """Suggest fix for ZeroDivisionError."""
        return "Division by zero detected. Add check for zero denominator: if denominator == 0: return 0 or handle appropriately."
    
    def _fix_file_not_found(self, pattern: FailurePattern) -> str:
        """Suggest fix for FileNotFoundError."""
        return "File not found. Verify file path exists, check working directory with os.getcwd(), and ensure file permissions."
    
    def _fix_permission_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for PermissionError."""
        return "Permission denied. Check file/directory permissions, close any open handles, or run with appropriate privileges."
    
    def _fix_import_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for ImportError."""
        missing_module = pattern.error_message.split("'")[1] if "'" in pattern.error_message else "unknown"
        return f"Missing module '{missing_module}'. Install with: pip install {missing_module}"
    
    def _fix_memory_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for MemoryError."""
        return "Out of memory. Consider processing data in chunks, using more efficient data types, or increasing available memory."
    
    def _fix_timeout_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for TimeoutError."""
        return "Operation timed out. Consider increasing timeout, optimizing the operation, or implementing retry logic."
    
    def _fix_connection_error(self, pattern: FailurePattern) -> str:
        """Suggest fix for ConnectionError."""
        return "Connection error. Check network connectivity, verify service is running, and implement retry with backoff."
    
    # ==================== Persistence ====================
    
    def _save_pattern(self, pattern: FailurePattern) -> None:
        """Save failure pattern to disk."""
        today = datetime.now().date().isoformat()
        filepath = os.path.join(self.storage_dir, f"patterns_{today}.jsonl")
        
        try:
            with open(filepath, 'a') as f:
                f.write(json.dumps(pattern.to_dict(), default=str) + '\n')
        except Exception as e:
            logger.error(f"Failed to save pattern: {e}")
    
    def _load_patterns(self, days: int = 30) -> None:
        """Load failure patterns from last N days."""
        loaded = 0
        for i in range(days):
            day = (datetime.now().date() - timedelta(days=i)).isoformat()
            filepath = os.path.join(self.storage_dir, f"patterns_{day}.jsonl")
            
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                pattern = FailurePattern.from_dict(data)
                                self.failure_patterns.append(pattern)
                                loaded += 1
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning(f"Error loading patterns from {filepath}: {e}")
        
        logger.info(f"Loaded {loaded} historical failure patterns")
    
    # ==================== Reporting ====================
    
    def get_healing_report(self) -> Dict[str, Any]:
        """Generate report on healing actions."""
        with self.lock:
            total_actions = len(self.healing_actions)
            auto_applied = sum(1 for a in self.healing_actions if a.auto_apply)
            resolved = sum(1 for a in self.healing_actions if a.fixed)
            
            return {
                'total_patterns': len(self.failure_patterns),
                'total_actions': total_actions,
                'auto_applied': auto_applied,
                'manual_applied': total_actions - auto_applied,
                'resolved': resolved,
                'success_rate': resolved / total_actions if total_actions > 0 else 0,
                'successful_fixes': dict(self.successful_fixes),
                'failed_fixes': dict(self.failed_fixes),
                'recent_patterns': [
                    p.to_dict() for p in self.failure_patterns[-10:]
                ],
                'pending_actions': [
                    a.to_dict() for a in self.healing_actions
                    if not a.fixed
                ],
                'stats': self._stats.copy()
            }
    
    def get_pattern_summary(self) -> Dict[str, int]:
        """Get summary of failure patterns by type."""
        pattern_counts = Counter()
        for p in self.failure_patterns:
            pattern_counts[p.error_type] += 1
        
        return dict(pattern_counts.most_common(20))
    
    def get_most_common_errors(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most common error types."""
        error_counts = Counter(p.error_type for p in self.failure_patterns)
        return error_counts.most_common(limit)
    
    def clear_old_patterns(self, days: int = 90) -> int:
        """Clear failure patterns older than specified days."""
        cutoff = time.time() - (days * 24 * 3600)
        with self.lock:
            original_count = len(self.failure_patterns)
            self.failure_patterns = [p for p in self.failure_patterns if p.timestamp >= cutoff]
            removed = original_count - len(self.failure_patterns)
        
        logger.info(f"Cleared {removed} old failure patterns (older than {days} days)")
        return removed


# Singleton instance
_healing_agent = None


def get_healing_agent() -> SelfHealingAgent:
    """Get or create the global healing agent instance."""
    global _healing_agent
    if _healing_agent is None:
        _healing_agent = SelfHealingAgent()
    return _healing_agent


__all__ = ['SelfHealingAgent', 'FailurePattern', 'HealingAction', 'get_healing_agent']