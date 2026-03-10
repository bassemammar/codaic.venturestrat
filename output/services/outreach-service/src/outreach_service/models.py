"""Domain models for Outreach Service."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OutreachServiceBase(BaseModel):
    """Base model for outreach_service entities."""

    name: str = Field(..., description="Name of the outreach_service")
    description: Optional[str] = Field(None, description="Description of the outreach_service")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")


class OutreachServiceCreate(OutreachServiceBase):
    """Model for creating a new outreach_service."""
    pass


class OutreachServiceUpdate(BaseModel):
    """Model for updating an existing outreach_service."""

    name: Optional[str] = Field(None, description="Name of the outreach_service")
    description: Optional[str] = Field(None, description="Description of the outreach_service")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class OutreachService(OutreachServiceBase):
    """Complete outreach_service model with all fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class OutreachServiceList(BaseModel):
    """Response model for listing outreach_service entities."""

    items: list[OutreachService] = Field(default_factory=list, description="List of outreach_service entities")
    total: int = Field(0, description="Total number of entities")
    offset: int = Field(0, description="Offset for pagination")
    limit: int = Field(100, description="Limit for pagination")


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
