"""End-to-End Tenant Data Export Tests.

These tests verify the complete tenant data export flow:
1. Create tenant and mock data export functionality
2. Trigger export through the service layer
3. Verify export completeness and data integrity
4. Test various export formats and options

This covers the full export pipeline from service request through data collection
to file generation and verification.
"""
import json
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from registry.export_service import (
    ExportFormat,
    ExportOptions,
    ExportStatus,
    TenantExportService,
)
from registry.models.tenant import Tenant, TenantStatus

# These tests require integration setup and may be slow
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.export]


@pytest.fixture
async def export_service_with_storage():
    """Create export service with real storage for E2E testing."""
    temp_dir = tempfile.mkdtemp()

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

    yield service, temp_dir

    await service.close()

    # Cleanup temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def comprehensive_tenant_data():
    """Comprehensive sample data across multiple tenant models."""
    tenant_id = str(uuid.uuid4())
    base_time = datetime.now(UTC)

    return {
        "tenant_id": tenant_id,
        "models": {
            "pricing.quotes": [
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "symbol": "USD/EUR",
                    "price": 0.8523,
                    "bid": 0.8521,
                    "ask": 0.8525,
                    "volume": 1000000,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "symbol": "GBP/USD",
                    "price": 1.2456,
                    "bid": 1.2454,
                    "ask": 1.2458,
                    "volume": 750000,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "symbol": "JPY/USD",
                    "price": 0.0067,
                    "bid": 0.0066,
                    "ask": 0.0068,
                    "volume": 2000000,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
            ],
            "reference_data.instruments": [
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "isin": "US0378331005",
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "symbol": "MSFT",
                    "name": "Microsoft Corp",
                    "isin": "US5949181045",
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
            ],
            "trading.positions": [
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "instrument_id": "AAPL",
                    "quantity": 1000,
                    "avg_price": 150.25,
                    "market_value": 150250.00,
                    "unrealized_pnl": 2500.00,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "instrument_id": "MSFT",
                    "quantity": 500,
                    "avg_price": 300.50,
                    "market_value": 150250.00,
                    "unrealized_pnl": -1200.00,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                },
            ],
            "risk.exposures": [
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "risk_type": "market",
                    "instrument_id": "AAPL",
                    "exposure_amount": 150250.00,
                    "var_1d": 5000.00,
                    "var_10d": 15000.00,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                }
            ],
            "registry.tenant_quotas": [
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "max_api_calls_per_day": 10000,
                    "max_users": 100,
                    "max_storage_mb": 5000,
                    "max_records_per_model": 50000,
                    "created_at": base_time.isoformat(),
                    "updated_at": base_time.isoformat(),
                }
            ],
        },
    }


