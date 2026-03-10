"""Health check utilities for Auth Service."""

import asyncio
from typing import Any, Dict
import httpx
import structlog

from auth_service.config import settings

logger = structlog.get_logger(__name__)


async def check_database() -> bool:
    """Check database connectivity."""
    try:
        # TODO: Implement actual database health check for BaseModel
        return True
    except Exception as e:
        logger.warning("database_health_check_failed", error=str(e))
        return False


async def check_consul() -> bool:
    """Check Consul connectivity."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.consul_scheme}://{settings.consul_host}:{settings.consul_port}/v1/status/leader"
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning("consul_health_check_failed", error=str(e))
        return False


async def check_kafka() -> bool:
    """Check Kafka connectivity."""
    try:
        from auth_service.integrations.events import event_publisher
        return event_publisher._initialized
    except Exception as e:
        logger.warning("kafka_health_check_failed", error=str(e))
        return False


async def check_redis() -> bool:
    """Check Redis connectivity (if Redis integration added)."""
    # TODO: Implement when Redis caching is added
    return True


async def get_detailed_health() -> Dict[str, Any]:
    """Get detailed health status including dependency checks."""
    try:
        checks_tasks = {
            "database": check_database(),
            "consul": check_consul(),
            "kafka": check_kafka(),
            "redis": check_redis(),
        }

        # Wait for all checks (5 second timeout total)
        results = await asyncio.wait_for(
            asyncio.gather(
                *checks_tasks.values(),
                return_exceptions=True
            ),
            timeout=5.0
        )

        # Build check results
        checks = {}
        for (name, _), result in zip(checks_tasks.items(), results):
            if isinstance(result, Exception):
                checks[name] = {"status": "unhealthy", "error": str(result)}
            else:
                checks[name] = {"status": "healthy" if result else "unhealthy"}

        # Critical dependencies: database, kafka
        critical_checks = ["database", "kafka"]
        all_healthy = all(
            checks[dep]["status"] == "healthy"
            for dep in critical_checks
            if dep in checks
        )

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "service": {
                "name": settings.service_name,
                "version": settings.service_version,
            },
            "checks": checks,
        }

    except asyncio.TimeoutError:
        logger.error("health_check_timeout")
        return {
            "status": "unhealthy",
            "error": "Health check timeout",
            "checks": {},
        }
