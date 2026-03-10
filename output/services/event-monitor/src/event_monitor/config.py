"""Configuration for Event Monitor service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
  """Application settings loaded from environment variables."""

  # Service
  service_name: str = 'event-monitor'
  service_version: str = '1.0.0'
  log_level: str = 'INFO'
  log_format: str = 'console'
  host: str = '0.0.0.0'
  port: int = 8101
  reload: bool = False

  # Database (shared schema on VentureStrat postgres)
  database_url: str = 'postgresql://venturestrat:venturestrat_dev_password@venturestrat-postgres:5432/venturestrat'

  # Kafka
  kafka_bootstrap_servers: str = 'venturestrat-kafka:29092'
  observer_group_id: str = 'event-monitor-observer'
  topic_pattern: str = '^(?!__).+'  # all non-internal topics

  # Manifest discovery
  services_dir: str = '/app/services'

  # CORS
  cors_origins: str = 'http://localhost:5178,http://localhost:3000'

  # Retention
  retention_days: int = 30

  @property
  def cors_origins_list(self) -> list[str]:
    return [o.strip() for o in self.cors_origins.split(',')]

  class Config:
    env_file = '.env'
    env_file_encoding = 'utf-8'


settings = Settings()
