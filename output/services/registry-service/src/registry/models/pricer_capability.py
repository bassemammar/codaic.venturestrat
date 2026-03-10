"""Pricer Capability model for pricing infrastructure.

This module defines the PricerCapability model for the Registry Service,
providing capability-based routing for the multi-tenant plugin architecture.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from venturestrat.models import BaseModel, fields


class PricerCapability(BaseModel):
    """
    Pricer Capability model - represents a specific capability of a pricing service.

    This model enables capability-based routing where the orchestrator can
    select appropriate pricers based on instrument type, model requirements,
    and feature needs.
    """

    _name = "pricer_capability"
    _schema = "registry"
    _description = "Pricer Capability Definition"

    # Mark this model as not needing tenant_id field since capabilities are shared
    _no_tenant = True
    _customizable = False  # Don't allow custom fields on capabilities

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # Foreign key to pricer_registry
    pricer_id: str = fields.String(size=255, required=True, help="Reference to registered pricer")

    # Capability definition
    instrument_type: str = fields.String(
        size=100, required=True, help="Type of financial instrument (swap, bond, option, etc.)"
    )
    model_type: Optional[str] = fields.String(
        size=100, required=False, help="Specific pricing model (Black-Scholes, Hull-White, etc.)"
    )
    features: list[str] = fields.JSON(
        required=True, default=[], help="List of supported features (greeks, monte_carlo, etc.)"
    )

    # Priority for routing (higher = preferred)
    priority: int = fields.Integer(
        required=True, default=0, help="Priority for capability-based routing (higher = preferred)"
    )

    # Note: Relationship with PricerRegistry handled via explicit queries
    # using pricer_id foreign key reference

    @classmethod
    def create_quantlib_capabilities(cls) -> list[PricerCapability]:
        """Create standard QuantLib capabilities.

        Returns:
            List of QuantLib capability instances
        """
        return [
            # Interest Rate Swaps
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                model_type="Hull-White",
                features=["greeks", "duration", "convexity", "pv01"],
                priority=10,
            ),
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                model_type="Vasicek",
                features=["greeks", "duration", "convexity"],
                priority=8,
            ),
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                model_type=None,
                features=["duration", "convexity"],
                priority=5,
            ),
            # Bonds
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="bond",
                model_type="Yield",
                features=["yield", "duration", "modified_duration", "convexity"],
                priority=10,
            ),
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="bond",
                model_type=None,
                features=["yield", "duration"],
                priority=7,
            ),
            # Options
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="option",
                model_type="Black-Scholes",
                features=["greeks", "delta", "gamma", "theta", "vega", "rho"],
                priority=9,
            ),
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="option",
                model_type="Binomial",
                features=["greeks", "early_exercise"],
                priority=7,
            ),
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="swaption",
                model_type="Black-76",
                features=["greeks", "vega", "theta"],
                priority=8,
            ),
            # FX
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="fx_forward",
                model_type="Black-Scholes",
                features=["greeks"],
                priority=8,
            ),
            cls(
                pricer_id="quantlib-v1.18",
                instrument_type="fx_option",
                model_type="Garman-Kohlhagen",
                features=["greeks", "delta", "gamma", "vega"],
                priority=9,
            ),
        ]

    @classmethod
    def create_treasury_capabilities(cls) -> list[PricerCapability]:
        """Create standard Treasury pricer capabilities.

        Returns:
            List of Treasury capability instances
        """
        return [
            # Interest Rate Products
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="swap",
                model_type="SABR",
                features=["greeks", "volatility_smile", "monte_carlo"],
                priority=12,
            ),
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="swap",
                model_type="HJM",
                features=["greeks", "path_dependent", "monte_carlo"],
                priority=10,
            ),
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="swap",
                model_type="LMM",
                features=["greeks", "caplet_pricing", "monte_carlo"],
                priority=11,
            ),
            # Exotic Options
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="barrier_option",
                model_type="Monte-Carlo",
                features=["greeks", "monte_carlo", "barrier_monitoring"],
                priority=15,
            ),
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="asian_option",
                model_type="Monte-Carlo",
                features=["greeks", "monte_carlo", "path_dependent"],
                priority=14,
            ),
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="swaption",
                model_type="SABR",
                features=["greeks", "volatility_smile", "monte_carlo"],
                priority=12,
            ),
            # Credit Products
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="cds",
                model_type="Intensity",
                features=["greeks", "survival_probability", "hazard_rate"],
                priority=13,
            ),
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="credit_bond",
                model_type="Merton",
                features=["greeks", "default_probability"],
                priority=11,
            ),
            # Structured Products
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="structured_note",
                model_type="Monte-Carlo",
                features=["greeks", "monte_carlo", "multi_asset"],
                priority=15,
            ),
            cls(
                pricer_id="treasury-v2.3",
                instrument_type="autocallable",
                model_type="PDE",
                features=["greeks", "pde", "early_termination"],
                priority=14,
            ),
        ]

    def matches_requirements(
        self,
        instrument_type: str,
        model_type: Optional[str] = None,
        required_features: Optional[list[str]] = None,
    ) -> bool:
        """Check if this capability matches the given requirements.

        Args:
            instrument_type: Required instrument type
            model_type: Required model type (None means any model)
            required_features: List of required features

        Returns:
            True if capability matches requirements
        """
        # Check instrument type
        if self.instrument_type != instrument_type:
            return False

        # Check model type
        if model_type is not None and self.model_type != model_type:
            return False

        # Check features
        if required_features:
            capability_features = set(self.features) if self.features else set()
            required_features_set = set(required_features)
            if not required_features_set.issubset(capability_features):
                return False

        return True

    def has_feature(self, feature: str) -> bool:
        """Check if this capability supports a specific feature.

        Args:
            feature: Feature name to check

        Returns:
            True if feature is supported
        """
        return feature in (self.features or [])

    def get_feature_list(self) -> list[str]:
        """Get list of supported features.

        Returns:
            List of feature names
        """
        return list(self.features) if self.features else []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of the capability
        """
        data = super().to_dict()

        # Ensure features is a proper list
        if data.get("features"):
            data["features"] = list(data["features"])

        return data

    def __str__(self) -> str:
        """String representation."""
        model_str = f", model='{self.model_type}'" if self.model_type else ""
        features_str = f", features={len(self.features or [])}" if self.features else ""
        return (
            f"PricerCapability("
            f"pricer='{self.pricer_id}', "
            f"instrument='{self.instrument_type}'"
            f"{model_str}"
            f"{features_str}, "
            f"priority={self.priority}"
            f")"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"PricerCapability("
            f"id={getattr(self, 'id', None)!r}, "
            f"pricer_id={self.pricer_id!r}, "
            f"instrument_type={self.instrument_type!r}, "
            f"model_type={self.model_type!r}, "
            f"features={self.features!r}, "
            f"priority={self.priority!r}"
            f")"
        )
