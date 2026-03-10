"""Integration tests for Event Monitor."""

import pytest
from fastapi.testclient import TestClient


class TestServiceIntegration:
  """Integration tests for the complete service."""

  def test_service_startup_and_health(self, client: TestClient):
    """Test service starts up and health endpoints work."""
    # Test liveness
    response = client.get('/health/live')
    assert response.status_code == 200
    assert response.json()['status'] == 'alive'

    # Test readiness
    response = client.get('/health/ready')
    assert response.status_code == 200

  def test_root_endpoint(self, client: TestClient):
    """Test root endpoint returns service info."""
    response = client.get('/')
    assert response.status_code == 200

    data = response.json()
    assert data['service'] == 'VentureStrat Event Monitor'
    assert data['version'] == '1.0.0'
    assert data['docs'] == '/docs'

  def test_application_lifecycle(self, client: TestClient):
    """Test application lifecycle endpoints."""
    # Test that the app can handle multiple requests
    for _ in range(10):
      response = client.get('/health/live')
      assert response.status_code == 200

    # Test different endpoints
    endpoints = ['/health/live', '/health/ready', '/openapi.json']
    for endpoint in endpoints:
      response = client.get(endpoint)
      assert response.status_code == 200

  def test_error_handling(self, client: TestClient):
    """Test error handling for non-existent endpoints."""
    response = client.get('/nonexistent')
    assert response.status_code == 404

    # Ensure the 404 response is properly formatted
    assert response.headers['content-type'].startswith('application/json')
