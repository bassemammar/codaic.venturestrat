"""FastAPI REST API for Registry Service.

This module provides the REST API endpoints for service registration,
discovery, and health management.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from registry.api.exceptions import (
    ConflictError,
    ConsulUnavailableError,
    InternalError,
    NotFoundError,
    RegistryAPIError,
)
from registry.api.models import (
    DiscoverResponse,
    ExportRequest,
    ExportResponse,
    ExportStatusResponse,
    HealthInstanceCount,
    HealthOverviewResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    InstanceHealthDetail,
    ListServicesResponse,
    ManifestResponse,
    RegisterRequest,
    RegisterResponse,
    ServiceHealthResponse,
    ServiceHealthSummary,
    ServiceInstanceResponse,
    ServiceSummary,
    TenantCreateRequest,
    TenantDeleteRequest,
    TenantListResponse,
    TenantResponse,
    TenantSuspendRequest,
    TenantUpdateRequest,
)
from registry.consul_client import ConsulOperationError
from registry.export_service import TenantExportService
from registry.models import (
    HealthCheckConfig,
    HealthStatus,
    ServiceRegistration,
)
from registry.service import RegistryService
from registry.tenant_service import TenantService

logger = logging.getLogger(__name__)


# =============================================================================
# Dependency Injection
# =============================================================================

# Global service instances (set during app startup)
_registry_service: RegistryService | None = None
_tenant_service: TenantService | None = None


def get_registry_service() -> RegistryService:
    """Get the registry service instance.

    This is a FastAPI dependency that provides the registry service.
    """
    if _registry_service is None:
        raise HTTPException(
            status_code=503,
            detail="Registry service not initialized",
        )
    return _registry_service


def set_registry_service(service: RegistryService) -> None:
    """Set the registry service instance."""
    global _registry_service
    _registry_service = service


def get_tenant_service() -> TenantService:
    """Get the tenant service instance.

    This is a FastAPI dependency that provides the tenant service.
    """
    if _tenant_service is None:
        raise HTTPException(
            status_code=503,
            detail="Tenant service not initialized",
        )
    return _tenant_service


def set_tenant_service(service: TenantService) -> None:
    """Set the tenant service instance."""
    global _tenant_service
    _tenant_service = service


# =============================================================================
# Error Handlers
# =============================================================================


def create_error_response(
    error: RegistryAPIError,
    request_id: str | None = None,
) -> JSONResponse:
    """Create a standard error response."""
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "request_id": request_id,
            }
        },
    )


# =============================================================================
# App Factory
# =============================================================================


def create_app(
    consul_host: str = "localhost",
    consul_port: int = 8500,
    kafka_bootstrap_servers: str = "localhost:9092",
    lifespan=None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        consul_host: Consul server hostname.
        consul_port: Consul server port.
        kafka_bootstrap_servers: Kafka bootstrap servers.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="VentureStrat Registry Service",
        description="Service registry and discovery for the VentureStrat platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Register exception handlers
    @app.exception_handler(RegistryAPIError)
    async def registry_error_handler(request: Request, exc: RegistryAPIError):
        request_id = getattr(request.state, "request_id", None)
        return create_error_response(exc, request_id)

    @app.exception_handler(ConsulOperationError)
    async def consul_error_handler(request: Request, exc: ConsulOperationError):
        request_id = getattr(request.state, "request_id", None)
        error = ConsulUnavailableError(str(exc))
        return create_error_response(error, request_id)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception")
        request_id = getattr(request.state, "request_id", None)
        error = InternalError(f"An unexpected error occurred: {type(exc).__name__}")
        return create_error_response(error, request_id)

    # Include routers
    app.include_router(service_router, prefix="/api/v1")
    app.include_router(tenant_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")

    # Include pricing registry router
    from registry.api.pricing_router import pricing_router

    app.include_router(pricing_router, prefix="/api/v1")

    # Include calibration registry router
    from registry.api.calibration_router import calibration_router

    app.include_router(calibration_router, prefix="/api/v1")

    return app


# =============================================================================
# Service Router (Registration, Discovery, Deregistration)
# =============================================================================

from fastapi import APIRouter

service_router = APIRouter(tags=["Services"])


@service_router.post(
    "/services",
    response_model=RegisterResponse,
    status_code=201,
    summary="Register a service",
    description="Register a new service instance with the registry.",
)
async def register_service(
    request: RegisterRequest,
    registry: Annotated[RegistryService, Depends(get_registry_service)],
) -> RegisterResponse:
    """Register a service instance."""
    # Build health check config
    health_check = HealthCheckConfig()
    if request.health_check:
        health_check = request.health_check

    # Create registration
    registration = ServiceRegistration(
        name=request.name,
        version=request.version,
        instance_id=request.instance_id,
        address=request.address,
        port=request.port,
        protocol=request.protocol,
        depends=request.depends,
        provides=request.provides,
        health_check=health_check,
        tags=request.tags,
        metadata=request.metadata,
    )

    # Register
    await registry.register(registration)

    return RegisterResponse(
        instance_id=registration.instance_id,
        consul_service_id=registration.instance_id,
        registered_at=registration.registered_at,
        health_check_id=f"service:{registration.instance_id}",
    )


@service_router.get(
    "/services",
    response_model=ListServicesResponse,
    summary="List all services",
    description="Get an overview of all registered services.",
)
async def list_services(
    registry: Annotated[RegistryService, Depends(get_registry_service)],
    tags: Annotated[str | None, Query(description="Comma-separated tags to filter by")] = None,
    include_health: Annotated[bool, Query(description="Include health status")] = False,
) -> ListServicesResponse:
    """List all registered services."""
    services = await registry.list_services()

    # Filter by tags if provided
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    service_summaries = []
    for service_name, service_tags in services.items():
        # Apply tag filter
        if tag_list and not any(t in service_tags for t in tag_list):
            continue

        info = await registry.get_service_info(service_name)
        service_summaries.append(
            ServiceSummary(
                name=service_name,
                versions=info.get("versions", []),
                instance_count=info.get("instance_count", 0),
                healthy_count=info.get("healthy_count", 0),
                tags=service_tags,
            )
        )

    return ListServicesResponse(
        services=service_summaries,
        total_services=len(service_summaries),
    )


@service_router.get(
    "/services/{service_name}",
    response_model=DiscoverResponse,
    summary="Discover service instances",
    description="Find healthy instances of a service for load balancing.",
)
async def discover_service(
    service_name: Annotated[str, Path(description="Service name to discover")],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
    version: Annotated[str | None, Query(description="Semver constraint (e.g., ^1.0.0)")] = None,
    tags: Annotated[str | None, Query(description="Comma-separated tags to filter by")] = None,
    healthy_only: Annotated[bool, Query(description="Only return healthy instances")] = True,
) -> DiscoverResponse:
    """Discover service instances."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    instances = await registry.discover(
        service_name=service_name,
        version_constraint=version,
        tags=tag_list,
        healthy_only=healthy_only,
    )

    if not instances:
        raise NotFoundError(f"Service '{service_name}' not found")

    healthy_count = sum(1 for i in instances if i.health_status == HealthStatus.HEALTHY)

    return DiscoverResponse(
        service=service_name,
        instances=[
            ServiceInstanceResponse(
                instance_id=i.instance_id,
                address=i.address,
                port=i.port,
                protocol=i.protocol.value,
                version=i.version,
                health_status=i.health_status.value,
                tags=i.tags,
                metadata=i.metadata,
            )
            for i in instances
        ],
        total_instances=len(instances),
        healthy_instances=healthy_count,
    )


