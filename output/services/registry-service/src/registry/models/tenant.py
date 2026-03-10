"""Tenant model for multi-tenancy support.

This module defines the Tenant model for the Registry Service,
providing tenant isolation and configuration management using
VentureStrat BaseModel infrastructure.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from venturestrat.models import BaseModel, fields


class TenantStatus(str, Enum):
    """Status of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(BaseModel):
    """
    Tenant model - represents an isolated customer organization.

    Note: Tenant itself does NOT have a tenant_id field (it IS the tenant).
    This is the only model that doesn't inherit TenantMixin.
    """

    _name = "tenant"
    _schema = "registry"
    _table = "tenants"  # Database table name (plural)
    _description = "Customer Tenant"

    # Mark this model as not needing tenant_id field since IT IS the tenant
    _no_tenant = True
    _customizable = False  # Don't allow custom fields on tenants

    # Identifiers
    id: str = fields.String(
        size=36, required=False, primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    slug: str = fields.String(
        size=63, required=True, unique=True, index=True, help="URL-safe tenant identifier"
    )

    # Display
    name: str = fields.String(size=255, required=True, help="Tenant display name")

    # Status
    status: str = fields.String(size=20, required=True, default="active", help="Tenant status")

    # Configuration (theme, quotas, settings)
    config: dict = fields.JSON(required=True, default={}, help="Tenant configuration dictionary")

    # Keycloak integration
    keycloak_org_id: str | None = fields.String(
        size=36, required=False, help="Keycloak organization ID"
    )

    # Timestamps
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.now(UTC)
    )
    deleted_at: datetime | None = fields.DateTime(required=False, help="Soft deletion timestamp")

    # Constraints will be handled by BaseModel infrastructure
    # _constraints = [
    #     ('slug_format', "CHECK (slug ~ '^[a-z0-9][a-z0-9-]*[a-z0-9]$')"),
    # ]

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

        Raises:
            ValueError: If trying to suspend system tenant
        """
        if self.is_system_tenant():
            raise ValueError("Cannot suspend system tenant")

        new_config = dict(self.config) if self.config else {}
        new_config.update(
            {"suspension_reason": reason, "suspended_at": datetime.now(UTC).isoformat()}
        )

        return self.__class__(
            id=self.id,
            slug=self.slug,
            name=self.name,
            status=TenantStatus.SUSPENDED,
            config=new_config,
            keycloak_org_id=self.keycloak_org_id,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=self.deleted_at,
        )

    def resume(self) -> Tenant:
        """Resume a suspended tenant.

        Returns:
            Updated tenant instance

        Raises:
            ValueError: If tenant is not suspended
        """
        if self.status != TenantStatus.SUSPENDED:
            raise ValueError("Can only resume suspended tenants")

        new_config = dict(self.config) if self.config else {}
        # Remove suspension-related config
        new_config.pop("suspension_reason", None)
        new_config.pop("suspended_at", None)

        return self.__class__(
            id=self.id,
            slug=self.slug,
            name=self.name,
            status=TenantStatus.ACTIVE,
            config=new_config,
            keycloak_org_id=self.keycloak_org_id,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=self.deleted_at,
        )

    def delete(self, reason: str) -> Tenant:
        """Soft delete the tenant.

        Args:
            reason: Reason for deletion

        Returns:
            Updated tenant instance

        Raises:
            ValueError: If trying to delete system tenant
        """
        if self.is_system_tenant():
            raise ValueError("Cannot delete system tenant")

        new_config = dict(self.config) if self.config else {}
        # Calculate purge date (30 days from now)
        purge_date = datetime.now(UTC) + timedelta(days=30)
        deleted_at = datetime.now(UTC)

        new_config.update({"deletion_reason": reason, "purge_at": purge_date.isoformat()})

        return self.__class__(
            id=self.id,
            slug=self.slug,
            name=self.name,
            status=TenantStatus.DELETED,
            config=new_config,
            keycloak_org_id=self.keycloak_org_id,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=deleted_at,
        )

    def update_config(self, new_config: dict[str, Any]) -> Tenant:
        """Update tenant configuration.

        Args:
            new_config: New configuration to merge with existing

        Returns:
            Updated tenant instance
        """
        merged_config = dict(self.config) if self.config else {}
        merged_config.update(new_config)

        return self.__class__(
            id=self.id,
            slug=self.slug,
            name=self.name,
            status=self.status,
            config=merged_config,
            keycloak_org_id=self.keycloak_org_id,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=self.deleted_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with ISO-formatted timestamps.

        Returns:
            Dictionary representation of the tenant
        """
        data = super().to_dict()

        # Convert datetime objects to ISO format strings
        if data.get("created_at"):
            if hasattr(data["created_at"], "isoformat"):
                data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at"):
            if hasattr(data["updated_at"], "isoformat"):
                data["updated_at"] = data["updated_at"].isoformat()
        if data.get("deleted_at"):
            if hasattr(data["deleted_at"], "isoformat"):
                data["deleted_at"] = data["deleted_at"].isoformat()

        # Ensure status is string value, not enum representation
        if data.get("status"):
            if isinstance(data["status"], TenantStatus):
                data["status"] = data["status"].value
            elif hasattr(data["status"], "value"):
                data["status"] = data["status"].value
            else:
                # Handle case where it's already a string or enum representation
                status_str = str(data["status"])
                if status_str.startswith("TenantStatus."):
                    data["status"] = status_str.split(".")[-1].lower()
                else:
                    data["status"] = status_str

        return data