@pytest.fixture
def sample_tenant():
    """Create a sample tenant for testing."""
    return Tenant(
        id=str(uuid.uuid4()),
        slug="export-test-tenant",
        name="Export Test Tenant",
        status=TenantStatus.ACTIVE,
        config={"test_export": True},
        keycloak_org_id="org-export-123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestTenantExportE2E:
    """End-to-end tests for complete tenant data export functionality."""

    @pytest.mark.asyncio
    async def test_e2e_complete_export_with_data_verification(
        self, export_service_with_storage, comprehensive_tenant_data, sample_tenant
    ):
        """
        Test complete E2E export flow with comprehensive data verification.

        Flow: Mock tenant data → Export → Verify data completeness
        """
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id
        test_data = comprehensive_tenant_data

        # Update test data to match tenant ID
        for model_name, records in test_data["models"].items():
            for record in records:
                record["tenant_id"] = tenant_id

        # =================================================================
        # Setup: Mock data discovery and collection
        # =================================================================

        discovered_models = list(test_data["models"].keys())

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            mock_discover.return_value = discovered_models

            with patch.object(export_service, "_collect_model_data") as mock_collect:

                def collect_side_effect(model_name, options):
                    return test_data["models"].get(model_name, [])

                mock_collect.side_effect = collect_side_effect

                with patch("registry.export_service.with_tenant") as mock_with_tenant:
                    mock_with_tenant.return_value.__aenter__ = AsyncMock()
                    mock_with_tenant.return_value.__aexit__ = AsyncMock()

                    # =============================================================
                    # Execute: Run export
                    # =============================================================

                    export_options = ExportOptions(
                        format=ExportFormat.JSON,
                        compress=False,
                        encrypt=False,
                        include_deleted=False,
                        include_audit_fields=True,
                    )

                    result = await export_service.export_tenant_data(
                        tenant_id=tenant_id,
                        options=export_options,
                        reason="E2E export test with data verification",
                    )

                    # =============================================================
                    # Verify: Export completed successfully
                    # =============================================================

                    assert result.status == ExportStatus.COMPLETED
                    assert result.tenant_id == tenant_id
                    assert result.file_path is not None
                    assert Path(result.file_path).exists()

                    # Calculate expected record count
                    expected_record_count = sum(
                        len(records) for records in test_data["models"].values()
                    )
                    assert result.records_exported == expected_record_count

                    # Verify all models were exported
                    assert len(result.models_exported) == len(discovered_models)
                    for model_name in discovered_models:
                        assert model_name in result.models_exported

                    # =============================================================
                    # Verify: Export file content
                    # =============================================================

                    with open(result.file_path) as f:
                        export_content = json.load(f)

                    # Verify export metadata
                    assert "export_version" in export_content
                    assert "exported_at" in export_content
                    assert "data" in export_content

                    exported_data = export_content["data"]

                    # Verify all models present in export
                    for model_name in discovered_models:
                        assert model_name in exported_data

                    # =============================================================
                    # DETAILED DATA COMPLETENESS VERIFICATION
                    # =============================================================

                    # Verify pricing quotes
                    exported_quotes = exported_data["pricing.quotes"]
                    expected_quotes = test_data["models"]["pricing.quotes"]
                    assert len(exported_quotes) == len(expected_quotes)

                    # Check specific quote data integrity
                    quote_symbols = [q["symbol"] for q in exported_quotes]
                    assert "USD/EUR" in quote_symbols
                    assert "GBP/USD" in quote_symbols
                    assert "JPY/USD" in quote_symbols

                    # Verify all quotes belong to correct tenant
                    for quote in exported_quotes:
                        assert quote["tenant_id"] == tenant_id
                        assert "id" in quote
                        assert "price" in quote
                        assert "bid" in quote
                        assert "ask" in quote
                        assert "volume" in quote

                    # Verify reference data instruments
                    exported_instruments = exported_data["reference_data.instruments"]
                    expected_instruments = test_data["models"]["reference_data.instruments"]
                    assert len(exported_instruments) == len(expected_instruments)

                    instrument_symbols = [i["symbol"] for i in exported_instruments]
                    assert "AAPL" in instrument_symbols
                    assert "MSFT" in instrument_symbols

                    for instrument in exported_instruments:
                        assert instrument["tenant_id"] == tenant_id
                        assert "id" in instrument
                        assert "name" in instrument
                        assert "isin" in instrument
                        assert "currency" in instrument
                        assert "exchange" in instrument
                        assert "sector" in instrument

                    # Verify trading positions
                    exported_positions = exported_data["trading.positions"]
                    expected_positions = test_data["models"]["trading.positions"]
                    assert len(exported_positions) == len(expected_positions)

                    for position in exported_positions:
                        assert position["tenant_id"] == tenant_id
                        assert "instrument_id" in position
                        assert "quantity" in position
                        assert "avg_price" in position
                        assert "market_value" in position
                        assert "unrealized_pnl" in position

                    # Verify risk exposures
                    exported_exposures = exported_data["risk.exposures"]
                    expected_exposures = test_data["models"]["risk.exposures"]
                    assert len(exported_exposures) == len(expected_exposures)

                    for exposure in exported_exposures:
                        assert exposure["tenant_id"] == tenant_id
                        assert "risk_type" in exposure
                        assert "instrument_id" in exposure
                        assert "exposure_amount" in exposure
                        assert "var_1d" in exposure
                        assert "var_10d" in exposure

                    # Verify quotas
                    exported_quotas = exported_data["registry.tenant_quotas"]
                    expected_quotas = test_data["models"]["registry.tenant_quotas"]
                    assert len(exported_quotas) == len(expected_quotas)

                    for quota in exported_quotas:
                        assert quota["tenant_id"] == tenant_id
                        assert "max_api_calls_per_day" in quota
                        assert "max_users" in quota
                        assert "max_storage_mb" in quota
                        assert "max_records_per_model" in quota

                    # =============================================================
                    # Verify: Service calls were made correctly
                    # =============================================================

                    # Verify discovery was called
                    mock_discover.assert_called_once()

                    # Verify data collection was called for each model
                    assert mock_collect.call_count == len(discovered_models)

                    # Verify with_tenant was used for tenant context
                    mock_with_tenant.assert_called_once_with(
                        tenant_id, "E2E export test with data verification"
                    )

    @pytest.mark.asyncio
    async def test_e2e_export_different_formats(
        self, export_service_with_storage, comprehensive_tenant_data, sample_tenant
    ):
        """
        Test E2E export in different formats (JSON, CSV, JSONL).

        Verifies that all formats produce valid output with correct data.
        """
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id

        # Use smaller dataset for format testing
        test_data = {
            "pricing.quotes": comprehensive_tenant_data["models"]["pricing.quotes"][:2],
            "reference_data.instruments": comprehensive_tenant_data["models"][
                "reference_data.instruments"
            ][:2],
        }

        # Update test data tenant IDs
        for model_name, records in test_data.items():
            for record in records:
                record["tenant_id"] = tenant_id

        discovered_models = list(test_data.keys())

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            mock_discover.return_value = discovered_models

            with patch.object(export_service, "_collect_model_data") as mock_collect:

                def collect_side_effect(model_name, options):
                    return test_data.get(model_name, [])

                mock_collect.side_effect = collect_side_effect

                with patch("registry.export_service.with_tenant") as mock_with_tenant:
                    mock_with_tenant.return_value.__aenter__ = AsyncMock()
                    mock_with_tenant.return_value.__aexit__ = AsyncMock()

                    # Test different formats
                    formats_to_test = [
                        (ExportFormat.JSON, ".json"),
                        (ExportFormat.CSV, ".csv"),
                        (ExportFormat.JSONL, ".jsonl"),
                    ]

                    export_results = []

                    for format_enum, expected_ext in formats_to_test:
                        export_options = ExportOptions(
                            format=format_enum, compress=False, encrypt=False
                        )

                        result = await export_service.export_tenant_data(
                            tenant_id=tenant_id,
                            options=export_options,
                            reason=f"E2E format test - {format_enum.value}",
                        )

                        assert result.status == ExportStatus.COMPLETED
                        assert result.records_exported == 4  # 2 quotes + 2 instruments
                        assert len(result.models_exported) == 2

                        export_results.append((result, format_enum, expected_ext))

                    # Verify files were created with correct extensions
                    files_by_ext = {}
                    for file_path in Path(temp_dir).iterdir():
                        if file_path.is_file():
                            ext = "".join(file_path.suffixes)
                            if not ext:
                                ext = file_path.suffix
                            files_by_ext[ext] = file_path

                    # Verify we have files for each format
                    assert ".json" in files_by_ext
                    assert ".csv" in files_by_ext
                    assert ".jsonl" in files_by_ext

                    # Verify JSON content
                    with open(files_by_ext[".json"]) as f:
                        json_content = json.load(f)

                    assert "data" in json_content
                    assert "pricing.quotes" in json_content["data"]
                    assert "reference_data.instruments" in json_content["data"]
                    assert len(json_content["data"]["pricing.quotes"]) == 2
                    assert len(json_content["data"]["reference_data.instruments"]) == 2

                    # Verify CSV content
                    with open(files_by_ext[".csv"]) as f:
                        csv_content = f.read()

                    assert "# Model: pricing.quotes" in csv_content
                    assert "# Model: reference_data.instruments" in csv_content
                    # Should contain some of our test data
                    assert "USD/EUR" in csv_content or "AAPL" in csv_content

                    # Verify JSONL content
                    with open(files_by_ext[".jsonl"]) as f:
                        jsonl_lines = [line.strip() for line in f if line.strip()]

                    assert len(jsonl_lines) == 4  # 2 quotes + 2 instruments

                    # Each line should be valid JSON with _model field
                    for line in jsonl_lines:
                        record = json.loads(line)
                        assert "_model" in record
                        assert record["_model"] in ["pricing.quotes", "reference_data.instruments"]
                        assert "tenant_id" in record
                        assert record["tenant_id"] == tenant_id

    @pytest.mark.asyncio
    async def test_e2e_export_with_encryption(
        self, export_service_with_storage, comprehensive_tenant_data, sample_tenant
    ):
        """
        Test E2E export with encryption enabled.

        Verifies that encryption works correctly in the full pipeline.
        """
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id

        # Use limited data for encryption testing
        test_data = {"pricing.quotes": comprehensive_tenant_data["models"]["pricing.quotes"][:1]}

        # Update tenant ID
        for record in test_data["pricing.quotes"]:
            record["tenant_id"] = tenant_id

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            mock_discover.return_value = ["pricing.quotes"]

            with patch.object(export_service, "_collect_model_data") as mock_collect:
                mock_collect.return_value = test_data["pricing.quotes"]

                with patch("registry.export_service.with_tenant") as mock_with_tenant:
                    mock_with_tenant.return_value.__aenter__ = AsyncMock()
                    mock_with_tenant.return_value.__aexit__ = AsyncMock()

                    # Export with encryption
                    from cryptography.fernet import Fernet

                    encryption_key = Fernet.generate_key()

                    export_options = ExportOptions(
                        format=ExportFormat.JSON,
                        compress=False,
                        encrypt=True,
                        encryption_key=encryption_key,
                    )

                    result = await export_service.export_tenant_data(
                        tenant_id=tenant_id, options=export_options, reason="E2E encryption test"
                    )

                    assert result.status == ExportStatus.COMPLETED
                    assert result.file_path.endswith(".enc")

                    # Verify file is encrypted (not readable as plain JSON)
                    with open(result.file_path, "rb") as f:
                        encrypted_content = f.read()

                    # Should not be able to read as plain JSON
                    try:
                        json.loads(encrypted_content.decode("utf-8"))
                        assert False, "File should be encrypted, not plain JSON"
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Expected - file is encrypted
                        pass

                    # Should be able to decrypt with the correct key
                    decrypted_content = export_service.decrypt_content(
                        encrypted_content, encryption_key
                    )
                    decrypted_json = json.loads(decrypted_content.decode("utf-8"))

                    # Verify decrypted content contains our data
                    assert "data" in decrypted_json
                    assert "pricing.quotes" in decrypted_json["data"]
                    assert len(decrypted_json["data"]["pricing.quotes"]) == 1

    @pytest.mark.asyncio
    async def test_e2e_export_with_compression(
        self, export_service_with_storage, comprehensive_tenant_data, sample_tenant
    ):
        """
        Test E2E export with compression enabled.

        Verifies that compression works correctly.
        """
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id

        # Use all data for compression testing
        test_data = comprehensive_tenant_data["models"]

        # Update tenant IDs
        for model_name, records in test_data.items():
            for record in records:
                record["tenant_id"] = tenant_id

        discovered_models = list(test_data.keys())

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            mock_discover.return_value = discovered_models

            with patch.object(export_service, "_collect_model_data") as mock_collect:

                def collect_side_effect(model_name, options):
                    return test_data.get(model_name, [])

                mock_collect.side_effect = collect_side_effect

                with patch("registry.export_service.with_tenant") as mock_with_tenant:
                    mock_with_tenant.return_value.__aenter__ = AsyncMock()
                    mock_with_tenant.return_value.__aexit__ = AsyncMock()

                    # Export with compression
                    export_options = ExportOptions(
                        format=ExportFormat.JSON, compress=True, encrypt=False
                    )

                    result = await export_service.export_tenant_data(
                        tenant_id=tenant_id, options=export_options, reason="E2E compression test"
                    )

                    assert result.status == ExportStatus.COMPLETED
                    assert result.file_path.endswith(".gz")

                    # Verify file is compressed
                    import gzip

                    with gzip.open(result.file_path, "rt") as f:
                        uncompressed_content = f.read()
                        uncompressed_json = json.loads(uncompressed_content)

                    # Verify uncompressed content contains our data
                    assert "data" in uncompressed_json
                    assert len(uncompressed_json["data"]) == len(discovered_models)

                    # Calculate total expected records
                    total_expected_records = sum(len(records) for records in test_data.values())
                    assert result.records_exported == total_expected_records


class TestExportE2EErrorHandling:
    """Test error handling in E2E export scenarios."""

    @pytest.mark.asyncio
    async def test_e2e_export_with_no_data(self, export_service_with_storage, sample_tenant):
        """Test export when tenant has no data."""
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            mock_discover.return_value = ["pricing.quotes"]

            with patch.object(export_service, "_collect_model_data") as mock_collect:
                mock_collect.return_value = []  # No data

                with patch("registry.export_service.with_tenant") as mock_with_tenant:
                    mock_with_tenant.return_value.__aenter__ = AsyncMock()
                    mock_with_tenant.return_value.__aexit__ = AsyncMock()

                    export_options = ExportOptions(
                        format=ExportFormat.JSON, compress=False, encrypt=False
                    )

                    result = await export_service.export_tenant_data(
                        tenant_id=tenant_id, options=export_options, reason="E2E test with no data"
                    )

                    # Export should still succeed with empty data
                    assert result.status == ExportStatus.COMPLETED
                    assert result.records_exported == 0
                    assert "pricing.quotes" in result.models_exported

                    # Verify export file exists and contains empty data structure
                    with open(result.file_path) as f:
                        export_content = json.load(f)

                    assert "data" in export_content
                    assert "pricing.quotes" in export_content["data"]
                    assert len(export_content["data"]["pricing.quotes"]) == 0

    @pytest.mark.asyncio
    async def test_e2e_export_service_error_handling(
        self, export_service_with_storage, sample_tenant
    ):
        """Test export error handling when service operations fail."""
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            # Simulate discovery failure
            mock_discover.side_effect = Exception("Database connection failed")

            with patch("registry.export_service.with_tenant") as mock_with_tenant:
                mock_with_tenant.return_value.__aenter__ = AsyncMock()
                mock_with_tenant.return_value.__aexit__ = AsyncMock()

                export_options = ExportOptions(format=ExportFormat.JSON)

                # Export should fail
                with pytest.raises(RuntimeError, match="Export failed"):
                    await export_service.export_tenant_data(
                        tenant_id=tenant_id, options=export_options, reason="E2E error test"
                    )


class TestExportE2EPerformance:
    """Performance-related E2E export tests."""

    @pytest.mark.asyncio
    async def test_e2e_export_performance_large_dataset(
        self, export_service_with_storage, sample_tenant
    ):
        """Test export performance with larger dataset."""
        export_service, temp_dir = export_service_with_storage
        tenant_id = sample_tenant.id

        # Generate larger dataset
        large_dataset = {
            "pricing.quotes": [
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "symbol": f"PAIR{i:04d}",
                    "price": round(1.0 + (i * 0.0001), 6),
                    "bid": round(1.0 + (i * 0.0001) - 0.00005, 6),
                    "ask": round(1.0 + (i * 0.0001) + 0.00005, 6),
                    "volume": (i + 1) * 1000,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                for i in range(500)  # 500 records
            ]
        }

        with patch.object(export_service, "_discover_tenant_models") as mock_discover:
            mock_discover.return_value = ["pricing.quotes"]

            with patch.object(export_service, "_collect_model_data") as mock_collect:
                mock_collect.return_value = large_dataset["pricing.quotes"]

                with patch("registry.export_service.with_tenant") as mock_with_tenant:
                    mock_with_tenant.return_value.__aenter__ = AsyncMock()
                    mock_with_tenant.return_value.__aexit__ = AsyncMock()

                    # Track timing
                    import time

                    start_time = time.time()

                    export_options = ExportOptions(
                        format=ExportFormat.JSON,
                        compress=True,  # Use compression for large dataset
                        encrypt=False,
                    )

                    result = await export_service.export_tenant_data(
                        tenant_id=tenant_id,
                        options=export_options,
                        reason="E2E large dataset performance test",
                    )

                    end_time = time.time()
                    total_time = end_time - start_time

                    # Performance assertions
                    assert total_time < 10.0, f"Large export took too long: {total_time:.2f}s"
                    assert result.status == ExportStatus.COMPLETED
                    assert result.records_exported == 500

                    # Verify file was created and has reasonable size
                    export_file = Path(result.file_path)
                    assert export_file.exists()

                    file_size = export_file.stat().st_size
                    assert file_size > 1000, "Export file seems too small"
                    assert file_size < 5000000, "Export file seems too large"
