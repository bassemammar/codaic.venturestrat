"""Forge service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class ForgeSettings(BaseSettings):
  """Forge service settings loaded from environment."""

  SERVICE_NAME: str = 'forge'
  PORT: int = 8000
  DATABASE_URL: str
  REDIS_URL: str = 'redis://localhost:6379/7'
  AUTH_SERVICE_URL: str = 'http://localhost:8106'
  JWT_SECRET_KEY: str = 'venturestrat-dev-secret-change-in-production'
  PLATFORM_NAME: str = 'venturestrat'
  PLATFORM_ROOT: str = '/app'
  AI_ELICITATION_ENABLED: bool = False
  LOG_LEVEL: str = 'INFO'
  CORS_ORIGINS: str = ''

  class Config:
    env_file = '.env'
    env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> ForgeSettings:
  """Return cached settings instance."""
  return ForgeSettings()
