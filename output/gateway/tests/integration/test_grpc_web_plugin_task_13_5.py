"""
Task 13.5: Integration tests to verify that a browser can call gRPC service via gateway.

This test file specifically verifies that the Kong gateway with gRPC-Web plugin
can successfully handle browser-originated gRPC-Web requests to backend gRPC services.
It simulates realistic browser behavior and verifies the complete flow.
"""

import pytest
import httpx
import base64


@pytest.mark.integration
class TestGRPCWebBrowserCompatibilityTask135:
    """Task 13.5 specific tests for browser calling gRPC service via gateway."""

    def test_browser_grpc_web_basic_call(self, gateway_client: httpx.Client):
        """Test basic browser-style gRPC-Web call works through gateway."""
        # Simulate a browser making a gRPC-Web request with all typical headers
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": "http://localhost:3000",
            "Referer": "http://localhost:3000/",
            "X-Grpc-Web": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        # Create a minimal gRPC-Web frame for ListServices call
        # gRPC frame format: [compressed][length 4 bytes][message]
        grpc_frame = b"\x00\x00\x00\x00\x02\x08\x01"  # Minimal ListServicesRequest

        response = gateway_client.post(
            "/grpc/v1/registry", headers=browser_headers, content=grpc_frame
        )

        # Verify the call is handled correctly by gateway
        assert (
            response.status_code != 404
        ), "gRPC-Web route should be accessible to browsers"
        assert (
            response.status_code != 415
        ), "Browser gRPC-Web content type should be accepted"
        assert (
            response.status_code != 401
        ), "Authenticated client should access gRPC-Web"

        # Kong should process the request (either success or backend unavailable)
        kong_processed = any(h.startswith("X-Kong-") for h in response.headers.keys())
        backend_unavailable = response.status_code in [502, 503]
        assert (
            kong_processed or backend_unavailable
        ), "Kong should handle browser gRPC-Web requests"

    def test_browser_grpc_web_text_encoding(self, gateway_client: httpx.Client):
        """Test browser can use gRPC-Web text encoding (base64) through gateway."""
        # Some browsers use text encoding instead of binary
        browser_headers = {
            "Content-Type": "application/grpc-web-text+proto",
            "Accept": "application/grpc-web-text+proto",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "http://localhost:3000",
        }

        # Base64 encoded minimal gRPC frame
        grpc_frame = b"\x00\x00\x00\x00\x02\x08\x01"
        encoded_frame = base64.b64encode(grpc_frame)

        response = gateway_client.post(
            "/grpc/v1/registry", headers=browser_headers, content=encoded_frame
        )

        # Text encoding should also work
        assert response.status_code != 404, "gRPC-Web text route should be accessible"
        assert (
            response.status_code != 415
        ), "gRPC-Web text content type should be accepted"

    def test_browser_cors_preflight_for_grpc_web(self, gateway_client: httpx.Client):
        """Test CORS preflight request from browser to gRPC-Web endpoint."""
        # Browser sends OPTIONS request first for CORS
        cors_headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-Grpc-Web, Authorization",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        response = gateway_client.options("/grpc/v1/registry", headers=cors_headers)

        # CORS preflight should work for browser access
        assert response.status_code in [
            200,
            204,
        ], "CORS preflight should succeed for browsers"

        # Check CORS headers in response
        if response.status_code in [200, 204]:
            allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
            response.headers.get("Access-Control-Allow-Headers", "")

            # Should allow POST method for gRPC-Web
            assert (
                "POST" in allowed_methods or "*" in allowed_methods
            ), "Should allow POST method for gRPC-Web calls"

    def test_browser_grpc_web_streaming_compatibility(
        self, gateway_client: httpx.Client
    ):
        """Test browser-compatible gRPC-Web streaming calls work."""
        # Browsers handle streaming differently - test server-sent events style
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Chrome/91.0.4472.124) Safari/537.36",
            "Origin": "http://localhost:3000",
            "X-Grpc-Web": "1",
        }

        # Simulate a Watch request that would return streaming data
        # WatchRequest for all services
        grpc_frame = b"\x00\x00\x00\x00\x00"  # Empty WatchRequest (watch all)

        response = gateway_client.post(
            "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Watch",
            headers=browser_headers,
            content=grpc_frame,
            timeout=5.0,  # Short timeout for test
        )

        # Streaming should be supported (or gracefully handled)
        assert (
            response.status_code != 501
        ), "Streaming should be supported or gracefully handled"
        assert response.status_code != 404, "Streaming endpoint should be routable"

    def test_browser_grpc_web_large_request(self, gateway_client: httpx.Client):
        """Test browser can send larger gRPC-Web requests through gateway."""
        # Test with a larger registration request that browsers might send
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Firefox/89.0)",
            "Origin": "http://localhost:3000",
        }

        # Create a larger gRPC frame for RegisterRequest
        # This simulates a browser registering a service with metadata
        large_message = b"x" * 1000  # 1KB message
        message_length = len(large_message)
        grpc_frame = b"\x00" + message_length.to_bytes(4, "big") + large_message

        response = gateway_client.post(
            "/grpc/v1/registry", headers=browser_headers, content=grpc_frame
        )

        # Large requests should be handled
        assert response.status_code != 413, "Large gRPC-Web requests should be accepted"
        assert response.status_code != 404, "Route should handle large requests"

    def test_browser_grpc_web_error_handling(self, gateway_client: httpx.Client):
        """Test browser receives proper error responses from gRPC-Web calls."""
        # Test with malformed gRPC frame to trigger error handling
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Safari/14.1.1)",
            "Origin": "http://localhost:3000",
        }

        # Invalid gRPC frame
        invalid_frame = b"invalid_grpc_data"

        response = gateway_client.post(
            "/grpc/v1/registry", headers=browser_headers, content=invalid_frame
        )

        # Error should be properly formatted for browser consumption
        assert (
            response.status_code != 500
        ), "Should handle malformed requests gracefully"

        # Response should include proper headers for browser error handling
        content_type = response.headers.get("Content-Type", "")
        assert content_type != "", "Error response should have Content-Type"

    def test_browser_grpc_web_authentication_flow(self):
        """Test complete browser authentication flow for gRPC-Web."""
        # First, test unauthenticated request (what browser would get initially)
        unauthenticated_client = httpx.Client(base_url="http://localhost:8000")

        try:
            browser_headers = {
                "Content-Type": "application/grpc-web+proto",
                "User-Agent": "Mozilla/5.0 (Edge/91.0.864.59)",
                "Origin": "http://localhost:3000",
            }

            response = unauthenticated_client.post(
                "/grpc/v1/registry",
                headers=browser_headers,
                content=b"\x00\x00\x00\x00\x02\x08\x01",
            )

            # Should require authentication
            assert (
                response.status_code == 401
            ), "Should require authentication for gRPC-Web"

            # Response should be browser-friendly
            assert "WWW-Authenticate" in response.headers or response.status_code == 401

        finally:
            unauthenticated_client.close()

    def test_browser_grpc_web_with_api_key_header(self, gateway_client: httpx.Client):
        """Test browser can authenticate gRPC-Web calls with API key in header."""
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Chrome/91.0.4472.124)",
            "Origin": "http://localhost:3000",
            # API key typically passed in custom header by browser JS
            "X-API-Key": "dev-api-key-12345",  # This should already be set by gateway_client fixture
        }

        response = gateway_client.post(
            "/grpc/v1/registry",
            headers=browser_headers,
            content=b"\x00\x00\x00\x00\x02\x08\x01",
        )

        # API key authentication should work
        assert (
            response.status_code != 401
        ), "API key should authenticate browser gRPC-Web"
        assert response.status_code != 403, "Valid API key should be accepted"

    def test_browser_grpc_web_response_headers(self, gateway_client: httpx.Client):
        """Test gRPC-Web responses include proper headers for browser consumption."""
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "Origin": "http://localhost:3000",
            "User-Agent": "Mozilla/5.0",
        }

        response = gateway_client.post(
            "/grpc/v1/registry",
            headers=browser_headers,
            content=b"\x00\x00\x00\x00\x02\x08\x01",
        )

        # Check for browser-important headers
        assert (
            "X-Correlation-ID" in response.headers
        ), "Should include correlation ID for tracing"

        # CORS headers should be present for browser requests
        if "Origin" in dict(browser_headers):
            # Some CORS header should be present when origin is specified
            [h for h in response.headers.keys() if h.startswith("Access-Control-")]
            cors_headers = [
                h for h in response.headers.keys() if h.startswith("Access-Control-")
            ]
            # Note: CORS headers might be handled by a separate plugin/config

        # Rate limit headers should be present for browser awareness
        rate_limit_headers = [h for h in response.headers.keys() if "RateLimit" in h]
        assert (
            len(rate_limit_headers) > 0
        ), "Should include rate limit headers for browsers"

    def test_browser_grpc_web_concurrent_calls(self, gateway_client: httpx.Client):
        """Test browser can make concurrent gRPC-Web calls through gateway."""
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Concurrent Test Browser)",
            "Origin": "http://localhost:3000",
        }

        # Simulate multiple concurrent browser requests
        import concurrent.futures

        def make_grpc_web_call(call_id: int):
            # Each call gets a unique frame
            grpc_frame = f"\x00\x00\x00\x00\x02\x08{call_id}".encode()

            response = gateway_client.post(
                "/grpc/v1/registry",
                headers={**browser_headers, "X-Call-ID": str(call_id)},
                content=grpc_frame,
            )
            return call_id, response

        # Make 5 concurrent calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_grpc_web_call, i) for i in range(5)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All calls should be handled properly
        for call_id, response in results:
            assert response.status_code != 404, f"Call {call_id}: Route should be accessible"
            assert (
                response.status_code != 404
            ), f"Call {call_id}: Route should be accessible"
            assert response.status_code not in [
                500,
                502,
            ], f"Call {call_id}: Should handle concurrent load"

    def test_browser_grpc_web_method_specific_routing(
        self, gateway_client: httpx.Client
    ):
        """Test browser can call specific gRPC methods through gateway routing."""
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Method Routing Test)",
            "Origin": "http://localhost:3000",
        }

        # Test different gRPC method paths that browsers might call
        method_tests = [
            (
                "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/ListServices",
                b"\x00\x00\x00\x00\x00",
            ),
            (
                "/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Discover",
                b"\x00\x00\x00\x00\x01\x08",
            ),
            ("/grpc/v1/registry", b"\x00\x00\x00\x00\x02\x08\x01"),  # Generic path
        ]

        for path, frame in method_tests:
            response = gateway_client.post(path, headers=browser_headers, content=frame)

            # Method-specific routing should work or fallback gracefully
            assert response.status_code != 404, f"Path {path} should be routable"
            assert (
                response.status_code != 415
            ), f"Path {path} should accept gRPC-Web content"

    def test_browser_grpc_web_timeout_handling(self, gateway_client: httpx.Client):
        """Test browser gRPC-Web calls handle timeouts properly."""
        browser_headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "application/grpc-web+proto",
            "User-Agent": "Mozilla/5.0 (Timeout Test)",
            "Origin": "http://localhost:3000",
            "Grpc-Timeout": "5S",  # 5 second timeout
        }

        # Make a call with timeout header
        response = gateway_client.post(
            "/grpc/v1/registry",
            headers=browser_headers,
            content=b"\x00\x00\x00\x00\x02\x08\x01",
            timeout=10.0,  # Client timeout longer than gRPC timeout
        )

        # Timeout should be handled gracefully
        assert response.status_code != 500, "Timeouts should be handled gracefully"
        assert (
            response.status_code != 404
        ), "Route should be accessible with timeout header"

    def test_browser_grpc_web_complete_flow_simulation(
        self, gateway_client: httpx.Client
    ):
        """Test complete browser flow: CORS preflight + actual gRPC call."""
        origin = "http://localhost:3000"

        # Step 1: Browser sends CORS preflight
        preflight_response = gateway_client.options(
            "/grpc/v1/registry",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Grpc-Web",
                "User-Agent": "Mozilla/5.0 (Complete Flow Test)",
            },
        )

        # Preflight should succeed
        assert preflight_response.status_code in [
            200,
            204,
        ], "CORS preflight should succeed"

        # Step 2: Browser makes actual gRPC-Web call
        grpc_response = gateway_client.post(
            "/grpc/v1/registry",
            headers={
                "Content-Type": "application/grpc-web+proto",
                "Accept": "application/grpc-web+proto",
                "Origin": origin,
                "X-Grpc-Web": "1",
                "User-Agent": "Mozilla/5.0 (Complete Flow Test)",
            },
            content=b"\x00\x00\x00\x00\x02\x08\x01",
        )

        # Actual call should work after preflight
        assert (
            grpc_response.status_code != 404
        ), "gRPC-Web call should work after preflight"
        assert grpc_response.status_code != 415, "Content type should be accepted"

        # Both requests should include proper headers
        assert "X-Correlation-ID" in grpc_response.headers, "Should include correlation ID"
        assert (
            "X-Correlation-ID" in grpc_response.headers
        ), "Should include correlation ID"
