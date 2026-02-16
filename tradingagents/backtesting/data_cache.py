"""File-based data cache for vendor API responses during backtesting.

Wraps `route_to_vendor` to cache raw responses on disk, making backtests
repeatable and avoiding API rate limits.
"""

import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class DataCache:
    """Persistent file-based cache for vendor data.

    Cache files are stored as JSON with a deterministic key derived from
    the method name and its arguments.

    Args:
        cache_dir: Directory for cache files. Created if it doesn't exist.
        enabled: Whether caching is active. If False, all calls pass through.
    """

    def __init__(self, cache_dir: str, enabled: bool = True):
        self.cache_dir = cache_dir
        self.enabled = enabled
        self._hits = 0
        self._misses = 0

        if enabled:
            os.makedirs(cache_dir, exist_ok=True)

    def _make_key(self, method: str, args: tuple, kwargs: dict) -> str:
        """Create a deterministic cache key from method + arguments.

        Returns:
            SHA256 hex digest string.
        """
        key_parts = [method] + [str(a) for a in args]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        raw = "|".join(key_parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_path(self, key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, method: str, args: tuple, kwargs: dict) -> Optional[str]:
        """Look up a cached response.

        Args:
            method: Vendor method name (e.g. "get_stock_data").
            args: Positional arguments passed to the method.
            kwargs: Keyword arguments passed to the method.

        Returns:
            Cached response string, or None if not cached.
        """
        if not self.enabled:
            return None

        key = self._make_key(method, args, kwargs)
        path = self._cache_path(key)

        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._hits += 1
                logger.debug("Cache HIT for %s (key=%s…)", method, key[:12])
                return data.get("response")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Cache read failed for %s: %s", method, e)
                return None

        self._misses += 1
        logger.debug("Cache MISS for %s (key=%s…)", method, key[:12])
        return None

    def put(self, method: str, args: tuple, kwargs: dict, response: str) -> None:
        """Store a response in the cache.

        Args:
            method: Vendor method name.
            args: Positional arguments.
            kwargs: Keyword arguments.
            response: Raw response string to cache.
        """
        if not self.enabled:
            return

        key = self._make_key(method, args, kwargs)
        path = self._cache_path(key)

        data = {
            "method": method,
            "args": [str(a) for a in args],
            "response": response,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            logger.debug("Cached response for %s (key=%s…)", method, key[:12])
        except IOError as e:
            logger.warning("Cache write failed for %s: %s", method, e)

    @property
    def stats(self) -> dict:
        """Return cache hit/miss statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": hit_rate,
        }


def create_cached_route_to_vendor(cache: DataCache):
    """Create a cached version of route_to_vendor.

    Returns a function with the same signature as `route_to_vendor`
    that checks the cache before calling the real implementation.

    Args:
        cache: DataCache instance.

    Returns:
        Wrapped function that caches vendor responses.
    """
    from tradingagents.dataflows.interface import route_to_vendor

    def cached_route(method: str, *args, **kwargs):
        cached = cache.get(method, args, kwargs)
        if cached is not None:
            return cached

        result = route_to_vendor(method, *args, **kwargs)

        if result is not None and isinstance(result, str):
            cache.put(method, args, kwargs, result)

        return result

    return cached_route
