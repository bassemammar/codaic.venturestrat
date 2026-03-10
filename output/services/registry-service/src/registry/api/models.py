"""API request and response models.

This module defines Pydantic models for REST API request/response handling.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Any, Optional

from pydantic import BaseModel, Field

from registry.models import HealthCheckConfig, Protocol

# =============================================================================
# Request Models
# =============================================================================


class RegisterRequest(BaseModel):
    """Request body for service registration."""

    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Semver version string")
    instance_id: str = Field(..., description="Unique instance identifier")
    address: str = Field(..., description="Service address (IP or hostname)")
    port: int = Field(..., ge=1, le=65535, description="Service port")
    protocol: Protocol = Field(default=Protocol.HTTP, description="Communication protocol")
    depends: list[str] = Field(default_factory=list, description="Service dependencies")
    provides: dict[str, Any] = Field(default_factory=dict, description="APIs and events provided")
    health_check: HealthCheckConfig | None = Field(
        default=None, description="Health check configuration"
    )
    tags: list[str] = Field(default_factory=list, description="Service tags")
    metadata: dict[str, str] = Field(default_factory=dict, description="Service metadata")


class HeartbeatRequest(BaseModel):
    """Request body for heartbeat."""

    status: str = Field(default="passing", description="Health status")


# =============================================================================
# Response Models
# =============================================================================


class RegisterResponse(BaseModel):
    """Response for successful service registration."""

    instance_id: str
    consul_service_id: str
    registered_at: datetime
    health_check_id: str


class HeartbeatResponse(BaseModel):
    """Response for heartbeat."""

    instance_id: str
    status: str
    last_heartbeat: datetime


class ServiceInstanceResponse(BaseModel):
    """Response model for a service instance."""

    instance_id: str
    address: str
    port: int
    protocol: str
    version: str
    health_status: str
    tags: list[str]
    metadata: dict[str, str]


class DiscoverResponse(BaseModel):
    """Response for service discovery."""

    service: str
    instances: list[ServiceInstanceResponse]
    total_instances: int
    healthy_instances: int


class ServiceSummary(BaseModel):
    """Summary of a single service."""

    name: str
    versions: list[str]
    instance_count: int
    healthy_count: int
    tags: list[str]


class ListServicesResponse(BaseModel):
    """Response for listing all services."""

    services: list[ServiceSummary]
    total_services: int


class ManifestResponse(BaseModel):
    """Response for service manifest."""

    name: str
    version: str
    description: str | None = None
    depends: list[str] = Field(default_factory=list)
    provides: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)


class HealthCheckDetail(BaseModel):
    """Detail of a single health check."""

    name: str
    status: str
    output: str | None = None
    last_check: datetime | None = None


class InstanceHealthDetail(BaseModel):
    """Health detail for a single instance."""

    instance_id: str
    status: str
    checks: list[HealthCheckDetail] = Field(default_factory=list)
    uptime_seconds: int | None = None


class ServiceHealthResponse(BaseModel):
    """Response for service health status."""

    service: str
    status: str
    instances: list[InstanceHealthDetail]


class HealthInstanceCount(BaseModel):
    """Instance counts by health status."""

    healthy: int
    warning: int
    critical: int


class ServiceHealthSummary(BaseModel):
    """Health summary for a single service."""

    name: str
    status: str
    instances: HealthInstanceCount


class HealthOverviewResponse(BaseModel):
    """Response for overall health overview."""

    services: list[ServiceHealthSummary]
    overall_status: str


# =============================================================================
# Error Response Models
# =============================================================================


class ErrorDetail(BaseModel):
    """Detail for a single validation error."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorInfo


class ErrorInfo(BaseModel):
    """Error information."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None


# =============================================================================
# Tenant Management Models
# =============================================================================


class TenantCreateRequest(BaseModel):
    """Request to create a new tenant."""

    slug: str = Field(
        ...,
        pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        min_length=2,
        max_length=63,
        description="URL-friendly tenant identifier",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable tenant name")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Tenant configuration (quotas, theme, etc.)"
    )
    admin_email: str | None = Field(None, description="Optional admin user email for invitation")
    admin_email: Optional[str] = Field(None, description="Optional admin user email for invitation")


class TenantUpdateRequest(BaseModel):
    """Request to update an existing tenant."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Updated tenant name")
    config: dict[str, Any] | None = Field(None, description="Updated tenant configuration")
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Updated tenant name"
    )
    config: Optional[dict[str, Any]] = Field(None, description="Updated tenant configuration")


class TenantResponse(BaseModel):
    """Response model for tenant data."""

    id: str = Field(..., description="Unique tenant identifier (UUID)")
    slug: str = Field(..., description="URL-friendly tenant identifier")
    name: str = Field(..., description="Human-readable tenant name")
    status: str = Field(..., description="Current tenant status (active, suspended, deleted)")
    config: dict[str, Any] = Field(default_factory=dict, description="Tenant configuration")
    keycloak_org_id: str | None = Field(None, description="Keycloak organization ID")
    created_at: datetime = Field(..., description="When tenant was created")
    updated_at: datetime = Field(..., description="When tenant was last updated")
    deleted_at: datetime | None = Field(None, description="When tenant was soft deleted")


class TenantListResponse(BaseModel):
    """Response for listing tenants."""

    items: list[TenantResponse] = Field(..., description="List of tenants")
    total: int = Field(..., description="Total number of tenants")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Number of items per page")


class TenantSuspendRequest(BaseModel):
    """Request to suspend a tenant."""

    reason: str = Field(
        ..., min_length=10, max_length=500, description="Reason for suspension (min 10 chars)"
    )


class TenantDeleteRequest(BaseModel):
    """Request to delete a tenant."""

    reason: str = Field(
        ..., min_length=10, max_length=500, description="Reason for deletion (min 10 chars)"
    )


# =============================================================================
# Tenant Export Models
# =============================================================================


class ExportRequest(BaseModel):
    """Request to export tenant data."""

    format: str = Field(default="json", description="Export format: json, csv, or jsonl")
    compress: bool = Field(default=True, description="Whether to compress the export")
    encrypt: bool = Field(default=True, description="Whether to encrypt the export")
    include_deleted: bool = Field(default=False, description="Include soft-deleted records")
    include_audit_fields: bool = Field(default=True, description="Include audit timestamp fields")
    reason: str = Field(..., min_length=10, description="Reason for export (min 10 chars)")


class ExportResponse(BaseModel):
    """Response for export request."""

    export_id: str = Field(..., description="Unique export identifier")
    status: str = Field(..., description="Export status")
    tenant_id: str = Field(..., description="Tenant ID being exported")
    created_at: datetime = Field(..., description="When export was initiated")
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")


class ExportStatusResponse(BaseModel):
    """Response for export status query."""

    export_id: str = Field(..., description="Export identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    status: str = Field(..., description="Current export status")
    file_path: str | None = Field(None, description="Path to export file if completed")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    records_exported: int = Field(default=0, description="Number of records exported")
    models_exported: list[str] = Field(
        default_factory=list, description="Models included in export"
    )
    created_at: datetime = Field(..., description="Export creation time")
    completed_at: datetime | None = Field(None, description="Export completion time")
    error_message: str | None = Field(None, description="Error message if failed")
