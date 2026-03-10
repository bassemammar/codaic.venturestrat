"""SQLAlchemy ORM models for registry service.

This module defines the SQLAlchemy table structures that map to the
BaseModel classes, enabling direct database operations.
"""
from __future__ import annotations

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class PricerRegistryORM(Base):
    """SQLAlchemy ORM model for pricer_registry table."""

    __tablename__ = "pricer_registry"
    __table_args__ = {"schema": "registry"}

    pricer_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    health_check_url = Column(String(512), nullable=False)
    pricing_url = Column(String(512), nullable=False)
    batch_supported = Column(Boolean, default=False)
    max_batch_size = Column(Integer, nullable=True)
    status = Column(String(20), default="unknown")
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_check_failures = Column(Integer, default=0)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PricerCapabilityORM(Base):
    """SQLAlchemy ORM model for pricer_capability table."""

    __tablename__ = "pricer_capability"
    __table_args__ = {"schema": "registry"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pricer_id = Column(
        String(255),
        ForeignKey("registry.pricer_registry.pricer_id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument_type = Column(String(100), nullable=False)
    model_type = Column(String(100), nullable=True)
    features = Column(ARRAY(Text), nullable=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CalibratorRegistryORM(Base):
    """SQLAlchemy ORM model for calibrator_registry table."""

    __tablename__ = "calibrator_registry"
    __table_args__ = {"schema": "registry"}

    calibrator_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    calibration_url = Column(String(512), nullable=False)
    health_check_url = Column(String(512), nullable=True)
    supported_modes = Column(JSONB, default={})
    status = Column(String(20), default="unknown")
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_check_failures = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalibratorCapabilityORM(Base):
    """SQLAlchemy ORM model for calibrator_capability table."""

    __tablename__ = "calibrator_capability"
    __table_args__ = {"schema": "registry"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    calibrator_id = Column(
        String(255),
        ForeignKey("registry.calibrator_registry.calibrator_id", ondelete="CASCADE"),
        nullable=False,
    )
    curve_type = Column(String(50), nullable=False)
    asset_class = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=True)
    method = Column(String(50), nullable=True)
    features = Column(ARRAY(Text), nullable=True)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantPricingConfigORM(Base):
    """SQLAlchemy ORM model for tenant_pricing_config table."""

    __tablename__ = "tenant_pricing_config"
    __table_args__ = {"schema": "registry"}

    tenant_id = Column(String(36), primary_key=True)
    default_pricer_id = Column(
        String(255),
        ForeignKey("registry.pricer_registry.pricer_id"),
        nullable=True,
    )
    fallback_pricer_id = Column(
        String(255),
        ForeignKey("registry.pricer_registry.pricer_id"),
        nullable=True,
    )
    config_json = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
