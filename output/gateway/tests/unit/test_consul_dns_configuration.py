"""
Unit tests for Consul DNS configuration validation.

Tests DNS configuration settings and format validation without requiring infrastructure.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def kong_config() -> Dict[str, Any]:
    """Load kong.yaml configuration for testing."""
    config_path = Path(__file__).parent.parent.parent / "kong.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def docker_compose_config() -> Dict[str, Any]:
    """Load docker-compose.gateway.yaml for DNS configuration validation."""
    config_path = Path(__file__).parent.parent.parent / "docker-compose.gateway.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.mark.unit
class TestConsulDNSConfiguration:
    """Unit tests for Consul DNS configuration validation."""

    def test_kong_dns_resolver_configuration(self, docker_compose_config):
        """Test that Kong is configured with Consul DNS resolver."""
        kong_service = docker_compose_config.get("services", {}).get("kong", {})
        environment = kong_service.get("environment", {})

        # Check DNS resolver configuration
        dns_resolver = environment.get("KONG_DNS_RESOLVER")
        assert dns_resolver is not None, "KONG_DNS_RESOLVER not configured"
        assert (
            "consul-server-1:8600" in dns_resolver
        ), f"DNS resolver should point to Consul: {dns_resolver}"

    def test_kong_dns_order_configuration(self, docker_compose_config):
        """Test that Kong DNS order is configured for Consul SRV records."""
        kong_service = docker_compose_config.get("services", {}).get("kong", {})
        environment = kong_service.get("environment", {})

        # Check DNS order configuration
        dns_order = environment.get("KONG_DNS_ORDER")
        assert dns_order is not None, "KONG_DNS_ORDER not configured"
        assert "SRV" in dns_order, "DNS order should include SRV records for Consul"
        assert "A" in dns_order, "DNS order should include A records as fallback"
        assert (
            "CNAME" in dns_order
        ), "DNS order should include CNAME records as fallback"

        # Check order - SRV should come first for Consul service discovery
        order_parts = [part.strip() for part in dns_order.split(",")]
        assert order_parts[0] == "SRV", "SRV records should be tried first for Consul"

    def test_kong_dns_stale_ttl_configuration(self, docker_compose_config):
        """Test that Kong DNS stale TTL is configured for resilience."""
        kong_service = docker_compose_config.get("services", {}).get("kong", {})
        environment = kong_service.get("environment", {})

        # Check stale TTL configuration
        stale_ttl = environment.get("KONG_DNS_STALE_TTL")
        assert stale_ttl is not None, "KONG_DNS_STALE_TTL not configured"
        assert int(stale_ttl) > 0, "DNS stale TTL should be positive"
        assert int(stale_ttl) <= 300, "DNS stale TTL should be reasonable (≤5 minutes)"

    def test_consul_service_dns_format(self, kong_config):
        """Test that all Consul service targets use correct DNS format."""
        upstreams = kong_config.get("upstreams", [])
        consul_targets = []

        for upstream in upstreams:
            targets = upstream.get("targets", [])
            for target in targets:
                target_address = target.get("target", "")
                if ".service.consul" in target_address:
                    consul_targets.append(target_address)

        assert len(consul_targets) > 0, "No Consul service targets found"

        for target in consul_targets:
            # Format: <service-name>.service.consul:<port>
            if ":" in target:
                hostname, port = target.rsplit(":", 1)
                assert port.isdigit(), f"Port should be numeric in: {target}"
                assert 1 <= int(port) <= 65535, f"Port should be valid in: {target}"
            else:
                hostname = target

            # Validate hostname format
            parts = hostname.split(".")
            assert (
                len(parts) == 3
            ), f"Consul DNS name should have 3 parts (service.service.consul): {hostname}"
            assert parts[1] == "service", f"Second part should be 'service': {hostname}"
            assert parts[2] == "consul", f"Third part should be 'consul': {hostname}"

            # Validate service name
            service_name = parts[0]
            assert len(service_name) > 0, f"Service name cannot be empty: {hostname}"
            assert all(
                c.isalnum() or c in "-_" for c in service_name
            ), f"Service name contains invalid characters: {service_name}"

    def test_upstream_consul_configuration(self, kong_config):
        """Test that upstreams using Consul are properly configured."""
        upstreams = kong_config.get("upstreams", [])
        consul_upstreams = []

        for upstream in upstreams:
            targets = upstream.get("targets", [])
            has_consul_target = any(
                ".service.consul" in target.get("target", "") for target in targets
            )
            if has_consul_target:
                consul_upstreams.append(upstream)

        assert (
            len(consul_upstreams) > 0
        ), "No upstreams configured for Consul service discovery"

        for upstream in consul_upstreams:
            # Check required upstream configuration for Consul
            assert "name" in upstream, "Upstream must have a name"
            assert "targets" in upstream, "Upstream must have targets"

            # Check algorithm is specified
            algorithm = upstream.get("algorithm")
            if algorithm:
                valid_algorithms = ["round-robin", "least-connections", "ip-hash"]
                assert (
                    algorithm in valid_algorithms
                ), f"Invalid load balancing algorithm: {algorithm}"

            # Check health checks are configured
            healthchecks = upstream.get("healthchecks")
            if healthchecks:
                assert (
                    "active" in healthchecks
                ), "Active health checks should be configured for Consul targets"

                active_checks = healthchecks["active"]
                assert "http_path" in active_checks, "HTTP health check path should be configured"
                assert (
                    "http_path" in active_checks
                ), "HTTP health check path should be configured"

                http_path = active_checks["http_path"]
                assert http_path.startswith(
                    "/"
                ), f"Health check path should start with '/': {http_path}"

    def test_consul_target_tags(self, kong_config):
        """Test that Consul targets include appropriate tags."""
        upstreams = kong_config.get("upstreams", [])

        for upstream in upstreams:
            targets = upstream.get("targets", [])
            for target in targets:
                target_address = target.get("target", "")
                if ".service.consul" in target_address:
                    tags = target.get("tags", [])
                    assert isinstance(tags, list), "Target tags should be a list"

                    # Check for descriptive tags
                    if tags:
                        assert all(
                            isinstance(tag, str) for tag in tags
                        ), "All tags should be strings"
                        assert all(len(tag) > 0 for tag in tags), "Tags should not be empty strings"
                        assert all(
                            len(tag) > 0 for tag in tags
                        ), "Tags should not be empty strings"

    def test_consul_service_name_extraction(self, kong_config):
        """Test extraction of service names from Consul DNS targets."""
        upstreams = kong_config.get("upstreams", [])
        service_names = []

        for upstream in upstreams:
            targets = upstream.get("targets", [])
            for target in targets:
                target_address = target.get("target", "")
                if ".service.consul" in target_address:
                    # Extract service name
                    hostname = (
                        target_address.split(":")[0] if ":" in target_address else target_address
                        target_address.split(":")[0]
                        if ":" in target_address
                        else target_address
                    )
                    service_name = hostname.split(".")[0]
                    service_names.append(service_name)

        assert len(service_names) > 0, "No service names found in Consul targets"

        for service_name in service_names:
            # Service names should follow naming conventions
            assert len(service_name) > 0, "Service name should not be empty"
            assert (
                service_name.replace("-", "").replace("_", "").isalnum()
            ), f"Service name should be alphanumeric with hyphens/underscores: {service_name}"
            assert not service_name.startswith("-") and not service_name.endswith(
                "-"
            ), f"Service name should not start/end with hyphen: {service_name}"

    def test_docker_compose_consul_dependency(self, docker_compose_config):
        """Test that Kong depends on Consul in docker-compose."""
        kong_service = docker_compose_config.get("services", {}).get("kong", {})
        depends_on = kong_service.get("depends_on", {})

        # Kong should depend on Consul
        consul_dependencies = [
            dep for dep in depends_on.keys() if "consul" in dep.lower()
        ]
        assert len(consul_dependencies) > 0, "Kong should depend on Consul service"

        # Check dependency configuration
        for consul_dep in consul_dependencies:
            dep_config = depends_on.get(consul_dep, {})
            if isinstance(dep_config, dict):
                condition = dep_config.get("condition")
                if condition:
                    assert (
                        condition == "service_healthy"
                    ), f"Kong should wait for Consul to be healthy: {condition}"

    def test_kong_network_configuration(self, docker_compose_config):
        """Test that Kong is on the same network as Consul for DNS resolution."""
        kong_service = docker_compose_config.get("services", {}).get("kong", {})
        networks = kong_service.get("networks", [])

        # Kong should be on venturestrat-network for service discovery
        if isinstance(networks, list):
            assert (
                "venturestrat-network" in networks
            ), "Kong should be on venturestrat-network for service discovery"
        elif isinstance(networks, dict):
            assert (
                "venturestrat-network" in networks
            ), "Kong should be on venturestrat-network for service discovery"

    def test_dns_configuration_environment_variables(self, docker_compose_config):
        """Test all DNS-related environment variables are properly set."""
        kong_service = docker_compose_config.get("services", {}).get("kong", {})
        environment = kong_service.get("environment", {})

        # Required DNS environment variables
        required_dns_vars = [
            "KONG_DNS_RESOLVER",
            "KONG_DNS_ORDER",
        ]

        for var in required_dns_vars:
            assert (
                var in environment
            ), f"Required DNS environment variable missing: {var}"
            assert environment[
                var
            ], f"DNS environment variable should not be empty: {var}"

        # Optional but recommended DNS variables
        optional_dns_vars = [
            "KONG_DNS_STALE_TTL",
        ]

        for var in optional_dns_vars:
            if var in environment:
                assert environment[
                    var
                ], f"Optional DNS environment variable should not be empty: {var}"

    def test_all_service_urls_use_consul_dns(self, kong_config):
        """Test that all service URLs use Consul DNS format."""
        services = kong_config.get("services", [])

        for service in services:
            service_name = service.get("name")

            # Check if service has a URL (direct service definition)
            service_url = service.get("url")
            if service_url:
                # Parse URL to check hostname
                from urllib.parse import urlparse

                parsed = urlparse(service_url)
                hostname = parsed.hostname

                if (
                    hostname
                    and hostname != "localhost"
                    and not hostname.startswith("127.")
                ):
                    # Should use Consul DNS format for non-local services
                    assert (
                        ".service.consul" in hostname
                    ), f"Service '{service_name}' URL should use Consul DNS: {service_url}"

                    # Validate Consul DNS format
                    parts = hostname.split(".")
                    assert len(parts) == 3, f"Consul DNS name should have 3 parts: {hostname}"
                    assert parts[1] == "service", f"Second part should be 'service': {hostname}"
                    assert parts[2] == "consul", f"Third part should be 'consul': {hostname}"
                    assert (
                        len(parts) == 3
                    ), f"Consul DNS name should have 3 parts: {hostname}"
                    assert (
                        parts[1] == "service"
                    ), f"Second part should be 'service': {hostname}"
                    assert (
                        parts[2] == "consul"
                    ), f"Third part should be 'consul': {hostname}"
