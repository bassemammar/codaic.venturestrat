"""Observability middleware for request tracking and metrics."""

import time
import uuid
from typing import Callable
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from auth_service.integrations.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    active_requests,
)

logger = structlog.get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for observability (metrics, logging, tracing)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request context to logger
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Track active requests
        active_requests.inc()

        # Start timer
        start_time = time.time()

        # Log request
        logger.info("request_started",
                   method=request.method,
                   path=request.url.path,
                   client=request.client.host if request.client else None)

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)

            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()

            # Log response
            logger.info("request_completed",
                       status_code=response.status_code,
                       duration=duration)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Record error metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()

            # Log error
            logger.error("request_failed",
                        error=str(e),
                        duration=duration,
                        exc_info=True)

            raise

        finally:
            active_requests.dec()
            structlog.contextvars.clear_contextvars()
