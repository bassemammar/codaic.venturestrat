"""Test configuration and fixtures for Legal Service."""

import pytest
from fastapi.testclient import TestClient

from legal_service.main import app
from legal_service.api.legal_service import _legal_service_store


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_legal_service_store():
    """Clear the in-memory legal_service store before each test."""
    _legal_service_store.clear()
    yield
    _legal_service_store.clear()


@pytest.fixture
def sample_legal_service_data() -> dict:
    """Sample legal_service data for testing."""
    return {
        "name": "test-legal_service",
        "description": "A test legal_service for unit tests",
        "metadata": {"test": True},
    }
