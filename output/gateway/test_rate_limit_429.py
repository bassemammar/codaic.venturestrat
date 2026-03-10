#!/usr/bin/env python3
"""
Manual test script to verify rate limit 429 responses with Retry-After headers.
Task 9.6: Verify: exceeding limit returns 429 with Retry-After
"""

import requests
import time
import json

GATEWAY_URL = "http://localhost:8000"
FREE_TIER_API_KEY = "free-api-key-11111"


def test_rate_limit_429():
    """Test rate limiting returns 429 with Retry-After header."""
    print("Testing rate limit 429 responses...")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"API Key: {FREE_TIER_API_KEY}")
    print("Free tier limit: 100 requests/minute")
    print()

    headers = {"X-API-Key": FREE_TIER_API_KEY}

    # First, check what endpoints are accessible
    test_endpoints = ["/health", "/api/v1/registry/services"]

    for endpoint in test_endpoints:
        try:
            response = requests.get(
                f"{GATEWAY_URL}{endpoint}", headers=headers, timeout=5
            )
            print(f"Testing endpoint {endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(
                    f"  Rate limit headers: {response.headers.get('X-RateLimit-Limit-Minute', 'None')}"
                )
                print(
                    f"  Remaining: {response.headers.get('X-RateLimit-Remaining-Minute', 'None')}"
                )
                break
        except requests.exceptions.RequestException as e:
            print(f"  Error: {e}")
            continue
    else:
        print("No accessible endpoints found, trying direct health check...")
        endpoint = "/health"

    print(f"\nUsing endpoint: {endpoint}")
    print("Making rapid requests to trigger rate limiting...")

    request_count = 0
    found_429 = False

    try:
        # Make requests to trigger rate limit
        for i in range(150):  # More than free tier limit of 100
            try:
                response = requests.get(
                    f"{GATEWAY_URL}{endpoint}", headers=headers, timeout=5
                )
                request_count += 1

                if response.status_code == 429:
                    found_429 = True
                    print(
                        f"\n✓ SUCCESS: Got 429 response after {request_count} requests!"
                    )
                    print(f"Status Code: {response.status_code}")

                    # Check for Retry-After header
                    if "Retry-After" in response.headers:
                        print(
                            f"✓ Retry-After header: {response.headers['Retry-After']}"
                        )
                    else:
                        print("✗ Missing Retry-After header")

                    # Check for rate limit headers
                    if "X-RateLimit-Limit-Minute" in response.headers:
                        print(
                            f"✓ X-RateLimit-Limit-Minute: {response.headers['X-RateLimit-Limit-Minute']}"
                        )
                    else:
                        print("✗ Missing X-RateLimit-Limit-Minute header")

                    if "X-RateLimit-Remaining-Minute" in response.headers:
                        print(
                            f"✓ X-RateLimit-Remaining-Minute: {response.headers['X-RateLimit-Remaining-Minute']}"
                        )
                    else:
                        print("✗ Missing X-RateLimit-Remaining-Minute header")

                    # Check response body
                    try:
                        data = response.json()
                        if "message" in data:
                            print(f"✓ Error message: {data['message']}")
                        else:
                            print("✗ Missing error message in response body")
                    except json.JSONDecodeError:
                        print("✗ Response body is not valid JSON")

                    # Test that subsequent requests also return 429
                    print("\nTesting subsequent requests also return 429...")
                    for j in range(3):
                        retry_response = requests.get(
                            f"{GATEWAY_URL}{endpoint}", headers=headers, timeout=5
                        )
                        if retry_response.status_code == 429:
                            print(f"✓ Request {j+1}: Still getting 429")
                        else:
                            print(
                                f"✗ Request {j+1}: Got {retry_response.status_code} instead of 429"
                            )
                        time.sleep(0.5)

                    break

                elif response.status_code == 200:
                    # Check rate limit headers on successful requests
                    remaining = response.headers.get(
                        "X-RateLimit-Remaining-Minute", "Unknown"
                    )
                    if request_count % 10 == 0:  # Print every 10th request
                        print(f"Request {request_count}: 200, remaining: {remaining}")

                else:
                    print(
                        f"Request {request_count}: Got {response.status_code} (not 200 or 429)"
                    )
                    if request_count < 10:  # Only show first few errors
                        try:
                            print(f"  Response: {response.text[:200]}")
                        except:
                            pass

                # Small delay between requests
                time.sleep(0.01)

            except requests.exceptions.RequestException as e:
                print(f"Request {request_count + 1} failed: {e}")
                break

        if not found_429:
            print(
                f"\n✗ FAILURE: Did not get 429 response after {request_count} requests"
            )
            print("This could mean:")
            print("1. Rate limiting is not configured properly")
            print("2. The API key has higher limits than expected")
            print("3. Kong is not enforcing rate limits")

    except KeyboardInterrupt:
        print(f"\nTest interrupted after {request_count} requests")

    print(f"\nTotal requests made: {request_count}")
    return found_429


if __name__ == "__main__":
    success = test_rate_limit_429()
    exit(0 if success else 1)
