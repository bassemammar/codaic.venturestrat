"""Custom exceptions for the API layer.

This module defines custom exceptions that map to HTTP error responses.
"""
from __future__ import annotations


class RegistryAPIError(Exception):
    """Base class for registry API errors."""

    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        details: list[dict] | None = None,
    ):
        """Initialize error.

        Args:
            message: Error message (overrides class default).
            details: List of error details (field-level errors).
        """
        self.message = message or self.__class__.message
        self.details = details or []
        super().__init__(self.message)


class ValidationError(RegistryAPIError):
    """Raised when request validation fails."""

    code = "VALIDATION_ERROR"
    message = "Invalid request payload"
    status_code = 400


class NotFoundError(RegistryAPIError):
    """Raised when a resource is not found."""

    code = "NOT_FOUND"
    message = "Resource not found"
    status_code = 404


class ConflictError(RegistryAPIError):
    """Raised when a resource already exists."""

    code = "CONFLICT"
    message = "Resource already exists"
    status_code = 409


class ConsulUnavailableError(RegistryAPIError):
    """Raised when Consul backend is unavailable."""

    code = "CONSUL_UNAVAILABLE"
    message = "Service registry backend unavailable"
    status_code = 503


class InternalError(RegistryAPIError):
    """Raised for unexpected internal errors."""

    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"
    status_code = 500
