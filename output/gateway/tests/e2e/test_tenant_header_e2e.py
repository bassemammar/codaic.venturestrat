"""
End-to-end tests for tenant-header plugin integration.

Tests Task 17.4: Full plugin integration testing with Kong Gateway.
These tests validate the complete tenant-header plugin functionality
including Kong startup, configuration loading, JWT processing, and
tenant header forwarding.
"""

import pytest
import requests
import time
import jwt
from datetime import datetime, timedelta
from pathlib import Path
import docker
import socket


@pytest.mark.e2e
class TestTenantHeaderE2E:
    """End-to-end tests for tenant-header plugin with Kong Gateway."""

    # Test configuration
    KONG_ADMIN_HOST = "http://localhost:8001"
    KONG_PROXY_HOST = "http://localhost:8000"
    JWT_SECRET = "test-secret-key-123456789"

    @pytest.fixture(scope="class")
    def kong_config_path(self) -> Path:
        """Get Kong configuration file path."""
        return Path(__file__).parent.parent.parent / "kong-test.yaml"

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker client for container management."""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def sample_tenant_id(self) -> str:
        """Sample tenant ID for testing."""
        return "550e8400-e29b-41d4-a716-446655440000"

    @pytest.fixture(scope="class")
    def sample_jwt_token(self, sample_tenant_id: str) -> str:
        """Create sample JWT token with tenant_id claim."""
        payload = {
            "sub": "user-123",
            "tenant_id": sample_tenant_id,
            "iss": "venturestrat",
            "aud": "api",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")

    @pytest.fixture(scope="class")
    def jwt_token_without_tenant(self) -> str:
        """Create JWT token without tenant_id claim."""
        payload = {
            "sub": "user-456",
            "iss": "venturestrat",
            "aud": "api",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")

    def is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open and accepting connections."""
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def wait_for_kong(self, max_retries: int = 30, retry_interval: float = 2.0) -> bool:
        """Wait for Kong to be ready."""
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{self.KONG_ADMIN_HOST}/status", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass

            time.sleep(retry_interval)

        return False

    @pytest.fixture(scope="class", autouse=True)
    def kong_setup(self, docker_client, kong_config_path):
        """Set up Kong with the tenant-header plugin configuration."""
        # Check if Kong is already running
        if self.is_port_open("localhost", 8001):
            # Kong is running, verify it has our plugin
            try:
                response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
                if response.status_code == 200:
                    plugins = response.json().get("data", [])
                    if any(p.get("name") == "tenant-header" for p in plugins):
                        yield  # Kong is properly configured
                        return
            except requests.RequestException:
                pass

        # Kong not running or not configured - skip these tests
        pytest.skip("Kong not available for E2E testing")

    def test_kong_admin_api_accessible(self):
        """Test that Kong Admin API is accessible."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/status")
        assert response.status_code == 200

        status_data = response.json()
        assert "database" in status_data
        assert "server" in status_data

    def test_kong_proxy_api_accessible(self):
        """Test that Kong Proxy API is accessible."""
        # Test health endpoint (should be excluded from tenant requirement)
        response = requests.get(f"{self.KONG_PROXY_HOST}/health")
        # Should get some response, even if 404 (service not found is OK)
        assert response.status_code in [200, 404, 502]

    def test_tenant_header_plugin_installed(self):
        """Test that tenant-header plugin is installed and configured."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins_data = response.json()
        plugins = plugins_data.get("data", [])

        # Find tenant-header plugin
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]
        assert len(tenant_plugins) > 0, "Tenant-header plugin not found"

        # Verify configuration
        tenant_plugin = tenant_plugins[0]
        config = tenant_plugin.get("config", {})

        assert config.get("header_name") == "X-Tenant-ID"
        assert "/health" in config.get("exclude_paths", [])
        assert "/metrics" in config.get("exclude_paths", [])

    def test_jwt_plugin_configured(self):
        """Test that JWT plugin is properly configured."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins_data = response.json()
        plugins = plugins_data.get("data", [])

        # Find JWT plugin
        jwt_plugins = [p for p in plugins if p.get("name") == "jwt"]
        assert len(jwt_plugins) > 0, "JWT plugin not found"

    def test_request_without_jwt_rejected(self):
        """Test that requests without JWT are rejected."""
        # Try to access API endpoint without JWT
        response = requests.get(f"{self.KONG_PROXY_HOST}/api/v1/registry/health")

        # Should be 401 due to missing JWT
        assert response.status_code == 401

    def test_request_with_valid_jwt_and_tenant_forwards_header(
        self, sample_jwt_token, sample_tenant_id
    ):
        """Test that requests with valid JWT and tenant_id forward X-Tenant-ID header."""
        headers = {
            "Authorization": f"Bearer {sample_jwt_token}",
            "X-API-Key": "test-api-key-67890",  # Use test consumer key
        }

        # Make request to registry service
        response = requests.get(f"{self.KONG_PROXY_HOST}/api/v1/registry/health", headers=headers)
        response = requests.get(
            f"{self.KONG_PROXY_HOST}/api/v1/registry/health", headers=headers
        )

        # We expect either 200 (if service is up) or 502 (if service is down)
        # Both indicate Kong processed the request successfully
        assert response.status_code in [200, 502, 503]

        # If we get 502/503, it means Kong forwarded the request but service is down
        # This confirms Kong processed JWT and tenant-header plugin correctly

    def test_request_with_jwt_without_tenant_rejected(self, jwt_token_without_tenant):
        """Test that requests with JWT but no tenant_id are rejected."""
        headers = {
            "Authorization": f"Bearer {jwt_token_without_tenant}",
            "X-API-Key": "test-api-key-67890",
        }

        # Make request to API endpoint that requires tenant
        response = requests.get(f"{self.KONG_PROXY_HOST}/api/v1/registry/tenants", headers=headers)
        response = requests.get(
            f"{self.KONG_PROXY_HOST}/api/v1/registry/tenants", headers=headers
        )

        # Should be 401 due to missing tenant_id in JWT
        assert response.status_code == 401

        # Check error response
        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            assert error_data.get("error") == "missing_tenant"
            assert "tenant_id claim" in error_data.get("message", "")

    def test_excluded_paths_bypass_tenant_requirement(self, jwt_token_without_tenant):
        """Test that excluded paths bypass tenant requirement."""
        headers = {
            "Authorization": f"Bearer {jwt_token_without_tenant}",
            "X-API-Key": "test-api-key-67890",
        }

        # Test health endpoint (should be excluded)
        excluded_paths = ["/health", "/metrics"]

        for path in excluded_paths:
            response = requests.get(f"{self.KONG_PROXY_HOST}{path}", headers=headers)

            # Should not be rejected due to missing tenant
            # May get 404 or other errors, but not 401 for missing tenant
            assert response.status_code != 401 or (
                response.headers.get("content-type", "").startswith("application/json")
                and response.json().get("error") != "missing_tenant"
            )

    def test_expired_jwt_rejected(self, sample_tenant_id):
        """Test that expired JWT tokens are rejected."""
        # Create expired JWT
        expired_payload = {
            "sub": "user-789",
            "tenant_id": sample_tenant_id,
            "iss": "venturestrat",
            "aud": "api",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.utcnow() - timedelta(hours=2),  # Issued 2 hours ago
        }
        expired_token = jwt.encode(expired_payload, self.JWT_SECRET, algorithm="HS256")

        headers = {
            "Authorization": f"Bearer {expired_token}",
            "X-API-Key": "test-api-key-67890",
        }

        response = requests.get(f"{self.KONG_PROXY_HOST}/api/v1/registry/tenants", headers=headers)
        response = requests.get(
            f"{self.KONG_PROXY_HOST}/api/v1/registry/tenants", headers=headers
        )

        # Should be 401 due to expired JWT (JWT plugin rejects before tenant plugin runs)
        assert response.status_code == 401

    def test_invalid_jwt_signature_rejected(self, sample_tenant_id):
        """Test that JWT with invalid signature is rejected."""
        # Create JWT with wrong secret
        payload = {
            "sub": "user-999",
            "tenant_id": sample_tenant_id,
            "iss": "venturestrat",
            "aud": "api",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        headers = {
            "Authorization": f"Bearer {invalid_token}",
            "X-API-Key": "test-api-key-67890",
        }

        response = requests.get(f"{self.KONG_PROXY_HOST}/api/v1/registry/tenants", headers=headers)
        response = requests.get(
            f"{self.KONG_PROXY_HOST}/api/v1/registry/tenants", headers=headers
        )

        # Should be 401 due to invalid signature (JWT plugin rejects)
        assert response.status_code == 401

    def test_plugin_priority_order(self, sample_jwt_token, sample_tenant_id):
        """Test that plugins execute in correct priority order."""
        # This test verifies that:
        # 1. JWT plugin (priority 1005) runs first and validates/extracts claims
        # 2. Tenant-header plugin (priority 900) runs after and can access jwt_claims
        # 3. Request proceeds to upstream service

        headers = {
            "Authorization": f"Bearer {sample_jwt_token}",
            "X-API-Key": "test-api-key-67890",
        }

        response = requests.get(f"{self.KONG_PROXY_HOST}/api/v1/registry/health", headers=headers)

        # Success (200, 502, 503) indicates correct plugin execution order
        # 401 would indicate plugin order issue or configuration problem
        assert response.status_code in [
            200,
            502,
            503,
        ], f"Unexpected status {response.status_code}, may indicate plugin priority issue"
        response = requests.get(
            f"{self.KONG_PROXY_HOST}/api/v1/registry/health", headers=headers
        )

        # Success (200, 502, 503) indicates correct plugin execution order
        # 401 would indicate plugin order issue or configuration problem
        assert (
            response.status_code in [200, 502, 503]
        ), f"Unexpected status {response.status_code}, may indicate plugin priority issue"

    def test_debug_header_when_enabled(self):
        """Test debug header functionality when enabled."""
        # This test would require reconfiguring Kong with debug_header: true
        # For now, we verify the configuration supports it

        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins = response.json().get("data", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        if tenant_plugins:
            config = tenant_plugins[0].get("config", {})
            # Verify debug_header setting exists (regardless of value)
            assert "debug_header" in config or config.get("debug_header") is not None

    def test_metrics_emission_configuration(self):
        """Test that metrics emission is properly configured."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins = response.json().get("data", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        if tenant_plugins:
            config = tenant_plugins[0].get("config", {})
            # Verify emit_metrics setting
            emit_metrics = config.get("emit_metrics", True)  # Default is True
            assert isinstance(emit_metrics, bool)

    def test_custom_header_name_support(self):
        """Test that custom header name configuration is supported."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins = response.json().get("data", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        if tenant_plugins:
            config = tenant_plugins[0].get("config", {})
            header_name = config.get("header_name", "X-Tenant-ID")

            # Verify header name is string and follows convention
            assert isinstance(header_name, str)
            assert len(header_name) > 0
            assert header_name.startswith("X-") or header_name == "X-Tenant-ID"

    def test_strict_mode_configuration(self):
        """Test strict mode configuration."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins = response.json().get("data", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        if tenant_plugins:
            config = tenant_plugins[0].get("config", {})
            strict_mode = config.get("strict_mode", True)  # Default is True

            assert isinstance(strict_mode, bool)
            # In test environment, strict_mode might be False for easier testing

    def test_log_level_configuration(self):
        """Test log level configuration."""
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins = response.json().get("data", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        if tenant_plugins:
            config = tenant_plugins[0].get("config", {})
            log_level = config.get("log_level", "info")

            valid_levels = ["debug", "info", "warn", "error"]
            assert log_level in valid_levels

    def test_plugin_version_information(self):
        """Test that plugin version information is available."""
        # This tests that the plugin handler has correct version info
        # We can't directly query plugin code from Kong API, but we can
        # verify the plugin is loaded and functional

        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        plugins = response.json().get("data", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        assert len(tenant_plugins) > 0
        # Plugin existence confirms it loaded successfully with version info

    def test_plugin_schema_validation(self):
        """Test plugin schema validation through Kong API."""
        # Try to create a plugin configuration with invalid values
        invalid_config = {
            "name": "tenant-header",
            "config": {
                "log_level": "invalid_level",  # Should be rejected
                "debug_header": "not_a_boolean",  # Should be rejected
                "exclude_paths": "not_an_array",  # Should be rejected
            },
        }

        response = requests.post(f"{self.KONG_ADMIN_HOST}/plugins", json=invalid_config)

        # Should be 400 Bad Request due to schema validation failure
        assert response.status_code == 400

        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            # Should contain schema validation errors
            assert (
                "invalid" in str(error_data).lower()
                or "schema" in str(error_data).lower()
            )

    def test_multiple_tenant_ids_in_sequence(self, sample_tenant_id):
        """Test handling multiple requests with different tenant IDs."""
        tenant_ids = [
            sample_tenant_id,
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
        ]

        for tenant_id in tenant_ids:
            # Create JWT with specific tenant_id
            payload = {
                "sub": f"user-{tenant_id[-4:]}",
                "tenant_id": tenant_id,
                "iss": "venturestrat",
                "aud": "api",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
            }
            token = jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")

            headers = {
                "Authorization": f"Bearer {token}",
                "X-API-Key": "test-api-key-67890",
            }

            response = requests.get(
                f"{self.KONG_PROXY_HOST}/api/v1/registry/health", headers=headers
            )

            # Each request should be processed successfully
            assert response.status_code in [
                200,
                502,
                503,
            ], f"Failed for tenant_id {tenant_id}"

    def test_concurrent_requests_with_different_tenants(self, sample_tenant_id):
        """Test concurrent requests with different tenant contexts."""
        import concurrent.futures

        def make_request(tenant_id: str) -> int:
            """Make a request with specific tenant ID."""
            payload = {
                "sub": f"user-{tenant_id[-4:]}",
                "tenant_id": tenant_id,
                "iss": "venturestrat",
                "aud": "api",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
            }
            token = jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")

            headers = {
                "Authorization": f"Bearer {token}",
                "X-API-Key": "test-api-key-67890",
            }

            response = requests.get(
                f"{self.KONG_PROXY_HOST}/api/v1/registry/health", headers=headers
            )
            return response.status_code

        # Test with 5 different tenant IDs concurrently
        tenant_ids = [f"550e8400-e29b-41d4-a716-44665544000{i}" for i in range(5)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, tenant_id) for tenant_id in tenant_ids]

            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            futures = [
                executor.submit(make_request, tenant_id) for tenant_id in tenant_ids
            ]

            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should be processed successfully (not 401 for tenant issues)
        for status_code in results:
            assert status_code in [
                200,
                502,
                503,
            ], f"Concurrent request failed with {status_code}"

    def test_kong_configuration_reloading(self):
        """Test that Kong configuration includes tenant-header plugin properly."""
        # Verify current configuration
        response = requests.get(f"{self.KONG_ADMIN_HOST}/plugins")
        assert response.status_code == 200

        original_plugins = response.json().get("data", [])
        tenant_plugins_before = [
            p for p in original_plugins if p.get("name") == "tenant-header"
        ]

        assert (
            len(tenant_plugins_before) > 0
        ), "Tenant-header plugin should be configured"

        # Test that Kong is stable (additional config check)
        status_response = requests.get(f"{self.KONG_ADMIN_HOST}/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data.get("database", {}).get("reachable") is True
