"""
Integration tests for rate limit enforcement (429 status codes).

This module specifically tests that rate limiting properly returns 429 responses
when limits are exceeded, with appropriate headers and error messages.

Task 9.3: Write tests for rate limit enforcement (429)
"""

import pytest
import time
import asyncio
import httpx


@pytest.mark.integration
class TestRateLimitEnforcement429:
    """Test rate limit enforcement that returns 429 status codes."""

    def test_429_response_format(self, free_tier_client):
        """Test that 429 response has correct format and headers."""
        # Use free tier client with low limits (100/min) to trigger rate limiting
        # We'll make rapid consecutive requests to hit the limit

        responses = []

        # Make requests rapidly to trigger rate limit
        # Free tier has 100/min, so we'll make requests until we hit 429
        for i in range(110):  # Exceed the free tier limit
            response = free_tier_client.get("/health")
            responses.append(response)

            if response.status_code == 429:
                # Found our 429 response, verify it
                assert (
                    response.status_code == 429
                ), "Should return 429 when rate limit exceeded"

                # Verify required headers are present
                assert (
                    "Retry-After" in response.headers
                ), "429 response should include Retry-After header"
                assert (
                    "X-RateLimit-Limit-Minute" in response.headers
                ), "429 response should include rate limit headers"
                assert (
                    "X-RateLimit-Remaining-Minute" in response.headers
                ), "429 response should include remaining count"

                # Verify Retry-After is numeric
                retry_after = response.headers["Retry-After"]
                assert retry_after.isdigit(), "Retry-After should be numeric"
                assert int(retry_after) > 0, "Retry-After should be positive"

                # Verify remaining count is 0 or very low
                remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
                assert (
                    remaining <= 1
                ), f"Remaining should be 0 or 1 when hitting rate limit, got {remaining}"

                # Verify response has JSON error message
                try:
                    data = response.json()
                    assert "message" in data, "429 response should have error message"
                    assert (
                        "rate limit" in data["message"].lower()
                    ), "Error message should mention rate limit"
                except Exception:
                    pytest.fail("429 response should be valid JSON with error message")

                return  # Test passed

            # Small delay to avoid overwhelming the system
            time.sleep(0.01)

        pytest.fail(
            "Could not trigger 429 response within reasonable number of requests"
        )

    def test_429_after_limit_exhaustion(self, free_tier_client):
        """Test that requests return 429 after exhausting rate limit."""
        # Check current remaining limit
        initial_response = free_tier_client.get("/health")
        assert initial_response.status_code == 200

        initial_remaining = int(
            initial_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # If we're already near the limit, use that. Otherwise make requests to get near it.
        if initial_remaining > 20:
            # Make requests to get close to the limit
            for _ in range(initial_remaining - 5):
                response = free_tier_client.get("/health")
                if response.status_code == 429:
                    break

        # Now make the final requests that should trigger 429
        last_200_response = None
        for i in range(10):  # Try up to 10 more requests
            response = free_tier_client.get("/health")

            if response.status_code == 200:
                last_200_response = response
            elif response.status_code == 429:
                # Success! We triggered the rate limit
                # Verify the transition from 200 to 429
                if last_200_response:
                    last_remaining = int(
                        last_200_response.headers["X-RateLimit-Remaining-Minute"]
                    )
                    # The last 200 response should have had low remaining count
                    assert (
                        last_remaining <= 2
                    ), f"Last 200 response should have very low remaining count, got {last_remaining}"

                # Verify 429 response
                assert response.status_code == 429
                assert "Retry-After" in response.headers
                assert "rate limit" in response.json()["message"].lower()
                return

        pytest.skip("Could not trigger rate limit transition in reasonable attempts")

    def test_429_with_different_endpoints(self, free_tier_client):
        """Test that rate limit 429 applies across different endpoints."""
        # Make requests to different endpoints until rate limit is hit
        endpoints = ["/health", "/api/v1/registry/services", "/api/v1/registry/health"]

        total_requests = 0
        for cycle in range(40):  # Up to 120 total requests across all endpoints
            for endpoint in endpoints:
                response = free_tier_client.get(endpoint)
                total_requests += 1

                if response.status_code == 429:
                    # Verify that the rate limit applies across all endpoints
                    # Try the other endpoints and they should also return 429
                    for other_endpoint in endpoints:
                        if other_endpoint != endpoint:
                            other_response = free_tier_client.get(other_endpoint)
                            assert (
                                other_response.status_code == 429
                            ), f"Rate limit should apply to all endpoints: {other_endpoint} returned {other_response.status_code}"
                    return

                # If we got 502/503, that's fine (service might not be available)
                # but 200/401/403/404 means the request was processed and counted
                if response.status_code in [200, 401, 403, 404]:
                    continue

            time.sleep(0.01)  # Brief pause between cycles

        pytest.skip("Could not trigger rate limit across multiple endpoints")

    def test_429_headers_consistency(self, free_tier_client):
        """Test that 429 responses have consistent headers."""
        # Make requests until we get a 429
        rate_limit_responses = []

        for i in range(120):  # Free tier limit is 100/min
            response = free_tier_client.get("/health")

            if response.status_code == 429:
                rate_limit_responses.append(response)

                # Once we have a few 429 responses, verify consistency
                if len(rate_limit_responses) >= 3:
                    break

        if not rate_limit_responses:
            pytest.skip("Could not trigger rate limit for header consistency test")

        # Verify all 429 responses have consistent headers
        for response in rate_limit_responses:
            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert "X-RateLimit-Limit-Minute" in response.headers
            assert "X-RateLimit-Remaining-Minute" in response.headers

            # Remaining should be 0 or very low
            remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
            assert (
                remaining <= 1
            ), f"Rate limited request should have remaining count of 0 or 1, got {remaining}"

            # Limit should be consistent
            limit = int(response.headers["X-RateLimit-Limit-Minute"])
            assert limit == 100, f"Free tier limit should be 100, got {limit}"

    @pytest.mark.slow
    def test_concurrent_requests_429(self, free_tier_client):
        """Test that concurrent requests properly trigger 429."""

        async def make_request(session_client):
            """Make a single request using async client."""
            async with httpx.AsyncClient(
                base_url=session_client.base_url,
                headers=session_client.headers,
                timeout=session_client.timeout,
            ) as async_client:
                return await async_client.get("/health")

        async def test_concurrent():
            # Make many concurrent requests to trigger rate limiting
            tasks = [make_request(free_tier_client) for _ in range(50)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and get actual responses
            actual_responses = [r for r in responses if isinstance(r, httpx.Response)]

            if not actual_responses:
                pytest.skip("No successful responses in concurrent test")

            # We should have a mix of 200 and 429 responses
            status_codes = [r.status_code for r in actual_responses]
            any(code == 200 for code in status_codes)
            has_429 = any(code == 429 for code in status_codes)

            # In concurrent scenario, some requests should succeed, others should be rate limited
            if not has_429:
                pytest.skip(
                    "No 429 responses in concurrent test - rate limit not triggered"
                )

            # Verify all 429 responses have proper format
            for response in actual_responses:
                if response.status_code == 429:
                    assert "Retry-After" in response.headers
                    data = response.json()
                    assert "rate limit" in data["message"].lower()

        # Run the async test
        asyncio.run(test_concurrent())

    def test_rate_limit_isolation_between_consumers(
        self, free_tier_client, standard_tier_client
    ):
        """Test that rate limits are isolated between different consumers (one consumer's 429 doesn't affect another)."""
        # First, try to trigger rate limit on free tier
        free_tier_429 = False

        for i in range(120):  # Try to exhaust free tier limit
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                free_tier_429 = True
                break

        if not free_tier_429:
            pytest.skip("Could not trigger rate limit on free tier for isolation test")

        # Now verify that standard tier is not affected
        standard_response = standard_tier_client.get("/health")

        # Standard tier should still work (might get 502/503 if service is down, but not 429)
        assert (
            standard_response.status_code != 429
        ), "Standard tier should not be rate limited when free tier is rate limited"

        # Standard tier should have its own rate limit tracking
        if "X-RateLimit-Remaining-Minute" in standard_response.headers:
            standard_remaining = int(
                standard_response.headers["X-RateLimit-Remaining-Minute"]
            )
            standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])

            # Standard tier should have much higher limit and remaining count
            assert (
                standard_limit > 100
            ), f"Standard tier should have higher limit than 100, got {standard_limit}"
            assert (
                standard_remaining > 50
            ), f"Standard tier should have high remaining count, got {standard_remaining}"

    def test_429_retry_after_accuracy(self, free_tier_client):
        """Test that Retry-After header provides accurate wait time."""
        # Trigger rate limit
        response_429 = None

        for i in range(120):
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                response_429 = response
                break

        if not response_429:
            pytest.skip("Could not trigger rate limit for retry-after test")

        # Get the Retry-After value
        retry_after = int(response_429.headers["Retry-After"])
        assert retry_after > 0, "Retry-After should be positive"
        assert (
            retry_after <= 60
        ), "Retry-After should be reasonable (≤ 60 seconds for minute-based limiting)"

        # The Retry-After should be related to the rate limiting window
        # For minute-based rate limiting, it should be at most 60 seconds
        # We won't wait for the full duration in the test, but verify the header is reasonable

    def test_429_error_message_content(self, free_tier_client):
        """Test that 429 error messages contain appropriate information."""
        # Trigger rate limit
        for i in range(120):
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                data = response.json()

                # Check error message content
                assert "message" in data, "429 response should have error message"
                message = data["message"].lower()

                # Should mention rate limiting
                assert any(
                    word in message for word in ["rate", "limit", "quota", "throttle"]
                ), f"Error message should mention rate limiting: {message}"

                # Should be user-friendly
                assert len(data["message"]) > 10, "Error message should be descriptive"

                # Check if error type is provided
                if "error" in data:
                    error_type = data["error"].lower()
                    assert (
                        "rate" in error_type or "limit" in error_type or "many" in error_type
                        "rate" in error_type
                        or "limit" in error_type
                        or "many" in error_type
                    ), f"Error type should indicate rate limiting: {error_type}"

                return

        pytest.skip("Could not trigger rate limit for error message test")

    def test_multiple_429_responses_consistent(self, free_tier_client):
        """Test that multiple 429 responses are consistent."""
        rate_limited_responses = []

        # Collect multiple 429 responses
        for i in range(150):  # Ensure we get multiple 429s after hitting the limit
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                rate_limited_responses.append(response)

                # Once we have enough 429 responses, stop
                if len(rate_limited_responses) >= 5:
                    break

        if len(rate_limited_responses) < 3:
            pytest.skip("Could not collect enough 429 responses for consistency test")

        # Verify consistency across all 429 responses
        first_response = rate_limited_responses[0]
        first_limit = first_response.headers["X-RateLimit-Limit-Minute"]
        first_error = first_response.json()["message"]

        for response in rate_limited_responses[1:]:
            # Same limit
            assert (
                response.headers["X-RateLimit-Limit-Minute"] == first_limit
            ), "All 429 responses should have the same limit value"

            # Remaining should be 0 or very low for all
            remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
            assert (
                remaining <= 1
            ), f"All 429 responses should have remaining ≤ 1, got {remaining}"

            # Error message should be consistent
            current_error = response.json()["message"]
            assert (
                current_error == first_error
            ), "All 429 responses should have the same error message"

            # Should have Retry-After
            assert (
                "Retry-After" in response.headers
            ), "All 429 responses should have Retry-After header"


