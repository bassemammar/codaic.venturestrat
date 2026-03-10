"""Unit tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
  """Test health check endpoints."""

  def test_liveness_endpoint(self, client: TestClient):
    """Test liveness endpoint returns 200."""
    response = client.get('/health/live')
    assert response.status_code == 200

    data = response.json()
    assert data['status'] == 'alive'
    assert data['service'] == 'event-monitor'

  def test_readiness_endpoint(self, client: TestClient):
    """Test readiness endpoint returns 200."""
    response = client.get('/health/ready')
    assert response.status_code == 200

    data = response.json()
    assert 'status' in data
    assert 'writer' in data
    assert 'observer' in data

  def test_openapi_docs(self, client: TestClient):
    """Test OpenAPI documentation is available."""
    response = client.get('/docs')
    assert response.status_code == 200

    response = client.get('/openapi.json')
    assert response.status_code == 200

    openapi_data = response.json()
    assert openapi_data['info']['title'] == 'VentureStrat Event Monitor'
    assert openapi_data['info']['version'] == '1.0.0'

  def test_cors_headers(self, client: TestClient):
    """Test CORS headers are present."""
    response = client.options('/health/live')
    assert response.status_code == 200
    assert 'access-control-allow-origin' in response.headers