@service_router.delete(
    "/services/{instance_id}",
    status_code=204,
    summary="Deregister a service",
    description="Deregister a service instance from the registry.",
)
async def deregister_service(
    instance_id: Annotated[str, Path(description="Instance ID to deregister")],
    service_name: Annotated[str, Query(description="Service name")],
    version: Annotated[str, Query(description="Service version")],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
    reason: Annotated[str, Query(description="Deregistration reason")] = "graceful_shutdown",
) -> None:
    """Deregister a service instance."""
    await registry.deregister(
        instance_id=instance_id,
        service_name=service_name,
        version=version,
        reason=reason,
    )


@service_router.put(
    "/services/{instance_id}/heartbeat",
    response_model=HeartbeatResponse,
    summary="Send heartbeat",
    description="Send a heartbeat to indicate service is alive.",
)
async def send_heartbeat(
    instance_id: Annotated[str, Path(description="Instance ID")],
    request: HeartbeatRequest,
    registry: Annotated[RegistryService, Depends(get_registry_service)],
) -> HeartbeatResponse:
    """Send a heartbeat for an instance."""
    # In a full implementation, this would update Consul TTL check
    # For now, just return current status
    return HeartbeatResponse(
        instance_id=instance_id,
        status=request.status,
        last_heartbeat=datetime.now(UTC),
    )


