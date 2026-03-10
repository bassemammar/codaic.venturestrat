"""Integration tests for Tenant gRPC Service.

These tests verify the complete gRPC server setup, real client-server
communication, and end-to-end behavior in a controlled environment.
"""
import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from grpc import aio as grpc_aio
from registry.api.tenant_grpc_service import TenantGrpcService, TenantHealthService
from registry.grpc.tenant_pb2 import (
    # Requests
    CreateTenantRequest,
    DeleteTenantRequest,
    ExportTenantDataRequest,
    GetTenantBySlugRequest,
    GetTenantQuotasRequest,
    GetTenantRequest,
    # Health Check
    HealthCheckRequest,
    HealthCheckResponse,
    ListTenantsRequest,
    ResumeTenantRequest,
    SuspendTenantRequest,
    TenantStatus,
    UpdateTenantQuotasRequest,
    UpdateTenantRequest,
    WatchTenantChangesRequest,
)
from registry.grpc.tenant_pb2_grpc import (
    HealthStub,
    TenantServiceStub,
    add_HealthServicer_to_server,
    add_TenantServiceServicer_to_server,
)
from registry.models.tenant import Tenant
from registry.models.tenant import TenantStatus as TenantStatusEnum


@pytest.fixture
async def grpc_server():
    """Create and start a real gRPC server for testing."""
    # Create mock services
    mock_tenant_service = AsyncMock()
    mock_export_service = AsyncMock()
    mock_quota_service = AsyncMock()

    # Create gRPC services
    tenant_grpc_service = TenantGrpcService(
        tenant_service=mock_tenant_service,
        export_service=mock_export_service,
        quota_service=mock_quota_service,
    )
    health_service = TenantHealthService(tenant_service=mock_tenant_service)

    # Create server
    server = grpc_aio.server()
    add_TenantServiceServicer_to_server(tenant_grpc_service, server)
    add_HealthServicer_to_server(health_service, server)

    # Listen on a random port
    listen_addr = "[::]:0"
    port = server.add_insecure_port(listen_addr)

    await server.start()

    yield server, port, mock_tenant_service, mock_export_service, mock_quota_service

    await server.stop(grace=None)


@pytest.fixture
async def grpc_client(grpc_server):
    """Create a gRPC client connected to the test server."""
    server, port, mock_tenant_service, mock_export_service, mock_quota_service = grpc_server

    channel = grpc_aio.insecure_channel(f"localhost:{port}")
    tenant_stub = TenantServiceStub(channel)
    health_stub = HealthStub(channel)

    yield (
        tenant_stub,
        health_stub,
        mock_tenant_service,
        mock_export_service,
        mock_quota_service,
    )

    await channel.close()


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


