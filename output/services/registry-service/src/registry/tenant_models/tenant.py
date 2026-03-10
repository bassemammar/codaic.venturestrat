"""Tenant model for multi-tenancy support.

This module defines the Tenant model for the Registry Service,
providing tenant isolation and configuration management.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TenantStatus(str, Enum):
    """Status of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(BaseModel):
    """Tenant model - represents an isolated customer organization.

    Note: Tenant itself does NOT have a tenant_id field (it IS the tenant).
    This is the only model that doesn't inherit TenantMixin.
    """

    # Identifiers
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique tenant identifier (UUID)"
    )
    slug: str = Field(
        ..., min_length=1, max_length=63, description="URL-friendly tenant identifier"
    )

    # Display
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable tenant name")

    # Status
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, description="Current tenant status")

    # Configuration (theme, quotas, settings)
    config: dict[str, Any] = Field(
        default_factory=dict, description="JSON configuration for quotas, theme, and settings"
    )

    # Keycloak integration
    keycloak_org_id: str | None = Field(
        default=None, max_length=36, description="Keycloak organization ID for SSO integration"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When the tenant was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When the tenant was last updated"
    )
    deleted_at: datetime | None = Field(
        default=None, description="When the tenant was soft deleted (null if active)"
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate tenant slug format.

        Must be lowercase alphanumeric with hyphens, starting and ending with alphanumeric.
        Examples: 'acme-corp', 'client123', 'big-bank-ltd'

        Args:
            v: The slug value to validate

        Returns:
            The validated slug

        Raises:
            ValueError: If slug format is invalid
        """
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v):
            if len(v) == 1:
                # Single character should be alphanumeric
                if not re.match(r"^[a-z0-9]$", v):
                    raise ValueError("Single character slug must be lowercase alphanumeric")
            else:
                raise ValueError(
                    "Slug must be lowercase alphanumeric with hyphens, "
                    "starting and ending with alphanumeric characters"
                )
        return v

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate tenant ID is a valid UUID.

        Args:
            v: The ID value to validate

        Returns:
            The validated ID

        Raises:
            ValueError: If ID is not a valid UUID
        """
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("Tenant ID must be a valid UUID")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with ISO-formatted timestamps.

        Returns:
            Dictionary representation of the tenant
        """
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.deleted_at:
            data["deleted_at"] = self.deleted_at.isoformat()
        data["status"] = self.status.value
        return data

    @classmethod
    def create_system_tenant(cls) -> Tenant:
        """Create the special system tenant.

        Returns:
            System tenant instance with predefined ID and slug
        """
        return cls(
            id="00000000-0000-0000-0000-000000000000",
            slug="system",
            name="System",
            status=TenantStatus.ACTIVE,
            config={"is_system": True},
        )

    def is_system_tenant(self) -> bool:
        """Check if this is the system tenant.

        Returns:
            True if this is the system tenant
        """
        return self.id == "00000000-0000-0000-0000-000000000000"

    def suspend(self, reason: str) -> Tenant:
        """Suspend the tenant.

        Args:
            reason: Reason for suspension

        Returns:
            Updated tenant instance
        """
        if self.is_system_tenant():
            raise ValueError("Cannot suspend system tenant")

        new_config = self.config.copy()
        new_config.update(
            {"suspension_reason": reason, "suspended_at": datetime.now(UTC).isoformat()}
        )

        return self.model_copy(
            update={
                "status": TenantStatus.SUSPENDED,
                "config": new_config,
                "updated_at": datetime.now(UTC),
            }
        )

    def resume(self) -> Tenant:
        """Resume a suspended tenant.

        Returns:
            Updated tenant instance
        """
        if self.status != TenantStatus.SUSPENDED:
            raise ValueError("Can only resume suspended tenants")

        new_config = self.config.copy()
        # Remove suspension-related config
        new_config.pop("suspension_reason", None)
        new_config.pop("suspended_at", None)

        return self.model_copy(
            update={
                "status": TenantStatus.ACTIVE,
                "config": new_config,
                "updated_at": datetime.now(UTC),
            }
        )

    def delete(self, reason: str) -> Tenant:
        """Soft delete the tenant.

        Args:
            reason: Reason for deletion

        Returns:
            Updated tenant instance
        """
        if self.is_system_tenant():
            raise ValueError("Cannot delete system tenant")

        new_config = self.config.copy()
        # Calculate purge date (30 days from now)
        purge_date = datetime.now(UTC) + timedelta(days=30)

        new_config.update({"deletion_reason": reason, "purge_at": purge_date.isoformat()})

        return self.model_copy(
            update={
                "status": TenantStatus.DELETED,
                "config": new_config,
                "deleted_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

    def update_config(self, new_config: dict[str, Any]) -> Tenant:
        """Update tenant configuration.

        Args:
            new_config: New configuration to merge with existing

        Returns:
            Updated tenant instance
        """
        merged_config = self.config.copy()
        merged_config.update(new_config)

        return self.model_copy(update={"config": merged_config, "updated_at": datetime.now(UTC)})
