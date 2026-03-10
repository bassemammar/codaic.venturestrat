"""Calibration Registry REST API endpoints.

This module provides the REST API endpoints for calibration service registration,
capability discovery, and health management for the calibration pipeline.
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
from registry.models.calibrator_capability import CalibratorCapability
from registry.models.calibrator_registry import CalibratorRegistry, CalibratorStatus

logger = logging.getLogger(__name__)

calibration_router = APIRouter(prefix="/registry/calibration", tags=["Calibration Registry"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CalibratorCapabilityModel(BaseModel):
    """Calibrator capability model for API responses."""

    curve_type: str = Field(..., description="Curve type (FX_CURVE, IR_DISCOUNT, etc.)")
    asset_class: Optional[str] = Field(None, description="Asset class (FX, IR, CREDIT)")
    currency: Optional[str] = Field(None, description="Currency code (null = all)")
    method: Optional[str] = Field(None, description="Calibration method")
    features: list[str] = Field(default_factory=list, description="Supported features")
    priority: int = Field(default=100, description="Priority for routing")


class CalibratorMetadataModel(BaseModel):
    """Calibrator metadata model for responses."""

    calibrator_id: str = Field(..., description="Unique calibrator identifier")
    name: str = Field(..., description="Human-readable calibrator name")
    version: str = Field(..., description="Calibrator version")
    description: Optional[str] = Field(None, description="Description")
    calibration_url: str = Field(..., description="Base calibration API URL")
    health_check_url: Optional[str] = Field(None, description="Health check URL")
    supported_modes: dict = Field(default_factory=dict, description="Supported modes")
    status: str = Field(default="unknown", description="Current health status")
    capabilities: list[CalibratorCapabilityModel] = Field(default_factory=list)


class CalibratorRegistrationRequest(BaseModel):
    """Request model for calibrator registration."""

    calibrator_id: str = Field(..., description="Unique calibrator identifier")
    name: str = Field(..., description="Human-readable calibrator name")
    version: str = Field(..., description="Calibrator version")
    description: Optional[str] = Field(None, description="Description")
    calibration_url: str = Field(..., description="Base calibration API URL")
    health_check_url: Optional[str] = Field(None, description="Health check URL")
    supported_modes: dict = Field(default_factory=dict, description="Supported modes")
    capabilities: list[CalibratorCapabilityModel] = Field(default_factory=list)


class CalibratorRegistrationResponse(BaseModel):
    """Response model for calibrator registration."""

    calibrator_id: str = Field(..., description="Registered calibrator ID")
    status: str = Field(..., description="Registration status")
    registered_at: str = Field(..., description="Registration timestamp")


class CalibratorListResponse(BaseModel):
    """Response model for listing calibrators."""

    calibrators: list[CalibratorMetadataModel] = Field(default_factory=list)
    total_calibrators: int = Field(..., description="Total number of calibrators")


class CalibratorQueryResponse(BaseModel):
    """Response model for capability-based calibrator query."""

    matching_calibrators: list[CalibratorMetadataModel] = Field(default_factory=list)
    query_params: dict = Field(..., description="Query parameters used")


class CalibratorHealthUpdateRequest(BaseModel):
    """Request model for health status updates."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    timestamp: str = Field(..., description="Update timestamp")


class CalibratorHealthUpdateResponse(BaseModel):
    """Response model for health status updates."""

    calibrator_id: str = Field(..., description="Calibrator ID")
    status: str = Field(..., description="Updated health status")
    updated_at: str = Field(..., description="Update timestamp")


# =============================================================================
# Dependencies
# =============================================================================


async def get_calibration_repository():
    """Get calibration repository dependency."""
    from registry.repositories.calibration_repository import CalibrationRepository

    repo = CalibrationRepository()
    await repo.initialize()
    try:
        yield repo
    finally:
        await repo.close()


