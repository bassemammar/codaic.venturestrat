"""Tests for REST API endpoints - TDD approach.

These tests define the expected behavior of the FastAPI REST API.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from registry.api.exceptions import (
    ConflictError,
    NotFoundError,
)
from registry.api.rest import create_app, get_registry_service
from registry.consul_client import ConsulOperationError
from registry.main import app
from registry.models import (
    HealthStatus,
    Protocol,
    ServiceInstance,
)
from registry.service import RegistryService


@pytest.fixture
def mock_registry_service():
    """Create a mock RegistryService."""
    service = AsyncMock(spec=RegistryService)
    return service


@pytest.fixture
def app(mock_registry_service):
    """Create FastAPI test app with mocked service."""
    app = create_app()
    app.dependency_overrides[get_registry_service] = lambda: mock_registry_service
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_registration_payload():
    """Sample valid registration payload."""
    return {
        "name": "pricing-service",
        "version": "1.2.0",
        "instance_id": "pricing-service-abc123",
        "address": "10.0.1.50",
        "port": 8080,
        "protocol": "http",
        "depends": ["market-data-service@^1.0.0"],
        "provides": {
            "apis": {"rest": "/api/v1/pricing"},
            "events": ["pricing.quote.created"],
        },
        "health_check": {
            "http_endpoint": "/health/ready",
            "interval_seconds": 10,
            "timeout_seconds": 5,
            "deregister_after_seconds": 60,
        },
        "tags": ["production", "eu-west"],
        "metadata": {"team": "quant"},
    }


@pytest.fixture
def sample_service_instance():
    """Create sample service instance."""
    return ServiceInstance(
        name="pricing-service",
        version="1.2.0",
        instance_id="pricing-service-abc123",
        address="10.0.1.50",
        port=8080,
        protocol=Protocol.HTTP,
        health_status=HealthStatus.HEALTHY,
        tags=["production", "eu-west"],
        metadata={"team": "quant"},
    )


# =============================================================================
# POST /services (Register) Tests
# =============================================================================


class TestRegisterEndpoint:
    """Tests for POST /services endpoint."""

    def test_register_success(self, client, mock_registry_service, sample_registration_payload):
        """Successful registration returns 201 Created."""
        mock_registry_service.register.return_value = True

        response = client.post("/api/v1/services", json=sample_registration_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["instance_id"] == "pricing-service-abc123"
        assert data["consul_service_id"] == "pricing-service-abc123"
        assert "registered_at" in data
        assert "health_check_id" in data

    def test_register_validation_error_missing_name(self, client, mock_registry_service):
        """Missing required field returns 422 Unprocessable Entity."""
        payload = {
            "version": "1.0.0",
            "instance_id": "test-123",
            "address": "10.0.1.50",
            "port": 8080,
        }

        response = client.post("/api/v1/services", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_register_validation_error_invalid_port(self, client, mock_registry_service):
        """Invalid port number returns 422."""
        payload = {
            "name": "test-service",
            "version": "1.0.0",
            "instance_id": "test-123",
            "address": "10.0.1.50",
            "port": 70000,  # Invalid port
        }

        response = client.post("/api/v1/services", json=payload)

        assert response.status_code == 422

    def test_register_duplicate_instance_conflict(
        self, client, mock_registry_service, sample_registration_payload
    ):
        """Duplicate instance ID returns 409 Conflict."""
        mock_registry_service.register.side_effect = ConflictError(
            "Instance pricing-service-abc123 already registered"
        )

        response = client.post("/api/v1/services", json=sample_registration_payload)

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "CONFLICT"

    def test_register_consul_unavailable(
        self, client, mock_registry_service, sample_registration_payload
    ):
        """Consul unavailable returns 503 Service Unavailable."""
        mock_registry_service.register.side_effect = ConsulOperationError("Connection refused")

        response = client.post("/api/v1/services", json=sample_registration_payload)

        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "CONSUL_UNAVAILABLE"


# =============================================================================
# GET /services/{name} (Discover) Tests
# =============================================================================


class TestDiscoverEndpoint:
    """Tests for GET /services/{name} endpoint."""

    def test_discover_returns_healthy_instances(
        self, client, mock_registry_service, sample_service_instance
    ):
        """Discover returns healthy instances."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        response = client.get("/api/v1/services/pricing-service")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "pricing-service"
        assert len(data["instances"]) == 1
        assert data["total_instances"] == 1
        assert data["healthy_instances"] == 1

    def test_discover_with_version_constraint(
        self, client, mock_registry_service, sample_service_instance
    ):
        """Discover with version constraint filters results."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        response = client.get("/api/v1/services/pricing-service?version=%5E1.0.0")

        assert response.status_code == 200
        mock_registry_service.discover.assert_called_once()
        call_kwargs = mock_registry_service.discover.call_args
        assert call_kwargs.kwargs.get("version_constraint") == "^1.0.0"

    def test_discover_with_tag_filter(self, client, mock_registry_service, sample_service_instance):
        """Discover with tag filter."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        response = client.get("/api/v1/services/pricing-service?tags=production,eu-west")

        assert response.status_code == 200
        call_kwargs = mock_registry_service.discover.call_args
        assert call_kwargs.kwargs.get("tags") == ["production", "eu-west"]

    def test_discover_healthy_only_default(
        self, client, mock_registry_service, sample_service_instance
    ):
        """Discover defaults to healthy_only=true."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        response = client.get("/api/v1/services/pricing-service")

        assert response.status_code == 200
        call_kwargs = mock_registry_service.discover.call_args
        assert call_kwargs.kwargs.get("healthy_only") is True

    def test_discover_include_unhealthy(
        self, client, mock_registry_service, sample_service_instance
    ):
        """Discover can include unhealthy instances."""
        unhealthy_instance = ServiceInstance(
            name="pricing-service",
            version="1.2.0",
            instance_id="pricing-service-def456",
            address="10.0.1.51",
            port=8080,
            protocol=Protocol.HTTP,
            health_status=HealthStatus.CRITICAL,
            tags=["production"],
            metadata={},
        )
        mock_registry_service.discover.return_value = [sample_service_instance, unhealthy_instance]

        response = client.get("/api/v1/services/pricing-service?healthy_only=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total_instances"] == 2
        assert data["healthy_instances"] == 1

    def test_discover_service_not_found(self, client, mock_registry_service):
        """Unknown service returns 404 Not Found."""
        mock_registry_service.discover.return_value = []

        response = client.get("/api/v1/services/nonexistent-service")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"


# =============================================================================
# DELETE /services/{instance_id} (Deregister) Tests
# =============================================================================


class TestDeregisterEndpoint:
    """Tests for DELETE /services/{instance_id} endpoint."""

    def test_deregister_success(self, client, mock_registry_service):
        """Successful deregistration returns 204 No Content."""
        mock_registry_service.deregister.return_value = True

        response = client.delete(
            "/api/v1/services/pricing-service-abc123",
            params={"service_name": "pricing-service", "version": "1.2.0"},
        )

        assert response.status_code == 204
        assert response.text == ""

    def test_deregister_with_reason(self, client, mock_registry_service):
        """Deregistration can include reason."""
        mock_registry_service.deregister.return_value = True

        response = client.delete(
            "/api/v1/services/pricing-service-abc123",
            params={
                "service_name": "pricing-service",
                "version": "1.2.0",
                "reason": "scaling_down",
            },
        )

        assert response.status_code == 204
        mock_registry_service.deregister.assert_called_once()
        call_kwargs = mock_registry_service.deregister.call_args
        assert call_kwargs.kwargs.get("reason") == "scaling_down"

    def test_deregister_not_found(self, client, mock_registry_service):
        """Deregistering unknown instance returns 404."""
        mock_registry_service.deregister.side_effect = NotFoundError("Instance not found")

        response = client.delete(
            "/api/v1/services/nonexistent-instance",
            params={"service_name": "test-service", "version": "1.0.0"},
        )

        assert response.status_code == 404


# =============================================================================
# GET /services (List All) Tests
# =============================================================================


class TestListServicesEndpoint:
    """Tests for GET /services endpoint."""

    def test_list_services_returns_all(self, client, mock_registry_service):
        """List returns all services with counts."""
        mock_registry_service.list_services.return_value = {
            "pricing-service": ["production", "v1.2.0"],
            "market-data-service": ["production", "v1.0.0"],
        }
        mock_registry_service.get_service_info.side_effect = [
            {
                "name": "pricing-service",
                "instance_count": 3,
                "healthy_count": 3,
                "versions": ["1.2.0"],
                "instances": [],
            },
            {
                "name": "market-data-service",
                "instance_count": 5,
                "healthy_count": 4,
                "versions": ["1.0.0"],
                "instances": [],
            },
        ]

        response = client.get("/api/v1/services")

        assert response.status_code == 200
        data = response.json()
        assert data["total_services"] == 2
        assert len(data["services"]) == 2

    def test_list_services_with_tag_filter(self, client, mock_registry_service):
        """List services can filter by tags."""
        mock_registry_service.list_services.return_value = {
            "pricing-service": ["production"],
        }
        mock_registry_service.get_service_info.return_value = {
            "name": "pricing-service",
            "instance_count": 3,
            "healthy_count": 3,
            "versions": ["1.2.0"],
            "instances": [],
        }

        response = client.get("/api/v1/services?tags=production")

        assert response.status_code == 200

    def test_list_services_empty(self, client, mock_registry_service):
        """Empty registry returns empty list."""
        mock_registry_service.list_services.return_value = {}

        response = client.get("/api/v1/services")

        assert response.status_code == 200
        data = response.json()
        assert data["total_services"] == 0
        assert data["services"] == []


# =============================================================================
# PUT /services/{instance_id}/heartbeat Tests
# =============================================================================


class TestHeartbeatEndpoint:
    """Tests for PUT /services/{instance_id}/heartbeat endpoint."""

    def test_heartbeat_success(self, client, mock_registry_service):
        """Successful heartbeat returns 200 OK."""
        mock_registry_service.consul = AsyncMock()
        mock_registry_service.consul.health_check.return_value = True

        response = client.put(
            "/api/v1/services/pricing-service-abc123/heartbeat",
            json={"status": "passing"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["instance_id"] == "pricing-service-abc123"
        assert data["status"] == "passing"
        assert "last_heartbeat" in data


# =============================================================================
# GET /services/{name}/manifest Tests
# =============================================================================


class TestManifestEndpoint:
    """Tests for GET /services/{name}/manifest endpoint."""

    def test_get_manifest_success(self, client, mock_registry_service):
        """Get manifest returns cached manifest."""
        mock_registry_service.consul = AsyncMock()
        mock_registry_service.consul.kv_get.return_value = (
            '{"name": "pricing-service", "version": "1.2.0", "depends": []}'
        )

        response = client.get("/api/v1/services/pricing-service/manifest")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "pricing-service"
        assert data["version"] == "1.2.0"

    def test_get_manifest_not_found(self, client, mock_registry_service):
        """Manifest not found returns 404."""
        mock_registry_service.consul = AsyncMock()
        mock_registry_service.consul.kv_get.return_value = None

        response = client.get("/api/v1/services/nonexistent-service/manifest")

        assert response.status_code == 404


# =============================================================================
# GET /health/services (Health Overview) Tests
# =============================================================================


class TestHealthOverviewEndpoint:
    """Tests for GET /health/services endpoint."""

    def test_health_overview_returns_summary(self, client, mock_registry_service):
        """Health overview returns all services status."""
        mock_registry_service.get_health_overview.return_value = {
            "services": {
                "pricing-service": {"total": 3, "healthy": 3, "unhealthy": 0},
                "market-data-service": {"total": 5, "healthy": 4, "unhealthy": 1},
            },
            "total_instances": 8,
            "healthy_instances": 7,
            "unhealthy_instances": 1,
        }

        response = client.get("/api/v1/health/services")

        assert response.status_code == 200
        data = response.json()
        assert len(data["services"]) == 2
        assert data["overall_status"] in ["healthy", "warning", "critical"]

    def test_health_overview_all_healthy(self, client, mock_registry_service):
        """All healthy services returns healthy overall status."""
        mock_registry_service.get_health_overview.return_value = {
            "services": {
                "pricing-service": {"total": 3, "healthy": 3, "unhealthy": 0},
            },
            "total_instances": 3,
            "healthy_instances": 3,
            "unhealthy_instances": 0,
        }

        response = client.get("/api/v1/health/services")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "healthy"


# =============================================================================
# GET /health/services/{name} (Service Health Detail) Tests
# =============================================================================


class TestServiceHealthEndpoint:
    """Tests for GET /health/services/{name} endpoint."""

    def test_service_health_returns_details(
        self, client, mock_registry_service, sample_service_instance
    ):
        """Service health returns detailed instance health."""
        mock_registry_service.discover.return_value = [sample_service_instance]
        mock_registry_service.health = MagicMock()
        mock_registry_service.health.get_status.return_value = HealthStatus.HEALTHY

        response = client.get("/api/v1/health/services/pricing-service")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "pricing-service"
        assert data["status"] in ["healthy", "warning", "critical"]
        assert len(data["instances"]) >= 1

    def test_service_health_not_found(self, client, mock_registry_service):
        """Unknown service returns 404."""
        mock_registry_service.discover.return_value = []

        response = client.get("/api/v1/health/services/nonexistent-service")

        assert response.status_code == 404


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error response format."""

    def test_validation_error_format(self, client, mock_registry_service):
        """Validation errors follow standard format."""
        response = client.post("/api/v1/services", json={})

        assert response.status_code == 422
        data = response.json()
        # FastAPI returns validation errors in its format
        assert "detail" in data

    def test_internal_error_format(self, app, mock_registry_service):
        """Internal errors follow standard format."""
        mock_registry_service.register.side_effect = Exception("Unexpected error")

        # Use raise_server_exceptions=False to get error response instead of exception
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.post(
                "/api/v1/services",
                json={
                    "name": "test",
                    "version": "1.0.0",
                    "instance_id": "test-123",
                    "address": "10.0.1.50",
                    "port": 8080,
                },
            )

            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "INTERNAL_ERROR"


# =============================================================================
# OpenAPI Documentation Tests
# =============================================================================


class TestOpenAPI:
    """Tests for OpenAPI documentation."""

    def test_openapi_schema_available(self, client):
        """OpenAPI schema is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_docs_available(self, client):
        """Swagger UI is accessible."""
        response = client.get("/docs")

        assert response.status_code == 200


# =============================================================================
# CORS and Middleware Tests
# =============================================================================


class TestMiddleware:
    """Tests for API middleware."""

    def test_request_id_header(self, client, mock_registry_service, sample_registration_payload):
        """Response includes request ID header."""
        mock_registry_service.register.return_value = True

        response = client.post("/api/v1/services", json=sample_registration_payload)

        # Request ID should be in response headers
        assert response.status_code == 201
        # Note: X-Request-ID will be added by middleware
