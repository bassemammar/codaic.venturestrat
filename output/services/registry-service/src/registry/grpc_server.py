"""gRPC server setup for Registry Service tenant management.

This module provides gRPC server initialization and lifecycle management
for the tenant service APIs.
"""
from __future__ import annotations

import asyncio
from typing import Any

import grpc
import structlog

from registry.api.tenant_grpc_service import TenantGrpcService, TenantHealthService
from registry.export_service import TenantExportService
from registry.grpc.tenant_pb2_grpc import (
    add_HealthServicer_to_server,
    add_TenantServiceServicer_to_server,
)
from registry.tenant_service import TenantService

logger = structlog.get_logger(__name__)


class TenantGrpcServer:
    """gRPC server for tenant management APIs.

    Manages the gRPC server lifecycle and service registration for
    tenant CRUD operations, status management, and data export.
    """

    def __init__(
        self,
        tenant_service: TenantService,
        export_service: TenantExportService | None = None,
        quota_service: Any = None,
        port: int = 50052,
        max_workers: int = 10,
        max_receive_message_length: int = 4 * 1024 * 1024,  # 4MB
        max_send_message_length: int = 4 * 1024 * 1024,  # 4MB
    ):
        """Initialize gRPC server.

        Args:
            tenant_service: Core tenant service instance
            export_service: Optional export service for data export operations
            quota_service: Optional quota service for quota management
            port: Port to listen on (default: 50052)
            max_workers: Maximum number of worker threads
            max_receive_message_length: Maximum message size for receiving
            max_send_message_length: Maximum message size for sending
        """
        self.tenant_service = tenant_service
        self.export_service = export_service
        self.quota_service = quota_service
        self.port = port

        # Create gRPC server with options
        self.server = grpc.aio.server(
            options=[
                ("grpc.keepalive_time_ms", 30000),  # Send keepalive every 30 seconds
                ("grpc.keepalive_timeout_ms", 10000),  # Wait 10 seconds for keepalive response
                ("grpc.keepalive_permit_without_calls", True),
                ("grpc.http2.max_pings_without_data", 0),
                ("grpc.http2.min_time_between_pings_ms", 10000),
                ("grpc.http2.min_ping_interval_without_data_ms", 5000),
                ("grpc.max_receive_message_length", max_receive_message_length),
                ("grpc.max_send_message_length", max_send_message_length),
            ]
        )

        # Initialize service handlers
        self.tenant_grpc_service = TenantGrpcService(
            tenant_service=tenant_service,
            export_service=export_service,
            quota_service=quota_service,
        )
        self.health_service = TenantHealthService(tenant_service=tenant_service)

        # Register services
        add_TenantServiceServicer_to_server(self.tenant_grpc_service, self.server)
        add_HealthServicer_to_server(self.health_service, self.server)

        # Add server port
        self.server.add_insecure_port(f"[::]:{port}")

        logger.info(
            "grpc_server_initialized",
            port=port,
            max_workers=max_workers,
            max_receive_message_length=max_receive_message_length,
            max_send_message_length=max_send_message_length,
        )

    async def start(self) -> None:
        """Start the gRPC server.

        Raises:
            RuntimeError: If server fails to start
        """
        try:
            await self.server.start()
            logger.info("grpc_server_started", port=self.port)

            # Log available services
            logger.info(
                "grpc_services_registered",
                services=[
                    "venturestrat.registry.v1.TenantService",
                    "venturestrat.registry.v1.Health",
                ],
                port=self.port,
            )

        except Exception as e:
            logger.error("grpc_server_start_failed", port=self.port, error=str(e))
            raise RuntimeError(f"Failed to start gRPC server on port {self.port}: {e}") from e

    async def stop(self, grace_period: float = 5.0) -> None:
        """Stop the gRPC server gracefully.

        Args:
            grace_period: Time to wait for graceful shutdown in seconds
        """
        try:
            logger.info("grpc_server_stopping", port=self.port, grace_period=grace_period)

            # Stop accepting new requests and wait for existing ones to complete
            await self.server.stop(grace_period)

            logger.info("grpc_server_stopped", port=self.port)

        except Exception as e:
            logger.error("grpc_server_stop_failed", port=self.port, error=str(e))
            # Force stop if graceful stop fails
            await self.server.stop(0)

    async def wait_for_termination(self) -> None:
        """Wait for the server to terminate.

        This method blocks until the server is stopped.
        """
        await self.server.wait_for_termination()

    def get_port(self) -> int:
        """Get the server port.

        Returns:
            The port number the server is listening on
        """
        return self.port


async def serve_tenant_grpc(
    tenant_service: TenantService,
    export_service: TenantExportService | None = None,
    quota_service: Any = None,
    port: int = 50052,
) -> TenantGrpcServer:
    """Start a gRPC server for tenant management.

    This is a convenience function that creates and starts a TenantGrpcServer.

    Args:
        tenant_service: Core tenant service instance
        export_service: Optional export service for data export operations
        quota_service: Optional quota service for quota management
        port: Port to listen on (default: 50052)

    Returns:
        Running TenantGrpcServer instance

    Raises:
        RuntimeError: If server fails to start
    """
    server = TenantGrpcServer(
        tenant_service=tenant_service,
        export_service=export_service,
        quota_service=quota_service,
        port=port,
    )

    await server.start()
    return server


async def main():
    """Main entry point for running the gRPC server standalone.

    This is useful for development and testing. In production,
    the gRPC server should be started as part of the main application.
    """
    from registry.config import settings

    # Initialize tenant service
    tenant_service = TenantService()

    try:
        # Initialize tenant service
        await tenant_service.initialize()
        logger.info("tenant_service_initialized")

        # Start gRPC server
        server = await serve_tenant_grpc(
            tenant_service=tenant_service,
            port=settings.grpc_port if hasattr(settings, "grpc_port") else 50052,
        )

        logger.info("grpc_server_running", port=server.get_port())

        # Wait for termination
        try:
            await server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("grpc_server_interrupted")

        # Graceful shutdown
        await server.stop()

    except Exception as e:
        logger.exception("grpc_server_main_error", error=str(e))
        raise

    finally:
        # Clean up tenant service
        try:
            await tenant_service.close()
            logger.info("tenant_service_closed")
        except Exception as e:
            logger.error("tenant_service_close_error", error=str(e))


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("grpc_server_shutdown_by_interrupt")
    except Exception as e:
        logger.exception("grpc_server_failed", error=str(e))
        exit(1)
