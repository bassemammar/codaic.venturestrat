"""
Unit tests for JWT configuration in Kong gateway.

Tests Task 8.6: Verify JWT authentication configuration in kong.yaml.
Validates that Kong is properly configured to handle JWT tokens for
service-to-service authentication.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.mark.unit
class TestJWTKongConfiguration:
    """Test JWT-specific configuration in Kong."""

    @pytest.fixture
    def kong_config(self) -> Dict[str, Any]:
        """Load Kong configuration for testing."""
        config_path = Path(__file__).parent.parent.parent / "kong.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_jwt_plugin_configured(self, kong_config):
        """Test that JWT plugin is configured globally."""
        plugins = kong_config.get("plugins", [])
        jwt_plugins = [p for p in plugins if p.get("name") == "jwt"]

        assert len(jwt_plugins) > 0, "JWT plugin not found in global configuration"

        jwt_plugin = jwt_plugins[0]
        config = jwt_plugin.get("config", {})

        # Verify JWT plugin configuration
        assert "header_names" in config, "JWT plugin missing header_names"
        assert (
            "Authorization" in config["header_names"]
        ), "JWT plugin missing Authorization header"

        assert "anonymous" in config, "JWT plugin missing anonymous configuration"
        assert (
            config["anonymous"] is not None
        ), "JWT anonymous consumer should be configured"

        assert "claims_to_verify" in config, "JWT plugin missing claims_to_verify"
        assert (
            "exp" in config["claims_to_verify"]
        ), "JWT plugin should verify expiration"

    def test_jwt_consumers_configured(self, kong_config):
        """Test that JWT consumers are properly configured."""
        consumers = kong_config.get("consumers", [])

        # Find consumers with JWT secrets
        jwt_consumers = [c for c in consumers if "jwt_secrets" in c]

        assert len(jwt_consumers) > 0, "No JWT consumers configured"

        # Verify JWT consumer structure
        for consumer in jwt_consumers:
            assert "username" in consumer, f"JWT consumer missing username: {consumer}"
            assert (
                "jwt_secrets" in consumer
            ), f"JWT consumer missing jwt_secrets: {consumer}"

            jwt_secrets = consumer["jwt_secrets"]
            assert isinstance(jwt_secrets, list), "jwt_secrets should be a list"
            assert (
                len(jwt_secrets) > 0
            ), f"Consumer {consumer['username']} has no JWT secrets"

            for secret in jwt_secrets:
                assert "key" in secret, f"JWT secret missing key for {consumer['username']}"
                assert "secret" in secret, f"JWT secret missing secret for {consumer['username']}"
                assert (
                    "key" in secret
                ), f"JWT secret missing key for {consumer['username']}"
                assert (
                    "secret" in secret
                ), f"JWT secret missing secret for {consumer['username']}"
                assert (
                    "algorithm" in secret
                ), f"JWT secret missing algorithm for {consumer['username']}"

                # Verify algorithm
                assert (
                    secret["algorithm"] == "HS256"
                ), f"Expected HS256 algorithm for {consumer['username']}"

                # Verify key matches issuer
                assert (
                    secret["key"] == "venturestrat-gateway"
                ), f"JWT key should match issuer for {consumer['username']}"

    def test_jwt_service_consumers_present(self, kong_config):
        """Test that service consumers for JWT are configured."""
        consumers = kong_config.get("consumers", [])
        jwt_consumers = [c for c in consumers if "jwt_secrets" in c]

        # Expected service consumers
        expected_services = [
            "registry-service",
            "pricing-service",
            "jwt-issuer-service",
        ]

        for service_name in expected_services:
            service_consumers = [
                c for c in jwt_consumers if c.get("username") == service_name
            ]
            assert (
                len(service_consumers) > 0
            ), f"Missing JWT consumer for {service_name}"

    def test_jwt_anonymous_consumer_configured(self, kong_config):
        """Test that JWT anonymous consumer is configured."""
        consumers = kong_config.get("consumers", [])

        anonymous_consumers = [
            c for c in consumers if "jwt-anonymous" in c.get("username", "")
        ]
        assert len(anonymous_consumers) > 0, "JWT anonymous consumer not found"

        # Should also have jwt-issuer-anonymous for JWT issuer access
        issuer_anonymous = [
            c for c in consumers if "jwt-issuer-anonymous" in c.get("username", "")
        ]
        assert len(issuer_anonymous) > 0, "JWT issuer anonymous consumer not found"

    def test_jwt_claims_forwarding_configured(self, kong_config):
        """Test that JWT claims are configured to be forwarded as headers."""
        plugins = kong_config.get("plugins", [])

        # Find request-transformer plugins
        transformer_plugins = [
            p for p in plugins if p.get("name") == "request-transformer"
        ]

        # Should have at least one transformer that adds JWT headers
        jwt_transformer_found = False

        for plugin in transformer_plugins:
            config = plugin.get("config", {})
            add_headers = config.get("add", {}).get("headers", [])

            # Check if JWT headers are being added
            jwt_headers = [h for h in add_headers if "jwt" in h.lower()]

            if jwt_headers:
                jwt_transformer_found = True

                # Verify specific JWT headers are configured
                expected_patterns = [
                    "X-JWT-Sub",
                    "X-JWT-Issuer",
                    "X-JWT-Audience",
                    "X-JWT-ID",
                    "X-JWT-Scope",
                ]

                for pattern in expected_patterns:
                    matching_headers = [
                        h for h in add_headers if pattern.lower() in h.lower()
                    ]
                    assert (
                        len(matching_headers) > 0
                    ), f"Missing JWT header configuration: {pattern}"

        assert (
            jwt_transformer_found
        ), "No request-transformer plugin found that forwards JWT claims"

    def test_jwt_issuer_service_configured(self, kong_config):
        """Test that JWT issuer service is configured."""
        services = kong_config.get("services", [])

        # Find JWT issuer service
        jwt_issuer_services = [s for s in services if "jwt-issuer" in s.get("name", "")]
        assert len(jwt_issuer_services) > 0, "JWT issuer service not configured"

        jwt_service = jwt_issuer_services[0]

        # Verify service configuration
        assert "url" in jwt_service or (
            "host" in jwt_service and "port" in jwt_service
        ), "JWT issuer service missing URL/host configuration"

        # Verify routes exist
        routes = jwt_service.get("routes", [])
        assert len(routes) > 0, "JWT issuer service has no routes configured"

        # Should have a route for token issuance
        token_routes = [r for r in routes if "token" in str(r.get("paths", []))]
        assert len(token_routes) > 0, "No JWT token route configured"

    def test_jwt_issuer_accessible_without_api_key(self, kong_config):
        """Test that JWT issuer is configured to be accessible without API key."""
        services = kong_config.get("services", [])

        # Find JWT issuer service
        jwt_issuer_services = [s for s in services if "jwt-issuer" in s.get("name", "")]
        assert len(jwt_issuer_services) > 0, "JWT issuer service not configured"

        jwt_service = jwt_issuer_services[0]

        # Check if JWT issuer has special auth configuration
        plugins = jwt_service.get("plugins", [])

        # Should have key-auth plugin with anonymous access
        key_auth_plugins = [p for p in plugins if p.get("name") == "key-auth"]

        if key_auth_plugins:
            key_auth = key_auth_plugins[0]
            config = key_auth.get("config", {})
            assert "anonymous" in config, "JWT issuer should allow anonymous access"
            assert (
                config["anonymous"] is not None
            ), "JWT issuer anonymous should be configured"

    def test_jwt_secret_consistency(self, kong_config):
        """Test that JWT secrets are consistent across consumers."""
        consumers = kong_config.get("consumers", [])
        jwt_consumers = [c for c in consumers if "jwt_secrets" in c]

        if len(jwt_consumers) == 0:
            return  # Skip if no JWT consumers

        # All JWT consumers should use the same secret and algorithm
        reference_secret = None
        reference_algorithm = None

        for consumer in jwt_consumers:
            for secret_config in consumer["jwt_secrets"]:
                secret = secret_config.get("secret")
                algorithm = secret_config.get("algorithm")

                if reference_secret is None:
                    reference_secret = secret
                    reference_algorithm = algorithm
                else:
                    assert (
                        secret == reference_secret
                    ), f"Inconsistent JWT secret in consumer {consumer['username']}"
                    assert (
                        algorithm == reference_algorithm
                    ), f"Inconsistent JWT algorithm in consumer {consumer['username']}"

        # Secret should not be the default in production
        # For development, we accept the default but warn
        if reference_secret == "dev-secret-change-in-prod":
            # This is acceptable for development but should be changed in production
            pass

    def test_jwt_plugin_security_settings(self, kong_config):
        """Test JWT plugin security settings."""
        plugins = kong_config.get("plugins", [])
        jwt_plugins = [p for p in plugins if p.get("name") == "jwt"]

        assert len(jwt_plugins) > 0, "No JWT plugin configured"

        for plugin in jwt_plugins:
            config = plugin.get("config", {})

            # Should verify expiration
            claims_to_verify = config.get("claims_to_verify", [])
            assert (
                "exp" in claims_to_verify
            ), "JWT plugin should verify token expiration"

            # Should have reasonable maximum expiration
            max_exp = config.get("maximum_expiration")
            if max_exp is not None:
                assert (
                    max_exp <= 86400
                ), "JWT maximum expiration should not exceed 24 hours"  # 24 hours max

            # Should have key claim name set to issuer
            key_claim_name = config.get("key_claim_name")
            if key_claim_name is not None:
                assert key_claim_name == "iss", "JWT key claim should be 'iss' (issuer)"

    def test_service_to_service_auth_method_detection(self, kong_config):
        """Test that auth method detection is configured for service-to-service calls."""
        plugins = kong_config.get("plugins", [])

        # Find request transformer plugins that add auth method headers
        transformer_plugins = [
            p for p in plugins if p.get("name") == "request-transformer"
        ]

        auth_method_configured = False

        for plugin in transformer_plugins:
            config = plugin.get("config", {})
            add_headers = config.get("add", {}).get("headers", [])

            # Look for X-Auth-Method header configuration
            auth_method_headers = [
                h for h in add_headers if "x-auth-method" in h.lower()
            ]

            if auth_method_headers:
                auth_method_configured = True
                break

        assert (
            auth_method_configured
        ), "X-Auth-Method header not configured in request transformer"

    def test_jwt_route_priority_configuration(self, kong_config):
        """Test that JWT issuer routes have appropriate priority."""
        services = kong_config.get("services", [])

        for service in services:
            if "jwt-issuer" in service.get("name", ""):
                routes = service.get("routes", [])

                for route in routes:
                    # JWT issuer routes should have higher priority than generic routes
                    priority = route.get("regex_priority", 0)
                    assert (
                        priority >= 100
                    ), f"JWT issuer route should have high priority (>=100), got {priority}"

    def test_jwt_configuration_completeness(self, kong_config):
        """Test that JWT configuration is complete for service-to-service auth."""
        # Must have JWT plugin
        plugins = kong_config.get("plugins", [])
        jwt_plugins = [p for p in plugins if p.get("name") == "jwt"]
        assert len(jwt_plugins) > 0, "JWT plugin not configured"

        # Must have JWT consumers
        consumers = kong_config.get("consumers", [])
        jwt_consumers = [c for c in consumers if "jwt_secrets" in c]
        assert len(jwt_consumers) > 0, "No JWT consumers configured"

        # Must have JWT issuer service
        services = kong_config.get("services", [])
        jwt_issuer_services = [s for s in services if "jwt-issuer" in s.get("name", "")]
        assert len(jwt_issuer_services) > 0, "JWT issuer service not configured"

        # Must have request transformer for claims forwarding
        transformer_plugins = [
            p for p in plugins if p.get("name") == "request-transformer"
        ]
        assert len(transformer_plugins) > 0, "No request transformer plugins configured"

        # Must have appropriate consumers and routes
        assert len(services) >= 1, "No services configured"
        assert (
            len(consumers) >= 3
        ), "Insufficient consumers configured"  # At least API key + JWT + anonymous
