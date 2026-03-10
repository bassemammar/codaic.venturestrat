"""Tests for tenant CRUD API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta
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
def sample_create_tenant_payload():
    """Sample valid create tenant payload."""
    return {
        "slug": "acme-corp",
        "name": "ACME Corporation",
        "config": {"quotas": {"max_users": 100}},
        "admin_email": "admin@acme.com",
    }


@pytest.fixture
def sample_tenant():
    """Sample tenant object."""
    tenant_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    return Tenant(
        id=tenant_id,
        slug="acme-corp",
        name="ACME Corporation",
        status=TenantStatus.ACTIVE,
        config={"quotas": {"max_users": 100}},
        keycloak_org_id="org-acme-corp",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_update_tenant_payload():
    """Sample valid update tenant payload."""
    return {"name": "ACME Corporation International", "config": {"quotas": {"max_users": 200}}}


class TestCreateTenantEndpoint:
    """Tests for POST /tenants endpoint."""

    def test_create_tenant_success(
        self, client, mock_tenant_service, sample_create_tenant_payload, sample_tenant
    ):
        """Successful tenant creation returns 201 Created."""
        mock_tenant_service.create_tenant.return_value = sample_tenant

        response = client.post("/api/v1/tenants/", json=sample_create_tenant_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "acme-corp"
        assert data["name"] == "ACME Corporation"
        assert data["status"] == "active"
        assert data["id"] == sample_tenant.id
        assert data["keycloak_org_id"] == "org-acme-corp"
        assert "created_at" in data
        assert "updated_at" in data

        # Verify service was called with correct parameters
        mock_tenant_service.create_tenant.assert_called_once_with(
            slug="acme-corp",
            name="ACME Corporation",
            config={"quotas": {"max_users": 100}},
            admin_email="admin@acme.com",
        )

    def test_create_tenant_minimal_payload(self, client, mock_tenant_service, sample_tenant):
        """Create tenant with minimal payload returns 201 Created."""
        minimal_payload = {"slug": "minimal-corp", "name": "Minimal Corp"}

        minimal_tenant = Tenant(
            id=str(uuid.uuid4()),
            slug="minimal-corp",
            name="Minimal Corp",
            status=TenantStatus.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.create_tenant.return_value = minimal_tenant

        response = client.post("/api/v1/tenants/", json=minimal_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "minimal-corp"
        assert data["config"] == {}
        assert data["keycloak_org_id"] is None

        # Verify service was called with correct parameters
        mock_tenant_service.create_tenant.assert_called_once_with(
            slug="minimal-corp", name="Minimal Corp", config={}, admin_email=None
        )

    def test_create_tenant_validation_error_invalid_slug(self, client, mock_tenant_service):
        """Invalid slug format returns 422 Unprocessable Entity."""
        invalid_payload = {
            "slug": "invalid slug!",  # Invalid format - contains space and special char
            "name": "Test Company",
        }

        response = client.post("/api/v1/tenants/", json=invalid_payload)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Should not call service if validation fails
        mock_tenant_service.create_tenant.assert_not_called()

    def test_create_tenant_validation_error_empty_name(self, client, mock_tenant_service):
        """Empty name returns 422 Unprocessable Entity."""
        invalid_payload = {
            "slug": "valid-slug",
            "name": "",  # Empty name
        }

        response = client.post("/api/v1/tenants/", json=invalid_payload)

        assert response.status_code == 422
        mock_tenant_service.create_tenant.assert_not_called()

    def test_create_tenant_validation_error_slug_too_short(self, client, mock_tenant_service):
        """Slug too short returns 422 Unprocessable Entity."""
        invalid_payload = {
            "slug": "a",  # Too short (min_length=2)
            "name": "Test Company",
        }

        response = client.post("/api/v1/tenants/", json=invalid_payload)

        assert response.status_code == 422
        mock_tenant_service.create_tenant.assert_not_called()

    def test_create_tenant_conflict(
        self, client, mock_tenant_service, sample_create_tenant_payload
    ):
        """Duplicate slug returns 409 Conflict."""
        mock_tenant_service.create_tenant.side_effect = ValueError(
            "Tenant with slug 'acme-corp' already exists"
        )

        response = client.post("/api/v1/tenants/", json=sample_create_tenant_payload)

        assert response.status_code == 409
        data = response.json()
        assert "error" in data
        assert "already exists" in data["error"]["message"]

    def test_create_tenant_service_error(
        self, client, mock_tenant_service, sample_create_tenant_payload
    ):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.create_tenant.side_effect = Exception("Database connection failed")

        response = client.post("/api/v1/tenants/", json=sample_create_tenant_payload)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to create tenant" in data["detail"]


class TestListTenantsEndpoint:
    """Tests for GET /tenants endpoint."""

    def test_list_tenants_success(self, client, mock_tenant_service, sample_tenant):
        """List tenants returns paginated results."""
        mock_tenant_service.list_tenants.return_value = (
            [sample_tenant],
            1,  # total count
        )

        response = client.get("/api/v1/tenants/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 50

        # Check tenant structure
        tenant_data = data["items"][0]
        assert tenant_data["id"] == sample_tenant.id
        assert tenant_data["slug"] == "acme-corp"
        assert tenant_data["name"] == "ACME Corporation"

        # Verify service was called with default parameters
        mock_tenant_service.list_tenants.assert_called_once_with(
            status=None, search=None, page=1, page_size=50
        )

    def test_list_tenants_empty_result(self, client, mock_tenant_service):
        """List tenants with no results returns empty list."""
        mock_tenant_service.list_tenants.return_value = ([], 0)

        response = client.get("/api/v1/tenants/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_tenants_with_status_filter(self, client, mock_tenant_service, sample_tenant):
        """List tenants with status filter."""
        mock_tenant_service.list_tenants.return_value = ([sample_tenant], 1)

        response = client.get("/api/v1/tenants/?status=active")

        assert response.status_code == 200
        mock_tenant_service.list_tenants.assert_called_once()
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["status"] == "active"

    def test_list_tenants_with_search_filter(self, client, mock_tenant_service, sample_tenant):
        """List tenants with search filter."""
        mock_tenant_service.list_tenants.return_value = ([sample_tenant], 1)

        response = client.get("/api/v1/tenants/?search=acme")

        assert response.status_code == 200
        mock_tenant_service.list_tenants.assert_called_once()
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["search"] == "acme"

    def test_list_tenants_with_pagination(self, client, mock_tenant_service, sample_tenant):
        """List tenants with pagination parameters."""
        mock_tenant_service.list_tenants.return_value = ([sample_tenant], 1)

        response = client.get("/api/v1/tenants/?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

        mock_tenant_service.list_tenants.assert_called_once()
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 10

    def test_list_tenants_with_all_filters(self, client, mock_tenant_service, sample_tenant):
        """List tenants with all filters combined."""
        mock_tenant_service.list_tenants.return_value = ([sample_tenant], 1)

        response = client.get("/api/v1/tenants/?status=active&search=acme&page=1&page_size=25")

        assert response.status_code == 200
        mock_tenant_service.list_tenants.assert_called_once()
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["status"] == "active"
        assert call_kwargs["search"] == "acme"
        assert call_kwargs["page"] == 1
        assert call_kwargs["page_size"] == 25

    def test_list_tenants_invalid_pagination(self, client, mock_tenant_service):
        """Invalid pagination parameters return 422."""
        # Test invalid page (< 1)
        response = client.get("/api/v1/tenants/?page=0")
        assert response.status_code == 422

        # Test invalid page_size (> 100)
        response = client.get("/api/v1/tenants/?page_size=101")
        assert response.status_code == 422

    def test_list_tenants_service_error(self, client, mock_tenant_service):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.list_tenants.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/tenants/")

        assert response.status_code == 500


class TestGetTenantEndpoint:
    """Tests for GET /tenants/{tenant_id} endpoint."""

    def test_get_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Get tenant returns tenant data."""
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        response = client.get(f"/api/v1/tenants/{sample_tenant.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tenant.id
        assert data["slug"] == "acme-corp"
        assert data["name"] == "ACME Corporation"
        assert data["status"] == "active"
        assert data["config"] == {"quotas": {"max_users": 100}}
        assert data["keycloak_org_id"] == "org-acme-corp"
        assert "created_at" in data
        assert "updated_at" in data

        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)

    def test_get_tenant_not_found(self, client, mock_tenant_service):
        """Unknown tenant returns 404 Not Found."""
        tenant_id = str(uuid.uuid4())
        mock_tenant_service.get_tenant_by_id.return_value = None

        response = client.get(f"/api/v1/tenants/{tenant_id}")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

        mock_tenant_service.get_tenant_by_id.assert_called_once_with(tenant_id)

    def test_get_tenant_service_error(self, client, mock_tenant_service, sample_tenant):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.get_tenant_by_id.side_effect = Exception("Database connection failed")

        response = client.get(f"/api/v1/tenants/{sample_tenant.id}")

        assert response.status_code == 500


