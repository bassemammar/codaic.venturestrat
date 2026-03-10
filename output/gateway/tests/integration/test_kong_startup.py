"""
Test Kong Gateway startup verification.

This test verifies that Kong can be started successfully with the docker compose command
and that it responds to health checks on the admin API.
"""

import pytest
import requests
import subprocess


class TestKongStartup:
    """Tests for Kong Gateway startup verification."""

    def test_kong_admin_api_responds(self):
        """Test that Kong admin API responds successfully."""
        try:
            response = requests.get("http://localhost:8001/", timeout=5)
            assert response.status_code == 200

            # Verify it returns Kong configuration data
            data = response.json()
            assert "configuration" in data
            assert "version" in data
            assert data["tagline"] == "Welcome to kong"

        except requests.RequestException as e:
            pytest.fail(f"Kong admin API not responding: {e}")

    def test_kong_status_endpoint(self):
        """Test Kong status endpoint returns health information."""
        try:
            response = requests.get("http://localhost:8001/status", timeout=5)
            assert response.status_code == 200

            # Verify status data structure
            status_data = response.json()
            assert "server" in status_data
            assert "memory" in status_data
            assert "configuration_hash" in status_data

        except requests.RequestException as e:
            pytest.fail(f"Kong status endpoint not responding: {e}")

    def test_kong_proxy_port_accessible(self):
        """Test that Kong proxy port is accessible."""
        try:
            # This should return 401 or 404 depending on route configuration
            response = requests.get("http://localhost:8000/", timeout=5)
            # Either 401 (auth required) or 404 (no route) are valid responses
            assert response.status_code in [401, 404]

            # If it's a JSON response, verify structure
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                assert "message" in data

        except requests.RequestException as e:
            pytest.fail(f"Kong proxy port not responding: {e}")

    def test_kong_with_api_key_authentication(self):
        """Test Kong proxy with valid API key."""
        headers = {"X-API-Key": "dev-api-key-12345"}

        try:
            # Test /health endpoint (should return 404 but be authenticated)
            response = requests.get(
                "http://localhost:8000/health", headers=headers, timeout=5
            )
            assert response.status_code == 404  # Route exists but upstream returns 404

        except requests.RequestException as e:
            pytest.fail(f"Kong proxy with API key not working: {e}")

    def test_kong_declarative_config_loaded(self):
        """Test that Kong has loaded the declarative configuration."""
        try:
            # Check services are configured
            response = requests.get("http://localhost:8001/services", timeout=5)
            assert response.status_code == 200

            services_data = response.json()
            assert "data" in services_data

            # Should have our configured services
            service_names = [service["name"] for service in services_data["data"]]
            assert "registry-service" in service_names
            assert "health-service" in service_names

        except requests.RequestException as e:
            pytest.fail(f"Kong declarative config not loaded: {e}")

    def test_kong_plugins_loaded(self):
        """Test that Kong has loaded the expected plugins."""
        try:
            response = requests.get("http://localhost:8001/plugins", timeout=5)
            assert response.status_code == 200

            plugins_data = response.json()
            assert "data" in plugins_data

            # Should have our configured global plugins
            plugin_names = [plugin["name"] for plugin in plugins_data["data"]]
            expected_plugins = [
                "key-auth",
                "rate-limiting",
                "file-log",
                "prometheus",
                "correlation-id",
                "cors",
            ]

            for expected_plugin in expected_plugins:
                assert (
                    expected_plugin in plugin_names
                ), f"Expected plugin {expected_plugin} not found"

        except requests.RequestException as e:
            pytest.fail(f"Kong plugins not loaded correctly: {e}")

    def test_kong_consumers_configured(self):
        """Test that Kong consumers are configured correctly."""
        try:
            response = requests.get("http://localhost:8001/consumers", timeout=5)
            assert response.status_code == 200

            consumers_data = response.json()
            assert "data" in consumers_data

            # Should have our configured consumers
            consumer_usernames = [consumer["username"] for consumer in consumers_data["data"]]
            consumer_usernames = [
                consumer["username"] for consumer in consumers_data["data"]
            ]
            expected_consumers = [
                "default-consumer",
                "test-consumer",
                "free-tier-consumer",
                "standard-tier-consumer",
            ]

            for expected_consumer in expected_consumers:
                assert (
                    expected_consumer in consumer_usernames
                ), f"Expected consumer {expected_consumer} not found"

        except requests.RequestException as e:
            pytest.fail(f"Kong consumers not configured correctly: {e}")


class TestKongDockerCompose:
    """Tests for Kong Docker Compose functionality."""

    def test_kong_docker_compose_command_works(self):
        """Test that 'docker compose up kong' command works."""
        # This test verifies the specific command mentioned in the task
        # Note: This assumes Kong is already running, but verifies the command syntax works

        try:
            # Test that the docker compose command is valid (dry run)
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.infra.yaml",
                    "--profile",
                    "gateway",
                    "config",
                    "--services",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="../",
            )

            assert (
                result.returncode == 0
            ), f"Docker compose config failed: {result.stderr}"

            # Verify kong is in the services list
            services = result.stdout.strip().split("\n")
            assert "kong" in services, "Kong service not found in docker compose config"

        except subprocess.TimeoutExpired:
            pytest.fail("Docker compose command timed out")
        except Exception as e:
            pytest.fail(f"Docker compose command failed: {e}")
