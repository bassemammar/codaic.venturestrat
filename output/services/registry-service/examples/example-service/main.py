#!/usr/bin/env python3
"""Example Service - Demonstrating VentureStrat Registry SDK Usage.

This example shows how to use the venturestrat-registry SDK to:
1. Register a service on startup
2. Discover dependencies
3. Handle graceful shutdown

Run with:
    python main.py
"""
import asyncio
import logging
import os
import signal
import socket

# Import the SDK (install with: pip install venturestrat-registry)
# For development, add the SDK to your PYTHONPATH
import sys
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sdk"))

from venturestrat_registry import (
    RegistryClient,
    RegistryClientConfig,
    ServiceInstance,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("example-service")

# FastAPI app
app = FastAPI(
    title="Example Service",
    description="Example service demonstrating registry SDK",
    version="1.0.0",
)

# Global registry client (set in lifespan)
registry_client: RegistryClient | None = None
market_data_instances: list[ServiceInstance] = []


@app.get("/health/live")
async def liveness():
    """Liveness probe - returns if the service is running."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    """Readiness probe - returns if the service can handle requests."""
    # Check if we've discovered our dependencies
    if not market_data_instances:
        return {"status": "not_ready", "reason": "waiting for dependencies"}
    return {"status": "ready"}


@app.get("/api/v1/example/dependencies")
async def get_dependencies():
    """Return discovered dependencies."""
    return {
        "market_data_service": [
            {
                "instance_id": inst.instance_id,
                "endpoint": inst.endpoint,
                "version": inst.version,
                "healthy": inst.is_healthy,
            }
            for inst in market_data_instances
        ]
    }


async def discover_dependencies(client: RegistryClient) -> None:
    """Discover service dependencies periodically."""
    global market_data_instances

    while True:
        try:
            instances = await client.discover(
                "market-data-service",
                version="^1.0.0",
                healthy_only=True,
            )
            market_data_instances = instances
            logger.info(f"Discovered {len(instances)} market-data-service instances")
        except Exception as e:
            logger.warning(f"Failed to discover market-data-service: {e}")

        # Refresh every 30 seconds
        await asyncio.sleep(30)


async def main():
    """Main entry point with auto-registration."""
    global registry_client

    # Generate unique instance ID
    hostname = socket.gethostname()
    instance_id = f"example-service-{hostname}-{uuid.uuid4().hex[:8]}"

    # Get service address and port
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", "8000"))

    # Configure registry client (supports both direct and gateway modes)
    config = RegistryClientConfig.from_env()

    # Manifest path
    manifest_path = Path(__file__).parent / "manifest.yaml"

    logger.info(f"Starting example-service (id={instance_id})")
    if config.use_gateway:
        logger.info(f"Using API Gateway mode - Registry URL: {config.base_url}")
    else:
        logger.info(f"Using direct mode - Registering with registry at {config.host}:{config.port}")

    # Use context manager for auto-registration/deregistration
    async with RegistryClient.from_manifest(
        manifest_path=manifest_path,
        instance_id=instance_id,
        address=host,
        port=port,
        config=config,
    ) as client:
        registry_client = client

        logger.info("Service registered successfully!")

        # Start background discovery task
        discovery_task = asyncio.create_task(discover_dependencies(client))

        # Run the FastAPI server
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        # Handle shutdown signals
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server)))

        try:
            await server.serve()
        finally:
            discovery_task.cancel()
            try:
                await discovery_task
            except asyncio.CancelledError:
                pass

    # Context manager will auto-deregister on exit
    logger.info("Service deregistered and shutdown complete")


async def shutdown(server: uvicorn.Server) -> None:
    """Graceful shutdown handler."""
    logger.info("Shutdown signal received, stopping...")
    server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
