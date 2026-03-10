"""Edge case and error handling tests for tenant gRPC service.

These tests focus on boundary conditions, error scenarios,
and edge cases that might not be covered in the main test suite.
"""
import asyncio
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from registry.api.tenant_grpc_service import TenantGrpcService, TenantHealthService
from registry.grpc.tenant_pb2 import (
    # Requests
    CreateTenantRequest,
    ExportTenantDataRequest,
    GetTenantQuotasRequest,
    GetTenantRequest,
    # Health Check
    HealthCheckRequest,
    HealthCheckResponse,
    ListTenantsRequest,
    TenantStatus,
    UpdateTenantRequest,
)
from registry.models.tenant import Tenant
from registry.models.tenant import TenantStatus as TenantStatusEnum


class MockServicerContext:
    """Enhanced mock gRPC servicer context for testing."""

    def __init__(self):
        self.code = None
        self.details = None
        self._cancelled = False
        self._peer = "test-client"

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self):
        return self._cancelled

    def peer(self):
        return self._peer


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
def enhanced_mock_context():
    """Enhanced mock gRPC context."""
    return MockServicerContext()


class TestTenantGrpcEdgeCases:
    """Test edge cases and error scenarios."""

    # =============================================================================
    # Input Validation Edge Cases
    # =============================================================================

    async def test_create_tenant_extremely_long_name(self, grpc_service, enhanced_mock_context):
        """Test tenant creation with extremely long name."""
        very_long_name = "A" * 1000  # 1000 characters

        request = CreateTenantRequest(
            slug="test-tenant",
            name=very_long_name,
        )

        await grpc_service.CreateTenant(request, enhanced_mock_context)

        # Should handle gracefully, either by truncating or rejecting
        assert enhanced_mock_context.code is not None

    async def test_create_tenant_unicode_characters(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation with Unicode characters."""
        unicode_name = "Test Tenant 测试 🏢"
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name=unicode_name,
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.create_tenant.return_value = sample_tenant

        request = CreateTenantRequest(
            slug="test-tenant",
            name=unicode_name,
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.name == unicode_name
        assert enhanced_mock_context.code is None

    async def test_create_tenant_empty_config_map(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation with empty config map."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.create_tenant.return_value = sample_tenant

        request = CreateTenantRequest(
            slug="test-tenant",
            name="Test Tenant",
            config={},  # Empty config
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.id == sample_tenant.id
        assert len(result.config) == 0
        assert enhanced_mock_context.code is None

    async def test_create_tenant_complex_config_values(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation with complex config values."""
        complex_config = {
            "nested": "{'key': 'value'}",
            "json_string": '{"array": [1, 2, 3], "null": null}',
            "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
            "unicode": "🚀 测试 配置",
            "empty_string": "",
            "numbers": "123456789",
        }

        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config=complex_config,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.create_tenant.return_value = sample_tenant

        request = CreateTenantRequest(slug="test-tenant", name="Test Tenant", config=complex_config)

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.config["nested"] == complex_config["nested"]
        assert result.config["unicode"] == complex_config["unicode"]
        assert enhanced_mock_context.code is None

    # =============================================================================
    # Boundary Value Tests
    # =============================================================================

    async def test_create_tenant_minimum_valid_slug(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation with minimum valid slug (1 character)."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="a",  # Minimum valid slug
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.create_tenant.return_value = sample_tenant

        request = CreateTenantRequest(
            slug="a",
            name="Test Tenant",
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.slug == "a"
        assert enhanced_mock_context.code is None

    async def test_create_tenant_maximum_valid_slug(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation with maximum valid slug (63 characters)."""
        max_slug = "a" + "b" * 61 + "c"  # 63 characters total

        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug=max_slug,
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.create_tenant.return_value = sample_tenant

        request = CreateTenantRequest(
            slug=max_slug,
            name="Test Tenant",
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.slug == max_slug
        assert enhanced_mock_context.code is None

    async def test_create_tenant_slug_too_long(self, grpc_service, enhanced_mock_context):
        """Test tenant creation with slug that's too long (64+ characters)."""
        too_long_slug = "a" * 64  # 64 characters - too long

        request = CreateTenantRequest(
            slug=too_long_slug,
            name="Test Tenant",
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.id == ""  # Empty tenant
        assert enhanced_mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid slug format" in enhanced_mock_context.details

    # =============================================================================
    # Service Interaction Edge Cases
    # =============================================================================

    async def test_create_tenant_service_timeout(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation when service times out."""
        # Simulate timeout
        mock_tenant_service.create_tenant.side_effect = TimeoutError("Service timeout")

        request = CreateTenantRequest(
            slug="test-tenant",
            name="Test Tenant",
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.id == ""  # Empty tenant
        assert enhanced_mock_context.code == grpc.StatusCode.INTERNAL

    async def test_create_tenant_service_memory_error(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test tenant creation when service runs out of memory."""
        # Simulate memory error
        mock_tenant_service.create_tenant.side_effect = MemoryError("Out of memory")

        request = CreateTenantRequest(
            slug="test-tenant",
            name="Test Tenant",
        )

        result = await grpc_service.CreateTenant(request, enhanced_mock_context)

        assert result.id == ""  # Empty tenant
        assert enhanced_mock_context.code == grpc.StatusCode.INTERNAL

    async def test_get_tenant_service_none_return(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test get tenant when service returns None."""
        mock_tenant_service.get_tenant_by_id.return_value = None

        request = GetTenantRequest(tenant_id="550e8400-e29b-41d4-a716-446655440000")

        result = await grpc_service.GetTenant(request, enhanced_mock_context)

        assert result.id == ""  # Empty tenant
        assert enhanced_mock_context.code == grpc.StatusCode.NOT_FOUND

    async def test_list_tenants_empty_result(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test list tenants when no tenants exist."""
        mock_tenant_service.list_tenants.return_value = ([], 0)

        request = ListTenantsRequest(page_size=50)

        result = await grpc_service.ListTenants(request, enhanced_mock_context)

        assert len(result.tenants) == 0
        assert result.total_count == 0
        assert result.next_page_token == ""
        assert enhanced_mock_context.code is None

    # =============================================================================
    # Quota Service Edge Cases
    # =============================================================================

    async def test_get_tenant_quotas_service_unavailable(
        self, mock_tenant_service, enhanced_mock_context
    ):
        """Test quota retrieval when quota service is not available."""
        # Create service without quota service
        grpc_service = TenantGrpcService(tenant_service=mock_tenant_service)

        request = GetTenantQuotasRequest(tenant_id="550e8400-e29b-41d4-a716-446655440000")

        result = await grpc_service.GetTenantQuotas(request, enhanced_mock_context)

        assert result.tenant_id == ""
        assert enhanced_mock_context.code == grpc.StatusCode.UNIMPLEMENTED
        assert "Quota service not available" in enhanced_mock_context.details

    async def test_get_tenant_quotas_empty_quotas(
        self, grpc_service, mock_tenant_service, mock_quota_service, enhanced_mock_context
    ):
        """Test quota retrieval when tenant has no quotas."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant
        mock_quota_service.get_tenant_quotas.return_value = {}  # Empty quotas

        request = GetTenantQuotasRequest(tenant_id=sample_tenant.id)

        result = await grpc_service.GetTenantQuotas(request, enhanced_mock_context)

        assert result.tenant_id == sample_tenant.id
        assert len(result.quotas) == 0
        assert enhanced_mock_context.code is None

    # =============================================================================
    # Export Service Edge Cases
    # =============================================================================

    async def test_export_tenant_data_service_unavailable(
        self, mock_tenant_service, enhanced_mock_context
    ):
        """Test export when export service is not available."""
        # Create service without export service
        grpc_service = TenantGrpcService(tenant_service=mock_tenant_service)

        request = ExportTenantDataRequest(tenant_id="550e8400-e29b-41d4-a716-446655440000")

        result = await grpc_service.ExportTenantData(request, enhanced_mock_context)

        assert result.export_id == ""
        assert enhanced_mock_context.code == grpc.StatusCode.UNIMPLEMENTED
        assert "Export service not available" in enhanced_mock_context.details

    async def test_export_tenant_data_invalid_data_types(
        self, grpc_service, mock_tenant_service, mock_export_service, enhanced_mock_context
    ):
        """Test export with empty data types list."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        export_job = MagicMock()
        export_job.export_id = "export-123"
        export_job.status = "in_progress"
        export_job.estimated_completion = datetime.now(UTC) + timedelta(hours=1)
        mock_export_service.start_export.return_value = export_job

        request = ExportTenantDataRequest(
            tenant_id=sample_tenant.id,
            data_types=[],  # Empty list
            format="json",
        )

        result = await grpc_service.ExportTenantData(request, enhanced_mock_context)

        # Should still work - empty list means export all
        assert result.export_id == "export-123"
        assert enhanced_mock_context.code is None

        # Verify service was called with None (all data types)
        mock_export_service.start_export.assert_called_once_with(
            tenant_id=sample_tenant.id, data_types=None, export_format="json"
        )

    # =============================================================================
    # Timestamp and Date Handling
    # =============================================================================

    async def test_tenant_conversion_with_timezone_edge_cases(self, grpc_service):
        """Test tenant model conversion with various timezone scenarios."""
        # Test with different timezones
        utc_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC)
        est_time = datetime(2026, 1, 5, 5, 0, 0, tzinfo=timezone(timedelta(hours=-5)))

        tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=utc_time,
            updated_at=est_time,
        )

        grpc_tenant = grpc_service._tenant_model_to_grpc(tenant)

        # Both timestamps should be properly converted
        assert grpc_tenant.created_at.seconds > 0
        assert grpc_tenant.updated_at.seconds > 0

    async def test_tenant_conversion_without_deleted_at(self, grpc_service):
        """Test tenant conversion when deleted_at is None."""
        tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,  # Explicitly None
        )

        grpc_tenant = grpc_service._tenant_model_to_grpc(tenant)

        # deleted_at should not be set in gRPC message
        assert not grpc_tenant.HasField("deleted_at")

    # =============================================================================
    # Status Enum Edge Cases
    # =============================================================================

    async def test_tenant_conversion_unknown_status(self, grpc_service):
        """Test tenant conversion with unknown status enum."""
        # Create a mock tenant with an unexpected status
        tenant = MagicMock()
        tenant.id = "550e8400-e29b-41d4-a716-446655440000"
        tenant.slug = "test-tenant"
        tenant.name = "Test Tenant"
        tenant.status = "UNKNOWN_STATUS"  # Not in enum
        tenant.config = {}
        tenant.keycloak_org_id = None
        tenant.created_at = datetime.now(UTC)
        tenant.updated_at = datetime.now(UTC)
        tenant.deleted_at = None

        grpc_tenant = grpc_service._tenant_model_to_grpc(tenant)

        # Should default to UNKNOWN status
        assert grpc_tenant.status == TenantStatus.TENANT_STATUS_UNKNOWN

    # =============================================================================
    # Update Operation Edge Cases
    # =============================================================================

    async def test_update_tenant_partial_update_name_only(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test partial tenant update with name only."""
        updated_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Updated Name Only",
            status=TenantStatusEnum.ACTIVE,
            config={"existing": "config"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.update_tenant.return_value = updated_tenant

        request = UpdateTenantRequest(
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Updated Name Only",
            # No config provided
        )

        result = await grpc_service.UpdateTenant(request, enhanced_mock_context)

        assert result.name == "Updated Name Only"
        assert result.config["existing"] == "config"
        assert enhanced_mock_context.code is None

        # Verify service was called with correct parameters
        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Updated Name Only",
            config=None,  # Should be None when not provided
        )

    async def test_update_tenant_partial_update_config_only(
        self, grpc_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test partial tenant update with config only."""
        updated_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Original Name",
            status=TenantStatusEnum.ACTIVE,
            config={"updated": "config"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_tenant_service.update_tenant.return_value = updated_tenant

        request = UpdateTenantRequest(
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            config={"updated": "config"},
            # No name provided
        )

        result = await grpc_service.UpdateTenant(request, enhanced_mock_context)

        assert result.name == "Original Name"
        assert result.config["updated"] == "config"
        assert enhanced_mock_context.code is None

        # Verify service was called with correct parameters
        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name=None,  # Should be None when not provided
            config={"updated": "config"},
        )

    # =============================================================================
    # Large Data Handling
    # =============================================================================

    async def test_list_tenants_large_page_size(self, grpc_service, enhanced_mock_context):
        """Test list tenants with page size at maximum boundary."""
        request = ListTenantsRequest(page_size=100)  # Maximum allowed

        await grpc_service.ListTenants(request, enhanced_mock_context)

        # Should succeed with max page size
        assert enhanced_mock_context.code is None

    async def test_list_tenants_excessive_page_size(self, grpc_service, enhanced_mock_context):
        """Test list tenants with excessive page size."""
        request = ListTenantsRequest(page_size=101)  # Over maximum

        await grpc_service.ListTenants(request, enhanced_mock_context)

        assert enhanced_mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Page size must be between 1 and 100" in enhanced_mock_context.details

    async def test_list_tenants_zero_page_size(self, grpc_service, enhanced_mock_context):
        """Test list tenants with zero page size."""
        request = ListTenantsRequest(page_size=0)

        await grpc_service.ListTenants(request, enhanced_mock_context)

        assert enhanced_mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Page size must be between 1 and 100" in enhanced_mock_context.details

    async def test_list_tenants_negative_page_size(self, grpc_service, enhanced_mock_context):
        """Test list tenants with negative page size."""
        request = ListTenantsRequest(page_size=-1)

        await grpc_service.ListTenants(request, enhanced_mock_context)

        assert enhanced_mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
        assert "Page size must be between 1 and 100" in enhanced_mock_context.details


class TestTenantHealthServiceEdgeCases:
    """Edge case tests for health service."""

    async def test_health_check_service_exception_during_check(
        self, health_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test health check when service raises unexpected exception."""
        mock_tenant_service.health_check.side_effect = RuntimeError("Unexpected error")

        request = HealthCheckRequest(service="TenantService")

        result = await health_service.Check(request, enhanced_mock_context)

        assert result.status == HealthCheckResponse.ServingStatus.NOT_SERVING

    async def test_health_watch_service_exception(
        self, health_service, mock_tenant_service, enhanced_mock_context
    ):
        """Test health watch when service raises exception."""
        mock_tenant_service.health_check.side_effect = RuntimeError("Unexpected error")

        request = HealthCheckRequest(service="TenantService")

        # Get the first response from watch
        watch_generator = health_service.Watch(request, enhanced_mock_context)
        response = await watch_generator.__anext__()

        assert response.status == HealthCheckResponse.ServingStatus.NOT_SERVING


class TestTenantGrpcSlugValidation:
    """Comprehensive slug validation tests."""

    def test_slug_validation_edge_cases(self, grpc_service):
        """Test various slug validation edge cases."""
        # Valid cases
        valid_slugs = [
            "a",
            "ab",
            "a1",
            "1a",
            "test-tenant",
            "tenant-123",
            "abc-def-ghi",
            "x" * 63,  # Maximum length
            "a1b2c3",
            "prod-eu-west-1",
        ]

        for slug in valid_slugs:
            assert grpc_service._is_valid_slug(slug), f"Slug '{slug}' should be valid"

        # Invalid cases
        invalid_slugs = [
            "",  # Empty
            "-",  # Just dash
            "-a",  # Starts with dash
            "a-",  # Ends with dash
            "A",  # Uppercase
            "TEST",  # All uppercase
            "test_tenant",  # Underscore
            "test tenant",  # Space
            "test.tenant",  # Dot
            "test@tenant",  # Special characters
            "test/tenant",  # Slash
            "test\\tenant",  # Backslash
            "test+tenant",  # Plus
            "test=tenant",  # Equals
            "x" * 64,  # Too long
            "ü-tenant",  # Unicode characters
            "test-tenant-",  # Ends with dash (multi-char)
            "-test-tenant",  # Starts with dash (multi-char)
            "--",  # Multiple dashes
            "a--b",  # Double dash in middle
        ]

        for slug in invalid_slugs:
            assert not grpc_service._is_valid_slug(slug), f"Slug '{slug}' should be invalid"

    def test_slug_validation_boundary_lengths(self, grpc_service):
        """Test slug validation at exact length boundaries."""
        # Exactly 1 character (minimum)
        assert grpc_service._is_valid_slug("a") is True
        assert grpc_service._is_valid_slug("1") is True

        # Exactly 63 characters (maximum)
        max_valid = "a" + "b" * 61 + "c"  # Start/end alphanumeric, middle can be anything
        assert len(max_valid) == 63
        assert grpc_service._is_valid_slug(max_valid) is True

        # Exactly 64 characters (too long)
        too_long = "a" + "b" * 62 + "c"
        assert len(too_long) == 64
        assert grpc_service._is_valid_slug(too_long) is False

    def test_slug_validation_dash_patterns(self, grpc_service):
        """Test various dash patterns in slugs."""
        # Valid dash patterns
        valid_dash_patterns = [
            "a-b",
            "a-b-c",
            "test-123",
            "a1-b2-c3",
            "very-long-slug-with-many-dashes",
        ]

        for slug in valid_dash_patterns:
            assert grpc_service._is_valid_slug(slug) is True, f"'{slug}' should be valid"

        # Invalid dash patterns
        invalid_dash_patterns = [
            "-",
            "-a",
            "a-",
            "--",
            "a--b",
            "-abc-",
            "a-b-",
            "-a-b",
        ]

        for slug in invalid_dash_patterns:
            assert grpc_service._is_valid_slug(slug) is False, f"'{slug}' should be invalid"
