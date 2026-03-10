"""Pytest configuration and shared fixtures for investor-service."""

import os

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("PLATFORM_MODE", "standalone")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application instance."""
    from investor_service.main import app
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Return authorization headers with default test tenant."""
    return {
        "Authorization": "Bearer test-token",
        "X-Tenant-ID": "00000000-0000-0000-0000-000000000000",
    }
