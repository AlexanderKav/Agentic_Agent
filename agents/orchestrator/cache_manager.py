# agents/orchestrator/cache_manager.py
"""
Cache Manager - Stores tool results to avoid redundant computation.
Single responsibility: Manage the analytics cache.
"""

import hashlib
import json
from typing import Any, Callable, Dict, Optional


class CacheManager:
    """
    Manages caching of tool results.
    Supports simple key-based caching and can be extended to Redis.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._hits = 0
        self._misses = 0
    
    def get_or_execute(
        self, 
        tool_name: str, 
        executor: Callable, 
        params: Optional[Dict] = None
    ) -> Any:
        """
        Get result from cache or execute and store.
        
        Args:
            tool_name: Name of the tool being called
            executor: Function to execute if cache miss
            params: Optional parameters for the tool
            
        Returns:
            The cached or computed result
        """
        key = self._generate_key(tool_name, params)
        
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        
        self._misses += 1
        result = executor()
        self._cache[key] = result
        return result
    
    def _generate_key(self, tool_name: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from tool and parameters"""
        key = tool_name
        if params:
            key += json.dumps(params, sort_keys=True)
        return hashlib.md5(key.encode()).hexdigest()
    
    def invalidate(self, tool_name: Optional[str] = None):
        """
        Invalidate cache.
        
        Args:
            tool_name: If provided, only invalidate keys for this tool
        """
        if tool_name:
            # Invalidate all keys containing the tool name
            self._cache = {
                k: v for k, v in self._cache.items()
                if not k.startswith(hashlib.md5(tool_name.encode()).hexdigest())
            }
        else:
            self._cache.clear()
    
    def clear(self):
        """Clear all cached results"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache hit/miss statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'total': total,
            'hit_rate_percent': round(hit_rate, 1)
        }