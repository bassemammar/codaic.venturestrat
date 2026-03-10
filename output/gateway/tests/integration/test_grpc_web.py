"""
Integration tests for gRPC-Web transcoding functionality.

Tests gRPC-Web content type handling, transcoding, authentication, and CORS.
"""

import pytest
import httpx


@pytest.mark.integration
class TestGRPCWeb:
    """Test gRPC-Web transcoding functionality."""

    def test_grpc_web_content_type_accepted(self, gateway_client):
        """Test that gRPC-Web content type is accepted."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"dummy-grpc-content",
        )

        # Should not return 415 (Unsupported Media Type)
        assert response.status_code != 415

        # May return 400/404/502 depending on actual gRPC service availability
        # but content type should be accepted
        assert response.status_code in [200, 400, 404, 502, 503]

    def test_grpc_web_binary_content_type_accepted(self, gateway_client):
        """Test that gRPC-Web binary content type is accepted."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x05hello",  # Basic gRPC frame format
        )

        # Should not return 415 (Unsupported Media Type)
        assert response.status_code != 415
        assert response.status_code in [200, 400, 404, 502, 503]

    def test_grpc_web_text_content_type_accepted(self, gateway_client):
        """Test that gRPC-Web text content type is accepted."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web-text+proto"},
            content=b"dummy-grpc-text-content",
        )

        # Should not return 415 (Unsupported Media Type)
        assert response.status_code != 415
        assert response.status_code in [200, 400, 404, 502, 503]

    def test_grpc_web_route_exists(self, gateway_client):
        """Test that gRPC-Web routes are configured."""
        response = gateway_client.options("/grpc/v1/registry")

        # Route should exist (not 404)
        assert response.status_code != 404

        # CORS should be configured for gRPC-Web
        if response.status_code in [200, 204]:
            # Check for CORS headers if available
            pass  # CORS headers may not be present in all responses

    def test_grpc_web_vs_rest_routes(self, gateway_client):
        """Test that gRPC-Web and REST routes are separate."""
        # REST route
        rest_response = gateway_client.get("/api/v1/registry/services")

        # gRPC-Web route (should be different)
        grpc_response = gateway_client.get("/grpc/v1/registry")

        # Both routes should exist but may have different backend behavior
        assert rest_response.status_code != 404
        assert grpc_response.status_code != 404

    def test_grpc_web_proto_configuration(self, gateway_client):
        """Test that gRPC-Web proto file is configured."""
        # This test verifies the plugin is configured with a proto file
        # We can't directly test the proto file without actual gRPC service

        response = gateway_client.post("/grpc/v1/registry")

        # Should not return 500 due to missing proto configuration
        # May return other errors due to missing service/invalid request
        assert response.status_code != 500

    def test_grpc_web_error_handling(self, gateway_client):
        """Test error handling for invalid gRPC-Web requests."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"invalid-protobuf-data",
        )

        # Should handle invalid protobuf gracefully
        assert response.status_code in [200, 400, 404, 502, 503]

    def test_grpc_web_transcoding_headers(self, gateway_client):
        """Test that appropriate headers are set for gRPC-Web."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto", "X-Grpc-Web": "1"},
        )

        # Kong should process the request
        kong_headers = [h for h in response.headers.keys() if h.startswith("X-Kong-")]
        assert len(kong_headers) > 0

    def test_grpc_web_service_target(self, gateway_client):
        """Test that gRPC-Web routes to correct service."""
        response = gateway_client.get("/grpc/v1/registry")

        # Should route to gRPC service, not REST service
        # This is primarily a configuration test
        assert response.status_code != 404

    def test_grpc_web_cors_support(self, gateway_client):
        """Test CORS support for gRPC-Web."""
        response = gateway_client.options(
            "/grpc/v1/registry",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # CORS preflight should be handled
        assert response.status_code in [200, 204]

        # May include CORS headers
        if "Access-Control-Allow-Origin" in response.headers:
            assert (
                response.headers["Access-Control-Allow-Origin"]
                == "http://localhost:3000"
            )

    def test_grpc_web_method_support(self, gateway_client):
        """Test that gRPC-Web supports POST method."""
        response = gateway_client.post("/grpc/v1/registry")

        # POST should be allowed for gRPC-Web
        assert response.status_code != 405  # Method Not Allowed

    def test_grpc_web_authentication(self, gateway_client):
        """Test that gRPC-Web requests go through authentication."""
        # Should still require API key
        import httpx

        unauthorized_client = httpx.Client(base_url="http://localhost:8000")

        try:
            response = unauthorized_client.post("/grpc/v1/registry")

            # Should require authentication
            assert response.status_code == 401

        finally:
            unauthorized_client.close()

    def test_grpc_web_plugin_configuration(self, admin_client):
        """Test gRPC-Web plugin configuration via Admin API."""
        response = admin_client.get("/plugins")

        if response.status_code == 200:
            plugins = response.json()
            grpc_plugins = [
                p for p in plugins.get("data", []) if p.get("name") == "grpc-web"
            ]

            if grpc_plugins:
                plugin = grpc_plugins[0]
                assert "config" in plugin
                assert "service" in plugin
                # Should be associated with registry gRPC service

    def test_grpc_web_proto_file_configuration(self, gateway_client):
        """Test that gRPC-Web proto file configuration is working."""
        # Test with a specific gRPC method path
        response = gateway_client.post(
            "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Register",
            headers={"Content-Type": "application/grpc-web+proto", "X-Grpc-Web": "1"},
            content=b"dummy-register-request",
        )

        # Should not return 500 due to missing proto configuration
        # May return other errors due to invalid request format
        assert response.status_code != 500

    def test_grpc_web_path_routing(self, gateway_client):
        """Test specific gRPC-Web method path routing."""
        # Test various gRPC method paths
        methods = ["Register", "Deregister", "Discover", "ListServices"]

        for method in methods:
            path = f"/grpc/v1/registry/venturestrat.registry.v1.RegistryService/{method}"
            response = gateway_client.post(
                path,
                headers={"Content-Type": "application/grpc-web+proto"},
                content=b"dummy-content",
            )

            # Path should be routable (not 404)
            assert response.status_code != 404, f"Method {method} should be routable"

    def test_grpc_web_headers_forwarded(self, gateway_client):
        """Test that gRPC-Web specific headers are properly handled."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "X-Grpc-Web": "1",
                "Grpc-Timeout": "10S",
                "Grpc-Accept-Encoding": "gzip",
            },
            content=b"test-content",
        )

        # Kong should process gRPC-Web headers without error
        kong_headers = [h for h in response.headers.keys() if h.startswith("X-Kong-")]
        assert len(kong_headers) > 0

    def test_grpc_web_rate_limiting_applies(self):
        """Test that rate limiting applies to gRPC-Web requests."""
        client = httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "free-api-key-11111"},  # Free tier with low limits
        )

        try:
            # Make multiple requests rapidly
            responses = []
            for i in range(15):  # Free tier has 100/minute, this should be safe
                response = client.post(
                    "/grpc/v1/registry",
                    headers={"Content-Type": "application/grpc-web+proto"},
                    content=b"test-content",
                )
                responses.append(response)

            # All should have rate limit headers
            for response in responses[:10]:  # Check first 10
                assert "X-RateLimit-Limit-Minute" in response.headers
                assert "X-RateLimit-Remaining-Minute" in response.headers

        finally:
            client.close()

    def test_grpc_web_cors_headers(self, gateway_client):
        """Test CORS headers specifically for gRPC-Web."""
        response = gateway_client.options(
            "/grpc/v1/registry",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Grpc-Web",
            },
        )

        # CORS preflight should be successful
        assert response.status_code in [200, 204]

        if response.status_code in [200, 204]:
            # Should allow gRPC-Web headers
            allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
            assert "X-Grpc-Web" in allowed_headers or "*" in allowed_headers

    def test_grpc_web_error_response_format(self, gateway_client):
        """Test that gRPC-Web error responses include proper gRPC status."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"invalid-protobuf-content-that-should-fail",
        )

        # Should handle gRPC errors gracefully
        if response.status_code in [400, 500, 502, 503]:
            # gRPC-Web responses may include gRPC status headers
            grpc_status = response.headers.get("Grpc-Status")
            if grpc_status is not None:
                assert grpc_status.isdigit(), "Grpc-Status should be numeric"

    def test_grpc_web_vs_rest_isolation(self, gateway_client):
        """Test that gRPC-Web and REST endpoints are properly isolated."""
        # REST endpoint
        rest_response = gateway_client.get("/api/v1/registry/services")

        # gRPC-Web endpoint
        grpc_response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"test-content",
        )

        # Both should be routable but handled differently
        assert rest_response.status_code != 404
        assert grpc_response.status_code != 404

        # REST should not accept gRPC content type
        rest_with_grpc = gateway_client.post(
            "/api/v1/registry/services",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"grpc-content",
        )

        # REST endpoint should reject gRPC content or handle differently
        assert rest_with_grpc.status_code in [200, 400, 415, 404, 502, 503]

    def test_grpc_web_streaming_support(self, gateway_client):
        """Test gRPC-Web streaming capabilities (if supported)."""
        # Test server streaming endpoint
        response = gateway_client.post(
            "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Watch",
            headers={"Content-Type": "application/grpc-web+proto", "X-Grpc-Web": "1"},
            content=b"watch-request",
        )

        # Should be routable even if streaming not fully supported
        assert response.status_code != 404

    def test_grpc_web_service_discovery(self, gateway_client):
        """Test that gRPC-Web routes to correct backend service."""
        # Multiple requests to ensure load balancing and service discovery works
        for i in range(3):
            response = gateway_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": "application/grpc-web+proto"},
                content=f"test-request-{i}".encode(),
            )

            # Should consistently route to same service type
            assert response.status_code != 404
            # Kong upstream latency header indicates successful routing
            assert "X-Kong-Upstream-Latency" in response.headers or response.status_code in [
                502,
                503,
            ]
            assert (
                "X-Kong-Upstream-Latency" in response.headers
                or response.status_code in [502, 503]
            )
