"""Utility functions for registry-service SDK.

This module provides common utility functions used across the SDK.
"""

import asyncio
import functools
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

import grpc

from .exceptions import RegistryServiceError, grpc_status_to_exception

T = TypeVar("T")


def handle_grpc_error(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle gRPC errors and convert to SDK exceptions.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function that converts gRPC errors
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except grpc.RpcError as e:
            # Convert gRPC error to SDK exception
            raise grpc_status_to_exception(e.code(), e.details())
        except Exception as e:
            # Wrap other exceptions
            if not isinstance(e, RegistryServiceError):
                msg = f"Unexpected error: {e}"
                raise RegistryServiceError(msg)
            raise

    return wrapper


def handle_grpc_error_async(func: Callable[..., T]) -> Callable[..., T]:
    """Async decorator to handle gRPC errors and convert to SDK exceptions.

    Args:
        func: Async function to wrap

    Returns:
        Wrapped async function that converts gRPC errors
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except grpc.aio.AioRpcError as e:
            # Convert async gRPC error to SDK exception
            raise grpc_status_to_exception(e.code(), e.details())
        except grpc.RpcError as e:
            # Convert sync gRPC error to SDK exception
            raise grpc_status_to_exception(e.code(), e.details())
        except Exception as e:
            # Wrap other exceptions
            if not isinstance(e, RegistryServiceError):
                msg = f"Unexpected error: {e}"
                raise RegistryServiceError(msg)
            raise

    return wrapper


def validate_response(response: Any) -> Any:
    """Validate and process response from service.

    Args:
        response: Response from gRPC call

    Returns:
        Validated response

    Raises:
        RegistryServiceError: If response is invalid
    """
    if response is None:
        msg = "Received null response from service"
        raise RegistryServiceError(msg)

    # Additional response validation can be added here
    # For example, checking for error fields in the response

    return response


def retry_on_failure(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (grpc.RpcError,),
) -> Callable:
    """Decorator to retry function calls on failure.

    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Exponential backoff factor
        exceptions: Exception types to retry on

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import random
            import time

            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise
                        break

                    # Calculate backoff time
                    backoff = backoff_factor * (2**attempt)
                    jitter = random.uniform(0, 0.1 * backoff)
                    sleep_time = backoff + jitter

                    time.sleep(sleep_time)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper

    return decorator


def async_retry_on_failure(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (grpc.aio.AioRpcError,),
) -> Callable:
    """Async decorator to retry function calls on failure.

    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Exponential backoff factor
        exceptions: Exception types to retry on

    Returns:
        Async decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            import random

            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise
                        break

                    # Calculate backoff time
                    backoff = backoff_factor * (2**attempt)
                    jitter = random.uniform(0, 0.1 * backoff)
                    sleep_time = backoff + jitter

                    await asyncio.sleep(sleep_time)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper

    return decorator


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string.

    Args:
        dt: Datetime to format

    Returns:
        ISO formatted string
    """
    return dt.isoformat() + "Z" if dt.utcoffset() is None else dt.isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime.

    Args:
        timestamp_str: ISO timestamp string

    Returns:
        Parsed datetime

    Raises:
        ValueError: If timestamp format is invalid
    """
    from datetime import datetime

    # Handle different timestamp formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    msg = f"Unable to parse timestamp: {timestamp_str}"
    raise ValueError(msg)


def mask_sensitive_data(data: str, keep_chars: int = 4) -> str:
    """Mask sensitive data for logging.

    Args:
        data: Sensitive data to mask
        keep_chars: Number of characters to keep visible

    Returns:
        Masked string
    """
    if len(data) <= keep_chars * 2:
        return "*" * len(data)

    visible_start = data[:keep_chars]
    visible_end = data[-keep_chars:]
    mask_length = len(data) - (keep_chars * 2)

    return f"{visible_start}{'*' * mask_length}{visible_end}"


def safe_get_nested(obj: dict, path: str, default: Any = None) -> Any:
    """Safely get nested dictionary value.

    Args:
        obj: Dictionary to search
        path: Dot-separated path (e.g., 'user.profile.name')
        default: Default value if path not found

    Returns:
        Value at path or default
    """
    keys = path.split(".")
    current = obj

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


__all__ = [
    "async_retry_on_failure",
    "format_timestamp",
    "handle_grpc_error",
    "handle_grpc_error_async",
    "mask_sensitive_data",
    "parse_timestamp",
    "retry_on_failure",
    "safe_get_nested",
    "validate_response",
]
