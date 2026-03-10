"""Unit tests for Investor Service models."""

import pytest
from uuid import UUID
from datetime import datetime

from investor_service.models import (
    InvestorService,
    InvestorServiceCreate,
    InvestorServiceUpdate,
    InvestorServiceList,
    HealthCheck,
)


@pytest.mark.unit
def test_investor_service_create_model():
    """Test InvestorServiceCreate model validation."""
    data = {
        "name": "test-investor_service",
        "description": "A test investor_service",
        "metadata": {"key": "value"},
    }

    investor_service = InvestorServiceCreate(**data)
    assert investor_service.name == "test-investor_service"
    assert investor_service.description == "A test investor_service"
    assert investor_service.metadata == {"key": "value"}


@pytest.mark.unit
def test_investor_service_create_model_required_fields():
    """Test InvestorServiceCreate model requires name field."""
    with pytest.raises(ValueError):
        InvestorServiceCreate(description="Missing name")


@pytest.mark.unit
def test_investor_service_update_model():
    """Test InvestorServiceUpdate model allows partial updates."""
    update = InvestorServiceUpdate(name="updated-name")
    assert update.name == "updated-name"
    assert update.description is None
    assert update.metadata is None


@pytest.mark.unit
def test_investor_service_full_model():
    """Test InvestorService model with auto-generated fields."""
    data = {
        "name": "test-investor_service",
        "description": "A test investor_service",
        "metadata": {"key": "value"},
    }

    investor_service = InvestorService(**data)
    assert isinstance(investor_service.id, UUID)
    assert isinstance(investor_service.created_at, datetime)
    assert investor_service.updated_at is None
    assert investor_service.name == "test-investor_service"


@pytest.mark.unit
def test_investor_service_list_model():
    """Test InvestorServiceList model structure."""
    investor_service_list = InvestorServiceList(
        items=[],
        total=0,
        offset=0,
        limit=100,
    )
    assert investor_service_list.items == []
    assert investor_service_list.total == 0
    assert investor_service_list.offset == 0
    assert investor_service_list.limit == 100


@pytest.mark.unit
def test_health_check_model():
    """Test HealthCheck model structure."""
    health = HealthCheck(
        status="healthy",
        service="investor-service",
        version="1.0.0",
    )
    assert health.status == "healthy"
    assert health.service == "investor-service"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
