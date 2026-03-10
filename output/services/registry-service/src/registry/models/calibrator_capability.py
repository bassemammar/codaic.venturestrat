"""Calibrator Capability model for calibration infrastructure.

This module defines the CalibratorCapability model for the Registry Service,
providing capability-based routing for the calibration pipeline.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from venturestrat.models import BaseModel, fields


class CalibratorCapability(BaseModel):
    """
    Calibrator Capability model - represents a specific calibration capability.

    Enables capability-based routing where the calibration orchestrator can
    select appropriate calibrators based on curve type, asset class, method,
    and currency requirements.
    """

    _name = "calibrator_capability"
    _schema = "registry"
    _description = "Calibrator Capability Definition"

    _no_tenant = True
    _customizable = False

    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    calibrator_id: str = fields.String(
        size=255, required=True, help="Reference to registered calibrator"
    )

    curve_type: str = fields.String(
        size=50, required=True, help="Curve type (FX_CURVE, IR_DISCOUNT, IR_FORECAST, CREDIT, VOL_SURFACE)"
    )
    asset_class: Optional[str] = fields.String(
        size=50, required=False, help="Asset class (FX, IR, CREDIT, EQUITY)"
    )
    currency: Optional[str] = fields.String(
        size=3, required=False, help="Currency code (NULL = all currencies)"
    )
    method: Optional[str] = fields.String(
        size=50, required=False, help="Calibration method (BOOTSTRAP, SABR, HULL_WHITE, etc.)"
    )
    features: list[str] = fields.JSON(
        required=True, default=[], help="Supported features (e.g., multi_curve, regularization)"
    )

    priority: int = fields.Integer(
        required=True, default=100, help="Priority for routing (higher = preferred)"
    )

    @classmethod
    def create_quantlib_capabilities(cls) -> list[CalibratorCapability]:
        """Create standard QuantLib calibration capabilities."""
        return [
            cls(
                calibrator_id="quantlib-v1.18",
                curve_type="FX_CURVE",
                asset_class="FX",
                method="INTERPOLATION",
                features=["spot_forward", "cross_rates"],
                priority=200,
            ),
            cls(
                calibrator_id="quantlib-v1.18",
                curve_type="IR_DISCOUNT",
                asset_class="IR",
                method="BOOTSTRAP",
                features=["deposit", "swap", "ois"],
                priority=200,
            ),
            cls(
                calibrator_id="quantlib-v1.18",
                curve_type="IR_FORECAST",
                asset_class="IR",
                method="BOOTSTRAP",
                features=["deposit", "fra", "swap"],
                priority=200,
            ),
            cls(
                calibrator_id="quantlib-v1.18",
                curve_type="VOL_SURFACE",
                asset_class="IR",
                method="SABR",
                features=["swaption_vol", "caplet_vol"],
                priority=200,
            ),
            cls(
                calibrator_id="quantlib-v1.18",
                curve_type="VOL_SURFACE",
                asset_class="FX",
                method="SABR",
                features=["fx_vol_smile"],
                priority=200,
            ),
        ]

    @classmethod
    def create_treasury_capabilities(cls) -> list[CalibratorCapability]:
        """Create standard Treasury calibration capabilities."""
        return [
            cls(
                calibrator_id="treasury-v2.3",
                curve_type="IR_DISCOUNT",
                asset_class="IR",
                method="BOOTSTRAP",
                features=["multi_curve", "regularization", "analytical_jacobian"],
                priority=150,
            ),
            cls(
                calibrator_id="treasury-v2.3",
                curve_type="IR_FORECAST",
                asset_class="IR",
                method="BOOTSTRAP",
                features=["multi_curve", "regularization"],
                priority=150,
            ),
            cls(
                calibrator_id="treasury-v2.3",
                curve_type="CREDIT",
                asset_class="CREDIT",
                method="BOOTSTRAP",
                features=["survival_probability", "hazard_rate"],
                priority=200,
            ),
            cls(
                calibrator_id="treasury-v2.3",
                curve_type="IR_DISCOUNT",
                asset_class="IR",
                method="MULTI_CURVE",
                features=["multi_curve", "cross_currency_basis", "dependency_graph"],
                priority=250,
            ),
        ]

    def matches_requirements(
        self,
        curve_type: str,
        asset_class: Optional[str] = None,
        currency: Optional[str] = None,
        method: Optional[str] = None,
    ) -> bool:
        """Check if this capability matches the given requirements."""
        if self.curve_type != curve_type:
            return False
        if asset_class is not None and self.asset_class != asset_class:
            return False
        if currency is not None and self.currency is not None and self.currency != currency:
            return False
        if method is not None and self.method != method:
            return False
        return True

    def has_feature(self, feature: str) -> bool:
        return feature in (self.features or [])

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        if data.get("features"):
            data["features"] = list(data["features"])
        return data

    def __str__(self) -> str:
        return (
            f"CalibratorCapability("
            f"calibrator='{self.calibrator_id}', "
            f"curve_type='{self.curve_type}', "
            f"asset_class='{self.asset_class}', "
            f"method='{self.method}', "
            f"priority={self.priority}"
            f")"
        )
