"""Integration tests for Outreach Service."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_service_startup_shutdown(client: TestClient):
    """Test that service starts up and shuts down correctly."""
    # Test basic connectivity
    response = client.get("/health/live")
    assert response.status_code == 200


@pytest.mark.integration
def test_openapi_schema(client: TestClient):
    """Test that OpenAPI schema is generated correctly."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "info" in schema
    assert schema["info"]["title"] == "Outreach Service"


@pytest.mark.integration
def test_docs_endpoints(client: TestClient):
    """Test that documentation endpoints are accessible."""
    # Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200

    # ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200


@pytest.mark.integration
def test_cors_headers(client: TestClient):
    """Test that CORS headers are set correctly."""
    response = client.options("/health/live", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


@pytest.mark.integration
def test_full_outreach_service_lifecycle(client: TestClient):
    """Test complete outreach_service lifecycle: create, read, update, delete."""
    # Create
    create_data = {
        "name": "integration-test-outreach_service",
        "description": "Outreach Service for integration testing",
        "metadata": {"test_type": "integration"},
    }

    create_response = client.post("/api/v1/outreach_service", json=create_data)
    assert create_response.status_code == 201
    outreach_service_data = create_response.json()
    outreach_service_id = outreach_service_data["id"]

    # Read
    get_response = client.get(f"/api/v1/outreach_service/{ outreach_service_id }")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["name"] == create_data["name"]

    # Update
    update_data = {"description": "Updated integration test outreach_service"}
    update_response = client.put(f"/api/v1/outreach_service/{ outreach_service_id }", json=update_data)
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["description"] == update_data["description"]

    # Delete
    delete_response = client.delete(f"/api/v1/outreach_service/{ outreach_service_id }")
    assert delete_response.status_code == 204

    # Verify deletion
    final_get_response = client.get(f"/api/v1/outreach_service/{ outreach_service_id }")
    assert final_get_response.status_code == 404
