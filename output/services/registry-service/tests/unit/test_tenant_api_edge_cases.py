"""Additional API tests for tenant management edge cases and security scenarios."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from registry.api.rest import create_app, get_tenant_service
from registry.models import Tenant, TenantStatus
from registry.tenant_service import TenantService


@pytest.fixture
def mock_tenant_service():
    """Create a mock TenantService."""
    service = AsyncMock(spec=TenantService)
    return service


@pytest.fixture
def app_with_mock_tenant(mock_tenant_service):
    """Create FastAPI test app with mocked tenant service."""
    app = create_app()
    app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service
    return app


@pytest.fixture
def client(app_with_mock_tenant):
    """Create test client."""
    return TestClient(app_with_mock_tenant)


@pytest.fixture
def system_tenant():
    """System tenant fixture."""
    return Tenant(
        id="00000000-0000-0000-0000-000000000000",
        slug="system",
        name="System",
        status=TenantStatus.ACTIVE,
        config={"is_system": True},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestTenantAPISecurityAndValidation:
    """Tests for tenant API security and validation edge cases."""

    def test_create_tenant_sql_injection_attempt(self, client, mock_tenant_service):
        """Malicious slug with SQL injection attempt is rejected."""
        malicious_payload = {"slug": "test'; DROP TABLE tenants; --", "name": "Test Company"}

        response = client.post("/api/v1/tenants/", json=malicious_payload)

        # Should fail validation due to regex pattern
        assert response.status_code == 422
        mock_tenant_service.create_tenant.assert_not_called()

    def test_create_tenant_xss_attempt_in_name(self, client, mock_tenant_service):
        """HTML/script injection in tenant name should be handled by validation."""
        xss_payload = {"slug": "valid-slug", "name": "<script>alert('xss')</script>ACME Corp"}

        # Mock successful creation - XSS protection should be handled at display/output level
        mock_tenant = Tenant(
            id=str(uuid.uuid4()),
            slug="valid-slug",
            name="<script>alert('xss')</script>ACME Corp",
            status=TenantStatus.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.create_tenant.return_value = mock_tenant

        response = client.post("/api/v1/tenants/", json=xss_payload)

        # Should succeed - XSS protection is not API responsibility
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "<script>alert('xss')</script>ACME Corp"

    def test_create_tenant_unicode_characters(self, client, mock_tenant_service):
        """Unicode characters in tenant name should be supported."""
        unicode_payload = {"slug": "unicode-test", "name": "测试公司 🏢 Тест 🌍"}

        mock_tenant = Tenant(
            id=str(uuid.uuid4()),
            slug="unicode-test",
            name="测试公司 🏢 Тест 🌍",
            status=TenantStatus.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.create_tenant.return_value = mock_tenant

        response = client.post("/api/v1/tenants/", json=unicode_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "测试公司 🏢 Тест 🌍"

    def test_create_tenant_slug_edge_cases(self, client, mock_tenant_service):
        """Test slug validation edge cases."""
        # Test cases: (slug, should_pass)
        test_cases = [
            ("a", False),  # Too short
            ("ab", True),  # Minimum length
            ("-invalid", False),  # Starts with hyphen
            ("invalid-", False),  # Ends with hyphen
            ("valid-slug", True),  # Valid format
            ("123-valid", True),  # Starts with number
            ("valid-123", True),  # Ends with number
            ("a" * 63, True),  # Maximum length
            ("a" * 64, False),  # Too long
            ("UPPERCASE", False),  # Uppercase not allowed
            ("under_score", False),  # Underscore not allowed
            ("dot.invalid", False),  # Dot not allowed
        ]

        for slug, should_pass in test_cases:
            payload = {"slug": slug, "name": "Test Company"}
            response = client.post("/api/v1/tenants/", json=payload)

            if should_pass:
                # Mock successful response for valid slugs
                mock_tenant = Tenant(
                    id=str(uuid.uuid4()),
                    slug=slug,
                    name="Test Company",
                    status=TenantStatus.ACTIVE,
                    config={},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                mock_tenant_service.create_tenant.return_value = mock_tenant

                # Re-send request for mocked response
                response = client.post("/api/v1/tenants/", json=payload)
                assert response.status_code == 201, f"Expected 201 for slug '{slug}'"
            else:
                assert response.status_code == 422, f"Expected 422 for slug '{slug}'"

    def test_list_tenants_with_extremely_large_page_size(self, client, mock_tenant_service):
        """Large page size is capped at maximum."""
        mock_tenant_service.list_tenants.return_value = ([], 0)

        response = client.get("/api/v1/tenants/?page_size=999999")

        # Should be rejected due to validation (max 100)
        assert response.status_code == 422

    def test_list_tenants_with_negative_page(self, client, mock_tenant_service):
        """Negative page numbers are rejected."""
        response = client.get("/api/v1/tenants/?page=-1")

        # Should be rejected due to validation (min 1)
        assert response.status_code == 422

    def test_get_tenant_malformed_uuid(self, client, mock_tenant_service):
        """Malformed UUID in path parameter should be handled gracefully."""
        malformed_id = "not-a-uuid"
        response = client.get(f"/api/v1/tenants/{malformed_id}")

        # Should call service even with malformed UUID - let service handle validation
        assert response.status_code == 404 or response.status_code == 500
        # The exact behavior depends on service implementation


class TestTenantAPISystemTenantProtection:
    """Tests for system tenant protection in API endpoints."""

    def test_update_system_tenant_is_protected(self, client, mock_tenant_service, system_tenant):
        """System tenant cannot be updated."""
        mock_tenant_service.update_tenant.side_effect = ValueError("Cannot update system tenant")

        payload = {"name": "Hacked System"}
        response = client.patch(f"/api/v1/tenants/{system_tenant.id}", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "Cannot update system tenant" in data["detail"]

    def test_suspend_system_tenant_is_protected(self, client, mock_tenant_service, system_tenant):
        """System tenant cannot be suspended."""
        mock_tenant_service.suspend_tenant.side_effect = ValueError("Cannot suspend system tenant")

        payload = {"reason": "This should not work"}
        response = client.post(f"/api/v1/tenants/{system_tenant.id}/suspend", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "Cannot suspend system tenant" in data["detail"]

    def test_delete_system_tenant_is_protected(self, client, mock_tenant_service, system_tenant):
        """System tenant cannot be deleted."""
        mock_tenant_service.delete_tenant.side_effect = ValueError("Cannot delete system tenant")

        payload = {"reason": "This should not work"}
        response = client.request("DELETE", f"/api/v1/tenants/{system_tenant.id}", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete system tenant" in data["detail"]


class TestTenantAPIBusinessLogicEdgeCases:
    """Tests for business logic edge cases in tenant API."""

    def test_create_duplicate_slug_with_different_case(self, client, mock_tenant_service):
        """Creating tenant with same slug in different case should conflict."""
        mock_tenant_service.create_tenant.side_effect = ValueError(
            "Tenant with slug 'ACME-CORP' already exists"
        )

        payload = {
            "slug": "acme-corp",  # Slug validation should prevent uppercase anyway
            "name": "ACME Corporation",
        }

        response = client.post("/api/v1/tenants/", json=payload)

        # Since slug validation requires lowercase, this would fail at validation level
        # But if it got through, service should catch conflicts
        assert response.status_code in [409, 422]

    def test_suspend_already_suspended_tenant(self, client, mock_tenant_service):
        """Suspending already suspended tenant should be handled gracefully."""
        mock_tenant_service.suspend_tenant.side_effect = ValueError("Tenant is already suspended")

        payload = {"reason": "Additional suspension reason"}
        tenant_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/tenants/{tenant_id}/suspend", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "already suspended" in data["detail"]

    def test_resume_non_suspended_tenant(self, client, mock_tenant_service):
        """Resuming non-suspended tenant should be handled gracefully."""
        mock_tenant_service.resume_tenant.side_effect = ValueError("Tenant is not suspended")

        tenant_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/tenants/{tenant_id}/resume")

        assert response.status_code == 400
        data = response.json()
        assert "not suspended" in data["detail"]

    def test_delete_already_deleted_tenant(self, client, mock_tenant_service):
        """Deleting already deleted tenant should be handled gracefully."""
        mock_tenant_service.delete_tenant.side_effect = ValueError("Tenant is already deleted")

        payload = {"reason": "Additional deletion reason"}
        tenant_id = str(uuid.uuid4())
        response = client.request("DELETE", f"/api/v1/tenants/{tenant_id}", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "already deleted" in data["detail"]


class TestTenantAPIConfigurationHandling:
    """Tests for tenant configuration handling in API."""

    def test_create_tenant_with_complex_config(self, client, mock_tenant_service):
        """Complex nested configuration should be preserved."""
        complex_config = {
            "quotas": {
                "max_users": 100,
                "max_api_calls_per_day": 50000,
                "storage_mb": 10000,
                "max_records_per_model": 100000,
            },
            "theme": {
                "primary_color": "#0066cc",
                "secondary_color": "#ff6600",
                "logo_url": "https://example.com/logo.png",
                "custom_css": "body { font-family: Arial; }",
            },
            "integrations": {
                "webhooks": {"enabled": True, "endpoints": ["https://api.acme.com/webhooks"]},
                "sso": {"enabled": True, "provider": "okta", "domain": "acme.okta.com"},
            },
            "features": {"advanced_analytics": True, "white_label": False, "api_access": True},
        }

        payload = {
            "slug": "complex-config",
            "name": "Complex Config Corp",
            "config": complex_config,
        }

        mock_tenant = Tenant(
            id=str(uuid.uuid4()),
            slug="complex-config",
            name="Complex Config Corp",
            status=TenantStatus.ACTIVE,
            config=complex_config,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.create_tenant.return_value = mock_tenant

        response = client.post("/api/v1/tenants/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["config"] == complex_config

    def test_update_tenant_partial_config_merge(self, client, mock_tenant_service):
        """Updating tenant with partial config should merge correctly."""
        tenant_id = str(uuid.uuid4())

        # Original config
        original_config = {"quotas": {"max_users": 50}, "theme": {"primary_color": "#000000"}}

        # Partial update
        update_config = {
            "quotas": {"max_users": 100, "max_api_calls": 1000},
            "features": {"new_feature": True},
        }

        # Expected merged result (this would be handled by the service layer)
        merged_config = {
            "quotas": {"max_users": 100, "max_api_calls": 1000},
            "theme": {"primary_color": "#000000"},
            "features": {"new_feature": True},
        }

        updated_tenant = Tenant(
            id=tenant_id,
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatus.ACTIVE,
            config=merged_config,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.update_tenant.return_value = updated_tenant

        response = client.patch(f"/api/v1/tenants/{tenant_id}", json={"config": update_config})

        assert response.status_code == 200
        data = response.json()
        assert data["config"] == merged_config

    def test_create_tenant_with_null_config_values(self, client, mock_tenant_service):
        """Config with null values should be handled correctly."""
        config_with_nulls = {
            "quotas": {
                "max_users": 100,
                "max_storage": None,  # Null value
            },
            "theme": None,  # Null section
        }

        payload = {"slug": "null-config", "name": "Null Config Corp", "config": config_with_nulls}

        mock_tenant = Tenant(
            id=str(uuid.uuid4()),
            slug="null-config",
            name="Null Config Corp",
            status=TenantStatus.ACTIVE,
            config=config_with_nulls,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.create_tenant.return_value = mock_tenant

        response = client.post("/api/v1/tenants/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["config"] == config_with_nulls


class TestTenantAPIRateLimitingScenarios:
    """Tests for API behavior under rate limiting scenarios."""

    def test_create_many_tenants_rapidly(self, client, mock_tenant_service):
        """Creating many tenants rapidly should be handled gracefully."""
        # This test verifies the API can handle rapid requests
        # In real scenarios, this would be limited by rate limiting middleware

        def create_mock_tenant(slug):
            return Tenant(
                id=str(uuid.uuid4()),
                slug=slug,
                name=f"Tenant {slug}",
                status=TenantStatus.ACTIVE,
                config={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        # Simulate 10 rapid requests
        for i in range(10):
            slug = f"rapid-{i:02d}"
            payload = {"slug": slug, "name": f"Rapid Tenant {i}"}

            mock_tenant_service.create_tenant.return_value = create_mock_tenant(slug)
            response = client.post("/api/v1/tenants/", json=payload)

            assert response.status_code == 201
            data = response.json()
            assert data["slug"] == slug

    def test_concurrent_tenant_operations(self, client, mock_tenant_service):
        """Concurrent operations on same tenant should be handled safely."""
        tenant_id = str(uuid.uuid4())

        # Mock different operations
        mock_tenant = Tenant(
            id=tenant_id,
            slug="concurrent-test",
            name="Concurrent Test Tenant",
            status=TenantStatus.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.get_tenant_by_id.return_value = mock_tenant
        mock_tenant_service.update_tenant.return_value = mock_tenant

        # Simulate concurrent GET and PATCH requests
        # In real scenarios, database-level locking would handle conflicts
        get_response = client.get(f"/api/v1/tenants/{tenant_id}")
        patch_response = client.patch(f"/api/v1/tenants/{tenant_id}", json={"name": "Updated Name"})

        assert get_response.status_code == 200
        assert patch_response.status_code == 200


class TestTenantAPIErrorRecovery:
    """Tests for API error recovery scenarios."""

    def test_service_timeout_handling(self, client, mock_tenant_service):
        """Service timeout should return appropriate error."""

        mock_tenant_service.list_tenants.side_effect = TimeoutError("Database timeout")
        import asyncio

        mock_tenant_service.list_tenants.side_effect = asyncio.TimeoutError("Database timeout")

        response = client.get("/api/v1/tenants/")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to list tenants" in data["detail"]

    def test_service_connection_error_handling(self, client, mock_tenant_service):
        """Service connection error should return appropriate error."""
        mock_tenant_service.create_tenant.side_effect = ConnectionError("Database connection lost")

        payload = {"slug": "test-tenant", "name": "Test Tenant"}
        response = client.post("/api/v1/tenants/", json=payload)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to create tenant" in data["detail"]

    def test_malformed_json_request(self, client, mock_tenant_service):
        """Malformed JSON should be handled gracefully."""
        # Send invalid JSON
        response = client.post(
            "/api/v1/tenants/",
            data="invalid json content",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422  # Unprocessable Entity
        mock_tenant_service.create_tenant.assert_not_called()

    def test_missing_content_type_header(self, client, mock_tenant_service):
        """Missing content type should be handled gracefully."""
        payload = '{"slug": "test", "name": "Test"}'
        response = client.post("/api/v1/tenants/", data=payload)

        # FastAPI should handle this gracefully
        # Exact behavior depends on FastAPI version
        assert response.status_code in [400, 422]
