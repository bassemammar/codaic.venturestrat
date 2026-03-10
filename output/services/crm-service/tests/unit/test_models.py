"""Unit tests for Crm Service models."""

import pytest
from uuid import UUID
from datetime import datetime

from crm_service.models import (
    CrmService,
    CrmServiceCreate,
    CrmServiceUpdate,
    CrmServiceList,
    HealthCheck,
)


@pytest.mark.unit
def test_crm_service_create_model():
    """Test CrmServiceCreate model validation."""
    data = {
        "name": "test-crm_service",
        "description": "A test crm_service",
        "metadata": {"key": "value"},
    }

    crm_service = CrmServiceCreate(**data)
    assert crm_service.name == "test-crm_service"
    assert crm_service.description == "A test crm_service"
    assert crm_service.metadata == {"key": "value"}


@pytest.mark.unit
def test_crm_service_create_model_required_fields():
    """Test CrmServiceCreate model requires name field."""
    with pytest.raises(ValueError):
        CrmServiceCreate(description="Missing name")


@pytest.mark.unit
def test_crm_service_update_model():
    """Test CrmServiceUpdate model allows partial updates."""
    update = CrmServiceUpdate(name="updated-name")
    assert update.name == "updated-name"
    assert update.description is None
    assert update.metadata is None


@pytest.mark.unit
def test_crm_service_full_model():
    """Test CrmService model with auto-generated fields."""
    data = {
        "name": "test-crm_service",
        "description": "A test crm_service",
        "metadata": {"key": "value"},
    }

    crm_service = CrmService(**data)
    assert isinstance(crm_service.id, UUID)
    assert isinstance(crm_service.created_at, datetime)
    assert crm_service.updated_at is None
    assert crm_service.name == "test-crm_service"


@pytest.mark.unit
def test_crm_service_list_model():
    """Test CrmServiceList model structure."""
    crm_service_list = CrmServiceList(
        items=[],
        total=0,
        offset=0,
        limit=100,
    )
    assert crm_service_list.items == []
    assert crm_service_list.total == 0
    assert crm_service_list.offset == 0
    assert crm_service_list.limit == 100


@pytest.mark.unit
def test_health_check_model():
    """Test HealthCheck model structure."""
    health = HealthCheck(
        status="healthy",
        service="crm-service",
        version="1.0.0",
    )
    assert health.status == "healthy"
    assert health.service == "crm-service"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
