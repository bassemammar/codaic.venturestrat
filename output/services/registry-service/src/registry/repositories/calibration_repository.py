"""Calibration Repository for calibration service registry operations.

This module provides data access layer for calibration service registration
and capability management using SQLAlchemy async sessions.
"""

from __future__ import annotations

import logging
from typing import Optional

from registry.db_models import CalibratorCapabilityORM, CalibratorRegistryORM
from registry.db_session import get_session
from registry.models.calibrator_capability import CalibratorCapability
from registry.models.calibrator_registry import CalibratorRegistry
from sqlalchemy import or_, select

logger = logging.getLogger(__name__)


class CalibrationRepository:
    """Repository for calibration service registry operations."""

    def __init__(self):
        logger.info("Calibration repository initialized (SQLAlchemy async)")

    async def initialize(self) -> None:
        logger.info("Calibration repository initialized")

    async def close(self) -> None:
        logger.info("Calibration repository closed")

    async def save_calibrator(self, calibrator: CalibratorRegistry) -> CalibratorRegistry:
        """Save or update a calibrator registration."""
        try:
            async with get_session() as session:
                stmt = select(CalibratorRegistryORM).where(
                    CalibratorRegistryORM.calibrator_id == calibrator.calibrator_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.name = calibrator.name
                    existing.version = calibrator.version
                    existing.description = calibrator.description
                    existing.calibration_url = calibrator.calibration_url
                    existing.health_check_url = calibrator.health_check_url
                    existing.supported_modes = calibrator.supported_modes
                    existing.status = calibrator.status
                    existing.last_health_check = calibrator.last_health_check
                    existing.health_check_failures = calibrator.health_check_failures
                else:
                    new_cal = CalibratorRegistryORM(
                        calibrator_id=calibrator.calibrator_id,
                        name=calibrator.name,
                        version=calibrator.version,
                        description=calibrator.description,
                        calibration_url=calibrator.calibration_url,
                        health_check_url=calibrator.health_check_url,
                        supported_modes=calibrator.supported_modes,
                        status=calibrator.status,
                        last_health_check=calibrator.last_health_check,
                        health_check_failures=calibrator.health_check_failures,
                    )
                    session.add(new_cal)

                await session.commit()

                if existing:
                    await session.refresh(existing)
                    result_cal = existing
                else:
                    result_cal = new_cal

                return self._orm_to_calibrator_registry(result_cal)

        except Exception as e:
            logger.error(f"Failed to save calibrator {calibrator.calibrator_id}: {str(e)}")
            raise

    async def get_calibrator(self, calibrator_id: str) -> Optional[CalibratorRegistry]:
        """Get a calibrator by ID."""
        try:
            async with get_session() as session:
                stmt = select(CalibratorRegistryORM).where(
                    CalibratorRegistryORM.calibrator_id == calibrator_id
                )
                result = await session.execute(stmt)
                orm_cal = result.scalar_one_or_none()

                if orm_cal is None:
                    return None

                return self._orm_to_calibrator_registry(orm_cal)

        except Exception as e:
            logger.error(f"Failed to get calibrator {calibrator_id}: {str(e)}")
            raise

    async def list_calibrators(self, status: Optional[str] = None) -> list[CalibratorRegistry]:
        """List all calibrators, optionally filtered by status."""
        try:
            async with get_session() as session:
                stmt = select(CalibratorRegistryORM)
                if status:
                    stmt = stmt.where(CalibratorRegistryORM.status == status)
                stmt = stmt.order_by(CalibratorRegistryORM.name, CalibratorRegistryORM.version)
                result = await session.execute(stmt)
                orm_cals = result.scalars().all()

                return [self._orm_to_calibrator_registry(c) for c in orm_cals]

        except Exception as e:
            logger.error(f"Failed to list calibrators: {str(e)}")
            raise

    async def save_capability(self, capability: CalibratorCapability) -> CalibratorCapability:
        """Save a calibrator capability."""
        try:
            async with get_session() as session:
                new_cap = CalibratorCapabilityORM(
                    calibrator_id=capability.calibrator_id,
                    curve_type=capability.curve_type,
                    asset_class=capability.asset_class,
                    currency=capability.currency,
                    method=capability.method,
                    features=capability.features or [],
                    priority=capability.priority,
                )
                session.add(new_cap)
                await session.commit()
                await session.refresh(new_cap)

                return self._orm_to_calibrator_capability(new_cap)

        except Exception as e:
            logger.error(f"Failed to save calibrator capability: {str(e)}")
            raise

    async def get_calibrator_capabilities(
        self, calibrator_id: str
    ) -> list[CalibratorCapability]:
        """Get all capabilities for a calibrator."""
        try:
            async with get_session() as session:
                stmt = select(CalibratorCapabilityORM).where(
                    CalibratorCapabilityORM.calibrator_id == calibrator_id
                )
                result = await session.execute(stmt)
                orm_caps = result.scalars().all()

                return [self._orm_to_calibrator_capability(c) for c in orm_caps]

        except Exception as e:
            logger.error(f"Failed to get capabilities for {calibrator_id}: {str(e)}")
            raise

    async def query_capabilities(
        self,
        curve_type: str,
        asset_class: Optional[str] = None,
        currency: Optional[str] = None,
        method: Optional[str] = None,
    ) -> list[CalibratorCapability]:
        """Query capabilities by curve type, asset class, currency, and method."""
        try:
            async with get_session() as session:
                stmt = select(CalibratorCapabilityORM).where(
                    CalibratorCapabilityORM.curve_type == curve_type
                )

                if asset_class:
                    stmt = stmt.where(
                        or_(
                            CalibratorCapabilityORM.asset_class == asset_class,
                            CalibratorCapabilityORM.asset_class.is_(None),
                        )
                    )
                if currency:
                    stmt = stmt.where(
                        or_(
                            CalibratorCapabilityORM.currency == currency,
                            CalibratorCapabilityORM.currency.is_(None),
                        )
                    )
                if method:
                    stmt = stmt.where(
                        or_(
                            CalibratorCapabilityORM.method == method,
                            CalibratorCapabilityORM.method.is_(None),
                        )
                    )

                result = await session.execute(stmt)
                orm_caps = result.scalars().all()

                return [self._orm_to_calibrator_capability(c) for c in orm_caps]

        except Exception as e:
            logger.error(f"Failed to query calibrator capabilities: {str(e)}")
            raise

    def _orm_to_calibrator_registry(self, orm: CalibratorRegistryORM) -> CalibratorRegistry:
        return CalibratorRegistry(
            calibrator_id=orm.calibrator_id,
            name=orm.name,
            version=orm.version,
            description=orm.description,
            calibration_url=orm.calibration_url,
            health_check_url=orm.health_check_url,
            supported_modes=orm.supported_modes or {},
            status=orm.status,
            last_health_check=orm.last_health_check,
            health_check_failures=orm.health_check_failures,
        )

    def _orm_to_calibrator_capability(self, orm: CalibratorCapabilityORM) -> CalibratorCapability:
        return CalibratorCapability(
            calibrator_id=orm.calibrator_id,
            curve_type=orm.curve_type,
            asset_class=orm.asset_class,
            currency=orm.currency,
            method=orm.method,
            features=orm.features or [],
            priority=orm.priority,
        )
