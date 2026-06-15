from typing import Any, Optional
from cachetools import TTLCache
from app.core.config import get_settings


class FlagCache:
    def __init__(self):
        # small in-memory TTL cache
        settings = get_settings()
        self._cache = TTLCache(maxsize=1024, ttl=settings.CACHE_TTL_SECONDS)

    def get(self, flag_name: str) -> Optional[Any]:
        return self._cache.get(flag_name)

    def set(self, flag_name: str, value: Any):
        self._cache[flag_name] = value

    def invalidate(self, flag_name: str):
        if flag_name in self._cache:
            del self._cache[flag_name]