async def get_redis_client():
    """Get Redis client dependency for caching."""
    from registry.config import settings

    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    client = redis.from_url(redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


# =============================================================================
# Calibrator Registration Endpoints
# =============================================================================


@calibration_router.post(
    "/calibrators",
    response_model=CalibratorRegistrationResponse,
    status_code=201,
    summary="Register a calibrator service",
)
async def register_calibrator(
    request: CalibratorRegistrationRequest,
    repo=Depends(get_calibration_repository),
) -> CalibratorRegistrationResponse:
    """Register a calibrator service on startup."""
    try:
        calibrator = CalibratorRegistry(
            calibrator_id=request.calibrator_id,
            name=request.name,
            version=request.version,
            description=request.description,
            calibration_url=request.calibration_url,
            health_check_url=request.health_check_url,
            supported_modes=request.supported_modes,
            status=CalibratorStatus.HEALTHY,
        )

        saved = await repo.save_calibrator(calibrator)

        for cap_data in request.capabilities:
            capability = CalibratorCapability(
                calibrator_id=request.calibrator_id,
                curve_type=cap_data.curve_type,
                asset_class=cap_data.asset_class,
                currency=cap_data.currency,
                method=cap_data.method,
                features=cap_data.features,
                priority=cap_data.priority,
            )
            await repo.save_capability(capability)

        logger.info(f"Registered calibrator: {request.calibrator_id}")

        return CalibratorRegistrationResponse(
            calibrator_id=saved.calibrator_id,
            status="registered",
            registered_at=saved.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to register calibrator {request.calibrator_id}: {str(e)}")
        if "already exists" in str(e):
            raise ConflictError(f"Calibrator {request.calibrator_id} already registered")
        raise InternalError(f"Registration failed: {str(e)}")


@calibration_router.get(
    "/calibrators",
    response_model=CalibratorListResponse,
    summary="List all registered calibrators",
)
async def list_calibrators(
    status: Annotated[Optional[str], Query(description="Filter by status")] = None,
    repo=Depends(get_calibration_repository),
) -> CalibratorListResponse:
    """List all registered calibrators."""
    try:
        calibrators = await repo.list_calibrators(status=status)

        calibrator_models = []
        for cal in calibrators:
            capabilities = await repo.get_calibrator_capabilities(cal.calibrator_id)

            cap_models = [
                CalibratorCapabilityModel(
                    curve_type=cap.curve_type,
                    asset_class=cap.asset_class,
                    currency=cap.currency,
                    method=cap.method,
                    features=cap.features or [],
                    priority=cap.priority,
                )
                for cap in capabilities
            ]

            calibrator_models.append(
                CalibratorMetadataModel(
                    calibrator_id=cal.calibrator_id,
                    name=cal.name,
                    version=cal.version,
                    description=cal.description,
                    calibration_url=cal.calibration_url,
                    health_check_url=cal.health_check_url,
                    supported_modes=cal.supported_modes or {},
                    status=cal.status.value if hasattr(cal.status, "value") else str(cal.status),
                    capabilities=cap_models,
                )
            )

        return CalibratorListResponse(
            calibrators=calibrator_models, total_calibrators=len(calibrator_models)
        )

    except Exception as e:
        logger.error(f"Failed to list calibrators: {str(e)}")
        raise InternalError(f"Failed to list calibrators: {str(e)}")


# =============================================================================
# Capability Query Endpoints
# =============================================================================


@calibration_router.get(
    "/calibrators/query",
    response_model=CalibratorQueryResponse,
    summary="Query calibrators by capability",
)
async def query_calibrators(
    curve_type: Annotated[str, Query(description="Required curve type")],
    asset_class: Annotated[Optional[str], Query(description="Asset class filter")] = None,
    currency: Annotated[Optional[str], Query(description="Currency filter")] = None,
    method: Annotated[Optional[str], Query(description="Calibration method filter")] = None,
    repo=Depends(get_calibration_repository),
    redis_client=Depends(get_redis_client),
) -> CalibratorQueryResponse:
    """Query calibrators by capability requirements with Redis caching."""
    try:
        query_params = {"curve_type": curve_type}
        if asset_class:
            query_params["asset_class"] = asset_class
        if currency:
            query_params["currency"] = currency
        if method:
            query_params["method"] = method

        cache_key = f"calibrator:query:{':'.join(f'{k}={v}' for k, v in sorted(query_params.items()))}"

        # Try cache
        try:
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return CalibratorQueryResponse(**json.loads(cached_result))
        except Exception:
            pass

        # Query database
        capabilities = await repo.query_capabilities(
            curve_type=curve_type,
            asset_class=asset_class,
            currency=currency,
            method=method,
        )

        calibrator_ids = list(set(cap.calibrator_id for cap in capabilities))

        matching_calibrators = []
        for calibrator_id in calibrator_ids:
            cal = await repo.get_calibrator(calibrator_id)
            if cal:
                all_caps = await repo.get_calibrator_capabilities(calibrator_id)

                cap_models = [
                    CalibratorCapabilityModel(
                        curve_type=cap.curve_type,
                        asset_class=cap.asset_class,
                        currency=cap.currency,
                        method=cap.method,
                        features=cap.features or [],
                        priority=cap.priority,
                    )
                    for cap in all_caps
                ]

                matching_calibrators.append(
                    CalibratorMetadataModel(
                        calibrator_id=cal.calibrator_id,
                        name=cal.name,
                        version=cal.version,
                        description=cal.description,
                        calibration_url=cal.calibration_url,
                        health_check_url=cal.health_check_url,
                        supported_modes=cal.supported_modes or {},
                        status=cal.status.value if hasattr(cal.status, "value") else str(cal.status),
                        capabilities=cap_models,
                    )
                )

        # Sort by highest priority for the matching curve_type
        matching_calibrators.sort(
            key=lambda c: max(
                (cap.priority for cap in c.capabilities if cap.curve_type == curve_type),
                default=0,
            ),
            reverse=True,
        )

        response = CalibratorQueryResponse(
            matching_calibrators=matching_calibrators, query_params=query_params
        )

        # Cache with 5 min TTL
        try:
            await redis_client.setex(cache_key, 300, response.model_dump_json())
        except Exception:
            pass

        return response

    except Exception as e:
        logger.error(f"Failed to query calibrators: {str(e)}")
        raise InternalError(f"Failed to query calibrators: {str(e)}")


@calibration_router.get(
    "/calibrators/{calibrator_id}",
    response_model=CalibratorMetadataModel,
    summary="Get calibrator metadata",
)
async def get_calibrator(
    calibrator_id: Annotated[str, Path(description="Calibrator ID")],
    repo=Depends(get_calibration_repository),
) -> CalibratorMetadataModel:
    """Get detailed metadata for a specific calibrator."""
    try:
        cal = await repo.get_calibrator(calibrator_id)
        if not cal:
            raise NotFoundError(f"Calibrator '{calibrator_id}' not found")

        capabilities = await repo.get_calibrator_capabilities(calibrator_id)

        cap_models = [
            CalibratorCapabilityModel(
                curve_type=cap.curve_type,
                asset_class=cap.asset_class,
                currency=cap.currency,
                method=cap.method,
                features=cap.features or [],
                priority=cap.priority,
            )
            for cap in capabilities
        ]

        return CalibratorMetadataModel(
            calibrator_id=cal.calibrator_id,
            name=cal.name,
            version=cal.version,
            description=cal.description,
            calibration_url=cal.calibration_url,
            health_check_url=cal.health_check_url,
            supported_modes=cal.supported_modes or {},
            status=cal.status.value if hasattr(cal.status, "value") else str(cal.status),
            capabilities=cap_models,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get calibrator {calibrator_id}: {str(e)}")
        raise InternalError(f"Failed to get calibrator: {str(e)}")


# =============================================================================
# Health Management Endpoints
# =============================================================================


@calibration_router.put(
    "/calibrators/{calibrator_id}/health",
    response_model=CalibratorHealthUpdateResponse,
    summary="Update calibrator health status",
)
async def update_calibrator_health(
    calibrator_id: Annotated[str, Path(description="Calibrator ID")],
    request: CalibratorHealthUpdateRequest,
    repo=Depends(get_calibration_repository),
) -> CalibratorHealthUpdateResponse:
    """Update calibrator health status."""
    try:
        cal = await repo.get_calibrator(calibrator_id)
        if not cal:
            raise NotFoundError(f"Calibrator '{calibrator_id}' not found")

        if request.status == "healthy":
            updated = cal.mark_healthy()
        else:
            updated = cal.mark_unhealthy()

        saved = await repo.save_calibrator(updated)

        return CalibratorHealthUpdateResponse(
            calibrator_id=saved.calibrator_id,
            status=saved.status,
            updated_at=saved.updated_at.isoformat(),
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to update calibrator health {calibrator_id}: {str(e)}")
        raise InternalError(f"Failed to update health: {str(e)}")
