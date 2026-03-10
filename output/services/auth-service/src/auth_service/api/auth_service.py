"""API routes for Auth Service."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from auth_service.models import (
    AuthService,
    AuthServiceCreate,
    AuthServiceList,
    AuthServiceUpdate,
)
from auth_service.api.exceptions import (
    AuthServiceNotFoundError,
    AuthServiceValidationError,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory storage for demonstration (replace with actual database)
_auth_service_store: dict[UUID, AuthService] = {}


@router.get("/auth_service", response_model=AuthServiceList)
async def list_auth_service(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit for pagination"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> AuthServiceList:
    """List auth_service entities with pagination and filtering."""
    logger.info(
        "listing_auth_service",
        offset=offset,
        limit=limit,
        name_filter=name_filter,
    )

    items = list(_auth_service_store.values())

    # Apply name filter if provided
    if name_filter:
        items = [item for item in items if name_filter.lower() in item.name.lower()]

    # Apply pagination
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return AuthServiceList(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/auth_service", response_model=AuthService, status_code=201)
async def create_auth_service(auth_service: AuthServiceCreate) -> AuthService:
    """Create a new auth_service entity."""
    logger.info("creating_auth_service", name=auth_service.name)

    # Validate unique name (in real implementation, this would be a database constraint)
    existing = [item for item in _auth_service_store.values() if item.name == auth_service.name]
    if existing:
        raise AuthServiceValidationError(f"AuthService with name '{auth_service.name}' already exists")

    # Create new entity
    new_auth_service = AuthService(**auth_service.model_dump())
    _auth_service_store[new_auth_service.id] = new_auth_service

    logger.info("auth_service_created", auth_service_id=str(new_auth_service.id))

    return new_auth_service


@router.get("/auth_service/{ auth_service_id }", response_model=AuthService)
async def get_auth_service(auth_service_id: UUID) -> AuthService:
    """Get a auth_service entity by ID."""
    logger.info("getting_auth_service", auth_service_id=str(auth_service_id))

    if auth_service_id not in _auth_service_store:
        raise AuthServiceNotFoundError(str(auth_service_id))

    return _auth_service_store[auth_service_id]


@router.put("/auth_service/{ auth_service_id }", response_model=AuthService)
async def update_auth_service(
    auth_service_id: UUID, update_data: AuthServiceUpdate
) -> AuthService:
    """Update a auth_service entity."""
    logger.info("updating_auth_service", auth_service_id=str(auth_service_id))

    if auth_service_id not in _auth_service_store:
        raise AuthServiceNotFoundError(str(auth_service_id))

    existing_auth_service = _auth_service_store[auth_service_id]

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(existing_auth_service, field, value)

    # Update timestamp
    from datetime import datetime
    existing_auth_service.updated_at = datetime.utcnow()

    logger.info("auth_service_updated", auth_service_id=str(auth_service_id))

    return existing_auth_service


@router.delete("/auth_service/{ auth_service_id }", status_code=204)
async def delete_auth_service(auth_service_id: UUID) -> None:
    """Delete a auth_service entity."""
    logger.info("deleting_auth_service", auth_service_id=str(auth_service_id))

    if auth_service_id not in _auth_service_store:
        raise AuthServiceNotFoundError(str(auth_service_id))

    del _auth_service_store[auth_service_id]

    logger.info("auth_service_deleted", auth_service_id=str(auth_service_id))
