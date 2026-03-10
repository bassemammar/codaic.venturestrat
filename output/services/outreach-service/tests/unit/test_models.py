"""Unit tests for Outreach Service models."""

import pytest
from uuid import UUID
from datetime import datetime

from outreach_service.models import (
    OutreachService,
    OutreachServiceCreate,
    OutreachServiceUpdate,
    OutreachServiceList,
    HealthCheck,
)


@pytest.mark.unit
def test_outreach_service_create_model():
    """Test OutreachServiceCreate model validation."""
    data = {
        "name": "test-outreach_service",
        "description": "A test outreach_service",
        "metadata": {"key": "value"},
    }

    outreach_service = OutreachServiceCreate(**data)
    assert outreach_service.name == "test-outreach_service"
    assert outreach_service.description == "A test outreach_service"
    assert outreach_service.metadata == {"key": "value"}


@pytest.mark.unit
def test_outreach_service_create_model_required_fields():
    """Test OutreachServiceCreate model requires name field."""
    with pytest.raises(ValueError):
        OutreachServiceCreate(description="Missing name")


@pytest.mark.unit
def test_outreach_service_update_model():
    """Test OutreachServiceUpdate model allows partial updates."""
    update = OutreachServiceUpdate(name="updated-name")
    assert update.name == "updated-name"
    assert update.description is None
    assert update.metadata is None


@pytest.mark.unit
def test_outreach_service_full_model():
    """Test OutreachService model with auto-generated fields."""
    data = {
        "name": "test-outreach_service",
        "description": "A test outreach_service",
        "metadata": {"key": "value"},
    }

    outreach_service = OutreachService(**data)
    assert isinstance(outreach_service.id, UUID)
    assert isinstance(outreach_service.created_at, datetime)
    assert outreach_service.updated_at is None
    assert outreach_service.name == "test-outreach_service"


@pytest.mark.unit
def test_outreach_service_list_model():
    """Test OutreachServiceList model structure."""
    outreach_service_list = OutreachServiceList(
        items=[],
        total=0,
        offset=0,
        limit=100,
    )
    assert outreach_service_list.items == []
    assert outreach_service_list.total == 0
    assert outreach_service_list.offset == 0
    assert outreach_service_list.limit == 100


@pytest.mark.unit
def test_health_check_model():
    """Test HealthCheck model structure."""
    health = HealthCheck(
        status="healthy",
        service="outreach-service",
        version="1.0.0",
    )
    assert health.status == "healthy"
    assert health.service == "outreach-service"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
