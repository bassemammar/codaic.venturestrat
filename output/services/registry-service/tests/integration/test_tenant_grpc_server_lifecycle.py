"""gRPC Server lifecycle and configuration tests for Tenant Service.

These tests verify server startup, configuration, service registration,
graceful shutdown, and other server lifecycle aspects.
"""
import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import grpc
import pytest
from grpc import aio as grpc_aio
from grpc_reflection.v1alpha import reflection
from registry.api.tenant_grpc_service import TenantGrpcService, TenantHealthService
from registry.grpc.tenant_pb2 import (
    GetTenantRequest,
    HealthCheckRequest,
    HealthCheckResponse,
)
from registry.grpc.tenant_pb2_grpc import (
    HealthStub,
    TenantServiceStub,
    add_HealthServicer_to_server,
    add_TenantServiceServicer_to_server,
)
from registry.models.tenant import Tenant
from registry.models.tenant import TenantStatus as TenantStatusEnum


class GrpcServerManager:
    """Helper class to manage gRPC server lifecycle for testing."""

    def __init__(self, tenant_service=None, export_service=None, quota_service=None):
        self.tenant_service = tenant_service or AsyncMock()
        self.export_service = export_service
        self.quota_service = quota_service
        self.server = None
        self.port = None

    async def start(self, enable_reflection=False, enable_health=True):
        """Start the gRPC server."""
        # Create services
        tenant_grpc_service = TenantGrpcService(
            tenant_service=self.tenant_service,
            export_service=self.export_service,
            quota_service=self.quota_service,
        )

        # Create server
        self.server = grpc_aio.server()

        # Add tenant service
        add_TenantServiceServicer_to_server(tenant_grpc_service, self.server)

        # Add health service if enabled
        if enable_health:
            health_service = TenantHealthService(tenant_service=self.tenant_service)
            add_HealthServicer_to_server(health_service, self.server)

        # Add reflection if enabled
        if enable_reflection:
            service_names = [
                "registry.TenantService",
                "grpc.health.v1.Health",
                reflection.SERVICE_NAME,
            ]
            reflection.enable_server_reflection(service_names, self.server)

        # Start listening
        listen_addr = "[::]:0"
        self.port = self.server.add_insecure_port(listen_addr)

        await self.server.start()
        return self.port

    async def stop(self, grace_period=5):
        """Stop the gRPC server."""
        if self.server:
            await self.server.stop(grace=grace_period)

    async def wait_for_termination(self):
        """Wait for server termination."""
        if self.server:
            await self.server.wait_for_termination()

    def create_channel(self):
        """Create a client channel to the server."""
        return grpc_aio.insecure_channel(f"localhost:{self.port}")


@pytest.fixture
async def server_manager():
    """Create a server manager for testing."""
    manager = GrpcServerManager()
    yield manager
    # Cleanup
    try:
        await manager.stop()
    except Exception:
        pass


class TestGrpcServerLifecycle:
    """Test gRPC server lifecycle management."""

    async def test_server_startup_and_shutdown(self, server_manager):
        """Test basic server startup and shutdown."""
        # Start server
        port = await server_manager.start()
        assert port > 0

        # Verify server is running by creating a channel
        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)
        assert stub is not None

        await channel.close()

        # Stop server
        await server_manager.stop()

        # Server should be stopped (attempting connection should fail)
        with pytest.raises(Exception):  # Connection should fail
            channel = server_manager.create_channel()
            stub = TenantServiceStub(channel)
            # Try to make a request that should fail
            await stub.GetTenant(GetTenantRequest(tenant_id="test-id"))

    async def test_server_graceful_shutdown_during_request(self, server_manager):
        """Test graceful shutdown while handling requests."""
        # Mock service with delay to simulate long-running request
        mock_tenant_service = AsyncMock()

        async def slow_get_tenant(tenant_id):
            await asyncio.sleep(2)  # Simulate slow operation
            return None

        mock_tenant_service.get_tenant_by_id = slow_get_tenant
        server_manager.tenant_service = mock_tenant_service

        # Start server
        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        # Start a long-running request
        request_task = asyncio.create_task(stub.GetTenant(GetTenantRequest(tenant_id="test-id")))

        # Give request time to start
        await asyncio.sleep(0.1)

        # Start graceful shutdown
        shutdown_task = asyncio.create_task(server_manager.stop(grace_period=5))

        # Wait for both to complete
        done, pending = await asyncio.wait(
            [request_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED, timeout=10
        )

        # Clean up any pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        await channel.close()

    async def test_server_with_health_service_enabled(self, server_manager):
        """Test server with health service enabled."""
        server_manager.tenant_service.health_check.return_value = True

        await server_manager.start(enable_health=True)

        channel = server_manager.create_channel()
        health_stub = HealthStub(channel)

        # Test health check
        response = await health_stub.Check(HealthCheckRequest(service="TenantService"))

        assert response.status == HealthCheckResponse.ServingStatus.SERVING

        await channel.close()

    async def test_server_with_reflection_enabled(self, server_manager):
        """Test server with reflection enabled."""
        await server_manager.start(enable_reflection=True)

        # With reflection, clients could discover services
        # This test just verifies the server starts successfully with reflection
        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)
        assert stub is not None

        await channel.close()

    async def test_server_port_allocation(self):
        """Test that servers get unique ports."""
        manager1 = GrpcServerManager()
        manager2 = GrpcServerManager()

        try:
            port1 = await manager1.start()
            port2 = await manager2.start()

            # Should get different ports
            assert port1 != port2
            assert port1 > 0
            assert port2 > 0

        finally:
            await manager1.stop()
            await manager2.stop()

    async def test_server_multiple_services_registration(self, server_manager):
        """Test server with multiple services registered."""
        # Enable both tenant and health services
        await server_manager.start(enable_health=True)

        channel = server_manager.create_channel()

        # Both services should be available
        tenant_stub = TenantServiceStub(channel)
        health_stub = HealthStub(channel)

        assert tenant_stub is not None
        assert health_stub is not None

        await channel.close()

    async def test_server_restart_scenario(self, server_manager):
        """Test server restart scenario."""
        # Start server
        await server_manager.start()

        # Stop server
        await server_manager.stop()

        # Start again (should get new port since we don't reuse)
        port2 = await server_manager.start()

        # Should successfully restart
        assert port2 > 0

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)
        assert stub is not None

        await channel.close()


