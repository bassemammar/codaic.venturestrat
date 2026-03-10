"""Kafka observer — passively subscribes to all topics and records events."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer

from event_monitor.writer import EventAuditWriter

logger = structlog.get_logger(__name__)

# Map topic prefix → producer service name
# e.g. 'sales.sale_order.confirmed' → 'sales-service'
_SERVICE_MAPPING: dict[str, str] = {
  'investor': 'investor-service',
  'outreach': 'outreach-service',
  'crm': 'crm-service',
  'billing': 'billing-service',
}


def _infer_producer(topic: str) -> str | None:
  prefix = topic.split('.')[0] if '.' in topic else topic
  return _SERVICE_MAPPING.get(prefix)


def _extract_event_data(topic: str, event: dict[str, Any]) -> dict[str, Any]:
  """Extract structured fields from raw event payload."""
  data: dict[str, Any] = {}

  # correlation / tracing
  data['correlation_id'] = event.get('correlation_id')
  data['trace_id'] = event.get('trace_id')
  data['event_id'] = event.get('event_id')
  data['tenant_id'] = event.get('tenant_id')

  # entity inference from topic: domain.entity_type.action
  parts = topic.split('.')
  if len(parts) >= 3:
    data['entity_type'] = parts[1]  # e.g. 'sale_order'
    data['action'] = parts[2]  # e.g. 'confirmed'
  elif len(parts) == 2:
    data['entity_type'] = parts[1]

  # entity_id from payload
  entity_id = event.get('id') or event.get('entity_id')
  if entity_id:
    data['entity_id'] = str(entity_id)

  # state transitions
  data['from_state'] = event.get('from_state') or event.get('old_state')
  data['to_state'] = event.get('to_state') or event.get('new_state') or event.get('state')

  # DLQ detection
  if topic.endswith('.dlq'):
    data['status'] = 'dlq'
    data['error_message'] = event.get('error')
    # original topic
    original = event.get('original_topic', topic.replace('.dlq', ''))
    data['consumer_service'] = event.get('group_id', '').split('-')[0] + '-service' if event.get('group_id') else None
  else:
    data['status'] = 'observed'

  return data


class KafkaObserver:
  """Passively observes all Kafka topics and records events to audit table."""

  def __init__(
    self,
    bootstrap_servers: str,
    group_id: str,
    writer: EventAuditWriter,
    topic_pattern: str = '^(?!__).+',
  ) -> None:
    self._bootstrap = bootstrap_servers
    self._group_id = group_id
    self._writer = writer
    self._pattern = re.compile(topic_pattern)
    self._consumer: AIOKafkaConsumer | None = None
    self._running = False
    self._task: asyncio.Task | None = None

  async def start(self) -> None:
    """Start observing in a background task."""
    self._running = True
    self._task = asyncio.create_task(self._run(), name='kafka-observer')
    logger.info('observer_started', group_id=self._group_id)

  async def stop(self) -> None:
    self._running = False
    if self._consumer:
      await self._consumer.stop()
    if self._task:
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass
    logger.info('observer_stopped')

  async def _run(self) -> None:
    """Main observe loop with reconnection."""
    while self._running:
      try:
        await self._observe()
      except asyncio.CancelledError:
        break
      except Exception as exc:
        logger.error('observer_error', error=str(exc))
        if self._running:
          await asyncio.sleep(5)  # reconnect backoff

  async def _observe(self) -> None:
    """Subscribe to all topics via pattern and consume events."""
    self._consumer = AIOKafkaConsumer(
      bootstrap_servers=self._bootstrap,
      group_id=self._group_id,
      auto_offset_reset='latest',
      enable_auto_commit=True,
      auto_commit_interval_ms=5000,
      value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None,
      metadata_max_age_ms=30000,
    )

    await self._consumer.start()
    # Pattern subscribe — matches all non-internal topics
    self._consumer.subscribe(pattern=self._pattern)
    logger.info('observer_subscribed', pattern=self._pattern.pattern)

    try:
      async for msg in self._consumer:
        if not self._running:
          break
        await self._handle_message(msg)
    finally:
      try:
        await self._consumer.stop()
      except Exception:
        pass

  async def _handle_message(self, msg: Any) -> None:
    """Process a single Kafka message into an audit record."""
    event = msg.value
    if not isinstance(event, dict):
      return

    # Parse headers
    headers: dict[str, str] = {}
    if msg.headers:
      for k, v in msg.headers:
        headers[k] = v.decode('utf-8') if isinstance(v, bytes) else str(v)

    # Extract structured data
    extracted = _extract_event_data(msg.topic, event)

    # Prefer header values over payload values
    correlation_id = headers.get('x-correlation-id') or extracted.get('correlation_id')
    trace_id = headers.get('x-trace-id') or extracted.get('trace_id')
    event_id = headers.get('x-event-id') or extracted.get('event_id')
    tenant_id = headers.get('x-tenant-id') or extracted.get('tenant_id')

    event_key = msg.key.decode('utf-8') if isinstance(msg.key, bytes) else msg.key

    await self._writer.write(
      topic=msg.topic,
      event_key=event_key,
      event_id=event_id,
      correlation_id=correlation_id,
      trace_id=trace_id,
      producer_service=_infer_producer(msg.topic),
      consumer_service=extracted.get('consumer_service'),
      entity_type=extracted.get('entity_type'),
      entity_id=extracted.get('entity_id'),
      action=extracted.get('action'),
      from_state=extracted.get('from_state'),
      to_state=extracted.get('to_state'),
      status=extracted.get('status', 'observed'),
      payload=event,
      tenant_id=tenant_id,
    )
