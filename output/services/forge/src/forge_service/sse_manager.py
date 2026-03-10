"""VentureStrat Forge — SSE event streaming manager."""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from sse_starlette.sse import ServerSentEvent

logger = logging.getLogger(__name__)


class SSEManager:
  """Manages SSE subscriptions for requirement execution streams."""

  def __init__(self):
    self._subscribers: dict[str, list[asyncio.Queue]] = {}

  async def subscribe(self, requirement_id: str) -> AsyncGenerator[ServerSentEvent, None]:
    """Subscribe to events for a requirement. Yields ServerSentEvent objects."""
    queue: asyncio.Queue = asyncio.Queue()

    if requirement_id not in self._subscribers:
      self._subscribers[requirement_id] = []
    self._subscribers[requirement_id].append(queue)

    logger.info(f'Client subscribed to {requirement_id}')

    try:
      while True:
        try:
          event = await asyncio.wait_for(queue.get(), timeout=30.0)
          yield ServerSentEvent(
            data=json.dumps(event['data']) if isinstance(event.get('data'), dict) else str(event.get('data', '')),
            event=event.get('event_type', 'message'),
          )
        except asyncio.TimeoutError:
          # Send heartbeat
          yield ServerSentEvent(
            data=json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()}),
            event='heartbeat',
          )
    except asyncio.CancelledError:
      pass
    finally:
      if requirement_id in self._subscribers:
        self._subscribers[requirement_id].remove(queue)
        if not self._subscribers[requirement_id]:
          del self._subscribers[requirement_id]
      logger.info(f'Client unsubscribed from {requirement_id}')

  def publish(self, requirement_id: str, event: dict):
    """Publish an event to all subscribers of a requirement."""
    if requirement_id not in self._subscribers:
      return

    for queue in self._subscribers[requirement_id]:
      try:
        queue.put_nowait(event)
      except asyncio.QueueFull:
        logger.warning(f'Queue full for subscriber on {requirement_id}, dropping event')


# Singleton instance
sse_manager = SSEManager()