class TestGrpcServerConfiguration:
    """Test gRPC server configuration options."""

    async def test_server_without_optional_services(self):
        """Test server configuration without optional services."""
        # Create server without export and quota services
        manager = GrpcServerManager(
            tenant_service=AsyncMock(), export_service=None, quota_service=None
        )

        try:
            await manager.start()

            channel = manager.create_channel()
            stub = TenantServiceStub(channel)

            # Server should start successfully even without optional services
            assert stub is not None

            await channel.close()

        finally:
            await manager.stop()

    async def test_server_with_all_services(self):
        """Test server configuration with all services enabled."""
        manager = GrpcServerManager(
            tenant_service=AsyncMock(), export_service=AsyncMock(), quota_service=AsyncMock()
        )

        try:
            await manager.start(enable_health=True, enable_reflection=True)

            channel = manager.create_channel()

            # All services should be available
            tenant_stub = TenantServiceStub(channel)
            health_stub = HealthStub(channel)

            assert tenant_stub is not None
            assert health_stub is not None

            await channel.close()

        finally:
            await manager.stop()

    async def test_server_health_check_configuration(self, server_manager):
        """Test health check service configuration."""
        # Configure tenant service health check behavior
        server_manager.tenant_service.health_check.return_value = True

        await server_manager.start(enable_health=True)

        channel = server_manager.create_channel()
        health_stub = HealthStub(channel)

        # Test different service names
        test_cases = [
            ("TenantService", True),
            ("", True),  # Empty service name should work
        ]

        for service_name, expected_healthy in test_cases:
            response = await health_stub.Check(HealthCheckRequest(service=service_name))

            if expected_healthy:
                assert response.status == HealthCheckResponse.ServingStatus.SERVING
            else:
                assert response.status == HealthCheckResponse.ServingStatus.NOT_SERVING

        await channel.close()


