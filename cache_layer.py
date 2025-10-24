"""
Caching layer for improved performance and reduced API calls.
Provides in-memory and persistent caching with TTL and invalidation strategies.
"""

import hashlib
import json
import pickle
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from logger import logger

T = TypeVar("T")


class CacheStrategy(Enum):
    """Cache eviction strategies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached item with metadata."""

    value: T
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None

    def __post_init__(self):
        self.access_count += 1
        self.accessed_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False

        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time

    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.accessed_at = datetime.utcnow()


class CacheBackend(ABC, Generic[T]):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Retrieve a cache entry."""
        pass

    @abstractmethod
    def put(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Store a cache entry."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def keys(self) -> List[str]:
        """Get all cache keys."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get cache size."""
        pass


class MemoryCacheBackend(CacheBackend[T]):
    """In-memory cache backend with configurable eviction strategies."""

    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.strategy = strategy
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Retrieve a cache entry."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                return None

            entry.touch()
            return entry

    def put(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Store a cache entry."""
        with self._lock:
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                accessed_at=datetime.utcnow(),
                access_count=1,
                ttl_seconds=ttl_seconds,
            )

            # Check if we need to evict entries
            if key not in self._cache and len(self._cache) >= self.max_size:
                self._evict_entry()

            self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        with self._lock:
            return self._cache.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """Get cache size."""
        with self._lock:
            return len(self._cache)

    def _evict_entry(self) -> None:
        """Evict an entry based on the configured strategy."""
        if not self._cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].accessed_at)
            del self._cache[oldest_key]
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            least_used_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[least_used_key]
        elif self.strategy == CacheStrategy.TTL:
            # Remove expired entries first, then oldest
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            if expired_keys:
                del self._cache[expired_keys[0]]
            else:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
        elif self.strategy == CacheStrategy.FIFO:
            # Remove first inserted
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]


class FileCacheBackend(CacheBackend[T]):
    """File-based persistent cache backend."""

    def __init__(self, cache_dir: str = ".cache", max_files: int = 10000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_files = max_files
        self._lock = threading.RLock()

    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Retrieve a cache entry from file."""
        with self._lock:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return None

            try:
                with open(file_path, "rb") as f:
                    entry = pickle.load(f)

                if entry.is_expired():
                    file_path.unlink(missing_ok=True)
                    return None

                entry.touch()
                # Save updated access metadata
                with open(file_path, "wb") as f:
                    pickle.dump(entry, f)

                return entry
            except Exception as e:
                logger.warning(f"Failed to load cache entry for key {key}: {e}")
                file_path.unlink(missing_ok=True)
                return None

    def put(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Store a cache entry to file."""
        with self._lock:
            # Check if we need to evict files
            if self.size() >= self.max_files:
                self._evict_files()

            entry = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                accessed_at=datetime.utcnow(),
                access_count=1,
                ttl_seconds=ttl_seconds,
            )

            file_path = self._get_file_path(key)
            try:
                with open(file_path, "wb") as f:
                    pickle.dump(entry, f)
            except Exception as e:
                logger.error(f"Failed to save cache entry for key {key}: {e}")

    def delete(self, key: str) -> bool:
        """Delete a cache entry file."""
        with self._lock:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False

    def clear(self) -> None:
        """Clear all cache files."""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)

    def keys(self) -> List[str]:
        """Get all cache keys (this is expensive for file cache)."""
        # Note: This is not efficient for file cache as we'd need to reverse hash
        # In practice, you might want to maintain a separate index file
        return [f.stem for f in self.cache_dir.glob("*.cache")]

    def size(self) -> int:
        """Get cache size (number of files)."""
        return len(list(self.cache_dir.glob("*.cache")))

    def _evict_files(self) -> None:
        """Evict old cache files."""
        cache_files = list(self.cache_dir.glob("*.cache"))
        if len(cache_files) >= self.max_files:
            # Sort by modification time and remove oldest
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            num_to_remove = len(cache_files) - self.max_files + 100  # Remove extra for buffer
            for cache_file in cache_files[:num_to_remove]:
                cache_file.unlink(missing_ok=True)


class CacheManager:
    """Manages multiple cache layers and provides high-level caching operations."""

    def __init__(self):
        self._backends: Dict[str, CacheBackend] = {}
        self._default_backend = "memory"
        self._lock = threading.RLock()

    def add_backend(self, name: str, backend: CacheBackend, is_default: bool = False) -> None:
        """Add a cache backend."""
        with self._lock:
            self._backends[name] = backend
            if is_default or not self._backends:
                self._default_backend = name

    def get(self, key: str, backend: Optional[str] = None) -> Optional[Any]:
        """Get value from cache."""
        backend_name = backend or self._default_backend
        if backend_name not in self._backends:
            raise ValueError(f"Unknown cache backend: {backend_name}")

        entry = self._backends[backend_name].get(key)
        return entry.value if entry else None

    def put(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None, backend: Optional[str] = None
    ) -> None:
        """Put value into cache."""
        backend_name = backend or self._default_backend
        if backend_name not in self._backends:
            raise ValueError(f"Unknown cache backend: {backend_name}")

        self._backends[backend_name].put(key, value, ttl_seconds)

    def delete(self, key: str, backend: Optional[str] = None) -> bool:
        """Delete value from cache."""
        backend_name = backend or self._default_backend
        if backend_name not in self._backends:
            return False

        return self._backends[backend_name].delete(key)

    def clear(self, backend: Optional[str] = None) -> None:
        """Clear cache."""
        if backend:
            if backend in self._backends:
                self._backends[backend].clear()
        else:
            # Clear all backends
            for backend_instance in self._backends.values():
                backend_instance.clear()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache statistics."""
        stats = {}
        for name, backend in self._backends.items():
            stats[name] = {"size": backend.size(), "type": backend.__class__.__name__}
        return stats


class CacheNamespace:
    """Provides namespaced access to cache with automatic key prefixing."""

    def __init__(self, cache_manager: CacheManager, namespace: str):
        self.cache_manager = cache_manager
        self.namespace = namespace

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self.namespace}:{key}"

    def get(self, key: str, backend: Optional[str] = None) -> Optional[Any]:
        """Get value from cache with namespace."""
        return self.cache_manager.get(self._make_key(key), backend)

    def put(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None, backend: Optional[str] = None
    ) -> None:
        """Put value into cache with namespace."""
        self.cache_manager.put(self._make_key(key), value, ttl_seconds, backend)

    def delete(self, key: str, backend: Optional[str] = None) -> bool:
        """Delete value from cache with namespace."""
        return self.cache_manager.delete(self._make_key(key), backend)


def cached(
    ttl_seconds: Optional[int] = None,
    backend: Optional[str] = None,
    key_func: Optional[Callable] = None,
    cache_manager: Optional[CacheManager] = None,
):
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        nonlocal cache_manager
        if cache_manager is None:
            cache_manager = get_default_cache_manager()

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.sha256(":".join(key_parts).encode()).hexdigest()

            # Try to get from cache
            cached_result = cache_manager.get(cache_key, backend)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Compute result and cache it
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache_manager.put(cache_key, result, ttl_seconds, backend)

            return result

        return wrapper

    return decorator


# Global cache manager instance
_default_cache_manager: Optional[CacheManager] = None


def get_default_cache_manager() -> CacheManager:
    """Get the default cache manager instance."""
    global _default_cache_manager
    if _default_cache_manager is None:
        _default_cache_manager = CacheManager()

        # Add default backends
        memory_backend = MemoryCacheBackend(max_size=1000)
        file_backend = FileCacheBackend()

        _default_cache_manager.add_backend("memory", memory_backend, is_default=True)
        _default_cache_manager.add_backend("file", file_backend)

    return _default_cache_manager


def create_namespace(namespace: str) -> CacheNamespace:
    """Create a cache namespace."""
    return CacheNamespace(get_default_cache_manager(), namespace)


# Pre-configured namespaces for common use cases
email_cache = create_namespace("emails")
prediction_cache = create_namespace("predictions")
model_cache = create_namespace("models")
gmail_api_cache = create_namespace("gmail_api")


# Convenience functions
def cache_email(email_id: str, email_data: Dict[str, Any], ttl_seconds: int = 3600) -> None:
    """Cache email data."""
    email_cache.put(email_id, email_data, ttl_seconds)


def get_cached_email(email_id: str) -> Optional[Dict[str, Any]]:
    """Get cached email data."""
    return email_cache.get(email_id)


def cache_prediction(email_id: str, prediction: Dict[str, Any], ttl_seconds: int = 1800) -> None:
    """Cache prediction result."""
    prediction_cache.put(email_id, prediction, ttl_seconds)


def get_cached_prediction(email_id: str) -> Optional[Dict[str, Any]]:
    """Get cached prediction result."""
    return prediction_cache.get(email_id)


def cache_gmail_api_response(
    endpoint: str, params: Dict[str, Any], response: Any, ttl_seconds: int = 300
) -> None:
    """Cache Gmail API response."""
    cache_key = (
        f"{endpoint}:{hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()}"
    )
    gmail_api_cache.put(cache_key, response, ttl_seconds)


def get_cached_gmail_api_response(endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
    """Get cached Gmail API response."""
    cache_key = (
        f"{endpoint}:{hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()}"
    )
    return gmail_api_cache.get(cache_key)


def invalidate_email_cache(email_id: str = None) -> None:
    """Invalidate email cache."""
    if email_id:
        email_cache.delete(email_id)
    else:
        # Clear entire email cache namespace
        cache_manager = get_default_cache_manager()
        # Note: This is a simplified implementation
        # In practice, you'd want to track namespace keys separately
        cache_manager.clear()


def clear_all_caches() -> None:
    """Clear all caches."""
    get_default_cache_manager().clear()


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get cache statistics."""
    return get_default_cache_manager().get_stats()
