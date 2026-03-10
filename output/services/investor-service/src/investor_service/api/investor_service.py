"""API routes for Investor Service."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from investor_service.models import (
    InvestorService,
    InvestorServiceCreate,
    InvestorServiceList,
    InvestorServiceUpdate,
)
from investor_service.api.exceptions import (
    InvestorServiceNotFoundError,
    InvestorServiceValidationError,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory storage for demonstration (replace with actual database)
_investor_service_store: dict[UUID, InvestorService] = {}


@router.get("/investor_service", response_model=InvestorServiceList)
async def list_investor_service(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> InvestorServiceList:
    """List investor_service entities with pagination and filtering."""
    logger.info(
        "listing_investor_service",
        offset=offset,
        limit=limit,
        name_filter=name_filter,
    )

    items = list(_investor_service_store.values())

    # Apply name filter if provided
    if name_filter:
        items = [item for item in items if name_filter.lower() in item.name.lower()]

    # Apply pagination
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return InvestorServiceList(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/investor_service", response_model=InvestorService, status_code=201)
async def create_investor_service(investor_service: InvestorServiceCreate) -> InvestorService:
    """Create a new investor_service entity."""
    logger.info("creating_investor_service", name=investor_service.name)

    # Validate unique name (in real implementation, this would be a database constraint)
    existing = [item for item in _investor_service_store.values() if item.name == investor_service.name]
    if existing:
        raise InvestorServiceValidationError(f"InvestorService with name '{investor_service.name}' already exists")

    # Create new entity
    new_investor_service = InvestorService(**investor_service.model_dump())
    _investor_service_store[new_investor_service.id] = new_investor_service

    logger.info("investor_service_created", investor_service_id=str(new_investor_service.id))

    return new_investor_service


@router.get("/investor_service/{ investor_service_id }", response_model=InvestorService)
async def get_investor_service(investor_service_id: UUID) -> InvestorService:
    """Get a investor_service entity by ID."""
    logger.info("getting_investor_service", investor_service_id=str(investor_service_id))

    if investor_service_id not in _investor_service_store:
        raise InvestorServiceNotFoundError(str(investor_service_id))

    return _investor_service_store[investor_service_id]


@router.put("/investor_service/{ investor_service_id }", response_model=InvestorService)
async def update_investor_service(
    investor_service_id: UUID, update_data: InvestorServiceUpdate
) -> InvestorService:
    """Update a investor_service entity."""
    logger.info("updating_investor_service", investor_service_id=str(investor_service_id))

    if investor_service_id not in _investor_service_store:
        raise InvestorServiceNotFoundError(str(investor_service_id))

    existing_investor_service = _investor_service_store[investor_service_id]

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(existing_investor_service, field, value)

    # Update timestamp
    from datetime import datetime
    existing_investor_service.updated_at = datetime.utcnow()

    logger.info("investor_service_updated", investor_service_id=str(investor_service_id))

    return existing_investor_service


@router.delete("/investor_service/{ investor_service_id }", status_code=204)
async def delete_investor_service(investor_service_id: UUID) -> None:
    """Delete a investor_service entity."""
    logger.info("deleting_investor_service", investor_service_id=str(investor_service_id))

    if investor_service_id not in _investor_service_store:
        raise InvestorServiceNotFoundError(str(investor_service_id))

    del _investor_service_store[investor_service_id]

    logger.info("investor_service_deleted", investor_service_id=str(investor_service_id))