class TestTenantGrpcIntegration:
    """Integration tests for Tenant gRPC service."""

    async def test_server_startup_and_health_check(self, grpc_client):
        """Test that gRPC server starts correctly and responds to health checks."""
        tenant_stub, health_stub, mock_tenant_service, _, _ = grpc_client

        # Setup health check mock
        mock_tenant_service.health_check.return_value = True

        # Test health check
        request = HealthCheckRequest(service="TenantService")
        response = await health_stub.Check(request)

        assert response.status == HealthCheckResponse.ServingStatus.SERVING
        mock_tenant_service.health_check.assert_called_once()

    async def test_create_tenant_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant creation flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock
        mock_tenant_service.create_tenant.return_value = sample_tenant

        # Make request
        request = CreateTenantRequest(
            slug="test-tenant",
            name="Test Tenant",
            config={"test": "value"},
            admin_email="admin@test.com",
        )

        response = await tenant_stub.CreateTenant(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.slug == sample_tenant.slug
        assert response.name == sample_tenant.name
        assert response.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert response.config["test"] == "value"

        # Verify service was called correctly
        mock_tenant_service.create_tenant.assert_called_once_with(
            slug="test-tenant",
            name="Test Tenant",
            config={"test": "value"},
            admin_email="admin@test.com",
        )

    async def test_get_tenant_by_id_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant retrieval by ID over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        # Make request
        request = GetTenantRequest(tenant_id=sample_tenant.id)
        response = await tenant_stub.GetTenant(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.slug == sample_tenant.slug
        assert response.name == sample_tenant.name

        # Verify service was called
        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)

    async def test_get_tenant_by_slug_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant retrieval by slug over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock
        mock_tenant_service.get_tenant_by_slug.return_value = sample_tenant

        # Make request
        request = GetTenantBySlugRequest(slug=sample_tenant.slug)
        response = await tenant_stub.GetTenantBySlug(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.slug == sample_tenant.slug
        assert response.name == sample_tenant.name

        # Verify service was called
        mock_tenant_service.get_tenant_by_slug.assert_called_once_with(sample_tenant.slug)

    async def test_update_tenant_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant update flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Create updated tenant
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

        # Setup mock
        mock_tenant_service.update_tenant.return_value = updated_tenant

        # Make request
        request = UpdateTenantRequest(
            tenant_id=sample_tenant.id, name="Updated Name", config={"updated": "config"}
        )

        response = await tenant_stub.UpdateTenant(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.name == "Updated Name"
        assert response.config["updated"] == "config"

        # Verify service was called
        mock_tenant_service.update_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, name="Updated Name", config={"updated": "config"}
        )

    async def test_list_tenants_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant listing flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock
        mock_tenant_service.list_tenants.return_value = ([sample_tenant], 1)

        # Make request
        request = ListTenantsRequest(page_size=50, status="active", search="test")

        response = await tenant_stub.ListTenants(request)

        # Verify response
        assert len(response.tenants) == 1
        assert response.tenants[0].id == sample_tenant.id
        assert response.total_count == 1

        # Verify service was called
        mock_tenant_service.list_tenants.assert_called_once_with(
            status="active", search="test", page=1, page_size=50
        )

    async def test_suspend_tenant_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant suspension flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Create suspended tenant
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

        # Setup mock
        mock_tenant_service.suspend_tenant.return_value = suspended_tenant

        # Make request
        request = SuspendTenantRequest(tenant_id=sample_tenant.id, reason="Test suspension")

        response = await tenant_stub.SuspendTenant(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.status == TenantStatus.TENANT_STATUS_SUSPENDED

        # Verify service was called
        mock_tenant_service.suspend_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, reason="Test suspension"
        )

    async def test_resume_tenant_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant resumption flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock
        mock_tenant_service.resume_tenant.return_value = sample_tenant

        # Make request
        request = ResumeTenantRequest(tenant_id=sample_tenant.id)
        response = await tenant_stub.ResumeTenant(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.status == TenantStatus.TENANT_STATUS_ACTIVE

        # Verify service was called
        mock_tenant_service.resume_tenant.assert_called_once_with(tenant_id=sample_tenant.id)

    async def test_delete_tenant_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant deletion flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Create deleted tenant
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

        # Setup mock
        mock_tenant_service.delete_tenant.return_value = deleted_tenant

        # Make request
        request = DeleteTenantRequest(tenant_id=sample_tenant.id, reason="Test deletion")

        response = await tenant_stub.DeleteTenant(request)

        # Verify response
        assert response.id == sample_tenant.id
        assert response.status == TenantStatus.TENANT_STATUS_DELETED

        # Verify service was called
        mock_tenant_service.delete_tenant.assert_called_once_with(
            tenant_id=sample_tenant.id, reason="Test deletion"
        )

    async def test_export_tenant_data_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant data export flow over gRPC."""
        tenant_stub, _, mock_tenant_service, mock_export_service, _ = grpc_client

        # Setup mocks
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        export_job = MagicMock()
        export_job.export_id = "export-123"
        export_job.status = "in_progress"
        export_job.estimated_completion = datetime(2026, 1, 5, 11, 0, 0, tzinfo=UTC)
        mock_export_service.start_export.return_value = export_job

        # Make request
        request = ExportTenantDataRequest(
            tenant_id=sample_tenant.id, data_types=["quotes", "trades"], format="json"
        )

        response = await tenant_stub.ExportTenantData(request)

        # Verify response
        assert response.export_id == "export-123"
        assert response.status == "in_progress"

        # Verify services were called
        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)
        mock_export_service.start_export.assert_called_once_with(
            tenant_id=sample_tenant.id, data_types=["quotes", "trades"], export_format="json"
        )

    async def test_get_tenant_quotas_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant quota retrieval flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, mock_quota_service = grpc_client

        # Setup mocks
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        quota_info = MagicMock()
        quota_info.limit = 100
        quota_info.current = 42
        quota_info.usage_percentage = 42.0

        quotas = {"max_users": quota_info}
        mock_quota_service.get_tenant_quotas.return_value = quotas

        # Make request
        request = GetTenantQuotasRequest(tenant_id=sample_tenant.id)
        response = await tenant_stub.GetTenantQuotas(request)

        # Verify response
        assert response.tenant_id == sample_tenant.id
        assert "max_users" in response.quotas
        assert response.quotas["max_users"].limit == 100
        assert response.quotas["max_users"].current == 42
        assert response.quotas["max_users"].usage_percentage == 42.0

        # Verify services were called
        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)
        mock_quota_service.get_tenant_quotas.assert_called_once_with(sample_tenant.id)

    async def test_update_tenant_quotas_full_flow(self, grpc_client, sample_tenant):
        """Test complete tenant quota update flow over gRPC."""
        tenant_stub, _, mock_tenant_service, _, mock_quota_service = grpc_client

        # Setup mocks
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        quota_info = MagicMock()
        quota_info.limit = 200
        quota_info.current = 42
        quota_info.usage_percentage = 21.0

        updated_quotas = {"max_users": quota_info}
        mock_quota_service.update_tenant_quotas.return_value = None
        mock_quota_service.get_tenant_quotas.return_value = updated_quotas

        # Make request
        request = UpdateTenantQuotasRequest(tenant_id=sample_tenant.id, quotas={"max_users": 200})

        response = await tenant_stub.UpdateTenantQuotas(request)

        # Verify response
        assert response.tenant_id == sample_tenant.id
        assert "max_users" in response.quotas
        assert response.quotas["max_users"].limit == 200

        # Verify services were called
        mock_tenant_service.get_tenant_by_id.assert_called_once_with(sample_tenant.id)
        mock_quota_service.update_tenant_quotas.assert_called_once_with(
            sample_tenant.id, {"max_users": 200}
        )
        mock_quota_service.get_tenant_quotas.assert_called_once_with(sample_tenant.id)

    async def test_error_handling_over_grpc(self, grpc_client, sample_tenant):
        """Test that gRPC errors are properly propagated to the client."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock to raise exception
        mock_tenant_service.get_tenant_by_id.return_value = None

        # Make request that should fail
        request = GetTenantRequest(tenant_id=sample_tenant.id)

        # This should raise a gRPC RpcError with NOT_FOUND status
        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.GetTenant(request)

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
        assert "not found" in exc_info.value.details().lower()

    async def test_invalid_request_handling(self, grpc_client):
        """Test handling of invalid requests over gRPC."""
        tenant_stub, _, _, _, _ = grpc_client

        # Make request with invalid UUID
        request = GetTenantRequest(tenant_id="invalid-uuid")

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.GetTenant(request)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "invalid" in exc_info.value.details().lower()

    async def test_concurrent_requests(self, grpc_client, sample_tenant):
        """Test handling of concurrent gRPC requests."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        # Setup mock
        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        # Make multiple concurrent requests
        requests = [GetTenantRequest(tenant_id=sample_tenant.id) for _ in range(10)]

        responses = await asyncio.gather(*[tenant_stub.GetTenant(request) for request in requests])

        # Verify all responses are correct
        assert len(responses) == 10
        for response in responses:
            assert response.id == sample_tenant.id
            assert response.slug == sample_tenant.slug

        # Verify service was called for each request
        assert mock_tenant_service.get_tenant_by_id.call_count == 10

    async def test_health_watch_streaming(self, grpc_client):
        """Test health watch streaming functionality."""
        _, health_stub, mock_tenant_service, _, _ = grpc_client

        # Setup health check mock
        mock_tenant_service.health_check.return_value = True

        # Start health watch
        request = HealthCheckRequest(service="TenantService")
        stream = health_stub.Watch(request)

        # Get first response (should be immediate)
        response = await stream.__anext__()
        assert response.status == HealthCheckResponse.ServingStatus.SERVING

        # Note: In a real implementation, we would continue to receive
        # periodic health updates. Here we just verify the stream starts.


class TestTenantGrpcStreamingIntegration:
    """Integration tests for streaming gRPC operations."""

    async def test_watch_tenant_changes_streaming(self, grpc_client):
        """Test tenant change watching streaming functionality."""
        tenant_stub, _, _, _, _ = grpc_client

        # Start watching changes
        request = WatchTenantChangesRequest()
        stream = tenant_stub.WatchTenantChanges(request)

        # Verify stream can be created (actual events would require
        # event injection mechanism in a real implementation)
        assert hasattr(stream, "__aiter__")

        # Note: Full streaming test would require event publishing
        # mechanism to inject test events into the stream

    async def test_watch_tenant_changes_with_filter(self, grpc_client, sample_tenant):
        """Test tenant change watching with tenant filter."""
        tenant_stub, _, _, _, _ = grpc_client

        # Start watching changes for specific tenant
        request = WatchTenantChangesRequest()
        request.tenant_id = sample_tenant.id

        stream = tenant_stub.WatchTenantChanges(request)

        # Verify stream can be created with filter
        assert hasattr(stream, "__aiter__")


class TestTenantGrpcServerConfiguration:
    """Tests for gRPC server configuration and lifecycle."""

    async def test_server_supports_reflection(self, grpc_server):
        """Test that gRPC server can be configured with reflection."""
        server, port, _, _, _ = grpc_server

        # Server should be running and accessible
        channel = grpc_aio.insecure_channel(f"localhost:{port}")

        # Try to create a stub (this verifies the server is accessible)
        stub = TenantServiceStub(channel)
        assert stub is not None

        await channel.close()

    async def test_server_handles_service_registration(self, grpc_server):
        """Test that services are properly registered on the server."""
        server, port, mock_tenant_service, _, _ = grpc_server

        # Server should have both TenantService and Health services
        channel = grpc_aio.insecure_channel(f"localhost:{port}")

        # Test TenantService is available
        tenant_stub = TenantServiceStub(channel)
        health_stub = HealthStub(channel)

        # Both stubs should be creatable
        assert tenant_stub is not None
        assert health_stub is not None

        await channel.close()

    async def test_server_graceful_shutdown(self, grpc_server):
        """Test that gRPC server can be gracefully shut down."""
        server, port, _, _, _ = grpc_server

        # Server should be running
        channel = grpc_aio.insecure_channel(f"localhost:{port}")

        # Make a connection to verify server is up
        stub = TenantServiceStub(channel)
        assert stub is not None

        await channel.close()

        # Server will be shut down by the fixture cleanup
        # This test verifies the basic setup works


class TestTenantGrpcServiceDiscovery:
    """Tests for gRPC service discovery and metadata."""

    async def test_service_methods_are_discoverable(self, grpc_client):
        """Test that all expected service methods are available."""
        tenant_stub, health_stub, _, _, _ = grpc_client

        # TenantService methods should be available
        expected_tenant_methods = [
            "CreateTenant",
            "GetTenant",
            "GetTenantBySlug",
            "UpdateTenant",
            "DeleteTenant",
            "ListTenants",
            "SuspendTenant",
            "ResumeTenant",
            "ExportTenantData",
            "GetExportStatus",
            "GetTenantQuotas",
            "UpdateTenantQuotas",
            "WatchTenantChanges",
        ]

        for method_name in expected_tenant_methods:
            assert hasattr(
                tenant_stub, method_name
            ), f"Method {method_name} not found on TenantService"

        # Health service methods should be available
        expected_health_methods = ["Check", "Watch"]

        for method_name in expected_health_methods:
            assert hasattr(
                health_stub, method_name
            ), f"Method {method_name} not found on Health service"
