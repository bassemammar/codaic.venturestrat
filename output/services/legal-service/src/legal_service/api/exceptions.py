"""Exception handlers for Legal Service API."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


class LegalServiceNotFoundError(Exception):
    """Raised when a legal_service entity is not found."""

    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        super().__init__(f"LegalService with id {entity_id} not found")


class LegalServiceValidationError(Exception):
    """Raised when legal_service validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def legal_service_not_found_handler(
    request: Request, exc: LegalServiceNotFoundError
) -> JSONResponse:
    """Handle legal_service not found errors."""
    logger.warning(
        "legal_service_not_found",
        entity_id=exc.entity_id,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=404,
        content={
            "error": "LegalService not found",
            "detail": str(exc),
            "entity_id": exc.entity_id,
        },
    )


async def legal_service_validation_handler(
    request: Request, exc: LegalServiceValidationError
) -> JSONResponse:
    """Handle legal_service validation errors."""
    logger.warning(
        "legal_service_validation_error",
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
