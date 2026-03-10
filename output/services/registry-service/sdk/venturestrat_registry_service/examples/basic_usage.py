"""Basic usage example for registry-service SDK.

This example demonstrates basic synchronous usage of the registry-service client.
"""

import os

from venturestrat_registry_service import RegistryServiceClient, RegistryServiceConfig
from venturestrat_registry_service.auth import ApiKeyAuthProvider


def main() -> None:
    """Main example function."""

    # Method 1: Direct client creation
    client = RegistryServiceClient(
        host=os.getenv("REGISTRY_SERVICE_HOST", "localhost"),
        port=int(os.getenv("REGISTRY_SERVICE_PORT", "50051")),
        timeout=30.0,
    )

    # Method 2: Using configuration
    config = RegistryServiceConfig.from_env()
    client_from_config = RegistryServiceClient.from_config(config)

    # Method 3: With authentication
    api_key = os.getenv("REGISTRY_SERVICE_API_KEY")
    if api_key:
        auth = ApiKeyAuthProvider(api_key)
        auth_client = RegistryServiceClient(
            host="api.example.com", port=443, secure=True, auth=auth
        )
    else:
        auth_client = None

    # Test connections
    clients_to_test = [
        ("Direct client", client),
        ("Config client", client_from_config),
    ]

    if auth_client:
        clients_to_test.append(("Auth client", auth_client))

    for _name, test_client in clients_to_test:
        try:
            with test_client:
                # Health check
                test_client.health_check()

                # Example service calls would go here
                # response = test_client.some_method(request)

        except Exception:
            pass


if __name__ == "__main__":
    main()
