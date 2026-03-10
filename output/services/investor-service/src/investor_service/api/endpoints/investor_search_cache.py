"""Redis cache helper for investor search endpoints.

Provides a thin async wrapper around redis.asyncio that gracefully degrades
to a no-op when Redis is unavailable (development mode, tests, etc.).
"""

import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

_redis_client = None
_init_attempted = False


async def _get_redis():
  """Lazy-init a shared redis.asyncio connection."""
  global _redis_client, _init_attempted
  if _redis_client is not None:
    return _redis_client
  if _init_attempted:
    return None
  _init_attempted = True
  try:
    import redis.asyncio as aioredis
    from investor_service.config import settings
    redis_url = getattr(settings, 'redis_url', None) or 'redis://localhost:6379/0'
    _redis_client = aioredis.from_url(redis_url, decode_responses=True)
    # Ping to verify connectivity
    await _redis_client.ping()
    logger.info('redis_connected', url=redis_url.split('@')[-1])
    return _redis_client
  except Exception as e:
    logger.warning('redis_unavailable', error=str(e))
    _redis_client = None
    return None


class RedisCache:
  """Async Redis cache with graceful fallback to no-op."""

  async def get(self, key: str) -> Optional[str]:
    r = await _get_redis()
    if r is None:
      return None
    try:
      return await r.get(key)
    except Exception as e:
      logger.warning('redis_get_error', key=key, error=str(e))
      return None

  async def set(self, key: str, value: str, ttl: int = 300) -> None:
    r = await _get_redis()
    if r is None:
      return
    try:
      await r.set(key, value, ex=ttl)
    except Exception as e:
      logger.warning('redis_set_error', key=key, error=str(e))

  async def delete(self, key: str) -> None:
    r = await _get_redis()
    if r is None:
      return
    try:
      await r.delete(key)
    except Exception as e:
      logger.warning('redis_delete_error', key=key, error=str(e))


redis_cache = RedisCache()
