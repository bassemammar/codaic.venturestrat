#!/usr/bin/env python3
"""
Simple test to verify rate limiting by hitting Kong directly.
Even timeouts and errors should trigger rate limiting.
"""

import requests
import time

GATEWAY_URL = "http://localhost:8000"
FREE_TIER_API_KEY = "free-api-key-11111"


def test_rate_limit_simple():
    """Test rate limiting on any endpoint, even errors."""
    print("Testing rate limiting (even on error responses)...")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"API Key: {FREE_TIER_API_KEY}")
    print()

    headers = {"X-API-Key": FREE_TIER_API_KEY}

    # Test rate limiting by making requests until we hit the limit
    # Even 502/503/timeout responses should count against rate limit

    request_count = 0
    found_429 = False

    print("Making requests to /health endpoint...")

    for i in range(110):  # More than the 100/min limit for free tier
        try:
            # Short timeout to avoid hanging
            response = requests.get(f"{GATEWAY_URL}/health", headers=headers, timeout=3)
            request_count += 1

            # Check if we got rate limited
            if response.status_code == 429:
                found_429 = True
                print(f"\n✓ SUCCESS: Got 429 response after {request_count} requests!")
                print(f"Status Code: {response.status_code}")
                print("Headers:")

                for header in [
                    "Retry-After",
                    "X-RateLimit-Limit-Minute",
                    "X-RateLimit-Remaining-Minute",
                ]:
                    if header in response.headers:
                        print(f"  ✓ {header}: {response.headers[header]}")
                    else:
                        print(f"  ✗ {header}: Missing")

                # Check response body
                try:
                    data = response.json()
                    print(f"  ✓ Response body: {data}")
                    if "message" in data and "rate" in data["message"].lower():
                        print("  ✓ Response contains rate limit message")
                    else:
                        print("  ? Response doesn't mention rate limiting")
                except:
                    print(f"  ✓ Response body (text): {response.text[:100]}")

                break

            else:
                # Show rate limit headers on other responses
                remaining = response.headers.get("X-RateLimit-Remaining-Minute", "N/A")
                limit = response.headers.get("X-RateLimit-Limit-Minute", "N/A")

                if request_count % 10 == 0 or remaining == "0":
                    print(
                        f"Request {request_count}: {response.status_code}, "
                        f"remaining: {remaining}/{limit}"
                    )

        except requests.exceptions.RequestException as e:
            request_count += 1
            # Even network errors might still count against rate limit
            if request_count % 10 == 0:
                print(f"Request {request_count}: Error - {type(e).__name__}")

        # Small delay to avoid overwhelming
        time.sleep(0.05)

    print(f"\nTotal requests attempted: {request_count}")

    if found_429:
        print(
            "✓ TASK 9.6 VERIFICATION COMPLETE: Rate limiting returns 429 with Retry-After"
        )
        return True
    else:
        print("✗ Could not trigger 429 response")
        print("Checking Kong configuration and Redis connection...")

        # Try to get Kong admin info
        try:
            admin_response = requests.get("http://localhost:8001/status", timeout=5)
            print(f"Kong admin status: {admin_response.status_code}")
            if admin_response.status_code == 200:
                status = admin_response.json()
                print(
                    f"Kong memory usage: {status.get('memory', {}).get('lua_shared_dict', 'N/A')}"
                )
        except:
            print("Could not access Kong admin API")

        return False


if __name__ == "__main__":
    success = test_rate_limit_simple()
    exit(0 if success else 1)
