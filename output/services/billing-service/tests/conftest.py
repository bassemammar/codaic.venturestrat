"""Test configuration and fixtures for Billing Service."""

import pytest
from fastapi.testclient import TestClient

from billing_service.main import app
from billing_service.api.billing_service import _billing_service_store


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_billing_service_store():
    """Clear the in-memory billing_service store before each test."""
    _billing_service_store.clear()
    yield
    _billing_service_store.clear()


@pytest.fixture
def sample_billing_service_data() -> dict:
    """Sample billing_service data for testing."""
    return {
        "name": "test-billing_service",
        "description": "A test billing_service for unit tests",
        "metadata": {"test": True},
    }
