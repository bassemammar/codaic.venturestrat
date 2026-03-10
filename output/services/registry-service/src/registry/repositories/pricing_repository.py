"""Pricing Repository for pricing service registry operations.

This module provides data access layer for pricing service registration,
capability management, and tenant pricing configuration using SQLAlchemy async sessions.
"""

from __future__ import annotations

import logging
from typing import Optional

from registry.db_models import (
    PricerCapabilityORM,
    PricerRegistryORM,
    TenantPricingConfigORM,
)
from registry.db_session import get_session
from registry.models.pricer_capability import PricerCapability
from registry.models.pricer_registry import PricerRegistry
from registry.models.tenant_pricing_config import TenantPricingConfig
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PricingRepository:
    """Repository for pricing service registry operations using SQLAlchemy async sessions."""

    def __init__(self):
        """Initialize the pricing repository."""
        logger.info("Pricing repository initialized (SQLAlchemy async)")

    async def initialize(self) -> None:
        """Initialize database connection."""
        logger.info("Pricing repository initialized (SQLAlchemy)")

    async def close(self) -> None:
        """Close database connections."""
        logger.info("Pricing repository closed (SQLAlchemy)")

    # =============================================================================
    # Pricer Registry Operations
    # =============================================================================

    async def save_pricer(self, pricer: PricerRegistry) -> PricerRegistry:
        """Save or update a pricer registration.

        Args:
            pricer: Pricer registry instance to save

        Returns:
            Saved pricer instance

        Raises:
            Exception: If save operation fails
        """
        try:
            async with get_session() as session:
                # Check if pricer already exists
                stmt = select(PricerRegistryORM).where(
                    PricerRegistryORM.pricer_id == pricer.pricer_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing pricer
                    existing.name = pricer.name
                    existing.version = pricer.version
                    existing.description = pricer.description
                    existing.health_check_url = pricer.health_check_url
                    existing.pricing_url = pricer.pricing_url
                    existing.batch_supported = pricer.batch_supported
                    existing.max_batch_size = pricer.max_batch_size
                    existing.status = pricer.status
                    existing.last_health_check = pricer.last_health_check
                    existing.health_check_failures = pricer.health_check_failures
                else:
                    # Create new pricer
                    new_pricer = PricerRegistryORM(
                        pricer_id=pricer.pricer_id,
                        name=pricer.name,
                        version=pricer.version,
                        description=pricer.description,
                        health_check_url=pricer.health_check_url,
                        pricing_url=pricer.pricing_url,
                        batch_supported=pricer.batch_supported,
                        max_batch_size=pricer.max_batch_size,
                        status=pricer.status,
                        last_health_check=pricer.last_health_check,
                        health_check_failures=pricer.health_check_failures,
                    )
                    session.add(new_pricer)

                await session.commit()

                # Refresh to get the saved instance
                if existing:
                    await session.refresh(existing)
                    result_pricer = existing
                else:
                    result_pricer = new_pricer

                # Convert ORM to BaseModel
                result = self._orm_to_pricer_registry(result_pricer)

                logger.info(f"Saved pricer: {result.pricer_id}")
                return result

        except Exception as e:
            logger.error(f"Failed to save pricer {pricer.pricer_id}: {str(e)}")
            raise

    async def get_pricer(self, pricer_id: str) -> Optional[PricerRegistry]:
        """Get a pricer by ID.

        Args:
            pricer_id: Pricer identifier

        Returns:
            Pricer instance or None if not found
        """
        try:
            async with get_session() as session:
                stmt = select(PricerRegistryORM).where(PricerRegistryORM.pricer_id == pricer_id)
                result = await session.execute(stmt)
                orm_pricer = result.scalar_one_or_none()

                if orm_pricer is None:
                    return None

                return self._orm_to_pricer_registry(orm_pricer)

        except Exception as e:
            logger.error(f"Failed to get pricer {pricer_id}: {str(e)}")
            raise

    async def list_pricers(self, status: Optional[str] = None) -> list[PricerRegistry]:
        """List all pricers, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of pricers
        """
        try:
            async with get_session() as session:
                stmt = select(PricerRegistryORM)
                if status:
                    stmt = stmt.where(PricerRegistryORM.status == status)

                stmt = stmt.order_by(PricerRegistryORM.name, PricerRegistryORM.version)
                result = await session.execute(stmt)
                orm_pricers = result.scalars().all()

                return [self._orm_to_pricer_registry(p) for p in orm_pricers]

        except Exception as e:
            logger.error(f"Failed to list pricers: {str(e)}")
            raise

    # =============================================================================
    # Pricer Capability Operations
    # =============================================================================

    async def save_capability(self, capability: PricerCapability) -> PricerCapability:
        """Save a pricer capability.

        Args:
            capability: Capability instance to save

        Returns:
            Saved capability instance

        Raises:
            Exception: If save operation fails
        """
        try:
            async with get_session() as session:
                new_cap = PricerCapabilityORM(
                    pricer_id=capability.pricer_id,
                    instrument_type=capability.instrument_type,
                    model_type=capability.model_type,
                    features=capability.features or [],
                    priority=capability.priority,
                )
                session.add(new_cap)
                await session.commit()
                await session.refresh(new_cap)

                result = self._orm_to_pricer_capability(new_cap)

                logger.debug(f"Saved capability: {result.pricer_id} - {result.instrument_type}")
                return result

        except Exception as e:
            logger.error(f"Failed to save capability: {str(e)}")
            raise

    async def get_pricer_capabilities(self, pricer_id: str) -> list[PricerCapability]:
        """Get all capabilities for a pricer.

        Args:
            pricer_id: Pricer identifier

        Returns:
            List of capabilities for the pricer
        """
        try:
            async with get_session() as session:
                stmt = select(PricerCapabilityORM).where(PricerCapabilityORM.pricer_id == pricer_id)
                result = await session.execute(stmt)
                orm_caps = result.scalars().all()

                return [self._orm_to_pricer_capability(c) for c in orm_caps]

        except Exception as e:
            logger.error(f"Failed to get capabilities for {pricer_id}: {str(e)}")
            raise

    async def query_capabilities(
        self,
        instrument_type: str,
        model_type: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> list[PricerCapability]:
        """Query capabilities by instrument type, model, and features.

        Args:
            instrument_type: Required instrument type
            model_type: Optional model type filter
            feature: Optional feature filter

        Returns:
            List of matching capabilities
        """
        try:
            async with get_session() as session:
                stmt = select(PricerCapabilityORM).where(
                    PricerCapabilityORM.instrument_type == instrument_type
                )

                if model_type:
                    stmt = stmt.where(PricerCapabilityORM.model_type == model_type)

                if feature:
                    # Use PostgreSQL array contains operator @>
                    from sqlalchemy import text

                    stmt = stmt.where(text(f"features @> ARRAY['{feature}']"))

                # Debug logging: Show SQL query
                logger.info(
                    f"[DEBUG] SQL Query for capabilities: instrument_type={instrument_type}, model_type={model_type}, feature={feature}"
                )
                logger.debug(f"[DEBUG] SQLAlchemy statement: {stmt}")

                result = await session.execute(stmt)
                orm_caps = result.scalars().all()

                logger.info(f"[DEBUG] Database returned {len(orm_caps)} capabilities")
                for cap in orm_caps:
                    logger.info(
                        f"[DEBUG]   - Capability: pricer_id={cap.pricer_id}, instrument_type={cap.instrument_type}, model_type={cap.model_type}, features={cap.features}"
                    )

                return [self._orm_to_pricer_capability(c) for c in orm_caps]

        except Exception as e:
            logger.error(f"Failed to query capabilities: {str(e)}")
            raise

    # =============================================================================
    # Tenant Pricing Config Operations
    # =============================================================================

    async def save_tenant_pricing_config(self, config: TenantPricingConfig) -> TenantPricingConfig:
        """Save or update tenant pricing configuration.

        Args:
            config: Tenant pricing config instance

        Returns:
            Saved configuration

        Raises:
            Exception: If save operation fails
        """
        try:
            async with get_session() as session:
                stmt = select(TenantPricingConfigORM).where(
                    TenantPricingConfigORM.tenant_id == config.tenant_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.default_pricer_id = config.default_pricer_id
                    existing.fallback_pricer_id = config.fallback_pricer_id
                    existing.config_json = config.config_json
                else:
                    # Create new
                    new_config = TenantPricingConfigORM(
                        tenant_id=config.tenant_id,
                        default_pricer_id=config.default_pricer_id,
                        fallback_pricer_id=config.fallback_pricer_id,
                        config_json=config.config_json,
                    )
                    session.add(new_config)

                await session.commit()

                if existing:
                    await session.refresh(existing)
                    result_config = existing
                else:
                    result_config = new_config

                result = self._orm_to_tenant_pricing_config(result_config)

                logger.info(f"Saved tenant pricing config: {result.tenant_id}")
                return result

        except Exception as e:
            logger.error(f"Failed to save tenant pricing config {config.tenant_id}: {str(e)}")
            raise

    async def get_tenant_pricing_config(self, tenant_id: str) -> Optional[TenantPricingConfig]:
        """Get tenant pricing configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Configuration or None if not found
        """
        try:
            async with get_session() as session:
                stmt = select(TenantPricingConfigORM).where(
                    TenantPricingConfigORM.tenant_id == tenant_id
                )
                result = await session.execute(stmt)
                orm_config = result.scalar_one_or_none()

                if orm_config is None:
                    return None

                return self._orm_to_tenant_pricing_config(orm_config)

        except Exception as e:
            logger.error(f"Failed to get tenant pricing config {tenant_id}: {str(e)}")
            raise

    # =============================================================================
    # Helper Methods
    # =============================================================================

    def _orm_to_pricer_registry(self, orm: PricerRegistryORM) -> PricerRegistry:
        """Convert ORM model to BaseModel."""
        return PricerRegistry(
            pricer_id=orm.pricer_id,
            name=orm.name,
            version=orm.version,
            description=orm.description,
            health_check_url=orm.health_check_url,
            pricing_url=orm.pricing_url,
            batch_supported=orm.batch_supported,
            max_batch_size=orm.max_batch_size,
            status=orm.status,
            last_health_check=orm.last_health_check,
            health_check_failures=orm.health_check_failures,
        )

    def _orm_to_pricer_capability(self, orm: PricerCapabilityORM) -> PricerCapability:
        """Convert ORM model to BaseModel."""
        return PricerCapability(
            pricer_id=orm.pricer_id,
            instrument_type=orm.instrument_type,
            model_type=orm.model_type,
            features=orm.features or [],
            priority=orm.priority,
        )

    def _orm_to_tenant_pricing_config(self, orm: TenantPricingConfigORM) -> TenantPricingConfig:
        """Convert ORM model to BaseModel."""
        return TenantPricingConfig(
            tenant_id=orm.tenant_id,
            default_pricer_id=orm.default_pricer_id,
            fallback_pricer_id=orm.fallback_pricer_id,
            config_json=orm.config_json or {},
        )
