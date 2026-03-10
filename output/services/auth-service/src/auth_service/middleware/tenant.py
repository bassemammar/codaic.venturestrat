"""
Tenant context middleware for auth-service.

Extracts X-Tenant-ID header and attaches to request state for multi-tenant operations.
"""
from typing import Callable
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from venturestrat.tenancy.context import set_current_tenant, clear_current_tenant, TenantContext

logger = structlog.get_logger(__name__)

# Paths that don't require tenant context
EXCLUDED_PATHS = {"/health", "/health/live", "/health/ready", "/metrics", "/docs", "/redoc", "/openapi.json", "/"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract tenant ID from request headers and set TenantContext."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip tenant extraction for health/docs endpoints
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID")
        request.state.tenant_id = tenant_id

        if tenant_id:
            set_current_tenant(TenantContext(tenant_id=tenant_id))

        try:
            response = await call_next(request)
        finally:
            clear_current_tenant()

        return response
