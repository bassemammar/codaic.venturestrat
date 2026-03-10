"""Calibrator Registry model for calibration infrastructure.

This module defines the CalibratorRegistry model for the Registry Service,
providing calibrator registration, metadata management, and health monitoring
for the market data calibration pipeline.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Optional

from venturestrat.models import BaseModel, fields


class CalibratorStatus(str, Enum):
    """Status of a registered calibrator."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


class CalibratorRegistry(BaseModel):
    """
    Calibrator Registry model - represents a registered calibration service.

    This model manages the registration and metadata for calibration services
    (curve builders, vol surface calibrators) in the calibration pipeline.
    """

    _name = "calibrator_registry"
    _schema = "registry"
    _description = "Registered Calibration Service"

    _no_tenant = True
    _customizable = False

    calibrator_id: str = fields.String(
        size=255,
        required=True,
        primary_key=True,
        help="Unique calibrator identifier (e.g., quantlib-v1.18)",
    )

    name: str = fields.String(size=255, required=True, help="Human-readable calibrator name")
    version: str = fields.String(size=50, required=True, help="Calibrator version (semver)")
    description: Optional[str] = fields.Text(required=False, help="Optional detailed description")

    calibration_url: str = fields.Text(
        required=True, help="Base URL for calibration endpoints"
    )
    health_check_url: Optional[str] = fields.Text(
        required=False, help="HTTP endpoint for health checks"
    )

    supported_modes: dict = fields.JSON(
        required=False,
        default={},
        help="Supported modes (e.g., batch, streaming, max_batch_size)",
    )

    status: str = fields.String(
        size=50, required=True, default=CalibratorStatus.HEALTHY.value, help="Current status"
    )
    last_health_check: Optional[datetime.datetime] = fields.DateTime(
        required=False, help="Timestamp of last health check"
    )
    health_check_failures: int = fields.Integer(
        required=True, default=0, help="Consecutive health check failures"
    )

    created_at: datetime.datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    updated_at: datetime.datetime = fields.DateTime(
        required=False, readonly=True, default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    @classmethod
    def create_quantlib_calibrator(cls) -> CalibratorRegistry:
        """Create the QuantLib calibrator registration."""
        return cls(
            calibrator_id="quantlib-v1.18",
            name="QuantLib Curve Builder",
            version="1.18.0",
            description="QuantLib-based curve bootstrapping and vol surface calibration",
            calibration_url="http://quantlib-service:8088/api/v1",
            health_check_url="http://quantlib-service:8088/health",
            supported_modes={"batch": True, "streaming": False, "max_batch_size": 50},
            status=CalibratorStatus.HEALTHY,
        )

    @classmethod
    def create_treasury_calibrator(cls) -> CalibratorRegistry:
        """Create the Treasury calibrator registration."""
        return cls(
            calibrator_id="treasury-v2.3",
            name="Treasury Calibration Engine",
            version="2.3.0",
            description="Advanced multi-curve calibration with Newton-Raphson solver",
            calibration_url="http://treasury-service:8101/api/v1",
            health_check_url="http://treasury-service:8101/health",
            supported_modes={"batch": True, "streaming": False, "max_batch_size": 20},
            status=CalibratorStatus.HEALTHY,
        )

    def is_healthy(self) -> bool:
        return self.status == CalibratorStatus.HEALTHY.value

    def mark_healthy(self) -> CalibratorRegistry:
        return self.__class__(
            calibrator_id=self.calibrator_id,
            name=self.name,
            version=self.version,
            description=self.description,
            calibration_url=self.calibration_url,
            health_check_url=self.health_check_url,
            supported_modes=self.supported_modes,
            status=CalibratorStatus.HEALTHY,
            last_health_check=datetime.datetime.now(datetime.UTC),
            health_check_failures=0,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def mark_unhealthy(self, increment_failures: bool = True) -> CalibratorRegistry:
        new_failures = self.health_check_failures or 0
        if increment_failures:
            new_failures += 1
        return self.__class__(
            calibrator_id=self.calibrator_id,
            name=self.name,
            version=self.version,
            description=self.description,
            calibration_url=self.calibration_url,
            health_check_url=self.health_check_url,
            supported_modes=self.supported_modes,
            status=CalibratorStatus.UNHEALTHY,
            last_health_check=datetime.datetime.now(datetime.UTC),
            health_check_failures=new_failures,
            created_at=self.created_at,
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        if data.get("created_at") and hasattr(data["created_at"], "isoformat"):
            data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at") and hasattr(data["updated_at"], "isoformat"):
            data["updated_at"] = data["updated_at"].isoformat()
        if data.get("last_health_check") and hasattr(data["last_health_check"], "isoformat"):
            data["last_health_check"] = data["last_health_check"].isoformat()
        if data.get("status") and hasattr(data["status"], "value"):
            data["status"] = data["status"].value
        return data

    def __str__(self) -> str:
        return f"CalibratorRegistry(calibrator_id='{self.calibrator_id}', name='{self.name}', status='{self.status}')"

    def __repr__(self) -> str:
        return (
            f"CalibratorRegistry("
            f"calibrator_id={self.calibrator_id!r}, "
            f"name={self.name!r}, "
            f"version={self.version!r}, "
            f"status={self.status!r}"
            f")"
        )
