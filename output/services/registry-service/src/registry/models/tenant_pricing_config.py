"""Tenant Pricing Configuration model for multi-tenant pricing.

This module defines the TenantPricingConfig model for the Registry Service,
providing tenant-specific pricing configuration and preferences.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional
from uuid import uuid4

from venturestrat.models import BaseModel, fields


class TenantPricingConfig(BaseModel):
    """
    Tenant Pricing Configuration model - represents pricing preferences for a tenant.

    This model enables multi-tenant SaaS where each client has isolated pricing
    configuration (default pricers, allowed pricers, curves, model parameters).
    """

    _name = "tenant_pricing_config"
    _schema = "registry"
    _description = "Tenant Pricing Configuration"

    # Mark this model as not needing additional tenant_id field since it has one
    _no_tenant = True
    _customizable = False  # Don't allow custom fields on pricing config

    # Primary Key
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # Foreign key to tenant
    tenant_id: str = fields.String(size=36, required=True, unique=True, help="Reference to tenant")

    # Default pricer selection
    default_pricer_id: Optional[str] = fields.String(
        size=255, required=False, help="Default pricer for this tenant"
    )
    fallback_pricer_id: Optional[str] = fields.String(
        size=255, required=False, help="Fallback pricer when default is unavailable"
    )

    # Tenant-specific configuration
    config_json: dict = fields.JSON(
        required=True,
        default={},
        help="Tenant-specific configuration (curves, model params, features)",
    )

    # Timestamps
    created_at: datetime.datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    updated_at: datetime.datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    # Note: Relationships handled via explicit queries

    @classmethod
    def create_system_tenant_config(cls) -> TenantPricingConfig:
        """Create pricing configuration for system tenant.

        Returns:
            System tenant pricing configuration with full access
        """
        return cls(
            tenant_id="00000000-0000-0000-0000-000000000000",
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
                "features": ["batch_pricing", "dual_pricing", "monte_carlo"],
                "max_batch_size": 50000,
                "custom_curves_allowed": True,
                "advanced_models_allowed": True,
            },
        )

    @classmethod
    def create_default_tenant_config(cls, tenant_id: str) -> TenantPricingConfig:
        """Create default pricing configuration for regular tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Default tenant pricing configuration with no specific pricers set
        """
        return cls(
            tenant_id=tenant_id,
            default_pricer_id=None,  # Will be auto-selected by routing logic
            fallback_pricer_id=None,  # Will be auto-selected by routing logic
            config_json={
                "allowed_pricers": [],  # Empty = allow all registered pricers
                "features": ["batch_pricing"],
                "max_batch_size": 1000,
                "custom_curves_allowed": False,
                "advanced_models_allowed": False,
            },
        )

    def get_allowed_pricers(self) -> list[str]:
        """Get list of pricers allowed for this tenant.

        Returns:
            List of allowed pricer IDs
        """
        return self.config_json.get("allowed_pricers", []) if self.config_json else []

    def get_enabled_features(self) -> list[str]:
        """Get list of features enabled for this tenant.

        Returns:
            List of enabled feature names
        """
        return self.config_json.get("features", []) if self.config_json else []

    def get_max_batch_size(self) -> int:
        """Get maximum batch size for this tenant.

        Returns:
            Maximum batch size allowed
        """
        return self.config_json.get("max_batch_size", 100) if self.config_json else 100

    def is_pricer_allowed(self, pricer_id: str) -> bool:
        """Check if a pricer is allowed for this tenant.

        Args:
            pricer_id: Pricer ID to check

        Returns:
            True if pricer is allowed
        """
        allowed_pricers = self.get_allowed_pricers()
        return pricer_id in allowed_pricers

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled for this tenant.

        Args:
            feature: Feature name to check

        Returns:
            True if feature is enabled
        """
        enabled_features = self.get_enabled_features()
        return feature in enabled_features

    def allows_custom_curves(self) -> bool:
        """Check if tenant is allowed to provide custom curves.

        Returns:
            True if custom curves are allowed
        """
        return self.config_json.get("custom_curves_allowed", False) if self.config_json else False

    def allows_advanced_models(self) -> bool:
        """Check if tenant is allowed to use advanced models.

        Returns:
            True if advanced models are allowed
        """
        return self.config_json.get("advanced_models_allowed", False) if self.config_json else False

    def update_configuration(self, new_config: dict[str, Any]) -> TenantPricingConfig:
        """Update tenant configuration.

        Args:
            new_config: New configuration to merge with existing

        Returns:
            Updated pricing configuration instance
        """
        merged_config = dict(self.config_json) if self.config_json else {}
        merged_config.update(new_config)

        return self.__class__(
            id=getattr(self, "id", None),
            tenant_id=self.tenant_id,
            default_pricer_id=self.default_pricer_id,
            fallback_pricer_id=self.fallback_pricer_id,
            config_json=merged_config,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def set_default_pricer(self, pricer_id: str) -> TenantPricingConfig:
        """Set the default pricer for this tenant.

        Args:
            pricer_id: New default pricer ID

        Returns:
            Updated pricing configuration instance

        Raises:
            ValueError: If pricer is not allowed for tenant
        """
        if not self.is_pricer_allowed(pricer_id):
            raise ValueError(f"Pricer {pricer_id} is not allowed for this tenant")

        return self.__class__(
            id=getattr(self, "id", None),
            tenant_id=self.tenant_id,
            default_pricer_id=pricer_id,
            fallback_pricer_id=self.fallback_pricer_id,
            config_json=self.config_json,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def set_fallback_pricer(self, pricer_id: Optional[str]) -> TenantPricingConfig:
        """Set the fallback pricer for this tenant.

        Args:
            pricer_id: New fallback pricer ID (None to remove fallback)

        Returns:
            Updated pricing configuration instance

        Raises:
            ValueError: If pricer is not allowed for tenant or same as default
        """
        if pricer_id is not None:
            if not self.is_pricer_allowed(pricer_id):
                raise ValueError(f"Pricer {pricer_id} is not allowed for this tenant")
            if pricer_id == self.default_pricer_id:
                raise ValueError("Fallback pricer cannot be the same as default pricer")

        return self.__class__(
            id=getattr(self, "id", None),
            tenant_id=self.tenant_id,
            default_pricer_id=self.default_pricer_id,
            fallback_pricer_id=pricer_id,
            config_json=self.config_json,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def enable_feature(self, feature: str) -> TenantPricingConfig:
        """Enable a feature for this tenant.

        Args:
            feature: Feature name to enable

        Returns:
            Updated pricing configuration instance
        """
        enabled_features = self.get_enabled_features()
        if feature not in enabled_features:
            enabled_features.append(feature)

        new_config = dict(self.config_json) if self.config_json else {}
        new_config["features"] = enabled_features

        return self.update_configuration(new_config)

    def disable_feature(self, feature: str) -> TenantPricingConfig:
        """Disable a feature for this tenant.

        Args:
            feature: Feature name to disable

        Returns:
            Updated pricing configuration instance
        """
        enabled_features = self.get_enabled_features()
        if feature in enabled_features:
            enabled_features.remove(feature)

        new_config = dict(self.config_json) if self.config_json else {}
        new_config["features"] = enabled_features

        return self.update_configuration(new_config)

    def add_allowed_pricer(self, pricer_id: str) -> TenantPricingConfig:
        """Add a pricer to the allowed list.

        Args:
            pricer_id: Pricer ID to add

        Returns:
            Updated pricing configuration instance
        """
        allowed_pricers = self.get_allowed_pricers()
        if pricer_id not in allowed_pricers:
            allowed_pricers.append(pricer_id)

        new_config = dict(self.config_json) if self.config_json else {}
        new_config["allowed_pricers"] = allowed_pricers

        return self.update_configuration(new_config)

    def remove_allowed_pricer(self, pricer_id: str) -> TenantPricingConfig:
        """Remove a pricer from the allowed list.

        Args:
            pricer_id: Pricer ID to remove

        Returns:
            Updated pricing configuration instance

        Raises:
            ValueError: If trying to remove default or fallback pricer
        """
        if pricer_id == self.default_pricer_id:
            raise ValueError("Cannot remove default pricer from allowed list")
        if pricer_id == self.fallback_pricer_id:
            raise ValueError("Cannot remove fallback pricer from allowed list")

        allowed_pricers = self.get_allowed_pricers()
        if pricer_id in allowed_pricers:
            allowed_pricers.remove(pricer_id)

        new_config = dict(self.config_json) if self.config_json else {}
        new_config["allowed_pricers"] = allowed_pricers

        return self.update_configuration(new_config)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with ISO-formatted timestamps.

        Returns:
            Dictionary representation of the pricing configuration
        """
        data = super().to_dict()

        # Convert datetime objects to ISO format strings
        if data.get("created_at"):
            if hasattr(data["created_at"], "isoformat"):
                data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at"):
            if hasattr(data["updated_at"], "isoformat"):
                data["updated_at"] = data["updated_at"].isoformat()

        # Convert UUID to string
        if data.get("tenant_id"):
            data["tenant_id"] = str(data["tenant_id"])

        return data

    def __str__(self) -> str:
        """String representation."""
        return (
            f"TenantPricingConfig("
            f"tenant_id='{self.tenant_id}', "
            f"default_pricer='{self.default_pricer_id}', "
            f"fallback_pricer='{self.fallback_pricer_id}'"
            f")"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"TenantPricingConfig("
            f"id={getattr(self, 'id', None)!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"default_pricer_id={self.default_pricer_id!r}, "
            f"fallback_pricer_id={self.fallback_pricer_id!r}"
            f")"
        )
