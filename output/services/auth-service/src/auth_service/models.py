"""Domain models for Auth Service."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuthServiceBase(BaseModel):
    """Base model for auth_service entities."""

    name: str = Field(..., description="Name of the auth_service")
    description: Optional[str] = Field(None, description="Description of the auth_service")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")


class AuthServiceCreate(AuthServiceBase):
    """Model for creating a new auth_service."""
    pass


class AuthServiceUpdate(BaseModel):
    """Model for updating an existing auth_service."""

    name: Optional[str] = Field(None, description="Name of the auth_service")
    description: Optional[str] = Field(None, description="Description of the auth_service")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class AuthService(AuthServiceBase):
    """Complete auth_service model with all fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class AuthServiceList(BaseModel):
    """Response model for listing auth_service entities."""

    items: list[AuthService] = Field(default_factory=list, description="List of auth_service entities")
    total: int = Field(0, description="Total number of entities")
    offset: int = Field(0, description="Offset for pagination")
    limit: int = Field(100, description="Limit for pagination")


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
