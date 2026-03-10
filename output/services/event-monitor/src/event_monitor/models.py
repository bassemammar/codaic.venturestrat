"""Pydantic models for event monitor API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventRecord(BaseModel):
  id: str
  correlation_id: str | None = None
  trace_id: str | None = None
  topic: str
  event_key: str | None = None
  event_id: str | None = None
  producer_service: str | None = None
  consumer_service: str | None = None
  entity_type: str | None = None
  entity_id: str | None = None
  action: str | None = None
  from_state: str | None = None
  to_state: str | None = None
  status: str = 'observed'
  duration_ms: int | None = None
  payload: dict[str, Any] | None = None
  error_message: str | None = None
  tenant_id: str | None = None
  created_at: datetime


class TraceNode(BaseModel):
  event: EventRecord
  children: list[TraceNode] = Field(default_factory=list)


class TraceSummary(BaseModel):
  correlation_id: str
  root_topic: str
  root_event_key: str | None = None
  service_count: int
  event_count: int
  has_errors: bool
  total_duration_ms: int | None = None
  started_at: datetime
  ended_at: datetime


class TopologyNode(BaseModel):
  id: str
  type: str  # 'service' | 'topic'
  label: str
  color: str | None = None
  metadata: dict[str, Any] = Field(default_factory=dict)


class TopologyEdge(BaseModel):
  source: str
  target: str
  label: str = ''  # 'produces' | 'consumes'
  animated: bool = False


class TopologyGraph(BaseModel):
  nodes: list[TopologyNode]
  edges: list[TopologyEdge]


class EventStats(BaseModel):
  total_events: int
  events_per_topic: dict[str, int]
  events_per_service: dict[str, int]
  events_per_status: dict[str, int]
  avg_duration_ms: float | None = None
  error_rate: float
  period_start: datetime
  period_end: datetime
  events_per_minute: float


class PaginatedResponse(BaseModel):
  items: list[EventRecord]
  total: int
  page: int
  page_size: int
  has_more: bool
