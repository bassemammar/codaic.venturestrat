"""Base Kafka consumer with shared setup and lifecycle management."""

import json
import asyncio
from typing import Any, Dict, Optional

import structlog
from aiokafka import AIOKafkaConsumer

from crm_service.config import settings

logger = structlog.get_logger(__name__)


class BaseConsumer:
  """Base class for Kafka consumers with common setup and error handling.

  Provides:
  - Consumer initialization with configurable group_id and topics
  - Graceful start/stop lifecycle
  - JSON deserialization
  - Background consumption loop with error handling
  """

  def __init__(self, group_id: str, topics: list[str]):
    self.group_id = group_id
    self.topics = topics
    self.consumer: Optional[AIOKafkaConsumer] = None
    self._task: Optional[asyncio.Task] = None
    self._running = False

  async def start(self) -> None:
    """Initialize and start the Kafka consumer in a background task."""
    try:
      self.consumer = AIOKafkaConsumer(
        *self.topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=self.group_id,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
      )
      await self.consumer.start()
      self._running = True
      self._task = asyncio.create_task(self._consume_loop())
      logger.info(
        'consumer_started',
        group_id=self.group_id,
        topics=self.topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
      )
    except Exception as e:
      logger.error(
        'consumer_start_failed',
        group_id=self.group_id,
        topics=self.topics,
        error=str(e),
      )

  async def stop(self) -> None:
    """Stop the consumer and cancel the background task."""
    self._running = False
    if self._task:
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass
    if self.consumer:
      try:
        await self.consumer.stop()
        logger.info('consumer_stopped', group_id=self.group_id)
      except Exception as e:
        logger.error('consumer_stop_failed', group_id=self.group_id, error=str(e))

  async def _consume_loop(self) -> None:
    """Main consumption loop — reads messages and dispatches to handle_event."""
    while self._running:
      try:
        async for msg in self.consumer:
          if not self._running:
            break
          try:
            await self.handle_event(msg.topic, msg.value)
          except Exception as e:
            logger.error(
              'event_handling_failed',
              group_id=self.group_id,
              topic=msg.topic,
              error=str(e),
              event_id=msg.value.get('event_id', 'unknown') if isinstance(msg.value, dict) else 'unknown',
            )
      except asyncio.CancelledError:
        raise
      except Exception as e:
        if self._running:
          logger.error('consume_loop_error', group_id=self.group_id, error=str(e))
          await asyncio.sleep(5)

  async def handle_event(self, topic: str, event: Dict[str, Any]) -> None:
    """Handle a single event. Must be implemented by subclasses.

    Args:
      topic: The Kafka topic the event was received on.
      event: Deserialized event payload dict.
    """
    raise NotImplementedError('Subclasses must implement handle_event')
