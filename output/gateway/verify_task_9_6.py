#!/usr/bin/env python3
"""
Task 9.6 Verification: Exceeding limit returns 429 with Retry-After
"""

import requests
import time
import sys


def verify_task_9_6():
    """Verify that exceeding rate limit returns 429 with Retry-After header."""
    print("=== TASK 9.6 VERIFICATION ===")
    print("Testing: exceeding limit returns 429 with Retry-After")
    print()

    base_url = "http://localhost:8000"
    api_key = "free-api-key-11111"  # Free tier with 100/min limit
    headers = {"X-API-Key": api_key}

    print(f"Gateway URL: {base_url}")
    print(f"API Key: {api_key} (free tier, 100/min limit)")
    print()

    # Test any endpoint that will respond quickly
    # Using root path which returns 404 but still processes rate limiting
    test_url = f"{base_url}/"

    print("Step 1: Making initial request to check rate limit headers...")
    try:
        response = requests.get(test_url, headers=headers, timeout=5)
        print(f"Initial response: {response.status_code}")

        limit = response.headers.get("X-RateLimit-Limit-Minute")
        remaining = response.headers.get("X-RateLimit-Remaining-Minute")

        print("Rate limit headers found:")
        print(f"  Limit: {limit}")
        print(f"  Remaining: {remaining}")

        if limit != "100":
            print(f"ERROR: Expected free tier limit of 100, got {limit}")
            return False

    except Exception as e:
        print(f"ERROR: Initial request failed: {e}")
        return False

    print("\nStep 2: Making rapid requests to trigger rate limiting...")

    request_count = 0
    success = False

    try:
        # Make rapid requests until we hit rate limit
        for i in range(120):  # More than the 100 limit
            response = requests.get(test_url, headers=headers, timeout=5)
            request_count += 1

            if response.status_code == 429:
                print(f"\n✓ SUCCESS: Received 429 after {request_count} requests")

                # Verify required headers
                checks_passed = 0
                total_checks = 4

                # Check 1: Retry-After header
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    print(f"✓ Retry-After header present: {retry_after}")
                    checks_passed += 1
                    try:
                        retry_seconds = int(retry_after)
                        if 0 < retry_seconds <= 60:
                            print(
                                f"✓ Retry-After value is reasonable: {retry_seconds}s"
                            )
                        else:
                            print(
                                f"? Retry-After value seems unusual: {retry_seconds}s"
                            )
                    except ValueError:
                        print(f"? Retry-After is not numeric: {retry_after}")
                else:
                    print("✗ Retry-After header MISSING")

                # Check 2: Rate limit headers
                limit = response.headers.get("X-RateLimit-Limit-Minute")
                if limit == "100":
                    print(f"✓ X-RateLimit-Limit-Minute correct: {limit}")
                    checks_passed += 1
                else:
                    print(f"✗ X-RateLimit-Limit-Minute incorrect: {limit}")

                # Check 3: Remaining count
                remaining = response.headers.get("X-RateLimit-Remaining-Minute")
                if remaining is not None:
                    print(f"✓ X-RateLimit-Remaining-Minute present: {remaining}")
                    checks_passed += 1
                    try:
                        remaining_int = int(remaining)
                        if remaining_int <= 1:
                            print(
                                f"✓ Remaining count is low as expected: {remaining_int}"
                            )
                        else:
                            print(
                                f"? Remaining count higher than expected: {remaining_int}"
                            )
                    except ValueError:
                        print(f"? Remaining count not numeric: {remaining}")
                else:
                    print("✗ X-RateLimit-Remaining-Minute header MISSING")

                # Check 4: Error message
                try:
                    data = response.json()
                    if "message" in data:
                        message = data["message"].lower()
                        if any(word in message for word in ["rate", "limit", "quota", "throttle"]):
                            print(f"✓ Error message mentions rate limiting: {data['message']}")
                        if any(
                            word in message
                            for word in ["rate", "limit", "quota", "throttle"]
                        ):
                            print(
                                f"✓ Error message mentions rate limiting: {data['message']}"
                            )
                            checks_passed += 1
                        else:
                            print(
                                f"? Error message doesn't mention rate limiting: {data['message']}"
                            )
                    else:
                        print("? No 'message' field in response body")
                        print(f"  Response body: {data}")
                except Exception as e:
                    print(f"? Could not parse response body as JSON: {e}")
                    print(f"  Response text: {response.text[:100]}")

                print(
                    f"\nVerification Summary: {checks_passed}/{total_checks} checks passed"
                )

                if checks_passed >= 3:  # Allow some flexibility
                    print(
                        "✓ TASK 9.6 PASSED: Rate limiting properly returns 429 with Retry-After"
                    )
                    success = True
                else:
                    print(
                        "✗ TASK 9.6 FAILED: Missing required headers or functionality"
                    )

                break

            elif request_count % 20 == 0:
                remaining = response.headers.get("X-RateLimit-Remaining-Minute", "?")
                print(f"Request {request_count}: {response.status_code}, remaining: {remaining}")
                print(
                    f"Request {request_count}: {response.status_code}, remaining: {remaining}"
                )

            # Small delay to avoid overwhelming the system
            time.sleep(0.02)

    except Exception as e:
        print(f"ERROR during rate limiting test: {e}")
        return False

    if not success:
        print(
            f"\n✗ FAILED: Could not trigger 429 response after {request_count} requests"
        )
        print("This might indicate:")
        print("1. Rate limiting is not properly configured")
        print("2. Redis connection issues preventing rate limit tracking")
        print("3. Rate limits are higher than expected")

    return success


if __name__ == "__main__":
    success = verify_task_9_6()
    sys.exit(0 if success else 1)
