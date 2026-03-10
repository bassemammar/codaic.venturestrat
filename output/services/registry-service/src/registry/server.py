"""Combined gRPC server for Registry and Tenant services.

This module provides a unified gRPC server that hosts both the Registry
service and the Tenant service on the same port for optimal resource usage.
"""

import asyncio
import logging
import signal
from typing import Optional

import grpc

from registry.api.grpc_service import RegistryGrpcService
from registry.api.tenant_grpc_service import TenantGrpcService
from registry.config import settings
from registry.grpc import (
    add_RegistryServiceServicer_to_server,
    add_TenantServiceServicer_to_server,
)
from registry.service import RegistryService
from registry.tenant_service import TenantService


logger = logging.getLogger(__name__)


class CombinedGrpcServer:
    """Combined gRPC server for Registry and Tenant services."""

    def __init__(
        self,
        registry_service: RegistryService,
        tenant_service: TenantService,
        port: int = 50051
    ):
        """Initialize the combined gRPC server.

        Args:
            registry_service: The core registry service instance.
            tenant_service: The core tenant service instance.
            port: Port to listen on.
        """
        self.registry_service = registry_service
        self.tenant_service = tenant_service
        self.port = port
        self.server: Optional[grpc.aio.Server] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the combined gRPC server."""
        try:
            # Initialize services
            await self.tenant_service.initialize()
            logger.info("Tenant service initialized")

            # Create gRPC server
            self.server = grpc.aio.server()

            # Add Registry service
            registry_grpc = RegistryGrpcService(self.registry_service)
            add_RegistryServiceServicer_to_server(registry_grpc, self.server)
            logger.info("Registry gRPC service added to server")

            # Add Tenant service
            tenant_grpc = TenantGrpcService(self.tenant_service)
            add_TenantServiceServicer_to_server(tenant_grpc, self.server)
            logger.info("Tenant gRPC service added to server")

            # Start server
            listen_addr = f"[::]:{self.port}"
            self.server.add_insecure_port(listen_addr)
            await self.server.start()

            logger.info(
                f"Combined gRPC server started on port {self.port} "
                f"with Registry and Tenant services"
            )

        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the combined gRPC server."""
        if self.server:
            logger.info("Stopping gRPC server...")
            await self.server.stop(5)  # 5 second grace period
            logger.info("gRPC server stopped")

        # Close tenant service
        await self.tenant_service.close()
        logger.info("Tenant service closed")

        self._shutdown_event.set()

    async def wait_for_termination(self) -> None:
        """Wait for server termination."""
        if self.server:
            await self.server.wait_for_termination()

    async def run_until_shutdown(self) -> None:
        """Run server until shutdown signal is received."""
        # Setup signal handlers
        loop = asyncio.get_running_loop()

        def signal_handler():
            logger.info("Received shutdown signal")
            asyncio.create_task(self.stop())

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Wait for shutdown
        await self._shutdown_event.wait()


async def serve_combined(
    registry_service: RegistryService,
    tenant_service: TenantService,
    port: int = 50051,
) -> CombinedGrpcServer:
    """Start the combined gRPC server.

    Args:
        registry_service: The core registry service.
        tenant_service: The core tenant service.
        port: Port to listen on.

    Returns:
        The running combined gRPC server.
    """
    server = CombinedGrpcServer(registry_service, tenant_service, port)
    await server.start()
    return server


async def main():
    """Main entry point for the gRPC server."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting Registry gRPC server...")

    try:
        # Initialize services
        registry_service = RegistryService(
            consul_host=settings.consul_host,
            consul_port=settings.consul_port
        )

        tenant_service = TenantService(
            database_url=settings.database_url
        )

        # Start server
        server = await serve_combined(
            registry_service,
            tenant_service,
            port=settings.grpc_port
        )

        logger.info("Server started successfully")

        # Run until shutdown
        await server.run_until_shutdown()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())