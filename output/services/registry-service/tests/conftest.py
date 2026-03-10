"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add src/ to path for src-layout package
# This allows imports like `from registry.main import app` when running pytest from project root
_src_path = Path(__file__).parent.parent / "src"
if _src_path.exists() and str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from registry.main import app


# =============================================================================
# Event Loop Configuration
# =============================================================================
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# HTTP Clients
# =============================================================================
@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    """Synchronous test client for FastAPI."""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async test client for FastAPI."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


# =============================================================================
# Mock Data Fixtures
# =============================================================================
@pytest.fixture
def sample_manifest() -> dict[str, Any]:
    """Sample manifest.yaml content."""
    return {
        "name": "test-service",
        "version": "1.0.0",
        "description": "A test service for unit tests",
        "depends": ["market-data-service@^1.0.0"],
        "provides": {
            "apis": {"rest": "/api/v1/test"},
            "events": ["test.created", "test.updated"],
        },
        "health": {"liveness": "/health/live", "readiness": "/health/ready"},
    }


@pytest.fixture
def sample_registration() -> dict[str, Any]:
    """Sample service registration payload."""
    return {
        "name": "test-service",
        "version": "1.0.0",
        "instance_id": "test-service-abc123",
        "address": "10.0.1.50",
        "port": 8080,
        "protocol": "http",
        "depends": ["market-data-service@^1.0.0"],
        "provides": {"apis": {"rest": "/api/v1/test"}},
        "health_check": {
            "http_endpoint": "/health/ready",
            "interval_seconds": 10,
            "timeout_seconds": 5,
            "deregister_after_seconds": 60,
        },
        "tags": ["production", "eu-west"],
        "metadata": {"team": "platform"},
    }


# =============================================================================
# Docker/Integration Test Markers
# =============================================================================
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require Docker)")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")
