"""Configuration management for Registry Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service info
    service_name: str = "registry-service"
    service_version: str = "0.1.0"
    log_level: str = "INFO"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    grpc_port: int = 50051

    # Features
    events_enabled: bool = False  # Kafka event publishing (optional)

    # Consul
    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_scheme: str = "http"
    consul_token: str | None = None

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_lifecycle: str = "platform.services.lifecycle"

    # PostgreSQL
    database_url: str = "postgresql://registry:registry@localhost:5432/registry"

    # Redis (for quota counters)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 0
    redis_quota_key_prefix: str = "quota"

    # Health checks
    health_check_interval: int = 10
    health_check_timeout: int = 5
    deregister_after: int = 60

    # Tenant purge settings
    tenant_purge_enabled: bool = True
    tenant_purge_check_interval: int = 3600  # 1 hour
    tenant_purge_retry_count: int = 3
    tenant_purge_retry_delay: int = 300  # 5 minutes

    # Keycloak settings (for cleanup during purge)
    keycloak_base_url: str = "http://localhost:8080"
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: str = "admin"
    keycloak_realm: str = "master"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def kafka_config(self) -> dict:
        """Get Kafka configuration for EventPublisher."""
        return {
            "bootstrap_servers": self.kafka_bootstrap_servers,
            # Add other Kafka config as needed
        }


settings = Settings()