@service_router.get(
    "/services/{service_name}/manifest",
    response_model=ManifestResponse,
    summary="Get service manifest",
    description="Retrieve the cached manifest for a service.",
)
async def get_manifest(
    service_name: Annotated[str, Path(description="Service name")],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
) -> ManifestResponse:
    """Get the cached manifest for a service."""
    manifest_key = f"{registry.KV_PREFIX}/{service_name}/manifest"
    manifest_json = await registry.consul.kv_get(manifest_key)

    if manifest_json is None:
        raise NotFoundError(f"Manifest for '{service_name}' not found")

    manifest_data = json.loads(manifest_json)

    return ManifestResponse(
        name=manifest_data.get("name", service_name),
        version=manifest_data.get("version", "0.0.0"),
        description=manifest_data.get("description"),
        depends=manifest_data.get("depends", []),
        provides=manifest_data.get("provides", {}),
        health=manifest_data.get("health", {}),
    )


# =============================================================================
# Health Router
# =============================================================================

health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get(
    "/headers",
    summary="Inspect request headers",
    description="Returns the request headers received by the backend service. Used for testing gateway header forwarding.",
)
async def inspect_headers(request: Request) -> dict:
    """Return the request headers for debugging/testing purposes."""
    return {
        "headers": dict(request.headers),
        "consumer_username": request.headers.get("X-Consumer-Username"),
        "consumer_id": request.headers.get("X-Consumer-ID"),
        "correlation_id": request.headers.get("X-Correlation-ID"),
        "forwarded_by": request.headers.get("X-Forwarded-By"),
        "service_version": request.headers.get("X-Service-Version"),
    }


@health_router.get(
    "/services",
    response_model=HealthOverviewResponse,
    summary="Get health overview",
    description="Get health status of all services.",
)
async def get_health_overview(
    registry: Annotated[RegistryService, Depends(get_registry_service)],
) -> HealthOverviewResponse:
    """Get health overview of all services."""
    overview = await registry.get_health_overview()

    # Determine overall status
    unhealthy = overview.get("unhealthy_instances", 0)
    total = overview.get("total_instances", 0)

    if total == 0:
        overall_status = "healthy"
    elif unhealthy == 0:
        overall_status = "healthy"
    elif unhealthy == total:
        overall_status = "critical"
    else:
        overall_status = "warning"

    service_summaries = []
    for name, counts in overview.get("services", {}).items():
        counts.get("total", 0)
        healthy = counts.get("healthy", 0)
        unhealthy_svc = counts.get("unhealthy", 0)

        if unhealthy_svc == 0:
            status = "healthy"
        elif healthy == 0:
            status = "critical"
        else:
            status = "warning"

        service_summaries.append(
            ServiceHealthSummary(
                name=name,
                status=status,
                instances=HealthInstanceCount(
                    healthy=healthy,
                    warning=0,  # We don't track warning separately yet
                    critical=unhealthy_svc,
                ),
            )
        )

    return HealthOverviewResponse(
        services=service_summaries,
        overall_status=overall_status,
    )


@health_router.get(
    "/services/{service_name}",
    response_model=ServiceHealthResponse,
    summary="Get service health",
    description="Get detailed health for a specific service.",
)
async def get_service_health(
    service_name: Annotated[str, Path(description="Service name")],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
) -> ServiceHealthResponse:
    """Get detailed health for a service."""
    instances = await registry.discover(service_name, healthy_only=False)

    if not instances:
        raise NotFoundError(f"Service '{service_name}' not found")

    # Determine overall status
    statuses = [i.health_status for i in instances]
    if all(s == HealthStatus.HEALTHY for s in statuses):
        status = "healthy"
    elif any(s == HealthStatus.CRITICAL for s in statuses):
        status = "critical"
    else:
        status = "warning"

    instance_details = []
    for instance in instances:
        instance_details.append(
            InstanceHealthDetail(
                instance_id=instance.instance_id,
                status=instance.health_status.value,
                checks=[],  # Would be populated from Consul health checks
                uptime_seconds=None,  # Would be calculated from registration time
            )
        )

    return ServiceHealthResponse(
        service=service_name,
        status=status,
        instances=instance_details,
    )


