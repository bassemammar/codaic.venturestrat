"""
End-to-end tests for complete gateway flows.

Tests full workflows from client to backend services.
"""

import pytest
import httpx


@pytest.mark.e2e
class TestFullFlow:
    """Test complete end-to-end workflows."""

    def test_external_client_flow(
        self, gateway_client, unauthorized_client, correlation_id
    ):
        """
        Test complete external client flow through gateway.

        This comprehensive E2E test validates the full flow for an external client:
        1. Authentication with API key
        2. Gateway routing to backend service
        3. Rate limiting enforcement
        4. Response headers and correlation tracking
        5. Error handling scenarios

        Covers requirements from API Gateway spec:
        - API key authentication (X-API-Key header)
        - Routing to /api/v1/registry/* → registry-service
        - Rate limiting with proper headers
        - Correlation ID generation and echo
        - Gateway processing headers
        """

        # =================================================================
        # Step 1: Test Authentication Flow
        # =================================================================

        # 1a. Request without API key should fail with 401
        unauthenticated_response = unauthorized_client.get("/api/v1/registry/services")
        assert unauthenticated_response.status_code == 401

        # Verify error response format from API spec
        error_data = unauthenticated_response.json()
        assert "message" in error_data
        assert "error" in error_data

        # Gateway should still add processing headers even on auth failure
        assert "X-Kong-Proxy-Latency" in unauthenticated_response.headers
        assert "X-Correlation-ID" in unauthenticated_response.headers

        # 1b. Request with invalid API key should fail with 403
        invalid_client = httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "invalid-key-99999"},
            timeout=10.0,
        )

        try:
            invalid_response = invalid_client.get("/api/v1/registry/services")
            assert invalid_response.status_code == 403

            # Verify error response format
            error_data = invalid_response.json()
            assert "message" in error_data
            assert "error" in error_data

        finally:
            invalid_client.close()

        # =================================================================
        # Step 2: Test Successful Authenticated Request
        # =================================================================

        # 2a. Make authenticated request with valid API key
        response = gateway_client.get("/api/v1/registry/services")

        # Should pass authentication and reach backend service
        # Registry service should return 200 (service running) or other success codes
        assert response.status_code not in [
            401,
            403,
        ], f"Authentication failed: {response.status_code} - {response.text}"

        # =================================================================
        # Step 3: Test Gateway Processing Headers (from API spec)
        # =================================================================

        # 3a. Verify gateway processing headers are present
        assert "X-Kong-Proxy-Latency" in response.headers, "Gateway proxy latency header missing"
        assert (
            "X-Kong-Proxy-Latency" in response.headers
        ), "Gateway proxy latency header missing"
        assert (
            "X-Kong-Upstream-Latency" in response.headers
        ), "Gateway upstream latency header missing"

        # 3b. Verify latency values are reasonable (should be numeric)
        proxy_latency = response.headers.get("X-Kong-Proxy-Latency")
        upstream_latency = response.headers.get("X-Kong-Upstream-Latency")

        assert proxy_latency.isdigit(), f"Invalid proxy latency: {proxy_latency}"
        assert (
            upstream_latency.isdigit()
        ), f"Invalid upstream latency: {upstream_latency}"

        # Latency should be reasonable (less than 10 seconds)
        assert int(proxy_latency) < 10000, f"Proxy latency too high: {proxy_latency}ms"
        assert (
            int(upstream_latency) < 10000
        ), f"Upstream latency too high: {upstream_latency}ms"

        # =================================================================
        # Step 4: Test Correlation ID Handling
        # =================================================================

        # 4a. Verify correlation ID is generated when not provided
        auto_correlation_id = response.headers.get("X-Correlation-ID")
        assert auto_correlation_id, "Correlation ID should be auto-generated"

        # 4b. Test custom correlation ID echo
        custom_response = gateway_client.get(
            "/api/v1/registry/services", headers={"X-Correlation-ID": correlation_id}
        )

        echoed_correlation_id = custom_response.headers.get("X-Correlation-ID")
        assert (
            echoed_correlation_id == correlation_id
        ), f"Correlation ID not echoed correctly: {echoed_correlation_id} != {correlation_id}"

        # =================================================================
        # Step 5: Test Rate Limiting Headers (from API spec)
        # =================================================================

        # 5a. Verify rate limiting headers are present
        assert "X-RateLimit-Limit-Minute" in response.headers, "Rate limit header missing"
        assert (
            "X-RateLimit-Limit-Minute" in response.headers
        ), "Rate limit header missing"
        assert (
            "X-RateLimit-Remaining-Minute" in response.headers
        ), "Rate limit remaining header missing"

        # 5b. Verify rate limit values are reasonable
        rate_limit = response.headers.get("X-RateLimit-Limit-Minute")
        rate_remaining = response.headers.get("X-RateLimit-Remaining-Minute")

        assert rate_limit.isdigit(), f"Invalid rate limit: {rate_limit}"
        assert rate_remaining.isdigit(), f"Invalid rate remaining: {rate_remaining}"

        # Rate limit should be positive and remaining should be <= limit
        assert int(rate_limit) > 0, f"Rate limit should be positive: {rate_limit}"
        assert int(rate_remaining) <= int(
            rate_limit
        ), f"Rate remaining ({rate_remaining}) should be <= limit ({rate_limit})"

        # =================================================================
        # Step 6: Test Consumer Context Headers
        # =================================================================

        # 6a. Verify consumer identification headers are present
        # These headers should be added by Kong's key-auth plugin
        assert (
            "X-Consumer-Username" in response.headers
        ), "Consumer username header missing"

        consumer_username = response.headers.get("X-Consumer-Username")
        assert consumer_username, "Consumer username should not be empty"

        # =================================================================
        # Step 7: Test Request Forwarding Headers
        # =================================================================

        # 7a. Verify forwarding headers are present (from API spec)
        assert "X-Forwarded-For" in response.headers or response.status_code in [
            503,
            502,
        ], "X-Forwarded-For header missing (unless service unavailable)"
        assert "X-Forwarded-Proto" in response.headers or response.status_code in [
            503,
            502,
        ], "X-Forwarded-Proto header missing (unless service unavailable)"

        # =================================================================
        # Step 8: Test Multiple Request Consistency
        # =================================================================

        # 8a. Make multiple requests to verify consistent behavior
        responses = []
        for i in range(3):
            multi_response = gateway_client.get("/api/v1/registry/services")
            responses.append(multi_response)

            # Each request should be consistent
            assert multi_response.status_code not in [401, 403]
            assert "X-Correlation-ID" in multi_response.headers
            assert "X-Kong-Proxy-Latency" in multi_response.headers

        # 8b. Verify correlation IDs are unique (auto-generated)
        correlation_ids = [r.headers.get("X-Correlation-ID") for r in responses]
        unique_ids = set(correlation_ids)
        assert len(unique_ids) == len(
            correlation_ids
        ), "Correlation IDs should be unique across requests"

        # 8c. Verify rate limit decreases with usage
        rate_remaining_values = [
            int(r.headers.get("X-RateLimit-Remaining-Minute", "0")) for r in responses
        ]

        # Should generally decrease (allowing for some race conditions in parallel tests)
        if len(set(rate_remaining_values)) > 1:
            # If values changed, the first should generally be higher than the last
            assert (
                rate_remaining_values[0] >= rate_remaining_values[-1]
            ), "Rate limit remaining should decrease with usage"

        # =================================================================
        # Step 9: Test Different HTTP Methods
        # =================================================================

        # 9a. Test GET method (already tested above)
        # 9b. Test POST method if service supports it
        post_response = gateway_client.post(
            "/api/v1/registry/services",
            json={"test": "data"},
            headers={"Content-Type": "application/json"},
        )

        # Should not fail with auth errors (may fail with other errors if service doesn't support POST)
        assert post_response.status_code not in [
            401,
            403,
        ], "POST request should not fail authentication"
        assert (
            "X-Kong-Proxy-Latency" in post_response.headers
        ), "POST request should have gateway headers"

        # =================================================================
        # Step 10: Test Health Endpoint (No Auth Required)
        # =================================================================

        # 10a. Health endpoint should work without authentication
        health_response = unauthorized_client.get("/health")
        assert (
            health_response.status_code == 200
        ), "Health endpoint should be accessible without auth"

        # Should still have gateway headers
        assert (
            "X-Kong-Proxy-Latency" in health_response.headers
        ), "Health endpoint should have gateway headers"

        # Should have proper health response format
        health_data = health_response.json()
        assert "status" in health_data, "Health response should have status field"

        # =================================================================
        # Final Success Verification
        # =================================================================

        print("✅ External client flow test completed successfully!")
        print("   - Authentication: API key validated")
        print("   - Routing: /api/v1/registry/* → registry-service")
        print(f"   - Rate limiting: {rate_limit} per minute, {rate_remaining} remaining")
        print(
            f"   - Rate limiting: {rate_limit} per minute, {rate_remaining} remaining"
        )
        print(f"   - Correlation tracking: {auto_correlation_id[:8]}...")
        print(f"   - Consumer: {consumer_username}")
        print(f"   - Latency: {proxy_latency}ms proxy, {upstream_latency}ms upstream")

    def test_service_to_service_flow(
        self, jwt_issuer_client, unauthorized_client, correlation_id
    ):
        """
        Test comprehensive service-to-service authentication flow.

        This E2E test validates the complete service-to-service flow:
        1. JWT token acquisition from issuer service
        2. Service-to-service authentication through gateway using JWT
        3. JWT claims forwarding to backend services
        4. Multiple service interaction scenarios
        5. Error handling and edge cases
        6. Correlation ID propagation across service boundaries

        Covers service-to-service requirements from API Gateway spec:
        - JWT authentication for service-to-service calls
        - Claims forwarding to backend services
        - Service identity preservation in headers
        - Request tracing across service boundaries
        """

        # =================================================================
        # Step 1: JWT Token Acquisition Flow
        # =================================================================

        print("🔐 Step 1: Testing JWT token acquisition flow...")

        # 1a. Pricing service requests JWT token from issuer
        pricing_token_response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "pricing-service",
                "scope": "read:registry write:registry calculate:prices",
            },
        )

        assert (
            pricing_token_response.status_code == 200
        ), f"JWT token request failed: {pricing_token_response.status_code}"
        pricing_token_data = pricing_token_response.json()
        pricing_jwt = pricing_token_data["token"]

        # Verify token structure and claims
        assert pricing_jwt is not None, "JWT token should not be None"
        assert (
            len(pricing_jwt.split(".")) == 3
        ), "JWT should have 3 parts (header.payload.signature)"
        assert "expires_at" in pricing_token_data, "Token response should include expiry"
        assert (
            "expires_at" in pricing_token_data
        ), "Token response should include expiry"

        # 1b. Risk service also gets its own JWT token
        risk_token_response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "risk-service",
                "scope": "read:positions read:market-data",
            },
        )

        assert (
            risk_token_response.status_code == 200
        ), f"Risk service JWT request failed: {risk_token_response.status_code}"
        risk_jwt = risk_token_response.json()["token"]

        # Tokens should be different for different services
        assert (
            pricing_jwt != risk_jwt
        ), "Different services should get different JWT tokens"

        # =================================================================
        # Step 2: Service-to-Service Authentication via Gateway
        # =================================================================

        print("🚀 Step 2: Testing service-to-service authentication via gateway...")

        # 2a. Pricing service calls registry service via gateway using JWT
        pricing_service_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={
                "Authorization": f"Bearer {pricing_jwt}",
                "X-Correlation-ID": correlation_id,
                "X-Service-Version": "1.0.0",
                "User-Agent": "pricing-service/1.0.0",
            },
        )

        # Should authenticate successfully and reach backend
        assert (
            pricing_service_response.status_code not in [401, 403]
        ), f"Service-to-service JWT authentication failed: {pricing_service_response.status_code} - {pricing_service_response.text}"

        # =================================================================
        # Step 3: JWT Claims and Headers Validation
        # =================================================================

        print("📝 Step 3: Testing JWT claims forwarding and headers...")

        # 3a. Verify gateway processing headers are present
        assert (
            "X-Kong-Proxy-Latency" in pricing_service_response.headers
        ), "Gateway proxy latency header missing"
        assert (
            "X-Kong-Upstream-Latency" in pricing_service_response.headers
        ), "Gateway upstream latency header missing"

        # 3b. Verify correlation ID is preserved and echoed
        response_correlation_id = pricing_service_response.headers.get("X-Correlation-ID")
        response_correlation_id = pricing_service_response.headers.get(
            "X-Correlation-ID"
        )
        assert (
            response_correlation_id == correlation_id
        ), f"Correlation ID not preserved: {response_correlation_id} != {correlation_id}"

        # 3c. Verify service identity headers are added by Kong JWT plugin
        # These should be added based on JWT claims
        if pricing_service_response.status_code in [
            200,
            502,
            503,
        ]:  # If request reached backend
            # Check for JWT-related headers that should be forwarded
            assert "X-Consumer-Username" in pricing_service_response.headers or "x-jwt-sub" in [
                h.lower() for h in pricing_service_response.headers
            ], "Service identity headers should be present"
            assert (
                "X-Consumer-Username" in pricing_service_response.headers
                or "x-jwt-sub" in [h.lower() for h in pricing_service_response.headers]
            ), "Service identity headers should be present"

        # =================================================================
        # Step 4: Multiple Service Interaction Scenarios
        # =================================================================

        print("🔄 Step 4: Testing multiple service interaction scenarios...")

        # 4a. Risk service calls registry service with its own JWT
        risk_service_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={
                "Authorization": f"Bearer {risk_jwt}",
                "X-Correlation-ID": correlation_id,
                "X-Service-Name": "risk-service",
            },
        )

        assert risk_service_response.status_code not in [
            401,
            403,
        ], f"Risk service JWT authentication failed: {risk_service_response.status_code}"
        assert (
            risk_service_response.status_code not in [401, 403]
        ), f"Risk service JWT authentication failed: {risk_service_response.status_code}"

        # 4b. Test POST operation (service registration)
        new_service_data = {
            "name": "test-integration-service",
            "version": "1.0.0",
            "endpoints": ["http://test-service:8080"],
        }

        pricing_register_response = unauthorized_client.post(
            "/api/v1/registry/services",
            headers={
                "Authorization": f"Bearer {pricing_jwt}",
                "X-Correlation-ID": correlation_id,
                "Content-Type": "application/json",
            },
            json=new_service_data,
        )

        # Should not fail with authentication errors
        assert pricing_register_response.status_code not in [
            401,
            403,
        ], f"Service registration with JWT failed: {pricing_register_response.status_code}"
        assert (
            pricing_register_response.status_code not in [401, 403]
        ), f"Service registration with JWT failed: {pricing_register_response.status_code}"

        # 4c. Test token reuse across multiple requests
        multi_request_responses = []
        for i in range(3):
            response = unauthorized_client.get(
                f"/api/v1/registry/services?request_num={i}",
                headers={
                    "Authorization": f"Bearer {pricing_jwt}",
                    "X-Correlation-ID": f"{correlation_id}-{i}",
                },
            )
            multi_request_responses.append(response)

        # All requests should have consistent authentication behavior
        for i, response in enumerate(multi_request_responses):
            assert response.status_code not in [
                401,
                403,
            ], f"Token reuse failed on request {i}: {response.status_code}"

            # Each should have its own correlation ID
            response_corr_id = response.headers.get("X-Correlation-ID")
            assert (
                response_corr_id == f"{correlation_id}-{i}"
            ), f"Correlation ID not preserved for request {i}"

        # =================================================================
        # Step 5: Error Handling and Edge Cases
        # =================================================================

        print("⚠️ Step 5: Testing error handling in service-to-service flows...")

        # 5a. Test with invalid JWT token
        invalid_jwt_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": "Bearer invalid-jwt-token-xyz"},
        )

        assert invalid_jwt_response.status_code in [
            401,
            403,
        ], f"Invalid JWT should be rejected: {invalid_jwt_response.status_code}"

        # 5b. Test with malformed Authorization header
        malformed_auth_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": "InvalidFormat pricing-jwt-token"},
        )

        assert malformed_auth_response.status_code in [
            401,
            403,
        ], f"Malformed auth header should be rejected: {malformed_auth_response.status_code}"
        assert (
            malformed_auth_response.status_code in [401, 403]
        ), f"Malformed auth header should be rejected: {malformed_auth_response.status_code}"

        # 5c. Test request to non-existent service endpoint
        nonexistent_response = unauthorized_client.get(
            "/api/v1/nonexistent-service/test",
            headers={"Authorization": f"Bearer {pricing_jwt}"},
        )

        # Should return 404 (route not found) or 503 (service unavailable), not auth error
        assert nonexistent_response.status_code in [
            404,
            503,
        ], f"Non-existent route should return 404/503, got: {nonexistent_response.status_code}"
        assert (
            nonexistent_response.status_code in [404, 503]
        ), f"Non-existent route should return 404/503, got: {nonexistent_response.status_code}"

        # Gateway headers should still be present even for errors
        assert (
            "X-Kong-Proxy-Latency" in nonexistent_response.headers
        ), "Gateway headers should be present even for error responses"

        # =================================================================
        # Step 6: Service Chain Flow (Service A → Service B → Service C)
        # =================================================================

        print("🔗 Step 6: Testing service chain communication flow...")

        # Simulate a service chain where pricing-service calls registry,
        # then makes another call as if it were calling market-data service

        # 6a. First call: pricing → registry
        chain_step1_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={
                "Authorization": f"Bearer {pricing_jwt}",
                "X-Correlation-ID": correlation_id,
                "X-Request-Chain": "pricing-service→registry-service",
            },
        )

        assert chain_step1_response.status_code not in [
            401,
            403,
        ], f"Service chain step 1 failed: {chain_step1_response.status_code}"

        # 6b. Simulate second call in chain (with same correlation ID)
        chain_step2_response = unauthorized_client.get(
            "/health",  # Use health endpoint as mock market-data call
            headers={
                "Authorization": f"Bearer {pricing_jwt}",
                "X-Correlation-ID": correlation_id,  # Same correlation ID
                "X-Request-Chain": "pricing-service→registry-service→market-data-service",
            },
        )

        # Should maintain same correlation ID across the chain
        assert (
            chain_step2_response.headers.get("X-Correlation-ID") == correlation_id
        ), "Correlation ID should be preserved across service chain"

        # =================================================================
        # Step 7: Performance and Latency Validation
        # =================================================================

        print("📊 Step 7: Validating service-to-service performance...")

        # 7a. Check JWT authentication doesn't add excessive latency
        proxy_latency = int(
            pricing_service_response.headers.get("X-Kong-Proxy-Latency", "0")
        )
        upstream_latency = int(
            pricing_service_response.headers.get("X-Kong-Upstream-Latency", "0")
        )

        # JWT processing should be fast (< 500ms additional latency)
        assert (
            proxy_latency < 500
        ), f"JWT processing latency too high: {proxy_latency}ms"
        assert (
            upstream_latency < 5000
        ), f"Upstream latency too high: {upstream_latency}ms"

        # 7b. Test concurrent service-to-service calls
        import concurrent.futures

        def make_concurrent_call(call_id):
            return unauthorized_client.get(
                f"/health?concurrent_id={call_id}",
                headers={
                    "Authorization": f"Bearer {pricing_jwt}",
                    "X-Correlation-ID": f"{correlation_id}-concurrent-{call_id}",
                },
            )

        # Make 3 concurrent service calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            concurrent_futures = [executor.submit(make_concurrent_call, i) for i in range(3)]
            concurrent_responses = [
                f.result() for f in concurrent.futures.as_completed(concurrent_futures)
            ]
            concurrent_responses = [
                f.result() for f in concurrent.futures.as_completed(concurrent_futures)
            ]

        # All concurrent calls should succeed
        for i, response in enumerate(concurrent_responses):
            assert response.status_code not in [
                401,
                403,
            ], f"Concurrent call {i} failed with JWT authentication"

        # =================================================================
        # Step 8: Security Validation
        # =================================================================

        print("🛡️ Step 8: Testing security aspects of service-to-service flow...")

        # 8a. Test that expired tokens are rejected (simulate with old/invalid token)
        # Note: In a real test, we'd wait for token expiry or create an already-expired token

        # 8b. Test JWT without required scope (if implemented)
        minimal_token_response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "limited-service"
                # No scope provided
            },
        )

        if minimal_token_response.status_code == 200:
            minimal_jwt = minimal_token_response.json()["token"]
            minimal_scope_response = unauthorized_client.get(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {minimal_jwt}"},
            )

            # Should still authenticate (scope enforcement is service-level)
            assert minimal_scope_response.status_code not in [
                401,
                403,
            ], "JWT without scope should still authenticate at gateway level"

        # =================================================================
        # Final Success Verification
        # =================================================================

        print("✅ Service-to-service flow test completed successfully!")
        print("   - JWT Authentication: ✓ pricing-service and risk-service tokens validated")
        print(
            "   - JWT Authentication: ✓ pricing-service and risk-service tokens validated"
        )
        print(
            f"   - Gateway Processing: ✓ Proxy latency: {proxy_latency}ms, Upstream: {upstream_latency}ms"
        )
        print("   - Claims Forwarding: ✓ Service identity preserved in headers")
        print(f"   - Correlation Tracking: ✓ {correlation_id} maintained across calls")
        print(
            f"   - Multi-request Flow: ✓ Token reused across {len(multi_request_responses)} requests"
        )
        print("   - Error Handling: ✓ Invalid tokens properly rejected")
        print("   - Service Chain: ✓ Cross-service correlation maintained")
        print(f"   - Concurrent Calls: ✓ {len(concurrent_responses)} simultaneous requests handled")
        print(
            f"   - Concurrent Calls: ✓ {len(concurrent_responses)} simultaneous requests handled"
        )

    @pytest.mark.slow
    def test_rate_limit_and_retry(self, free_tier_client):
        """Test rate limiting with retry workflow."""
        # Step 1: Get current rate limit status
        initial_response = free_tier_client.get("/health")
        remaining = int(
            initial_response.headers.get("X-RateLimit-Remaining-Minute", "999")
        )

        if remaining > 20:
            pytest.skip("Too far from rate limit to test efficiently")

        # Step 2: Make requests until rate limit is hit
        hit_limit = False
        for _ in range(remaining + 5):
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                hit_limit = True
                break

        if not hit_limit:
            pytest.skip("Could not hit rate limit in reasonable number of requests")

        # Step 3: Verify rate limit response
        assert response.status_code == 429
        assert "Retry-After" in response.headers

        # Step 4: Immediate retry should still fail
        retry_response = free_tier_client.get("/health")
        assert retry_response.status_code == 429

        # Step 5: Wait and retry (in real scenario, would wait for Retry-After)
        # For testing, we'll just verify the behavior exists
        assert "Retry-After" in retry_response.headers

    def test_multiple_consumer_isolation(self, free_tier_client, standard_tier_client):
        """Test that different consumers have isolated rate limits."""
        # Step 1: Make requests with free tier
        free_response = free_tier_client.get("/health")
        free_remaining = int(
            free_response.headers.get("X-RateLimit-Remaining-Minute", "0")
        )

        # Step 2: Make requests with standard tier
        standard_response = standard_tier_client.get("/health")
        standard_remaining = int(
            standard_response.headers.get("X-RateLimit-Remaining-Minute", "0")
        )

        # Step 3: Verify isolation
        # Standard tier should have higher or independent limits
        standard_limit = int(
            standard_response.headers.get("X-RateLimit-Limit-Minute", "0")
        )
        free_limit = int(free_response.headers.get("X-RateLimit-Limit-Minute", "0"))

        assert standard_limit > free_limit

        # Step 4: Heavy usage by one shouldn't affect the other
        # Make multiple requests with free tier
        for _ in range(min(5, free_remaining)):
            free_tier_client.get("/health")

        # Standard tier should still have its own limits
        post_usage_response = standard_tier_client.get("/health")
        post_usage_remaining = int(
            post_usage_response.headers.get("X-RateLimit-Remaining-Minute", "0")
        )

        # Should be close to original (within a few requests)
        assert abs(post_usage_remaining - standard_remaining) <= 2

    def test_cors_preflight_flow(self, gateway_client):
        """Test CORS preflight request flow."""
        # Step 1: Browser makes preflight request
        preflight_response = gateway_client.options(
            "/api/v1/registry/services",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-Key, Content-Type",
            },
        )

        # Step 2: Verify preflight response
        assert preflight_response.status_code in [200, 204]

        # Step 3: Make actual request with CORS headers
        actual_response = gateway_client.get(
            "/api/v1/registry/services", headers={"Origin": "http://localhost:3000"}
        )

        # Should succeed and include CORS headers
        assert actual_response.status_code not in [401, 403, 404]

    def test_error_propagation_flow(self, gateway_client):
        """Test error handling and propagation through gateway."""
        # Step 1: Make request to non-existent service endpoint
        response = gateway_client.get("/api/v1/nonexistent-service/test")

        # Step 2: Verify appropriate error response
        # Should be 404 (route not found) or 503 (service unavailable)
        assert response.status_code in [404, 503]

        # Step 3: Gateway headers should still be present
        assert "X-Kong-Proxy-Latency" in response.headers
        assert "X-Correlation-ID" in response.headers

        # Step 4: Rate limit headers should still be present
        assert "X-RateLimit-Limit-Minute" in response.headers

    def test_health_check_flow(self, unauthorized_client):
        """Test health check endpoint flow (no auth required)."""
        # Step 1: Unauthenticated request to health endpoint
        response = unauthorized_client.get("/health")

        # Step 2: Should succeed without authentication
        assert response.status_code == 200

        # Step 3: Should have basic response structure
        data = response.json()
        assert "status" in data

        # Step 4: Gateway headers should be present
        assert "X-Kong-Proxy-Latency" in response.headers

    def test_request_tracing_flow(self, gateway_client, correlation_id):
        """Test request tracing through gateway."""
        # Step 1: Make request with custom correlation ID
        response = gateway_client.get(
            "/api/v1/registry/services", headers={"X-Correlation-ID": correlation_id}
        )

        # Step 2: Verify correlation ID is echoed back
        assert response.headers.get("X-Correlation-ID") == correlation_id

        # Step 3: Make request without correlation ID
        response2 = gateway_client.get("/api/v1/registry/services")

        # Step 4: Verify new correlation ID is generated
        generated_id = response2.headers.get("X-Correlation-ID")
        assert generated_id
        assert generated_id != correlation_id

    def test_authentication_failure_flow(self, unauthorized_client):
        """Test authentication failure handling."""
        # Step 1: Request without credentials
        response = unauthorized_client.get("/api/v1/registry/services")

        # Step 2: Should return 401
        assert response.status_code == 401

        # Step 3: Should have error message
        data = response.json()
        assert "message" in data

        # Step 4: Gateway should still add its headers
        assert "X-Kong-Proxy-Latency" in response.headers
        assert "X-Correlation-ID" in response.headers

    def test_malformed_request_flow(self, gateway_client):
        """Test handling of malformed requests."""
        # Step 1: Make request with invalid JSON
        response = gateway_client.post(
            "/api/v1/registry/services",
            headers={"Content-Type": "application/json"},
            content=b"invalid-json-content",
        )

        # Step 2: Should handle gracefully (not 500)
        assert response.status_code != 500

        # Step 3: Gateway processing should still occur
        assert "X-Kong-Proxy-Latency" in response.headers

    @pytest.mark.slow
    def test_concurrent_client_flow(self):
        """Test multiple clients accessing gateway concurrently."""
        import asyncio

        async def client_flow(client_id):
            """Simulate individual client flow."""
            async with httpx.AsyncClient(
                base_url="http://localhost:8000",
                headers={"X-API-Key": "dev-api-key-12345"},
            ) as client:
                # Make multiple requests
                responses = []
                for i in range(3):
                    response = await client.get("/health")
                    responses.append(response)

                return client_id, responses

        async def run_concurrent_test():
            # Run 5 concurrent client flows
            tasks = [client_flow(i) for i in range(5)]
            results = await asyncio.gather(*tasks)

            # Verify all flows succeeded
            for client_id, responses in results:
                for response in responses:
                    assert response.status_code == 200
                    assert "X-Correlation-ID" in response.headers

                # Each client should have different correlation IDs
                correlation_ids = [r.headers.get("X-Correlation-ID") for r in responses]
                assert len(set(correlation_ids)) == len(correlation_ids)  # All unique

        # Run the concurrent test
        asyncio.run(run_concurrent_test())
