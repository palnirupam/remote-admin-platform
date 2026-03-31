"""
Cache Manager Module for Remote System Enhancement

This module provides caching capabilities for agent lists, plugin metadata,
and authentication tokens to improve performance.

Requirements: 23.1, 23.2, 23.3, 23.4, 23.5
"""

import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class CacheEntry:
    """
    Represents a cached entry with TTL
    
    Attributes:
        data: Cached data
        expires_at: Expiration timestamp
    """
    
    def __init__(self, data: Any, ttl: float):
        self.data = data
        self.expires_at = time.time() + ttl
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() > self.expires_at


class CacheManager:
    """
    Cache Manager for performance optimization
    
    Provides caching for:
    - Agent lists (5-second refresh)
    - Plugin metadata
    - Authentication tokens with TTL
    """
    
    def __init__(self):
        """Initialize cache manager"""
        self.agent_list_cache: Optional[CacheEntry] = None
        self.plugin_metadata_cache: Dict[str, CacheEntry] = {}
        self.token_cache: Dict[str, CacheEntry] = {}
        self.lock = threading.Lock()
        
        # Cache TTL settings (in seconds)
        self.agent_list_ttl = 5.0  # 5 seconds for agent list
        self.plugin_metadata_ttl = 300.0  # 5 minutes for plugin metadata
        self.token_ttl = 3600.0  # 1 hour for tokens
    
    def get_agent_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached agent list
        
        Returns:
            Cached agent list or None if expired/not cached
        
        Requirements: 23.3
        """
        with self.lock:
            if self.agent_list_cache and not self.agent_list_cache.is_expired():
                return self.agent_list_cache.data
            return None
    
    def set_agent_list(self, agent_list: List[Dict[str, Any]]) -> None:
        """
        Cache agent list with 5-second TTL
        
        Args:
            agent_list: List of agent information dictionaries
        
        Requirements: 23.3
        """
        with self.lock:
            self.agent_list_cache = CacheEntry(agent_list, self.agent_list_ttl)
    
    def invalidate_agent_list(self) -> None:
        """
        Invalidate agent list cache
        
        Call this when agent status changes to force refresh
        """
        with self.lock:
            self.agent_list_cache = None
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached plugin metadata
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            Cached plugin metadata or None if expired/not cached
        
        Requirements: 23.4
        """
        with self.lock:
            if plugin_name in self.plugin_metadata_cache:
                entry = self.plugin_metadata_cache[plugin_name]
                if not entry.is_expired():
                    return entry.data
                else:
                    # Remove expired entry
                    del self.plugin_metadata_cache[plugin_name]
            return None
    
    def set_plugin_metadata(self, plugin_name: str, metadata: Dict[str, Any]) -> None:
        """
        Cache plugin metadata
        
        Args:
            plugin_name: Name of the plugin
            metadata: Plugin metadata dictionary
        
        Requirements: 23.4
        """
        with self.lock:
            self.plugin_metadata_cache[plugin_name] = CacheEntry(metadata, self.plugin_metadata_ttl)
    
    def get_token_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get cached token validation result
        
        Args:
            token: JWT token string
        
        Returns:
            Cached validation result or None if expired/not cached
        
        Requirements: 23.5
        """
        with self.lock:
            if token in self.token_cache:
                entry = self.token_cache[token]
                if not entry.is_expired():
                    return entry.data
                else:
                    # Remove expired entry
                    del self.token_cache[token]
            return None
    
    def set_token_validation(self, token: str, validation_result: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """
        Cache token validation result
        
        Args:
            token: JWT token string
            validation_result: Validation result dictionary
            ttl: Optional custom TTL (defaults to 1 hour)
        
        Requirements: 23.5
        """
        with self.lock:
            cache_ttl = ttl if ttl is not None else self.token_ttl
            self.token_cache[token] = CacheEntry(validation_result, cache_ttl)
    
    def invalidate_token(self, token: str) -> None:
        """
        Invalidate cached token validation
        
        Args:
            token: JWT token string to invalidate
        """
        with self.lock:
            if token in self.token_cache:
                del self.token_cache[token]
    
    def clear_expired_entries(self) -> None:
        """
        Clear all expired cache entries
        
        Should be called periodically to prevent memory growth
        """
        with self.lock:
            # Clear expired plugin metadata
            expired_plugins = [
                name for name, entry in self.plugin_metadata_cache.items()
                if entry.is_expired()
            ]
            for name in expired_plugins:
                del self.plugin_metadata_cache[name]
            
            # Clear expired tokens
            expired_tokens = [
                token for token, entry in self.token_cache.items()
                if entry.is_expired()
            ]
            for token in expired_tokens:
                del self.token_cache[token]
            
            # Clear expired agent list
            if self.agent_list_cache and self.agent_list_cache.is_expired():
                self.agent_list_cache = None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            return {
                'agent_list_cached': self.agent_list_cache is not None and not self.agent_list_cache.is_expired(),
                'plugin_metadata_count': len(self.plugin_metadata_cache),
                'token_cache_count': len(self.token_cache)
            }