# =============================================================================
# Tenant Export Router
# =============================================================================

export_router = APIRouter(prefix="/export", tags=["Tenant Export"])


async def get_export_service():
    """Dependency for getting export service instance."""
    # In production, this would be a singleton maintained by the main app
    export_service = TenantExportService()
    await export_service.initialize()
    try:
        yield export_service
    finally:
        await export_service.close()


@export_router.post(
    "/tenant/{tenant_id}",
    response_model=ExportResponse,
    summary="Export tenant data",
    description="Create an export of all data for the specified tenant.",
)
async def export_tenant_data(
    tenant_id: Annotated[str, Path(description="Tenant ID to export")],
    request: ExportRequest,
    export_service: Annotated[TenantExportService, Depends(get_export_service)],
) -> ExportResponse:
    """Export all data for a tenant."""
    try:
        from registry.export_service import ExportFormat, ExportOptions

        # Validate format
        valid_formats = ["json", "csv", "jsonl"]
        if request.format not in valid_formats:
            raise HTTPException(
                status_code=400, detail=f"Invalid format. Must be one of: {valid_formats}"
            )

        # Convert request to options
        options = ExportOptions(
            format=ExportFormat(request.format),
            compress=request.compress,
            encrypt=request.encrypt,
            include_deleted=request.include_deleted,
            include_audit_fields=request.include_audit_fields,
        )

        # Start export (this is async and may take time for large datasets)
        result = await export_service.export_tenant_data(
            tenant_id=tenant_id, options=options, reason=request.reason
        )

        return ExportResponse(
            export_id=result.export_id,
            status=result.status,
            tenant_id=result.tenant_id,
            created_at=result.created_at,
            estimated_completion=None,  # Could be calculated based on data size
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("export_endpoint_failed", tenant_id=tenant_id, error=str(e))
        raise HTTPException(status_code=500, detail="Export failed")


@export_router.get(
    "/status/{export_id}",
    response_model=ExportStatusResponse,
    summary="Get export status",
    description="Get the current status and details of an export.",
)
async def get_export_status(
    export_id: Annotated[str, Path(description="Export ID")],
    export_service: Annotated[TenantExportService, Depends(get_export_service)],
) -> ExportStatusResponse:
    """Get export status and details."""
    try:
        result = await export_service.get_export_result(export_id)

        if not result:
            raise NotFoundError(f"Export '{export_id}' not found")

        return ExportStatusResponse(
            export_id=result.export_id,
            tenant_id=result.tenant_id,
            status=result.status,
            file_path=result.file_path,
            file_size_bytes=result.file_size_bytes,
            records_exported=result.records_exported,
            models_exported=result.models_exported,
            created_at=result.created_at,
            completed_at=result.completed_at,
            error_message=result.error_message,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("export_status_endpoint_failed", export_id=export_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get export status")


# =============================================================================
# Tenant Management Router
# =============================================================================

tenant_router = APIRouter(prefix="/tenants", tags=["Tenants"])


@tenant_router.post(
    "/",
    response_model=TenantResponse,
    status_code=201,
    summary="Create tenant",
    description="Create a new tenant organization.",
)
async def create_tenant(
    request: TenantCreateRequest,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> TenantResponse:
    """Create a new tenant."""
    try:
        tenant = await tenant_service.create_tenant(
            slug=request.slug,
            name=request.name,
            config=request.config,
            admin_email=request.admin_email,
        )

        return TenantResponse(
            id=tenant.id,
            slug=tenant.slug,
            name=tenant.name,
            status=tenant.status,
            config=tenant.config,
            keycloak_org_id=tenant.keycloak_org_id,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            deleted_at=tenant.deleted_at,
        )

    except ValueError as e:
        if "already exists" in str(e):
            raise ConflictError(str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_tenant_failed: slug=%s, error=%s", request.slug, str(e))
        raise HTTPException(status_code=500, detail="Failed to create tenant")


@tenant_router.get(
    "/",
    response_model=TenantListResponse,
    summary="List tenants",
    description="List all tenants with optional filtering and pagination.",
)
async def list_tenants(
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    status: Annotated[
        str | None, Query(description="Filter by status (active, suspended, deleted)")
    ] = None,
    search: Annotated[str | None, Query(description="Search by name or slug")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
) -> TenantListResponse:
    """List tenants with filtering and pagination."""
    try:
        tenants, total = await tenant_service.list_tenants(
            status=status, search=search, page=page, page_size=page_size
        )

        tenant_responses = [
            TenantResponse(
                id=tenant.id,
                slug=tenant.slug,
                name=tenant.name,
                status=tenant.status,
                config=tenant.config,
                keycloak_org_id=tenant.keycloak_org_id,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                deleted_at=tenant.deleted_at,
            )
            for tenant in tenants
        ]

        return TenantListResponse(
            items=tenant_responses, total=total, page=page, page_size=page_size
        )

    except Exception as e:
        logger.error("list_tenants_failed: error=%s", str(e))
        raise HTTPException(status_code=500, detail="Failed to list tenants")


@tenant_router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant",
    description="Get a specific tenant by ID.",
)
async def get_tenant(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> TenantResponse:
    """Get a tenant by ID."""
    try:
        tenant = await tenant_service.get_tenant_by_id(tenant_id)

        if not tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        return TenantResponse(
            id=tenant.id,
            slug=tenant.slug,
            name=tenant.name,
            status=tenant.status,
            config=tenant.config,
            keycloak_org_id=tenant.keycloak_org_id,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            deleted_at=tenant.deleted_at,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("get_tenant_failed: tenant_id=%s, error=%s", tenant_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to get tenant")


@tenant_router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant",
    description="Update a tenant's name or configuration.",
)
async def update_tenant(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: TenantUpdateRequest,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> TenantResponse:
    """Update a tenant."""
    try:
        updated_tenant = await tenant_service.update_tenant(
            tenant_id=tenant_id, name=request.name, config=request.config
        )

        if not updated_tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        return TenantResponse(
            id=updated_tenant.id,
            slug=updated_tenant.slug,
            name=updated_tenant.name,
            status=updated_tenant.status,
            config=updated_tenant.config,
            keycloak_org_id=updated_tenant.keycloak_org_id,
            created_at=updated_tenant.created_at,
            updated_at=updated_tenant.updated_at,
            deleted_at=updated_tenant.deleted_at,
        )

    except NotFoundError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("update_tenant_failed: tenant_id=%s, error=%s", tenant_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to update tenant")


@tenant_router.post(
    "/{tenant_id}/suspend",
    response_model=TenantResponse,
    summary="Suspend tenant",
    description="Suspend a tenant, preventing access to the platform.",
)
async def suspend_tenant(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: TenantSuspendRequest,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> TenantResponse:
    """Suspend a tenant."""
    try:
        suspended_tenant = await tenant_service.suspend_tenant(
            tenant_id=tenant_id, reason=request.reason
        )

        if not suspended_tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        return TenantResponse(
            id=suspended_tenant.id,
            slug=suspended_tenant.slug,
            name=suspended_tenant.name,
            status=suspended_tenant.status,
            config=suspended_tenant.config,
            keycloak_org_id=suspended_tenant.keycloak_org_id,
            created_at=suspended_tenant.created_at,
            updated_at=suspended_tenant.updated_at,
            deleted_at=suspended_tenant.deleted_at,
        )

    except NotFoundError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("suspend_tenant_failed: tenant_id=%s, error=%s", tenant_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to suspend tenant")


@tenant_router.post(
    "/{tenant_id}/resume",
    response_model=TenantResponse,
    summary="Resume tenant",
    description="Resume a suspended tenant, restoring access to the platform.",
)
async def resume_tenant(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> TenantResponse:
    """Resume a suspended tenant."""
    try:
        resumed_tenant = await tenant_service.resume_tenant(tenant_id=tenant_id)

        if not resumed_tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        return TenantResponse(
            id=resumed_tenant.id,
            slug=resumed_tenant.slug,
            name=resumed_tenant.name,
            status=resumed_tenant.status,
            config=resumed_tenant.config,
            keycloak_org_id=resumed_tenant.keycloak_org_id,
            created_at=resumed_tenant.created_at,
            updated_at=resumed_tenant.updated_at,
            deleted_at=resumed_tenant.deleted_at,
        )

    except NotFoundError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("resume_tenant_failed: tenant_id=%s, error=%s", tenant_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to resume tenant")


@tenant_router.delete(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Delete tenant",
    description="Soft delete a tenant. Data will be retained for 30 days before permanent deletion.",
)
async def delete_tenant(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: TenantDeleteRequest,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> TenantResponse:
    """Delete a tenant."""
    try:
        deleted_tenant = await tenant_service.delete_tenant(
            tenant_id=tenant_id, reason=request.reason
        )

        if not deleted_tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        return TenantResponse(
            id=deleted_tenant.id,
            slug=deleted_tenant.slug,
            name=deleted_tenant.name,
            status=deleted_tenant.status,
            config=deleted_tenant.config,
            keycloak_org_id=deleted_tenant.keycloak_org_id,
            created_at=deleted_tenant.created_at,
            updated_at=deleted_tenant.updated_at,
            deleted_at=deleted_tenant.deleted_at,
        )

    except NotFoundError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("delete_tenant_failed: tenant_id=%s, error=%s", tenant_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to delete tenant")


@tenant_router.post(
    "/{tenant_id}/export",
    response_model=ExportResponse,
    status_code=201,
    summary="Export tenant data",
    description="Trigger GDPR data export for a tenant.",
)
async def export_tenant_data_gdpr(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: ExportRequest,
    export_service: Annotated[TenantExportService, Depends(get_export_service)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> ExportResponse:
    """Export all data for a tenant for GDPR compliance."""
    try:
        from registry.export_service import ExportFormat, ExportOptions

        # Validate tenant exists
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        # Convert request to export options
        options = ExportOptions(
            format=ExportFormat(request.format),
            compress=request.compress,
            encrypt=request.encrypt,
            include_deleted=request.include_deleted,
            include_audit_fields=request.include_audit_fields,
            batch_size=1000,
        )

        # Trigger export
        result = await export_service.export_tenant_data(
            tenant_id=tenant_id, reason=request.reason, options=options
        )

        # Calculate estimated completion if not completed yet
        estimated_completion = None
        if result.status == "in_progress":
            # Estimate 5 minutes from creation time
            from datetime import timedelta

            estimated_completion = result.created_at + timedelta(minutes=5)

        return ExportResponse(
            export_id=result.export_id,
            status=result.status,
            tenant_id=result.tenant_id,
            created_at=result.created_at,
            estimated_completion=estimated_completion,
        )

    except NotFoundError:
        raise
    except ValueError as e:
        logger.error(f"export_tenant_validation_failed: tenant_id={tenant_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"export_tenant_failed: tenant_id={tenant_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start tenant export")


@tenant_router.get(
    "/{tenant_id}/export/{export_id}",
    response_model=ExportStatusResponse,
    summary="Get export status",
    description="Get the status of a tenant data export.",
)
async def get_tenant_export_status(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    export_id: Annotated[str, Path(description="Export ID")],
    export_service: Annotated[TenantExportService, Depends(get_export_service)],
) -> ExportStatusResponse:
    """Get the status of a tenant data export."""
    try:
        result = await export_service.get_export_result(export_id)

        if not result:
            raise NotFoundError(f"Export '{export_id}' not found")

        # Verify the export belongs to the requested tenant
        if result.tenant_id != tenant_id:
            raise NotFoundError(f"Export '{export_id}' not found for tenant '{tenant_id}'")

        return ExportStatusResponse(
            export_id=result.export_id,
            tenant_id=result.tenant_id,
            status=result.status,
            file_path=result.file_path,
            file_size_bytes=result.file_size_bytes,
            records_exported=result.records_exported,
            models_exported=result.models_exported,
            created_at=result.created_at,
            completed_at=result.completed_at,
            error_message=result.error_message,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(
            f"export_status_endpoint_failed: tenant_id={tenant_id}, export_id={export_id}, error={str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to get export status")
