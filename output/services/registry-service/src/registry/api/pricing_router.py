"""Pricing Registry REST API endpoints.

This module provides the REST API endpoints for pricing service registration,
capability discovery, and tenant pricing configuration management.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Optional

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from registry.api.exceptions import ConflictError, InternalError, NotFoundError
from registry.api.rest import get_tenant_service
from registry.models.pricer_capability import PricerCapability
from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.tenant_pricing_config import TenantPricingConfig
from registry.tenant_service import TenantService

logger = logging.getLogger(__name__)

pricing_router = APIRouter(prefix="/registry", tags=["Pricing Registry"])


# =============================================================================
# Request/Response Models
# =============================================================================


class PricerCapabilityModel(BaseModel):
    """Pricer capability model for API responses."""

    instrument_type: str = Field(..., description="Financial instrument type")
    model_type: Optional[str] = Field(None, description="Pricing model type")
    features: list[str] = Field(default_factory=list, description="Supported features")
    priority: int = Field(default=0, description="Priority for routing")


class PricerMetadataModel(BaseModel):
    """Pricer metadata model for registration."""

    pricer_id: str = Field(..., description="Unique pricer identifier")
    name: str = Field(..., description="Human-readable pricer name")
    version: str = Field(..., description="Pricer version")
    description: Optional[str] = Field(None, description="Pricer description")
    health_check_url: str = Field(..., description="Health check endpoint URL")
    pricing_url: str = Field(..., description="Base pricing API URL")
    batch_supported: bool = Field(False, description="Supports batch pricing")
    max_batch_size: Optional[int] = Field(None, description="Maximum batch size")
    status: str = Field(default="unknown", description="Current health status")
    capabilities: list[PricerCapabilityModel] = Field(default_factory=list)


class PricerRegistrationRequest(BaseModel):
    """Request model for pricer registration."""

    pricer_id: str = Field(..., description="Unique pricer identifier")
    name: str = Field(..., description="Human-readable pricer name")
    version: str = Field(..., description="Pricer version")
    description: Optional[str] = Field(None, description="Pricer description")
    health_check_url: str = Field(..., description="Health check endpoint URL")
    pricing_url: str = Field(..., description="Base pricing API URL")
    batch_supported: bool = Field(False, description="Supports batch pricing")
    max_batch_size: Optional[int] = Field(None, description="Maximum batch size")
    capabilities: list[PricerCapabilityModel] = Field(default_factory=list)


class PricerRegistrationResponse(BaseModel):
    """Response model for pricer registration."""

    pricer_id: str = Field(..., description="Registered pricer ID")
    status: str = Field(..., description="Registration status")
    registered_at: str = Field(..., description="Registration timestamp")


class PricerListResponse(BaseModel):
    """Response model for listing pricers."""

    pricers: list[PricerMetadataModel] = Field(default_factory=list)
    total_pricers: int = Field(..., description="Total number of pricers")


class PricerQueryResponse(BaseModel):
    """Response model for capability-based pricer query."""

    matching_pricers: list[PricerMetadataModel] = Field(default_factory=list)
    query_params: dict = Field(..., description="Query parameters used")


class HealthUpdateRequest(BaseModel):
    """Request model for health status updates."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    timestamp: str = Field(..., description="Update timestamp")


class HealthUpdateResponse(BaseModel):
    """Response model for health status updates."""

    pricer_id: str = Field(..., description="Pricer ID")
    status: str = Field(..., description="Updated health status")
    updated_at: str = Field(..., description="Update timestamp")


class HealthStatusResponse(BaseModel):
    """Response model for pricer health status."""

    pricer_id: str = Field(..., description="Pricer ID")
    name: str = Field(..., description="Pricer name")
    status: str = Field(..., description="Current health status")
    last_health_check: Optional[str] = Field(None, description="Last health check timestamp")
    health_check_failures: int = Field(..., description="Consecutive health check failures")
    response_time_ms: Optional[float] = Field(
        None, description="Last response time in milliseconds"
    )
    error_message: Optional[str] = Field(None, description="Last error message if unhealthy")


