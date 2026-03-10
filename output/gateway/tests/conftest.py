"""
Test configuration and fixtures for gateway tests.
"""

import pytest
import httpx
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from testcontainers.compose import DockerCompose

# Test configuration
TEST_GATEWAY_URL = "http://localhost:8000"
TEST_ADMIN_URL = "http://localhost:8001"
TEST_JWT_ISSUER_URL = "http://localhost:8002"


@pytest.fixture(scope="session")
def gateway_config() -> Dict[str, Any]:
    """Load and parse kong.yaml configuration for testing."""
    config_path = Path(__file__).parent.parent / "kong.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def docker_compose_file() -> str:
    """Docker compose file path for integration tests."""
    return str(Path(__file__).parent.parent / "docker-compose.gateway.yaml")


@pytest.fixture(scope="session")
def gateway_stack(docker_compose_file):
    """Start gateway + dependencies for integration tests."""
    # Only run if INTEGRATION_TESTS env var is set
    if not os.getenv("INTEGRATION_TESTS"):
        pytest.skip("Integration tests disabled. Set INTEGRATION_TESTS=1 to enable.")

    # Change to project root directory where docker-compose files are located
    project_root = Path(__file__).parent.parent.parent

    compose = DockerCompose(
        filepath=str(project_root),
        compose_file_name=[
            "docker-compose.infra.yaml",  # Infrastructure services
            docker_compose_file,  # Gateway services
        ],
    )

    try:
        compose.start()

        # Wait for Kong health
        for attempt in range(60):  # 2 minutes timeout
            try:
                response = httpx.get(f"{TEST_GATEWAY_URL}/health", timeout=2)
                if response.status_code == 200:
                    break
            except Exception:
                pass
            import time

            time.sleep(2)  # Use time.sleep instead of asyncio.sleep
        else:
            raise RuntimeError("Gateway did not become healthy within timeout")

        yield compose

    finally:
        compose.stop()


@pytest.fixture
def gateway_client(gateway_stack):
    """HTTP client configured for gateway with default API key."""
    return httpx.Client(
        base_url=TEST_GATEWAY_URL,
        headers={"X-API-Key": "dev-api-key-12345"},
        timeout=10.0,
    )


@pytest.fixture
def unauthorized_client(gateway_stack):
    """HTTP client without authentication."""
    return httpx.Client(base_url=TEST_GATEWAY_URL, timeout=10.0)


@pytest.fixture
def admin_client(gateway_stack):
    """HTTP client for Kong Admin API."""
    return httpx.Client(base_url=TEST_ADMIN_URL, timeout=10.0)


@pytest.fixture
def jwt_issuer_client(gateway_stack):
    """HTTP client for JWT issuer service."""
    return httpx.Client(base_url=TEST_JWT_ISSUER_URL, timeout=10.0)


@pytest.fixture
def free_tier_client(gateway_stack):
    """HTTP client with free tier API key."""
    return httpx.Client(
        base_url=TEST_GATEWAY_URL,
        headers={"X-API-Key": "free-api-key-11111"},
        timeout=10.0,
    )


@pytest.fixture
def standard_tier_client(gateway_stack):
    """HTTP client with standard tier API key."""
    return httpx.Client(
        base_url=TEST_GATEWAY_URL,
        headers={"X-API-Key": "standard-api-key-22222"},
        timeout=10.0,
    )


@pytest.fixture
def premium_tier_client(gateway_stack):
    """HTTP client with premium tier API key."""
    return httpx.Client(
        base_url=TEST_GATEWAY_URL,
        headers={"X-API-Key": "premium-api-key-33333"},
        timeout=10.0,
    )


@pytest.fixture
def correlation_id() -> str:
    """Generate a unique correlation ID for test requests."""
    import uuid

    return f"test-{uuid.uuid4()}"


class MockBackendService:
    """Mock backend service for testing gateway behavior."""

    def __init__(self, base_url: str = "http://httpbin.org"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)

    def get_services(self):
        """Mock registry service list endpoint."""
        return {"services": []}

    def health_check(self):
        """Mock health check endpoint."""
        return {"status": "healthy"}


@pytest.fixture
def mock_backend():
    """Mock backend service instance."""
    return MockBackendService()


# Test markers
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require Docker)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (require Docker)"
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests (full stack)")
    config.addinivalue_line("markers", "slow: Tests taking > 30 seconds")
