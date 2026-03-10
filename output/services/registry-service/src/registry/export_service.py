"""Tenant data export service for Registry Service.

This module provides the TenantExportService class for exporting all tenant-scoped
data in various formats with encryption and secure storage support.
"""

from __future__ import annotations

import csv
import gzip
import json
import tempfile
import uuid
from datetime import UTC, datetime
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any, Optional

import structlog
from cryptography.fernet import Fernet
from venturestrat.tenancy import get_current_tenant_id, with_tenant

from registry.config import settings
from registry.events import TenantEventPublisher

try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = structlog.get_logger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"  # JSON Lines for streaming


class ExportStatus(str, Enum):
    """Export task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ExportOptions:
    """Configuration options for data export."""

    def __init__(
        self,
        format: ExportFormat = ExportFormat.JSON,
        compress: bool = True,
        encrypt: bool = True,
        include_deleted: bool = False,
        include_audit_fields: bool = True,
        batch_size: int = 1000,
        max_file_size_mb: int = 100,
        encryption_key: Optional[bytes] = None,
    ):
        self.format = format
        self.compress = compress
        self.encrypt = encrypt
        self.include_deleted = include_deleted
        self.include_audit_fields = include_audit_fields
        self.batch_size = batch_size
        self.max_file_size_mb = max_file_size_mb
        self.encryption_key = encryption_key or self._generate_key()

    def _generate_key(self) -> bytes:
        """Generate a random encryption key."""
        return Fernet.generate_key()


class TenantExportResult:
    """Result of a tenant data export operation."""

    def __init__(
        self,
        export_id: str,
        tenant_id: str,
        status: ExportStatus,
        file_path: str | None = None,
        file_size_bytes: int | None = None,
        records_exported: int = 0,
        models_exported: list[str] = None,
        encryption_key: Optional[bytes] = None,
        created_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ):
        self.export_id = export_id
        self.tenant_id = tenant_id
        self.status = status
        self.file_path = file_path
        self.file_size_bytes = file_size_bytes
        self.records_exported = records_exported
        self.models_exported = models_exported or []
        self.encryption_key = encryption_key
        self.created_at = created_at or datetime.now(UTC)
        self.completed_at = completed_at
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "export_id": self.export_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "records_exported": self.records_exported,
            "models_exported": self.models_exported,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class TenantExportService:
    """Service for exporting tenant-scoped data with encryption and secure storage.

    This service handles:
    - Collecting all tenant-scoped data across all models
    - Exporting data in various formats (JSON, CSV, JSONL)
    - Creating encrypted archives for sensitive data
    - Storing exports in secure locations
    - Managing export lifecycle and cleanup
    """

    def __init__(self, database_url: Optional[str] = None, storage_path: Optional[str] = None):
        """Initialize the export service.

        Args:
            database_url: PostgreSQL connection URL. Uses settings if not provided.
            storage_path: Directory for storing export files. Uses temp if not provided.
        """
        self.database_url = database_url or settings.database_url
        self.storage_path = Path(storage_path or tempfile.gettempdir()) / "tenant_exports"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._pool = None

        # Initialize event publisher
        self._event_publisher = TenantEventPublisher(
            bootstrap_servers=settings.kafka_bootstrap_servers, topic="platform.tenant.export"
        )

    async def initialize(self) -> None:
        """Initialize the export service and database connection."""
        if asyncpg is None:
            from venturestrat.exceptions import ERR_ASYNCPG_NOT_INSTALLED, create_error_from_code

            raise create_error_from_code(
                ERR_ASYNCPG_NOT_INSTALLED,
                "asyncpg is not installed and is required for PostgreSQL database operations",
                "Install with: pip install asyncpg\n\nFor complete setup instructions, see Prerequisites section in README:\nhttps://github.com/your-org/venturestrat#prerequisites",
            )

        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=300,  # Longer timeout for exports
                ssl=False,  # Disable SSL for local development
            )

            # Initialize event publisher
            try:
                await self._event_publisher.start()
                logger.info("export_service_event_publisher_started")
            except Exception as e:
                logger.warning("export_service_event_publisher_failed", error=str(e))

            logger.info(
                "tenant_export_service_initialized",
                database_url=self.database_url,
                storage_path=str(self.storage_path),
            )

        except Exception as e:
            logger.error("failed_to_initialize_export_service", error=str(e))
            raise

    async def close(self) -> None:
        """Close database connections and cleanup."""
        try:
            await self._event_publisher.stop()
            logger.info("export_service_event_publisher_stopped")
        except Exception as e:
            logger.warning("export_service_event_publisher_stop_failed", error=str(e))

        if self._pool:
            await self._pool.close()
            logger.info("tenant_export_service_closed")

    async def export_tenant_data(
        self,
        tenant_id: str,
        options: Optional[ExportOptions] = None,
        reason: str = "Data export requested",
    ) -> TenantExportResult:
        """Export all data for a tenant.

        Args:
            tenant_id: UUID of the tenant to export
            options: Export configuration options
            reason: Reason for the export (for audit purposes)

        Returns:
            TenantExportResult with export details and file location

        Raises:
            ValueError: If tenant not found or invalid options
            RuntimeError: If export fails
        """
        if not self._pool:
            raise RuntimeError("ExportService not initialized. Call initialize() first.")

        export_id = str(uuid.uuid4())
        options = options or ExportOptions()

        logger.info(
            "tenant_export_started",
            export_id=export_id,
            tenant_id=tenant_id,
            format=options.format,
            reason=reason,
        )

        # Create initial result
        result = TenantExportResult(
            export_id=export_id,
            tenant_id=tenant_id,
            status=ExportStatus.IN_PROGRESS,
            encryption_key=options.encryption_key,
        )

        try:
            # Emit export started event
            await self._emit_export_event("export.started", result, reason)

            # Collect all tenant data
            async with with_tenant(tenant_id, reason=f"Export data: {reason}"):
                tenant_models = await self._discover_tenant_models()
                all_data = {}
                total_records = 0

                for model_name in tenant_models:
                    logger.debug("exporting_model_data", export_id=export_id, model_name=model_name)

                    model_data = await self._collect_model_data(model_name, options)

                    if model_data:
                        all_data[model_name] = model_data
                        total_records += len(model_data)
                        result.models_exported.append(model_name)

            result.records_exported = total_records

            # Create export file
            file_path = await self._create_export_file(all_data, export_id, tenant_id, options)

            # Get file size
            file_size = Path(file_path).stat().st_size

            # Update result
            result.file_path = file_path
            result.file_size_bytes = file_size
            result.status = ExportStatus.COMPLETED
            result.completed_at = datetime.now(UTC)

            logger.info(
                "tenant_export_completed",
                export_id=export_id,
                tenant_id=tenant_id,
                records_exported=total_records,
                models_exported=len(result.models_exported),
                file_size_mb=file_size / 1024 / 1024,
            )

            # Emit export completed event
            await self._emit_export_event("export.completed", result, reason)

            return result

        except Exception as e:
            logger.error(
                "tenant_export_failed", export_id=export_id, tenant_id=tenant_id, error=str(e)
            )

            # Update result with error
            result.status = ExportStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now(UTC)

            # Emit export failed event
            await self._emit_export_event("export.failed", result, reason)

            raise RuntimeError(f"Export failed: {e}") from e

    async def _discover_tenant_models(self) -> list[str]:
        """Discover all models that contain tenant-scoped data.

        Returns:
            List of model names that have tenant_id fields
        """
        if not self._pool:
            raise RuntimeError("Database connection not available")

        # For now, we'll query the information_schema to find tables with tenant_id
        # In a full implementation, this would use the model registry
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT
                    table_schema,
                    table_name
                FROM information_schema.columns
                WHERE column_name = 'tenant_id'
                AND table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY table_schema, table_name
            """
            )

        # Convert to model-like names
        models = []
        for row in rows:
            schema = row["table_schema"]
            table = row["table_name"]
            model_name = f"{schema}.{table}"
            models.append(model_name)

        logger.debug("discovered_tenant_models", models=models, count=len(models))
        return models

    async def _collect_model_data(
        self, model_name: str, options: ExportOptions
    ) -> list[dict[str, Any]]:
        """Collect all data for a specific model.

        Args:
            model_name: Name of the model to export
            options: Export options

        Returns:
            List of records as dictionaries
        """
        if not self._pool:
            raise RuntimeError("Database connection not available")

        schema, table = model_name.split(".", 1)
        tenant_id = get_current_tenant_id()

        # Build query based on options
        base_query = f"SELECT * FROM {schema}.{table} WHERE tenant_id = $1"

        if not options.include_deleted:
            # Check if table has deleted_at column
            async with self._pool.acquire() as conn:
                has_deleted_at = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = $1
                        AND table_name = $2
                        AND column_name = 'deleted_at'
                    )
                """,
                    schema,
                    table,
                )

                if has_deleted_at:
                    base_query += " AND deleted_at IS NULL"

        # Add ordering for consistent exports
        base_query += " ORDER BY created_at, id"

        # Collect data in batches
        records = []
        offset = 0

        async with self._pool.acquire() as conn:
            while True:
                batch_query = f"{base_query} LIMIT {options.batch_size} OFFSET {offset}"
                rows = await conn.fetch(batch_query, tenant_id)

                if not rows:
                    break

                # Convert to dictionaries
                batch_records = []
                for row in rows:
                    record = dict(row)
                    # Convert datetime objects to ISO strings
                    for key, value in record.items():
                        if isinstance(value, datetime):
                            record[key] = value.isoformat()

                    # Apply field filtering if needed
                    if not options.include_audit_fields:
                        # Remove common audit fields
                        for field in ["created_at", "updated_at", "deleted_at"]:
                            record.pop(field, None)

                    batch_records.append(record)

                records.extend(batch_records)
                offset += len(rows)

                # Break if we got fewer records than requested (end of data)
                if len(rows) < options.batch_size:
                    break

        logger.debug("collected_model_data", model_name=model_name, records_count=len(records))

        return records

    async def _create_export_file(
        self,
        data: dict[str, list[dict[str, Any]]],
        export_id: str,
        tenant_id: str,
        options: ExportOptions,
    ) -> str:
        """Create the export file with specified format and options.

        Args:
            data: Dictionary of model_name -> records
            export_id: Unique export identifier
            tenant_id: Tenant ID
            options: Export options

        Returns:
            Path to the created file
        """
        # Generate filename
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"tenant_{tenant_id}_{export_id}_{timestamp}"

        # Add format extension
        if options.format == ExportFormat.JSON:
            filename += ".json"
        elif options.format == ExportFormat.CSV:
            filename += ".csv"
        elif options.format == ExportFormat.JSONL:
            filename += ".jsonl"

        # Add compression extension
        if options.compress:
            filename += ".gz"

        # Add encryption extension
        if options.encrypt:
            filename += ".enc"

        file_path = self.storage_path / filename

        # Create the file content
        if options.format == ExportFormat.JSON:
            content = self._create_json_content(data)
        elif options.format == ExportFormat.CSV:
            content = self._create_csv_content(data)
        elif options.format == ExportFormat.JSONL:
            content = self._create_jsonl_content(data)
        else:
            raise ValueError(f"Unsupported format: {options.format}")

        # Write file with optional compression and encryption
        final_content = content.encode("utf-8")

        if options.compress:
            final_content = gzip.compress(final_content)

        if options.encrypt:
            final_content = self._encrypt_content(final_content, options.encryption_key)

        # Write to file
        with open(file_path, "wb") as f:
            f.write(final_content)

        logger.info(
            "export_file_created",
            export_id=export_id,
            file_path=str(file_path),
            file_size_bytes=len(final_content),
            compressed=options.compress,
            encrypted=options.encrypt,
        )

        return str(file_path)

    def _create_json_content(self, data: dict[str, list[dict[str, Any]]]) -> str:
        """Create JSON export content."""
        export_metadata = {
            "export_version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        return json.dumps(export_metadata, indent=2, sort_keys=True)

    def _create_csv_content(self, data: dict[str, list[dict[str, Any]]]) -> str:
        """Create CSV export content with multiple sheets."""
        output = StringIO()

        for model_name, records in data.items():
            if not records:
                continue

            output.write(f"\n# Model: {model_name}\n")

            # Get all field names
            fieldnames = set()
            for record in records:
                fieldnames.update(record.keys())
            fieldnames = sorted(list(fieldnames))

            # Write CSV
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
            output.write("\n")

        return output.getvalue()

    def _create_jsonl_content(self, data: dict[str, list[dict[str, Any]]]) -> str:
        """Create JSON Lines export content."""
        lines = []

        for model_name, records in data.items():
            for record in records:
                line_data = {"_model": model_name, **record}
                lines.append(json.dumps(line_data, sort_keys=True))

        return "\n".join(lines)

    def _encrypt_content(self, content: bytes, key: bytes) -> bytes:
        """Encrypt content using Fernet symmetric encryption."""
        fernet = Fernet(key)
        return fernet.encrypt(content)

    def decrypt_content(self, encrypted_content: bytes, key: bytes) -> bytes:
        """Decrypt content using Fernet symmetric encryption."""
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_content)

    async def _emit_export_event(
        self, event_type: str, result: TenantExportResult, reason: str
    ) -> None:
        """Emit export-related events."""
        try:
            event_data = {
                "event_type": event_type,
                "export_id": result.export_id,
                "tenant_id": result.tenant_id,
                "status": result.status,
                "records_exported": result.records_exported,
                "models_exported": result.models_exported,
                "reason": reason,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            }

            await self._event_publisher.publish_export_event(**event_data)
            logger.debug(
                "export_event_published", event_type=event_type, export_id=result.export_id
            )

        except Exception as e:
            logger.error(
                "export_event_failed",
                event_type=event_type,
                export_id=result.export_id,
                error=str(e),
            )
            # Don't raise - event failure shouldn't block export

    async def get_export_result(self, export_id: str) -> TenantExportResult | None:
        """Get export result by ID.

        Args:
            export_id: Export identifier

        Returns:
            Export result or None if not found
        """
        # In a full implementation, this would query a database table
        # For now, we'll check if the file exists
        export_files = list(self.storage_path.glob(f"*_{export_id}_*"))

        if not export_files:
            return None

        # For this implementation, we'll return a basic result
        # In production, export metadata would be stored in database
        file_path = export_files[0]
        file_size = file_path.stat().st_size

        return TenantExportResult(
            export_id=export_id,
            tenant_id="unknown",  # Would be stored in metadata
            status=ExportStatus.COMPLETED,
            file_path=str(file_path),
            file_size_bytes=file_size,
        )

    async def cleanup_expired_exports(self, max_age_days: int = 7) -> int:
        """Clean up export files older than specified age.

        Args:
            max_age_days: Maximum age in days before deletion

        Returns:
            Number of files deleted
        """
        import time

        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        deleted_count = 0

        for file_path in self.storage_path.glob("tenant_*"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug("export_file_deleted", file_path=str(file_path))
                except Exception as e:
                    logger.warning(
                        "export_file_deletion_failed", file_path=str(file_path), error=str(e)
                    )

        if deleted_count > 0:
            logger.info(
                "export_cleanup_completed", deleted_count=deleted_count, max_age_days=max_age_days
            )

        return deleted_count

    async def health_check(self) -> bool:
        """Check if the export service is healthy."""
        try:
            if not self._pool:
                return False

            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            # Check storage directory
            if not self.storage_path.exists():
                return False

            return True

        except Exception as e:
            logger.error("export_service_health_check_failed", error=str(e))
            return False