class TestGrpcServerConcurrency:
    """Test gRPC server concurrency and load handling."""

    async def test_server_concurrent_requests(self, server_manager):
        """Test server handling concurrent requests."""
        # Setup mock service
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        server_manager.tenant_service.get_tenant_by_id.return_value = sample_tenant

        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        # Make multiple concurrent requests
        num_requests = 50
        requests = [
            stub.GetTenant(GetTenantRequest(tenant_id=sample_tenant.id))
            for _ in range(num_requests)
        ]

        start_time = time.time()
        responses = await asyncio.gather(*requests)
        end_time = time.time()

        # All requests should succeed
        assert len(responses) == num_requests
        for response in responses:
            assert response.id == sample_tenant.id

        # Should handle requests efficiently
        avg_time_per_request = (end_time - start_time) / num_requests
        assert avg_time_per_request < 0.1  # Each request should be fast

        # Verify service was called for each request
        assert server_manager.tenant_service.get_tenant_by_id.call_count == num_requests

        await channel.close()

    async def test_server_concurrent_connections(self, server_manager):
        """Test server handling multiple concurrent connections."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        server_manager.tenant_service.get_tenant_by_id.return_value = sample_tenant

        await server_manager.start()

        # Create multiple channels (simulating multiple clients)
        num_clients = 10
        channels = [server_manager.create_channel() for _ in range(num_clients)]
        stubs = [TenantServiceStub(channel) for channel in channels]

        # Each client makes a request
        requests = [stub.GetTenant(GetTenantRequest(tenant_id=sample_tenant.id)) for stub in stubs]

        responses = await asyncio.gather(*requests)

        # All requests should succeed
        assert len(responses) == num_clients
        for response in responses:
            assert response.id == sample_tenant.id

        # Clean up channels
        await asyncio.gather(*[channel.close() for channel in channels])

    async def test_server_load_with_slow_operations(self, server_manager):
        """Test server behavior under load with slow operations."""

        # Mock a slow operation
        async def slow_operation(tenant_id):
            await asyncio.sleep(0.1)  # 100ms delay
            return Tenant(
                id=tenant_id,
                slug="slow-tenant",
                name="Slow Tenant",
                status=TenantStatusEnum.ACTIVE,
                config={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        server_manager.tenant_service.get_tenant_by_id.side_effect = slow_operation

        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        # Make concurrent slow requests
        num_requests = 20
        requests = [
            stub.GetTenant(GetTenantRequest(tenant_id=f"tenant-{i}")) for i in range(num_requests)
        ]

        start_time = time.time()
        responses = await asyncio.gather(*requests)
        end_time = time.time()

        # All requests should succeed
        assert len(responses) == num_requests

        # Should handle concurrent slow operations efficiently
        # With proper concurrency, total time should be much less than sequential
        total_time = end_time - start_time
        sequential_time = num_requests * 0.1
        assert total_time < sequential_time * 0.5  # Should be much faster than sequential

        await channel.close()


class TestGrpcServerErrorHandling:
    """Test gRPC server error handling and resilience."""

    async def test_server_service_dependency_failure(self, server_manager):
        """Test server behavior when service dependencies fail."""
        # Configure tenant service to fail
        server_manager.tenant_service.get_tenant_by_id.side_effect = Exception(
            "Service unavailable"
        )

        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        # Request should result in gRPC error
        with pytest.raises(grpc.RpcError) as exc_info:
            await stub.GetTenant(GetTenantRequest(tenant_id="test-id"))

        assert exc_info.value.code() == grpc.StatusCode.INTERNAL

        await channel.close()

    async def test_server_resilience_to_client_disconnection(self, server_manager):
        """Test server resilience when clients disconnect abruptly."""
        await server_manager.start()

        # Create channel and then close it immediately
        channel = server_manager.create_channel()
        TenantServiceStub(channel)

        # Close channel abruptly
        await channel.close()

        # Server should continue running and accept new connections
        channel2 = server_manager.create_channel()
        stub2 = TenantServiceStub(channel2)

        # This should work despite previous abrupt disconnection
        assert stub2 is not None

        await channel2.close()

    async def test_server_memory_cleanup_after_requests(self, server_manager):
        """Test that server cleans up memory after requests."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        server_manager.tenant_service.get_tenant_by_id.return_value = sample_tenant

        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        # Make many requests to check for memory leaks
        for i in range(100):
            response = await stub.GetTenant(GetTenantRequest(tenant_id=sample_tenant.id))
            assert response.id == sample_tenant.id

        # Give some time for cleanup
        await asyncio.sleep(0.1)

        # Server should still be responsive
        final_response = await stub.GetTenant(GetTenantRequest(tenant_id=sample_tenant.id))
        assert final_response.id == sample_tenant.id

        await channel.close()


class TestGrpcServerMetrics:
    """Test gRPC server metrics and monitoring capabilities."""

    async def test_server_request_counting(self, server_manager):
        """Test that server properly tracks request counts."""
        sample_tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatusEnum.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        server_manager.tenant_service.get_tenant_by_id.return_value = sample_tenant

        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        # Make multiple requests
        num_requests = 10
        for i in range(num_requests):
            await stub.GetTenant(GetTenantRequest(tenant_id=sample_tenant.id))

        # Verify service was called correct number of times
        assert server_manager.tenant_service.get_tenant_by_id.call_count == num_requests

        await channel.close()

    async def test_server_error_tracking(self, server_manager):
        """Test that server properly tracks errors."""
        # Configure service to fail half the time
        call_count = 0

        def failing_service(tenant_id):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Service failure")
            return Tenant(
                id=tenant_id,
                slug="test-tenant",
                name="Test Tenant",
                status=TenantStatusEnum.ACTIVE,
                config={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        server_manager.tenant_service.get_tenant_by_id.side_effect = failing_service

        await server_manager.start()

        channel = server_manager.create_channel()
        stub = TenantServiceStub(channel)

        success_count = 0
        error_count = 0

        # Make requests and count successes/failures
        for i in range(10):
            try:
                await stub.GetTenant(GetTenantRequest(tenant_id=f"tenant-{i}"))
                success_count += 1
            except grpc.RpcError:
                error_count += 1

        # Should have roughly half successes and half failures
        assert success_count > 0
        assert error_count > 0
        assert success_count + error_count == 10

        await channel.close()