class TestUpdateTenantEndpoint:
    """Tests for PATCH /tenants/{tenant_id} endpoint."""

    def test_update_tenant_success(
        self, client, mock_tenant_service, sample_tenant, sample_update_tenant_payload
    ):
        """Update tenant returns updated data."""
        # Create updated tenant with changes
        updated_tenant = Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name="ACME Corporation International",  # Updated name
            status=sample_tenant.status,
            config={"quotas": {"max_users": 200}},  # Updated config
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),  # Updated timestamp
        )
        mock_tenant_service.update_tenant.return_value = updated_tenant

        response = client.patch(
            f"/api/v1/tenants/{sample_tenant.id}", json=sample_update_tenant_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tenant.id
        assert data["name"] == "ACME Corporation International"
        assert data["config"]["quotas"]["max_users"] == 200

        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id,
            name="ACME Corporation International",
            config={"quotas": {"max_users": 200}},
        )

    def test_update_tenant_name_only(self, client, mock_tenant_service, sample_tenant):
        """Update tenant name only."""
        updated_tenant = Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name="Updated Name",
            status=sample_tenant.status,
            config=sample_tenant.config,
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.update_tenant.return_value = updated_tenant

        payload = {"name": "Updated Name"}
        response = client.patch(f"/api/v1/tenants/{sample_tenant.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, name="Updated Name", config=None
        )

    def test_update_tenant_config_only(self, client, mock_tenant_service, sample_tenant):
        """Update tenant config only."""
        updated_tenant = Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name=sample_tenant.name,
            status=sample_tenant.status,
            config={"new": "config"},
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.update_tenant.return_value = updated_tenant

        payload = {"config": {"new": "config"}}
        response = client.patch(f"/api/v1/tenants/{sample_tenant.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["config"] == {"new": "config"}

        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, name=None, config={"new": "config"}
        )

    def test_update_tenant_not_found(self, client, mock_tenant_service):
        """Update non-existent tenant returns 404 Not Found."""
        tenant_id = str(uuid.uuid4())
        mock_tenant_service.update_tenant.return_value = None

        payload = {"name": "New Name"}
        response = client.patch(f"/api/v1/tenants/{tenant_id}", json=payload)

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_update_tenant_validation_error(self, client, mock_tenant_service, sample_tenant):
        """Invalid update payload returns 422 Unprocessable Entity."""
        # Empty name should fail validation
        invalid_payload = {"name": ""}

        response = client.patch(f"/api/v1/tenants/{sample_tenant.id}", json=invalid_payload)

        assert response.status_code == 422
        mock_tenant_service.update_tenant.assert_not_called()

    def test_update_tenant_system_tenant_error(self, client, mock_tenant_service, sample_tenant):
        """Trying to update system tenant returns 400 Bad Request."""
        mock_tenant_service.update_tenant.side_effect = ValueError("Cannot update system tenant")

        payload = {"name": "New Name"}
        response = client.patch(f"/api/v1/tenants/{sample_tenant.id}", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "Cannot update system tenant" in data["detail"]

    def test_update_tenant_empty_payload(self, client, mock_tenant_service, sample_tenant):
        """Update with empty payload still calls service."""
        mock_tenant_service.update_tenant.return_value = sample_tenant

        response = client.patch(f"/api/v1/tenants/{sample_tenant.id}", json={})

        assert response.status_code == 200
        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, name=None, config=None
        )

    def test_update_tenant_service_error(self, client, mock_tenant_service, sample_tenant):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.update_tenant.side_effect = Exception("Database connection failed")

        payload = {"name": "New Name"}
        response = client.patch(f"/api/v1/tenants/{sample_tenant.id}", json=payload)

        assert response.status_code == 500


