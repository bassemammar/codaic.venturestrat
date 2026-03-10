"""
Unit tests for gRPC-Web Docker Compose configuration.

Tests that the Docker Compose file includes proper proto file mounting.
"""

import pytest
import yaml
import os


class TestGRPCWebDockerConfiguration:
    """Test Docker Compose configuration for gRPC-Web support."""

    @pytest.fixture
    def docker_compose_config(self):
        """Load Docker Compose configuration."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.gateway.yaml"
        )
        with open(compose_path, "r") as f:
            return yaml.safe_load(f)

    def test_kong_service_exists(self, docker_compose_config):
        """Test that Kong service is defined."""
        services = docker_compose_config.get("services", {})
        assert "kong" in services, "Kong service should be defined"

    def test_proto_volume_mount_exists(self, docker_compose_config):
        """Test that protos directory is mounted in Kong container."""
        kong_service = docker_compose_config["services"]["kong"]
        volumes = kong_service.get("volumes", [])

        proto_volume = None
        for volume in volumes:
            if "/kong/protos" in volume:
                proto_volume = volume
                break

        assert proto_volume is not None, "Proto volume mount should exist"
        assert (
            "./gateway/protos:/kong/protos:ro" == proto_volume
        ), "Proto volume should be read-only mount"

    def test_kong_volumes_include_required_mounts(self, docker_compose_config):
        """Test that Kong has all required volume mounts."""
        kong_service = docker_compose_config["services"]["kong"]
        volumes = kong_service.get("volumes", [])

        required_volumes = [
            "./gateway/kong.yaml:/kong/kong.yaml:ro",
            "./gateway/certs:/kong/certs:ro",
            "./gateway/plugins:/kong/plugins:ro",
            "./gateway/protos:/kong/protos:ro",
        ]

        for required_volume in required_volumes:
            assert (
                required_volume in volumes
            ), f"Required volume {required_volume} should be mounted"

    def test_kong_environment_variables(self, docker_compose_config):
        """Test Kong environment variables for gRPC support."""
        kong_service = docker_compose_config["services"]["kong"]
        environment = kong_service.get("environment", {})

        # Test essential configuration
        assert environment.get("KONG_DATABASE") == "off", "Kong should be in DB-less mode"
        assert (
            environment.get("KONG_DATABASE") == "off"
        ), "Kong should be in DB-less mode"
        assert (
            environment.get("KONG_DECLARATIVE_CONFIG") == "/kong/kong.yaml"
        ), "Config path should be set"

        # Test plugins configuration
        plugins = environment.get("KONG_PLUGINS")
        assert (
            plugins == "bundled" or "grpc-web" in plugins
        ), "gRPC-Web plugin should be available"

    def test_kong_ports_configuration(self, docker_compose_config):
        """Test that Kong exposes required ports."""
        kong_service = docker_compose_config["services"]["kong"]
        ports = kong_service.get("ports", [])

        required_ports = ["8000:8000", "8443:8443", "8001:8001"]
        for required_port in required_ports:
            assert required_port in ports, f"Port {required_port} should be exposed"

    def test_kong_network_configuration(self, docker_compose_config):
        """Test that Kong is on the correct network."""
        kong_service = docker_compose_config["services"]["kong"]
        networks = kong_service.get("networks", [])

        assert "venturestrat-network" in networks, "Kong should be on venturestrat-network"

    def test_kong_dependencies(self, docker_compose_config):
        """Test that Kong has proper service dependencies."""
        kong_service = docker_compose_config["services"]["kong"]
        depends_on = kong_service.get("depends_on", {})

        required_dependencies = ["consul-server-1", "redis", "health-service"]

        for dependency in required_dependencies:
            assert dependency in depends_on, f"Kong should depend on {dependency}"
            assert (
                depends_on[dependency].get("condition") == "service_healthy"
            ), f"{dependency} should be healthy"

    def test_kong_health_check(self, docker_compose_config):
        """Test that Kong has proper health check configuration."""
        kong_service = docker_compose_config["services"]["kong"]
        healthcheck = kong_service.get("healthcheck", {})

        assert "test" in healthcheck, "Health check test should be defined"
        assert "kong" in " ".join(
            healthcheck["test"]
        ), "Health check should use Kong command"
        assert (
            healthcheck.get("interval") == "10s"
        ), "Health check interval should be 10s"
        assert healthcheck.get("timeout") == "5s", "Health check timeout should be 5s"
        assert healthcheck.get("retries") == 5, "Health check should have 5 retries"

    def test_proto_directory_structure_requirement(self):
        """Test that proto directory structure exists."""
        proto_dir = os.path.join(os.path.dirname(__file__), "..", "..", "protos")
        assert os.path.exists(proto_dir), "Protos directory should exist"

        # Test that registry.proto exists
        registry_proto = os.path.join(proto_dir, "registry.proto")
        assert os.path.exists(
            registry_proto
        ), "registry.proto should exist in protos directory"

    def test_kong_resource_limits(self, docker_compose_config):
        """Test that Kong has appropriate resource limits for gRPC-Web."""
        kong_service = docker_compose_config["services"]["kong"]
        deploy = kong_service.get("deploy", {})
        resources = deploy.get("resources", {})

        limits = resources.get("limits", {})
        reservations = resources.get("reservations", {})

        # Test memory limits (gRPC-Web may need more memory)
        assert "memory" in limits, "Memory limit should be set"
        assert "memory" in reservations, "Memory reservation should be set"

        # Test CPU limits
        assert "cpus" in limits, "CPU limit should be set"
        assert "cpus" in reservations, "CPU reservation should be set"

    def test_volumes_are_read_only(self, docker_compose_config):
        """Test that configuration volumes are mounted read-only."""
        kong_service = docker_compose_config["services"]["kong"]
        volumes = kong_service.get("volumes", [])

        config_volumes = [
            v
            for v in volumes
            if any(conf in v for conf in ["kong.yaml", "protos", "certs", "plugins"])
        ]

        for volume in config_volumes:
            assert volume.endswith(
                ":ro"
            ), f"Configuration volume {volume} should be read-only"

    def test_external_network_requirement(self, docker_compose_config):
        """Test that the required external network is defined."""
        networks = docker_compose_config.get("networks", {})
        venturestrat_network = networks.get("venturestrat-network", {})

        assert venturestrat_network.get("external"), "venturestrat-network should be external"
        assert (
            venturestrat_network.get("external") == True
        ), "venturestrat-network should be external"
