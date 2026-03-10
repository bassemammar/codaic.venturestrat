"""Exception handlers for Investor Service API."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


class InvestorServiceNotFoundError(Exception):
    """Raised when a investor_service entity is not found."""

    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        super().__init__(f"InvestorService with id {entity_id} not found")


class InvestorServiceValidationError(Exception):
    """Raised when investor_service validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def investor_service_not_found_handler(
    request: Request, exc: InvestorServiceNotFoundError
) -> JSONResponse:
    """Handle investor_service not found errors."""
    logger.warning(
        "investor_service_not_found",
        entity_id=exc.entity_id,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=404,
        content={
            "error": "InvestorService not found",
            "detail": str(exc),
            "entity_id": exc.entity_id,
        },
    )


async def investor_service_validation_handler(
    request: Request, exc: InvestorServiceValidationError
) -> JSONResponse:
    """Handle investor_service validation errors."""
    logger.warning(
        "investor_service_validation_error",
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
