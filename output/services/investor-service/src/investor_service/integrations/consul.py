"""Consul service discovery integration."""

import consul
import socket
import structlog
from typing import Optional

from investor_service.config import settings

logger = structlog.get_logger(__name__)


class ConsulClient:
    """Consul service discovery client."""

    def __init__(self):
        self.client: Optional[consul.Consul] = None
        self.service_id: Optional[str] = None

    def connect(self) -> None:
        """Connect to Consul server."""
        try:
            self.client = consul.Consul(
                host=settings.consul_host,
                port=settings.consul_port,
                scheme=settings.consul_scheme,
                token=settings.consul_token,
            )
            # Test connection
            self.client.agent.self()
            logger.info("consul_connected",
                       host=settings.consul_host,
                       port=settings.consul_port)
        except Exception as e:
            logger.error("consul_connection_failed", error=str(e))
            raise

    def register_service(self) -> None:
        """Register service with Consul."""
        if not self.client:
            raise RuntimeError("Consul client not connected")

        # Generate unique service ID
        hostname = socket.gethostname()
        self.service_id = f"{settings.service_name}-{hostname}-{settings.port}"

        # Register service
        try:
            self.client.agent.service.register(
                name=settings.service_name,
                service_id=self.service_id,
                address=settings.host if settings.host != "0.0.0.0" else hostname,
                port=settings.port,
                tags=["fastapi", "investor-service", "v1"],
                check=consul.Check.http(
                    url=f"http://{hostname}:{settings.port}/health/ready",
                    interval=f"{settings.health_check_interval}s",
                    timeout=f"{settings.health_check_timeout}s",
                    deregister=f"{settings.deregister_after}s",
                ),
                # meta parameter removed - not supported by python-consul
            )
            logger.info("service_registered",
                       service_id=self.service_id,
                       name=settings.service_name)
        except Exception as e:
            logger.error("service_registration_failed",
                        service_id=self.service_id,
                        error=str(e))
            raise

    def deregister_service(self) -> None:
        """Deregister service from Consul."""
        if not self.client or not self.service_id:
            return

        try:
            self.client.agent.service.deregister(self.service_id)
            logger.info("service_deregistered", service_id=self.service_id)
        except Exception as e:
            logger.error("service_deregistration_failed",
                        service_id=self.service_id,
                        error=str(e))


# Global instance
consul_client = ConsulClient()
