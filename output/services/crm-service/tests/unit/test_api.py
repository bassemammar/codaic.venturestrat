"""Unit tests for Crm Service API."""

import pytest
from uuid import UUID
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_list_crm_service_empty(client: TestClient):
    """Test listing crm_service when store is empty."""
    response = client.get("/api/v1/crm_service")
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["offset"] == 0
    assert data["limit"] == 100


@pytest.mark.unit
def test_create_crm_service(client: TestClient, sample_crm_service_data):
    """Test creating a new crm_service."""
    response = client.post("/api/v1/crm_service", json=sample_crm_service_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == sample_crm_service_data["name"]
    assert data["description"] == sample_crm_service_data["description"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.unit
def test_create_crm_service_duplicate_name(client: TestClient, sample_crm_service_data):
    """Test creating crm_service with duplicate name fails."""
    # Create first crm_service
    response1 = client.post("/api/v1/crm_service", json=sample_crm_service_data)
    assert response1.status_code == 201

    # Try to create second with same name
    response2 = client.post("/api/v1/crm_service", json=sample_crm_service_data)
    assert response2.status_code == 400


@pytest.mark.unit
def test_get_crm_service(client: TestClient, sample_crm_service_data):
    """Test getting a crm_service by ID."""
    # Create crm_service
    create_response = client.post("/api/v1/crm_service", json=sample_crm_service_data)
    crm_service_data = create_response.json()
    crm_service_id = crm_service_data["id"]

    # Get crm_service
    response = client.get(f"/api/v1/crm_service/{ crm_service_id }")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == crm_service_id
    assert data["name"] == sample_crm_service_data["name"]


@pytest.mark.unit
def test_get_crm_service_not_found(client: TestClient):
    """Test getting non-existent crm_service returns 404."""
    fake_id = "12345678-1234-5678-9abc-123456789012"
    response = client.get(f"/api/v1/crm_service/{fake_id}")
    assert response.status_code == 404


@pytest.mark.unit
def test_update_crm_service(client: TestClient, sample_crm_service_data):
    """Test updating a crm_service."""
    # Create crm_service
    create_response = client.post("/api/v1/crm_service", json=sample_crm_service_data)
    crm_service_data = create_response.json()
    crm_service_id = crm_service_data["id"]

    # Update crm_service
    update_data = {"description": "Updated description"}
    response = client.put(f"/api/v1/crm_service/{ crm_service_id }", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["description"] == "Updated description"
    assert data["updated_at"] is not None


@pytest.mark.unit
def test_delete_crm_service(client: TestClient, sample_crm_service_data):
    """Test deleting a crm_service."""
    # Create crm_service
    create_response = client.post("/api/v1/crm_service", json=sample_crm_service_data)
    crm_service_data = create_response.json()
    crm_service_id = crm_service_data["id"]

    # Delete crm_service
    response = client.delete(f"/api/v1/crm_service/{ crm_service_id }")
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(f"/api/v1/crm_service/{ crm_service_id }")
    assert get_response.status_code == 404


@pytest.mark.unit
def test_list_crm_service_with_pagination(client: TestClient):
    """Test listing crm_service with pagination parameters."""
    # Create multiple crm_services
    for i in range(5):
        crm_service_data = {
            "name": f"crm_service-{i}",
            "description": f"Crm Service {i}",
        }
        client.post("/api/v1/crm_service", json=crm_service_data)

    # Test pagination
    response = client.get("/api/v1/crm_service?offset=1&limit=2")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["offset"] == 1
    assert data["limit"] == 2


@pytest.mark.unit
def test_list_crm_service_with_name_filter(client: TestClient):
    """Test listing crm_service with name filtering."""
    # Create crm_services with different names
    client.post("/api/v1/crm_service", json={"name": "alpha-service"})
    client.post("/api/v1/crm_service", json={"name": "beta-service"})
    client.post("/api/v1/crm_service", json={"name": "alpha-worker"})

    # Filter by "alpha"
    response = client.get("/api/v1/crm_service?name_filter=alpha")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert all("alpha" in item["name"] for item in data["items"])
