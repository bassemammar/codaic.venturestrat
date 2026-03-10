"""registry-service service exceptions.

This module defines the exception hierarchy for the registry-service SDK.
All exceptions inherit from RegistryServiceError and can be caught
collectively or individually.
"""

from typing import Any
from typing import Any, Optional

import grpc


class RegistryServiceError(Exception):
    """Base exception for registry-service service.

    All service-specific exceptions inherit from this base class.

    Attributes:
        message: Error message
        code: Error code (if available)
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize error.

        Args:
            message: Error message
            code: Error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        """String representation of error."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

    def __repr__(self) -> str:
        """Repr of error."""
        return (
            f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"
        )


class RegistryServiceConnectionError(RegistryServiceError):
    """Connection error for registry-service service.

    Raised when unable to establish or maintain a connection to the service.
    """


class RegistryServiceAuthenticationError(RegistryServiceError):
    """Authentication error for registry-service service.

    Raised when authentication fails or credentials are invalid.
    """


class RegistryServiceValidationError(RegistryServiceError):
    """Validation error for registry-service service.

    Raised when request data validation fails.
    """


class RegistryServiceNotFoundError(RegistryServiceError):
    """Resource not found error for registry-service service.

    Raised when a requested resource does not exist.
    """


class RegistryServiceConflictError(RegistryServiceError):
    """Resource conflict error for registry-service service.

    Raised when an operation conflicts with the current state.
    """


class RegistryServiceRateLimitError(RegistryServiceError):
    """Rate limit exceeded error for registry-service service.

    Raised when API rate limits are exceeded.
    """


class RegistryServiceServerError(RegistryServiceError):
    """Server error for registry-service service.

    Raised when the service encounters an internal error.
    """


class RegistryServiceTimeoutError(RegistryServiceError):
    """Timeout error for registry-service service.

    Raised when a request times out.
    """


def grpc_status_to_exception(
    status_code: grpc.StatusCode, message: str
) -> RegistryServiceError:
    """Convert gRPC status code to appropriate exception.

    Args:
        status_code: gRPC status code
        message: Error message

    Returns:
        Appropriate exception instance
    """
    mapping = {
        grpc.StatusCode.INVALID_ARGUMENT: RegistryServiceValidationError,
        grpc.StatusCode.NOT_FOUND: RegistryServiceNotFoundError,
        grpc.StatusCode.ALREADY_EXISTS: RegistryServiceConflictError,
        grpc.StatusCode.PERMISSION_DENIED: RegistryServiceAuthenticationError,
        grpc.StatusCode.UNAUTHENTICATED: RegistryServiceAuthenticationError,
        grpc.StatusCode.RESOURCE_EXHAUSTED: RegistryServiceRateLimitError,
        grpc.StatusCode.DEADLINE_EXCEEDED: RegistryServiceTimeoutError,
        grpc.StatusCode.UNAVAILABLE: RegistryServiceConnectionError,
        grpc.StatusCode.INTERNAL: RegistryServiceServerError,
        grpc.StatusCode.UNIMPLEMENTED: RegistryServiceServerError,
        grpc.StatusCode.DATA_LOSS: RegistryServiceServerError,
    }

    exception_class = mapping.get(status_code, RegistryServiceError)
    return exception_class(message, code=status_code.name)


__all__ = [
    "RegistryServiceAuthenticationError",
    "RegistryServiceConflictError",
    "RegistryServiceConnectionError",
    "RegistryServiceError",
    "RegistryServiceNotFoundError",
    "RegistryServiceRateLimitError",
    "RegistryServiceServerError",
    "RegistryServiceTimeoutError",
    "RegistryServiceValidationError",
    "grpc_status_to_exception",
]
