"""
Audit logging for compliance and accountability.
Provides tamper-proof logging with HMAC hash chaining.
"""

import hashlib
import hmac
import json
import logging
import math
import os
import threading
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Secure audit logging for all agent actions.
    
    Features:
    - Tamper-proof HMAC hash chaining
    - Automatic sanitization of sensitive data
    - Daily log file rotation
    - Query interface with filters
    - Thread-safe operations
    - Chain integrity verification
    """
    
    def __init__(self, log_dir: str = "logs/audit/", secret_key: Optional[str] = None):
        """
        Initialize the Audit Logger.
        
        Args:
            log_dir: Directory to store audit logs
            secret_key: Secret key for HMAC hashing (defaults to env var)
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.secret_key = secret_key or os.environ.get('AUDIT_SECRET_KEY', 'dev-key')
        self.lock = threading.Lock()
        
        # Track statistics
        self._total_entries = 0
        self._failed_entries = 0
        
        logger.info(f"AuditLogger initialized with log directory: {log_dir}")
    
    def _convert_to_native(self, obj: Any) -> Any:
        """Convert numpy/pandas types to Python native types for JSON serialization."""
        if obj is None:
            return None
        
        # Handle numpy integers
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        
        # Handle numpy floats
        if isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return float(obj)
        
        # Handle numpy booleans
        if isinstance(obj, np.bool_):
            return bool(obj)
        
        # Handle pandas Timestamp
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return obj.isoformat()
        
        # Handle datetime
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # Handle numpy arrays
        if isinstance(obj, np.ndarray):
            return [self._convert_to_native(item) for item in obj.tolist()]
        
        # Handle pandas Series
        if isinstance(obj, pd.Series):
            return self._convert_to_native(obj.to_dict())
        
        # Handle pandas DataFrame
        if isinstance(obj, pd.DataFrame):
            return self._convert_to_native(obj.to_dict('records'))
        
        # Handle dictionaries recursively
        if isinstance(obj, dict):
            return {self._convert_to_native(k): self._convert_to_native(v) for k, v in obj.items()}
        
        # Handle lists/tuples
        if isinstance(obj, (list, tuple)):
            return [self._convert_to_native(item) for item in obj]
        
        return obj
    
    def _create_hash(self, data: str) -> str:
        """Create HMAC hash for tamper-proof logging."""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def log_action(
        self,
        action_type: str,
        agent: str,
        details: Dict[str, Any],
        user: str = "system",
        session_id: Optional[str] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Log an action with tamper-proof hash.
        
        Args:
            action_type: Type of action (e.g., 'run_start', 'compute_kpis')
            agent: Name of the agent performing the action
            details: Dictionary of action details
            user: User identifier
            session_id: Optional session ID for tracking
            success: Whether the action was successful
            
        Returns:
            The created log entry
        """
        # First sanitize and convert details to JSON-serializable types
        sanitized_details = self._sanitize_details(details)
        converted_details = self._convert_to_native(sanitized_details)
        
        # Prepare log entry (without hash first)
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action_type': action_type,
            'agent': agent,
            'user': user,
            'session_id': session_id,
            'success': success,
            'details': converted_details
        }
        
        # Get previous hash
        prev_hash = self._get_last_hash()
        entry['prev_hash'] = prev_hash
        
        # Create a copy for hashing
        entry_for_hash = self._convert_to_native(entry)
        
        # Create hash of current entry
        try:
            entry_string = json.dumps(entry_for_hash, sort_keys=True, default=str)
            entry['hash'] = self._create_hash(entry_string)
            self._total_entries += 1
        except Exception as e:
            logger.warning(f"Audit hash creation error: {e}")
            self._failed_entries += 1
            # Fallback: create a simpler entry
            entry['hash'] = self._create_hash(str(entry_for_hash))
        
        # Write to log
        self._write_entry(entry)
        
        return entry
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from logs.
        
        Args:
            details: Dictionary of details to sanitize
            
        Returns:
            Sanitized dictionary
        """
        sensitive_keys = [
            'password', 'token', 'api_key', 'secret', 'key',
            'authorization', 'auth', 'credential', 'private'
        ]
        
        sanitized = {}
        
        for key, value in details.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_last_hash(self) -> str:
        """Get hash of last log entry for chain integrity."""
        today = date.today().isoformat()
        log_file = os.path.join(self.log_dir, f"audit_{today}.jsonl")
        
        if not os.path.exists(log_file):
            return "0" * 64
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return "0" * 64
                
                last_entry = json.loads(lines[-1])
                return last_entry.get('hash', "0" * 64)
        except Exception as e:
            logger.warning(f"Error reading last hash: {e}")
            return "0" * 64
    
    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write entry to daily log file."""
        today = date.today().isoformat()
        log_file = os.path.join(self.log_dir, f"audit_{today}.jsonl")
        
        # Ensure all values are serializable
        serializable_entry = self._convert_to_native(entry)
        
        with self.lock:
            try:
                with open(log_file, 'a') as f:
                    f.write(json.dumps(serializable_entry, default=str) + '\n')
            except Exception as e:
                logger.error(f"Failed to write audit entry: {e}")
                # Last resort: write minimal info
                fallback_entry = {
                    'timestamp': entry.get('timestamp', datetime.utcnow().isoformat()),
                    'action_type': entry.get('action_type', 'unknown'),
                    'agent': entry.get('agent', 'unknown'),
                    'user': entry.get('user', 'system'),
                    'success': entry.get('success', False),
                    'details': {'error': str(e), 'original_error': str(entry.get('details', {}))[:200]}
                }
                try:
                    with open(log_file, 'a') as f:
                        f.write(json.dumps(fallback_entry, default=str) + '\n')
                except Exception:
                    logger.critical("Unable to write audit entry even to fallback")
    
    def query_audit(
        self,
        user: Optional[str] = None,
        agent: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        success: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.
        
        Args:
            user: Filter by user
            agent: Filter by agent name
            action_type: Filter by action type
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            success: Filter by success status
            limit: Maximum number of entries to return
            
        Returns:
            List of matching audit entries
        """
        results = []
        
        # Determine date range
        if start_date is None:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        if end_date is None:
            end_date = date.today().isoformat()
        
        # Parse dates
        try:
            current = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            return []
        
        # Iterate through daily logs
        while current <= end:
            log_file = os.path.join(self.log_dir, f"audit_{current.isoformat()}.jsonl")
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if limit and len(results) >= limit:
                                break
                            
                            try:
                                entry = json.loads(line)
                                
                                # Apply filters
                                if user and entry.get('user') != user:
                                    continue
                                if agent and entry.get('agent') != agent:
                                    continue
                                if action_type and entry.get('action_type') != action_type:
                                    continue
                                if success is not None and entry.get('success') != success:
                                    continue
                                
                                results.append(entry)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse line in {log_file}")
                                continue
                except Exception as e:
                    logger.warning(f"Error reading {log_file}: {e}")
            
            current += timedelta(days=1)
        
        return results
    
    def verify_chain_integrity(self, date_str: Optional[str] = None) -> bool:
        """
        Verify the hash chain integrity for a given date.
        
        Args:
            date_str: Date to verify (YYYY-MM-DD), defaults to today
            
        Returns:
            True if chain is intact, False otherwise
        """
        if date_str is None:
            date_str = date.today().isoformat()
        
        log_file = os.path.join(self.log_dir, f"audit_{date_str}.jsonl")
        
        if not os.path.exists(log_file):
            logger.info(f"No audit log found for {date_str}")
            return True
        
        prev_hash = "0" * 64
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
                for line_num, line in enumerate(lines):
                    try:
                        entry = json.loads(line)
                        
                        # Get stored values
                        stored_hash = entry.get('hash', '')
                        stored_prev_hash = entry.get('prev_hash', '')
                        
                        # Check chain link
                        if stored_prev_hash != prev_hash:
                            logger.error(f"Chain break at line {line_num + 1}: prev_hash mismatch")
                            logger.error(f"  Expected: {prev_hash}")
                            logger.error(f"  Got: {stored_prev_hash}")
                            return False
                        
                        # Create a copy without the hash for verification
                        entry_copy = entry.copy()
                        entry_copy.pop('hash', None)
                        
                        # Recalculate hash
                        entry_string = json.dumps(entry_copy, sort_keys=True, default=str)
                        calculated_hash = self._create_hash(entry_string)
                        
                        # Verify hash
                        if calculated_hash != stored_hash:
                            logger.error(f"Hash mismatch at line {line_num + 1}")
                            logger.error(f"  Expected: {calculated_hash}")
                            logger.error(f"  Got: {stored_hash}")
                            return False
                        
                        prev_hash = stored_hash
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing line {line_num + 1}: {e}")
                        return False
                    except Exception as e:
                        logger.error(f"Unexpected error at line {line_num + 1}: {e}")
                        return False
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return False
        
        logger.info(f"Chain integrity verified for {date_str} ({len(lines)} entries)")
        return True
    
    def verify_all_chains(self, days: int = 30) -> Dict[str, bool]:
        """
        Verify hash chain integrity for recent days.
        
        Args:
            days: Number of days to check
            
        Returns:
            Dictionary mapping date to integrity status
        """
        results = {}
        current = date.today()
        
        for i in range(days):
            check_date = current - timedelta(days=i)
            date_str = check_date.isoformat()
            results[date_str] = self.verify_chain_integrity(date_str)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about audit logging.
        
        Returns:
            Dictionary with audit statistics
        """
        return {
            'total_entries': self._total_entries,
            'failed_entries': self._failed_entries,
            'log_directory': self.log_dir,
            'success_rate': (self._total_entries - self._failed_entries) / max(self._total_entries, 1) * 100
        }
    
    def get_daily_counts(self, days: int = 7) -> Dict[str, int]:
        """
        Get count of entries per day for recent days.
        
        Args:
            days: Number of days to check
            
        Returns:
            Dictionary mapping date to entry count
        """
        counts = {}
        current = date.today()
        
        for i in range(days):
            check_date = current - timedelta(days=i)
            date_str = check_date.isoformat()
            log_file = os.path.join(self.log_dir, f"audit_{date_str}.jsonl")
            
            count = 0
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        count = sum(1 for _ in f)
                except Exception:
                    pass
            
            counts[date_str] = count
        
        return counts


# Singleton instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


__all__ = ['AuditLogger', 'get_audit_logger']