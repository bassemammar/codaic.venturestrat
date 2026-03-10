"""Health check utilities for Event Monitor."""

import asyncio
from typing import Any

import structlog

from event_monitor.config import settings

logger = structlog.get_logger(__name__)


async def check_writer(writer) -> bool:
  """Check audit writer is initialized and has a pool."""
  try:
    return writer is not None and writer._pool is not None
  except Exception as exc:
    logger.warning('writer_health_check_failed', error=str(exc))
    return False


async def check_observer(observer) -> bool:
  """Check Kafka observer is running."""
  try:
    return observer is not None and observer._running
  except Exception as exc:
    logger.warning('observer_health_check_failed', error=str(exc))
    return False


async def get_detailed_health(writer=None, observer=None) -> dict[str, Any]:
  """Get detailed health status including dependency checks."""
  try:
    checks_tasks = {
      'writer': check_writer(writer),
      'observer': check_observer(observer),
    }

    # Wait for all checks (5 second timeout total)
    results = await asyncio.wait_for(
      asyncio.gather(*checks_tasks.values(), return_exceptions=True), timeout=5.0
    )

    # Build check results
    checks = {}
    for (name, _), result in zip(checks_tasks.items(), results):
      if isinstance(result, Exception):
        checks[name] = {'status': 'unhealthy', 'error': str(result)}
      else:
        checks[name] = {'status': 'healthy' if result else 'unhealthy'}

    all_healthy = all(
      checks[dep]['status'] == 'healthy' for dep in checks
    )

    return {
      'status': 'healthy' if all_healthy else 'unhealthy',
      'service': {
        'name': settings.service_name,
        'version': settings.service_version,
      },
      'checks': checks,
    }

  except asyncio.TimeoutError:
    logger.error('health_check_timeout')
    return {
      'status': 'unhealthy',
      'error': 'Health check timeout',
      'checks': {},
    }
