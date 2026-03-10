"""Unit tests for Investor Service API."""

import pytest
from uuid import UUID
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_list_investor_service_empty(client: TestClient):
    """Test listing investor_service when store is empty."""
    response = client.get("/api/v1/investor_service")
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["offset"] == 0
    assert data["limit"] == 100


@pytest.mark.unit
def test_create_investor_service(client: TestClient, sample_investor_service_data):
    """Test creating a new investor_service."""
    response = client.post("/api/v1/investor_service", json=sample_investor_service_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == sample_investor_service_data["name"]
    assert data["description"] == sample_investor_service_data["description"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.unit
def test_create_investor_service_duplicate_name(client: TestClient, sample_investor_service_data):
    """Test creating investor_service with duplicate name fails."""
    # Create first investor_service
    response1 = client.post("/api/v1/investor_service", json=sample_investor_service_data)
    assert response1.status_code == 201

    # Try to create second with same name
    response2 = client.post("/api/v1/investor_service", json=sample_investor_service_data)
    assert response2.status_code == 400


@pytest.mark.unit
def test_get_investor_service(client: TestClient, sample_investor_service_data):
    """Test getting a investor_service by ID."""
    # Create investor_service
    create_response = client.post("/api/v1/investor_service", json=sample_investor_service_data)
    investor_service_data = create_response.json()
    investor_service_id = investor_service_data["id"]

    # Get investor_service
    response = client.get(f"/api/v1/investor_service/{ investor_service_id }")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == investor_service_id
    assert data["name"] == sample_investor_service_data["name"]


@pytest.mark.unit
def test_get_investor_service_not_found(client: TestClient):
    """Test getting non-existent investor_service returns 404."""
    fake_id = "12345678-1234-5678-9abc-123456789012"
    response = client.get(f"/api/v1/investor_service/{fake_id}")
    assert response.status_code == 404


@pytest.mark.unit
def test_update_investor_service(client: TestClient, sample_investor_service_data):
    """Test updating a investor_service."""
    # Create investor_service
    create_response = client.post("/api/v1/investor_service", json=sample_investor_service_data)
    investor_service_data = create_response.json()
    investor_service_id = investor_service_data["id"]

    # Update investor_service
    update_data = {"description": "Updated description"}
    response = client.put(f"/api/v1/investor_service/{ investor_service_id }", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["description"] == "Updated description"
    assert data["updated_at"] is not None


@pytest.mark.unit
def test_delete_investor_service(client: TestClient, sample_investor_service_data):
    """Test deleting a investor_service."""
    # Create investor_service
    create_response = client.post("/api/v1/investor_service", json=sample_investor_service_data)
    investor_service_data = create_response.json()
    investor_service_id = investor_service_data["id"]

    # Delete investor_service
    response = client.delete(f"/api/v1/investor_service/{ investor_service_id }")
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(f"/api/v1/investor_service/{ investor_service_id }")
    assert get_response.status_code == 404


@pytest.mark.unit
def test_list_investor_service_with_pagination(client: TestClient):
    """Test listing investor_service with pagination parameters."""
    # Create multiple investor_services
    for i in range(5):
        investor_service_data = {
            "name": f"investor_service-{i}",
            "description": f"Investor Service {i}",
        }
        client.post("/api/v1/investor_service", json=investor_service_data)

    # Test pagination
    response = client.get("/api/v1/investor_service?offset=1&limit=2")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["offset"] == 1
    assert data["limit"] == 2


@pytest.mark.unit
def test_list_investor_service_with_name_filter(client: TestClient):
    """Test listing investor_service with name filtering."""
    # Create investor_services with different names
    client.post("/api/v1/investor_service", json={"name": "alpha-service"})
    client.post("/api/v1/investor_service", json={"name": "beta-service"})
    client.post("/api/v1/investor_service", json={"name": "alpha-worker"})

    # Filter by "alpha"
    response = client.get("/api/v1/investor_service?name_filter=alpha")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert all("alpha" in item["name"] for item in data["items"])
