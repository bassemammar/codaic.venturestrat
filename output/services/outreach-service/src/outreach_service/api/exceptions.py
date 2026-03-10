"""Exception handlers for Outreach Service API."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


class OutreachServiceNotFoundError(Exception):
    """Raised when a outreach_service entity is not found."""

    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        super().__init__(f"OutreachService with id {entity_id} not found")


class OutreachServiceValidationError(Exception):
    """Raised when outreach_service validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def outreach_service_not_found_handler(
    request: Request, exc: OutreachServiceNotFoundError
) -> JSONResponse:
    """Handle outreach_service not found errors."""
    logger.warning(
        "outreach_service_not_found",
        entity_id=exc.entity_id,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=404,
        content={
            "error": "OutreachService not found",
            "detail": str(exc),
            "entity_id": exc.entity_id,
        },
    )


async def outreach_service_validation_handler(
    request: Request, exc: OutreachServiceValidationError
) -> JSONResponse:
    """Handle outreach_service validation errors."""
    logger.warning(
        "outreach_service_validation_error",
        message=exc.message,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "detail": exc.message,
        },
    )
