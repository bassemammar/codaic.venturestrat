"""Unit tests for TenantExportService."""

import gzip
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from registry.export_service import (
    ExportFormat,
    ExportOptions,
    ExportStatus,
    TenantExportResult,
    TenantExportService,
)


@pytest.fixture
async def export_service():
    """Create a test export service instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        service = TenantExportService(
            database_url="postgresql://test:test@localhost:5432/test", storage_path=temp_dir
        )

        # Mock the database pool and event publisher
        service._pool = AsyncMock()
        service._event_publisher = AsyncMock()
        service._event_publisher.start = AsyncMock()
        service._event_publisher.stop = AsyncMock()
        service._event_publisher.publish_export_event = AsyncMock()

        await service.initialize()

        try:
            yield service
        finally:
            await service.close()


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "pricing.quotes": [
            {
                "id": str(uuid.uuid4()),
                "tenant_id": "test-tenant-id",
                "symbol": "USD/EUR",
                "price": 0.85,
                "created_at": "2026-01-01T10:00:00Z",
                "updated_at": "2026-01-01T10:00:00Z",
            },
            {
                "id": str(uuid.uuid4()),
                "tenant_id": "test-tenant-id",
                "symbol": "GBP/USD",
                "price": 1.25,
                "created_at": "2026-01-01T11:00:00Z",
                "updated_at": "2026-01-01T11:00:00Z",
            },
        ],
        "reference_data.instruments": [
            {
                "id": str(uuid.uuid4()),
                "tenant_id": "test-tenant-id",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "created_at": "2026-01-01T09:00:00Z",
                "updated_at": "2026-01-01T09:00:00Z",
            }
        ],
    }


class TestExportOptions:
    """Test ExportOptions configuration."""

    def test_default_options(self):
        """Test default export options."""
        options = ExportOptions()

        assert options.format == ExportFormat.JSON
        assert options.compress is True
        assert options.encrypt is True
        assert options.include_deleted is False
        assert options.include_audit_fields is True
        assert options.batch_size == 1000
        assert options.max_file_size_mb == 100
        assert options.encryption_key is not None

    def test_custom_options(self):
        """Test custom export options."""
        custom_key = Fernet.generate_key()

        options = ExportOptions(
            format=ExportFormat.CSV,
            compress=False,
            encrypt=False,
            include_deleted=True,
            include_audit_fields=False,
            batch_size=500,
            max_file_size_mb=50,
            encryption_key=custom_key,
        )

        assert options.format == ExportFormat.CSV
        assert options.compress is False
        assert options.encrypt is False
        assert options.include_deleted is True
        assert options.include_audit_fields is False
        assert options.batch_size == 500
        assert options.max_file_size_mb == 50
        assert options.encryption_key == custom_key


class TestTenantExportResult:
    """Test TenantExportResult data structure."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        export_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        created_at = datetime.now(UTC)

        result = TenantExportResult(
            export_id=export_id,
            tenant_id=tenant_id,
            status=ExportStatus.COMPLETED,
            file_path="/path/to/file.json",
            file_size_bytes=1024,
            records_exported=150,
            models_exported=["pricing.quotes", "reference_data.instruments"],
            created_at=created_at,
        )

        data = result.to_dict()

        assert data["export_id"] == export_id
        assert data["tenant_id"] == tenant_id
        assert data["status"] == ExportStatus.COMPLETED
        assert data["file_path"] == "/path/to/file.json"
        assert data["file_size_bytes"] == 1024
        assert data["records_exported"] == 150
        assert data["models_exported"] == ["pricing.quotes", "reference_data.instruments"]
        assert data["created_at"] == created_at.isoformat()


