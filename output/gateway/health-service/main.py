#!/usr/bin/env python3
"""
Simple health service for Kong Gateway.

Returns a standardized health response for the /health endpoint.
This service provides the health check backend for Kong routing.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import os

app = FastAPI(title="VentureStrat Gateway Health Service", version="1.0.0")


class HealthResponse(BaseModel):
    """Standard health check response."""

    status: str
    timestamp: str


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Gateway health check endpoint.

    Returns basic health status with timestamp.
    This endpoint is called by Kong for the /health route.
    """
    return HealthResponse(status="healthy", timestamp=datetime.now().isoformat() + "Z")


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    """Root endpoint (same as health for simplicity)."""
    return health_check()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
    )
