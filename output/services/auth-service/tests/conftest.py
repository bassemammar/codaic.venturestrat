"""Test configuration and fixtures for Auth Service."""

import pytest
from fastapi.testclient import TestClient

from auth_service.main import app
from auth_service.api.auth_service import _auth_service_store


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_auth_service_store():
    """Clear the in-memory auth_service store before each test."""
    _auth_service_store.clear()
    yield
    _auth_service_store.clear()


@pytest.fixture
def sample_auth_service_data() -> dict:
    """Sample auth_service data for testing."""
    return {
        "name": "test-auth_service",
        "description": "A test auth_service for unit tests",
        "metadata": {"test": True},
    }
