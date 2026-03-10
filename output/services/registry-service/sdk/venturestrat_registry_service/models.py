"""registry-service service data models.

This module contains Pydantic models that correspond to the protobuf messages
used by the registry-service service. These models provide Python-native
data validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, validator


class BaseRegistryServiceModel(BaseModel):
    """Base model for registry-service service.

    All service models inherit from this base class, which provides
    common configuration and validation behavior.
    """

    model_config = ConfigDict(
        # Forbid extra fields to catch typos
        extra="forbid",
        # Use enum values in serialization
        use_enum_values=True,
        # Validate assignment to catch runtime errors
        validate_assignment=True,
        # Allow population by field name or alias
        populate_by_name=True,
        # Custom JSON encoders for special types
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        },
    )


# Service-specific models will be generated from protobuf definitions
# These are example templates:


class HealthCheckRequest(BaseRegistryServiceModel):
    """Health check request message.

    Example of a simple request model.
    """

    service: str | None = Field(None, description="Service name to check")
    service: Optional[str] = Field(None, description="Service name to check")


class HealthCheckResponse(BaseRegistryServiceModel):
    """Health check response message.

    Example of a simple response model.
    """

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str | None = Field(None, description="Service version")


class ServiceStatus(str, Enum):
    """Service status enumeration.

    Example of how enum types are handled.
    """

    UNKNOWN = "UNKNOWN"
    SERVING = "SERVING"
    NOT_SERVING = "NOT_SERVING"
    SERVICE_UNKNOWN = "SERVICE_UNKNOWN"


# Complex model example with validation
class ExampleRequest(BaseRegistryServiceModel):
    """Example request with validation.

    Demonstrates various field types and validation.
    """

    id: str = Field(..., min_length=1, max_length=100, description="Unique identifier")
    name: str | None = Field(None, max_length=255, description="Display name")
    amount: Decimal | None = Field(None, gt=0, description="Monetary amount")
    name: Optional[str] = Field(None, max_length=255, description="Display name")
    amount: Optional[Decimal] = Field(None, gt=0, description="Monetary amount")
    tags: list[str] = Field(default_factory=list, description="Tags list")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate ID format."""
        if not v.isalnum():
            msg = "ID must be alphanumeric"
            raise ValueError(msg)
        return v.lower()

    @validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags list."""
        if len(v) > 10:
            msg = "Too many tags (max 10)"
            raise ValueError(msg)
        return [tag.lower().strip() for tag in v]


class ExampleResponse(BaseRegistryServiceModel):
    """Example response model."""

    id: str = Field(..., description="Request ID")
    result: str = Field(..., description="Processing result")
    status: ServiceStatus = Field(..., description="Operation status")
    created_at: datetime = Field(..., description="Creation timestamp")


# Error models
class ErrorDetail(BaseRegistryServiceModel):
    """Error detail information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: str | None = Field(None, description="Field that caused error")


class ErrorResponse(BaseRegistryServiceModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: list[ErrorDetail] = Field(
        default_factory=list, description="Error details"
    )
    request_id: str | None = Field(None, description="Request ID for tracking")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# Pagination models
class PaginationRequest(BaseRegistryServiceModel):
    """Pagination parameters for list requests."""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=1000, description="Items per page")
    sort_by: str | None = Field(None, description="Sort field")
    sort_desc: bool = Field(False, description="Sort descending")


class PaginationResponse(BaseRegistryServiceModel):
    """Pagination metadata for list responses."""

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")


class ListExampleResponse(BaseRegistryServiceModel):
    """Example paginated list response."""

    items: list[ExampleResponse] = Field(..., description="List items")
    pagination: PaginationResponse = Field(..., description="Pagination metadata")


# Export all models
__all__ = [
    "BaseRegistryServiceModel",
    "ErrorDetail",
    "ErrorResponse",
    "ExampleRequest",
    "ExampleResponse",
    "HealthCheckRequest",
    "HealthCheckResponse",
    "ListExampleResponse",
    "PaginationRequest",
    "PaginationResponse",
    "ServiceStatus",
    "ListExampleResponse",
]
