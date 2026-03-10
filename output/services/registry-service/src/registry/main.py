"""FastAPI application entrypoint for Registry Service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from venturestrat_observability import ObservabilityMiddleware, get_metrics_api

from registry.api.rest import create_app as create_rest_app
from registry.api.rest import set_registry_service, set_tenant_service
from registry.config import settings
from registry.consul_client import ConsulClient
from registry.events import EventPublisher
from registry.health import HealthManager
from registry.service import RegistryService
from registry.db_session import close_db, init_db
from registry.health_monitor import HealthCheckConfig, HealthMonitoringService
from registry.tenant_purge_scheduler import create_tenant_purge_scheduler
from registry.tenant_service import TenantService

# Note: Structured logging is configured by ObservabilityMiddleware
logger = structlog.get_logger(__name__)

# Global tenant service instance
tenant_service = TenantService()

# Global purge scheduler instance
purge_scheduler = None

# Global gRPC server instance
grpc_server = None

# Global health monitoring service instance
health_monitor = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    global purge_scheduler, grpc_server, health_monitor

    # Startup
    logger.info(
        "starting_registry_service",
        service=settings.service_name,
        version=settings.service_version,
    )

    # Initialize database session manager
    try:
        init_db(settings.database_url)
        logger.info("database_session_manager_initialized")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise

    # Initialize tenant service and ensure system tenant exists
    try:
        await tenant_service.initialize()
        # Set up tenant service dependency
        set_tenant_service(tenant_service)
        logger.info("tenant_service_startup_complete")
    except Exception as e:
        logger.error("tenant_service_startup_failed", error=str(e))
        raise

    # Initialize and start tenant purge scheduler
    try:
        purge_scheduler = create_tenant_purge_scheduler(tenant_service)
        await purge_scheduler.start()
        logger.info("tenant_purge_scheduler_startup_complete")
    except Exception as e:
        logger.error("tenant_purge_scheduler_startup_failed", error=str(e))
        # Don't fail startup if purge scheduler fails
        logger.warning("continuing_without_purge_scheduler")

    # Initialize and start gRPC server for tenant management
    try:
        from registry.grpc_server import serve_tenant_grpc

        grpc_server = await serve_tenant_grpc(
            tenant_service=tenant_service, port=getattr(settings, "grpc_port", 50052)
        )
        logger.info("tenant_grpc_server_startup_complete", port=grpc_server.get_port())
    except Exception as e:
        logger.error("tenant_grpc_server_startup_failed", error=str(e))
        # Don't fail startup if gRPC server fails - REST API can still work
        logger.warning("continuing_without_grpc_server")

    # Seed calibrator registry data (idempotent - skips if already exists)
    try:
        from registry.repositories.calibration_repository import CalibrationRepository
        from registry.models.calibrator_registry import CalibratorRegistry
        from registry.models.calibrator_capability import CalibratorCapability

        cal_repo = CalibrationRepository()
        await cal_repo.initialize()

        # Check if calibrators already seeded
        existing = await cal_repo.list_calibrators()
        if not existing:
            logger.info("seeding_calibrator_registry")
            # Register calibrators
            quantlib = CalibratorRegistry.create_quantlib_calibrator()
            treasury = CalibratorRegistry.create_treasury_calibrator()
            await cal_repo.save_calibrator(quantlib)
            await cal_repo.save_calibrator(treasury)

            # Register capabilities
            for cap in CalibratorCapability.create_quantlib_capabilities():
                await cal_repo.save_capability(cap)
            for cap in CalibratorCapability.create_treasury_capabilities():
                await cal_repo.save_capability(cap)

            # Add CREDIT capability for quantlib (has /curves/credit/build)
            credit_cap = CalibratorCapability(
                calibrator_id="quantlib-v1.18",
                curve_type="CREDIT",
                asset_class="CREDIT",
                method="BOOTSTRAP",
                features=["cds_spread", "survival_probability"],
                priority=5,
            )
            await cal_repo.save_capability(credit_cap)

            logger.info(
                "calibrator_registry_seeded",
                calibrators=2,
                capabilities=10,
            )
        else:
            logger.info(
                "calibrator_registry_already_seeded",
                calibrator_count=len(existing),
            )
    except Exception as e:
        logger.error("calibrator_registry_seed_failed", error=str(e))
        logger.warning("continuing_without_calibrator_seed")

    # Initialize and start health monitoring service
    try:
        from registry.repositories.pricing_repository import PricingRepository

        pricing_repo = PricingRepository()
        await pricing_repo.initialize()

        config = HealthCheckConfig(
            check_interval_seconds=15,
            timeout_seconds=15,
            failure_threshold=6,
            recovery_threshold=2,
            max_concurrent_checks=10,
        )

        health_monitor = HealthMonitoringService(
            config=config,
            get_pricers_callback=pricing_repo.list_pricers,
            update_pricer_callback=pricing_repo.save_pricer,
        )
        await health_monitor.start()
        logger.info("health_monitoring_service_startup_complete", check_interval=10)
    except Exception as e:
        logger.error("health_monitoring_service_startup_failed", error=str(e))
        # Don't fail startup if health monitoring fails
        logger.warning("continuing_without_health_monitoring")

    # Initialize Consul client for service registration/discovery
    consul_client = None
    event_publisher = None
    try:
        consul_client = ConsulClient(
            host=getattr(settings, "consul_host", "consul-server-1"),
            port=getattr(settings, "consul_port", 8500),
        )
        event_publisher = EventPublisher(
            bootstrap_servers=getattr(settings, "kafka_bootstrap_servers", "kafka:29092"),
            topic=getattr(settings, "kafka_topic_lifecycle", "platform.services.lifecycle"),
        )
        await event_publisher.start()
        health_manager = HealthManager()
        registry_service = RegistryService(
            consul_client=consul_client,
            event_publisher=event_publisher,
            health_manager=health_manager,
        )
        set_registry_service(registry_service)
        logger.info("registry_service_initialized")
    except Exception as e:
        logger.error("registry_service_initialization_failed", error=str(e))
        logger.warning("continuing_without_registry_service")

    yield

    # Shutdown
    logger.info("shutting_down_registry_service")

    # Close database session manager
    try:
        await close_db()
        logger.info("database_session_manager_closed")
    except Exception as e:
        logger.error("database_shutdown_failed", error=str(e))

    # Stop event publisher
    if event_publisher:
        try:
            await event_publisher.stop()
            logger.info("event_publisher_shutdown_complete")
        except Exception as e:
            logger.error("event_publisher_shutdown_failed", error=str(e))

    # Stop health monitoring service
    if health_monitor:
        try:
            await health_monitor.stop()
            logger.info("health_monitoring_service_shutdown_complete")
        except Exception as e:
            logger.error("health_monitoring_service_shutdown_failed", error=str(e))

    # Stop gRPC server
    if grpc_server:
        try:
            await grpc_server.stop()
            logger.info("tenant_grpc_server_shutdown_complete")
        except Exception as e:
            logger.error("tenant_grpc_server_shutdown_failed", error=str(e))

    # Stop tenant purge scheduler
    if purge_scheduler:
        try:
            await purge_scheduler.stop()
            logger.info("tenant_purge_scheduler_shutdown_complete")
        except Exception as e:
            logger.error("tenant_purge_scheduler_shutdown_failed", error=str(e))

    # Close tenant service connections
    try:
        await tenant_service.close()
        logger.info("tenant_service_shutdown_complete")
    except Exception as e:
        logger.error("tenant_service_shutdown_failed", error=str(e))

    # TODO: Close Consul, Kafka, and database connections gracefully


# Create the REST API app with the lifespan handler
app = create_rest_app(lifespan=lifespan)

# Install observability middleware (metrics, logging, tracing, correlation IDs)
ObservabilityMiddleware.install(app)

# Initialize custom business metrics after observability middleware
try:
    metrics = get_metrics_api()

    # Gauge for tracking number of active registered services
    services_active_gauge = metrics.gauge(
        "treasury_registry_services_active",
        "Number of active registered services",
        labels=["service_type"],
    )

    # Counter for tracking health check executions
    health_checks_counter = metrics.counter(
        "treasury_registry_health_checks_total", "Total health check executions", labels=["status"]
    )

    # Initialize services active to 0 for different service types
    services_active_gauge.set(0, {"service_type": "fastapi"})
    services_active_gauge.set(0, {"service_type": "grpc"})
    services_active_gauge.set(0, {"service_type": "other"})

except Exception as e:
    logger.warning("Failed to initialize custom metrics", error=str(e))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Endpoints
# =============================================================================
@app.get("/health/live", tags=["health"])
async def liveness() -> dict:
    """Liveness probe - service is running."""
    try:
        health_checks_counter.labels(status="healthy").inc()
    except NameError:
        # Metrics not initialized, skip
        pass
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict:
    """Readiness probe - service is ready to accept traffic."""
    # Check tenant service health (includes PostgreSQL connection)
    tenant_healthy = await tenant_service.health_check()

    if not tenant_healthy:
        try:
            health_checks_counter.labels(status="unhealthy").inc()
        except NameError:
            # Metrics not initialized, skip
            pass
        return {"status": "not_ready", "reason": "tenant_service_unhealthy"}

    # TODO: Check health of Consul and Kafka connections

    try:
        health_checks_counter.labels(status="healthy").inc()
    except NameError:
        # Metrics not initialized, skip
        pass
    return {"status": "ready"}


# API routes are now handled by the REST API module


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
