"""Exception handlers for Auth Service API."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


class AuthServiceNotFoundError(Exception):
    """Raised when a auth_service entity is not found."""

    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        super().__init__(f"AuthService with id {entity_id} not found")


class AuthServiceValidationError(Exception):
    """Raised when auth_service validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def auth_service_not_found_handler(
    request: Request, exc: AuthServiceNotFoundError
) -> JSONResponse:
    """Handle auth_service not found errors."""
    logger.warning(
        "auth_service_not_found",
        entity_id=exc.entity_id,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=404,
        content={
            "error": "AuthService not found",
            "detail": str(exc),
            "entity_id": exc.entity_id,
        },
    )


async def auth_service_validation_handler(
    request: Request, exc: AuthServiceValidationError
) -> JSONResponse:
    """Handle auth_service validation errors."""
    logger.warning(
        "auth_service_validation_error",
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
