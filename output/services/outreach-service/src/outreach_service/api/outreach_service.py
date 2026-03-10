"""API routes for Outreach Service."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from outreach_service.models import (
    OutreachService,
    OutreachServiceCreate,
    OutreachServiceList,
    OutreachServiceUpdate,
)
from outreach_service.api.exceptions import (
    OutreachServiceNotFoundError,
    OutreachServiceValidationError,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory storage for demonstration (replace with actual database)
_outreach_service_store: dict[UUID, OutreachService] = {}


@router.get("/outreach_service", response_model=OutreachServiceList)
async def list_outreach_service(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> OutreachServiceList:
    """List outreach_service entities with pagination and filtering."""
    logger.info(
        "listing_outreach_service",
        offset=offset,
        limit=limit,
        name_filter=name_filter,
    )

    items = list(_outreach_service_store.values())

    # Apply name filter if provided
    if name_filter:
        items = [item for item in items if name_filter.lower() in item.name.lower()]

    # Apply pagination
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return OutreachServiceList(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/outreach_service", response_model=OutreachService, status_code=201)
async def create_outreach_service(outreach_service: OutreachServiceCreate) -> OutreachService:
    """Create a new outreach_service entity."""
    logger.info("creating_outreach_service", name=outreach_service.name)

    # Validate unique name (in real implementation, this would be a database constraint)
    existing = [item for item in _outreach_service_store.values() if item.name == outreach_service.name]
    if existing:
        raise OutreachServiceValidationError(f"OutreachService with name '{outreach_service.name}' already exists")

    # Create new entity
    new_outreach_service = OutreachService(**outreach_service.model_dump())
    _outreach_service_store[new_outreach_service.id] = new_outreach_service

    logger.info("outreach_service_created", outreach_service_id=str(new_outreach_service.id))

    return new_outreach_service


@router.get("/outreach_service/{ outreach_service_id }", response_model=OutreachService)
async def get_outreach_service(outreach_service_id: UUID) -> OutreachService:
    """Get a outreach_service entity by ID."""
    logger.info("getting_outreach_service", outreach_service_id=str(outreach_service_id))

    if outreach_service_id not in _outreach_service_store:
        raise OutreachServiceNotFoundError(str(outreach_service_id))

    return _outreach_service_store[outreach_service_id]


@router.put("/outreach_service/{ outreach_service_id }", response_model=OutreachService)
async def update_outreach_service(
    outreach_service_id: UUID, update_data: OutreachServiceUpdate
) -> OutreachService:
    """Update a outreach_service entity."""
    logger.info("updating_outreach_service", outreach_service_id=str(outreach_service_id))

    if outreach_service_id not in _outreach_service_store:
        raise OutreachServiceNotFoundError(str(outreach_service_id))

    existing_outreach_service = _outreach_service_store[outreach_service_id]

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(existing_outreach_service, field, value)

    # Update timestamp
    from datetime import datetime
    existing_outreach_service.updated_at = datetime.utcnow()

    logger.info("outreach_service_updated", outreach_service_id=str(outreach_service_id))

    return existing_outreach_service


@router.delete("/outreach_service/{ outreach_service_id }", status_code=204)
async def delete_outreach_service(outreach_service_id: UUID) -> None:
    """Delete a outreach_service entity."""
    logger.info("deleting_outreach_service", outreach_service_id=str(outreach_service_id))

    if outreach_service_id not in _outreach_service_store:
        raise OutreachServiceNotFoundError(str(outreach_service_id))

    del _outreach_service_store[outreach_service_id]

    logger.info("outreach_service_deleted", outreach_service_id=str(outreach_service_id))
