"""Pricer Registry model for pricing infrastructure.

This module defines the PricerRegistry model for the Registry Service,
providing pricer registration, metadata management, and health monitoring.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Optional

from venturestrat.models import BaseModel, fields


class PricerStatus(str, Enum):
    """Status of a registered pricer."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


class PricerRegistry(BaseModel):
    """
    Pricer Registry model - represents a registered pricing service.

    This model manages the registration and metadata for pricing services
    in the multi-tenant plugin architecture.
    """

    _name = "pricer_registry"
    _schema = "registry"
    _description = "Registered Pricing Service"

    # Mark this model as not needing tenant_id field since it's shared across tenants
    _no_tenant = True
    _customizable = False  # Don't allow custom fields on pricer registry

    # Primary identifier - Use pricer_id as primary key instead of UUID
    pricer_id: str = fields.String(
        size=255,
        required=True,
        primary_key=True,
        help="Unique pricer identifier (e.g., quantlib-v1.18)",
    )

    # Metadata
    name: str = fields.String(size=255, required=True, help="Human-readable pricer name")
    version: str = fields.String(size=50, required=True, help="Pricer version (semver)")
    description: Optional[str] = fields.Text(required=False, help="Optional detailed description")

    # Service endpoints
    health_check_url: str = fields.Text(required=True, help="HTTP endpoint for health checks")
    pricing_url: str = fields.Text(required=True, help="Base URL for pricing endpoints")

    # Capabilities
    batch_supported: bool = fields.Boolean(
        required=True, default=False, help="Whether pricer supports batch pricing"
    )
    max_batch_size: Optional[int] = fields.Integer(
        required=False, help="Maximum batch size for batch operations"
    )

    # Status and health monitoring
    status: str = fields.String(
        size=50, required=True, default=PricerStatus.HEALTHY.value, help="Current pricer status"
    )
    last_health_check: Optional[datetime.datetime] = fields.DateTime(
        required=False, help="Timestamp of last health check"
    )
    health_check_failures: int = fields.Integer(
        required=True, default=0, help="Consecutive health check failures"
    )

    # Audit Timestamps (auto-populated by BaseModel)
    created_at: datetime.datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    updated_at: datetime.datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    # Note: Relationships with PricerCapability will be handled via BaseModel's
    # relational field system or explicit queries

    @classmethod
    def create_quantlib_pricer(cls) -> PricerRegistry:
        """Create the QuantLib pricer registration.

        Returns:
            QuantLib pricer instance with default configuration
        """
        return cls(
            pricer_id="quantlib-v1.18",
            name="QuantLib",
            version="1.18.0",
            description="Open-source quantitative finance library for pricing and risk management",
            health_check_url="http://quantlib-service:8088/health",
            pricing_url="http://quantlib-service:8088/api/v1",
            batch_supported=True,
            max_batch_size=10000,
            status=PricerStatus.HEALTHY,
        )

    @classmethod
    def create_treasury_pricer(cls) -> PricerRegistry:
        """Create the Treasury pricer registration.

        Returns:
            Treasury pricer instance with default configuration
        """
        return cls(
            pricer_id="treasury-v2.3",
            name="Treasury",
            version="2.3.0",
            description="Proprietary Treasury pricing engine with Monte Carlo and PDE methods",
            health_check_url="http://treasury-service:8101/health",
            pricing_url="http://treasury-service:8101/api/v1",
            batch_supported=True,
            max_batch_size=5000,
            status=PricerStatus.HEALTHY,
        )

    def is_healthy(self) -> bool:
        """Check if the pricer is currently healthy.

        Returns:
            True if pricer status is healthy
        """
        return self.status == PricerStatus.HEALTHY.value

    def mark_healthy(self) -> PricerRegistry:
        """Mark the pricer as healthy and reset failure count.

        Returns:
            Updated pricer instance
        """
        return self.__class__(
            pricer_id=self.pricer_id,
            name=self.name,
            version=self.version,
            description=self.description,
            health_check_url=self.health_check_url,
            pricing_url=self.pricing_url,
            batch_supported=self.batch_supported,
            max_batch_size=self.max_batch_size,
            status=PricerStatus.HEALTHY,
            last_health_check=datetime.datetime.now(datetime.UTC),
            health_check_failures=0,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def mark_unhealthy(self, increment_failures: bool = True) -> PricerRegistry:
        """Mark the pricer as unhealthy.

        Args:
            increment_failures: Whether to increment failure count

        Returns:
            Updated pricer instance
        """
        new_failures = self.health_check_failures or 0
        if increment_failures:
            new_failures += 1

        return self.__class__(
            pricer_id=self.pricer_id,
            name=self.name,
            version=self.version,
            description=self.description,
            health_check_url=self.health_check_url,
            pricing_url=self.pricing_url,
            batch_supported=self.batch_supported,
            max_batch_size=self.max_batch_size,
            status=PricerStatus.UNHEALTHY,
            last_health_check=datetime.datetime.now(datetime.UTC),
            health_check_failures=new_failures,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def disable(self, reason: str) -> PricerRegistry:
        """Disable the pricer.

        Args:
            reason: Reason for disabling

        Returns:
            Updated pricer instance
        """
        return self.__class__(
            pricer_id=self.pricer_id,
            name=self.name,
            version=self.version,
            description=f"{self.description}\n\nDISABLED: {reason}",
            health_check_url=self.health_check_url,
            pricing_url=self.pricing_url,
            batch_supported=self.batch_supported,
            max_batch_size=self.max_batch_size,
            status=PricerStatus.DISABLED,
            last_health_check=self.last_health_check,
            health_check_failures=self.health_check_failures,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def get_capabilities_summary(self) -> dict[str, Any]:
        """Get a summary of pricer capabilities.

        Returns:
            Dictionary with capability summary
        """
        if not self.capabilities:
            return {
                "total_capabilities": 0,
                "supported_instruments": [],
                "supported_models": [],
                "features": [],
            }

        instruments = set()
        models = set()
        features = set()

        for cap in self.capabilities:
            instruments.add(cap.instrument_type)
            if cap.model_type:
                models.add(cap.model_type)
            if cap.features:
                for feature in cap.features:
                    features.add(feature)

        return {
            "total_capabilities": len(self.capabilities),
            "supported_instruments": sorted(list(instruments)),
            "supported_models": sorted(list(models)),
            "features": sorted(list(features)),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with ISO-formatted timestamps.

        Returns:
            Dictionary representation of the pricer
        """
        data = super().to_dict()

        # Convert datetime objects to ISO format strings
        if data.get("created_at"):
            if hasattr(data["created_at"], "isoformat"):
                data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at"):
            if hasattr(data["updated_at"], "isoformat"):
                data["updated_at"] = data["updated_at"].isoformat()
        if data.get("last_health_check"):
            if hasattr(data["last_health_check"], "isoformat"):
                data["last_health_check"] = data["last_health_check"].isoformat()

        # Ensure status is string value
        if data.get("status"):
            if isinstance(data["status"], PricerStatus):
                data["status"] = data["status"].value
            elif hasattr(data["status"], "value"):
                data["status"] = data["status"].value

        return data

    def __str__(self) -> str:
        """String representation."""
        return f"PricerRegistry(pricer_id='{self.pricer_id}', name='{self.name}', status='{self.status}')"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"PricerRegistry("
            f"pricer_id={self.pricer_id!r}, "
            f"name={self.name!r}, "
            f"version={self.version!r}, "
            f"status={self.status!r}"
            f")"
        )
