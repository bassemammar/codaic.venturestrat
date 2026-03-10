"""Unit tests for tenant gRPC service implementation.

Tests for all gRPC endpoints including CRUD operations, status management,
quota management, and data export functionality.
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from google.protobuf.timestamp_pb2 import Timestamp
from registry.api.tenant_grpc_service import TenantGrpcService, TenantHealthService
from registry.grpc.tenant_pb2 import (
    CreateTenantRequest,
    DeleteTenantRequest,
    ExportTenantDataRequest,
    GetExportStatusRequest,
    GetTenantBySlugRequest,
    GetTenantQuotasRequest,
    GetTenantRequest,
    # Health Check
    HealthCheckRequest,
    HealthCheckResponse,
    ListTenantsRequest,
    ResumeTenantRequest,
    SuspendTenantRequest,
    # Messages
    TenantStatus,
    UpdateTenantQuotasRequest,
    UpdateTenantRequest,
    WatchTenantChangesRequest,
)
from registry.models.tenant import Tenant
from registry.models.tenant import TenantStatus as TenantStatusEnum


class MockServicerContext:
    """Mock gRPC servicer context for testing."""

    def __init__(self):
        self.code = None
        self.details = None

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


@pytest.fixture
def mock_tenant_service():
    """Mock tenant service for testing."""
    return AsyncMock()


@pytest.fixture
def mock_export_service():
    """Mock export service for testing."""
    return AsyncMock()


@pytest.fixture
def mock_quota_service():
    """Mock quota service for testing."""
    return AsyncMock()


@pytest.fixture
def grpc_service(mock_tenant_service, mock_export_service, mock_quota_service):
    """Create TenantGrpcService instance for testing."""
    return TenantGrpcService(
        tenant_service=mock_tenant_service,
        export_service=mock_export_service,
        quota_service=mock_quota_service,
    )


@pytest.fixture
def health_service(mock_tenant_service):
    """Create TenantHealthService instance for testing."""
    return TenantHealthService(tenant_service=mock_tenant_service)


@pytest.fixture
def mock_context():
    """Mock gRPC context."""
    return MockServicerContext()


@pytest.fixture
def sample_tenant():
    """Sample tenant for testing."""
    return Tenant(
        id="550e8400-e29b-41d4-a716-446655440000",
        slug="test-tenant",
        name="Test Tenant",
        status=TenantStatusEnum.ACTIVE,
        config={"test": "value"},
        keycloak_org_id="org-123",
        created_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
    )


class TestTenantGrpcService:
    """Test cases for TenantGrpcService."""

    async def test_create_tenant_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant creation."""
        # Setup
        mock_tenant_service.create_tenant.return_value = sample_tenant

        request = CreateTenantRequest(
            slug="test-tenant",
            name="Test Tenant",
            config={"test": "value"},
            admin_email="admin@test.com",
        )

        # Execute
        result = await grpc_service.CreateTenant(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.slug == sample_tenant.slug
        assert result.name == sample_tenant.name
        assert result.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert result.config["test"] == "value"
        assert mock_context.code is None

        mock_tenant_service.create_tenant.assert_called_once_with(
            slug="test-tenant",
            name="Test Tenant",
            config={"test": "value"},
            admin_email="admin@test.com",
        )

    async def test_create_tenant_missing_slug(self, grpc_service, mock_context):
        """Test tenant creation with missing slug."""
        request = CreateTenantRequest(name="Test Tenant")

        result = await grpc_service.CreateTenant(request, mock_context)

        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "slug is required" in mock_context.details

    async def test_create_tenant_missing_name(self, grpc_service, mock_context):
        """Test tenant creation with missing name."""
        request = CreateTenantRequest(slug="test-tenant")

        result = await grpc_service.CreateTenant(request, mock_context)

        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "name is required" in mock_context.details

    async def test_create_tenant_invalid_slug(self, grpc_service, mock_context):
        """Test tenant creation with invalid slug format."""
        request = CreateTenantRequest(
            slug="Invalid_Slug!",  # Invalid characters
            name="Test Tenant",
        )

        result = await grpc_service.CreateTenant(request, mock_context)

        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid slug format" in mock_context.details

    async def test_create_tenant_service_error(
        self, grpc_service, mock_tenant_service, mock_context
    ):
        """Test tenant creation when service raises error."""
        # Setup
        mock_tenant_service.create_tenant.side_effect = ValueError("Slug already exists")

        request = CreateTenantRequest(slug="test-tenant", name="Test Tenant")

        # Execute
        result = await grpc_service.CreateTenant(request, mock_context)

        # Verify
        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Slug already exists" in mock_context.details

    async def test_get_tenant_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant retrieval by ID."""
        # Setup
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        request = GetTenantRequest(tenant_id=sample_tenant.id)

        # Execute
        result = await grpc_service.GetTenant(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.slug == sample_tenant.slug
        assert result.name == sample_tenant.name
        assert mock_context.code is None

        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)

    async def test_get_tenant_not_found(self, grpc_service, mock_tenant_service, mock_context):
        """Test tenant retrieval when tenant not found."""
        # Setup
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_tenant_service.get_tenant_by_id.return_value = None

        request = GetTenantRequest(tenant_id=tenant_id)

        # Execute
        result = await grpc_service.GetTenant(request, mock_context)

        # Verify
        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.NOT_FOUND
        assert f"Tenant with ID '{tenant_id}' not found" in mock_context.details

    async def test_get_tenant_invalid_id(self, grpc_service, mock_context):
        """Test tenant retrieval with invalid UUID."""
        request = GetTenantRequest(tenant_id="invalid-uuid")

        result = await grpc_service.GetTenant(request, mock_context)

        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid tenant ID format" in mock_context.details

    async def test_get_tenant_by_slug_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant retrieval by slug."""
        # Setup
        mock_tenant_service.get_tenant_by_slug.return_value = sample_tenant

        request = GetTenantBySlugRequest(slug=sample_tenant.slug)

        # Execute
        result = await grpc_service.GetTenantBySlug(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.slug == sample_tenant.slug
        assert result.name == sample_tenant.name
        assert mock_context.code is None

        mock_tenant_service.get_tenant_by_slug.assert_called_once_with(sample_tenant.slug)

    async def test_update_tenant_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant update."""
        # Setup - create updated tenant
        updated_tenant = Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name="Updated Name",
            status=sample_tenant.status,
            config={"updated": "config"},
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.update_tenant.return_value = updated_tenant

        request = UpdateTenantRequest(
            tenant_id=sample_tenant.id, name="Updated Name", config={"updated": "config"}
        )

        # Execute
        result = await grpc_service.UpdateTenant(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.name == "Updated Name"
        assert result.config["updated"] == "config"
        assert mock_context.code is None

        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, name="Updated Name", config={"updated": "config"}
        )

    async def test_delete_tenant_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant deletion."""
        # Setup - create deleted tenant
        deleted_tenant = Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name=sample_tenant.name,
            status=TenantStatusEnum.DELETED,
            config={"deletion_reason": "Test deletion"},
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),
        )
        mock_tenant_service.delete_tenant.return_value = deleted_tenant

        request = DeleteTenantRequest(tenant_id=sample_tenant.id, reason="Test deletion")

        # Execute
        result = await grpc_service.DeleteTenant(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.status == TenantStatus.TENANT_STATUS_DELETED
        assert mock_context.code is None

        mock_tenant_service.delete_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, reason="Test deletion"
        )

    async def test_delete_tenant_missing_reason(self, grpc_service, mock_context):
        """Test tenant deletion without reason."""
        request = DeleteTenantRequest(tenant_id="550e8400-e29b-41d4-a716-446655440000")

        result = await grpc_service.DeleteTenant(request, mock_context)

        assert result.id == ""  # Empty tenant
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "reason is required" in mock_context.details

    async def test_list_tenants_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant listing."""
        # Setup
        tenants = [sample_tenant]
        total_count = 1
        mock_tenant_service.list_tenants.return_value = (tenants, total_count)

        request = ListTenantsRequest(page_size=50, status="active", search="test")

        # Execute
        result = await grpc_service.ListTenants(request, mock_context)

        # Verify
        assert len(result.tenants) == 1
        assert result.tenants[0].id == sample_tenant.id
        assert result.total_count == total_count
        assert mock_context.code is None

        mock_tenant_service.list_tenants.assert_called_once_with(
            status="active", search="test", page=1, page_size=50
        )

    async def test_list_tenants_invalid_page_size(self, grpc_service, mock_context):
        """Test tenant listing with invalid page size."""
        request = ListTenantsRequest(page_size=150)  # Too large

        result = await grpc_service.ListTenants(request, mock_context)

        assert len(result.tenants) == 0
        assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Page size must be between 1 and 100" in mock_context.details

    async def test_suspend_tenant_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant suspension."""
        # Setup - create suspended tenant
        suspended_tenant = Tenant(
            id=sample_tenant.id,
            slug=sample_tenant.slug,
            name=sample_tenant.name,
            status=TenantStatusEnum.SUSPENDED,
            config={"suspension_reason": "Test suspension"},
            keycloak_org_id=sample_tenant.keycloak_org_id,
            created_at=sample_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_tenant_service.suspend_tenant.return_value = suspended_tenant

        request = SuspendTenantRequest(tenant_id=sample_tenant.id, reason="Test suspension")

        # Execute
        result = await grpc_service.SuspendTenant(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.status == TenantStatus.TENANT_STATUS_SUSPENDED
        assert mock_context.code is None

        mock_tenant_service.suspend_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, reason="Test suspension"
        )

    async def test_resume_tenant_success(
        self, grpc_service, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test successful tenant resumption."""
        # Setup
        mock_tenant_service.resume_tenant.return_value = sample_tenant

        request = ResumeTenantRequest(tenant_id=sample_tenant.id)

        # Execute
        result = await grpc_service.ResumeTenant(request, mock_context)

        # Verify
        assert result.id == sample_tenant.id
        assert result.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert mock_context.code is None

        mock_tenant_service.resume_tenant.assert_called_once_with(tenant_id=sample_tenant.id)

    async def test_export_tenant_data_success(
        self, grpc_service, mock_tenant_service, mock_export_service, mock_context, sample_tenant
    ):
        """Test successful tenant data export."""
        # Setup
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        export_job = MagicMock()
        export_job.export_id = "export-123"
        export_job.status = "in_progress"
        export_job.estimated_completion = datetime(2026, 1, 5, 11, 0, 0, tzinfo=UTC)
        mock_export_service.start_export.return_value = export_job

        request = ExportTenantDataRequest(
            tenant_id=sample_tenant.id, data_types=["quotes", "trades"], format="json"
        )

        # Execute
        result = await grpc_service.ExportTenantData(request, mock_context)

        # Verify
        assert result.export_id == "export-123"
        assert result.status == "in_progress"
        assert mock_context.code is None

        mock_export_service.start_export.assert_called_once_with(
            tenant_id=sample_tenant.id, data_types=["quotes", "trades"], export_format="json"
        )

    async def test_export_tenant_data_no_export_service(
        self, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test export when export service is not available."""
        # Create service without export service
        grpc_service = TenantGrpcService(tenant_service=mock_tenant_service)

        request = ExportTenantDataRequest(tenant_id=sample_tenant.id)

        result = await grpc_service.ExportTenantData(request, mock_context)

        assert result.export_id == ""
        assert mock_context.code == grpc.StatusCode.UNIMPLEMENTED
        assert "Export service not available" in mock_context.details

    async def test_get_export_status_success(
        self, grpc_service, mock_export_service, mock_context, sample_tenant
    ):
        """Test successful export status retrieval."""
        # Setup
        export_job = MagicMock()
        export_job.export_id = "export-123"
        export_job.status = "completed"
        export_job.download_url = "https://example.com/download"
        export_job.expires_at = datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC)
        export_job.error_message = None
        mock_export_service.get_export_status.return_value = export_job

        request = GetExportStatusRequest(tenant_id=sample_tenant.id, export_id="export-123")

        # Execute
        result = await grpc_service.GetExportStatus(request, mock_context)

        # Verify
        assert result.export_id == "export-123"
        assert result.status == "completed"
        assert result.download_url == "https://example.com/download"
        assert mock_context.code is None

    async def test_get_tenant_quotas_success(
        self, grpc_service, mock_tenant_service, mock_quota_service, mock_context, sample_tenant
    ):
        """Test successful tenant quota retrieval."""
        # Setup
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        quota_info = MagicMock()
        quota_info.limit = 100
        quota_info.current = 42
        quota_info.usage_percentage = 42.0

        quotas = {"max_users": quota_info}
        mock_quota_service.get_tenant_quotas.return_value = quotas

        request = GetTenantQuotasRequest(tenant_id=sample_tenant.id)

        # Execute
        result = await grpc_service.GetTenantQuotas(request, mock_context)

        # Verify
        assert result.tenant_id == sample_tenant.id
        assert "max_users" in result.quotas
        assert result.quotas["max_users"].limit == 100
        assert result.quotas["max_users"].current == 42
        assert result.quotas["max_users"].usage_percentage == 42.0
        assert mock_context.code is None

    async def test_get_tenant_quotas_no_quota_service(
        self, mock_tenant_service, mock_context, sample_tenant
    ):
        """Test quota retrieval when quota service is not available."""
        # Create service without quota service
        grpc_service = TenantGrpcService(tenant_service=mock_tenant_service)

        request = GetTenantQuotasRequest(tenant_id=sample_tenant.id)

        result = await grpc_service.GetTenantQuotas(request, mock_context)

        assert result.tenant_id == ""
        assert mock_context.code == grpc.StatusCode.UNIMPLEMENTED
        assert "Quota service not available" in mock_context.details

    async def test_update_tenant_quotas_success(
        self, grpc_service, mock_tenant_service, mock_quota_service, mock_context, sample_tenant
    ):
        """Test successful tenant quota update."""
        # Setup
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        quota_info = MagicMock()
        quota_info.limit = 200
        quota_info.current = 42
        quota_info.usage_percentage = 21.0

        updated_quotas = {"max_users": quota_info}
        mock_quota_service.update_tenant_quotas.return_value = None
        mock_quota_service.get_tenant_quotas.return_value = updated_quotas

        request = UpdateTenantQuotasRequest(tenant_id=sample_tenant.id, quotas={"max_users": 200})

        # Execute
        result = await grpc_service.UpdateTenantQuotas(request, mock_context)

        # Verify
        assert result.tenant_id == sample_tenant.id
        assert "max_users" in result.quotas
        assert result.quotas["max_users"].limit == 200
        assert result.quotas["max_users"].current == 42
        assert result.quotas["max_users"].usage_percentage == 21.0
        assert mock_context.code is None

        mock_quota_service.update_tenant_quotas.assert_called_once_with(
            sample_tenant.id, {"max_users": 200}
        )

    async def test_watch_tenant_changes_basic(self, grpc_service, mock_context):
        """Test basic tenant change watching."""
        request = WatchTenantChangesRequest()

        # This is a streaming method, so we need to create an async iterator
        watch_generator = grpc_service.WatchTenantChanges(request, mock_context)

        # Verify we can create the generator without errors
        assert hasattr(watch_generator, "__aiter__")

        # For this test, we'll just verify the setup is correct
        # In a full implementation, we would test the streaming behavior

    def test_is_valid_slug(self, grpc_service):
        """Test slug validation logic."""
        # Valid slugs
        assert grpc_service._is_valid_slug("a") is True
        assert grpc_service._is_valid_slug("ab") is True
        assert grpc_service._is_valid_slug("test-tenant") is True
        assert grpc_service._is_valid_slug("abc123") is True
        assert grpc_service._is_valid_slug("a" * 63) is True

        # Invalid slugs
        assert grpc_service._is_valid_slug("") is False
        assert grpc_service._is_valid_slug("A") is False  # Uppercase
        assert grpc_service._is_valid_slug("-test") is False  # Starts with dash
        assert grpc_service._is_valid_slug("test-") is False  # Ends with dash
        assert grpc_service._is_valid_slug("test_tenant") is False  # Underscore
        assert grpc_service._is_valid_slug("test tenant") is False  # Space
        assert grpc_service._is_valid_slug("a" * 64) is False  # Too long


class TestTenantHealthService:
    """Test cases for TenantHealthService."""

    async def test_health_check_healthy(self, health_service, mock_tenant_service, mock_context):
        """Test health check when service is healthy."""
        # Setup
        mock_tenant_service.health_check.return_value = True

        request = HealthCheckRequest(service="tenant")

        # Execute
        result = await health_service.Check(request, mock_context)

        # Verify
        assert result.status == HealthCheckResponse.ServingStatus.SERVING
        mock_tenant_service.health_check.assert_called_once()

    async def test_health_check_unhealthy(self, health_service, mock_tenant_service, mock_context):
        """Test health check when service is unhealthy."""
        # Setup
        mock_tenant_service.health_check.return_value = False

        request = HealthCheckRequest(service="tenant")

        # Execute
        result = await health_service.Check(request, mock_context)

        # Verify
        assert result.status == HealthCheckResponse.ServingStatus.NOT_SERVING
        mock_tenant_service.health_check.assert_called_once()

    async def test_health_check_exception(self, health_service, mock_tenant_service, mock_context):
        """Test health check when exception occurs."""
        # Setup
        mock_tenant_service.health_check.side_effect = Exception("Database error")

        request = HealthCheckRequest(service="tenant")

        # Execute
        result = await health_service.Check(request, mock_context)

        # Verify
        assert result.status == HealthCheckResponse.ServingStatus.NOT_SERVING

    async def test_health_watch_basic(self, health_service, mock_tenant_service, mock_context):
        """Test basic health watching."""
        # Setup
        mock_tenant_service.health_check.return_value = True

        request = HealthCheckRequest(service="tenant")

        # This is a streaming method, so we need to create an async iterator
        watch_generator = health_service.Watch(request, mock_context)

        # Verify we can create the generator without errors
        assert hasattr(watch_generator, "__aiter__")

        # For this test, we'll just verify the setup is correct
        # In a full implementation, we would test the streaming behavior


class TestTenantModelConversion:
    """Test cases for tenant model to gRPC conversion."""

    def test_tenant_model_to_grpc_conversion(self, grpc_service):
        """Test conversion from Tenant model to gRPC Tenant."""
        # Create a tenant model
        tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={"test": "value"},
            keycloak_org_id="org-123",
            created_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
        )

        # Convert to gRPC
        grpc_tenant = grpc_service._tenant_model_to_grpc(tenant)

        # Verify conversion
        assert grpc_tenant.id == tenant.id
        assert grpc_tenant.slug == tenant.slug
        assert grpc_tenant.name == tenant.name
        assert grpc_tenant.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert grpc_tenant.config["test"] == "value"
        assert grpc_tenant.keycloak_org_id == "org-123"

        # Check timestamps
        expected_timestamp = Timestamp()
        expected_timestamp.FromDatetime(tenant.created_at)
        assert grpc_tenant.created_at == expected_timestamp

    def test_tenant_model_to_grpc_conversion_with_deleted_at(self, grpc_service):
        """Test conversion with deleted_at field."""
        deleted_at = datetime(2026, 1, 10, 10, 0, 0, tzinfo=UTC)

        tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.DELETED,
            config={},
            created_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
            deleted_at=deleted_at,
        )

        # Convert to gRPC
        grpc_tenant = grpc_service._tenant_model_to_grpc(tenant)

        # Verify conversion
        assert grpc_tenant.status == TenantStatus.TENANT_STATUS_DELETED

        # Check deleted_at timestamp
        expected_timestamp = Timestamp()
        expected_timestamp.FromDatetime(deleted_at)
        assert grpc_tenant.deleted_at == expected_timestamp

    def test_tenant_status_enum_conversion(self, grpc_service):
        """Test all tenant status enum conversions."""
        status_mappings = [
            (TenantStatusEnum.ACTIVE, TenantStatus.TENANT_STATUS_ACTIVE),
            (TenantStatusEnum.SUSPENDED, TenantStatus.TENANT_STATUS_SUSPENDED),
            (TenantStatusEnum.DELETED, TenantStatus.TENANT_STATUS_DELETED),
        ]

        for model_status, grpc_status in status_mappings:
            tenant = Tenant(
                id="550e8400-e29b-41d4-a716-446655440000",
                slug="test-tenant",
                name="Test Tenant",
                status=model_status,
                config={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            grpc_tenant = grpc_service._tenant_model_to_grpc(tenant)
            assert grpc_tenant.status == grpc_status
