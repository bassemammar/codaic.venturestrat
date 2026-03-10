"""Configuration for registry-service SDK.

This module provides configuration management for the SDK, including
loading from environment variables and configuration files.
"""

from pathlib import Path
from typing import Any
from typing import Any, Optional, Union

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class RegistryServiceConfig(BaseSettings):
    """Configuration for registry-service client.

    Configuration can be loaded from environment variables, .env files,
    or passed directly to the constructor.

    Environment variables are prefixed with REGISTRY_SERVICE_.

    Examples:
        From environment:
        >>> import os
        >>> os.environ['REGISTRY_SERVICE_HOST'] = 'api.example.com'
        >>> config = RegistryServiceConfig()
        >>> print(config.host)  # 'api.example.com'

        From constructor:
        >>> config = RegistryServiceConfig(
        ...     host='localhost',
        ...     port=50051,
        ...     auth_api_key='my-key'
        ... )
    """

    # Connection settings
    host: str = Field(default="localhost", description="Service host")
    port: int = Field(default=50051, ge=1, le=65535, description="Service port")
    secure: bool = Field(default=False, description="Use TLS connection")
    timeout: float = Field(
        default=30.0, gt=0, description="Default request timeout in seconds"
    )

    # Authentication settings
    auth_token: str | None = Field(
        default=None, description="Bearer token for authentication"
    )
    auth_api_key: str | None = Field(
        default=None, description="API key for authentication"
    )
    auth_username: str | None = Field(
        default=None, description="Username for basic auth"
    )
    auth_password: str | None = Field(
    auth_token: Optional[str] = Field(
        default=None, description="Bearer token for authentication"
    )
    auth_api_key: Optional[str] = Field(
        default=None, description="API key for authentication"
    )
    auth_username: Optional[str] = Field(
        default=None, description="Username for basic auth"
    )
    auth_password: Optional[str] = Field(
        default=None, description="Password for basic auth"
    )

    # gRPC settings
    grpc_max_receive_message_length: int = Field(
        default=4 * 1024 * 1024,  # 4MB
        description="Max gRPC receive message length",
    )
    grpc_max_send_message_length: int = Field(
        default=4 * 1024 * 1024,  # 4MB
        description="Max gRPC send message length",
    )
    grpc_keepalive_time_ms: int = Field(
        default=30000, description="gRPC keepalive time in milliseconds"
    )
    grpc_keepalive_timeout_ms: int = Field(
        default=5000, description="gRPC keepalive timeout in milliseconds"
    )

    # Additional metadata
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional metadata headers"
    )

    # Development settings
    debug: bool = Field(default=False, description="Enable debug logging")
    retry_attempts: int = Field(
        default=3, ge=0, le=10, description="Number of retry attempts"
    )
    retry_backoff: float = Field(
        default=1.0, gt=0, description="Retry backoff multiplier"
    )

    model_config = {
        # Environment variable prefix
        "env_prefix": "REGISTRY_SERVICE_",
        # Load from .env file
        "env_file": ".env",
        # Case sensitive environment variables
        "case_sensitive": False,
        # Ignore extra fields
        "extra": "ignore",
    }

    @classmethod
    def from_env(cls) -> "RegistryServiceConfig":
        """Load configuration from environment variables.

        Returns:
            Configuration instance loaded from environment
        """
        return cls()

    @classmethod
    def from_file(cls, config_file: str | Path) -> "RegistryServiceConfig":
        """Load configuration from file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configuration instance loaded from file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_path = Path(config_file)
        if not config_path.exists():
            msg = f"Config file not found: {config_path}"
            raise FileNotFoundError(msg)

        if config_path.suffix.lower() == ".json":
            return cls.from_json_file(config_path)
        if config_path.suffix.lower() in [".yaml", ".yml"]:
        elif config_path.suffix.lower() in [".yaml", ".yml"]:
            return cls.from_yaml_file(config_path)
        msg = f"Unsupported config file format: {config_path.suffix}"
        raise ValueError(msg)

    @classmethod
    def from_json_file(cls, json_file: str | Path) -> "RegistryServiceConfig":
        """Load configuration from JSON file.

        Args:
            json_file: Path to JSON file

        Returns:
            Configuration instance
        """
        import json

        with open(json_file) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def from_yaml_file(cls, yaml_file: str | Path) -> "RegistryServiceConfig":
        """Load configuration from YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            Configuration instance
        """
        import yaml

        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_grpc_options(self) -> dict[str, Any]:
        """Get gRPC channel options.

        Returns:
            Dictionary of gRPC options
        """
        return {
            "grpc.max_receive_message_length": self.grpc_max_receive_message_length,
            "grpc.max_send_message_length": self.grpc_max_send_message_length,
            "grpc.keepalive_time_ms": self.grpc_keepalive_time_ms,
            "grpc.keepalive_timeout_ms": self.grpc_keepalive_timeout_ms,
        }

    @validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host format."""
        v = v.strip()
        if not v:
            msg = "Host cannot be empty"
            raise ValueError(msg)
        return v

    @validator("auth_token", "auth_api_key")
    @classmethod
    def validate_auth_fields(cls, v: str | None) -> str | None:
        """Validate authentication fields."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        return self.model_dump()

    def to_json(self, file_path: str | Path | None = None) -> str:
        """Convert config to JSON.

        Args:
            file_path: Optional file to write JSON to

        Returns:
            JSON string representation
        """
        json_str = self.model_dump_json(indent=2)

        if file_path:
            with open(file_path, "w") as f:
                f.write(json_str)

        return json_str

    def to_yaml(self, file_path: str | Path | None = None) -> str:
        """Convert config to YAML.

        Args:
            file_path: Optional file to write YAML to

        Returns:
            YAML string representation
        """
        import yaml

        yaml_str = yaml.dump(
            self.model_dump(), default_flow_style=False, sort_keys=True
        )

        if file_path:
            with open(file_path, "w") as f:
                f.write(yaml_str)

        return yaml_str


__all__ = ["RegistryServiceConfig"]
