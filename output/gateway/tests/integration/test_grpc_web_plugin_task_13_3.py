"""
Task 13.3: Integration tests for gRPC-Web plugin configuration for registry-service.

This test file verifies that the Kong gateway correctly handles gRPC-Web requests
to the registry service with the plugin configuration from task 13.3.
"""

import pytest
import httpx


@pytest.mark.integration
class TestGRPCWebPluginIntegrationTask133:
    """Task 13.3 specific integration tests for gRPC-Web plugin."""

    def test_grpc_web_route_is_accessible(self, gateway_client: httpx.Client):
        """Test that /grpc/v1/registry route is accessible and accepts gRPC-Web."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x04test",  # Minimal gRPC frame
        )

        # Route should be accessible (not 404)
        assert response.status_code != 404, "gRPC-Web route should be accessible"

        # Content type should be accepted (not 415)
        assert response.status_code != 415, "gRPC-Web content type should be accepted"

        # Kong should process the request (add headers or return 502/503 if backend unavailable)
        has_kong_headers = any(h.startswith("X-Kong-") for h in response.headers.keys())
        backend_unavailable = response.status_code in [502, 503]
        assert (
            has_kong_headers or backend_unavailable
        ), "Kong should process the request"

    def test_grpc_web_transcoding_plugin_active(self, gateway_client: httpx.Client):
        """Test that gRPC-Web transcoding plugin is active for registry service."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "Accept": "application/grpc-web+proto",
            },
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Plugin should handle the request
        assert response.status_code != 404, "Route should exist"
        assert response.status_code != 415, "Content-type should be supported"

        # If backend is available, response should have appropriate headers
        if response.status_code not in [502, 503]:
            # gRPC-Web responses typically have specific content type
            content_type = response.headers.get("Content-Type", "")
            grpc_related = any(
                [
                    "grpc" in content_type.lower(),
                    "application/grpc" in content_type.lower(),
                    response.status_code == 200,  # Successfully handled by plugin
                ]
            )
            assert (
                grpc_related
            ), f"Response should be gRPC-related, got content-type: {content_type}"

    def test_grpc_web_authentication_required(self):
        """Test that gRPC-Web requests require authentication."""
        unauthorized_client = httpx.Client(base_url="http://localhost:8000")

        try:
            response = unauthorized_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": "application/grpc-web+proto"},
                content=b"\x00\x00\x00\x00\x04test",
            )

            # Should require authentication
            assert response.status_code == 401, "gRPC-Web requests should require authentication"
            assert (
                response.status_code == 401
            ), "gRPC-Web requests should require authentication"

        finally:
            unauthorized_client.close()

    def test_grpc_web_with_api_key_authentication(self, gateway_client: httpx.Client):
        """Test that gRPC-Web requests work with API key authentication."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Should not be rejected for authentication (client has API key)
        assert response.status_code != 401, "Should accept API key authentication"
        assert response.status_code != 403, "Should accept valid API key"

    def test_grpc_web_rate_limiting_applies(self, free_tier_client: httpx.Client):
        """Test that rate limiting applies to gRPC-Web requests."""
        responses = []

        # Make several requests to check rate limiting
        for i in range(5):
            response = free_tier_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": "application/grpc-web+proto"},
                content=f"\x00\x00\x00\x00\x04req{i}".encode(),
            )
            responses.append(response)

        # All responses should include rate limit headers
        for i, response in enumerate(responses):
            assert (
                "X-RateLimit-Limit-Minute" in response.headers
            ), f"Request {i}: Should include rate limit headers"

    def test_grpc_web_correlation_id_propagation(self, gateway_client: httpx.Client):
        """Test that correlation IDs are properly handled for gRPC-Web requests."""
        custom_correlation_id = "grpc-web-test-correlation-13-3"

        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "X-Correlation-ID": custom_correlation_id,
            },
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Correlation ID should be echoed back
        echoed_id = response.headers.get("X-Correlation-ID")
        assert (
            echoed_id == custom_correlation_id
        ), f"Correlation ID should be preserved: expected {custom_correlation_id}, got {echoed_id}"

    def test_grpc_web_different_content_types(self, gateway_client: httpx.Client):
        """Test that both gRPC-Web content types work with the plugin."""
        content_types = [
            "application/grpc-web+proto",
            "application/grpc-web-text+proto",
        ]

        for content_type in content_types:
            response = gateway_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": content_type},
                content=b"\x00\x00\x00\x00\x04test",
            )

            # Both content types should be accepted
            assert response.status_code != 415, f"Content type {content_type} should be accepted"
            assert (
                response.status_code != 415
            ), f"Content type {content_type} should be accepted"
            assert (
                response.status_code != 404
            ), f"Route should exist for content type {content_type}"

    def test_grpc_web_vs_rest_endpoint_separation(self, gateway_client: httpx.Client):
        """Test that gRPC-Web and REST endpoints are properly separated."""
        # Test REST endpoint
        rest_response = gateway_client.get("/api/v1/registry/services")

        # Test gRPC-Web endpoint
        grpc_response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Both should be routable but handled differently
        assert rest_response.status_code != 404, "REST endpoint should be accessible"
        assert (
            grpc_response.status_code != 404
        ), "gRPC-Web endpoint should be accessible"

        # They should not interfere with each other
        assert (
            grpc_response.status_code != 415
        ), "gRPC-Web should accept grpc-web content type"

    def test_grpc_web_with_grpc_headers(self, gateway_client: httpx.Client):
        """Test gRPC-Web plugin handles additional gRPC headers correctly."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "X-Grpc-Web": "1",
                "Grpc-Timeout": "30S",
                "Grpc-Accept-Encoding": "gzip",
            },
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Plugin should handle gRPC headers
        assert response.status_code != 400, "Should handle gRPC headers correctly"
        assert response.status_code != 404, "Route should be accessible"
        assert response.status_code != 415, "Content type should be accepted"

    def test_grpc_web_proto_file_accessibility(self, gateway_client: httpx.Client):
        """Test that the proto file configuration is working correctly."""
        # This test ensures that the proto file path is correct and accessible to Kong
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x04test",
        )

        # If proto file is inaccessible, Kong might return specific errors
        assert (
            response.status_code != 500
        ), "Should not have internal server error from missing proto"

        # Plugin should be able to process the request
        kong_processed = any(h.startswith("X-Kong-") for h in response.headers.keys())
        backend_unavailable = response.status_code in [502, 503]
        assert (
            kong_processed or backend_unavailable
        ), "Kong should process the request (proto file should be accessible)"

    def test_grpc_web_options_cors_support(self, gateway_client: httpx.Client):
        """Test that CORS OPTIONS requests work for gRPC-Web endpoints."""
        response = gateway_client.options(
            "/grpc/v1/registry",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Grpc-Web",
            },
        )

        # CORS should work for gRPC-Web endpoints
        assert response.status_code in [200, 204], "CORS OPTIONS should work"

        # Should allow gRPC-Web related headers
        if response.status_code in [200, 204]:
            response.headers.get("Access-Control-Allow-Headers", "")
            methods = response.headers.get("Access-Control-Allow-Methods", "")

            # Should allow POST method for gRPC-Web
            assert "POST" in methods or "*" in methods, "Should allow POST method"
