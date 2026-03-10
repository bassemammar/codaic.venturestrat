"""API routes for Crm Service."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from crm_service.models import (
    CrmService,
    CrmServiceCreate,
    CrmServiceList,
    CrmServiceUpdate,
)
from crm_service.api.exceptions import (
    CrmServiceNotFoundError,
    CrmServiceValidationError,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory storage for demonstration (replace with actual database)
_crm_service_store: dict[UUID, CrmService] = {}


@router.get("/crm_service", response_model=CrmServiceList)
async def list_crm_service(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> CrmServiceList:
    """List crm_service entities with pagination and filtering."""
    logger.info(
        "listing_crm_service",
        offset=offset,
        limit=limit,
        name_filter=name_filter,
    )

    items = list(_crm_service_store.values())

    # Apply name filter if provided
    if name_filter:
        items = [item for item in items if name_filter.lower() in item.name.lower()]

    # Apply pagination
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return CrmServiceList(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/crm_service", response_model=CrmService, status_code=201)
async def create_crm_service(crm_service: CrmServiceCreate) -> CrmService:
    """Create a new crm_service entity."""
    logger.info("creating_crm_service", name=crm_service.name)

    # Validate unique name (in real implementation, this would be a database constraint)
    existing = [item for item in _crm_service_store.values() if item.name == crm_service.name]
    if existing:
        raise CrmServiceValidationError(f"CrmService with name '{crm_service.name}' already exists")

    # Create new entity
    new_crm_service = CrmService(**crm_service.model_dump())
    _crm_service_store[new_crm_service.id] = new_crm_service

    logger.info("crm_service_created", crm_service_id=str(new_crm_service.id))

    return new_crm_service


@router.get("/crm_service/{ crm_service_id }", response_model=CrmService)
async def get_crm_service(crm_service_id: UUID) -> CrmService:
    """Get a crm_service entity by ID."""
    logger.info("getting_crm_service", crm_service_id=str(crm_service_id))

    if crm_service_id not in _crm_service_store:
        raise CrmServiceNotFoundError(str(crm_service_id))

    return _crm_service_store[crm_service_id]


@router.put("/crm_service/{ crm_service_id }", response_model=CrmService)
async def update_crm_service(
    crm_service_id: UUID, update_data: CrmServiceUpdate
) -> CrmService:
    """Update a crm_service entity."""
    logger.info("updating_crm_service", crm_service_id=str(crm_service_id))

    if crm_service_id not in _crm_service_store:
        raise CrmServiceNotFoundError(str(crm_service_id))

    existing_crm_service = _crm_service_store[crm_service_id]

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(existing_crm_service, field, value)

    # Update timestamp
    from datetime import datetime
    existing_crm_service.updated_at = datetime.utcnow()

    logger.info("crm_service_updated", crm_service_id=str(crm_service_id))

    return existing_crm_service


@router.delete("/crm_service/{ crm_service_id }", status_code=204)
async def delete_crm_service(crm_service_id: UUID) -> None:
    """Delete a crm_service entity."""
    logger.info("deleting_crm_service", crm_service_id=str(crm_service_id))

    if crm_service_id not in _crm_service_store:
        raise CrmServiceNotFoundError(str(crm_service_id))

    del _crm_service_store[crm_service_id]

    logger.info("crm_service_deleted", crm_service_id=str(crm_service_id))
