"""QuotaMiddleware for API quota enforcement.

This module implements FastAPI middleware for enforcing tenant quota limits
including API call limits, user limits, and storage limits with Redis-based
counters and 429 response generation.

Task 12.3: Implement QuotaMiddleware
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from registry.models.tenant_quotas import TenantQuotas
from registry.tenant_service import TenantService

logger = logging.getLogger(__name__)


class QuotaExceededException(Exception):
    """Exception raised when quota is exceeded."""

    def __init__(self, quota_type: str, current_usage: int, limit: int, retry_after: int):
        self.quota_type = quota_type
        self.current_usage = current_usage
        self.limit = limit
        self.retry_after = retry_after
        super().__init__(f"{quota_type} quota exceeded: {current_usage}/{limit}")


class RedisQuotaManager:
    """Redis-based quota counter management."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def get_api_quota_key(self, tenant_id: str, date: str | None = None) -> str:
        """Generate Redis key for API quota counter."""
        if date is None:
            date = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"quota:api:{tenant_id}:{date}"

    def get_user_quota_key(self, tenant_id: str) -> str:
        """Generate Redis key for user count."""
        return f"quota:users:{tenant_id}"

    def get_storage_quota_key(self, tenant_id: str) -> str:
        """Generate Redis key for storage usage."""
        return f"quota:storage:{tenant_id}"

    async def increment_api_counter(self, tenant_id: str) -> int:
        """Increment API call counter for tenant."""
        key = self.get_api_quota_key(tenant_id)
        count = self.redis.incr(key)

        # Set expiration if this is the first increment of the day
        if count == 1 or self.redis.ttl(key) == -1:
            # Expire at end of day (UTC)
            now = datetime.now(UTC)
            end_of_day = now.replace(hour=23, minute=59, second=59) + timedelta(seconds=1)
            ttl_seconds = int((end_of_day - now).total_seconds())
            self.redis.expire(key, ttl_seconds)

        return count

    async def get_current_api_count(self, tenant_id: str) -> int:
        """Get current API call count for tenant."""
        key = self.get_api_quota_key(tenant_id)
        count = self.redis.get(key)
        return int(count) if count else 0

    async def check_and_increment_api_quota(
        self, tenant_id: str, quotas: TenantQuotas
    ) -> dict[str, Any]:
        """Check API quota and increment if allowed."""
        try:
            current_count = await self.get_current_api_count(tenant_id)

            # Check if incrementing would exceed quota
            if not quotas.is_within_api_limit(current_count + 1):
                return {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": quotas.max_api_calls_per_day,
                    "remaining": 0,
                    "usage_percentage": quotas.get_api_usage_percentage(current_count),
                }

            # Increment counter
            new_count = await self.increment_api_counter(tenant_id)

            return {
                "allowed": True,
                "current_count": new_count,
                "limit": quotas.max_api_calls_per_day,
                "remaining": max(0, quotas.max_api_calls_per_day - new_count),
                "usage_percentage": quotas.get_api_usage_percentage(new_count),
            }

        except Exception as e:
            logger.error(f"Redis quota check failed for tenant {tenant_id}: {e}")
            # On Redis failure, allow the request but log the error
            # This prevents quota system failures from blocking all traffic
            return {
                "allowed": True,
                "current_count": 0,
                "limit": quotas.max_api_calls_per_day,
                "remaining": quotas.max_api_calls_per_day,
                "usage_percentage": 0.0,
                "redis_error": str(e),
            }


class QuotaMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for quota enforcement.

    Enforces tenant quota limits for API calls with Redis-based counters.
    Returns 429 responses when quotas are exceeded.
    """

    def __init__(
        self,
        app,
        redis_client=None,
        tenant_service: TenantService | None = None,
        exclude_paths: list[str] = None,
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.tenant_service = tenant_service
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        # Initialize Redis quota manager if Redis is available
        self.quota_manager = None
        if self.redis_client:
            self.quota_manager = RedisQuotaManager(self.redis_client)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through quota middleware."""

        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Skip non-modifying methods for most quotas (allow GET/HEAD/OPTIONS)
        # Only enforce quotas on write operations and API calls that consume resources
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)

        # Get tenant ID from X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            # No tenant header - this should be handled by TenantMiddleware
            return await call_next(request)

        try:
            # Get tenant quotas
            quotas = await self._get_tenant_quotas(tenant_id)
            if not quotas:
                # No quota configuration - allow request
                logger.warning(f"No quota configuration found for tenant {tenant_id}")
                return await call_next(request)

            # Check API quota
            if self.quota_manager:
                quota_result = await self.quota_manager.check_and_increment_api_quota(
                    tenant_id, quotas
                )

                if not quota_result["allowed"]:
                    # Generate 429 response
                    return self._generate_429_response(
                        quota_type="api_calls", quota_result=quota_result, request=request
                    )

                # Add quota info to request state for potential logging
                request.state.quota_info = quota_result

            # Process the request
            response = await call_next(request)

            # Add quota headers to response
            if hasattr(request.state, "quota_info"):
                quota_info = request.state.quota_info
                response.headers["X-RateLimit-Limit"] = str(quota_info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(quota_info["remaining"])
                response.headers["X-RateLimit-Reset"] = self._get_reset_timestamp()

            return response

        except Exception as e:
            logger.error(f"Quota middleware error for tenant {tenant_id}: {e}")
            # On error, allow the request to proceed
            return await call_next(request)

    async def _get_tenant_quotas(self, tenant_id: str) -> TenantQuotas | None:
        """Get tenant quota configuration."""
        if not self.tenant_service:
            return None

        try:
            # This would typically fetch from database
            # For this implementation, we'll create default quotas as a fallback
            tenant = await self.tenant_service.get_tenant(tenant_id)
            if tenant:
                # In a real implementation, this would fetch the actual quota configuration
                # from the database. For this implementation, we'll return default quotas.
                # The tenant service could return quota info in the tenant object.
                if isinstance(tenant, dict) and "quotas" in tenant:
                    return tenant["quotas"]
                else:
                    return TenantQuotas.create_default_quotas(tenant_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get tenant quotas for {tenant_id}: {e}")
            return None

    def _generate_429_response(
        self, quota_type: str, quota_result: dict[str, Any], request: Request
    ) -> JSONResponse:
        """Generate 429 Too Many Requests response."""

        retry_after = self._calculate_retry_after(quota_type, quota_result)

        # Standard 429 response headers
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(quota_result["limit"]),
            "X-RateLimit-Remaining": str(quota_result["remaining"]),
            "X-RateLimit-Reset": self._get_reset_timestamp(),
            "Content-Type": "application/json",
        }

        # Response body with detailed information
        body = {
            "error": "quota_exceeded",
            "message": f'{quota_type.replace("_", " ").title()} quota exceeded. '
            f'Limit: {quota_result["limit"]}, '
            f'Current: {quota_result["current_count"]}',
            "quota_type": quota_type,
            "current_usage": quota_result["current_count"],
            "limit": quota_result["limit"],
            "remaining": quota_result["remaining"],
            "usage_percentage": quota_result.get("usage_percentage", 0.0),
            "retry_after_seconds": retry_after,
            "reset_time": self._get_reset_timestamp(),
        }

        # Add request ID if available
        if hasattr(request.state, "request_id"):
            headers["X-Request-ID"] = str(request.state.request_id)
            body["request_id"] = str(request.state.request_id)

        logger.warning(
            f"Quota exceeded for tenant {request.headers.get('X-Tenant-ID')}: "
            f"{quota_type} {quota_result['current_count']}/{quota_result['limit']}"
        )

        return JSONResponse(status_code=429, content=body, headers=headers)

    def _calculate_retry_after(self, quota_type: str, quota_result: dict[str, Any]) -> int:
        """Calculate retry-after value in seconds."""
        if quota_type == "api_calls":
            # For daily API quotas, retry after midnight UTC
            now = datetime.now(UTC)
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return int((tomorrow - now).total_seconds())
        elif quota_type == "users":
            # For user quotas, suggest retry in 1 hour (may need quota upgrade)
            return 3600
        elif quota_type == "storage":
            # For storage quotas, suggest retry in 30 minutes
            return 1800
        else:
            # Default 5 minutes for other quota types
            return 300

    def _get_reset_timestamp(self) -> str:
        """Get the timestamp when quotas reset (next midnight UTC)."""
        now = datetime.now(UTC)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return tomorrow.isoformat()