class HealthSummaryResponse(BaseModel):
    """Response model for overall health summary."""

    total_pricers: int = Field(..., description="Total number of pricers")
    healthy_pricers: int = Field(..., description="Number of healthy pricers")
    unhealthy_pricers: int = Field(..., description="Number of unhealthy pricers")
    unknown_pricers: int = Field(..., description="Number of pricers with unknown status")
    disabled_pricers: int = Field(..., description="Number of disabled pricers")
    health_ratio: float = Field(..., description="Ratio of healthy to total pricers")
    last_check_time: str = Field(..., description="Timestamp of last health check cycle")
    monitoring_enabled: bool = Field(..., description="Whether health monitoring is active")
    pricers: list[HealthStatusResponse] = Field(
        default_factory=list, description="Individual pricer statuses"
    )


class HealthMetricsResponse(BaseModel):
    """Response model for health monitoring metrics."""

    monitoring_config: dict = Field(..., description="Health monitoring configuration")
    metrics: dict = Field(..., description="Health monitoring metrics")
    circuit_breaker_states: dict = Field(
        default_factory=dict, description="Circuit breaker states by pricer"
    )


class CircuitBreakerStatusResponse(BaseModel):
    """Response model for circuit breaker status."""

    pricer_id: str = Field(..., description="Pricer ID")
    state: str = Field(..., description="Circuit breaker state (closed/open/half_open)")
    failure_count: int = Field(..., description="Current failure count")
    last_failure_time: Optional[str] = Field(None, description="Last failure timestamp")
    next_attempt_time: Optional[str] = Field(None, description="Next retry attempt time")


class TenantPricingConfigModel(BaseModel):
    """Tenant pricing configuration model."""

    tenant_id: str = Field(..., description="Tenant UUID")
    default_pricer_id: Optional[str] = Field(None, description="Default pricer")
    fallback_pricer_id: Optional[str] = Field(None, description="Fallback pricer")
    config_json: dict = Field(default_factory=dict, description="Configuration JSON")


class TenantPricingConfigRequest(BaseModel):
    """Request model for tenant pricing configuration."""

    default_pricer_id: Optional[str] = Field(None, description="Default pricer")
    fallback_pricer_id: Optional[str] = Field(None, description="Fallback pricer")
    allowed_pricers: Optional[list[str]] = Field(None, description="Allowed pricers")
    features: Optional[list[str]] = Field(None, description="Enabled features")
    max_batch_size: Optional[int] = Field(None, description="Maximum batch size")
    custom_curves_allowed: Optional[bool] = Field(None, description="Allow custom curves")
    advanced_models_allowed: Optional[bool] = Field(None, description="Allow advanced models")


class TenantPricingConfigResponse(BaseModel):
    """Response model for tenant pricing configuration."""

    tenant_id: str = Field(..., description="Tenant UUID")
    default_pricer_id: Optional[str] = Field(None, description="Default pricer")
    fallback_pricer_id: Optional[str] = Field(None, description="Fallback pricer")
    config_json: dict = Field(default_factory=dict, description="Configuration JSON")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")


# =============================================================================
# Dependencies
# =============================================================================


async def get_pricing_repository():
    """Get pricing repository dependency."""
    from registry.repositories.pricing_repository import PricingRepository

    # In a real implementation, this would be injected properly
    repo = PricingRepository()
    await repo.initialize()
    try:
        yield repo
    finally:
        await repo.close()


