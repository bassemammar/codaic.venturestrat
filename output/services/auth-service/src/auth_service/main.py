"""FastAPI application entrypoint for Auth Service."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from auth_service.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level.upper())
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configure platform integration (if using BaseModel ORM)
try:
    from auth_service.infrastructure.platform import init_platform
    _has_platform = True
    # NOTE: ORM models are imported inside init_platform() after security is disabled
except ImportError:
    _has_platform = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("service_starting", service=settings.service_name)

    # Initialize platform integration (BaseModel ORM + Database)
    if _has_platform:
        try:
            registry_url = os.getenv("REGISTRY_SERVICE_URL", "http://localhost:8080")
            platform_mode = settings.platform_mode
            init_platform(registry_url=registry_url, platform_mode=platform_mode)
            logger.info("platform_initialized")
        except Exception as e:
            logger.error("platform_init_failed", error=str(e), error_type=type(e).__name__)
            # Fail fast - don't start service without proper platform setup
            raise RuntimeError(f"Failed to initialize platform: {e}") from e

    # Register with Consul
    try:
        from auth_service.integrations.consul import consul_client
        consul_client.connect()
        consul_client.register_service()
    except Exception as e:
        logger.error("consul_registration_failed", error=str(e))

    # Initialize Kafka event publisher
    try:
        from auth_service.integrations.events import event_publisher
        await event_publisher.initialize()
    except Exception as e:
        logger.error("kafka_initialization_failed", error=str(e))

    yield

    # Shutdown
    logger.info("service_shutting_down")

    # Close Kafka producer
    try:
        from auth_service.integrations.events import event_publisher
        await event_publisher.close()
    except Exception:
        pass

    # Deregister from Consul
    try:
        from auth_service.integrations.consul import consul_client
        consul_client.deregister_service()
    except Exception:
        pass


app = FastAPI(
    title="Auth Service",
    description="Authentication and authorization service",
    version=settings.service_version,
    lifespan=lifespan,
)

# Add middleware (order matters!)
from auth_service.middleware.security_headers import SecurityHeadersMiddleware
from auth_service.middleware.tenant import TenantContextMiddleware
from auth_service.middleware.rate_limit import RateLimitMiddleware
from auth_service.middleware.observability import ObservabilityMiddleware

# 1. Security headers (outermost)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Tenant context (extract X-Tenant-ID early)
app.add_middleware(TenantContextMiddleware)

# 3. Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window,
)

# 4. Observability
app.add_middleware(ObservabilityMiddleware)

# 4. CORS (configured properly, no wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Setup tracing
if settings.tracing_enabled:
    from auth_service.integrations.tracing import setup_tracing
    setup_tracing(app)


# =============================================================================
# Health Endpoints
# =============================================================================
from fastapi import status
from fastapi.responses import JSONResponse
from auth_service.health import get_detailed_health


@app.get("/health/live", tags=["Health"])
async def liveness():
    """Liveness probe - indicates the service process is running."""
    return {
        "status": "alive",
        "service": settings.service_name,
        "version": settings.service_version,
    }


@app.get("/health/ready", tags=["Health"], status_code=status.HTTP_200_OK)
async def readiness():
    """Readiness probe - indicates the service can accept traffic."""
    health_status = await get_detailed_health()

    if health_status["status"] != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )

    return health_status


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint."""
    from auth_service.integrations.metrics import metrics_endpoint
    return metrics_endpoint()


# =============================================================================
# API Routes
# =============================================================================
try:
    from auth_service.api.router_registry import register_entity_routers
    register_entity_routers(app)
except ImportError:
    pass


try:
    from auth_service.api.auth_service import router as auth_service_router
    app.include_router(auth_service_router, prefix="/api/v1", tags=["auth_service"])
except ImportError:
    pass

# Custom auth endpoints (login, logout, refresh, validate, me, change-password)
try:
    from auth_service.api.auth_endpoints import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
except ImportError:
    pass



@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Auth Service",
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs",
    }


def main():
    """Main entry point for the service."""
    import uvicorn

    uvicorn.run(
        "auth_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
