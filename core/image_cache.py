"""
Image processing cache to avoid re-encoding identical images.

Uses SHA-256 hash of image bytes as cache key to detect duplicate images
and reuse previously processed results (resized + base64 encoded).
"""

import hashlib
from functools import lru_cache
from typing import Dict, Tuple


class ImageProcessingCache:
    """In-memory cache for processed image data."""

    def __init__(self, max_size: int = 100):
        """
        Initialize cache with size limit.

        Args:
            max_size: Maximum number of images to cache
        """
        self.max_size = max_size
        self.cache: Dict[str, Dict] = {}

    def _hash_image(self, image_bytes: bytes) -> str:
        """
        Generate SHA-256 hash of image bytes.

        Args:
            image_bytes: Raw image data

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(image_bytes).hexdigest()

    def get(self, image_bytes: bytes) -> Dict | None:
        """
        Retrieve cached image processing result.

        Args:
            image_bytes: Raw image data to look up

        Returns:
            Cached result dict or None if not cached
        """
        image_hash = self._hash_image(image_bytes)
        return self.cache.get(image_hash)

    def set(self, image_bytes: bytes, result: Dict) -> None:
        """
        Store image processing result in cache.

        Args:
            image_bytes: Raw image data (used for hash)
            result: Processed data dict containing resized_bytes and base64
        """
        # Enforce cache size limit with simple FIFO eviction
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (first key)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        image_hash = self._hash_image(image_bytes)
        self.cache[image_hash] = result

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_images": len(self.cache),
            "max_size": self.max_size,
            "memory_estimate_bytes": sum(
                len(v.get("resized_bytes", b"")) + len(v.get("base64", ""))
                for v in self.cache.values()
            ),
        }


# Global cache instance for image processing
image_cache = ImageProcessingCache(max_size=100)


def get_cached_image(image_bytes: bytes) -> Dict | None:
    """
    Retrieve cached image processing result.

    Args:
        image_bytes: Raw image data

    Returns:
        Cached result or None
    """
    return image_cache.get(image_bytes)


def cache_image(image_bytes: bytes, result: Dict) -> None:
    """
    Store image processing result in cache.

    Args:
        image_bytes: Raw image data
        result: Processed data dict
    """
    image_cache.set(image_bytes, result)


def clear_image_cache() -> None:
    """Clear the image cache."""
    image_cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """Get image cache statistics."""
    return image_cache.stats()

