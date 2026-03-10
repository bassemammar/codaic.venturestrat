"""Configuration management for Crm Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service info
    service_name: str = "crm-service"
    service_version: str = "1.0.0"
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8062

    # Registry integration
    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_scheme: str = "http"
    consul_token: str | None = None

    # Event bus
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_prefix: str = "crm_service"

    # Database (BaseModel ORM)
    database_url: str = "postgresql://venturestrat:venturestrat_dev_password@venturestrat-postgres:5432/venturestrat"

    # Platform
    platform_mode: str = "integrated"  # integrated or standalone
    # Health checks
    health_check_interval: int = 10
    health_check_timeout: int = 5
    deregister_after: int = 60

    # Observability
    otlp_endpoint: str = "http://jaeger:4317"
    log_format: str = "json"  # json or console
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    tracing_sample_rate: float = 1.0

    # Security
    cors_origins: str = "http://localhost:3000,http://localhost:4000"
    cors_allow_credentials: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Development
    reload: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
