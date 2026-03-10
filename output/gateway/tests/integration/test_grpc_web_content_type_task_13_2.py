"""
Task 13.2: Tests for gRPC-Web content type handling.

This test file specifically verifies that the Kong gateway correctly handles
gRPC-Web content types as required by task 13.2 in the API gateway specification.
"""

import pytest
import httpx


@pytest.mark.integration
class TestGRPCWebContentTypeTask132:
    """Task 13.2 specific tests for gRPC-Web content type handling."""

    def test_grpc_web_proto_content_type_accepted(self, gateway_client: httpx.Client):
        """Test that application/grpc-web+proto content type is accepted."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x04test",  # Simple gRPC frame format
        )

        # Kong should accept the content type and route the request
        # (Response may vary based on backend availability, but should not be 415)
        assert response.status_code != 415, "gRPC-Web proto content type should be accepted"
        assert (
            response.status_code != 415
        ), "gRPC-Web proto content type should be accepted"
        assert "X-Kong-Proxy-Latency" in response.headers or response.status_code in [
            502,
            503,
        ]

    def test_grpc_web_text_content_type_accepted(self, gateway_client: httpx.Client):
        """Test that application/grpc-web-text+proto content type is accepted."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web-text+proto"},
            content=b"AAAAAAQOFSRM",  # Base64-encoded gRPC frame
        )

        # Kong should accept the content type and route the request
        assert response.status_code != 415, "gRPC-Web text content type should be accepted"
        assert (
            response.status_code != 415
        ), "gRPC-Web text content type should be accepted"
        assert "X-Kong-Proxy-Latency" in response.headers or response.status_code in [
            502,
            503,
        ]

    def test_grpc_web_content_types_comparison(self, gateway_client: httpx.Client):
        """Test both gRPC-Web content types work equally."""
        content_types = [
            "application/grpc-web+proto",
            "application/grpc-web-text+proto",
        ]

        responses = []
        for content_type in content_types:
            response = gateway_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": content_type},
                content=b"test-content",
            )
            responses.append((content_type, response))

        # Both content types should be handled similarly (both accepted)
        for content_type, response in responses:
            assert response.status_code != 415, f"{content_type} should be accepted"
            # Should have Kong processing headers regardless of backend status
            has_kong_headers = any(
                header.startswith("X-Kong-") for header in response.headers.keys()
            )
            assert has_kong_headers or response.status_code in [
                502,
                503,
            ], f"{content_type} should be processed by Kong"

    def test_grpc_web_vs_regular_http_content_type(self, gateway_client: httpx.Client):
        """Test gRPC-Web content types are handled differently from regular HTTP."""
        # Test regular JSON content type on gRPC-Web endpoint
        json_response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/json"},
            json={"test": "data"},
        )

        # Test gRPC-Web content type on same endpoint
        grpc_response = gateway_client.post(
            "/grpc/v1/registry",
            headers={"Content-Type": "application/grpc-web+proto"},
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Both should be routable but may be handled differently
        assert (
            json_response.status_code != 404
        ), "gRPC endpoint should accept JSON for testing"
        assert grpc_response.status_code != 404, "gRPC endpoint should accept gRPC-Web"
        assert (
            grpc_response.status_code != 415
        ), "gRPC-Web content type should be accepted"

    def test_grpc_web_content_type_with_specific_method(
        self, gateway_client: httpx.Client
    ):
        """Test gRPC-Web content type with specific gRPC method paths."""
        test_cases = [
            {
                "path": "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Register",
                "method": "Register",
            },
            {
                "path": "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Discover",
                "method": "Discover",
            },
            {
                "path": "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/ListServices",
                "method": "ListServices",
            },
        ]

        for test_case in test_cases:
            response = gateway_client.post(
                test_case["path"],
                headers={"Content-Type": "application/grpc-web+proto"},
                content=b"\x00\x00\x00\x00\x04test",
            )

            # Should accept content type and route to gRPC method
            assert (
                response.status_code != 415
            ), f"gRPC-Web content type should be accepted for {test_case['method']}"
            assert (
                response.status_code != 404
            ), f"gRPC method {test_case['method']} should be routable"

    def test_grpc_web_content_type_with_grpc_headers(
        self, gateway_client: httpx.Client
    ):
        """Test gRPC-Web content type with additional gRPC headers."""
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "X-Grpc-Web": "1",
                "Grpc-Timeout": "10S",
                "Grpc-Accept-Encoding": "gzip",
            },
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Kong should handle gRPC-Web content type with additional headers
        assert (
            response.status_code != 415
        ), "gRPC-Web content type with headers should be accepted"
        # Kong should add its own processing headers
        kong_headers = [h for h in response.headers.keys() if h.startswith("X-Kong-")]
        backend_unavailable = response.status_code in [502, 503]
        assert (
            len(kong_headers) > 0 or backend_unavailable
        ), "Kong should process the request"

    def test_grpc_web_content_type_without_auth_returns_401(self):
        """Test that gRPC-Web requests without auth are rejected."""
        unauthorized_client = httpx.Client(base_url="http://localhost:8000")

        try:
            response = unauthorized_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": "application/grpc-web+proto"},
                content=b"\x00\x00\x00\x00\x04test",
            )

            # Should require authentication regardless of content type
            assert response.status_code == 401, "gRPC-Web requests should require authentication"
            assert (
                response.status_code == 401
            ), "gRPC-Web requests should require authentication"

        finally:
            unauthorized_client.close()

    def test_grpc_web_content_type_rate_limiting(self, free_tier_client: httpx.Client):
        """Test that rate limiting applies to gRPC-Web content types."""
        # Make a few requests to check rate limiting headers
        responses = []
        for i in range(3):
            response = free_tier_client.post(
                "/grpc/v1/registry",
                headers={"Content-Type": "application/grpc-web+proto"},
                content=f"\x00\x00\x00\x00\x04req{i}".encode(),
            )
            responses.append(response)

        # All responses should include rate limit headers
        for i, response in enumerate(responses):
            assert (
                response.status_code != 415
            ), f"Request {i}: gRPC-Web content type should be accepted"
            assert (
                "X-RateLimit-Limit-Minute" in response.headers
            ), f"Request {i}: Rate limit headers should be present"
            assert (
                "X-RateLimit-Remaining-Minute" in response.headers
            ), f"Request {i}: Rate limit remaining header should be present"

    def test_grpc_web_content_type_correlation_id(self, gateway_client: httpx.Client):
        """Test that correlation ID works with gRPC-Web content types."""
        custom_correlation_id = "test-grpc-web-correlation-12345"

        response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "X-Correlation-ID": custom_correlation_id,
            },
            content=b"\x00\x00\x00\x00\x04test",
        )

        # Kong should accept content type and preserve correlation ID
        assert response.status_code != 415, "gRPC-Web content type should be accepted"

        # Correlation ID should be echoed back
        echoed_id = response.headers.get("X-Correlation-ID")
        assert (
            echoed_id == custom_correlation_id
        ), f"Correlation ID should be echoed back: expected {custom_correlation_id}, got {echoed_id}"

    def test_grpc_web_content_type_options_preflight(
        self, gateway_client: httpx.Client
    ):
        """Test CORS OPTIONS preflight for gRPC-Web content types."""
        response = gateway_client.options(
            "/grpc/v1/registry",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Grpc-Web",
            },
        )

        # CORS preflight should be successful for gRPC-Web
        assert response.status_code in [
            200,
            204,
        ], "CORS preflight should succeed for gRPC-Web"

        # Should allow the requested headers
        if response.status_code in [200, 204]:
            allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
            content_type_allowed = (
                "Content-Type" in allowed_headers or "*" in allowed_headers
            )
            grpc_header_allowed = (
                "X-Grpc-Web" in allowed_headers or "*" in allowed_headers
            )

            assert content_type_allowed, "Content-Type header should be allowed"
            assert grpc_header_allowed, "X-Grpc-Web header should be allowed"