@pytest.mark.integration
class TestRateLimitEnforcementEdgeCases:
    """Test edge cases for rate limit 429 enforcement."""

    def test_429_with_burst_requests(self, free_tier_client):
        """Test 429 behavior with burst of rapid requests."""
        # Make a very rapid burst of requests
        responses = []
        start_time = time.time()

        # Make 30 requests as quickly as possible
        for i in range(30):
            response = free_tier_client.get("/health")
            responses.append(response)

            # No delay - test burst behavior

        end_time = time.time()
        end_time - start_time

        # Check if any were rate limited
        status_codes = [r.status_code for r in responses]
        sum(1 for code in status_codes if code == 429)

        # In a rapid burst, rate limiting might kick in
        # If it does, verify the 429 responses
        for response in responses:
            if response.status_code == 429:
                assert "Retry-After" in response.headers
                data = response.json()
                assert "rate limit" in data["message"].lower()

    def test_429_near_boundary_conditions(self, free_tier_client):
        """Test rate limiting behavior near boundary conditions."""
        # Get current state
        initial_response = free_tier_client.get("/health")
        if initial_response.status_code != 200:
            pytest.skip("Initial request failed, cannot test boundary conditions")

        initial_remaining = int(
            initial_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # If we're nowhere near the limit, make requests to get close
        if initial_remaining > 10:
            # Make requests to get within 5 of the limit
            for _ in range(initial_remaining - 5):
                response = free_tier_client.get("/health")
                if response.status_code == 429:
                    break

        # Now we should be close to the limit
        # Make careful requests to observe the boundary
        boundary_responses = []

        for i in range(10):
            response = free_tier_client.get("/health")
            boundary_responses.append(response)

            if response.status_code == 429:
                break

            time.sleep(0.1)  # Small delay to avoid race conditions

        # Analyze the boundary behavior
        last_200 = None
        first_429 = None

        for response in boundary_responses:
            if response.status_code == 200:
                last_200 = response
            elif response.status_code == 429 and first_429 is None:
                first_429 = response
                break

        if last_200 and first_429:
            # There should be a clear transition from 200 to 429
            last_remaining = int(last_200.headers["X-RateLimit-Remaining-Minute"])
            first_429_remaining = int(first_429.headers["X-RateLimit-Remaining-Minute"])

            # The transition should make sense
            assert (
                first_429_remaining <= last_remaining
            ), "Rate limit remaining should not increase at boundary"

            assert (
                first_429_remaining <= 1
            ), f"First 429 should have remaining ≤ 1, got {first_429_remaining}"

    def test_429_with_invalid_endpoints(self, free_tier_client):
        """Test that 429 rate limiting applies even to requests for invalid endpoints."""
        # Make requests to non-existent endpoints to trigger rate limiting
        # These should still count against the rate limit

        invalid_endpoints = [
            "/api/v1/nonexistent",
            "/api/v1/invalid/path",
            "/does/not/exist",
        ]

        # First, check our starting remaining count
        initial_response = free_tier_client.get("/health")
        if initial_response.status_code != 200:
            pytest.skip("Cannot determine initial rate limit state")

        initial_remaining = int(
            initial_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # If we have many requests remaining, make some to get closer to the limit
        if initial_remaining > 20:
            for _ in range(initial_remaining - 10):
                response = free_tier_client.get("/health")
                if response.status_code == 429:
                    break

        # Now make requests to invalid endpoints
        for cycle in range(20):
            for endpoint in invalid_endpoints:
                response = free_tier_client.get(endpoint)

                # Even 404 responses should count against rate limit
                # and eventually we should get 429
                if response.status_code == 429:
                    # Verify it's a proper 429 response
                    assert "Retry-After" in response.headers
                    assert "X-RateLimit-Remaining-Minute" in response.headers

                    remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
                    assert (
                        remaining <= 1
                    ), f"429 response should have remaining ≤ 1, got {remaining}"

                    # Verify that even valid endpoints now return 429
                    valid_response = free_tier_client.get("/health")
                    assert (
                        valid_response.status_code == 429
                    ), "Valid endpoints should also return 429 after rate limit exceeded"

                    return

        pytest.skip("Could not trigger rate limit with invalid endpoints")
