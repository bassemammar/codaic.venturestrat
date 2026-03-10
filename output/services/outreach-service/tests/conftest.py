"""Test configuration and fixtures for Outreach Service."""

import pytest
from fastapi.testclient import TestClient

from outreach_service.main import app
from outreach_service.api.outreach_service import _outreach_service_store


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_outreach_service_store():
    """Clear the in-memory outreach_service store before each test."""
    _outreach_service_store.clear()
    yield
    _outreach_service_store.clear()


@pytest.fixture
def sample_outreach_service_data() -> dict:
    """Sample outreach_service data for testing."""
    return {
        "name": "test-outreach_service",
        "description": "A test outreach_service for unit tests",
        "metadata": {"test": True},
    }