class TestTenantExportService:
    """Test TenantExportService functionality."""

    def test_service_initialization(self):
        """Test service initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = TenantExportService(
                database_url="postgresql://test:test@localhost:5432/test", storage_path=temp_dir
            )

            assert service.database_url == "postgresql://test:test@localhost:5432/test"
            assert service.storage_path == Path(temp_dir) / "tenant_exports"

    @pytest.mark.asyncio
    async def test_discover_tenant_models(self, export_service):
        """Test discovery of tenant models."""
        # Mock database response
        mock_rows = [
            {"table_schema": "pricing", "table_name": "quotes"},
            {"table_schema": "reference_data", "table_name": "instruments"},
            {"table_schema": "registry", "table_name": "tenant_quotas"},
        ]

        export_service._pool.acquire().__aenter__.return_value.fetch.return_value = mock_rows

        models = await export_service._discover_tenant_models()

        expected_models = ["pricing.quotes", "reference_data.instruments", "registry.tenant_quotas"]
        assert models == expected_models

    @pytest.mark.asyncio
    async def test_collect_model_data(self, export_service, sample_tenant_data):
        """Test collecting data for a specific model."""
        model_name = "pricing.quotes"
        options = ExportOptions()

        # Mock tenant context
        with patch("registry.export_service.get_current_tenant_id") as mock_get_tenant:
            mock_get_tenant.return_value = "test-tenant-id"

            # Mock database responses
            mock_conn = export_service._pool.acquire().__aenter__.return_value
            mock_conn.fetchval.return_value = True  # has_deleted_at
            mock_conn.fetch.return_value = [
                dict(sample_tenant_data["pricing.quotes"][0]),
                dict(sample_tenant_data["pricing.quotes"][1]),
            ]

            data = await export_service._collect_model_data(model_name, options)

            assert len(data) == 2
            assert data[0]["symbol"] == "USD/EUR"
            assert data[1]["symbol"] == "GBP/USD"

    @pytest.mark.asyncio
    async def test_collect_model_data_exclude_deleted(self, export_service):
        """Test collecting data excluding soft-deleted records."""
        model_name = "pricing.quotes"
        options = ExportOptions(include_deleted=False)

        with patch("registry.export_service.get_current_tenant_id") as mock_get_tenant:
            mock_get_tenant.return_value = "test-tenant-id"

            mock_conn = export_service._pool.acquire().__aenter__.return_value
            mock_conn.fetchval.return_value = True  # has_deleted_at
            mock_conn.fetch.return_value = []

            await export_service._collect_model_data(model_name, options)

            # Verify the query included deleted_at IS NULL
            calls = mock_conn.fetch.call_args_list
            assert len(calls) > 0
            query = calls[0][0][0]  # First call, first argument (the query)
            assert "deleted_at IS NULL" in query

    @pytest.mark.asyncio
    async def test_collect_model_data_exclude_audit_fields(
        self, export_service, sample_tenant_data
    ):
        """Test collecting data excluding audit fields."""
        model_name = "pricing.quotes"
        options = ExportOptions(include_audit_fields=False)

        with patch("registry.export_service.get_current_tenant_id") as mock_get_tenant:
            mock_get_tenant.return_value = "test-tenant-id"

            mock_conn = export_service._pool.acquire().__aenter__.return_value
            mock_conn.fetchval.return_value = False  # no deleted_at column
            mock_conn.fetch.return_value = [dict(sample_tenant_data["pricing.quotes"][0])]

            data = await export_service._collect_model_data(model_name, options)

            # Verify audit fields are removed
            assert len(data) == 1
            record = data[0]
            assert "created_at" not in record
            assert "updated_at" not in record

    def test_create_json_content(self, export_service, sample_tenant_data):
        """Test JSON content creation."""
        content = export_service._create_json_content(sample_tenant_data)

        parsed = json.loads(content)

        assert "export_version" in parsed
        assert "exported_at" in parsed
        assert "data" in parsed
        assert parsed["data"] == sample_tenant_data

    def test_create_csv_content(self, export_service, sample_tenant_data):
        """Test CSV content creation."""
        content = export_service._create_csv_content(sample_tenant_data)

        # Should contain model headers and data
        assert "# Model: pricing.quotes" in content
        assert "# Model: reference_data.instruments" in content
        assert "USD/EUR" in content
        assert "AAPL" in content

    def test_create_jsonl_content(self, export_service, sample_tenant_data):
        """Test JSON Lines content creation."""
        content = export_service._create_jsonl_content(sample_tenant_data)

        lines = content.strip().split("\n")

        # Should have one line per record
        assert len(lines) == 3  # 2 quotes + 1 instrument

        # Each line should be valid JSON with _model field
        for line in lines:
            record = json.loads(line)
            assert "_model" in record
            assert record["_model"] in ["pricing.quotes", "reference_data.instruments"]

    def test_encrypt_and_decrypt_content(self, export_service):
        """Test content encryption and decryption."""
        content = b"Test content for encryption"
        key = Fernet.generate_key()

        # Encrypt
        encrypted = export_service._encrypt_content(content, key)
        assert encrypted != content

        # Decrypt
        decrypted = export_service.decrypt_content(encrypted, key)
        assert decrypted == content

    @pytest.mark.asyncio
    async def test_create_export_file_json(self, export_service, sample_tenant_data):
        """Test creating export file in JSON format."""
        export_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        options = ExportOptions(format=ExportFormat.JSON, compress=False, encrypt=False)

        file_path = await export_service._create_export_file(
            sample_tenant_data, export_id, tenant_id, options
        )

        # Verify file exists and has correct content
        assert Path(file_path).exists()

        with open(file_path) as f:
            content = f.read()
            parsed = json.loads(content)
            assert parsed["data"] == sample_tenant_data

    @pytest.mark.asyncio
    async def test_create_export_file_compressed(self, export_service, sample_tenant_data):
        """Test creating compressed export file."""
        export_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        options = ExportOptions(format=ExportFormat.JSON, compress=True, encrypt=False)

        file_path = await export_service._create_export_file(
            sample_tenant_data, export_id, tenant_id, options
        )

        # Verify file exists and is compressed
        assert Path(file_path).exists()
        assert file_path.endswith(".gz")

        with gzip.open(file_path, "rt") as f:
            content = f.read()
            parsed = json.loads(content)
            assert parsed["data"] == sample_tenant_data

    @pytest.mark.asyncio
    async def test_create_export_file_encrypted(self, export_service, sample_tenant_data):
        """Test creating encrypted export file."""
        export_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        key = Fernet.generate_key()
        options = ExportOptions(
            format=ExportFormat.JSON, compress=False, encrypt=True, encryption_key=key
        )

        file_path = await export_service._create_export_file(
            sample_tenant_data, export_id, tenant_id, options
        )

        # Verify file exists and is encrypted
        assert Path(file_path).exists()
        assert file_path.endswith(".enc")

        with open(file_path, "rb") as f:
            encrypted_content = f.read()

        # Decrypt and verify content
        decrypted = export_service.decrypt_content(encrypted_content, key)
        parsed = json.loads(decrypted.decode("utf-8"))
        assert parsed["data"] == sample_tenant_data

    @pytest.mark.asyncio
    async def test_export_tenant_data_success(self, export_service, sample_tenant_data):
        """Test successful tenant data export."""
        tenant_id = str(uuid.uuid4())
        options = ExportOptions(compress=False, encrypt=False)
        reason = "Test export for unit testing"

        # Mock dependencies
        with patch("registry.export_service.with_tenant") as mock_with_tenant:
            mock_with_tenant.return_value.__aenter__ = AsyncMock()
            mock_with_tenant.return_value.__aexit__ = AsyncMock()

            with patch.object(export_service, "_discover_tenant_models") as mock_discover:
                mock_discover.return_value = ["pricing.quotes"]

                with patch.object(export_service, "_collect_model_data") as mock_collect:
                    mock_collect.return_value = sample_tenant_data["pricing.quotes"]

                    result = await export_service.export_tenant_data(tenant_id, options, reason)

                    assert result.status == ExportStatus.COMPLETED
                    assert result.tenant_id == tenant_id
                    assert result.records_exported == 2
                    assert "pricing.quotes" in result.models_exported
                    assert result.file_path is not None
                    assert Path(result.file_path).exists()

    @pytest.mark.asyncio
    async def test_export_tenant_data_failure(self, export_service):
        """Test export failure handling."""
        tenant_id = str(uuid.uuid4())
        options = ExportOptions()
        reason = "Test export failure"

        # Mock failure in model discovery
        with patch("registry.export_service.with_tenant") as mock_with_tenant:
            mock_with_tenant.return_value.__aenter__ = AsyncMock()
            mock_with_tenant.return_value.__aexit__ = AsyncMock()

            with patch.object(export_service, "_discover_tenant_models") as mock_discover:
                mock_discover.side_effect = Exception("Database connection failed")

                with pytest.raises(RuntimeError, match="Export failed"):
                    await export_service.export_tenant_data(tenant_id, options, reason)

    @pytest.mark.asyncio
    async def test_get_export_result(self, export_service):
        """Test getting export result by ID."""
        export_id = str(uuid.uuid4())

        # Create a test file
        test_file = export_service.storage_path / f"tenant_test_{export_id}_20260101_120000.json"
        test_file.write_text('{"test": "data"}')

        result = await export_service.get_export_result(export_id)

        assert result is not None
        assert result.export_id == export_id
        assert result.status == ExportStatus.COMPLETED
        assert result.file_path == str(test_file)
        assert result.file_size_bytes == len('{"test": "data"}')

    @pytest.mark.asyncio
    async def test_get_export_result_not_found(self, export_service):
        """Test getting non-existent export result."""
        export_id = str(uuid.uuid4())

        result = await export_service.get_export_result(export_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_exports(self, export_service):
        """Test cleanup of expired export files."""
        # Create test files with different ages
        old_file = export_service.storage_path / "tenant_old_export.json"
        old_file.write_text('{"old": "data"}')

        # Set modification time to 8 days ago
        old_time = datetime.now().timestamp() - (8 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        new_file = export_service.storage_path / "tenant_new_export.json"
        new_file.write_text('{"new": "data"}')

        # Run cleanup with 7 day retention
        deleted_count = await export_service.cleanup_expired_exports(max_age_days=7)

        assert deleted_count == 1
        assert not old_file.exists()
        assert new_file.exists()

    @pytest.mark.asyncio
    async def test_health_check_success(self, export_service):
        """Test successful health check."""
        # Mock database health check
        mock_conn = export_service._pool.acquire().__aenter__.return_value
        mock_conn.fetchval.return_value = 1

        is_healthy = await export_service.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, export_service):
        """Test health check failure."""
        # Mock database failure
        mock_conn = export_service._pool.acquire().__aenter__.return_value
        mock_conn.fetchval.side_effect = Exception("Database connection failed")

        is_healthy = await export_service.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_emit_export_event(self, export_service):
        """Test export event emission."""
        result = TenantExportResult(
            export_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()), status=ExportStatus.COMPLETED
        )
        reason = "Test export event"

        await export_service._emit_export_event("export.completed", result, reason)

        # Verify event was published
        export_service._event_publisher.publish_export_event.assert_called_once()
        call_args = export_service._event_publisher.publish_export_event.call_args[1]
        assert call_args["event_type"] == "export.completed"
        assert call_args["export_id"] == result.export_id
        assert call_args["tenant_id"] == result.tenant_id
        assert call_args["reason"] == reason


class TestExportFormats:
    """Test different export format implementations."""

    @pytest.mark.asyncio
    async def test_json_format_content(self, export_service, sample_tenant_data):
        """Test JSON format creates valid JSON content."""
        content = export_service._create_json_content(sample_tenant_data)

        # Should be valid JSON
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
        assert "export_version" in parsed
        assert "data" in parsed

        # Should preserve data structure
        assert parsed["data"]["pricing.quotes"] == sample_tenant_data["pricing.quotes"]

    @pytest.mark.asyncio
    async def test_csv_format_content(self, export_service, sample_tenant_data):
        """Test CSV format creates proper CSV content."""
        content = export_service._create_csv_content(sample_tenant_data)

        lines = content.split("\n")

        # Should have model section headers
        model_headers = [line for line in lines if line.startswith("# Model:")]
        assert len(model_headers) == 2

        # Should have CSV headers and data
        assert any("id,tenant_id,symbol" in line for line in lines)

    @pytest.mark.asyncio
    async def test_jsonl_format_content(self, export_service, sample_tenant_data):
        """Test JSON Lines format creates valid JSONL content."""
        content = export_service._create_jsonl_content(sample_tenant_data)

        lines = [line for line in content.split("\n") if line.strip()]

        # Should have one line per record
        total_records = sum(len(records) for records in sample_tenant_data.values())
        assert len(lines) == total_records

        # Each line should be valid JSON with model info
        for line in lines:
            record = json.loads(line)
            assert "_model" in record
            assert "id" in record
            assert "tenant_id" in record


class TestExportSecurity:
    """Test export security features."""

    def test_encryption_key_generation(self):
        """Test automatic encryption key generation."""
        options1 = ExportOptions()
        options2 = ExportOptions()

        # Each instance should have a unique key
        assert options1.encryption_key != options2.encryption_key
        assert len(options1.encryption_key) == len(Fernet.generate_key())

    def test_custom_encryption_key(self):
        """Test using custom encryption key."""
        custom_key = Fernet.generate_key()
        options = ExportOptions(encryption_key=custom_key)

        assert options.encryption_key == custom_key

    @pytest.mark.asyncio
    async def test_file_encryption_prevents_plain_text_access(
        self, export_service, sample_tenant_data
    ):
        """Test that encrypted files cannot be read as plain text."""
        export_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        key = Fernet.generate_key()

        options = ExportOptions(
            format=ExportFormat.JSON, compress=False, encrypt=True, encryption_key=key
        )

        file_path = await export_service._create_export_file(
            sample_tenant_data, export_id, tenant_id, options
        )

        # Reading as plain text should not give original data
        with open(file_path, errors="ignore") as f:
            plain_content = f.read()

        # Original data should not be visible in plain text
        assert "pricing.quotes" not in plain_content
        assert "USD/EUR" not in plain_content


@pytest.fixture
async def mock_export_service():
    """Create a fully mocked export service instance for testing without database connections."""
    with tempfile.TemporaryDirectory() as temp_dir:
        service = TenantExportService(
            database_url="postgresql://test:test@localhost:5432/test", storage_path=temp_dir
        )

        # Mock the database pool and event publisher without initializing
        service._pool = AsyncMock()
        service._event_publisher = AsyncMock()
        service._event_publisher.start = AsyncMock()
        service._event_publisher.stop = AsyncMock()
        service._event_publisher.publish_export_event = AsyncMock()

        try:
            yield service
        finally:
            # Mock the close method to avoid database cleanup
            pass


class TestDataExportRequirements:
    """Test specific requirements for data export functionality.

    These tests address the specific requirements from task 13.2:
    - Test all models exported
    - Test encryption applied
    - Test audit event emitted
    """

    @pytest.mark.asyncio
    async def test_all_models_exported(self, mock_export_service, sample_tenant_data):
        """Test that all discovered tenant models are exported."""
        tenant_id = str(uuid.uuid4())
        options = ExportOptions(compress=False, encrypt=False)
        reason = "Test all models exported"

        # Mock dependencies
        with patch("registry.export_service.with_tenant") as mock_with_tenant:
            mock_with_tenant.return_value.__aenter__ = AsyncMock()
            mock_with_tenant.return_value.__aexit__ = AsyncMock()

            with patch.object(mock_export_service, "_discover_tenant_models") as mock_discover:
                # Set up multiple models to be discovered
                expected_models = [
                    "pricing.quotes",
                    "reference_data.instruments",
                    "trading.positions",
                    "risk.exposures",
                ]
                mock_discover.return_value = expected_models

                # Mock data collection for each model
                with patch.object(mock_export_service, "_collect_model_data") as mock_collect:

                    def collect_side_effect(model_name, options):
                        # Return different data for each model
                        if model_name == "pricing.quotes":
                            return sample_tenant_data["pricing.quotes"]
                        elif model_name == "reference_data.instruments":
                            return sample_tenant_data["reference_data.instruments"]
                        else:
                            # Return mock data for other models
                            return [
                                {"id": f"{model_name}_id", "tenant_id": tenant_id, "value": "test"}
                            ]

                    mock_collect.side_effect = collect_side_effect

                    result = await mock_export_service.export_tenant_data(
                        tenant_id, options, reason
                    )

                    # Verify all models were discovered and exported
                    assert result.status == ExportStatus.COMPLETED
                    assert len(result.models_exported) == len(expected_models)

                    # Check that all expected models are in the exported models
                    for model in expected_models:
                        assert model in result.models_exported

                    # Verify _collect_model_data was called for each model
                    assert mock_collect.call_count == len(expected_models)

                    # Verify the exported data contains all models
                    assert Path(result.file_path).exists()
                    with open(result.file_path) as f:
                        content = json.loads(f.read())
                        exported_data = content["data"]

                        # All models should be present in the exported data
                        for model in expected_models:
                            assert model in exported_data
                            assert len(exported_data[model]) > 0

    @pytest.mark.asyncio
    async def test_encryption_applied(self, mock_export_service, sample_tenant_data):
        """Test that encryption is properly applied to exported data."""
        tenant_id = str(uuid.uuid4())
        encryption_key = Fernet.generate_key()
        options = ExportOptions(
            format=ExportFormat.JSON, compress=False, encrypt=True, encryption_key=encryption_key
        )
        reason = "Test encryption applied"

        # Mock dependencies
        with patch("registry.export_service.with_tenant") as mock_with_tenant:
            mock_with_tenant.return_value.__aenter__ = AsyncMock()
            mock_with_tenant.return_value.__aexit__ = AsyncMock()

            with patch.object(mock_export_service, "_discover_tenant_models") as mock_discover:
                mock_discover.return_value = ["pricing.quotes"]

                with patch.object(mock_export_service, "_collect_model_data") as mock_collect:
                    mock_collect.return_value = sample_tenant_data["pricing.quotes"]

                    result = await mock_export_service.export_tenant_data(
                        tenant_id, options, reason
                    )

                    # Verify export completed successfully
                    assert result.status == ExportStatus.COMPLETED
                    assert result.file_path is not None
                    assert Path(result.file_path).exists()

                    # Verify file has encryption extension
                    assert result.file_path.endswith(".enc")

                    # Verify the file is actually encrypted
                    with open(result.file_path, "rb") as f:
                        encrypted_content = f.read()

                    # Content should not contain readable JSON
                    try:
                        # This should fail because content is encrypted
                        json.loads(encrypted_content.decode("utf-8"))
                        assert False, "File content should be encrypted and not readable as JSON"
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # This is expected - the file is encrypted
                        pass

                    # Verify we can decrypt the content with the correct key
                    decrypted_content = mock_export_service.decrypt_content(
                        encrypted_content, encryption_key
                    )
                    decrypted_json = json.loads(decrypted_content.decode("utf-8"))

                    # Decrypted content should contain our original data
                    assert "data" in decrypted_json
                    assert "pricing.quotes" in decrypted_json["data"]
                    assert (
                        decrypted_json["data"]["pricing.quotes"]
                        == sample_tenant_data["pricing.quotes"]
                    )

                    # Verify we cannot decrypt with wrong key
                    wrong_key = Fernet.generate_key()
                    with pytest.raises(Exception):
                        mock_export_service.decrypt_content(encrypted_content, wrong_key)

    @pytest.mark.asyncio
    async def test_audit_event_emitted(self, mock_export_service, sample_tenant_data):
        """Test that audit events are properly emitted during export."""
        tenant_id = str(uuid.uuid4())
        options = ExportOptions(compress=False, encrypt=False)
        reason = "Test audit event emitted"

        # Mock dependencies
        with patch("registry.export_service.with_tenant") as mock_with_tenant:
            mock_with_tenant.return_value.__aenter__ = AsyncMock()
            mock_with_tenant.return_value.__aexit__ = AsyncMock()

            with patch.object(mock_export_service, "_discover_tenant_models") as mock_discover:
                mock_discover.return_value = ["pricing.quotes"]

                with patch.object(mock_export_service, "_collect_model_data") as mock_collect:
                    mock_collect.return_value = sample_tenant_data["pricing.quotes"]

                    # Reset the mock to track calls
                    mock_export_service._event_publisher.publish_export_event.reset_mock()

                    result = await mock_export_service.export_tenant_data(
                        tenant_id, options, reason
                    )

                    # Verify export completed successfully
                    assert result.status == ExportStatus.COMPLETED

                    # Verify audit events were emitted
                    publish_calls = (
                        mock_export_service._event_publisher.publish_export_event.call_args_list
                    )
                    assert len(publish_calls) == 2  # Started and completed events

                    # Verify export.started event
                    started_call = publish_calls[0]
                    started_kwargs = started_call[1]
                    assert started_kwargs["event_type"] == "export.started"
                    assert started_kwargs["export_id"] == result.export_id
                    assert started_kwargs["tenant_id"] == tenant_id
                    assert started_kwargs["reason"] == reason
                    assert started_kwargs["status"] == ExportStatus.IN_PROGRESS

                    # Verify export.completed event
                    completed_call = publish_calls[1]
                    completed_kwargs = completed_call[1]
                    assert completed_kwargs["event_type"] == "export.completed"
                    assert completed_kwargs["export_id"] == result.export_id
                    assert completed_kwargs["tenant_id"] == tenant_id
                    assert completed_kwargs["reason"] == reason
                    assert completed_kwargs["status"] == ExportStatus.COMPLETED
                    assert completed_kwargs["records_exported"] == 2
                    assert completed_kwargs["models_exported"] == ["pricing.quotes"]

    @pytest.mark.asyncio
    async def test_audit_event_emitted_on_failure(self, mock_export_service):
        """Test that audit events are emitted even when export fails."""
        tenant_id = str(uuid.uuid4())
        options = ExportOptions()
        reason = "Test audit event on failure"

        # Mock dependencies to simulate failure
        with patch("registry.export_service.with_tenant") as mock_with_tenant:
            mock_with_tenant.return_value.__aenter__ = AsyncMock()
            mock_with_tenant.return_value.__aexit__ = AsyncMock()

            with patch.object(mock_export_service, "_discover_tenant_models") as mock_discover:
                mock_discover.side_effect = Exception("Database connection failed")

                # Reset the mock to track calls
                mock_export_service._event_publisher.publish_export_event.reset_mock()

                # Export should fail
                with pytest.raises(RuntimeError, match="Export failed"):
                    await mock_export_service.export_tenant_data(tenant_id, options, reason)

                # Verify audit events were emitted even on failure
                publish_calls = (
                    mock_export_service._event_publisher.publish_export_event.call_args_list
                )
                assert len(publish_calls) == 2  # Started and failed events

                # Verify export.started event
                started_call = publish_calls[0]
                started_kwargs = started_call[1]
                assert started_kwargs["event_type"] == "export.started"
                assert started_kwargs["tenant_id"] == tenant_id
                assert started_kwargs["reason"] == reason

                # Verify export.failed event
                failed_call = publish_calls[1]
                failed_kwargs = failed_call[1]
                assert failed_kwargs["event_type"] == "export.failed"
                assert failed_kwargs["tenant_id"] == tenant_id
                assert failed_kwargs["reason"] == reason
                assert failed_kwargs["status"] == ExportStatus.FAILED
