"""API router for event monitoring endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg
import structlog
from fastapi import APIRouter, Depends, Query

from event_monitor.models import (
  EventRecord,
  EventStats,
  PaginatedResponse,
  TopologyGraph,
  TraceSummary,
)
from event_monitor.topology import build_topology

logger = structlog.get_logger(__name__)

router = APIRouter(prefix='/api/v1/events', tags=['Events'])

# Will be set by main.py on startup
_pool: asyncpg.Pool | None = None
_services_dir: str = '/app/services'
_topology_cache: TopologyGraph | None = None


def set_pool(pool: asyncpg.Pool) -> None:
  global _pool
  _pool = pool


def set_services_dir(path: str) -> None:
  global _services_dir, _topology_cache
  _services_dir = path
  _topology_cache = None


async def _get_pool() -> asyncpg.Pool:
  if _pool is None:
    raise RuntimeError('Database pool not initialized')
  return _pool


# -----------------------------------------------------------------------
# Event Stream
# -----------------------------------------------------------------------

@router.get('/stream', response_model=PaginatedResponse)
async def get_event_stream(
  page: int = Query(1, ge=1),
  page_size: int = Query(50, ge=1, le=200),
  topic: str | None = None,
  service: str | None = None,
  entity_type: str | None = None,
  status: str | None = None,
  since: str | None = None,
  pool: asyncpg.Pool = Depends(_get_pool),
):
  """Get paginated event stream with filters."""
  conditions = []
  params = []
  idx = 1

  if topic:
    conditions.append(f'topic LIKE ${idx}')
    params.append(f'%{topic}%')
    idx += 1
  if service:
    conditions.append(f'(producer_service = ${idx} OR consumer_service = ${idx})')
    params.append(service)
    idx += 1
  if entity_type:
    conditions.append(f'entity_type = ${idx}')
    params.append(entity_type)
    idx += 1
  if status:
    conditions.append(f'status = ${idx}')
    params.append(status)
    idx += 1
  if since:
    conditions.append(f'created_at >= ${idx}')
    params.append(datetime.fromisoformat(since))
    idx += 1

  where = f"WHERE {' AND '.join(conditions)}" if conditions else ''
  offset = (page - 1) * page_size

  count_sql = f'SELECT COUNT(*) FROM shared.event_audit {where}'
  total = await pool.fetchval(count_sql, *params)

  query = f"""
    SELECT id::text, correlation_id, trace_id, topic, event_key, event_id,
           producer_service, consumer_service, entity_type, entity_id,
           action, from_state, to_state, status, duration_ms,
           payload::text, error_message, tenant_id, created_at
    FROM shared.event_audit {where}
    ORDER BY created_at DESC
    LIMIT ${idx} OFFSET ${idx + 1}
  """
  params.extend([page_size, offset])

  rows = await pool.fetch(query, *params)
  items = [_row_to_record(r) for r in rows]

  return PaginatedResponse(
    items=items,
    total=total,
    page=page,
    page_size=page_size,
    has_more=(offset + page_size) < total,
  )


# -----------------------------------------------------------------------
# Traces
# -----------------------------------------------------------------------

@router.get('/traces', response_model=list[TraceSummary])
async def get_traces(
  limit: int = Query(20, ge=1, le=100),
  since_hours: int = Query(24, ge=1, le=168),
  pool: asyncpg.Pool = Depends(_get_pool),
):
  """Get recent trace summaries grouped by correlation_id."""
  since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

  query = """
    SELECT
      correlation_id,
      MIN(topic) FILTER (WHERE created_at = sub.first_at) as root_topic,
      MIN(event_key) FILTER (WHERE created_at = sub.first_at) as root_key,
      COUNT(DISTINCT COALESCE(producer_service, '')) +
        COUNT(DISTINCT COALESCE(consumer_service, '')) as service_count,
      COUNT(*) as event_count,
      bool_or(status IN ('dlq', 'failed')) as has_errors,
      EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) * 1000 as total_duration_ms,
      MIN(created_at) as started_at,
      MAX(created_at) as ended_at
    FROM shared.event_audit ea
    JOIN (
      SELECT correlation_id, MIN(created_at) as first_at
      FROM shared.event_audit
      WHERE correlation_id IS NOT NULL AND created_at >= $1
      GROUP BY correlation_id
    ) sub USING (correlation_id)
    WHERE correlation_id IS NOT NULL AND ea.created_at >= $1
    GROUP BY correlation_id
    ORDER BY started_at DESC
    LIMIT $2
  """
  rows = await pool.fetch(query, since, limit)

  return [
    TraceSummary(
      correlation_id=r['correlation_id'],
      root_topic=r['root_topic'] or '',
      root_event_key=r['root_key'],
      service_count=r['service_count'],
      event_count=r['event_count'],
      has_errors=r['has_errors'],
      total_duration_ms=int(r['total_duration_ms']) if r['total_duration_ms'] else None,
      started_at=r['started_at'],
      ended_at=r['ended_at'],
    )
    for r in rows
  ]


@router.get('/traces/{correlation_id}', response_model=list[EventRecord])
async def get_trace_detail(
  correlation_id: str,
  pool: asyncpg.Pool = Depends(_get_pool),
):
  """Get all events in a trace ordered by time."""
  query = """
    SELECT id::text, correlation_id, trace_id, topic, event_key, event_id,
           producer_service, consumer_service, entity_type, entity_id,
           action, from_state, to_state, status, duration_ms,
           payload::text, error_message, tenant_id, created_at
    FROM shared.event_audit
    WHERE correlation_id = $1
    ORDER BY created_at ASC
  """
  rows = await pool.fetch(query, correlation_id)
  return [_row_to_record(r) for r in rows]


# -----------------------------------------------------------------------
# Entity events
# -----------------------------------------------------------------------

@router.get('/entity/{entity_type}/{entity_id}', response_model=list[EventRecord])
async def get_entity_events(
  entity_type: str,
  entity_id: str,
  limit: int = Query(50, ge=1, le=200),
  pool: asyncpg.Pool = Depends(_get_pool),
):
  """Get all events for a specific entity."""
  query = """
    SELECT id::text, correlation_id, trace_id, topic, event_key, event_id,
           producer_service, consumer_service, entity_type, entity_id,
           action, from_state, to_state, status, duration_ms,
           payload::text, error_message, tenant_id, created_at
    FROM shared.event_audit
    WHERE entity_type = $1 AND entity_id = $2
    ORDER BY created_at DESC
    LIMIT $3
  """
  rows = await pool.fetch(query, entity_type, entity_id, limit)
  return [_row_to_record(r) for r in rows]


# -----------------------------------------------------------------------
# Topology
# -----------------------------------------------------------------------

@router.get('/topology', response_model=TopologyGraph)
async def get_topology():
  """Get service-topic topology graph from manifests."""
  global _topology_cache
  if _topology_cache is None:
    _topology_cache = build_topology(_services_dir)
  return _topology_cache


@router.post('/topology/refresh', response_model=TopologyGraph)
async def refresh_topology():
  """Force refresh of topology cache."""
  global _topology_cache
  _topology_cache = build_topology(_services_dir)
  return _topology_cache


# -----------------------------------------------------------------------
# Stats
# -----------------------------------------------------------------------

@router.get('/stats', response_model=EventStats)
async def get_stats(
  since_hours: int = Query(1, ge=1, le=168),
  pool: asyncpg.Pool = Depends(_get_pool),
):
  """Get aggregated event statistics."""
  since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
  now = datetime.now(timezone.utc)
  minutes = max((now - since).total_seconds() / 60, 1)

  # Total + per-status
  status_query = """
    SELECT status, COUNT(*) as cnt
    FROM shared.event_audit WHERE created_at >= $1
    GROUP BY status
  """
  status_rows = await pool.fetch(status_query, since)
  per_status = {r['status']: r['cnt'] for r in status_rows}
  total = sum(per_status.values())

  # Per-topic (top 20)
  topic_query = """
    SELECT topic, COUNT(*) as cnt
    FROM shared.event_audit WHERE created_at >= $1
    GROUP BY topic ORDER BY cnt DESC LIMIT 20
  """
  topic_rows = await pool.fetch(topic_query, since)
  per_topic = {r['topic']: r['cnt'] for r in topic_rows}

  # Per-service
  svc_query = """
    SELECT COALESCE(producer_service, 'unknown') as svc, COUNT(*) as cnt
    FROM shared.event_audit WHERE created_at >= $1
    GROUP BY svc ORDER BY cnt DESC
  """
  svc_rows = await pool.fetch(svc_query, since)
  per_service = {r['svc']: r['cnt'] for r in svc_rows}

  # Avg duration
  dur_query = """
    SELECT AVG(duration_ms) as avg_dur
    FROM shared.event_audit WHERE created_at >= $1 AND duration_ms IS NOT NULL
  """
  avg_dur = await pool.fetchval(dur_query, since)

  error_count = per_status.get('dlq', 0) + per_status.get('failed', 0)

  return EventStats(
    total_events=total,
    events_per_topic=per_topic,
    events_per_service=per_service,
    events_per_status=per_status,
    avg_duration_ms=float(avg_dur) if avg_dur else None,
    error_rate=error_count / total if total > 0 else 0.0,
    period_start=since,
    period_end=now,
    events_per_minute=total / minutes,
  )


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _row_to_record(r: asyncpg.Record) -> EventRecord:
  import json as _json

  payload = None
  if r['payload']:
    try:
      payload = _json.loads(r['payload'])
    except (ValueError, TypeError):
      pass

  return EventRecord(
    id=r['id'],
    correlation_id=r['correlation_id'],
    trace_id=r['trace_id'],
    topic=r['topic'],
    event_key=r['event_key'],
    event_id=r['event_id'],
    producer_service=r['producer_service'],
    consumer_service=r['consumer_service'],
    entity_type=r['entity_type'],
    entity_id=r['entity_id'],
    action=r['action'],
    from_state=r['from_state'],
    to_state=r['to_state'],
    status=r['status'],
    duration_ms=r['duration_ms'],
    payload=payload,
    error_message=r['error_message'],
    tenant_id=r['tenant_id'],
    created_at=r['created_at'],
  )

