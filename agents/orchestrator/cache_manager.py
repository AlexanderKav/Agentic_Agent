"""
Cache Manager - Stores tool results to avoid redundant computation.
Single responsibility: Manage the analytics cache.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class CacheEntry:
    """
    Cache entry with metadata for TTL and tracking.
    """
    
    def __init__(self, value: Any, ttl_seconds: Optional[int] = None):
        """
        Initialize a cache entry.
        
        Args:
            value: The cached value
            ttl_seconds: Time-to-live in seconds (None = no expiration)
        """
        self.value: Any = value
        self.created_at: datetime = datetime.now()
        self.last_accessed: datetime = datetime.now()
        self.access_count: int = 0
        self.ttl_seconds: Optional[int] = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
            'ttl_seconds': self.ttl_seconds
        }


class CacheManager:
    """
    Manages caching of tool results.
    Supports simple key-based caching and can be extended to Redis.
    
    Features:
    - TTL (Time-to-Live) for automatic expiration
    - Cache statistics (hits/misses/hit rate)
    - Selective invalidation by tool or pattern
    - LRU-style cleanup when cache gets too large
    """
    
    DEFAULT_MAX_SIZE = 1000
    
    def __init__(self, max_size: int = DEFAULT_MAX_SIZE):
        """
        Initialize the cache manager.
        
        Args:
            max_size: Maximum number of entries in the cache
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._max_size: int = max_size
    
    def get_or_execute(
        self, 
        tool_name: str, 
        executor: Callable, 
        params: Optional[Dict] = None,
        ttl_seconds: Optional[int] = None,
        force_refresh: bool = False
    ) -> Any:
        """
        Get result from cache or execute and store.
        
        Args:
            tool_name: Name of the tool being called
            executor: Function to execute if cache miss
            params: Optional parameters for the tool
            ttl_seconds: Time-to-live for cached result (None = no expiration)
            force_refresh: If True, bypass cache and execute fresh
            
        Returns:
            The cached or computed result
        """
        key = self._generate_key(tool_name, params)
        
        # Check if we should force refresh
        if force_refresh:
            self._invalidate_key(key)
        
        # Try to get from cache
        entry = self._get(key)
        if entry is not None and not entry.is_expired():
            self._hits += 1
            entry.touch()
            logger.debug(f"Cache hit for {tool_name} (key: {key[:8]}...)")
            return entry.value
        
        # Cache miss - execute and store
        self._misses += 1
        logger.debug(f"Cache miss for {tool_name} (key: {key[:8]}...)")
        
        result = executor()
        self._set(key, result, ttl_seconds)
        
        return result
    
    def get(self, tool_name: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        Get a value from cache without executing.
        
        Args:
            tool_name: Name of the tool
            params: Optional parameters for the tool
            
        Returns:
            Cached value or None if not found
        """
        key = self._generate_key(tool_name, params)
        entry = self._get(key)
        
        if entry is not None and not entry.is_expired():
            self._hits += 1
            entry.touch()
            return entry.value
        
        return None
    
    def set(
        self, 
        tool_name: str, 
        value: Any, 
        params: Optional[Dict] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store a value in cache.
        
        Args:
            tool_name: Name of the tool
            value: Value to cache
            params: Optional parameters for the tool
            ttl_seconds: Time-to-live for cached result
        """
        key = self._generate_key(tool_name, params)
        self._set(key, value, ttl_seconds)
    
    def _get(self, key: str) -> Optional[CacheEntry]:
        """Internal method to get a cache entry."""
        # Clean expired entries before lookup
        self._clean_expired()
        
        return self._cache.get(key)
    
    def _set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Internal method to set a cache entry."""
        # Check if we need to clean up
        if len(self._cache) >= self._max_size:
            self._evict_lru()
        
        self._cache[key] = CacheEntry(value, ttl_seconds)
    
    def _generate_key(self, tool_name: str, params: Optional[Dict] = None) -> str:
        """
        Generate cache key from tool and parameters.
        
        Args:
            tool_name: Name of the tool
            params: Optional parameters
            
        Returns:
            MD5 hash of the key
        """
        key_parts = [tool_name]
        
        if params:
            # Sort keys to ensure consistent key generation
            sorted_params = json.dumps(params, sort_keys=True, default=str)
            key_parts.append(sorted_params)
        
        key = "::".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def _invalidate_key(self, key: str) -> None:
        """Invalidate a specific cache key."""
        if key in self._cache:
            del self._cache[key]
    
    def invalidate(self, tool_name: Optional[str] = None, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            tool_name: If provided, only invalidate keys for this tool
            pattern: If provided, invalidate keys matching this pattern
            
        Returns:
            Number of entries invalidated
        """
        invalidated = 0
        
        if tool_name:
            # Generate the key prefix for this tool
            tool_prefix = hashlib.md5(tool_name.encode()).hexdigest()[:8]
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(tool_prefix)]
            for key in keys_to_remove:
                del self._cache[key]
                invalidated += 1
        elif pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
                invalidated += 1
        else:
            invalidated = len(self._cache)
            self._cache.clear()
        
        logger.info(f"Invalidated {invalidated} cache entries")
        return invalidated
    
    def clear(self) -> None:
        """Clear all cached results and reset statistics."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")
    
    def _clean_expired(self) -> int:
        """Remove expired entries from cache."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Removed {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def _evict_lru(self) -> int:
        """
        Evict least recently used entries when cache is full.
        
        Returns:
            Number of entries evicted
        """
        if len(self._cache) < self._max_size:
            return 0
        
        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest 20% or at least 1
        evict_count = max(1, int(self._max_size * 0.2))
        keys_to_evict = [k for k, _ in sorted_entries[:evict_count]]
        
        for key in keys_to_evict:
            del self._cache[key]
        
        logger.debug(f"Evicted {len(keys_to_evict)} LRU cache entries")
        return len(keys_to_evict)
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get cache hit/miss statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        # Count expired entries
        expired_count = sum(1 for v in self._cache.values() if v.is_expired())
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 1),
            'cache_size': len(self._cache),
            'expired_entries': expired_count,
            'max_size': self._max_size
        }
    
    def get_keys(self, tool_name: Optional[str] = None) -> list:
        """
        Get all cache keys, optionally filtered by tool.
        
        Args:
            tool_name: Optional tool name to filter by
            
        Returns:
            List of cache keys
        """
        if tool_name:
            tool_prefix = hashlib.md5(tool_name.encode()).hexdigest()[:8]
            return [k for k in self._cache.keys() if k.startswith(tool_prefix)]
        return list(self._cache.keys())
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            Dictionary with entry info or None if not found
        """
        entry = self._cache.get(key)
        if entry is None:
            return None
        
        return entry.to_dict()


# Singleton instance for global use
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(max_size: int = CacheManager.DEFAULT_MAX_SIZE) -> CacheManager:
    """
    Get the global cache manager instance.
    
    Args:
        max_size: Maximum cache size (only used on first initialization)
        
    Returns:
        Global CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(max_size=max_size)
    return _cache_manager


__all__ = ['CacheManager', 'CacheEntry', 'get_cache_manager']