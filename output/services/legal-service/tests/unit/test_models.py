"""Unit tests for Legal Service models."""

import pytest
from uuid import UUID
from datetime import datetime

from legal_service.models import (
    LegalService,
    LegalServiceCreate,
    LegalServiceUpdate,
    LegalServiceList,
    HealthCheck,
)


@pytest.mark.unit
def test_legal_service_create_model():
    """Test LegalServiceCreate model validation."""
    data = {
        "name": "test-legal_service",
        "description": "A test legal_service",
        "metadata": {"key": "value"},
    }

    legal_service = LegalServiceCreate(**data)
    assert legal_service.name == "test-legal_service"
    assert legal_service.description == "A test legal_service"
    assert legal_service.metadata == {"key": "value"}


@pytest.mark.unit
def test_legal_service_create_model_required_fields():
    """Test LegalServiceCreate model requires name field."""
    with pytest.raises(ValueError):
        LegalServiceCreate(description="Missing name")


@pytest.mark.unit
def test_legal_service_update_model():
    """Test LegalServiceUpdate model allows partial updates."""
    update = LegalServiceUpdate(name="updated-name")
    assert update.name == "updated-name"
    assert update.description is None
    assert update.metadata is None


@pytest.mark.unit
def test_legal_service_full_model():
    """Test LegalService model with auto-generated fields."""
    data = {
        "name": "test-legal_service",
        "description": "A test legal_service",
        "metadata": {"key": "value"},
    }

    legal_service = LegalService(**data)
    assert isinstance(legal_service.id, UUID)
    assert isinstance(legal_service.created_at, datetime)
    assert legal_service.updated_at is None
    assert legal_service.name == "test-legal_service"


@pytest.mark.unit
def test_legal_service_list_model():
    """Test LegalServiceList model structure."""
    legal_service_list = LegalServiceList(
        items=[],
        total=0,
        offset=0,
        limit=100,
    )
    assert legal_service_list.items == []
    assert legal_service_list.total == 0
    assert legal_service_list.offset == 0
    assert legal_service_list.limit == 100


@pytest.mark.unit
def test_health_check_model():
    """Test HealthCheck model structure."""
    health = HealthCheck(
        status="healthy",
        service="legal-service",
        version="1.0.0",
    )
    assert health.status == "healthy"
    assert health.service == "legal-service"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
