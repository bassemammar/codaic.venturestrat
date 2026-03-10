"""Unit tests for Billing Service models."""

import pytest
from uuid import UUID
from datetime import datetime

from billing_service.models import (
    BillingService,
    BillingServiceCreate,
    BillingServiceUpdate,
    BillingServiceList,
    HealthCheck,
)


@pytest.mark.unit
def test_billing_service_create_model():
    """Test BillingServiceCreate model validation."""
    data = {
        "name": "test-billing_service",
        "description": "A test billing_service",
        "metadata": {"key": "value"},
    }

    billing_service = BillingServiceCreate(**data)
    assert billing_service.name == "test-billing_service"
    assert billing_service.description == "A test billing_service"
    assert billing_service.metadata == {"key": "value"}


@pytest.mark.unit
def test_billing_service_create_model_required_fields():
    """Test BillingServiceCreate model requires name field."""
    with pytest.raises(ValueError):
        BillingServiceCreate(description="Missing name")


@pytest.mark.unit
def test_billing_service_update_model():
    """Test BillingServiceUpdate model allows partial updates."""
    update = BillingServiceUpdate(name="updated-name")
    assert update.name == "updated-name"
    assert update.description is None
    assert update.metadata is None


@pytest.mark.unit
def test_billing_service_full_model():
    """Test BillingService model with auto-generated fields."""
    data = {
        "name": "test-billing_service",
        "description": "A test billing_service",
        "metadata": {"key": "value"},
    }

    billing_service = BillingService(**data)
    assert isinstance(billing_service.id, UUID)
    assert isinstance(billing_service.created_at, datetime)
    assert billing_service.updated_at is None
    assert billing_service.name == "test-billing_service"


@pytest.mark.unit
def test_billing_service_list_model():
    """Test BillingServiceList model structure."""
    billing_service_list = BillingServiceList(
        items=[],
        total=0,
        offset=0,
        limit=100,
    )
    assert billing_service_list.items == []
    assert billing_service_list.total == 0
    assert billing_service_list.offset == 0
    assert billing_service_list.limit == 100


@pytest.mark.unit
def test_health_check_model():
    """Test HealthCheck model structure."""
    health = HealthCheck(
        status="healthy",
        service="billing-service",
        version="1.0.0",
    )
    assert health.status == "healthy"
    assert health.service == "billing-service"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
