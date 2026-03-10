"""VentureStrat Registry SDK.

A Python client library for interacting with the VentureStrat Registry Service.

Usage:
    from venturestrat_registry import RegistryClient

    # Create client
    async with RegistryClient(host="registry-service", port=8080) as client:
        # Register service
        await client.register_from_manifest("manifest.yaml")

        # Discover services
        instances = await client.discover("market-data-service", version="^1.0.0")

        # Watch for changes
        async for event in client.watch("market-data-service"):
            print(f"Event: {event.type}")
"""

from venturestrat_registry.client import (
    ConnectionError,
    DiscoveryError,
    RegistrationError,
    RegistryClient,
    RegistryClientConfig,
    RegistryError,
    ServiceEvent,
    ServiceInstance,
    ServiceRegistration,
)
from venturestrat_registry.manifest import ManifestLoader

__version__ = "0.1.0"

__all__ = [
    # Client
    "RegistryClient",
    "RegistryClientConfig",
    # Models
    "ServiceRegistration",
    "ServiceInstance",
    "ServiceEvent",
    # Errors
    "RegistryError",
    "ConnectionError",
    "RegistrationError",
    "DiscoveryError",
    # Utilities
    "ManifestLoader",
]
