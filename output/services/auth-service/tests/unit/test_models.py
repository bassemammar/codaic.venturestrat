"""Unit tests for Auth Service models."""

import pytest
from uuid import UUID
from datetime import datetime

from auth_service.models import (
    AuthService,
    AuthServiceCreate,
    AuthServiceUpdate,
    AuthServiceList,
    HealthCheck,
)


@pytest.mark.unit
def test_auth_service_create_model():
    """Test AuthServiceCreate model validation."""
    data = {
        "name": "test-auth_service",
        "description": "A test auth_service",
        "metadata": {"key": "value"},
    }

    auth_service = AuthServiceCreate(**data)
    assert auth_service.name == "test-auth_service"
    assert auth_service.description == "A test auth_service"
    assert auth_service.metadata == {"key": "value"}


@pytest.mark.unit
def test_auth_service_create_model_required_fields():
    """Test AuthServiceCreate model requires name field."""
    with pytest.raises(ValueError):
        AuthServiceCreate(description="Missing name")


@pytest.mark.unit
def test_auth_service_update_model():
    """Test AuthServiceUpdate model allows partial updates."""
    update = AuthServiceUpdate(name="updated-name")
    assert update.name == "updated-name"
    assert update.description is None
    assert update.metadata is None


@pytest.mark.unit
def test_auth_service_full_model():
    """Test AuthService model with auto-generated fields."""
    data = {
        "name": "test-auth_service",
        "description": "A test auth_service",
        "metadata": {"key": "value"},
    }

    auth_service = AuthService(**data)
    assert isinstance(auth_service.id, UUID)
    assert isinstance(auth_service.created_at, datetime)
    assert auth_service.updated_at is None
    assert auth_service.name == "test-auth_service"


@pytest.mark.unit
def test_auth_service_list_model():
    """Test AuthServiceList model structure."""
    auth_service_list = AuthServiceList(
        items=[],
        total=0,
        offset=0,
        limit=100,
    )
    assert auth_service_list.items == []
    assert auth_service_list.total == 0
    assert auth_service_list.offset == 0
    assert auth_service_list.limit == 100


@pytest.mark.unit
def test_health_check_model():
    """Test HealthCheck model structure."""
    health = HealthCheck(
        status="healthy",
        service="auth-service",
        version="1.0.0",
    )
    assert health.status == "healthy"
    assert health.service == "auth-service"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
