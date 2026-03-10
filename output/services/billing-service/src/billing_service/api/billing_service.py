"""API routes for Billing Service."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from billing_service.models import (
    BillingService,
    BillingServiceCreate,
    BillingServiceList,
    BillingServiceUpdate,
)
from billing_service.api.exceptions import (
    BillingServiceNotFoundError,
    BillingServiceValidationError,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory storage for demonstration (replace with actual database)
_billing_service_store: dict[UUID, BillingService] = {}


@router.get("/billing_service", response_model=BillingServiceList)
async def list_billing_service(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> BillingServiceList:
    """List billing_service entities with pagination and filtering."""
    logger.info(
        "listing_billing_service",
        offset=offset,
        limit=limit,
        name_filter=name_filter,
    )

    items = list(_billing_service_store.values())

    # Apply name filter if provided
    if name_filter:
        items = [item for item in items if name_filter.lower() in item.name.lower()]

    # Apply pagination
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return BillingServiceList(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/billing_service", response_model=BillingService, status_code=201)
async def create_billing_service(billing_service: BillingServiceCreate) -> BillingService:
    """Create a new billing_service entity."""
    logger.info("creating_billing_service", name=billing_service.name)

    # Validate unique name (in real implementation, this would be a database constraint)
    existing = [item for item in _billing_service_store.values() if item.name == billing_service.name]
    if existing:
        raise BillingServiceValidationError(f"BillingService with name '{billing_service.name}' already exists")

    # Create new entity
    new_billing_service = BillingService(**billing_service.model_dump())
    _billing_service_store[new_billing_service.id] = new_billing_service

    logger.info("billing_service_created", billing_service_id=str(new_billing_service.id))

    return new_billing_service


@router.get("/billing_service/{ billing_service_id }", response_model=BillingService)
async def get_billing_service(billing_service_id: UUID) -> BillingService:
    """Get a billing_service entity by ID."""
    logger.info("getting_billing_service", billing_service_id=str(billing_service_id))

    if billing_service_id not in _billing_service_store:
        raise BillingServiceNotFoundError(str(billing_service_id))

    return _billing_service_store[billing_service_id]


@router.put("/billing_service/{ billing_service_id }", response_model=BillingService)
async def update_billing_service(
    billing_service_id: UUID, update_data: BillingServiceUpdate
) -> BillingService:
    """Update a billing_service entity."""
    logger.info("updating_billing_service", billing_service_id=str(billing_service_id))

    if billing_service_id not in _billing_service_store:
        raise BillingServiceNotFoundError(str(billing_service_id))

    existing_billing_service = _billing_service_store[billing_service_id]

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(existing_billing_service, field, value)

    # Update timestamp
    from datetime import datetime
    existing_billing_service.updated_at = datetime.utcnow()

    logger.info("billing_service_updated", billing_service_id=str(billing_service_id))

    return existing_billing_service


@router.delete("/billing_service/{ billing_service_id }", status_code=204)
async def delete_billing_service(billing_service_id: UUID) -> None:
    """Delete a billing_service entity."""
    logger.info("deleting_billing_service", billing_service_id=str(billing_service_id))

    if billing_service_id not in _billing_service_store:
        raise BillingServiceNotFoundError(str(billing_service_id))

    del _billing_service_store[billing_service_id]

    logger.info("billing_service_deleted", billing_service_id=str(billing_service_id))
