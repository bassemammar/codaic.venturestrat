"""Kafka event producer for outreach-service domain events.

Thin wrapper around aiokafka AIOKafkaProducer with lazy initialization
and JSON serialization. Used by consumers and endpoints to publish
domain events (outreach.message.sent, outreach.message.replied, etc.).
"""

import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, Optional

import structlog
from aiokafka import AIOKafkaProducer

from outreach_service.config import settings

logger = structlog.get_logger(__name__)


def _json_serializer(obj: Any) -> str:
  """JSON serializer for datetime, date, Decimal, and UUID objects."""
  if isinstance(obj, (datetime, date)):
    return obj.isoformat()
  if isinstance(obj, Decimal):
    return str(obj)
  if isinstance(obj, uuid.UUID):
    return str(obj)
  raise TypeError(f'Type {type(obj)} not serializable')


class EventProducer:
  """Async Kafka producer with lazy initialization.

  Usage:
      producer = EventProducer()
      await producer.start()
      await producer.publish_event('outreach.message.sent', {...})
      await producer.stop()
  """

  def __init__(self) -> None:
    self._producer: Optional[AIOKafkaProducer] = None
    self._started = False

  async def start(self) -> None:
    """Initialize and start the Kafka producer."""
    if self._started:
      return
    try:
      self._producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(
          v, default=_json_serializer
        ).encode('utf-8'),
        compression_type='gzip',
        acks='all',
        request_timeout_ms=30000,
      )
      await self._producer.start()
      self._started = True
      logger.info(
        'event_producer_started',
        bootstrap_servers=settings.kafka_bootstrap_servers,
      )
    except Exception as e:
      logger.error('event_producer_start_failed', error=str(e))

  async def stop(self) -> None:
    """Stop the Kafka producer gracefully."""
    if self._producer:
      try:
        await self._producer.stop()
        self._started = False
        logger.info('event_producer_stopped')
      except Exception as e:
        logger.error('event_producer_stop_failed', error=str(e))

  async def publish_event(
    self,
    topic: str,
    data: Dict[str, Any],
    tenant_id: Optional[str] = None,
  ) -> None:
    """Publish a domain event to the given Kafka topic.

    If the producer is not started, logs a warning and returns silently.
    This prevents crashes when Kafka is unavailable during development.

    Args:
        topic: Full Kafka topic name (e.g. 'outreach.message.sent').
        data: Event payload dict (can contain datetime/UUID objects).
        tenant_id: Optional tenant ID to include in the event envelope.
    """
    if not self._started or not self._producer:
      logger.warning(
        'event_producer_not_started', topic=topic,
      )
      return

    event = {
      'event_id': str(uuid.uuid4()),
      'topic': topic,
      'data': data,
      'timestamp': datetime.utcnow().isoformat(),
      'service': settings.service_name,
    }
    if tenant_id:
      event['tenant_id'] = tenant_id

    try:
      await self._producer.send_and_wait(topic, value=event)
      logger.info(
        'event_published',
        topic=topic,
        event_id=event['event_id'],
      )
    except Exception as e:
      logger.error(
        'event_publish_failed',
        topic=topic,
        error=str(e),
      )


# Global singleton — start/stop from main.py lifespan
event_producer = EventProducer()
