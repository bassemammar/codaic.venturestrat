"""API routes for Legal Service."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from legal_service.models import (
    LegalService,
    LegalServiceCreate,
    LegalServiceList,
    LegalServiceUpdate,
)
from legal_service.api.exceptions import (
    LegalServiceNotFoundError,
    LegalServiceValidationError,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory storage for demonstration (replace with actual database)
_legal_service_store: dict[UUID, LegalService] = {}


@router.get("/legal_service", response_model=LegalServiceList)
async def list_legal_service(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> LegalServiceList:
    """List legal_service entities with pagination and filtering."""
    logger.info(
        "listing_legal_service",
        offset=offset,
        limit=limit,
        name_filter=name_filter,
    )

    items = list(_legal_service_store.values())

    # Apply name filter if provided
    if name_filter:
        items = [item for item in items if name_filter.lower() in item.name.lower()]

    # Apply pagination
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return LegalServiceList(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/legal_service", response_model=LegalService, status_code=201)
async def create_legal_service(legal_service: LegalServiceCreate) -> LegalService:
    """Create a new legal_service entity."""
    logger.info("creating_legal_service", name=legal_service.name)

    # Validate unique name (in real implementation, this would be a database constraint)
    existing = [item for item in _legal_service_store.values() if item.name == legal_service.name]
    if existing:
        raise LegalServiceValidationError(f"LegalService with name '{legal_service.name}' already exists")

    # Create new entity
    new_legal_service = LegalService(**legal_service.model_dump())
    _legal_service_store[new_legal_service.id] = new_legal_service

    logger.info("legal_service_created", legal_service_id=str(new_legal_service.id))

    return new_legal_service


@router.get("/legal_service/{ legal_service_id }", response_model=LegalService)
async def get_legal_service(legal_service_id: UUID) -> LegalService:
    """Get a legal_service entity by ID."""
    logger.info("getting_legal_service", legal_service_id=str(legal_service_id))

    if legal_service_id not in _legal_service_store:
        raise LegalServiceNotFoundError(str(legal_service_id))

    return _legal_service_store[legal_service_id]


@router.put("/legal_service/{ legal_service_id }", response_model=LegalService)
async def update_legal_service(
    legal_service_id: UUID, update_data: LegalServiceUpdate
) -> LegalService:
    """Update a legal_service entity."""
    logger.info("updating_legal_service", legal_service_id=str(legal_service_id))

    if legal_service_id not in _legal_service_store:
        raise LegalServiceNotFoundError(str(legal_service_id))

    existing_legal_service = _legal_service_store[legal_service_id]

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(existing_legal_service, field, value)

    # Update timestamp
    from datetime import datetime
    existing_legal_service.updated_at = datetime.utcnow()

    logger.info("legal_service_updated", legal_service_id=str(legal_service_id))

    return existing_legal_service


@router.delete("/legal_service/{ legal_service_id }", status_code=204)
async def delete_legal_service(legal_service_id: UUID) -> None:
    """Delete a legal_service entity."""
    logger.info("deleting_legal_service", legal_service_id=str(legal_service_id))

    if legal_service_id not in _legal_service_store:
        raise LegalServiceNotFoundError(str(legal_service_id))

    del _legal_service_store[legal_service_id]

    logger.info("legal_service_deleted", legal_service_id=str(legal_service_id))
