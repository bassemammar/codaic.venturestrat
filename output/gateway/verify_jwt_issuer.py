#!/usr/bin/env python3
"""
JWT Issuer Verification Script

Verifies that the JWT issuer service is properly configured and working.
This script tests:
1. JWT issuer service starts successfully
2. Health endpoint responds correctly
3. Token issuance works
4. Token validation works

Usage: python verify_jwt_issuer.py
"""

import requests
import time
import sys
import jwt
from datetime import datetime


def test_jwt_issuer_service():
    """Test the JWT issuer service functionality."""
    base_url = "http://localhost:8002"

    print("🔍 Testing JWT Issuer Service...")

    # Test 1: Health check
    print("\n1️⃣  Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Health check passed: {health_data['status']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # Test 2: Token issuance
    print("\n2️⃣  Testing token issuance...")
    try:
        token_request = {"service_name": "pricing-service"}
        response = requests.post(
            f"{base_url}/token",
            json=token_request,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )

        if response.status_code == 200:
            token_data = response.json()
            token = token_data["token"]
            print("   ✅ Token issued successfully")
            print(f"   📅 Expires at: {token_data['expires_at']}")
            print(f"   🔑 Token type: {token_data['token_type']}")
        else:
            print(f"   ❌ Token issuance failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Token issuance failed: {e}")
        return False

    # Test 3: Token validation (decode locally)
    print("\n3️⃣  Testing token validation...")
    try:
        # Decode without verification first to check structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        print("   ✅ Token decoded successfully")
        print(f"   👤 Subject: {decoded.get('sub')}")
        print(f"   🏢 Issuer: {decoded.get('iss')}")
        print(f"   👥 Audience: {decoded.get('aud')}")
        print(f"   ⏰ Expires: {datetime.fromtimestamp(decoded.get('exp'))}")

        # Verify required claims
        required_claims = ["sub", "iss", "aud", "exp", "iat", "jti"]
        missing_claims = [claim for claim in required_claims if claim not in decoded]
        if missing_claims:
            print(f"   ❌ Missing required claims: {missing_claims}")
            return False
        else:
            print("   ✅ All required claims present")

    except Exception as e:
        print(f"   ❌ Token validation failed: {e}")
        return False

    # Test 4: Service validation endpoint
    print("\n4️⃣  Testing service validation endpoint...")
    try:
        validation_request = {"token": token}
        response = requests.post(
            f"{base_url}/validate",
            json=validation_request,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )

        if response.status_code == 200:
            validation_data = response.json()
            if validation_data.get("valid"):
                print("   ✅ Token validation passed")
                print(f"   ⏳ Expires in: {validation_data.get('expires_in')} seconds")
            else:
                print("   ❌ Token validation failed: invalid token")
                return False
        else:
            print(f"   ❌ Token validation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Token validation failed: {e}")
        return False

    print("\n🎉 All tests passed! JWT issuer service is working correctly.")
    return True


def check_service_availability():
    """Wait for service to become available."""
    base_url = "http://localhost:8002"
    max_attempts = 30

    print("⏳ Waiting for JWT issuer service to start...")
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print("✅ JWT issuer service is ready!")
                return True
        except:
            pass

        if attempt < max_attempts - 1:
            print(f"   Attempt {attempt + 1}/{max_attempts}, retrying in 2s...")
            time.sleep(2)

    print("❌ JWT issuer service did not start within timeout")
    return False


if __name__ == "__main__":
    print("🚀 JWT Issuer Service Verification")
    print("=" * 50)

    if check_service_availability():
        success = test_jwt_issuer_service()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Service verification failed - JWT issuer not available")
        sys.exit(1)
