"""TenantQuotas model for resource quota management.

This module defines the TenantQuotas model for the Registry Service,
providing per-tenant resource quotas and limitations using
VentureStrat BaseModel infrastructure.
"""

from __future__ import annotations

from datetime import UTC, datetime

from venturestrat.models import BaseModel, fields


class TenantQuotas(BaseModel):
    """
    TenantQuotas model - defines resource limits for a tenant.

    This model stores quota configurations for each tenant, defining
    limits on users, data storage, API usage, and record counts.

    Note: This model does NOT have a tenant_id field in the traditional sense.
    Instead, it uses tenant_id as the primary key, creating a one-to-one
    relationship with the Tenant model.
    """

    _name = "tenant_quotas"
    _schema = "registry"
    _description = "Tenant Resource Quotas"
    _customizable = False  # Don't allow custom fields on tenant quotas

    # Mark this model as not needing automatic tenant_id field
    # since we're implementing it manually as a primary key
    _no_tenant = True

    # Primary key: references tenant.id (one-to-one relationship)
    tenant_id: str = fields.String(
        size=36, required=True, primary_key=True, help="Tenant ID (primary key)"
    )

    # User quotas
    max_users: int = fields.Integer(required=True, default=100, help="Maximum number of users")

    # Data storage quotas
    max_records_per_model: int = fields.Integer(
        required=True, default=1000000, help="Maximum records per model"
    )

    # API usage quotas
    max_api_calls_per_day: int = fields.Integer(
        required=True, default=100000, help="Maximum API calls per day"
    )

    # Storage quotas (in megabytes)
    max_storage_mb: int = fields.Integer(
        required=True, default=10240, help="Maximum storage in megabytes (10GB default)"
    )

    # Timestamps
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.now(UTC)
    )

    @classmethod
    def create_default_quotas(cls, tenant_id: str) -> TenantQuotas:
        """Create default quota configuration for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            TenantQuotas instance with default values
        """
        return cls(tenant_id=tenant_id)

    @classmethod
    def create_enterprise_quotas(cls, tenant_id: str) -> TenantQuotas:
        """Create enterprise-tier quota configuration for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            TenantQuotas instance with enterprise values
        """
        return cls(
            tenant_id=tenant_id,
            max_users=1000,
            max_records_per_model=10000000,
            max_api_calls_per_day=1000000,
            max_storage_mb=102400,  # 100GB
        )

    @classmethod
    def create_startup_quotas(cls, tenant_id: str) -> TenantQuotas:
        """Create startup-tier quota configuration for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            TenantQuotas instance with startup values
        """
        return cls(
            tenant_id=tenant_id,
            max_users=10,
            max_records_per_model=100000,
            max_api_calls_per_day=10000,
            max_storage_mb=1024,  # 1GB
        )

    def is_within_user_limit(self, current_users: int) -> bool:
        """Check if current user count is within quota.

        Args:
            current_users: Current number of users

        Returns:
            True if within limit, False otherwise
        """
        return current_users <= self.max_users

    def is_within_record_limit(self, current_records: int) -> bool:
        """Check if current record count is within quota per model.

        Args:
            current_records: Current number of records for a model

        Returns:
            True if within limit, False otherwise
        """
        return current_records <= self.max_records_per_model

    def is_within_api_limit(self, current_calls: int) -> bool:
        """Check if current API calls are within daily quota.

        Args:
            current_calls: Current number of API calls today

        Returns:
            True if within limit, False otherwise
        """
        return current_calls <= self.max_api_calls_per_day

    def is_within_storage_limit(self, current_storage_mb: int) -> bool:
        """Check if current storage usage is within quota.

        Args:
            current_storage_mb: Current storage usage in megabytes

        Returns:
            True if within limit, False otherwise
        """
        return current_storage_mb <= self.max_storage_mb

    def get_user_usage_percentage(self, current_users: int) -> float:
        """Get user quota usage as percentage.

        Args:
            current_users: Current number of users

        Returns:
            Usage percentage (0.0 to 100.0+)
        """
        return (current_users / self.max_users) * 100.0

    def get_storage_usage_percentage(self, current_storage_mb: int) -> float:
        """Get storage quota usage as percentage.

        Args:
            current_storage_mb: Current storage usage in megabytes

        Returns:
            Usage percentage (0.0 to 100.0+)
        """
        return (current_storage_mb / self.max_storage_mb) * 100.0

    def get_api_usage_percentage(self, current_calls: int) -> float:
        """Get API quota usage as percentage.

        Args:
            current_calls: Current number of API calls today

        Returns:
            Usage percentage (0.0 to 100.0+)
        """
        return (current_calls / self.max_api_calls_per_day) * 100.0

    def update_quotas(
        self,
        max_users: int = None,
        max_records_per_model: int = None,
        max_api_calls_per_day: int = None,
        max_storage_mb: int = None,
    ) -> TenantQuotas:
        """Update quota values.

        Args:
            max_users: New user limit (optional)
            max_records_per_model: New record limit per model (optional)
            max_api_calls_per_day: New API call limit (optional)
            max_storage_mb: New storage limit (optional)

        Returns:
            Updated TenantQuotas instance
        """
        updates = {}

        if max_users is not None:
            updates["max_users"] = max_users
        if max_records_per_model is not None:
            updates["max_records_per_model"] = max_records_per_model
        if max_api_calls_per_day is not None:
            updates["max_api_calls_per_day"] = max_api_calls_per_day
        if max_storage_mb is not None:
            updates["max_storage_mb"] = max_storage_mb

        # Add updated timestamp
        updates["updated_at"] = datetime.now()

        return self.__class__(**{**self.to_dict(), **updates})

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary representation of the quota configuration
        """
        return {
            "tenant_id": self.tenant_id,
            "max_users": self.max_users,
            "max_records_per_model": self.max_records_per_model,
            "max_api_calls_per_day": self.max_api_calls_per_day,
            "max_storage_mb": self.max_storage_mb,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        """String representation of TenantQuotas.

        Returns:
            String representation
        """
        return (
            f"TenantQuotas("
            f"tenant_id={self.tenant_id}, "
            f"max_users={self.max_users}, "
            f"max_records_per_model={self.max_records_per_model}, "
            f"max_api_calls_per_day={self.max_api_calls_per_day}, "
            f"max_storage_mb={self.max_storage_mb})"
        )
