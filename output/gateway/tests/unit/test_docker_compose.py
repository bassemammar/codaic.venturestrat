"""Tests for docker-compose.gateway.yaml configuration."""

import yaml
import pytest
from pathlib import Path


class TestDockerComposeGateway:
    """Test suite for gateway docker-compose configuration."""

    @pytest.fixture
    def compose_config(self):
        """Load the docker-compose.gateway.yaml configuration."""
        gateway_dir = Path(__file__).parent.parent.parent
        compose_file = gateway_dir / "docker-compose.gateway.yaml"

        with open(compose_file, "r") as f:
            config = yaml.safe_load(f)
        return config

    def test_compose_yaml_valid_syntax(self, compose_config):
        """Test that docker-compose.gateway.yaml has valid YAML syntax."""
        assert compose_config is not None
        assert isinstance(compose_config, dict)

    def test_required_services_present(self, compose_config):
        """Test that required services are defined."""
        services = compose_config.get("services", {})

        # Kong gateway service is required
        assert "kong" in services

        # JWT issuer service is required for service-to-service auth
        assert "jwt-issuer" in services

        # Health service is required for proper health endpoint
        assert "health-service" in services

    def test_kong_service_configuration(self, compose_config):
        """Test Kong service configuration."""
        kong_service = compose_config["services"]["kong"]

        # Check image
        assert kong_service["image"] == "kong:3.5"

        # Check environment variables
        env = kong_service["environment"]
        assert env["KONG_DATABASE"] == "off"  # DB-less mode
        assert env["KONG_DECLARATIVE_CONFIG"] == "/kong/kong.yaml"
        assert "consul-server-1:8600" in env["KONG_DNS_RESOLVER"]

        # Check ports
        ports = kong_service["ports"]
        assert "8000:8000" in ports  # Proxy HTTP
        assert "8443:8443" in ports  # Proxy HTTPS
        assert "8001:8001" in ports  # Admin API

        # Check volumes
        volumes = kong_service["volumes"]
        kong_yaml_mounted = any(
            "kong.yaml:/kong/kong.yaml:ro" in vol for vol in volumes
        )
        assert kong_yaml_mounted

    def test_jwt_issuer_service_configuration(self, compose_config):
        """Test JWT issuer service configuration."""
        jwt_service = compose_config["services"]["jwt-issuer"]

        # Check build context
        assert "build" in jwt_service
        assert jwt_service["build"]["context"] == "./gateway/jwt-issuer"

        # Check environment
        env = jwt_service["environment"]
        assert "JWT_SECRET" in env
        assert "JWT_ISSUER" in env

        # Check ports
        ports = jwt_service["ports"]
        assert "8002:8000" in ports

    def test_health_service_configuration(self, compose_config):
        """Test health service configuration."""
        health_service = compose_config["services"]["health-service"]

        # Check build context
        assert "build" in health_service
        assert health_service["build"]["context"] == "./gateway/health-service"

        # Check environment
        env = health_service["environment"]
        assert "PORT" in env
        assert env["PORT"] == 8003

        # Check ports
        ports = health_service["ports"]
        assert "8003:8003" in ports

    def test_dependencies_configured(self, compose_config):
        """Test that service dependencies are properly configured."""
        kong_service = compose_config["services"]["kong"]

        # Kong should depend on consul, redis, and health-service
        depends_on = kong_service["depends_on"]
        assert "consul-server-1" in depends_on
        assert "redis" in depends_on
        assert "health-service" in depends_on

        # Check health check conditions
        assert depends_on["consul-server-1"]["condition"] == "service_healthy"
        assert depends_on["redis"]["condition"] == "service_healthy"
        assert depends_on["health-service"]["condition"] == "service_healthy"

    def test_healthchecks_configured(self, compose_config):
        """Test that health checks are configured."""
        kong_service = compose_config["services"]["kong"]
        jwt_service = compose_config["services"]["jwt-issuer"]
        health_service = compose_config["services"]["health-service"]

        # Kong health check
        assert "healthcheck" in kong_service
        assert kong_service["healthcheck"]["test"] == ["CMD", "kong", "health"]

        # JWT issuer health check
        assert "healthcheck" in jwt_service
        assert "curl" in jwt_service["healthcheck"]["test"][1]

        # Health service health check
        assert "healthcheck" in health_service
        health_test = health_service["healthcheck"]["test"]
        assert "python" in health_test[1]
        assert "requests.get" in health_test[3]  # The python code is in the 4th element

    def test_network_configuration(self, compose_config):
        """Test network configuration."""
        services = compose_config["services"]

        # All services should be on venturestrat-network
        for service_name, service_config in services.items():
            networks = service_config.get("networks", [])
            assert "venturestrat-network" in networks

        # Network should be external
        networks = compose_config.get("networks", {})
        assert "venturestrat-network" in networks
        assert networks["venturestrat-network"]["external"] is True

    def test_resource_limits_configured(self, compose_config):
        """Test that resource limits are configured for production readiness."""
        kong_service = compose_config["services"]["kong"]
        jwt_service = compose_config["services"]["jwt-issuer"]

        # Kong resource limits
        kong_deploy = kong_service.get("deploy", {})
        assert "resources" in kong_deploy
        assert "limits" in kong_deploy["resources"]
        assert "memory" in kong_deploy["resources"]["limits"]

        # JWT issuer resource limits
        jwt_deploy = jwt_service.get("deploy", {})
        assert "resources" in jwt_deploy
        assert "limits" in jwt_deploy["resources"]

    def test_security_configuration(self, compose_config):
        """Test security-related configuration."""
        kong_service = compose_config["services"]["kong"]

        # Kong should have security environment variables
        env = kong_service["environment"]
        assert "KONG_REAL_IP_HEADER" in env
        assert "KONG_REAL_IP_RECURSIVE" in env
        assert "KONG_TRUSTED_IPS" in env

    def test_volume_mounts_secure(self, compose_config):
        """Test that volume mounts are configured securely."""
        kong_service = compose_config["services"]["kong"]

        volumes = kong_service["volumes"]

        # Check that configuration files are mounted read-only
        for volume in volumes:
            if "kong.yaml" in volume:
                assert volume.endswith(":ro"), "Kong config should be read-only"
            elif "certs" in volume:
                assert volume.endswith(":ro"), "Certificates should be read-only"
            elif "plugins" in volume:
                assert volume.endswith(":ro"), "Plugins should be read-only"

    def test_restart_policy_configured(self, compose_config):
        """Test that restart policies are configured."""
        services = compose_config["services"]

        for service_name, service_config in services.items():
            restart = service_config.get("restart")
            assert restart is not None, f"Service {service_name} should have restart policy"
            assert (
                restart is not None
            ), f"Service {service_name} should have restart policy"
            assert restart in ["unless-stopped", "always", "on-failure"]
