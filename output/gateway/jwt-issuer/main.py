#!/usr/bin/env python3
"""
JWT Issuer Service for VentureStrat Gateway

A minimal JWT issuing service for Phase 1 service-to-service authentication.
Provides tokens for internal service communication.
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import jwt
import os
import logging
from datetime import datetime
from typing import Optional
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-prod")
JWT_ISSUER = os.getenv("JWT_ISSUER", "venturestrat-gateway")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "1"))

app = FastAPI(
    title="VentureStrat JWT Issuer",
    description="JWT token issuer for service-to-service authentication",
    version="1.0.0",
)


# Request/Response Models
class TokenRequest(BaseModel):
    service_name: str = Field(..., description="Name of the requesting service")
    scope: Optional[str] = Field(None, description="Token scope (optional)")


class TokenResponse(BaseModel):
    token: str = Field(..., description="JWT token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_at: str = Field(..., description="Token expiration time (ISO 8601)")
    expires_in: int = Field(..., description="Token expiry in seconds")


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for container orchestration."""
    return HealthResponse(
        status="healthy", timestamp=datetime.utcnow().isoformat() + "Z", version="1.0.0"
    )


# JWT token issuance endpoint
@app.post("/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest, http_request: Request):
    """
    Issue a JWT token for service-to-service authentication.

    Args:
        request: Token request with service name and optional scope
        http_request: FastAPI request object for client IP logging

    Returns:
        JWT token with expiration information

    Raises:
        HTTPException: On invalid service name or token generation failure
    """
    # Validate service name first (before try block to avoid catching HTTPException)
    if not request.service_name or len(request.service_name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Service name is required and cannot be empty")
        raise HTTPException(
            status_code=400, detail="Service name is required and cannot be empty"
        )

    try:
        # Create token expiration using consistent UTC timestamps
        import time

        now_timestamp = int(time.time())
        expires_timestamp = now_timestamp + (JWT_EXPIRY_HOURS * 3600)
        expires_at = datetime.utcfromtimestamp(expires_timestamp)

        # Build JWT payload with explicit timestamps
        payload = {
            "sub": request.service_name,  # Subject (service name)
            "iss": JWT_ISSUER,  # Issuer
            "aud": "venturestrat-services",  # Audience
            "exp": expires_timestamp,  # Expiration time as unix timestamp
            "iat": now_timestamp,  # Issued at as unix timestamp
            "jti": str(uuid.uuid4()),  # JWT ID (unique identifier)
            "typ": "access_token",  # Token type
        }

        # Add scope if provided
        if request.scope:
            payload["scope"] = request.scope

        # Sign the token
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Log token issuance
        client_ip = http_request.client.host if http_request.client else "unknown"
        logger.info(
            f"JWT issued for service '{request.service_name}' "
            f"from client {client_ip}, expires at {expires_at.isoformat()}"
        )

        return TokenResponse(
            token=token,
            token_type="Bearer",
            expires_at=expires_at.isoformat() + "Z",
            expires_in=JWT_EXPIRY_HOURS * 3600,
        )

    except jwt.InvalidKeyError:
        logger.error("JWT secret key is invalid")
        raise HTTPException(
            status_code=500, detail="Internal server error: invalid JWT configuration"
        )
    except Exception as e:
        logger.error(f"Error issuing JWT token: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during token generation")

        raise HTTPException(
            status_code=500, detail="Internal server error during token generation"
        )


# Token validation request model
class TokenValidateRequest(BaseModel):
    token: str = Field(..., description="JWT token to validate")


# Token validation endpoint (for testing)
@app.post("/validate")
async def validate_token(request: TokenValidateRequest):
    """
    Validate a JWT token (for testing purposes).

    Args:
        request: Token validation request with JWT token

    Returns:
        Decoded token payload

    Raises:
        HTTPException: On invalid or expired token
    """
    try:
        payload = jwt.decode(
            request.token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="venturestrat-services",
        )

        return {
            "valid": True,
            "payload": payload,
            "expires_in": int(
                (datetime.fromtimestamp(payload["exp"]) - datetime.utcnow()).total_seconds()
                (
                    datetime.fromtimestamp(payload["exp"]) - datetime.utcnow()
                ).total_seconds()
            ),
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token audience")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error validating JWT token: {str(e)}")
        raise HTTPException(status_code=500, detail="Token validation error")


# Application startup
@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("JWT Issuer service starting up")
    logger.info(f"Issuer: {JWT_ISSUER}")
    logger.info(f"Algorithm: {JWT_ALGORITHM}")
    logger.info(f"Token expiry: {JWT_EXPIRY_HOURS} hours")

    # Validate JWT secret in production
    if JWT_SECRET == "dev-secret-change-in-prod":
        logger.warning("Using default JWT secret - change in production!")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
