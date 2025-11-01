"""
Cache manager for document processing
Avoids reprocessing identical documents using file hash
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class CacheManager:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_ttl = timedelta(hours=24)  # Cache for 24 hours

    def _get_cache_path(self, file_hash: str) -> str:
        """Get cache file path for a given file hash"""
        return os.path.join(self.cache_dir, f"{file_hash}.json")

    def get(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result for a file hash

        Returns:
            Cached result or None if not found/expired
        """
        cache_path = self._get_cache_path(file_hash)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)

            # Check if cache is expired
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cached_time > self.cache_ttl:
                # Cache expired, delete it
                os.remove(cache_path)
                return None

            return cached_data['result']

        except Exception as e:
            print(f"Error reading cache for {file_hash}: {e}")
            return None

    def set(self, file_hash: str, result: Dict[str, Any]) -> None:
        """
        Store result in cache

        Args:
            file_hash: SHA-256 hash of the file
            result: Analysis result to cache
        """
        cache_path = self._get_cache_path(file_hash)

        cache_data = {
            'file_hash': file_hash,
            'cached_at': datetime.now().isoformat(),
            'result': result
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"Error writing cache for {file_hash}: {e}")

    def invalidate(self, file_hash: str) -> bool:
        """
        Invalidate (delete) cache for a file hash

        Returns:
            True if cache was deleted, False if not found
        """
        cache_path = self._get_cache_path(file_hash)

        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except Exception as e:
                print(f"Error deleting cache for {file_hash}: {e}")
                return False

        return False

    def clear_expired(self) -> int:
        """
        Clear all expired cache entries

        Returns:
            Number of entries cleared
        """
        cleared = 0

        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue

                cache_path = os.path.join(self.cache_dir, filename)

                try:
                    with open(cache_path, 'r') as f:
                        cached_data = json.load(f)

                    cached_time = datetime.fromisoformat(cached_data['cached_at'])
                    if datetime.now() - cached_time > self.cache_ttl:
                        os.remove(cache_path)
                        cleared += 1

                except Exception as e:
                    print(f"Error processing cache file {filename}: {e}")

        except FileNotFoundError:
            # Cache directory doesn't exist or is empty
            pass

        return cleared

    def clear_all(self) -> int:
        """
        Clear ALL cache entries (including non-expired)

        Returns:
            Number of entries cleared
        """
        cleared = 0

        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue

                cache_path = os.path.join(self.cache_dir, filename)

                try:
                    os.remove(cache_path)
                    cleared += 1
                except Exception as e:
                    print(f"Error deleting cache file {filename}: {e}")

        except FileNotFoundError:
            # Cache directory doesn't exist or is empty
            pass

        return cleared

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = 0
        expired = 0
        total_size = 0

        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue

            cache_path = os.path.join(self.cache_dir, filename)
            total += 1
            total_size += os.path.getsize(cache_path)

            try:
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)

                cached_time = datetime.fromisoformat(cached_data['cached_at'])
                if datetime.now() - cached_time > self.cache_ttl:
                    expired += 1

            except:
                pass

        return {
            'total_entries': total,
            'expired_entries': expired,
            'active_entries': total - expired,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / 1024 / 1024
        }
