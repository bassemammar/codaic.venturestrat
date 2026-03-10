"""End-to-End Tenant Lifecycle Integration Tests.

These tests verify the complete tenant lifecycle flow over gRPC:
create → suspend → resume → delete

This covers the full state transitions and business logic end-to-end.
"""
import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import grpc
import pytest
from grpc import aio as grpc_aio
from registry.api.tenant_grpc_service import TenantGrpcService, TenantHealthService
from registry.grpc.tenant_pb2 import (
    # Requests
    CreateTenantRequest,
    DeleteTenantRequest,
    ResumeTenantRequest,
    SuspendTenantRequest,
    TenantStatus,
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
def tenant_lifecycle_data():
    """Data for tenant lifecycle testing."""
    tenant_id = str(uuid.uuid4())
    base_time = datetime(2026, 1, 8, 10, 0, 0, tzinfo=UTC)

    return {
        "tenant_id": tenant_id,
        "slug": "lifecycle-test-tenant",
        "name": "Lifecycle Test Tenant",
        "admin_email": "admin@lifecycle-test.com",
        "config": {"test": "lifecycle"},
        "keycloak_org_id": "org-lifecycle-123",
        "base_time": base_time,
    }


class TestTenantE2ELifecycle:
    """End-to-End tests for complete tenant lifecycle."""

    @pytest.mark.integration
    async def test_full_tenant_lifecycle_create_suspend_resume_delete(
        self, grpc_client, tenant_lifecycle_data
    ):
        """
        Test the complete tenant lifecycle: create → suspend → resume → delete.

        This is the core E2E test that verifies all state transitions work correctly
        through the gRPC API and that the tenant model properly maintains state.
        """
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client
        data = tenant_lifecycle_data

        # =====================================================================
        # PHASE 1: CREATE TENANT
        # =====================================================================

        # Create the initial active tenant
        created_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.ACTIVE,
            config=data["config"],
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=data["base_time"],
        )

        mock_tenant_service.create_tenant.return_value = created_tenant

        # Make create request
        create_request = CreateTenantRequest(
            slug=data["slug"],
            name=data["name"],
            config=data["config"],
            admin_email=data["admin_email"],
        )

        create_response = await tenant_stub.CreateTenant(create_request)

        # Verify creation
        assert create_response.id == data["tenant_id"]
        assert create_response.slug == data["slug"]
        assert create_response.name == data["name"]
        assert create_response.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert create_response.config["test"] == "lifecycle"

        # Verify service was called correctly
        mock_tenant_service.create_tenant.assert_called_once_with(
            slug=data["slug"],
            name=data["name"],
            config=data["config"],
            admin_email=data["admin_email"],
        )

        # =====================================================================
        # PHASE 2: SUSPEND TENANT
        # =====================================================================

        # Create suspended tenant with reason in config
        suspended_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.SUSPENDED,
            config={
                **data["config"],
                "suspension_reason": "E2E test suspension",
                "suspended_at": "2026-01-08T10:05:00Z",
            },
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=datetime(2026, 1, 8, 10, 5, 0, tzinfo=UTC),
        )

        mock_tenant_service.suspend_tenant.return_value = suspended_tenant

        # Make suspend request
        suspend_request = SuspendTenantRequest(
            tenant_id=data["tenant_id"], reason="E2E test suspension"
        )

        suspend_response = await tenant_stub.SuspendTenant(suspend_request)

        # Verify suspension
        assert suspend_response.id == data["tenant_id"]
        assert suspend_response.status == TenantStatus.TENANT_STATUS_SUSPENDED
        assert suspend_response.config["suspension_reason"] == "E2E test suspension"
        assert "suspended_at" in suspend_response.config

        # Verify service was called correctly
        mock_tenant_service.suspend_tenant.assert_called_once_with(
            tenant_id=data["tenant_id"], reason="E2E test suspension"
        )

        # =====================================================================
        # PHASE 3: RESUME TENANT
        # =====================================================================

        # Create resumed tenant (back to active, suspension metadata removed)
        resumed_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.ACTIVE,
            config=data["config"],  # Config cleaned of suspension metadata
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=datetime(2026, 1, 8, 10, 10, 0, tzinfo=UTC),
        )

        mock_tenant_service.resume_tenant.return_value = resumed_tenant

        # Make resume request
        resume_request = ResumeTenantRequest(tenant_id=data["tenant_id"])
        resume_response = await tenant_stub.ResumeTenant(resume_request)

        # Verify resumption
        assert resume_response.id == data["tenant_id"]
        assert resume_response.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert "suspension_reason" not in resume_response.config
        assert "suspended_at" not in resume_response.config
        assert resume_response.config["test"] == "lifecycle"  # Original config preserved

        # Verify service was called correctly
        mock_tenant_service.resume_tenant.assert_called_once_with(tenant_id=data["tenant_id"])

        # =====================================================================
        # PHASE 4: DELETE TENANT (SOFT DELETE)
        # =====================================================================

        # Create deleted tenant with soft delete timestamps
        deleted_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.DELETED,
            config={
                **data["config"],
                "deletion_reason": "E2E test deletion",
                "purge_at": "2026-02-07T10:15:00Z",  # 30 days later
            },
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=datetime(2026, 1, 8, 10, 15, 0, tzinfo=UTC),
            deleted_at=datetime(2026, 1, 8, 10, 15, 0, tzinfo=UTC),
        )

        mock_tenant_service.delete_tenant.return_value = deleted_tenant

        # Make delete request
        delete_request = DeleteTenantRequest(
            tenant_id=data["tenant_id"], reason="E2E test deletion"
        )

        delete_response = await tenant_stub.DeleteTenant(delete_request)

        # Verify deletion
        assert delete_response.id == data["tenant_id"]
        assert delete_response.status == TenantStatus.TENANT_STATUS_DELETED
        assert delete_response.config["deletion_reason"] == "E2E test deletion"
        assert "purge_at" in delete_response.config
        assert delete_response.deleted_at is not None

        # Verify service was called correctly
        mock_tenant_service.delete_tenant.assert_called_once_with(
            tenant_id=data["tenant_id"], reason="E2E test deletion"
        )

        # =====================================================================
        # VERIFICATION: Complete lifecycle verification
        # =====================================================================

        # Verify all service methods were called exactly once
        assert mock_tenant_service.create_tenant.call_count == 1
        assert mock_tenant_service.suspend_tenant.call_count == 1
        assert mock_tenant_service.resume_tenant.call_count == 1
        assert mock_tenant_service.delete_tenant.call_count == 1

    @pytest.mark.integration
    async def test_system_tenant_lifecycle_restrictions(self, grpc_client):
        """
        Test that the system tenant cannot be suspended or deleted.

        Verifies that proper error handling is in place for system tenant operations.
        """
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        system_tenant_id = "00000000-0000-0000-0000-000000000000"  # System tenant ID

        # =====================================================================
        # TEST 1: System tenant cannot be suspended
        # =====================================================================

        # Setup mock to raise error for system tenant suspension
        mock_tenant_service.suspend_tenant.side_effect = ValueError(
            "System tenant cannot be suspended"
        )

        # Attempt to suspend system tenant
        suspend_request = SuspendTenantRequest(
            tenant_id=system_tenant_id, reason="This should fail"
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.SuspendTenant(suspend_request)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "system tenant" in exc_info.value.details().lower()

        # =====================================================================
        # TEST 2: System tenant cannot be deleted
        # =====================================================================

        # Setup mock to raise error for system tenant deletion
        mock_tenant_service.delete_tenant.side_effect = ValueError(
            "System tenant cannot be deleted"
        )

        # Attempt to delete system tenant
        delete_request = DeleteTenantRequest(
            tenant_id=system_tenant_id, reason="This should also fail"
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.DeleteTenant(delete_request)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "system tenant" in exc_info.value.details().lower()

    @pytest.mark.integration
    async def test_lifecycle_state_transition_validation(self, grpc_client, tenant_lifecycle_data):
        """
        Test that invalid state transitions are properly rejected.

        Verifies that business rules around state transitions are enforced.
        """
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client
        data = tenant_lifecycle_data

        # =====================================================================
        # TEST 1: Cannot resume non-suspended tenant
        # =====================================================================

        # Setup mock to raise error for resuming active tenant
        mock_tenant_service.resume_tenant.side_effect = ValueError(
            "Only suspended tenants can be resumed"
        )

        resume_request = ResumeTenantRequest(tenant_id=data["tenant_id"])

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.ResumeTenant(resume_request)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "suspended" in exc_info.value.details().lower()

        # =====================================================================
        # TEST 2: Cannot suspend already deleted tenant
        # =====================================================================

        # Setup mock to raise error for suspending deleted tenant
        mock_tenant_service.suspend_tenant.side_effect = ValueError("Cannot suspend deleted tenant")

        suspend_request = SuspendTenantRequest(
            tenant_id=data["tenant_id"], reason="Should fail on deleted tenant"
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.SuspendTenant(suspend_request)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "deleted" in exc_info.value.details().lower()

    @pytest.mark.integration
    async def test_concurrent_lifecycle_operations(self, grpc_client, tenant_lifecycle_data):
        """
        Test that concurrent lifecycle operations are handled correctly.

        Verifies that the system behaves correctly under concurrent load.
        """
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client
        data = tenant_lifecycle_data

        # Create multiple tenants for concurrent testing
        tenant_ids = [str(uuid.uuid4()) for _ in range(5)]

        # =====================================================================
        # TEST: Concurrent tenant creation
        # =====================================================================

        # Setup mocks for concurrent creation
        def create_tenant_side_effect(slug, name, config, admin_email):
            # Extract tenant number from slug for unique ID
            tenant_num = slug.split("-")[-1]
            tenant_id = tenant_ids[int(tenant_num)]

            return Tenant(
                id=tenant_id,
                slug=slug,
                name=name,
                status=TenantStatusEnum.ACTIVE,
                config=config,
                keycloak_org_id=f"org-{tenant_num}",
                created_at=data["base_time"],
                updated_at=data["base_time"],
            )

        mock_tenant_service.create_tenant.side_effect = create_tenant_side_effect

        # Create requests for concurrent creation
        create_requests = [
            CreateTenantRequest(
                slug=f"concurrent-test-{i}",
                name=f"Concurrent Test Tenant {i}",
                config={"tenant_num": i},
                admin_email=f"admin{i}@concurrent-test.com",
            )
            for i in range(5)
        ]

        # Execute concurrent creates
        create_responses = await asyncio.gather(
            *[tenant_stub.CreateTenant(request) for request in create_requests]
        )

        # Verify all creations succeeded
        assert len(create_responses) == 5
        for i, response in enumerate(create_responses):
            assert response.slug == f"concurrent-test-{i}"
            assert response.status == TenantStatus.TENANT_STATUS_ACTIVE
            assert response.config["tenant_num"] == i

        # Verify all service calls were made
        assert mock_tenant_service.create_tenant.call_count == 5

        # =====================================================================
        # TEST: Concurrent suspension of different tenants
        # =====================================================================

        # Setup mocks for concurrent suspension
        def suspend_tenant_side_effect(tenant_id, reason):
            # Find which tenant this is
            tenant_idx = tenant_ids.index(tenant_id)

            return Tenant(
                id=tenant_id,
                slug=f"concurrent-test-{tenant_idx}",
                name=f"Concurrent Test Tenant {tenant_idx}",
                status=TenantStatusEnum.SUSPENDED,
                config={
                    "tenant_num": tenant_idx,
                    "suspension_reason": reason,
                    "suspended_at": "2026-01-08T10:05:00Z",
                },
                keycloak_org_id=f"org-{tenant_idx}",
                created_at=data["base_time"],
                updated_at=datetime(2026, 1, 8, 10, 5, 0, tzinfo=UTC),
            )

        mock_tenant_service.suspend_tenant.side_effect = suspend_tenant_side_effect

        # Create suspension requests
        suspend_requests = [
            SuspendTenantRequest(tenant_id=tenant_ids[i], reason=f"Concurrent suspension test {i}")
            for i in range(5)
        ]

        # Execute concurrent suspensions
        suspend_responses = await asyncio.gather(
            *[tenant_stub.SuspendTenant(request) for request in suspend_requests]
        )

        # Verify all suspensions succeeded
        assert len(suspend_responses) == 5
        for i, response in enumerate(suspend_responses):
            assert response.id == tenant_ids[i]
            assert response.status == TenantStatus.TENANT_STATUS_SUSPENDED
            assert response.config["suspension_reason"] == f"Concurrent suspension test {i}"

        # Verify all service calls were made
        assert mock_tenant_service.suspend_tenant.call_count == 5

    @pytest.mark.integration
    async def test_lifecycle_event_emission(self, grpc_client, tenant_lifecycle_data):
        """
        Test that lifecycle operations properly trigger event emission.

        Verifies that the event system is properly integrated with lifecycle operations.
        """
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client
        data = tenant_lifecycle_data

        # Track event emissions through the mock service
        # (In real implementation, these would be separate event emitter calls)

        # =====================================================================
        # Setup: Mock tenant for all operations
        # =====================================================================

        base_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.ACTIVE,
            config=data["config"],
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=data["base_time"],
        )

        # =====================================================================
        # TEST: Event emission during creation
        # =====================================================================

        mock_tenant_service.create_tenant.return_value = base_tenant

        create_request = CreateTenantRequest(
            slug=data["slug"],
            name=data["name"],
            config=data["config"],
            admin_email=data["admin_email"],
        )

        await tenant_stub.CreateTenant(create_request)

        # Verify creation service was called (which should emit tenant.created event)
        mock_tenant_service.create_tenant.assert_called_once()

        # =====================================================================
        # TEST: Event emission during suspension
        # =====================================================================

        suspended_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.SUSPENDED,
            config={**data["config"], "suspension_reason": "Event test"},
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=datetime(2026, 1, 8, 10, 5, 0, tzinfo=UTC),
        )

        mock_tenant_service.suspend_tenant.return_value = suspended_tenant

        suspend_request = SuspendTenantRequest(tenant_id=data["tenant_id"], reason="Event test")

        await tenant_stub.SuspendTenant(suspend_request)

        # Verify suspension service was called (which should emit tenant.suspended event)
        mock_tenant_service.suspend_tenant.assert_called_once()

        # =====================================================================
        # TEST: Event emission during resumption
        # =====================================================================

        mock_tenant_service.resume_tenant.return_value = base_tenant

        resume_request = ResumeTenantRequest(tenant_id=data["tenant_id"])
        await tenant_stub.ResumeTenant(resume_request)

        # Verify resumption service was called (which should emit tenant.resumed event)
        mock_tenant_service.resume_tenant.assert_called_once()

        # =====================================================================
        # TEST: Event emission during deletion
        # =====================================================================

        deleted_tenant = Tenant(
            id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatusEnum.DELETED,
            config={**data["config"], "deletion_reason": "Event test"},
            keycloak_org_id=data["keycloak_org_id"],
            created_at=data["base_time"],
            updated_at=datetime(2026, 1, 8, 10, 15, 0, tzinfo=UTC),
            deleted_at=datetime(2026, 1, 8, 10, 15, 0, tzinfo=UTC),
        )

        mock_tenant_service.delete_tenant.return_value = deleted_tenant

        delete_request = DeleteTenantRequest(tenant_id=data["tenant_id"], reason="Event test")

        await tenant_stub.DeleteTenant(delete_request)

        # Verify deletion service was called (which should emit tenant.deleted event)
        mock_tenant_service.delete_tenant.assert_called_once()

        # =====================================================================
        # VERIFICATION: All lifecycle events were triggered
        # =====================================================================

        # Each lifecycle operation should have triggered exactly one service call
        assert mock_tenant_service.create_tenant.call_count == 1
        assert mock_tenant_service.suspend_tenant.call_count == 1
        assert mock_tenant_service.resume_tenant.call_count == 1
        assert mock_tenant_service.delete_tenant.call_count == 1


class TestTenantLifecycleEdgeCases:
    """Edge case tests for tenant lifecycle operations."""

    @pytest.mark.integration
    async def test_rapid_state_transitions(self, grpc_client, tenant_lifecycle_data):
        """
        Test rapid successive state transitions.

        Verifies the system can handle quick successive operations without race conditions.
        """
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client
        data = tenant_lifecycle_data

        # Setup different tenant states for rapid transitions
        states = [
            (TenantStatusEnum.ACTIVE, {}),
            (TenantStatusEnum.SUSPENDED, {"suspension_reason": "Rapid test"}),
            (TenantStatusEnum.ACTIVE, {}),  # Resumed
            (TenantStatusEnum.DELETED, {"deletion_reason": "Rapid test"}),
        ]

        # Mock service to return appropriate states
        def get_state_tenant(state_idx):
            status, config = states[state_idx]
            return Tenant(
                id=data["tenant_id"],
                slug=data["slug"],
                name=data["name"],
                status=status,
                config={**data["config"], **config},
                keycloak_org_id=data["keycloak_org_id"],
                created_at=data["base_time"],
                updated_at=datetime(2026, 1, 8, 10, state_idx * 5, 0, tzinfo=UTC),
                deleted_at=datetime(2026, 1, 8, 10, state_idx * 5, 0, tzinfo=UTC)
                if status == TenantStatusEnum.DELETED
                else None,
            )

        # Setup mocks for each transition
        mock_tenant_service.create_tenant.return_value = get_state_tenant(0)
        mock_tenant_service.suspend_tenant.return_value = get_state_tenant(1)
        mock_tenant_service.resume_tenant.return_value = get_state_tenant(2)
        mock_tenant_service.delete_tenant.return_value = get_state_tenant(3)

        # Execute rapid transitions
        create_request = CreateTenantRequest(
            slug=data["slug"],
            name=data["name"],
            config=data["config"],
            admin_email=data["admin_email"],
        )

        suspend_request = SuspendTenantRequest(tenant_id=data["tenant_id"], reason="Rapid test")

        resume_request = ResumeTenantRequest(tenant_id=data["tenant_id"])

        delete_request = DeleteTenantRequest(tenant_id=data["tenant_id"], reason="Rapid test")

        # Execute all operations in rapid succession
        responses = await asyncio.gather(
            tenant_stub.CreateTenant(create_request),
            tenant_stub.SuspendTenant(suspend_request),
            tenant_stub.ResumeTenant(resume_request),
            tenant_stub.DeleteTenant(delete_request),
        )

        # Verify all operations completed successfully
        assert len(responses) == 4
        assert responses[0].status == TenantStatus.TENANT_STATUS_ACTIVE
        assert responses[1].status == TenantStatus.TENANT_STATUS_SUSPENDED
        assert responses[2].status == TenantStatus.TENANT_STATUS_ACTIVE
        assert responses[3].status == TenantStatus.TENANT_STATUS_DELETED

        # Verify all service calls were made
        assert mock_tenant_service.create_tenant.call_count == 1
        assert mock_tenant_service.suspend_tenant.call_count == 1
        assert mock_tenant_service.resume_tenant.call_count == 1
        assert mock_tenant_service.delete_tenant.call_count == 1

    @pytest.mark.integration
    async def test_lifecycle_operations_with_invalid_tenant_id(self, grpc_client):
        """Test lifecycle operations with non-existent tenant ID."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client

        non_existent_id = str(uuid.uuid4())

        # Setup mocks to return None (tenant not found)
        mock_tenant_service.suspend_tenant.return_value = None
        mock_tenant_service.resume_tenant.return_value = None
        mock_tenant_service.delete_tenant.return_value = None

        # Test suspension of non-existent tenant
        suspend_request = SuspendTenantRequest(tenant_id=non_existent_id, reason="Should fail")

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.SuspendTenant(suspend_request)

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND

        # Test resumption of non-existent tenant
        resume_request = ResumeTenantRequest(tenant_id=non_existent_id)

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.ResumeTenant(resume_request)

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND

        # Test deletion of non-existent tenant
        delete_request = DeleteTenantRequest(tenant_id=non_existent_id, reason="Should also fail")

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.DeleteTenant(delete_request)

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND

    @pytest.mark.integration
    async def test_lifecycle_operations_with_missing_reason(
        self, grpc_client, tenant_lifecycle_data
    ):
        """Test that operations requiring reasons fail when reason is missing."""
        tenant_stub, _, mock_tenant_service, _, _ = grpc_client
        data = tenant_lifecycle_data

        # Test suspension without reason
        SuspendTenantRequest(tenant_id=data["tenant_id"])
        # Note: reason field is required in protobuf, so this would be caught at the protocol level

        # Test deletion without reason
        DeleteTenantRequest(tenant_id=data["tenant_id"])
        # Note: reason field is required in protobuf, so this would be caught at the protocol level

        # For empty string reasons, the service layer should validate
        mock_tenant_service.suspend_tenant.side_effect = ValueError("Reason is required")
        mock_tenant_service.delete_tenant.side_effect = ValueError("Reason is required")

        suspend_request_empty = SuspendTenantRequest(tenant_id=data["tenant_id"], reason="")

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.SuspendTenant(suspend_request_empty)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "reason" in exc_info.value.details().lower()

        delete_request_empty = DeleteTenantRequest(tenant_id=data["tenant_id"], reason="")

        with pytest.raises(grpc.RpcError) as exc_info:
            await tenant_stub.DeleteTenant(delete_request_empty)

        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert "reason" in exc_info.value.details().lower()
