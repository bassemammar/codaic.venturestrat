"""Test configuration and fixtures for Crm Service."""

import pytest
from fastapi.testclient import TestClient

from crm_service.main import app
from crm_service.api.crm_service import _crm_service_store


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_crm_service_store():
    """Clear the in-memory crm_service store before each test."""
    _crm_service_store.clear()
    yield
    _crm_service_store.clear()


@pytest.fixture
def sample_crm_service_data() -> dict:
    """Sample crm_service data for testing."""
    return {
        "name": "test-crm_service",
        "description": "A test crm_service for unit tests",
        "metadata": {"test": True},
    }
