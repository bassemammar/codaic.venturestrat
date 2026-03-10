"""Asynchronous usage example for registry-service SDK.

This example demonstrates asynchronous usage of the registry-service client.
"""

import asyncio
import os

from venturestrat_registry_service import (
    AsyncRegistryServiceClient,
    RegistryServiceConfig,
)
from venturestrat_registry_service.auth import ApiKeyAuthProvider


async def test_client(name: str, client: AsyncRegistryServiceClient) -> None:
    """Test an async client instance.

    Args:
        name: Client description
        client: Client to test
    """

    try:
        async with client:
            # Health check
            await client.health_check()

            # Example async service calls would go here
            # response = await client.some_async_method(request)

    except Exception:
        pass


async def main() -> None:
    """Main async example function."""

    # Method 1: Direct client creation
    client = AsyncRegistryServiceClient(
        host=os.getenv("REGISTRY_SERVICE_HOST", "localhost"),
        port=int(os.getenv("REGISTRY_SERVICE_PORT", "50051")),
        timeout=30.0,
    )

    # Method 2: Using configuration
    config = RegistryServiceConfig.from_env()
    client_from_config = AsyncRegistryServiceClient.from_config(config)

    # Method 3: With authentication
    api_key = os.getenv("REGISTRY_SERVICE_API_KEY")
    if api_key:
        auth = ApiKeyAuthProvider(api_key)
        auth_client = AsyncRegistryServiceClient(
            host="api.example.com", port=443, secure=True, auth=auth
        )
    else:
        auth_client = None

    # Test clients
    clients_to_test = [
        ("Direct async client", client),
        ("Config async client", client_from_config),
    ]

    if auth_client:
        clients_to_test.append(("Auth async client", auth_client))

    # Test all clients
    tasks = []
    for name, test_client in clients_to_test:
        tasks.append(test_client(name, test_client))

    # Run tests concurrently
    await asyncio.gather(*tasks, return_exceptions=True)

    # Example of sequential async calls
    try:
        async with client as c:
            # Multiple sequential calls
            for _i in range(3):
                await c.health_check()
                await asyncio.sleep(0.1)  # Small delay

    except Exception:
        pass


def run_example() -> None:
    """Run the async example."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    run_example()
