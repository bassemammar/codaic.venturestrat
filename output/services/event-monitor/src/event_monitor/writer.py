"""Async database writer for event audit records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

INSERT_SQL = """
INSERT INTO shared.event_audit (
  id, correlation_id, trace_id, topic, event_key, event_id,
  producer_service, consumer_service, entity_type, entity_id,
  action, from_state, to_state, status, payload, tenant_id, created_at
) VALUES (
  $1, $2, $3, $4, $5, $6,
  $7, $8, $9, $10,
  $11, $12, $13, $14, $15, $16, $17
)
"""


class EventAuditWriter:
  """Writes event audit records to PostgreSQL using asyncpg."""

  def __init__(self, dsn: str) -> None:
    self._dsn = dsn
    self._pool: asyncpg.Pool | None = None

  async def start(self) -> None:
    self._pool = await asyncpg.create_pool(
      self._dsn, min_size=2, max_size=5,
      command_timeout=10,
    )
    logger.info('audit_writer_started')

  async def stop(self) -> None:
    if self._pool:
      await self._pool.close()
      logger.info('audit_writer_stopped')

  async def write(
    self,
    *,
    topic: str,
    event_key: str | None = None,
    event_id: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    producer_service: str | None = None,
    consumer_service: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    from_state: str | None = None,
    to_state: str | None = None,
    status: str = 'observed',
    payload: dict[str, Any] | None = None,
    tenant_id: str | None = None,
  ) -> None:
    """Write a single audit record."""
    if not self._pool:
      return

    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Trim large payloads (keep first 4KB of JSON)
    payload_json = None
    if payload:
      raw = json.dumps(payload, default=str)
      if len(raw) > 4096:
        raw = raw[:4096]
      payload_json = raw

    try:
      await self._pool.execute(
        INSERT_SQL,
        uuid.UUID(record_id),
        correlation_id,
        trace_id,
        topic,
        event_key,
        event_id,
        producer_service,
        consumer_service,
        entity_type,
        entity_id,
        action,
        from_state,
        to_state,
        status,
        payload_json,
        tenant_id,
        now,
      )
    except Exception as exc:
      logger.error('audit_write_failed', error=str(exc), topic=topic)
