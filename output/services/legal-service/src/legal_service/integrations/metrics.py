"""Prometheus metrics integration."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import structlog

logger = structlog.get_logger(__name__)

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Business metrics
entity_operations_total = Counter(
    'entity_operations_total',
    'Total entity operations',
    ['entity', 'operation', 'status']
)

# Dependency metrics
dependency_health = Gauge(
    'dependency_health',
    'Dependency health status (1=healthy, 0=unhealthy)',
    ['dependency']
)

# Active connections
active_requests = Gauge(
    'active_requests',
    'Number of active requests'
)


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
