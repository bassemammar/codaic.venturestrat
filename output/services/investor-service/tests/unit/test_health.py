"""Unit tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_liveness_endpoint(client: TestClient):
    """Test liveness endpoint returns expected status."""
    response = client.get("/health/live")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "investor-service"


@pytest.mark.unit
def test_readiness_endpoint(client: TestClient):
    """Test readiness endpoint returns expected status."""
    response = client.get("/health/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "investor-service"