async def get_redis_client():
    """Get Redis client dependency for caching."""
    from registry.config import settings

    # Create Redis client with connection pool
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    client = redis.from_url(redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


# =============================================================================
# Pricer Registration Endpoints
# =============================================================================


@pricing_router.post(
    "/pricers",
    response_model=PricerRegistrationResponse,
    status_code=201,
    summary="Register a pricer service",
    description="Register a new pricing service with capabilities",
)
async def register_pricer(
    request: PricerRegistrationRequest, repo=Depends(get_pricing_repository)
) -> PricerRegistrationResponse:
    """Register a pricer service on startup."""
    try:
        # Create pricer registry entry
        pricer = PricerRegistry(
            pricer_id=request.pricer_id,
            name=request.name,
            version=request.version,
            description=request.description,
            health_check_url=request.health_check_url,
            pricing_url=request.pricing_url,
            batch_supported=request.batch_supported,
            max_batch_size=request.max_batch_size,
            status=PricerStatus.HEALTHY,
        )

        # Save pricer
        saved_pricer = await repo.save_pricer(pricer)

        # Save capabilities
        for cap_data in request.capabilities:
            capability = PricerCapability(
                pricer_id=request.pricer_id,
                instrument_type=cap_data.instrument_type,
                model_type=cap_data.model_type,
                features=cap_data.features,
                priority=cap_data.priority,
            )
            await repo.save_capability(capability)

        logger.info(f"Registered pricer: {request.pricer_id}")

        return PricerRegistrationResponse(
            pricer_id=saved_pricer.pricer_id,
            status="registered",
            registered_at=saved_pricer.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to register pricer {request.pricer_id}: {str(e)}")
        if "already exists" in str(e):
            raise ConflictError(f"Pricer {request.pricer_id} already registered")
        raise InternalError(f"Registration failed: {str(e)}")


@pricing_router.get(
    "/pricers",
    response_model=PricerListResponse,
    summary="List all registered pricers",
    description="Get all registered pricing services with their metadata",
)
async def list_pricers(
    status: Annotated[Optional[str], Query(description="Filter by status")] = None,
    repo=Depends(get_pricing_repository),
) -> PricerListResponse:
    """List all registered pricers."""
    try:
        pricers = await repo.list_pricers(status=status)

        pricer_models = []
        for pricer in pricers:
            capabilities = await repo.get_pricer_capabilities(pricer.pricer_id)

            cap_models = [
                PricerCapabilityModel(
                    instrument_type=cap.instrument_type,
                    model_type=cap.model_type,
                    features=cap.features or [],
                    priority=cap.priority,
                )
                for cap in capabilities
            ]

            pricer_models.append(
                PricerMetadataModel(
                    pricer_id=pricer.pricer_id,
                    name=pricer.name,
                    version=pricer.version,
                    description=pricer.description,
                    health_check_url=pricer.health_check_url,
                    pricing_url=pricer.pricing_url,
                    batch_supported=pricer.batch_supported,
                    max_batch_size=pricer.max_batch_size,
                    status=pricer.status.value
                    if hasattr(pricer.status, "value")
                    else str(pricer.status),
                    capabilities=cap_models,
                )
            )

        return PricerListResponse(pricers=pricer_models, total_pricers=len(pricer_models))

    except Exception as e:
        logger.error(f"Failed to list pricers: {str(e)}")
        raise InternalError(f"Failed to list pricers: {str(e)}")


# =============================================================================
# Capability Query Endpoints
# =============================================================================


@pricing_router.get(
    "/pricers/query",
    response_model=PricerQueryResponse,
    summary="Query pricers by capability",
    description="Find pricers that match specific capability requirements",
)
async def query_pricers(
    instrument_type: Annotated[str, Query(description="Required instrument type")],
    model_type: Annotated[Optional[str], Query(description="Required model type")] = None,
    feature: Annotated[Optional[str], Query(description="Required feature")] = None,
    repo=Depends(get_pricing_repository),
    redis_client=Depends(get_redis_client),
) -> PricerQueryResponse:
    """Query pricers by capability requirements with Redis caching (5 min TTL)."""
    try:
        # Normalize enum-style instrument types (InstrumentType.SWAP -> swap)
        if "." in instrument_type:
            instrument_type = instrument_type.split(".")[-1].lower()

        # Build query parameters
        query_params = {"instrument_type": instrument_type}
        if model_type:
            query_params["model_type"] = model_type
        if feature:
            query_params["feature"] = feature

        # Generate cache key
        cache_key_parts = [f"pricer:query:{instrument_type}"]
        if model_type:
            cache_key_parts.append(f"model:{model_type}")
        if feature:
            cache_key_parts.append(f"feature:{feature}")
        cache_key = ":".join(cache_key_parts)

        # Try to get from cache
        try:
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for query: {cache_key}")
                cached_data = json.loads(cached_result)
                return PricerQueryResponse(**cached_data)
        except Exception as cache_error:
            # Log cache error but continue with database query
            logger.warning(f"Redis cache read failed: {cache_error}")

        # Cache miss - query database
        logger.debug(f"Cache miss for query: {cache_key}")
        logger.info(
            f"[DEBUG] Querying capabilities with instrument_type={instrument_type}, model_type={model_type}, feature={feature}"
        )

        # Find matching capabilities
        capabilities = await repo.query_capabilities(
            instrument_type=instrument_type, model_type=model_type, feature=feature
        )

        logger.info(
            f"[DEBUG] Found {len(capabilities)} matching capabilities: {[(c.pricer_id, c.instrument_type) for c in capabilities]}"
        )

        # Get unique pricers
        pricer_ids = list(set(cap.pricer_id for cap in capabilities))
        logger.info(f"[DEBUG] Unique pricer_ids from capabilities: {pricer_ids}")

        # Build response
        matching_pricers = []
        for pricer_id in pricer_ids:
            pricer = await repo.get_pricer(pricer_id)
            logger.info(
                f"[DEBUG] Retrieved pricer {pricer_id}: exists={pricer is not None}, status={pricer.status if pricer else 'N/A'}, is_healthy={pricer.is_healthy() if pricer else 'N/A'}"
            )
            if pricer:
                pricer_capabilities = await repo.get_pricer_capabilities(pricer_id)

                cap_models = [
                    PricerCapabilityModel(
                        instrument_type=cap.instrument_type,
                        model_type=cap.model_type,
                        features=cap.features or [],
                        priority=cap.priority,
                    )
                    for cap in pricer_capabilities
                ]

                matching_pricers.append(
                    PricerMetadataModel(
                        pricer_id=pricer.pricer_id,
                        name=pricer.name,
                        version=pricer.version,
                        description=pricer.description,
                        health_check_url=pricer.health_check_url,
                        pricing_url=pricer.pricing_url,
                        batch_supported=pricer.batch_supported,
                        max_batch_size=pricer.max_batch_size,
                        status=pricer.status.value
                        if hasattr(pricer.status, "value")
                        else str(pricer.status),
                        capabilities=cap_models,
                    )
                )

        # Sort by highest priority capability match
        matching_pricers.sort(
            key=lambda p: max(
                (cap.priority for cap in p.capabilities if cap.instrument_type == instrument_type),
                default=0,
            ),
            reverse=True,
        )

        response = PricerQueryResponse(matching_pricers=matching_pricers, query_params=query_params)

        # Cache the result with 5 minute TTL
        try:
            cache_value = response.model_dump_json()
            await redis_client.setex(cache_key, 300, cache_value)  # 300 seconds = 5 minutes
            logger.debug(f"Cached query result: {cache_key}")
        except Exception as cache_error:
            # Log cache error but don't fail the request
            logger.warning(f"Redis cache write failed: {cache_error}")

        return response

    except Exception as e:
        logger.error(f"Failed to query pricers: {str(e)}")
        raise InternalError(f"Failed to query pricers: {str(e)}")


@pricing_router.get(
    "/pricers/{pricer_id}",
    response_model=PricerMetadataModel,
    summary="Get pricer metadata",
    description="Get detailed metadata for a specific pricer",
)
async def get_pricer(
    pricer_id: Annotated[str, Path(description="Pricer ID")], repo=Depends(get_pricing_repository)
) -> PricerMetadataModel:
    """Get detailed metadata for a specific pricer."""
    try:
        pricer = await repo.get_pricer(pricer_id)
        if not pricer:
            raise NotFoundError(f"Pricer '{pricer_id}' not found")

        capabilities = await repo.get_pricer_capabilities(pricer_id)

        cap_models = [
            PricerCapabilityModel(
                instrument_type=cap.instrument_type,
                model_type=cap.model_type,
                features=cap.features or [],
                priority=cap.priority,
            )
            for cap in capabilities
        ]

        return PricerMetadataModel(
            pricer_id=pricer.pricer_id,
            name=pricer.name,
            version=pricer.version,
            description=pricer.description,
            health_check_url=pricer.health_check_url,
            pricing_url=pricer.pricing_url,
            batch_supported=pricer.batch_supported,
            max_batch_size=pricer.max_batch_size,
            capabilities=cap_models,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get pricer {pricer_id}: {str(e)}")
        raise InternalError(f"Failed to get pricer: {str(e)}")


# =============================================================================
# Health Management Endpoints
# =============================================================================


@pricing_router.put(
    "/pricers/{pricer_id}/health",
    response_model=HealthUpdateResponse,
    summary="Update pricer health status",
    description="Update the health status of a registered pricer",
)
async def update_pricer_health(
    pricer_id: Annotated[str, Path(description="Pricer ID")],
    request: HealthUpdateRequest,
    repo=Depends(get_pricing_repository),
) -> HealthUpdateResponse:
    """Update pricer health status."""
    try:
        pricer = await repo.get_pricer(pricer_id)
        if not pricer:
            raise NotFoundError(f"Pricer '{pricer_id}' not found")

        # Update health status
        if request.status == "healthy":
            updated_pricer = pricer.mark_healthy()
        else:
            updated_pricer = pricer.mark_unhealthy()

        # Save updated pricer
        saved_pricer = await repo.save_pricer(updated_pricer)

        logger.info(f"Updated pricer health: {pricer_id} -> {request.status}")

        return HealthUpdateResponse(
            pricer_id=saved_pricer.pricer_id,
            status=saved_pricer.status,
            updated_at=saved_pricer.updated_at.isoformat(),
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to update pricer health {pricer_id}: {str(e)}")
        raise InternalError(f"Failed to update health: {str(e)}")


@pricing_router.get(
    "/health/summary",
    response_model=HealthSummaryResponse,
    summary="Get overall health summary",
    description="Get aggregated health status of all registered pricers",
)
async def get_health_summary(
    repo=Depends(get_pricing_repository),
    include_details: Annotated[
        bool, Query(description="Include individual pricer details")
    ] = False,
) -> HealthSummaryResponse:
    """Get overall health summary of all pricers."""
    try:
        # Get all pricers
        pricers = await repo.list_pricers()

        # Count by status
        status_counts = {
            PricerStatus.HEALTHY: 0,
            PricerStatus.UNHEALTHY: 0,
            PricerStatus.UNKNOWN: 0,
            PricerStatus.DISABLED: 0,
        }

        pricer_details = []

        for pricer in pricers:
            status = PricerStatus(pricer.status)
            status_counts[status] += 1

            if include_details:
                # Get health monitoring status if available
                response_time = None
                error_message = None

                # Check if health monitoring service is available
                try:
                    from registry.health_monitor import HealthMonitoringManager

                    # This would be injected in a real implementation
                    # For now, we'll use the database fields
                    pass
                except ImportError:
                    pass

                pricer_details.append(
                    HealthStatusResponse(
                        pricer_id=pricer.pricer_id,
                        name=pricer.name,
                        status=pricer.status,
                        last_health_check=pricer.last_health_check.isoformat()
                        if pricer.last_health_check
                        else None,
                        health_check_failures=pricer.health_check_failures or 0,
                        response_time_ms=response_time,
                        error_message=error_message,
                    )
                )

        total_pricers = len(pricers)
        healthy_pricers = status_counts[PricerStatus.HEALTHY]
        health_ratio = healthy_pricers / total_pricers if total_pricers > 0 else 1.0

        return HealthSummaryResponse(
            total_pricers=total_pricers,
            healthy_pricers=healthy_pricers,
            unhealthy_pricers=status_counts[PricerStatus.UNHEALTHY],
            unknown_pricers=status_counts[PricerStatus.UNKNOWN],
            disabled_pricers=status_counts[PricerStatus.DISABLED],
            health_ratio=health_ratio,
            last_check_time=datetime.now(UTC).isoformat(),
            monitoring_enabled=False,  # Would check actual monitoring service status
            pricers=pricer_details if include_details else [],
        )

    except Exception as e:
        logger.error(f"Failed to get health summary: {str(e)}")
        raise InternalError(f"Failed to get health summary: {str(e)}")


@pricing_router.get(
    "/health/metrics",
    response_model=HealthMetricsResponse,
    summary="Get health monitoring metrics",
    description="Get detailed health monitoring metrics and configuration",
)
async def get_health_metrics() -> HealthMetricsResponse:
    """Get health monitoring metrics and configuration."""
    try:
        # In a real implementation, this would get metrics from the health monitoring service
        # For now, return default structure

        monitoring_config = {
            "check_interval_seconds": 30,
            "timeout_seconds": 10,
            "failure_threshold": 3,
            "recovery_threshold": 2,
            "retry_backoff_seconds": 60,
            "max_concurrent_checks": 10,
        }

        metrics = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "success_rate": 1.0,
            "last_check_duration_seconds": 0.0,
            "is_running": False,
        }

        circuit_breaker_states = {}

        return HealthMetricsResponse(
            monitoring_config=monitoring_config,
            metrics=metrics,
            circuit_breaker_states=circuit_breaker_states,
        )

    except Exception as e:
        logger.error(f"Failed to get health metrics: {str(e)}")
        raise InternalError(f"Failed to get health metrics: {str(e)}")


@pricing_router.get(
    "/health/pricers/{pricer_id}",
    response_model=HealthStatusResponse,
    summary="Get pricer health status",
    description="Get detailed health status for a specific pricer",
)
async def get_pricer_health_status(
    pricer_id: Annotated[str, Path(description="Pricer ID")], repo=Depends(get_pricing_repository)
) -> HealthStatusResponse:
    """Get detailed health status for a specific pricer."""
    try:
        pricer = await repo.get_pricer(pricer_id)
        if not pricer:
            raise NotFoundError(f"Pricer '{pricer_id}' not found")

        # Get additional health monitoring data if available
        response_time = None
        error_message = None

        # In a real implementation, this would query the health monitoring service
        # For now, use basic database fields

        return HealthStatusResponse(
            pricer_id=pricer.pricer_id,
            name=pricer.name,
            status=pricer.status,
            last_health_check=pricer.last_health_check.isoformat()
            if pricer.last_health_check
            else None,
            health_check_failures=pricer.health_check_failures or 0,
            response_time_ms=response_time,
            error_message=error_message,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get pricer health status {pricer_id}: {str(e)}")
        raise InternalError(f"Failed to get pricer health status: {str(e)}")


@pricing_router.get(
    "/health/circuit-breakers",
    response_model=list[CircuitBreakerStatusResponse],
    summary="Get circuit breaker statuses",
    description="Get circuit breaker status for all pricers",
)
async def get_circuit_breaker_statuses(
    repo=Depends(get_pricing_repository),
) -> list[CircuitBreakerStatusResponse]:
    """Get circuit breaker statuses for all pricers."""
    try:
        pricers = await repo.list_pricers()
        statuses = []

        for pricer in pricers:
            # In a real implementation, this would query the actual circuit breaker states
            # For now, infer state from health status
            if pricer.status == PricerStatus.HEALTHY.value:
                state = "closed"
                failure_count = 0
            elif pricer.status == PricerStatus.UNHEALTHY.value:
                state = "open"
                failure_count = pricer.health_check_failures or 0
            else:
                state = "unknown"
                failure_count = 0

            statuses.append(
                CircuitBreakerStatusResponse(
                    pricer_id=pricer.pricer_id,
                    state=state,
                    failure_count=failure_count,
                    last_failure_time=pricer.last_health_check.isoformat()
                    if pricer.last_health_check and failure_count > 0
                    else None,
                    next_attempt_time=None,  # Would calculate based on backoff strategy
                )
            )

        return statuses

    except Exception as e:
        logger.error(f"Failed to get circuit breaker statuses: {str(e)}")
        raise InternalError(f"Failed to get circuit breaker statuses: {str(e)}")


# =============================================================================
# Tenant Pricing Configuration Endpoints
# =============================================================================


@pricing_router.get(
    "/tenants/{tenant_id}/pricing-config",
    response_model=TenantPricingConfigResponse,
    summary="Get tenant pricing configuration",
    description="Get pricing configuration for a specific tenant",
)
async def get_tenant_pricing_config(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    tenant_service: TenantService = Depends(get_tenant_service),
    repo=Depends(get_pricing_repository),
) -> TenantPricingConfigResponse:
    """Get tenant pricing configuration."""
    try:
        # Verify tenant exists
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        # Get pricing configuration
        config = await repo.get_tenant_pricing_config(tenant_id)
        if not config:
            # Create default configuration if none exists
            config = TenantPricingConfig.create_default_tenant_config(tenant_id)
            config = await repo.save_tenant_pricing_config(config)

        return TenantPricingConfigResponse(
            tenant_id=str(config.tenant_id),
            default_pricer_id=config.default_pricer_id,
            fallback_pricer_id=config.fallback_pricer_id,
            config_json=config.config_json or {},
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant pricing config {tenant_id}: {str(e)}")
        raise InternalError(f"Failed to get pricing configuration: {str(e)}")


@pricing_router.put(
    "/tenants/{tenant_id}/pricing-config",
    response_model=TenantPricingConfigResponse,
    summary="Update tenant pricing configuration",
    description="Update pricing configuration for a specific tenant",
)
async def update_tenant_pricing_config(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: TenantPricingConfigRequest,
    tenant_service: TenantService = Depends(get_tenant_service),
    repo=Depends(get_pricing_repository),
) -> TenantPricingConfigResponse:
    """Update tenant pricing configuration."""
    try:
        # Verify tenant exists
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")

        # Get existing configuration
        config = await repo.get_tenant_pricing_config(tenant_id)
        if not config:
            config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Build updated configuration
        new_config_json = dict(config.config_json) if config.config_json else {}

        if request.allowed_pricers is not None:
            new_config_json["allowed_pricers"] = request.allowed_pricers
        if request.features is not None:
            new_config_json["features"] = request.features
        if request.max_batch_size is not None:
            new_config_json["max_batch_size"] = request.max_batch_size
        if request.custom_curves_allowed is not None:
            new_config_json["custom_curves_allowed"] = request.custom_curves_allowed
        if request.advanced_models_allowed is not None:
            new_config_json["advanced_models_allowed"] = request.advanced_models_allowed

        # Update configuration
        updated_config = config.update_configuration(new_config_json)

        # Update pricers if specified
        if request.default_pricer_id is not None:
            updated_config = updated_config.set_default_pricer(request.default_pricer_id)
        if request.fallback_pricer_id is not None:
            updated_config = updated_config.set_fallback_pricer(request.fallback_pricer_id)

        # Save updated configuration
        saved_config = await repo.save_tenant_pricing_config(updated_config)

        logger.info(f"Updated tenant pricing config: {tenant_id}")

        return TenantPricingConfigResponse(
            tenant_id=str(saved_config.tenant_id),
            default_pricer_id=saved_config.default_pricer_id,
            fallback_pricer_id=saved_config.fallback_pricer_id,
            config_json=saved_config.config_json or {},
            created_at=saved_config.created_at.isoformat(),
            updated_at=saved_config.updated_at.isoformat(),
        )

    except NotFoundError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update tenant pricing config {tenant_id}: {str(e)}")
        raise InternalError(f"Failed to update pricing configuration: {str(e)}")