class TestSuspendTenantEndpoint:
    """Tests for POST /tenants/{tenant_id}/suspend endpoint."""

    @pytest.fixture
    def sample_suspend_payload(self):
        """Sample valid suspend tenant payload."""
        return {"reason": "Payment overdue for 30 days - invoice #12345"}

    @pytest.fixture
    def suspended_tenant(self, sample_tenant):
        """Sample suspended tenant."""
        return Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name=sample_tenant.name,
            status=TenantStatus.SUSPENDED,
            config={
                **sample_tenant.config,
                "suspension_reason": "Payment overdue for 30 days - invoice #12345",
                "suspended_at": datetime.now(UTC).isoformat(),
            },
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
        )

    def test_suspend_tenant_success(
        self, client, mock_tenant_service, sample_tenant, suspended_tenant, sample_suspend_payload
    ):
        """Successful tenant suspension returns 200 OK."""
        mock_tenant_service.suspend_tenant.return_value = suspended_tenant

        response = client.post(
            f"/api/v1/tenants/{sample_tenant.id}/suspend", json=sample_suspend_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tenant.id
        assert data["status"] == "suspended"
        assert "suspension_reason" in data["config"]
        assert data["config"]["suspension_reason"] == "Payment overdue for 30 days - invoice #12345"
        assert "suspended_at" in data["config"]

        mock_tenant_service.suspend_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, reason="Payment overdue for 30 days - invoice #12345"
        )

    def test_suspend_tenant_not_found(self, client, mock_tenant_service, sample_suspend_payload):
        """Suspend non-existent tenant returns 404 Not Found."""
        tenant_id = str(uuid.uuid4())
        mock_tenant_service.suspend_tenant.return_value = None

        response = client.post(f"/api/v1/tenants/{tenant_id}/suspend", json=sample_suspend_payload)

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_suspend_tenant_validation_error_short_reason(
        self, client, mock_tenant_service, sample_tenant
    ):
        """Short reason returns 422 Unprocessable Entity."""
        invalid_payload = {"reason": "short"}  # Less than 10 chars

        response = client.post(f"/api/v1/tenants/{sample_tenant.id}/suspend", json=invalid_payload)

        assert response.status_code == 422
        mock_tenant_service.suspend_tenant.assert_not_called()

    def test_suspend_tenant_validation_error_missing_reason(
        self, client, mock_tenant_service, sample_tenant
    ):
        """Missing reason returns 422 Unprocessable Entity."""
        response = client.post(f"/api/v1/tenants/{sample_tenant.id}/suspend", json={})

        assert response.status_code == 422
        mock_tenant_service.suspend_tenant.assert_not_called()

    def test_suspend_tenant_system_tenant_error(
        self, client, mock_tenant_service, sample_tenant, sample_suspend_payload
    ):
        """Trying to suspend system tenant returns 400 Bad Request."""
        mock_tenant_service.suspend_tenant.side_effect = ValueError("Cannot suspend system tenant")

        response = client.post(
            f"/api/v1/tenants/{sample_tenant.id}/suspend", json=sample_suspend_payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "Cannot suspend system tenant" in data["detail"]

    def test_suspend_tenant_service_error(
        self, client, mock_tenant_service, sample_tenant, sample_suspend_payload
    ):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.suspend_tenant.side_effect = Exception("Database connection failed")

        response = client.post(
            f"/api/v1/tenants/{sample_tenant.id}/suspend", json=sample_suspend_payload
        )

        assert response.status_code == 500
        data = response.json()
        assert "Failed to suspend tenant" in data["detail"]


class TestResumeTenantEndpoint:
    """Tests for POST /tenants/{tenant_id}/resume endpoint."""

    @pytest.fixture
    def suspended_tenant(self, sample_tenant):
        """Sample suspended tenant."""
        return Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name=sample_tenant.name,
            status=TenantStatus.SUSPENDED,
            config={
                **sample_tenant.config,
                "suspension_reason": "Payment overdue",
                "suspended_at": datetime.now(UTC).isoformat(),
            },
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def resumed_tenant(self, suspended_tenant):
        """Sample resumed tenant."""
        config = suspended_tenant.config.copy()
        config.pop("suspension_reason", None)
        config.pop("suspended_at", None)
        config["resumed_at"] = datetime.now(UTC).isoformat()

        return Tenant(
            id=suspended_tenant.id,
            slug=suspended_tenant.slug,
            name=suspended_tenant.name,
            status=TenantStatus.ACTIVE,
            config=config,
            keycloak_org_id=suspended_tenant.keycloak_org_id,
            created_at=suspended_tenant.created_at,
            updated_at=datetime.now(UTC),
        )

    def test_resume_tenant_success(
        self, client, mock_tenant_service, suspended_tenant, resumed_tenant
    ):
        """Successful tenant resume returns 200 OK."""
        mock_tenant_service.resume_tenant.return_value = resumed_tenant

        response = client.post(f"/api/v1/tenants/{suspended_tenant.id}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == suspended_tenant.id
        assert data["status"] == "active"
        assert "suspension_reason" not in data["config"]
        assert "suspended_at" not in data["config"]
        assert "resumed_at" in data["config"]

        mock_tenant_service.resume_tenant.assert_called_once_with(tenant_id=suspended_tenant.id)

    def test_resume_tenant_not_found(self, client, mock_tenant_service):
        """Resume non-existent tenant returns 404 Not Found."""
        tenant_id = str(uuid.uuid4())
        mock_tenant_service.resume_tenant.return_value = None

        response = client.post(f"/api/v1/tenants/{tenant_id}/resume")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_resume_tenant_not_suspended_error(self, client, mock_tenant_service, sample_tenant):
        """Trying to resume non-suspended tenant returns 400 Bad Request."""
        mock_tenant_service.resume_tenant.side_effect = ValueError("Tenant is not suspended")

        response = client.post(f"/api/v1/tenants/{sample_tenant.id}/resume")

        assert response.status_code == 400
        data = response.json()
        assert "Tenant is not suspended" in data["detail"]

    def test_resume_tenant_service_error(self, client, mock_tenant_service, sample_tenant):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.resume_tenant.side_effect = Exception("Database connection failed")

        response = client.post(f"/api/v1/tenants/{sample_tenant.id}/resume")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to resume tenant" in data["detail"]


class TestDeleteTenantEndpoint:
    """Tests for DELETE /tenants/{tenant_id} endpoint."""

    @pytest.fixture
    def sample_delete_payload(self):
        """Sample valid delete tenant payload."""
        return {"reason": "Customer requested account closure - ticket #67890"}

    @pytest.fixture
    def deleted_tenant(self, sample_tenant):
        """Sample deleted tenant."""
        deleted_at = datetime.now(UTC)
        purge_at = datetime(
            deleted_at.year, deleted_at.month + 1, deleted_at.day, tzinfo=UTC
        )  # 30 days later

        return Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name=sample_tenant.name,
            status=TenantStatus.DELETED,
            config={
                **sample_tenant.config,
                "deletion_reason": "Customer requested account closure - ticket #67890",
                "purge_at": purge_at.isoformat(),
            },
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=deleted_at,
        )

    def test_delete_tenant_success(
        self, client, mock_tenant_service, sample_tenant, deleted_tenant, sample_delete_payload
    ):
        """Successful tenant deletion returns 200 OK."""
        mock_tenant_service.delete_tenant.return_value = deleted_tenant

        response = client.request(
            "DELETE", f"/api/v1/tenants/{sample_tenant.id}", json=sample_delete_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tenant.id
        assert data["status"] == "deleted"
        assert "deletion_reason" in data["config"]
        assert (
            data["config"]["deletion_reason"]
            == "Customer requested account closure - ticket #67890"
        )
        assert "purge_at" in data["config"]
        assert data["deleted_at"] is not None

        mock_tenant_service.delete_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, reason="Customer requested account closure - ticket #67890"
        )

    def test_delete_tenant_not_found(self, client, mock_tenant_service, sample_delete_payload):
        """Delete non-existent tenant returns 404 Not Found."""
        tenant_id = str(uuid.uuid4())
        mock_tenant_service.delete_tenant.return_value = None

        response = client.request(
            "DELETE", f"/api/v1/tenants/{tenant_id}", json=sample_delete_payload
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_delete_tenant_validation_error_short_reason(
        self, client, mock_tenant_service, sample_tenant
    ):
        """Short reason returns 422 Unprocessable Entity."""
        invalid_payload = {"reason": "short"}  # Less than 10 chars

        response = client.request(
            "DELETE", f"/api/v1/tenants/{sample_tenant.id}", json=invalid_payload
        )

        assert response.status_code == 422
        mock_tenant_service.delete_tenant.assert_not_called()

    def test_delete_tenant_validation_error_missing_reason(
        self, client, mock_tenant_service, sample_tenant
    ):
        """Missing reason returns 422 Unprocessable Entity."""
        response = client.request("DELETE", f"/api/v1/tenants/{sample_tenant.id}", json={})

        assert response.status_code == 422
        mock_tenant_service.delete_tenant.assert_not_called()

    def test_delete_tenant_system_tenant_error(
        self, client, mock_tenant_service, sample_tenant, sample_delete_payload
    ):
        """Trying to delete system tenant returns 400 Bad Request."""
        mock_tenant_service.delete_tenant.side_effect = ValueError("Cannot delete system tenant")

        response = client.request(
            "DELETE", f"/api/v1/tenants/{sample_tenant.id}", json=sample_delete_payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete system tenant" in data["detail"]

    def test_delete_tenant_service_error(
        self, client, mock_tenant_service, sample_tenant, sample_delete_payload
    ):
        """Service error returns 500 Internal Server Error."""
        mock_tenant_service.delete_tenant.side_effect = Exception("Database connection failed")

        response = client.request(
            "DELETE", f"/api/v1/tenants/{sample_tenant.id}", json=sample_delete_payload
        )

        assert response.status_code == 500
        data = response.json()
        assert "Failed to delete tenant" in data["detail"]


# =============================================================================
# Export Endpoint Tests
# =============================================================================


@pytest.fixture
def mock_export_service():
    """Create a mock TenantExportService."""
    from registry.export_service import TenantExportService

    service = AsyncMock(spec=TenantExportService)
    return service


@pytest.fixture
def app_with_mock_services(mock_tenant_service, mock_export_service):
    """Create FastAPI test app with both mocked services."""
    from registry.api.rest import get_export_service

    app = create_app()
    app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service
    app.dependency_overrides[get_export_service] = lambda: mock_export_service
    return app


@pytest.fixture
def export_client(app_with_mock_services):
    """Create test client with export service."""
    return TestClient(app_with_mock_services)


@pytest.fixture
def sample_export_request():
    """Sample valid export request payload."""
    return {
        "format": "json",
        "compress": True,
        "encrypt": True,
        "include_deleted": False,
        "include_audit_fields": False,
        "reason": "GDPR data export request from customer",
    }


@pytest.fixture
def sample_export_result():
    """Sample export result object."""
    from registry.export_service import ExportStatus, TenantExportResult

    export_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    return TenantExportResult(
        export_id=export_id,
        tenant_id=tenant_id,
        status=ExportStatus.IN_PROGRESS,
        file_path=None,
        file_size_bytes=None,
        records_exported=0,
        models_exported=[],
        created_at=now,
        completed_at=None,
        error_message=None,
    )


@pytest.fixture
def completed_export_result():
    """Sample completed export result object."""
    from registry.export_service import ExportStatus, TenantExportResult

    export_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    return TenantExportResult(
        export_id=export_id,
        tenant_id=tenant_id,
        status=ExportStatus.COMPLETED,
        file_path=f"/exports/tenant_{tenant_id}_{export_id}_20260105_120000.json.gz.enc",
        file_size_bytes=1024000,
        records_exported=1234,
        models_exported=["quotes", "trades", "users"],
        created_at=now - timedelta(minutes=10),
        completed_at=now,
        error_message=None,
    )


class TestExportTenantDataEndpoint:
    """Tests for POST /tenants/{tenant_id}/export endpoint."""

    def test_export_tenant_success(
        self,
        export_client,
        mock_tenant_service,
        mock_export_service,
        sample_tenant,
        sample_export_request,
        sample_export_result,
    ):
        """Successful export request returns 201 Created."""
        # Ensure tenant IDs match
        sample_export_result.tenant_id = sample_tenant.id

        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant
        mock_export_service.export_tenant_data.return_value = sample_export_result

        response = export_client.post(
            f"/api/v1/tenants/{sample_tenant.id}/export", json=sample_export_request
        )

        assert response.status_code == 201
        data = response.json()
        assert data["export_id"] == sample_export_result.export_id
        assert data["status"] == "in_progress"
        assert data["tenant_id"] == sample_tenant.id
        assert "created_at" in data
        assert (
            data["estimated_completion"] is not None
        )  # Should have estimated completion for in-progress status

        # Verify services were called correctly
        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)
        mock_export_service.export_tenant_data.assert_called_once()
        call_args = mock_export_service.export_tenant_data.call_args
        assert call_args[1]["tenant_id"] == sample_tenant.id
        assert call_args[1]["reason"] == "GDPR data export request from customer"
        # Verify export options were created correctly
        assert call_args[1]["options"].format.value == "json"
        assert call_args[1]["options"].compress is True
        assert call_args[1]["options"].encrypt is True

    def test_export_tenant_minimal_request(
        self,
        export_client,
        mock_tenant_service,
        mock_export_service,
        sample_tenant,
        sample_export_result,
    ):
        """Export with minimal request returns 201 Created."""
        minimal_request = {"reason": "Data portability request"}

        # Ensure tenant IDs match
        sample_export_result.tenant_id = sample_tenant.id

        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant
        mock_export_service.export_tenant_data.return_value = sample_export_result

        response = export_client.post(
            f"/api/v1/tenants/{sample_tenant.id}/export", json=minimal_request
        )

        assert response.status_code == 201

        # Verify default options were applied
        call_args = mock_export_service.export_tenant_data.call_args
        assert call_args[1]["options"].format.value == "json"  # Default format
        assert call_args[1]["options"].compress is True  # Default compress
        assert call_args[1]["options"].encrypt is True  # Default encrypt

    def test_export_tenant_not_found(
        self, export_client, mock_tenant_service, mock_export_service, sample_export_request
    ):
        """Export for non-existent tenant returns 404 Not Found."""
        non_existent_id = str(uuid.uuid4())
        mock_tenant_service.get_tenant_by_id.return_value = None

        response = export_client.post(
            f"/api/v1/tenants/{non_existent_id}/export", json=sample_export_request
        )

        assert response.status_code == 404
        data = response.json()
        assert f"Tenant '{non_existent_id}' not found" in str(data)

        # Export service should not be called
        mock_export_service.export_tenant_data.assert_not_called()

    def test_export_tenant_validation_error_short_reason(
        self, export_client, mock_tenant_service, mock_export_service, sample_tenant
    ):
        """Export with reason too short returns 422 Unprocessable Entity."""
        invalid_request = {
            "reason": "Short"  # Less than 10 characters
        }

        response = export_client.post(
            f"/api/v1/tenants/{sample_tenant.id}/export", json=invalid_request
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        # Services should not be called for validation errors
        mock_tenant_service.get_tenant_by_id.assert_not_called()
        mock_export_service.export_tenant_data.assert_not_called()

    def test_export_tenant_validation_error_invalid_format(self, export_client, sample_tenant):
        """Export with invalid format returns 400 Bad Request."""
        invalid_request = {
            "format": "xml",  # Invalid format
            "reason": "Valid reason for export request",
        }

        response = export_client.post(
            f"/api/v1/tenants/{sample_tenant.id}/export", json=invalid_request
        )

        assert response.status_code == 400  # Invalid format causes ValueError, which returns 400
        data = response.json()
        assert "not a valid ExportFormat" in str(data)

    def test_export_tenant_service_error(
        self,
        export_client,
        mock_tenant_service,
        mock_export_service,
        sample_tenant,
        sample_export_request,
    ):
        """Export service error returns 500 Internal Server Error."""
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant
        mock_export_service.export_tenant_data.side_effect = Exception(
            "Storage service unavailable"
        )

        response = export_client.post(
            f"/api/v1/tenants/{sample_tenant.id}/export", json=sample_export_request
        )

        assert response.status_code == 500
        data = response.json()
        assert "Failed to start tenant export" in data["detail"]


class TestGetTenantExportStatusEndpoint:
    """Tests for GET /tenants/{tenant_id}/export/{export_id} endpoint."""

    def test_get_export_status_success(
        self, export_client, mock_export_service, sample_tenant, completed_export_result
    ):
        """Successful status request returns 200 OK with export details."""
        completed_export_result.tenant_id = sample_tenant.id
        mock_export_service.get_export_result.return_value = completed_export_result

        response = export_client.get(
            f"/api/v1/tenants/{sample_tenant.id}/export/{completed_export_result.export_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["export_id"] == completed_export_result.export_id
        assert data["tenant_id"] == sample_tenant.id
        assert data["status"] == "completed"
        assert data["file_path"] == completed_export_result.file_path
        assert data["file_size_bytes"] == 1024000
        assert data["records_exported"] == 1234
        assert data["models_exported"] == ["quotes", "trades", "users"]
        assert "created_at" in data
        assert "completed_at" in data
        assert data["error_message"] is None

        # Verify service was called correctly
        mock_export_service.get_export_result.assert_called_once_with(
            completed_export_result.export_id
        )

    def test_get_export_status_in_progress(
        self, export_client, mock_export_service, sample_tenant, sample_export_result
    ):
        """In-progress export returns 200 OK with current status."""
        sample_export_result.tenant_id = sample_tenant.id
        mock_export_service.get_export_result.return_value = sample_export_result

        response = export_client.get(
            f"/api/v1/tenants/{sample_tenant.id}/export/{sample_export_result.export_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["export_id"] == sample_export_result.export_id
        assert data["status"] == "in_progress"
        assert data["file_path"] is None
        assert data["file_size_bytes"] is None
        assert data["records_exported"] == 0
        assert "created_at" in data  # This is what should be checked in status endpoint

    def test_get_export_status_not_found(self, export_client, mock_export_service, sample_tenant):
        """Non-existent export ID returns 404 Not Found."""
        non_existent_export_id = str(uuid.uuid4())
        mock_export_service.get_export_result.return_value = None

        response = export_client.get(
            f"/api/v1/tenants/{sample_tenant.id}/export/{non_existent_export_id}"
        )

        assert response.status_code == 404
        data = response.json()
        assert f"Export '{non_existent_export_id}' not found" in str(data)

    def test_get_export_status_wrong_tenant(
        self, export_client, mock_export_service, sample_tenant, completed_export_result
    ):
        """Export belonging to different tenant returns 404 Not Found."""
        other_tenant_id = str(uuid.uuid4())
        completed_export_result.tenant_id = other_tenant_id  # Different tenant
        mock_export_service.get_export_result.return_value = completed_export_result

        response = export_client.get(
            f"/api/v1/tenants/{sample_tenant.id}/export/{completed_export_result.export_id}"
        )

        assert response.status_code == 404
        data = response.json()
        assert (
            f"Export '{completed_export_result.export_id}' not found for tenant '{sample_tenant.id}'"
            in str(data)
        )

    def test_get_export_status_failed_export(
        self, export_client, mock_export_service, sample_tenant
    ):
        """Failed export returns 200 OK with error details."""
        from registry.export_service import ExportStatus, TenantExportResult

        failed_export = TenantExportResult(
            export_id=str(uuid.uuid4()),
            tenant_id=sample_tenant.id,
            status=ExportStatus.FAILED,
            file_path=None,
            file_size_bytes=None,
            records_exported=0,
            models_exported=[],
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            error_message="Database connection timeout during export",
        )

        mock_export_service.get_export_result.return_value = failed_export

        response = export_client.get(
            f"/api/v1/tenants/{sample_tenant.id}/export/{failed_export.export_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Database connection timeout during export"
        assert data["file_path"] is None

    def test_get_export_status_service_error(
        self, export_client, mock_export_service, sample_tenant
    ):
        """Export service error returns 500 Internal Server Error."""
        export_id = str(uuid.uuid4())
        mock_export_service.get_export_result.side_effect = Exception("Redis connection failed")

        response = export_client.get(f"/api/v1/tenants/{sample_tenant.id}/export/{export_id}")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to get export status" in data["detail"]
